# ============================================================
# PSJ TOOL - IMPORT NASTRAN + MASS MEASURE + EXPORT CSV
# ============================================================

import os
import csv


# ============================================================
# USER INPUT
# ============================================================

nas_file = r"Z:/sarrogate_202609/18_396D_HEV/BLK/396D_HEV_CCO.nas"

# Output CSV cùng thư mục với file NAS
csv_file = os.path.splitext(nas_file)[0] + "_mass_properties.csv"


# ============================================================
# SETTINGS
# ============================================================

note_name = "Mass_Result"


# ============================================================
# 1. CHECK INPUT FILE
# ============================================================

if not os.path.isfile(nas_file):
    raise RuntimeError(
        "NAS file does not exist:\n{}".format(nas_file)
    )

print("==============================================")
print("PSJ MASS PROPERTY TOOL")
print("==============================================")
print("Input file:")
print(nas_file)
print("")


# ============================================================
# 2. IMPORT NASTRAN BDF / NAS
# ============================================================

nas_psj = nas_file.replace("\\", "/")

import_command = (
    'ImportBdf(["{}"], 2, 1.0472, 1.0472, 0, -1, 0)'
).format(nas_psj)

print("Importing NASTRAN file...")

JPT.Exec(import_command)

print("Import completed.")

JPT.ViewFitToModel()


# ============================================================
# 3. CREATE MASS MEASURE NOTE
# ============================================================
#
# IMPORTANT
#
# Không dùng:
#
#     Part(1)
#
# vì database hiện tại không có Part ID = 1.
#
# Macro recorder của PSJ cho thấy entity cursor:
#
#     [3:1]
#
# nên hiện tại dùng trực tiếp macro command.
#
# ============================================================

print("")
print("Creating mass measure note...")

mass_command = (
    '"CreateMeasureNoteMassByProperty" '
    '"{}", '
    '[3:1], '
    '0:0, '
    '16, '
    '0, '
    '0, '
    '16777215, '
    '1, '
    '0, '
    '1, '
    '0, '
    '1, '
    '1'
).format(note_name)

JPT.Exec(mass_command)

print("Mass measure note created:")
print(note_name)


# ============================================================
# 4. MASS / CENTER OF GRAVITY RESULT
# ============================================================
#
# PSJ đã tạo Measure Note "Mass_Result".
#
# Tuy nhiên, tại thời điểm hiện tại chưa có API/documentation
# xác nhận cách đọc numerical values từ Measure Note.
#
# Khi tìm được API đọc result, 4 biến dưới đây sẽ được thay
# bằng kết quả tự động.
#
# ============================================================

total_mass = None
gravity_x = None
gravity_y = None
gravity_z = None


# ============================================================
# 5. WRITE CSV
# ============================================================

print("")
print("Writing CSV...")

with open(csv_file, "w", newline="") as f:

    writer = csv.writer(f)

    writer.writerow([
        "MASS PROPERTIES",
        "Value",
        "Unit"
    ])

    if total_mass is not None:

        writer.writerow([
            "Total Mass",
            total_mass,
            "g"
        ])

        writer.writerow([
            "Gravity Center X",
            gravity_x,
            "mm"
        ])

        writer.writerow([
            "Gravity Center Y",
            gravity_y,
            "mm"
        ])

        writer.writerow([
            "Gravity Center Z",
            gravity_z,
            "mm"
        ])

    else:

        writer.writerow([
            "Total Mass",
            "READ FROM PSJ NOTE: {}".format(note_name),
            "g"
        ])

        writer.writerow([
            "Gravity Center X",
            "READ FROM PSJ NOTE: {}".format(note_name),
            "mm"
        ])

        writer.writerow([
            "Gravity Center Y",
            "READ FROM PSJ NOTE: {}".format(note_name),
            "mm"
        ])

        writer.writerow([
            "Gravity Center Z",
            "READ FROM PSJ NOTE: {}".format(note_name),
            "mm"
        ])


# ============================================================
# 6. CONSOLE OUTPUT
# ============================================================

print("")
print("==============================================")
print("              MASS PROPERTIES")
print("==============================================")

if total_mass is not None:

    print(
        "Total Mass       : {:.3f} g".format(
            total_mass
        )
    )

    print(
        "Gravity Center X : {:.3f} mm".format(
            gravity_x
        )
    )

    print(
        "Gravity Center Y : {:.3f} mm".format(
            gravity_y
        )
    )

    print(
        "Gravity Center Z : {:.3f} mm".format(
            gravity_z
        )
    )

else:

    print("Measure Note created successfully.")
    print("")
    print("Note name:")
    print(note_name)
    print("")
    print("Mass/CoG numerical values are stored in PSJ")
    print("Measure Note but are not read by the script yet.")

print("==============================================")

print("")
print("CSV saved to:")
print(csv_file)

print("")
print("Done.")
