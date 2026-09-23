import os
import tempfile
import urllib.request


# ============================================================
# INPUT FILE
# ============================================================

# Local / network file:
NAS_SOURCE = r"M:\Technstar\07_Personal\Ikeda\01_Macro_PSJ\CoG\data\model.nas"

# Hoặc direct URL:
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
# CHECK URL
# ============================================================

def is_url(source):

    return source.lower().startswith(
        ("http://", "https://")
    )


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

    urllib.request.urlretrieve(
        url,
        temp_path
    )

    return temp_path


# ============================================================
# NORMALIZE NAME
# ============================================================

def normalize_name(name):

    return name.strip().upper()


# ============================================================
# READ $DSTRCT
# ============================================================

def read_dstrct(nas_file):

    """
    Example:

    $DSTRCT 1  02_FR_ASSY

    $DSTRCT 2  CCO_1760g
    $DSTRCT 3  1501_CCO_SHELL
    $DSTRCT 3  S24_TANTAI_13R-11_690g

    $DSTRCT 2  S/M_2310g
    $DSTRCT 3  SUBMODEL_A
    $DSTRCT 3  SUBMODEL_B

    $DSTRCT 2  M/M_1500g
    $DSTRCT 3  SUBMODEL_C
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

            # --------------------------------------------
            # Split:
            #
            # $DSTRCT 3 SUBMODEL_NAME
            #
            # --------------------------------------------

            parts = stripped.split(
                maxsplit=2
            )

            if len(parts) < 3:
                continue


            # --------------------------------------------
            # Get hierarchy level
            # --------------------------------------------

            try:

                level = int(
                    parts[1]
                )

            except ValueError:

                continue


            # --------------------------------------------
            # Structure name
            # --------------------------------------------

            name = parts[2].strip()


            structures.append(
                (
                    level,
                    name
                )
            )


    return structures


# ============================================================
# DETECT GROUP
# ============================================================

def get_group_type(name):

    name_upper = normalize_name(
        name
    )


    if name_upper.startswith("CCO_"):
        return "CCO_"


    if name_upper.startswith("S/M_"):
        return "S/M_"


    if name_upper.startswith("M/M_"):
        return "M/M_"


    return None


# ============================================================
# FIND ALL SUBMODELS UNDER EACH GROUP
# ============================================================

def find_group_submodels(nas_file):

    """
    Example hierarchy:

    $DSTRCT 2 CCO_1760g
    $DSTRCT 3 1501_CCO_SHELL
    $DSTRCT 3 S24_TANTAI_13R-11_690g

    $DSTRCT 2 S/M_2310g
    $DSTRCT 3 AAA
    $DSTRCT 3 BBB

    $DSTRCT 2 M/M_1500g
    $DSTRCT 3 CCC


    Result:

    CCO_:
        CCO_1760g
        1501_CCO_SHELL
        S24_TANTAI_13R-11_690g

    S/M_:
        S/M_2310g
        AAA
        BBB

    M/M_:
        M/M_1500g
        CCC
    """

    structures = read_dstrct(
        nas_file
    )


    groups = {

        "CCO_": set(),

        "S/M_": set(),

        "M/M_": set(),

    }


    # ========================================================
    # Go through DSTRCT hierarchy
    # ========================================================

    for i, (
        parent_level,
        parent_name
    ) in enumerate(structures):


        # ----------------------------------------------------
        # Is this CCO_, S/M_ or M/M_ ?
        # ----------------------------------------------------

        group_type = get_group_type(
            parent_name
        )


        if group_type is None:
            continue


        # ----------------------------------------------------
        # Include parent itself
        # ----------------------------------------------------

        groups[
            group_type
        ].add(
            normalize_name(
                parent_name
            )
        )


        # ----------------------------------------------------
        # Find ALL descendants
        #
        # Example:
        #
        # Level 2 Parent
        #
        #     Level 3 Child
        #
        #         Level 4 Child
        #
        #     Level 3 Child
        #
        # Level 2 <-- STOP
        #
        # ----------------------------------------------------

        for j in range(
            i + 1,
            len(structures)
        ):

            child_level, child_name = (
                structures[j]
            )


            # --------------------------------------------
            # End of current parent
            # --------------------------------------------

            if child_level <= parent_level:

                break


            # --------------------------------------------
            # Child / descendant belongs to parent
            # --------------------------------------------

            groups[
                group_type
            ].add(
                normalize_name(
                    child_name
                )
            )


    return groups


# ============================================================
# GET $DBLOCK NAME
# ============================================================

def get_dblock_name(line):

    """
    Example:

    $DBLOCK 1501_CCO_SHELL

    -> 1501_CCO_SHELL
    """

    stripped = line.strip()


    if not stripped.upper().startswith("$DBLOCK"):

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
# GET NASTRAN CARD NAME
# ============================================================

def get_card_name(line):

    """
    Supports:

    CQUAD4 12080 1501 ...
    CTRIA3 12081 1501 ...
    CHEXA  20000 2001 ...
    CTETRA 30000 2002 ...

    Free-field:

    CQUAD4,12080,1501,...

    Large field:

    CHEXA* ...
    """

    stripped = line.strip()


    # --------------------------------------------------------
    # Empty line
    # --------------------------------------------------------

    if not stripped:

        return None


    # --------------------------------------------------------
    # Comment / metadata
    # --------------------------------------------------------

    if stripped.startswith("$"):

        return None


    # --------------------------------------------------------
    # Continuation
    # --------------------------------------------------------

    if stripped.startswith("+"):

        return None


    if stripped.startswith("*"):

        return None


    # --------------------------------------------------------
    # Free-field format
    # --------------------------------------------------------

    if "," in stripped:

        card = stripped.split(
            ",",
            1
        )[0].strip()


    # --------------------------------------------------------
    # Fixed / whitespace format
    # --------------------------------------------------------

    else:

        parts = stripped.split()


        if not parts:

            return None


        card = parts[0]


    # --------------------------------------------------------
    # Large field
    #
    # CHEXA* -> CHEXA
    # --------------------------------------------------------

    return card.rstrip("*").upper()


# ============================================================
# CHECK IF CARD SHOULD BE COUNTED
# ============================================================

def is_target_element(card):

    if card is None:

        return False


    # ========================================================
    # 2D SHELL
    # ========================================================

    # CQUAD4
    # CQUAD8
    # CQUADR
    # etc.

    if card.startswith("CQUAD"):

        return True


    # CTRIA3
    # CTRIA6
    # CTRIAR
    # etc.

    if card.startswith("CTRIA"):

        return True


    # CSHEAR

    if card == "CSHEAR":

        return True


    # ========================================================
    # 3D SOLID
    # ========================================================

    if card in SOLID_ELEMENTS:

        return True


    # ========================================================
    # EVERYTHING ELSE IGNORED
    #
    # GRID
    # RBE2
    # RBE3
    # CBAR
    # CBEAM
    # CBUSH
    # CROD
    # CONM2
    # ...
    # ========================================================

    return False


# ============================================================
# GET ELEMENT ID
# ============================================================

def get_element_id(line):

    """
    Example:

    CQUAD4 12080 1501 ...
           ^^^^^
           EID

    CHEXA  20000 2001 ...
           ^^^^^
           EID
    """

    stripped = line.strip()


    try:

        # ====================================================
        # FREE FIELD
        #
        # CQUAD4,12080,1501,...
        # ====================================================

        if "," in stripped:

            fields = stripped.split(",")


            return int(
                fields[1].strip()
            )


        # ====================================================
        # WHITESPACE / FIXED FIELD
        # ====================================================

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
# COUNT ELEMENTS
# ============================================================

def count_group_elements(nas_file):

    # ========================================================
    # STEP 1:
    #
    # Get all submodels belonging to:
    #
    # CCO_
    # S/M_
    # M/M_
    # ========================================================

    group_submodels = (
        find_group_submodels(
            nas_file
        )
    )


    # ========================================================
    # Unique EID for each group
    # ========================================================

    group_elements = {

        "CCO_": set(),

        "S/M_": set(),

        "M/M_": set(),

    }


    # ========================================================
    # Current DBLOCK membership
    # ========================================================

    active_groups = set()


    # ========================================================
    # Read entire NAS
    # ========================================================

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


                block_name = get_dblock_name(
                    line
                )


                # Reset current active group
                active_groups = set()


                if block_name is not None:


                    # ------------------------------------------
                    # Determine which group owns this DBLOCK
                    # ------------------------------------------

                    for group_name, submodels in (
                        group_submodels.items()
                    ):


                        if block_name in submodels:


                            active_groups.add(
                                group_name
                            )


                continue


            # ==================================================
            # GBLOCK
            #
            # GRID/node section starts.
            # Stop counting current element block.
            # ==================================================

            if stripped.upper().startswith("$GBLOCK"):


                active_groups = set()


                continue


            # ==================================================
            # Current DBLOCK not part of target groups
            # ==================================================

            if not active_groups:

                continue


            # ==================================================
            # GET CARD
            # ==================================================

            card = get_card_name(
                line
            )


            # ==================================================
            # ONLY SHELL + SOLID
            # ==================================================

            if not is_target_element(
                card
            ):

                continue


            # ==================================================
            # ELEMENT ID
            # ==================================================

            eid = get_element_id(
                line
            )


            if eid is None:

                continue


            # ==================================================
            # ADD EID TO CORRESPONDING GROUP
            #
            # set() prevents duplicate EID
            # ==================================================

            for group_name in active_groups:


                group_elements[
                    group_name
                ].add(
                    eid
                )


    # ========================================================
    # FINAL COUNTS
    # ========================================================

    results = {

        "CCO_": len(
            group_elements["CCO_"]
        ),

        "S/M_": len(
            group_elements["S/M_"]
        ),

        "M/M_": len(
            group_elements["M/M_"]
        ),

    }


    return results


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
        # COUNT
        # ====================================================

        results = count_group_elements(
            nas_file
        )


        # ====================================================
        # OUTPUT
        # ====================================================

        print(
            f"CCO_ : {results['CCO_']}"
        )


        print(
            f"S/M_ : {results['S/M_']}"
        )


        print(
            f"M/M_ : {results['M/M_']}"
        )


    finally:


        # ====================================================
        # DELETE TEMPORARY DOWNLOAD
        # ====================================================

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
