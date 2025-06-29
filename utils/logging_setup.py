"""
Centralized logging setup for AWS resource discovery.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_level: str = "INFO",
    console_level: str = "INFO", 
    file_level: str = "DEBUG",
    log_file: Optional[Path] = None,
    logger_name: str = "aws_discovery"
) -> logging.Logger:
    """
    Setup centralized logging for AWS resource discovery.
    
    Args:
        log_level: Overall log level
        console_level: Console output log level
        file_level: File output log level
        log_file: Path to log file (optional)
        logger_name: Name of the logger
    
    Returns:
        Configured logger instance
    """
    
    # Create main logger
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    logger.propagate = False
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log file specified)
    if log_file:
        # Ensure log file directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, file_level.upper()))
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_service_logger(service_name: str, parent_logger: str = "aws_discovery") -> logging.Logger:
    """
    Setup logger for a specific service.
    
    Args:
        service_name: Name of the service (e.g., 'ec2', 's3')
        parent_logger: Parent logger name
    
    Returns:
        Service-specific logger
    """
    logger_name = f"{parent_logger}.{service_name}"
    logger = logging.getLogger(logger_name)
    
    # Inherit from parent logger
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.propagate = True
    
    return logger


def setup_module_logger(module_name: str, parent_logger: str = "aws_discovery") -> logging.Logger:
    """
    Setup logger for a specific module.
    
    Args:
        module_name: Name of the module (e.g., 'neo4j', 'exporter')
        parent_logger: Parent logger name
    
    Returns:
        Module-specific logger
    """
    logger_name = f"{parent_logger}.{module_name}"
    logger = logging.getLogger(logger_name)
    
    # Inherit from parent logger
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.propagate = True
    
    return logger


def log_system_info(logger: logging.Logger):
    """Log system and environment information"""
    import platform
    import boto3
    
    logger.info("🖥️  System Information:")
    logger.info(f"   Platform: {platform.platform()}")
    logger.info(f"   Python: {platform.python_version()}")
    logger.info(f"   Boto3: {boto3.__version__}")


def log_configuration(logger: logging.Logger, config):
    """Log discovery configuration"""
    logger.info("⚙️  Discovery Configuration:")
    logger.info(f"   Region: {config.region}")
    logger.info(f"   Profile: {config.profile or 'default'}")
    logger.info(f"   Max Workers: {config.max_workers}")
    logger.info(f"   Service Filter: {config.service_filter or 'none'}")
    logger.info(f"   Output Formats: {', '.join(config.output_formats)}")
    logger.info(f"   Individual Descriptions: {config.individual_descriptions}")
    
    if config.is_neo4j_enabled():
        logger.info(f"   Neo4j: {config.graph_db_url}")
        logger.info(f"   Reset Graph: {config.reset_graph}")


def configure_third_party_loggers():
    """Configure third-party library loggers to reduce noise"""
    # Reduce boto3/botocore logging
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # Reduce Neo4j driver logging
    logging.getLogger('neo4j').setLevel(logging.WARNING)
    
    # Reduce other noisy loggers
    logging.getLogger('requests').setLevel(logging.WARNING)


class ProgressLogger:
    """Logger for tracking progress of long-running operations"""
    
    def __init__(self, logger: logging.Logger, total_items: int, operation_name: str = "Processing"):
        self.logger = logger
        self.total_items = total_items
        self.operation_name = operation_name
        self.processed_items = 0
        self.last_logged_percentage = 0
    
    def update(self, increment: int = 1):
        """Update progress and log if significant progress made"""
        self.processed_items += increment
        
        if self.total_items > 0:
            percentage = (self.processed_items / self.total_items) * 100
            
            # Log every 10% or at completion
            if (percentage - self.last_logged_percentage >= 10) or self.processed_items == self.total_items:
                self.logger.info(f"📈 {self.operation_name}: {self.processed_items}/{self.total_items} ({percentage:.1f}%)")
                self.last_logged_percentage = percentage
    
    def complete(self):
        """Mark operation as complete"""
        self.logger.info(f"✅ {self.operation_name} complete: {self.processed_items}/{self.total_items}")


class TimedLogger:
    """Logger that tracks timing of operations"""
    
    def __init__(self, logger: logging.Logger, operation_name: str):
        self.logger = logger
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.info(f"🚀 Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        if self.start_time:
            duration = time.time() - self.start_time
            if exc_type is None:
                self.logger.info(f"✅ {self.operation_name} completed in {duration:.2f} seconds")
            else:
                self.logger.error(f"❌ {self.operation_name} failed after {duration:.2f} seconds")
    
    def log_milestone(self, milestone: str):
        """Log a milestone during the operation"""
        import time
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.logger.info(f"📍 {self.operation_name} - {milestone} (elapsed: {elapsed:.2f}s)")