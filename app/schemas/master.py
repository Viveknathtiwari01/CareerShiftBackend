from pydantic import BaseModel, UUID4, ConfigDict
from typing import Optional

class MasterBase(BaseModel):
    id: UUID4

    model_config = ConfigDict(from_attributes=True)

class SectorResponse(MasterBase):
    name: str
    slug: str

class DepartmentResponse(MasterBase):
    name: str
    sector_id: UUID4
    description: Optional[str] = None

class FunctionalDomainResponse(MasterBase):
    name: str
    department_id: UUID4
    description: Optional[str] = None

class SpecializationResponse(MasterBase):
    name: str
    slug: str
    functional_domain_id: UUID4
    display_name: Optional[str] = None

class JobTitleResponse(MasterBase):
    job_title: str
    slug: str
    specialization_id: UUID4
