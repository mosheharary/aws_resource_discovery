#!/usr/bin/env python3
"""
AWS Resource Discovery Tool - Modular Version

Comprehensive AWS resource discovery using Cloud Control API with 
object-oriented architecture for easy service management and debugging.
"""

import argparse
import sys
import os
from pathlib import Path

# Add the current directory to Python path to allow imports
sys.path.insert(0, str(Path(__file__).parent))

from core.config import DiscoveryConfig
from core.discovery_engine import DiscoveryEngine

# Import services to register them
from services.ec2_service import EC2Service
from services.s3_service import S3Service
from services.iam_service import IAMService


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description='Comprehensive AWS Resource Discovery Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic discovery in us-east-1
  python main.py --region us-east-1

  # High performance discovery with filtering
  python main.py --region us-east-1 --max-workers 20 --filter ec2 --individual-descriptions

  # Multi-format export with Neo4j integration
  python main.py --region us-west-2 --output-formats json csv --update-graph

  # Full graph reset with custom account name
  python main.py --region eu-west-1 --update-graph --reset-graph --account-name "Production-Account"

  # Exclude specific resource types from discovery
  python main.py --region us-east-1 --exclude "AWS::S3::Bucket" "AWS::EC2::Instance"

Environment Variables:
  AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN - AWS credentials
  NEO4J_URL, NEO4J_USER, NEO4J_PASSWORD - Neo4j connection details
  LOG_LEVEL - Logging level (DEBUG, INFO, WARNING, ERROR)
        """
    )
    
    # AWS Configuration
    aws_group = parser.add_argument_group('AWS Configuration')
    aws_group.add_argument(
        '--region', 
        help='AWS region to discover resources in (required for discovery operations)'
    )
    aws_group.add_argument(
        '--profile',
        help='AWS profile to use (default: use default profile or environment credentials)'
    )
    
    # Discovery Settings
    discovery_group = parser.add_argument_group('Discovery Settings')
    discovery_group.add_argument(
        '--max-workers',
        type=int,
        default=10,
        help='Maximum number of worker threads for parallel discovery (default: 10)'
    )
    discovery_group.add_argument(
        '--description-workers',
        type=int,
        default=5,
        help='Number of workers for individual resource descriptions (default: 5)'
    )
    discovery_group.add_argument(
        '--individual-descriptions',
        action='store_true',
        help='Create individual description files for each resource'
    )
    discovery_group.add_argument(
        '--filter',
        dest='service_filter',
        help='Filter discovery to specific service (e.g., "ec2", "s3", "iam")'
    )
    discovery_group.add_argument(
        '--exclude',
        nargs='+',
        help='Exclude specific resource types from discovery (e.g., "AWS::S3::Bucket" "AWS::EC2::Instance")'
    )
    
    # Output Settings
    output_group = parser.add_argument_group('Output Settings')
    output_group.add_argument(
        '--output-formats',
        nargs='+',
        choices=['json', 'csv', 'excel', 'html'],
        default=['json'],
        help='Output formats to generate (default: json)'
    )
    output_group.add_argument(
        '--output-dir',
        help='Custom output directory (default: timestamped directory)'
    )
    
    # Neo4j Configuration
    neo4j_group = parser.add_argument_group('Neo4j Graph Database')
    neo4j_group.add_argument(
        '--update-graph',
        action='store_true',
        help='Update Neo4j graph database with discovered resources'
    )
    neo4j_group.add_argument(
        '--reset-graph',
        action='store_true',
        help='Reset the entire graph database before adding resources'
    )
    neo4j_group.add_argument(
        '--graph-db-url',
        default='localhost:7687',
        help='Neo4j database URL (default: localhost:7687)'
    )
    neo4j_group.add_argument(
        '--graph-db-user',
        default='neo4j',
        help='Neo4j username (default: neo4j)'
    )
    neo4j_group.add_argument(
        '--graph-db-password',
        default='Mh123456',
        help='Neo4j password (default: Mh123456)'
    )
    neo4j_group.add_argument(
        '--account-name',
        help='Custom account name for graph database (default: auto-generated)'
    )
    
    # Logging Configuration
    logging_group = parser.add_argument_group('Logging')
    logging_group.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Overall logging level (default: INFO)'
    )
    logging_group.add_argument(
        '--console-log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Console logging level (default: INFO)'
    )
    logging_group.add_argument(
        '--file-log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='DEBUG',
        help='File logging level (default: DEBUG)'
    )
    
    # Utility commands
    parser.add_argument(
        '--list-services',
        action='store_true',
        help='List all registered services and exit'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='AWS Resource Discovery Tool v2.0 (Modular)'
    )
    
    return parser


def validate_arguments(args) -> bool:
    """Validate command line arguments"""
    errors = []
    
    # Skip validation for utility commands
    if args.list_services:
        return True
    
    # Validate required arguments for discovery
    if not args.region:
        errors.append("--region is required for discovery operations")
    
    # Validate workers
    if args.max_workers < 1:
        errors.append("--max-workers must be at least 1")
    
    if args.description_workers < 1:
        errors.append("--description-workers must be at least 1")
    
    # Validate Neo4j settings
    if args.reset_graph and not args.update_graph:
        errors.append("--reset-graph requires --update-graph")
    
    # Validate output directory
    if args.output_dir:
        try:
            Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create output directory {args.output_dir}: {e}")
    
    if errors:
        print("❌ Argument validation errors:")
        for error in errors:
            print(f"   • {error}")
        return False
    
    return True


def list_services():
    """List all registered services"""
    from services.service_registry import get_registry
    
    registry = get_registry()
    services = registry.list_registered_services()
    
    print("📋 Registered AWS Services:")
    print(f"   Total Services: {len(services)}")
    print("   Available Services:")
    
    for service_name in sorted(services):
        print(f"     • {service_name}")
    
    print("\nℹ️  Use --filter <service_name> to discover only specific services")
    print("   Example: --filter ec2")


def main():
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle utility commands
    if args.list_services:
        list_services()
        return 0
    
    # Validate arguments
    if not validate_arguments(args):
        return 1
    
    # Create configuration
    try:
        config = DiscoveryConfig(
            region=args.region,
            profile=args.profile,
            max_workers=args.max_workers,
            description_workers=args.description_workers,
            individual_descriptions=args.individual_descriptions,
            service_filter=args.service_filter,
            exclude_resources=args.exclude,
            output_formats=args.output_formats,
            output_dir=args.output_dir,
            update_graph=args.update_graph,
            reset_graph=args.reset_graph,
            graph_db_url=args.graph_db_url,
            graph_db_user=args.graph_db_user,
            graph_db_password=args.graph_db_password,
            account_name=args.account_name,
            log_level=args.log_level,
            console_log_level=args.console_log_level,
            file_log_level=args.file_log_level
        )
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return 1
    
    # Create and run discovery engine
    discovery_engine = None
    
    try:
        discovery_engine = DiscoveryEngine(config)
        
        print("🚀 Starting AWS Resource Discovery...")
        print(f"   Region: {config.region}")
        print(f"   Service Filter: {config.service_filter or 'All services'}")
        print(f"   Output Directory: {config.get_output_path()}")
        
        if config.is_neo4j_enabled():
            print(f"   Neo4j: {config.get_neo4j_uri()}")
        
        # Discover resources
        resources = discovery_engine.discover_all_resources()
        
        print(f"\n✅ Discovery completed successfully!")
        print(f"   Total Resources: {len(resources)}")
        print(f"   Output Directory: {config.get_output_path()}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  Discovery interrupted by user")
        return 1
        
    except Exception as e:
        print(f"\n❌ Discovery failed: {e}")
        return 1
        
    finally:
        # Cleanup
        if discovery_engine:
            discovery_engine.cleanup()
        
        # Force thread cleanup to prevent Python 3.13 garbage collection warnings
        import threading
        import time
        
        # Give threads a moment to clean up
        time.sleep(0.1)
        
        # Force garbage collection
        import gc
        gc.collect()


if __name__ == "__main__":
    sys.exit(main())