#!/bin/bash

# AWS List Resources Docker Runner Script
# This script validates AWS credentials and runs the aws-list-resources Docker container

set -e  # Exit on any error

# Configuration
DOCKER_IMAGE_NAME="aws-list-resources"
DOCKER_TAG="latest"
FULL_IMAGE_NAME="${DOCKER_IMAGE_NAME}:${DOCKER_TAG}"

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
    echo "Usage: $0 [docker-options] -- [aws-list-resources-options]"
    echo ""
    echo "This script validates AWS credentials and runs the aws-list-resources tool in Docker."
    echo ""
    echo "Examples:"
    echo "  $0 -- --regions us-east-1,eu-central-1"
    echo "  $0 -- --regions ALL --show-stats"
    echo "  $0 -- --regions us-east-1 --include-resource-types 'AWS::EC2::*'"
    echo ""
    echo "Required AWS Environment Variables:"
    echo "  AWS_ACCESS_KEY_ID     - Your AWS access key"
    echo "  AWS_SECRET_ACCESS_KEY - Your AWS secret key"
    echo "  AWS_SESSION_TOKEN     - Your AWS session token (for temporary credentials)"
    echo ""
    echo "Optional AWS Environment Variables:"
    echo "  AWS_DEFAULT_REGION    - Default AWS region"
    echo "  AWS_PROFILE          - AWS profile to use"
    echo ""
    echo "Environment File:"
    echo "  Create a .env file in the current directory with your AWS credentials:"
    echo "  AWS_ACCESS_KEY_ID=your-access-key"
    echo "  AWS_SECRET_ACCESS_KEY=your-secret-key"
    echo "  AWS_SESSION_TOKEN=your-session-token"
    echo ""
}

# Function to load environment variables from .env file
load_env_file() {
    local env_file=".env"
    
    if [[ -f "$env_file" ]]; then
        print_info "Found .env file, loading environment variables..."
        
        # Read the .env file and export variables
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Skip empty lines and comments
            [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
            
            # Export the variable if it's in KEY=VALUE format
            if [[ "$line" =~ ^[[:space:]]*([^=]+)=(.*)$ ]]; then
                local key="${BASH_REMATCH[1]}"
                local value="${BASH_REMATCH[2]}"
                # Remove leading/trailing whitespace from key
                key=$(echo "$key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                # Remove quotes from value if present
                value=$(echo "$value" | sed 's/^["'\'']*//;s/["'\'']*$//')
                export "$key"="$value"
                print_info "Loaded: $key"
            fi
        done < "$env_file"
        
        print_success "Environment variables loaded from .env file"
    else
        print_info "No .env file found, using existing environment variables"
    fi
}

# Function to validate AWS credentials
validate_aws_credentials() {
    print_info "Validating AWS credentials..."
    
    local missing_vars=()
    
    # Check for required AWS credentials
    if [[ -z "${AWS_ACCESS_KEY_ID:-}" ]]; then
        missing_vars+=("AWS_ACCESS_KEY_ID")
    fi
    
    if [[ -z "${AWS_SECRET_ACCESS_KEY:-}" ]]; then
        missing_vars+=("AWS_SECRET_ACCESS_KEY")
    fi
    
    if [[ -z "${AWS_SESSION_TOKEN:-}" ]]; then
        missing_vars+=("AWS_SESSION_TOKEN")
    fi
    
    # If any required variables are missing, show error and exit
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_error "Missing required AWS environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        print_info "Please set these environment variables before running the script:"
        echo "  export AWS_ACCESS_KEY_ID='your-access-key'"
        echo "  export AWS_SECRET_ACCESS_KEY='your-secret-key'"
        echo "  export AWS_SESSION_TOKEN='your-session-token'"
        echo ""
        print_info "For permanent credentials (not recommended for production):"
        echo "  You may omit AWS_SESSION_TOKEN, but this is less secure."
        return 1
    fi
    
    print_success "AWS credentials found and appear to be configured correctly"
    
    # Optional: Show which AWS account we're using (without exposing credentials)
    if command -v aws &> /dev/null; then
        print_info "Checking AWS account identity..."
        local account_info
        if account_info=$(aws sts get-caller-identity 2>/dev/null); then
            local account_id=$(echo "$account_info" | grep -o '"Account": "[^"]*"' | cut -d'"' -f4)
            local user_arn=$(echo "$account_info" | grep -o '"Arn": "[^"]*"' | cut -d'"' -f4)
            print_success "AWS Account ID: $account_id"
            print_success "User/Role ARN: $user_arn"
        else
            print_warning "Could not verify AWS account (aws CLI not available or credentials invalid)"
        fi
    fi
}

# Function to check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        print_info "Please install Docker: https://docs.docker.com/get-docker/"
        return 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        print_info "Please start Docker service"
        return 1
    fi
    
    print_success "Docker is available and running"
}

# Function to build Docker image if it doesn't exist
build_image_if_needed() {
    if docker image inspect "$FULL_IMAGE_NAME" &> /dev/null; then
        print_info "Docker image '$FULL_IMAGE_NAME' already exists"
    else
        print_info "Docker image '$FULL_IMAGE_NAME' not found. Building..."
        
        # Check if Dockerfile exists in current directory
        if [[ ! -f "Dockerfile" ]]; then
            print_error "Dockerfile not found in current directory"
            print_info "Please ensure you're running this script from the aws-list-resources directory"
            return 1
        fi
        
        print_info "Building Docker image..."
        if docker build -t "$FULL_IMAGE_NAME" .; then
            print_success "Docker image built successfully"
        else
            print_error "Failed to build Docker image"
            return 1
        fi
    fi
}

# Function to run the Docker container
run_container() {
    local args="$@"
    
    # Create results directory on host if it doesn't exist
    local host_results_dir="$(pwd)/results"
    mkdir -p "$host_results_dir"
    
    print_info "Running aws-list-resources container..."
    print_info "Results will be saved to: $host_results_dir"
    
    # Prepare environment variables to pass to container
    local env_vars=(
        "-e" "AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}"
        "-e" "AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}"
        "-e" "AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}"
    )
    
    # Add optional AWS environment variables if they exist
    if [[ -n "${AWS_DEFAULT_REGION:-}" ]]; then
        env_vars+=("-e" "AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}")
    fi
    
    if [[ -n "${AWS_PROFILE:-}" ]]; then
        env_vars+=("-e" "AWS_PROFILE=${AWS_PROFILE}")
    fi
    
    # Run the container
    docker run --rm \
        "${env_vars[@]}" \
        -v "$host_results_dir:/app/results" \
        -v "$(pwd):/workspace:ro" \
        "$FULL_IMAGE_NAME" \
        $args
    
    print_success "Container execution completed"
    print_info "Check the results directory for output files: $host_results_dir"
}

# Main script execution
main() {
    print_info "Starting AWS List Resources Docker Runner"
    
    # Show help if requested
    if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
        show_usage
        exit 0
    fi
    
    # Validate prerequisites
    check_docker || exit 1
    load_env_file
    validate_aws_credentials || exit 1
    
    # Build image if needed
    build_image_if_needed || exit 1
    
    # Run the container with all provided arguments
    run_container "$@"
    
    print_success "All done!"
}

# Run main function with all arguments
main "$@"