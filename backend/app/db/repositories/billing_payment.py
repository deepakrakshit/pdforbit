from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.repositories.base import SQLAlchemyRepository
from app.models.billing_payment import BillingPayment


class BillingPaymentRepository(SQLAlchemyRepository[BillingPayment]):
    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=BillingPayment)

    def get_by_provider_order_id(self, provider_order_id: str) -> BillingPayment | None:
        statement = select(BillingPayment).where(BillingPayment.provider_order_id == provider_order_id).limit(1)
        return self.session.scalar(statement)

    def get_by_provider_payment_id(self, provider_payment_id: str) -> BillingPayment | None:
        statement = select(BillingPayment).where(BillingPayment.provider_payment_id == provider_payment_id).limit(1)
        return self.session.scalar(statement)

    def get_latest_by_provider_subscription_id(self, provider_subscription_id: str) -> BillingPayment | None:
        statement = (
            select(BillingPayment)
            .where(BillingPayment.provider_subscription_id == provider_subscription_id)
            .order_by(desc(BillingPayment.created_at))
            .limit(1)
        )
        return self.session.scalar(statement)