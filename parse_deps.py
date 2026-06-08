import os
import json
import re
import fitz  # PyMuPDF
import pandas as pd

def extract_from_pdf(filepath):
    text = ""
    try:
        doc = fitz.open(filepath)
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None
    return parse_text(text, text)

def extract_from_excel(filepath):
    text = ""
    try:
        df = pd.read_excel(filepath)
        text = df.to_string()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None
    return parse_text(text, text, filepath)

def parse_text(text, raw_text, filepath=""):
    # Regex to find total, obligatory, and elective credits
    # Default values
    reqs = {"total": 128, "obligatory": 80, "elective": 48}
    
    # Try to find "畢業總學分" or similar
    total_match = re.search(r'(?:畢業(?:應修)?總學分(?:數)?|總學分).*?(\d{2,3})', text)
    if total_match:
        reqs["total"] = int(total_match.group(1))
        
    ob_match = re.search(r'(?:必修(?:學分(?:數)?)?).*?(\d{2,3})', text)
    if ob_match:
        reqs["obligatory"] = int(ob_match.group(1))
        
    el_match = re.search(r'(?:選修(?:學分(?:數)?)?).*?(\d{2,3})', text)
    if el_match:
        reqs["elective"] = int(el_match.group(1))
        
    # Validation / adjustment
    if reqs["total"] > 200 or reqs["total"] < 50:
        reqs["total"] = 128
    if reqs["obligatory"] > reqs["total"]:
        reqs["obligatory"] = 80
    if reqs["elective"] > reqs["total"]:
        reqs["elective"] = 48
        
    # Store raw text
    reqs["raw_text"] = raw_text.strip()
    
    # Extract required courses
    lines = raw_text.split('\n')
    courses = []
    for i, line in enumerate(lines):
        line = line.strip()
        if line in ["必", "必修"]:
            if i > 0:
                prev_line = lines[i-1].strip()
                if re.match(r'^[A-Za-z0-9]{4,10}$', prev_line) and i > 1:
                    course_name = lines[i-2].strip()
                else:
                    course_name = prev_line
                
                if len(course_name) > 1 and not re.match(r'^[\d\W]+$', course_name):
                    courses.append(course_name)
                    
    # Clean and deduplicate
    bad_words = {"導師時間", "必選", "學分數", "學分", "上", "下", "類別", "備註", "模組", "選別", "科  目  名  稱", "系主任", "院長"}
    clean_courses = []
    for c in set(courses):
        # Remove any leading/trailing weird chars
        c = re.sub(r'^\W+|\W+$', '', c)
        if c and c not in bad_words and len(c) <= 25:
            clean_courses.append(c)
            
    reqs["required_courses"] = clean_courses
        
    return reqs

def main():
    directory = "畢業門檻整理"
    results = {}
    
    if not os.path.exists(directory):
        print(f"Directory {directory} not found.")
        return

    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        name, ext = os.path.splitext(filename)
        name = name.strip() # Remove leading/trailing spaces
        
        reqs = None
        if ext.lower() == '.pdf':
            reqs = extract_from_pdf(filepath)
        elif ext.lower() in ['.xls', '.xlsx']:
            reqs = extract_from_excel(filepath)
        
        if reqs:
            results[name] = reqs
        else:
            results[name] = {"total": 128, "obligatory": 80, "elective": 48, "raw_text": "無資料"}
            
    with open("test_project/department_reqs.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
        
    print("Done. Wrote to test_project/department_reqs.json")

if __name__ == "__main__":
    main()
