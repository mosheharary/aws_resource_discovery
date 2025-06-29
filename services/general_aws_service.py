"""
General AWS service implementation for comprehensive resource discovery.

This service handles all AWS resource types not covered by specific service implementations
(EC2, S3, IAM). It organizes resource types by service prefix and provides comprehensive
discovery across all 600+ AWS resource types.
"""

from typing import List, Dict, Set, Any
from collections import defaultdict
from core.base_service import BaseAWSService
from core.resource_info import ResourceInfo
from core.resource_config import get_resource_config
from .service_registry import register_service


@register_service
class GeneralAWSService(BaseAWSService):
    """General AWS service discovery implementation for all remaining resource types"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Group resource types by service prefix for better organization
        self._resource_groups = self._organize_resource_types_by_service()
        
        # Track which services have been processed
        self._processed_services = set()
    
    def get_service_name(self) -> str:
        return "general"
    
    def get_supported_resource_types(self) -> List[str]:
        """Return all AWS resource types not handled by specific services"""
        
        # Get resource types from configuration
        config = get_resource_config()
        all_resource_types = config.get_all_resource_types()
        
        # Resource types already handled by dedicated services
        ec2_types = set([
            "AWS::EC2::CapacityReservation", "AWS::EC2::CapacityReservationFleet", "AWS::EC2::CarrierGateway",
            "AWS::EC2::CustomerGateway", "AWS::EC2::DHCPOptions", "AWS::EC2::EC2Fleet", "AWS::EC2::EIP",
            "AWS::EC2::EIPAssociation", "AWS::EC2::EgressOnlyInternetGateway", "AWS::EC2::EnclaveCertificateIamRoleAssociation",
            "AWS::EC2::FlowLog", "AWS::EC2::GatewayRouteTableAssociation", "AWS::EC2::Host", "AWS::EC2::IPAM",
            "AWS::EC2::IPAMAllocation", "AWS::EC2::IPAMPool", "AWS::EC2::IPAMPoolCidr", "AWS::EC2::IPAMResourceDiscovery",
            "AWS::EC2::IPAMResourceDiscoveryAssociation", "AWS::EC2::IPAMScope", "AWS::EC2::Instance",
            "AWS::EC2::InstanceConnectEndpoint", "AWS::EC2::InternetGateway", "AWS::EC2::KeyPair",
            "AWS::EC2::LaunchTemplate", "AWS::EC2::LocalGatewayRoute", "AWS::EC2::LocalGatewayRouteTable",
            "AWS::EC2::LocalGatewayRouteTableVPCAssociation", "AWS::EC2::LocalGatewayRouteTableVirtualInterfaceGroupAssociation",
            "AWS::EC2::NatGateway", "AWS::EC2::NetworkAcl", "AWS::EC2::NetworkInsightsAccessScope",
            "AWS::EC2::NetworkInsightsAccessScopeAnalysis", "AWS::EC2::NetworkInsightsAnalysis", "AWS::EC2::NetworkInsightsPath",
            "AWS::EC2::NetworkInterface", "AWS::EC2::NetworkInterfaceAttachment", "AWS::EC2::NetworkPerformanceMetricSubscription",
            "AWS::EC2::PlacementGroup", "AWS::EC2::PrefixList", "AWS::EC2::Route", "AWS::EC2::RouteServer",
            "AWS::EC2::RouteServerAssociation", "AWS::EC2::RouteServerEndpoint", "AWS::EC2::RouteServerPeer",
            "AWS::EC2::RouteServerPropagation", "AWS::EC2::RouteTable", "AWS::EC2::SecurityGroup",
            "AWS::EC2::SecurityGroupEgress", "AWS::EC2::SecurityGroupIngress", "AWS::EC2::SecurityGroupVpcAssociation",
            "AWS::EC2::SnapshotBlockPublicAccess", "AWS::EC2::SpotFleet", "AWS::EC2::Subnet", "AWS::EC2::SubnetCidrBlock",
            "AWS::EC2::SubnetNetworkAclAssociation", "AWS::EC2::SubnetRouteTableAssociation", "AWS::EC2::TransitGateway",
            "AWS::EC2::TransitGatewayAttachment", "AWS::EC2::TransitGatewayConnect", "AWS::EC2::TransitGatewayMulticastDomain",
            "AWS::EC2::TransitGatewayMulticastDomainAssociation", "AWS::EC2::TransitGatewayMulticastGroupMember",
            "AWS::EC2::TransitGatewayMulticastGroupSource", "AWS::EC2::TransitGatewayPeeringAttachment",
            "AWS::EC2::TransitGatewayRoute", "AWS::EC2::TransitGatewayRouteTable", "AWS::EC2::TransitGatewayRouteTableAssociation",
            "AWS::EC2::TransitGatewayRouteTablePropagation", "AWS::EC2::TransitGatewayVpcAttachment", "AWS::EC2::VPC",
            "AWS::EC2::VPCBlockPublicAccessExclusion", "AWS::EC2::VPCBlockPublicAccessOptions", "AWS::EC2::VPCCidrBlock",
            "AWS::EC2::VPCDHCPOptionsAssociation", "AWS::EC2::VPCEndpoint", "AWS::EC2::VPCEndpointConnectionNotification",
            "AWS::EC2::VPCEndpointService", "AWS::EC2::VPCEndpointServicePermissions", "AWS::EC2::VPCGatewayAttachment",
            "AWS::EC2::VPCPeeringConnection", "AWS::EC2::VPNConnection", "AWS::EC2::VPNConnectionRoute",
            "AWS::EC2::VPNGateway", "AWS::EC2::VerifiedAccessEndpoint", "AWS::EC2::VerifiedAccessGroup",
            "AWS::EC2::VerifiedAccessInstance", "AWS::EC2::VerifiedAccessTrustProvider", "AWS::EC2::Volume",
            "AWS::EC2::VolumeAttachment"
        ])
        
        s3_types = set([
            "AWS::S3::AccessGrant", "AWS::S3::AccessGrantsInstance", "AWS::S3::AccessGrantsLocation",
            "AWS::S3::AccessPoint", "AWS::S3::Bucket", "AWS::S3::BucketPolicy", "AWS::S3::MultiRegionAccessPoint",
            "AWS::S3::MultiRegionAccessPointPolicy", "AWS::S3::StorageLens", "AWS::S3::StorageLensGroup",
            "AWS::S3Express::AccessPoint", "AWS::S3Express::BucketPolicy", "AWS::S3Express::DirectoryBucket",
            "AWS::S3ObjectLambda::AccessPoint", "AWS::S3ObjectLambda::AccessPointPolicy", "AWS::S3Outposts::AccessPoint",
            "AWS::S3Outposts::Bucket", "AWS::S3Outposts::BucketPolicy", "AWS::S3Outposts::Endpoint",
            "AWS::S3Tables::TableBucket", "AWS::S3Tables::TableBucketPolicy"
        ])
        
        iam_types = set([
            "AWS::IAM::Group", "AWS::IAM::GroupPolicy", "AWS::IAM::InstanceProfile", "AWS::IAM::ManagedPolicy",
            "AWS::IAM::OIDCProvider", "AWS::IAM::Role", "AWS::IAM::RolePolicy", "AWS::IAM::SAMLProvider",
            "AWS::IAM::ServerCertificate", "AWS::IAM::ServiceLinkedRole", "AWS::IAM::User", "AWS::IAM::UserPolicy",
            "AWS::IAM::VirtualMFADevice"
        ])
        
        # Filter out resource types handled by dedicated services
        excluded_types = ec2_types | s3_types | iam_types
        remaining_types = [rt for rt in all_resource_types if rt not in excluded_types]
        
        return remaining_types
    
    def _organize_resource_types_by_service(self) -> Dict[str, List[str]]:
        """Organize resource types by AWS service prefix for better management"""
        service_groups = defaultdict(list)
        
        for resource_type in self.get_supported_resource_types():
            # Extract service prefix (e.g., "AutoScaling" from "AWS::AutoScaling::LaunchConfiguration")
            parts = resource_type.split("::")
            if len(parts) >= 3:
                service_prefix = parts[1]
                service_groups[service_prefix].append(resource_type)
        
        return dict(service_groups)
    
    def get_available_services(self) -> List[str]:
        """Get list of AWS services that have discoverable resources"""
        return list(self._resource_groups.keys())
    
    def is_service_filter_match(self, service_filter: str) -> bool:
        """Check if this service matches the provided filter"""
        if not service_filter:
            return True
        
        service_filter = service_filter.lower()
        
        # Check against service name
        if service_filter in self.get_service_name():
            return True
        
        # Check against available AWS services
        for service in self.get_available_services():
            if service_filter in service.lower():
                return True
        
        return False
    
    def discover_resources(self) -> List[ResourceInfo]:
        """
        Discover resources from all registered AWS services
        
        Returns:
            List of discovered ResourceInfo objects
        """
        if not self.is_service_filter_match(self.config.service_filter):
            self.logger.info(f"🔄 Skipping {self.get_service_name()} service (filter: {self.config.service_filter})")
            return []
        
        # Statistics tracking
        discovery_stats = {
            'services_processed': 0,
            'services_successful': 0,
            'services_failed': 0,
            'resources_discovered': 0
        }
        
        # Discover from all services
        all_resources = []
        
        # Sort services alphabetically for consistent output
        for service_name in sorted(self.get_available_services()):
            try:
                self.logger.info(f"🔍 Discovering {service_name} resources...")
                discovery_stats['services_processed'] += 1
                
                service_resources = self._discover_service_resources(service_name)
                
                if service_resources:
                    valid_resources = [r for r in service_resources if not r.error]
                    error_resources = [r for r in service_resources if r.error]
                    
                    all_resources.extend(service_resources)
                    discovery_stats['resources_discovered'] += len(service_resources)
                    discovery_stats['services_successful'] += 1
                    
                    self.logger.info(f"✅ {service_name}: {len(valid_resources)} resources, {len(error_resources)} errors")
                else:
                    self.logger.info(f"⚫ {service_name}: No resources found")
                    discovery_stats['services_successful'] += 1
                
                # Track processed services
                self._processed_services.add(service_name)
                
            except Exception as e:
                discovery_stats['services_failed'] += 1
                self.logger.error(f"❌ Failed to discover {service_name} resources: {e}")
                
                # Create error resource for tracking
                error_resource = ResourceInfo(
                    resource_type=f"AWS::{service_name}::*",
                    identifier="discovery-error",
                    region=self.config.region,
                    error=str(e)
                )
                all_resources.append(error_resource)
        
        # Log discovery summary
        self.logger.info(f"📊 General Service Discovery Summary:")
        self.logger.info(f"   Services Processed: {discovery_stats['services_processed']}")
        self.logger.info(f"   Services Successful: {discovery_stats['services_successful']}")
        self.logger.info(f"   Services Failed: {discovery_stats['services_failed']}")
        self.logger.info(f"   Total Resources: {discovery_stats['resources_discovered']}")
        
        return all_resources
    
    def _discover_service_resources(self, service_name: str) -> List[ResourceInfo]:
        """
        Discover resources for a specific AWS service
        
        Args:
            service_name: Name of the AWS service (e.g., "AutoScaling", "Lambda")
            
        Returns:
            List of ResourceInfo objects for the service
        """
        if service_name not in self._resource_groups:
            self.logger.warning(f"⚠️  Service {service_name} not found in resource groups")
            return []
        
        # Get resource types for this service
        service_resources = []
        resource_types = self._resource_groups[service_name]
        
        for resource_type in resource_types:
            try:
                # Use parent class method to discover resources of this type
                resources = super().discover_resources_by_type(resource_type)
                service_resources.extend(resources)
                
            except Exception as e:
                self.logger.error(f"❌ Failed to discover {resource_type}: {e}")
                # Create error resource for tracking
                error_resource = ResourceInfo(
                    resource_type=resource_type,
                    identifier="discovery-error",
                    region=self.config.region,
                    error=str(e)
                )
                service_resources.append(error_resource)
        
        valid_resources = [r for r in service_resources if not r.error]
        if valid_resources:
            self.logger.debug(f"🔍 {service_name}: Found {len(valid_resources)} resources across {len(resource_types)} types")
        
        return service_resources
    
    def get_discovery_summary(self) -> Dict[str, Any]:
        """Get summary of discovery operations"""
        return {
            'service_name': self.get_service_name(),
            'total_resource_types': len(self.get_supported_resource_types()),
            'services_available': len(self.get_available_services()),
            'services_processed': len(self._processed_services),
            'resource_groups': {
                service: len(types) 
                for service, types in self._resource_groups.items()
            }
        }