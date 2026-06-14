import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

R = 1.0
t = 0.01
nSide = 12
nRadial = 5
innerHalfSide = 0.35

# Same 5-patch Q4 circle mesh generator used for the saved result.
# Output element count = nSide**2 + 4*nSide*nRadial.

def add_node(nodes, key_to_node, point, tol_digits=12):
    key = tuple(np.round(point, tol_digits))
    if key in key_to_node:
        return key_to_node[key]
    key_to_node[key] = len(nodes)
    nodes.append(point)
    return len(nodes) - 1

def orient_q4_ccw(nodes_arr, elements_arr):
    elems = elements_arr.copy()
    xy = nodes_arr[:, :2]
    for e, conn in enumerate(elems):
        p = xy[conn]
        signed_area = 0.5 * np.sum(
            p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]
        )
        if signed_area < 0:
            elems[e] = conn[[0, 3, 2, 1]]
    return elems

def q4_mesh_area(nodes_arr, elements_arr):
    p1 = nodes_arr[elements_arr[:, 0]]
    p2 = nodes_arr[elements_arr[:, 1]]
    p3 = nodes_arr[elements_arr[:, 2]]
    p4 = nodes_arr[elements_arr[:, 3]]
    area1 = 0.5 * np.linalg.norm(np.cross(p2 - p1, p3 - p1), axis=1)
    area2 = 0.5 * np.linalg.norm(np.cross(p3 - p1, p4 - p1), axis=1)
    return float(np.sum(area1 + area2))

def boundary_from_q4(elements_arr):
    edges = np.vstack([
        elements_arr[:, [0, 1]],
        elements_arr[:, [1, 2]],
        elements_arr[:, [2, 3]],
        elements_arr[:, [3, 0]],
    ])
    edges_sorted = np.sort(edges, axis=1)
    unique_edges, counts = np.unique(edges_sorted, axis=0, return_counts=True)
    boundary_edges = unique_edges[counts == 1]
    boundary_nodes = np.unique(boundary_edges)
    return boundary_nodes, boundary_edges

def sample_center_patch(a, nU, nV):
    xs = np.linspace(-a, a, nU + 1)
    ys = np.linspace(-a, a, nV + 1)
    P = np.zeros((nU + 1, nV + 1, 3))
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            P[i, j] = [x, y, 0.0]
    return P

def sample_ring_patch(name, R, a, nU, nV):
    u_vals = np.linspace(0.0, 1.0, nU + 1)
    v_vals = np.linspace(0.0, 1.0, nV + 1)
    P = np.zeros((nU + 1, nV + 1, 3))

    if name == "top":
        def inner(u): return np.array([-a + 2*a*u, a, 0.0])
        def outer(u):
            theta = 3*np.pi/4 + (np.pi/4 - 3*np.pi/4) * u
            return np.array([R*np.cos(theta), R*np.sin(theta), 0.0])
    elif name == "right":
        def inner(u): return np.array([a, -a + 2*a*u, 0.0])
        def outer(u):
            theta = -np.pi/4 + (np.pi/4 + np.pi/4) * u
            return np.array([R*np.cos(theta), R*np.sin(theta), 0.0])
    elif name == "bottom":
        def inner(u): return np.array([-a + 2*a*u, -a, 0.0])
        def outer(u):
            theta = 5*np.pi/4 + (7*np.pi/4 - 5*np.pi/4) * u
            return np.array([R*np.cos(theta), R*np.sin(theta), 0.0])
    elif name == "left":
        def inner(u): return np.array([-a, -a + 2*a*u, 0.0])
        def outer(u):
            theta = 5*np.pi/4 + (3*np.pi/4 - 5*np.pi/4) * u
            return np.array([R*np.cos(theta), R*np.sin(theta), 0.0])
    else:
        raise ValueError(name)

    for i, u in enumerate(u_vals):
        pin = inner(u)
        pout = outer(u)
        for j, v in enumerate(v_vals):
            P[i, j] = (1.0 - v) * pin + v * pout
    return P

def add_patch_q4(P, nodes, elements, key_to_node):
    nU = P.shape[0] - 1
    nV = P.shape[1] - 1
    ids = np.zeros((nU + 1, nV + 1), dtype=int)
    for i in range(nU + 1):
        for j in range(nV + 1):
            ids[i, j] = add_node(nodes, key_to_node, P[i, j])
    for i in range(nU):
        for j in range(nV):
            elements.append([ids[i, j], ids[i+1, j], ids[i+1, j+1], ids[i, j+1]])
    return ids

def build_mesh(R=1.0, nSide=12, nRadial=5, innerHalfSide=0.35):
    nodes = []
    elements = []
    key_to_node = {}

    add_patch_q4(sample_center_patch(innerHalfSide, nSide, nSide), nodes, elements, key_to_node)

    for name in ["top", "right", "bottom", "left"]:
        add_patch_q4(sample_ring_patch(name, R, innerHalfSide, nSide, nRadial), nodes, elements, key_to_node)

    nodes_arr = np.array(nodes, dtype=float)
    elements_arr = orient_q4_ccw(nodes_arr, np.array(elements, dtype=int))
    return nodes_arr, elements_arr

if __name__ == "__main__":
    nodes, elements = build_mesh(R, nSide, nRadial, innerHalfSide)
    boundary_nodes, boundary_edges = boundary_from_q4(elements)
    area = q4_mesh_area(nodes, elements)

    print("numNode =", len(nodes))
    print("numElement =", len(elements))
    print("numBoundaryNode =", len(boundary_nodes))
    print("area =", area)
    print("area_error_percent =", (area - np.pi * R**2) / (np.pi * R**2) * 100)

    np.savez(
        "circle_q4_mesh_coarse_384.npz",
        R=R,
        t=t,
        nSide=nSide,
        nRadial=nRadial,
        innerHalfSide=innerHalfSide,
        nodes=nodes,
        elements0=elements,
        elements1=elements + 1,
        boundary_nodes0=boundary_nodes,
        boundary_edges0=boundary_edges,
        area=area,
    )

    fig, ax = plt.subplots(figsize=(7, 7))
    segments = []
    for e in elements:
        pts = nodes[e, :2]
        for k in range(4):
            segments.append([pts[k], pts[(k + 1) % 4]])

    ax.add_collection(LineCollection(segments, linewidths=0.8))
    theta = np.linspace(0, 2*np.pi, 500)
    ax.plot(R*np.cos(theta), R*np.sin(theta), linewidth=1.2)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(f"Coarse Q4 circle mesh: nodes={len(nodes)}, elements={len(elements)}")
    ax.grid(True, linewidth=0.3)
    ax.autoscale()
    fig.tight_layout()
    plt.show()
