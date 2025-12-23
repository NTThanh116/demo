import numpy as np
import re
import csv
import os
from tkinter import filedialog, Tk
from pyjdg import *
from pathlib import Path

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


# ============================================================
# PLOT
# ============================================================
def plot_results(nodes, elements, results, result_index=0, title='VALUE', cmap='jet'):
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    triangles = []
    colors = []
    centers = []
    labels = []

    for eid in sorted(elements.keys()):
        nids = elements[eid]
        if len(nids) == 3:
            tri = [nodes[nid] for nid in nids]
            triangles.append(tri)

            val = results.get(eid, (np.nan, np.nan))[result_index]
            colors.append(val)

            center = np.mean(tri, axis=0)
            centers.append(center)
            label = f"{val:.2f}" if not np.isnan(val) else "NaN"
            labels.append(label)

    poly_collection = Poly3DCollection(triangles, edgecolors='k')
    poly_collection.set_array(np.array(colors))
    poly_collection.set_cmap(cmap)
    poly_collection.set_clim(np.nanmin(colors), np.nanmax(colors))
    ax.add_collection3d(poly_collection)

    for center, label in zip(centers, labels):
        ax.text(center[0], center[1], center[2], label, fontsize=8, color='black')

    ax.auto_scale_xyz(*zip(*[pt for tri in triangles for pt in tri]))
    ax.set_title(title)
    fig.colorbar(poly_collection, ax=ax, label='value')

    plt.tight_layout()
    plt.show()


# ============================================================
# READ INP / CSV
# ============================================================
def read_nodes(inp_file):
    nodes = {}
    with open(inp_file, 'r') as f:
        lines = f.readlines()
    node_section = False
    for line in lines:
        if line.strip().startswith('*NODE'):
            node_section = True
            continue
        if node_section:
            if line.strip().startswith('**') or line.strip().startswith('*'):
                break
            parts = re.split(r',\s*', line.strip())
            if len(parts) >= 4:
                try:
                    node_id = int(parts[0])
                    coords = list(map(float, parts[1:4]))
                    nodes[node_id] = coords
                except:
                    pass
    return nodes


def read_elements(inp_file):
    elements = {}
    with open(inp_file, 'r') as f:
        lines = f.readlines()
    elem_section = False
    for line in lines:
        if line.strip().startswith('*ELEMENT'):
            elem_section = True
            continue
        if elem_section:
            if line.strip().startswith('**') or line.strip().startswith('*'):
                break
            parts = re.split(r',\s*', line.strip())
            if len(parts) >= 4:
                try:
                    elem_id = int(parts[0])
                    node_ids = list(map(int, parts[1:]))
                    elements[elem_id] = node_ids
                except:
                    pass
    return elements


def read_results(csv_file):
    results = {}
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 4:
                continue
            try:
                elem_id = int(row[0].strip())
                value1 = float(row[2].strip())
                value2 = float(row[3].strip())
                results[elem_id] = (value1, value2)
            except Exception as e:
                print("Error in row:", row, "->", e)
                continue
    return results


# ============================================================
# GEOMETRY HELPERS
# ============================================================
def longest_edge(nodes_coords, nids):
    edges = [
        (nids[0], nids[1]),
        (nids[1], nids[2]),
        (nids[2], nids[0])
    ]
    lengths = [
        np.linalg.norm(np.array(nodes_coords[nids[0]]) - np.array(nodes_coords[nids[1]])),
        np.linalg.norm(np.array(nodes_coords[nids[1]]) - np.array(nodes_coords[nids[2]])),
        np.linalg.norm(np.array(nodes_coords[nids[2]]) - np.array(nodes_coords[nids[0]]))
    ]
    max_idx = np.argmax(lengths)
    return tuple(sorted(edges[max_idx]))


def tri_edges(nids):
    return [
        tuple(sorted((nids[0], nids[1]))),
        tuple(sorted((nids[1], nids[2]))),
        tuple(sorted((nids[2], nids[0])))
    ]


