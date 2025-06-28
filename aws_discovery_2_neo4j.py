#!/usr/bin/env python3

import boto3
import json
import argparse
import logging
import csv
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
import re
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import sys
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

# Optional dependencies with graceful fallbacks
try:
    from tqdm import tqdm
    HAS_TQDM_AVAILABLE = True
except ImportError:
    HAS_TQDM_AVAILABLE = False
    print("Install tqdm for progress bars: pip install tqdm")

# This will be set based on command line arguments
HAS_TQDM = HAS_TQDM_AVAILABLE

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Install pandas for Excel export: pip install pandas openpyxl")

# Complete list of AWS resource types supported by Cloud Control API (600+ types)
AWS_RESOURCE_TYPES = [
    "AWS::AutoScaling::LaunchConfiguration",
    "AWS::AutoScaling::LifecycleHook",
    "AWS::AutoScaling::ScalingPolicy",
    "AWS::AutoScaling::ScheduledAction",
    "AWS::AutoScaling::WarmPool",
    "AWS::Backup::BackupPlan",
    "AWS::Backup::BackupSelection",
    "AWS::Backup::BackupVault",
    "AWS::Backup::Framework",
    "AWS::Backup::LogicallyAirGappedBackupVault",
    "AWS::Backup::ReportPlan",
    "AWS::Backup::RestoreTestingPlan",
    "AWS::Backup::RestoreTestingSelection",
    "AWS::BackupGateway::Hypervisor",
    "AWS::Batch::ComputeEnvironment",
    "AWS::Batch::ConsumableResource",
    "AWS::Batch::JobDefinition",
    "AWS::Batch::JobQueue",
    "AWS::Batch::SchedulingPolicy",
    "AWS::Bedrock::Agent",
    "AWS::Bedrock::AgentAlias",
    "AWS::Bedrock::ApplicationInferenceProfile",
    "AWS::Bedrock::DataSource",
    "AWS::Bedrock::Flow",
    "AWS::Bedrock::FlowAlias",
    "AWS::Bedrock::FlowVersion",
    "AWS::Bedrock::Guardrail",
    "AWS::Bedrock::GuardrailVersion",
    "AWS::Bedrock::IntelligentPromptRouter",
    "AWS::Bedrock::KnowledgeBase",
    "AWS::Bedrock::Prompt",
    "AWS::Bedrock::PromptVersion",
    "AWS::Budgets::BudgetsAction",
    "AWS::CE::AnomalyMonitor",
    "AWS::CE::AnomalySubscription",
    "AWS::CE::CostCategory",
    "AWS::Cassandra::Keyspace",
    "AWS::Cassandra::Table",
    "AWS::Cassandra::Type",
    "AWS::CertificateManager::Account",
    "AWS::Chatbot::CustomAction",
    "AWS::Chatbot::MicrosoftTeamsChannelConfiguration",
    "AWS::Chatbot::SlackChannelConfiguration",
    "AWS::CleanRooms::AnalysisTemplate",
    "AWS::CleanRooms::Collaboration",
    "AWS::CleanRooms::ConfiguredTable",
    "AWS::CleanRooms::ConfiguredTableAssociation",
    "AWS::CleanRooms::IdMappingTable",
    "AWS::CleanRooms::IdNamespaceAssociation",
    "AWS::CleanRooms::Membership",
    "AWS::CleanRooms::PrivacyBudgetTemplate",
    "AWS::CleanRoomsML::TrainingDataset",
    "AWS::CloudFormation::GuardHook",
    "AWS::CloudFormation::HookDefaultVersion",
    "AWS::CloudFormation::HookTypeConfig",
    "AWS::CloudFormation::HookVersion",
    "AWS::CloudFormation::LambdaHook",
    "AWS::CloudFormation::ModuleDefaultVersion",
    "AWS::CloudFormation::ModuleVersion",
    "AWS::CloudFormation::PublicTypeVersion",
    "AWS::CloudFormation::Publisher",
    "AWS::CloudFormation::ResourceDefaultVersion",
    "AWS::CloudFormation::ResourceVersion",
    "AWS::CloudFormation::Stack",
    "AWS::CloudFormation::StackSet",
    "AWS::CloudFormation::TypeActivation",
    "AWS::CloudFront::AnycastIpList",
    "AWS::CloudFront::CachePolicy",
    "AWS::CloudFront::CloudFrontOriginAccessIdentity",
    "AWS::CloudFront::ConnectionGroup",
    "AWS::CloudFront::ContinuousDeploymentPolicy",
    "AWS::CloudFront::Distribution",
    "AWS::CloudFront::DistributionTenant",
    "AWS::CloudFront::Function",
    "AWS::CloudFront::KeyGroup",
    "AWS::CloudFront::KeyValueStore",
    "AWS::CloudFront::MonitoringSubscription",
    "AWS::CloudFront::OriginAccessControl",
    "AWS::CloudFront::OriginRequestPolicy",
    "AWS::CloudFront::PublicKey",
    "AWS::CloudFront::RealtimeLogConfig",
    "AWS::CloudFront::ResponseHeadersPolicy",
    "AWS::CloudFront::VpcOrigin",
    "AWS::CloudTrail::Channel",
    "AWS::CloudTrail::Dashboard",
    "AWS::CloudTrail::EventDataStore",
    "AWS::CloudTrail::ResourcePolicy",
    "AWS::CloudTrail::Trail",
    "AWS::CloudWatch::Alarm",
    "AWS::CloudWatch::CompositeAlarm",
    "AWS::CloudWatch::Dashboard",
    "AWS::CloudWatch::MetricStream",
    "AWS::CodeArtifact::Domain",
    "AWS::CodeArtifact::PackageGroup",
    "AWS::CodeArtifact::Repository",
    "AWS::CodeBuild::Fleet",
    "AWS::CodeConnections::Connection",
    "AWS::CodeDeploy::Application",
    "AWS::CodeDeploy::DeploymentConfig",
    "AWS::CodeGuruProfiler::ProfilingGroup",
    "AWS::CodeGuruReviewer::RepositoryAssociation",
    "AWS::CodePipeline::CustomActionType",
    "AWS::CodePipeline::Pipeline",
    "AWS::CodeStarConnections::Connection",
    "AWS::CodeStarConnections::RepositoryLink",
    "AWS::CodeStarConnections::SyncConfiguration",
    "AWS::CodeStarNotifications::NotificationRule",
    "AWS::Cognito::IdentityPool",
    "AWS::Cognito::IdentityPoolPrincipalTag",
    "AWS::Cognito::IdentityPoolRoleAttachment",
    "AWS::Cognito::LogDeliveryConfiguration",
    "AWS::Cognito::ManagedLoginBranding",
    "AWS::Cognito::UserPool",
    "AWS::Cognito::UserPoolClient",
    "AWS::Cognito::UserPoolDomain",
    "AWS::Cognito::UserPoolGroup",
    "AWS::Cognito::UserPoolIdentityProvider",
    "AWS::Cognito::UserPoolResourceServer",
    "AWS::Cognito::UserPoolRiskConfigurationAttachment",
    "AWS::Cognito::UserPoolUICustomizationAttachment",
    "AWS::Cognito::UserPoolUser",
    "AWS::Cognito::UserPoolUserToGroupAttachment",
    "AWS::Comprehend::DocumentClassifier",
    "AWS::Comprehend::Flywheel",
    "AWS::Config::AggregationAuthorization",
    "AWS::Config::ConfigRule",
    "AWS::Config::ConfigurationAggregator",
    "AWS::Config::ConformancePack",
    "AWS::Config::OrganizationConformancePack",
    "AWS::Config::StoredQuery",
    "AWS::ControlTower::EnabledBaseline",
    "AWS::ControlTower::EnabledControl",
    "AWS::ControlTower::LandingZone",
    "AWS::DMS::DataMigration",
    "AWS::DMS::DataProvider",
    "AWS::DMS::InstanceProfile",
    "AWS::DMS::MigrationProject",
    "AWS::DMS::ReplicationConfig",
    "AWS::DSQL::Cluster",
    "AWS::DataBrew::Dataset",
    "AWS::DataBrew::Job",
    "AWS::DataBrew::Project",
    "AWS::DataBrew::Recipe",
    "AWS::DataBrew::Ruleset",
    "AWS::DataBrew::Schedule",
    "AWS::DataPipeline::Pipeline",
    "AWS::DataSync::Agent",
    "AWS::DataSync::LocationAzureBlob",
    "AWS::DataSync::LocationEFS",
    "AWS::DataSync::LocationFSxLustre",
    "AWS::DataSync::LocationFSxONTAP",
    "AWS::DataSync::LocationFSxOpenZFS",
    "AWS::DataSync::LocationFSxWindows",
    "AWS::DataSync::LocationHDFS",
    "AWS::DataSync::LocationNFS",
    "AWS::DataSync::LocationObjectStorage",
    "AWS::DataSync::LocationS3",
    "AWS::DataSync::LocationSMB",
    "AWS::DataSync::Task",
    "AWS::DataZone::Connection",
    "AWS::DataZone::DataSource",
    "AWS::DataZone::Domain",
    "AWS::DataZone::DomainUnit",
    "AWS::DataZone::Environment",
    "AWS::DataZone::EnvironmentActions",
    "AWS::DataZone::EnvironmentBlueprintConfiguration",
    "AWS::DataZone::EnvironmentProfile",
    "AWS::DataZone::GroupProfile",
    "AWS::DataZone::Owner",
    "AWS::DataZone::Project",
    "AWS::DataZone::ProjectMembership",
    "AWS::DataZone::ProjectProfile",
    "AWS::DataZone::SubscriptionTarget",
    "AWS::DataZone::UserProfile",
    "AWS::Deadline::Farm",
    "AWS::Deadline::Fleet",
    "AWS::Deadline::LicenseEndpoint",
    "AWS::Deadline::Limit",
    "AWS::Deadline::MeteredProduct",
    "AWS::Deadline::Monitor",
    "AWS::Deadline::Queue",
    "AWS::Deadline::QueueEnvironment",
    "AWS::Deadline::QueueFleetAssociation",
    "AWS::Deadline::QueueLimitAssociation",
    "AWS::Deadline::StorageProfile",
    "AWS::Detective::Graph",
    "AWS::Detective::MemberInvitation",
    "AWS::Detective::OrganizationAdmin",
    "AWS::DevOpsGuru::LogAnomalyDetectionIntegration",
    "AWS::DevOpsGuru::NotificationChannel",
    "AWS::DevOpsGuru::ResourceCollection",
    "AWS::DirectoryService::SimpleAD",
    "AWS::DocDBElastic::Cluster",
    "AWS::DynamoDB::GlobalTable",
    "AWS::DynamoDB::Table",
    "AWS::EC2::CapacityReservation",
    "AWS::EC2::CapacityReservationFleet",
    "AWS::EC2::CarrierGateway",
    "AWS::EC2::CustomerGateway",
    "AWS::EC2::DHCPOptions",
    "AWS::EC2::EC2Fleet",
    "AWS::EC2::EIP",
    "AWS::EC2::EIPAssociation",
    "AWS::EC2::EgressOnlyInternetGateway",
    "AWS::EC2::EnclaveCertificateIamRoleAssociation",
    "AWS::EC2::FlowLog",
    "AWS::EC2::GatewayRouteTableAssociation",
    "AWS::EC2::Host",
    "AWS::EC2::IPAM",
    "AWS::EC2::IPAMAllocation",
    "AWS::EC2::IPAMPool",
    "AWS::EC2::IPAMPoolCidr",
    "AWS::EC2::IPAMResourceDiscovery",
    "AWS::EC2::IPAMResourceDiscoveryAssociation",
    "AWS::EC2::IPAMScope",
    "AWS::EC2::Instance",
    "AWS::EC2::InstanceConnectEndpoint",
    "AWS::EC2::InternetGateway",
    "AWS::EC2::KeyPair",
    "AWS::EC2::LaunchTemplate",
    "AWS::EC2::LocalGatewayRoute",
    "AWS::EC2::LocalGatewayRouteTable",
    "AWS::EC2::LocalGatewayRouteTableVPCAssociation",
    "AWS::EC2::LocalGatewayRouteTableVirtualInterfaceGroupAssociation",
    "AWS::EC2::NatGateway",
    "AWS::EC2::NetworkAcl",
    "AWS::EC2::NetworkInsightsAccessScope",
    "AWS::EC2::NetworkInsightsAccessScopeAnalysis",
    "AWS::EC2::NetworkInsightsAnalysis",
    "AWS::EC2::NetworkInsightsPath",
    "AWS::EC2::NetworkInterface",
    "AWS::EC2::NetworkInterfaceAttachment",
    "AWS::EC2::NetworkPerformanceMetricSubscription",
    "AWS::EC2::PlacementGroup",
    "AWS::EC2::PrefixList",
    "AWS::EC2::Route",
    "AWS::EC2::RouteServer",
    "AWS::EC2::RouteServerAssociation",
    "AWS::EC2::RouteServerEndpoint",
    "AWS::EC2::RouteServerPeer",
    "AWS::EC2::RouteServerPropagation",
    "AWS::EC2::RouteTable",
    "AWS::EC2::SecurityGroup",
    "AWS::EC2::SecurityGroupEgress",
    "AWS::EC2::SecurityGroupIngress",
    "AWS::EC2::SecurityGroupVpcAssociation",
    "AWS::EC2::SnapshotBlockPublicAccess",
    "AWS::EC2::SpotFleet",
    "AWS::EC2::Subnet",
    "AWS::EC2::SubnetCidrBlock",
    "AWS::EC2::SubnetNetworkAclAssociation",
    "AWS::EC2::SubnetRouteTableAssociation",
    "AWS::EC2::TransitGateway",
    "AWS::EC2::TransitGatewayAttachment",
    "AWS::EC2::TransitGatewayConnect",
    "AWS::EC2::TransitGatewayMulticastDomain",
    "AWS::EC2::TransitGatewayMulticastDomainAssociation",
    "AWS::EC2::TransitGatewayMulticastGroupMember",
    "AWS::EC2::TransitGatewayMulticastGroupSource",
    "AWS::EC2::TransitGatewayPeeringAttachment",
    "AWS::EC2::TransitGatewayRoute",
    "AWS::EC2::TransitGatewayRouteTable",
    "AWS::EC2::TransitGatewayRouteTableAssociation",
    "AWS::EC2::TransitGatewayRouteTablePropagation",
    "AWS::EC2::TransitGatewayVpcAttachment",
    "AWS::EC2::VPC",
    "AWS::EC2::VPCBlockPublicAccessExclusion",
    "AWS::EC2::VPCBlockPublicAccessOptions",
    "AWS::EC2::VPCCidrBlock",
    "AWS::EC2::VPCDHCPOptionsAssociation",
    "AWS::EC2::VPCEndpoint",
    "AWS::EC2::VPCEndpointConnectionNotification",
    "AWS::EC2::VPCEndpointService",
    "AWS::EC2::VPCEndpointServicePermissions",
    "AWS::EC2::VPCGatewayAttachment",
    "AWS::EC2::VPCPeeringConnection",
    "AWS::EC2::VPNConnection",
    "AWS::EC2::VPNConnectionRoute",
    "AWS::EC2::VPNGateway",
    "AWS::EC2::VerifiedAccessEndpoint",
    "AWS::EC2::VerifiedAccessGroup",
    "AWS::EC2::VerifiedAccessInstance",
    "AWS::EC2::VerifiedAccessTrustProvider",
    "AWS::EC2::Volume",
    "AWS::EC2::VolumeAttachment",
    "AWS::ECR::PullThroughCacheRule",
    "AWS::ECR::RegistryPolicy",
    "AWS::ECR::RegistryScanningConfiguration",
    "AWS::ECR::ReplicationConfiguration",
    "AWS::ECR::Repository",
    "AWS::ECR::RepositoryCreationTemplate",
    "AWS::ECS::CapacityProvider",
    "AWS::ECS::Cluster",
    "AWS::ECS::ClusterCapacityProviderAssociations",
    "AWS::ECS::PrimaryTaskSet",
    "AWS::ECS::Service",
    "AWS::ECS::TaskDefinition",
    "AWS::ECS::TaskSet",
    "AWS::EFS::AccessPoint",
    "AWS::EFS::FileSystem",
    "AWS::EFS::MountTarget",
    "AWS::EKS::AccessEntry",
    "AWS::EKS::Addon",
    "AWS::EKS::Cluster",
    "AWS::EKS::FargateProfile",
    "AWS::EKS::IdentityProviderConfig",
    "AWS::EKS::Nodegroup",
    "AWS::EKS::PodIdentityAssociation",
    "AWS::EMR::SecurityConfiguration",
    "AWS::EMR::Step",
    "AWS::EMR::Studio",
    "AWS::EMR::StudioSessionMapping",
    "AWS::EMR::WALWorkspace",
    "AWS::EMRContainers::VirtualCluster",
    "AWS::EMRServerless::Application",
    "AWS::ElastiCache::GlobalReplicationGroup",
    "AWS::ElastiCache::ParameterGroup",
    "AWS::ElastiCache::ServerlessCache",
    "AWS::ElastiCache::SubnetGroup",
    "AWS::ElastiCache::User",
    "AWS::ElastiCache::UserGroup",
    "AWS::ElasticBeanstalk::Application",
    "AWS::ElasticBeanstalk::ApplicationVersion",
    "AWS::ElasticBeanstalk::ConfigurationTemplate",
    "AWS::ElasticBeanstalk::Environment",
    "AWS::ElasticLoadBalancingV2::Listener",
    "AWS::ElasticLoadBalancingV2::ListenerRule",
    "AWS::ElasticLoadBalancingV2::LoadBalancer",
    "AWS::ElasticLoadBalancingV2::TargetGroup",
    "AWS::ElasticLoadBalancingV2::TrustStore",
    "AWS::ElasticLoadBalancingV2::TrustStoreRevocation",
    "AWS::EntityResolution::IdMappingWorkflow",
    "AWS::EntityResolution::IdNamespace",
    "AWS::EntityResolution::MatchingWorkflow",
    "AWS::EntityResolution::PolicyStatement",
    "AWS::EntityResolution::SchemaMapping",
    "AWS::EventSchemas::Discoverer",
    "AWS::EventSchemas::Registry",
    "AWS::EventSchemas::RegistryPolicy",
    "AWS::EventSchemas::Schema",
    "AWS::Events::ApiDestination",
    "AWS::Events::Archive",
    "AWS::Events::Connection",
    "AWS::Events::Endpoint",
    "AWS::Events::EventBus",
    "AWS::Events::Rule",
    "AWS::Evidently::Experiment",
    "AWS::Evidently::Feature",
    "AWS::Evidently::Launch",
    "AWS::Evidently::Project",
    "AWS::Evidently::Segment",
    "AWS::FIS::ExperimentTemplate",
    "AWS::FIS::TargetAccountConfiguration",
    "AWS::FMS::NotificationChannel",
    "AWS::FMS::Policy",
    "AWS::FMS::ResourceSet",
    "AWS::FSx::DataRepositoryAssociation",
    "AWS::FinSpace::Environment",
    "AWS::Forecast::Dataset",
    "AWS::Forecast::DatasetGroup",
    "AWS::FraudDetector::Detector",
    "AWS::FraudDetector::EntityType",
    "AWS::FraudDetector::EventType",
    "AWS::FraudDetector::Label",
    "AWS::FraudDetector::List",
    "AWS::FraudDetector::Outcome",
    "AWS::FraudDetector::Variable",
    "AWS::GameLift::Alias",
    "AWS::GameLift::Build",
    "AWS::GameLift::ContainerFleet",
    "AWS::GameLift::ContainerGroupDefinition",
    "AWS::GameLift::Fleet",
    "AWS::GameLift::GameServerGroup",
    "AWS::GameLift::GameSessionQueue",
    "AWS::GameLift::Location",
    "AWS::GameLift::MatchmakingConfiguration",
    "AWS::GameLift::MatchmakingRuleSet",
    "AWS::GameLift::Script",
    "AWS::GlobalAccelerator::Accelerator",
    "AWS::GlobalAccelerator::CrossAccountAttachment",
    "AWS::GlobalAccelerator::EndpointGroup",
    "AWS::GlobalAccelerator::Listener",
    "AWS::Glue::Crawler",
    "AWS::Glue::Database",
    "AWS::Glue::Job",
    "AWS::Glue::Registry",
    "AWS::Glue::Schema",
    "AWS::Glue::SchemaVersion",
    "AWS::Glue::SchemaVersionMetadata",
    "AWS::Glue::Trigger",
    "AWS::Glue::UsageProfile",
    "AWS::Grafana::Workspace",
    "AWS::GreengrassV2::ComponentVersion",
    "AWS::GreengrassV2::Deployment",
    "AWS::GroundStation::Config",
    "AWS::GroundStation::DataflowEndpointGroup",
    "AWS::GroundStation::MissionProfile",
    "AWS::GuardDuty::Detector",
    "AWS::GuardDuty::Filter",
    "AWS::GuardDuty::IPSet",
    "AWS::GuardDuty::MalwareProtectionPlan",
    "AWS::GuardDuty::Master",
    "AWS::GuardDuty::Member",
    "AWS::GuardDuty::PublishingDestination",
    "AWS::GuardDuty::ThreatIntelSet",
    "AWS::HealthImaging::Datastore",
    "AWS::IAM::Group",
    "AWS::IAM::GroupPolicy",
    "AWS::IAM::InstanceProfile",
    "AWS::IAM::ManagedPolicy",
    "AWS::IAM::OIDCProvider",
    "AWS::IAM::Role",
    "AWS::IAM::RolePolicy",
    "AWS::IAM::SAMLProvider",
    "AWS::IAM::ServerCertificate",
    "AWS::IAM::ServiceLinkedRole",
    "AWS::IAM::User",
    "AWS::IAM::UserPolicy",
    "AWS::IAM::VirtualMFADevice",
    "AWS::IVS::Channel",
    "AWS::IVS::EncoderConfiguration",
    "AWS::IVS::IngestConfiguration",
    "AWS::IVS::PlaybackKeyPair",
    "AWS::IVS::PlaybackRestrictionPolicy",
    "AWS::IVS::PublicKey",
    "AWS::IVS::RecordingConfiguration",
    "AWS::IVS::Stage",
    "AWS::IVS::StorageConfiguration",
    "AWS::IVS::StreamKey",
    "AWS::IVSChat::LoggingConfiguration",
    "AWS::IVSChat::Room",
    "AWS::IdentityStore::Group",
    "AWS::IdentityStore::GroupMembership",
    "AWS::ImageBuilder::Component",
    "AWS::ImageBuilder::ContainerRecipe",
    "AWS::ImageBuilder::DistributionConfiguration",
    "AWS::ImageBuilder::Image",
    "AWS::ImageBuilder::ImagePipeline",
    "AWS::ImageBuilder::ImageRecipe",
    "AWS::ImageBuilder::InfrastructureConfiguration",
    "AWS::ImageBuilder::LifecyclePolicy",
    "AWS::ImageBuilder::Workflow",
    "AWS::Inspector::AssessmentTarget",
    "AWS::Inspector::AssessmentTemplate",
    "AWS::Inspector::ResourceGroup",
    "AWS::InspectorV2::CisScanConfiguration",
    "AWS::InspectorV2::Filter",
    "AWS::InternetMonitor::Monitor",
    "AWS::Invoicing::InvoiceUnit",
    "AWS::IoT::AccountAuditConfiguration",
    "AWS::IoT::Authorizer",
    "AWS::IoT::BillingGroup",
    "AWS::IoT::CACertificate",
    "AWS::IoT::Certificate",
    "AWS::IoT::CertificateProvider",
    "AWS::IoT::Command",
    "AWS::IoT::CustomMetric",
    "AWS::IoT::Dimension",
    "AWS::IoT::DomainConfiguration",
    "AWS::IoT::FleetMetric",
    "AWS::IoT::JobTemplate",
    "AWS::IoT::Logging",
    "AWS::IoT::MitigationAction",
    "AWS::IoT::Policy",
    "AWS::IoT::ProvisioningTemplate",
    "AWS::IoT::ResourceSpecificLogging",
    "AWS::IoT::RoleAlias",
    "AWS::IoT::ScheduledAudit",
    "AWS::IoT::SecurityProfile",
    "AWS::IoT::SoftwarePackage",
    "AWS::IoT::SoftwarePackageVersion",
    "AWS::IoT::Thing",
    "AWS::IoT::ThingGroup",
    "AWS::IoT::ThingType",
    "AWS::IoT::TopicRule",
    "AWS::IoT::TopicRuleDestination",
    "AWS::IoTAnalytics::Channel",
    "AWS::IoTAnalytics::Dataset",
    "AWS::IoTAnalytics::Datastore",
    "AWS::IoTAnalytics::Pipeline",
    "AWS::IoTCoreDeviceAdvisor::SuiteDefinition",
    "AWS::IoTEvents::AlarmModel",
    "AWS::IoTEvents::DetectorModel",
    "AWS::IoTEvents::Input",
    "AWS::IoTFleetHub::Application",
    "AWS::IoTSiteWise::AccessPolicy",
    "AWS::IoTSiteWise::Asset",
    "AWS::IoTSiteWise::AssetModel",
    "AWS::IoTSiteWise::Dashboard",
    "AWS::IoTSiteWise::Dataset",
    "AWS::IoTSiteWise::Gateway",
    "AWS::IoTSiteWise::Portal",
    "AWS::IoTSiteWise::Project",
    "AWS::IoTTwinMaker::ComponentType",
    "AWS::IoTTwinMaker::Entity",
    "AWS::IoTTwinMaker::Scene",
    "AWS::IoTTwinMaker::SyncJob",
    "AWS::IoTTwinMaker::Workspace",
    "AWS::IoTWireless::Destination",
    "AWS::IoTWireless::DeviceProfile",
    "AWS::IoTWireless::FuotaTask",
    "AWS::IoTWireless::MulticastGroup",
    "AWS::IoTWireless::NetworkAnalyzerConfiguration",
    "AWS::IoTWireless::ServiceProfile",
    "AWS::IoTWireless::TaskDefinition",
    "AWS::IoTWireless::WirelessDevice",
    "AWS::IoTWireless::WirelessGateway",
    "AWS::KMS::Alias",
    "AWS::KMS::Key",
    "AWS::KMS::ReplicaKey",
    "AWS::KafkaConnect::Connector",
    "AWS::KafkaConnect::CustomPlugin",
    "AWS::KafkaConnect::WorkerConfiguration",
    "AWS::Kendra::DataSource",
    "AWS::Kendra::Faq",
    "AWS::Kendra::Index",
    "AWS::KendraRanking::ExecutionPlan",
    "AWS::Kinesis::ResourcePolicy",
    "AWS::Kinesis::Stream",
    "AWS::KinesisAnalyticsV2::Application",
    "AWS::KinesisFirehose::DeliveryStream",
    "AWS::KinesisVideo::SignalingChannel",
    "AWS::KinesisVideo::Stream",
    "AWS::LakeFormation::DataCellsFilter",
    "AWS::LakeFormation::PrincipalPermissions",
    "AWS::LakeFormation::Tag",
    "AWS::LakeFormation::TagAssociation",
    "AWS::Lambda::Alias",
    "AWS::Lambda::CodeSigningConfig",
    "AWS::Lambda::EventInvokeConfig",
    "AWS::Lambda::EventSourceMapping",
    "AWS::Lambda::Function",
    "AWS::Lambda::LayerVersion",
    "AWS::Lambda::LayerVersionPermission",
    "AWS::Lambda::Permission",
    "AWS::Lambda::ResourcePolicy",
    "AWS::Lambda::Url",
    "AWS::Lambda::Version",
    "AWS::LaunchWizard::Deployment",
    "AWS::Lex::Bot",
    "AWS::Lex::BotAlias",
    "AWS::Lex::BotVersion",
    "AWS::Lex::ResourcePolicy",
    "AWS::LicenseManager::Grant",
    "AWS::LicenseManager::License",
    "AWS::Lightsail::Alarm",
    "AWS::Lightsail::Bucket",
    "AWS::Lightsail::Certificate",
    "AWS::Lightsail::Container",
    "AWS::Lightsail::Database",
    "AWS::Lightsail::Disk",
    "AWS::Lightsail::Instance",
    "AWS::Lightsail::InstanceSnapshot",
    "AWS::Lightsail::LoadBalancer",
    "AWS::Lightsail::LoadBalancerTlsCertificate",
    "AWS::Lightsail::StaticIp",
    "AWS::Location::APIKey",
    "AWS::Location::GeofenceCollection",
    "AWS::Location::Map",
    "AWS::Location::PlaceIndex",
    "AWS::Location::RouteCalculator",
    "AWS::Location::Tracker",
    "AWS::Location::TrackerConsumer",
    "AWS::Logs::AccountPolicy",
    "AWS::Logs::Delivery",
    "AWS::Logs::DeliveryDestination",
    "AWS::Logs::DeliverySource",
    "AWS::Logs::Destination",
    "AWS::Logs::Integration",
    "AWS::Logs::LogAnomalyDetector",
    "AWS::Logs::LogGroup",
    "AWS::Logs::LogStream",
    "AWS::Logs::MetricFilter",
    "AWS::Logs::QueryDefinition",
    "AWS::Logs::ResourcePolicy",
    "AWS::Logs::SubscriptionFilter",
    "AWS::Logs::Transformer",
    "AWS::LookoutEquipment::InferenceScheduler",
    "AWS::LookoutMetrics::Alert",
    "AWS::LookoutMetrics::AnomalyDetector",
    "AWS::LookoutVision::Project",
    "AWS::M2::Application",
    "AWS::M2::Deployment",
    "AWS::M2::Environment",
    "AWS::MSK::BatchScramSecret",
    "AWS::MSK::Cluster",
    "AWS::MSK::ClusterPolicy",
    "AWS::MSK::Configuration",
    "AWS::MSK::Replicator",
    "AWS::MSK::ServerlessCluster",
    "AWS::MSK::VpcConnection",
    "AWS::MWAA::Environment",
    "AWS::Macie::AllowList",
    "AWS::Macie::CustomDataIdentifier",
    "AWS::Macie::FindingsFilter",
    "AWS::Macie::Session",
    "AWS::ManagedBlockchain::Accessor",
    "AWS::MediaConnect::Bridge",
    "AWS::MediaConnect::BridgeOutput",
    "AWS::MediaConnect::BridgeSource",
    "AWS::MediaConnect::Flow",
    "AWS::MediaConnect::FlowEntitlement",
    "AWS::MediaConnect::FlowOutput",
    "AWS::MediaConnect::FlowSource",
    "AWS::MediaConnect::FlowVpcInterface",
    "AWS::MediaConnect::Gateway",
    "AWS::MediaLive::ChannelPlacementGroup",
    "AWS::MediaLive::CloudWatchAlarmTemplate",
    "AWS::MediaLive::CloudWatchAlarmTemplateGroup",
    "AWS::MediaLive::Cluster",
    "AWS::MediaLive::EventBridgeRuleTemplate",
    "AWS::MediaLive::EventBridgeRuleTemplateGroup",
    "AWS::MediaLive::Multiplex",
    "AWS::MediaLive::Multiplexprogram",
    "AWS::MediaLive::Network",
    "AWS::MediaLive::SdiSource",
    "AWS::MediaLive::SignalMap",
    "AWS::MediaPackage::Asset",
    "AWS::MediaPackage::Channel",
    "AWS::MediaPackage::OriginEndpoint",
    "AWS::MediaPackage::PackagingConfiguration",
    "AWS::MediaPackage::PackagingGroup",
    "AWS::MediaPackageV2::Channel",
    "AWS::MediaPackageV2::ChannelGroup",
    "AWS::MediaPackageV2::ChannelPolicy",
    "AWS::MediaPackageV2::OriginEndpoint",
    "AWS::MediaPackageV2::OriginEndpointPolicy",
    "AWS::MediaTailor::Channel",
    "AWS::MediaTailor::ChannelPolicy",
    "AWS::MediaTailor::LiveSource",
    "AWS::MediaTailor::PlaybackConfiguration",
    "AWS::MediaTailor::SourceLocation",
    "AWS::MediaTailor::VodSource",
    "AWS::MemoryDB::ACL",
    "AWS::MemoryDB::Cluster",
    "AWS::MemoryDB::MultiRegionCluster",
    "AWS::MemoryDB::ParameterGroup",
    "AWS::MemoryDB::SubnetGroup",
    "AWS::MemoryDB::User",
    "AWS::Neptune::DBCluster",
    "AWS::Neptune::DBClusterParameterGroup",
    "AWS::Neptune::DBParameterGroup",
    "AWS::Neptune::DBSubnetGroup",
    "AWS::NeptuneGraph::Graph",
    "AWS::NeptuneGraph::PrivateGraphEndpoint",
    "AWS::NetworkFirewall::Firewall",
    "AWS::NetworkFirewall::FirewallPolicy",
    "AWS::NetworkFirewall::LoggingConfiguration",
    "AWS::NetworkFirewall::RuleGroup",
    "AWS::NetworkFirewall::TLSInspectionConfiguration",
    "AWS::NetworkManager::ConnectAttachment",
    "AWS::NetworkManager::ConnectPeer",
    "AWS::NetworkManager::CoreNetwork",
    "AWS::NetworkManager::CustomerGatewayAssociation",
    "AWS::NetworkManager::Device",
    "AWS::NetworkManager::DirectConnectGatewayAttachment",
    "AWS::NetworkManager::GlobalNetwork",
    "AWS::NetworkManager::Link",
    "AWS::NetworkManager::LinkAssociation",
    "AWS::NetworkManager::Site",
    "AWS::NetworkManager::SiteToSiteVpnAttachment",
    "AWS::NetworkManager::TransitGatewayPeering",
    "AWS::NetworkManager::TransitGatewayRegistration",
    "AWS::NetworkManager::TransitGatewayRouteTableAttachment",
    "AWS::NetworkManager::VpcAttachment",
    "AWS::NimbleStudio::Studio",
    "AWS::OSIS::Pipeline",
    "AWS::Oam::Link",
    "AWS::Oam::Sink",
    "AWS::Omics::AnnotationStore",
    "AWS::Omics::ReferenceStore",
    "AWS::Omics::RunGroup",
    "AWS::Omics::SequenceStore",
    "AWS::Omics::VariantStore",
    "AWS::Omics::Workflow",
    "AWS::Omics::WorkflowVersion",
    "AWS::OpenSearchServerless::AccessPolicy",
    "AWS::OpenSearchServerless::Collection",
    "AWS::OpenSearchServerless::Index",
    "AWS::OpenSearchServerless::LifecyclePolicy",
    "AWS::OpenSearchServerless::SecurityConfig",
    "AWS::OpenSearchServerless::SecurityPolicy",
    "AWS::OpenSearchServerless::VpcEndpoint",
    "AWS::OpenSearchService::Application",
    "AWS::OpenSearchService::Domain",
    "AWS::OpsWorksCM::Server",
    "AWS::Organizations::Account",
    "AWS::Organizations::Organization",
    "AWS::Organizations::OrganizationalUnit",
    "AWS::Organizations::Policy",
    "AWS::Organizations::ResourcePolicy",
    "AWS::PCAConnectorAD::Connector",
    "AWS::PCAConnectorAD::DirectoryRegistration",
    "AWS::PCAConnectorAD::ServicePrincipalName",
    "AWS::PCAConnectorAD::Template",
    "AWS::PCAConnectorAD::TemplateGroupAccessControlEntry",
    "AWS::PCAConnectorSCEP::Challenge",
    "AWS::PCAConnectorSCEP::Connector",
    "AWS::PCS::Cluster",
    "AWS::PCS::ComputeNodeGroup",
    "AWS::PCS::Queue",
    "AWS::Panorama::ApplicationInstance",
    "AWS::Panorama::Package",
    "AWS::Panorama::PackageVersion",
    "AWS::PaymentCryptography::Alias",
    "AWS::PaymentCryptography::Key",
    "AWS::Personalize::Dataset",
    "AWS::Personalize::DatasetGroup",
    "AWS::Personalize::Schema",
    "AWS::Personalize::Solution",
    "AWS::Pinpoint::InAppTemplate",
    "AWS::Pipes::Pipe",
    "AWS::Proton::EnvironmentAccountConnection",
    "AWS::Proton::EnvironmentTemplate",
    "AWS::Proton::ServiceTemplate",
    "AWS::QBusiness::Application",
    "AWS::QBusiness::DataAccessor",
    "AWS::QBusiness::DataSource",
    "AWS::QBusiness::Index",
    "AWS::QBusiness::Permission",
    "AWS::QBusiness::Retriever",
    "AWS::QBusiness::WebExperience",
    "AWS::QLDB::Stream",
    "AWS::QuickSight::Analysis",
    "AWS::QuickSight::CustomPermissions",
    "AWS::QuickSight::Dashboard",
    "AWS::QuickSight::DataSet",
    "AWS::QuickSight::DataSource",
    "AWS::QuickSight::Folder",
    "AWS::QuickSight::RefreshSchedule",
    "AWS::QuickSight::Template",
    "AWS::QuickSight::Theme",
    "AWS::QuickSight::Topic",
    "AWS::QuickSight::VPCConnection",
    "AWS::RAM::Permission",
    "AWS::RAM::ResourceShare",
    "AWS::RDS::CustomDBEngineVersion",
    "AWS::RDS::DBCluster",
    "AWS::RDS::DBClusterParameterGroup",
    "AWS::RDS::DBInstance",
    "AWS::RDS::DBParameterGroup",
    "AWS::RDS::DBProxy",
    "AWS::RDS::DBProxyEndpoint",
    "AWS::RDS::DBProxyTargetGroup",
    "AWS::RDS::DBShardGroup",
    "AWS::RDS::DBSubnetGroup",
    "AWS::RDS::EventSubscription",
    "AWS::RDS::GlobalCluster",
    "AWS::RDS::Integration",
    "AWS::RDS::OptionGroup",
    "AWS::RUM::AppMonitor",
    "AWS::Rbin::Rule",
    "AWS::Redshift::Cluster",
    "AWS::Redshift::ClusterParameterGroup",
    "AWS::Redshift::ClusterSubnetGroup",
    "AWS::Redshift::EndpointAccess",
    "AWS::Redshift::EndpointAuthorization",
    "AWS::Redshift::EventSubscription",
    "AWS::Redshift::Integration",
    "AWS::Redshift::ScheduledAction",
    "AWS::RedshiftServerless::Namespace",
    "AWS::RedshiftServerless::Workgroup",
    "AWS::RefactorSpaces::Application",
    "AWS::RefactorSpaces::Environment",
    "AWS::RefactorSpaces::Route",
    "AWS::RefactorSpaces::Service",
    "AWS::Rekognition::Collection",
    "AWS::Rekognition::Project",
    "AWS::Rekognition::StreamProcessor",
    "AWS::ResilienceHub::App",
    "AWS::ResilienceHub::ResiliencyPolicy",
    "AWS::ResourceExplorer2::DefaultViewAssociation",
    "AWS::ResourceExplorer2::Index",
    "AWS::ResourceExplorer2::View",
    "AWS::ResourceGroups::Group",
    "AWS::ResourceGroups::TagSyncTask",
    "AWS::RoboMaker::Fleet",
    "AWS::RoboMaker::Robot",
    "AWS::RoboMaker::RobotApplication",
    "AWS::RoboMaker::RobotApplicationVersion",
    "AWS::RoboMaker::SimulationApplication",
    "AWS::RoboMaker::SimulationApplicationVersion",
    "AWS::RolesAnywhere::CRL",
    "AWS::RolesAnywhere::Profile",
    "AWS::RolesAnywhere::TrustAnchor",
    "AWS::Route53::CidrCollection",
    "AWS::Route53::DNSSEC",
    "AWS::Route53::HealthCheck",
    "AWS::Route53::HostedZone",
    "AWS::Route53::KeySigningKey",
    "AWS::Route53Profiles::Profile",
    "AWS::Route53Profiles::ProfileAssociation",
    "AWS::Route53Profiles::ProfileResourceAssociation",
    "AWS::Route53Resolver::FirewallDomainList",
    "AWS::Route53Resolver::FirewallRuleGroup",
    "AWS::Route53Resolver::FirewallRuleGroupAssociation",
    "AWS::Route53Resolver::OutpostResolver",
    "AWS::Route53Resolver::ResolverConfig",
    "AWS::Route53Resolver::ResolverDNSSECConfig",
    "AWS::Route53Resolver::ResolverEndpoint",
    "AWS::Route53Resolver::ResolverQueryLoggingConfig",
    "AWS::Route53Resolver::ResolverQueryLoggingConfigAssociation",
    "AWS::Route53Resolver::ResolverRule",
    "AWS::Route53Resolver::ResolverRuleAssociation",
    "AWS::S3::AccessGrant",
    "AWS::S3::AccessGrantsInstance",
    "AWS::S3::AccessGrantsLocation",
    "AWS::S3::AccessPoint",
    "AWS::S3::Bucket",
    "AWS::S3::BucketPolicy",
    "AWS::S3::MultiRegionAccessPoint",
    "AWS::S3::MultiRegionAccessPointPolicy",
    "AWS::S3::StorageLens",
    "AWS::S3::StorageLensGroup",
    "AWS::S3Express::AccessPoint",
    "AWS::S3Express::BucketPolicy",
    "AWS::S3Express::DirectoryBucket",
    "AWS::S3ObjectLambda::AccessPoint",
    "AWS::S3ObjectLambda::AccessPointPolicy",
    "AWS::S3Outposts::AccessPoint",
    "AWS::S3Outposts::Bucket",
    "AWS::S3Outposts::BucketPolicy",
    "AWS::S3Outposts::Endpoint",
    "AWS::S3Tables::TableBucket",
    "AWS::S3Tables::TableBucketPolicy",
    "AWS::SES::ConfigurationSet",
    "AWS::SES::ConfigurationSetEventDestination",
    "AWS::SES::ContactList",
    "AWS::SES::DedicatedIpPool",
    "AWS::SES::EmailIdentity",
    "AWS::SES::MailManagerAddonInstance",
    "AWS::SES::MailManagerAddonSubscription",
    "AWS::SES::MailManagerAddressList",
    "AWS::SES::MailManagerArchive",
    "AWS::SES::MailManagerIngressPoint",
    "AWS::SES::MailManagerRelay",
    "AWS::SES::MailManagerRuleSet",
    "AWS::SES::MailManagerTrafficPolicy",
    "AWS::SES::Template",
    "AWS::SES::VdmAttributes",
    "AWS::SNS::Subscription",
    "AWS::SNS::Topic",
    "AWS::SNS::TopicInlinePolicy",
    "AWS::SQS::Queue",
    "AWS::SQS::QueueInlinePolicy",
    "AWS::SSM::Association",
    "AWS::SSM::Document",
    "AWS::SSM::Parameter",
    "AWS::SSM::PatchBaseline",
    "AWS::SSM::ResourceDataSync",
    "AWS::SSM::ResourcePolicy",
    "AWS::SSMContacts::Contact",
    "AWS::SSMContacts::ContactChannel",
    "AWS::SSMContacts::Plan",
    "AWS::SSMContacts::Rotation",
    "AWS::SSMGuiConnect::Preferences",
    "AWS::SSMIncidents::ReplicationSet",
    "AWS::SSMIncidents::ResponsePlan",
    "AWS::SSMQuickSetup::ConfigurationManager",
    "AWS::SSO::Application",
    "AWS::SSO::ApplicationAssignment",
    "AWS::SSO::Assignment",
    "AWS::SSO::Instance",
    "AWS::SSO::InstanceAccessControlAttributeConfiguration",
    "AWS::SSO::PermissionSet",
    "AWS::SageMaker::App",
    "AWS::SageMaker::AppImageConfig",
    "AWS::SageMaker::Cluster",
    "AWS::SageMaker::DataQualityJobDefinition",
    "AWS::SageMaker::Device",
    "AWS::SageMaker::DeviceFleet",
    "AWS::SageMaker::Domain",
    "AWS::SageMaker::FeatureGroup",
    "AWS::SageMaker::Image",
    "AWS::SageMaker::ImageVersion",
    "AWS::SageMaker::InferenceComponent",
    "AWS::SageMaker::InferenceExperiment",
    "AWS::SageMaker::MlflowTrackingServer",
    "AWS::SageMaker::ModelBiasJobDefinition",
    "AWS::SageMaker::ModelCard",
    "AWS::SageMaker::ModelExplainabilityJobDefinition",
    "AWS::SageMaker::ModelPackage",
    "AWS::SageMaker::ModelPackageGroup",
    "AWS::SageMaker::ModelQualityJobDefinition",
    "AWS::SageMaker::MonitoringSchedule",
    "AWS::SageMaker::PartnerApp",
    "AWS::SageMaker::Pipeline",
    "AWS::SageMaker::Project",
    "AWS::SageMaker::Space",
    "AWS::SageMaker::StudioLifecycleConfig",
    "AWS::SageMaker::UserProfile",
    "AWS::Scheduler::Schedule",
    "AWS::Scheduler::ScheduleGroup",
    "AWS::SecretsManager::ResourcePolicy",
    "AWS::SecretsManager::RotationSchedule",
    "AWS::SecretsManager::Secret",
    "AWS::SecretsManager::SecretTargetAttachment",
    "AWS::SecurityHub::AutomationRule",
    "AWS::SecurityHub::ConfigurationPolicy",
    "AWS::SecurityHub::DelegatedAdmin",
    "AWS::SecurityHub::FindingAggregator",
    "AWS::SecurityHub::Hub",
    "AWS::SecurityHub::Insight",
    "AWS::SecurityHub::OrganizationConfiguration",
    "AWS::SecurityHub::PolicyAssociation",
    "AWS::SecurityHub::ProductSubscription",
    "AWS::SecurityHub::SecurityControl",
    "AWS::SecurityHub::Standard",
    "AWS::SecurityLake::AwsLogSource",
    "AWS::SecurityLake::DataLake",
    "AWS::SecurityLake::Subscriber",
    "AWS::SecurityLake::SubscriberNotification",
    "AWS::ServiceCatalog::CloudFormationProvisionedProduct",
    "AWS::ServiceCatalog::ServiceAction",
    "AWS::ServiceCatalog::ServiceActionAssociation",
    "AWS::ServiceCatalogAppRegistry::Application",
    "AWS::ServiceCatalogAppRegistry::AttributeGroup",
    "AWS::ServiceCatalogAppRegistry::AttributeGroupAssociation",
    "AWS::ServiceCatalogAppRegistry::ResourceAssociation",
    "AWS::Shield::DRTAccess",
    "AWS::Shield::ProactiveEngagement",
    "AWS::Shield::Protection",
    "AWS::Shield::ProtectionGroup",
    "AWS::Signer::ProfilePermission",
    "AWS::Signer::SigningProfile",
    "AWS::SimSpaceWeaver::Simulation",
    "AWS::StepFunctions::Activity",
    "AWS::StepFunctions::StateMachine",
    "AWS::StepFunctions::StateMachineAlias",
    "AWS::StepFunctions::StateMachineVersion",
    "AWS::SupportApp::AccountAlias",
    "AWS::SupportApp::SlackChannelConfiguration",
    "AWS::SupportApp::SlackWorkspaceConfiguration",
    "AWS::Synthetics::Canary",
    "AWS::Synthetics::Group",
    "AWS::SystemsManagerSAP::Application",
    "AWS::Timestream::Database",
    "AWS::Timestream::InfluxDBInstance",
    "AWS::Timestream::ScheduledQuery",
    "AWS::Timestream::Table",
    "AWS::Transfer::Agreement",
    "AWS::Transfer::Certificate",
    "AWS::Transfer::Connector",
    "AWS::Transfer::Profile",
    "AWS::Transfer::Server",
    "AWS::Transfer::User",
    "AWS::Transfer::WebApp",
    "AWS::Transfer::Workflow",
    "AWS::VerifiedPermissions::IdentitySource",
    "AWS::VerifiedPermissions::Policy",
    "AWS::VerifiedPermissions::PolicyStore",
    "AWS::VerifiedPermissions::PolicyTemplate",
    "AWS::VpcLattice::AccessLogSubscription",
    "AWS::VpcLattice::AuthPolicy",
    "AWS::VpcLattice::Listener",
    "AWS::VpcLattice::ResourceConfiguration",
    "AWS::VpcLattice::ResourceGateway",
    "AWS::VpcLattice::ResourcePolicy",
    "AWS::VpcLattice::Rule",
    "AWS::VpcLattice::Service",
    "AWS::VpcLattice::ServiceNetwork",
    "AWS::VpcLattice::ServiceNetworkResourceAssociation",
    "AWS::VpcLattice::ServiceNetworkServiceAssociation",
    "AWS::VpcLattice::ServiceNetworkVpcAssociation",
    "AWS::VpcLattice::TargetGroup",
    "AWS::WAFv2::IPSet",
    "AWS::WAFv2::LoggingConfiguration",
    "AWS::WAFv2::RegexPatternSet",
    "AWS::WAFv2::RuleGroup",
    "AWS::WAFv2::WebACL",
    "AWS::WAFv2::WebACLAssociation",
    "AWS::WorkSpaces::ConnectionAlias",
    "AWS::WorkSpaces::WorkspacesPool",
    "AWS::WorkSpacesThinClient::Environment",
    "AWS::WorkSpacesWeb::BrowserSettings",
    "AWS::WorkSpacesWeb::DataProtectionSettings",
    "AWS::WorkSpacesWeb::IdentityProvider",
    "AWS::WorkSpacesWeb::IpAccessSettings",
    "AWS::WorkSpacesWeb::NetworkSettings",
    "AWS::WorkSpacesWeb::Portal",
    "AWS::WorkSpacesWeb::TrustStore",
    "AWS::WorkSpacesWeb::UserAccessLoggingSettings",
    "AWS::WorkSpacesWeb::UserSettings",
    "AWS::XRay::Group",
    "AWS::XRay::ResourcePolicy",
    "AWS::XRay::SamplingRule",
    "AWS::XRay::TransactionSearchConfig"
]
@dataclass
class ResourceInfo:
    """Data class to hold comprehensive resource information for discovered AWS resources"""
    resource_type: str  # AWS resource type (e.g., "AWS::EC2::Instance")
    identifier: str     # Unique resource identifier
    arn: str = ""       # Amazon Resource Name
    properties: Dict[str, Any] = None  # Resource properties from AWS APIs
    service: str = ""   # AWS service name (extracted from resource_type)
    region: str = ""    # AWS region where resource exists
    error: str = ""     # Error message if discovery failed
    
    def __post_init__(self):
        # Initialize empty properties dict if none provided
        if self.properties is None:
            self.properties = {}
        # Extract service name from resource type (AWS::EC2::Instance -> ec2)
        if "::" in self.resource_type:
            self.service = self.resource_type.split("::")[1].lower()
