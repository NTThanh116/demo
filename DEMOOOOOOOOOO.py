import os
import tempfile
import urllib.request


# ============================================================
# ELEMENT TYPES TO COUNT
# ============================================================

# 2D SHELL
SHELL_ELEMENTS = {
    "CTRIA3",
    "CTRIA6",
    "CTRIAR",
    "CQUAD4",
    "CQUAD8",
    "CQUADR",
    "CSHEAR",
}

# 3D SOLID
SOLID_ELEMENTS = {
    "CTETRA",
    "CPENTA",
    "CHEXA",
    "CPYRAM",
}

ELEMENT_TYPES = SHELL_ELEMENTS | SOLID_ELEMENTS


# ============================================================
# CHECK IF SOURCE IS URL
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
# GET DBLOCK NAME
# ============================================================

def get_dblock_name(line):
    """
    Examples:

        $DBLOCK CCO_1760g
        $DBLOCK 1501_CCO_SHELL
        $DBLOCK S24_TANTAI_13R-11_690g

    Returns block name.
    """

    stripped = line.strip()

    if not stripped.upper().startswith("$DBLOCK"):
        return None

    parts = stripped.split(maxsplit=1)

    if len(parts) < 2:
        return None

    return parts[1].strip()


# ============================================================
# GET NASTRAN CARD NAME
# ============================================================

def get_card_name(line):
    """
    Examples:

        CQUAD4  12080 1501 ...
        CTRIA3  13000 1501 ...
        CHEXA   20000 2001 ...
        CTETRA  30000 2002 ...

    Also supports free-field:

        CQUAD4,12080,1501,...

    and large-field:

        CHEXA*  20000 ...
    """

    stripped = line.strip()

    if not stripped:
        return None

    # Ignore comment / metadata
    if stripped.startswith("$"):
        return None

    # Ignore continuation lines
    if stripped.startswith("+"):
        return None

    # --------------------------------------------
    # Free-field format
    # --------------------------------------------

    if "," in stripped:

        card = stripped.split(",", 1)[0].strip()

    # --------------------------------------------
    # Fixed / whitespace format
    # --------------------------------------------

    else:

        parts = stripped.split()

        if not parts:
            return None

        card = parts[0]

    # Large-field:
    #
    # CHEXA* -> CHEXA
    # CTETRA* -> CTETRA

    card = card.rstrip("*").upper()

    return card


# ============================================================
# GET ELEMENT ID
# ============================================================

def get_element_id(line):
    """
    Extract Element ID.

    Example:

        CQUAD4 12080 1501 ...
               ^^^^^

        CHEXA  20001 2001 ...
               ^^^^^
    """

    stripped = line.strip()

    try:

        # --------------------------------------------
        # Free-field
        # --------------------------------------------

        if "," in stripped:

            fields = stripped.split(",")

            return int(fields[1].strip())

        # --------------------------------------------
        # Fixed / whitespace
        # --------------------------------------------

        else:

            fields = stripped.split()

            return int(fields[1])

    except (ValueError, IndexError):

        return None


# ============================================================
# COUNT ELEMENTS
# ============================================================

def count_cco_elements(nas_file):

    # ========================================================
    # Store unique Element IDs
    #
    # Prevent same element from being counted twice
    # ========================================================

    element_ids = set()


    # ========================================================
    # False until first:
    #
    # $DBLOCK CCO_xxx
    #
    # is found
    # ========================================================

    inside_cco = False


    with open(
        nas_file,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        for line in f:

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
                # FOUND CCO PARENT
                #
                # Example:
                #
                # $DBLOCK CCO_1760g
                #
                # Start counting from here
                # ==============================================

                if block_upper.startswith("CCO_"):

                    inside_cco = True

                    continue


                # ==============================================
                # IMPORTANT
                #
                # If already inside CCO:
                #
                # DO NOT turn it off here.
                #
                # Because these are children:
                #
                # $DBLOCK 1501_CCO_SHELL
                #
                # $DBLOCK S24_TANTAI_13R-11_690g
                #
                # Both belong to CCO_1760g.
                # ==============================================

                if inside_cco:

                    continue


            # ==================================================
            # NOT YET INSIDE CCO
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
            # ONLY COUNT 2D SHELL + 3D SOLID
            #
            # GRID     -> ignored
            # RBE2     -> ignored
            # RBE3     -> ignored
            # CBAR     -> ignored
            # CBEAM    -> ignored
            # CBUSH    -> ignored
            # CONM2    -> ignored
            #
            # CQUAD*   -> counted
            # CTRIA*   -> counted
            # CHEXA    -> counted
            # CTETRA   -> counted
            # CPENTA   -> counted
            # CPYRAM   -> counted
            # ==================================================

            if card not in ELEMENT_TYPES:
                continue


            # ==================================================
            # ELEMENT ID
            # ==================================================

            eid = get_element_id(line)

            if eid is None:
                continue


            # ==================================================
            # ADD UNIQUE ELEMENT
            # ==================================================

            element_ids.add(eid)


    # ========================================================
    # RETURN TOTAL
    # ========================================================

    return len(element_ids)


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # INPUT FILE
    # ========================================================
    #
    # Local:
    #
    # nas_source = r"C:\CAE\model.nas"
    #
    # Network:
    #
    # nas_source = r"\\server\project\model.nas"
    #
    # URL:
    #
    # nas_source = "https://example.com/model.nas"
    #
    # ========================================================

    nas_source = r"C:\CAE\model.nas"


    temp_file = None


    try:

        # ====================================================
        # URL
        # ====================================================

        if is_url(nas_source):

            temp_file = download_nas(nas_source)

            nas_file = temp_file


        # ====================================================
        # LOCAL / NETWORK FILE
        # ====================================================

        else:

            nas_file = nas_source

            if not os.path.isfile(nas_file):

                raise FileNotFoundError(
                    f"File not found: {nas_file}"
                )


        # ====================================================
        # COUNT
        # ====================================================

        total_elements = count_cco_elements(nas_file)


        # ====================================================
        # OUTPUT
        #
        # ONLY TOTAL NUMBER
        # ====================================================

        print(total_elements)


    finally:

        # ====================================================
        # DELETE TEMPORARY DOWNLOAD
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
