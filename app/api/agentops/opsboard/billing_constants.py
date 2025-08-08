from enum import Enum


class BillingConstants:
    GRACE_PERIOD_DAYS = 3
    RACE_CONDITION_WINDOW_SECONDS = 5
    DEFAULT_SEAT_PRICE_CENTS = 4000


class BillingAuditAction(str, Enum):
    MEMBER_LICENSED = "member_licensed"
    MEMBER_UNLICENSED = "member_unlicensed"
    LICENSES_SYNCED_BY_WEBHOOK = "licenses_synced_by_webhook"
    SUBSCRIPTION_CREATED = "subscription_created"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
