#!/bin/bash

# AWS Discovery Docker Compose Management Script
# This script manages the AWS Discovery tool with Neo4j using Docker Compose

set -e  # Exit on any error

# Configuration
COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="aws-discovery"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 {start|stop|restart|build|status|logs|cleanup|shell|neo4j|web|help} [options]"
    echo ""
    echo "AWS Discovery Docker Compose Management Script"
    echo ""
    echo "Commands:"
    echo "  start [--neo4j-password PASSWORD]  - Start all services (build if needed)"
    echo "  stop                               - Stop all services"
    echo "  restart [--neo4j-password PASSWORD] - Restart all services"
    echo "  build                              - Build/rebuild the AWS discovery image"
    echo "  status                             - Show status of all services"
    echo "  logs                               - Show logs for all services"
    echo "  cleanup                            - Stop services and remove volumes/networks"
    echo "  shell                              - Open shell in aws-discovery container"
    echo "  neo4j                              - Open Neo4j browser (requires services to be running)"
    echo "  web                                - Open web interface browser (requires services to be running)"
    echo "  help                               - Show this help message"
    echo ""
    echo "Options:"
    echo "  --neo4j-password PASSWORD         - Set custom Neo4j password (default: password)"
    echo ""
    echo "Examples:"
    echo "  $0 start                           - Start with default Neo4j password"
    echo "  $0 start --neo4j-password mypass   - Start with custom Neo4j password"
    echo "  $0 restart --neo4j-password secret - Restart with custom password"
    echo ""
    echo "Environment Setup:"
    echo "  Create a .env file with your AWS credentials:"
    echo "  AWS_ACCESS_KEY_ID=your-access-key"
    echo "  AWS_SECRET_ACCESS_KEY=your-secret-key"
    echo "  AWS_SESSION_TOKEN=your-session-token"
    echo ""
    echo "Services:"
    echo "  - Neo4j Database: http://localhost:7474 (neo4j/[password])"
    echo "  - Web Interface: http://localhost:3000"
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        print_info "Please install Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        print_error "Docker Compose is not installed or not in PATH"
        print_info "Please install Docker Compose: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        print_info "Please start Docker service"
        exit 1
    fi
    
    # Check if compose file exists
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        print_error "Docker compose file not found: $COMPOSE_FILE"
        print_info "Please ensure you're running this script from the project directory"
        exit 1
    fi
}

# Function to detect Docker Compose command
get_compose_cmd() {
    if docker compose version &> /dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose &> /dev/null; then
        echo "docker-compose"
    else
        print_error "Neither 'docker compose' nor 'docker-compose' is available"
        exit 1
    fi
}

# Function to check if .env file exists
check_env_file() {
    if [[ ! -f ".env" ]]; then
        print_warning "No .env file found"
        print_info "Create a .env file with your AWS credentials:"
        echo "  AWS_ACCESS_KEY_ID=your-access-key"
        echo "  AWS_SECRET_ACCESS_KEY=your-secret-key" 
        echo "  AWS_SESSION_TOKEN=your-session-token"
        echo ""
        read -p "Do you want to continue without .env file? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "Found .env file"
    fi
}

# Function to create results directory
create_results_dir() {
    if [[ ! -d "results" ]]; then
        mkdir -p results
        print_info "Created results directory"
    fi
}

# Function to start services
start_services() {
    local compose_cmd=$(get_compose_cmd)
    local neo4j_password="${1:-password}"  # Default to 'password' if not provided
    
    print_info "Starting AWS Discovery services..."
    check_env_file
    create_results_dir
    
    # Set Neo4j password as environment variable for docker-compose
    export NEO4J_PASSWORD="$neo4j_password"
    
    print_info "Using Neo4j password: $neo4j_password"
    $compose_cmd -p "$PROJECT_NAME" up -d --build
    
    print_success "Services started successfully!"
    print_info "Neo4j Browser: http://localhost:7474 (neo4j/$neo4j_password)"
    print_info "Web Interface: http://localhost:3000"
    print_info "Results will be saved to: $(pwd)/results"
    
    # Wait a moment and show status
    sleep 3
    show_status
}

# Function to stop services
stop_services() {
    local compose_cmd=$(get_compose_cmd)
    
    print_info "Stopping AWS Discovery services..."
    $compose_cmd -p "$PROJECT_NAME" down
    print_success "Services stopped successfully!"
}

# Function to restart services
restart_services() {
    local neo4j_password="${1:-password}"  # Default to 'password' if not provided
    
    print_info "Restarting AWS Discovery services..."
    stop_services
    start_services "$neo4j_password"
}

