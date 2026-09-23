import os
import tempfile
import urllib.request


# ============================================================
# INPUT
# ============================================================

# Local file:
NAS_SOURCE = r"M:\Technstar\07_Personal\Ikeda\01_Macro_PSJ\CoG\data\CCO.nas"

# Or direct URL:
# NAS_SOURCE = "https://example.com/CCO.nas"


# ============================================================
# ELEMENT TYPES
# ============================================================

# 2D shell
SHELL_ELEMENTS = {
    "CTRIA3",
    "CTRIA6",
    "CTRIAR",
    "CQUAD4",
    "CQUAD8",
    "CQUADR",
    "CSHEAR",
}

# 3D solid
SOLID_ELEMENTS = {
    "CTETRA",
    "CPENTA",
    "CHEXA",
    "CPYRAM",
}

ELEMENT_TYPES = SHELL_ELEMENTS | SOLID_ELEMENTS


# ============================================================
# CHECK URL
# ============================================================

def is_url(source):
    return source.lower().startswith(("http://", "https://"))


# ============================================================
# DOWNLOAD NAS FILE
# ============================================================

def download_nas(url):

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".nas",
        delete=False
    )

    temp_path = temp_file.name
    temp_file.close()

    urllib.request.urlretrieve(url, temp_path)

    return temp_path


# ============================================================
# NORMALIZE NAME
# ============================================================

def normalize_name(name):
    """
    Normalize DBLOCK / DSTRCT name for comparison.
    """

    return name.strip().upper()


# ============================================================
# READ $DSTRCT HIERARCHY
# ============================================================

def read_dstrct(nas_file):
    """
    Example input:

        $DSTRCT 1  02_FR_ASSY
        $DSTRCT 2  CCO_1760g
        $DSTRCT 3  1501_CCO_SHELL
        $DSTRCT 3  S24_TANTAI_13R-11_690g
        $DSTRCT 2  S/M_2310g

    Returns:

        [
            (1, "02_FR_ASSY"),
            (2, "CCO_1760g"),
            (3, "1501_CCO_SHELL"),
            (3, "S24_TANTAI_13R-11_690g"),
            (2, "S/M_2310g")
        ]
    """

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

            # Example:
            #
            # $DSTRCT 3 S24_TANTAI_13R-11_690g
            #
            parts = stripped.split(maxsplit=2)

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
# FIND ALL SUBMODELS INSIDE CCO_xxx
# ============================================================

def find_cco_submodels(nas_file):
    """
    Example:

        $DSTRCT 2 CCO_1760g
        $DSTRCT 3 1501_CCO_SHELL
        $DSTRCT 3 S24_TANTAI_13R-11_690g
        $DSTRCT 2 S/M_2310g

    Result:

        {
            "1501_CCO_SHELL",
            "S24_TANTAI_13R-11_690G"
        }

    All descendants are included, not only direct children.

    Example:

        level 2 CCO
            level 3 child
                level 4 child
                level 4 child
            level 3 child

    All level 3 and level 4 structures are included.
    """

    structures = read_dstrct(nas_file)

    target_submodels = set()

    for i, (cco_level, cco_name) in enumerate(structures):

        # ----------------------------------------------------
        # Find CCO_xxx
        # ----------------------------------------------------

        if not normalize_name(cco_name).startswith("CCO_"):
            continue

        # ----------------------------------------------------
        # Everything below CCO with a higher level belongs
        # to this CCO.
        #
        # Stop when level <= CCO level.
        # ----------------------------------------------------

        for j in range(i + 1, len(structures)):

            child_level, child_name = structures[j]

            if child_level <= cco_level:
                break

            target_submodels.add(
                normalize_name(child_name)
            )

    return target_submodels


# ============================================================
# GET $DBLOCK NAME
# ============================================================

def get_dblock_name(line):
    """
    Example:

        $DBLOCK 1501_CCO_SHELL

    returns:

        1501_CCO_SHELL
    """

    stripped = line.strip()

    if not stripped.upper().startswith("$DBLOCK"):
        return None

    parts = stripped.split(maxsplit=1)

    if len(parts) < 2:
        return None

    return normalize_name(parts[1])


# ============================================================
# GET NASTRAN CARD NAME
# ============================================================

