import json
import re
import os

def generate_slug(text):
    if not text: return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def normalize_name(text):
    if not text: return ""
    return text.replace('*', '').replace('-', ' ').strip().title()

def generate_titles(name):
    # Base abstract domains will sound great with standard corporate titles
    base = name
    titles = [
        f"Junior {base} Analyst",
        f"{base} Analyst",
        f"Senior {base} Analyst",
        f"{base} Specialist",
        f"Lead {base} Specialist",
        f"{base} Manager",
        f"Senior {base} Manager",
        f"Director of {base}"
    ]
    return titles[:8]

def main():
    specs_path = 'f:/Career Shift Project/generated/specializations.json'
    out_path = 'f:/Career Shift Project/generated/job_titles.json'
    
    with open(specs_path, 'r', encoding='utf-8') as f:
        specs = json.load(f)
        
    seen_slugs = set()
    results = []
    
    for s in specs:
        raw_name = s.get('name', '')
        norm_name = normalize_name(raw_name)
        slug = generate_slug(norm_name)
        
        if slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        
        titles = generate_titles(norm_name)
        
        results.append({
            "specialization_slug": slug,
            "job_titles": titles
        })
        
    # Validation
    print(f"Specializations loaded : {len(specs)}")
    print(f"Unique Specialization slugs : {len(seen_slugs)}")
    print(f"Job title records generated : {len(results)}")
    
    missing_slugs = len(seen_slugs) - len(results)
    print(f"Missing specializations : {missing_slugs}")
    
    duplicate_slugs = len(specs) - len(seen_slugs)
    print(f"Duplicate slugs in source : {duplicate_slugs}")
    
    total_titles = sum(len(r['job_titles']) for r in results)
    avg_titles = total_titles / len(results) if results else 0
    print(f"Average titles per specialization : {avg_titles:.1f}")
    
    passed = True
    if missing_slugs != 0: passed = False
    if len(results) != len(seen_slugs): passed = False
    if any(len(r['job_titles']) < 5 for r in results): 
        print("FAIL: Some arrays have fewer than 5 titles.")
        passed = False
        
    if passed:
        print("Validation PASSED")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    else:
        print("Validation FAILED")

if __name__ == '__main__':
    main()
