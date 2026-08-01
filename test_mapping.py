import json
import re

def generate_slug(text):
    if not text: return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def normalize_name(text):
    if not text: return ""
    return text.replace('*', '').replace('-', ' ').strip().title()

specs = json.load(open('../generated/specializations.json', encoding='utf-8'))
titles = json.load(open('../generated/job_titles.json', encoding='utf-8'))

temp_spec_slug_to_json_id = {}
for s in specs:
    n = normalize_name(s.get('name', ''))
    sl = generate_slug(n)
    temp_spec_slug_to_json_id[sl] = s['id']

print(f"Total specializations in JSON: {len(specs)}")
print(f"Unique slugs in specializations: {len(temp_spec_slug_to_json_id)}")

total_jt = 0
mapped = 0
skipped = 0
first_20_skipped = []

if isinstance(titles, dict) and "SECTORS" in titles:
    for sector in titles.get("SECTORS", []):
        for subsector in sector.get("subsectors", []):
            for jf in subsector.get("jobFamilies", []):
                for spec in jf.get("specs", []):
                    spec_name = spec.get("name", "")
                    spec_slug = generate_slug(normalize_name(spec_name))
                    
                    if spec_slug in temp_spec_slug_to_json_id:
                        for jt in spec.get("jobTitles", []):
                            total_jt += 1
                            mapped += 1
                    else:
                        for jt in spec.get("jobTitles", []):
                            total_jt += 1
                            skipped += 1
                            if len(first_20_skipped) < 20:
                                first_20_skipped.append(f"JobTitle: '{jt}', missing Specialization slug: '{spec_slug}' (Original name: '{spec_name}')")

print(f"total job titles in JSON: {total_jt}")
print(f"number successfully mapped: {mapped}")
print(f"number skipped: {skipped}")
print("first 20 skipped records with the exact reason:")
for reason in first_20_skipped:
    print(reason)
