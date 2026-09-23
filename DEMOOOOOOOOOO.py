import os
import tempfile
import urllib.request


# ============================================================
# INPUT
# ============================================================

NAS_SOURCE = r"M:\Technstar\07_Personal\Ikeda\01_Macro_PSJ\CoG\data\model.nas"

# Nếu muốn dùng URL:
# NAS_SOURCE = "https://example.com/model.nas"


# ============================================================
# OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR = r"M:\Technstar\07_Personal\Ikeda\01_Macro_PSJ\CoG\data\split_models"


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
# PARSE DSTRCT
# ============================================================

def parse_dstrct_line(line):

    stripped = line.strip()

    if not stripped.upper().startswith("$DSTRCT"):
        return None

    parts = stripped.split(
        maxsplit=2
    )

    if len(parts) < 3:
        return None

    try:

        level = int(
            parts[1]
        )

    except ValueError:

        return None

    name = parts[2].strip()

    return (
        level,
        name
    )


# ============================================================
# READ DSTRCT HIERARCHY
# ============================================================

def read_dstrct(lines):

    structures = []

    for line_index, line in enumerate(lines):

        result = parse_dstrct_line(
            line
        )

        if result is None:
            continue

        level, name = result

        structures.append(
            {
                "line_index": line_index,
                "level": level,
                "name": name,
                "name_norm": normalize_name(name),
            }
        )

    return structures


# ============================================================
# GET DESCENDANTS
# ============================================================

def get_descendants(
    structures,
    parent_index
):

    """
    Example:

    level 2 CCO
        level 3 A
        level 3 B
            level 4 C
    level 2 NEXT

    Result:
        A
        B
        C
    """

    parent = structures[
        parent_index
    ]

    parent_level = parent[
        "level"
    ]

    descendants = []

    for i in range(
        parent_index + 1,
        len(structures)
    ):

        item = structures[i]

        if item["level"] <= parent_level:

            break

        descendants.append(
            item
        )

    return descendants


# ============================================================
# FIND GROUP:
#
# CCO_
# S/M_
# M/M_
# ============================================================

def find_prefix_group(
    structures,
    prefix
):

    """
    Return all parent + descendant model names
    belonging to the requested prefix.
    """

    prefix = normalize_name(
        prefix
    )

    selected = set()

    for i, item in enumerate(
        structures
    ):

        if not item[
            "name_norm"
        ].startswith(prefix):

            continue


        # ====================================================
        # Include parent itself
        # ====================================================

        selected.add(
            item["name_norm"]
        )


        # ====================================================
        # Include all descendants
        # ====================================================

        descendants = get_descendants(
            structures,
            i
        )

        for child in descendants:

            selected.add(
                child["name_norm"]
            )

    return selected


# ============================================================
# FIND TANTAI UNDER 01_EX_ASSY
# ============================================================

def find_ex_tantai_group(
    structures
):

    """
    Find:

        01_EX_ASSY

    then search all descendants containing:

        TANTAI

    For every TANTAI model found, include:

        TANTAI parent itself
        +
        all its descendants
    """

    selected = set()


    # ========================================================
    # Find every 01_EX_ASSY
    # ========================================================

    for ex_index, ex_item in enumerate(
        structures
    ):

        if ex_item[
            "name_norm"
        ] != "01_EX_ASSY":

            continue


        ex_level = ex_item[
            "level"
        ]


        # ====================================================
        # Search inside 01_EX_ASSY only
        # ====================================================

        i = ex_index + 1

        while i < len(structures):

            item = structures[i]


            # End of 01_EX_ASSY
            if item["level"] <= ex_level:

                break


            # =================================================
            # Found TANTAI
            # =================================================

            if "TANTAI" in item[
                "name_norm"
            ]:

                selected.add(
                    item["name_norm"]
                )


                # =============================================
                # Also include everything below this TANTAI
                # =============================================

                descendants = get_descendants(
                    structures,
                    i
                )

                for child in descendants:

                    selected.add(
                        child["name_norm"]
                    )


            i += 1


    return selected


# ============================================================
# FIND ANCESTORS
# ============================================================

