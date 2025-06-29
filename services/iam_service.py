"""
IAM service implementation for AWS resource discovery.
"""

from typing import List, Dict
from core.base_service import BaseAWSService
from core.resource_info import ResourceInfo
from .service_registry import register_service


@register_service
class IAMService(BaseAWSService):
    """IAM service discovery implementation"""
    
    def get_service_name(self) -> str:
        return "iam"
    
    def get_supported_resource_types(self) -> List[str]:
        """Return IAM resource types supported by Cloud Control API"""
        return [
            "AWS::IAM::AccessKey",
            "AWS::IAM::Group",
            "AWS::IAM::GroupPolicy",
            "AWS::IAM::InstanceProfile",
            "AWS::IAM::ManagedPolicy",
            "AWS::IAM::OIDCProvider",
            "AWS::IAM::Policy",
            "AWS::IAM::Role",
            "AWS::IAM::RolePolicy",
            "AWS::IAM::SAMLProvider",
            "AWS::IAM::ServerCertificate",
            "AWS::IAM::ServiceLinkedRole",
            "AWS::IAM::User",
            "AWS::IAM::UserPolicy",
            "AWS::IAM::VirtualMFADevice",
        ]
    
    def get_skip_patterns(self) -> Dict[str, List[str]]:
        """IAM-specific resource types to skip"""
        return {
            'missing_required_key': [
                "AWS::IAM::AccessKey",  # Requires username
                "AWS::IAM::GroupPolicy",  # Requires group name and policy name
                "AWS::IAM::RolePolicy",  # Requires role name and policy name
                "AWS::IAM::UserPolicy",  # Requires username and policy name
            ],
            'unsupported_action': [],
            'type_not_found': [],
            'subscription_required': []
        }
    
    def discover_resources(self) -> List[ResourceInfo]:
        """Discover all IAM resources"""
        self.logger.info("🔍 Starting IAM resource discovery (global service)")
        
        all_resources = []
        resource_types = self.get_supported_resource_types()
        
        self.logger.info(f"📋 Discovering {len(resource_types)} IAM resource types")
        
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
                    region=""  # IAM is global
                )
                all_resources.append(error_resource)
        
        # Enhance IAM resources with additional information
        enhanced_resources = []
        for resource in all_resources:
            if not resource.has_error():
                enhanced_resource = self.get_enhanced_iam_info(resource)
                enhanced_resources.append(enhanced_resource)
            else:
                enhanced_resources.append(resource)
        
        self.logger.info(f"🏁 IAM discovery complete: {len(enhanced_resources)} total resources")
        self.log_statistics()
        
        return enhanced_resources
    
    def get_enhanced_iam_info(self, resource_info: ResourceInfo) -> ResourceInfo:
        """Get enhanced information for IAM resources using direct IAM API"""
        try:
            iam_client = self.get_client('iam')
            enhanced_properties = resource_info.properties.copy()
            
            # Enhance based on resource type
            if resource_info.resource_type == "AWS::IAM::Role":
                role_name = resource_info.identifier
                try:
                    role_response = iam_client.get_role(RoleName=role_name)
                    role_data = role_response['Role']
                    
                    enhanced_properties.update({
                        'CreateDate': str(role_data.get('CreateDate', '')),
                        'MaxSessionDuration': role_data.get('MaxSessionDuration', 0),
                        'Path': role_data.get('Path', '/'),
                        'AssumeRolePolicyDocument': role_data.get('AssumeRolePolicyDocument', {}),
                        'Tags': role_data.get('Tags', [])
                    })
                    
                    # Get attached policies
                    try:
                        policies_response = iam_client.list_attached_role_policies(RoleName=role_name)
                        enhanced_properties['AttachedManagedPolicies'] = policies_response.get('AttachedPolicies', [])
                    except Exception as e:
                        self.logger.debug(f"Failed to get attached policies for role {role_name}: {e}")
                    
                except Exception as e:
                    self.logger.debug(f"Failed to enhance IAM role {role_name}: {e}")
            
            elif resource_info.resource_type == "AWS::IAM::User":
                user_name = resource_info.identifier
                try:
                    user_response = iam_client.get_user(UserName=user_name)
                    user_data = user_response['User']
                    
                    enhanced_properties.update({
                        'CreateDate': str(user_data.get('CreateDate', '')),
                        'Path': user_data.get('Path', '/'),
                        'PasswordLastUsed': str(user_data.get('PasswordLastUsed', '')),
                        'Tags': user_data.get('Tags', [])
                    })
                    
                    # Get user groups
                    try:
                        groups_response = iam_client.get_groups_for_user(UserName=user_name)
                        enhanced_properties['Groups'] = [g['GroupName'] for g in groups_response.get('Groups', [])]
                    except Exception as e:
                        self.logger.debug(f"Failed to get groups for user {user_name}: {e}")
                    
                except Exception as e:
                    self.logger.debug(f"Failed to enhance IAM user {user_name}: {e}")
            
            elif resource_info.resource_type == "AWS::IAM::Policy":
                policy_arn = resource_info.arn or resource_info.identifier
                try:
                    policy_response = iam_client.get_policy(PolicyArn=policy_arn)
                    policy_data = policy_response['Policy']
                    
                    enhanced_properties.update({
                        'CreateDate': str(policy_data.get('CreateDate', '')),
                        'UpdateDate': str(policy_data.get('UpdateDate', '')),
                        'AttachmentCount': policy_data.get('AttachmentCount', 0),
                        'IsAttachable': policy_data.get('IsAttachable', False),
                        'Path': policy_data.get('Path', '/'),
                        'DefaultVersionId': policy_data.get('DefaultVersionId', ''),
                        'Tags': policy_data.get('Tags', [])
                    })
                    
                except Exception as e:
                    self.logger.debug(f"Failed to enhance IAM policy {policy_arn}: {e}")
            
            resource_info.properties = enhanced_properties
            
        except Exception as e:
            self.logger.warning(f"Failed to enhance IAM resource {resource_info.identifier}: {e}")
        
        return resource_info
    
    def is_global_service(self) -> bool:
        """IAM is a global service"""
        return True