import uuid
from sqlalchemy import String, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import MasterBaseModel

class JobTitle(MasterBaseModel):
    __tablename__ = "job_titles"

    specialization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    search_text: Mapped[str | None] = mapped_column(String, nullable=True)

    specialization: Mapped["Specialization"] = relationship("Specialization", back_populates="job_titles")

    __table_args__ = (
        Index('ix_job_titles_job_title', 'job_title'),
        Index('ix_job_titles_search_text', 'search_text'),
    )