def find_ancestor_names(
    structures,
    selected_names
):

    """
    Keep parent hierarchy in the output DSTRCT.

    Example:

    01_EX_ASSY
        ABC
            ABC_TANTAI

    If ABC_TANTAI is selected,
    keep 01_EX_ASSY and ABC too.
    """

    keep_names = set(
        selected_names
    )

    stack = []


    for item in structures:

        level = item[
            "level"
        ]


        # Remove stack entries at same/deeper level
        while stack and (
            stack[-1]["level"] >= level
        ):

            stack.pop()


        if item[
            "name_norm"
        ] in selected_names:

            # Add all ancestors
            for ancestor in stack:

                keep_names.add(
                    ancestor[
                        "name_norm"
                    ]
                )


        stack.append(
            item
        )


    return keep_names


# ============================================================
# GET BLOCK NAME
# ============================================================

def get_named_block(line):

    """
    Returns:

        ("DBLOCK", "MODEL_NAME")

    or:

        ("GBLOCK", "MODEL_NAME")

    or None
    """

    stripped = line.strip()

    upper = stripped.upper()


    if upper.startswith("$DBLOCK"):

        parts = stripped.split(
            maxsplit=1
        )

        if len(parts) < 2:
            return None

        return (
            "DBLOCK",
            normalize_name(
                parts[1]
            )
        )


    if upper.startswith("$GBLOCK"):

        parts = stripped.split(
            maxsplit=1
        )

        if len(parts) < 2:
            return None

        return (
            "GBLOCK",
            normalize_name(
                parts[1]
            )
        )


    return None


# ============================================================
# FIND FIRST DATA BLOCK
# ============================================================

def find_first_block_index(lines):

    for i, line in enumerate(
        lines
    ):

        if get_named_block(
            line
        ) is not None:

            return i

    return len(lines)


# ============================================================
# FIND ENDDATA
# ============================================================

def find_enddata_index(
    lines,
    start_index
):

    for i in range(
        start_index,
        len(lines)
    ):

        if lines[
            i
        ].strip().upper().startswith(
            "ENDDATA"
        ):

            return i

    return len(lines)


# ============================================================
# SPLIT DBLOCK / GBLOCK SECTIONS
# ============================================================

def parse_named_blocks(
    lines,
    start_index,
    end_index
):

    """
    A block starts at:

        $DBLOCK name

    or:

        $GBLOCK name

    and ends when next DBLOCK/GBLOCK starts.
    """

    blocks = []

    current_start = None
    current_type = None
    current_name = None


    for i in range(
        start_index,
        end_index
    ):

        block_info = get_named_block(
            lines[i]
        )


        if block_info is None:
            continue


        # ====================================================
        # Close previous block
        # ====================================================

        if current_start is not None:

            blocks.append(
                {
                    "type":
                        current_type,

                    "name":
                        current_name,

                    "lines":
                        lines[
                            current_start:i
                        ]
                }
            )


        # ====================================================
        # Start new block
        # ====================================================

        current_start = i

        current_type, current_name = (
            block_info
        )


    # ========================================================
    # Last block
    # ========================================================

    if current_start is not None:

        blocks.append(
            {
                "type":
                    current_type,

                "name":
                    current_name,

                "lines":
                    lines[
                        current_start:
                        end_index
                    ]
            }
        )


    return blocks


# ============================================================
# FILTER PREFIX
# ============================================================

def build_filtered_prefix(
    prefix_lines,
    keep_hierarchy_names
):

    """
    Keep all global/common information.

    For $DSTRCT lines:
    only keep hierarchy relevant to current output model.
    """

    output = []


    for line in prefix_lines:

        dstrct = parse_dstrct_line(
            line
        )


        # ====================================================
        # Not a DSTRCT line
        #
        # Keep global/common data:
        #
        # MAT1
        # PSHELL
        # PSOLID
        # coordinate systems
        # comments
        # etc.
        # ====================================================

        if dstrct is None:

            output.append(
                line
            )

            continue


        # ====================================================
        # DSTRCT line
        # ====================================================

        level, name = dstrct

        if normalize_name(
            name
        ) in keep_hierarchy_names:

            output.append(
                line
            )


    return output


