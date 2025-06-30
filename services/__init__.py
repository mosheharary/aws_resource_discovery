"""
Service modules for AWS resource discovery.

Contains individual service implementations for different AWS services.
"""

# Import all service implementations to ensure they get registered
from .ec2_service import EC2Service
from .s3_service import S3Service
from .iam_service import IAMService
from .general_aws_service import GeneralAWSService

# Import service registry components for external use
from .service_registry import ServiceRegistry, ServiceFactory, get_registry, register_service

__all__ = [
    'EC2Service',
    'S3Service', 
    'IAMService',
    'GeneralAWSService',
    'ServiceRegistry',
    'ServiceFactory',
    'get_registry',
    'register_service'
]