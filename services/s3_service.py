"""
S3 service implementation for AWS resource discovery.
"""

from typing import List, Dict
from core.base_service import BaseAWSService
from core.resource_info import ResourceInfo
from .service_registry import register_service


@register_service
class S3Service(BaseAWSService):
    """S3 service discovery implementation"""
    
    def get_service_name(self) -> str:
        return "s3"
    
    def get_supported_resource_types(self) -> List[str]:
        """Return S3 resource types supported by Cloud Control API"""
        return [
            "AWS::S3::AccessGrant",
            "AWS::S3::AccessGrantsInstance",
            "AWS::S3::AccessGrantsLocation",
            "AWS::S3::AccessPoint",
            "AWS::S3::Bucket",
            "AWS::S3::BucketPolicy",
            "AWS::S3::MultiRegionAccessPoint",
            "AWS::S3::MultiRegionAccessPointPolicy",
            "AWS::S3::StorageLens",
            "AWS::S3::AccessPointAlias",
            "AWS::S3::BucketIntelligentTieringConfiguration",
            "AWS::S3::BucketInventoryConfiguration",
            "AWS::S3::BucketLoggingConfiguration",
            "AWS::S3::BucketMetricsConfiguration",
            "AWS::S3::BucketNotification",
            "AWS::S3::BucketOwnershipControlsConfiguration",
            "AWS::S3::BucketPublicAccessBlockConfiguration",
            "AWS::S3::BucketReplicationConfiguration",
            "AWS::S3::BucketRequestPaymentConfiguration",
            "AWS::S3::BucketTaggingConfiguration",
            "AWS::S3::BucketVersioningConfiguration",
            "AWS::S3::BucketWebsiteConfiguration",
        ]
    
    def get_skip_patterns(self) -> Dict[str, List[str]]:
        """S3-specific resource types to skip"""
        return {
            'missing_required_key': [
                "AWS::S3::BucketPolicy",  # Requires bucket name
                "AWS::S3::MultiRegionAccessPointPolicy",  # Requires access point ARN
            ],
            'unsupported_action': [],
            'type_not_found': [
                "AWS::S3::AccessPointAlias",  # May not be available in all regions
            ],
            'subscription_required': [
                # S3 Access Grants requires setup
                "AWS::S3::AccessGrant",
                "AWS::S3::AccessGrantsInstance", 
                "AWS::S3::AccessGrantsLocation",
            ]
        }
    
    def discover_resources(self) -> List[ResourceInfo]:
        """Discover all S3 resources"""
        self.logger.info(f"🔍 Starting S3 resource discovery in {self.region}")
        
        all_resources = []
        resource_types = self.get_supported_resource_types()
        
        self.logger.info(f"📋 Discovering {len(resource_types)} S3 resource types")
        
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
        
        # Enhance S3 bucket information
        enhanced_resources = []
        for resource in all_resources:
            if resource.resource_type == "AWS::S3::Bucket" and not resource.has_error():
                enhanced_resource = self.get_enhanced_bucket_info(resource)
                enhanced_resources.append(enhanced_resource)
            else:
                enhanced_resources.append(resource)
        
        self.logger.info(f"🏁 S3 discovery complete: {len(enhanced_resources)} total resources")
        self.log_statistics()
        
        return enhanced_resources
    
    def get_enhanced_bucket_info(self, resource_info: ResourceInfo) -> ResourceInfo:
        """Get enhanced information for S3 buckets using direct S3 API"""
        if resource_info.resource_type != "AWS::S3::Bucket":
            return resource_info
        
        try:
            s3_client = self.get_client('s3')
            bucket_name = resource_info.identifier
            
            enhanced_properties = resource_info.properties.copy()
            
            # Get bucket location
            try:
                location = s3_client.get_bucket_location(Bucket=bucket_name)
                enhanced_properties['LocationConstraint'] = location.get('LocationConstraint', 'us-east-1')
            except Exception as e:
                self.logger.debug(f"Failed to get location for bucket {bucket_name}: {e}")
            
            # Get bucket encryption
            try:
                encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
                enhanced_properties['Encryption'] = encryption.get('ServerSideEncryptionConfiguration', {})
            except Exception as e:
                self.logger.debug(f"No encryption config for bucket {bucket_name}: {e}")
            
            # Get bucket versioning
            try:
                versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
                enhanced_properties['Versioning'] = {
                    'Status': versioning.get('Status', 'Disabled'),
                    'MfaDelete': versioning.get('MfaDelete', 'Disabled')
                }
            except Exception as e:
                self.logger.debug(f"Failed to get versioning for bucket {bucket_name}: {e}")
            
            # Get bucket public access block
            try:
                public_access_block = s3_client.get_public_access_block(Bucket=bucket_name)
                enhanced_properties['PublicAccessBlockConfiguration'] = public_access_block.get('PublicAccessBlockConfiguration', {})
            except Exception as e:
                self.logger.debug(f"No public access block for bucket {bucket_name}: {e}")
            
            # Get bucket logging
            try:
                logging_config = s3_client.get_bucket_logging(Bucket=bucket_name)
                enhanced_properties['LoggingConfiguration'] = logging_config.get('LoggingEnabled', {})
            except Exception as e:
                self.logger.debug(f"No logging config for bucket {bucket_name}: {e}")
            
            resource_info.properties = enhanced_properties
            
        except Exception as e:
            self.logger.warning(f"Failed to enhance S3 bucket {resource_info.identifier}: {e}")
        
        return resource_info
    
    def is_global_service(self) -> bool:
        """S3 bucket names are global but buckets exist in specific regions"""
        return False  # S3 buckets are region-specific even though names are global