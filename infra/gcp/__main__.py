"""GCP Infrastructure with Pulumi - Supports Compute Engine, GKE, and Cloud Functions deployments"""
import pulumi
import pulumi_gcp as gcp

# Get configuration
config = pulumi.Config()
deployment_type = config.get("deploymentType") or "functions"  # functions, compute, or gke
app_name = config.get("appName") or "multi-cloud-api"
project = config.require("gcpProject")
region = config.get("region") or "us-central1"
zone = config.get("zone") or "us-central1-a"

# Enable required APIs
apis = [
    "compute.googleapis.com",
    "container.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
]

for api in apis:
    gcp.projects.Service(f"enable-{api}",
        service=api,
        project=project,
    )

# Create Artifact Registry repository for Docker images
artifact_repo = gcp.artifactregistry.Repository(f"{app_name}-repo",
    location=region,
    repository_id=app_name,
    format="DOCKER",
    project=project,
)

if deployment_type == "functions":
    # Cloud Functions deployment (Gen 2)
    # Create storage bucket for function source
    bucket = gcp.storage.Bucket(f"{app_name}-bucket",
        location=region,
        project=project,
        uniform_bucket_level_access=True,
    )

    # Create Cloud Run service (Cloud Functions v2 uses Cloud Run)
    cloud_run_service = gcp.cloudrunv2.Service(f"{app_name}-service",
        location=region,
        project=project,
        template=gcp.cloudrunv2.ServiceTemplateArgs(
            containers=[
                gcp.cloudrunv2.ServiceTemplateContainerArgs(
                    image=pulumi.Output.concat(
                        region, "-docker.pkg.dev/", project, "/", 
                        artifact_repo.repository_id, "/", app_name, ":latest"
                    ),
                    ports=[
                        gcp.cloudrunv2.ServiceTemplateContainerPortArgs(
                            container_port=8080,
                        ),
                    ],
                ),
            ],
            scaling=gcp.cloudrunv2.ServiceTemplateScalingArgs(
                max_instance_count=10,
            ),
        ),
    )

    # Make Cloud Run service publicly accessible
    cloud_run_iam = gcp.cloudrunv2.ServiceIamMember(f"{app_name}-invoker",
        project=cloud_run_service.project,
        location=cloud_run_service.location,
        name=cloud_run_service.name,
        role="roles/run.invoker",
        member="allUsers",
    )

    pulumi.export("cloud_run_url", cloud_run_service.uri)
    pulumi.export("service_name", cloud_run_service.name)

elif deployment_type == "compute":
    # Compute Engine deployment
    # Create VPC network
    network = gcp.compute.Network(f"{app_name}-network",
        auto_create_subnetworks=True,
        project=project,
    )

    # Create firewall rule
    firewall = gcp.compute.Firewall(f"{app_name}-firewall",
        network=network.self_link,
        project=project,
        allows=[
            gcp.compute.FirewallAllowArgs(
                protocol="tcp",
                ports=["80", "8080"],
            ),
        ],
        source_ranges=["0.0.0.0/0"],
        target_tags=[app_name],
    )

    # Create service account for VM
    service_account = gcp.serviceaccount.Account(f"{app_name}-sa",
        account_id=f"{app_name}-sa",
        display_name=f"{app_name} Service Account",
        project=project,
    )

    # Grant storage access to service account
    gcp.projects.IAMMember(f"{app_name}-storage-access",
        project=project,
        role="roles/storage.objectViewer",
        member=service_account.email.apply(lambda email: f"serviceAccount:{email}"),
    )

    # Startup script
    startup_script = pulumi.Output.all(
        region, project, artifact_repo.repository_id, app_name
    ).apply(lambda args: f"""#!/bin/bash
    apt-get update
    apt-get install -y docker.io
    
    # Configure Docker to use Artifact Registry
    gcloud auth configure-docker {args[0]}-docker.pkg.dev
    
    # Pull and run container
    docker pull {args[0]}-docker.pkg.dev/{args[1]}/{args[2]}/{args[3]}:latest
    docker run -d -p 80:8080 {args[0]}-docker.pkg.dev/{args[1]}/{args[2]}/{args[3]}:latest
    """)

    # Create Compute Engine instance
    instance = gcp.compute.Instance(f"{app_name}-instance",
        machine_type="e2-small",
        zone=zone,
        project=project,
        boot_disk=gcp.compute.InstanceBootDiskArgs(
            initialize_params=gcp.compute.InstanceBootDiskInitializeParamsArgs(
                image="ubuntu-os-cloud/ubuntu-2004-lts",
            ),
        ),
        network_interfaces=[
            gcp.compute.InstanceNetworkInterfaceArgs(
                network=network.id,
                access_configs=[gcp.compute.InstanceNetworkInterfaceAccessConfigArgs()],
            ),
        ],
        metadata_startup_script=startup_script,
        service_account=gcp.compute.InstanceServiceAccountArgs(
            email=service_account.email,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        ),
        tags=[app_name],
    )

    pulumi.export("instance_external_ip", instance.network_interfaces[0].access_configs[0].nat_ip)
    pulumi.export("instance_name", instance.name)

elif deployment_type == "gke":
    # GKE deployment
    # Create GKE cluster
    cluster = gcp.container.Cluster(f"{app_name}-gke",
        location=zone,
        project=project,
        initial_node_count=2,
        min_master_version="latest",
        node_config=gcp.container.ClusterNodeConfigArgs(
            machine_type="e2-medium",
            oauth_scopes=[
                "https://www.googleapis.com/auth/compute",
                "https://www.googleapis.com/auth/devstorage.read_only",
                "https://www.googleapis.com/auth/logging.write",
                "https://www.googleapis.com/auth/monitoring",
            ],
        ),
        deletion_protection=False,
    )

    # Generate kubeconfig
    cluster_name = cluster.name
    cluster_endpoint = cluster.endpoint
    cluster_ca = cluster.master_auth.cluster_ca_certificate

    kubeconfig = pulumi.Output.all(cluster_name, cluster_endpoint, cluster_ca).apply(
        lambda args: f"""apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {args[2]}
    server: https://{args[1]}
  name: {args[0]}
contexts:
- context:
    cluster: {args[0]}
    user: {args[0]}
  name: {args[0]}
current-context: {args[0]}
kind: Config
preferences: {{}}
users:
- name: {args[0]}
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: gke-gcloud-auth-plugin
      installHint: Install gke-gcloud-auth-plugin for kubectl
      provideClusterInfo: true
"""
    )

    pulumi.export("kubeconfig", kubeconfig)
    pulumi.export("cluster_name", cluster.name)
    pulumi.export("cluster_endpoint", cluster.endpoint)

# Export common outputs
pulumi.export("artifact_registry_url", artifact_repo.name.apply(
    lambda name: f"{region}-docker.pkg.dev/{project}/{name}"
))
pulumi.export("deployment_type", deployment_type)
pulumi.export("project_id", project)
