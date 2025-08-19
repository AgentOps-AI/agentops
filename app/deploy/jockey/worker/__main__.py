import click
import signal
import sys
from jockey.worker.worker import Worker


@click.group()
def cli():
    """Jockey deployment worker."""
    pass


@cli.command()
def start():
    """Start the deployment worker to process queued jobs."""
    from jockey.environment import WORKER_POLL_INTERVAL

    click.echo("🚀 Starting deployment worker...")
    click.echo("Press Ctrl+C to stop")
    click.echo(f"Polling interval: {WORKER_POLL_INTERVAL} seconds (from WORKER_POLL_INTERVAL env var)")

    worker = Worker()

    def signal_handler(signum, frame):
        click.echo("\n🛑 Received shutdown signal, stopping worker...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        worker.start()
    except KeyboardInterrupt:
        click.echo("\n🛑 Stopping deployment worker...")
        worker.stop()


@cli.command()
def status():
    """Check worker and queue status."""
    from jockey.worker import queue

    try:
        # Test Redis connection
        if queue.health_check():
            click.echo("✅ Redis connection: OK")
        else:
            click.echo("❌ Redis connection: Failed")
            raise click.Abort()

        # Get pending jobs count
        pending_count = queue.get_queue_length()
        click.echo(f"📋 Pending jobs: {pending_count}")

        # Get processing jobs count (jobs that exist but not in queue)
        all_job_keys = len(queue._get_redis_client().keys("jobs:*"))
        processing_count = all_job_keys - pending_count
        click.echo(f"⚙️  Processing jobs: {processing_count}")

        # Simple status summary
        if pending_count > 0 or processing_count > 0:
            click.echo("📊 Queue status: Active")
        else:
            click.echo("📊 Queue status: Idle")

    except Exception as e:
        click.echo(f"❌ Error checking status: {e}", err=True)
        raise click.Abort()


@cli.command()
def health():
    """Health check for container monitoring."""
    from jockey.worker import queue

    try:
        # Test Redis connection - this is our main dependency
        if queue.health_check():
            # Exit 0 for healthy
            sys.exit(0)
        else:
            # Exit 1 for unhealthy
            sys.exit(1)
    except Exception:
        # Exit 1 for any errors
        sys.exit(1)


if __name__ == "__main__":
    cli()
