"""
Resource configuration management for AWS Resource Discovery.

Handles loading AWS resource types from configuration files and provides
filtering capabilities based on user preferences.
"""

import json
import os
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class ResourceTypeConfig:
    """Manages AWS resource type configuration and filtering"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize resource type configuration
        
        Args:
            config_path: Path to the configuration file. If None, uses default location.
        """
        self._resource_types = []
        self._excluded_types = set()
        self._loaded = False
        
        if config_path is None:
            # Default to config/aws_resource_types.json relative to project root
            project_root = Path(__file__).parent.parent
            config_path = project_root / "config" / "aws_resource_types.json"
        
        self._config_path = Path(config_path)
        self._load_configuration()
    
    def _load_configuration(self):
        """Load resource types from configuration file"""
        try:
            if not self._config_path.exists():
                logger.warning(f"Configuration file not found: {self._config_path}")
                logger.warning("Using fallback resource types list")
                self._load_fallback_types()
                return
            
            with open(self._config_path, 'r') as f:
                config_data = json.load(f)
            
            if 'aws_resource_types' not in config_data:
                raise ValueError("Configuration file must contain 'aws_resource_types' key")
            
            self._resource_types = config_data['aws_resource_types']
            self._loaded = True
            
            logger.info(f"Loaded {len(self._resource_types)} resource types from {self._config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {self._config_path}: {e}")
            logger.warning("Using fallback resource types list")
            self._load_fallback_types()
    
    def _load_fallback_types(self):
        """Load a minimal fallback list of resource types"""
        self._resource_types = [
            "AWS::EC2::Instance",
            "AWS::S3::Bucket",
            "AWS::IAM::User",
            "AWS::IAM::Role",
            "AWS::Lambda::Function",
            "AWS::CloudFormation::Stack",
            "AWS::RDS::DBInstance",
            "AWS::ECS::Cluster",
            "AWS::EKS::Cluster",
            "AWS::ElasticLoadBalancingV2::LoadBalancer"
        ]
        self._loaded = True
        logger.warning(f"Using fallback configuration with {len(self._resource_types)} resource types")
    
    def get_all_resource_types(self) -> List[str]:
        """Get all configured AWS resource types"""
        return self._resource_types.copy()
    
    def set_excluded_types(self, excluded_types: Optional[List[str]] = None):
        """
        Set resource types to exclude from discovery
        
        Args:
            excluded_types: List of resource types to exclude
        """
        self._excluded_types = set(excluded_types or [])
        if excluded_types:
            logger.info(f"Excluding {len(excluded_types)} resource types: {excluded_types}")
    
    def get_filtered_resource_types(self, service_filter: Optional[str] = None) -> List[str]:
        """
        Get filtered list of resource types based on service filter and exclusions
        
        Args:
            service_filter: Optional service filter (e.g., "ec2", "s3")
            
        Returns:
            List of resource types to discover
        """
        # Start with all resource types
        filtered_types = self._resource_types.copy()
        
        # Apply service filter
        if service_filter:
            service_filter = service_filter.lower()
            filtered_types = [
                rt for rt in filtered_types 
                if service_filter in rt.lower()
            ]
        
        # Apply exclusions
        if self._excluded_types:
            filtered_types = [
                rt for rt in filtered_types 
                if rt not in self._excluded_types
            ]
        
        logger.info(f"Filtered to {len(filtered_types)} resource types for discovery")
        if service_filter:
            logger.info(f"Service filter: {service_filter}")
        if self._excluded_types:
            logger.info(f"Excluded types: {sorted(self._excluded_types)}")
        
        return filtered_types
    
    def is_loaded(self) -> bool:
        """Check if configuration was successfully loaded"""
        return self._loaded
    
    def get_config_path(self) -> Path:
        """Get the path to the configuration file"""
        return self._config_path
    
    def reload(self):
        """Reload configuration from file"""
        self._loaded = False
        self._load_configuration()


# Global instance for easy access
_global_config = None


def get_resource_config() -> ResourceTypeConfig:
    """Get the global resource configuration instance"""
    global _global_config
    if _global_config is None:
        _global_config = ResourceTypeConfig()
    return _global_config


def initialize_resource_config(config_path: Optional[str] = None, 
                             excluded_types: Optional[List[str]] = None):
    """
    Initialize the global resource configuration
    
    Args:
        config_path: Path to configuration file
        excluded_types: List of resource types to exclude
    """
    global _global_config
    _global_config = ResourceTypeConfig(config_path)
    if excluded_types:
        _global_config.set_excluded_types(excluded_types)