def common_edge(e1, e2, elements):
    """Return the common edge (2 shared nodes) between 2 triangle elements; else None."""
    if e1 not in elements or e2 not in elements:
        return None
    s = set(elements[e1]) & set(elements[e2])
    if len(s) == 2:
        return tuple(sorted(s))
    return None


# ============================================================
# MAIN PROPAGATION (UPDATED WITH CASE 1/2)
# ============================================================
def propagate_results(nodes, elements, results):
    """
    Keep your old idea:
      - find OA pairs using longest-edge grouping (valid-valid)
      - find A: valid element adjacent to a NaN element across any edge
      - For each (A,O) build the related (B,C) in the next layer (both NaN),
        then assign using Condition 1/2:
            edge_n = common_edge(A,O)
            edge_m = common_edge(B,C)
            if edge_n and edge_m share exactly 1 node => CASE 2 else CASE 1
    IMPORTANT:
      - we DO NOT zip(sorted(O), sorted(B)) anymore (that was the source of mismatch/NaN).
      - We pair by topology per OA index i.
    """
    valid_elem_ids = [eid for eid in elements if eid in results]
    nan_elem_ids = [eid for eid in elements if eid not in results]

    if len(valid_elem_ids) == 0 or len(nan_elem_ids) == 0:
        return 0

    nan_set = set(nan_elem_ids)
    valid_set = set(valid_elem_ids)

    # Build edge->elements adjacency for ALL elements
    edge_to_elem_all = {}
    for eid, nids in elements.items():
        if len(nids) != 3:
            continue
        for e in tri_edges(nids):
            edge_to_elem_all.setdefault(e, []).append(eid)

    # --- Step 1: OA candidates by longest-edge of VALID elements
    edge_to_valid = {}
    for eid in valid_elem_ids:
        nids = elements[eid]
        if len(nids) != 3:
            continue
        le = longest_edge(nodes, nids)
        edge_to_valid.setdefault(le, []).append(eid)

    # oa_pairs_all: list of (e1,e2) where both valid share the same longest edge (size==2)
    oa_pairs_all = []
    for le, eids in edge_to_valid.items():
        if len(eids) == 2:
            oa_pairs_all.append((eids[0], eids[1]))

    if len(oa_pairs_all) == 0:
        return 0

    # --- Step 2: find A: valid element that touches at least 1 NaN element by sharing an edge
    A_set = set()
    for eid in valid_elem_ids:
        nids = elements[eid]
        if len(nids) != 3:
            continue
        for ed in tri_edges(nids):
            shared = edge_to_elem_all.get(ed, [])
            if len(shared) == 2:
                other = shared[0] if shared[1] == eid else shared[1]
                if other in nan_set:
                    A_set.add(eid)
                    break

    if len(A_set) == 0:
        return 0

    # --- Step 3: build oriented OA list as (A,O,i) where A is in A_set and O is the other in the OA pair
    OA_list = []
    i = 0
    for e1, e2 in oa_pairs_all:
        if e1 in A_set and e2 in valid_set:
            i += 1
            OA_list.append((e1, e2, i))
        elif e2 in A_set and e1 in valid_set:
            i += 1
            OA_list.append((e2, e1, i))

    if len(OA_list) == 0:
        return 0

    # --- Step 4: for each OA(i), find related B/C in the next layer (both NaN)
    # Logic:
    #   B: a NaN element sharing an edge with A (any of A's 3 edges)
    #   C: the other NaN element that forms the same quad with B, i.e.,
    #      it shares an edge with B that is the longest edge of BOTH B and C (your old "diagonal" rule)
    assigned = 0

    for A_eid, O_eid, idx in OA_list:
        if A_eid not in results or O_eid not in results:
            continue

        # collect B candidates touching A
        B_candidates = []
        A_edges = tri_edges(elements[A_eid])
        for ed in A_edges:
            neigh = edge_to_elem_all.get(ed, [])
            if len(neigh) == 2:
                other = neigh[0] if neigh[1] == A_eid else neigh[1]
                if other in nan_set:
                    B_candidates.append(other)

        if len(B_candidates) == 0:
            continue

        # For stability: try each B, and try to find a valid C paired with it
        found_pair = False

        for B_eid in B_candidates:
            if B_eid not in nan_set:
                continue
            if len(elements[B_eid]) != 3:
                continue

            B_le = longest_edge(nodes, elements[B_eid])

            # Find C: NaN neighbor of B across B_le AND also C's longest edge is the same edge
            neigh = edge_to_elem_all.get(B_le, [])
            if len(neigh) != 2:
                continue
            other = neigh[0] if neigh[1] == B_eid else neigh[1]
            C_eid = other

            if C_eid not in nan_set:
                continue
            if len(elements[C_eid]) != 3:
                continue

            C_le = longest_edge(nodes, elements[C_eid])
            if C_le != B_le:
                continue

            # Now we have OA and BC. Decide case 1/2 using your rule:
            edge_n = common_edge(A_eid, O_eid, elements)  # diagonal of OA
            edge_m = common_edge(B_eid, C_eid, elements)  # diagonal of BC
            if edge_n is None or edge_m is None:
                continue

            shared_nodes = set(edge_n) & set(edge_m)

            # CASE 2: diagonals touch by 1 node
            if len(shared_nodes) == 1:
                # B <- A ; C <- O
                results[B_eid] = results[A_eid]
                results[C_eid] = results[O_eid]
            else:
                # CASE 1: otherwise
                # B <- O ; C <- A
                results[B_eid] = results[O_eid]
                results[C_eid] = results[A_eid]

            # Update sets so later OA won't reuse already-filled elements in the same call
            nan_set.discard(B_eid)
            nan_set.discard(C_eid)

            assigned += 2
            found_pair = True
            break  # one BC pair per OA index i

        # if not found_pair: just skip this OA

    return assigned


