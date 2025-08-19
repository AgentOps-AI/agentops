import os
import subprocess
import time
from pathlib import Path
import pytest
from .common import REPO_ROOT, is_github_actions, get_free_port


# these vars are also hard-coded inside the `clickhouse_server` Dockerfile and the
# github actions workflow
TEST_CLICKHOUSE_HOST = "localhost"
TEST_CLICKHOUSE_PORT = get_free_port(8123)
TEST_CLICKHOUSE_HTTP_PORT = get_free_port(9000)
TEST_CLICKHOUSE_DATABASE = "otel_2"  # this has to be the same as prod because the schema has it hard-coded
TEST_CLICKHOUSE_USER = "default"
TEST_CLICKHOUSE_PASSWORD = "clickhouse"

CLICKHOUSE_MIGRATIONS_DIR = REPO_ROOT / 'clickhouse' / 'migrations'
CLICKHOUSE_DOCKER_IMAGE_PATH = Path(__file__).parent / "clickhouse_server" / "Dockerfile"
CLICKHOUSE_DOCKER_CONTAINER_NAME = "agentops-test-clickhouse"

__all__ = [
    'clickhouse_verify_test_environment',
    'clickhouse_setup_db_server',
    'clickhouse_client',
    'async_clickhouse_client',
]


@pytest.fixture(scope="session", autouse=True)
def clickhouse_verify_test_environment():
    """Verify we don't have access to production credentials before running tests."""
    message = "%s environment variable is set! This risks connecting to production."
    assert not os.environ.get('CLICKHOUSE_HOST'), message % "CLICKHOUSE_HOST"
    assert not os.environ.get('CLICKHOUSE_PORT'), message % "CLICKHOUSE_PORT"
    assert not os.environ.get('CLICKHOUSE_DATABASE'), message % "CLICKHOUSE_DATABASE"
    assert not os.environ.get('CLICKHOUSE_USER'), message % "CLICKHOUSE_USER"
    assert not os.environ.get('CLICKHOUSE_PASSWORD'), message % "CLICKHOUSE_PASSWORD"


def clickhouse_start_docker():
    """Start the Docker container for ClickHouse."""
    print("Starting ClickHouse Docker container...")

    # Clean up any existing container
    subprocess.run(['docker', 'stop', CLICKHOUSE_DOCKER_CONTAINER_NAME], check=False)
    subprocess.run(['docker', 'rm', CLICKHOUSE_DOCKER_CONTAINER_NAME], check=False)

    # Build the Docker image
    build_command = [
        'docker',
        'build',
        '-t',
        CLICKHOUSE_DOCKER_CONTAINER_NAME,
        '-f',
        str(CLICKHOUSE_DOCKER_IMAGE_PATH),
        str(CLICKHOUSE_DOCKER_IMAGE_PATH.parent),
    ]
    print(' '.join(build_command))
    subprocess.run(build_command, check=True)

    # Run the container
    run_command = [
        'docker',
        'run',
        '-d',
        '--name',
        CLICKHOUSE_DOCKER_CONTAINER_NAME,
        '-p',
        f'{TEST_CLICKHOUSE_PORT}:8123',
        '-p',
        f'{TEST_CLICKHOUSE_HTTP_PORT}:9000',
        CLICKHOUSE_DOCKER_CONTAINER_NAME,
    ]
    print(' '.join(run_command))
    subprocess.run(run_command, check=True)


def clickhouse_stop_docker():
    """Stop the Docker container."""
    print("Stopping ClickHouse Docker container...")
    subprocess.run(['docker', 'stop', CLICKHOUSE_DOCKER_CONTAINER_NAME], check=True)


def clickhouse_verify_connection(client):
    """Verify the connection to the database uses the test environment."""

    def _get_auth_header(username: str, password: str) -> str:
        from base64 import b64encode

        # from clickhouse_connect/driver/httpclient.py:126
        return 'Basic ' + b64encode(f'{username}:{password}'.encode()).decode()

    assert TEST_CLICKHOUSE_HOST in client.url
    assert str(TEST_CLICKHOUSE_PORT) in client.url
    assert client.database == TEST_CLICKHOUSE_DATABASE
    assert client.headers['Authorization'] == _get_auth_header(TEST_CLICKHOUSE_USER, TEST_CLICKHOUSE_PASSWORD)


