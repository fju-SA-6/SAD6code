import json
with open('test_project/department_reqs.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(list(data.keys()))
