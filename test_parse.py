import json
with open('test_project/department_reqs.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(data.get('日本語文學系-學士班 (114學年度)', {}).get('required_courses', []))
