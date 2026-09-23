# ============================================================
# PSJ - Import Nastran + Create Mass Measure Note
# ============================================================

import os
import csv

# ------------------------------------------------------------
# INPUT
# ------------------------------------------------------------

nas_file = r"M:/Technostar/07_Personal/Ikeda/01_Macro_PSJ/CoG/data/si_396D_HEV_2307_newBJ_rekka.nas"

csv_file = os.path.splitext(nas_file)[0] + "_mass_properties.csv"


# ------------------------------------------------------------
# 1. IMPORT NASTRAN
# ------------------------------------------------------------

JPT.Exec(
    'ImportBdf(["{}"], 2, 1.0472, 1.0472, 0, -1, 0)'.format(
        nas_file.replace("\\", "/")
    )
)

JPT.ViewFitToModel()


# ------------------------------------------------------------
# 2. CREATE MASS MEASURE NOTE
#
# Hiện tại ví dụ này giả sử model import ra Part(1).
# ------------------------------------------------------------

mass_note = Tools.Measure.Mass.CreateMeasureNote.Property(
    strNoteName="Mass_Result",
    crlParts=[Part(1)]
)

print("Mass measure note created:")
print(mass_note)


# ------------------------------------------------------------
# 3. MASS RESULT
#
# THAY 4 GIÁ TRỊ BÊN DƯỚI bằng giá trị đọc được từ Measure Note.
# Khi có API đọc nội dung Measure Note, phần này sẽ được tự động hóa.
# ------------------------------------------------------------

total_mass = 1760.253
gravity_x = 123.456
gravity_y = -45.672
gravity_z = 315.873


# ------------------------------------------------------------
# 4. WRITE CSV
# ------------------------------------------------------------

with open(csv_file, "w", newline="") as f:
    writer = csv.writer(f)

    writer.writerow(["MASS PROPERTIES", "Value", "Unit"])
    writer.writerow(["Total Mass", total_mass, "g"])
    writer.writerow(["Gravity Center X", gravity_x, "mm"])
    writer.writerow(["Gravity Center Y", gravity_y, "mm"])
    writer.writerow(["Gravity Center Z", gravity_z, "mm"])


print("=================================")
print("        MASS PROPERTIES")
print("=================================")
print("Total Mass       : {:.3f} g".format(total_mass))
print("Gravity Center X : {:.3f} mm".format(gravity_x))
print("Gravity Center Y : {:.3f} mm".format(gravity_y))
print("Gravity Center Z : {:.3f} mm".format(gravity_z))
print("=================================")

print("CSV saved:")
print(csv_file)
