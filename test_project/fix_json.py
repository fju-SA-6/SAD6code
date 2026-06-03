import json
with open('department_reqs.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

if "資訊管理學系-學士班" in data:
    data["資訊管理學系-學士班"]["obligatory"] = 96
    data["資訊管理學系-學士班"]["elective"] = 32

with open('department_reqs.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
print("Done")
