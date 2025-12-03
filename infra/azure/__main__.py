"""Azure Infrastructure with Pulumi - Supports VM, AKS, and Functions deployments"""
import pulumi
import pulumi_azure_native as azure

# Get configuration
config = pulumi.Config()
deployment_type = config.get("deploymentType") or "functions"  # functions, vm, or aks
app_name = config.get("appName") or "multi-cloud-api"
location = config.get("location") or "eastus"

# Create resource group
resource_group = azure.resources.ResourceGroup(f"{app_name}-rg",
    location=location,
)

# Create Azure Container Registry
acr = azure.containerregistry.Registry(f"{app_name}acr",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku=azure.containerregistry.SkuArgs(
        name="Basic",
    ),
    admin_user_enabled=True,
)

if deployment_type == "functions":
    # Azure Functions deployment
    # Create storage account (required for Functions)
    storage_account = azure.storage.StorageAccount(f"{app_name}storage",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        sku=azure.storage.SkuArgs(
            name="Standard_LRS",
        ),
        kind="StorageV2",
    )

    # Get storage account keys
    storage_account_keys = pulumi.Output.all(resource_group.name, storage_account.name).apply(
        lambda args: azure.storage.list_storage_account_keys(
            resource_group_name=args[0],
            account_name=args[1]
        )
    )

    primary_storage_key = storage_account_keys.apply(lambda keys: keys.keys[0].value)

    # Create App Service Plan (Linux, Premium for container support)
    app_service_plan = azure.web.AppServicePlan(f"{app_name}-plan",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        kind="Linux",
        reserved=True,
        sku=azure.web.SkuDescriptionArgs(
            name="EP1",
            tier="ElasticPremium",
        ),
    )

    # Create Function App
    function_app = azure.web.WebApp(f"{app_name}-func",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        server_farm_id=app_service_plan.id,
        kind="functionapp,linux,container",
        site_config=azure.web.SiteConfigArgs(
            linux_fx_version=pulumi.Output.concat("DOCKER|", acr.login_server, "/", app_name, ":latest"),
            app_settings=[
                azure.web.NameValuePairArgs(name="FUNCTIONS_EXTENSION_VERSION", value="~4"),
                azure.web.NameValuePairArgs(name="FUNCTIONS_WORKER_RUNTIME", value="python"),
                azure.web.NameValuePairArgs(
                    name="AzureWebJobsStorage",
                    value=pulumi.Output.all(storage_account.name, primary_storage_key).apply(
                        lambda args: f"DefaultEndpointsProtocol=https;AccountName={args[0]};AccountKey={args[1]};EndpointSuffix=core.windows.net"
                    )
                ),
                azure.web.NameValuePairArgs(
                    name="DOCKER_REGISTRY_SERVER_URL",
                    value=acr.login_server.apply(lambda server: f"https://{server}")
                ),
                azure.web.NameValuePairArgs(
                    name="DOCKER_REGISTRY_SERVER_USERNAME",
                    value=acr.name
                ),
                azure.web.NameValuePairArgs(
                    name="DOCKER_REGISTRY_SERVER_PASSWORD",
                    value=pulumi.Output.all(resource_group.name, acr.name).apply(
                        lambda args: azure.containerregistry.list_registry_credentials(
                            resource_group_name=args[0],
                            registry_name=args[1]
                        )
                    ).apply(lambda creds: creds.passwords[0].value)
                ),
            ],
        ),
    )

    pulumi.export("function_app_url", function_app.default_host_name.apply(lambda name: f"https://{name}"))
    pulumi.export("function_app_name", function_app.name)

