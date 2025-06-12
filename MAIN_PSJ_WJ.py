### Mapping_WJ ###
### Author: Ikeda (Trung Thanh) ###

import os
from tkinter import filedialog, Tk
from pyjdg import *

def select_output_folder():
    # Use Tkinter to select a folder for saving the results.
    root = Tk()
    root.withdraw()  # Hide the main window.
    folder = filedialog.askdirectory(title="Select folder to save results")
    root.destroy()
    return folder

def generate_heat_files(input_mapping_path: str):
    """
    Reads the input mapping file and exports 3 files with fixed names:
      - Film Property: _HEAT_filmprop_WJ.inp
      - SFILM: _HEAT_sfilm_WJ.inp
      - Surface Map: _HEAT_surface_WJ.inp
    The files are saved in a folder selected by the user.
    """
    # Choose the output folder.
    output_folder = select_output_folder()
    if not output_folder:
        print("No folder selected, export aborted!")
        return

    # Use fixed output file names.
    output_filmprop_path = os.path.join(output_folder, "_HEAT_filmprop_WJ.inp")
    output_sfilm_path = os.path.join(output_folder, "_HEAT_sfilm_WJ.inp")
    output_surface_map_path = os.path.join(output_folder, "_HEAT_surface_WJ.inp")

    with open(input_mapping_path, 'r') as fin, \
         open(output_filmprop_path, 'w') as fout_filmprop, \
         open(output_sfilm_path, 'w') as fout_sfilm, \
         open(output_surface_map_path, 'w') as fout_surface_map:

        fout_sfilm.write("*SFILM\n")
        index = 1
        for line in fin:
            line = line.strip()
            if not line or line.startswith('*'):
                continue

            parts = [p.strip() for p in line.split(',')]
            if len(parts) != 4:
                continue

            node_id = parts[0]
            try:
                temp_kelvin = float(parts[2])
                htc_value = float(parts[3])
            except ValueError:
                print(f"⚠️ ERROR: Cannot read TEMP or HTC from line: {line}")
                continue

            htc_scaled = htc_value / 1_000_000

            # Write Film Property file data.
            fout_filmprop.write(f"*FILM PROPERTY, NAME=FPnwjc1_{index}\n")
            fout_filmprop.write(f"{htc_scaled:e}, 0.0\n")
            fout_filmprop.write(f"{htc_scaled:e}, 140.0\n")
            fout_filmprop.write(f"{htc_scaled * 1.25:e}, 160.0\n")
            fout_filmprop.write(f"{htc_scaled * 2.5:e}, 200.0\n")

            # Write Surface Map file data (without blank lines between blocks).
            fout_surface_map.write(f"*SURFACE, NAME=SEwj_{index} , TYPE=ELEMENT\n")
            fout_surface_map.write(f"{node_id}, SPOS\n")

            # Write SFILM file data (temperature in Celsius using exponential format).
            temp_celsius = temp_kelvin - 273.15
            fout_sfilm.write(f"SEwj_{index}, F, {temp_celsius:e}, FPnwjc1_{index}\n")
            
            index += 1

# PSJ command: on button click, get input file from dialog and call generate_heat_files.
def onGetButton1Clicked(dlg):
    input_mapping_path = dlg.get_item_text(name="_mapping_WJ.inp")
    if not input_mapping_path or not os.path.exists(input_mapping_path):
        JPT.MessageBoxPSJ("Please choose a valid input file", JPT.MsgBoxType.MB_INFORMATION)
        return
    generate_heat_files(input_mapping_path)
    JPT.MessageBoxPSJ("Export successful", JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)

def main():
    dlg = JDGCreator(title="WJ Mapping", include_apply=False)
    
    dlg.add_groupbox(name="GroupBox1", text="INPUT FILE", layout="Window")
    dlg.add_label(name="Label", text="Input mapping_WJ:", layout="GroupBox1")
    dlg.add_browser(name="_mapping_WJ.inp", mode="file", file_filter="All Files(*.*)", layout="GroupBox1")
    
    # Create a horizontal layout with specific margin (based on your provided format)
    dlg.add_layout(name="Layout1.2", margin=[200, 0, 0, 0], 
                   orientation=orientation.horizontal, layout="GroupBox1")
    # Add a button to the new layout with the specified size.
    dlg.add_button(name="Button1", text="Previews", width=60, height=22, 
                   bk_color=15790320, layout="Layout1.2")
    
    dlg.generate_window()
    dlg.on_dlg_ok(callfunc=onGetButton1Clicked)

if __name__=='__main__':
    main()
