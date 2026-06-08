import json

with open("department_reqs.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# The list of required courses parsed from the new markdown
required_courses = [
    "微積分", "會計學", "企業管理概論", "程式設計概論", "進階程式設計",
    "Web前端設計", "Web程式設計", "統計學", "經濟學", "資料庫管理",
    "創新與設計思考", "資料結構", "系統分析與設計", "資料通訊與網路",
    "作業系統", "資訊系統專題一", "資訊系統專題二", "管理資訊系統",
    # Add common general education required courses
    "國文", "外國語文", "專業倫理", "大學入門", "人生哲學"
]

raw_text = """## 資訊管理學系-學士班 (114學年度)

* **畢業最低學分數：** 128 學分 (全人教育課程：32 學分、院系指定專業核心必修課程)。
* **全人教育核心基本規格 (32學分)：** * 導師時間 (0學分)、大學入門 (2學分)、人生哲學 (4學分)、專業倫理 (2學分)、體育 (2學分)。
* 國文 (4學分)、外國語文 (8學分，大一英文為學年課且至少4學分)、資訊素養基本能力檢定 (0學分，需通過基本能力檢定或修讀相關課程方式抵免)。
* 通識涵養課程（人文與藝術、自然與科技、社會科學、永續素養各2學分，另加2學分自由選修，合計 10 學分，且須排除所屬系院之通識排除科目）。


* **課程結構與修課提示：**
微積分 必 6
會計學 必 6
企業管理概論 必 3
程式設計概論 必 3
進階程式設計 必 3
Web前端設計 必 2
Web程式設計 必 3
統計學 必 6
經濟學 必 6
資料庫管理 必 3
創新與設計思考 必 2
資料結構 必 3
系統分析與設計 必 3
資料通訊與網路 必 3
作業系統 必 3
資訊系統專題一 必 3
資訊系統專題二 必 3
管理資訊系統 必 3
"""

if "資訊管理學系-學士班" in data:
    data["資訊管理學系-學士班"]["raw_text"] = raw_text
    data["資訊管理學系-學士班"]["required_courses"] = required_courses
    data["資訊管理學系-學士班"]["obligatory"] = 64  # Based on 64 credits from previous text

if "資訊管理學系-學士班 (114學年度) - 完整補正版" in data:
    del data["資訊管理學系-學士班 (114學年度) - 完整補正版"]

with open("department_reqs.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("Updated department_reqs.json")
