# Multi-Cloud API Deployment Project

A comprehensive project template for deploying a Python FastAPI application to AWS, Azure, or GCP using Pulumi infrastructure as code and GitHub Actions workflows.

## Project Structure

```
.
├── api/                    # Python FastAPI application
│   ├── main.py            # API endpoints
│   ├── requirements.txt   # Python dependencies
│   └── Dockerfile         # Container configuration
├── infra/                 # Infrastructure as Code (Pulumi)
│   ├── aws/              # AWS infrastructure
│   ├── azure/            # Azure infrastructure
│   └── gcp/              # GCP infrastructure
├── k8s/                  # Kubernetes manifests
│   ├── deployment.yaml   # K8s deployment config
│   └── service.yaml      # K8s service config
└── .github/
    └── workflows/        # GitHub Actions workflows
        ├── deploy-aws.yml
        ├── deploy-azure.yml
        └── deploy-gcp.yml
```

## Features

- **REST API**: Simple FastAPI application with `/` and `/health` endpoints
- **Multi-Cloud Support**: Deploy to AWS, Azure, or GCP
- **Multiple Deployment Options**:
  - **AWS**: Lambda, EC2, or EKS
  - **Azure**: Functions, VM, or AKS
  - **GCP**: Cloud Run, Compute Engine, or GKE
- **Infrastructure as Code**: Pulumi for consistent infrastructure management
- **CI/CD**: GitHub Actions workflows for automated deployment
- **Containerized**: Docker support for consistent deployments

## Prerequisites

1. **Cloud Provider Account**:
   - AWS account with appropriate permissions
   - Azure subscription
   - GCP project

2. **Tools**:
   - [Pulumi CLI](https://www.pulumi.com/docs/get-started/install/)
   - [Docker](https://docs.docker.com/get-docker/)
   - [kubectl](https://kubernetes.io/docs/tasks/tools/) (for Kubernetes deployments)

3. **GitHub Secrets** (configure in your repository):
   
   **For AWS**:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   
   **For Azure**:
   - `AZURE_CREDENTIALS` (JSON format service principal)
   
   **For GCP**:
   - `GCP_CREDENTIALS` (JSON format service account key)
   
   **For all providers**:
   - `PULUMI_ACCESS_TOKEN`
   - `PULUMI_CONFIG_PASSPHRASE`

## Local Development

### Run the API locally

```bash
cd api
pip install -r requirements.txt
python main.py
```

Visit `http://localhost:8080` to test the API.

### Build Docker image

```bash
cd api
docker build -t multi-cloud-api .
docker run -p 8080:8080 multi-cloud-api
```

## Deployment

### Using GitHub Actions (Recommended)

1. Push your code to GitHub
2. Go to **Actions** tab in your repository
3. Select the appropriate workflow:
   - **Deploy to AWS**
   - **Deploy to Azure**
   - **Deploy to GCP**
4. Click **Run workflow**
5. Choose your deployment type and provide required inputs
6. Click **Run workflow**

### Manual Deployment with Pulumi

#### AWS Deployment

```bash
cd infra/aws
pip install -r requirements.txt

# Initialize Pulumi stack
pulumi stack init dev

# Configure deployment
pulumi config set deploymentType lambda  # or ec2, eks
pulumi config set appName multi-cloud-api

# Deploy
pulumi up
```

#### Azure Deployment

```bash
cd infra/azure
pip install -r requirements.txt

# Initialize Pulumi stack
pulumi stack init dev

# Configure deployment
pulumi config set deploymentType functions  # or vm, aks
pulumi config set appName multi-cloud-api
pulumi config set location eastus

# Login to Azure
az login

# Deploy
pulumi up
```

#### GCP Deployment

```bash
cd infra/gcp
pip install -r requirements.txt

# Initialize Pulumi stack
pulumi stack init dev

# Configure deployment
pulumi config set deploymentType functions  # or compute, gke
pulumi config set appName multi-cloud-api
pulumi config set gcpProject YOUR_PROJECT_ID
pulumi config set region us-central1

# Authenticate with GCP
gcloud auth application-default login

# Deploy
pulumi up
```

## Deployment Options

### AWS

1. **Lambda** (Serverless)
   - Best for: Event-driven, low-traffic APIs
   - Scales automatically
   - Pay per request

2. **EC2** (Virtual Machine)
   - Best for: Consistent workloads
   - Full control over environment
   - Fixed pricing

3. **EKS** (Kubernetes)
   - Best for: Complex applications with multiple services
   - High availability and scalability
   - Advanced orchestration

### Azure

1. **Functions** (Serverless)
   - Best for: Event-driven workloads
   - Automatic scaling
   - Pay per execution

2. **VM** (Virtual Machine)
   - Best for: Traditional applications
   - Full OS control
   - Predictable pricing

3. **AKS** (Kubernetes)
   - Best for: Containerized microservices
   - Enterprise-grade orchestration
   - High availability

### GCP

1. **Cloud Run** (Serverless Containers)
   - Best for: Containerized APIs
   - Automatic scaling to zero
   - Pay per use

2. **Compute Engine** (Virtual Machine)
   - Best for: Custom configurations
   - Persistent workloads
   - Full machine control

3. **GKE** (Kubernetes)
   - Best for: Cloud-native applications
   - Multi-container deployments
   - Advanced networking

## Kubernetes Deployments

For EKS, AKS, or GKE deployments, the workflows automatically apply Kubernetes manifests after cluster creation.

To manually deploy to an existing cluster:

```bash
# Update the image in deployment.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Get the service URL
kubectl get service multi-cloud-api-service
```

## Testing the Deployment

Once deployed, test your API:

```bash
# Replace <URL> with your deployment URL
curl https://<URL>/
# Response: {"hi": "Hello from Multi-Cloud API!"}

curl https://<URL>/health
# Response: {"status": "healthy"}
```

## Monitoring and Logs

### AWS
- Lambda: CloudWatch Logs
- EC2: CloudWatch Logs (requires agent)
- EKS: CloudWatch Container Insights

### Azure
- Functions: Application Insights
- VM: Azure Monitor
- AKS: Azure Monitor for containers

### GCP
- Cloud Run: Cloud Logging
- Compute Engine: Cloud Logging (requires agent)
- GKE: Cloud Logging and Monitoring

## Cost Optimization

- **Lambda/Functions/Cloud Run**: Best for intermittent traffic
- **EC2/VM/Compute Engine**: Use reserved instances for consistent workloads
- **Kubernetes**: Enable autoscaling and right-size your nodes

## Cleanup

To destroy infrastructure:

```bash
cd infra/<cloud-provider>
pulumi destroy
```

## Security Best Practices

1. **Secrets Management**:
   - Use GitHub Secrets for sensitive data
   - Never commit credentials to version control

2. **Network Security**:
   - Configure security groups/firewall rules
   - Use HTTPS in production

3. **IAM/RBAC**:
   - Follow principle of least privilege
   - Use managed identities where possible

4. **Container Security**:
   - Scan images for vulnerabilities
   - Use minimal base images
   - Keep dependencies updated

## Troubleshooting

### Pulumi Issues
- Ensure `PULUMI_ACCESS_TOKEN` is set correctly
- Check stack configuration with `pulumi config`

### Docker Build Failures
- Verify Dockerfile syntax
- Check Docker daemon is running

### Deployment Failures
- Review GitHub Actions logs
- Check cloud provider quotas
- Verify IAM permissions

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - feel free to use this template for your projects.
