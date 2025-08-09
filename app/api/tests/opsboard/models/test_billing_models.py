import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from agentops.opsboard.models import BillingAuditLog, BillingPeriod, OrgModel

# Import shared billing fixtures
pytest_plugins = ["tests._conftest.billing"]
from tests._conftest.billing_constants import (
    TOKEN_COST_SAMPLE,
    SPAN_COST_SAMPLE,
    TOKEN_QUANTITY_SAMPLE,
    SPAN_QUANTITY_SAMPLE,
)


@pytest.fixture
def test_billing_period(orm_session, test_org, billing_period_factory):
    """Create a test billing period for testing."""
    billing_period = billing_period_factory(
        test_org.id,
        seat_cost=8000,  # $80 in cents
        seat_count=2,
        usage_costs={"tokens": TOKEN_COST_SAMPLE, "spans": SPAN_COST_SAMPLE},
        usage_quantities={"tokens": TOKEN_QUANTITY_SAMPLE, "spans": SPAN_QUANTITY_SAMPLE},
        total_cost=8200,
        status='pending',
    )
    orm_session.add(billing_period)
    orm_session.flush()
    return billing_period


@pytest.fixture
def test_billing_audit_log(orm_session, test_org, test_user):
    """Create a test billing audit log for testing."""
    try:
        audit_log = BillingAuditLog(
            org_id=test_org.id,
            user_id=test_user.id,
            action='member_licensed',
            details={
                'member_id': str(test_user.id),
                'member_email': 'test@example.com',
                'before_seat_count': 1,
                'after_seat_count': 2,
            },
        )
        orm_session.add(audit_log)
        orm_session.flush()
        return audit_log
    except Exception:
        orm_session.rollback()
        raise


@pytest.fixture(autouse=True)
def ensure_clean_session(orm_session):
    """Ensure clean session state before each test."""
    try:
        # Check if session has pending rollback
        if orm_session.in_transaction() and orm_session.is_active:
            if hasattr(orm_session, '_transaction') and orm_session._transaction.is_active:
                # Session is in a good state
                pass
        yield
    except Exception:
        orm_session.rollback()
        raise
    finally:
        # Cleanup after test
        try:
            if orm_session.in_transaction():
                orm_session.rollback()
        except Exception:
            pass


