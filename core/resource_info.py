"""
Resource information data model for AWS resource discovery.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ResourceInfo:
    """Data class to hold comprehensive resource information for discovered AWS resources"""
    resource_type: str  # AWS resource type (e.g., "AWS::EC2::Instance")
    identifier: str     # Unique resource identifier
    arn: str = ""       # Amazon Resource Name
    properties: Dict[str, Any] = None  # Resource properties from AWS APIs
    service: str = ""   # AWS service name (extracted from resource_type)
    region: str = ""    # AWS region where resource exists
    error: str = ""     # Error message if discovery failed
    
    def __post_init__(self):
        """Initialize properties and extract service name"""
        if self.properties is None:
            self.properties = {}
        
        # Extract service name from resource type (AWS::EC2::Instance -> ec2)
        if "::" in self.resource_type:
            self.service = self.resource_type.split("::")[1].lower()
    
    def has_error(self) -> bool:
        """Check if resource discovery encountered an error"""
        return bool(self.error)
    
    def is_valid(self) -> bool:
        """Check if resource has valid data"""
        return bool(self.identifier and not self.has_error())
    
    def get_service_name(self) -> str:
        """Get the AWS service name"""
        return self.service
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ResourceInfo to dictionary for serialization"""
        return {
            'resource_type': self.resource_type,
            'identifier': self.identifier,
            'arn': self.arn,
            'properties': self.properties,
            'service': self.service,
            'region': self.region,
            'error': self.error
        }