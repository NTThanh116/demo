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

    triangles, colors, centers, labels = [], [], [], []

    for eid in sorted(elements.keys()):
        nids = elements[eid]
        if len(nids) != 3:
            continue

        tri = [nodes[nid] for nid in nids]
        triangles.append(tri)

        val = results.get(eid, (np.nan, np.nan))[result_index]
        colors.append(val)

        c = np.mean(tri, axis=0)
        centers.append(c)
        labels.append(f"{val:.2f}" if not np.isnan(val) else "NaN")

    poly = Poly3DCollection(triangles, edgecolors='k')
    poly.set_array(np.array(colors))
    poly.set_cmap(cmap)
    poly.set_clim(np.nanmin(colors), np.nanmax(colors))
    ax.add_collection3d(poly)

    for c, lab in zip(centers, labels):
        ax.text(c[0], c[1], c[2], lab, fontsize=8)

    ax.auto_scale_xyz(*zip(*[p for t in triangles for p in t]))
    ax.set_title(title)
    fig.colorbar(poly, ax=ax)
    plt.tight_layout()
    plt.show()


# ============================================================
# READ INPUT
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
            if line.strip().startswith('*') or line.strip().startswith('**'):
                break
            parts = re.split(r',\s*', line.strip())
            if len(parts) >= 4:
                try:
                    nodes[int(parts[0])] = list(map(float, parts[1:4]))
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
            if line.strip().startswith('*') or line.strip().startswith('**'):
                break
            parts = re.split(r',\s*', line.strip())
            if len(parts) >= 4:
                try:
                    elements[int(parts[0])] = list(map(int, parts[1:]))
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
                results[int(row[0])] = (float(row[2]), float(row[3]))
            except:
                pass
    return results


# ============================================================
# GEOMETRY HELPERS
# ============================================================
def tri_edges(n):
    return [
        tuple(sorted((n[0], n[1]))),
        tuple(sorted((n[1], n[2]))),
        tuple(sorted((n[2], n[0])))
    ]


def longest_edge(nodes, n):
    edges = tri_edges(n)
    lengths = [
        np.linalg.norm(np.array(nodes[e[0]]) - np.array(nodes[e[1]]))
        for e in edges
    ]
    return edges[np.argmax(lengths)]


def common_edge(e1, e2, elements):
    s = set(elements[e1]) & set(elements[e2])
    return tuple(sorted(s)) if len(s) == 2 else None


# ============================================================
# CORE – ONLY THIS PART IS CHANGED
# ============================================================
def propagate_results(nodes, elements, results):

    valid = [e for e in elements if e in results]
    nan_elems = [e for e in elements if e not in results]

    if not valid or not nan_elems:
        return 0

    nan_set = set(nan_elems)

    edge2elem = {}
    for e, n in elements.items():
        if len(n) != 3:
            continue
        for ed in tri_edges(n):
            edge2elem.setdefault(ed, []).append(e)

    # OA pairs (valid-valid via longest edge)
    edge2valid = {}
    for e in valid:
        le = longest_edge(nodes, elements[e])
        edge2valid.setdefault(le, []).append(e)

    oa_pairs = [p for p in edge2valid.values() if len(p) == 2]

    new_assigned = 0

    for e1, e2 in oa_pairs:

        A = O = None

        # find A (touches NaN)
        for e in (e1, e2):
            for ed in tri_edges(elements[e]):
                nei = edge2elem.get(ed, [])
                if len(nei) == 2:
                    other = nei[0] if nei[1] == e else nei[1]
                    if other in nan_set:
                        A = e
                        O = e2 if e == e1 else e1
                        break
            if A:
                break

        if A is None:
            continue

        # find B/C
        for ed in tri_edges(elements[A]):
            nei = edge2elem.get(ed, [])
            if len(nei) != 2:
                continue

            B = nei[0] if nei[1] == A else nei[1]
            if B not in nan_set:
                continue

            leB = longest_edge(nodes, elements[B])
            nei2 = edge2elem.get(leB, [])
            if len(nei2) != 2:
                continue

            C = nei2[0] if nei2[1] == B else nei2[1]
            if C not in nan_set:
                continue

            if longest_edge(nodes, elements[C]) != leB:
                continue

            edge_n = common_edge(A, O, elements)
            edge_m = common_edge(B, C, elements)
            if not edge_n or not edge_m:
                continue

            if len(set(edge_n) & set(edge_m)) == 1:
                # CASE 2
                results[B] = results[A]
                results[C] = results[O]
            else:
                # CASE 1
                results[B] = results[O]
                results[C] = results[A]

            nan_set.remove(B)
            nan_set.remove(C)
            new_assigned += 2
            break

    return new_assigned