class TestBillingPeriod:
    """Test cases for BillingPeriod model."""

    def test_billing_period_creation(self, orm_session, test_org):
        """Test creating a new billing period."""
        period_start = datetime(2024, 2, 1, tzinfo=timezone.utc)
        period_end = datetime(2024, 2, 29, tzinfo=timezone.utc)

        billing_period = BillingPeriod(
            org_id=test_org.id,
            period_start=period_start,
            period_end=period_end,
            seat_cost=4000,
            seat_count=1,
            total_cost=4000,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        # Verify it was created
        assert billing_period.id is not None
        assert billing_period.org_id == test_org.id
        assert billing_period.period_start == period_start
        assert billing_period.period_end == period_end

    def test_billing_period_required_fields(self, orm_session, test_org, billing_period_factory):
        """Test billing period with all required fields."""
        billing_period = billing_period_factory(
            test_org.id,
            seat_cost=0,
            seat_count=0,
            total_cost=0,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        assert billing_period.id is not None

    def test_billing_period_default_values(self, orm_session, test_org, billing_period_factory):
        """Test billing period default field values."""
        billing_period = billing_period_factory(test_org.id)

        orm_session.add(billing_period)
        orm_session.commit()

        # Check defaults
        assert billing_period.seat_cost == 0
        assert billing_period.seat_count == 0
        assert billing_period.usage_costs == {}
        assert billing_period.usage_quantities == {}
        assert billing_period.total_cost == 0
        assert billing_period.status == 'pending'
        assert billing_period.stripe_invoice_id is None
        assert billing_period.invoiced_at is None
        assert billing_period.created_at is not None

    def test_billing_period_usage_costs_json_field(self, orm_session, test_org, billing_period_factory):
        """Test usage_costs JSONB field stores and retrieves data correctly."""
        usage_costs = {"tokens": 120, "spans": 45, "custom_metric": 25}

        billing_period = billing_period_factory(
            test_org.id,
            usage_costs=usage_costs,
            total_cost=190,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        # Retrieve and verify JSON data
        retrieved_period = orm_session.query(BillingPeriod).filter_by(id=billing_period.id).one()
        assert retrieved_period.usage_costs == usage_costs

    def test_billing_period_usage_quantities_json_field(self, orm_session, test_org, billing_period_factory):
        """Test usage_quantities JSONB field stores and retrieves data correctly."""
        usage_quantities = {"tokens": 6000000, "spans": 4500, "api_calls": 150}

        billing_period = billing_period_factory(
            test_org.id,
            usage_quantities=usage_quantities,
            total_cost=0,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        # Retrieve and verify JSON data
        retrieved_period = orm_session.query(BillingPeriod).filter_by(id=billing_period.id).one()
        assert retrieved_period.usage_quantities == usage_quantities

    def test_billing_period_seat_cost_calculation(self, orm_session, test_org, billing_period_factory):
        """Test seat_cost field stores cost in cents."""
        billing_period = billing_period_factory(
            test_org.id,
            seat_cost=15000,  # $150.00 in cents
            seat_count=3,
            total_cost=15000,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        assert billing_period.seat_cost == 15000
        assert billing_period.seat_count == 3

    def test_billing_period_total_cost_calculation(self, orm_session, test_org, billing_period_factory):
        """Test total_cost field calculation."""
        billing_period = billing_period_factory(
            test_org.id,
            seat_cost=8000,
            usage_costs={"tokens": 200, "spans": 75},
            total_cost=8275,  # 8000 + 200 + 75
        )

        orm_session.add(billing_period)
        orm_session.commit()

        assert billing_period.total_cost == 8275

    def test_billing_period_status_values(self, orm_session, test_org, billing_period_factory):
        """Test billing period status field accepts valid values."""
        valid_statuses = ['pending', 'invoiced', 'paid', 'failed']

        for status in valid_statuses:
            billing_period = billing_period_factory(
                test_org.id,
                status=status,
                total_cost=0,
            )

            orm_session.add(billing_period)
            orm_session.flush()

            assert billing_period.status == status

            orm_session.delete(billing_period)
            orm_session.flush()

    def test_billing_period_datetime_fields(self, orm_session, test_org, billing_period_factory):
        """Test datetime fields are properly handled."""
        now = datetime.now(timezone.utc)

        period_start = datetime(2024, 10, 15, tzinfo=timezone.utc)
        period_end = datetime(2024, 10, 16, tzinfo=timezone.utc)
        invoiced_at = datetime(2024, 11, 1, tzinfo=timezone.utc)

        billing_period = billing_period_factory(
            test_org.id,
            period_start=period_start,
            period_end=period_end,
            invoiced_at=invoiced_at,
            total_cost=0,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        assert billing_period.period_start == period_start
        assert billing_period.period_end == period_end
        assert billing_period.invoiced_at == invoiced_at

        # Just verify created_at was set automatically and is a reasonable timestamp
        assert billing_period.created_at is not None
        assert isinstance(billing_period.created_at, datetime)
        # Verify it's within the last hour (very generous range)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        one_hour_future = datetime.now(timezone.utc) + timedelta(hours=1)

        if billing_period.created_at.tzinfo is None:
            created_at_utc = billing_period.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at_utc = billing_period.created_at

        assert one_hour_ago <= created_at_utc <= one_hour_future

    def test_billing_period_foreign_key_relationship(self, orm_session, test_org, billing_period_factory):
        """Test billing period foreign key to organization."""
        billing_period = billing_period_factory(
            test_org.id,
            total_cost=0,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        # Verify foreign key relationship
        assert billing_period.org_id == test_org.id

    def test_billing_period_unique_constraint(self, orm_session, test_org, billing_period_factory):
        """Test unique constraint on org_id and period_start."""
        period_start = datetime(2024, 12, 15, tzinfo=timezone.utc)
        period_end = datetime(2024, 12, 16, tzinfo=timezone.utc)

        # Create first billing period
        billing_period1 = billing_period_factory(
            test_org.id, period_start=period_start, period_end=period_end, total_cost=0
        )
        orm_session.add(billing_period1)
        orm_session.commit()

        # Try to create second billing period with same org_id and period_start
        billing_period2 = BillingPeriod(
            org_id=test_org.id,
            period_start=period_start,  # Same period_start
            period_end=datetime(2025, 1, 1, tzinfo=timezone.utc),  # Different period_end
            total_cost=0,
        )
        orm_session.add(billing_period2)

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError):
            orm_session.commit()

        # Rollback the failed transaction to cleanup
        orm_session.rollback()

    def test_billing_period_query_by_org(
        self, orm_session, test_org, test_billing_period, billing_period_factory
    ):
        """Test querying billing periods by organization."""
        # Create another org to ensure we only get periods for the specific org
        other_org = OrgModel(name="Other Test Org")
        orm_session.add(other_org)
        orm_session.flush()

        other_period = billing_period_factory(
            other_org.id,
            total_cost=0,
        )
        orm_session.add(other_period)
        orm_session.commit()

        # Query periods for test_org only, filter by the specific fixture period
        periods = (
            orm_session.query(BillingPeriod)
            .filter(BillingPeriod.org_id == test_org.id, BillingPeriod.id == test_billing_period.id)
            .all()
        )

        assert len(periods) == 1
        assert periods[0].id == test_billing_period.id

    def test_billing_period_query_by_date_range(self, orm_session, test_org, billing_period_factory):
        """Test querying billing periods by date range."""
        # Create periods for different months with very specific dates
        jan_start = datetime(2025, 3, 15, tzinfo=timezone.utc)
        jan_end = datetime(2025, 3, 16, tzinfo=timezone.utc)

        feb_start = datetime(2025, 4, 15, tzinfo=timezone.utc)
        feb_end = datetime(2025, 4, 16, tzinfo=timezone.utc)

        jan_period = billing_period_factory(
            test_org.id, period_start=jan_start, period_end=jan_end, total_cost=0
        )

        feb_period = billing_period_factory(
            test_org.id, period_start=feb_start, period_end=feb_end, total_cost=0
        )

        orm_session.add_all([jan_period, feb_period])
        orm_session.commit()

        # Query periods ending before April 1st - should only get the March period
        cutoff_date = datetime(2025, 4, 1, tzinfo=timezone.utc)
        early_periods = (
            orm_session.query(BillingPeriod)
            .filter(
                BillingPeriod.org_id == test_org.id,
                BillingPeriod.period_end < cutoff_date,
                BillingPeriod.id.in_([jan_period.id, feb_period.id]),  # Only check our test records
            )
            .all()
        )

        assert len(early_periods) == 1
        assert early_periods[0].id == jan_period.id

    def test_billing_period_stripe_invoice_id_field(self, orm_session, test_org, billing_period_factory):
        """Test stripe_invoice_id field stores Stripe invoice reference."""
        stripe_invoice_id = "in_1234567890abcdef"

        billing_period = billing_period_factory(
            test_org.id,
            stripe_invoice_id=stripe_invoice_id,
            total_cost=0,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        assert billing_period.stripe_invoice_id == stripe_invoice_id

    def test_billing_period_invoiced_at_timestamp(self, orm_session, test_org, billing_period_factory):
        """Test invoiced_at timestamp field."""
        invoiced_at = datetime(2025, 6, 1, 12, 30, 45, tzinfo=timezone.utc)

        billing_period = billing_period_factory(
            test_org.id,
            invoiced_at=invoiced_at,
            status='invoiced',
            total_cost=0,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        assert billing_period.invoiced_at == invoiced_at

    def test_billing_period_auto_created_at(self, orm_session, test_org, billing_period_factory):
        """Test created_at field is automatically set."""
        before_creation = datetime.now(timezone.utc)

        billing_period = billing_period_factory(
            test_org.id,
            total_cost=0,
        )

        orm_session.add(billing_period)
        orm_session.commit()

        # Just verify created_at was set automatically and is a reasonable timestamp
        assert billing_period.created_at is not None
        assert isinstance(billing_period.created_at, datetime)
        # Verify it's within the last hour (very generous range)
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        one_hour_future = datetime.now(timezone.utc) + timedelta(hours=1)

        if billing_period.created_at.tzinfo is None:
            created_at_utc = billing_period.created_at.replace(tzinfo=timezone.utc)
        else:
            created_at_utc = billing_period.created_at

        assert one_hour_ago <= created_at_utc <= one_hour_future


class TestBillingAuditLog:
    """Test cases for BillingAuditLog model."""

    def test_billing_audit_log_creation(self, orm_session, test_org, test_user):
        """Test creating a new billing audit log entry."""
        # Ensure session is clean before test
        try:
            audit_log = BillingAuditLog(
                org_id=test_org.id,
                user_id=test_user.id,
                action='member_licensed',
                details={'member_id': str(test_user.id)},
            )

            orm_session.add(audit_log)
            orm_session.commit()

            assert audit_log.id is not None
            assert audit_log.org_id == test_org.id
            assert audit_log.user_id == test_user.id
        except Exception:
            # Rollback on any error to clean up session
            orm_session.rollback()
            raise

    def test_billing_audit_log_required_fields(self, orm_session, test_org, test_user):
        """Test billing audit log with all required fields."""
        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='seats_updated', details={}
        )

        orm_session.add(audit_log)
        orm_session.commit()

        assert audit_log.id is not None
        assert audit_log.action == 'seats_updated'
        assert audit_log.details == {}

    def test_billing_audit_log_auto_id_generation(self, orm_session, test_org, test_user):
        """Test audit log ID is automatically generated."""
        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='member_unlicensed', details={'test': 'data'}
        )

        # ID should be None before adding to session
        assert audit_log.id is None

        orm_session.add(audit_log)
        orm_session.commit()

        # ID should be generated after commit
        assert audit_log.id is not None
        assert isinstance(audit_log.id, uuid.UUID)

    def test_billing_audit_log_foreign_key_org(self, orm_session, test_org, test_user):
        """Test foreign key relationship to organization."""
        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='test_action', details={}
        )

        orm_session.add(audit_log)
        orm_session.commit()

        assert audit_log.org_id == test_org.id

    def test_billing_audit_log_foreign_key_user(self, orm_session, test_org, test_user):
        """Test foreign key relationship to user."""
        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='test_action', details={}
        )

        orm_session.add(audit_log)
        orm_session.commit()

        assert audit_log.user_id == test_user.id

    def test_billing_audit_log_action_field(self, orm_session, test_org, test_user):
        """Test action field stores different action types."""
        actions = [
            'member_licensed',
            'member_unlicensed',
            'seats_updated',
            'subscription_created',
            'subscription_cancelled',
        ]

        for action in actions:
            audit_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action=action, details={'action_type': action}
            )

            orm_session.add(audit_log)
            orm_session.flush()

            assert audit_log.action == action

            orm_session.delete(audit_log)
            orm_session.flush()

    def test_billing_audit_log_details_json_field(self, orm_session, test_org, test_user):
        """Test details JSON field stores complex data."""
        complex_details = {
            'member_id': str(test_user.id),
            'member_email': 'test@example.com',
            'before_seat_count': 2,
            'after_seat_count': 3,
            'changed_by': 'admin@example.com',
            'timestamp': '2024-01-01T12:00:00Z',
            'metadata': {'ip_address': '192.168.1.1', 'user_agent': 'Mozilla/5.0...'},
        }

        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='member_licensed', details=complex_details
        )

        orm_session.add(audit_log)
        orm_session.commit()

        # Retrieve and verify JSON data
        retrieved_log = orm_session.query(BillingAuditLog).filter_by(id=audit_log.id).one()
        assert retrieved_log.details == complex_details

    def test_billing_audit_log_auto_created_at(self, orm_session, test_org, test_user):
        """Test created_at field is automatically set."""
        try:
            before_creation = datetime.now(timezone.utc)

            audit_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action='test_action', details={}
            )

            orm_session.add(audit_log)
            orm_session.commit()

            # Just verify created_at was set automatically and is a reasonable timestamp
            assert audit_log.created_at is not None
            assert isinstance(audit_log.created_at, datetime)
            # Verify it's within the last hour (very generous range)
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            one_hour_future = datetime.now(timezone.utc) + timedelta(hours=1)

            if audit_log.created_at.tzinfo is None:
                created_at_utc = audit_log.created_at.replace(tzinfo=timezone.utc)
            else:
                created_at_utc = audit_log.created_at

            assert one_hour_ago <= created_at_utc <= one_hour_future
        except Exception:
            orm_session.rollback()
            raise

    def test_billing_audit_log_member_licensed_action(self, orm_session, test_org, test_user):
        """Test audit log for member licensed action."""
        details = {
            'member_id': str(test_user.id),
            'member_email': test_user.email,
            'new_seat_count': 2,
            'updated_by': 'admin@example.com',
        }

        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='member_licensed', details=details
        )

        orm_session.add(audit_log)
        orm_session.commit()

        assert audit_log.action == 'member_licensed'
        assert audit_log.details['member_id'] == str(test_user.id)

    def test_billing_audit_log_member_unlicensed_action(self, orm_session, test_org, test_user):
        """Test audit log for member unlicensed action."""
        details = {
            'member_id': str(test_user.id),
            'member_email': test_user.email,
            'new_seat_count': 1,
            'updated_by': 'admin@example.com',
        }

        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='member_unlicensed', details=details
        )

        orm_session.add(audit_log)
        orm_session.commit()

        assert audit_log.action == 'member_unlicensed'
        assert audit_log.details['new_seat_count'] == 1

    def test_billing_audit_log_seats_updated_action(self, orm_session, test_org, test_user):
        """Test audit log for seats updated action."""
        details = {
            'before_seat_count': 2,
            'after_seat_count': 5,
            'change_reason': 'bulk_member_addition',
            'updated_by': str(test_user.id),
        }

        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='seats_updated', details=details
        )

        orm_session.add(audit_log)
        orm_session.commit()

        assert audit_log.action == 'seats_updated'
        assert audit_log.details['before_seat_count'] == 2
        assert audit_log.details['after_seat_count'] == 5

    def test_billing_audit_log_query_by_org(self, orm_session, test_org, test_user, test_billing_audit_log):
        """Test querying audit logs by organization."""
        # Create another org to ensure we only get logs for the specific org
        other_org = OrgModel(name="Other Test Org")
        orm_session.add(other_org)
        orm_session.flush()

        other_log = BillingAuditLog(
            org_id=other_org.id, user_id=test_user.id, action='other_action', details={}
        )
        orm_session.add(other_log)
        orm_session.commit()

        # Query logs for test_org only
        logs = orm_session.query(BillingAuditLog).filter_by(org_id=test_org.id).all()

        assert len(logs) == 1
        assert logs[0].id == test_billing_audit_log.id

    def test_billing_audit_log_query_by_user(
        self, orm_session, test_org, test_user, test_user2, test_billing_audit_log
    ):
        """Test querying audit logs by user."""
        try:
            # Use test_user2 fixture instead of creating a new user

            other_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user2.id, action='other_action', details={}
            )
            orm_session.add(other_log)
            orm_session.commit()

            # Query logs for test_user only, specifically filter by our test fixture
            logs = (
                orm_session.query(BillingAuditLog)
                .filter(
                    BillingAuditLog.user_id == test_user.id, BillingAuditLog.id == test_billing_audit_log.id
                )
                .all()
            )

            assert len(logs) == 1
            assert logs[0].id == test_billing_audit_log.id
        except Exception:
            orm_session.rollback()
            raise

    def test_billing_audit_log_query_by_action(self, orm_session, test_org, test_user):
        """Test querying audit logs by action type."""
        try:
            # Create logs with different actions
            licensed_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action='member_licensed', details={}
            )

            unlicensed_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action='member_unlicensed', details={}
            )

            orm_session.add_all([licensed_log, unlicensed_log])
            orm_session.commit()

            # Query only licensed actions, filter by our specific test records
            licensed_logs = (
                orm_session.query(BillingAuditLog)
                .filter(
                    BillingAuditLog.action == 'member_licensed',
                    BillingAuditLog.org_id == test_org.id,
                    BillingAuditLog.id.in_([licensed_log.id, unlicensed_log.id]),
                )
                .all()
            )

            assert len(licensed_logs) == 1
            assert licensed_logs[0].id == licensed_log.id
        except Exception:
            orm_session.rollback()
            raise

    def test_billing_audit_log_query_by_date_range(self, orm_session, test_org, test_user):
        """Test querying audit logs by date range."""
        try:
            from datetime import timedelta
            from sqlalchemy import text

            # Create logs at different times
            old_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action='old_action', details={}
            )
            orm_session.add(old_log)
            orm_session.commit()

            # Manually set an older created_at time using proper SQLAlchemy text()
            old_time = datetime.now(timezone.utc) - timedelta(days=30)
            orm_session.execute(
                text("UPDATE billing_audit_logs SET created_at = :old_time WHERE id = :log_id"),
                {"old_time": old_time, "log_id": str(old_log.id)},
            )
            orm_session.commit()

            new_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action='new_action', details={}
            )
            orm_session.add(new_log)
            orm_session.commit()

            # Query logs from the last week, filter by our specific test records
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
            recent_logs = (
                orm_session.query(BillingAuditLog)
                .filter(
                    BillingAuditLog.created_at >= cutoff_date,
                    BillingAuditLog.org_id == test_org.id,
                    BillingAuditLog.id.in_([old_log.id, new_log.id]),
                )
                .all()
            )

            assert len(recent_logs) == 1
            assert recent_logs[0].id == new_log.id
        except Exception:
            orm_session.rollback()
            raise

    def test_billing_audit_log_details_before_after_structure(self, orm_session, test_org, test_user):
        """Test audit log details contain before/after values."""
        details = {
            'before': {'seat_count': 2, 'licensed_members': ['user1@example.com', 'user2@example.com']},
            'after': {
                'seat_count': 3,
                'licensed_members': ['user1@example.com', 'user2@example.com', 'user3@example.com'],
            },
            'changed_by': 'admin@example.com',
        }

        audit_log = BillingAuditLog(
            org_id=test_org.id, user_id=test_user.id, action='seats_updated', details=details
        )

        orm_session.add(audit_log)
        orm_session.commit()

        assert 'before' in audit_log.details
        assert 'after' in audit_log.details
        assert audit_log.details['before']['seat_count'] == 2
        assert audit_log.details['after']['seat_count'] == 3

    def test_billing_audit_log_multiple_entries_same_org(self, orm_session, test_org, test_user):
        """Test multiple audit log entries for same organization."""
        logs = []
        for i in range(5):
            log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action=f'action_{i}', details={'step': i}
            )
            logs.append(log)

        orm_session.add_all(logs)
        orm_session.commit()

        # Query all logs for the org
        org_logs = orm_session.query(BillingAuditLog).filter_by(org_id=test_org.id).all()

        assert len(org_logs) == 5
        for log in org_logs:
            assert log.org_id == test_org.id


