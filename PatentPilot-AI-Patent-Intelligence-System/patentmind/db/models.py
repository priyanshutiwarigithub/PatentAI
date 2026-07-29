import datetime
from typing import Optional, Any
from sqlalchemy import (
    String, Text, DateTime, ForeignKey, Integer, JSON
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

# Helper to use JSONB for Postgres and fallback to standard JSON
JSONType = JSONB().with_variant(JSON(), "sqlite")

class Patent(Base):
    __tablename__ = "patents"

    patent_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patent_number: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claims: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    inventors: Mapped[Optional[Any]] = mapped_column(JSONType, nullable=True)
    assignee: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    filing_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    publication_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cpc_codes: Mapped[Optional[Any]] = mapped_column(JSONType, nullable=True)
    ipc_codes: Mapped[Optional[Any]] = mapped_column(JSONType, nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    s3_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_repository: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    domain_tags: Mapped[Optional[Any]] = mapped_column(JSONType, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="ingested", nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    logs: Mapped[list["ProcessingLog"]] = relationship("ProcessingLog", back_populates="patent")
    embeddings: Mapped[list["EmbeddingsMeta"]] = relationship("EmbeddingsMeta", back_populates="patent")


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("patents.patent_id", ondelete="CASCADE"), nullable=True)
    stage: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    patent: Mapped[Optional["Patent"]] = relationship("Patent", back_populates="logs")


class EmbeddingsMeta(Base):
    __tablename__ = "embeddings_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patent_id: Mapped[int] = mapped_column(Integer, ForeignKey("patents.patent_id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    section_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    claim_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    vector_db_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    patent: Mapped["Patent"] = relationship("Patent", back_populates="embeddings")
