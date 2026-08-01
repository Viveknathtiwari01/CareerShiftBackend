from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from typing import List, Optional
import uuid

from app.database.session import get_db
from app.models.master.sector import Sector
from app.models.master.department import Department
from app.models.master.functional_domain import FunctionalDomain
from app.models.master.specialization import Specialization
from app.models.master.job_title import JobTitle
from app.schemas.master import (
    SectorResponse,
    DepartmentResponse,
    FunctionalDomainResponse,
    SpecializationResponse,
    JobTitleResponse
)

router = APIRouter()

@router.get("/sectors", response_model=List[SectorResponse])
async def get_sectors(
    q: Optional[str] = Query(None, description="Search term"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Sector)
    if q:
        stmt = stmt.filter(Sector.search_text.ilike(f"%{q}%"))
    stmt = stmt.order_by(Sector.display_order.asc(), Sector.name.asc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/sectors/{sector_id}/departments", response_model=List[DepartmentResponse])
async def get_departments(
    sector_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Department).filter(Department.sector_id == sector_id)
    stmt = stmt.order_by(Department.name.asc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/departments/{department_id}/functional-domains", response_model=List[FunctionalDomainResponse])
async def get_functional_domains(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(FunctionalDomain).filter(FunctionalDomain.department_id == department_id)
    stmt = stmt.order_by(FunctionalDomain.name.asc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/functional-domains/{functional_domain_id}/specializations", response_model=List[SpecializationResponse])
async def get_specializations(
    functional_domain_id: uuid.UUID,
    q: Optional[str] = Query(None, description="Search term"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Specialization).filter(Specialization.functional_domain_id == functional_domain_id)
    if q:
        stmt = stmt.filter(Specialization.search_text.ilike(f"%{q}%"))
    stmt = stmt.order_by(Specialization.display_order.asc(), Specialization.name.asc())
    
    result = await db.execute(stmt)
    return result.scalars().all()

@router.get("/specializations/{specialization_id}/job-titles", response_model=List[JobTitleResponse])
async def get_job_titles(
    specialization_id: uuid.UUID,
    q: Optional[str] = Query(None, description="Search term"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(JobTitle).filter(JobTitle.specialization_id == specialization_id)
    if q:
        stmt = stmt.filter(JobTitle.search_text.ilike(f"%{q}%"))
    stmt = stmt.order_by(JobTitle.display_order.asc(), JobTitle.job_title.asc())
    
    result = await db.execute(stmt)
    return result.scalars().all()
