%% NURBS circle plate Q4 mesh

clc; clear; close all;
addpath('nurbs_toolbox');


%% Geometry and mesh parameters
R = 1.0;
t = 0.01;

nSide = 32;          
nRadial = 16;       
innerHalfSide = 0.35 * R;

%% NURBS geometry: 5 surface patches
outerCircle = nrbcirc(R, [0, 0, 0], 0, 2*pi);
patches = q4_patches(R, innerHalfSide);

%% Mesh: sample each NURBS patch and build Q4 connectivity
[nodes, elements, patchNodeIds] = mesh_patches_q4(patches, nSide, nRadial);
[boundaryNodes, boundaryEdges] = boundary_from_q4(elements, nodes);

mesh.radius = R;
mesh.thickness = t;
mesh.elementType = 'Q4';
mesh.nSide = nSide;
mesh.nRadial = nRadial;
mesh.innerHalfSide = innerHalfSide;
mesh.nodes = nodes;                       
mesh.elements = elements;                 
mesh.boundaryNodes = boundaryNodes;
mesh.boundaryEdges = boundaryEdges;
mesh.circleNurbs = outerCircle;
mesh.surfacePatches = patches;
mesh.patchNodeIds = patchNodeIds;
mesh.numNode = size(nodes, 1);
mesh.numElement = size(elements, 1);
mesh.area = q4_mesh_area(nodes, elements);


%% Plot NURBS patches and generated Q4 mesh
figure('Name', 'NURBS surface patches');
hold on;
for k = 1:numel(patches)
    nrbplot(patches(k).surface, [24, 12]);
end
axis equal; grid on;
xlabel('x'); ylabel('y'); zlabel('z');
title('NURBS surface');
view(2);
hold off;

figure('Name', 'Q4 mesh from NURBS patches');
patch('Faces', elements, 'Vertices', nodes, ...
    'FaceColor', 'none', 'EdgeColor', [0.15 0.15 0.15]);
hold on;
boundaryPts = nrbeval(outerCircle, linspace(0, 1, 400));
plot3(boundaryPts(1,:), boundaryPts(2,:), boundaryPts(3,:), 'r-', 'LineWidth', 1.5);
axis equal; grid on;
xlabel('x'); ylabel('y'); zlabel('z');
title('Q4 mesh');
view(2);
hold off;

%% Local functions
function patches = q4_patches(R, a)
c = R / sqrt(2);

pSW = [-a, -a, 0]; pSE = [ a, -a, 0];
pNE = [ a,  a, 0]; pNW = [-a,  a, 0];

bSW = [-c, -c, 0]; bSE = [ c, -c, 0];
bNE = [ c,  c, 0]; bNW = [-c,  c, 0];

patches(1).name = 'center';
patches(1).surface = nrb4surf(pSW, pSE, pNW, pNE);
patches(1).nU = [];
patches(1).nV = [];

topInner = nrbline(pNW, pNE);
topOuter = nrbreverse(nrbcirc(R, [0, 0, 0], pi/4, 3*pi/4));
topLeft = nrbline(pNW, bNW);
topRight = nrbline(pNE, bNE);
patches(2).name = 'top';
patches(2).surface = nrbcoons(topInner, topOuter, topLeft, topRight);
patches(2).nU = [];
patches(2).nV = [];

rightInner = nrbline(pSE, pNE);
rightOuter = nrbcirc(R, [0, 0, 0], 7*pi/4, pi/4);
rightBottom = nrbline(pSE, bSE);
rightTop = nrbline(pNE, bNE);
patches(3).name = 'right';
patches(3).surface = nrbcoons(rightInner, rightOuter, rightBottom, rightTop);
patches(3).nU = [];
patches(3).nV = [];

bottomInner = nrbline(pSW, pSE);
bottomOuter = nrbcirc(R, [0, 0, 0], 5*pi/4, 7*pi/4);
bottomLeft = nrbline(pSW, bSW);
bottomRight = nrbline(pSE, bSE);
patches(4).name = 'bottom';
patches(4).surface = nrbcoons(bottomInner, bottomOuter, bottomLeft, bottomRight);
patches(4).nU = [];
patches(4).nV = [];

