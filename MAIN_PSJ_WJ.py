### Mapping_WJ ###
### Author: Ikeda (Trung Thanh) ###

import os
from pyjdg import *



def generate_heat_files(input_mapping_path: str):
    """
    Reads an input .inp mapping file and generates output file names based on it.
    Outputs:
      - Film Property file: *_HEAT_filmprop_WJ.inp
      - SFILM file: *_HEAT_sfilm_WJ.inp
      - Surface map file: *_HEAT_surface_WJ.inp
    """
    base, ext = os.path.splitext(input_mapping_path)
    output_filmprop_path = base + "_HEAT_filmprop_WJ.inp"
    output_sfilm_path = base + "_HEAT_sfilm_WJ.inp"
    output_surface_map_path = base + "_HEAT_surface_WJ.inp"

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

            # Film property file output
            fout_filmprop.write(f"*FILM PROPERTY, NAME=FPnwjc1_{index}\n")
            fout_filmprop.write(f"{htc_scaled:e}, 0.0\n")
            fout_filmprop.write(f"{htc_scaled:e}, 140.0\n")
            fout_filmprop.write(f"{htc_scaled * 1.25:e}, 160.0\n")
            fout_filmprop.write(f"{htc_scaled * 2.5:e}, 200.0\n")

            # Surface map file output (no blank lines between blocks)
            fout_surface_map.write(f"*SURFACE, NAME=SEwj_{index} , TYPE=ELEMENT\n")
            fout_surface_map.write(f"{node_id}, SPOS\n")

            # SFILM file output (temp in Celsius, exponential format)
            temp_celsius = temp_kelvin - 273.15
            fout_sfilm.write(f"SEwj_{index}, F, {temp_celsius:e}, FPnwjc1_{index}\n")

            index += 1

# Example usage
# generate_heat_files("_mapping_WJ.inp")

# PSJ command
def onGetButton1Clicked(dlg):
    input_mapping_path = dlg.get_item_text(name="_mapping_WJ.inp")
    generate_heat_files(input_mapping_path)
    JPT.MessageBoxPSJ("Export successful", JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)

def main():
    dlg = JDGCreator(title="WJ mapping", include_apply=False)
    
    dlg.add_label(name="Label", text="Input mapping_WJ:", layout="Window")
    dlg.add_browser(name="File Ndelm", mode="file", file_filter="All Files(*.*)", layout="Window")

    dlg.generate_window()
    dlg.on_dlg_ok(callfunc=onGetButton1Clicked)

if __name__=='__main__':
    main()
