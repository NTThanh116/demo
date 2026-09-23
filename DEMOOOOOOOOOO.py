import os
import re
import tempfile
import urllib.request


# ============================================================
# INPUT FILE
# ============================================================

NAS_SOURCE = r"M:\Technstar\07_Personal\Ikeda\01_Macro_PSJ\CoG\data\model.nas"

# Hoặc direct URL:
# NAS_SOURCE = "https://example.com/model.nas"


# ============================================================
# BASIC FUNCTIONS
# ============================================================

def normalize_name(name):
    return name.strip().upper()


def is_url(source):
    return source.lower().startswith(
        ("http://", "https://")
    )


def download_nas(url):

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".nas",
        delete=False
    )

    path = temp_file.name
    temp_file.close()

    urllib.request.urlretrieve(
        url,
        path
    )

    return path


# ============================================================
# NASTRAN FLOAT
# ============================================================

def nastran_float(value):
    """
    Convert Nastran number formats to float.

    Supports examples:

        1.234
        1.2E+03
        1.2D+03
        1.234+3
        1.234-3
    """

    value = value.strip()

    if not value:
        return 0.0

    value = value.replace(
        "D",
        "E"
    ).replace(
        "d",
        "E"
    )

    try:
        return float(value)

    except ValueError:
        pass

    # Nastran implicit exponent:
    #
    # 1.23+4  -> 1.23E+4
    # 1.23-4  -> 1.23E-4

    match = re.match(
        r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))([+-]\d+)$",
        value
    )

    if match:

        return float(
            match.group(1)
            + "E"
            + match.group(2)
        )

    raise ValueError(
        f"Cannot convert Nastran number: {value}"
    )


# ============================================================
# READ FILE
# ============================================================

