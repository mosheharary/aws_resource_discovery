"""
Neo4j client for managing graph database connections and operations.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
import json

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError

from core.config import DiscoveryConfig
from core.resource_info import ResourceInfo


class Neo4jClient:
    """Neo4j client for AWS resource discovery graph operations"""
    
    def __init__(self, config: DiscoveryConfig):
        """Initialize Neo4j client with configuration"""
        self.config = config
        self.logger = logging.getLogger('aws_discovery.neo4j')
        self.driver = None
        self._account_id = None
        
        # Connection statistics
        self.stats = {
            'nodes_created': 0,
            'relationships_created': 0,
            'cross_account_connections': 0,
            'nodes_updated': 0,
            'constraints_created': 0,
            'indexes_created': 0
        }
        
        if config.is_neo4j_enabled():
            self._connect()
    
    def _connect(self):
        """Establish connection to Neo4j database"""
        try:
            uri = self.config.get_neo4j_uri()
            self.logger.info(f"Connecting to Neo4j at {uri}")
            
            self.driver = GraphDatabase.driver(
                uri,
                auth=(self.config.graph_db_user, self.config.graph_db_password)
            )
            
            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                test_value = result.single()["test"]
                if test_value == 1:
                    self.logger.info("✓ Neo4j connection successful")
                else:
                    raise Exception("Connection test failed")
                    
        except AuthError as e:
            self.logger.error(f"✗ Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            self.logger.error(f"✗ Neo4j service unavailable: {e}")
            raise
        except Exception as e:
            self.logger.error(f"✗ Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j connection closed")
    
    def is_connected(self) -> bool:
        """Check if Neo4j connection is active"""
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                session.run("RETURN 1").single()
            return True
        except Exception:
            return False
    
    def reset_graph(self):
        """Reset the entire graph database"""
        if not self.config.reset_graph:
            return
        
        self.logger.info("🔄 Resetting Neo4j graph database")
        
        try:
            with self.driver.session() as session:
                # Delete all nodes and relationships
                session.run("MATCH (n) DETACH DELETE n")
                self.logger.info("✓ All nodes and relationships deleted")
                
                # Create constraints and indexes
                self._create_constraints_and_indexes(session)
                
        except Exception as e:
            self.logger.error(f"✗ Failed to reset graph: {e}")
            raise
    
    def _create_constraints_and_indexes(self, session):
        """Create necessary constraints and indexes"""
        constraints_and_indexes = [
            # Unique constraints
            "CREATE CONSTRAINT account_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT resource_arn_unique IF NOT EXISTS FOR (r:Resource) REQUIRE r.arn IS UNIQUE",
            
            # Indexes for performance
            "CREATE INDEX resource_type_index IF NOT EXISTS FOR (r:Resource) ON (r.resource_type)",
            "CREATE INDEX resource_region_index IF NOT EXISTS FOR (r:Resource) ON (r.region)",
            "CREATE INDEX resource_account_index IF NOT EXISTS FOR (r:Resource) ON (r.account_id)",
            "CREATE INDEX resource_service_index IF NOT EXISTS FOR (r:Resource) ON (r.service)",
        ]
        
        for statement in constraints_and_indexes:
            try:
                session.run(statement)
                self.stats['constraints_created'] += 1
                self.logger.debug(f"✓ Created constraint/index: {statement}")
            except Exception as e:
                self.logger.debug(f"Constraint/index already exists or failed: {e}")
    
    def create_account_node(self, account_id: str, account_name: Optional[str] = None):
        """Create or update account node"""
        self._account_id = account_id
        
        if not account_name:
            account_name = f"Account-{account_id}"
        
        self.logger.info(f"📊 Creating account node: {account_name} ({account_id})")
        
        try:
            with self.driver.session() as session:
                query = """
                MERGE (a:Account {id: $account_id})
                SET a.name = $account_name, a.updated_at = datetime()
                RETURN a
                """
                
                result = session.run(query, account_id=account_id, account_name=account_name)
                if result.single():
                    self.logger.info(f"✓ Account node created/updated: {account_name}")
                    self.stats['nodes_created'] += 1
                
        except Exception as e:
            self.logger.error(f"✗ Failed to create account node: {e}")
            raise
    
    def add_resources_to_graph(self, resources: List[ResourceInfo]):
        """Add resources to Neo4j graph"""
        if not resources:
            return
        
        self.logger.info(f"📈 Adding {len(resources)} resources to Neo4j graph")
        
        # Convert resources to dictionary format for enhanced components
        resources_dict = {}
        for resource in resources:
            if not resource.has_error() and resource.is_valid():
                resources_dict[resource.arn] = {
                    'resource_type': resource.resource_type,
                    'identifier': resource.identifier,
                    'service': resource.service,
                    'region': resource.region,
                    'properties': resource.properties or {}
                }
        
        # Group resources by type for efficient processing
        resources_by_type = defaultdict(list)
        for resource in resources:
            if not resource.has_error() and resource.is_valid():
                resources_by_type[resource.resource_type].append(resource)
        
        # Process each resource type
        for resource_type, type_resources in resources_by_type.items():
            self._add_resources_of_type(resource_type, type_resources)
        
        with self.driver.session() as session:
            # Create route rules from route tables
            self._create_route_rules(session, resources_dict)
            
            # Create enhanced service components
            self._create_enhanced_service_components(session, resources_dict)
            
            # Create relationships between resources
            self._create_resource_relationships(resources)
            
            # Log cross-account connections
            self._log_cross_account_connections(session)
        
        self.logger.info(f"✓ Added {self.stats['nodes_created']} nodes and {self.stats['relationships_created']} relationships")
    
    def _add_resources_of_type(self, resource_type: str, resources: List[ResourceInfo]):
        """Add resources of a specific type to graph"""
        self.logger.debug(f"Adding {len(resources)} resources of type {resource_type}")
        
        try:
            with self.driver.session() as session:
                for resource in resources:
                    self._create_resource_node(session, resource)
                    
        except Exception as e:
            self.logger.error(f"Failed to add resources of type {resource_type}: {e}")
    
    def _create_resource_node(self, session, resource: ResourceInfo):
        """Create a resource node with extracted type from AWS resource type"""
        try:
            # Extract node type from AWS resource type (AWS::EC2::PrefixList -> PrefixList)
            node_type = self._extract_node_type(resource.resource_type)
            
            # Flatten properties for Neo4j storage
            flattened_props = self._flatten_properties(resource.properties)
            
            # Build node properties
            node_props = {
                'aws_resource_type': resource.resource_type,
                'identifier': resource.identifier,
                'arn': resource.arn,
                'service': resource.service,
                'account_id': self._account_id,
                'updated_at': 'datetime()'
            }
            
            # Add region if not global service
            if not self._is_global_service(resource.service):
                node_props['region'] = resource.region
            
            # Add flattened properties
            node_props.update(flattened_props)
            
            # Determine unique identifier for MERGE operation
            # Use ARN if available, otherwise use identifier + account + region + resource_type
            if resource.arn and resource.arn.strip():
                unique_key = 'arn'
                unique_value = resource.arn
                query = f"""
                MERGE (r:{node_type} {{arn: $unique_value}})
                SET r += $props
                RETURN r
                """
            else:
                unique_key = 'composite_id'
                region_part = resource.region if not self._is_global_service(resource.service) else 'global'
                unique_value = f"{resource.identifier}:{self._account_id}:{region_part}:{resource.resource_type}"
                node_props['composite_id'] = unique_value
                query = f"""
                MERGE (r:{node_type} {{composite_id: $unique_value}})
                SET r += $props
                RETURN r
                """
            
            result = session.run(query, unique_value=unique_value, props=node_props)
            if result.single():
                self.stats['nodes_created'] += 1
                
                # Create relationship to account - use the unique identifier we just used
                if self._account_id:
                    self._create_account_relationship(session, unique_value, node_type, unique_key)
            
        except Exception as e:
            self.logger.error(f"Failed to create resource node {resource.identifier}: {e}")
    
    def _extract_node_type(self, resource_type: str) -> str:
        """Extract clean node type from AWS resource type"""
        # AWS::EC2::PrefixList -> PrefixList
        # AWS::S3::Bucket -> Bucket
        # AWS::IAM::Role -> Role
        
        if not resource_type.startswith('AWS::'):
            return 'UnknownResource'
        
        parts = resource_type.split('::')
        if len(parts) >= 3:
            return parts[2]  # Extract the actual resource type
        
        return 'UnknownResource'
    
    def _create_account_relationship(self, session, unique_value: str, node_type: str, unique_key: str = 'arn'):
        """Create OWNS relationship between account and resource"""
        try:
            query = f"""
            MATCH (a:Account {{id: $account_id}})
            MATCH (r:{node_type} {{{unique_key}: $unique_value}})
            MERGE (a)-[:OWNS]->(r)
            """
            
            session.run(query, account_id=self._account_id, unique_value=unique_value)
            self.stats['relationships_created'] += 1
            
        except Exception as e:
            self.logger.debug(f"Failed to create account relationship for {unique_value}: {e}")
    
    def _create_resource_relationships(self, resources: List[ResourceInfo]):
        """Create intelligent relationships between resources based on actual usage"""
        self.logger.info("🔗 Analyzing resource relationships based on usage patterns")
        
        # Build comprehensive resource mappings
        arn_to_resource = {}
        id_to_resources = {}
        name_to_resources = {}
        
        for resource in resources:
            if resource.has_error():
                continue
                
            # Map by ARN
            if resource.arn:
                arn_to_resource[resource.arn] = resource
            
            # Map by identifier/ID
            if resource.identifier:
                if resource.identifier not in id_to_resources:
                    id_to_resources[resource.identifier] = []
                id_to_resources[resource.identifier].append(resource)
            
            # Map by common name patterns
            name_keys = self._extract_name_keys(resource)
            for name_key in name_keys:
                if name_key not in name_to_resources:
                    name_to_resources[name_key] = []
                name_to_resources[name_key].append(resource)
        
        relationship_count = 0
        
        with self.driver.session() as session:
            for resource in resources:
                if resource.has_error():
                    continue
                
                # Find usage-based relationships
                relationships = self._analyze_resource_usage(
                    resource, arn_to_resource, id_to_resources, name_to_resources
                )
                
                for rel_type, target_resource in relationships:
                    try:
                        source_type = self._extract_node_type(resource.resource_type)
                        target_type = self._extract_node_type(target_resource.resource_type)
                        
                        self._create_usage_relationship(
                            session, resource.arn, target_resource.arn, 
                            source_type, target_type, rel_type
                        )
                        relationship_count += 1
                    except Exception as e:
                        self.logger.debug(f"Failed to create relationship {rel_type}: {e}")
        
        self.logger.info(f"✓ Created {relationship_count} usage-based relationships")
    
    def _extract_name_keys(self, resource: ResourceInfo) -> List[str]:
        """Extract various name patterns from resource for matching"""
        name_keys = []
        
        if not resource.properties:
            return name_keys
        
        # Common name patterns in AWS resources
        name_fields = [
            'Name', 'BucketName', 'VpcId', 'SubnetId', 'GroupId', 'GroupName',
            'InstanceId', 'VolumeId', 'SnapshotId', 'ImageId', 'KeyName',
            'RoleName', 'PolicyName', 'UserName', 'FunctionName', 'TableName',
            'ClusterName', 'DBName', 'DBInstanceIdentifier', 'TopicArn'
        ]
        
        def extract_names(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in name_fields and isinstance(value, str) and value:
                        name_keys.append(value)
                    elif isinstance(value, (dict, list)):
                        extract_names(value, f"{prefix}.{key}")
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        extract_names(item, prefix)
        
        extract_names(resource.properties)
        return list(set(name_keys))  # Remove duplicates
    
    def _analyze_resource_usage(self, resource: ResourceInfo, arn_to_resource: Dict, 
                               id_to_resources: Dict, name_to_resources: Dict) -> List[Tuple[str, ResourceInfo]]:
        """Analyze how this resource uses other resources"""
        relationships = []
        
        if not resource.properties:
            return relationships
        
        # Analyze different usage patterns
        relationships.extend(self._find_arn_references(resource, arn_to_resource))
        relationships.extend(self._find_id_references(resource, id_to_resources))
        relationships.extend(self._find_vpc_relationships(resource, id_to_resources))
        relationships.extend(self._find_security_group_relationships(resource, id_to_resources))
        relationships.extend(self._find_subnet_relationships(resource, id_to_resources))
        relationships.extend(self._find_role_relationships(resource, name_to_resources))
        relationships.extend(self._find_policy_relationships(resource, arn_to_resource))
        
        return relationships
    
    def _find_arn_references(self, resource: ResourceInfo, arn_to_resource: Dict) -> List[Tuple[str, ResourceInfo]]:
        """Find direct ARN references in resource properties"""
        relationships = []
        
        def search_arns(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    
                    if isinstance(value, str) and value.startswith('arn:aws:'):
                        if value in arn_to_resource:
                            target_resource = arn_to_resource[value]
                            rel_type = self._determine_usage_relationship(resource, target_resource, current_path, key)
                            relationships.append((rel_type, target_resource))
                    
                    elif isinstance(value, (dict, list)):
                        search_arns(value, current_path)
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    search_arns(item, f"{path}[{i}]" if path else f"[{i}]")
        
        search_arns(resource.properties)
        return relationships
    
    def _find_id_references(self, resource: ResourceInfo, id_to_resources: Dict) -> List[Tuple[str, ResourceInfo]]:
        """Find ID-based references (VPC ID, Subnet ID, etc.)"""
        relationships = []
        
        def search_ids(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value in id_to_resources:
                        for target_resource in id_to_resources[value]:
                            if target_resource.arn != resource.arn:  # Don't link to self
                                rel_type = self._determine_usage_relationship(resource, target_resource, path, key)
                                relationships.append((rel_type, target_resource))
                    elif isinstance(value, (dict, list)):
                        search_ids(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        search_ids(item, f"{path}[{i}]" if path else f"[{i}]")
        
        search_ids(resource.properties)
        return relationships
    
    def _find_vpc_relationships(self, resource: ResourceInfo, id_to_resources: Dict) -> List[Tuple[str, ResourceInfo]]:
        """Find VPC membership relationships"""
        relationships = []
        vpc_id = None
        
        # Look for VPC ID in properties
        if resource.properties:
            vpc_id = resource.properties.get('VpcId')
        
        if vpc_id and vpc_id in id_to_resources:
            for vpc_resource in id_to_resources[vpc_id]:
                if 'VPC' in vpc_resource.resource_type:
                    relationships.append(('DEPLOYED_IN', vpc_resource))
        
        return relationships
    
    def _find_security_group_relationships(self, resource: ResourceInfo, id_to_resources: Dict) -> List[Tuple[str, ResourceInfo]]:
        """Find security group usage relationships"""
        relationships = []
        
        if not resource.properties:
            return relationships
        
        # Look for security group references
        sg_fields = ['SecurityGroups', 'SecurityGroupIds', 'GroupId']
        
        def find_sgs(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in sg_fields:
                        if isinstance(value, list):
                            for sg_id in value:
                                if isinstance(sg_id, str) and sg_id in id_to_resources:
                                    for sg_resource in id_to_resources[sg_id]:
                                        if 'SecurityGroup' in sg_resource.resource_type:
                                            relationships.append(('PROTECTED_BY', sg_resource))
                        elif isinstance(value, str) and value in id_to_resources:
                            for sg_resource in id_to_resources[value]:
                                if 'SecurityGroup' in sg_resource.resource_type:
                                    relationships.append(('PROTECTED_BY', sg_resource))
                    elif isinstance(value, (dict, list)):
                        find_sgs(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        find_sgs(item)
        
        find_sgs(resource.properties)
        return relationships
    
    def _find_subnet_relationships(self, resource: ResourceInfo, id_to_resources: Dict) -> List[Tuple[str, ResourceInfo]]:
        """Find subnet deployment relationships"""
        relationships = []
        
        if not resource.properties:
            return relationships
        
        subnet_id = resource.properties.get('SubnetId')
        if subnet_id and subnet_id in id_to_resources:
            for subnet_resource in id_to_resources[subnet_id]:
                if 'Subnet' in subnet_resource.resource_type:
                    relationships.append(('DEPLOYED_IN', subnet_resource))
        
        return relationships
    
    def _find_role_relationships(self, resource: ResourceInfo, name_to_resources: Dict) -> List[Tuple[str, ResourceInfo]]:
        """Find IAM role usage relationships"""
        relationships = []
        
        if not resource.properties:
            return relationships
        
        # Look for IAM role references
        role_fields = ['RoleName', 'RoleArn', 'IamInstanceProfile']
        
        def find_roles(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in role_fields:
                        if isinstance(value, str):
                            # Extract role name from ARN if needed
                            role_name = value.split('/')[-1] if '/' in value else value
                            if role_name in name_to_resources:
                                for role_resource in name_to_resources[role_name]:
                                    if 'Role' in role_resource.resource_type:
                                        relationships.append(('ASSUMES', role_resource))
                    elif isinstance(value, (dict, list)):
                        find_roles(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        find_roles(item)
        
        find_roles(resource.properties)
        return relationships
    
    def _find_policy_relationships(self, resource: ResourceInfo, arn_to_resource: Dict) -> List[Tuple[str, ResourceInfo]]:
        """Find policy attachment relationships"""
        relationships = []
        
        if not resource.properties:
            return relationships
        
        # Look for policy ARNs
        def find_policies(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if 'policy' in key.lower() or 'Policy' in key:
                        if isinstance(value, str) and value.startswith('arn:aws:iam'):
                            if value in arn_to_resource:
                                policy_resource = arn_to_resource[value]
                                relationships.append(('HAS_POLICY', policy_resource))
                        elif isinstance(value, list):
                            for policy_arn in value:
                                if isinstance(policy_arn, str) and policy_arn.startswith('arn:aws:iam'):
                                    if policy_arn in arn_to_resource:
                                        policy_resource = arn_to_resource[policy_arn]
                                        relationships.append(('HAS_POLICY', policy_resource))
                    elif isinstance(value, (dict, list)):
                        find_policies(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        find_policies(item)
        
        find_policies(resource.properties)
        return relationships
    
    def _determine_usage_relationship(self, source: ResourceInfo, target: ResourceInfo, path: str, key: str) -> str:
        """Determine the relationship type based on how source uses target"""
        key_lower = key.lower()
        path_lower = path.lower()
        source_type = source.resource_type
        target_type = target.resource_type
        
        # Logging relationships
        if 'log' in key_lower or 'logging' in path_lower:
            return 'LOGS_TO'
        
        # Network relationships
        if 'vpc' in key_lower and 'VPC' in target_type:
            return 'DEPLOYED_IN'
        if 'subnet' in key_lower and 'Subnet' in target_type:
            return 'DEPLOYED_IN'
        if 'securitygroup' in key_lower or 'groupid' in key_lower:
            return 'PROTECTED_BY'
        
        # IAM relationships
        if 'role' in key_lower and 'Role' in target_type:
            return 'ASSUMES'
        if 'policy' in key_lower and 'Policy' in target_type:
            return 'HAS_POLICY'
        
        # Storage relationships
        if 'volume' in key_lower and 'Volume' in target_type:
            return 'USES_VOLUME'
        if 'snapshot' in key_lower and 'Snapshot' in target_type:
            return 'CREATED_FROM'
        
        # Network routing
        if 'route' in key_lower or 'gateway' in key_lower:
            return 'ROUTES_THROUGH'
        
        # Load balancer relationships
        if 'loadbalancer' in key_lower or 'targetgroup' in key_lower:
            return 'LOAD_BALANCED_BY'
        
        # Database relationships
        if 'db' in key_lower and any(db in target_type for db in ['DB', 'Database', 'RDS']):
            return 'CONNECTS_TO'
        
        # Default fallback
        return 'USES'
    
    def _create_usage_relationship(self, session, source_arn: str, target_arn: str, 
                                  source_type: str, target_type: str, rel_type: str):
        """Create a usage-based relationship between two resource nodes"""
        query = f"""
        MATCH (source:{source_type} {{arn: $source_arn}})
        MATCH (target:{target_type} {{arn: $target_arn}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r.created_at = datetime()
        RETURN r
        """
        
        result = session.run(query, source_arn=source_arn, target_arn=target_arn)
        if result.single():
            self.stats['relationships_created'] += 1
            self.logger.debug(f"Created {rel_type}: {source_type} -> {target_type}")
    
    def _flatten_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested properties for Neo4j storage"""
        flattened = {}
        
        def flatten_dict(obj, prefix=""):
            for key, value in obj.items():
                new_key = f"{prefix}_{key}" if prefix else key
                
                if isinstance(value, dict):
                    flatten_dict(value, new_key)
                elif isinstance(value, list):
                    # Convert lists to JSON strings
                    flattened[new_key] = json.dumps(value) if value else "[]"
                elif isinstance(value, (str, int, float, bool)):
                    flattened[new_key] = value
                elif value is None:
                    flattened[new_key] = ""
                else:
                    # Convert other types to strings
                    flattened[new_key] = str(value)
        
        if isinstance(properties, dict):
            flatten_dict(properties)
        
        return flattened
    
    def _is_global_service(self, service: str) -> bool:
        """Check if service is global (no region property needed)"""
        global_services = {'iam', 'organizations', 'route53', 'waf', 'wafv2', 'artifacts', 'controltower'}
        return service.lower() in global_services
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get Neo4j operation statistics"""
        return self.stats.copy()
    
    def log_statistics(self):
        """Log Neo4j operation statistics"""
        self.logger.info("📊 Neo4j Operation Statistics:")
        self.logger.info(f"   Nodes Created: {self.stats['nodes_created']}")
        self.logger.info(f"   Relationships Created: {self.stats['relationships_created']}")
        self.logger.info(f"   Cross-Account Connections: {self.stats['cross_account_connections']}")
        
        if self.stats['nodes_updated'] > 0:
            self.logger.info(f"   Nodes Updated: {self.stats['nodes_updated']}")
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a custom Cypher query"""
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            self.logger.error(f"Failed to execute query: {e}")
            raise
    
    def get_node_count(self) -> int:
        """Get total number of nodes in the graph"""
        try:
            result = self.execute_query("MATCH (n) RETURN count(n) as count")
            return result[0]['count'] if result else 0
        except Exception:
            return 0
    
    def get_relationship_count(self) -> int:
        """Get total number of relationships in the graph"""
        try:
            result = self.execute_query("MATCH ()-[r]->() RETURN count(r) as count")
            return result[0]['count'] if result else 0
        except Exception:
            return 0
    
    def get_service_client(self, service_name: str):
        """Get AWS service client"""
        try:
            import boto3
            session = boto3.Session()
            return session.client(service_name, region_name=self.config.region)
        except Exception as e:
            self.logger.error(f"Failed to create {service_name} client: {e}")
            return None
    
    def _get_account_id(self) -> str:
        """Get AWS account ID"""
        return self._account_id or "unknown"
    
    def _create_route_rules(self, session, resources: Dict[str, Any]):
        """Create individual RouteRule nodes from RouteTable resources"""
        try:
            ec2_client = self.get_service_client('ec2')
            if not ec2_client:
                return
                
            route_tables = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::EC2::RouteTable'
            ]
            if not route_tables:
                self.logger.debug("No route tables found for route rule extraction")
                return
                
            self.logger.info(f"Processing {len(route_tables)} route tables for route rule extraction")
            
            for route_table_arn, route_table_info in route_tables:
                route_table_id = route_table_info.get('identifier', '')
                if not route_table_id:
                    continue
                    
                try:
                    response = ec2_client.describe_route_tables(RouteTableIds=[route_table_id])
                    for route_table in response.get('RouteTables', []):
                        routes = route_table.get('Routes', [])
                        for i, route in enumerate(routes):
                            route_id = f"{route_table_id}_route_{i}"
                            route_arn = f"arn:aws:ec2:{self.config.region}:{self._get_account_id()}:route/{route_id}"
                            
                            route_properties = {
                                'route_id': route_id,
                                'route_table_id': route_table_id,
                                'destination_cidr_block': route.get('DestinationCidrBlock', ''),
                                'destination_ipv6_cidr_block': route.get('DestinationIpv6CidrBlock', ''),
                                'destination_prefix_list_id': route.get('DestinationPrefixListId', ''),
                                'gateway_id': route.get('GatewayId', ''),
                                'instance_id': route.get('InstanceId', ''),
                                'instance_owner_id': route.get('InstanceOwnerId', ''),
                                'network_interface_id': route.get('NetworkInterfaceId', ''),
                                'transit_gateway_id': route.get('TransitGatewayId', ''),
                                'vpc_peering_connection_id': route.get('VpcPeeringConnectionId', ''),
                                'nat_gateway_id': route.get('NatGatewayId', ''),
                                'carrier_gateway_id': route.get('CarrierGatewayId', ''),
                                'local_gateway_id': route.get('LocalGatewayId', ''),
                                'core_network_arn': route.get('CoreNetworkArn', ''),
                                'state': route.get('State', ''),
                                'origin': route.get('Origin', ''),
                                'arn': route_arn,
                                'resource_type': 'AWS::EC2::RouteRule',
                                'service': 'ec2',
                                'region': self.config.region,
                                'account_id': self._get_account_id()
                            }
                            
                            route_properties = {k: v for k, v in route_properties.items() if v}
                            
                            create_route_query = """
                            MERGE (rr:RouteRule {arn: $arn})
                            SET rr += $properties
                            """
                            session.run(create_route_query, arn=route_arn, properties=route_properties)
                            
                            account_route_query = """
                            MATCH (account:Account {id: $account_id})
                            MATCH (rr:RouteRule {arn: $route_arn})
                            MERGE (account)-[:OWNS]->(rr)
                            """
                            session.run(account_route_query, 
                                       account_id=self._get_account_id(),
                                       route_arn=route_arn)
                            
                            relationship_query = """
                            MATCH (rt:RouteTable {arn: $route_table_arn})
                            MATCH (rr:RouteRule {arn: $route_arn})
                            MERGE (rt)-[:HAS_ROUTE]->(rr)
                            """
                            session.run(relationship_query, 
                                       route_table_arn=route_table_arn, 
                                       route_arn=route_arn)
                            
                            self._create_route_target_relationships(session, route_properties, resources)
                            self.stats['nodes_created'] += 1
                            self.stats['relationships_created'] += 2
                            
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed routes for route table {route_table_id}: {e}")
                    continue
                    
            self.logger.info("Route rule creation completed")
        except Exception as e:
            self.logger.error(f"Failed to create route rules: {e}")
    
    def _create_route_target_relationships(self, session, route_properties: Dict[str, Any], resources: Dict[str, Any]):
        """Create relationships from route rules to their target resources"""
        route_arn = route_properties.get('arn')
        
        target_mappings = {
            'gateway_id': 'AWS::EC2::InternetGateway',
            'nat_gateway_id': 'AWS::EC2::NatGateway', 
            'instance_id': 'AWS::EC2::Instance',
            'network_interface_id': 'AWS::EC2::NetworkInterface',
            'transit_gateway_id': 'AWS::EC2::TransitGateway',
            'vpc_peering_connection_id': 'AWS::EC2::VPCPeeringConnection'
        }
        
        for prop_name, resource_type in target_mappings.items():
            target_id = route_properties.get(prop_name)
            if target_id and target_id != 'local':
                target_arn = None
                for arn, info in resources.items():
                    if (info.get('resource_type') == resource_type and 
                        info.get('identifier') == target_id):
                        target_arn = arn
                        break
                
                if target_arn:
                    safe_resource_type = self._extract_node_type(resource_type)
                    relationship_query = f"""
                    MATCH (rr:RouteRule {{arn: $route_arn}})
                    MATCH (target:{safe_resource_type} {{arn: $target_arn}})
                    MERGE (rr)-[:ROUTES_TO]->(target)
                    """
                    session.run(relationship_query, route_arn=route_arn, target_arn=target_arn)
                    self.stats['relationships_created'] += 1
    
    def _create_enhanced_service_components(self, session, resources: Dict[str, Any]):
        """Create detailed sub-components for RDS, ElastiCache, MQ, and API Gateway"""
        try:
            self.logger.info("Creating enhanced service components...")
            self._create_rds_components(session, resources)
            self._create_elasticache_components(session, resources)
            self._create_mq_components(session, resources)
            self._create_apigateway_components(session, resources)
            self._create_transit_gateway_components(session, resources)
            self._create_vpc_peering_components(session, resources)
        except Exception as e:
            self.logger.error(f"Failed to create enhanced service components: {e}")
    
    def _create_rds_components(self, session, resources: Dict[str, Any]):
        """Create RDS sub-components: instances, clusters, snapshots, parameter groups"""
        try:
            rds_client = self.get_service_client('rds')
            if not rds_client:
                return
                
            rds_clusters = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::RDS::DBCluster'
            ]
            
            # Process RDS Clusters
            for cluster_arn, cluster_info in rds_clusters:
                cluster_id = cluster_info.get('identifier', '')
                if not cluster_id:
                    continue
                    
                try:
                    response = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)
                    for cluster in response.get('DBClusters', []):
                        # Create cluster members
                        for member in cluster.get('DBClusterMembers', []):
                            instance_id = member.get('DBInstanceIdentifier')
                            if instance_id:
                                instance_arn = f"arn:aws:rds:{self.config.region}:{self._get_account_id()}:db:{instance_id}"
                                member_query = """
                                MERGE (instance:RDSClusterMember {
                                    arn: $instance_arn,
                                    instance_id: $instance_id,
                                    is_writer: $is_writer,
                                    promotion_tier: $promotion_tier,
                                    resource_type: 'AWS::RDS::DBClusterMember',
                                    service: 'rds',
                                    region: $region,
                                    account_id: $account_id
                                })
                                WITH instance
                                MATCH (account:Account {id: $account_id})
                                MERGE (account)-[:OWNS]->(instance)
                                WITH instance
                                MATCH (cluster:DBCluster {arn: $cluster_arn})
                                MERGE (cluster)-[:HAS_MEMBER]->(instance)
                                """
                                session.run(member_query,
                                           cluster_arn=cluster_arn,
                                           instance_arn=instance_arn,
                                           instance_id=instance_id,
                                           is_writer=member.get('IsClusterWriter', False),
                                           promotion_tier=member.get('PromotionTier', 0),
                                           region=self.config.region,
                                           account_id=self._get_account_id())
                                self.stats['nodes_created'] += 1
                                self.stats['relationships_created'] += 2
                        
                        # Create parameter group relationships
                        param_group = cluster.get('DBClusterParameterGroup')
                        if param_group:
                            param_group_arn = f"arn:aws:rds:{self.config.region}:{self._get_account_id()}:cluster-pg:{param_group}"
                            param_query = """
                            MERGE (pg:RDSParameterGroup {
                                arn: $param_group_arn,
                                name: $param_group,
                                resource_type: 'AWS::RDS::DBClusterParameterGroup',
                                service: 'rds',
                                region: $region,
                                account_id: $account_id
                            })
                            WITH pg
                            MATCH (account:Account {id: $account_id})
                            MERGE (account)-[:OWNS]->(pg)
                            WITH pg
                            MATCH (cluster:DBCluster {arn: $cluster_arn})
                            MERGE (cluster)-[:USES_PARAMETER_GROUP]->(pg)
                            """
                            session.run(param_query,
                                       cluster_arn=cluster_arn,
                                       param_group_arn=param_group_arn,
                                       param_group=param_group,
                                       region=self.config.region,
                                       account_id=self._get_account_id())
                            self.stats['nodes_created'] += 1
                            self.stats['relationships_created'] += 2
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for RDS cluster {cluster_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to create RDS components: {e}")
    
    def _create_elasticache_components(self, session, resources: Dict[str, Any]):
        """Create ElastiCache sub-components: clusters, nodes, parameter groups"""
        try:
            elasticache_client = self.get_service_client('elasticache')
            if not elasticache_client:
                return
                
            cache_clusters = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::ElastiCache::CacheCluster'
            ]
            
            # Process Cache Clusters
            for cluster_arn, cluster_info in cache_clusters:
                cluster_id = cluster_info.get('identifier', '')
                if not cluster_id:
                    continue
                    
                try:
                    response = elasticache_client.describe_cache_clusters(
                        CacheClusterId=cluster_id,
                        ShowCacheNodeInfo=True
                    )
                    
                    for cluster in response.get('CacheClusters', []):
                        # Create cache nodes
                        for node in cluster.get('CacheNodes', []):
                            node_id = node.get('CacheNodeId')
                            if node_id:
                                node_arn = f"arn:aws:elasticache:{self.config.region}:{self._get_account_id()}:cachenode:{cluster_id}:{node_id}"
                                node_properties = {
                                    'arn': node_arn,
                                    'node_id': node_id,
                                    'cluster_id': cluster_id,
                                    'node_status': node.get('CacheNodeStatus', ''),
                                    'creation_time': str(node.get('CacheNodeCreateTime', '')),
                                    'endpoint_address': node.get('Endpoint', {}).get('Address', ''),
                                    'endpoint_port': node.get('Endpoint', {}).get('Port', 0),
                                    'parameter_group_status': node.get('ParameterGroupStatus', ''),
                                    'resource_type': 'AWS::ElastiCache::CacheNode',
                                    'service': 'elasticache',
                                    'region': self.config.region
                                }
                                node_properties = {k: v for k, v in node_properties.items() if v}
                                
                                node_query = """
                                MERGE (node:ElastiCacheNode {arn: $arn})
                                SET node += $properties
                                """
                                session.run(node_query, arn=node_arn, properties=node_properties)
                                
                                cluster_node_query = """
                                MATCH (cluster:CacheCluster {arn: $cluster_arn})
                                MATCH (node:ElastiCacheNode {arn: $node_arn})
                                MERGE (cluster)-[:HAS_NODE]->(node)
                                """
                                session.run(cluster_node_query, cluster_arn=cluster_arn, node_arn=node_arn)
                                self.stats['nodes_created'] += 1
                                self.stats['relationships_created'] += 1
                                
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for ElastiCache cluster {cluster_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to create ElastiCache components: {e}")
    
    def _create_mq_components(self, session, resources: Dict[str, Any]):
        """Create Amazon MQ sub-components: brokers, configurations, users"""
        try:
            mq_client = self.get_service_client('mq')
            if not mq_client:
                return
                
            mq_brokers = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::MQ::Broker'
            ]
            
            for broker_arn, broker_info in mq_brokers:
                broker_id = broker_info.get('identifier', '')
                if not broker_id:
                    continue
                    
                try:
                    response = mq_client.describe_broker(BrokerId=broker_id)
                    
                    # Create broker instances
                    for instance in response.get('BrokerInstances', []):
                        instance_id = instance.get('ConsoleURL', '').split('/')[-1] if instance.get('ConsoleURL') else f"{broker_id}_instance"
                        instance_arn = f"arn:aws:mq:{self.config.region}:{self._get_account_id()}:broker-instance:{broker_id}:{instance_id}"
                        
                        instance_properties = {
                            'arn': instance_arn,
                            'broker_id': broker_id,
                            'console_url': instance.get('ConsoleURL', ''),
                            'endpoints': str(instance.get('Endpoints', [])),
                            'ip_address': instance.get('IpAddress', ''),
                            'resource_type': 'AWS::MQ::BrokerInstance',
                            'service': 'mq',
                            'region': self.config.region
                        }
                        instance_properties = {k: v for k, v in instance_properties.items() if v}
                        
                        instance_query = """
                        MERGE (instance:MQBrokerInstance {arn: $arn})
                        SET instance += $properties
                        """
                        session.run(instance_query, arn=instance_arn, properties=instance_properties)
                        
                        broker_instance_query = """
                        MATCH (broker:Broker {arn: $broker_arn})
                        MATCH (instance:MQBrokerInstance {arn: $instance_arn})
                        MERGE (broker)-[:HAS_INSTANCE]->(instance)
                        """
                        session.run(broker_instance_query, broker_arn=broker_arn, instance_arn=instance_arn)
                        self.stats['nodes_created'] += 1
                        self.stats['relationships_created'] += 1
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for MQ broker {broker_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to create MQ components: {e}")
    
    def _create_apigateway_components(self, session, resources: Dict[str, Any]):
        """Create API Gateway sub-components: stages, resources, methods"""
        try:
            apigw_client = self.get_service_client('apigateway')
            apigwv2_client = self.get_service_client('apigatewayv2')
            if not apigw_client or not apigwv2_client:
                return
                
            rest_apis = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::ApiGateway::RestApi'
            ]
            
            # Process REST APIs (v1)
            for api_arn, api_info in rest_apis:
                api_id = api_info.get('identifier', '')
                if not api_id:
                    continue
                    
                try:
                    # Create stages
                    stages_response = apigw_client.get_stages(restApiId=api_id)
                    for stage in stages_response.get('item', []):
                        stage_name = stage.get('stageName')
                        if stage_name:
                            stage_arn = f"arn:aws:apigateway:{self.config.region}::/restapis/{api_id}/stages/{stage_name}"
                            stage_properties = {
                                'arn': stage_arn,
                                'stage_name': stage_name,
                                'api_id': api_id,
                                'deployment_id': stage.get('deploymentId', ''),
                                'description': stage.get('description', ''),
                                'cache_cluster_enabled': stage.get('cacheClusterEnabled', False),
                                'created_date': str(stage.get('createdDate', '')),
                                'resource_type': 'AWS::ApiGateway::Stage',
                                'service': 'apigateway',
                                'region': self.config.region
                            }
                            stage_properties = {k: v for k, v in stage_properties.items() if v}
                            
                            stage_query = """
                            MERGE (stage:ApiGatewayStage {arn: $arn})
                            SET stage += $properties
                            """
                            session.run(stage_query, arn=stage_arn, properties=stage_properties)
                            
                            api_stage_query = """
                            MATCH (api:RestApi {arn: $api_arn})
                            MATCH (stage:ApiGatewayStage {arn: $stage_arn})
                            MERGE (api)-[:HAS_STAGE]->(stage)
                            """
                            session.run(api_stage_query, api_arn=api_arn, stage_arn=stage_arn)
                            self.stats['nodes_created'] += 1
                            self.stats['relationships_created'] += 1
                            
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for API Gateway REST API {api_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to create API Gateway components: {e}")
    
    def _create_transit_gateway_components(self, session, resources: Dict[str, Any]):
        """Create Transit Gateway sub-components and detect cross-account connections"""
        try:
            ec2_client = self.get_service_client('ec2')
            if not ec2_client:
                return
                
            transit_gateways = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::EC2::TransitGateway'
            ]
            
            for tgw_arn, tgw_info in transit_gateways:
                tgw_id = tgw_info.get('identifier', '')
                if not tgw_id:
                    continue
                    
                try:
                    # Check for cross-account VPC attachments
                    vpc_attachments_response = ec2_client.describe_transit_gateway_vpc_attachments(
                        Filters=[{'Name': 'transit-gateway-id', 'Values': [tgw_id]}]
                    )
                    
                    for vpc_attachment in vpc_attachments_response.get('TransitGatewayVpcAttachments', []):
                        vpc_owner_id = vpc_attachment.get('VpcOwnerId', '')
                        current_account_id = self._get_account_id()
                        
                        if vpc_owner_id and vpc_owner_id != current_account_id:
                            self.logger.info(f"Found cross-account Transit Gateway connection: {current_account_id} -> {vpc_owner_id}")
                            
                            cross_account_query = """
                            MERGE (source_account:Account {id: $source_account_id})
                            MERGE (target_account:Account {id: $target_account_id})
                            MERGE (source_account)-[:CONNECTED_VIA_TRANSIT_GATEWAY {
                                transit_gateway_id: $tgw_id,
                                attachment_id: $attachment_id,
                                connection_type: 'Transit Gateway VPC Attachment',
                                vpc_id: $vpc_id,
                                created_at: datetime()
                            }]->(target_account)
                            """
                            session.run(cross_account_query,
                                       source_account_id=current_account_id,
                                       target_account_id=vpc_owner_id,
                                       tgw_id=tgw_id,
                                       attachment_id=vpc_attachment.get('TransitGatewayAttachmentId', ''),
                                       vpc_id=vpc_attachment.get('VpcId', ''))
                            self.stats['cross_account_connections'] += 1
                            self.stats['relationships_created'] += 1
                            
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for Transit Gateway {tgw_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to create Transit Gateway components: {e}")
    
    def _create_vpc_peering_components(self, session, resources: Dict[str, Any]):
        """Create VPC Peering connection components and detect cross-account connections"""
        try:
            ec2_client = self.get_service_client('ec2')
            if not ec2_client:
                return
                
            peering_connections = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::EC2::VPCPeeringConnection'
            ]
            
            for pcx_arn, pcx_info in peering_connections:
                pcx_id = pcx_info.get('identifier', '')
                if not pcx_id:
                    continue
                    
                try:
                    response = ec2_client.describe_vpc_peering_connections(VpcPeeringConnectionIds=[pcx_id])
                    
                    for pcx in response.get('VpcPeeringConnections', []):
                        accepter_vpc_info = pcx.get('AccepterVpcInfo', {})
                        requester_vpc_info = pcx.get('RequesterVpcInfo', {})
                        
                        accepter_owner_id = accepter_vpc_info.get('OwnerId', '')
                        requester_owner_id = requester_vpc_info.get('OwnerId', '')
                        current_account_id = self._get_account_id()
                        
                        # Check for cross-account connections
                        cross_account_targets = []
                        if accepter_owner_id and accepter_owner_id != current_account_id:
                            cross_account_targets.append(accepter_owner_id)
                        if requester_owner_id and requester_owner_id != current_account_id:
                            cross_account_targets.append(requester_owner_id)
                        
                        for target_account_id in cross_account_targets:
                            self.logger.info(f"Found cross-account VPC Peering connection: {current_account_id} -> {target_account_id}")
                            
                            cross_account_query = """
                            MERGE (source_account:Account {id: $source_account_id})
                            MERGE (target_account:Account {id: $target_account_id})
                            MERGE (source_account)-[:CONNECTED_VIA_VPC_PEERING {
                                peering_connection_id: $pcx_id,
                                connection_type: 'VPC Peering Connection',
                                accepter_vpc_id: $accepter_vpc_id,
                                requester_vpc_id: $requester_vpc_id,
                                status: $status,
                                created_at: datetime()
                            }]->(target_account)
                            """
                            session.run(cross_account_query,
                                       source_account_id=current_account_id,
                                       target_account_id=target_account_id,
                                       pcx_id=pcx_id,
                                       accepter_vpc_id=accepter_vpc_info.get('VpcId', ''),
                                       requester_vpc_id=requester_vpc_info.get('VpcId', ''),
                                       status=pcx.get('Status', {}).get('Code', ''))
                            self.stats['cross_account_connections'] += 1
                            self.stats['relationships_created'] += 1
                            
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for VPC Peering connection {pcx_id}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to create VPC Peering components: {e}")
    
    def _log_cross_account_connections(self, session):
        """Log summary of all cross-account connections discovered"""
        try:
            # Query Transit Gateway connections
            tgw_query = """
            MATCH (source:Account)-[r:CONNECTED_VIA_TRANSIT_GATEWAY]->(target:Account)
            RETURN source.id as source_account, target.id as target_account, 
                   r.transit_gateway_id as tgw_id, r.connection_type as type
            """
            tgw_results = session.run(tgw_query)
            
            # Query VPC Peering connections
            pcx_query = """
            MATCH (source:Account)-[r:CONNECTED_VIA_VPC_PEERING]->(target:Account)
            RETURN source.id as source_account, target.id as target_account,
                   r.peering_connection_id as pcx_id, r.connection_type as type, r.status as status
            """
            pcx_results = session.run(pcx_query)
            
            tgw_connections = list(tgw_results)
            pcx_connections = list(pcx_results)
            
            if tgw_connections or pcx_connections:
                self.logger.info("=" * 60)
                self.logger.info("CROSS-ACCOUNT CONNECTIVITY SUMMARY")
                self.logger.info("=" * 60)
                
                if tgw_connections:
                    self.logger.info(f"Transit Gateway Connections ({len(tgw_connections)}):")
                    for conn in tgw_connections:
                        self.logger.info(f"  📡 {conn['source_account']} -> {conn['target_account']} via TGW {conn['tgw_id']}")
                
                if pcx_connections:
                    self.logger.info(f"VPC Peering Connections ({len(pcx_connections)}):")
                    for conn in pcx_connections:
                        status_emoji = "✅" if conn['status'] == 'active' else "⚠️"
                        self.logger.info(f"  {status_emoji} {conn['source_account']} -> {conn['target_account']} via PCX {conn['pcx_id']} ({conn['status']})")
                
                # Calculate summary statistics
                total_connections = len(tgw_connections) + len(pcx_connections)
                unique_accounts = set()
                for conn in tgw_connections + pcx_connections:
                    unique_accounts.add(conn['source_account'])
                    unique_accounts.add(conn['target_account'])
                
                self.logger.info("=" * 60)
                self.logger.info(f"Total cross-account connections: {total_connections}")
                self.logger.info(f"Connected accounts: {len(unique_accounts)}")
                self.logger.info("=" * 60)
            else:
                self.logger.info("No cross-account connections detected via Transit Gateway or VPC Peering")
                
        except Exception as e:
            self.logger.error(f"Failed to log cross-account connections: {e}")