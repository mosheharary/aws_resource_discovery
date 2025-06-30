"""
Service registry for managing AWS service discovery implementations.
"""

from typing import Dict, List, Type, Optional
import logging
import boto3

from core.base_service import BaseAWSService
from core.config import DiscoveryConfig


class ServiceRegistry:
    """Registry for AWS service discovery implementations"""
    
    def __init__(self):
        self._services: Dict[str, Type[BaseAWSService]] = {}
        self.logger = logging.getLogger('aws_discovery.registry')
    
    def register_service(self, service_class: Type[BaseAWSService]):
        """Register a service implementation"""
        # Create temporary instance to get service name
        temp_config = DiscoveryConfig(region='us-east-1')  # Dummy config
        temp_session = boto3.Session()  # Dummy session
        
        try:
            temp_instance = service_class(temp_config, temp_session)
            service_name = temp_instance.get_service_name()
            
            if service_name in self._services:
                self.logger.warning(f"Service {service_name} already registered, overwriting")
            
            self._services[service_name] = service_class
            self.logger.debug(f"Registered service: {service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to register service {service_class.__name__}: {e}")
    
    def get_service(self, service_name: str, config: DiscoveryConfig, session: boto3.Session) -> Optional[BaseAWSService]:
        """Get a service instance by name"""
        if service_name not in self._services:
            self.logger.error(f"Service {service_name} not found in registry")
            return None
        
        try:
            service_class = self._services[service_name]
            return service_class(config, session)
        except Exception as e:
            self.logger.error(f"Failed to create service instance for {service_name}: {e}")
            return None
    
    def get_all_services(self, config: DiscoveryConfig, session: boto3.Session) -> List[BaseAWSService]:
        """Get instances of all registered services"""
        services = []
        
        for service_name, service_class in self._services.items():
            try:
                service_instance = service_class(config, session)
                services.append(service_instance)
            except Exception as e:
                self.logger.error(f"Failed to create service instance for {service_name}: {e}")
        
        return services
    
    def get_filtered_services(self, service_filter: str, config: DiscoveryConfig, session: boto3.Session) -> List[BaseAWSService]:
        """Get services filtered by service name pattern"""
        services = []
        filter_lower = service_filter.lower()
        
        for service_name, service_class in self._services.items():
            if filter_lower in service_name.lower():
                try:
                    service_instance = service_class(config, session)
                    services.append(service_instance)
                except Exception as e:
                    self.logger.error(f"Failed to create service instance for {service_name}: {e}")
        
        return services
    
    def list_registered_services(self) -> List[str]:
        """Get list of registered service names"""
        return list(self._services.keys())
    
    def get_all_resource_types(self, config: DiscoveryConfig, session: boto3.Session) -> Dict[str, List[str]]:
        """Get all resource types supported by registered services"""
        all_resource_types = {}
        
        for service_name, service_class in self._services.items():
            try:
                service_instance = service_class(config, session)
                resource_types = service_instance.get_supported_resource_types()
                all_resource_types[service_name] = resource_types
            except Exception as e:
                self.logger.error(f"Failed to get resource types for {service_name}: {e}")
                all_resource_types[service_name] = []
        
        return all_resource_types
    
    def get_service_by_resource_type(self, resource_type: str, config: DiscoveryConfig, session: boto3.Session) -> Optional[BaseAWSService]:
        """Get the service that handles a specific resource type"""
        for service_name, service_class in self._services.items():
            try:
                service_instance = service_class(config, session)
                if resource_type in service_instance.get_supported_resource_types():
                    return service_instance
            except Exception as e:
                self.logger.error(f"Failed to check resource types for {service_name}: {e}")
        
        return None


# Global service registry instance
_registry = ServiceRegistry()


def register_service(service_class: Type[BaseAWSService]):
    """Decorator to register a service class"""
    _registry.register_service(service_class)
    return service_class


def get_registry() -> ServiceRegistry:
    """Get the global service registry"""
    return _registry


class ServiceFactory:
    """Factory for creating service instances"""
    
    def __init__(self, config: DiscoveryConfig, session: boto3.Session):
        self.config = config
        self.session = session
        self.registry = get_registry()
        self.logger = logging.getLogger('aws_discovery.factory')
    
    def create_all_services(self) -> List[BaseAWSService]:
        """Create instances of all registered services"""
        return self.registry.get_all_services(self.config, self.session)
    
    def create_filtered_services(self, service_filter: str) -> List[BaseAWSService]:
        """Create services filtered by name pattern"""
        return self.registry.get_filtered_services(service_filter, self.config, self.session)
    
    def create_service(self, service_name: str) -> Optional[BaseAWSService]:
        """Create a specific service instance"""
        return self.registry.get_service(service_name, self.config, self.session)
    
    def get_services_for_discovery(self) -> List[BaseAWSService]:
        """Get services based on configuration filters"""
        if self.config.service_filter:
            self.logger.info(f"Filtering services by: {self.config.service_filter}")
            return self.create_filtered_services(self.config.service_filter)
        else:
            self.logger.info("Discovering all services")
            return self.create_all_services()
    
    def log_available_services(self):
        """Log information about available services"""
        services = self.registry.list_registered_services()
        self.logger.info(f"Available services ({len(services)}): {', '.join(sorted(services))}")
    
    def get_resource_type_mapping(self) -> Dict[str, str]:
        """Get mapping of resource types to service names"""
        mapping = {}
        resource_types_by_service = self.registry.get_all_resource_types(self.config, self.session)
        
        for service_name, resource_types in resource_types_by_service.items():
            for resource_type in resource_types:
                mapping[resource_type] = service_name
        
        return mapping