# ============================================================
# EXPORT / UI
# ============================================================
def select_output_folder():
    root = Tk()
    root.withdraw()
    folder = filedialog.askdirectory(title="Select folder to save results")
    root.destroy()
    return folder


def maincode(inp_file, csv_file):
    nodes = read_nodes(inp_file)
    elements = read_elements(inp_file)
    results = read_results(csv_file)

    # Propagate results until no new values are assigned
    while True:
        num_new = propagate_results(nodes, elements, results)
        if num_new == 0:
            break

    output_folder = select_output_folder()
    if not output_folder:
        print("No folder selected, export aborted!")
        return

    os.makedirs(output_folder, exist_ok=True)
    output_csv = os.path.join(output_folder, 'COPIED RESULTS.csv')

    original_results = {}
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # skip header row
        for row in reader:
            if len(row) < 3:
                continue
            try:
                elem_id = int(row[0])
                value1 = float(row[1])
                value2 = float(row[2])
                original_results[elem_id] = (value1, value2)
            except:
                continue

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["$JPT-Post user's result adding", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
        writer.writerow(["$TITTLE = Static Analysis", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
        writer.writerow(["$SUBCASE = Subcase1", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
        writer.writerow(["$BINDING = element", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
        writer.writerow(["$COLUMN_INFO = ENTITY_ID", "", "", "", "", "", "", "", "", "", "", "", "", "", ""])
        writer.writerow(["$RESULT_TYPE = Temperature(s), bb(s), cc(s), dd(s), ee(s), ff(s), g(ss), h(s), i(s), j(s), k(s), l(s), m(s), n(s)"])
        header = ["ENTITY_ID", "Temperature(s)", "bb(s)", "cc(s)", "dd(s)", "ee(s)", "ff(s)",
                  "g(ss)", "h(s)", "i(s)", "j(s)", "k(s)", "l(s)", "m(s)", "n(s)"]
        writer.writerow(header)

        for eid in sorted(elements.keys()):
            if eid in original_results:
                temp_vals = original_results[eid]
            else:
                temp_vals = results.get(eid, (np.nan, np.nan))
            row = [eid, temp_vals[0], temp_vals[1]] + [0]*13
            writer.writerow(row)

    print("Export CSV File, DONE!")

    output_inp = os.path.join(output_folder, 'COPIED RESULTS.inp')
    with open(output_inp, 'w', encoding='utf-8') as f_inp:
        f_inp.write("*FILM\n")
        for eid in sorted(elements.keys()):
            if eid in original_results:
                result_vals = original_results[eid]
            else:
                result_vals = results.get(eid, (np.nan, np.nan))
            res_str1 = f"{result_vals[0]:.2f}" if not np.isnan(result_vals[0]) else "NaN"
            res_str2 = f"{result_vals[1]:.2f}" if not np.isnan(result_vals[1]) else "NaN"
            f_inp.write(f"{eid},FPOS,{res_str1},{res_str2}\n")

    print("Export INP File, DONE!")
    JPT.ClearLog()


def onGetButton1Clicked(dlg):
    inp_file = dlg.get_item_text(name="File Ndelm")
    csv_file = dlg.get_item_text(name="Mapping results")
    maincode(inp_file, csv_file)
    JPT.MessageBoxPSJ("Exported copy data", JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)


def onGetButton2Clicked(dlg):
    inp_file = dlg.get_item_text(name="File Ndelm")
    csv_file = dlg.get_item_text(name="Mapping results")
    print("Preview Input file:", inp_file)
    print("Preview CSV file:", csv_file)

    nodes_local = read_nodes(inp_file)
    elements_local = read_elements(inp_file)
    results_local = read_results(csv_file)

    while True:
        num_new = propagate_results(nodes_local, elements_local, results_local)
        if num_new == 0:
            break

    plot_results(nodes_local, elements_local, results_local, result_index=0, title='TEMPERATURE')


def onGetButton3Clicked(dlg):
    inp_file = dlg.get_item_text(name="File Ndelm")
    csv_file = dlg.get_item_text(name="Mapping results")
    print("Preview Input file:", inp_file)
    print("Preview CSV file:", csv_file)

    nodes_local = read_nodes(inp_file)
    elements_local = read_elements(inp_file)
    results_local = read_results(csv_file)

    while True:
        num_new = propagate_results(nodes_local, elements_local, results_local)
        if num_new == 0:
            break

    plot_results(nodes_local, elements_local, results_local, result_index=1, title='HTC')


def main():
    dlg = JDGCreator(title="Copy Mapping", include_apply=False)

    dlg.add_label(name="Label", text="Input model file:", layout="Window")
    dlg.add_browser(name="File Ndelm", mode="file", file_filter="All Files(*.*)", layout="Window")

    dlg.add_label(name="Label1", text="Input mapped results:", layout="Window")
    dlg.add_browser(name="Mapping results", mode="file", file_filter="All Files(*.*)", layout="Window")

    dlg.add_groupbox(name="GroupBox1", text="PREVIEW", layout="Window")

    dlg.add_layout(name="Layout1.2", margin=[200, 0, 0, 0], orientation=orientation.horizontal, layout="GroupBox1")
    dlg.add_button(name="Button1", text="TEMP", width=60, height=22, bk_color=15790320, layout="Layout1.2")
    dlg.on_button_clicked(name="Button1", callfunc=onGetButton2Clicked)

    dlg.add_layout(name="Layout1.3", margin=[200, 0, 0, 0], orientation=orientation.horizontal, layout="GroupBox1")
    dlg.add_button(name="Button2", text="HTC", width=60, height=22, bk_color=15790320, layout="Layout1.3")
    dlg.on_button_clicked(name="Button2", callfunc=onGetButton3Clicked)

    dlg.generate_window()
    dlg.on_dlg_ok(callfunc=onGetButton1Clicked)


if __name__ == '__main__':
    main()
