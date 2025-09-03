import os
import logging

logger = logging.getLogger(__name__)

SUPABASE_URL: str = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")

SUPABASE_S3_BUCKET: str = os.getenv("SUPABASE_S3_BUCKET")
SUPABASE_S3_LOGS_BUCKET: str = os.getenv("SUPABASE_S3_LOGS_BUCKET")
SUPABASE_S3_ACCESS_KEY_ID: str = os.getenv("SUPABASE_S3_ACCESS_KEY_ID")
SUPABASE_S3_SECRET_ACCESS_KEY: str = os.getenv("SUPABASE_S3_SECRET_ACCESS_KEY")

JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")

CLICKHOUSE_HOST: str = os.getenv("CLICKHOUSE_HOST")
CLICKHOUSE_PORT: int = int(os.getenv("CLICKHOUSE_PORT", 0))
CLICKHOUSE_USER: str = os.getenv("CLICKHOUSE_USER", "")
CLICKHOUSE_PASSWORD: str = os.getenv("CLICKHOUSE_PASSWORD", "")
CLICKHOUSE_DATABASE: str = os.getenv("CLICKHOUSE_DATABASE", "")
CLICKHOUSE_SECURE: bool = os.getenv("CLICKHOUSE_SECURE", "false").lower() in ("1", "true", "yes")


PROFILING_ENABLED: bool = os.environ.get("PROFILING_ENABLED", "false").lower() == "true"
PROFILING_FORMAT: str = os.environ.get("PROFILING_FORMAT", "html")
if PROFILING_FORMAT not in ["html", "speedscope"]:
    PROFILING_FORMAT = "html"
PROFILING_OUTPUT_DIR: str = os.environ.get("PROFILING_OUTPUT_DIR", ".")

# Stripe Configuration
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_SUBSCRIPTION_PRICE_ID: str = os.getenv("STRIPE_SUBSCRIPTION_PRICE_ID", "")
STRIPE_TOKEN_PRICE_ID: str = os.getenv("STRIPE_TOKEN_PRICE_ID", "")
STRIPE_SPAN_PRICE_ID: str = os.getenv("STRIPE_SPAN_PRICE_ID", "")


# Log Stripe configuration status on module load
def _log_stripe_config():
    """Log the status of Stripe environment variables for debugging"""
    stripe_vars = {
        "STRIPE_SECRET_KEY": STRIPE_SECRET_KEY,
        "STRIPE_WEBHOOK_SECRET": STRIPE_WEBHOOK_SECRET,
        "STRIPE_SUBSCRIPTION_PRICE_ID": STRIPE_SUBSCRIPTION_PRICE_ID,
        "STRIPE_TOKEN_PRICE_ID": STRIPE_TOKEN_PRICE_ID,
        "STRIPE_SPAN_PRICE_ID": STRIPE_SPAN_PRICE_ID,
    }

    logger.info("=== Stripe Configuration Status ===")
    found_count = 0
    missing_vars = []
    for var_name, var_value in stripe_vars.items():
        if var_value:
            # Show first 8 characters for verification without exposing secrets
            masked_value = f"{var_value[:8]}..." if len(var_value) > 8 else var_value
            logger.info(f"✓ {var_name}: {masked_value}")
            found_count += 1
        else:
            logger.warning(f"✗ {var_name}: NOT FOUND")
            missing_vars.append(var_name)

    logger.info(f"Stripe configuration: {found_count}/{len(stripe_vars)} variables found")

    if missing_vars:
        logger.error(f"MISSING STRIPE VARIABLES: {', '.join(missing_vars)}")
        logger.error("These variables are required for proper Stripe integration:")
        for var in missing_vars:
            logger.error(f"  - {var}")
    else:
        logger.info("✓ All Stripe environment variables are configured")

    logger.info("==================================")


# Call the logging function when module is imported
_log_stripe_config()
