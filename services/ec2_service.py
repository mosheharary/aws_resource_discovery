"""
EC2 service implementation for AWS resource discovery.
"""

from typing import List, Dict
from core.base_service import BaseAWSService
from core.resource_info import ResourceInfo
from .service_registry import register_service


@register_service
class EC2Service(BaseAWSService):
    """EC2 service discovery implementation"""
    
    def get_service_name(self) -> str:
        return "ec2"
    
    def get_supported_resource_types(self) -> List[str]:
        """Return EC2 resource types supported by Cloud Control API"""
        return [
            "AWS::EC2::CapacityReservation",
            "AWS::EC2::CapacityReservationFleet",
            "AWS::EC2::CarrierGateway",
            "AWS::EC2::CustomerGateway",
            "AWS::EC2::DHCPOptions",
            "AWS::EC2::EC2Fleet",
            "AWS::EC2::EIP",
            "AWS::EC2::EIPAssociation",
            "AWS::EC2::EgressOnlyInternetGateway",
            "AWS::EC2::EnclaveCertificateIamRoleAssociation",
            "AWS::EC2::FlowLog",
            "AWS::EC2::GatewayRouteTableAssociation",
            "AWS::EC2::Host",
            "AWS::EC2::IPAM",
            "AWS::EC2::IPAMAllocation",
            "AWS::EC2::IPAMPool",
            "AWS::EC2::IPAMPoolCidr",
            "AWS::EC2::IPAMResourceDiscovery",
            "AWS::EC2::IPAMResourceDiscoveryAssociation",
            "AWS::EC2::IPAMScope",
            "AWS::EC2::Instance",
            "AWS::EC2::InstanceConnectEndpoint",
            "AWS::EC2::InternetGateway",
            "AWS::EC2::KeyPair",
            "AWS::EC2::LaunchTemplate",
            "AWS::EC2::LocalGatewayRoute",
            "AWS::EC2::LocalGatewayRouteTable",
            "AWS::EC2::LocalGatewayRouteTableVPCAssociation",
            "AWS::EC2::LocalGatewayRouteTableVirtualInterfaceGroupAssociation",
            "AWS::EC2::NatGateway",
            "AWS::EC2::NetworkAcl",
            "AWS::EC2::NetworkInsightsAccessScope",
            "AWS::EC2::NetworkInsightsAccessScopeAnalysis",
            "AWS::EC2::NetworkInsightsAnalysis",
            "AWS::EC2::NetworkInsightsPath",
            "AWS::EC2::NetworkInterface",
            "AWS::EC2::NetworkInterfaceAttachment",
            "AWS::EC2::NetworkPerformanceMetricSubscription",
            "AWS::EC2::PlacementGroup",
            "AWS::EC2::PrefixList",
            "AWS::EC2::Route",
            "AWS::EC2::RouteServer",
            "AWS::EC2::RouteServerAssociation",
            "AWS::EC2::RouteServerEndpoint",
            "AWS::EC2::RouteServerPeer",
            "AWS::EC2::RouteServerPropagation",
            "AWS::EC2::RouteTable",
            "AWS::EC2::SecurityGroup",
            "AWS::EC2::SecurityGroupEgress",
            "AWS::EC2::SecurityGroupIngress",
            "AWS::EC2::SecurityGroupVpcAssociation",
            "AWS::EC2::SnapshotBlockPublicAccess",
            "AWS::EC2::SpotFleet",
            "AWS::EC2::Subnet",
            "AWS::EC2::SubnetCidrBlock",
            "AWS::EC2::SubnetNetworkAclAssociation",
            "AWS::EC2::SubnetRouteTableAssociation",
            "AWS::EC2::TransitGateway",
            "AWS::EC2::TransitGatewayAttachment",
            "AWS::EC2::TransitGatewayConnect",
            "AWS::EC2::TransitGatewayMulticastDomain",
            "AWS::EC2::TransitGatewayMulticastDomainAssociation",
            "AWS::EC2::TransitGatewayMulticastGroupMember",
            "AWS::EC2::TransitGatewayMulticastGroupSource",
            "AWS::EC2::TransitGatewayPeeringAttachment",
            "AWS::EC2::TransitGatewayRoute",
            "AWS::EC2::TransitGatewayRouteTable",
            "AWS::EC2::TransitGatewayRouteTableAssociation",
            "AWS::EC2::TransitGatewayRouteTablePropagation",
            "AWS::EC2::TransitGatewayVpcAttachment",
            "AWS::EC2::VPC",
            "AWS::EC2::VPCBlockPublicAccessExclusion",
            "AWS::EC2::VPCBlockPublicAccessOptions",
            "AWS::EC2::VPCCidrBlock",
            "AWS::EC2::VPCDHCPOptionsAssociation",
            "AWS::EC2::VPCEndpoint",
            "AWS::EC2::VPCEndpointConnectionNotification",
            "AWS::EC2::VPCEndpointService",
            "AWS::EC2::VPCEndpointServicePermissions",
            "AWS::EC2::VPCGatewayAttachment",
            "AWS::EC2::VPCPeeringConnection",
            "AWS::EC2::VPNConnection",
            "AWS::EC2::VPNConnectionRoute",
            "AWS::EC2::VPNGateway",
            "AWS::EC2::VerifiedAccessEndpoint",
            "AWS::EC2::VerifiedAccessGroup",
            "AWS::EC2::VerifiedAccessInstance",
            "AWS::EC2::VerifiedAccessTrustProvider",
            "AWS::EC2::Volume",
            "AWS::EC2::VolumeAttachment",
        ]
    
    def get_skip_patterns(self) -> Dict[str, List[str]]:
        """EC2-specific resource types to skip"""
        return {
            'missing_required_key': [
                "AWS::EC2::EIPAssociation",
                "AWS::EC2::NetworkInterfaceAttachment",
                "AWS::EC2::VolumeAttachment",
                # Transit Gateway resources requiring parent IDs
                "AWS::EC2::TransitGatewayMulticastDomainAssociation",
                "AWS::EC2::TransitGatewayMulticastGroupMember", 
                "AWS::EC2::TransitGatewayMulticastGroupSource",
                # Resources requiring certificate ARNs
                "AWS::EC2::EnclaveCertificateIamRoleAssociation",
            ],
            'unsupported_action': [
                "AWS::EC2::SecurityGroupEgress",
                "AWS::EC2::SecurityGroupIngress",
            ],
            'type_not_found': [],
            'subscription_required': []
        }
    
    def discover_resources(self) -> List[ResourceInfo]:
        """Discover all EC2 resources"""
        self.logger.info(f"🔍 Starting EC2 resource discovery in {self.region}")
        
        all_resources = []
        resource_types = self.get_supported_resource_types()
        
        self.logger.info(f"📋 Discovering {len(resource_types)} EC2 resource types")
        
        for resource_type in resource_types:
            try:
                resources = self.discover_resource_type(resource_type)
                all_resources.extend(resources)
                
                if resources:
                    self.logger.debug(f"✓ {resource_type}: {len(resources)} resources")
                
            except Exception as e:
                self.logger.error(f"✗ Failed to discover {resource_type}: {e}")
                # Add error resource
                error_resource = ResourceInfo(
                    resource_type=resource_type,
                    identifier="ERROR",
                    error=str(e),
                    region=self.region
                )
                all_resources.append(error_resource)
        
        self.logger.info(f"🏁 EC2 discovery complete: {len(all_resources)} total resources")
        self.log_statistics()
        
        return all_resources
    
    def get_enhanced_instance_info(self, resource_info: ResourceInfo) -> ResourceInfo:
        """Get enhanced information for EC2 instances using direct EC2 API"""
        if resource_info.resource_type != "AWS::EC2::Instance":
            return resource_info
        
        try:
            ec2_client = self.get_client('ec2')
            
            # Get instance details
            response = ec2_client.describe_instances(
                InstanceIds=[resource_info.identifier]
            )
            
            if response.get('Reservations'):
                for reservation in response['Reservations']:
                    for instance in reservation.get('Instances', []):
                        if instance['InstanceId'] == resource_info.identifier:
                            # Enhance properties with EC2 API data
                            enhanced_properties = resource_info.properties.copy()
                            enhanced_properties.update({
                                'State': instance.get('State', {}),
                                'InstanceType': instance.get('InstanceType', ''),
                                'LaunchTime': str(instance.get('LaunchTime', '')),
                                'VpcId': instance.get('VpcId', ''),
                                'SubnetId': instance.get('SubnetId', ''),
                                'PrivateIpAddress': instance.get('PrivateIpAddress', ''),
                                'PublicIpAddress': instance.get('PublicIpAddress', ''),
                                'SecurityGroups': instance.get('SecurityGroups', []),
                                'Tags': instance.get('Tags', [])
                            })
                            
                            resource_info.properties = enhanced_properties
                            break
            
        except Exception as e:
            self.logger.warning(f"Failed to enhance EC2 instance {resource_info.identifier}: {e}")
        
        return resource_info