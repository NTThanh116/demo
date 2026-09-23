import os
import re
import tempfile
import urllib.request
from urllib.parse import urlparse


# ============================================================
# ELEMENT TYPES TO COUNT
# ============================================================

# 2D shell elements
SHELL_ELEMENTS = {
    "CTRIA3",
    "CTRIA6",
    "CTRIAR",
    "CQUAD4",
    "CQUAD8",
    "CQUADR",
    "CSHEAR",
}

# 3D solid elements
SOLID_ELEMENTS = {
    "CTETRA",
    "CPENTA",
    "CHEXA",
    "CPYRAM",
}

ELEMENT_TYPES = SHELL_ELEMENTS | SOLID_ELEMENTS


# ============================================================
# CHECK IF INPUT IS URL
# ============================================================

def is_url(path):
    parsed = urlparse(path)
    return parsed.scheme in ("http", "https")


# ============================================================
# DOWNLOAD .NAS FILE
# ============================================================

def download_nas(url):
    """
    Download .nas file from a direct URL.
    Returns temporary local file path.
    """

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".nas",
        delete=False
    )

    temp_path = temp_file.name
    temp_file.close()

    urllib.request.urlretrieve(url, temp_path)

    return temp_path


# ============================================================
# GET NASTRAN CARD NAME
# ============================================================

def get_card_name(line):
    """
    Extract Nastran card name.

    Supports:

    Fixed field:
        CQUAD4  1001 ...

    Large field:
        CQUAD4* 1001 ...

    Free field:
        CQUAD4,1001,...
    """

    stripped = line.strip()

    if not stripped:
        return None

    # Ignore comment lines
    if stripped.startswith("$"):
        return None

    # Continuation line
    if stripped.startswith("+") or stripped.startswith("*"):
        return None

    # Free-field format
    if "," in stripped:
        card = stripped.split(",", 1)[0].strip()

    # Fixed-field format
    else:
        parts = stripped.split()

        if not parts:
            return None

        card = parts[0]

    # Example:
    # CQUAD4* -> CQUAD4
    card = card.rstrip("*").upper()

    return card


# ============================================================
# EXTRACT DSTRCT NAME
# ============================================================

def get_dstrct_name(line):
    """
    Example:

        $DSTRCT 2 CCO_1760g

    returns:

        CCO_1760g
    """

    stripped = line.strip()

    if not stripped.upper().startswith("$DSTRCT"):
        return None

    parts = stripped.split()

    if len(parts) < 3:
        return None

    return parts[-1]


# ============================================================
# COUNT ELEMENTS IN CCO_* STRUCTURES
# ============================================================

def count_cco_elements(nas_file):

    total = 0

    # Keep unique element IDs to avoid accidental double counting
    counted_elements = set()

    current_is_cco = False

    with open(
        nas_file,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        for line in f:

            stripped = line.strip()

            # ==================================================
            # Detect structure
            # ==================================================

            if stripped.upper().startswith("$DSTRCT"):

                structure_name = get_dstrct_name(line)

                if structure_name is None:
                    current_is_cco = False
                    continue

                current_is_cco = (
                    structure_name.upper().startswith("CCO_")
                )

                continue

            # ==================================================
            # We only care about CCO_*
            # ==================================================

            if not current_is_cco:
                continue

            # ==================================================
            # Read Nastran element card
            # ==================================================

            card = get_card_name(line)

            if card not in ELEMENT_TYPES:
                continue

            # ==================================================
            # Get Element ID
            # ==================================================

            try:

                if "," in line:
                    fields = line.split(",")
                    eid = int(fields[1].strip())

                else:
                    # Standard Nastran fixed-field:
                    #
                    # columns 1-8   = card
                    # columns 9-16  = EID

                    eid_field = line[8:16].strip()

                    if eid_field:
                        eid = int(eid_field)

                    else:
                        # Fallback for whitespace-separated files
                        fields = line.split()
                        eid = int(fields[1])

            except (ValueError, IndexError):

                # If EID cannot be read,
                # count the physical card instead
                total += 1
                continue

            # ==================================================
            # Prevent duplicate EID
            # ==================================================

            key = (card, eid)

            if key not in counted_elements:

                counted_elements.add(key)
                total += 1

    return total


# ============================================================
# MAIN FUNCTION
# ============================================================

def main():

    # --------------------------------------------------------
    # Put your .nas path OR direct URL here
    # --------------------------------------------------------

    nas_source = r"C:\CAE\model.nas"

    # Example direct URL:
    #
    # nas_source = "https://example.com/model.nas"


    downloaded_file = None

    try:

        # ====================================================
        # URL
        # ====================================================

        if is_url(nas_source):

            downloaded_file = download_nas(nas_source)

            nas_file = downloaded_file

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
        # COUNT
        # ====================================================

        total_elements = count_cco_elements(nas_file)

        # ====================================================
        # ONLY OUTPUT
        # ====================================================

        print(total_elements)


    finally:

        # Delete temporary downloaded file
        if downloaded_file:

            try:
                os.remove(downloaded_file)

            except OSError:
                pass


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