async def clickhouse_run_migrations(client):
    """Run database schema initialization and migrations."""
    print("Running ClickHouse migrations...")

    # Basic setup
    # extracted from prod with:
    # SELECT concat('SET ', name, ' = \'', value, '\';') as settings FROM system.settings WHERE changed = 1 FORMAT TSVRaw;
    setup_query = """
SET min_joined_block_size_bytes = '524288';
SET max_insert_threads = '2';
SET max_insert_delayed_streams_for_parallel_write = '50';
SET max_threads = '5';
SET use_concurrency_control = '0';
SET use_hedged_requests = '0';
SET s3_skip_empty_files = '0';
SET distributed_foreground_insert = '1';
SET insert_distributed_sync = '1';
SET alter_sync = '0';
SET replication_alter_partitions_sync = '0';
SET allow_suspicious_types_in_group_by = '1';
SET allow_suspicious_types_in_order_by = '1';
SET enable_memory_bound_merging_of_aggregation_results = '1';
SET merge_tree_use_v1_object_and_dynamic_serialization = '1';
SET do_not_merge_across_partitions_select_final = '0';
SET log_queries = '1';
SET log_queries_probability = '1';
SET http_response_headers = '{}';
SET max_http_get_redirects = '10';
SET send_progress_in_http_headers = '1';
SET http_headers_progress_interval_ms = '60000';
SET query_plan_join_swap_table = '0';
SET enable_zstd_qat_codec = '0';
SET query_profiler_real_time_period_ns = '0';
SET max_bytes_before_external_group_by = '8589934592';
SET max_bytes_before_external_sort = '8589934592';
SET max_result_rows = '500000';
SET result_overflow_mode = 'break';
SET join_algorithm = 'default';
SET max_memory_usage = '17179869184';
SET backup_restore_keeper_max_retries = '20';
SET backup_restore_keeper_retry_max_backoff_ms = '60000';
SET backup_restore_failure_after_host_disconnected_for_seconds = '0';
SET backup_restore_keeper_max_retries_while_initializing = '0';
SET backup_restore_keeper_max_retries_while_handling_error = '0';
SET backup_restore_finish_timeout_after_error_sec = '0';
SET enable_job_stack_trace = '0';
SET cancel_http_readonly_queries_on_client_close = '1';
SET least_greatest_legacy_null_behavior = '1';
SET max_table_size_to_drop = '1000000000000';
SET max_partition_size_to_drop = '1000000000000';
SET default_table_engine = 'ReplicatedMergeTree';
SET mutations_sync = '0';
SET validate_mutation_query = '0';
SET optimize_trivial_insert_select = '0';
SET max_size_to_preallocate_for_aggregation = '100000000';
SET max_size_to_preallocate_for_joins = '100000000';
SET database_replicated_allow_only_replicated_engine = '1';
SET database_replicated_allow_replicated_engine_arguments = '2';
SET cloud_mode = '1';
SET cloud_mode_engine = '2';
SET distributed_ddl_output_mode = 'none_only_active';
SET distributed_ddl_entry_format_version = '6';
SET query_plan_merge_filters = '1';
SET async_insert_max_data_size = '10485760';
SET async_insert_busy_timeout_max_ms = '1000';
SET async_insert_busy_timeout_ms = '1000';
SET enable_filesystem_cache = '1';
SET filesystem_cache_name = 's3diskWithCache';
SET enable_filesystem_cache_on_write_operations = '1';
SET filesystem_cache_skip_download_if_exceeds_per_query_cache_write_limit = '1';
SET skip_download_if_exceeds_query_cache = '1';
SET filesystem_cache_boundary_alignment = '0';
SET load_marks_asynchronously = '1';
SET allow_prefetched_read_pool_for_remote_filesystem = '1';
SET filesystem_prefetch_max_memory_usage = '1717986918';
SET filesystem_prefetches_limit = '200';
SET compatibility = '24.10';
SET insert_keeper_max_retries = '20';
SET cluster_for_parallel_replicas = 'default';
SET parallel_replicas_local_plan = '0';
SET push_external_roles_in_interserver_queries = '0';
--SET shared_merge_tree_sync_parts_on_partition_operations = '1';
SET allow_experimental_materialized_postgresql_table = '0';
SET enable_deflate_qpl_codec = '0';
SET date_time_input_format = 'best_effort';
    """
    for command in setup_query.split(';'):
        try:
            client.command(command)
        except Exception as e:
            if "Empty query" in str(e):
                continue
            raise e

    # Find and run migration files
    migration_files = sorted(CLICKHOUSE_MIGRATIONS_DIR.glob('*.sql'))
    print(f"Running {len(migration_files)} migrations...")

    for migration_file in migration_files:
        print(f"Running migration: {os.path.basename(migration_file)}")
        with open(migration_file) as f:
            sql = f.read()
            # run commands one at a time cuz that's how it be in Clickhouse
            for command in sql.split(';'):
                try:
                    client.command(command)
                except Exception as e:
                    if "Empty query" in str(e):
                        continue
                    raise e

    print("Migrations complete!")


@pytest.fixture(scope="session", autouse=True)
async def clickhouse_setup_db_server():
    """Configure test database server and connection."""
    from agentops.api.db.clickhouse_client import ConnectionConfig, get_clickhouse

    # Override environment variables for test
    ConnectionConfig.host = TEST_CLICKHOUSE_HOST
    ConnectionConfig.port = TEST_CLICKHOUSE_PORT
    ConnectionConfig.database = TEST_CLICKHOUSE_DATABASE
    ConnectionConfig.username = TEST_CLICKHOUSE_USER
    ConnectionConfig.password = TEST_CLICKHOUSE_PASSWORD
    ConnectionConfig.secure = False

    if not is_github_actions():
        clickhouse_start_docker()

    print(f"Waiting for ClickHouse to be ready at {TEST_CLICKHOUSE_HOST}:{TEST_CLICKHOUSE_PORT}...")

    # Wait for ClickHouse to be available
    for attempt in range(30):
        try:
            # Use clickhouse_connect directly for the health check
            client = get_clickhouse()
            client.command("SELECT 1")
            print("ClickHouse is ready!")
            break
        except Exception:
            print('.', end='', flush=True)
            time.sleep(2)
    else:
        raise Exception("Failed to connect to ClickHouse after multiple attempts")

    # Get clickhouse client and verify connection
    client = get_clickhouse()
    clickhouse_verify_connection(client)

    # Run migrations
    await clickhouse_run_migrations(client)

    try:
        yield
    finally:
        if not is_github_actions():
            clickhouse_stop_docker()


@pytest.fixture(scope="function")
async def clickhouse_client():
    """Fixture to provide a clickhouse client for tests."""
    from agentops.api.db.clickhouse_client import get_clickhouse

    client = get_clickhouse()
    clickhouse_verify_connection(client)

    yield client


@pytest.fixture(scope="function")
async def async_clickhouse_client():
    """Fixture to provide an async clickhouse client for tests."""
    from agentops.api.db.clickhouse_client import get_async_clickhouse

    client = await get_async_clickhouse()
    clickhouse_verify_connection(client.client)

    yield client
