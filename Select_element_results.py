##############################################
### EXTRACT CFD RESULTS & EXPORT FILM INP
##############################################
### Input:
###   1. ID file
###   2. CFD mapping result file
### Output:
###   INP file with *FILM keyword
##############################################
### Writer: Thanh Trung Nguyen (IKEDA)
### Update: 25/12/2025
##############################################

import os
import re
from pyjdg import *


# ============================================================
# READ IDS FROM FILE #1
# ============================================================
def read_ids(id_file):

    ids = set()

    with open(id_file, 'r') as f:
        for line in f:
            line = line.strip()

            # Skip empty / comment / keyword
            if not line or line.startswith('*') or line.startswith('**'):
                continue

            try:
                eid = int(line.split(',')[0])
                ids.add(eid)
            except:
                pass

    return ids


# ============================================================
# EXTRACT RESULTS AND WRITE *FILM INP
# ============================================================
def extract_to_inp(id_file, result_file):

    ids = read_ids(id_file)

    base, _ = os.path.splitext(result_file)
    out_file = base + "_EXTRACT.inp"

    count = 0

    with open(result_file, 'r', encoding='utf-8') as fin, \
         open(out_file, 'w', encoding='utf-8') as fout:

        # === REQUIRED ABAQUS / ACTRAN KEYWORD ===
        fout.write("*FILM\n")

        for line in fin:
            stripped = line.strip()
            if not stripped:
                continue

            # Only use first field as ID, keep full line format
            parts = re.split(r'[,\s]+', stripped)

            try:
                eid = int(parts[0])
            except:
                continue

            if eid in ids:
                fout.write(line if line.endswith("\n") else line + "\n")
                count += 1

    return out_file, count


# ============================================================
# OK BUTTON CALLBACK
# ============================================================
def onOkClicked(dlg):

    id_file  = dlg.get_item_text(name="ID file")
    res_file = dlg.get_item_text(name="Result file")

    if not id_file or not res_file:
        JPT.MessageBoxPSJ(
            "Please select both ID file and Result file!",
            JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL
        )
        return

    out_file, n = extract_to_inp(id_file, res_file)

    msg = (
        f"Extracted elements : {n}\n"
        f"Output INP file    :\n{out_file}"
    )

    JPT.ClearLog()
    print(msg)
    JPT.MessageBoxPSJ(msg, JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)


# ============================================================
# MAIN GUI
# ============================================================
def main():

    dlg = JDGCreator(
        title="Extract CFD Results to *FILM INP",
        include_apply=False
    )

    dlg.add_label(
        name="Label1",
        text="ID file:",
        layout="Window"
    )

    dlg.add_browser(
        name="ID file",
        mode="file",
        file_filter="All Files (*.*)",
        layout="Window"
    )

    dlg.add_label(
        name="Label2",
        text="CFD mapping result file:",
        layout="Window"
    )

    dlg.add_browser(
        name="Result file",
        mode="file",
        file_filter="All Files (*.*)",
        layout="Window"
    )

    dlg.add_groupbox(
        name="GroupBox1",
        text="PROCESS",
        layout="Window"
    )

    dlg.add_layout(
        name="Layout1",
        margin=[200, 0, 0, 0],
        orientation=orientation.horizontal,
        layout="GroupBox1"
    )

    dlg.add_button(
        name="BtnOK",
        text="OK",
        width=80,
        height=24,
        bk_color=12632256,
        layout="Layout1"
    )

    dlg.on_button_clicked(
        name="BtnOK",
        callfunc=onOkClicked
    )

    dlg.generate_window()


# ============================================================
if __name__ == '__main__':
    main()