elif deployment_type == "vm":
    # Azure VM deployment
    # Create virtual network
    vnet = azure.network.VirtualNetwork(f"{app_name}-vnet",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        address_space=azure.network.AddressSpaceArgs(
            address_prefixes=["10.0.0.0/16"],
        ),
    )

    # Create subnet
    subnet = azure.network.Subnet(f"{app_name}-subnet",
        resource_group_name=resource_group.name,
        virtual_network_name=vnet.name,
        address_prefix="10.0.1.0/24",
    )

    # Create public IP
    public_ip = azure.network.PublicIPAddress(f"{app_name}-ip",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        public_ip_allocation_method="Static",
        sku=azure.network.PublicIPAddressSkuArgs(
            name="Standard",
        ),
    )

    # Create network security group
    nsg = azure.network.NetworkSecurityGroup(f"{app_name}-nsg",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        security_rules=[
            azure.network.SecurityRuleArgs(
                name="allow-http",
                priority=1000,
                direction="Inbound",
                access="Allow",
                protocol="Tcp",
                source_port_range="*",
                destination_port_range="80",
                source_address_prefix="*",
                destination_address_prefix="*",
            ),
            azure.network.SecurityRuleArgs(
                name="allow-8080",
                priority=1001,
                direction="Inbound",
                access="Allow",
                protocol="Tcp",
                source_port_range="*",
                destination_port_range="8080",
                source_address_prefix="*",
                destination_address_prefix="*",
            ),
        ],
    )

    # Create network interface
    nic = azure.network.NetworkInterface(f"{app_name}-nic",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        ip_configurations=[
            azure.network.NetworkInterfaceIPConfigurationArgs(
                name="ipconfig1",
                subnet=azure.network.SubnetArgs(id=subnet.id),
                public_ip_address=azure.network.PublicIPAddressArgs(id=public_ip.id),
                private_ip_allocation_method="Dynamic",
            ),
        ],
        network_security_group=azure.network.NetworkSecurityGroupArgs(id=nsg.id),
    )

    # Cloud init script
    custom_data = pulumi.Output.all(acr.login_server, acr.name, resource_group.name).apply(
        lambda args: f"""#!/bin/bash
        apt-get update
        apt-get install -y docker.io
        systemctl start docker
        systemctl enable docker
        
        # Login to ACR
        ACR_PASSWORD=$(az acr credential show --name {args[1]} --resource-group {args[2]} --query "passwords[0].value" -o tsv)
        echo $ACR_PASSWORD | docker login {args[0]} -u {args[1]} --password-stdin
        
        # Pull and run container
        docker pull {args[0]}/{app_name}:latest
        docker run -d -p 80:8080 {args[0]}/{app_name}:latest
        """
    )

    # Create VM
    vm = azure.compute.VirtualMachine(f"{app_name}-vm",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        network_profile=azure.compute.NetworkProfileArgs(
            network_interfaces=[
                azure.compute.NetworkInterfaceReferenceArgs(id=nic.id),
            ],
        ),
        hardware_profile=azure.compute.HardwareProfileArgs(
            vm_size="Standard_B2s",
        ),
        os_profile=azure.compute.OSProfileArgs(
            computer_name=app_name,
            admin_username="azureuser",
            admin_password="P@ssw0rd123!",  # Change in production!
            custom_data=custom_data,
        ),
        storage_profile=azure.compute.StorageProfileArgs(
            image_reference=azure.compute.ImageReferenceArgs(
                publisher="Canonical",
                offer="0001-com-ubuntu-server-focal",
                sku="20_04-lts-gen2",
                version="latest",
            ),
            os_disk=azure.compute.OSDiskArgs(
                create_option="FromImage",
                managed_disk=azure.compute.ManagedDiskParametersArgs(
                    storage_account_type="Standard_LRS",
                ),
            ),
        ),
        identity=azure.compute.VirtualMachineIdentityArgs(
            type="SystemAssigned",
        ),
    )

    pulumi.export("vm_public_ip", public_ip.ip_address)
    pulumi.export("vm_name", vm.name)

elif deployment_type == "aks":
    # AKS deployment
    # Create AKS cluster
    aks = azure.containerservice.ManagedCluster(f"{app_name}-aks",
        resource_group_name=resource_group.name,
        location=resource_group.location,
        dns_prefix=app_name,
        agent_pool_profiles=[
            azure.containerservice.ManagedClusterAgentPoolProfileArgs(
                name="agentpool",
                count=2,
                vm_size="Standard_B2s",
                mode="System",
            ),
        ],
        identity=azure.containerservice.ManagedClusterIdentityArgs(
            type="SystemAssigned",
        ),
    )

    # Get AKS credentials
    creds = pulumi.Output.all(resource_group.name, aks.name).apply(
        lambda args: azure.containerservice.list_managed_cluster_user_credentials(
            resource_group_name=args[0],
            resource_name=args[1]
        )
    )

    # Export kubeconfig
    kubeconfig = creds.apply(lambda c: c.kubeconfigs[0].value)

    pulumi.export("kubeconfig", kubeconfig)
    pulumi.export("aks_cluster_name", aks.name)

# Export common outputs
pulumi.export("acr_login_server", acr.login_server)
pulumi.export("deployment_type", deployment_type)
pulumi.export("resource_group_name", resource_group.name)
