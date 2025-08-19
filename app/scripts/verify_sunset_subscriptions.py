#!/usr/bin/env python3
"""
Simple script to verify which subscriptions will be caught by the invoice webhook check.
This shows which subscriptions have both cancel_at_period_end=True and cancellation_reason='billing_model_change'.
"""

import os
import sys
import stripe
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    # Get environment variables
    stripe_secret_key = os.getenv('STRIPE_SECRET_KEY')
    if not stripe_secret_key:
        logger.error("STRIPE_SECRET_KEY environment variable not set")
        sys.exit(1)

    stripe.api_key = stripe_secret_key

    logger.info("Checking for sunset legacy subscriptions...")

    # Counters
    total_active = 0
    sunset_legacy = 0
    cancelling_other_reason = 0
    not_cancelling = 0

    sunset_subscriptions = []

    try:
        # Get all active subscriptions
        has_more = True
        starting_after = None

        while has_more:
            params = {
                'status': 'active',
                'limit': 100,
            }
            if starting_after:
                params['starting_after'] = starting_after

            subscriptions = stripe.Subscription.list(**params)

            for sub in subscriptions.data:
                total_active += 1

                cancel_at_period_end = sub.get('cancel_at_period_end', False)
                cancellation_reason = sub.get('metadata', {}).get('cancellation_reason')

                # This is the exact check from the webhook handler
                if cancel_at_period_end and cancellation_reason == 'billing_model_change':
                    sunset_legacy += 1

                    # Get customer email for display
                    customer_email = 'unknown'
                    try:
                        customer = stripe.Customer.retrieve(sub.get('customer'))
                        customer_email = customer.get('email', 'unknown')
                    except:
                        pass

                    # Calculate days until cancellation
                    current_period_end_ts = sub.get('current_period_end')
                    if current_period_end_ts:
                        current_period_end = datetime.fromtimestamp(current_period_end_ts)
                        days_until_cancel = (current_period_end - datetime.now()).days
                        cancel_date = current_period_end.strftime('%Y-%m-%d')
                    else:
                        days_until_cancel = -1
                        cancel_date = 'Unknown'

                    sunset_subscriptions.append(
                        {
                            'id': sub.get('id'),
                            'customer': customer_email,
                            'days_until_cancel': days_until_cancel,
                            'cancel_date': cancel_date,
                        }
                    )

                elif cancel_at_period_end:
                    cancelling_other_reason += 1
                else:
                    not_cancelling += 1

            # Check if there are more pages
            has_more = subscriptions.has_more
            if has_more and subscriptions.data:
                starting_after = subscriptions.data[-1].get('id')

    except Exception as e:
        logger.error(f"Error fetching subscriptions: {e}")
        sys.exit(1)

    # Display results
    logger.info("\n=== VERIFICATION RESULTS ===")
    logger.info(f"Total active subscriptions: {total_active}")
    logger.info(f"Sunset legacy (will skip usage charges): {sunset_legacy}")
    logger.info(f"Cancelling for other reasons: {cancelling_other_reason}")
    logger.info(f"Not cancelling: {not_cancelling}")

    if sunset_subscriptions:
        logger.info("\n=== SUNSET SUBSCRIPTIONS (Usage charges will be skipped) ===")
        for sub in sorted(sunset_subscriptions, key=lambda x: x['days_until_cancel']):
            logger.info(
                f"- {sub['id']} | {sub['customer']} | Cancels in {sub['days_until_cancel']} days ({sub['cancel_date']})"
            )

    logger.info("\n✅ These subscriptions will NOT receive usage charges on their final invoice.")


if __name__ == '__main__':
    main()
