import os
import tempfile
import urllib.request


# ============================================================
# INPUT FILE
# ============================================================

NAS_SOURCE = r"M:\Technstar\07_Personal\Ikeda\01_Macro_PSJ\CoG\data\model.nas"

# Hoặc:
# NAS_SOURCE = "https://example.com/model.nas"


# ============================================================
# TARGET GROUPS
# ============================================================

GROUP_PREFIXES = (
    "CCO_",
    "S/M_",
    "M/M_",
)


# ============================================================
# 3D SOLID ELEMENT TYPES
# ============================================================

SOLID_ELEMENTS = {
    "CTETRA",
    "CPENTA",
    "CHEXA",
    "CPYRAM",
}


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
# READ $DSTRCT HIERARCHY
# ============================================================

def read_dstrct(nas_file):

    structures = []

    with open(
        nas_file,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        for line in f:

            stripped = line.strip()

            if not stripped.upper().startswith("$DSTRCT"):
                continue

            parts = stripped.split(
                maxsplit=2
            )

            if len(parts) < 3:
                continue

            try:
                level = int(parts[1])

            except ValueError:
                continue

            name = parts[2].strip()

            structures.append(
                (level, name)
            )

    return structures


# ============================================================
# DETECT CCO / S/M / M/M
# ============================================================

def get_group_type(name):

    name = normalize_name(name)

    if name.startswith("CCO_"):
        return "CCO_"

    if name.startswith("S/M_"):
        return "S/M_"

    if name.startswith("M/M_"):
        return "M/M_"

    return None


# ============================================================
# FIND SUBMODELS OF CCO / S/M / M/M
# ============================================================

def find_group_submodels(nas_file):

    structures = read_dstrct(
        nas_file
    )

    groups = {
        "CCO_": set(),
        "S/M_": set(),
        "M/M_": set(),
    }

    for i, (
        parent_level,
        parent_name
    ) in enumerate(structures):

        group_type = get_group_type(
            parent_name
        )

        if group_type is None:
            continue

        # Include parent
        groups[group_type].add(
            normalize_name(
                parent_name
            )
        )

        # Find all descendants
        for j in range(
            i + 1,
            len(structures)
        ):

            child_level, child_name = (
                structures[j]
            )

            # End of this parent
            if child_level <= parent_level:
                break

            groups[group_type].add(
                normalize_name(
                    child_name
                )
            )

    return groups


# ============================================================
# FIND TANTAI SUBMODELS UNDER 01_EX_ASSY
# ============================================================

def find_ex_tantai_submodels(nas_file):

    """
    Find 01_EX_ASSY in DSTRCT hierarchy.

    Then take every descendant whose name contains TANTAI.

    Example:

    $DSTRCT 1  01_EX_ASSY
    $DSTRCT 2  ABC
    $DSTRCT 3  S24_TANTAI_01
    $DSTRCT 2  XYZ_TANTAI_02
    $DSTRCT 1  02_FR_ASSY

    Result:

    {
        "S24_TANTAI_01",
        "XYZ_TANTAI_02"
    }
    """

    structures = read_dstrct(
        nas_file
    )

    target_submodels = set()

    for i, (
        parent_level,
        parent_name
    ) in enumerate(structures):

        # ================================================
        # Find 01_EX_ASSY
        # ================================================

        if normalize_name(parent_name) != "01_EX_ASSY":
            continue


        # ================================================
        # Read all descendants
        # ================================================

        for j in range(
            i + 1,
            len(structures)
        ):

            child_level, child_name = (
                structures[j]
            )

            # End of 01_EX_ASSY hierarchy
            if child_level <= parent_level:
                break


            # ============================================
            # Only names containing TANTAI
            # ============================================

            if "TANTAI" in normalize_name(
                child_name
            ):

                target_submodels.add(
                    normalize_name(
                        child_name
                    )
                )


    return target_submodels


# ============================================================
# GET BLOCK NAME
# ============================================================

def get_block_name(line, keyword):

    stripped = line.strip()

    if not stripped.upper().startswith(
        keyword.upper()
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
# GET NASTRAN CARD
# ============================================================

def get_card_name(line):

    stripped = line.strip()

    if not stripped:
        return None

    if stripped.startswith("$"):
        return None

    if stripped.startswith("+"):
        return None

    if stripped.startswith("*"):
        return None


    # Free field
    if "," in stripped:

        card = stripped.split(
            ",",
            1
        )[0].strip()

    else:

        parts = stripped.split()

        if not parts:
            return None

        card = parts[0]


    return card.rstrip("*").upper()


# ============================================================
# CHECK SHELL / SOLID
# ============================================================

def is_target_element(card):

    if card is None:
        return False


    # ========================================================
    # 2D SHELL
    # ========================================================

    if card.startswith("CQUAD"):
        return True

    if card.startswith("CTRIA"):
        return True

    if card == "CSHEAR":
        return True


    # ========================================================
    # 3D SOLID
    # ========================================================

    if card in SOLID_ELEMENTS:
        return True


    # RBE2 / RBE3 / BAR / BEAM etc. ignored
    return False


# ============================================================
# GET ID
# ============================================================

def get_second_field_id(line):

    """
    Works for both:

    CQUAD4 12080 ...
    GRID   2788 ...

    -> returns field #2
    """

    stripped = line.strip()

    try:

        if "," in stripped:

            fields = stripped.split(",")

            return int(
                fields[1].strip()
            )


        fields = stripped.split()

        return int(
            fields[1]
        )


    except (
        ValueError,
        IndexError
    ):

        return None


# ============================================================
# COUNT CCO / S/M / M/M ELEMENTS
# ============================================================

def count_group_elements(nas_file):

    group_submodels = find_group_submodels(
        nas_file
    )


    group_elements = {
        "CCO_": set(),
        "S/M_": set(),
        "M/M_": set(),
    }


    active_groups = set()


    with open(
        nas_file,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        for line in f:

            stripped = line.strip()


            # ==================================================
            # NEW DBLOCK
            # ==================================================

            if stripped.upper().startswith("$DBLOCK"):

                block_name = get_block_name(
                    line,
                    "$DBLOCK"
                )

                active_groups = set()

                if block_name is not None:

                    for (
                        group_name,
                        submodels
                    ) in group_submodels.items():

                        if block_name in submodels:

                            active_groups.add(
                                group_name
                            )

                continue


            # ==================================================
            # GBLOCK means node section starts
            # ==================================================

            if stripped.upper().startswith("$GBLOCK"):

                active_groups = set()

                continue


            if not active_groups:
                continue


            card = get_card_name(
                line
            )


            if not is_target_element(
                card
            ):
                continue


            eid = get_second_field_id(
                line
            )


            if eid is None:
                continue


            for group_name in active_groups:

                group_elements[
                    group_name
                ].add(
                    eid
                )


    return {

        "CCO_":
            len(group_elements["CCO_"]),

        "S/M_":
            len(group_elements["S/M_"]),

        "M/M_":
            len(group_elements["M/M_"]),

    }


# ============================================================
# COUNT GRID OF TANTAI SUBMODELS UNDER 01_EX_ASSY
# ============================================================

def count_ex_tantai_grids(nas_file):

    # ========================================================
    # Get TANTAI submodels under 01_EX_ASSY
    # ========================================================

    tantai_submodels = (
        find_ex_tantai_submodels(
            nas_file
        )
    )


    # ========================================================
    # Unique GRID IDs
    # ========================================================

    grid_ids = set()


    # Current GBLOCK is a target TANTAI block?
    active_grid_block = False


    with open(
        nas_file,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        for line in f:

            stripped = line.strip()


            # ==================================================
            # START GBLOCK
            #
            # Example:
            #
            # $GBLOCK S24_TANTAI_13R-11_690g
            # ==================================================

            if stripped.upper().startswith("$GBLOCK"):

                block_name = get_block_name(
                    line,
                    "$GBLOCK"
                )

                active_grid_block = (
                    block_name
                    in tantai_submodels
                )

                continue


            # ==================================================
            # DBLOCK starts -> GBLOCK has ended
            # ==================================================

            if stripped.upper().startswith("$DBLOCK"):

                active_grid_block = False

                continue


            # ==================================================
            # Not a target TANTAI GBLOCK
            # ==================================================

            if not active_grid_block:
                continue


            # ==================================================
            # Only GRID
            # ==================================================

            card = get_card_name(
                line
            )

            if card != "GRID":
                continue


            # ==================================================
            # GRID ID
            # ==================================================

            gid = get_second_field_id(
                line
            )

            if gid is None:
                continue


            grid_ids.add(
                gid
            )


    return len(
        grid_ids
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
        # LOCAL / NETWORK FILE
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
        # ELEMENT COUNTS
        # ====================================================

        element_results = (
            count_group_elements(
                nas_file
            )
        )


        # ====================================================
        # TANTAI GRID COUNT IN 01_EX_ASSY
        # ====================================================

        tantai_grids = (
            count_ex_tantai_grids(
                nas_file
            )
        )


        # ====================================================
        # OUTPUT
        # ====================================================

        print(
            f"CCO_ : {element_results['CCO_']}"
        )

        print(
            f"S/M_ : {element_results['S/M_']}"
        )

        print(
            f"M/M_ : {element_results['M/M_']}"
        )

        print(
            f"01_EX_ASSY TANTAI GRID : {tantai_grids}"
        )


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
