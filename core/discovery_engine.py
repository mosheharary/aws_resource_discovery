"""
Main discovery engine for AWS resource discovery.
"""

import boto3
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter

from core.config import DiscoveryConfig
from core.resource_info import ResourceInfo
from core.resource_config import initialize_resource_config
from services.service_registry import ServiceFactory
from graph.neo4j_client import Neo4jClient
from exporters.json_exporter import JSONExporter
from utils.logging_setup import setup_logging, TimedLogger, ProgressLogger, log_system_info, log_configuration, configure_third_party_loggers


class DiscoveryEngine:
    """Main engine for AWS resource discovery"""
    
    def __init__(self, config: DiscoveryConfig):
        """Initialize discovery engine with configuration"""
        self.config = config
        self.output_dir = config.get_output_path()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = setup_logging(
            log_level=config.log_level,
            console_level=config.console_log_level,
            file_level=config.file_log_level,
            log_file=self.output_dir / "discovery.log"
        )
        
        # Configure third-party loggers
        configure_third_party_loggers()
        
        # Log system info and configuration
        log_system_info(self.logger)
        log_configuration(self.logger, config)
        
        # Initialize resource configuration
        initialize_resource_config(
            excluded_types=config.exclude_resources
        )
        
        # Initialize AWS session
        self.session = boto3.Session(profile_name=config.profile) if config.profile else boto3.Session()
        self._account_id = None
        
        # Initialize components
        self.service_factory = ServiceFactory(config, self.session)
        self.neo4j_client = None
        
        if config.is_neo4j_enabled():
            self.neo4j_client = Neo4jClient(config)
        
        # Discovery statistics
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_services': 0,
            'successful_services': 0,
            'failed_services': 0,
            'total_resources': 0,
            'valid_resources': 0,
            'resources_with_errors': 0,
            'resources_by_service': Counter(),
            'resources_by_region': Counter(),
            'exported_files': [],
            'errors': []
        }
    
    def discover_all_resources(self) -> List[ResourceInfo]:
        """Discover all AWS resources using registered services"""
        with TimedLogger(self.logger, "AWS Resource Discovery"):
            self.stats['start_time'] = datetime.now()
            
            # Get account ID
            self._get_account_id()
            
            # Setup Neo4j if enabled
            if self.neo4j_client:
                self._setup_neo4j_graph()
            
            # Get services for discovery
            services = self.service_factory.get_services_for_discovery()
            self.stats['total_services'] = len(services)
            
            self.logger.info(f"🔍 Starting discovery with {len(services)} services")
            self.service_factory.log_available_services()
            
            # Discover resources from all services
            all_resources = []
            
            if self.config.max_workers > 1:
                all_resources = self._discover_resources_parallel(services)
            else:
                all_resources = self._discover_resources_sequential(services)
            
            # Update statistics
            self._update_final_statistics(all_resources)
            
            # Export results
            self._export_results(all_resources)
            
            # Update Neo4j if enabled
            if self.neo4j_client and all_resources:
                self._update_neo4j_graph(all_resources)
            
            self.stats['end_time'] = datetime.now()
            self._log_final_statistics()
            
            return all_resources
    
    def _discover_resources_parallel(self, services) -> List[ResourceInfo]:
        """Discover resources using parallel processing"""
        self.logger.info(f"🔄 Using parallel discovery with {self.config.max_workers} workers")
        
        all_resources = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit discovery tasks
            future_to_service = {
                executor.submit(self._discover_service_resources, service): service 
                for service in services
            }
            
            progress = ProgressLogger(self.logger, len(services), "Service Discovery")
            
            # Collect results
            for future in as_completed(future_to_service):
                service = future_to_service[future]
                
                try:
                    resources = future.result()
                    all_resources.extend(resources)
                    self.stats['successful_services'] += 1
                    
                    self.logger.info(f"✓ {service.get_service_name()}: {len(resources)} resources")
                    
                except Exception as e:
                    self.stats['failed_services'] += 1
                    self.stats['errors'].append(f"{service.get_service_name()}: {str(e)}")
                    self.logger.error(f"✗ {service.get_service_name()}: {e}")
                
                progress.update()
        
        return all_resources
    
    def _discover_resources_sequential(self, services) -> List[ResourceInfo]:
        """Discover resources sequentially"""
        self.logger.info("🔄 Using sequential discovery")
        
        all_resources = []
        progress = ProgressLogger(self.logger, len(services), "Service Discovery")
        
        for service in services:
            try:
                resources = self._discover_service_resources(service)
                all_resources.extend(resources)
                self.stats['successful_services'] += 1
                
                self.logger.info(f"✓ {service.get_service_name()}: {len(resources)} resources")
                
            except Exception as e:
                self.stats['failed_services'] += 1
                self.stats['errors'].append(f"{service.get_service_name()}: {str(e)}")
                self.logger.error(f"✗ {service.get_service_name()}: {e}")
            
            progress.update()
        
        return all_resources
    
    def _discover_service_resources(self, service) -> List[ResourceInfo]:
        """Discover resources for a single service"""
        try:
            with TimedLogger(self.logger, f"{service.get_service_name().upper()} Discovery"):
                resources = service.discover_resources()
                
                # Log service statistics
                service.log_statistics()
                
                return resources
                
        except Exception as e:
            self.logger.error(f"Service {service.get_service_name()} discovery failed: {e}")
            raise
    
    def _get_account_id(self) -> str:
        """Get AWS account ID"""
        if self._account_id:
            return self._account_id
        
        try:
            sts_client = self.session.client('sts')
            response = sts_client.get_caller_identity()
            self._account_id = response['Account']
            
            self.logger.info(f"🏢 AWS Account ID: {self._account_id}")
            return self._account_id
            
        except Exception as e:
            self.logger.error(f"Failed to get account ID: {e}")
            self._account_id = "unknown"
            return self._account_id
    
    def _setup_neo4j_graph(self):
        """Setup Neo4j graph database"""
        if not self.neo4j_client:
            return
        
        try:
            with TimedLogger(self.logger, "Neo4j Setup"):
                # Reset graph if requested
                if self.config.reset_graph:
                    self.neo4j_client.reset_graph()
                
                # Create account node
                account_name = self.config.account_name or f"Account-{self._account_id}"
                self.neo4j_client.create_account_node(self._account_id, account_name)
                
        except Exception as e:
            self.logger.error(f"Failed to setup Neo4j graph: {e}")
            # Continue without Neo4j
            self.neo4j_client = None
    
    def _update_neo4j_graph(self, resources: List[ResourceInfo]):
        """Update Neo4j graph with discovered resources"""
        if not self.neo4j_client:
            return
        
        try:
            with TimedLogger(self.logger, "Neo4j Graph Update"):
                # Filter valid resources
                valid_resources = [r for r in resources if r.is_valid()]
                
                self.logger.info(f"📈 Updating Neo4j with {len(valid_resources)} valid resources")
                
                # Add resources to graph
                self.neo4j_client.add_resources_to_graph(valid_resources)
                
                # Log Neo4j statistics
                self.neo4j_client.log_statistics()
                
        except Exception as e:
            self.logger.error(f"Failed to update Neo4j graph: {e}")
    
    def _export_results(self, resources: List[ResourceInfo]):
        """Export discovery results to configured formats"""
        with TimedLogger(self.logger, "Results Export"):
            exporters = self._get_exporters()
            
            for exporter in exporters:
                try:
                    output_path = exporter.export_resources(resources)
                    if output_path:
                        self.stats['exported_files'].append(str(output_path))
                    
                    # Export individual descriptions if configured
                    if hasattr(exporter, 'export_individual_descriptions'):
                        individual_files = exporter.export_individual_descriptions(resources)
                        self.stats['exported_files'].extend([str(f) for f in individual_files])
                    
                except Exception as e:
                    self.logger.error(f"Export failed for {exporter.get_format_name()}: {e}")
                    self.stats['errors'].append(f"Export {exporter.get_format_name()}: {str(e)}")
    
    def _get_exporters(self) -> List:
        """Get configured exporters"""
        exporters = []
        
        # JSON exporter (always included as primary format)
        json_exporter = JSONExporter(self.config, self.output_dir)
        exporters.append(json_exporter)
        
        # TODO: Add other exporters (CSV, Excel, HTML) when implemented
        
        return exporters
    
    def _update_final_statistics(self, resources: List[ResourceInfo]):
        """Update final discovery statistics"""
        self.stats['total_resources'] = len(resources)
        self.stats['valid_resources'] = sum(1 for r in resources if r.is_valid())
        self.stats['resources_with_errors'] = sum(1 for r in resources if r.has_error())
        
        # Count by service and region
        for resource in resources:
            if resource.service:
                self.stats['resources_by_service'][resource.service] += 1
            
            region = resource.region or 'global'
            self.stats['resources_by_region'][region] += 1
    
    def _log_final_statistics(self):
        """Log final discovery statistics"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        self.logger.info("🎉 AWS Resource Discovery Complete!")
        self.logger.info(f"📊 Final Statistics:")
        self.logger.info(f"   Duration: {duration:.2f} seconds")
        self.logger.info(f"   Services: {self.stats['successful_services']}/{self.stats['total_services']}")
        self.logger.info(f"   Total Resources: {self.stats['total_resources']}")
        self.logger.info(f"   Valid Resources: {self.stats['valid_resources']}")
        
        if self.stats['resources_with_errors'] > 0:
            self.logger.warning(f"   Resources with Errors: {self.stats['resources_with_errors']}")
        
        # Log top services
        top_services = self.stats['resources_by_service'].most_common(5)
        if top_services:
            self.logger.info(f"   Top Services: {', '.join([f'{s}({c})' for s, c in top_services])}")
        
        # Log regions
        regions = list(self.stats['resources_by_region'].keys())
        if len(regions) > 1:
            self.logger.info(f"   Regions: {', '.join(regions)}")
        
        # Log exported files
        if self.stats['exported_files']:
            self.logger.info(f"   Exported Files: {len(self.stats['exported_files'])}")
            for file_path in self.stats['exported_files'][:5]:  # Show first 5
                self.logger.info(f"     - {file_path}")
        
        # Log errors if any
        if self.stats['errors']:
            self.logger.warning(f"   Errors Encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:3]:  # Show first 3
                self.logger.warning(f"     - {error}")
    
    def cleanup(self):
        """Cleanup resources and prevent thread leaks"""
        try:
            # Close Neo4j connection
            if self.neo4j_client:
                self.neo4j_client.close()
                self.neo4j_client = None
                
            # Clear statistics and references
            self.stats.clear()
            
            self.logger.debug("✓ Cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get discovery statistics"""
        return self.stats.copy()