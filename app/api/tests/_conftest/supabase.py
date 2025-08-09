import os
import subprocess
from pathlib import Path
import pytest
from .common import is_github_actions, get_free_port


# these vars are also hard-coded inside the `supabase_server` Dockerfile and the
# github actions workflow
TEST_SUPABASE_HOST = "localhost"
TEST_SUPABASE_PORT = get_free_port(5432)
TEST_SUPABASE_NAME = "test_db"
TEST_SUPABASE_USER = "postgres"
TEST_SUPABASE_PASSWORD = "postgres"

SUPABASE_DOCKER_IMAGE_PATH = Path(__file__).parent / "supabase_server" / "Dockerfile"
SUPABASE_DOCKER_CONTAINER_NAME = "agentops-test-supabase"

__all__ = [
    'supabase_verify_test_environment',
    'supabase_setup_db_server',
    'db_session',
    'orm_session',
]


@pytest.fixture(scope="session", autouse=True)
def supabase_verify_test_environment():
    """Verify we don't have access to production credentials before running tests."""
    message = "%s environment variable is set! This risks connecting to production."
    assert not os.environ.get('SUPABASE_HOST'), message % "SUPABASE_HOST"
    assert not os.environ.get('SUPABASE_PORT'), message % "SUPABASE_PORT"
    assert not os.environ.get('SUPABASE_DATABASE'), message % "SUPABASE_DATABASE"
    assert not os.environ.get('SUPABASE_USER'), message % "SUPABASE_USER"
    assert not os.environ.get('SUPABASE_PASSWORD'), message % "SUPABASE_PASSWORD"


def supabase_start_docker():
    """Start the Docker container for PostgreSQL."""
    print("Starting Supabase/Postgres Docker container...")

    subprocess.run(['docker', 'stop', SUPABASE_DOCKER_CONTAINER_NAME], check=False)
    subprocess.run(['docker', 'rm', SUPABASE_DOCKER_CONTAINER_NAME], check=False)
    subprocess.run(
        [
            'docker',
            'build',
            '-t',
            SUPABASE_DOCKER_CONTAINER_NAME,
            '-f',
            str(SUPABASE_DOCKER_IMAGE_PATH),
            str(SUPABASE_DOCKER_IMAGE_PATH.parent),
        ],
        check=True,
    )
    subprocess.run(
        [
            'docker',
            'run',
            '-d',
            '--name',
            SUPABASE_DOCKER_CONTAINER_NAME,
            '-p',
            f'{TEST_SUPABASE_PORT}:5432',
            SUPABASE_DOCKER_CONTAINER_NAME,
        ],
        check=True,
    )


def supabase_stop_docker():
    """Stop the Docker container."""
    print("Stopping Supabase/Postgres Docker container...")
    subprocess.run(['docker', 'stop', SUPABASE_DOCKER_CONTAINER_NAME], check=True)


def supabase_verify_connection(conn):
    """Verify the connection to the database uses the test environment."""
    assert conn.info.host == TEST_SUPABASE_HOST
    assert conn.info.port == TEST_SUPABASE_PORT
    assert conn.info.dbname == TEST_SUPABASE_NAME
    assert conn.info.user == TEST_SUPABASE_USER
    assert conn.info.password == TEST_SUPABASE_PASSWORD


