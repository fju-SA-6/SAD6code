import customtkinter as ctk
import tkinter.messagebox as messagebox
from database import get_db_connection
import math

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

        self.search_entry = ctk.CTkEntry(self.filter_frame, placeholder_text="🔍 搜尋課程名稱...", font=self.f_body, height=40, border_width=1)
        self.search_entry.pack(side="left", padx=15, pady=15, expand=True, fill="x")
        self.search_entry.bind("<KeyRelease>", self.on_filter_change)

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
        self.lbl_elec_prog.pack(anchor="w", padx=30, pady=(15, 5))
        self.prog_elec = ctk.CTkProgressBar(self.res_stats_frame, height=20, corner_radius=10, progress_color="#00C851")
        self.prog_elec.set(0)
        self.prog_elec.pack(fill="x", padx=30, pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self.res_stats_frame, text="狀態：尚未查核", font=self.f_header, text_color="orange")
        self.lbl_status.pack(pady=30)

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
            # 1. 取得已過關之個人成績
            cursor.execute("SELECT course_name, grade FROM FJU_Personal_Grades")
            for row in cursor.fetchall():
                c_name, grade = row[0], row[1].strip() if row[1] else ""
                is_passed = False
                if grade.isdigit() and int(grade) >= 60:
                    is_passed = True
                elif grade not in ['不及格', '未通過', '停修', 'W', 'F', '']:
                    is_passed = True
                
                if is_passed:
                    self.passed_course_names.add(c_name)

            # 2. 取得所有課程資料
            sql = """
                SELECT id, course_name, credits, category, 
                       GROUP_CONCAT(DISTINCT semester) as semesters, 
                       GROUP_CONCAT(DISTINCT day_of_week) as days, 
                       GROUP_CONCAT(DISTINCT teacher SEPARATOR ', ') as teachers 
                FROM FJU_Courses 
                GROUP BY course_name 
                ORDER BY category, course_name
            """
            cursor.execute(sql)
            self.all_courses = []
            for row in cursor.fetchall():
                c_id, name, credits_v, category, sems, days, teachers = row
                
                # 自動勾選邏輯：若在已通過名單內，加入 checked_course_ids
                if name in self.passed_course_names:
                    self.checked_course_ids.add(str(c_id))

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
        sem_q = self.semester_var.get()
        day_q = self.day_var.get()

        self.filtered_courses = []
        for c in self.all_courses:
            match_name = search_q in c['name'].lower()
            match_sem = (sem_q == "所有學期" or sem_q in c['semesters'])
            match_day = (day_q == "所有星期" or day_q in c['days'])
            if match_name and match_sem and match_day:
                self.filtered_courses.append(c)
        
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
            
            def make_cmd(c_id=c['id'], var=v):
                return lambda: self.toggle_course(c_id, var.get())

            chk = ctk.CTkCheckBox(
                self.list_frame, 
                text=f"【{c['category']}】 {c['name']}  —  {c['credits']} 學分  |  👨‍🏫 {c['teachers']}",
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

        total_req = 128
        obligatory_req = 80
        elective_req = 48
        
        sum_total = sum_obligatory = sum_elective = 0
        
        # 統計勾選的學分數
        for c_id in self.checked_course_ids:
            # 在 all_courses 找這筆資料
            course = next((c for c in self.all_courses if c['id'] == c_id), None)
            if course:
                sum_total += course['credits']
                if course['category'] == '必修':
                    sum_obligatory += course['credits']
                else:
                    sum_elective += course['credits']

        # 更新進度條與數值
        self.lbl_total_prog.configure(text=f"🎯 總學分進度: {sum_total} / {total_req}")
        self.prog_total.set(min(1.0, sum_total / total_req))

        self.lbl_req_prog.configure(text=f"📚 必修學分: {sum_obligatory} / {obligatory_req}")
        self.prog_req.set(min(1.0, sum_obligatory / obligatory_req))

        self.lbl_elec_prog.configure(text=f"🧩 選修學分: {sum_elective} / {elective_req}")
        self.prog_elec.set(min(1.0, sum_elective / elective_req))

        total_gap = max(0, total_req - sum_total)
        ob_gap = max(0, obligatory_req - sum_obligatory)
        el_gap = max(0, elective_req - sum_elective)

        if total_gap == 0 and ob_gap == 0 and el_gap == 0:
            self.lbl_status.configure(text="🎉 恭喜！您已滿足所有畢業要求！", text_color="#00C851")
        else:
            self.lbl_status.configure(text=f"⚠️ 尚未滿足要求！ 總缺口: {total_gap}\n(必修缺: {ob_gap}  /  選修缺: {el_gap})", text_color="#ff4444")

        # 產生推薦修課清單
        self.generate_recommendations(ob_gap, el_gap)
        
        # 自動跳轉 Tab (需對應正確含 Emoji 的標籤名稱)
        self.tabview.set("📊 畢業查核結果")

    def generate_recommendations(self, ob_gap, el_gap):
        # 正確清空舊推薦
        for w in self.rec_widgets:
            try:
                w.destroy()
            except:
                pass
        self.rec_widgets.clear()
            
        if ob_gap == 0 and el_gap == 0:
            lbl = ctk.CTkLabel(self.rec_scroll, text="學分已滿，無需推薦修課！", text_color="gray")
            lbl.pack(pady=20)
            self.rec_widgets.append(lbl)
            return

        conn, cursor = get_db_connection()
        if not conn: return

        try:
            # 準備已修課的名稱，推薦時避開
            taken_names = [c['name'] for c in self.all_courses if c['id'] in self.checked_course_ids]
            
            # 從 graduation_db 找缺口 (優先推薦)
            priority_cases = []
            cursor.execute("SELECT requirement_name FROM FJU_Graduation_Check WHERE grade = '尚未修課'")
            for row in cursor.fetchall():
                req_name_clean = row[0].replace('通識領域', '').replace('領域', '')
                if '-' in req_name_clean:
                    req_name_clean = req_name_clean.split('-')[-1]
                if req_name_clean:
                    priority_cases.append(req_name_clean)

            # --- 取出並過濾候選清單 --- 
            cursor.execute("SELECT course_name, credits, category FROM FJU_Courses WHERE credits > 0 GROUP BY course_name")
            candidates = []
            for row in cursor.fetchall():
                n, cr, cat = row
                if n not in taken_names:
                    candidates.append({"name": n, "credits": cr, "category": cat})

            # 計算優先度排序
            def sort_key(c):
                # 如果名稱包含任何優先缺口關鍵字，排到最前 (-1)
                is_priority = any(p in c["name"] for p in priority_cases)
                return (0 if is_priority else 1, c["name"])

            candidates.sort(key=sort_key)

            # 開始配置缺漏
            if ob_gap > 0:
                self.add_rec_section("【必修推薦】", candidates, "必修", ob_gap, "#dc3545")
            
            if el_gap > 0:
                self.add_rec_section("【選修推薦】", candidates, "選修", el_gap, "#28a745")

        except Exception as e:
            lbl = ctk.CTkLabel(self.rec_scroll, text=f"產生推薦發生錯誤: {e}", text_color="red")
            lbl.pack()
            self.rec_widgets.append(lbl)
        finally:
            cursor.close()
            conn.close()

    def add_rec_section(self, title, candidates, category, target_gap, color):
        lbl_title = ctk.CTkLabel(self.rec_scroll, text=f"{title} 缺 {target_gap} 學分", font=self.f_header, text_color=color)
        lbl_title.pack(anchor="w", pady=(15, 10), padx=5)
        self.rec_widgets.append(lbl_title)

        accumulated = 0
        for c in candidates:
            if c["category"] == category:
                # 替推薦課程建立小卡片感
                card = ctk.CTkFrame(self.rec_scroll, corner_radius=8, fg_color="gray20")
                card.pack(fill="x", padx=10, pady=4)
                
                lbl = ctk.CTkLabel(card, text=f"➤ {c['name']} ", font=self.f_body, text_color="gray90")
                lbl.pack(side="left", padx=10, pady=8)
                
                lbl_cr = ctk.CTkLabel(card, text=f"{c['credits']} 學分", font=self.f_small, text_color=color)
                lbl_cr.pack(side="right", padx=10, pady=8)
                
                self.rec_widgets.append(card)
                accumulated += c["credits"]
                if accumulated >= target_gap:
                    break
        
        lbl_info = ctk.CTkLabel(self.rec_scroll, text=f"※ 以上推薦合計提供 {accumulated} 學分可補足此項要求。", text_color="gray60", font=self.f_small)
        lbl_info.pack(anchor="w", padx=10, pady=(5, 20))
        self.rec_widgets.append(lbl_info)


if __name__ == "__main__":
    app = GraduationGUI()
    app.mainloop()
