##### Check for Blank Lines in Abaqus Files #####
# Writer: Ikeda (Trung Thanh)
# 23/10/2023

import tkinter as tk
from pyjdg import *

def check_blank_lines_in_inp(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    blank_lines = [i+1 for i, line in enumerate(lines) if line.strip() == ""]
    result = ""

    if blank_lines:
        result += f"🔍 {file_path}\nFound {len(blank_lines)} blank lines at:\n"
        for line_num in blank_lines:
            result += f"  - Line {line_num}\n"
    else:
        result += f"✅ {file_path}: No blank lines found.\n"
    
    return result

def process_files(file_path_list):
    all_results = ""
    for file in file_path_list:
        all_results += check_blank_lines_in_inp(file) + "\n"
    
    JPT.MessageBoxPSJ(all_results.strip(), JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)

def onGetButton1Clicked(dlg):
    file_path = dlg.get_item_text(name="Check blank lines")
    if isinstance(file_path, str):
        if ";" in file_path:
            file_path = [s.strip() for s in file_path.split(";") if s.strip()]
        else:
            file_path = [file_path]
    process_files(file_path)

def main():
    dlg = JDGCreator(title="Check blank lines", include_apply=False)

    dlg.add_groupbox(name="GroupBox1", text="INPUT FILES", layout="Window")
    dlg.add_label(name="Label", text="Select Abaqus file(s):", layout="GroupBox1")
    dlg.add_browser("GroupBox1", "Check blank lines", "file", "INP Files (*.inp)|*.inp|All Files(*.*)", "", 1)

    dlg.add_layout(name="Layout1.2", margin=[200, 0, 0, 0], 
                   orientation=orientation.horizontal, layout="GroupBox1")
    dlg.add_button(name="Button1", text="Previews", width=60, height=22, 
                   bk_color=15790320, layout="Layout1.2")

    dlg.generate_window()
    dlg.on_dlg_ok(callfunc=onGetButton1Clicked)

if __name__=='__main__':
    main()
