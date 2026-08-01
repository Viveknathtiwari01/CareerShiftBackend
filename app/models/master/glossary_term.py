from sqlalchemy import String, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import MasterBaseModel

class GlossaryTerm(MasterBaseModel):
    __tablename__ = "glossary_terms"

    term: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    search_text: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index('ix_glossary_terms_term', 'term'),
        Index('ix_glossary_terms_search_text', 'search_text'),
    )
