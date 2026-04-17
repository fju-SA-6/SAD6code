import customtkinter as ctk
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
from database import get_db_connection
import math
import platform
import os
import datetime

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from fpdf import FPDF

# 設定 matplotlib 全域中文字型
os_name = platform.system()
if os_name == "Windows":
    plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
elif os_name == "Darwin":
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang HK', 'Heiti TC']
else:
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei']
plt.rcParams['axes.unicode_minus'] = False

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

        self.sys_rule_var = ctk.StringVar(value="113(含)以前學士班")
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
        self.prog_gen.pack(fill="x", padx=30, pady=(0, 20))

        self.lbl_status = ctk.CTkLabel(self.res_stats_frame, text="狀態：尚未查核", font=self.f_header, text_color="orange")
        self.lbl_status.pack(pady=(5, 5))

        # 下方加入匯出 PDF 按鈕 (優先使用底端空間以防被圖表擠出畫面)
        self.btn_export_pdf = ctk.CTkButton(
            self.res_stats_frame, text="📄 匯出查核結果成 PDF", font=self.f_btn, 
            height=50, fg_color="#ff8800", hover_color="#cc6600",
            command=self.export_to_pdf, state="disabled"
        )
        self.btn_export_pdf.pack(side="bottom", fill="x", padx=30, pady=(10, 25))

        # 中間圓環圖區域 (排在按鈕前面，利用 expand 搶佔剩餘空間)
        self.chart_frame = ctk.CTkFrame(self.res_stats_frame, fg_color="transparent")
        self.chart_frame.pack(side="bottom", fill="both", expand=True, padx=20, pady=5)
        
        self.fig = Figure(figsize=(5, 4), facecolor='#2B2B2B', tight_layout=True)
        self.ax = self.fig.add_subplot(111)
        self.ax.axis('off')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

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

        sys_rule = self.sys_rule_var.get()
        gen_req = 12
        if "114" in sys_rule:
            gen_req = 10
        elif "二年制" in sys_rule:
            gen_req = 6

        total_req = 128
        obligatory_req = 80 - gen_req  # 將原必修目標扣除通識
        elective_req = 48
        
        sum_total = sum_obligatory = sum_elective = sum_general = 0
        
        # 統計勾選的學分數
        for c_id in self.checked_course_ids:
            # 在 all_courses 找這筆資料
            course = next((c for c in self.all_courses if c['id'] == c_id), None)
            if course:
                sum_total += course['credits']
                if course['category'] == '通識':
                    sum_general += course['credits']
                elif course['category'] == '必修':
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

        self.lbl_gen_prog.configure(text=f"🌍 通識學分: {sum_general} / {gen_req}")
        self.prog_gen.set(min(1.0, sum_general / gen_req))

        total_gap = max(0, total_req - sum_total)
        ob_gap = max(0, obligatory_req - sum_obligatory)
        el_gap = max(0, elective_req - sum_elective)
        gen_gap = max(0, gen_req - sum_general)

        if total_gap == 0 and ob_gap == 0 and el_gap == 0 and gen_gap == 0:
            self.lbl_status.configure(text="🎉 恭喜！您已滿足所有畢業要求！", text_color="#00C851")
        else:
            self.lbl_status.configure(text=f"⚠️ 缺口: 必修缺 {ob_gap}  /  選修缺 {el_gap}  /  通識缺 {gen_gap}", text_color="#ff4444")

        # 產生推薦修課清單
        self.generate_recommendations(ob_gap, el_gap, gen_gap)
        
        # 更新分析圖表
        self.update_chart(sum_obligatory, ob_gap, sum_elective, el_gap, sum_general, gen_gap)
        
        # 啟用 PDF 匯出按鈕
        self.btn_export_pdf.configure(state="normal")
        
        # 自動跳轉 Tab (需對應正確含 Emoji 的標籤名稱)
        self.tabview.set("📊 畢業查核結果")

    def update_chart(self, ob_done, ob_gap, el_done, el_gap, gen_done, gen_gap):
        self.ax.clear()
        
        labels = []
        sizes = []
        colors = []
        
        if ob_done > 0:
            labels.append(f'已修必修\n({ob_done})')
            sizes.append(ob_done)
            colors.append('#ff4444')
        if ob_gap > 0:
            labels.append(f'缺必修\n({ob_gap})')
            sizes.append(ob_gap)
            colors.append('#dc3545')
        if el_done > 0:
            labels.append(f'已修選修\n({el_done})')
            sizes.append(el_done)
            colors.append('#00C851')
        if el_gap > 0:
            labels.append(f'缺選修\n({el_gap})')
            sizes.append(el_gap)
            colors.append('#28a745')
        if gen_done > 0:
            labels.append(f'已修通識\n({gen_done})')
            sizes.append(gen_done)
            colors.append('#9933cc')
        if gen_gap > 0:
            labels.append(f'缺通識\n({gen_gap})')
            sizes.append(gen_gap)
            colors.append('#aa66cc')
            
        if sum(sizes) == 0:
            self.ax.text(0.5, 0.5, "無數據", ha="center", va="center", color="white")
            self.ax.axis('off')
            self.canvas.draw()
            return

        # 這裡設定 textprops, 讓 matplotlib 會使用我們前面定義的中文字型 (受 matplotlib rcParams 控制)
        wedges, texts, autotexts = self.ax.pie(
            sizes, labels=labels, colors=colors, autopct='%1.1f%%', 
            startangle=140, textprops={'color': "white", 'fontsize': 11, 'fontfamily': plt.rcParams['font.sans-serif'][0]}
        )
        
        # 中間挖空變圓環圖
        centre_circle = plt.Circle((0,0), 0.65, fc='#2B2B2B')
        self.ax.add_artist(centre_circle)
        
        self.ax.axis('equal')  
        self.canvas.draw()

    def generate_recommendations(self, ob_gap, el_gap, gen_gap):
        # 正確清空舊推薦
        for w in self.rec_widgets:
            try:
                w.destroy()
            except:
                pass
        self.rec_widgets.clear()
        self.current_recommendations = []
            
        if ob_gap == 0 and el_gap == 0 and gen_gap == 0:
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

            # --- 通識領域關鍵字篩選函式 ---
            domain_keywords = {
                "人文與藝術": ['文學', '哲學', '聽覺', '視覺', '表演', '生活藝術', '藝術', '歷史', '文化', '音樂', '中世紀', '思想', '唐宋', '倫理', '論'],
                "自然與科技": ['醫學', '自然', '資訊', '科技', '民生', '地球', '電腦', '程式', '生態', '健康', '癌症', '診斷', '人體', '應用', '數位'],
                "社會科學": ['管理', '教育', '心理', '社會', '宗教', '政治', '經濟', '法律', '傳播', '國際', '發展', '外交', '關係'],
                "永續素養": ['永續', '風險', '多元', 'SDGs']
            }
            def categorize_domain(name):
                for domain, kws in domain_keywords.items():
                    if any(kw in name for kw in kws):
                        return domain
                return "人文與藝術" # 預設指派

            # --- 計算通識各領域的滿足狀況 ---
            taken_general = [c for c in self.all_courses if c['id'] in self.checked_course_ids and c['category'] == '通識']
            taken_domains = {"人文與藝術": 0, "自然與科技": 0, "社會科學": 0, "永續素養": 0, "任一通識": 0}
            for tc in taken_general:
                dom = categorize_domain(tc['name'])
                taken_domains[dom] += tc['credits']

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
            cursor.execute("SELECT course_name, credits, category FROM FJU_Courses WHERE credits > 0 GROUP BY course_name")
            candidates = []
            general_candidates = []
            for row in cursor.fetchall():
                n, cr, cat = row
                if n not in taken_names:
                    cand = {"name": n, "credits": cr, "category": cat}
                    if cat == "通識":
                        cand["domain"] = categorize_domain(n)
                        general_candidates.append(cand)
                    candidates.append(cand)

            # 計算優先度排序
            def sort_key(c):
                is_priority = any(p in c["name"] for p in priority_cases)
                return (0 if is_priority else 1, c["name"])

            candidates.sort(key=sort_key)
            general_candidates.sort(key=sort_key)

            # 開始配置缺漏
            if ob_gap > 0:
                self.add_rec_section("【必修推薦】", candidates, "必修", ob_gap, "#dc3545", self.current_recommendations)
            
            if el_gap > 0:
                self.add_rec_section("【選修推薦】", candidates, "選修", el_gap, "#28a745", self.current_recommendations)

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

        except Exception as e:
            lbl = ctk.CTkLabel(self.rec_scroll, text=f"產生推薦發生錯誤: {e}", text_color="red")
            lbl.pack()
            self.rec_widgets.append(lbl)
        finally:
            cursor.close()
            conn.close()

    def add_rec_section(self, title, candidates, category, target_gap, color, rec_list=None):
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
                if rec_list is not None:
                    rec_list.append({"name": c['name'], "credits": c['credits'], "category": category})
                
                accumulated += c["credits"]
                if accumulated >= target_gap:
                    break
        
        lbl_info = ctk.CTkLabel(self.rec_scroll, text=f"※ 以上推薦合計提供 {accumulated} 學分可補足此項要求。", text_color="gray60", font=self.f_small)
        lbl_info.pack(anchor="w", padx=10, pady=(5, 20))
        self.rec_widgets.append(lbl_info)

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
                
            pdf.cell(190, 15, txt="🎓 輔大畢業學分查核報告", ln=True, align="C")
            
            pdf.set_font('tc_font', '', 11) if has_tc_font else pdf.set_font("Arial", size=11)
            pdf.cell(190, 8, txt=f"產生時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align="R")
            
            # 分隔線
            pdf.set_line_width(0.5)
            pdf.line(10, 40, 200, 40)
            
            # --- 學分狀態 ---
            pdf.ln(15)
            pdf.set_font('tc_font', '', 14) if has_tc_font else None
            pdf.set_text_color(0, 102, 204)  # 藍色標題
            pdf.cell(190, 10, txt="📊 【 當前學分狀態 】", ln=True)
            
            pdf.set_text_color(0, 0, 0) # 恢復黑色
            pdf.set_font('tc_font', '', 12) if has_tc_font else None
            pdf.cell(190, 8, txt=self.lbl_total_prog.cget("text"), ln=True)
            pdf.cell(190, 8, txt=self.lbl_req_prog.cget("text"), ln=True)
            pdf.cell(190, 8, txt=self.lbl_elec_prog.cget("text"), ln=True)
            pdf.cell(190, 8, txt=self.lbl_gen_prog.cget("text"), ln=True)
            
            pdf.ln(5)
            # 處理帶有多行的狀態字串
            status_lines = self.lbl_status.cget("text").split('\n')
            for line in status_lines:
                pdf.cell(190, 8, txt=line, ln=True)
                
            pdf.ln(10)
            pdf.set_line_width(0.2)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            
            # --- 推薦課程 ---
            pdf.ln(10)
            pdf.set_font('tc_font', '', 14) if has_tc_font else None
            pdf.set_text_color(0, 153, 51)  # 綠色標題
            pdf.cell(190, 10, txt="💡 【 系統推薦修課清單 】", ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('tc_font', '', 12) if has_tc_font else None
            
            if not self.current_recommendations:
                pdf.cell(190, 8, txt="✅ 學分已滿或無推薦課程。", ln=True)
            else:
                for rec in self.current_recommendations:
                    cat_tag = f"[{rec['category']}]"
                    pdf.cell(190, 8, txt=f"   🔹 {cat_tag} {rec['name']} - {rec['credits']} 學分", ln=True)
            
            pdf.output(filepath)
            messagebox.showinfo("匯出成功", f"報告已成功儲存至：\n{filepath}")
            
        except Exception as e:
            messagebox.showerror("匯出錯誤", f"匯出 PDF 發生錯誤：\n{e}")

if __name__ == "__main__":
    app = GraduationGUI()
    app.mainloop()