class ComprehensiveAWSDiscovery:
    """
    Comprehensive AWS Resource Discovery Tool
    
    Discovers all AWS resources using Cloud Control API across 600+ resource types
    with parallel processing, Neo4j integration, and multiple export formats.
    """
    
    def __init__(self, region: str, profile: str = None):
        """Initialize discovery tool with AWS session and output directories"""
        self.region = region        
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self._account_id = None
        
        # Initialize primary AWS clients
        self.cloudcontrol_client = self.session.client('cloudcontrol', region_name=region)
        self.tagging_client = self.session.client('resourcegroupstaggingapi', region_name=region)
        
        # Setup timestamped output directory structure
        self.output_dir = Path(f"aws-discovery-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        self.output_dir.mkdir(exist_ok=True)
        self.descriptions_dir = self.output_dir / "detailed-descriptions"
        self.descriptions_dir.mkdir(exist_ok=True)
        
        # Cache for service-specific AWS clients
        self.service_clients = {}
        
        # Discovery statistics tracking
        self.stats = {
            'total_resource_types': len(AWS_RESOURCE_TYPES),
            'successful_types': 0,
            'failed_types': 0,
            'total_resources': 0,
            'resources_with_arns': 0,
            'detailed_descriptions_created': 0,
            'resources_by_service': Counter(),
            'errors': [],
            'start_time': None,
            'end_time': None
        }
        
        self.setup_logging()
        
        # Services that are global (not region-specific)
        self.global_services = {'iam', 'organizations', 'route53', 'waf', 'wafv2', 'artifacts', 'controltower'}
        
        # Resource types to skip based on known API limitations
        self.skip_patterns = {
            'missing_required_key': [
                'AWS::AutoScaling::WarmPool',
                'AWS::AutoScaling::LifecycleHook',
                'AWS::Bedrock::FlowVersion',
                'AWS::Bedrock::PromptVersion',
                'AWS::CleanRooms::AnalysisTemplate',
                'AWS::CleanRooms::IdMappingTable',
                'AWS::CleanRooms::IdNamespaceAssociation',
                'AWS::WAFv2::RuleGroup',
                'AWS::WAFv2::WebACL',
            ],
            'unsupported_action': [
                'AWS::WAFv2::WebACLAssociation',
            ],
            'type_not_found': [
                'AWS::WorkSpaces::WorkspacesPool',
                'AWS::WorkSpacesWeb::UserSettings',
                'AWS::WorkSpacesWeb::UserAccessLoggingSettings',
                'AWS::WorkSpacesWeb::TrustStore',
                'AWS::WorkSpacesWeb::Portal',
                'AWS::WorkSpacesWeb::NetworkSettings',
                'AWS::WorkSpacesWeb::IpAccessSettings',
                'AWS::WorkSpacesWeb::DataProtectionSettings',
                'AWS::WorkSpacesWeb::BrowserSettings',
                'AWS::WorkSpaces::ConnectionAlias',
            ],
            'subscription_required': [
                'AWS::Shield::Protection',
                'AWS::CloudFormation::Publisher',
                'AWS::CE::CostCategory',
            ]
        }
    def setup_logging(self):
        """Configure file and console logging with appropriate levels and formatters"""
        log_file = self.output_dir / "discovery.log"
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # Create handlers
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        
        console_handler = logging.StreamHandler(sys.stdout)  # Use stdout instead of stderr
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        
        # Get logger and clear any existing handlers
        self.logger = logging.getLogger('aws_discovery')
        self.logger.handlers.clear()
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # Prevent propagation to root logger
        
        # Add our handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    def _should_skip_resource_type(self, resource_type: str, error_msg: str = "") -> bool:
        """
        Determine if a resource type should be skipped based on known error patterns
        """
        for category, resource_types in self.skip_patterns.items():
            if resource_type in resource_types:
                self.logger.debug(f"⚠ Skipping {resource_type}: Known {category} issue")
                return True
        error_lower = error_msg.lower()
        if 'throttlingexception' in error_lower or 'rate exceeded' in error_lower:
            self.logger.debug(f"⚠ Skipping {resource_type}: Throttling error")
            return True
        if 'required key' in error_lower and 'not found' in error_lower:
            self.logger.debug(f"⚠ Skipping {resource_type}: Missing required parameter")
            return True
        if 'does not support list action' in error_lower or 'unsupportedactionexception' in error_lower:
            self.logger.debug(f"⚠ Skipping {resource_type}: Unsupported LIST action")
            return True
        if 'typenotfoundexception' in error_lower or 'cannot be found' in error_lower:
            self.logger.debug(f"⚠ Skipping {resource_type}: Resource type not found")
            return True
        if ('subscription does not exist' in error_lower or 
            'not registered as a publisher' in error_lower or
            'linked account' in error_lower and 'access' in error_lower):
            self.logger.debug(f"⚠ Skipping {resource_type}: Subscription or account access issue")
            return True
        return False
    def _is_global_service(self, service: str) -> bool:
        """Check if a service is global (doesn't require region property)"""
        return service.lower() in self.global_services
    def _build_node_properties(self, base_properties: Dict[str, Any], service: str) -> Dict[str, Any]:
        """Build node properties with conditional region based on service type"""
        properties = dict(base_properties)
        properties['account_id'] = self._get_account_id()
        if not self._is_global_service(service):
            properties['region'] = self.region
        return properties
    def discover_resource_type(self, resource_type: str) -> List[ResourceInfo]:
        """Discover all resources of a specific type using Cloud Control API with error handling"""
        try:
            if self._should_skip_resource_type(resource_type, str(Exception())):
                return []
            resources = []
            paginator = self.cloudcontrol_client.get_paginator('list_resources')
            page_iterator = paginator.paginate(TypeName=resource_type)
            for page in page_iterator:
                for resource_desc in page.get('ResourceDescriptions', []):
                    identifier = resource_desc.get('Identifier', '')
                    properties_str = resource_desc.get('Properties', '{}')
                    try:
                        properties = json.loads(properties_str) if properties_str else {}
                    except json.JSONDecodeError:
                        properties = {"raw_properties": properties_str}
                    arn = self.extract_arn_from_properties(properties, resource_type, identifier)
                    resource_info = ResourceInfo(
                        resource_type=resource_type,
                        identifier=identifier,
                        arn=arn,
                        properties=properties,
                        region=self.region
                    )
                    resources.append(resource_info)
            self.stats['successful_types'] += 1
            self.stats['total_resources'] += len(resources)
            self.stats['resources_with_arns'] += len([r for r in resources if r.arn])
            self.stats['resources_by_service'][resource_type.split("::")[1]] += len(resources)
            if resources:
                self.logger.info(f"✓ {resource_type}: Found {len(resources)} resources")
            else:
                self.logger.debug(f"○ {resource_type}: No resources found")
            return resources
        except Exception as e:
            if self._should_skip_resource_type(resource_type, str(e)):
                return []
            error_msg = f"Failed to discover {resource_type}: {str(e)}"
            self.logger.debug(error_msg)
            self.stats['failed_types'] += 1
            self.stats['errors'].append({'resource_type': resource_type, 'error': str(e)})
            return [ResourceInfo(
                resource_type=resource_type,
                identifier="",
                error=str(e),
                region=self.region
            )]
    def extract_arn_from_properties(self, properties: Dict[str, Any], resource_type: str, identifier: str) -> str:
        """
        Extract ARN from resource properties using common patterns
        """
        for arn_field in ['Arn', 'ARN', 'arn', 'ResourceArn']:
            if arn_field in properties:
                return properties[arn_field]
        service = resource_type.split("::")[1].lower()
        resource_name = resource_type.split("::")[-1].lower()
        if service == "s3" and resource_name == "bucket":
            return f"arn:aws:s3:::{identifier}"
        elif service == "lambda" and resource_name == "function":
            return f"arn:aws:lambda:{self.region}:{properties.get('FunctionArn', '').split(':')[4] if 'FunctionArn' in properties else ''}:function:{identifier}"
        elif service == "dynamodb" and resource_name == "table":
            return f"arn:aws:dynamodb:{self.region}:{properties.get('TableArn', '').split(':')[4] if 'TableArn' in properties else ''}:table/{identifier}"
        elif service == "iam":
            if resource_name in ["role", "user", "group"]:
                return f"arn:aws:iam::{properties.get('RoleArn', '').split(':')[4] if 'RoleArn' in properties else ''}:{resource_name}/{identifier}"
        account_id = self.get_account_id()
        return f"arn:aws:{service}:{self.region}:{account_id}:{resource_name}/{identifier}"
    def get_service_client(self, service: str):
        """Get or create a boto3 client for a specific service"""
        if service not in self.service_clients:
            try:
                self.service_clients[service] = self.session.client(service, region_name=self.region)
            except Exception as e:
                self.logger.debug(f"Failed to create {service} client: {e}")
                return None
        return self.service_clients[service]
    def parse_arn(self, arn: str) -> Dict[str, str]:
        """Parse an ARN into its components"""
        if not arn or not arn.startswith('arn:'):
            return {}
        try:
            parts = arn.split(':')
            if len(parts) < 6:
                return {}
            resource_part = parts[5]
            if '/' in resource_part:
                resource_type = resource_part.split('/')[0]
                resource_id = resource_part.split('/', 1)[1]
            else:
                resource_type = resource_part
                resource_id = ""
            return {
                'partition': parts[1],
                'service': parts[2],
                'region': parts[3],
                'account': parts[4],
                'resource_type': resource_type,
                'resource_id': resource_id,
                'full_resource': resource_part
            }
        except Exception:
            return {}
    def get_detailed_resource_description(self, resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get comprehensive resource description using service-specific APIs"""
        if not resource_info.arn:
            return {"error": "No ARN available for detailed description"}
        arn_parts = self.parse_arn(resource_info.arn)
        if not arn_parts:
            return {"error": "Invalid ARN format"}
        service = arn_parts['service']
        resource_type = arn_parts['resource_type']
        resource_id = arn_parts['resource_id']
        try:
            try:
                cloudcontrol_desc = self.cloudcontrol_client.get_resource(
                    TypeName=resource_info.resource_type,
                    Identifier=resource_info.identifier
                )
                parsed_cloudcontrol_desc = self.parse_cloudcontrol_properties(cloudcontrol_desc)
                base_description = {
                    "source": "cloudcontrol",
                    "resource_description": parsed_cloudcontrol_desc
                }
            except Exception as e:
                parsed_basic_properties = self.ensure_properties_are_json(resource_info.properties)
                base_description = {
                    "source": "discovery",
                    "error": f"CloudControl API failed: {str(e)}",
                    "basic_properties": parsed_basic_properties
                }
            service_details = self.get_service_specific_details(arn_parts, resource_info)
            comprehensive_description = {
                "metadata": {
                    "arn": resource_info.arn,
                    "resource_type": resource_info.resource_type,
                    "service": service,
                    "region": self.region,
                    "identifier": resource_info.identifier,
                    "discovery_time": datetime.now().isoformat()
                },
                "base_description": base_description,
                "service_specific_details": service_details,
                "tags": self.get_resource_tags(resource_info.arn)
            }
            return comprehensive_description
        except Exception as e:
            parsed_basic_properties = self.ensure_properties_are_json(resource_info.properties)
            return {
                "metadata": {
                    "arn": resource_info.arn,
                    "resource_type": resource_info.resource_type,
                    "service": service,
                    "region": self.region,
                    "identifier": resource_info.identifier,
                    "discovery_time": datetime.now().isoformat()
                },
                "error": f"Failed to get detailed description: {str(e)}",
                "basic_properties": parsed_basic_properties
            }
    def parse_cloudcontrol_properties(self, cloudcontrol_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse CloudControl API response and convert Properties JSON string to actual JSON object
        """
        try:
            parsed_response = cloudcontrol_response.copy()
            if ('ResourceDescription' in parsed_response and 
                'Properties' in parsed_response['ResourceDescription']):
                properties_str = parsed_response['ResourceDescription']['Properties']
                if isinstance(properties_str, str):
                    try:
                        parsed_properties = json.loads(properties_str)
                        parsed_response['ResourceDescription']['Properties'] = parsed_properties
                        self.logger.debug(f"Successfully parsed Properties JSON string to object")
                    except json.JSONDecodeError as e:
                        self.logger.debug(f"Failed to parse Properties JSON: {e}")
                        parsed_response['ResourceDescription']['Properties'] = {
                            "parse_error": f"Failed to parse JSON: {str(e)}",
                            "raw_properties": properties_str
                        }
                elif properties_str is None:
                    parsed_response['ResourceDescription']['Properties'] = {}
            return parsed_response
        except Exception as e:
            self.logger.debug(f"Error parsing CloudControl properties: {e}")
            return cloudcontrol_response
    def ensure_properties_are_json(self, properties: Any) -> Dict[str, Any]:
        """
        Ensure properties are properly formatted JSON objects, not strings
        """
        try:
            if properties is None:
                return {}
            if isinstance(properties, str):
                try:
                    return json.loads(properties)
                except json.JSONDecodeError:
                    return {"raw_properties": properties, "parse_error": "Invalid JSON string"}
            if isinstance(properties, dict):
                parsed_properties = {}
                for key, value in properties.items():
                    if isinstance(value, str) and value.strip().startswith(('{', '[')):
                        try:
                            parsed_properties[key] = json.loads(value)
                        except json.JSONDecodeError:
                            parsed_properties[key] = value
                    else:
                        parsed_properties[key] = value
                return parsed_properties
            return properties if isinstance(properties, (dict, list)) else {"value": properties}
        except Exception as e:
            self.logger.debug(f"Error ensuring properties are JSON: {e}")
            return {"error": f"Failed to process properties: {str(e)}", "raw_properties": str(properties)}
    def get_service_specific_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """
        Get service-specific detailed information using native AWS APIs
        """
        service = arn_parts['service']
        resource_type = arn_parts['resource_type']
        resource_id = arn_parts['resource_id']
        try:
            if service == 'ec2':
                return self.get_ec2_details(arn_parts, resource_info)
            elif service == 's3':
                return self.get_s3_details(arn_parts, resource_info)
            elif service == 'lambda':
                return self.get_lambda_details(arn_parts, resource_info)
            elif service == 'rds':
                return self.get_rds_details(arn_parts, resource_info)
            elif service == 'iam':
                return self.get_iam_details(arn_parts, resource_info)
            elif service == 'dynamodb':
                return self.get_dynamodb_details(arn_parts, resource_info)
            elif service == 'cloudformation':
                return self.get_cloudformation_details(arn_parts, resource_info)
            elif service == 'sns':
                return self.get_sns_details(arn_parts, resource_info)
            elif service == 'sqs':
                return self.get_sqs_details(arn_parts, resource_info)
            elif service == 'logs':
                return self.get_logs_details(arn_parts, resource_info)
            elif service == 'eks':
                return self.get_eks_details(arn_parts, resource_info)
            elif service == 'ecs':
                return self.get_ecs_details(arn_parts, resource_info)
            elif service == 'cloudwatch':
                return self.get_cloudwatch_details(arn_parts, resource_info)
            else:
                return {"info": f"Service {service} details not implemented"}
        except Exception as e:
            return {"error": f"Failed to get {service} details: {str(e)}"}
    def get_ec2_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed EC2 resource information"""
        client = self.get_service_client('ec2')
        if not client:
            return {"error": "EC2 client not available"}
        resource_type = arn_parts['resource_type']
        resource_id = arn_parts['resource_id']
        try:
            if resource_type == 'instance':
                response = client.describe_instances(InstanceIds=[resource_id])
                return {"instances": response}
            elif resource_type == 'volume':
                response = client.describe_volumes(VolumeIds=[resource_id])
                return {"volumes": response}
            elif resource_type == 'vpc':
                response = client.describe_vpcs(VpcIds=[resource_id])
                return {"vpcs": response}
            elif resource_type == 'subnet':
                response = client.describe_subnets(SubnetIds=[resource_id])
                return {"subnets": response}
            elif resource_type == 'security-group':
                response = client.describe_security_groups(GroupIds=[resource_id])
                return {"security_groups": response}
            elif resource_type == 'network-interface':
                response = client.describe_network_interfaces(NetworkInterfaceIds=[resource_id])
                return {"network_interfaces": response}
            else:
                return {"info": f"EC2 resource type {resource_type} not implemented"}
        except Exception as e:
            return {"error": f"EC2 API call failed: {str(e)}"}
    def get_s3_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed S3 resource information"""
        client = self.get_service_client('s3')
        if not client:
            return {"error": "S3 client not available"}
        bucket_name = arn_parts['full_resource']
        try:
            details = {}
            details['location'] = client.get_bucket_location(Bucket=bucket_name)
            try:
                details['versioning'] = client.get_bucket_versioning(Bucket=bucket_name)
            except:
                pass
            try:
                details['encryption'] = client.get_bucket_encryption(Bucket=bucket_name)
            except:
                pass
            try:
                details['policy'] = client.get_bucket_policy(Bucket=bucket_name)
            except:
                pass
            try:
                details['logging'] = client.get_bucket_logging(Bucket=bucket_name)
            except:
                pass
            try:
                details['notification'] = client.get_bucket_notification_configuration(Bucket=bucket_name)
            except:
                pass
            return details
        except Exception as e:
            return {"error": f"S3 API call failed: {str(e)}"}
    def get_lambda_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed Lambda resource information"""
        client = self.get_service_client('lambda')
        if not client:
            return {"error": "Lambda client not available"}
        function_name = resource_info.identifier
        try:
            details = {}
            details['function'] = client.get_function(FunctionName=function_name)
            try:
                details['policy'] = client.get_policy(FunctionName=function_name)
            except:
                pass
            try:
                details['event_source_mappings'] = client.list_event_source_mappings(FunctionName=function_name)
            except:
                pass
            return details
        except Exception as e:
            return {"error": f"Lambda API call failed: {str(e)}"}
    def get_rds_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed RDS resource information"""
        client = self.get_service_client('rds')
        if not client:
            return {"error": "RDS client not available"}
        resource_type = arn_parts['resource_type']
        resource_id = arn_parts['resource_id']
        try:
            if resource_type == 'db':
                response = client.describe_db_instances(DBInstanceIdentifier=resource_id)
                return {"db_instances": response}
            elif resource_type == 'cluster':
                response = client.describe_db_clusters(DBClusterIdentifier=resource_id)
                return {"db_clusters": response}
            else:
                return {"info": f"RDS resource type {resource_type} not implemented"}
        except Exception as e:
            return {"error": f"RDS API call failed: {str(e)}"}
    def get_iam_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed IAM resource information"""
        client = self.get_service_client('iam')
        if not client:
            return {"error": "IAM client not available"}
        resource_type = arn_parts['resource_type']
        resource_id = arn_parts['resource_id']
        try:
            if resource_type == 'role':
                details = {}
                details['role'] = client.get_role(RoleName=resource_id)
                try:
                    details['role_policies'] = client.list_role_policies(RoleName=resource_id)
                    details['attached_policies'] = client.list_attached_role_policies(RoleName=resource_id)
                except:
                    pass
                return details
            elif resource_type == 'user':
                details = {}
                details['user'] = client.get_user(UserName=resource_id)
                try:
                    details['user_policies'] = client.list_user_policies(UserName=resource_id)
                    details['attached_policies'] = client.list_attached_user_policies(UserName=resource_id)
                    details['groups'] = client.get_groups_for_user(UserName=resource_id)
                except:
                    pass
                return details
            elif resource_type == 'policy':
                details = {}
                details['policy'] = client.get_policy(PolicyArn=resource_info.arn)
                try:
                    details['policy_version'] = client.get_policy_version(
                        PolicyArn=resource_info.arn,
                        VersionId=details['policy']['Policy']['DefaultVersionId']
                    )
                except:
                    pass
                return details
            else:
                return {"info": f"IAM resource type {resource_type} not implemented"}
        except Exception as e:
            return {"error": f"IAM API call failed: {str(e)}"}
    def get_dynamodb_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed DynamoDB resource information"""
        client = self.get_service_client('dynamodb')
        if not client:
            return {"error": "DynamoDB client not available"}
        table_name = resource_info.identifier
        try:
            details = {}
            details['table'] = client.describe_table(TableName=table_name)
            try:
                details['backup_summary'] = client.list_backups(TableName=table_name)
            except:
                pass
            try:
                details['continuous_backups'] = client.describe_continuous_backups(TableName=table_name)
            except:
                pass
            return details
        except Exception as e:
            return {"error": f"DynamoDB API call failed: {str(e)}"}
    def get_cloudformation_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed CloudFormation resource information"""
        client = self.get_service_client('cloudformation')
        if not client:
            return {"error": "CloudFormation client not available"}
        stack_name = resource_info.identifier
        try:
            details = {}
            details['stack'] = client.describe_stacks(StackName=stack_name)
            try:
                details['resources'] = client.describe_stack_resources(StackName=stack_name)
            except:
                pass
            try:
                details['events'] = client.describe_stack_events(StackName=stack_name)
            except:
                pass
            return details
        except Exception as e:
            return {"error": f"CloudFormation API call failed: {str(e)}"}
    def get_sns_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed SNS resource information"""
        client = self.get_service_client('sns')
        if not client:
            return {"error": "SNS client not available"}
        topic_arn = resource_info.arn
        try:
            details = {}
            details['attributes'] = client.get_topic_attributes(TopicArn=topic_arn)
            try:
                details['subscriptions'] = client.list_subscriptions_by_topic(TopicArn=topic_arn)
            except:
                pass
            return details
        except Exception as e:
            return {"error": f"SNS API call failed: {str(e)}"}
    def get_sqs_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed SQS resource information"""
        client = self.get_service_client('sqs')
        if not client:
            return {"error": "SQS client not available"}
        try:
            queue_url = client.get_queue_url(QueueName=resource_info.identifier)['QueueUrl']
            details = {}
            details['attributes'] = client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=['All']
            )
            return details
        except Exception as e:
            return {"error": f"SQS API call failed: {str(e)}"}
    def get_logs_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed CloudWatch Logs resource information"""
        client = self.get_service_client('logs')
        if not client:
            return {"error": "Logs client not available"}
        log_group_name = resource_info.identifier
        try:
            details = {}
            details['log_groups'] = client.describe_log_groups(logGroupNamePrefix=log_group_name)
            try:
                details['log_streams'] = client.describe_log_streams(logGroupName=log_group_name)
            except:
                pass
            return details
        except Exception as e:
            return {"error": f"Logs API call failed: {str(e)}"}
    def get_eks_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed EKS resource information"""
        client = self.get_service_client('eks')
        if not client:
            return {"error": "EKS client not available"}
        cluster_name = resource_info.identifier
        try:
            details = {}
            details['cluster'] = client.describe_cluster(name=cluster_name)
            try:
                details['nodegroups'] = client.list_nodegroups(clusterName=cluster_name)
            except:
                pass
            try:
                details['fargate_profiles'] = client.list_fargate_profiles(clusterName=cluster_name)
            except:
                pass
            return details
        except Exception as e:
            return {"error": f"EKS API call failed: {str(e)}"}
    def get_ecs_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed ECS resource information"""
        client = self.get_service_client('ecs')
        if not client:
            return {"error": "ECS client not available"}
        resource_type = arn_parts['resource_type']
        try:
            if resource_type == 'cluster':
                cluster_name = resource_info.identifier
                details = {}
                details['cluster'] = client.describe_clusters(clusters=[cluster_name])
                try:
                    details['services'] = client.list_services(cluster=cluster_name)
                except:
                    pass
                return details
            else:
                return {"info": f"ECS resource type {resource_type} not implemented"}
        except Exception as e:
            return {"error": f"ECS API call failed: {str(e)}"}
    def get_cloudwatch_details(self, arn_parts: Dict[str, str], resource_info: ResourceInfo) -> Dict[str, Any]:
        """Get detailed CloudWatch resource information"""
        client = self.get_service_client('cloudwatch')
        if not client:
            return {"error": "CloudWatch client not available"}
        resource_type = arn_parts['resource_type']
        try:
            if resource_type == 'alarm':
                alarm_name = resource_info.identifier
                details = {}
                details['alarms'] = client.describe_alarms(AlarmNames=[alarm_name])
                try:
                    details['alarm_history'] = client.describe_alarm_history(AlarmName=alarm_name)
                except:
                    pass
                return details
            else:
                return {"info": f"CloudWatch resource type {resource_type} not implemented"}
        except Exception as e:
            return {"error": f"CloudWatch API call failed: {str(e)}"}
    def get_resource_tags(self, arn: str) -> Dict[str, Any]:
        """Get resource tags using Resource Groups Tagging API"""
        try:
            response = self.tagging_client.get_resources(
                ResourceARNList=[arn]
            )
            if response['ResourceTagMappingList']:
                return {
                    "tags": response['ResourceTagMappingList'][0].get('Tags', [])
                }
            else:
                return {"tags": []}
        except Exception as e:
            return {"error": f"Failed to get tags: {str(e)}"}
    def save_consolidated_resource_descriptions(self, resources: List[ResourceInfo], max_workers: int = 10) -> int:
        """
        Save detailed descriptions for all resources to a single consolidated JSON file
        Returns the number of descriptions successfully processed
        """
        valid_resources = [r for r in resources if r.arn and not r.error]
        if not valid_resources:
            self.logger.warning("No valid resources with ARNs to create detailed descriptions")
            return 0
        self.logger.info(f"🔍 Creating consolidated resource descriptions for {len(valid_resources)} resources...")
        all_descriptions = []
        failed_count = 0
        processed_count = 0
        if HAS_TQDM:
            progress_bar = tqdm(total=len(valid_resources), desc="Processing descriptions", unit="resource")
        executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_to_resource = {
                executor.submit(self.get_detailed_resource_description, resource): resource
                for resource in valid_resources
            }
            for future in as_completed(future_to_resource):
                resource = future_to_resource[future]
                try:
                    description = future.result()
                    all_descriptions.append(description)
                    processed_count += 1
                    if HAS_TQDM:
                        progress_bar.update(1)
                        progress_bar.set_postfix({
                            'Processed': processed_count,
                            'Failed': failed_count
                        })
                except Exception as e:
                    failed_count += 1
                    self.logger.debug(f"Failed to create description for {resource.arn}: {e}")
                    error_description = {
                        "metadata": {
                            "arn": resource.arn,
                            "resource_type": resource.resource_type,
                            "service": resource.service,
                            "region": self.region,
                            "identifier": resource.identifier,
                            "discovery_time": datetime.now().isoformat()
                        },
                        "error": f"Failed to get detailed description: {str(e)}",
                        "basic_properties": self.ensure_properties_are_json(resource.properties)
                    }
                    all_descriptions.append(error_description)
                    processed_count += 1
                    if HAS_TQDM:
                        progress_bar.update(1)
                        progress_bar.set_postfix({
                            'Processed': processed_count,
                            'Failed': failed_count
                        })
        finally:
            executor.shutdown(wait=True)
        if HAS_TQDM:
            progress_bar.close()
        consolidated_file = self.descriptions_dir / "all_resources_detailed.json"
        consolidated_data = {
            "metadata": {
                "discovery_time": datetime.now().isoformat(),
                "region": self.region,
                "total_resources_processed": processed_count,
                "successful_descriptions": processed_count - failed_count,
                "failed_descriptions": failed_count,
                "discovery_statistics": self.stats
            },
            "resources": all_descriptions
        }
        all_resource = {}
        for resource in consolidated_data['resources']:
            if 'metadata' in resource:
                try:
                    arn = resource['metadata'].get('arn', '')
                    resource_type = resource['metadata'].get('resource_type', '')
                    parts = resource_type.split('::')
                    service = parts[1] if len(parts) > 1 else 'Unknown'
                    resource_type = parts[2] if len(parts) > 2 else 'Unknown'
                    region = resource['metadata'].get('region', self.region)
                    identifier = resource['metadata'].get('identifier', '')
                    parts = identifier.split('|')
                    part1 = parts[0] if len(parts) > 0 else ''
                    part2 = parts[1] if len(parts) > 1 else ''
                    resource_description = resource.get('base_description', {}).get('resource_description', {})
                    if 'ResourceDescription' in resource_description:
                        properties = resource_description['ResourceDescription']['Properties']
                    else:
                        properties = resource_description
                    all_resource[arn] = {
                        'resource_type': resource_type,
                        'service': service,
                        'region': region,
                        'identifier': identifier,
                        'part1': part1,
                        'part2': part2,
                        'properties': properties
                    }
                except Exception as e:
                    self.logger.error(f"Error processing resource metadata: {e}")
        for arn , info in all_resource.items():
            self.logger.info(f"Resource ARN: {arn}, Type: {info['resource_type']}, Service: {info['service']}, Region: {info['region']}, Identifier: {info['identifier']}, Part1: {info['part1']}, Part2: {info['part2']}, Properties: {info['properties']}")
        try:
            with open(consolidated_file, 'w') as f:
                json.dump(consolidated_data, f, indent=2, default=str)
            self.logger.info(f"💾 Saved consolidated descriptions to: {consolidated_file}")
            self.stats['detailed_descriptions_created'] = processed_count - failed_count
            self.logger.info(f"✅ Successfully processed {processed_count} resource descriptions")
            self.logger.info(f"📄 Successful: {processed_count - failed_count}, Failed: {failed_count}")
            if failed_count > 0:
                self.logger.warning(f"❌ {failed_count} resource descriptions had errors (included in output)")
            return processed_count - failed_count , all_resource
        except Exception as e:
            self.logger.error(f"❌ Failed to save consolidated descriptions file: {e}")
            return 0
    def get_account_id(self) -> str:
        """Get AWS account ID"""
        try:
            if self._account_id is not None:
                return self._account_id
            sts_client = self.session.client('sts')
            self._account_id = sts_client.get_caller_identity()['Account']
            return self._account_id
        except:
            return "unknown"
    def discover_all_resources(self, max_workers: int = 10, resource_filter: str = None) -> List[ResourceInfo]:
        """
        Discover all AWS resources across all supported types using parallel processing
        """
        self.logger.info(f"🚀 Starting comprehensive AWS resource discovery in {self.region}")
        self.logger.info(f"📊 Scanning {len(AWS_RESOURCE_TYPES)} resource types with {max_workers} workers")
        self.stats['start_time'] = datetime.now()
        resource_types_to_scan = AWS_RESOURCE_TYPES
        if resource_filter:
            resource_types_to_scan = [rt for rt in AWS_RESOURCE_TYPES if resource_filter.lower() in rt.lower()]
            self.logger.info(f"🔍 Filtered to {len(resource_types_to_scan)} resource types matching '{resource_filter}'")
        all_resources = []
        if HAS_TQDM:
            progress_bar = tqdm(total=len(resource_types_to_scan), desc="Discovering resources", unit="type")
        executor = ThreadPoolExecutor(max_workers=max_workers)
        try:
            future_to_resource_type = {
                executor.submit(self.discover_resource_type, resource_type): resource_type
                for resource_type in resource_types_to_scan
            }
            for future in as_completed(future_to_resource_type):
                resource_type = future_to_resource_type[future]
                try:
                    resources = future.result()
                    all_resources.extend(resources)
                    if HAS_TQDM:
                        progress_bar.update(1)
                        progress_bar.set_postfix({
                            'Found': len([r for r in all_resources if not r.error]),
                            'Types': f"{self.stats['successful_types']}/{len(resource_types_to_scan)}"
                        })
                except Exception as e:
                    self.logger.error(f"❌ Exception processing {resource_type}: {e}")
                    self.stats['errors'].append({'resource_type': resource_type, 'error': str(e)})
        finally:
            executor.shutdown(wait=True)
        if HAS_TQDM:
            progress_bar.close()
        self.stats['end_time'] = datetime.now()
        self.log_discovery_summary()
        return all_resources
    def log_discovery_summary(self):
        """Log comprehensive discovery summary"""
        duration = self.stats['end_time'] - self.stats['start_time']
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 DISCOVERY SUMMARY")
        self.logger.info("="*60)
        self.logger.info(f"⏱️  Duration: {duration}")
        self.logger.info(f"🎯 Resource Types Scanned: {self.stats['total_resource_types']}")
        self.logger.info(f"✅ Successful: {self.stats['successful_types']}")
        self.logger.info(f"❌ Failed: {self.stats['failed_types']}")
        self.logger.info(f"📦 Total Resources Found: {self.stats['total_resources']}")
        self.logger.info(f"🔗 Resources with ARNs: {self.stats['resources_with_arns']}")
        if self.stats['detailed_descriptions_created'] > 0:
            self.logger.info(f"📄 Detailed Descriptions Created: {self.stats['detailed_descriptions_created']}")
        if self.stats['resources_by_service']:
            self.logger.info("\n🏆 Top Services by Resource Count:")
            for service, count in self.stats['resources_by_service'].most_common(10):
                self.logger.info(f"   {service}: {count} resources")
        if self.stats['errors']:
            self.logger.info(f"\n⚠️  Errors encountered: {len(self.stats['errors'])}")
        self.logger.info("="*60)
    def export_to_json(self, resources: List[ResourceInfo], filename: str = "resources.json"):
        """Export resources to JSON format"""
        output_file = self.output_dir / filename
        export_data = {
            'metadata': {
                'discovery_time': datetime.now().isoformat(),
                'region': self.region,
                'total_resources': len(resources),
                'statistics': self.stats
            },
            'resources': [asdict(resource) for resource in resources]
        }
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        self.logger.info(f"💾 Exported to JSON: {output_file}")
        return output_file
    def export_to_csv(self, resources: List[ResourceInfo], filename: str = "resources.csv"):
        """Export resources to CSV format"""
        output_file = self.output_dir / filename
        valid_resources = [r for r in resources if r.identifier and not r.error]
        if not valid_resources:
            self.logger.warning("No valid resources to export to CSV")
            return None
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ResourceType', 'Service', 'Identifier', 'ARN', 'Region', 
                'PropertiesCount', 'HasError'
            ])
            for resource in valid_resources:
                writer.writerow([
                    resource.resource_type,
                    resource.service,
                    resource.identifier,
                    resource.arn,
                    resource.region,
                    len(resource.properties),
                    bool(resource.error)
                ])
        self.logger.info(f"💾 Exported to CSV: {output_file}")
        return output_file
    def export_to_excel(self, resources: List[ResourceInfo], filename: str = "resources.xlsx"):
        """Export resources to Excel format with multiple sheets"""
        if not HAS_PANDAS:
            self.logger.warning("Pandas not available, skipping Excel export")
            return None
        output_file = self.output_dir / filename
        valid_resources = [r for r in resources if r.identifier and not r.error]
        if not valid_resources:
            self.logger.warning("No valid resources to export to Excel")
            return None
        data = []
        for resource in valid_resources:
            data.append({
                'ResourceType': resource.resource_type,
                'Service': resource.service,
                'Identifier': resource.identifier,
                'ARN': resource.arn,
                'Region': resource.region,
                'PropertiesCount': len(resource.properties),
                'HasProperties': bool(resource.properties)
            })
        df = pd.DataFrame(data)
        summary_data = []
        for service, count in self.stats['resources_by_service'].most_common():
            summary_data.append({'Service': service, 'ResourceCount': count})
        summary_df = pd.DataFrame(summary_data)
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Resources', index=False)
            summary_df.to_excel(writer, sheet_name='Summary by Service', index=False)
            stats_data = [
                ['Metric', 'Value'],
                ['Total Resource Types Scanned', self.stats['total_resource_types']],
                ['Successful Types', self.stats['successful_types']],
                ['Failed Types', self.stats['failed_types']],
                ['Total Resources Found', self.stats['total_resources']],
                ['Discovery Region', self.region],
                ['Discovery Time', self.stats['start_time']],
                ['Duration', str(self.stats['end_time'] - self.stats['start_time']) if self.stats['end_time'] else 'N/A']
            ]
            stats_df = pd.DataFrame(stats_data[1:], columns=stats_data[0])
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
        self.logger.info(f"💾 Exported to Excel: {output_file}")
        return output_file
    def search_resources(self, resources: List[ResourceInfo], query: str) -> List[ResourceInfo]:
        """Search resources by identifier, type, or service"""
        query_lower = query.lower()
        matches = []
        for resource in resources:
            if (query_lower in resource.resource_type.lower() or
                query_lower in resource.identifier.lower() or
                query_lower in resource.service.lower() or
                query_lower in resource.arn.lower()):
                matches.append(resource)
        return matches
    def filter_by_service(self, resources: List[ResourceInfo], service: str) -> List[ResourceInfo]:
        """Filter resources by AWS service"""
        return [r for r in resources if r.service.lower() == service.lower()]
    def generate_report(self, resources: List[ResourceInfo]):
        """Generate a comprehensive HTML report"""
        report_file = self.output_dir / "discovery_report.html"
        valid_resources = [r for r in resources if not r.error]
        services = list(self.stats['resources_by_service'].keys())
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AWS Resource Discovery Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color:
        .summary {{ background-color:
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric .value {{ font-size: 24px; font-weight: bold; color:
        .metric .label {{ font-size: 14px; color:
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid
        th {{ background-color:
        .error {{ color:
        .success {{ color:
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 AWS Resource Discovery Report</h1>
        <p>Region: {self.region} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="summary">
        <h2>📊 Summary</h2>
        <div class="metric">
            <div class="value">{len(valid_resources)}</div>
            <div class="label">Total Resources</div>
        </div>
        <div class="metric">
            <div class="value">{len(services)}</div>
            <div class="label">AWS Services</div>
        </div>
        <div class="metric">
            <div class="value">{self.stats['successful_types']}</div>
            <div class="label">Resource Types</div>
        </div>
        <div class="metric">
            <div class="value">{len(self.stats['errors'])}</div>
            <div class="label">Errors</div>
        </div>
    </div>
    <h2>🏆 Top Services</h2>
    <table>
        <tr><th>Service</th><th>Resource Count</th></tr>
    </table>
    <h2>📋 Sample Resources</h2>
    <table>
        <tr><th>Resource Type</th><th>Identifier</th><th>Service</th><th>Status</th></tr>
        <tr>
            <td>{resource.resource_type}</td>
            <td>{resource.identifier}</td>
            <td>{resource.service}</td>
            <td>{status}</td>
        </tr>
    </table>
    <p><em>This report shows a sample of discovered resources. Full data is available in the exported JSON/CSV files.</em></p>
</body>
</html>
"""
        with open(self.output_dir / "report.html", 'w') as f:
            f.write(html_content)
        self.logger.info(f"📄 HTML report saved to {self.output_dir / 'report.html'}")

    def _flatten_properties_for_neo4j(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten complex properties for Neo4j compatibility"""
        flattened = {}
        
        def flatten_value(value, prefix=""):
            if isinstance(value, dict):
                for k, v in value.items():
                    new_key = f"{prefix}_{k}" if prefix else k
                    flatten_value(v, new_key)
            elif isinstance(value, list):
                if all(isinstance(item, (str, int, float, bool)) for item in value):
                    flattened[prefix] = value
                else:
                    flattened[prefix] = json.dumps(value)
            elif isinstance(value, (str, int, float, bool)) or value is None:
                flattened[prefix] = value
            else:
                flattened[prefix] = json.dumps(value) if value is not None else None
        
        flatten_value(properties)
        return flattened

    def _get_account_id(self) -> str:
        """Get the current AWS account ID"""
        try:
            if self._account_id is not None:
                return self._account_id
            sts_client = self.session.client('sts')
            response = sts_client.get_caller_identity()
            self._account_id = response.get('Account', 'unknown')
            return self._account_id
        except Exception as e:
            self.logger.warning(f"Could not retrieve account ID: {e}")
            return 'unknown'
    def update_graph_database(self, resources: Dict[str, Any], db_url: str, db_user: str, db_password: str, reset_graph: bool = False, account_name: str = None):
        """Update Neo4j graph database with discovered resources, relationships, and cross-account connectivity"""
        self.logger.info("Connecting to graph database...")
        try:
            driver = GraphDatabase.driver(f"bolt://{db_url}", auth=(db_user, db_password))
            with driver.session() as session:
                if reset_graph:
                    self.logger.info("Resetting graph database...")
                    session.run("MATCH (n) DETACH DELETE n")
                account_id = self._get_account_id()
                self.logger.info(f"Creating account node: {account_id}")
                account_query = """
                MERGE (a:Account {id: $account_id})
                SET a.name = $account_name,
                    a.created_at = datetime()
                """
                session.run(account_query, 
                            account_id=account_id, 
                            account_name=account_name or f"Account-{account_id}")
                self.logger.info("Updating graph database with discovered resources...")
                for arn, info in resources.items():
                    safe_resource_type = info['resource_type'].replace('-', '_').replace('.', '_').replace(':', '_')
                    flattened_properties = self._flatten_properties_for_neo4j(info['properties'])
                    service = info.get('service', '')
                    is_global = self._is_global_service(service)
                    neo4j_properties = {
                        'arn': arn,
                        'resource_type': info['resource_type'],
                        'service': info.get('service', ''),
                        'account_id': account_id,
                        'identifier': info.get('identifier', ''),
                        **flattened_properties
                    }
                    if not is_global:
                        neo4j_properties['region'] = info.get('region', '')
                    query = f"""
                            MERGE (r:{safe_resource_type} {{arn: $arn}})
                            SET r += $properties
                            """
                    session.run(
                        query,
                        arn=arn,
                        properties=neo4j_properties
                    )
                    resource_account_query = f"""
                    MATCH (account:Account {{id: $account_id}})
                    MATCH (res:{safe_resource_type} {{arn: $arn}})
                    MERGE (account)-[:OWNS]->(res)
                    """
                    session.run(resource_account_query, 
                               arn=arn, 
                               account_id=account_id)
                self.logger.info("Creating route rules from route tables...")
                self._create_route_rules(session, resources)
                self.logger.info("Creating enhanced service sub-components...")
                self._create_enhanced_service_components(session, resources)
                self.logger.info("Creating resource-to-resource relationships...")
                self._create_resource_relationships(session, resources)
                self._log_cross_account_connections(session)
            driver.close()
            self.logger.info("Graph database updated successfully.")
        except Neo4jError as e:
            self.logger.error(f"❌ Failed to update graph database: {e}")
    def _create_route_rules(self, session, resources: Dict[str, Any]):
        """Create individual RouteRule nodes from RouteTable resources"""
        try:
            ec2_client = self.get_service_client('ec2')
            route_tables = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::EC2::RouteTable'
            ]
            if not route_tables:
                self.logger.debug("No route tables found for route rule extraction")
                return
            self.logger.info(f"Processing {len(route_tables)} route tables for route rule extraction")
            for route_table_arn, route_table_info in route_tables:
                route_table_id = route_table_info.get('identifier', '')
                if not route_table_id:
                    continue
                try:
                    response = ec2_client.describe_route_tables(RouteTableIds=[route_table_id])
                    for route_table in response.get('RouteTables', []):
                        routes = route_table.get('Routes', [])
                        for i, route in enumerate(routes):
                            route_id = f"{route_table_id}_route_{i}"
                            route_arn = f"arn:aws:ec2:{self.region}:{self._get_account_id()}:route/{route_id}"
                            route_properties = {
                                'route_id': route_id,
                                'route_table_id': route_table_id,
                                'destination_cidr_block': route.get('DestinationCidrBlock', ''),
                                'destination_ipv6_cidr_block': route.get('DestinationIpv6CidrBlock', ''),
                                'destination_prefix_list_id': route.get('DestinationPrefixListId', ''),
                                'gateway_id': route.get('GatewayId', ''),
                                'instance_id': route.get('InstanceId', ''),
                                'instance_owner_id': route.get('InstanceOwnerId', ''),
                                'network_interface_id': route.get('NetworkInterfaceId', ''),
                                'transit_gateway_id': route.get('TransitGatewayId', ''),
                                'vpc_peering_connection_id': route.get('VpcPeeringConnectionId', ''),
                                'nat_gateway_id': route.get('NatGatewayId', ''),
                                'carrier_gateway_id': route.get('CarrierGatewayId', ''),
                                'local_gateway_id': route.get('LocalGatewayId', ''),
                                'core_network_arn': route.get('CoreNetworkArn', ''),
                                'state': route.get('State', ''),
                                'origin': route.get('Origin', ''),
                                'arn': route_arn,
                                'resource_type': 'AWS::EC2::RouteRule',
                                'service': 'ec2',
                                'region': self.region,
                                'account_id': self._get_account_id()
                            }
                            route_properties = {k: v for k, v in route_properties.items() if v}
                            create_route_query = """
                            MERGE (rr:RouteRule {arn: $arn})
                            SET rr += $properties
                            """
                            session.run(create_route_query, arn=route_arn, properties=route_properties)
                            account_route_query = """
                            MATCH (account:Account {id: $account_id})
                            MATCH (rr:RouteRule {arn: $route_arn})
                            MERGE (account)-[:OWNS]->(rr)
                            """
                            session.run(account_route_query, 
                                       account_id=self._get_account_id(),
                                       route_arn=route_arn)
                            relationship_query = """
                            MATCH (rt:AWS_EC2_RouteTable {arn: $route_table_arn})
                            MATCH (rr:RouteRule {arn: $route_arn})
                            MERGE (rt)-[:HAS_ROUTE]->(rr)
                            """
                            session.run(relationship_query, 
                                       route_table_arn=route_table_arn, 
                                       route_arn=route_arn)
                            self._create_route_target_relationships(session, route_properties, resources)
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed routes for route table {route_table_id}: {e}")
                    continue
            self.logger.info("Route rule creation completed")
        except Exception as e:
            self.logger.error(f"Failed to create route rules: {e}")
    def _create_route_target_relationships(self, session, route_properties: Dict[str, Any], resources: Dict[str, Any]):
        """Create relationships from route rules to their target resources"""
        route_arn = route_properties.get('arn')
        target_mappings = {
            'gateway_id': 'AWS::EC2::InternetGateway',
            'nat_gateway_id': 'AWS::EC2::NatGateway', 
            'instance_id': 'AWS::EC2::Instance',
            'network_interface_id': 'AWS::EC2::NetworkInterface',
            'transit_gateway_id': 'AWS::EC2::TransitGateway',
            'vpc_peering_connection_id': 'AWS::EC2::VPCPeeringConnection'
        }
        for prop_name, resource_type in target_mappings.items():
            target_id = route_properties.get(prop_name)
            if target_id and target_id != 'local':
                target_arn = None
                for arn, info in resources.items():
                    if (info.get('resource_type') == resource_type and 
                        info.get('identifier') == target_id):
                        target_arn = arn
                        break
                if target_arn:
                    safe_resource_type = resource_type.replace('-', '_').replace('.', '_').replace(':', '_')
                    relationship_query = f"""
                    MATCH (rr:RouteRule {{arn: $route_arn}})
                    MATCH (target:{safe_resource_type} {{arn: $target_arn}})
                    MERGE (rr)-[:ROUTES_TO]->(target)
                    """
                    session.run(relationship_query, route_arn=route_arn, target_arn=target_arn)
    def _create_enhanced_service_components(self, session, resources: Dict[str, Any]):
        """Create detailed sub-components for RDS, ElastiCache, RabbitMQ, and API Gateway"""
        try:
            self.logger.info("Creating RDS sub-components...")
            self._create_rds_components(session, resources)
            self.logger.info("Creating ElastiCache sub-components...")
            self._create_elasticache_components(session, resources)
            self.logger.info("Creating Amazon MQ (RabbitMQ) sub-components...")
            self._create_mq_components(session, resources)
            self.logger.info("Creating API Gateway sub-components...")
            self._create_apigateway_components(session, resources)
            self.logger.info("Creating Transit Gateway sub-components...")
            self._create_transit_gateway_components(session, resources)
            self.logger.info("Creating VPC Peering sub-components...")
            self._create_vpc_peering_components(session, resources)
        except Exception as e:
            self.logger.error(f"Failed to create enhanced service components: {e}")
    def _create_rds_components(self, session, resources: Dict[str, Any]):
        """Create RDS sub-components: instances, clusters, snapshots, parameter groups, subnet groups"""
        try:
            rds_client = self.get_service_client('rds')
            rds_clusters = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::RDS::DBCluster'
            ]
            rds_instances = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::RDS::DBInstance'
            ]
            for cluster_arn, cluster_info in rds_clusters:
                cluster_id = cluster_info.get('identifier', '')
                if not cluster_id:
                    continue
                try:
                    response = rds_client.describe_db_clusters(DBClusterIdentifier=cluster_id)
                    for cluster in response.get('DBClusters', []):
                        for member in cluster.get('DBClusterMembers', []):
                            instance_id = member.get('DBInstanceIdentifier')
                            if instance_id:
                                instance_arn = f"arn:aws:rds:{self.region}:{self._get_account_id()}:db:{instance_id}"
                                member_query = """
                                MATCH (cluster:AWS_RDS_DBCluster {arn: $cluster_arn})
                                MERGE (instance:RDSClusterMember {
                                    arn: $instance_arn,
                                    instance_id: $instance_id,
                                    is_writer: $is_writer,
                                    promotion_tier: $promotion_tier,
                                    resource_type: 'AWS::RDS::DBClusterMember',
                                    service: 'rds',
                                    region: $region,
                                    account_id: $account_id
                                })
                                WITH instance
                                MATCH (account:Account {id: $account_id})
                                MERGE (account)-[:OWNS]->(instance)
                                WITH instance
                                MATCH (cluster:AWS_RDS_DBCluster {arn: $cluster_arn})
                                MERGE (cluster)-[:HAS_MEMBER]->(instance)
                                """
                                session.run(member_query,
                                           cluster_arn=cluster_arn,
                                           instance_arn=instance_arn,
                                           instance_id=instance_id,
                                           is_writer=member.get('IsClusterWriter', False),
                                           promotion_tier=member.get('PromotionTier', 0),
                                           region=self.region,
                                           account_id=self._get_account_id())
                        param_group = cluster.get('DBClusterParameterGroup')
                        if param_group:
                            param_group_arn = f"arn:aws:rds:{self.region}:{self._get_account_id()}:cluster-pg:{param_group}"
                            param_query = """
                            MATCH (cluster:AWS_RDS_DBCluster {arn: $cluster_arn})
                            MERGE (pg:RDSParameterGroup {
                                arn: $param_group_arn,
                                name: $param_group,
                                resource_type: 'AWS::RDS::DBClusterParameterGroup',
                                service: 'rds',
                                region: $region,
                                account_id: $account_id
                            })
                            WITH pg
                            MATCH (account:Account {id: $account_id})
                            MERGE (account)-[:OWNS]->(pg)
                            WITH pg
                            MATCH (cluster:AWS_RDS_DBCluster {arn: $cluster_arn})
                            MERGE (cluster)-[:USES_PARAMETER_GROUP]->(pg)
                            """
                            session.run(param_query,
                                       cluster_arn=cluster_arn,
                                       param_group_arn=param_group_arn,
                                       param_group=param_group,
                                       region=self.region,
                                       account_id=self._get_account_id())
                        subnet_group = cluster.get('DBSubnetGroup')
                        if subnet_group:
                            subnet_group_arn = f"arn:aws:rds:{self.region}:{self._get_account_id()}:subgrp:{subnet_group}"
                            subnet_query = """
                            MATCH (cluster:AWS_RDS_DBCluster {arn: $cluster_arn})
                            MERGE (sg:RDSSubnetGroup {
                                arn: $subnet_group_arn,
                                name: $subnet_group,
                                resource_type: 'AWS::RDS::DBSubnetGroup',
                                service: 'rds',
                                region: $region,
                                account_id: $account_id
                            })
                            WITH sg
                            MATCH (account:Account {id: $account_id})
                            MERGE (account)-[:OWNS]->(sg)
                            WITH sg
                            MATCH (cluster:AWS_RDS_DBCluster {arn: $cluster_arn})
                            MERGE (cluster)-[:USES_SUBNET_GROUP]->(sg)
                            """
                            session.run(subnet_query,
                                       cluster_arn=cluster_arn,
                                       subnet_group_arn=subnet_group_arn,
                                       subnet_group=subnet_group,
                                       region=self.region,
                                       account_id=self._get_account_id())
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for RDS cluster {cluster_id}: {e}")
            for instance_arn, instance_info in rds_instances:
                instance_id = instance_info.get('identifier', '')
                if not instance_id:
                    continue
                try:
                    response = rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
                    for instance in response.get('DBInstances', []):
                        for param_group in instance.get('DBParameterGroups', []):
                            param_group_name = param_group.get('DBParameterGroupName')
                            if param_group_name:
                                param_group_arn = f"arn:aws:rds:{self.region}:{self._get_account_id()}:pg:{param_group_name}"
                                param_query = """
                                MATCH (instance:AWS_RDS_DBInstance {arn: $instance_arn})
                                MERGE (pg:RDSParameterGroup {
                                    arn: $param_group_arn,
                                    name: $param_group_name,
                                    status: $status,
                                    resource_type: 'AWS::RDS::DBParameterGroup',
                                    service: 'rds',
                                    region: $region
                                })
                                MERGE (instance)-[:USES_PARAMETER_GROUP]->(pg)
                                """
                                session.run(param_query,
                                           instance_arn=instance_arn,
                                           param_group_arn=param_group_arn,
                                           param_group_name=param_group_name,
                                           status=param_group.get('ParameterApplyStatus', ''),
                                           region=self.region)
                        for option_group in instance.get('OptionGroupMemberships', []):
                            option_group_name = option_group.get('OptionGroupName')
                            if option_group_name:
                                option_group_arn = f"arn:aws:rds:{self.region}:{self._get_account_id()}:og:{option_group_name}"
                                option_query = """
                                MATCH (instance:AWS_RDS_DBInstance {arn: $instance_arn})
                                MERGE (og:RDSOptionGroup {
                                    arn: $option_group_arn,
                                    name: $option_group_name,
                                    status: $status,
                                    resource_type: 'AWS::RDS::OptionGroup',
                                    service: 'rds',
                                    region: $region
                                })
                                MERGE (instance)-[:USES_OPTION_GROUP]->(og)
                                """
                                session.run(option_query,
                                           instance_arn=instance_arn,
                                           option_group_arn=option_group_arn,
                                           option_group_name=option_group_name,
                                           status=option_group.get('Status', ''),
                                           region=self.region)
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for RDS instance {instance_id}: {e}")
            try:
                snapshots_response = rds_client.describe_db_snapshots(OwnerFilter='self', MaxRecords=100)
                for snapshot in snapshots_response.get('DBSnapshots', []):
                    snapshot_id = snapshot.get('DBSnapshotIdentifier')
                    source_db = snapshot.get('DBInstanceIdentifier')
                    if snapshot_id:
                        snapshot_arn = f"arn:aws:rds:{self.region}:{self._get_account_id()}:snapshot:{snapshot_id}"
                        base_snapshot_properties = {
                            'arn': snapshot_arn,
                            'snapshot_id': snapshot_id,
                            'source_db_instance': source_db or '',
                            'snapshot_type': snapshot.get('SnapshotType', ''),
                            'status': snapshot.get('Status', ''),
                            'create_time': str(snapshot.get('SnapshotCreateTime', '')),
                            'engine': snapshot.get('Engine', ''),
                            'engine_version': snapshot.get('EngineVersion', ''),
                            'allocated_storage': snapshot.get('AllocatedStorage', 0),
                            'encrypted': snapshot.get('Encrypted', False),
                            'resource_type': 'AWS::RDS::DBSnapshot',
                            'service': 'rds'
                        }
                        snapshot_properties = self._build_node_properties(base_snapshot_properties, 'rds')
                        snapshot_properties = {k: v for k, v in snapshot_properties.items() if v}
                        snapshot_query = """
                        MERGE (snapshot:RDSSnapshot {arn: $arn})
                        SET snapshot += $properties
                        WITH snapshot
                        MATCH (account:Account {id: $account_id})
                        MERGE (account)-[:OWNS]->(snapshot)
                        """
                        session.run(snapshot_query, arn=snapshot_arn, properties=snapshot_properties, account_id=self._get_account_id())
                        if source_db:
                            source_arn = f"arn:aws:rds:{self.region}:{self._get_account_id()}:db:{source_db}"
                            source_query = """
                            MATCH (instance:AWS_RDS_DBInstance {arn: $source_arn})
                            MATCH (snapshot:RDSSnapshot {arn: $snapshot_arn})
                            MERGE (instance)-[:HAS_SNAPSHOT]->(snapshot)
                            """
                            session.run(source_query, source_arn=source_arn, snapshot_arn=snapshot_arn)
            except Exception as e:
                self.logger.warning(f"Failed to get RDS snapshots: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create RDS components: {e}")
    def _create_elasticache_components(self, session, resources: Dict[str, Any]):
        """Create ElastiCache sub-components: clusters, nodes, parameter groups, subnet groups"""
        try:
            elasticache_client = self.get_service_client('elasticache')
            cache_clusters = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::ElastiCache::CacheCluster'
            ]
            replication_groups = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::ElastiCache::ReplicationGroup'
            ]
            for cluster_arn, cluster_info in cache_clusters:
                cluster_id = cluster_info.get('identifier', '')
                if not cluster_id:
                    continue
                try:
                    response = elasticache_client.describe_cache_clusters(
                        CacheClusterId=cluster_id,
                        ShowCacheNodeInfo=True
                    )
                    for cluster in response.get('CacheClusters', []):
                        for node in cluster.get('CacheNodes', []):
                            node_id = node.get('CacheNodeId')
                            if node_id:
                                node_arn = f"arn:aws:elasticache:{self.region}:{self._get_account_id()}:cachenode:{cluster_id}:{node_id}"
                                node_properties = {
                                    'arn': node_arn,
                                    'node_id': node_id,
                                    'cluster_id': cluster_id,
                                    'node_status': node.get('CacheNodeStatus', ''),
                                    'creation_time': str(node.get('CacheNodeCreateTime', '')),
                                    'endpoint_address': node.get('Endpoint', {}).get('Address', ''),
                                    'endpoint_port': node.get('Endpoint', {}).get('Port', 0),
                                    'parameter_group_status': node.get('ParameterGroupStatus', ''),
                                    'resource_type': 'AWS::ElastiCache::CacheNode',
                                    'service': 'elasticache',
                                    'region': self.region
                                }
                                node_properties = {k: v for k, v in node_properties.items() if v}
                                node_query = """
                                MERGE (node:ElastiCacheNode {arn: $arn})
                                SET node += $properties
                                """
                                session.run(node_query, arn=node_arn, properties=node_properties)
                                cluster_node_query = """
                                MATCH (cluster:AWS_ElastiCache_CacheCluster {arn: $cluster_arn})
                                MATCH (node:ElastiCacheNode {arn: $node_arn})
                                MERGE (cluster)-[:HAS_NODE]->(node)
                                """
                                session.run(cluster_node_query, cluster_arn=cluster_arn, node_arn=node_arn)
                        param_group = cluster.get('CacheParameterGroup', {}).get('CacheParameterGroupName')
                        if param_group:
                            param_group_arn = f"arn:aws:elasticache:{self.region}:{self._get_account_id()}:parametergroup:{param_group}"
                            param_query = """
                            MATCH (cluster:AWS_ElastiCache_CacheCluster {arn: $cluster_arn})
                            MERGE (pg:ElastiCacheParameterGroup {
                                arn: $param_group_arn,
                                name: $param_group,
                                status: $status,
                                resource_type: 'AWS::ElastiCache::ParameterGroup',
                                service: 'elasticache',
                                region: $region
                            })
                            MERGE (cluster)-[:USES_PARAMETER_GROUP]->(pg)
                            """
                            session.run(param_query,
                                       cluster_arn=cluster_arn,
                                       param_group_arn=param_group_arn,
                                       param_group=param_group,
                                       status=cluster.get('CacheParameterGroup', {}).get('ParameterApplyStatus', ''),
                                       region=self.region)
                        subnet_group = cluster.get('CacheSubnetGroupName')
                        if subnet_group:
                            subnet_group_arn = f"arn:aws:elasticache:{self.region}:{self._get_account_id()}:subnetgroup:{subnet_group}"
                            subnet_query = """
                            MATCH (cluster:AWS_ElastiCache_CacheCluster {arn: $cluster_arn})
                            MERGE (sg:ElastiCacheSubnetGroup {
                                arn: $subnet_group_arn,
                                name: $subnet_group,
                                resource_type: 'AWS::ElastiCache::SubnetGroup',
                                service: 'elasticache',
                                region: $region
                            })
                            MERGE (cluster)-[:USES_SUBNET_GROUP]->(sg)
                            """
                            session.run(subnet_query,
                                       cluster_arn=cluster_arn,
                                       subnet_group_arn=subnet_group_arn,
                                       subnet_group=subnet_group,
                                       region=self.region)
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for ElastiCache cluster {cluster_id}: {e}")
            for rg_arn, rg_info in replication_groups:
                rg_id = rg_info.get('identifier', '')
                if not rg_id:
                    continue
                try:
                    response = elasticache_client.describe_replication_groups(ReplicationGroupId=rg_id)
                    for rg in response.get('ReplicationGroups', []):
                        for node_group in rg.get('NodeGroups', []):
                            node_group_id = node_group.get('NodeGroupId')
                            if node_group_id:
                                node_group_arn = f"arn:aws:elasticache:{self.region}:{self._get_account_id()}:nodegroup:{rg_id}:{node_group_id}"
                                node_group_properties = {
                                    'arn': node_group_arn,
                                    'node_group_id': node_group_id,
                                    'replication_group_id': rg_id,
                                    'status': node_group.get('Status', ''),
                                    'primary_endpoint': node_group.get('PrimaryEndpoint', {}).get('Address', ''),
                                    'reader_endpoint': node_group.get('ReaderEndpoint', {}).get('Address', ''),
                                    'slots': node_group.get('Slots', ''),
                                    'resource_type': 'AWS::ElastiCache::NodeGroup',
                                    'service': 'elasticache',
                                    'region': self.region
                                }
                                node_group_properties = {k: v for k, v in node_group_properties.items() if v}
                                ng_query = """
                                MERGE (ng:ElastiCacheNodeGroup {arn: $arn})
                                SET ng += $properties
                                """
                                session.run(ng_query, arn=node_group_arn, properties=node_group_properties)
                                rg_ng_query = """
                                MATCH (rg:AWS_ElastiCache_ReplicationGroup {arn: $rg_arn})
                                MATCH (ng:ElastiCacheNodeGroup {arn: $ng_arn})
                                MERGE (rg)-[:HAS_NODE_GROUP]->(ng)
                                """
                                session.run(rg_ng_query, rg_arn=rg_arn, ng_arn=node_group_arn)
                                for member in node_group.get('NodeGroupMembers', []):
                                    cache_cluster_id = member.get('CacheClusterId')
                                    if cache_cluster_id:
                                        member_arn = f"arn:aws:elasticache:{self.region}:{self._get_account_id()}:member:{cache_cluster_id}"
                                        member_properties = {
                                            'arn': member_arn,
                                            'cache_cluster_id': cache_cluster_id,
                                            'node_group_id': node_group_id,
                                            'current_role': member.get('CurrentRole', ''),
                                            'preferred_availability_zone': member.get('PreferredAvailabilityZone', ''),
                                            'read_endpoint': member.get('ReadEndpoint', {}).get('Address', ''),
                                            'resource_type': 'AWS::ElastiCache::NodeGroupMember',
                                            'service': 'elasticache',
                                            'region': self.region
                                        }
                                        member_properties = {k: v for k, v in member_properties.items() if v}
                                        member_query = """
                                        MERGE (member:ElastiCacheNodeGroupMember {arn: $arn})
                                        SET member += $properties
                                        """
                                        session.run(member_query, arn=member_arn, properties=member_properties)
                                        ng_member_query = """
                                        MATCH (ng:ElastiCacheNodeGroup {arn: $ng_arn})
                                        MATCH (member:ElastiCacheNodeGroupMember {arn: $member_arn})
                                        MERGE (ng)-[:HAS_MEMBER]->(member)
                                        """
                                        session.run(ng_member_query, ng_arn=node_group_arn, member_arn=member_arn)
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for ElastiCache replication group {rg_id}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create ElastiCache components: {e}")
    def _create_mq_components(self, session, resources: Dict[str, Any]):
        """Create Amazon MQ (RabbitMQ) sub-components: brokers, configurations, users"""
        try:
            mq_client = self.get_service_client('mq')
            mq_brokers = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::MQ::Broker'
            ]
            for broker_arn, broker_info in mq_brokers:
                broker_id = broker_info.get('identifier', '')
                if not broker_id:
                    continue
                try:
                    response = mq_client.describe_broker(BrokerId=broker_id)
                    for instance in response.get('BrokerInstances', []):
                        instance_id = instance.get('ConsoleURL', '').split('/')[-1] if instance.get('ConsoleURL') else f"{broker_id}_instance"
                        instance_arn = f"arn:aws:mq:{self.region}:{self._get_account_id()}:broker-instance:{broker_id}:{instance_id}"
                        instance_properties = {
                            'arn': instance_arn,
                            'broker_id': broker_id,
                            'console_url': instance.get('ConsoleURL', ''),
                            'endpoints': str(instance.get('Endpoints', [])),
                            'ip_address': instance.get('IpAddress', ''),
                            'resource_type': 'AWS::MQ::BrokerInstance',
                            'service': 'mq',
                            'region': self.region
                        }
                        instance_properties = {k: v for k, v in instance_properties.items() if v}
                        instance_query = """
                        MERGE (instance:MQBrokerInstance {arn: $arn})
                        SET instance += $properties
                        """
                        session.run(instance_query, arn=instance_arn, properties=instance_properties)
                        broker_instance_query = """
                        MATCH (broker:AWS_MQ_Broker {arn: $broker_arn})
                        MATCH (instance:MQBrokerInstance {arn: $instance_arn})
                        MERGE (broker)-[:HAS_INSTANCE]->(instance)
                        """
                        session.run(broker_instance_query, broker_arn=broker_arn, instance_arn=instance_arn)
                    config = response.get('Configurations', {}).get('Current')
                    if config and config.get('Id'):
                        config_arn = f"arn:aws:mq:{self.region}:{self._get_account_id()}:configuration:{config.get('Id')}"
                        config_query = """
                        MATCH (broker:AWS_MQ_Broker {arn: $broker_arn})
                        MERGE (config:MQConfiguration {
                            arn: $config_arn,
                            config_id: $config_id,
                            revision: $revision,
                            resource_type: 'AWS::MQ::Configuration',
                            service: 'mq',
                            region: $region
                        })
                        MERGE (broker)-[:USES_CONFIGURATION]->(config)
                        """
                        session.run(config_query,
                                   broker_arn=broker_arn,
                                   config_arn=config_arn,
                                   config_id=config.get('Id'),
                                   revision=config.get('Revision', 0),
                                   region=self.region)
                    try:
                        users_response = mq_client.list_users(BrokerId=broker_id)
                        for user in users_response.get('Users', []):
                            username = user.get('Username')
                            if username:
                                user_arn = f"arn:aws:mq:{self.region}:{self._get_account_id()}:user:{broker_id}:{username}"
                                user_properties = {
                                    'arn': user_arn,
                                    'username': username,
                                    'broker_id': broker_id,
                                    'console_access': user.get('ConsoleAccess', False),
                                    'groups': str(user.get('Groups', [])),
                                    'resource_type': 'AWS::MQ::User',
                                    'service': 'mq',
                                    'region': self.region
                                }
                                user_properties = {k: v for k, v in user_properties.items() if v}
                                user_query = """
                                MERGE (user:MQUser {arn: $arn})
                                SET user += $properties
                                """
                                session.run(user_query, arn=user_arn, properties=user_properties)
                                broker_user_query = """
                                MATCH (broker:AWS_MQ_Broker {arn: $broker_arn})
                                MATCH (user:MQUser {arn: $user_arn})
                                MERGE (broker)-[:HAS_USER]->(user)
                                """
                                session.run(broker_user_query, broker_arn=broker_arn, user_arn=user_arn)
                    except Exception as e:
                        self.logger.warning(f"Failed to get users for MQ broker {broker_id}: {e}")
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for MQ broker {broker_id}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create MQ components: {e}")
    def _create_apigateway_components(self, session, resources: Dict[str, Any]):
        """Create API Gateway sub-components: stages, resources, methods, deployments"""
        try:
            apigw_client = self.get_service_client('apigateway')
            apigwv2_client = self.get_service_client('apigatewayv2')
            rest_apis = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::ApiGateway::RestApi'
            ]
            v2_apis = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::ApiGatewayV2::Api'
            ]
            for api_arn, api_info in rest_apis:
                api_id = api_info.get('identifier', '')
                if not api_id:
                    continue
                try:
                    stages_response = apigw_client.get_stages(restApiId=api_id)
                    for stage in stages_response.get('item', []):
                        stage_name = stage.get('stageName')
                        if stage_name:
                            stage_arn = f"arn:aws:apigateway:{self.region}::/restapis/{api_id}/stages/{stage_name}"
                            stage_properties = {
                                'arn': stage_arn,
                                'stage_name': stage_name,
                                'api_id': api_id,
                                'deployment_id': stage.get('deploymentId', ''),
                                'description': stage.get('description', ''),
                                'cache_cluster_enabled': stage.get('cacheClusterEnabled', False),
                                'cache_cluster_size': stage.get('cacheClusterSize', ''),
                                'created_date': str(stage.get('createdDate', '')),
                                'last_updated_date': str(stage.get('lastUpdatedDate', '')),
                                'resource_type': 'AWS::ApiGateway::Stage',
                                'service': 'apigateway',
                                'region': self.region
                            }
                            stage_properties = {k: v for k, v in stage_properties.items() if v}
                            stage_query = """
                            MERGE (stage:ApiGatewayStage {arn: $arn})
                            SET stage += $properties
                            """
                            session.run(stage_query, arn=stage_arn, properties=stage_properties)
                            api_stage_query = """
                            MATCH (api:AWS_ApiGateway_RestApi {arn: $api_arn})
                            MATCH (stage:ApiGatewayStage {arn: $stage_arn})
                            MERGE (api)-[:HAS_STAGE]->(stage)
                            """
                            session.run(api_stage_query, api_arn=api_arn, stage_arn=stage_arn)
                    resources_response = apigw_client.get_resources(restApiId=api_id)
                    for resource in resources_response.get('items', []):
                        resource_id = resource.get('id')
                        if resource_id:
                            resource_arn = f"arn:aws:apigateway:{self.region}::/restapis/{api_id}/resources/{resource_id}"
                            resource_properties = {
                                'arn': resource_arn,
                                'resource_id': resource_id,
                                'api_id': api_id,
                                'parent_id': resource.get('parentId', ''),
                                'path_part': resource.get('pathPart', ''),
                                'path': resource.get('path', ''),
                                'resource_type': 'AWS::ApiGateway::Resource',
                                'service': 'apigateway',
                                'region': self.region
                            }
                            resource_properties = {k: v for k, v in resource_properties.items() if v}
                            resource_query = """
                            MERGE (res:ApiGatewayResource {arn: $arn})
                            SET res += $properties
                            """
                            session.run(resource_query, arn=resource_arn, properties=resource_properties)
                            api_resource_query = """
                            MATCH (api:AWS_ApiGateway_RestApi {arn: $api_arn})
                            MATCH (res:ApiGatewayResource {arn: $res_arn})
                            MERGE (api)-[:HAS_RESOURCE]->(res)
                            """
                            session.run(api_resource_query, api_arn=api_arn, res_arn=resource_arn)
                            for http_method in resource.get('resourceMethods', {}):
                                method_arn = f"arn:aws:apigateway:{self.region}::/restapis/{api_id}/resources/{resource_id}/methods/{http_method}"
                                method_properties = {
                                    'arn': method_arn,
                                    'http_method': http_method,
                                    'resource_id': resource_id,
                                    'api_id': api_id,
                                    'resource_type': 'AWS::ApiGateway::Method',
                                    'service': 'apigateway',
                                    'region': self.region
                                }
                                method_query = """
                                MERGE (method:ApiGatewayMethod {arn: $arn})
                                SET method += $properties
                                """
                                session.run(method_query, arn=method_arn, properties=method_properties)
                                resource_method_query = """
                                MATCH (res:ApiGatewayResource {arn: $res_arn})
                                MATCH (method:ApiGatewayMethod {arn: $method_arn})
                                MERGE (res)-[:HAS_METHOD]->(method)
                                """
                                session.run(resource_method_query, res_arn=resource_arn, method_arn=method_arn)
                    deployments_response = apigw_client.get_deployments(restApiId=api_id)
                    for deployment in deployments_response.get('items', []):
                        deployment_id = deployment.get('id')
                        if deployment_id:
                            deployment_arn = f"arn:aws:apigateway:{self.region}::/restapis/{api_id}/deployments/{deployment_id}"
                            deployment_properties = {
                                'arn': deployment_arn,
                                'deployment_id': deployment_id,
                                'api_id': api_id,
                                'description': deployment.get('description', ''),
                                'created_date': str(deployment.get('createdDate', '')),
                                'resource_type': 'AWS::ApiGateway::Deployment',
                                'service': 'apigateway',
                                'region': self.region
                            }
                            deployment_properties = {k: v for k, v in deployment_properties.items() if v}
                            deployment_query = """
                            MERGE (deployment:ApiGatewayDeployment {arn: $arn})
                            SET deployment += $properties
                            """
                            session.run(deployment_query, arn=deployment_arn, properties=deployment_properties)
                            api_deployment_query = """
                            MATCH (api:AWS_ApiGateway_RestApi {arn: $api_arn})
                            MATCH (deployment:ApiGatewayDeployment {arn: $deployment_arn})
                            MERGE (api)-[:HAS_DEPLOYMENT]->(deployment)
                            """
                            session.run(api_deployment_query, api_arn=api_arn, deployment_arn=deployment_arn)
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for API Gateway REST API {api_id}: {e}")
            for api_arn, api_info in v2_apis:
                api_id = api_info.get('identifier', '')
                if not api_id:
                    continue
                try:
                    stages_response = apigwv2_client.get_stages(ApiId=api_id)
                    for stage in stages_response.get('Items', []):
                        stage_name = stage.get('StageName')
                        if stage_name:
                            stage_arn = f"arn:aws:apigateway:{self.region}::/apis/{api_id}/stages/{stage_name}"
                            stage_properties = {
                                'arn': stage_arn,
                                'stage_name': stage_name,
                                'api_id': api_id,
                                'deployment_id': stage.get('DeploymentId', ''),
                                'description': stage.get('Description', ''),
                                'auto_deploy': stage.get('AutoDeploy', False),
                                'created_date': str(stage.get('CreatedDate', '')),
                                'last_updated_date': str(stage.get('LastUpdatedDate', '')),
                                'resource_type': 'AWS::ApiGatewayV2::Stage',
                                'service': 'apigatewayv2',
                                'region': self.region
                            }
                            stage_properties = {k: v for k, v in stage_properties.items() if v}
                            stage_query = """
                            MERGE (stage:ApiGatewayV2Stage {arn: $arn})
                            SET stage += $properties
                            """
                            session.run(stage_query, arn=stage_arn, properties=stage_properties)
                            api_stage_query = """
                            MATCH (api:AWS_ApiGatewayV2_Api {arn: $api_arn})
                            MATCH (stage:ApiGatewayV2Stage {arn: $stage_arn})
                            MERGE (api)-[:HAS_STAGE]->(stage)
                            """
                            session.run(api_stage_query, api_arn=api_arn, stage_arn=stage_arn)
                    routes_response = apigwv2_client.get_routes(ApiId=api_id)
                    for route in routes_response.get('Items', []):
                        route_id = route.get('RouteId')
                        if route_id:
                            route_arn = f"arn:aws:apigateway:{self.region}::/apis/{api_id}/routes/{route_id}"
                            route_properties = {
                                'arn': route_arn,
                                'route_id': route_id,
                                'api_id': api_id,
                                'route_key': route.get('RouteKey', ''),
                                'target': route.get('Target', ''),
                                'authorization_type': route.get('AuthorizationType', ''),
                                'authorizer_id': route.get('AuthorizerId', ''),
                                'operation_name': route.get('OperationName', ''),
                                'resource_type': 'AWS::ApiGatewayV2::Route',
                                'service': 'apigatewayv2',
                                'region': self.region
                            }
                            route_properties = {k: v for k, v in route_properties.items() if v}
                            route_query = """
                            MERGE (route:ApiGatewayV2Route {arn: $arn})
                            SET route += $properties
                            """
                            session.run(route_query, arn=route_arn, properties=route_properties)
                            api_route_query = """
                            MATCH (api:AWS_ApiGatewayV2_Api {arn: $api_arn})
                            MATCH (route:ApiGatewayV2Route {arn: $route_arn})
                            MERGE (api)-[:HAS_ROUTE]->(route)
                            """
                            session.run(api_route_query, api_arn=api_arn, route_arn=route_arn)
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for API Gateway v2 API {api_id}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create API Gateway components: {e}")
    def _create_transit_gateway_components(self, session, resources: Dict[str, Any]):
        """Create Transit Gateway sub-components: attachments, route tables, associations, propagations"""
        try:
            ec2_client = self.get_service_client('ec2')
            transit_gateways = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::EC2::TransitGateway'
            ]
            for tgw_arn, tgw_info in transit_gateways:
                tgw_id = tgw_info.get('identifier', '')
                if not tgw_id:
                    continue
                try:
                    attachments_response = ec2_client.describe_transit_gateway_attachments(
                        Filters=[{'Name': 'transit-gateway-id', 'Values': [tgw_id]}]
                    )
                    for attachment in attachments_response.get('TransitGatewayAttachments', []):
                        attachment_id = attachment.get('TransitGatewayAttachmentId')
                        if attachment_id:
                            attachment_arn = f"arn:aws:ec2:{self.region}:{self._get_account_id()}:transit-gateway-attachment/{attachment_id}"
                            attachment_properties = {
                                'arn': attachment_arn,
                                'attachment_id': attachment_id,
                                'transit_gateway_id': tgw_id,
                                'resource_type': attachment.get('ResourceType', ''),
                                'resource_id': attachment.get('ResourceId', ''),
                                'resource_owner_id': attachment.get('ResourceOwnerId', ''),
                                'state': attachment.get('State', ''),
                                'creation_time': str(attachment.get('CreationTime', '')),
                                'association_state': attachment.get('Association', {}).get('State', ''),
                                'association_route_table_id': attachment.get('Association', {}).get('TransitGatewayRouteTableId', ''),
                                'resource_type': 'AWS::EC2::TransitGatewayAttachment',
                                'service': 'ec2',
                                'region': self.region,
                                'account_id': self._get_account_id()
                            }
                            attachment_properties = {k: v for k, v in attachment_properties.items() if v}
                            attachment_query = """
                            MERGE (attachment:TransitGatewayAttachment {arn: $arn})
                            SET attachment += $properties
                            WITH attachment
                            MATCH (account:Account {id: $account_id})
                            MERGE (account)-[:OWNS]->(attachment)
                            WITH attachment
                            MATCH (tgw:AWS_EC2_TransitGateway {arn: $tgw_arn})
                            MERGE (tgw)-[:HAS_ATTACHMENT]->(attachment)
                            """
                            session.run(attachment_query, 
                                       arn=attachment_arn, 
                                       properties=attachment_properties,
                                       account_id=self._get_account_id(),
                                       tgw_arn=tgw_arn)
                    route_tables_response = ec2_client.describe_transit_gateway_route_tables(
                        Filters=[{'Name': 'transit-gateway-id', 'Values': [tgw_id]}]
                    )
                    for route_table in route_tables_response.get('TransitGatewayRouteTables', []):
                        route_table_id = route_table.get('TransitGatewayRouteTableId')
                        if route_table_id:
                            route_table_arn = f"arn:aws:ec2:{self.region}:{self._get_account_id()}:transit-gateway-route-table/{route_table_id}"
                            route_table_properties = {
                                'arn': route_table_arn,
                                'route_table_id': route_table_id,
                                'transit_gateway_id': tgw_id,
                                'state': route_table.get('State', ''),
                                'default_association_route_table': route_table.get('DefaultAssociationRouteTable', False),
                                'default_propagation_route_table': route_table.get('DefaultPropagationRouteTable', False),
                                'creation_time': str(route_table.get('CreationTime', '')),
                                'resource_type': 'AWS::EC2::TransitGatewayRouteTable',
                                'service': 'ec2',
                                'region': self.region,
                                'account_id': self._get_account_id()
                            }
                            route_table_properties = {k: v for k, v in route_table_properties.items() if v}
                            route_table_query = """
                            MERGE (rt:TransitGatewayRouteTable {arn: $arn})
                            SET rt += $properties
                            WITH rt
                            MATCH (account:Account {id: $account_id})
                            MERGE (account)-[:OWNS]->(rt)
                            WITH rt
                            MATCH (tgw:AWS_EC2_TransitGateway {arn: $tgw_arn})
                            MERGE (tgw)-[:HAS_ROUTE_TABLE]->(rt)
                            """
                            session.run(route_table_query, 
                                       arn=route_table_arn, 
                                       properties=route_table_properties,
                                       account_id=self._get_account_id(),
                                       tgw_arn=tgw_arn)
                            try:
                                routes_response = ec2_client.search_transit_gateway_routes(
                                    TransitGatewayRouteTableId=route_table_id,
                                    Filters=[{'Name': 'state', 'Values': ['active', 'blackhole']}]
                                )
                                for i, route in enumerate(routes_response.get('Routes', [])):
                                    route_id = f"{route_table_id}_route_{i}"
                                    route_arn = f"arn:aws:ec2:{self.region}:{self._get_account_id()}:transit-gateway-route/{route_id}"
                                    route_properties = {
                                        'arn': route_arn,
                                        'route_id': route_id,
                                        'route_table_id': route_table_id,
                                        'destination_cidr_block': route.get('DestinationCidrBlock', ''),
                                        'prefix_list_id': route.get('PrefixListId', ''),
                                        'state': route.get('State', ''),
                                        'route_type': route.get('Type', ''),
                                        'attachment_id': '',
                                        'resource_id': '',
                                        'resource_type': 'AWS::EC2::TransitGatewayRoute',
                                        'service': 'ec2',
                                        'region': self.region,
                                        'account_id': self._get_account_id()
                                    }
                                    for attachment in route.get('TransitGatewayAttachments', []):
                                        route_properties['attachment_id'] = attachment.get('TransitGatewayAttachmentId', '')
                                        route_properties['resource_id'] = attachment.get('ResourceId', '')
                                        break
                                    route_properties = {k: v for k, v in route_properties.items() if v}
                                    route_query = """
                                    MERGE (route:TransitGatewayRoute {arn: $arn})
                                    SET route += $properties
                                    WITH route
                                    MATCH (account:Account {id: $account_id})
                                    MERGE (account)-[:OWNS]->(route)
                                    WITH route
                                    MATCH (rt:TransitGatewayRouteTable {arn: $route_table_arn})
                                    MERGE (rt)-[:HAS_ROUTE]->(route)
                                    """
                                    session.run(route_query, 
                                               arn=route_arn, 
                                               properties=route_properties,
                                               account_id=self._get_account_id(),
                                               route_table_arn=route_table_arn)
                            except Exception as e:
                                self.logger.warning(f"Failed to get routes for Transit Gateway route table {route_table_id}: {e}")
                    vpc_attachments_response = ec2_client.describe_transit_gateway_vpc_attachments(
                        Filters=[{'Name': 'transit-gateway-id', 'Values': [tgw_id]}]
                    )
                    for vpc_attachment in vpc_attachments_response.get('TransitGatewayVpcAttachments', []):
                        vpc_owner_id = vpc_attachment.get('VpcOwnerId', '')
                        current_account_id = self._get_account_id()
                        if vpc_owner_id and vpc_owner_id != current_account_id:
                            self.logger.info(f"Found cross-account Transit Gateway connection: {current_account_id} -> {vpc_owner_id}")
                            cross_account_query = """
                            MERGE (source_account:Account {id: $source_account_id})
                            MERGE (target_account:Account {id: $target_account_id})
                            MERGE (source_account)-[:CONNECTED_VIA_TRANSIT_GATEWAY {
                                transit_gateway_id: $tgw_id,
                                attachment_id: $attachment_id,
                                connection_type: 'Transit Gateway VPC Attachment',
                                vpc_id: $vpc_id,
                                created_at: datetime()
                            }]->(target_account)
                            """
                            session.run(cross_account_query,
                                       source_account_id=current_account_id,
                                       target_account_id=vpc_owner_id,
                                       tgw_id=tgw_id,
                                       attachment_id=vpc_attachment.get('TransitGatewayAttachmentId', ''),
                                       vpc_id=vpc_attachment.get('VpcId', ''))
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for Transit Gateway {tgw_id}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create Transit Gateway components: {e}")
    def _create_vpc_peering_components(self, session, resources: Dict[str, Any]):
        """Create VPC Peering connection components and detect cross-account connections"""
        try:
            ec2_client = self.get_service_client('ec2')
            peering_connections = [
                (arn, info) for arn, info in resources.items() 
                if info.get('resource_type') == 'AWS::EC2::VPCPeeringConnection'
            ]
            for pcx_arn, pcx_info in peering_connections:
                pcx_id = pcx_info.get('identifier', '')
                if not pcx_id:
                    continue
                try:
                    response = ec2_client.describe_vpc_peering_connections(VpcPeeringConnectionIds=[pcx_id])
                    for pcx in response.get('VpcPeeringConnections', []):
                        accepter_vpc_info = pcx.get('AccepterVpcInfo', {})
                        requester_vpc_info = pcx.get('RequesterVpcInfo', {})
                        accepter_owner_id = accepter_vpc_info.get('OwnerId', '')
                        requester_owner_id = requester_vpc_info.get('OwnerId', '')
                        current_account_id = self._get_account_id()
                        pcx_properties = {
                            'arn': pcx_arn,
                            'peering_connection_id': pcx_id,
                            'accepter_vpc_id': accepter_vpc_info.get('VpcId', ''),
                            'accepter_owner_id': accepter_owner_id,
                            'accepter_region': accepter_vpc_info.get('Region', ''),
                            'requester_vpc_id': requester_vpc_info.get('VpcId', ''),
                            'requester_owner_id': requester_owner_id,
                            'requester_region': requester_vpc_info.get('Region', ''),
                            'status_code': pcx.get('Status', {}).get('Code', ''),
                            'status_message': pcx.get('Status', {}).get('Message', ''),
                            'expiration_time': str(pcx.get('ExpirationTime', '')),
                            'resource_type': 'AWS::EC2::VPCPeeringConnection',
                            'service': 'ec2',
                            'region': self.region,
                            'account_id': current_account_id
                        }
                        pcx_properties = {k: v for k, v in pcx_properties.items() if v}
                        update_pcx_query = """
                        MATCH (pcx:AWS_EC2_VPCPeeringConnection {arn: $arn})
                        SET pcx += $properties
                        """
                        session.run(update_pcx_query, arn=pcx_arn, properties=pcx_properties)
                        cross_account_targets = []
                        if accepter_owner_id and accepter_owner_id != current_account_id:
                            cross_account_targets.append(accepter_owner_id)
                        if requester_owner_id and requester_owner_id != current_account_id:
                            cross_account_targets.append(requester_owner_id)
                        for target_account_id in cross_account_targets:
                            self.logger.info(f"Found cross-account VPC Peering connection: {current_account_id} -> {target_account_id}")
                            cross_account_query = """
                            MERGE (source_account:Account {id: $source_account_id})
                            MERGE (target_account:Account {id: $target_account_id})
                            MERGE (source_account)-[:CONNECTED_VIA_VPC_PEERING {
                                peering_connection_id: $pcx_id,
                                connection_type: 'VPC Peering Connection',
                                accepter_vpc_id: $accepter_vpc_id,
                                requester_vpc_id: $requester_vpc_id,
                                status: $status,
                                created_at: datetime()
                            }]->(target_account)
                            """
                            session.run(cross_account_query,
                                       source_account_id=current_account_id,
                                       target_account_id=target_account_id,
                                       pcx_id=pcx_id,
                                       accepter_vpc_id=accepter_vpc_info.get('VpcId', ''),
                                       requester_vpc_id=requester_vpc_info.get('VpcId', ''),
                                       status=pcx.get('Status', {}).get('Code', ''))
                except Exception as e:
                    self.logger.warning(f"Failed to get detailed info for VPC Peering connection {pcx_id}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to create VPC Peering components: {e}")
    def _log_cross_account_connections(self, session):
        """Log summary of all cross-account connections discovered"""
        try:
            tgw_query = """
            MATCH (source:Account)-[r:CONNECTED_VIA_TRANSIT_GATEWAY]->(target:Account)
            RETURN source.id as source_account, target.id as target_account, 
                   r.transit_gateway_id as tgw_id, r.connection_type as type
            """
            tgw_results = session.run(tgw_query)
            pcx_query = """
            MATCH (source:Account)-[r:CONNECTED_VIA_VPC_PEERING]->(target:Account)
            RETURN source.id as source_account, target.id as target_account,
                   r.peering_connection_id as pcx_id, r.connection_type as type, r.status as status
            """
            pcx_results = session.run(pcx_query)
            tgw_connections = list(tgw_results)
            pcx_connections = list(pcx_results)
            if tgw_connections or pcx_connections:
                self.logger.info("=" * 60)
                self.logger.info("CROSS-ACCOUNT CONNECTIVITY SUMMARY")
                self.logger.info("=" * 60)
                if tgw_connections:
                    self.logger.info(f"Transit Gateway Connections ({len(tgw_connections)}):")
                    for conn in tgw_connections:
                        self.logger.info(f"  📡 {conn['source_account']} -> {conn['target_account']} via TGW {conn['tgw_id']}")
                if pcx_connections:
                    self.logger.info(f"VPC Peering Connections ({len(pcx_connections)}):")
                    for conn in pcx_connections:
                        status_emoji = "✅" if conn['status'] == 'active' else "⚠️"
                        self.logger.info(f"  {status_emoji} {conn['source_account']} -> {conn['target_account']} via PCX {conn['pcx_id']} ({conn['status']})")
                total_connections = len(tgw_connections) + len(pcx_connections)
                unique_accounts = set()
                for conn in tgw_connections + pcx_connections:
                    unique_accounts.add(conn['source_account'])
                    unique_accounts.add(conn['target_account'])
                self.logger.info("=" * 60)
                self.logger.info(f"Total cross-account connections: {total_connections}")
                self.logger.info(f"Connected accounts: {len(unique_accounts)}")
                self.logger.info("=" * 60)
            else:
                self.logger.info("No cross-account connections detected via Transit Gateway or VPC Peering")
        except Exception as e:
            self.logger.error(f"Failed to log cross-account connections: {e}")
    def _create_resource_relationships(self, session, resources: Dict[str, Any]):
        """Create relationships between resources based on property references"""
        self.logger.info("Analyzing resources for cross-references...")
        relationships = []
        resource_lookup = {}
        for arn, info in resources.items():
            resource_lookup[arn] = arn
            identifier = info.get('identifier', '')
            if identifier:
                resource_lookup[identifier] = arn
            if info.get('resource_type') == 'AWS::S3::Bucket':
                bucket_name = info.get('properties', {}).get('BucketName', '')
                if bucket_name:
                    resource_lookup[bucket_name] = arn
            properties = info.get('properties', {})
            for key, value in properties.items():
                if isinstance(value, str) and value:
                    if (value.startswith('arn:aws:') or 
                        value.startswith('s3-') or 
                        key.lower().endswith('bucket') or
                        key.lower().endswith('bucketname')):
                        resource_lookup[value] = arn
        for source_arn, source_info in resources.items():
            source_properties = source_info.get('properties', {})
            for prop_name, prop_value in source_properties.items():
                refs = self._find_property_references(prop_value, resource_lookup, source_arn)
                for target_arn, relationship_type in refs:
                    relationships.append({
                        'source_arn': source_arn,
                        'target_arn': target_arn,
                        'relationship_type': relationship_type,
                        'property': prop_name
                    })
        self.logger.info(f"Creating {len(relationships)} resource relationships...")
        for rel in relationships:
            try:
                source_type = self._get_safe_resource_type(resources[rel['source_arn']]['resource_type'])
                target_type = self._get_safe_resource_type(resources[rel['target_arn']]['resource_type'])
                relationship_query = f"""
                MATCH (source:{source_type} {{arn: $source_arn}})
                MATCH (target:{target_type} {{arn: $target_arn}})
                MERGE (source)-[r:{rel['relationship_type']} {{property: $property}}]->(target)
                """
                session.run(relationship_query,
                           source_arn=rel['source_arn'],
                           target_arn=rel['target_arn'],
                           property=rel['property'])
                self.logger.debug(f"Created relationship: {rel['relationship_type']} from {rel['source_arn']} to {rel['target_arn']}")
            except Exception as e:
                self.logger.warning(f"Failed to create relationship {rel}: {e}")
        self.logger.info(f"✅ Successfully created {len(relationships)} resource relationships")
    def _get_safe_resource_type(self, resource_type: str) -> str:
        """Convert resource type to safe Neo4j label"""
        return resource_type.replace('-', '_').replace('.', '_').replace(':', '_')
    def _find_property_references(self, prop_value, resource_lookup: dict, source_arn: str) -> list:
        """Find references to other resources in a property value"""
        references = []
        if isinstance(prop_value, str):
            if prop_value.startswith('arn:aws:') and prop_value in resource_lookup and prop_value != source_arn:
                references.append((resource_lookup[prop_value], 'REFERENCES'))
            elif prop_value in resource_lookup and prop_value != source_arn:
                target_arn = resource_lookup[prop_value]
                if target_arn != source_arn:
                    if 'bucket' in prop_value.lower():
                        references.append((target_arn, 'LOGS_TO'))
                    else:
                        references.append((target_arn, 'REFERENCES'))
        elif isinstance(prop_value, dict):
            for key, value in prop_value.items():
                refs = self._find_property_references(value, resource_lookup, source_arn)
                references.extend(refs)
                if key == 'DestinationBucketName' and isinstance(value, str):
                    if value in resource_lookup:
                        target_arn = resource_lookup[value]
                        if target_arn != source_arn:
                            references.append((target_arn, 'LOGS_TO'))
                elif key == 'Bucket' and isinstance(value, str):
                    if value in resource_lookup:
                        target_arn = resource_lookup[value]
                        if target_arn != source_arn:
                            references.append((target_arn, 'APPLIES_TO'))
        elif isinstance(prop_value, list):
            for item in prop_value:
                refs = self._find_property_references(item, resource_lookup, source_arn)
                references.extend(refs)
        return references
    def _clear_graph(self,driver):
        """Clear all nodes and relationships from the database."""
        self.logger.info("Clearing Neo4j database...")
        with driver.session() as session:
            session.run("MATCH ()-[r]-() DELETE r")
            session.run("MATCH (n) DELETE n")
            self.logger.info("Database cleared successfully")
    def _create_constraints_and_indexes(self,driver):
        """Create database constraints and indexes for better performance."""
        constraints_and_indexes = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Region) REQUIRE (r.name, r.account_id) IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (res:Resource) REQUIRE (res.arn, res.region, res.account_id) IS UNIQUE",
            "CREATE INDEX IF NOT EXISTS FOR (a:Account) ON (a.id)",
            "CREATE INDEX IF NOT EXISTS FOR (r:Region) ON (r.name)",
            "CREATE INDEX IF NOT EXISTS FOR (res:Resource) ON (res.resourceType)",
            "CREATE INDEX IF NOT EXISTS FOR (res:Resource) ON (res.region)",
            "CREATE INDEX IF NOT EXISTS FOR (res:Resource) ON (res.account_id)",
        ]
        with driver.session() as session:
            for constraint_or_index in constraints_and_indexes:
                try:
                    session.run(constraint_or_index)
                    self.logger.debug(f"Created: {constraint_or_index}")
                except Neo4jError as e:
                    self.logger.warning(f"Could not create constraint/index: {e}")

def validate_aws_connectivity(region: str, profile: str = None) -> Tuple[bool, str, str]:
    """
    Validate AWS connectivity and return account information
    
    Returns:
        Tuple[bool, str, str]: (success, account_id, account_alias)
    """
    try:
        # Create session with specified profile if provided
        if profile:
            session = boto3.Session(profile_name=profile, region_name=region)
        else:
            session = boto3.Session(region_name=region)
        
        # Test STS connectivity and get account info
        sts_client = session.client('sts')
        identity = sts_client.get_caller_identity()
        account_id = identity.get('Account', 'Unknown')
        
        # Try to get account alias
        try:
            iam_client = session.client('iam')
            aliases = iam_client.list_account_aliases()
            account_alias = aliases.get('AccountAliases', [''])[0] or account_id
        except Exception:
            # If IAM access fails, use account ID as alias
            account_alias = account_id
            
        print(f"✅ AWS Connectivity Validated")
        print(f"   Account ID: {account_id}")
        print(f"   Account Alias: {account_alias}")
        print(f"   Region: {region}")
        if profile:
            print(f"   Profile: {profile}")
        print()
        
        return True, account_id, account_alias
        
    except Exception as e:
        print(f"❌ AWS Connectivity Failed: {str(e)}")
        print("   Please check:")
        print("   - AWS credentials are configured")
        print("   - Profile exists (if specified)")
        print("   - Region is valid")
        print("   - Network connectivity to AWS")
        return False, "", ""

def validate_graph_db_connectivity(url: str, user: str, password: str) -> bool:
    """
    Validate Neo4j graph database connectivity
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        # Create Neo4j driver with auth
        driver = GraphDatabase.driver(f"bolt://{url}", auth=(user, password))
        
        # Test connection with a simple query
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]
            
            # Get Neo4j version info
            version_result = session.run("CALL dbms.components() YIELD name, versions, edition")
            version_info = version_result.single()
            
        driver.close()
        
        print(f"✅ Neo4j Connectivity Validated")
        print(f"   Database URL: bolt://{url}")
        print(f"   User: {user}")
        print(f"   Version: {version_info['name']} {version_info['versions'][0]} ({version_info['edition']})")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Neo4j Connectivity Failed: {str(e)}")
        print("   Please check:")
        print("   - Neo4j is running and accessible")
        print(f"   - Database URL is correct (bolt://{url})")
        print(f"   - Username/password are valid ({user}/***)")
        print("   - Network connectivity to the database")
        print("   - Firewall settings allow bolt protocol (port 7687)")
        return False

def main():
    """Main entry point - parse arguments and execute AWS resource discovery"""
    parser = argparse.ArgumentParser(
        description='Comprehensive AWS Resource Discovery Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --region us-east-1
  %(prog)s --region eu-west-1 --max-workers 20 --filter ec2
  %(prog)s --region us-west-2 --profile production --output-formats json csv excel
  %(prog)s --region us-east-1 --individual-descriptions --description-workers 10
  %(prog)s --region us-east-1 --no-progress  # For web interfaces or non-interactive environments
        """
    )
    parser.add_argument('--region', required=True, help='AWS region to scan')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--max-workers', type=int, default=10, 
                       help='Maximum number of parallel workers (default: 10)')
    parser.add_argument('--filter', help='Filter resource types (e.g., "ec2", "s3")')
    parser.add_argument('--output-formats', nargs='+', 
                       choices=['json', 'csv', 'excel', 'html'], 
                       default=['json', 'csv'],
                       help='Output formats (default: json csv)')
    parser.add_argument('--search', help='Search discovered resources')
    parser.add_argument('--individual-descriptions', action='store_true', help='Create a consolidated JSON file with detailed descriptions for all resources')
    parser.add_argument('--description-workers', type=int, default=5,help='Number of parallel workers for detailed descriptions (default: 5)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--update-graph',  action='store_true', help='Update the graph database with discovered resources (optional)')
    parser.add_argument('--graph-db-url', default="localhost:7687", help='Graph database URL for updates (optional)')
    parser.add_argument('--graph-db-user', default="neo4j", help='Graph database username (optional)')
    parser.add_argument('--graph-db-password', default="password", help='Graph database password (optional)')
    parser.add_argument('--reset-graph', action='store_true',help='Reset the graph database before updating (optional)')
    parser.add_argument('--account-name', help='AWS account name for graph database labeling (optional)')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bars (useful for web interfaces)')
    args = parser.parse_args()
    
    # Set HAS_TQDM based on command line arguments and availability
    global HAS_TQDM
    if args.no_progress:
        HAS_TQDM = False
    else:
        HAS_TQDM = HAS_TQDM_AVAILABLE
    
    # Validate AWS connectivity before proceeding
    success, account_id, account_alias = validate_aws_connectivity(args.region, args.profile)
    if not success:
        sys.exit(1)
    
    # Validate Neo4j connectivity if graph update is requested
    if args.update_graph:
        graph_success = validate_graph_db_connectivity(args.graph_db_url, args.graph_db_user, args.graph_db_password)
        if not graph_success:
            sys.exit(1)
    
    try:
        discovery = ComprehensiveAWSDiscovery(args.region, args.profile)
        if args.verbose:
            discovery.logger.setLevel(logging.DEBUG)
        resources = discovery.discover_all_resources(
            max_workers=args.max_workers,
            resource_filter=args.filter
        )
        if args.search:
            resources = discovery.search_resources(resources, args.search)
            discovery.logger.info(f"🔍 Search '{args.search}' returned {len(resources)} results")
        all_resource = None
        detailed_descriptions_count = 0
        if args.individual_descriptions:
            detailed_descriptions_count , all_resource = discovery.save_consolidated_resource_descriptions(
                resources, max_workers=args.description_workers
            )
        if args.update_graph and all_resource:
            discovery.logger.info("Updating graph database with discovered resources...")
            discovery.update_graph_database(all_resource, args.graph_db_url, args.graph_db_user, args.graph_db_password, args.reset_graph, args.account_name)
        exported_files = []
        if 'json' in args.output_formats:
            exported_files.append(discovery.export_to_json(resources))
        if 'csv' in args.output_formats:
            csv_file = discovery.export_to_csv(resources)
            if csv_file:
                exported_files.append(csv_file)
        if 'excel' in args.output_formats:
            excel_file = discovery.export_to_excel(resources)
            if excel_file:
                exported_files.append(excel_file)
        if 'html' in args.output_formats:
            exported_files.append(discovery.generate_report(resources))
        print(f"\n🎉 Discovery completed successfully!")
        print(f"📁 Output directory: {discovery.output_dir}")
        print(f"📊 Total resources discovered: {len([r for r in resources if not r.error])}")
        print(f"📄 Files generated: {len(exported_files)}")
        if args.individual_descriptions:
            print(f"🔍 Detailed resource descriptions: {detailed_descriptions_count}")
            print(f"📂 Descriptions file: {discovery.descriptions_dir}/all_resources_detailed.json")
        for file_path in exported_files:
            if file_path:
                print(f"   - {file_path}")
    except KeyboardInterrupt:
        print("\n⚠️ Discovery interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Discovery failed: {e}")
        sys.exit(1)
if __name__ == "__main__":
    import atexit
    import threading
    def cleanup_threads():
        """Clean up any remaining threads to prevent cleanup errors"""
        try:
            import time
            time.sleep(0.1)
            for thread in threading.enumerate():
                if thread != threading.current_thread() and hasattr(thread, '_stop'):
                    try:
                        thread._stop()
                    except:
                        pass
        except:
            pass
    atexit.register(cleanup_threads)
    try:
        main()
    finally:
        cleanup_threads()