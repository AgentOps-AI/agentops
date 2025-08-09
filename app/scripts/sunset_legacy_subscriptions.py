#!/usr/bin/env python3
"""
Script to sunset all legacy subscriptions by setting them to cancel at period end.
This should be run after updating the STRIPE_SUBSCRIPTION_PRICE_ID environment variable.

Usage:
    python scripts/sunset_legacy_subscriptions.py [--dry-run]
"""

import os
import sys
import stripe
import time
import argparse
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Sunset all legacy subscriptions')
    parser.add_argument(
        '--dry-run', action='store_true', help='Show what would be done without making changes'
    )
    parser.add_argument('--limit', type=int, default=100, help='Number of subscriptions to process per page')
    args = parser.parse_args()

    # Get environment variables
    stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
    current_price_id = os.getenv('STRIPE_SUBSCRIPTION_PRICE_ID')

    if not stripe_secret_key:
        logger.error("STRIPE_SECRET_KEY environment variable not set")
        sys.exit(1)

    if not current_price_id:
        logger.error("STRIPE_SUBSCRIPTION_PRICE_ID environment variable not set")
        sys.exit(1)

    stripe.api_key = stripe_secret_key

    logger.info(f"Current price ID: {current_price_id}")
    logger.info(f"Dry run: {args.dry_run}")

    sunset_count = 0
    already_cancelled_count = 0
    current_pricing_count = 0
    error_count = 0

    try:
        # Get all active subscriptions
        has_more = True
        starting_after = None

        while has_more:
            params = {
                'status': 'active',
                'limit': args.limit,
            }
            if starting_after:
                params['starting_after'] = starting_after

            subscriptions = stripe.Subscription.list(**params)

            for sub in subscriptions.data:
                try:
                    # Check if it's using the old price
                    is_legacy = True
                    legacy_price_id = None

                    for item in sub.get('items', {}).get('data', []):
                        price_id = item.get('price', {}).get('id')
                        if price_id == current_price_id:
                            is_legacy = False
                            break
                        else:
                            legacy_price_id = price_id

                    if not is_legacy:
                        current_pricing_count += 1
                        continue

                    if sub.get('cancel_at_period_end'):
                        already_cancelled_count += 1
                        logger.debug(f"Subscription {sub.id} already set to cancel")
                        continue

                    # Get customer info for logging
                    customer_email = 'unknown'
                    try:
                        customer = stripe.Customer.retrieve(sub.customer)
                        customer_email = customer.get('email', 'unknown')
                    except:
                        pass

                    if args.dry_run:
                        logger.info(
                            f"[DRY RUN] Would sunset subscription {sub.id} for customer {customer_email} (price: {legacy_price_id})"
                        )
                        sunset_count += 1  # Count what would be done in dry run
                    else:
                        # Cancel at period end
                        stripe.Subscription.modify(
                            sub.id,
                            cancel_at_period_end=True,
                            metadata={
                                'cancellation_reason': 'billing_model_change',
                                'notification_email_sent': 'pending',
                                'original_price_id': legacy_price_id or 'unknown',
                                'sunset_script_run': datetime.utcnow().isoformat(),
                            },
                        )
                        logger.info(f"✓ Sunset subscription {sub.id} for customer {customer_email}")
                        sunset_count += 1

                        # Rate limit to avoid hitting Stripe's API limits
                        time.sleep(0.1)

                except Exception as e:
                    error_count += 1
                    logger.error(f"✗ Error with subscription {sub.id}: {e}")

            # Check if there are more pages
            has_more = subscriptions.has_more
            if has_more and subscriptions.data:
                starting_after = subscriptions.data[-1].id

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

    # Summary
    logger.info("\n=== SUMMARY ===")
    if args.dry_run:
        logger.info(f"Would sunset: {sunset_count} subscriptions")
    else:
        logger.info(f"Total subscriptions sunset: {sunset_count}")
    logger.info(f"Already cancelled: {already_cancelled_count}")
    logger.info(f"Using current pricing: {current_pricing_count}")
    logger.info(f"Errors: {error_count}")

    if args.dry_run:
        logger.info("\nThis was a dry run. No changes were made.")
        logger.info(f"Run without --dry-run to sunset {sunset_count} legacy subscriptions.")


if __name__ == '__main__':
    main()
