"""
JSON exporter for AWS resource discovery.
"""

import json
from typing import List
from pathlib import Path
from datetime import datetime

from core.resource_info import ResourceInfo
from .base_exporter import BaseExporter


class JSONExporter(BaseExporter):
    """Export resources to JSON format"""
    
    def get_format_name(self) -> str:
        return "json"
    
    def get_file_extension(self) -> str:
        return ".json"
    
    def export_resources(self, resources: List[ResourceInfo], filename: str = None) -> Path:
        """Export resources to JSON file"""
        if not self.should_export():
            self.logger.debug("JSON export disabled by configuration")
            return None
        
        if filename is None:
            filename = self.get_output_filename()
        
        output_path = self.get_output_path(filename)
        
        self.logger.info(f"📄 Exporting {len(resources)} resources to JSON: {output_path}")
        
        # Filter resources
        filtered_resources = self.filter_resources(resources)
        
        # Prepare export data
        export_data = {
            'metadata': {
                'export_format': 'json',
                'timestamp': datetime.now().isoformat(),
                'region': self.config.region,
                'service_filter': self.config.service_filter,
                'total_resources': len(resources),
                'filtered_resources': len(filtered_resources)
            },
            'statistics': self.get_export_statistics(filtered_resources),
            'resources': []
        }
        
        # Add resource data
        for resource in filtered_resources:
            resource_data = self.prepare_resource_data(resource)
            export_data['resources'].append(resource_data)
        
        # Write JSON file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)
            
            self.log_export_summary(filtered_resources, output_path)
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to export JSON: {e}")
            raise
    
    def export_individual_descriptions(self, resources: List[ResourceInfo]) -> List[Path]:
        """Export individual resource descriptions as separate JSON files"""
        if not self.config.individual_descriptions:
            return []
        
        descriptions_dir = self.output_dir / "detailed-descriptions"
        descriptions_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"📁 Creating individual JSON descriptions in: {descriptions_dir}")
        
        exported_files = []
        filtered_resources = self.filter_resources(resources)
        
        for resource in filtered_resources:
            if not resource.is_valid():
                continue
            
            # Create safe filename
            safe_identifier = self._make_safe_filename(resource.identifier)
            filename = f"{resource.service}_{resource.resource_type.split('::')[-1]}_{safe_identifier}.json"
            file_path = descriptions_dir / filename
            
            try:
                resource_data = {
                    'metadata': {
                        'export_format': 'json_individual',
                        'timestamp': datetime.now().isoformat(),
                        'resource_type': resource.resource_type,
                        'service': resource.service,
                        'region': resource.region
                    },
                    'resource': self.prepare_resource_data(resource)
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(resource_data, f, indent=2, default=str, ensure_ascii=False)
                
                exported_files.append(file_path)
                
            except Exception as e:
                self.logger.warning(f"Failed to export individual description for {resource.identifier}: {e}")
        
        self.logger.info(f"✓ Created {len(exported_files)} individual JSON descriptions")
        return exported_files
    
    def _make_safe_filename(self, identifier: str) -> str:
        """Make a safe filename from resource identifier"""
        # Replace unsafe characters
        safe = identifier.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe = safe.replace('<', '_').replace('>', '_').replace('|', '_')
        safe = safe.replace('*', '_').replace('?', '_').replace('"', '_')
        
        # Limit length
        if len(safe) > 100:
            safe = safe[:97] + "..."
        
        return safe
    
    def create_resource_summary(self, resources: List[ResourceInfo]) -> Path:
        """Create a summary JSON file with statistics"""
        summary_filename = self.get_output_filename("summary")
        summary_path = self.get_output_path(summary_filename)
        
        filtered_resources = self.filter_resources(resources)
        stats = self.get_export_statistics(filtered_resources)
        
        summary_data = {
            'metadata': {
                'export_format': 'json_summary',
                'timestamp': datetime.now().isoformat(),
                'region': self.config.region,
                'service_filter': self.config.service_filter
            },
            'discovery_statistics': stats,
            'resource_types': {},
            'services': {}
        }
        
        # Group by resource type
        for resource in filtered_resources:
            rt = resource.resource_type
            if rt not in summary_data['resource_types']:
                summary_data['resource_types'][rt] = {
                    'count': 0,
                    'service': resource.service,
                    'sample_resources': []
                }
            
            summary_data['resource_types'][rt]['count'] += 1
            
            # Add sample resource (limit to 3 samples per type)
            samples = summary_data['resource_types'][rt]['sample_resources']
            if len(samples) < 3:
                samples.append({
                    'identifier': resource.identifier,
                    'arn': resource.arn,
                    'region': resource.region
                })
        
        # Group by service
        for service, count in stats['services'].items():
            resource_types = [rt for rt, data in summary_data['resource_types'].items() 
                            if data['service'] == service]
            
            summary_data['services'][service] = {
                'total_resources': count,
                'resource_types': resource_types,
                'resource_type_count': len(resource_types)
            }
        
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, default=str, ensure_ascii=False)
            
            self.logger.info(f"📊 Created JSON summary: {summary_path}")
            return summary_path
            
        except Exception as e:
            self.logger.error(f"Failed to create JSON summary: {e}")
            raise