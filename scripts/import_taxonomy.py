import os
import sys
import json
import re
import time
import uuid
from datetime import datetime
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.future import select

# Setup path for app imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.session import AsyncSessionLocal
from app.models.master.sector import Sector
from app.models.master.department import Department
from app.models.master.functional_domain import FunctionalDomain
from app.models.master.specialization import Specialization
from app.models.master.job_title import JobTitle
from app.models.master.master_data_import_log import MasterDataImportLog

# Helper functions
def generate_slug(text: str) -> str:
    """Generates a unique, lowercase, hyphen-separated slug."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def normalize_name(text: str) -> str:
    """Normalizes string for matching (remove *, replace - with spaces, title case)."""
    if not text:
        return ""
    text = text.replace('*', '')
    text = text.replace('-', ' ')
    return text.strip().title()

async def upsert_records(session: AsyncSession, model, records, index_elements):
    """
    Performs a PostgreSQL UPSERT with dynamic batching.
    
    Batching is required because asyncpg enforces a strict limit of 32,767 bind parameters 
    per query. When inserting thousands of rows, a single bulk insert easily exceeds this.
    """
    if not records:
        return 0, 0
        
    # SQLAlchemy will bind parameters for all mapped columns, not just the keys in the dictionary.
    column_count = len(model.__table__.columns)
    # Use 10000 instead of 30000 to give asyncpg massive headroom and avoid hidden overhead
    batch_size = max(1, 10000 // column_count)
    
    total_processed = 0
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        
        # Calculate diagnostics
        current_batch_size = len(batch)
        params = current_batch_size * column_count
        
        print(f"{model.__name__} records: {len(records)}")
        print(f"Columns: {column_count}")
        print(f"Batch size: {current_batch_size}")
        print(f"Total batches: {(len(records) + batch_size - 1) // batch_size}")
        print(f"Expected bind parameters: {params}")
        
        if params > 32000:
            raise ValueError(f"Parameters ({params}) exceed asyncpg limit of 32767!")
        
        stmt = insert(model).values(batch)
        
        # Exclude id and created_at from update
        update_dict = {c.name: c for c in stmt.excluded if c.name not in ['id', 'created_at']}
        
        # If the model has a slug and it is in excluded, avoid updating it to prevent overriding generated ones
        if 'slug' in update_dict:
            del update_dict['slug']
            
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=index_elements,
            set_=update_dict
        ).returning(model.id)
        
        await session.execute(upsert_stmt)
        total_processed += current_batch_size
        
    return total_processed, 0

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

async def run_import():
    start_time = time.time()
    print("Loading taxonomy...")
    
    db = AsyncSessionLocal()
    
    # Initialize Log
    import_log = MasterDataImportLog(
        started_at=datetime.utcnow(),
        status='IN_PROGRESS'
    )
    db.add(import_log)
    await db.commit()
    await db.refresh(import_log)
    
    # Ensure reports dir exists
    reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    stats = {
        'sectors': 0, 'departments': 0, 'functional_domains': 0, 
        'specializations': 0, 'job_titles': 0, 'errors': [], 'warnings': []
    }
    
    try:
        # Load Files
        base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'generated')
        
        sectors_data = load_json(os.path.join(base_dir, 'sectors.json'))
        departments_data = load_json(os.path.join(base_dir, 'departments.json'))
        fd_data = load_json(os.path.join(base_dir, 'functional_domains.json'))
        specs_data = load_json(os.path.join(base_dir, 'specializations.json'))
        titles_data = load_json(os.path.join(base_dir, 'job_titles.json'))

        # Mapping dictionaries (JSON ID -> Database UUID)
        sector_map = {}
        department_map = {}
        functional_domain_map = {}
        specialization_map = {}
        
        # 1. PROCESS SECTORS
        sectors = []
        temp_slug_to_json_id = {}
        seen_sector_slugs = set()
        
        for s_data in sectors_data:
            name = s_data.get('name', '')
            slug = generate_slug(name)
            
            if slug in seen_sector_slugs:
                continue
            seen_sector_slugs.add(slug)
            
            temp_slug_to_json_id[slug] = s_data.get('id')
            
            sectors.append({
                'id': s_data.get('id', uuid.uuid4()),
                'name': name,
                'slug': slug,
                'display_order': s_data.get('display_order', 0),
                'search_text': s_data.get('search_text', name)
            })
            
        await upsert_records(db, Sector, sectors, ['slug'])
        await db.commit()
        
        # Populate sector_map
        for s in (await db.execute(select(Sector))).scalars().all():
            json_id = temp_slug_to_json_id.get(s.slug)
            if json_id:
                sector_map[json_id] = s.id
            stats['sectors'] += 1
            
        # 2. PROCESS DEPARTMENTS
        departments = []
        temp_dept_key_to_json_id = {}
        seen_dept_keys = set()
        
        for d_data in departments_data:
            db_sector_id = sector_map.get(d_data.get('sector_id'))
            if not db_sector_id:
                continue
                
            name = d_data.get('name', '')
            dept_key = (db_sector_id, name)
            if dept_key in seen_dept_keys:
                continue
            seen_dept_keys.add(dept_key)
            
            temp_dept_key_to_json_id[dept_key] = d_data.get('id')
            
            departments.append({
                'id': d_data.get('id', uuid.uuid4()),
                'sector_id': db_sector_id,
                'name': name,
                'description': d_data.get('description')
            })
                
        await upsert_records(db, Department, departments, ['sector_id', 'name'])
        await db.commit()
        
        # Populate department_map
        for d in (await db.execute(select(Department))).scalars().all():
            json_id = temp_dept_key_to_json_id.get((d.sector_id, d.name))
            if json_id:
                department_map[json_id] = d.id
            stats['departments'] += 1

        # 3. PROCESS FUNCTIONAL DOMAINS
        functional_domains = []
        temp_fd_key_to_json_id = {}
        seen_fd_keys = set()
        
        for fd in fd_data:
            db_dept_id = department_map.get(fd.get('department_id'))
            if not db_dept_id:
                continue
                
            name = fd.get('name', '')
            fd_key = (db_dept_id, name)
            if fd_key in seen_fd_keys:
                continue
            seen_fd_keys.add(fd_key)
            
            temp_fd_key_to_json_id[fd_key] = fd.get('id')
            
            functional_domains.append({
                'id': fd.get('id', uuid.uuid4()),
                'department_id': db_dept_id,
                'name': name,
                'description': fd.get('description')
            })
                    
        await upsert_records(db, FunctionalDomain, functional_domains, ['department_id', 'name'])
        await db.commit()
        
        # Populate functional_domain_map
        for fd_obj in (await db.execute(select(FunctionalDomain))).scalars().all():
            json_id = temp_fd_key_to_json_id.get((fd_obj.department_id, fd_obj.name))
            if json_id:
                functional_domain_map[json_id] = fd_obj.id
            stats['functional_domains'] += 1

        # 4. PROCESS SPECIALIZATIONS
        specializations = []
        temp_spec_slug_to_json_id = {}
        temp_spec_json_id_to_slug = {} # needed for job titles
        seen_spec_slugs = set()
        
        for spec_data in specs_data:
            db_fd_id = functional_domain_map.get(spec_data.get('functional_domain_id'))
            if not db_fd_id:
                continue
                
            raw_name = spec_data.get('name', '')
            normalized_name = normalize_name(raw_name)
            slug = generate_slug(normalized_name)
            
            if slug in seen_spec_slugs:
                continue
            seen_spec_slugs.add(slug)
            
            temp_spec_slug_to_json_id[slug] = spec_data.get('id')
            temp_spec_json_id_to_slug[spec_data.get('id')] = slug
            
            specializations.append({
                'id': spec_data.get('id', uuid.uuid4()),
                'functional_domain_id': db_fd_id,
                'name': normalized_name,
                'slug': slug,
                'specialization_code': spec_data.get('specialization_code'),
                'display_name': spec_data.get('display_name'),
                'path': spec_data.get('path'),
                'onet': spec_data.get('onet'),
                'isco': spec_data.get('isco'),
                'esco': spec_data.get('esco'),
                'display_order': spec_data.get('display_order', 0),
                'search_text': spec_data.get('search_text', normalized_name)
            })
                        
        await upsert_records(db, Specialization, specializations, ['slug'])
        await db.commit()
        
        # Populate specialization_map
        for sp in (await db.execute(select(Specialization))).scalars().all():
            json_id = temp_spec_slug_to_json_id.get(sp.slug)
            if json_id:
                specialization_map[json_id] = sp.id
            stats['specializations'] += 1

        # 5. PROCESS JOB TITLES
        job_titles = []
        seen_jt_slugs = set()
        
        if isinstance(titles_data, dict) and "SECTORS" in titles_data:
            # Handle the old nested hierarchy format
            for sector in titles_data.get("SECTORS", []):
                for subsector in sector.get("subsectors", []):
                    for jf in subsector.get("jobFamilies", []):
                        for spec in jf.get("specs", []):
                            spec_name = spec.get("name", "")
                            spec_slug = generate_slug(normalize_name(spec_name))
                            
                            # Find the DB specialization ID using the slug
                            spec_json_id = temp_spec_slug_to_json_id.get(spec_slug)
                            db_spec_id = specialization_map.get(spec_json_id)
                            
                            if not db_spec_id:
                                continue
                                
                            for jt_name in spec.get("jobTitles", []):
                                slug = generate_slug(f"{spec_slug}-{jt_name}")
                                if slug in seen_jt_slugs:
                                    continue
                                seen_jt_slugs.add(slug)
                                
                                job_titles.append({
                                    'id': uuid.uuid4(),
                                    'specialization_id': db_spec_id,
                                    'job_title': jt_name,
                                    'slug': slug,
                                    'display_order': len(job_titles),
                                    'search_text': normalize_name(jt_name)
                                })
        else:
            # Handle the flat array format
            titles_path = os.path.join(base_dir, 'job_titles.json')
            print(f"absolute path: {titles_path}")
            print(f"current working directory: {os.getcwd()}")
            print(f"total JSON records loaded: {len(titles_data)}")
            print(f"JSON type: {type(titles_data)}")
            if titles_data:
                print(f"first record: {titles_data[0]}")
            
            matched_specs = 0
            missing_specs = 0
            mapped_count = 0
            
            for jt_data in titles_data:
                # NEW format: {"specialization_slug": "...", "job_titles": [...]}
                if "specialization_slug" in jt_data and "job_titles" in jt_data:
                    spec_slug = jt_data["specialization_slug"]
                    spec_json_id = temp_spec_slug_to_json_id.get(spec_slug)
                    db_spec_id = specialization_map.get(spec_json_id)
                    
                    if not db_spec_id:
                        print(f"Missing specialization:\n{spec_slug}")
                        missing_specs += 1
                        continue
                    
                    matched_specs += 1
                    
                    for jt_name in jt_data["job_titles"]:
                        slug = generate_slug(f"{spec_slug}-{jt_name}")
                        if slug in seen_jt_slugs:
                            continue
                        seen_jt_slugs.add(slug)
                        
                        job_titles.append({
                            'id': uuid.uuid4(),
                            'specialization_id': db_spec_id,
                            'job_title': jt_name,
                            'slug': slug,
                            'display_order': len(job_titles),
                            'search_text': normalize_name(jt_name)
                        })
                        
                        if mapped_count < 5:
                            print(f"Mapped:\n{spec_slug}\n-> {db_spec_id}\n{jt_name}\n{slug}\n")
                        mapped_count += 1
                else:
                    # LEGACY flat array format
                    db_spec_id = specialization_map.get(jt_data.get('specialization_id'))
                    if not db_spec_id:
                        continue
                        
                    jt_name = jt_data.get('job_title', jt_data.get('name', ''))
                    spec_slug = temp_spec_json_id_to_slug.get(jt_data.get('specialization_id'), '')
                    slug = generate_slug(f"{spec_slug}-{jt_name}")
                    
                    if slug in seen_jt_slugs:
                        continue
                    seen_jt_slugs.add(slug)
                    
                    job_titles.append({
                        'id': jt_data.get('id', uuid.uuid4()),
                        'specialization_id': db_spec_id,
                        'job_title': jt_name,
                        'slug': slug,
                        'display_order': jt_data.get('display_order', len(job_titles)),
                        'search_text': jt_data.get('search_text') or normalize_name(jt_name)
                    })
            
            print(f"Total JSON records: {len(titles_data)}")
            print(f"Matched specializations: {matched_specs}")
            print(f"Missing specializations: {missing_specs}")
            print(f"Prepared JobTitle rows: {len(job_titles)}")
            
        print(f"Job title rows prepared: {len(job_titles)}")
                            
        await upsert_records(db, JobTitle, job_titles, ['slug'])
        await db.commit()
        
        stats['job_titles'] = len((await db.execute(select(JobTitle))).scalars().all())

        # Update Log
        duration = time.time() - start_time
        import_log.completed_at = datetime.utcnow()
        import_log.duration = duration
        import_log.status = 'SUCCESS'
        import_log.total_records = sum(v for k, v in stats.items() if isinstance(v, int))
        await db.commit()
        
        # Save Report
        report_path = os.path.join(reports_dir, 'taxonomy_import_report.json')
        with open(report_path, 'w') as f:
            json.dump(stats, f, indent=4)
            
        print(f"\nImported Sectors: {stats['sectors']}")
        print(f"Imported Departments: {stats['departments']}")
        print(f"Imported Functional Domains: {stats['functional_domains']}")
        print(f"Imported Specializations: {stats['specializations']}")
        print(f"Imported Job Titles: {stats['job_titles']}\n")
        print(f"Duration: {duration:.2f} seconds")

    except Exception as e:
        await db.rollback()
        import_log.status = 'FAILED'
        import_log.completed_at = datetime.utcnow()
        import_log.error_summary = str(e)
        import_log.duration = time.time() - start_time
        await db.commit()
        print(f"Error during import: {e}")
        raise e
    finally:
        await db.close()

if __name__ == "__main__":
    asyncio.run(run_import())
