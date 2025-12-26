##############################################
### UPDATE HTC IN RESULT FILE BY ID LIST
##############################################
### Input:
###   1. ID file (Element IDs)
###   2. Result file (to be exported)
###   3. HTC file (ONLY ONE VALUE, e.g. 1e5)
### Output:
###   Updated result file
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
            if not line or line.startswith('*') or line.startswith('**'):
                continue
            try:
                ids.add(int(line.split(',')[0]))
            except:
                pass

    return ids


# ============================================================
# READ SINGLE HTC VALUE FROM FILE #3
# ============================================================
def read_htc_value(htc_file):

    with open(htc_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('*') or line.startswith('**'):
                continue
            try:
                return float(line)
            except:
                continue

    raise ValueError("No valid HTC value found in HTC file")


# ============================================================
# UPDATE HTC IN RESULT FILE (SAFE FORMAT)
# ============================================================
def update_htc(id_file, result_file, htc_file):

    ids = read_ids(id_file)
    htc_value = read_htc_value(htc_file)

    base, ext = os.path.splitext(result_file)
    out_file = base + "_HTC_UPDATED" + ext

    count = 0

    # Regex:
    # group(1): element ID
    # group(2): middle content
    # group(3): delimiter before HTC
    # group(4): HTC value (last number)
    pattern = re.compile(
        r'^(\s*\d+)(.*?)([,\s]+)([-+0-9.Ee]+)\s*$'
    )

    with open(result_file, 'r', encoding='utf-8', errors='ignore') as fin, \
         open(out_file, 'w', encoding='utf-8') as fout:

        for line in fin:

            m = pattern.match(line)
            if not m:
                fout.write(line)
                continue

            try:
                eid = int(m.group(1))
            except:
                fout.write(line)
                continue

            if eid in ids:
                new_line = (
                    m.group(1)
                    + m.group(2)
                    + m.group(3)
                    + f"{htc_value:.6e}\n"
                )
                fout.write(new_line)
                count += 1
            else:
                fout.write(line)

    return out_file, count


# ============================================================
# OK BUTTON CALLBACK
# ============================================================
def onOkClicked(dlg):

    id_file  = dlg.get_item_text(name="ID file")
    res_file = dlg.get_item_text(name="Result file")
    htc_file = dlg.get_item_text(name="HTC file")

    if not id_file or not res_file or not htc_file:
        JPT.MessageBoxPSJ(
            "Please select all 3 files!",
            JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL
        )
        return

    try:
        out_file, n = update_htc(id_file, res_file, htc_file)
    except Exception as e:
        JPT.MessageBoxPSJ(
            str(e),
            JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL
        )
        return

    msg = (
        f"Updated HTC elements : {n}\n"
        f"Output file:\n{out_file}"
    )

    JPT.ClearLog()
    print(msg)
    JPT.MessageBoxPSJ(msg, JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)


# ============================================================
# MAIN GUI
# ============================================================
def main():

    dlg = JDGCreator(
        title="Update HTC in Result File",
        include_apply=False
    )

    dlg.add_label(layout="Window", name="L1", text="ID file:")
    dlg.add_browser(layout="Window", name="ID file", mode="file")

    dlg.add_label(layout="Window", name="L2", text="Result file:")
    dlg.add_browser(layout="Window", name="Result file", mode="file")

    dlg.add_label(layout="Window", name="L3", text="HTC file (single value):")
    dlg.add_browser(layout="Window", name="HTC file", mode="file")

    dlg.add_groupbox(layout="Window", name="G1", text="PROCESS")

    dlg.add_layout(
        name="Layout1",
        margin=[200, 0, 0, 0],
        orientation=orientation.horizontal,
        layout="G1"
    )

    dlg.add_button(
        layout="Layout1",
        name="BtnOK",
        text="OK",
        width=80,
        height=24,
        bk_color=12632256
    )

    dlg.on_button_clicked(name="BtnOK", callfunc=onOkClicked)

    dlg.generate_window()


# ============================================================
if __name__ == "__main__":
    main()