class TestBillingModelIntegration:
    """Test cases for billing model integration scenarios."""

    def test_billing_period_with_audit_logs(self, orm_session, test_org, test_user, billing_period_factory):
        """Test billing period creation generates appropriate audit logs."""
        try:
            # Create billing period
            billing_period = billing_period_factory(
                test_org.id,
                seat_cost=8000,
                total_cost=8000,
            )
            orm_session.add(billing_period)
            orm_session.commit()

            # Create related audit log
            audit_log = BillingAuditLog(
                org_id=test_org.id,
                user_id=test_user.id,
                action='billing_period_created',
                details={
                    'period_id': str(billing_period.id),
                    'period_start': billing_period.period_start.isoformat(),
                    'total_cost': billing_period.total_cost,
                },
            )
            orm_session.add(audit_log)
            orm_session.commit()

            # Verify they're linked through org_id
            period_logs = orm_session.query(BillingAuditLog).filter_by(org_id=test_org.id).all()
            assert len(period_logs) == 1
            assert period_logs[0].details['period_id'] == str(billing_period.id)
        except Exception:
            orm_session.rollback()
            raise

    def test_billing_data_consistency(self, orm_session, test_org, test_user, billing_period_factory):
        """Test data consistency between billing period and audit logs."""
        try:
            # Create billing period
            billing_period = billing_period_factory(
                test_org.id,
                seat_count=3,
                seat_cost=12000,
                total_cost=12000,
            )
            orm_session.add(billing_period)
            orm_session.commit()

            # Create audit log with matching data
            audit_log = BillingAuditLog(
                org_id=test_org.id,
                user_id=test_user.id,
                action='billing_snapshot_created',
                details={
                    'period_id': str(billing_period.id),
                    'seat_count': billing_period.seat_count,
                    'seat_cost': billing_period.seat_cost,
                    'total_cost': billing_period.total_cost,
                },
            )
            orm_session.add(audit_log)
            orm_session.commit()

            # Verify data consistency
            assert audit_log.details['seat_count'] == billing_period.seat_count
            assert audit_log.details['seat_cost'] == billing_period.seat_cost
            assert audit_log.details['total_cost'] == billing_period.total_cost
        except Exception:
            orm_session.rollback()
            raise

    def test_billing_models_cascade_delete(self, orm_session, test_org, test_user, billing_period_factory):
        """Test that billing records prevent organization deletion (foreign key constraint)."""
        try:
            # Create billing period and audit log
            billing_period = billing_period_factory(
                test_org.id,
                total_cost=0,
            )

            audit_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action='test_action', details={}
            )

            orm_session.add_all([billing_period, audit_log])
            orm_session.commit()

            # Try to delete the organization - should fail due to foreign key constraint
            # This is the expected behavior for billing records (audit trail preservation)
            orm_session.delete(test_org)

            with pytest.raises(IntegrityError):
                orm_session.commit()

            # Rollback the failed transaction
            orm_session.rollback()

            # Verify billing records still exist
            remaining_periods = orm_session.query(BillingPeriod).filter_by(id=billing_period.id).all()
            remaining_logs = orm_session.query(BillingAuditLog).filter_by(id=audit_log.id).all()

            assert len(remaining_periods) == 1
            assert len(remaining_logs) == 1
        except Exception:
            orm_session.rollback()
            raise

    def test_billing_models_org_relationship_integrity(
        self, orm_session, test_org, test_user, billing_period_factory
    ):
        """Test referential integrity with organization model."""
        try:
            # Create billing records
            billing_period = billing_period_factory(
                test_org.id,
                total_cost=0,
            )

            audit_log = BillingAuditLog(
                org_id=test_org.id, user_id=test_user.id, action='test_action', details={}
            )

            orm_session.add_all([billing_period, audit_log])
            orm_session.commit()

            # Verify they reference the correct organization
            assert billing_period.org_id == test_org.id
            assert audit_log.org_id == test_org.id

            # Try to create billing record with non-existent org_id
            fake_org_id = uuid.uuid4()
            invalid_period = BillingPeriod(
                org_id=fake_org_id,
                period_start=datetime(2025, 12, 15, tzinfo=timezone.utc),
                period_end=datetime(2025, 12, 16, tzinfo=timezone.utc),
                total_cost=0,
            )

            orm_session.add(invalid_period)

            # Should raise IntegrityError due to foreign key constraint
            with pytest.raises(IntegrityError):
                orm_session.commit()

            # Rollback the failed transaction
            orm_session.rollback()
        except Exception:
            orm_session.rollback()
            raise
