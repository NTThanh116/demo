import os
import tempfile
import urllib.request


# ============================================================
# 2D SHELL + 3D SOLID ELEMENT TYPES
# ============================================================

SHELL_ELEMENTS = {
    "CTRIA3",
    "CTRIA6",
    "CTRIAR",
    "CQUAD4",
    "CQUAD8",
    "CQUADR",
    "CSHEAR",
}

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
# DOWNLOAD NAS FILE IF INPUT IS URL
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
# GET DBLOCK NAME
# ============================================================

def get_dblock_name(line):
    """
    Examples:

        $DBLOCK CCO_1760g
        $DBLOCK 1501_CCO_SHELL

    Returns:

        CCO_1760g
        1501_CCO_SHELL
    """

    stripped = line.strip()

    if not stripped.upper().startswith("$DBLOCK"):
        return None

    parts = stripped.split()

    if len(parts) < 2:
        return None

    return parts[1]


# ============================================================
# GET NASTRAN CARD NAME
# ============================================================

def get_card_name(line):
    """
    Supports:

        CQUAD4  12080 1501 ...
        CQUAD4,12080,1501,...
        CQUAD4* 12080 ...

    Returns:

        CQUAD4
    """

    stripped = line.strip()

    if not stripped:
        return None

    # Ignore comments
    if stripped.startswith("$"):
        return None

    # Ignore continuation lines
    if stripped.startswith("+"):
        return None

    # Free-field Nastran
    if "," in stripped:

        card = stripped.split(",", 1)[0].strip()

    # Fixed / whitespace field
    else:

        parts = stripped.split()

        if not parts:
            return None

        card = parts[0]

    # Large-field:
    # CQUAD4* -> CQUAD4
    card = card.rstrip("*").upper()

    return card


# ============================================================
# GET ELEMENT ID
# ============================================================

def get_element_id(line):
    """
    Examples:

        CQUAD4  12080 1501 ...
                 ^^^^^
                  EID

        CQUAD4,12080,1501,...
               ^^^^^
                EID
    """

    stripped = line.strip()

    try:

        # Free-field format
        if "," in stripped:

            fields = stripped.split(",")

            return int(fields[1].strip())

        # Fixed / whitespace format
        else:

            fields = stripped.split()

            return int(fields[1])

    except (ValueError, IndexError):

        return None


# ============================================================
# COUNT ELEMENTS IN ALL CCO_* BLOCKS
# ============================================================

def count_cco_elements(nas_file):

    # Store unique Element IDs
    # Prevent duplicate counting
    element_ids = set()

    # Are we currently inside a CCO structure?
    inside_cco = False

    with open(
        nas_file,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        for line in file:

            stripped = line.strip()

            # ==================================================
            # DBLOCK
            # ==================================================

            if stripped.upper().startswith("$DBLOCK"):

                block_name = get_dblock_name(line)

                if block_name is None:
                    continue

                block_upper = block_name.upper()


                # ==============================================
                # START OF CCO
                #
                # Example:
                #
                # $DBLOCK CCO_1760g
                # ==============================================

                if block_upper.startswith("CCO_"):

                    inside_cco = True

                    continue


                # ==============================================
                # SUB-BLOCK BELONGING TO CCO
                #
                # Examples:
                #
                # $DBLOCK 1501_CCO_SHELL
                # $DBLOCK 1502_CCO_SHELL
                # $DBLOCK 2001_CCO_SOLID
                #
                # Keep inside_cco = True
                # ==============================================

                if inside_cco:

                    if "CCO" in block_upper:

                        continue

                    else:

                        # New unrelated DBLOCK
                        # End current CCO
                        inside_cco = False

                        continue


            # ==================================================
            # SKIP IF NOT INSIDE CCO
            # ==================================================

            if not inside_cco:
                continue


            # ==================================================
            # GET NASTRAN CARD
            # ==================================================

            card = get_card_name(line)

            if card is None:
                continue


            # ==================================================
            # ONLY COUNT:
            #
            # 2D SHELL
            # 3D SOLID
            #
            # GRID / RBE / BAR / BEAM etc. are ignored
            # ==================================================

            if card not in ELEMENT_TYPES:
                continue


            # ==================================================
            # GET ELEMENT ID
            # ==================================================

            eid = get_element_id(line)

            if eid is None:
                continue


            # ==================================================
            # STORE UNIQUE ELEMENT
            # ==================================================

            element_ids.add(eid)


    # ========================================================
    # TOTAL NUMBER OF UNIQUE ELEMENTS
    # ========================================================

    return len(element_ids)


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # INPUT
    #
    # OPTION 1:
    # Local NAS file
    #
    # nas_source = r"C:\CAE\model.nas"
    #
    # OPTION 2:
    # URL
    #
    # nas_source = "https://example.com/model.nas"
    # ========================================================

    nas_source = r"C:\CAE\model.nas"


    temp_file = None

    try:

        # ====================================================
        # DOWNLOAD IF URL
        # ====================================================

        if is_url(nas_source):

            temp_file = download_nas(nas_source)

            nas_file = temp_file


        # ====================================================
        # LOCAL FILE
        # ====================================================

        else:

            nas_file = nas_source

            if not os.path.isfile(nas_file):

                raise FileNotFoundError(
                    f"File not found: {nas_file}"
                )


        # ====================================================
        # COUNT ELEMENTS
        # ====================================================

        total_elements = count_cco_elements(nas_file)


        # ====================================================
        # OUTPUT
        #
        # ONLY PRINT TOTAL NUMBER
        # ====================================================

        print(total_elements)


    finally:

        # ====================================================
        # DELETE TEMP FILE IF DOWNLOADED
        # ====================================================

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
