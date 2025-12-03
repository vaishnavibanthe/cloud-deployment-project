"""AWS Infrastructure with Pulumi - Supports EC2, EKS, and Lambda deployments"""
import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
import json

# Get configuration
config = pulumi.Config()
deployment_type = config.get("deploymentType") or "lambda"  # lambda, ec2, or eks
app_name = config.get("appName") or "multi-cloud-api"

# Create VPC
vpc = awsx.ec2.Vpc(f"{app_name}-vpc",
    cidr_block="10.0.0.0/16",
    number_of_availability_zones=2,
    enable_dns_hostnames=True,
    enable_dns_support=True,
)

# Create ECR repository for container images
ecr_repo = aws.ecr.Repository(f"{app_name}-repo",
    name=app_name,
    image_scanning_configuration=aws.ecr.RepositoryImageScanningConfigurationArgs(
        scan_on_push=True,
    ),
    force_delete=True,
)

if deployment_type == "lambda":
    # Lambda deployment
    # Create IAM role for Lambda
    lambda_role = aws.iam.Role(f"{app_name}-lambda-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com",
                },
            }],
        }),
    )

    # Attach basic Lambda execution policy
    aws.iam.RolePolicyAttachment(f"{app_name}-lambda-policy",
        role=lambda_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
    )

    # Lambda function (using container image)
    lambda_function = aws.lambda_.Function(f"{app_name}-function",
        package_type="Image",
        image_uri=pulumi.Output.concat(ecr_repo.repository_url, ":latest"),
        role=lambda_role.arn,
        timeout=30,
        memory_size=512,
    )

    # API Gateway
    api_gateway = aws.apigatewayv2.Api(f"{app_name}-api",
        protocol_type="HTTP",
    )

    # Lambda integration
    integration = aws.apigatewayv2.Integration(f"{app_name}-integration",
        api_id=api_gateway.id,
        integration_type="AWS_PROXY",
        integration_uri=lambda_function.arn,
        payload_format_version="2.0",
    )

    # API Gateway route
    route = aws.apigatewayv2.Route(f"{app_name}-route",
        api_id=api_gateway.id,
        route_key="$default",
        target=integration.id.apply(lambda id: f"integrations/{id}"),
    )

    # API Gateway stage
    stage = aws.apigatewayv2.Stage(f"{app_name}-stage",
        api_id=api_gateway.id,
        name="$default",
        auto_deploy=True,
    )

    # Lambda permission for API Gateway
    aws.lambda_.Permission(f"{app_name}-lambda-permission",
        action="lambda:InvokeFunction",
        function=lambda_function.name,
        principal="apigateway.amazonaws.com",
        source_arn=pulumi.Output.concat(api_gateway.execution_arn, "/*/*"),
    )

    pulumi.export("api_endpoint", api_gateway.api_endpoint)
    pulumi.export("lambda_function_name", lambda_function.name)

elif deployment_type == "ec2":
    # EC2 deployment
    # Security group
    security_group = aws.ec2.SecurityGroup(f"{app_name}-sg",
        vpc_id=vpc.vpc_id,
        description="Allow HTTP traffic",
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=8080,
                to_port=8080,
                cidr_blocks=["0.0.0.0/0"],
            ),
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=80,
                to_port=80,
                cidr_blocks=["0.0.0.0/0"],
            ),
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1",
                from_port=0,
                to_port=0,
                cidr_blocks=["0.0.0.0/0"],
            ),
        ],
    )

    # Get latest Amazon Linux 2 AMI
    ami = aws.ec2.get_ami(
        most_recent=True,
        owners=["amazon"],
        filters=[
            aws.ec2.GetAmiFilterArgs(
                name="name",
                values=["amzn2-ami-hvm-*-x86_64-gp2"],
            ),
        ],
    )

    # User data script to install Docker and run container
    user_data = pulumi.Output.all(ecr_repo.repository_url).apply(lambda args: f"""#!/bin/bash
    yum update -y
    yum install -y docker
    service docker start
    usermod -a -G docker ec2-user
    
    # Install AWS CLI v2
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    ./aws/install
    
    # Login to ECR and pull image
    aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin {args[0]}
    docker pull {args[0]}:latest
    docker run -d -p 80:8080 {args[0]}:latest
    """)

    # IAM role for EC2
    ec2_role = aws.iam.Role(f"{app_name}-ec2-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com",
                },
            }],
        }),
    )

    # Attach policies for ECR access
    aws.iam.RolePolicyAttachment(f"{app_name}-ecr-policy",
        role=ec2_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    )

    # Instance profile
    instance_profile = aws.iam.InstanceProfile(f"{app_name}-instance-profile",
        role=ec2_role.name,
    )

    # EC2 instance
    instance = aws.ec2.Instance(f"{app_name}-instance",
        instance_type="t3.small",
        vpc_security_group_ids=[security_group.id],
        ami=ami.id,
        subnet_id=vpc.public_subnet_ids[0],
        user_data=user_data,
        iam_instance_profile=instance_profile.name,
        tags={
            "Name": app_name,
        },
    )

    pulumi.export("ec2_public_ip", instance.public_ip)
    pulumi.export("ec2_public_dns", instance.public_dns)

elif deployment_type == "eks":
    # EKS deployment
    # Create EKS cluster
    cluster = aws.eks.Cluster(f"{app_name}-eks",
        vpc_id=vpc.vpc_id,
        subnet_ids=vpc.public_subnet_ids + vpc.private_subnet_ids,
        instance_type="t3.medium",
        desired_capacity=2,
        min_size=1,
        max_size=3,
    )

    pulumi.export("kubeconfig", cluster.kubeconfig)
    pulumi.export("cluster_name", cluster.eks_cluster.name)

# Export common outputs
pulumi.export("ecr_repository_url", ecr_repo.repository_url)
pulumi.export("deployment_type", deployment_type)
pulumi.export("vpc_id", vpc.vpc_id)
