import uuid
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import MasterBaseModel

class CareerPath(MasterBaseModel):
    __tablename__ = "career_paths"

    sector_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sectors.id", ondelete="RESTRICT"), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    functional_domain_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("functional_domains.id", ondelete="RESTRICT"), nullable=False)
    specialization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("specializations.id", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            'sector_id', 'department_id', 'functional_domain_id', 'specialization_id',
            name='uq_career_path_composite'
        ),
    )
