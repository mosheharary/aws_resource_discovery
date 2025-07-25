# AWS Comprehensive Resource Discovery Tool - Modular Architecture

A powerful, **modular** tool for discovering and cataloging ALL AWS resources across 600+ resource types using AWS Cloud Control API. Redesigned with object-oriented architecture for easy service management and debugging. Features parallel processing, Neo4j graph database integration, and **Claude Desktop integration through Neo4j MCP Server** for natural language querying of your AWS infrastructure.

## 🚀 **Featured Integration: Claude Desktop + Neo4j MCP Server**

**Query your AWS infrastructure using natural language through Claude Desktop!**

This tool's unique integration with [Neo4j MCP Server](https://github.com/neo4j-contrib/mcp-neo4j) allows you to:
- Ask questions about your AWS resources in plain English
- Discover cross-account connections and relationships
- Analyze infrastructure patterns and dependencies
- Get instant insights without writing complex queries

**Example queries you can ask Claude:**
- *"Show me all EC2 instances in my production account"*
- *"Find cross-account connections via Transit Gateway"*
- *"What S3 buckets have logging enabled?"*
- *"Which resources reference this specific VPC?"*

➡️ **[Setup Claude Desktop Integration](#neo4j-mcp-server-integration)** ⬅️

## Overview

This tool discovers AWS resources at scale using:
- **AWS Cloud Control API**: Primary discovery mechanism for modern AWS resources
- **Service-specific APIs**: Enhanced details for EC2, S3, Lambda, RDS, and other services
- **Neo4j Graph Database**: Stores discovered resources with relationships and cross-account connectivity mapping
- **Web Interface**: User-friendly form for configuration and real-time progress monitoring

## 🏗️ **New Modular Architecture**

### **Object-Oriented Design Benefits**
- ✅ **Easy Service Management**: Add/remove AWS services with simple class registration
- ✅ **Debug-Friendly**: Individual service logging and error handling  
- ✅ **Maintainable**: Clear separation of concerns and single responsibility
- ✅ **Extensible**: Simple registration pattern for new services
- ✅ **Testable**: Each component can be individually tested

### Core Components

1. **main.py**: CLI entry point with comprehensive argument handling
   - Enhanced command-line interface with validation
   - Service registry integration
   - Configuration management

2. **core/**: Foundation modules
   - `discovery_engine.py`: Main orchestration engine
   - `base_service.py`: Abstract base class for all AWS services
   - `resource_info.py`: Resource data model with validation
   - `config.py`: Configuration management with .env integration

3. **services/**: Modular AWS service implementations
   - `service_registry.py`: Service registration and factory pattern
   - `ec2_service.py`: EC2-specific discovery (80+ resource types)
   - `s3_service.py`: S3-specific discovery (22+ resource types) 
   - `iam_service.py`: IAM-specific discovery (15+ resource types)
   - `general_aws_service.py`: All remaining 600+ resource types

4. **graph/**: Neo4j database operations
   - `neo4j_client.py`: Connection management and graph operations

5. **exporters/**: Modular export system
   - `base_exporter.py`: Abstract exporter pattern
   - `json_exporter.py`: JSON export with individual descriptions

6. **utils/**: Shared utilities
   - `logging_setup.py`: Centralized logging with service-specific loggers

7. **server.js**: Express web server (updated for new architecture)
   - HTML form interface for configuration
   - Real-time streaming of discovery progress
   - AWS credential parsing and environment setup
   - Process management and cleanup

### Discovery Process

1. **Service Registration**: Auto-registration of AWS service discovery classes
2. **Resource Type Enumeration**: Each service manages its own resource types
3. **Parallel Discovery**: Configurable worker threads with service-level parallelism
4. **Service-Specific Enhancement**: Individual service implementations with enhanced APIs
5. **Graph Database Population**: Modular Neo4j client with relationship mapping
6. **Cross-Account Analysis**: Automated detection of multi-account connectivity
7. **Modular Export**: Pluggable export system with multiple format support

## AWS APIs Used

### Primary Discovery APIs

- **Cloud Control API**: `list_resources()` and `get_resource()` for all resource types
- **Resource Groups Tagging API**: Additional resource metadata and tags

### Service-Specific APIs

- **EC2**: Instances, Volumes, Snapshots, Security Groups, VPCs, Subnets
- **S3**: Buckets, Objects, Policies, Lifecycle configurations
- **Lambda**: Functions, Layers, Event mappings, Aliases
- **RDS**: Instances, Clusters, Snapshots, Parameter groups
- **ElastiCache**: Clusters, Nodes, Replication groups
- **API Gateway**: APIs, Stages, Resources, Methods
- **Transit Gateway**: Attachments, Route tables, Cross-account connections
- **VPC Peering**: Cross-account peering relationships

## Neo4j Graph Structure

### Node Types

#### Account Node
```cypher
(:Account {
  id: "123456789012",
  name: "Production-Account"
})
```

#### Resource Nodes
```cypher
(:EC2Instance {
  resource_type: "AWS::EC2::Instance",
  identifier: "i-1234567890abcdef0",
  arn: "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
  account_id: "123456789012",
  region: "us-east-1",
  // Flattened resource properties...
})
```

#### Enhanced Sub-Component Nodes
- **Route Rules**: Individual routes in route tables
- **RDS Components**: Cluster members, snapshots, parameter groups
- **ElastiCache Components**: Cache nodes, node groups, members
- **API Gateway Components**: Stages, resources, methods, routes
- **Amazon MQ Components**: Broker instances, users, configurations

### Relationship Types

#### Core Relationships
- `(:Account)-[:OWNS]->(:Resource)` - Account ownership
- `(:Resource)-[:LOGS_TO]->(:Resource)` - Logging configurations
- `(:Resource)-[:APPLIES_TO]->(:Resource)` - Policy applications
- `(:Resource)-[:REFERENCES]->(:Resource)` - General references

#### Service-Specific Relationships
- `(:RouteTable)-[:HAS_ROUTE]->(:RouteRule)-[:ROUTES_TO]->(:Target)`
- `(:RDSCluster)-[:HAS_MEMBER]->(:ClusterMember)`
- `(:ElastiCacheCluster)-[:HAS_NODE]->(:CacheNode)`
- `(:APIGateway)-[:HAS_STAGE]->(:Stage)`
- `(:TransitGateway)-[:HAS_ATTACHMENT]->(:Attachment)`

#### Cross-Account Connectivity
- `(:Account)-[:CONNECTED_VIA_TRANSIT_GATEWAY]->(:Account)`
- `(:Account)-[:CONNECTED_VIA_VPC_PEERING]->(:Account)`

### Global vs Regional Services

**Global Services** (no region property):
- IAM, Organizations, Route 53, WAF, WAFv2, Artifacts, Control Tower

**Regional Services** (include region property):
- All other AWS services

## Docker Usage

### Using the Shell Script (Recommended)

The `run-aws-list-resources.sh` script provides an easy way to manage Docker containers with automatic credential handling:

```bash
# Make the script executable
chmod +x run-aws-list-resources.sh

# Run with environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_SESSION_TOKEN="your-session-token"
./run-aws-list-resources.sh -- --region us-east-1

# Or create a .env file with your credentials
cat > .env << EOF
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_SESSION_TOKEN=your-session-token
AWS_DEFAULT_REGION=us-east-1
EOF

# Run the script (it will automatically load .env)
./run-aws-list-resources.sh -- --region us-east-1 --filter ec2

# Show help for available options
./run-aws-list-resources.sh --help
```

### Shell Script Features

- **Automatic .env Loading**: Loads AWS credentials from `.env` file if present
- **Credential Validation**: Verifies AWS credentials before running using `aws sts get-caller-identity`
- **Docker Management**: Automatically builds image if needed
- **Results Directory**: Creates and mounts `./results` directory for output
- **Error Handling**: Comprehensive error checking and user feedback
- **Colored Output**: Enhanced terminal output with info, success, warning, and error indicators
- **Account Identity Verification**: Shows AWS account ID and user/role ARN before execution
- **Security**: Supports both permanent and temporary credentials (session tokens)
- **Cross-Platform**: Works on macOS, Linux, and Windows with WSL

### Manual Docker Usage

```bash
# Build the Docker image
docker build -t aws-discovery .

# Run the container
docker run -p 3000:3000 aws-discovery
```

### Environment Variables

```bash
# Optional: Set custom port
docker run -p 8080:8080 -e PORT=8080 aws-discovery
```

### Docker Compose (with Neo4j) - Recommended

Use the Docker Compose management script for the easiest setup:

```bash
# Make the script executable
chmod +x run-docker-compose.sh

# Create .env file with AWS credentials
cat > .env << EOF
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_SESSION_TOKEN=your-session-token
AWS_DEFAULT_REGION=us-east-1
EOF

# Start all services (Neo4j + Web Interface)
./run-docker-compose.sh start

# Start with custom Neo4j password
./run-docker-compose.sh start --neo4j-password mypassword

# Access the services
# Neo4j Browser: http://localhost:7474 (neo4j/[your-password])
# Web Interface: http://localhost:3000

# Show service status
./run-docker-compose.sh status

# View logs
./run-docker-compose.sh logs

# Open web interface in browser
./run-docker-compose.sh web

# Open Neo4j browser interface
./run-docker-compose.sh neo4j

# Stop all services
./run-docker-compose.sh stop

# Full cleanup (removes volumes)
./run-docker-compose.sh cleanup
```

#### Docker Compose Script Commands

| Command | Description | Options |
|---------|-------------|---------|
| `start` | Start all services (build if needed) | `--neo4j-password PASSWORD` |
| `stop` | Stop all services | - |
| `restart` | Restart all services | `--neo4j-password PASSWORD` |
| `build` | Build/rebuild the AWS discovery image | - |
| `status` | Show status of all services | - |
| `logs` | Show logs for all services | - |
| `cleanup` | Stop services and remove volumes/networks | - |
| `shell` | Open shell in aws-discovery container | - |
| `neo4j` | Open Neo4j browser | - |
| `web` | Open web interface browser | - |
| `help` | Show help message | - |

**Advanced Usage Examples:**
```bash
# Start with custom Neo4j password
./run-docker-compose.sh start --neo4j-password mypassword

# Restart with custom password
./run-docker-compose.sh restart --neo4j-password secret123

# Quick browser access
./run-docker-compose.sh web        # Opens web interface
./run-docker-compose.sh neo4j      # Opens Neo4j browser

# Development workflow
./run-docker-compose.sh build      # Rebuild image
./run-docker-compose.sh status     # Check service status
./run-docker-compose.sh logs       # View service logs
./run-docker-compose.sh shell      # Access container shell
```

#### Manual Docker Compose

```yaml
version: '3.8'
services:
  neo4j:
    image: neo4j:5.15
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/password
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data

  aws-discovery-web:
    build: .
    ports:
      - "3000:3000"
    volumes:
      - ./results:/app/results
      # Note: .env file is NOT mounted - credentials come from web interface
    depends_on:
      - neo4j

volumes:
  neo4j_data:
```

**Important Changes:**
- **No .env File Mount**: The `.env` file is only used for standalone Python execution, not in containers
- **Web-Based Credentials**: All AWS credentials are passed through the web interface
- **Container Isolation**: Enhanced security by not mounting credential files into containers

## 🎯 Neo4j MCP Server Integration

**🌟 FEATURED CAPABILITY: Ask Claude Desktop about your AWS infrastructure in natural language!**

This project's most powerful feature is its integration with Claude Desktop through the Neo4j MCP server, enabling interactive querying of discovered AWS resources using natural language. Transform your AWS resource graph into an intelligent, conversational interface.

### Setup Neo4j MCP Server

1. **Install the Neo4j MCP Server**:
   ```bash
   # Clone the Neo4j MCP server repository
   git clone https://github.com/neo4j-contrib/mcp-neo4j.git
   cd mcp-neo4j/servers/mcp-neo4j-cypher
   
   # Install dependencies
   npm install
   
   # Build the server
   npm run build
   ```

2. **Configure Claude Desktop**:
   
   Add the following configuration to your Claude Desktop config file:
   
   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   
   ```json
   {
     "mcpServers": {
       "neo4j": {
         "command": "node",
         "args": ["/path/to/mcp-neo4j/servers/mcp-neo4j-cypher/build/server.js"],
         "env": {
           "NEO4J_URI": "bolt://localhost:7687",
           "NEO4J_USERNAME": "neo4j",
           "NEO4J_PASSWORD": "password"
         }
       }
     }
   }
   ```

3. **Restart Claude Desktop** to load the MCP server

### 💬 Using Claude Desktop with Neo4j

Once configured, you can interact with your AWS resource graph directly through Claude Desktop using natural language:

#### 🔍 **Real-World Query Examples:**
```
Security & Compliance:
- "Which EC2 instances don't have security groups attached?"
- "Show me all S3 buckets that are publicly accessible"
- "Find resources without proper tagging in my production account"
- "What IAM roles have cross-account trust relationships?"

Infrastructure Analysis:
- "Show me all resources connected to VPC vpc-12345"
- "Find orphaned resources that aren't attached to anything"
- "Which Lambda functions connect to which databases?"
- "Map the data flow from my API Gateway to backend services"

Cost & Resource Management:
- "List all unused EBS volumes"
- "Show me the largest EC2 instances and their utilization data"
- "Find resources in non-standard regions"
- "Which services are consuming the most resources?"

Cross-Account Discovery:
- "Show all cross-account connections via Transit Gateway"
- "Find VPC peering relationships between accounts"
- "Which accounts share resources with production?"
```

#### 🚀 **Advanced Capabilities:**
- **Schema Discovery**: Automatically discovers your graph structure
- **Cypher Generation**: Claude converts natural language to graph queries
- **Interactive Analysis**: Follow relationships and discover connected resources
- **Visual Insights**: Generate architectural diagrams and dependency maps
- **Security Analysis**: Identify potential security risks and compliance gaps

### 🎁 **Benefits of MCP Integration**

✅ **No Query Language Required**: Ask questions in plain English instead of learning Cypher  
✅ **Instant Insights**: Get immediate answers about your infrastructure  
✅ **Relationship Discovery**: Automatically find connections you didn't know existed  
✅ **Cross-Account Visibility**: Easily identify multi-account relationships and security implications  
✅ **Compliance Checking**: Quickly verify security and compliance configurations  
✅ **Cost Optimization**: Identify unused or misconfigured resources  
✅ **Architectural Understanding**: Gain deep insights into your infrastructure patterns

## Installation & Setup

### Prerequisites

1. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Node.js Dependencies**:
   ```bash
   npm install
   ```

3. **Neo4j Database**:
   - Install Neo4j Desktop or use Docker
   - Install APOC plugin for enhanced graph operations
   - Default credentials: `neo4j/password`

### AWS Credentials

Configure AWS credentials using one of these methods:

1. **AWS CLI**:
   ```bash
   aws configure
   ```

2. **Environment Variables**:
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_SESSION_TOKEN="your-session-token"  # Optional
   ```

3. **Environment File**: Create a `.env` file in the project directory (for standalone Python execution only):
   ```bash
   # .env file (not used in Docker containers)
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_SESSION_TOKEN=your-session-token
   AWS_DEFAULT_REGION=us-east-1
   ```

4. **Web Interface**: Paste credentials directly into the web form (supports both formats):
   ```bash
   # Export format
   export AWS_ACCESS_KEY_ID="your-access-key"
   export AWS_SECRET_ACCESS_KEY="your-secret-key"
   export AWS_SESSION_TOKEN="your-session-token"
   
   # Plain format
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_SESSION_TOKEN=your-session-token
   ```

5. **IAM Roles**: When running on EC2 instances

## Recent Improvements & New Features

### 🌐 Web Interface Enhancements
- **✅ No Default Values**: All form fields now require user input for enhanced security
- **✅ Neo4j Connection Testing**: Green "Test Neo4j Connection" button to verify database connectivity before discovery
- **✅ Dual Credential Format Support**: Accepts both `export KEY=value` and `KEY=value` formats seamlessly
- **✅ Enhanced User Experience**: Clear placeholders, improved validation, and better error messages
- **✅ Browser Quick Access**: One-command browser opening for web interface
- **✅ Progress Bar Control**: Automatic disabling of progress bars for web interface using `--no-progress`
- **✅ Fixed Logging Output**: Corrected "ERROR: INFO" issue by directing console logs to stdout

### 🔐 Docker & Container Security
- **✅ Isolated Credential Handling**: `.env` files are not mounted into containers for security
- **✅ Web-Based Configuration**: All AWS credentials passed through secure web interface only
- **✅ Improved Container Architecture**: Enhanced security and isolation between services
- **✅ Configurable Neo4j Password**: Custom Neo4j passwords can be set via command line options
- **✅ Dynamic Password Management**: Environment variable-based password configuration

### 🛠️ Management & Operations
- **✅ Comprehensive Management Script**: Full lifecycle management with `run-docker-compose.sh`
- **✅ Browser Integration**: Quick browser access to both Neo4j and web interfaces via command line
- **✅ Enhanced Shell Scripts**: Updated with better error handling and .env support
- **✅ Cross-Platform Support**: Works on macOS, Linux, and Windows with WSL
- **✅ Service Health Monitoring**: Automatic health checks and status validation
- **✅ AWS Account Verification**: Scripts now display AWS account ID and user/role ARN before execution
- **✅ Colored Terminal Output**: Enhanced scripts with colored info, success, warning, and error messages
- **✅ Improved Docker Script**: `run-aws-list-resources.sh` with comprehensive credential validation and Docker management

### 🚀 Development Workflow
- **✅ Flexible Deployment**: Multiple deployment options (standalone, Docker, Docker Compose)
- **✅ Better Documentation**: Comprehensive README with clear examples and troubleshooting
- **✅ Streamlined Setup**: Simplified configuration and startup process
- **✅ Development Tools**: Container shell access, log viewing, and status monitoring

## Usage Instructions

### Quick Start (Recommended)

1. **Clone and Setup**:
   ```bash
   git clone <repository-url>
   cd aws_resource_discovery
   chmod +x run-docker-compose.sh
   ```

2. **Create credentials file**:
   ```bash
   cat > .env << EOF
   AWS_ACCESS_KEY_ID=your-access-key
   AWS_SECRET_ACCESS_KEY=your-secret-key
   AWS_SESSION_TOKEN=your-session-token
   EOF
   ```

3. **Start services**:
   ```bash
   ./run-docker-compose.sh start
   ```

4. **Access interfaces**:
   ```bash
   ./run-docker-compose.sh web     # Opens web interface
   ./run-docker-compose.sh neo4j   # Opens Neo4j browser
   ```

### Web Interface (Standalone)

1. **Start the server**:
   ```bash
   node server.js
   ```

2. **Open browser**: Navigate to `http://localhost:3000` or use:
   ```bash
   ./run-docker-compose.sh web
   ```

3. **Configure discovery**:
   - **AWS Region**: Target region for discovery (no default value)
   - **AWS Credentials**: Supports both formats:
     - Export format: `export AWS_ACCESS_KEY_ID="key"`
     - Plain format: `AWS_ACCESS_KEY_ID=key`
   - **Account Name**: Friendly name for the account (no default value)
   - **Neo4j Settings**: Database URL and password (no default values)
   - **Workers**: Number of parallel threads (1-50, no default value)
   - **Service Filter**: Optional service filtering (e.g., "ec2", "s3")
   - **Exclude Resource Types**: Optional comma-separated list of AWS resource types to exclude (e.g., "AWS::S3::Bucket, AWS::EC2::Instance")
   - **Reset Graph**: Clear existing data before discovery (unchecked by default)
   - **Individual Descriptions**: Generate detailed resource files (unchecked by default)

4. **Test Neo4j Connection**: Use the green "Test Neo4j Connection" button to verify database connectivity before running discovery

5. **Monitor progress**: Real-time output stream shows discovery progress

### Command Line Interface (New Modular Version)

#### List Available Services
```bash
python main.py --list-services
```

#### Basic Discovery
```bash
python main.py --region us-east-1
```

#### High Performance with Service Filtering
```bash
python main.py \
  --region us-east-1 \
  --max-workers 20 \
  --filter ec2 \
  --individual-descriptions
```

#### Exclude Specific Resource Types
```bash
python main.py \
  --region us-east-1 \
  --exclude "AWS::S3::Bucket" "AWS::EC2::Instance" "AWS::IAM::User"
```

#### Combined Filtering and Exclusion
```bash
python main.py \
  --region us-east-1 \
  --filter lambda \
  --exclude "AWS::Lambda::Version" "AWS::Lambda::Alias" \
  --max-workers 15
```

#### Full Graph Database Integration
```bash
python main.py \
  --region eu-west-1 \
  --update-graph \
  --reset-graph \
  --graph-db-password Mh123456 \
  --account-name "Production-Account" \
  --individual-descriptions
```

#### Multi-format Export (JSON default, others coming soon)
```bash
python main.py \
  --region us-west-2 \
  --profile production \
  --output-formats json
```

#### Service-Specific Discovery
```bash
# Discover only S3 resources
python main.py --region us-east-1 --filter s3

# Discover only IAM resources (global)
python main.py --region us-east-1 --filter iam

# Discover only EC2 resources with enhanced logging
python main.py --region us-east-1 --filter ec2 --log-level DEBUG
```

### Command Line Arguments (New Modular Version)

| Argument | Description | Default |
|----------|-------------|---------|
| `--region` | AWS region for discovery | Required |
| `--profile` | AWS credential profile | Default profile |
| `--max-workers` | Parallel discovery workers | 10 |
| `--filter` | Service filter (e.g., "ec2", "s3", "iam") | None |
| `--exclude` | Exclude specific resource types | None |
| `--individual-descriptions` | Generate detailed files | False |
| `--description-workers` | Parallel description workers | 5 |
| `--output-formats` | Export formats (json, csv, excel, html) | ["json"] |
| `--update-graph` | Update Neo4j database | False |
| `--reset-graph` | Clear graph before update | False |
| `--graph-db-url` | Neo4j connection URL | "localhost:7687" |
| `--graph-db-user` | Neo4j username | "neo4j" |
| `--graph-db-password` | Neo4j password | "Mh123456" |
| `--account-name` | Friendly account name | Auto-generated |
| `--log-level` | Overall logging level | "INFO" |
| `--console-log-level` | Console logging level | "INFO" |
| `--file-log-level` | File logging level | "DEBUG" |
| `--list-services` | List available services and exit | False |

### Available Services (--filter options)

| Service | Description | Resource Types |
|---------|-------------|----------------|
| `ec2` | Amazon EC2 resources | 80+ types (instances, VPCs, subnets, etc.) |
| `s3` | Amazon S3 resources | 22+ types (buckets, access points, etc.) |
| `iam` | AWS IAM resources | 15+ types (roles, users, policies, etc.) |
| `general` | All other AWS services | 600+ types (Lambda, RDS, CloudFormation, etc.) |

### Configuration File for AWS Resource Types

The tool now uses a configuration file approach for managing AWS resource types, making it easier to maintain and customize.

#### Configuration File Location
```
config/aws_resource_types.json
```

#### Configuration File Format
```json
{
  "aws_resource_types": [
    "AWS::EC2::Instance",
    "AWS::S3::Bucket",
    "AWS::Lambda::Function",
    "AWS::RDS::DBInstance",
    "..."
  ]
}
```

#### Benefits of Configuration File Approach
- **Easy Maintenance**: Update resource types without modifying code
- **Customizable**: Add or remove resource types as needed
- **Centralized**: Single source of truth for all AWS resource types
- **Version Control Friendly**: Track changes to resource type lists
- **Fallback Support**: Automatically falls back to minimal list if config file is missing

#### Customizing Resource Types
1. **Edit the configuration file**: Modify `config/aws_resource_types.json`
2. **Add new resource types**: Include newly released AWS resource types
3. **Remove unnecessary types**: Exclude resource types you don't need
4. **Use with --exclude**: Combine with command-line exclusions for fine-grained control

#### Working with Exclusions
The `--exclude` option works in combination with the configuration file:
1. Load all resource types from configuration file
2. Apply service filter if specified (`--filter`)
3. Remove excluded types specified with `--exclude`
4. Proceed with discovery of remaining types

## Output Structure

### Directory Layout
```
aws-discovery-YYYYMMDD-HHMMSS/
├── discovery.log                    # Detailed execution logs
├── resources.json                   # Main resource inventory
├── resources.csv                    # CSV export (if requested)
├── resources.xlsx                   # Excel export (if requested)
├── resources.html                   # HTML report (if requested)
└── detailed-descriptions/           # Individual resource files
    ├── EC2_Instances/
    ├── S3_Buckets/
    ├── Lambda_Functions/
    └── ...
```

### Resource Data Format
```json
{
  "resource_type": "AWS::EC2::Instance",
  "identifier": "i-1234567890abcdef0",
  "arn": "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
  "service": "ec2",
  "region": "us-east-1",
  "properties": {
    "InstanceId": "i-1234567890abcdef0",
    "InstanceType": "t3.micro",
    "State": { "Name": "running" },
    "VpcId": "vpc-12345678",
    "SubnetId": "subnet-12345678"
  }
}
```

## Performance Considerations

### Optimization Settings

- **Max Workers**: 10-20 for most accounts, up to 50 for large accounts
- **Description Workers**: 5-10 parallel workers for detailed descriptions
- **Service Filtering**: Use `--filter` to discover specific services only
- **Region Selection**: Run per region for comprehensive coverage

### Rate Limiting

- AWS API rate limits are automatically handled with exponential backoff
- Cloud Control API has generous rate limits for list operations
- Service-specific APIs may have lower limits (automatically throttled)

### Memory Usage

- Approximately 100MB base memory usage
- Additional ~1MB per 1000 resources discovered
- Neo4j requires minimum 2GB RAM for large datasets

## Troubleshooting

### Common Issues

1. **Missing AWS Credentials**:
   - Verify credentials are properly configured
   - Check AWS CLI with `aws sts get-caller-identity`

2. **Neo4j Connection Errors**:
   - Ensure Neo4j is running on specified URL
   - Verify username/password combination
   - Check firewall settings for port 7687

3. **Rate Limiting**:
   - Reduce `--max-workers` value
   - Add delays between service API calls
   - Use service filtering to reduce API calls

4. **Memory Issues**:
   - Reduce worker count
   - Use service filtering
   - Process regions separately

### Debug Mode (New Modular Version)

Enable detailed logging:
```bash
python main.py --region us-east-1 --log-level DEBUG
```

Service-specific debugging:
```bash
# Debug only EC2 service
python main.py --region us-east-1 --filter ec2 --log-level DEBUG

# Debug with different console and file levels
python main.py --region us-east-1 --console-log-level WARNING --file-log-level DEBUG
```

## 🎯 **Benefits of New Modular Architecture**

### **Easy Service Management**
```python
# Adding a new AWS service is simple:
@register_service
class LambdaService(BaseAWSService):
    def get_service_name(self) -> str:
        return "lambda"
    
    def get_supported_resource_types(self) -> List[str]:
        return ["AWS::Lambda::Function", "AWS::Lambda::Layer"]
    
    def discover_resources(self) -> List[ResourceInfo]:
        # Service-specific implementation
        pass
```

### **Debug-Friendly Design**
- **Individual Service Logging**: Each service has its own logger (`aws_discovery.ec2`, `aws_discovery.s3`, etc.)
- **Service Statistics**: Per-service metrics and performance tracking
- **Error Isolation**: Service failures don't stop other services
- **Skip Pattern Management**: Service-specific resource type skipping

### **Service Registry Pattern**
```bash
# List all registered services
python main.py --list-services

# Output:
# 📋 Registered AWS Services:
#    Total Services: 4
#    Available Services:
#      • ec2
#      • general  
#      • iam
#      • s3
```

### **Extensible Architecture**
- **Plugin System**: New services automatically register with `@register_service` decorator
- **Base Class Benefits**: All services inherit common functionality
- **Configuration Management**: Centralized config with service-specific overrides
- **Export System**: Modular exporters for different output formats

## Example Cypher Queries

### Find All Resources in Account
```cypher
MATCH (a:Account {name: "Production-Account"})-[:OWNS]->(r)
RETURN r.resource_type, count(*) as count
ORDER BY count DESC
```

### Cross-Account Connectivity
```cypher
MATCH (a1:Account)-[r:CONNECTED_VIA_TRANSIT_GATEWAY]->(a2:Account)
RETURN a1.name, a2.name, r.connection_id, r.status
```

### VPC and Subnet Relationships
```cypher
MATCH (vpc)-[:OWNS]->(subnet)
WHERE vpc.resource_type = "AWS::EC2::VPC"
AND subnet.resource_type = "AWS::EC2::Subnet"
RETURN vpc.identifier, collect(subnet.identifier) as subnets
```

### Resource Dependencies
```cypher
MATCH (r1)-[:REFERENCES]->(r2)
WHERE r1.account_id = "123456789012"
RETURN r1.resource_type, r1.identifier, 
       r2.resource_type, r2.identifier
LIMIT 100
```

## Security Considerations

### AWS Permissions

Minimum required IAM permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudcontrol:ListResources",
        "cloudcontrol:GetResource",
        "tag:GetResources",
        "ec2:Describe*",
        "s3:GetBucket*",
        "s3:ListBucket*",
        "lambda:List*",
        "lambda:Get*",
        "rds:Describe*"
      ],
      "Resource": "*"
    }
  ]
}
```

### Credential Handling

- Credentials are passed as environment variables to subprocess
- No credentials are stored in files or database
- Web interface processes credentials in memory only
- Session tokens expire automatically

### Network Security

- Neo4j connection uses standard ports (7687)
- Web interface binds to localhost by default
- Consider VPN or firewall rules for production deployments

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Summary of All Features

### 🌟 **FLAGSHIP FEATURE: Claude Desktop Integration**
- **🎯 Natural Language Queries**: Ask Claude about your AWS infrastructure in plain English
- **🔍 Instant Insights**: Get immediate answers without learning query languages
- **🔗 Relationship Discovery**: Automatically find connections and dependencies
- **🛡️ Security Analysis**: Identify risks and compliance gaps through conversation
- **💰 Cost Optimization**: Discover unused resources and optimization opportunities

### 🔍 **Core Discovery Capabilities**
- **600+ AWS Resource Types**: Comprehensive coverage using AWS Cloud Control API
- **Configurable Resource Types**: JSON configuration file for easy maintenance and customization
- **Resource Exclusion**: Exclude specific resource types from discovery via `--exclude` option
- **Parallel Processing**: Configurable multi-threaded discovery (1-50 workers)
- **Service-Specific APIs**: Enhanced details for 15+ services (EC2, S3, Lambda, RDS, etc.)
- **Cross-Account Analysis**: Automatic detection of multi-account connectivity
- **Multiple Export Formats**: JSON, CSV, Excel, HTML outputs

### 🌐 **Web Interface Features**
- **User-Friendly Configuration**: No default values for security
- **Real-Time Progress**: Live streaming of discovery progress
- **Neo4j Connection Testing**: Verify database connectivity before discovery
- **Flexible Credential Input**: Supports both export and plain key=value formats
- **Browser Integration**: One-click browser access

### 🗄️ **Neo4j Graph Database**
- **Comprehensive Relationships**: 15+ relationship types between resources
- **Cross-Account Connectivity**: Transit Gateway and VPC Peering detection
- **Enhanced Sub-Components**: Detailed nodes for complex services
- **Global vs Regional Services**: Proper handling of IAM, Route53, etc.
- **MCP Server Integration**: Claude Desktop integration for natural language queries

### 🐳 **Docker & Container Support**
- **Docker Compose**: Full-stack deployment with Neo4j
- **Management Scripts**: Comprehensive lifecycle management
- **Security**: Isolated credential handling, no file mounts
- **Health Checks**: Automatic service monitoring
- **Configurable Passwords**: Custom Neo4j passwords

### 🛠️ **Management Tools**
- **Shell Scripts**: `run-aws-list-resources.sh` and `run-docker-compose.sh`
- **Browser Commands**: Quick access to web and Neo4j interfaces
- **Service Management**: Start, stop, restart, build, status, logs
- **Development Tools**: Container shell access, cleanup commands
- **Cross-Platform**: macOS, Linux, Windows WSL support

### 📊 **Output & Analysis**
- **Timestamped Directories**: Organized output with discovery logs
- **Individual Descriptions**: Detailed resource files when requested
- **Search Capabilities**: Post-discovery resource search
- **Performance Metrics**: Statistics and timing information
- **Results Persistence**: Docker volume mapping for output

## Support

For issues and questions:
1. Check existing GitHub issues
2. Review troubleshooting section
3. Create new issue with detailed description
4. Include log files and error messages

---

**Latest Version**: **Completely redesigned with modular object-oriented architecture** for easy service management and debugging. Features **Claude Desktop integration via Neo4j MCP Server** for natural language AWS infrastructure queries, plus web interface improvements, Docker security updates, and comprehensive management scripts.

## 🔄 **Migration from Old to New Architecture**

### **What Changed**
- **Monolithic File**: `aws_discovery_2_neo4j.py` (3,571 lines) → **Modular Architecture**: Multiple focused modules
- **Single Class**: One massive class → **Service-Based Classes**: Individual service implementations
- **Hard to Debug**: Single error log → **Service-Specific Logging**: Per-service debug capabilities
- **Hard to Extend**: Modify one large file → **Plugin System**: Simple service registration

### **Backward Compatibility**
- ✅ **Same Output**: Identical JSON structure and Neo4j schema
- ✅ **Same Web Interface**: UI unchanged, backend points to new `main.py`
- ✅ **Same Docker Support**: Updated Dockerfile and docker-compose.yml
- ✅ **Same CLI Arguments**: Most arguments preserved with enhancements

### **Migration Commands**
```bash
# Old command
python aws_discovery_2_neo4j.py --region us-east-1 --update-graph

# New equivalent command  
python main.py --region us-east-1 --update-graph

# List available services (new feature)
python main.py --list-services

# Service-specific discovery (enhanced)
python main.py --region us-east-1 --filter ec2 --log-level DEBUG
```

**Quick Commands Reference**:
```bash
# Docker Compose (Recommended)
./run-docker-compose.sh start --neo4j-password mypass
./run-docker-compose.sh web
./run-docker-compose.sh neo4j

# Docker with Shell Script  
./run-aws-list-resources.sh -- --region us-east-1

# Standalone (New Modular Version)
python main.py --region us-east-1 --update-graph
python main.py --list-services
node server.js
```
