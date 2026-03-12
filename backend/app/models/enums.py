from __future__ import annotations

from enum import Enum


class UserPlan(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class BillingPlanCode(str, Enum):
    PRO_MONTHLY = "PRO_MONTHLY"
    PRO_YEARLY = "PRO_YEARLY"


class SubscriptionInterval(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PaymentProvider(str, Enum):
    RAZORPAY = "razorpay"


class PaymentStatus(str, Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    CANCELLED = "cancelled"
    FAILED = "failed"
    REFUNDED = "refunded"


class UploadStatus(str, Enum):
    UPLOADED = "uploaded"
    IN_USE = "in_use"
    EXPIRED = "expired"
    DELETED = "deleted"
    QUARANTINED = "quarantined"


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class ArtifactKind(str, Enum):
    RESULT = "result"
    ARCHIVE = "archive"
    PREVIEW = "preview"

