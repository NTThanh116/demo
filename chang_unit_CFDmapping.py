#Change UNIT from CFD mapping result
# OUT_Temp = IN_TEMP - 273.15
# OUT_HTC = IN_HTC/1000^2
## Witer: Ikeda

import os

# access folder input
current_dir = os.path.dirname(os.path.abspath(__file__))

input_folder = current_dir
output_folder = os.path.join(current_dir, "output_files")

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

def process_file(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    inside_film = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("*FILM"):
            inside_film = True
            new_lines.append(line)
            continue
        if inside_film and stripped.startswith("*") and not stripped.startswith("*FILM"):
            inside_film = False

        if inside_film and not stripped.startswith("*"):
            parts = stripped.split(",")
            if len(parts) >= 4:
                try:
                    val3 = float(parts[2]) - 273.15           # TEMP
                    val4 = float(parts[3]) / 1_000_000         # HTC
                    parts[2] = f"{val3:.10g}"
                    parts[3] = f"{val4:.10g}"
                    line = ",".join(parts) + "\n"
                except ValueError:
                    pass
        new_lines.append(line)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

# Confirm output file processing
for filename in os.listdir(input_folder):
    if filename.endswith(".txt"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        process_file(input_path, output_path)
        print(f"Finished: {filename}")
