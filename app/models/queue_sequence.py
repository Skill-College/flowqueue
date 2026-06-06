"""QueueSequence model — per-queue monotonic counter for message.sequence_num.

Incremented under SELECT ... FOR UPDATE inside the publish transaction so each
queue gets a gapless, ordered sequence independent of other queues.
"""

import uuid

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class QueueSequence(Base):
    __tablename__ = "queue_sequences"

    queue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("queues.id", ondelete="CASCADE"),
        primary_key=True,
    )
    last_value: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
