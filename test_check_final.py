import tkinter as tk
import customtkinter as ctk
import os
os.environ['FJU_DEPARTMENT'] = '資訊管理學系-學士班 (114學年度) - 完整補正版'
import sys
sys.path.append('test_project')
from gui import GraduationGUI

app = GraduationGUI()
app.update()
app.do_graduation_check()
print("Check completed successfully")