leftInner = nrbline(pSW, pNW);
leftOuter = nrbreverse(nrbcirc(R, [0, 0, 0], 3*pi/4, 5*pi/4));
leftBottom = nrbline(pSW, bSW);
leftTop = nrbline(pNW, bNW);
patches(5).name = 'left';
patches(5).surface = nrbcoons(leftInner, leftOuter, leftBottom, leftTop);
patches(5).nU = [];
patches(5).nV = [];
end

function [nodes, elements, patchNodeIds] = mesh_patches_q4(patches, nSide, nRadial)
nodes = zeros(0, 3);
elements = zeros(0, 4);
keyToNode = containers.Map('KeyType', 'char', 'ValueType', 'double');
patchNodeIds = cell(numel(patches), 1);

for k = 1:numel(patches)
    if strcmp(patches(k).name, 'center')
        nU = nSide;
        nV = nSide;
    else
        nU = nSide;
        nV = nRadial;
    end

    [nodes, elements, keyToNode, patchNodeIds{k}] = ...
        add_patch_q4(nodes, elements, keyToNode, patches(k).surface, nU, nV);
end

elements = orient_q4_ccw(nodes, elements);
end

function [nodes, elements, keyToNode, ids] = add_patch_q4(nodes, elements, keyToNode, S, nU, nV)
uKnots = S.knots{1};
vKnots = S.knots{2};
u0 = uKnots(S.order(1));
u1 = uKnots(end - S.order(1) + 1);
v0 = vKnots(S.order(2));
v1 = vKnots(end - S.order(2) + 1);

u = linspace(u0, u1, nU + 1);
v = linspace(v0, v1, nV + 1);
pts = nrbeval(S, {u, v});

ids = zeros(nU + 1, nV + 1);
for j = 1:(nV + 1)
    for i = 1:(nU + 1)
        point = squeeze(pts(:, i, j)).';
        [nodes, ids(i, j), keyToNode] = add_node(nodes, keyToNode, point);
    end
end

elems = zeros(nU*nV, 4);
e = 0;
for j = 1:nV
    for i = 1:nU
        e = e + 1;
        elems(e, :) = [ids(i, j), ids(i + 1, j), ids(i + 1, j + 1), ids(i, j + 1)];
    end
end

elements = [elements; elems];
end

function [nodes, id, keyToNode] = add_node(nodes, keyToNode, point)
key = sprintf('%.12f_%.12f_%.12f', point(1), point(2), point(3));
if isKey(keyToNode, key)
    id = keyToNode(key);
else
    nodes(end + 1, :) = point;
    id = size(nodes, 1);
    keyToNode(key) = id;
end
end

function elements = orient_q4_ccw(nodes, elements)
for e = 1:size(elements, 1)
    p = nodes(elements(e, :), 1:2);
    signedArea = 0.5 * sum(p(:,1).*p([2:end, 1],2) - p([2:end, 1],1).*p(:,2));
    if signedArea < 0
        elements(e, :) = elements(e, [1, 4, 3, 2]);
    end
end
end

function [boundaryNodes, boundaryEdges] = boundary_from_q4(elements, nodes)
edges = [elements(:, [1, 2]); elements(:, [2, 3]); ...
         elements(:, [3, 4]); elements(:, [4, 1])];
sortedEdges = sort(edges, 2);
[uniqueEdges, ~, ic] = unique(sortedEdges, 'rows');
edgeCount = accumarray(ic, 1);
boundaryEdges = uniqueEdges(edgeCount == 1, :);
boundaryNodes = unique(boundaryEdges(:));

theta = atan2(nodes(boundaryNodes, 2), nodes(boundaryNodes, 1));
[~, order] = sort(theta);
boundaryNodes = boundaryNodes(order);
end

function area = q4_mesh_area(nodes, elements)
p1 = nodes(elements(:,1), :);
p2 = nodes(elements(:,2), :);
p3 = nodes(elements(:,3), :);
p4 = nodes(elements(:,4), :);
area1 = 0.5 * vecnorm(cross(p2 - p1, p3 - p1, 2), 2, 2);
area2 = 0.5 * vecnorm(cross(p3 - p1, p4 - p1, 2), 2, 2);
area = sum(area1 + area2);
end