# ============================================================
# EXPORT + UI (GIỮ NGUYÊN CODE GỐC)
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

    while True:
        if propagate_results(nodes, elements, results) == 0:
            break

    output_folder = select_output_folder()
    if not output_folder:
        return

    os.makedirs(output_folder, exist_ok=True)
    output_inp = os.path.join(output_folder, 'COPIED RESULTS.inp')

    with open(output_inp, 'w') as f:
        f.write("*FILM\n")
        for eid in sorted(elements):
            v = results.get(eid, (np.nan, np.nan))
            f.write(f"{eid},FPOS,{v[0]},{v[1]}\n")

    print("Export DONE")
    JPT.ClearLog()


def onGetButton1Clicked(dlg):
    maincode(
        dlg.get_item_text(name="File Ndelm"),
        dlg.get_item_text(name="Mapping results")
    )
    JPT.MessageBoxPSJ("Exported copy data", JPT.MsgBoxType.MB_INFORMATION_YESNOCANCEL)


def onGetButton2Clicked(dlg):
    n = read_nodes(dlg.get_item_text(name="File Ndelm"))
    e = read_elements(dlg.get_item_text(name="File Ndelm"))
    r = read_results(dlg.get_item_text(name="Mapping results"))
    while propagate_results(n, e, r):
        pass
    plot_results(n, e, r, 0, "TEMPERATURE")


def onGetButton3Clicked(dlg):
    n = read_nodes(dlg.get_item_text(name="File Ndelm"))
    e = read_elements(dlg.get_item_text(name="File Ndelm"))
    r = read_results(dlg.get_item_text(name="Mapping results"))
    while propagate_results(n, e, r):
        pass
    plot_results(n, e, r, 1, "HTC")


def main():
    dlg = JDGCreator(title="Copy Mapping", include_apply=False)

    dlg.add_label(name="Label", text="Input model file:", layout="Window")
    dlg.add_browser(name="File Ndelm", mode="file", file_filter="All Files(*.*)", layout="Window")

    dlg.add_label(name="Label1", text="Input mapped results:", layout="Window")
    dlg.add_browser(name="Mapping results", mode="file", file_filter="All Files(*.*)", layout="Window")

    dlg.add_groupbox(name="GroupBox1", text="PREVIEW", layout="Window")

    dlg.add_layout(name="Layout1.2", margin=[200, 0, 0, 0],
                   orientation=orientation.horizontal, layout="GroupBox1")
    dlg.add_button(name="Button1", text="TEMP", width=60, height=22,
                   bk_color=15790320, layout="Layout1.2")
    dlg.on_button_clicked(name="Button1", callfunc=onGetButton2Clicked)

    dlg.add_layout(name="Layout1.3", margin=[200, 0, 0, 0],
                   orientation=orientation.horizontal, layout="GroupBox1")
    dlg.add_button(name="Button2", text="HTC", width=60, height=22,
                   bk_color=15790320, layout="Layout1.3")
    dlg.on_button_clicked(name="Button2", callfunc=onGetButton3Clicked)

    dlg.generate_window()
    dlg.on_dlg_ok(callfunc=onGetButton1Clicked)


if __name__ == '__main__':
    main()
