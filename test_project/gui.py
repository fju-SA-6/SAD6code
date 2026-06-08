import customtkinter as ctk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
from database import get_db_connection
import math
import platform
import os
import datetime
import sys
import subprocess
import threading
import tempfile
import json

from fpdf import FPDF

class GraduationGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🎓 輔大畢業學分查核系統")
        self.geometry("1100x750")
        
        # 設定為深色科技風格
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        # 全域字型設定
        self.f_title = ("Helvetica", 28, "bold")
        self.f_header = ("Helvetica", 16, "bold")
        self.f_body = ("Helvetica", 15)
        self.f_small = ("Helvetica", 13)
        self.f_btn = ("Helvetica", 15, "bold")

        # 資料庫快取
        self.all_courses = []
        self.passed_course_names = set()
        self.filtered_courses = []
        
        # 變數狀態
        self.checked_course_ids = set()
        self.checkbox_vars = {} # id -> BooleanVar
        
        # 畫面元件快取 (用來安全清除，不破壞 ScrollableFrame 內部結構)
        self.course_widgets = []
        self.rec_widgets = []
        
        # 無限滾動 (Infinite Scroll) 狀態
        self._courses_to_draw_queue = []
        self._page_courses_total = 0
        
        # 分頁狀態
        self.current_page = 1
        self.items_per_page = 100
        
        # 匯出資料快取
        self.current_recommendations = []

        # 讀取系所選項
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(script_dir, "department_reqs.json")
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                self.dep_reqs = json.load(f)
                self.departments = ["通用"] + sorted(list(self.dep_reqs.keys()))
        except:
            self.departments = ["通用"]
            
        default_dep = "資訊管理學系-學士班" if "資訊管理學系-學士班" in self.departments else self.departments[0]
        self.department_var = ctk.StringVar(value=default_dep)

        self.setup_ui()
        self.load_data_from_db()
        self.after(200, self.check_scroll_bottom)

    def setup_ui(self):
        # 建立 Tab
        self.tabview = ctk.CTkTabview(self, corner_radius=15, border_width=1, border_color="gray30")
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        self.tabview._segmented_button.configure(font=self.f_header)

        self.tab_courses = self.tabview.add("✨ 課程選擇區")
        self.tab_results = self.tabview.add("📊 畢業查核結果")

        self.setup_course_tab()
        self.setup_result_tab()



    def setup_course_tab(self):
        # 上方篩選列 (卡片風格)
        self.filter_frame = ctk.CTkFrame(self.tab_courses, corner_radius=15, fg_color="gray16", border_width=1, border_color="gray25")
        self.filter_frame.pack(fill="x", padx=10, pady=10)

        self.search_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="🔍 搜尋課程...", font=self.f_body, height=40, border_width=1)
        self.search_entry.pack(side="left", padx=10, pady=15, expand=True, fill="x")
        self.search_entry.bind("<KeyRelease>", self.on_filter_change)

        self.teacher_search_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="👨‍🏫 搜尋老師...", font=self.f_body, height=40, border_width=1)
        self.teacher_search_entry.pack(side="left", padx=10, pady=15, expand=True, fill="x")
        self.teacher_search_entry.bind("<KeyRelease>", self.on_filter_change)

        self.combo_department = ctk.CTkOptionMenu(
            self.filter_frame, variable=self.department_var, 
            values=self.departments, font=self.f_body, height=40
        )
        self.combo_department.pack(side="left", padx=10, pady=15)

        self.sys_rule_var = ctk.StringVar(value="114起學士班")
        self.sys_rule_menu = ctk.CTkOptionMenu(
            self.filter_frame, variable=self.sys_rule_var, 
            values=["113(含)以前學士班", "114起學士班", "二年制在職專班"], 
            font=self.f_body, height=40, command=self.on_filter_change
        )
        self.sys_rule_menu.pack(side="left", padx=10, pady=15)

        self.semester_var = ctk.StringVar(value="所有學期")
        self.semester_menu = ctk.CTkOptionMenu(self.filter_frame, variable=self.semester_var, values=["所有學期", "上學期", "下學期"], font=self.f_body, height=40, command=self.on_filter_change)
        self.semester_menu.pack(side="left", padx=10, pady=15)

        self.day_var = ctk.StringVar(value="所有星期")
        self.day_menu = ctk.CTkOptionMenu(self.filter_frame, variable=self.day_var, values=["所有星期", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"], font=self.f_body, height=40, command=self.on_filter_change)
        self.day_menu.pack(side="left", padx=10, pady=15)

        self.per_page_var = ctk.StringVar(value="100 筆 / 頁")
        self.per_page_menu = ctk.CTkOptionMenu(self.filter_frame, variable=self.per_page_var, values=["100 筆 / 頁", "200 筆 / 頁", "300 筆 / 頁", "全部顯示"], font=self.f_body, height=40, command=self.on_per_page_change)
        self.per_page_menu.pack(side="left", padx=10, pady=15)

        # 動作按鈕列
        self.action_frame = ctk.CTkFrame(self.tab_courses, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=10, pady=(0, 5))

        self.btn_select_all = ctk.CTkButton(self.action_frame, text="☑ 全選此頁", font=self.f_btn, height=35, command=self.select_all_page)
        self.btn_select_all.pack(side="left", padx=5)

        self.btn_clear_all = ctk.CTkButton(self.action_frame, text="☐ 清空此頁", font=self.f_btn, height=35, fg_color="transparent", border_width=2, text_color="gray80", hover_color="gray30", command=self.clear_all_page)
        self.btn_clear_all.pack(side="left", padx=5)

        self.btn_check = ctk.CTkButton(self.action_frame, text="🚀 查核學分", font=self.f_title, height=45, fg_color="#00C851", hover_color="#007E33", command=self.do_graduation_check)
        self.btn_check.pack(side="right", padx=5)

        self.btn_update_db = ctk.CTkButton(self.action_frame, text="🔄 重新擷取學校資料", font=self.f_btn, height=35, fg_color="#33b5e5", hover_color="#0099cc", command=self.update_school_db)
        self.btn_update_db.pack(side="right", padx=15)

        # 中間滾動清單 (外框美化)
        self.list_frame = ctk.CTkScrollableFrame(self.tab_courses, corner_radius=15, fg_color="gray12", border_width=1, border_color="gray20")
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 下方分頁按鈕列
        self.pagination_frame = ctk.CTkFrame(self.tab_courses, fg_color="transparent")
        self.pagination_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_prev = ctk.CTkButton(self.pagination_frame, text="◀ 上一頁", font=self.f_btn, width=100, height=35, command=self.go_prev_page)
        self.btn_prev.pack(side="left", padx=5)
        
        self.lbl_page = ctk.CTkLabel(self.pagination_frame, text="第 1 / 1 頁", font=self.f_body, text_color="gray70")
        self.lbl_page.pack(side="left", padx=20, expand=True)

        self.btn_next = ctk.CTkButton(self.pagination_frame, text="下一頁 ▶", font=self.f_btn, width=100, height=35, command=self.go_next_page)
        self.btn_next.pack(side="right", padx=5)

    def setup_result_tab(self):
        # 以左右分割結果視窗
        self.res_split = ctk.CTkFrame(self.tab_results, fg_color="transparent")
        self.res_split.pack(fill="both", expand=True, padx=5, pady=5)

        # 左：統計資訊卡片
        self.res_stats_frame = ctk.CTkFrame(self.res_split, corner_radius=15, fg_color="gray16", border_width=1, border_color="gray25")
        self.res_stats_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.lbl_res_title = ctk.CTkLabel(self.res_stats_frame, text="📈 學分統計狀態", font=self.f_title)
        self.lbl_res_title.pack(pady=(25, 15))
        
        # 總學分
        self.lbl_total_prog = ctk.CTkLabel(self.res_stats_frame, text="🎯 總學分進度: 0 / 128", font=self.f_header)
        self.lbl_total_prog.pack(anchor="w", padx=30, pady=(15, 5))
        self.prog_total = ctk.CTkProgressBar(self.res_stats_frame, height=20, corner_radius=10, progress_color="#33b5e5")
        self.prog_total.set(0)
        self.prog_total.pack(fill="x", padx=30, pady=(0, 15))

        # 必修
        self.lbl_req_prog = ctk.CTkLabel(self.res_stats_frame, text="📚 必修學分: 0 / 80", font=self.f_header)
        self.lbl_req_prog.pack(anchor="w", padx=30, pady=(15, 5))
        self.prog_req = ctk.CTkProgressBar(self.res_stats_frame, height=20, corner_radius=10, progress_color="#ff4444")
        self.prog_req.set(0)
        self.prog_req.pack(fill="x", padx=30, pady=(0, 15))

        # 選修
        self.lbl_elec_prog = ctk.CTkLabel(self.res_stats_frame, text="🧩 選修學分: 0 / 48", font=self.f_header)
        self.lbl_elec_prog.pack(anchor="w", padx=30, pady=(5, 5))
        self.prog_elec = ctk.CTkProgressBar(self.res_stats_frame, height=20, corner_radius=10, progress_color="#00C851")
        self.prog_elec.set(0)
        self.prog_elec.pack(fill="x", padx=30, pady=(0, 10))

        # 通識
        self.lbl_gen_prog = ctk.CTkLabel(self.res_stats_frame, text="🌍 通識學分: 0 / 12", font=self.f_header)
        self.lbl_gen_prog.pack(anchor="w", padx=30, pady=(5, 5))
        self.prog_gen = ctk.CTkProgressBar(self.res_stats_frame, height=20, corner_radius=10, progress_color="#9933cc")
        self.prog_gen.set(0)
        self.prog_gen.pack(fill="x", padx=30, pady=(0, 5))

        self.lbl_gen_details = ctk.CTkLabel(self.res_stats_frame, text="人文與藝術: 0  |  自然與科技: 0  |  社會科學: 0", font=self.f_small, text_color="gray70", justify="left")
        self.lbl_gen_details.pack(anchor="w", padx=35, pady=(0, 15))

        # 體育 (PE)
        self.lbl_pe_prog = ctk.CTkLabel(self.res_stats_frame, text="🏃 體育: 尚未查核", font=self.f_header)
        self.lbl_pe_prog.pack(anchor="w", padx=30, pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self.res_stats_frame, text="狀態：尚未查核", font=self.f_header, text_color="orange")
        self.lbl_status.pack(pady=(5, 5))

        self.lbl_semesters = ctk.CTkLabel(self.res_stats_frame, text="🎓 預估最快畢業：尚未查核", font=self.f_header, text_color="#33b5e5")
        self.lbl_semesters.pack(pady=(0, 10))

        # 下方加入匯出 PDF 按鈕 (優先使用底端空間以防被圖表擠出畫面)
        self.btn_export_pdf = ctk.CTkButton(
            self.res_stats_frame, text="📄 匯出查核結果成 PDF", font=self.f_btn, 
            height=50, fg_color="#ff8800", hover_color="#cc6600",
            command=self.export_to_pdf, state="disabled"
        )
        self.btn_export_pdf.pack(side="bottom", fill="x", padx=30, pady=(10, 25))

        # 中間顯示額外門檻區域
        self.threshold_frame = ctk.CTkFrame(self.res_stats_frame, fg_color="gray12", corner_radius=10)
        self.threshold_frame.pack(side="bottom", fill="both", expand=True, padx=20, pady=5)
        
        self.lbl_threshold_title = ctk.CTkLabel(self.threshold_frame, text="📌 額外畢業門檻", font=self.f_header, text_color="#33b5e5")
        self.lbl_threshold_title.pack(anchor="w", padx=15, pady=(10, 0))

        self.txt_threshold = ctk.CTkTextbox(self.threshold_frame, font=self.f_body, fg_color="transparent", wrap="word")
        self.txt_threshold.pack(fill="both", expand=True, padx=10, pady=10)
        self.txt_threshold.insert("0.0", "尚未查核")
        self.txt_threshold.configure(state="disabled")

        # 右：推薦清單卡片
        self.res_rec_frame = ctk.CTkFrame(self.res_split, corner_radius=15, fg_color="gray16", border_width=1, border_color="gray25")
        self.res_rec_frame.pack(side="right", fill="both", expand=True)

        self.lbl_rec_title = ctk.CTkLabel(self.res_rec_frame, text="💡 智慧推薦修課", font=self.f_title)
        self.lbl_rec_title.pack(pady=(25, 5))

        self.rec_scroll = ctk.CTkScrollableFrame(self.res_rec_frame, fg_color="transparent")
        self.rec_scroll.pack(fill="both", expand=True, padx=10, pady=10)


    # ---------------- 邏輯函數 ----------------

    def check_scroll_bottom(self):
        # 如果候選清單中還有等待被繪製的課程
        if hasattr(self, 'list_frame') and self._courses_to_draw_queue:
            try:
                # 取得 Canvas 目前視野的位置 (top, bottom 都是 0 ~ 1 之間的小數)
                top, bottom = self.list_frame._parent_canvas.yview()
                # 提早觸發門檻 (80% 處即開始載入下一批次)
                if bottom >= 0.80:
                    self.draw_next_batch()
            except Exception:
                pass
        self.after(50, self.check_scroll_bottom)

    def load_data_from_db(self):
        conn, cursor = get_db_connection()
        if not conn:
            messagebox.showerror("資料庫錯誤", "無法連線至資料庫，請確認環境！")
            return
            
        try:
            # 建立通識分類字典 (從 Courses_Scraped 的 general_field 取得)
            cursor.execute("SELECT course_name, general_field FROM Courses_Scraped WHERE category='通識' AND general_field IS NOT NULL")
            self.gen_ed_map = {}
            for row in cursor.fetchall():
                n, gf = row
                if gf:
                    import re
                    match = re.search(r"領域：\s*(\S+)", gf)
                    if match:
                        raw_domain = match.group(1)
                        if raw_domain == "人文藝術":
                            self.gen_ed_map[n] = "人文與藝術"
                        elif raw_domain == "自然科技":
                            self.gen_ed_map[n] = "自然與科技"
                        else:
                            self.gen_ed_map[n] = raw_domain

            # 1. 取得已過關之個人成績，並找出重複修課時最好的成績，同時記錄該科學分數
            self.course_best_grades = {}
            cursor.execute("SELECT course_name, grade, credits FROM Personal_Grades")
            
            def get_grade_val(g):
                if isinstance(g, int): return g
                if isinstance(g, str):
                    if g.isdigit(): return int(g)
                    if g in ['抵免', '通過']: return 60
                return -1

            for row in cursor.fetchall():
                c_name = row[0]
                grade = row[1] if row[1] is not None else ""
                if isinstance(grade, str):
                    grade = grade.strip()
                
                c_credits = float(row[2]) if row[2] else 0.0
                c_credits = int(c_credits) if c_credits == int(c_credits) else c_credits

                current_val = get_grade_val(grade)
                
                if c_name not in self.course_best_grades:
                    self.course_best_grades[c_name] = {'grade': grade, 'credits': c_credits}
                else:
                    best_val = get_grade_val(self.course_best_grades[c_name]['grade'])
                    if current_val > best_val:
                        self.course_best_grades[c_name] = {'grade': grade, 'credits': c_credits}
            
            for c_name, data in self.course_best_grades.items():
                grade = data['grade']
                is_passed = False
                if isinstance(grade, int):
                    if grade >= 60:
                        is_passed = True
                else:
                    if grade.isdigit() and int(grade) >= 60:
                        is_passed = True
                    elif grade not in ['不及格', '未通過', '停修', 'W', 'F', '', '未評定成績']:
                        is_passed = True
                
                if is_passed:
                    self.passed_course_names.add(c_name)

            # 2. 取得所有課程資料
            # 2. 取得所有課程資料，將「課名相同且學分相同」的合併顯示
            sql = """
                SELECT c.id, c.course_name, c.credits, c.category, 
                       GROUP_CONCAT(DISTINCT c.semester) as semesters, 
                       GROUP_CONCAT(DISTINCT s.day_of_week) as days, 
                       GROUP_CONCAT(DISTINCT c.teacher SEPARATOR ', ') as teachers 
                FROM Courses_Scraped c
                LEFT JOIN Course_Schedule s ON c.id = s.course_id
                GROUP BY c.course_name, c.credits
                ORDER BY c.category, c.course_name, c.credits
            """
            cursor.execute(sql)
            self.all_courses = []
            
            already_auto_checked = set()
            for row in cursor.fetchall():
                c_id, name, credits_v_raw, category, sems, days, teachers = row
                
                # 確保 credits_v 為數值型態，避免後續加總時發生字串相加的錯誤
                try:
                    c_val = float(credits_v_raw)
                    credits_v = int(c_val) if c_val == int(c_val) else c_val
                except:
                    credits_v = 0
                
                # 自動勾選邏輯：若在已通過名單內，且學分數符合個人真實獲得的學分，才加入 checked_course_ids
                if name in self.passed_course_names:
                    personal_credits = self.course_best_grades[name]['credits']
                    try:
                        match_credits = (float(credits_v) == float(personal_credits))
                    except:
                        match_credits = (credits_v == personal_credits)
                        
                    if match_credits and name not in already_auto_checked:
                        self.checked_course_ids.add(str(c_id))
                        already_auto_checked.add(name)

                self.all_courses.append({
                    "id": str(c_id),
                    "name": name,
                    "credits": credits_v,
                    "category": category,
                    "semesters": sems or "",
                    "days": days or "",
                    "teachers": teachers or "無資料"
                })
                
        except Exception as e:
            messagebox.showerror("讀取失敗", f"讀取資料庫發生錯誤：{e}")
        finally:
            cursor.close()
            conn.close()

        # 載入完成，觸發第一次渲染
        self.apply_filter()

    def apply_filter(self):
        search_q = self.search_entry.get().strip().lower()
        teacher_q = self.teacher_search_entry.get().strip().lower()
        sem_q = self.semester_var.get()
        day_q = self.day_var.get()

        self.filtered_courses = []
        for c in self.all_courses:
            match_name = search_q in c['name'].lower()
            match_teacher = teacher_q in c['teachers'].lower()
            match_sem = (sem_q == "所有學期" or sem_q in c['semesters'])
            match_day = (day_q == "所有星期" or day_q in c['days'])
            if match_name and match_teacher and match_sem and match_day:
                self.filtered_courses.append(c)
        
        # 排序：將系統自動勾選（已在 passed_course_names 中）的課程排在最前面
        self.filtered_courses.sort(key=lambda c: 0 if c['name'] in self.passed_course_names else 1)
        
        self.current_page = 1
        self.render_page()

    def on_filter_change(self, *args):
        self.apply_filter()

    def on_per_page_change(self, value):
        if "全部" in value:
            self.items_per_page = 999999
        else:
            self.items_per_page = int(value.split()[0])
        self.current_page = 1
        self.render_page()

    def render_page(self):
        # 暫時關閉操作按鈕
        self.btn_select_all.configure(state="disabled")
        self.btn_clear_all.configure(state="disabled")
        self.btn_prev.configure(state="disabled")
        self.btn_next.configure(state="disabled")

        # 斷開前一次的無限滾動資料
        self._courses_to_draw_queue = []
        self._page_courses_total = 0

        # 正確清除目前列表：只刪除我們放進去的 CheckBox，絕對不呼叫 winfo_children 以免砍到內部的 Canvas
        for w in self.course_widgets:
            try:
                w.destroy()
            except:
                pass
        self.course_widgets.clear()
        self.checkbox_vars.clear()

        total_items = len(self.filtered_courses)
        total_pages = math.ceil(total_items / self.items_per_page) if total_items > 0 else 1
        
        if self.current_page > total_pages: 
            self.current_page = total_pages
        if self.current_page < 1:
            self.current_page = 1
            
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, total_items)
        
        page_courses = self.filtered_courses[start_idx:end_idx]

        # 如果找不到資料
        if not page_courses:
            lbl = ctk.CTkLabel(self.list_frame, text="找不到符合條件的課程。", text_color="gray")
            lbl.pack(pady=20)
            self.course_widgets.append(lbl)
            self.lbl_page.configure(text=f"第 {self.current_page} / {total_pages} 頁 (共 {total_items} 筆)")
            self.btn_select_all.configure(state="normal")
            self.btn_clear_all.configure(state="normal")
            return

        # 啟動無限滾動載入
        self._page_courses_total = len(page_courses)
        self._courses_to_draw_queue = page_courses[:]
        self.draw_next_batch()

    def draw_next_batch(self):
        if not self._courses_to_draw_queue:
            return

        batch_size = 20  # 降低單次拔取量 (讓主執行緒不會被單次長迴圈卡住)
        batch = self._courses_to_draw_queue[:batch_size]
        self._courses_to_draw_queue = self._courses_to_draw_queue[batch_size:]
        
        for c in batch:
            v = ctk.StringVar(value="on" if c['id'] in self.checked_course_ids else "off")
            self.checkbox_vars[c['id']] = v

            # 美化 CheckBox 色彩與設定
            color = "#ff4444" if c['category'] == "必修" else "#00C851"
            
            grade_info = ""
            if hasattr(self, 'course_best_grades') and c['name'] in self.course_best_grades:
                if c['name'] in self.passed_course_names:
                    grade_info = "  |  🏆"
                else:
                    grade_info = "  |  ❌"
            
            def make_cmd(c_id=c['id'], var=v):
                self.toggle_course(c_id, var.get())

            chk = ctk.CTkCheckBox(
                self.list_frame, 
                text=f"【{c['category']}】 {c['name']}  —  {c['credits']} 學分  |  👨‍🏫 {c['teachers']}{grade_info}",
                variable=v,
                onvalue="on",
                offvalue="off",
                command=make_cmd,
                text_color="gray90",
                font=self.f_body,
                border_width=2,
                border_color=color,
                fg_color=color,
                hover_color=color
            )
            chk.pack(anchor="w", padx=15, pady=8)
            self.course_widgets.append(chk)

        total_items = len(self.filtered_courses)
        total_pages = math.ceil(total_items / self.items_per_page) if total_items > 0 else 1
        drawn_count = self._page_courses_total - len(self._courses_to_draw_queue)

        if self._courses_to_draw_queue:
            self.lbl_page.configure(text=f"第 {self.current_page} / {total_pages} 頁 (向下滾動顯示... {drawn_count}/{self._page_courses_total} 筆)")
        else:
            self.lbl_page.configure(text=f"第 {self.current_page} / {total_pages} 頁 (共 {total_items} 筆)")
            self.btn_select_all.configure(state="normal")
            self.btn_clear_all.configure(state="normal")
            self.btn_prev.configure(state="normal" if self.current_page > 1 else "disabled")
            self.btn_next.configure(state="normal" if self.current_page < total_pages else "disabled")

    def toggle_course(self, c_id, val):
        if val == "on":
            self.checked_course_ids.add(c_id)
        else:
            self.checked_course_ids.discard(c_id)

    def go_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.render_page()

    def go_next_page(self):
        self.current_page += 1
        self.render_page()

    def select_all_page(self):
        for c_id, var in self.checkbox_vars.items():
            var.set("on")
            self.checked_course_ids.add(c_id)

    def clear_all_page(self):
        for c_id, var in self.checkbox_vars.items():
            var.set("off")
            self.checked_course_ids.discard(c_id)

    def do_graduation_check(self):
        if not self.checked_course_ids:
            messagebox.showwarning("警告", "您尚未勾選任何課程！")
            return

        sys_rule = self.sys_rule_var.get()
        gen_req = 12
        if "114" in sys_rule:
            gen_req = 10
        elif "二年制" in sys_rule:
            gen_req = 6

        total_req = 128
        obligatory_req = 80 - gen_req  # 將原必修目標扣除通識
        elective_req = 48
        
        dep = self.department_var.get()
        reqs = {}
        if dep != '通用':
            try:
                script_dir = os.path.dirname(os.path.abspath(__file__))
                json_path = os.path.join(script_dir, "department_reqs.json")
                with open(json_path, "r", encoding="utf-8") as f:
                    dep_reqs = json.load(f)
                    if dep in dep_reqs:
                        reqs = dep_reqs[dep]
                        total_req = reqs.get("total", 128)
                        # 如果有通識扣除，依舊套用
                        obligatory_req = reqs.get("obligatory", 80) - gen_req
                        elective_req = reqs.get("elective", 48)
            except Exception as e:
                print(f"Failed to load department reqs: {e}")
        
        sum_total = sum_obligatory = sum_elective = sum_general = 0
        pe_count = 0
        taken_domains = {"人文與藝術": 0, "自然與科技": 0, "社會科學": 0, "永續素養": 0}
        
        # 統計勾選的學分數，避免同名課程重複計算
        counted_course_names = set()
        for c_id in self.checked_course_ids:
            # 在 all_courses 找這筆資料
            course = next((c for c in self.all_courses if c['id'] == c_id), None)
            if course:
                if course['name'] not in counted_course_names:
                    sum_total += course['credits']
                    if course['category'] == '通識':
                        sum_general += course['credits']
                        dom = self.categorize_domain(course['name'])
                        taken_domains[dom] += course['credits']
                    elif course['category'] == '必修':
                        sum_obligatory += course['credits']
                    else:
                        sum_elective += course['credits']
                        
                    pe_keywords = ['體育', '網球', '棒球', '足球', '羽球', '體適能', '體式能', '籃球', '排球', '桌球', '高爾夫', '游泳', '撞球', '保齡球', '舞蹈', '柔道', '跆拳道', '太極拳', '武術', '田徑', '飛盤', '軟網', '壘球', '扯鈴', '瑜珈', '木球', '皮拉提斯', '飛輪']
                    if any(kw in course['name'] for kw in pe_keywords):
                        pe_count += 1
                        
                    counted_course_names.add(course['name'])

        # 更新進度條與數值
        self.lbl_total_prog.configure(text=f"🎯 總學分進度: {sum_total} / {total_req}")
        self.prog_total.set(min(1.0, sum_total / total_req))

        self.lbl_req_prog.configure(text=f"📚 必修學分: {sum_obligatory} / {obligatory_req}")
        self.prog_req.set(min(1.0, sum_obligatory / obligatory_req))

        self.lbl_elec_prog.configure(text=f"🧩 選修學分: {sum_elective} / {elective_req}")
        self.prog_elec.set(min(1.0, sum_elective / elective_req))

        self.lbl_gen_prog.configure(text=f"🌍 通識學分: {sum_general} / {gen_req}")
        self.prog_gen.set(min(1.0, sum_general / gen_req))

        if "114" in sys_rule:
            detail_text = (f"人文與藝術: {taken_domains['人文與藝術']}  |  自然與科技: {taken_domains['自然與科技']}\n"
                           f"社會科學: {taken_domains['社會科學']}  |  永續素養: {taken_domains['永續素養']}")
        else:
            detail_text = (f"人文與藝術: {taken_domains['人文與藝術']}  |  自然與科技: {taken_domains['自然與科技']}\n"
                           f"社會科學: {taken_domains['社會科學']}")
        self.lbl_gen_details.configure(text=detail_text)

        if pe_count >= 4:
            self.lbl_pe_prog.configure(text=f"🏃 體育: 已通過 ({pe_count} / 4 門)", text_color="#00C851")
        else:
            self.lbl_pe_prog.configure(text=f"🏃 體育: 缺 {4 - pe_count} 門", text_color="#ff4444")

        total_gap = max(0, total_req - sum_total)
        ob_gap = max(0, obligatory_req - sum_obligatory)
        el_gap = max(0, elective_req - sum_elective)
        gen_gap = max(0, gen_req - sum_general)
        
        # 檢查通識細項是否滿足
        domain_gaps = {}
        if "114" in sys_rule:
            for d in ["人文與藝術", "自然與科技", "社會科學", "永續素養"]:
                domain_gaps[d] = max(0, 2 - taken_domains.get(d, 0))
            total_specific_req = sum(domain_gaps.values())
            free_gap = max(0, gen_gap - total_specific_req)
            if free_gap > 0:
                domain_gaps["任一通識"] = free_gap
        elif "二年制" in sys_rule:
            for d in ["人文與藝術", "自然與科技", "社會科學"]:
                domain_gaps[d] = max(0, 2 - taken_domains.get(d, 0))
        else: # 113含以前
            for d in ["人文與藝術", "自然與科技", "社會科學"]:
                domain_gaps[d] = max(0, 4 - taken_domains.get(d, 0))
                
        gen_details_satisfied = (sum(domain_gaps.values()) == 0)
        
        # 判斷是否缺少各系指定的必修課程
        req_courses = reqs.get("required_courses", [])
        taken_course_names = {c['name'] for c in self.all_courses if c['id'] in self.checked_course_ids}
        
        missing_req_courses = []
        for rc in req_courses:
            found = False
            for tc in taken_course_names:
                if rc in tc or tc in rc:
                    found = True
                    break
            if not found:
                missing_req_courses.append(rc)
                
        # 從資料庫抓取系統官方判定未過的必修/校定課
        sys_missing_official = []
        try:
            conn, cursor = get_db_connection()
            if cursor:
                cursor.execute("SELECT course_name FROM Graduation_Check WHERE category IN ('院系必修', '全人/校定') AND grade IN ('尚未修課', '未評定成績', '0')")
                for row in cursor.fetchall():
                    req_name = row[0]
                    if "通識領域" in req_name:
                        continue
                    
                    # 檢查使用者是否已經在 GUI 中勾選了這門課 (模擬已修畢)
                    found_in_checked = False
                    for tc in taken_course_names:
                        if req_name == tc or req_name in tc or tc in req_name:
                            found_in_checked = True
                            break
                    
                    if not found_in_checked:
                        sys_missing_official.append(req_name)
        except:
            pass

        sys_missing_count = len(sys_missing_official)

        missing_course_text = ""
        if sys_missing_count > 0:
            missing_course_text = f"\n⚠️ 系統檢核有 {sys_missing_count} 門必修/校定尚未完成 (詳見推薦清單)"
        else:
            missing_course_text = "\n✅ 系統檢核必修與校定已全部完成"

        if total_gap == 0 and ob_gap == 0 and el_gap == 0 and gen_gap == 0 and pe_count >= 4 and sys_missing_count == 0 and gen_details_satisfied:
            self.lbl_status.configure(text=f"🎉 恭喜！您已滿足所有學分要求！{missing_course_text}", text_color="#00C851")
        else:
            pe_gap_text = f" / 體育缺 {4 - pe_count} 門" if pe_count < 4 else ""
            gen_detail_gap_text = ""
            if gen_gap == 0 and not gen_details_satisfied:
                gen_detail_gap_text = "(細項未滿)"
            self.lbl_status.configure(text=f"⚠️ 缺口: 必修缺 {ob_gap}  /  選修缺 {el_gap}  /  通識缺 {gen_gap}{gen_detail_gap_text}{pe_gap_text}{missing_course_text}", text_color="#ff4444")

        # 產生推薦修課清單
        raw_text = reqs.get("raw_text", "")
        self.generate_recommendations(ob_gap, el_gap, gen_gap, taken_domains, missing_req_courses, raw_text)
        
        # 更新額外門檻顯示
        self.update_additional_threshold()
        
        # 啟用 PDF 匯出按鈕
        self.btn_export_pdf.configure(state="normal")
        
        # 自動跳轉 Tab (需對應正確含 Emoji 的標籤名稱)
        self.tabview.set("📊 畢業查核結果")

    def update_additional_threshold(self):
        dep = self.department_var.get()
        # 取得不含 "-" 或 "(" 的系所核心名稱
        dep_base = dep.split('-')[0].split('(')[0].split('（')[0].strip()
        is_dep_ext = "進修" in dep
        
        threshold_text = "無額外門檻設定。"
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        md_path = os.path.join(script_dir, "額外門檻.md")
        if os.path.exists(md_path):
            try:
                import re
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                rows = re.findall(r'<tr[^>]*>.*?</tr>', content, re.IGNORECASE | re.DOTALL)
                for row in rows:
                    tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.IGNORECASE | re.DOTALL)
                    if not tds:
                        continue
                        
                    def clean_html(raw_html):
                        return re.sub(r'<.*?>', '', raw_html).strip()
                        
                    first_td = clean_html(tds[0])
                    is_td_ext = "進修" in first_td
                    
                    # 模糊比對：系所核心名稱有交集，且進修部屬性一致
                    if (dep_base in first_td or first_td in dep_base) and (is_dep_ext == is_td_ext):
                        cols = [clean_html(td) for td in tds]
                        
                        out = []
                        if len(cols) > 0:
                            out.append(f"🎯 系所：{cols[0]}")
                        
                        has_threshold = False
                        if len(cols) > 4 and cols[4] and cols[4] not in ['-', '']:
                            out.append(f"🗣️ 外語門檻：{cols[4]}")
                            has_threshold = True
                        if len(cols) > 5 and cols[5] and cols[5] not in ['-', '']:
                            out.append(f"📌 其他門檻：{cols[5]}")
                            has_threshold = True
                        if len(cols) > 6 and cols[6] and cols[6] not in ['-', '']:
                            out.append(f"📋 附加規定：{cols[6]}")
                            has_threshold = True
                            
                        if not has_threshold:
                            out.append("✅ 目前系統資料顯示無特殊外語或額外畢業門檻。")
                            
                        threshold_text = '\n'.join(out)
                        break
                        
            except Exception as e:
                threshold_text = f"讀取額外門檻檔案失敗: {e}"
        
        self.txt_threshold.configure(state="normal")
        self.txt_threshold.delete("0.0", "end")
        self.txt_threshold.insert("0.0", threshold_text)
        self.txt_threshold.configure(state="disabled")

    def categorize_domain(self, name):
        sys_rule = self.sys_rule_var.get()
        if "114" in sys_rule:
            sustainable_courses = [
                '生死學', '社區發展與生活', '環境生物概論', '中國后妃政治', '綠能科技',
                '環保、能源與生命科學', '臺灣自然生態與人文療癒', '環境藝術與生活',
                '人文地理學', '婦女研究', '人與環境', '婦女與歷史', '生態文學', '節慶觀光',
                '發展傳播', '全球化與永續發展', '看不見的世界：微生物與生活的秘密',
                '餐桌上的科學：瞭解食品安全與健康', '醱酵秘訣：如何利用微生物打造健康與風味',
                '國際關係', '環境保護', '全球化下的文化發展', '唐宋以來婦女文化與生活',
                '地球科學與人', '動物健康與動物福祉'
            ]
            if any(sc in name for sc in sustainable_courses):
                return "永續素養"
                
        domain_keywords = {
            "人文與藝術": ['文學', '哲學', '聽覺', '視覺', '表演', '生活藝術', '藝術', '歷史', '文化', '音樂', '中世紀', '思想', '唐宋', '倫理', '論'],
            "自然與科技": ['醫學', '自然', '資訊', '科技', '民生', '地球', '電腦', '程式', '生態', '健康', '癌症', '診斷', '人體', '應用', '數位'],
            "社會科學": ['管理', '教育', '心理', '社會', '宗教', '政治', '經濟', '法律', '傳播', '國際', '發展', '外交', '關係'],
            "永續素養": ['永續', '風險', '多元', 'SDGs']
        }
        for domain, kws in domain_keywords.items():
            if any(kw in name for kw in kws):
                return domain
        return "人文與藝術"

    def generate_recommendations(self, ob_gap, el_gap, gen_gap, taken_domains=None, missing_req_courses=None, raw_text=""):
        orig_ob_gap = ob_gap
        orig_el_gap = el_gap
        orig_gen_gap = gen_gap
        
        if missing_req_courses is None: missing_req_courses = []
        
        # 正確清空舊推薦
        for w in self.rec_widgets:
            try:
                w.destroy()
            except:
                pass
        self.rec_widgets.clear()
        self.current_recommendations = []
            
        if ob_gap <= 0 and el_gap <= 0 and gen_gap <= 0 and not missing_req_courses:
            lbl = ctk.CTkLabel(self.rec_scroll, text="學分與必修皆已滿，無需推薦修課！", text_color="gray")
            lbl.pack(pady=20)
            self.rec_widgets.append(lbl)
            return

        conn, cursor = get_db_connection()
        if not conn: return

        try:
            # 準備已修課的名稱，推薦時避開
            taken_names = [c['name'] for c in self.all_courses if c['id'] in self.checked_course_ids]
            
            # --- 計算通識各領域的滿足狀況 ---
            if taken_domains is None:
                taken_general = [c for c in self.all_courses if c['id'] in self.checked_course_ids and c['category'] == '通識']
                taken_domains = {"人文與藝術": 0, "自然與科技": 0, "社會科學": 0, "永續素養": 0, "任一通識": 0}
                for tc in taken_general:
                    dom = self.categorize_domain(tc['name'])
                    taken_domains[dom] += tc['credits']
            
            # 確保有任一通識的鍵值
            if "任一通識" not in taken_domains:
                taken_domains["任一通識"] = 0

            # 計算各領域通識缺口
            domain_gaps = {}
            sys_rule = self.sys_rule_var.get()
            if "114" in sys_rule:
                for d in ["人文與藝術", "自然與科技", "社會科學", "永續素養"]:
                    domain_gaps[d] = max(0, 2 - taken_domains[d])
                total_specific_req = sum(domain_gaps.values())
                free_gap = max(0, gen_gap - total_specific_req)
                if free_gap > 0:
                    domain_gaps["任一通識"] = free_gap
            elif "二年制" in sys_rule:
                for d in ["人文與藝術", "自然與科技", "社會科學"]:
                    domain_gaps[d] = max(0, 2 - taken_domains[d])
            else: # 113含以前
                for d in ["人文與藝術", "自然與科技", "社會科學"]:
                    domain_gaps[d] = max(0, 4 - taken_domains[d])

            # --- 取出並過濾候選清單 --- 
            cursor.execute("SELECT course_name, credits, category, GROUP_CONCAT(DISTINCT semester) FROM FJU_Courses_Scraped WHERE credits > 0 GROUP BY course_name")
            candidates = []
            general_candidates = []
            for row in cursor.fetchall():
                n, cr, cat, sems = row
                if n not in taken_names:
                    cand = {"name": n, "credits": cr, "category": cat, "semesters": sems}
                    if cat == "通識":
                        cand["domain"] = self.categorize_domain(n)
                        general_candidates.append(cand)
                    candidates.append(cand)

            # 計算優先度排序，優先推薦有出現在畢業門檻.md裡的課程
            def sort_key(c):
                is_priority = c["name"] in raw_text
                return (0 if is_priority else 1, len(c["name"]))

            candidates.sort(key=sort_key)
            general_candidates.sort(key=sort_key)

            # 準備系所前綴
            dept_full = self.department_var.get()
            dept_base = dept_full.split("-")[0]
            dept_mapping = {
                "資訊管理學系": "資管", "中國文學系": "中文", "英國語文學系": "英文",
                "日本語文學系": "日文", "企業管理學系": "企管", "資訊工程學系": "資工",
                "財務金融學系": "財金", "統計資訊學系": "統資", "歷史學系": "歷史",
                "哲學系": "哲學", "物理學系": "物理", "化學系": "化學",
                "數學系": "數學", "生命科學系": "生科", "心理學系": "心理",
                "護理學系": "護理", "公共衛生學系": "公衛", "臨床心理學系": "臨心",
                "職能治療學系": "職治", "呼吸治療學系": "呼吸", "音樂學系": "音樂",
                "應用美術學系": "應美", "景觀設計學系": "景觀", "食品科學系": "食科",
                "營養科學系": "營養", "電機工程學系": "電機", "宗教學系": "宗教",
                "醫學系": "醫學", "法國語文學系": "法文", "西班牙語文學系": "西文",
                "義大利語文學系": "義文", "德國語文學系": "德語", "社會學系": "社會",
                "社會工作學系": "社工", "經濟學系": "經濟", "法律學系": "法律",
                "財經法律學系": "財法", "會計學系": "會計"
            }
            dept_prefix = dept_mapping.get(dept_base, dept_base[:2])
            
            # 從 FJU_Courses_Scraped 取得該系所開的選修與必修課
            dept_el_cands = []
            dept_ob_cands = []
            cursor.execute("SELECT course_name, credits, category, GROUP_CONCAT(DISTINCT semester) FROM FJU_Courses_Scraped WHERE department LIKE %s AND category IN ('必修', '選修') GROUP BY course_name", (f"{dept_prefix}%",))
            for row in cursor.fetchall():
                n, cr, cat, sems = row
                if n not in taken_names:
                    if cat == '選修':
                        dept_el_cands.append({"name": n, "credits": cr, "category": "選修", "semesters": sems})
                    elif cat == '必修':
                        dept_ob_cands.append({"name": n, "credits": cr, "category": "必修", "semesters": sems})

            # 從 FJU_Graduation_Check 抓取系統判定未過的必修與校定課
            sys_ob_cands = []
            try:
                cursor.execute("SELECT requirement_name FROM FJU_Graduation_Check WHERE category IN ('院系必修', '全人/校定') AND grade IN ('尚未修課', '未評定成績')")
                sys_missing_names = [row[0] for row in cursor.fetchall()]
                
                for missing_name in sys_missing_names:
                    # 排除不具體的通識大類名稱
                    if "通識領域" in missing_name:
                        continue
                    
                    # 檢查是否已在畫面上打勾 (模擬已修畢)
                    if any(missing_name == tc or missing_name in tc or tc in missing_name for tc in taken_names):
                        continue
                        
                    found_cr = 2 # 預設2學分
                    found_sems = "依開課為主"
                    for c in candidates + general_candidates:
                        if c["name"] == missing_name or missing_name in c["name"]:
                            found_cr = c["credits"]
                            found_sems = c.get("semesters", "")
                            break
                    sys_ob_cands.append({"name": missing_name, "credits": found_cr, "category": "必修", "semesters": found_sems})
                
                # 直接替換掉原本靠系所代碼盲猜的必修清單，改用官方系統認證的缺漏清單
                if sys_ob_cands:
                    dept_ob_cands = sys_ob_cands
            except:
                pass # 如果表不存在或結構改變，忽略錯誤

            # 加入系所指定必修推薦 (來自 FJU_Courses_Scraped department 查詢)
            if dept_ob_cands:
                used_ob = self.add_rec_section("【系所指定必修推薦】", dept_ob_cands, "必修", 999, "#dc3545", self.current_recommendations)
                if used_ob: ob_gap -= used_ob

            # 加入系所指定選修推薦 (來自 FJU_Courses_Scraped department 查詢)
            if dept_el_cands:
                used_el = self.add_rec_section("【系所選修推薦】", dept_el_cands, "選修", el_gap, "#00C851", self.current_recommendations)
                if used_el: el_gap -= used_el

            # 開始配置缺漏 (門檻指定)
            if missing_req_courses:
                missing_unknown = []
                for mrc in missing_req_courses:
                    # 如果這門門檻指定的課不在 dept_ob_cands 和 dept_el_cands 裡，就找看看全校有沒有開
                    if not any(c["name"] == mrc or mrc in c["name"] for c in dept_ob_cands + dept_el_cands):
                        found_cr = None
                        found_cat = None
                        found_sems = ""
                        for c in candidates:
                            if c["name"] == mrc or mrc in c["name"]:
                                found_cr = c["credits"]
                                found_cat = c["category"]
                                found_sems = c.get("semesters", "")
                                break
                        if found_cr:
                            missing_unknown.append({"name": mrc, "credits": found_cr, "category": found_cat, "semesters": found_sems})
                        else:
                            missing_unknown.append({"name": mrc, "credits": 2, "category": "未知(本學期未開課或無法判定)", "semesters": ""})
                
                if missing_unknown:
                    self.add_rec_section("【其他門檻指定課程 (非本系或未開課)】", missing_unknown, "未知/其他", 999, "gray", self.current_recommendations)
                
                # 過濾掉已經在其他門檻推薦過的課程，避免重複推薦
                candidates = [c for c in candidates if c["name"] not in missing_req_courses and not any(mrc in c["name"] for mrc in missing_req_courses)]

            # 從 candidates 中過濾掉已經出現在系所指定推薦的課程
            dept_course_names = {c["name"] for c in dept_ob_cands + dept_el_cands}
            candidates = [c for c in candidates if c["name"] not in dept_course_names]

            # (已移除隨機的「必修學分推薦」，改由官方系統缺漏清單完全取代)
            if el_gap > 0:
                self.add_rec_section("【選修學分推薦】", candidates, "選修", el_gap, "#28a745", self.current_recommendations)

            # 配置通識領域缺漏
            if gen_gap > 0:
                for d, req in domain_gaps.items():
                    if req > 0:
                        if d == "任一通識":
                            self.add_rec_section("【任選通識領域】", general_candidates, "通識", req, "#9933cc", self.current_recommendations)
                        else:
                            # 過濾只推薦該特定領域的課
                            spec_cands = [c for c in general_candidates if c["domain"] == d]
                            self.add_rec_section(f"【{d}通識】", spec_cands, "通識", req, "#9933cc", self.current_recommendations)
                            
            # 計算剩餘學期數
            s1_must = 0
            s2_must = 0
            for c in dept_ob_cands:
                if c.get("semesters") == "上學期":
                    s1_must += c["credits"]
                elif c.get("semesters") == "下學期":
                    s2_must += c["credits"]
                    
            if missing_req_courses and 'missing_unknown' in locals():
                for c in missing_unknown:
                    if c.get("semesters") == "上學期":
                        s1_must += c["credits"]
                    elif c.get("semesters") == "下學期":
                        s2_must += c["credits"]
                        
            total_gap = orig_ob_gap + orig_el_gap + orig_gen_gap
            flex = max(0, total_gap - s1_must - s2_must)
            
            def sim_semesters(start_s1):
                sem = 0
                s1 = s1_must
                s2 = s2_must
                f = flex
                is_s1 = start_s1
                while s1 > 0 or s2 > 0 or f > 0:
                    sem += 1
                    cap = 25
                    if is_s1:
                        take = min(s1, cap)
                        s1 -= take
                        cap -= take
                    else:
                        take = min(s2, cap)
                        s2 -= take
                        cap -= take
                    take_f = min(f, cap)
                    f -= take_f
                    is_s1 = not is_s1
                return sem
                
            # 固定從「上學期」開始模擬，真實反映必須「空等學期」的情況
            min_semesters = sim_semesters(True)
            if min_semesters > 0:
                self.lbl_semesters.configure(text=f"🎓 預估最快畢業：還需 {min_semesters} 學期 (以每學期最高 25 學分估算)", text_color="#33b5e5")
            else:
                self.lbl_semesters.configure(text=f"🎓 預估最快畢業：已達標 (0 學期)", text_color="#00C851")

        except Exception as e:
            lbl = ctk.CTkLabel(self.rec_scroll, text=f"產生推薦發生錯誤: {e}", text_color="red")
            lbl.pack()
            self.rec_widgets.append(lbl)
        finally:
            cursor.close()
            conn.close()

    def add_rec_section(self, title, candidates, category, target_gap, color, rec_list=None):
        if target_gap == 999:
            title_text = title
        else:
            title_text = f"{title} 缺 {target_gap} 學分"
            
        lbl_title = ctk.CTkLabel(self.rec_scroll, text=title_text, font=self.f_header, text_color=color)
        lbl_title.pack(anchor="w", pady=(15, 10), padx=5)
        self.rec_widgets.append(lbl_title)

        accumulated = 0
        for c in candidates:
            if c["category"] == category:
                # 替推薦課程建立小卡片感
                card = ctk.CTkFrame(self.rec_scroll, corner_radius=8, fg_color="gray20")
                card.pack(fill="x", padx=10, pady=4)
                
                sems = c.get("semesters", "")
                sem_text = f" [{sems}]" if sems else ""
                
                lbl = ctk.CTkLabel(card, text=f"➤ {c['name']}{sem_text} ", font=self.f_body, text_color="gray90")
                lbl.pack(side="left", padx=10, pady=8)
                
                lbl_cr = ctk.CTkLabel(card, text=f"{c['credits']} 學分", font=self.f_small, text_color=color)
                lbl_cr.pack(side="right", padx=10, pady=8)
                
                self.rec_widgets.append(card)
                if rec_list is not None:
                    rec_list.append({"name": c['name'], "credits": c['credits'], "category": category, "semesters": sems})
                
                accumulated += c["credits"]
                if accumulated >= target_gap:
                    break
        
        if target_gap == 999:
            info_text = "※ 以上為您漏勾選的系所指定必修課程。"
        else:
            info_text = f"※ 以上推薦合計提供 {accumulated} 學分可補足此項要求。"
            
        lbl_info = ctk.CTkLabel(self.rec_scroll, text=info_text, text_color="gray60", font=self.f_small)
        lbl_info.pack(anchor="w", padx=10, pady=(5, 20))
        self.rec_widgets.append(lbl_info)
        return accumulated

    def export_to_pdf(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="儲存畢業查核報告",
            initialfile="輔大畢業查核報告.pdf"
        )
        if not filepath:
            return
            
        try:
            def clean_text(text):
                # 移除 PDF 無法顯示的常見 Emoji (包含 \ufe0f 變體選擇器)
                emojis = ['🎓', '📊', '🎯', '📚', '🧩', '🌍', '🏃', '⚠', '\ufe0f', '📌', '✅', '❌', '💡', '🔹', '🗣', '📋']
                for e in emojis:
                    text = text.replace(e, '')
                return text.strip()

            pdf = FPDF()
            pdf.add_page()
            
            os_name = platform.system()
            font_path = ""
            if os_name == "Windows":
                font_path = "C:/Windows/Fonts/msjh.ttc"
            elif os_name == "Darwin":
                font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
                
            has_tc_font = False
            if os.path.exists(font_path):
                pdf.add_font('tc_font', '', font_path, uni=True)
                pdf.set_font('tc_font', '', 18)
                has_tc_font = True
            else:
                pdf.set_font("Arial", size=18)
                
            pdf.cell(190, 15, txt=clean_text("🎓 輔大畢業學分查核報告"), ln=True, align="C")
            
            pdf.set_font('tc_font', '', 11) if has_tc_font else pdf.set_font("Arial", size=11)
            pdf.cell(190, 8, txt=f"產生時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="R")
            
            # 分隔線
            pdf.set_line_width(0.5)
            pdf.line(10, 40, 200, 40)
            
            # --- 學分狀態 ---
            pdf.ln(15)
            pdf.set_font('tc_font', '', 14) if has_tc_font else None
            pdf.set_text_color(0, 102, 204)  # 藍色標題
            pdf.cell(190, 10, txt=clean_text("📊 【 當前學分狀態 】"), ln=True)
            
            pdf.set_text_color(0, 0, 0) # 恢復黑色
            pdf.set_font('tc_font', '', 12) if has_tc_font else None
            pdf.cell(190, 8, txt=clean_text(self.lbl_total_prog.cget("text")), ln=True)
            pdf.cell(190, 8, txt=clean_text(self.lbl_req_prog.cget("text")), ln=True)
            pdf.cell(190, 8, txt=clean_text(self.lbl_elec_prog.cget("text")), ln=True)
            pdf.cell(190, 8, txt=clean_text(self.lbl_gen_prog.cget("text")), ln=True)
            
            pdf.set_font('tc_font', '', 10) if has_tc_font else None
            pdf.set_text_color(100, 100, 100)
            for d_line in self.lbl_gen_details.cget("text").split('\n'):
                pdf.cell(190, 6, txt=clean_text("      " + d_line), ln=True)
            
            pdf.set_font('tc_font', '', 12) if has_tc_font else None
            pdf.set_text_color(0, 0, 0)
            pdf.cell(190, 8, txt=clean_text(self.lbl_pe_prog.cget("text")), ln=True)
            
            pdf.ln(5)
            # 處理帶有多行的狀態字串
            status_lines = self.lbl_status.cget("text").split('\n')
            for line in status_lines:
                pdf.cell(190, 8, clean_text(line), ln=True)
                
            # --- 預估最快畢業 ---
            pdf.ln(2)
            pdf.set_font('tc_font', '', 12) if has_tc_font else None
            pdf.set_text_color(0, 153, 204)
            pdf.cell(190, 8, clean_text(self.lbl_semesters.cget("text")), ln=True)
            pdf.set_text_color(0, 0, 0)
                
            # --- 插入額外門檻 ---
            pdf.ln(5)
            pdf.set_font('tc_font', '', 14) if has_tc_font else None
            pdf.set_text_color(0, 102, 204)  # 藍色標題
            pdf.cell(190, 10, txt=clean_text("【 額外畢業門檻 】"), ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('tc_font', '', 10) if has_tc_font else None
            
            threshold_text = self.txt_threshold.get("0.0", "end").strip()
            # 移除在 PDF 中無法顯示的 Emoji
            threshold_text = clean_text(threshold_text)
            
            # 直接將包含換行符號的完整字串傳給 multi_cell 處理，避免 X 座標異常偏移
            # 使用位置參數以避免 fpdf/fpdf2 不同版本的 txt/text 警告
            pdf.multi_cell(190, 6, threshold_text, 0, 'L')
                
            pdf.ln(5)
            pdf.set_line_width(0.2)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            
            # --- 推薦課程 ---
            pdf.ln(10)
            pdf.set_font('tc_font', '', 14) if has_tc_font else None
            pdf.set_text_color(0, 153, 51)  # 綠色標題
            pdf.cell(190, 10, txt=clean_text("【 系統推薦修課清單 】"), ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('tc_font', '', 12) if has_tc_font else None
            
            if not self.current_recommendations:
                pdf.cell(190, 8, txt="學分已滿或無推薦課程。", ln=True)
            else:
                for rec in self.current_recommendations:
                    cat_tag = f"[{rec['category']}]"
                    sems = rec.get("semesters", "")
                    sem_tag = f" [{sems}]" if sems else ""
                    pdf.cell(190, 8, txt=clean_text(f"   - {cat_tag} {rec['name']}{sem_tag} - {rec['credits']} 學分"), ln=True)
            
            pdf.output(filepath)
            messagebox.showinfo("匯出成功", f"報告已成功儲存至：\n{filepath}")
        except Exception as e:
            messagebox.showerror("匯出錯誤", f"匯出 PDF 發生錯誤：\n{e}")

    def update_school_db(self):
        if not messagebox.askyesno("確認更新", "這將開啟自動化瀏覽器重新抓取輔大最新的課程清單與通識分類資料。\n\n過程可能需要 5 ~ 10 分鐘，期間請勿關閉主程式或彈出的瀏覽器視窗，確定要繼續嗎？"):
            return
            
        self.btn_update_db.configure(state="disabled", text="⏳ 正在擷取中...")
        self.btn_check.configure(state="disabled")
        
        # 建立進度視窗
        self.progress_win = ctk.CTkToplevel(self)
        self.progress_win.title("資料更新進度")
        self.progress_win.geometry("400x150")
        self.progress_win.transient(self) # 綁定在主視窗上
        self.progress_win.grab_set() # 鎖定主視窗 (強制停留)
        
        lbl = ctk.CTkLabel(self.progress_win, text="🚀 正在啟動爬蟲抓取資料\n請勿操作滑鼠或關閉視窗，這可能需要幾分鐘...", font=self.f_body)
        lbl.pack(pady=20)
        
        prog = ctk.CTkProgressBar(self.progress_win, mode="indeterminate", width=300, progress_color="#33b5e5")
        prog.pack(pady=10)
        prog.start()
        
        def run_scraper():
            try:
                # 使用 sys.executable 確保使用同一個虛擬環境中的 python
                # 執行主課程爬蟲 (先下學期重建資料表，再上學期補入)
                subprocess.run([sys.executable, "test_project/fju_scr_2.py"], check=True)
                subprocess.run([sys.executable, "test_project/fju_scr_1.py"], check=True)
                
                # 執行完成後，透過 after 回到主執行緒處理 UI
                self.after(0, self.on_update_success)
            except subprocess.CalledProcessError as e:
                self.after(0, lambda err=e: self.on_update_fail(err))
            except Exception as e:
                self.after(0, lambda err=e: self.on_update_fail(err))
                
        # 在背景執行緒中啟動，避免凍結 GUI
        threading.Thread(target=run_scraper, daemon=True).start()

    def on_update_success(self):
        if hasattr(self, 'progress_win') and self.progress_win.winfo_exists():
            self.progress_win.destroy()
        messagebox.showinfo("更新成功", "學校課程資料與通識分類已成功更新！\n系統即將為您重新載入資料。")
        self.btn_update_db.configure(state="normal", text="🔄 重新擷取學校資料")
        self.btn_check.configure(state="normal")
        self.load_data_from_db()

    def on_update_fail(self, error):
        if hasattr(self, 'progress_win') and self.progress_win.winfo_exists():
            self.progress_win.destroy()
        messagebox.showerror("更新失敗", f"執行爬蟲時發生錯誤：\n{error}")
        self.btn_update_db.configure(state="normal", text="🔄 重新擷取學校資料")
        self.btn_check.configure(state="normal")

class LoginWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🎓 輔大系統登入")
        self.geometry("450x620")
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.f_title = ("Helvetica", 28, "bold")
        self.f_body = ("Helvetica", 16)
        
        self.lbl_title = ctk.CTkLabel(self, text="🎓 輔大成績爬蟲登入", font=self.f_title)
        self.lbl_title.pack(pady=(50, 30))
        
        self.entry_account = ctk.CTkEntry(self, placeholder_text="請輸入學號 (帳號)", font=self.f_body, width=280, height=45)
        self.entry_account.pack(pady=15)
        
        self.entry_password = ctk.CTkEntry(self, placeholder_text="請輸入密碼", show="*", font=self.f_body, width=280, height=45)
        self.entry_password.pack(pady=15)
        
        # 嘗試讀取 account.txt 自動填寫帳號密碼
        try:
            account_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "account.txt")
            if os.path.exists(account_file):
                with open(account_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    import re
                    acc_match = re.search(r"帳號[：:]\s*(.+)", content)
                    pwd_match = re.search(r"密碼[：:]\s*(.+)", content)
                    if acc_match:
                        self.entry_account.insert(0, acc_match.group(1).strip())
                    if pwd_match:
                        self.entry_password.insert(0, pwd_match.group(1).strip())
        except Exception as e:
            print(f"讀取 account.txt 失敗: {e}")

        
        self.btn_run = ctk.CTkButton(self, text="🚀 開始更新資料", font=("Helvetica", 18, "bold"), width=280, height=50, command=self.start_scraping)
        self.btn_run.pack(pady=30)
        
        self.lbl_status = ctk.CTkLabel(self, text="請輸入您的輔大 SIS 系統帳號密碼", font=("Helvetica", 14), text_color="gray60")
        self.lbl_status.pack(pady=10)
        
        self.btn_skip = ctk.CTkButton(self, text="跳過更新，直接開啟查核系統", font=("Helvetica", 14), fg_color="transparent", border_width=1, text_color="gray80", hover_color="gray30", command=self.open_main_gui)
        self.btn_skip.pack(pady=10)

    def start_scraping(self):
        account = self.entry_account.get().strip()
        password = self.entry_password.get().strip()
        
        if not account or not password:
            messagebox.showwarning("警告", "請輸入帳號與密碼！")
            return
            
        os.environ['FJU_ACCOUNT'] = account
        os.environ['FJU_PASSWORD'] = password
        
        self.btn_run.configure(state="disabled")
        self.btn_skip.configure(state="disabled")
        self.entry_account.configure(state="disabled")
        self.entry_password.configure(state="disabled")
        
        self.lbl_status.configure(text="⏳ 正在背景啟動瀏覽器...", text_color="#33b5e5")
        
        threading.Thread(target=self.run_scripts_thread, daemon=True).start()
        
    def run_scripts_thread(self):
        python_exe = sys.executable
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        try:
            self.after(0, lambda: self.lbl_status.configure(text="⏳ [1/2] 正在執行 test1.py (個人成績)..."))
            proc1 = subprocess.run([python_exe, "test1.py"], cwd=script_dir)
            if proc1.returncode != 0:
                self.after(0, self.show_error, "test1.py 執行失敗", "請查看終端機輸出以了解錯誤原因。")
                return
                
            self.after(0, lambda: self.lbl_status.configure(text="⏳ [2/2] 正在執行 test2.py (畢業檢核表)..."))
            proc2 = subprocess.run([python_exe, "test2.py"], cwd=script_dir)
            if proc2.returncode != 0:
                self.after(0, self.show_error, "test2.py 執行失敗", "請查看終端機輸出以了解錯誤原因。")
                return
                
            self.after(0, lambda: self.lbl_status.configure(text="✅ 更新完成！正在開啟系統...", text_color="#00C851"))
            self.after(1000, self.open_main_gui)
            
        except Exception as e:
            self.after(0, self.show_error, "執行發生例外錯誤", str(e))
            
    def show_error(self, title, msg):
        messagebox.showerror(title, msg)
        self.btn_run.configure(state="normal")
        self.btn_skip.configure(state="normal")
        self.entry_account.configure(state="normal")
        self.entry_password.configure(state="normal")
        self.lbl_status.configure(text="❌ 執行失敗，請重試", text_color="#ff4444")
        
    def open_main_gui(self):
        self.destroy()
        app = GraduationGUI()
        app.mainloop()

if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
