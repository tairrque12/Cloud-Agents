# db/models.py
# Inkbook — SQLAlchemy ORM Models
# Maps Python classes to database tables
# Last updated: April 30, 2026

import uuid
from datetime import datetime, date, time
from sqlalchemy import (
    String, Boolean, Integer, Numeric,
    DateTime, Date, Time, Text,
    ForeignKey, ARRAY, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


# ─────────────────────────────────────────
# ARTISTS
# ─────────────────────────────────────────

class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    instagram_handle: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(50))
    studio_name: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[str] = mapped_column(String(20), default="active")
    plan: Mapped[str] = mapped_column(String(20), default="starter")
    is_founding_artist: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(50))
    telegram_bot_token: Mapped[str | None] = mapped_column(String(200))
    referral_code: Mapped[str | None] = mapped_column(String(20), unique=True)
    affiliate_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    affiliate_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=20.00)
    booking_min_days: Mapped[int] = mapped_column(Integer, default=14)
    booking_max_days: Mapped[int] = mapped_column(Integer, default=60)
    onboarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Relationships
    intakes: Mapped[list["Intake"]] = relationship(back_populates="artist")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="artist")


# ─────────────────────────────────────────
# CLIENTS
# ─────────────────────────────────────────

class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    name: Mapped[str] = mapped_column(String(100))
    contact: Mapped[str] = mapped_column(String(255), unique=True)
    contact_type: Mapped[str] = mapped_column(String(10), default="phone")
    total_intakes: Mapped[int] = mapped_column(Integer, default=0)
    total_bookings: Mapped[int] = mapped_column(Integer, default=0)
    total_spent: Mapped[float] = mapped_column(Numeric(10, 2), default=0.00)
    last_intake_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_booking_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Relationships
    intakes: Mapped[list["Intake"]] = relationship(back_populates="client")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="client")


# ─────────────────────────────────────────
# INTAKES
# ─────────────────────────────────────────

class Intake(Base):
    __tablename__ = "intakes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    short_id: Mapped[str] = mapped_column(String(10), unique=True)
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artists.id")
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id")
    )
    classification: Mapped[str] = mapped_column(String(10))
    confidence_level: Mapped[str | None] = mapped_column(String(10))
    flags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    size_selection: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    placement: Mapped[str | None] = mapped_column(String(100))
    styles: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    is_cover_up: Mapped[bool] = mapped_column(Boolean, default=False)
    cover_up_description: Mapped[str | None] = mapped_column(Text)
    budget_range: Mapped[str | None] = mapped_column(String(20))
    preferred_timing: Mapped[str | None] = mapped_column(String(20))
    idea_readiness: Mapped[str | None] = mapped_column(String(20))
    reference_image_url: Mapped[str | None] = mapped_column(Text)
    guided_meaning: Mapped[str | None] = mapped_column(Text)
    guided_imagery: Mapped[str | None] = mapped_column(Text)
    guided_style_notes: Mapped[str | None] = mapped_column(Text)
    raw_crew_output: Mapped[str | None] = mapped_column(Text)
    emotional_tone_note: Mapped[str | None] = mapped_column(Text)
    selected_date: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # Relationships
    artist: Mapped["Artist"] = relationship(back_populates="intakes")
    client: Mapped["Client"] = relationship(back_populates="intakes")
    estimate: Mapped["Estimate | None"] = relationship(
        back_populates="intake"
    )
    schedule: Mapped["Schedule | None"] = relationship(
        back_populates="intake"
    )
    approval: Mapped["Approval | None"] = relationship(
        back_populates="intake"
    )
    booking: Mapped["Booking | None"] = relationship(
        back_populates="intake"
    )


# ─────────────────────────────────────────
# ESTIMATES
# ─────────────────────────────────────────

class Estimate(Base):
    __tablename__ = "estimates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    intake_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intakes.id")
    )
    session_type: Mapped[str] = mapped_column(String(20))
    session_type_confidence: Mapped[str | None] = mapped_column(String(10))
    price_min: Mapped[float] = mapped_column(Numeric(10, 2))
    price_max: Mapped[float] = mapped_column(Numeric(10, 2))
    deposit_amount: Mapped[float] = mapped_column(Numeric(10, 2))
    duration_estimate: Mapped[str | None] = mapped_column(String(50))
    personalized_note: Mapped[str | None] = mapped_column(Text)
    disclaimer_included: Mapped[bool] = mapped_column(Boolean, default=True)
    pricing_flags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    is_cover_up_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    cover_up_note: Mapped[str | None] = mapped_column(Text)

    # Relationship
    intake: Mapped["Intake"] = relationship(back_populates="estimate")


# ─────────────────────────────────────────
# SCHEDULES
# ─────────────────────────────────────────

class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    intake_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intakes.id")
    )
    offered_dates: Mapped[list[date]] = mapped_column(ARRAY(Date))
    day_capacity_rule: Mapped[str | None] = mapped_column(String(20))
    capacity_flag: Mapped[str | None] = mapped_column(Text)
    calendar_source: Mapped[str] = mapped_column(
        String(30),
        default="manual"
    )
    selected_date: Mapped[date | None] = mapped_column(Date)
    confirmed_time: Mapped[time | None] = mapped_column(Time)

    # Relationship
    intake: Mapped["Intake"] = relationship(back_populates="schedule")


# ─────────────────────────────────────────
# APPROVALS
# ─────────────────────────────────────────

class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    intake_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intakes.id")
    )
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artists.id")
    )
    decision: Mapped[str] = mapped_column(String(10))
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    adjusted_price: Mapped[str | None] = mapped_column(String(50))
    adjusted_dates: Mapped[str | None] = mapped_column(Text)
    adjusted_message: Mapped[str | None] = mapped_column(Text)
    client_message_sent: Mapped[str | None] = mapped_column(Text)
    message_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    notification_channel: Mapped[str] = mapped_column(
        String(20),
        default="sms"
    )

    # Relationship
    intake: Mapped["Intake"] = relationship(back_populates="approval")


# ─────────────────────────────────────────
# BOOKINGS
# ─────────────────────────────────────────

class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    intake_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("intakes.id")
    )
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artists.id")
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clients.id")
    )
    approval_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("approvals.id")
    )
    appointment_date: Mapped[date] = mapped_column(Date)
    appointment_time: Mapped[time | None] = mapped_column(Time)
    session_type: Mapped[str] = mapped_column(String(20))
    duration_estimate: Mapped[str | None] = mapped_column(String(50))
    quoted_price_min: Mapped[float | None] = mapped_column(Numeric(10, 2))
    quoted_price_max: Mapped[float | None] = mapped_column(Numeric(10, 2))
    final_price: Mapped[float | None] = mapped_column(Numeric(10, 2))
    deposit_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    deposit_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    deposit_paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    stripe_payment_id: Mapped[str | None] = mapped_column(String(200))
    deposit_link: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        default="deposit_pending"
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    final_price_charged: Mapped[float | None] = mapped_column(Numeric(10, 2))
    artist_notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    artist: Mapped["Artist"] = relationship(back_populates="bookings")
    client: Mapped["Client"] = relationship(back_populates="bookings")
    intake: Mapped["Intake"] = relationship(back_populates="booking")


class BetaApplication(Base):
    __tablename__ = "beta_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    name: Mapped[str] = mapped_column(String(100))
    instagram: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )