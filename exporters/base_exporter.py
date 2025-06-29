"""
Base exporter class for AWS resource discovery output formats.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from pathlib import Path
import logging

from core.resource_info import ResourceInfo
from core.config import DiscoveryConfig


class BaseExporter(ABC):
    """Abstract base class for resource exporters"""
    
    def __init__(self, config: DiscoveryConfig, output_dir: Path):
        """Initialize exporter with configuration and output directory"""
        self.config = config
        self.output_dir = output_dir
        self.logger = logging.getLogger(f'aws_discovery.exporter.{self.get_format_name()}')
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def get_format_name(self) -> str:
        """Return the format name (e.g., 'json', 'csv', 'excel')"""
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """Return the file extension (e.g., '.json', '.csv', '.xlsx')"""
        pass
    
    @abstractmethod
    def export_resources(self, resources: List[ResourceInfo], filename: str = None) -> Path:
        """Export resources to the specified format"""
        pass
    
    def should_export(self) -> bool:
        """Check if this format should be exported based on configuration"""
        return self.config.should_export_format(self.get_format_name())
    
    def get_output_filename(self, base_name: str = "resources") -> str:
        """Get the output filename with appropriate extension"""
        return f"{base_name}{self.get_file_extension()}"
    
    def get_output_path(self, filename: str) -> Path:
        """Get the full output path for a filename"""
        return self.output_dir / filename
    
    def filter_resources(self, resources: List[ResourceInfo]) -> List[ResourceInfo]:
        """Filter resources based on configuration"""
        filtered = []
        
        for resource in resources:
            # Skip resources with errors if configured
            if resource.has_error():
                continue
            
            # Apply service filter if configured
            if self.config.service_filter:
                if self.config.service_filter.lower() not in resource.service.lower():
                    continue
            
            filtered.append(resource)
        
        return filtered
    
    def prepare_resource_data(self, resource: ResourceInfo) -> Dict[str, Any]:
        """Prepare resource data for export"""
        return {
            'resource_type': resource.resource_type,
            'service': resource.service,
            'identifier': resource.identifier,
            'arn': resource.arn,
            'region': resource.region,
            'properties': resource.properties,
            'error': resource.error
        }
    
    def get_export_statistics(self, resources: List[ResourceInfo]) -> Dict[str, Any]:
        """Get statistics about the exported resources"""
        total_resources = len(resources)
        resources_with_errors = sum(1 for r in resources if r.has_error())
        valid_resources = total_resources - resources_with_errors
        
        # Count by service
        service_counts = {}
        for resource in resources:
            service = resource.service or 'unknown'
            service_counts[service] = service_counts.get(service, 0) + 1
        
        # Count by region
        region_counts = {}
        for resource in resources:
            region = resource.region or 'global'
            region_counts[region] = region_counts.get(region, 0) + 1
        
        return {
            'total_resources': total_resources,
            'valid_resources': valid_resources,
            'resources_with_errors': resources_with_errors,
            'services': service_counts,
            'regions': region_counts
        }
    
    def log_export_summary(self, resources: List[ResourceInfo], output_path: Path):
        """Log export summary"""
        stats = self.get_export_statistics(resources)
        
        self.logger.info(f"📄 {self.get_format_name().upper()} Export Summary:")
        self.logger.info(f"   File: {output_path}")
        self.logger.info(f"   Total Resources: {stats['total_resources']}")
        self.logger.info(f"   Valid Resources: {stats['valid_resources']}")
        
        if stats['resources_with_errors'] > 0:
            self.logger.warning(f"   Resources with Errors: {stats['resources_with_errors']}")
        
        # Log top services
        top_services = sorted(stats['services'].items(), key=lambda x: x[1], reverse=True)[:5]
        if top_services:
            self.logger.info(f"   Top Services: {', '.join([f'{s}({c})' for s, c in top_services])}")
    
    def create_summary_data(self, resources: List[ResourceInfo]) -> Dict[str, Any]:
        """Create summary data for export"""
        stats = self.get_export_statistics(resources)
        
        return {
            'export_metadata': {
                'format': self.get_format_name(),
                'timestamp': str(Path().cwd()),  # Will be replaced with actual timestamp
                'region': self.config.region,
                'service_filter': self.config.service_filter,
                'statistics': stats
            }
        }