# ============================================================
# WRITE ONE OUTPUT MODEL
# ============================================================

def write_model_file(
    output_path,
    lines,
    structures,
    selected_names
):

    # ========================================================
    # Also preserve ancestors for DSTRCT hierarchy
    # ========================================================

    hierarchy_names = (
        find_ancestor_names(
            structures,
            selected_names
        )
    )


    # ========================================================
    # Locate data blocks
    # ========================================================

    first_block = (
        find_first_block_index(
            lines
        )
    )


    enddata_index = (
        find_enddata_index(
            lines,
            first_block
        )
    )


    # ========================================================
    # Prefix / common information
    # ========================================================

    prefix = lines[
        :first_block
    ]


    filtered_prefix = (
        build_filtered_prefix(
            prefix,
            hierarchy_names
        )
    )


    # ========================================================
    # DBLOCK / GBLOCK
    # ========================================================

    blocks = parse_named_blocks(
        lines,
        first_block,
        enddata_index
    )


    selected_blocks = []


    for block in blocks:

        if block[
            "name"
        ] in selected_names:

            selected_blocks.extend(
                block[
                    "lines"
                ]
            )


    # ========================================================
    # Footer
    # ========================================================

    footer = []

    if enddata_index < len(
        lines
    ):

        footer = lines[
            enddata_index:
        ]


    # ========================================================
    # Write
    # ========================================================

    with open(
        output_path,
        "w",
        encoding="utf-8",
        errors="ignore"
    ) as f:


        # Common/global information
        f.writelines(
            filtered_prefix
        )


        # Selected model blocks
        f.writelines(
            selected_blocks
        )


        # ENDDATA etc.
        f.writelines(
            footer
        )


# ============================================================
# MAIN SPLITTER
# ============================================================

def split_nas_models(
    nas_file,
    output_dir
):

    # ========================================================
    # Read source
    # ========================================================

    lines = read_lines(
        nas_file
    )


    structures = read_dstrct(
        lines
    )


    # ========================================================
    # MODEL 1 — CCO_
    # ========================================================

    cco_models = find_prefix_group(
        structures,
        "CCO_"
    )


    # ========================================================
    # MODEL 2 — S/M_
    # ========================================================

    sm_models = find_prefix_group(
        structures,
        "S/M_"
    )


    # ========================================================
    # MODEL 3 — M/M_
    # ========================================================

    mm_models = find_prefix_group(
        structures,
        "M/M_"
    )


    # ========================================================
    # MODEL 4 — TANTAI inside 01_EX_ASSY
    # ========================================================

    tantai_models = (
        find_ex_tantai_group(
            structures
        )
    )


    # ========================================================
    # Create output directory
    # ========================================================

    os.makedirs(
        output_dir,
        exist_ok=True
    )


    # ========================================================
    # Output files
    # ========================================================

    outputs = {

        "01_CCO.nas":
            cco_models,

        "02_SM.nas":
            sm_models,

        "03_MM.nas":
            mm_models,

        "04_EX_TANTAI.nas":
            tantai_models,

    }


    # ========================================================
    # Write
    # ========================================================

    for filename, selected_names in (
        outputs.items()
    ):


        output_path = os.path.join(
            output_dir,
            filename
        )


        write_model_file(
            output_path,
            lines,
            structures,
            selected_names
        )


        print(
            f"{filename:<20}"
            f" submodels = "
            f"{len(selected_names):>4}"
        )


    print()

    print(
        "Output folder:"
    )

    print(
        output_dir
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
        # LOCAL / NETWORK
        # ====================================================

        else:

            nas_file = NAS_SOURCE


            if not os.path.isfile(
                nas_file
            ):

                raise FileNotFoundError(
                    f"File not found: "
                    f"{nas_file}"
                )


        # ====================================================
        # SPLIT
        # ====================================================

        split_nas_models(
            nas_file,
            OUTPUT_DIR
        )


    finally:

        # ====================================================
        # Delete temporary download
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
