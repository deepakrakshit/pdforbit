from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


JSONVariant = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def enum_type(enum_cls: type, name: str) -> sa.Enum:
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        validate_strings=True,
        create_constraint=True,
        values_callable=lambda members: [member.value for member in members],
    )
