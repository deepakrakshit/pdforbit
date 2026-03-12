from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db.repositories.billing_payment import BillingPaymentRepository
from app.db.repositories.user import UserRepository
from app.models.enums import BillingPlanCode, PaymentStatus, SubscriptionInterval, SubscriptionStatus, UserPlan
from tests.support.integration import authenticate_user, create_migrated_client


INTERNAL_SECRET = "billing-internal-secret-with-32-plus-chars"


@pytest.fixture()
def billing_client(tmp_path: Path, backend_root: Path) -> TestClient:
    return create_migrated_client(
        tmp_path=tmp_path,
        backend_root=backend_root,
        database_name="billing.sqlite3",
        storage_name="storage",
        access_secret="billing-access-secret-with-32-plus-chars",
        refresh_secret="billing-refresh-secret-with-32-plus-chars",
        settings_overrides={
            "BILLING_INTERNAL_API_SECRET": INTERNAL_SECRET,
        },
    )


def _internal_headers() -> dict[str, str]:
    return {"X-Internal-API-Secret": INTERNAL_SECRET}


def test_internal_activation_upgrades_user_and_records_payment(billing_client: TestClient) -> None:
    user_headers = authenticate_user(billing_client, email="billing1@pdforbit.test")
    me_response = billing_client.get("/api/v1/users/me", headers=user_headers)
    assert me_response.status_code == 200
    user_body = me_response.json()

    order_response = billing_client.post(
        "/api/v1/billing/internal/order-created",
        json={
            "user_id": user_body["id"],
            "plan_code": "PRO_MONTHLY",
            "razorpay_order_id": "order_test_pdforbit_monthly_001",
            "receipt": "rcpt_pdforbit_monthly_001",
            "amount_paise": 50000,
            "currency": "INR",
        },
        headers=_internal_headers(),
    )

    assert order_response.status_code == 201
    assert order_response.json()["status"] == PaymentStatus.CREATED.value

    activation_response = billing_client.post(
        "/api/v1/billing/internal/activate",
        json={
            "user_id": user_body["id"],
            "plan_code": "PRO_MONTHLY",
            "razorpay_order_id": "order_test_pdforbit_monthly_001",
            "razorpay_payment_id": "pay_test_pdforbit_monthly_001",
            "amount_paise": 50000,
            "currency": "INR",
            "status": "captured",
            "signature_verified": True,
            "provider_subscription_id": "sub_test_pdforbit_monthly_001",
            "paid_at": "2026-03-11T16:30:00Z",
            "raw_payload": {"source": "integration-test"},
        },
        headers=_internal_headers(),
    )

    assert activation_response.status_code == 200
    activation_body = activation_response.json()
    assert activation_body["plan_type"] == UserPlan.PRO.value
    assert activation_body["credits_remaining"] == 1000
    assert activation_body["credit_limit"] == 1000
    assert activation_body["subscription_status"] == SubscriptionStatus.ACTIVE.value
    assert activation_body["subscription_interval"] == SubscriptionInterval.MONTHLY.value
    assert activation_body["subscription_expires_at"] is not None

    refreshed_me = billing_client.get("/api/v1/users/me", headers=user_headers)
    assert refreshed_me.status_code == 200
    assert refreshed_me.json()["plan_type"] == UserPlan.PRO.value
    assert refreshed_me.json()["subscription_status"] == SubscriptionStatus.ACTIVE.value

    container = billing_client.app.state.container
    with container.database_manager.session_scope() as session:
        payment = BillingPaymentRepository(session).get_by_provider_payment_id("pay_test_pdforbit_monthly_001")
        assert payment is not None
        assert payment.plan_code == BillingPlanCode.PRO_MONTHLY
        assert payment.status == PaymentStatus.CAPTURED
        assert payment.signature_verified is True


def test_expired_pro_subscription_downgrades_on_profile_fetch(billing_client: TestClient) -> None:
    user_headers = authenticate_user(billing_client, email="billing2@pdforbit.test")
    container = billing_client.app.state.container

    with container.database_manager.session_scope() as session:
        user = UserRepository(session).get_by_email("billing2@pdforbit.test")
        assert user is not None
        user.plan = UserPlan.PRO
        user.subscription_status = SubscriptionStatus.ACTIVE
        user.subscription_interval = SubscriptionInterval.MONTHLY
        user.subscription_started_at = datetime.now(timezone.utc) - timedelta(days=40)
        user.subscription_expires_at = datetime.now(timezone.utc) - timedelta(days=2)
        user.credits_remaining = 900
        session.add(user)

    me_response = billing_client.get("/api/v1/users/me", headers=user_headers)
    assert me_response.status_code == 200
    me_body = me_response.json()
    assert me_body["plan_type"] == UserPlan.FREE.value
    assert me_body["subscription_status"] == SubscriptionStatus.EXPIRED.value
    assert me_body["subscription_interval"] is None
    assert me_body["credits_remaining"] == 30
    assert me_body["credit_limit"] == 30


def test_subscription_cancelled_webhook_downgrades_user(billing_client: TestClient) -> None:
    user_headers = authenticate_user(billing_client, email="billing3@pdforbit.test")
    user_body = billing_client.get("/api/v1/users/me", headers=user_headers).json()

    billing_client.post(
        "/api/v1/billing/internal/order-created",
        json={
            "user_id": user_body["id"],
            "plan_code": "PRO_YEARLY",
            "razorpay_order_id": "order_test_pdforbit_yearly_001",
            "receipt": "rcpt_pdforbit_yearly_001",
            "amount_paise": 240000,
            "currency": "INR",
        },
        headers=_internal_headers(),
    )

    activation_response = billing_client.post(
        "/api/v1/billing/internal/activate",
        json={
            "user_id": user_body["id"],
            "plan_code": "PRO_YEARLY",
            "razorpay_order_id": "order_test_pdforbit_yearly_001",
            "razorpay_payment_id": "pay_test_pdforbit_yearly_001",
            "amount_paise": 240000,
            "currency": "INR",
            "status": "captured",
            "signature_verified": True,
            "provider_subscription_id": "sub_test_pdforbit_yearly_001",
            "paid_at": "2026-03-11T16:30:00Z",
            "raw_payload": {"source": "integration-test"},
        },
        headers=_internal_headers(),
    )
    assert activation_response.status_code == 200

    webhook_response = billing_client.post(
        "/api/v1/billing/internal/webhook",
        json={
            "event": "subscription.cancelled",
            "payload": {
                "payload": {
                    "subscription": {
                        "entity": {
                            "id": "sub_test_pdforbit_yearly_001",
                            "notes": {
                                "user_id": user_body["id"],
                                "plan_code": "PRO_YEARLY",
                            },
                        }
                    }
                }
            },
        },
        headers=_internal_headers(),
    )

    assert webhook_response.status_code == 200
    webhook_body = webhook_response.json()
    assert webhook_body["plan_type"] == UserPlan.FREE.value
    assert webhook_body["subscription_status"] == SubscriptionStatus.CANCELLED.value
    assert webhook_body["subscription_interval"] is None
    assert webhook_body["credit_limit"] == 30
