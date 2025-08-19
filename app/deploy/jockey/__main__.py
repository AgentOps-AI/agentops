import os
import subprocess
import click

from .backend import Pod
from . import DeploymentConfig, execute_serve
from .backend.event import EventStatus
from .environment import EKS_CLUSTER_NAME, AWS_REGION, AWS_PROFILE, KUBECONFIG_PATH, BUILDER_NAMESPACE, ALB_SHARED_GROUP_NAME


@click.group()
def cli():
    """Jockey - Kubernetes deployment management tool."""
    pass


@cli.command()
@click.option('--namespace', default='default', help='Kubernetes namespace to list pods from')
def list_instances(namespace):
    """List all running pod instances in the namespace."""
    try:
        pods = Pod.filter(namespace=namespace)

        if not pods:
            click.echo(f"No running instances found in namespace '{namespace}'.")
            return

        click.echo(f"Found {len(pods)} running instance(s) in namespace '{namespace}':\n")

        for pod in pods:
            status = "●" if pod.ready else "○"
            phase = pod.phase or "Unknown"
            node = pod.node_name or "N/A"

            click.echo(f"{status} {pod.name}")
            click.echo(f"  Phase: {phase}")
            click.echo(f"  Node: {node}")
            click.echo(f"  Restarts: {pod.restart_count}")
            if pod.pod_ip:
                click.echo(f"  IP: {pod.pod_ip}")
            click.echo()

    except Exception as e:
        click.echo(f"Error listing instances: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--namespace', default='default', help='Kubernetes namespace')
@click.argument('pod_name')
def stop_pod(namespace, pod_name):
    """Stop (delete) a pod by name."""
    try:
        click.echo(f"🛑 Stopping pod '{pod_name}' in namespace '{namespace}'...")

        success = Pod.delete_by_name(name=pod_name, namespace=namespace)

        if success:
            click.echo(f"✅ Pod '{pod_name}' deleted successfully!")
        else:
            click.echo(
                f"❌ Failed to delete pod '{pod_name}' - it may not exist or you may not have permission."
            )
            raise click.Abort()

    except Exception as e:
        click.echo(f"❌ Error stopping pod: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--namespace', default='default', help='Kubernetes namespace')
@click.argument('deployment_name')
def stop_deployment(namespace, deployment_name):
    """Stop (delete) a deployment by name."""
    try:
        from .backend.models.deployment import Deployment

        click.echo(f"🛑 Stopping deployment '{deployment_name}' in namespace '{namespace}'...")

        # Check if deployment exists first
        deployment = Deployment.get(name=deployment_name, namespace=namespace)
        if not deployment:
            click.echo(f"❌ Deployment '{deployment_name}' not found in namespace '{namespace}'.")
            raise click.Abort()

        # Delete the deployment
        success = Deployment.delete_by_name(name=deployment_name, namespace=namespace)

        if success:
            click.echo(f"✅ Deployment '{deployment_name}' deleted successfully!")
            click.echo("💡 All pods managed by this deployment will be terminated.")
        else:
            click.echo(f"❌ Failed to delete deployment '{deployment_name}'.")
            raise click.Abort()

    except Exception as e:
        click.echo(f"❌ Error stopping deployment: {e}", err=True)
        raise click.Abort()


@cli.command()
def setup_kubeconfig():
    """Generate kubeconfig for EKS cluster using AWS CLI."""
    try:
        # Assert required environment variables are set
        if not EKS_CLUSTER_NAME:
            raise ValueError("EKS_CLUSTER_NAME")
        if not AWS_REGION:
            raise ValueError("AWS_REGION")

        # Ensure config directory exists
        os.makedirs(os.path.dirname(KUBECONFIG_PATH), exist_ok=True)

        click.echo(f"Generating kubeconfig for cluster: {EKS_CLUSTER_NAME}")
        click.echo(f"Region: {AWS_REGION}")

        # Run aws eks update-kubeconfig command
        cmd = [
            'aws',
            'eks',
            'update-kubeconfig',
            '--region',
            AWS_REGION,
            '--name',
            EKS_CLUSTER_NAME,
            '--kubeconfig',
            KUBECONFIG_PATH,
        ]

        if AWS_PROFILE:
            cmd.extend(['--profile', AWS_PROFILE])

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            click.echo("✅ Kubeconfig generated successfully!")
            click.echo(f"Config saved to: {KUBECONFIG_PATH}")
        else:
            click.echo("❌ Failed to generate kubeconfig:")
            click.echo(result.stderr)
            raise click.Abort()

    except ValueError as e:
        click.echo(f"❌ Missing required environment variable: {e}")
        click.echo("Please ensure EKS_CLUSTER_NAME and AWS_REGION are set in your .env file")
        raise click.Abort()
    except FileNotFoundError:
        click.echo("❌ awscli not found. Please install it first.")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error generating kubeconfig: {e}")
        raise click.Abort()


@cli.command()
def setup_builder():
    """Setup builder namespace and create AWS credentials secret from local AWS CLI."""
    try:
        from .environment import KUBECONFIG_PATH, AWS_PROFILE
        
        click.echo("🔧 Setting up builder namespace and AWS credentials...")
        
        # Create builder namespace
        cmd = ['kubectl', '--kubeconfig', KUBECONFIG_PATH, 'create', 'namespace', BUILDER_NAMESPACE]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            click.echo("✅ Builder namespace created")
        elif "already exists" in result.stderr:
            click.echo("✅ Builder namespace already exists")
        else:
            click.echo(f"❌ Failed to create builder namespace: {result.stderr}")
            raise click.Abort()
        
        # Get AWS credentials from local AWS CLI
        aws_cmd = ['aws', 'configure', 'get', 'aws_access_key_id']
        if AWS_PROFILE:
            aws_cmd.extend(['--profile', AWS_PROFILE])
        
        access_key_result = subprocess.run(aws_cmd, capture_output=True, text=True)
        if access_key_result.returncode != 0:
            click.echo("❌ Failed to get AWS access key from local AWS CLI")
            click.echo("   Please ensure AWS CLI is configured with 'aws configure'")
            raise click.Abort()
        
        aws_cmd = ['aws', 'configure', 'get', 'aws_secret_access_key']
        if AWS_PROFILE:
            aws_cmd.extend(['--profile', AWS_PROFILE])
        
        secret_key_result = subprocess.run(aws_cmd, capture_output=True, text=True)
        if secret_key_result.returncode != 0:
            click.echo("❌ Failed to get AWS secret key from local AWS CLI")
            click.echo("   Please ensure AWS CLI is configured with 'aws configure'")
            raise click.Abort()
        
        access_key = access_key_result.stdout.strip()
        secret_key = secret_key_result.stdout.strip()
        
        if not access_key or not secret_key:
            click.echo("❌ AWS credentials are empty")
            click.echo("   Please ensure AWS CLI is configured with 'aws configure'")
            raise click.Abort()
        
        # Delete existing secret if it exists
        delete_cmd = ['kubectl', '--kubeconfig', KUBECONFIG_PATH, 'delete', 'secret', 'aws-credentials', '-n', BUILDER_NAMESPACE]
        subprocess.run(delete_cmd, capture_output=True, text=True)  # Ignore errors
        
        # Create aws-credentials secret in builder namespace
        secret_cmd = [
            'kubectl', '--kubeconfig', KUBECONFIG_PATH, 'create', 'secret', 'generic', 'aws-credentials',
            f'--from-literal=access-key={access_key}',
            f'--from-literal=secret-key={secret_key}',
            '--namespace', BUILDER_NAMESPACE
        ]
        
        result = subprocess.run(secret_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            click.echo("✅ AWS credentials secret created in builder namespace")
        else:
            click.echo(f"❌ Failed to create AWS credentials secret: {result.stderr}")
            raise click.Abort()
        
        click.echo("🎉 Builder namespace setup complete!")
        click.echo("   • Builder namespace created")
        click.echo("   • AWS credentials secret created from local AWS CLI")
        
    except FileNotFoundError:
        click.echo("❌ kubectl or aws CLI not found. Please install them first.")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error setting up builder namespace: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--name', help='Name for the test image (defaults to configured repository)')
@click.option('--namespace', default='default', help='Kubernetes namespace for build context')
@click.option('--template', default='test', help='Docker template to use (test or python-agent)')
def test_build(name, namespace, template):
    """Test image build and push with streaming progress."""
    try:
        from .backend.models.image import Image
        from .backend.event import EventStatus

        from jockey.environment import IMAGE_REGISTRY, IMAGE_REPOSITORY

        # Use default repository if no name provided
        image_name = name or IMAGE_REPOSITORY

        click.echo("🔨 Testing image build and push:")
        click.echo(f"   Name: {image_name}")
        click.echo(f"   Namespace: {namespace}")
        click.echo(f"   Template: {template}")
        click.echo("   Builder: Kaniko in-cluster")
        click.echo(f"   Registry: {IMAGE_REGISTRY}")
        click.echo()

        image = Image(
            name=image_name,
            tag='test',
            namespace=namespace,
            dockerfile_template=template,
        )

        click.echo("🔨 Building and pushing image...")
        for event in image.build():
            if event.status == EventStatus.STARTED:
                click.echo(f"   Started building {image.image_name}")
            elif event.status == EventStatus.PROGRESS and event.message:
                # Show build steps but filter out excessive output
                message = event.message.strip()
                if message and not message.startswith(' ---'):
                    click.echo(f"   {message}")
            elif event.status == EventStatus.COMPLETED:
                click.echo(f"✅ Build completed: {image.image_name}")
                click.echo(f"✅ Image pushed to registry: {image.url}")
                click.echo("💡 Image available for deployments in cluster!")
                return
            elif event.status == EventStatus.ERROR:
                click.echo(f"❌ Build failed: {event.message}")
                raise click.Abort()

    except Exception as e:
        click.echo(f"❌ Error during build test: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--namespace', default=BUILDER_NAMESPACE, help=f'Kubernetes namespace (defaults to {BUILDER_NAMESPACE})')
@click.option('--follow', '-f', is_flag=True, help='Follow/stream logs in real-time')
def logs_builder(namespace, follow):
    """Show logs from the most recent builder pod."""
    try:
        # Search only in the builder namespace (or specified namespace)
        pods = Pod.filter(namespace=namespace, label_selector="job-name")
        builder_pods = [p for p in pods if p.name.startswith('builder-')]

        if not builder_pods:
            click.echo(f"No builder pods found in namespace '{namespace}'.")
            return

        # Sort by creation time (most recent first)
        builder_pods.sort(key=lambda p: p.creation_timestamp or "", reverse=True)
        latest_builder = builder_pods[0]

        click.echo(f"📋 Showing logs for builder pod: {latest_builder.name}")
        click.echo(f"   Namespace: {latest_builder.namespace}")
        click.echo(f"   Phase: {latest_builder.phase}")
        click.echo(f"   Created: {latest_builder.creation_timestamp}")
        click.echo()

        # Use kubectl to follow logs
        import subprocess
        from .environment import KUBECONFIG_PATH

        cmd = ['kubectl', '--kubeconfig', KUBECONFIG_PATH, 'logs', latest_builder.name, '-n', latest_builder.namespace]

        if follow:
            cmd.append('--follow')

        # Stream logs directly to terminal
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        try:
            for line in process.stdout:
                click.echo(line.rstrip())
        except KeyboardInterrupt:
            process.terminate()
            click.echo("\n🛑 Log streaming stopped.")

        process.wait()

    except Exception as e:
        click.echo(f"❌ Error getting builder logs: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--name', help='Name for the test application (defaults to configured repository)')
@click.option('--namespace', default='default', help='Kubernetes namespace')
@click.option('--template', default='test', help='Docker template to use (test, simple-api, or python-agent)')
def deploy_test(name, namespace, template):
    """Deploy a minimal test application with health checks."""
    from jockey.environment import IMAGE_REGISTRY, IMAGE_REPOSITORY

    # Use default repository if no name provided
    click.echo(f"🚀 Starting test deployment: {name or IMAGE_REPOSITORY}")
    click.echo(f"   Namespace: {namespace}")
    click.echo(f"   Template: {template}")
    click.echo(f"   Registry: {IMAGE_REGISTRY}")
    click.echo()

    # Create deployment config without repository
    config = DeploymentConfig(
        namespace=namespace,
        tag='test',
        dockerfile_template=template,
        ports=[8080],  # Simple API runs on port 8080
    )

    # Deploy with progress events and capture the return value
    generator = execute_serve(config)
    deployment = None

    try:
        for event in generator:
            if hasattr(event, 'event_type'):
                if event.event_type == 'build':
                    if event.status == EventStatus.STARTED:
                        click.echo("🔨 Building Docker image...")
                    elif event.status == EventStatus.PROGRESS and event.message:
                        click.echo(f"   {event.message.strip()}")
                    elif event.status == EventStatus.COMPLETED:
                        click.echo(f"✅ Build completed: {name or IMAGE_REPOSITORY}:test")
                    elif event.status == EventStatus.ERROR:
                        click.echo(f"❌ Build failed: {event.message}")
                        raise click.Abort()

                elif event.event_type == 'push':
                    if event.status == EventStatus.STARTED:
                        click.echo("📤 Pushing to registry...")
                    elif event.status == EventStatus.PROGRESS and event.message:
                        # Only show important push messages
                        if 'digest:' in event.message or 'Pushed' in event.message:
                            click.echo(f"   {event.message}")
                    elif event.status == EventStatus.COMPLETED:
                        click.echo(f"✅ Push completed: {event.image_url}")
                    elif event.status == EventStatus.ERROR:
                        click.echo(f"❌ Push failed: {event.message}")
                        raise click.Abort()

                elif event.event_type == 'deployment':
                    if event.status == EventStatus.STARTED:
                        click.echo("🚀 Deploying to Kubernetes...")
                    elif event.status == EventStatus.PROGRESS:
                        click.echo(f"   {event.message}")
                    elif event.status == EventStatus.COMPLETED:
                        click.echo(f"✅ Deployment ready: {event.message}")
                    elif event.status == EventStatus.ERROR:
                        click.echo(f"❌ Deployment failed: {event.message}")
                        raise click.Abort()
    except StopIteration as e:
        # Capture the return value from the generator
        deployment = e.value

    if deployment:
        click.echo("\n🎉 Test deployment successful!")
        click.echo(f"   Name: {deployment.name}")
        click.echo(f"   Image: {deployment.image_url}")
        click.echo(f"   Namespace: {deployment.namespace}")
        click.echo("\n💡 Use 'jockey list-instances' to check status")
    else:
        click.echo("⚠️  Deployment completed but no final deployment object returned")


@cli.command()
@click.option('--namespace', default='default', help='Kubernetes namespace to search')
def list_alb_ingresses(namespace):
    """List all ingresses using the shared ALB."""
    try:
        from .backend.models.service import Ingress
        
        click.echo(f"🔍 Searching for ingresses using shared ALB: {ALB_SHARED_GROUP_NAME}")
        click.echo(f"   Namespace: {namespace}")
        click.echo()
        
        ingresses = Ingress.filter(namespace=namespace)
        shared_alb_ingresses = []
        
        for ingress in ingresses:
            annotations = ingress.data.metadata.annotations or {}
            group_name = annotations.get('alb.ingress.kubernetes.io/group.name', '')
            if group_name == ALB_SHARED_GROUP_NAME:
                shared_alb_ingresses.append(ingress)
        
        if not shared_alb_ingresses:
            click.echo(f"No ingresses found using shared ALB group: {ALB_SHARED_GROUP_NAME}")
            return
        
        click.echo(f"Found {len(shared_alb_ingresses)} ingress(es) using shared ALB:")
        click.echo()
        
        for ingress in shared_alb_ingresses:
            annotations = ingress.data.metadata.annotations or {}
            hostname = ingress.hostname or "N/A"
            alb_hostname = ingress.load_balancer_hostname or "Pending"
            tags = annotations.get('alb.ingress.kubernetes.io/tags', 'N/A')
            
            click.echo(f"📋 {ingress.name}")
            click.echo(f"   Hostname: {hostname}")
            click.echo(f"   ALB Hostname: {alb_hostname}")
            click.echo(f"   Tags: {tags}")
            click.echo(f"   Namespace: {ingress.namespace}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Error listing ALB ingresses: {e}", err=True)
        raise click.Abort()


@cli.command()
def alb_status():
    """Check the status of the shared ALB configuration."""
    try:
        from .backend.models.service import Ingress
        
        click.echo(f"🔍 Checking shared ALB status: {ALB_SHARED_GROUP_NAME}")
        click.echo()
        
        # Get all ingresses across all namespaces
        all_ingresses = []
        namespaces = ['default', 'kube-system', 'agentops-deploy']  # Common namespaces
        
        for namespace in namespaces:
            try:
                ingresses = Ingress.filter(namespace=namespace)
                all_ingresses.extend(ingresses)
            except:
                continue  # Skip if namespace doesn't exist or no access
        
        shared_alb_ingresses = []
        for ingress in all_ingresses:
            annotations = ingress.data.metadata.annotations or {}
            group_name = annotations.get('alb.ingress.kubernetes.io/group.name', '')
            if group_name == ALB_SHARED_GROUP_NAME:
                shared_alb_ingresses.append(ingress)
        
        if not shared_alb_ingresses:
            click.echo(f"⚠️  No ingresses found using shared ALB group: {ALB_SHARED_GROUP_NAME}")
            click.echo("   This means the shared ALB is not yet provisioned.")
            return
        
        # Check ALB status
        alb_hostnames = set()
        ready_count = 0
        
        for ingress in shared_alb_ingresses:
            alb_hostname = ingress.load_balancer_hostname
            if alb_hostname:
                alb_hostnames.add(alb_hostname)
                ready_count += 1
        
        click.echo(f"✅ Shared ALB Status:")
        click.echo(f"   Group Name: {ALB_SHARED_GROUP_NAME}")
        click.echo(f"   Total Ingresses: {len(shared_alb_ingresses)}")
        click.echo(f"   Ready Ingresses: {ready_count}")
        click.echo(f"   ALB Hostnames: {len(alb_hostnames)}")
        
        if alb_hostnames:
            click.echo("   ALB Endpoints:")
            for hostname in alb_hostnames:
                click.echo(f"     - {hostname}")
        
        # Show ingresses by namespace
        namespace_counts = {}
        for ingress in shared_alb_ingresses:
            ns = ingress.namespace
            namespace_counts[ns] = namespace_counts.get(ns, 0) + 1
        
        click.echo("   Ingresses by namespace:")
        for ns, count in namespace_counts.items():
            click.echo(f"     - {ns}: {count}")
            
    except Exception as e:
        click.echo(f"❌ Error checking ALB status: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option('--namespace', default='default', help='Kubernetes namespace')
@click.argument('hostname')
def validate_alb_routing(namespace, hostname):
    """Validate that ALB routing is configured correctly for a hostname."""
    try:
        from .backend.models.service import Ingress
        
        click.echo(f"🔍 Validating ALB routing for hostname: {hostname}")
        click.echo(f"   Namespace: {namespace}")
        click.echo(f"   Shared ALB Group: {ALB_SHARED_GROUP_NAME}")
        click.echo()
        
        ingresses = Ingress.filter(namespace=namespace)
        matching_ingresses = []
        
        for ingress in ingresses:
            if ingress.hostname == hostname:
                matching_ingresses.append(ingress)
        
        if not matching_ingresses:
            click.echo(f"❌ No ingresses found for hostname: {hostname}")
            return
        
        ingress = matching_ingresses[0]
        annotations = ingress.data.metadata.annotations or {}
        
        # Check ALB configuration
        group_name = annotations.get('alb.ingress.kubernetes.io/group.name', '')
        scheme = annotations.get('alb.ingress.kubernetes.io/scheme', '')
        target_type = annotations.get('alb.ingress.kubernetes.io/target-type', '')
        tags = annotations.get('alb.ingress.kubernetes.io/tags', '')
        
        click.echo(f"✅ Ingress Configuration:")
        click.echo(f"   Name: {ingress.name}")
        click.echo(f"   Hostname: {ingress.hostname}")
        click.echo(f"   ALB Group: {group_name}")
        click.echo(f"   Scheme: {scheme}")
        click.echo(f"   Target Type: {target_type}")
        click.echo(f"   Tags: {tags}")
        click.echo(f"   ALB Hostname: {ingress.load_balancer_hostname or 'Pending'}")
        
        # Validation checks
        issues = []
        if group_name != ALB_SHARED_GROUP_NAME:
            issues.append(f"Group name mismatch: expected {ALB_SHARED_GROUP_NAME}, got {group_name}")
        if scheme != 'internet-facing':
            issues.append(f"Scheme should be 'internet-facing', got '{scheme}'")
        if target_type != 'ip':
            issues.append(f"Target type should be 'ip', got '{target_type}'")
        if not tags:
            issues.append("No ALB tags configured")
        
        if issues:
            click.echo()
            click.echo("⚠️  Configuration Issues:")
            for issue in issues:
                click.echo(f"   - {issue}")
        else:
            click.echo()
            click.echo("✅ All validations passed!")
            
    except Exception as e:
        click.echo(f"❌ Error validating ALB routing: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