# Function to build images
build_images() {
    local compose_cmd=$(get_compose_cmd)
    
    print_info "Building AWS Discovery Docker image..."
    $compose_cmd -p "$PROJECT_NAME" build --no-cache
    print_success "Image built successfully!"
}

# Function to show status
show_status() {
    local compose_cmd=$(get_compose_cmd)
    
    print_info "Service Status:"
    $compose_cmd -p "$PROJECT_NAME" ps
    
    # Check if services are healthy
    if $compose_cmd -p "$PROJECT_NAME" ps | grep -q "Up"; then
        print_success "Services are running"
        
        # Show URLs if services are up
        if $compose_cmd -p "$PROJECT_NAME" ps | grep -q "neo4j.*Up"; then
            print_info "Neo4j Browser: http://localhost:7474"
        fi
        
        if $compose_cmd -p "$PROJECT_NAME" ps | grep -q "aws-discovery-web.*Up"; then
            print_info "Web Interface: http://localhost:3000"
        fi
    fi
}

# Function to show logs
show_logs() {
    local compose_cmd=$(get_compose_cmd)
    
    print_info "Showing logs for all services..."
    $compose_cmd -p "$PROJECT_NAME" logs -f
}

# Function to cleanup everything
cleanup_services() {
    local compose_cmd=$(get_compose_cmd)
    
    print_warning "This will stop all services and remove volumes/networks"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cleaning up AWS Discovery environment..."
        $compose_cmd -p "$PROJECT_NAME" down -v --remove-orphans
        
        # Remove dangling images
        docker image prune -f
        
        print_success "Cleanup completed!"
    else
        print_info "Cleanup cancelled"
    fi
}

# Function to open shell in container
open_shell() {
    local compose_cmd=$(get_compose_cmd)
    
    # Check if container is running
    if ! $compose_cmd -p "$PROJECT_NAME" ps | grep -q "aws-discovery-web.*Up"; then
        print_error "AWS Discovery container is not running"
        print_info "Start the services first with: $0 start"
        exit 1
    fi
    
    print_info "Opening shell in AWS Discovery container..."
    $compose_cmd -p "$PROJECT_NAME" exec aws-discovery-web /bin/bash
}

# Function to open Neo4j browser
open_neo4j() {
    # Check if Neo4j is running
    local compose_cmd=$(get_compose_cmd)
    if ! $compose_cmd -p "$PROJECT_NAME" ps | grep -q "neo4j.*Up"; then
        print_error "Neo4j container is not running"
        print_info "Start the services first with: $0 start"
        exit 1
    fi
    
    print_info "Opening Neo4j Browser..."
    print_info "URL: http://localhost:7474"
    print_info "Username: neo4j"
    print_info "Password: password"
    
    # Try to open browser (macOS/Linux)
    if command -v open &> /dev/null; then
        open http://localhost:7474
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:7474
    else
        print_info "Please open http://localhost:7474 in your browser"
    fi
}

# Function to open web interface browser
open_web() {
    # Check if web interface is running
    local compose_cmd=$(get_compose_cmd)
    if ! $compose_cmd -p "$PROJECT_NAME" ps | grep -q "aws-discovery-web.*Up"; then
        print_error "Web interface container is not running"
        print_info "Start the services first with: $0 start"
        exit 1
    fi
    
    print_info "Opening Web Interface..."
    print_info "URL: http://localhost:3000"
    
    # Try to open browser (macOS/Linux)
    if command -v open &> /dev/null; then
        open http://localhost:3000
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:3000
    else
        print_info "Please open http://localhost:3000 in your browser"
    fi
}

# Function to parse arguments and extract Neo4j password
parse_arguments() {
    local command="$1"
    shift
    
    neo4j_password="password"  # Default password
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --neo4j-password)
                neo4j_password="$2"
                shift 2
                ;;
            *)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo "$neo4j_password"
}

# Main script execution
main() {
    print_info "AWS Discovery Docker Compose Manager"
    
    # Check prerequisites
    check_prerequisites
    
    local command="${1:-help}"
    shift
    
    case "$command" in
        start)
            local password=$(parse_arguments "start" "$@")
            start_services "$password"
            ;;
        stop)
            stop_services
            ;;
        restart)
            local password=$(parse_arguments "restart" "$@")
            restart_services "$password"
            ;;
        build)
            build_images
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        cleanup)
            cleanup_services
            ;;
        shell)
            open_shell
            ;;
        neo4j)
            open_neo4j
            ;;
        web)
            open_web
            ;;
        help|--help|-h)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"