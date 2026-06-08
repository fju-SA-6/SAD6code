import json
import re

line = "* 一年級：初級日語 (8學分)、初級日語會話 (4學分)、初級日語聽解實務 (2學分)、日本語讀本 (4學分)"
line = re.sub(r'^\*\s*\*\*[^\*]+[：:]\s*\*\*\s*', '', line)
line = re.sub(r'^\*\s*', '', line)
print("Line after sub:", line)

items = re.split(r'[、，]', line)
courses = []
for item in items:
    item = item.strip()
    print("Testing item:", item)
    m_course = re.search(r'^(.*?)\s*[\(（]\d+(?:~\d+)?學分[\)）]$', item)
    if m_course:
        c_name = m_course.group(1).strip()
        c_name = re.sub(r'^.*?[：:]\s*', '', c_name)
        c_name = c_name.replace('*', '').strip()
        print("Found course:", c_name)
        courses.append(c_name)
    else:
        print("No match for:", item)
        
print("Final courses:", courses)
