import json
import re
import os

def parse_markdown():
    filepath = "test_project/畢業門檻.md"
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Split by department headers
    dept_blocks = re.split(r'\n## \d+\. ', content)
    
    results = {}
    
    for block in dept_blocks[1:]: # Skip the first chunk (header)
        # Extract department name
        lines = block.split('\n')
        header_line = lines[0].strip()
        
        # E.g. "醫學資訊與健康科技進修學士學位學程 (111學年度)"
        # or "餐旅管理學系-碩士班 (114學年度)"
        m_dept = re.match(r'^(.*?)(?:\s*\(.*?\))?$', header_line)
        if not m_dept:
            continue
            
        dept_name = m_dept.group(1).strip()
        
        reqs = {
            "total": 128,
            "obligatory": 80,
            "elective": 48,
            "raw_text": "## " + block.strip(),
            "required_courses": []
        }
        
        # Extract total credits
        # E.g. * **畢業最低學分數：** 128 學分
        m_total = re.search(r'畢業最低學分數[^\d]*(\d+)', block)
        if m_total:
            reqs["total"] = int(m_total.group(1))
            
        # Try to extract obligatory/elective from the parenthesis if present
        # E.g. (全人教育課程：32 學分、院系必修必選：72 學分、選修：24 學分)
        # But this format is highly variable, so we'll fallback to defaults if not found.
        # Often: 必修: 72, 選修: 24, 全人: 32 -> 總共 128.
        # Actually GUI subtracts General (12) from obligatory. So we just need rough numbers or we can rely on course list.
        # Let's try to find 必修(\d+)
        m_ob = re.search(r'必修[^\d\n]{0,20}?(\d+)\s*學分', block)
        if m_ob:
            reqs["obligatory"] = int(m_ob.group(1))
            
        m_el = re.search(r'選修[^\d\n]{0,20}?(\d+)\s*學分', block)
        if m_el:
            reqs["elective"] = int(m_el.group(1))

        # Extract required courses
        courses = []
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('*') and '學分' in line:
                # Remove leading header like "* **一年級：** "
                line = re.sub(r'^\*\s*\*\*[^\*]+[：:]\s*\*\*\s*', '', line)
                line = re.sub(r'^\*\s*', '', line)
                
                items = re.split(r'[、，]', line)
                for item in items:
                    item = item.strip()
                    m_course = re.search(r'^(.*?)\s*[\(（]\d+(?:~\d+)?學分[\)）]$', item)
                    if m_course:
                        c_name = m_course.group(1).strip()
                        c_name = re.sub(r'^.*?[：:]\s*', '', c_name)
                        c_name = c_name.replace('*', '').strip()
                        if c_name and len(c_name) > 1:
                            courses.append(c_name)
                            
        # Deduplicate and remove garbage
        bad_words = ["論文", "導師時間", "體育", "資訊素養", "專題討論", "畢業製作"]
        clean_courses = []
        for c in set(courses):
            # remove "或 XX"
            c = re.split(r'\s*或\s*', c)[0].strip()
            if c and not any(bw in c for bw in bad_words):
                clean_courses.append(c)
                
        reqs["required_courses"] = clean_courses
        results[dept_name] = reqs
        
    with open("test_project/department_reqs.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully parsed {len(results)} departments.")

if __name__ == "__main__":
    parse_markdown()
