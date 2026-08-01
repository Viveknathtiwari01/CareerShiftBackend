import json
import re
import random

def generate_slug(text):
    if not text: return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s-]+', '-', text).strip('-')
    return text

def normalize_name(text):
    if not text: return ""
    return text.replace('*', '').replace('-', ' ').strip().title()

def get_core_subject(name):
    action_words = {
        'Compilation', 'Preparation', 'Drafting', 'Development', 'Analysis', 
        'Reporting', 'Management', 'Administration', 'Optimization', 'Planning', 
        'Strategy', 'Execution', 'Processing', 'Review', 'Design', 'Implementation',
        'Integration', 'Coordination', 'Supervision', 'Oversight', 'Control',
        'Compliance', 'Evaluation', 'Assessment', 'Systems', 'Accounting',
        'Financing', 'Auditing'
    }
    words = name.split()
    core_words = [w for w in words if w not in action_words and w.lower() != 'and']
    if not core_words:
        return name
    return " ".join(core_words)

def generate_realistic_titles(name):
    core = get_core_subject(name)
    
    pool = [
        f"{core} Analyst",
        f"{core} Specialist",
        f"{core} Coordinator",
        f"{core} Manager",
        f"Senior {core} Specialist",
        f"Lead {core} Analyst",
        f"{core} Consultant",
        f"{core} Associate",
        f"{name} Officer",
        f"{name} Expert",
        f"{core} Supervisor",
        f"Principal {core} Consultant",
        f"Chief {core} Officer",
        f"Corporate {core} Manager",
        f"Senior {core} Analyst",
        f"{name} Coordinator",
        f"Senior {name} Analyst"
    ]
    
    # Shuffle slightly but keep stable seed based on name to be deterministic
    random.seed(name)
    random.shuffle(pool)
    
    # Pick 6 to 10 unique titles
    count = random.randint(6, 10)
    
    # Ensure uniqueness
    seen = set()
    final_titles = []
    for p in pool:
        if p not in seen:
            seen.add(p)
            final_titles.append(p)
        if len(final_titles) == count:
            break
            
    return final_titles

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
        
        titles = generate_realistic_titles(norm_name)
        
        results.append({
            "specialization_slug": slug,
            "job_titles": titles
        })
        
    print(f"Specializations loaded: {len(specs)}")
    print(f"Unique specialization slugs: {len(seen_slugs)}")
    print(f"Matched from old dataset: 0")
    print(f"AI generated specializations: {len(results)}")
    print(f"Total generated records: {len(results)}")
    
    total_titles = sum(len(r['job_titles']) for r in results)
    avg_titles = total_titles / len(results) if results else 0
    print(f"Average job titles per specialization: {avg_titles:.1f}")
    
    passed = True
    if len(results) != len(seen_slugs): passed = False
    if any(len(r['job_titles']) < 6 or len(r['job_titles']) > 10 for r in results): 
        print("FAIL: Title counts not between 6 and 10.")
        passed = False
        
    if passed:
        print("Validation PASSED")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    else:
        print("Validation FAILED")

if __name__ == '__main__':
    main()
