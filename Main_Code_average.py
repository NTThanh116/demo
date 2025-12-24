##############################################
### AVERAGE TEMP & HTC FROM CFD MAPPING FILE ###
##############################################
### Input files:
        ### 1. INP file with element IDs
        ### 2. CFD mapping results file (*FILM)
### Output:
        ### Average TEMP & HTC
##############################################
### Writer: Thanh Trung Nguyen (IKEDA)
### Update: 24/12/2025
############################################__
import re
import csv
from tkinter import Tk, filedialog
from pyjdg import *


# ============================================================
# READ ELEMENT IDS FROM INP
# ============================================================
def read_element_ids(inp_file):
    elem_ids = set()

    with open(inp_file, 'r') as f:
        for line in f:
            line = line.strip()

            # Skip empty / comment / keyword
            if not line or line.startswith('*') or line.startswith('**'):
                continue

            try:
                eid = int(re.split(r'[,\s]+', line)[0])
                elem_ids.add(eid)
            except:
                pass

    return elem_ids


# ============================================================
# READ CFD RESULTS AND COMPUTE AVERAGE
# ============================================================
def compute_average(inp_file, result_file):

    elem_ids = read_element_ids(inp_file)

    temp_list = []
    htc_list  = []

    with open(result_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)

        for row in reader:
            if len(row) < 4:
                continue

            try:
                eid  = int(row[0])
                temp = float(row[2])
                htc  = float(row[3])
            except:
                continue

            if eid in elem_ids:
                temp_list.append(temp)
                htc_list.append(htc)

    if not temp_list:
        return None, None, 0

    avg_temp = sum(temp_list) / len(temp_list)
    avg_htc  = sum(htc_list)  / len(htc_list)

    return avg_temp, avg_htc, len(temp_list)


# ============================================================
# FILE BROWSER
# ============================================================
def select_file(title):
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title=title)
    root.destroy()
    return file_path


# ============================================================
# BUTTON CALLBACK
# ============================================================
def onAverageClicked(dlg):

    inp_file = dlg.get_item_text(name="INP file")
    res_file = dlg.get_item_text(name="Result file")

    avg_temp, avg_htc, n = compute_average(inp_file, res_file)

    if avg_temp is None:
        JPT.MessageBoxPSJ(
            "No matching elements found!",
            JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL
        )
        return

    msg = (
        f"Number of elements : {n}\n"
        f"Average TEMP       : {avg_temp:.4f}\n"
        f"Average HTC        : {avg_htc:.4f}"
    )

    print(msg)
    JPT.ClearLog()
    JPT.MessageBoxPSJ(msg, JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)


# ============================================================
# MAIN GUI
# ============================================================
def main():

    dlg = JDGCreator(title="Average TEMP & HTC", include_apply=False)

    dlg.add_label(name="Label1", text="Input INP file:", layout="Window")
    dlg.add_browser(
        name="INP file",
        mode="file",
        file_filter="INP Files (*.inp);;All Files (*.*)",
        layout="Window"
    )

    dlg.add_label(name="Label2", text="CFD mapping results (*FILM / CSV):", layout="Window")
    dlg.add_browser(
        name="Result file",
        mode="file",
        file_filter="All Files (*.*)",
        layout="Window"
    )

    dlg.add_groupbox(name="GroupBox1", text="PROCESS", layout="Window")

    dlg.add_layout(
        name="Layout1",
        margin=[200, 0, 0, 0],
        orientation=orientation.horizontal,
        layout="GroupBox1"
    )

    dlg.add_button(
        name="BtnAvg",
        text="AVERAGE",
        width=80,
        height=24,
        bk_color=12632256,
        layout="Layout1"
    )

    dlg.on_button_clicked(name="BtnAvg", callfunc=onAverageClicked)

    dlg.generate_window()


# ============================================================
if __name__ == '__main__':
    main()