def read_lines(nas_file):

    with open(
        nas_file,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        return f.readlines()


# ============================================================
# READ $DSTRCT
# ============================================================

def read_dstrct(lines):

    structures = []

    for line in lines:

        stripped = line.strip()

        if not stripped.upper().startswith(
            "$DSTRCT"
        ):
            continue

        parts = stripped.split(
            maxsplit=2
        )

        if len(parts) < 3:
            continue

        try:
            level = int(
                parts[1]
            )

        except ValueError:
            continue

        name = parts[2].strip()

        structures.append(
            (
                level,
                name
            )
        )

    return structures


# ============================================================
# FIND TANTAI UNDER 01_EX_ASSY
# ============================================================

def find_tantai_models(lines):

    structures = read_dstrct(
        lines
    )

    tantai_models = []

    for i, (
        parent_level,
        parent_name
    ) in enumerate(structures):

        # ====================================================
        # Find 01_EX_ASSY
        # ====================================================

        if normalize_name(
            parent_name
        ) != "01_EX_ASSY":

            continue


        # ====================================================
        # Search all descendants
        # ====================================================

        for j in range(
            i + 1,
            len(structures)
        ):

            level, name = structures[j]


            # End of 01_EX_ASSY
            if level <= parent_level:
                break


            # =================================================
            # TANTAI model
            # =================================================

            if "TANTAI" in normalize_name(
                name
            ):

                tantai_models.append(
                    normalize_name(
                        name
                    )
                )

    return list(
        dict.fromkeys(
            tantai_models
        )
    )


# ============================================================
# GET BLOCK NAME
# ============================================================

def get_block_name(
    line,
    block_type
):

    stripped = line.strip()

    if not stripped.upper().startswith(
        block_type.upper()
    ):
        return None

    parts = stripped.split(
        maxsplit=1
    )

    if len(parts) < 2:
        return None

    return normalize_name(
        parts[1]
    )


# ============================================================
# SPLIT CARD FIELDS
# ============================================================

def split_fields(line):
    """
    Supports common whitespace and free-field formats.

    GRID  123  0  100.0 200.0 300.0

    GRID,123,0,100.0,200.0,300.0
    """

    stripped = line.strip()

    if "," in stripped:

        return [
            x.strip()
            for x in stripped.split(",")
        ]

    return stripped.split()


# ============================================================
# GET GRID INFORMATION
# ============================================================

def find_tantai_grids(
    lines,
    tantai_models
):

    target = set(
        tantai_models
    )

    result = {
        name: []
        for name in target
    }

    current_gblock = None


    for line in lines:

        stripped = line.strip()


        # ====================================================
        # GBLOCK
        # ====================================================

        if stripped.upper().startswith(
            "$GBLOCK"
        ):

            current_gblock = get_block_name(
                line,
                "$GBLOCK"
            )

            continue


        # ====================================================
        # Next DBLOCK means GBLOCK has ended
        # ====================================================

        if stripped.upper().startswith(
            "$DBLOCK"
        ):

            current_gblock = None

            continue


        if current_gblock not in target:

            continue


        # ====================================================
        # GRID
        # ====================================================

        fields = split_fields(
            line
        )

        if not fields:
            continue

        if fields[0].upper() != "GRID":
            continue


        # ====================================================
        # Standard GRID:
        #
        # GRID ID CP X1 X2 X3 CD PS SEID
        # ====================================================

        try:

            grid_id = int(
                fields[1]
            )

            cp = 0

            if len(fields) > 2 and fields[2]:

                try:
                    cp = int(
                        fields[2]
                    )
                except ValueError:
                    cp = 0


            x = nastran_float(
                fields[3]
            )

            y = nastran_float(
                fields[4]
            )

            z = nastran_float(
                fields[5]
            )

        except (
            ValueError,
            IndexError
        ):

            continue


        result[
            current_gblock
        ].append(
            {
                "GRID": grid_id,
                "CP": cp,
                "X": x,
                "Y": y,
                "Z": z,
            }
        )


    return result


# ============================================================
# FIND CONM2 MASS
# ============================================================

def find_tantai_mass(
    lines,
    tantai_models,
    grids
):

    target = set(
        tantai_models
    )


    # ========================================================
    # GRID -> TANTAI mapping
    # ========================================================

    grid_to_model = {}

    for model_name, grid_list in (
        grids.items()
    ):

        for grid in grid_list:

            grid_to_model[
                grid["GRID"]
            ] = model_name


    masses = {
        name: 0.0
        for name in target
    }


    current_dblock = None


    for line in lines:

        stripped = line.strip()


        # ====================================================
        # DBLOCK
        # ====================================================

        if stripped.upper().startswith(
            "$DBLOCK"
        ):

            current_dblock = get_block_name(
                line,
                "$DBLOCK"
            )

            continue


        # ====================================================
        # GBLOCK -> end element block
        # ====================================================

        if stripped.upper().startswith(
            "$GBLOCK"
        ):

            current_dblock = None

            continue


        if current_dblock not in target:

            continue


        fields = split_fields(
            line
        )

        if not fields:
            continue


        # ====================================================
        # CONM2
        #
        # CONM2 EID G CID M X1 X2 X3
        #
        #             ^
        #             GRID
        #
        #                 ^
        #                 MASS
        # ====================================================

        if fields[0].upper() != "CONM2":
            continue


        try:

            grid_id = int(
                fields[2]
            )


            # CID = fields[3]
            # MASS = fields[4]

            mass = nastran_float(
                fields[4]
            )

        except (
            ValueError,
            IndexError
        ):

            continue


        # ====================================================
        # Make sure CONM2 belongs to TANTAI GRID
        # ====================================================

        if grid_id in grid_to_model:

            model_name = grid_to_model[
                grid_id
            ]

            masses[
                model_name
            ] += mass


    return masses


# ============================================================
# EXTRACT TANTAI INFORMATION
# ============================================================

def get_tantai_information(
    nas_file
):

    lines = read_lines(
        nas_file
    )


    # ========================================================
    # STEP 1
    # TANTAI models under 01_EX_ASSY
    # ========================================================

    tantai_models = find_tantai_models(
        lines
    )


    # ========================================================
    # STEP 2
    # GRID + coordinates
    # ========================================================

    grids = find_tantai_grids(
        lines,
        tantai_models
    )


    # ========================================================
    # STEP 3
    # Mass
    # ========================================================

    masses = find_tantai_mass(
        lines,
        tantai_models,
        grids
    )


    return (
        tantai_models,
        grids,
        masses
    )


# ============================================================
# MAIN
# ============================================================

def main():

    temp_file = None


    try:

        # ====================================================
        # URL
        # ====================================================

        if is_url(
            NAS_SOURCE
        ):

            temp_file = download_nas(
                NAS_SOURCE
            )

            nas_file = temp_file


        # ====================================================
        # LOCAL FILE
        # ====================================================

        else:

            nas_file = NAS_SOURCE


            if not os.path.isfile(
                nas_file
            ):

                raise FileNotFoundError(
                    f"File not found: {nas_file}"
                )


        # ====================================================
        # GET TANTAI DATA
        # ====================================================

        (
            tantai_models,
            grids,
            masses
        ) = get_tantai_information(
            nas_file
        )


        # ====================================================
        # OUTPUT
        # ====================================================

        if not tantai_models:

            print(
                "No TANTAI model found under 01_EX_ASSY."
            )

            return


        for model_name in tantai_models:

            grid_list = grids.get(
                model_name,
                []
            )


            print(
                f"TANTAI : {model_name}"
            )


            if not grid_list:

                print(
                    "GRID   : NOT FOUND"
                )

                print(
                    f"MASS   : {masses.get(model_name, 0.0)}"
                )

                print()

                continue


            for grid in grid_list:

                print(
                    f"GRID   : {grid['GRID']}"
                )

                print(
                    f"X      : {grid['X']}"
                )

                print(
                    f"Y      : {grid['Y']}"
                )

                print(
                    f"Z      : {grid['Z']}"
                )

                print(
                    f"CP     : {grid['CP']}"
                )


            print(
                f"MASS   : {masses.get(model_name, 0.0)}"
            )

            print()


    finally:

        if temp_file is not None:

            try:

                os.remove(
                    temp_file
                )

            except OSError:

                pass


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
