import os
import sys
import json
import re
import time
import uuid
from datetime import datetime
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.future import select

# Setup path for app imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.session import AsyncSessionLocal
from app.models.master.sector import Sector
from app.models.master.subsector import Subsector
from app.models.master.job_family import JobFamily
from app.models.master.specialization import Specialization
from app.models.master.job_title import JobTitle
from app.models.master.skill import Skill
from app.models.master.glossary_term import GlossaryTerm
from app.models.master.career_path import CareerPath
from app.models.master.master_data_version import MasterDataVersion
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
    Performs a PostgreSQL UPSERT.
    """
    if not records:
        return 0, 0
        
    stmt = insert(model).values(records)
    
    # Exclude id and created_at from update
    update_dict = {c.name: c for c in stmt.excluded if c.name not in ['id', 'created_at', 'slug']}
    
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=index_elements,
        set_=update_dict
    ).returning(model.id)
    
    await session.execute(upsert_stmt)
    return len(records), 0

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
        'sectors': 0, 'subsectors': 0, 'job_families': 0, 
        'specializations': 0, 'job_titles': 0, 'skills': 0, 
        'glossary_terms': 0, 'errors': [], 'warnings': []
    }
    
    try:
        # Load Files
        taxonomy_path = os.path.join(os.path.dirname(__file__), '..', '..', 'workforce-skills-taxonomy.json')
        job_titles_path = os.path.join(os.path.dirname(__file__), '..', '..', 'master_job_titles.json')
        
        taxonomy_data = load_json(taxonomy_path)
        job_titles_data = load_json(job_titles_path)

        # Build dictionaries for fast lookups
        specialization_map = {} # slug -> id
        job_family_map = {}
        subsector_map = {}
        sector_map = {}
        
        # 1. PROCESS SECTORS
        sectors = []
        for i, s_data in enumerate(taxonomy_data.get('SECTORS', [])):
            name = s_data['name']
            slug = generate_slug(name)
            sectors.append({
                'id': uuid.uuid4(),
                'name': name,
                'slug': slug,
                'isco_code': s_data.get('isco'),
                'display_order': i,
                'search_text': name
            })
            
        await upsert_records(db, Sector, sectors, ['slug'])
        await db.commit()
        
        # Refresh maps
        result = await db.execute(select(Sector))
        all_sectors = result.scalars().all()
        for s in all_sectors:
            sector_map[s.slug] = s.id
            stats['sectors'] += 1
            
        # 2. PROCESS SUBSECTORS
        subsectors = []
        for s_data in taxonomy_data.get('SECTORS', []):
            sector_slug = generate_slug(s_data['name'])
            sector_id = sector_map.get(sector_slug)
            
            for i, sub_data in enumerate(s_data.get('subsectors', [])):
                name = sub_data['name']
                slug = generate_slug(f"{sector_slug}-{name}")
                subsectors.append({
                    'id': uuid.uuid4(),
                    'sector_id': sector_id,
                    'name': name,
                    'slug': slug,
                    'display_order': i,
                    'search_text': name
                })
                
        await upsert_records(db, Subsector, subsectors, ['slug'])
        await db.commit()
        
        result = await db.execute(select(Subsector))
        all_subsectors = result.scalars().all()
        for sub in all_subsectors:
            subsector_map[sub.slug] = sub.id
            stats['subsectors'] += 1

        # 3. PROCESS JOB FAMILIES
        job_families = []
        for s_data in taxonomy_data.get('SECTORS', []):
            sector_slug = generate_slug(s_data['name'])
            for sub_data in s_data.get('subsectors', []):
                sub_slug = generate_slug(f"{sector_slug}-{sub_data['name']}")
                sub_id = subsector_map.get(sub_slug)
                
                for i, jf_data in enumerate(sub_data.get('jobFamilies', [])):
                    name = jf_data['name']
                    slug = generate_slug(f"{sub_slug}-{name}")
                    job_families.append({
                        'id': uuid.uuid4(),
                        'subsector_id': sub_id,
                        'name': name,
                        'slug': slug,
                        'display_order': i,
                        'search_text': name
                    })
                    
        await upsert_records(db, JobFamily, job_families, ['slug'])
        await db.commit()
        
        result = await db.execute(select(JobFamily))
        all_jf = result.scalars().all()
        for jf in all_jf:
            job_family_map[jf.slug] = jf.id
            stats['job_families'] += 1

        # Pre-process SPECIALIZATIONS array from taxonomy to map IDs/Names to onet/isco/esco
        spec_metadata_map = {}
        for spec_data in taxonomy_data.get('SPECIALIZATIONS', []):
            spec_id = spec_data.get('id')
            if spec_id:
                spec_metadata_map[spec_id] = spec_data

        # 4. PROCESS SPECIALIZATIONS
        specializations = []
        spec_order = 0
        for s_data in taxonomy_data.get('SECTORS', []):
            sector_slug = generate_slug(s_data['name'])
            for sub_data in s_data.get('subsectors', []):
                sub_slug = generate_slug(f"{sector_slug}-{sub_data['name']}")
                for jf_data in sub_data.get('jobFamilies', []):
                    jf_slug = generate_slug(f"{sub_slug}-{jf_data['name']}")
                    jf_id = job_family_map.get(jf_slug)
                    
                    for spec_entry in jf_data.get('specs', []):
                        if isinstance(spec_entry, str):
                            raw_name = spec_entry
                        else:
                            raw_name = spec_entry.get('name', '')
                            
                        # Extract clean name for slug matching, remove asterisk
                        clean_id = raw_name.replace('*', '')
                        normalized_name = normalize_name(raw_name)
                        slug = generate_slug(normalized_name)
                        
                        # Check metadata map
                        metadata = spec_metadata_map.get(clean_id) or spec_metadata_map.get(slug) or {}
                        
                        specializations.append({
                            'id': uuid.uuid4(),
                            'job_family_id': jf_id,
                            'name': normalized_name,
                            'slug': slug,
                            'specialization_code': metadata.get('id', clean_id),
                            'display_name': metadata.get('name', normalized_name),
                            'path': metadata.get('path'),
                            'onet': metadata.get('onet'),
                            'isco': metadata.get('isco'),
                            'esco': metadata.get('esco'),
                            'display_order': spec_order,
                            'search_text': normalized_name
                        })
                        spec_order += 1
                        
        await upsert_records(db, Specialization, specializations, ['slug'])
        await db.commit()
        
        result = await db.execute(select(Specialization))
        all_specs = result.scalars().all()
        for sp in all_specs:
            specialization_map[sp.slug] = sp.id
            stats['specializations'] += 1

        # 5. PROCESS SKILLS
        skills_to_insert = []
        skill_order = 0
        for spec_data in taxonomy_data.get('SPECIALIZATIONS', []):
            spec_slug = generate_slug(normalize_name(spec_data.get('id', '')))
            spec_id = specialization_map.get(spec_slug)
            
            if not spec_id:
                spec_slug = generate_slug(normalize_name(spec_data.get('name', '')))
                spec_id = specialization_map.get(spec_slug)
                
            if spec_id:
                for sk_data in spec_data.get('skills', []):
                    sk_name = sk_data.get('name', '')
                    sk_slug = generate_slug(f"{spec_slug}-{sk_name}")
                    skills_to_insert.append({
                        'id': uuid.uuid4(),
                        'specialization_id': spec_id,
                        'skill_name': sk_name,
                        'slug': sk_slug,
                        'category': sk_data.get('category'),
                        'proficiency_level': str(sk_data.get('level', '')),
                        'criticality': sk_data.get('criticality'),
                        'roles': sk_data.get('roles'),
                        'transferability': sk_data.get('transferability'),
                        'certification': sk_data.get('cert'),
                        'ai_impact': sk_data.get('ai'),
                        'future_trajectory': sk_data.get('trajectory'),
                        'description': sk_data.get('desc'),
                        'display_order': skill_order,
                        'search_text': sk_name
                    })
                    skill_order += 1
            else:
                stats['warnings'].append(f"Specialization not found for skills: {spec_data.get('id')}")
                
        await upsert_records(db, Skill, skills_to_insert, ['slug'])
        await db.commit()
        stats['skills'] = len(skills_to_insert)

        # 6. PROCESS GLOSSARY TERMS
        glossary_terms = []
        for term_data in taxonomy_data.get('GLOSSARY', []):
            term_name = term_data.get('term', '')
            term_slug = generate_slug(term_name)
            glossary_terms.append({
                'id': uuid.uuid4(),
                'term': term_name,
                'slug': term_slug,
                'definition': term_data.get('def', ''),
                'search_text': term_name
            })
            
        await upsert_records(db, GlossaryTerm, glossary_terms, ['slug'])
        await db.commit()
        stats['glossary_terms'] = len(glossary_terms)

        # 7. PROCESS JOB TITLES
        job_titles = []
        jt_order = 0
        for s_data in job_titles_data.get('SECTORS', []):
            for sub_data in s_data.get('subsectors', []):
                for jf_data in sub_data.get('jobFamilies', []):
                    for spec_entry in jf_data.get('specs', []):
                        spec_name = spec_entry.get('name', '')
                        slug = generate_slug(normalize_name(spec_name))
                        spec_id = specialization_map.get(slug)
                        
                        if not spec_id:
                            stats['warnings'].append(f"Specialization not found for job titles: {spec_name}")
                            continue
                            
                        for jt in spec_entry.get('jobTitles', []):
                            jt_slug = generate_slug(f"{slug}-{jt}")
                            job_titles.append({
                                'id': uuid.uuid4(),
                                'specialization_id': spec_id,
                                'job_title': jt,
                                'slug': jt_slug,
                                'display_order': jt_order,
                                'search_text': jt
                            })
                            jt_order += 1
                            
        await upsert_records(db, JobTitle, job_titles, ['slug'])
        await db.commit()
        stats['job_titles'] = len(job_titles)

        # 8. POPULATE CAREER PATHS
        await db.execute(text("TRUNCATE TABLE career_paths;"))
        paths = []
        for sp in all_specs:
            result_jf = await db.execute(select(JobFamily).filter(JobFamily.id == sp.job_family_id))
            jf = result_jf.scalars().first()
            if jf:
                result_sub = await db.execute(select(Subsector).filter(Subsector.id == jf.subsector_id))
                sub = result_sub.scalars().first()
                if sub:
                    paths.append({
                        'id': uuid.uuid4(),
                        'sector_id': sub.sector_id,
                        'subsector_id': jf.subsector_id,
                        'job_family_id': sp.job_family_id,
                        'specialization_id': sp.id
                    })
                    
        await upsert_records(db, CareerPath, paths, ['sector_id', 'subsector_id', 'job_family_id', 'specialization_id'])
        await db.commit()

        # Update Log
        duration = time.time() - start_time
        import_log.completed_at = datetime.utcnow()
        import_log.duration = duration
        import_log.status = 'SUCCESS'
        import_log.total_records = sum(v for k, v in stats.items() if isinstance(v, int))
        await db.commit()
        
        # Save Report
        report_path = os.path.join(reports_dir, 'master_data_import_report.json')
        with open(report_path, 'w') as f:
            json.dump(stats, f, indent=4)
            
        print(f"\n{stats['sectors']} Sectors Imported")
        print(f"{stats['subsectors']} Subsectors Imported")
        print(f"{stats['job_families']} Job Families Imported")
        print(f"{stats['specializations']} Specializations Imported")
        print(f"{stats['job_titles']} Job Titles Imported")
        print(f"{stats['skills']} Skills Imported")
        print(f"{stats['glossary_terms']} Glossary Terms Imported\n")
        print("Completed Successfully")
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
