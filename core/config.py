"""
Configuration management for AWS Resource Discovery.
"""

import os
from dataclasses import dataclass
from typing import Optional, List
from pathlib import Path
import logging


@dataclass
class DiscoveryConfig:
    """Configuration settings for AWS resource discovery"""
    
    # AWS Configuration
    region: str
    profile: Optional[str] = None
    
    # Discovery Settings
    max_workers: int = 10
    description_workers: int = 5
    individual_descriptions: bool = False
    service_filter: Optional[str] = None
    exclude_resources: Optional[List[str]] = None
    
    # Output Settings
    output_formats: List[str] = None
    output_dir: Optional[str] = None
    
    # Neo4j Configuration
    update_graph: bool = False
    reset_graph: bool = False
    graph_db_url: str = "localhost:7687"
    graph_db_user: str = "neo4j"
    graph_db_password: str = "Mh123456"
    account_name: Optional[str] = None
    
    # Logging Configuration
    log_level: str = "INFO"
    console_log_level: str = "INFO"
    file_log_level: str = "DEBUG"
    
    def __post_init__(self):
        """Initialize default values and validate configuration"""
        if self.output_formats is None:
            self.output_formats = ["json"]
        
        # Load environment variables if they exist
        self._load_from_env()
        
        # Validate configuration
        self._validate()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # AWS credentials are loaded automatically by boto3
        
        # Neo4j settings from environment
        if os.getenv('NEO4J_URL'):
            self.graph_db_url = os.getenv('NEO4J_URL')
        if os.getenv('NEO4J_USER'):
            self.graph_db_user = os.getenv('NEO4J_USER')
        if os.getenv('NEO4J_PASSWORD'):
            self.graph_db_password = os.getenv('NEO4J_PASSWORD')
        
        # Logging level from environment
        if os.getenv('LOG_LEVEL'):
            self.log_level = os.getenv('LOG_LEVEL').upper()
    
    def _validate(self):
        """Validate configuration settings"""
        valid_formats = {'json', 'csv', 'excel', 'html'}
        for fmt in self.output_formats:
            if fmt not in valid_formats:
                raise ValueError(f"Invalid output format: {fmt}. Valid formats: {valid_formats}")
        
        valid_log_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if self.log_level not in valid_log_levels:
            raise ValueError(f"Invalid log level: {self.log_level}. Valid levels: {valid_log_levels}")
    
    def get_log_level(self) -> int:
        """Get numeric log level for logging module"""
        return getattr(logging, self.log_level)
    
    def get_console_log_level(self) -> int:
        """Get numeric console log level"""
        return getattr(logging, self.console_log_level)
    
    def get_file_log_level(self) -> int:
        """Get numeric file log level"""
        return getattr(logging, self.file_log_level)
    
    def should_export_format(self, format_name: str) -> bool:
        """Check if a specific format should be exported"""
        return format_name in self.output_formats
    
    def get_output_path(self) -> Path:
        """Get the output directory path"""
        if self.output_dir:
            return Path(self.output_dir)
        
        from datetime import datetime
        return Path(f"aws-discovery-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    
    def is_neo4j_enabled(self) -> bool:
        """Check if Neo4j integration is enabled"""
        return self.update_graph
    
    def get_neo4j_uri(self) -> str:
        """Get Neo4j connection URI"""
        if not self.graph_db_url.startswith(('bolt://', 'neo4j://')):
            return f"bolt://{self.graph_db_url}"
        return self.graph_db_url