async def supabase_run_migrations(conn):
    """Run database schema initialization and migrations."""

    print("Running Supabase migrations...")
    with conn.cursor() as cur:
        # we need to do some stuff to get the new database to match what we expect
        # in Supabase. Some of these `SET`s might not be necessary, but they don't hurt.
        setup_query = """
        SET statement_timeout = 0;
        SET lock_timeout = 0;
        SET idle_in_transaction_session_timeout = 0;
        SET client_encoding = 'UTF8';
        SET standard_conforming_strings = on;
        SET search_path TO public;
        SET check_function_bodies = false;
        SET xmloption = content;
        SET client_min_messages = warning;
        SET row_security = off;

        -- Create essential extensions
        CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS pgcrypto;

        -- Create auth schema and dummy JWT function
        CREATE OR REPLACE FUNCTION auth.jwt() RETURNS jsonb AS $$
        BEGIN
            RETURN '{"role": "authenticated", "sub": "00000000-0000-0000-0000-000000000000"}'::jsonb;
        END;
        $$ LANGUAGE plpgsql;

        -- the production bucket table differs from the one in the docker image
        -- so we drop it and recreate it
        DROP TABLE IF EXISTS storage.buckets CASCADE;
        CREATE TABLE IF NOT EXISTS storage.buckets (
            id text NOT NULL,
            name text NOT NULL,
            owner uuid,
            created_at timestamp with time zone DEFAULT now(),
            updated_at timestamp with time zone DEFAULT now(),
            public boolean DEFAULT false,
            avif_autodetection boolean DEFAULT false,
            file_size_limit bigint,
            allowed_mime_types text[],
            CONSTRAINT buckets_pkey PRIMARY KEY (id)
        );

        -- create two test users in the auth.users table so that we can reference them
        -- TODO move these to be inside the test_user, test_user2, and test_user3 fixtures
        -- so that it's obvious they are dependencies
        INSERT INTO auth.users (
            id,
            instance_id,
            aud,
            role,
            email,
            encrypted_password,
            confirmed_at,
            created_at,
            updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000000',
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            'test@example.com',
            '$2a$10$abcdefghijklmnopqrstuvwxyz0123456789',
            NOW(),
            NOW(),
            NOW()
        ), (
            '00000000-0000-0000-0000-000000000001',
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            'test2@example.com',
            '$2a$10$abcdefghijklmnopqrstuvwxyz0123456789',
            NOW(),
            NOW(),
            NOW()
        ), (
            '00000000-0000-0000-0000-000000000002',
            '00000000-0000-0000-0000-000000000000',
            'authenticated',
            'authenticated',
            'test3@example.com',
            '$2a$10$abcdefghijklmnopqrstuvwxyz0123456789',
            NOW(),
            NOW(),
            NOW()
        );
        """
        cur.execute(setup_query)

        # migration files sorted by name
        migrations_dir = Path(__file__).parents[3] / 'supabase' / 'migrations'
        migration_files = sorted(migrations_dir.glob('*.sql'))

        print(f"Running {len(migration_files)} migrations...")

        for migration_file in migration_files:
            print(f"Running migration: {os.path.basename(migration_file)}")
            with open(migration_file) as f:
                sql = f.read()
                cur.execute(sql)

        # update public.orgs to have a `subscription_id TEXT DEFAULT ''` because this is in
        # prod, but not in the schema migrations.
        orgs_subscription_id_query = """
        ALTER TABLE public.orgs
        ADD COLUMN IF NOT EXISTS subscription_id TEXT DEFAULT '';
        """
        cur.execute(orgs_subscription_id_query)

    conn.commit()  # must commit transaction to apply changes
    print("Migrations complete!")


@pytest.fixture(scope="session", autouse=True)
async def supabase_setup_db_server():
    """Configure test database server and connection."""
    import time
    import psycopg
    from agentops.common.postgres import get_connection, close_connection, ConnectionConfig

    # Close any existing connections (sweaty)
    close_connection()

    if not is_github_actions():
        supabase_start_docker()

    # NOTE: we do not need to save or restore these variables as the tests will run
    # and then we'll be done
    ConnectionConfig.host = TEST_SUPABASE_HOST
    ConnectionConfig.port = TEST_SUPABASE_PORT
    ConnectionConfig.database = TEST_SUPABASE_NAME
    ConnectionConfig.user = TEST_SUPABASE_USER
    ConnectionConfig.password = TEST_SUPABASE_PASSWORD

    print(f"Waiting for PostgreSQL to be ready at {ConnectionConfig.host}:{ConnectionConfig.port}...")

    for attempt in range(30):
        try:
            # Use psycopg directly for the health check
            conn = psycopg.connect(ConnectionConfig.to_connection_string())
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            conn.close()
            print("PostgreSQL is ready!")
            break
        except Exception:
            print('.', end='', flush=True)
            time.sleep(2)
    else:
        raise Exception("Failed to connect to PostgreSQL after multiple attempts")

    pool = get_connection()
    with pool.connection() as conn:
        # double-check connection info (sweaty)
        supabase_verify_connection(conn)

        # run migrations once for the session
        await supabase_run_migrations(conn)

    yield

    if not is_github_actions():
        supabase_stop_docker()


@pytest.fixture(scope="session")
async def db_session():
    """Session fixture providing a database connection."""
    from agentops.common.postgres import get_connection, close_connection

    print("Creating database connection...")
    pool = get_connection()
    with pool.connection() as conn:
        try:
            # double-check connection uses test creds (sweaty)
            supabase_verify_connection(conn)

            yield conn
        except Exception as e:
            print(f"Error during database session: {str(e)}")
            conn.rollback()
        finally:
            close_connection()


@pytest.fixture(scope="session")
async def orm_session():
    """Fixture to provide an orm session for tests."""
    # does not automatically commit or rollback
    from agentops.common.orm import get_orm_session

    session = next(get_orm_session())

    # double-check connection uses test creds (sweaty)
    conn = session.connection()
    supabase_verify_connection(conn.connection.driver_connection)

    yield session

    session.close()