def get_card_name(line):
    """
    Supports:

        CQUAD4 12080 1501 ...
        CQUAD4,12080,1501,...
        CHEXA* 20000 ...
    """

    stripped = line.strip()

    if not stripped:
        return None

    # Metadata / comments
    if stripped.startswith("$"):
        return None

    # Continuation line
    if stripped.startswith("+"):
        return None

    # Large-field continuation line
    if stripped.startswith("*"):
        return None

    # --------------------------------------------------------
    # Free-field format
    # --------------------------------------------------------

    if "," in stripped:

        card = stripped.split(",", 1)[0].strip()

    # --------------------------------------------------------
    # Fixed / whitespace format
    # --------------------------------------------------------

    else:

        parts = stripped.split()

        if not parts:
            return None

        card = parts[0]

    # Example:
    #
    # CHEXA* -> CHEXA
    #
    return card.rstrip("*").upper()


# ============================================================
# GET ELEMENT ID
# ============================================================

def get_element_id(line):
    """
    Example:

        CQUAD4 12080 1501 ...
               ^^^^^
               EID
    """

    stripped = line.strip()

    try:

        # ----------------------------------------------------
        # Free-field
        # ----------------------------------------------------

        if "," in stripped:

            fields = stripped.split(",")

            return int(fields[1].strip())

        # ----------------------------------------------------
        # Fixed / whitespace
        # ----------------------------------------------------

        fields = stripped.split()

        return int(fields[1])

    except (ValueError, IndexError):

        return None


# ============================================================
# COUNT CCO ELEMENTS
# ============================================================

def count_cco_elements(nas_file):

    # --------------------------------------------------------
    # STEP 1:
    # Find ALL submodels belonging to CCO_xxx
    # --------------------------------------------------------

    target_submodels = find_cco_submodels(
        nas_file
    )

    # --------------------------------------------------------
    # Store unique element IDs.
    #
    # Avoid double counting if same element appears twice.
    # --------------------------------------------------------

    element_ids = set()

    # --------------------------------------------------------
    # Is current $DBLOCK one of the target submodels?
    # --------------------------------------------------------

    active_block = False

    with open(
        nas_file,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        for line in f:

            stripped = line.strip()

            # =================================================
            # NEW DBLOCK
            # =================================================

            if stripped.upper().startswith("$DBLOCK"):

                block_name = get_dblock_name(line)

                if block_name is None:

                    active_block = False

                else:

                    active_block = (
                        block_name in target_submodels
                    )

                continue

            # =================================================
            # GBLOCK = GRID / node block
            #
            # Element section has ended.
            # =================================================

            if stripped.upper().startswith("$GBLOCK"):

                active_block = False

                continue

            # =================================================
            # Not one of the CCO submodels
            # =================================================

            if not active_block:
                continue

            # =================================================
            # GET CARD
            # =================================================

            card = get_card_name(line)

            if card is None:
                continue

            # =================================================
            # ONLY 2D SHELL + 3D SOLID
            # =================================================

            if card not in ELEMENT_TYPES:
                continue

            # =================================================
            # GET ELEMENT ID
            # =================================================

            eid = get_element_id(line)

            if eid is None:
                continue

            # =================================================
            # ADD UNIQUE ELEMENT
            # =================================================

            element_ids.add(eid)

    return len(element_ids)


# ============================================================
# MAIN
# ============================================================

def main():

    temp_file = None

    try:

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        if is_url(NAS_SOURCE):

            temp_file = download_nas(
                NAS_SOURCE
            )

            nas_file = temp_file

        # ----------------------------------------------------
        # LOCAL / NETWORK FILE
        # ----------------------------------------------------

        else:

            nas_file = NAS_SOURCE

            if not os.path.isfile(nas_file):

                raise FileNotFoundError(
                    f"File not found: {nas_file}"
                )

        # ----------------------------------------------------
        # COUNT
        # ----------------------------------------------------

        total_elements = count_cco_elements(
            nas_file
        )

        # ----------------------------------------------------
        # ONLY OUTPUT
        # ----------------------------------------------------

        print(total_elements)

    finally:

        # ----------------------------------------------------
        # DELETE TEMPORARY DOWNLOAD
        # ----------------------------------------------------

        if temp_file is not None:

            try:
                os.remove(temp_file)

            except OSError:
                pass


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
