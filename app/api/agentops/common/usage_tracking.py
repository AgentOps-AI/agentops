from enum import Enum


class UsageType(str, Enum):
    """Types of usage we track for billing"""

    TOKENS = "tokens"
    SPANS = "spans"
    # Future: STORAGE = "storage", COMPUTE = "compute", etc.
