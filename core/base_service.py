"""
Base service class for AWS service discovery implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .resource_info import ResourceInfo
from .config import DiscoveryConfig


class BaseAWSService(ABC):
    """Abstract base class for AWS service discovery implementations"""
    
    def __init__(self, config: DiscoveryConfig, session: boto3.Session):
        """Initialize base service with configuration and AWS session"""
        self.config = config
        self.session = session
        self.region = config.region
        self.logger = logging.getLogger(f'aws_discovery.{self.get_service_name()}')
        
        # Service-specific client cache
        self._clients = {}
        
        # Service statistics
        self.stats = {
            'resource_types_discovered': 0,
            'resources_found': 0,
            'resources_with_errors': 0,
            'api_calls_made': 0,
            'skipped_resource_types': 0
        }
    
    @abstractmethod
    def get_service_name(self) -> str:
        """Return the AWS service name (e.g., 'ec2', 's3', 'rds')"""
        pass
    
    @abstractmethod
    def get_supported_resource_types(self) -> List[str]:
        """Return list of AWS resource types this service can discover"""
        pass
    
    @abstractmethod
    def discover_resources(self) -> List[ResourceInfo]:
        """Discover all resources for this service"""
        pass
    
    def get_client(self, service_name: str = None):
        """Get cached AWS client for service"""
        if service_name is None:
            service_name = self.get_service_name()
        
        if service_name not in self._clients:
            try:
                self._clients[service_name] = self.session.client(
                    service_name, 
                    region_name=self.region
                )
            except Exception as e:
                self.logger.error(f"Failed to create {service_name} client: {e}")
                raise
        
        return self._clients[service_name]
    
    def should_skip_resource_type(self, resource_type: str, error_msg: str = "") -> bool:
        """Determine if a resource type should be skipped based on known patterns"""
        # Check service-specific skip patterns
        skip_patterns = self.get_skip_patterns()
        
        for category, resource_types in skip_patterns.items():
            if resource_type in resource_types:
                self.logger.info(f"⚠ Skipping {resource_type}: Known {category} issue")
                self.stats['skipped_resource_types'] += 1
                return True
        
        # Check error message patterns
        error_lower = error_msg.lower()
        
        skip_error_patterns = [
            # Rate limiting and throttling
            'throttlingexception',
            'rate exceeded',
            'too many requests',
            
            # Missing required parameters (common Cloud Control API issues)
            'required key',
            'required property',
            'missing or invalid resourcemodel property',
            'property cannot be empty',
            'autoscalinggroupname is required',
            'certificatearn cannot be empty',
            'transitgatewaymulticastdomainid',
            'domainidentifier',
            'projectidentifier',
            'environmentidentifier',
            'identitypoolid',
            'identityprovidername',
            
            # Service not available or not supported
            'does not support list action',
            'unsupportedactionexception',
            'typenotfoundexception',
            'cannot be found',
            'operation is not supported',
            'feature is not available',
            
            # Access and subscription issues
            'subscription does not exist',
            'not registered as a publisher',
            'access grants instance does not exist',
            'cost category',
            'linked account doesn\'t have access',
            'controltower could not complete',
            'awscontroltoweradmin',
            
            # Service-specific limitations
            'failed to list cost categories',
            'error occurred during operation',
            'handler returned status failed',
            'generalserviceexception'
        ]
        
        for pattern in skip_error_patterns:
            if pattern in error_lower:
                self.logger.info(f"⚠ Skipping {resource_type}: {pattern}")
                self.stats['skipped_resource_types'] += 1
                return True
        
        return False
    
    def get_skip_patterns(self) -> Dict[str, List[str]]:
        """Get service-specific resource types to skip"""
        # Default patterns - can be overridden by services
        return {
            'missing_required_key': [],
            'unsupported_action': [],
            'type_not_found': [],
            'subscription_required': []
        }
    
    def discover_resource_type(self, resource_type: str) -> List[ResourceInfo]:
        """Discover resources of a specific type using Cloud Control API"""
        try:
            if self.should_skip_resource_type(resource_type):
                return []
            
            resources = []
            cloudcontrol_client = self.get_client('cloudcontrol')
            
            paginator = cloudcontrol_client.get_paginator('list_resources')
            page_iterator = paginator.paginate(TypeName=resource_type)
            
            for page in page_iterator:
                if 'ResourceDescriptions' in page:
                    for resource_desc in page['ResourceDescriptions']:
                        resource_info = self._parse_resource_description(
                            resource_type, resource_desc
                        )
                        if resource_info:
                            resources.append(resource_info)
            
            self.stats['api_calls_made'] += 1
            self.stats['resource_types_discovered'] += 1
            self.stats['resources_found'] += len(resources)
            
            if resources:
                self.logger.info(f"✓ {resource_type}: Found {len(resources)} resources")
            else:
                self.logger.debug(f"○ {resource_type}: No resources found")
            
            return resources
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = str(e)
            
            if self.should_skip_resource_type(resource_type, error_msg):
                return []
            
            self.logger.warning(f"✗ {resource_type}: {error_code} - {error_msg}")
            
            # Return resource with error information
            error_resource = ResourceInfo(
                resource_type=resource_type,
                identifier="ERROR",
                error=f"{error_code}: {error_msg}"
            )
            self.stats['resources_with_errors'] += 1
            return [error_resource]
        
        except Exception as e:
            self.logger.error(f"✗ {resource_type}: Unexpected error - {str(e)}")
            error_resource = ResourceInfo(
                resource_type=resource_type,
                identifier="ERROR",
                error=str(e)
            )
            self.stats['resources_with_errors'] += 1
            return [error_resource]
    
    def _parse_resource_description(self, resource_type: str, resource_desc: Dict[str, Any]) -> Optional[ResourceInfo]:
        """Parse resource description from Cloud Control API response"""
        try:
            identifier = resource_desc.get('Identifier', '')
            properties = resource_desc.get('Properties', {})
            
            # Parse properties if it's a JSON string
            if isinstance(properties, str):
                import json
                try:
                    properties = json.loads(properties)
                except json.JSONDecodeError:
                    self.logger.warning(f"Failed to parse properties JSON for {resource_type}:{identifier}")
                    properties = {}
            
            # Extract ARN from properties
            arn = self._extract_arn(properties)
            
            return ResourceInfo(
                resource_type=resource_type,
                identifier=identifier,
                arn=arn,
                properties=properties,
                region=self.region
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse resource description for {resource_type}: {e}")
            return None
    
    def _extract_arn(self, properties: Dict[str, Any]) -> str:
        """Extract ARN from resource properties"""
        # Common ARN field names
        arn_fields = ['Arn', 'ARN', 'arn', 'ResourceArn', 'resource_arn']
        
        for field in arn_fields:
            if field in properties and properties[field]:
                return str(properties[field])
        
        return ""
    
    def is_global_service(self) -> bool:
        """Check if this service is global (not region-specific)"""
        global_services = {'iam', 'organizations', 'route53', 'waf', 'wafv2', 'artifacts', 'controltower'}
        return self.get_service_name().lower() in global_services
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service discovery statistics"""
        return {
            'service': self.get_service_name(),
            'region': self.region,
            'stats': self.stats.copy(),
            'supported_resource_types': len(self.get_supported_resource_types())
        }
    
    def log_statistics(self):
        """Log service discovery statistics"""
        stats = self.stats
        service_name = self.get_service_name().upper()
        
        self.logger.info(f"📊 {service_name} Discovery Statistics:")
        self.logger.info(f"   Resource Types: {stats['resource_types_discovered']}")
        self.logger.info(f"   Resources Found: {stats['resources_found']}")
        self.logger.info(f"   API Calls: {stats['api_calls_made']}")
        
        if stats['resources_with_errors'] > 0:
            self.logger.warning(f"   Resources with Errors: {stats['resources_with_errors']}")
        
        if stats['skipped_resource_types'] > 0:
            self.logger.info(f"   Skipped Resource Types: {stats['skipped_resource_types']}")