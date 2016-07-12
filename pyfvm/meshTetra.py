# -*- coding: utf-8 -*-
#
import numpy
from pyfvm.base import _base_mesh, _row_dot
import os
import matplotlib as mpl
from mpl_toolkits.mplot3d import Axes3D
if 'DISPLAY' not in os.environ:
    # headless mode, for remote executions (and travis)
    mpl.use('Agg')
from matplotlib import pyplot as plt

__all__ = ['meshTetra']


class meshTetra(_base_mesh):
    '''Class for handling tetrahedral meshes.

    .. inheritance-diagram:: meshTetra
    '''
    def __init__(self, node_coords, cells):
        '''Initialization.
        '''
        super(meshTetra, self).__init__(node_coords, cells)

        num_cells = len(cells)
        self.cells = numpy.empty(
                num_cells,
                dtype=numpy.dtype([('nodes', (int, 4))])
                )
        self.cells['nodes'] = cells

        self.create_adjacent_entities()
        self.create_cell_volumes()
        self.create_cell_circumcenters()
        self.compute_edge_lengths()
        self.compute_covolumes()
        self.compute_control_volumes()

        self.mark_default_subdomains()
        return

    def mark_default_subdomains(self):
        self.subdomains = {}
        self.subdomains['everywhere'] = {
                'vertices': range(len(self.node_coords)),
                'edges': range(len(self.edges['nodes'])),
                'faces': range(len(self.faces['nodes']))
                }

        # Find the boundary edges, i.e., all edges that belong to just one
        # cell.
        boundary_faces = []
        for k, faces_cells in enumerate(self.faces['cells']):
            if len(faces_cells) == 1:
                boundary_faces.append(k)

        # Get vertices on the boundary edges
        boundary_vertices = numpy.unique(
                self.faces['nodes'][boundary_faces].flatten()
                )

        self.subdomains['Boundary'] = {
                'vertices': boundary_vertices
                }

        return

    def mark_subdomains(self, subdomains):
        for subdomain in subdomains:
            # find vertices in subdomain
            if subdomain.is_boundary_only:
                nodes = self.get_vertices('Boundary')
            else:
                nodes = self.get_vertices('everywhere')

            subdomain_vertices = []
            for vertex_id in nodes:
                if subdomain.is_inside(self.node_coords[vertex_id]):
                    subdomain_vertices.append(vertex_id)
            subdomain_vertices = numpy.unique(subdomain_vertices)

            name = subdomain.__class__.__name__
            self.subdomains[name] = {
                    'vertices': subdomain_vertices
                    }

        return

    def get_edges(self, subdomain):
        return self.subdomains[subdomain]['edges']

    def get_vertices(self, subdomain):
        return self.subdomains[subdomain]['vertices']

    def create_cell_volumes(self):
        '''Computes the volumes of the tetrahedra in the mesh.
        '''
        from vtk import vtkTetra
        num_cells = len(self.cells['nodes'])
        self.cell_volumes = numpy.empty(num_cells, dtype=float)
        for cell_id, cell in enumerate(self.cells):
            # edge0 = node0 - node1
            # edge1 = node1 - node2
            # edge2 = node2 - node3
            # edge3 = node3 - node0

            # alpha = numpy.vdot(edge0, numpy.cross(edge1, edge2))
            # norm_prod = \
            #     numpy.linalg.norm(edge0) * \
            #     numpy.linalg.norm(edge1) * \
            #     numpy.linalg.norm(edge2)
            # if abs(alpha) / norm_prod < 1.0e-5:
            #     # Edges probably conplanar. Take a different set.
            #     alpha = numpy.vdot(edge0, numpy.cross(edge1, edge3))
            #     norm_prod = \
            #         numpy.linalg.norm(edge0) * \
            #         numpy.linalg.norm(edge1) * \
            #         numpy.linalg.norm(edge3)

            # self.cell_volumes[cell_id] = abs(alpha) / 6.0

            x = self.node_coords[cell['nodes']]
            self.cell_volumes[cell_id] = \
                abs(vtkTetra.ComputeVolume(x[0], x[1], x[2], x[3]))
        return

    def create_adjacent_entities(self):
        '''Setup edge-node, edge-cell, edge-face, face-node, and face-cell
        relations.
        '''
        num_cells = len(self.cells['nodes'])

        # Get upper bound for number of edges; trim later.
        max_num_edges = 6 * num_cells
        dt = numpy.dtype([('nodes', (int, 2)),
                          ('faces', numpy.object),
                          ('cells', numpy.object)
                          ])
        # To create an array of empty lists, do what's described at
        # http://mail.scipy.org/pipermail/numpy-discussion/2009-November/046566.html
        self.edges = numpy.empty(max_num_edges, dt)
        filler = numpy.frompyfunc(lambda x: list(), 1, 1)
        self.edges['faces'] = filler(self.edges['faces'])
        self.edges['cells'] = filler(self.edges['cells'])

        # Extend the self.cells array by the keywords 'edges' and 'faces'.
        cells = self.cells['nodes']
        dt = numpy.dtype([('nodes', (int, 4)),
                          ('edges', (int, 6)),
                          ('faces', (int, 4))
                          ])
        self.cells = numpy.empty(len(cells), dtype=dt)
        self.cells['nodes'] = cells

        # The (sorted) dictionary node_edges keeps track of how nodes and edges
        # are connected.
        # If  node_edges[(3,4)] == 17  is true, then the nodes (3,4) are
        # connected  by edge 17.
        registered_edges = {}
        new_edge_gid = 0
        # Create edges.
        import itertools
        for cell_id, cell in enumerate(self.cells):
            # We're treating simplices so loop over all combinations of
            # local nodes.
            # Make sure cellNodes are sorted.
            self.cells['nodes'][cell_id] = numpy.sort(cell['nodes'])
            for k, indices in enumerate(itertools.combinations(cell['nodes'],
                                        2)
                                        ):
                if indices in registered_edges:
                    # edge already assigned
                    edge_gid = registered_edges[indices]
                    self.edges['cells'][edge_gid].append(cell_id)
                    self.cells['edges'][cell_id][k] = edge_gid
                else:
                    # add edge
                    self.edges['nodes'][new_edge_gid] = indices
                    self.edges['cells'][new_edge_gid].append(cell_id)
                    self.cells['edges'][cell_id][k] = new_edge_gid
                    registered_edges[indices] = new_edge_gid
                    new_edge_gid += 1

        # trim edges
        self.edges = self.edges[:new_edge_gid]

        # Create faces.
        max_num_faces = 4 * num_cells
        dt = numpy.dtype([('nodes', (int, 3)),
                          ('edges', (int, 3)),
                          ('cells', numpy.object)
                          ])
        self.faces = numpy.empty(max_num_faces, dt)
        self.faces['cells'] = filler(self.faces['cells'])

        # Loop over all elements.
        new_face_gid = 0
        registered_faces = {}
        for cell_id, cell in enumerate(self.cells):
            # Make sure cellNodes are sorted.
            self.cells['nodes'][cell_id] = numpy.sort(cell['nodes'])
            for k in range(4):
                # Remove the k-th element. This makes sure that the k-th
                # face is opposite of the k-th node. Useful later in
                # in construction of face normals.
                indices = tuple(cell['nodes'][:k]) \
                    + tuple(cell['nodes'][k+1:])
                if indices in registered_faces:
                    # Face already assigned, just register it with the
                    # current cell.
                    face_gid = registered_faces[indices]
                    self.faces['cells'][face_gid].append(cell_id)
                    self.cells['faces'][cell_id][k] = face_gid
                else:
                    # Add face.
                    # Make sure that facesNodes[k] and facesEdge[k] are
                    # coordinated in such a way that facesNodes[k][i]
                    # and facesEdge[k][i] are opposite in face k.
                    self.faces['nodes'][new_face_gid] = indices
                    # Register edges.
                    for kk in range(len(indices)):
                        # Note that node_tuple is also sorted, and thus
                        # is a key in the edges dictionary.
                        node_tuple = indices[:kk] + indices[kk+1:]
                        edge_id = registered_edges[node_tuple]
                        self.edges['faces'][edge_id].append(new_face_gid)
                        self.faces['edges'][new_face_gid][kk] = edge_id
                    # Register cells.
                    self.faces['cells'][new_face_gid].append(cell_id)
                    self.cells['faces'][cell_id][k] = new_face_gid
                    # Finalize.
                    registered_faces[indices] = new_face_gid
                    new_face_gid += 1
        # trim faces
        self.faces = self.faces[:new_face_gid]
        return

    def create_cell_circumcenters(self):
        '''Computes the center of the circumsphere of each cell.
        '''
        from vtk import vtkTetra
        num_cells = len(self.cells['nodes'])
        self.cell_circumcenters = numpy.empty(
                num_cells,
                dtype=numpy.dtype((float, 3))
                )
        for cell_id, cell in enumerate(self.cells):
            # Explicitly cast indices to 'int' here as the array node_coords
            # might only accept those. (This is the case with tetgen arrays,
            # for example.)
            x = self.node_coords[cell['nodes']]
            vtkTetra.Circumsphere(x[0], x[1], x[2], x[3],
                                  self.cell_circumcenters[cell_id])
            # # http://www.cgafaq.info/wiki/Tetrahedron_Circumsphere
            # x = self.node_coords[cell['nodes']]
            # b = x[1] - x[0]
            # c = x[2] - x[0]
            # d = x[3] - x[0]

            # omega = (2.0 * numpy.dot(b, numpy.cross(c, d)))

            # if abs(omega) < 1.0e-10:
            #    raise ZeroDivisionError('Tetrahedron is degenerate.')
            # self.cell_circumcenters[cell_id] = x[0] + (
            #         numpy.dot(b, b) * numpy.cross(c, d) +
            #         numpy.dot(c, c) * numpy.cross(d, b) +
            #         numpy.dot(d, d) * numpy.cross(b, c)
            #         ) / omega
        return

    def _get_face_circumcenter(self, face_id):
        '''Computes the center of the circumcircle of a given face.

        :params face_id: Face ID for which to compute circumcenter.
        :type face_id: int
        :returns circumcenter: Circumcenter of the face with given face ID.
        :type circumcenter: numpy.ndarray((float,3))
        '''
        from vtk import vtkTriangle

        x = self.node_coords[self.faces['nodes'][face_id]]
        # Project triangle to 2D.
        v = numpy.empty(3, dtype=numpy.dtype((float, 2)))
        vtkTriangle.ProjectTo2D(x[0], x[1], x[2],
                                v[0], v[1], v[2])
        # Get the circumcenter in 2D.
        cc_2d = numpy.empty(2, dtype=float)
        vtkTriangle.Circumcircle(v[0], v[1], v[2], cc_2d)
        # Project back to 3D by using barycentric coordinates.
        bcoords = numpy.empty(3, dtype=float)
        vtkTriangle.BarycentricCoords(cc_2d, v[0], v[1], v[2], bcoords)
        return bcoords[0] * x[0] + bcoords[1] * x[1] + bcoords[2] * x[2]

        # a = x[0] - x[1]
        # b = x[1] - x[2]
        # c = x[2] - x[0]
        # w = numpy.cross(a, b)
        # omega = 2.0 * numpy.dot(w, w)
        # if abs(omega) < 1.0e-10:
        #     raise ZeroDivisionError(
        #             'The nodes don''t seem to form a proper triangle.'
        #             )
        # alpha = -numpy.dot(b, b) * numpy.dot(a, c) / omega
        # beta = -numpy.dot(c, c) * numpy.dot(b, a) / omega
        # gamma = -numpy.dot(a, a) * numpy.dot(c, b) / omega
        # m = alpha * x[0] + beta * x[1] + gamma * x[2]

        # # Alternative implementation from
        # # https://www.ics.uci.edu/~eppstein/junkyard/circumcenter.html
        # a = x[1] - x[0]
        # b = x[2] - x[0]
        # alpha = numpy.dot(a, a)
        # beta = numpy.dot(b, b)
        # w = numpy.cross(a, b)
        # omega = 2.0 * numpy.dot(w, w)
        # m = numpy.empty(3)
        # m[0] = x[0][0] + (
        #         (alpha * b[1] - beta * a[1]) * w[2] -
        #         (alpha * b[2] - beta * a[2]) * w[1]
        #         ) / omega
        # m[1] = x[0][1] + (
        #         (alpha * b[2] - beta * a[2]) * w[0] -
        #         (alpha * b[0] - beta * a[0]) * w[2]
        #         ) / omega
        # m[2] = x[0][2] + (
        #         (alpha * b[0] - beta * a[0]) * w[1] -
        #         (alpha * b[1] - beta * a[1]) * w[0]
        #         ) / omega
        # return

    def compute_control_volumes(self):
        '''Compute the control volumes of all nodes in the mesh.
        '''
        self.control_volumes = numpy.zeros(len(self.node_coords), dtype=float)

        # 1/3. * (0.5 * edge_length) * covolume
        vals = self.edge_lengths * self.covolumes / 6.0

        edge_nodes = self.edges['nodes']
        numpy.add.at(self.control_volumes, edge_nodes[:, 0], vals)
        numpy.add.at(self.control_volumes, edge_nodes[:, 1], vals)

        return

    def num_delaunay_violations(self):
        # is_delaunay = True
        num_faces = len(self.faces['nodes'])
        num_interior_faces = 0
        num_delaunay_violations = 0
        for face_id in range(num_faces):
            # Boundary faces don't need to be checked.
            if len(self.faces['cells'][face_id]) != 2:
                continue

            num_interior_faces += 1
            # Each interior edge divides the domain into to half-planes.
            # The Delaunay condition is fulfilled if and only if
            # the circumcenters of the adjacent cells are in "the right order",
            # i.e., line between the nodes of the cells which do not sit
            # on the hyperplane have the same orientation as the line
            # between the circumcenters.

            # The orientation of the coedge needs gauging.
            # Do it in such as a way that the control volume contribution
            # is positive if and only if the area of the triangle
            # (node, other0, edge_midpoint) (in this order) is positive.
            # Equivalently, the triangles (node, edge_midpoint, other1)
            # or (node, other0, other1) could  be considered.
            # other{0,1} refers to the the node opposing the edge in the
            # adjacent cell {0,1}.
            # Get the opposing node of the first adjacent cell.
            cell0 = self.faces['cells'][face_id][0]
            # This nonzero construct is an ugly replacement for the nonexisting
            # index() method. (Compare with Python lists.)
            face_lid = \
                numpy.nonzero(self.cells['faces'][cell0] == face_id)[0][0]
            # This makes use of the fact that cellsEdges and cellsNodes
            # are coordinated such that in cell #i, the edge cellsEdges[i][k]
            # opposes cellsNodes[i][k].
            other0 = self.node_coords[self.cells['nodes'][cell0][face_lid]]

            # Get the edge midpoint.
            node_ids = self.faces['nodes'][face_id]
            node_coords = self.node_coords[node_ids]
            edge_midpoint = 0.5 * (node_coords[0] + node_coords[1])

            # Get the circumcenters of the adjacent cells.
            cc = self.cell_circumcenters[self.faces['cells'][face_id]]
            # Check if cc[1]-cc[0] and the gauge point
            # in the "same" direction.
            if numpy.dot(edge_midpoint-other0, cc[1]-cc[0]) < 0.0:
                num_delaunay_violations += 1
        return num_delaunay_violations

    def show_control_volume(self, node_id):
        '''Displays a node with its surrounding control volume.

        :param node_id: Node ID for which to show the control volume.
        :type node_id: int
        '''
        fig = plt.figure()
        ax = fig.gca(projection='3d')
        plt.axis('equal')

        # get cell circumcenters
        cell_ccs = self.cell_circumcenters

        # There are not node->edge relations so manually build the list.
        adjacent_edge_ids = []
        for edge_id, edge in enumerate(self.edges):
            if node_id in edge['nodes']:
                adjacent_edge_ids.append(edge_id)

        # Loop over all adjacent edges and plot the edges and their covolumes.
        for k, edge_id in enumerate(adjacent_edge_ids):
            # get rainbow color
            h = float(k) / len(adjacent_edge_ids)
            hsv_face_col = numpy.array([[[h, 1.0, 1.0]]])
            col = mpl.colors.hsv_to_rgb(hsv_face_col)[0][0]

            edge_nodes = self.node_coords[self.edges['nodes'][edge_id]]

            # highlight edge
            ax.plot(
                edge_nodes[:, 0], edge_nodes[:, 1], edge_nodes[:, 2],
                color=col, linewidth=3.0
                )

            # edge_midpoint = 0.5 * (edge_nodes[0] + edge_nodes[1])

            # Plot covolume.
            # face_col = '0.7'
            edge_col = 'k'
            for k, face_id in enumerate(self.edges['faces'][edge_id]):
                ccs = cell_ccs[self.faces['cells'][face_id]]
                if len(ccs) == 2:
                    ax.plot(ccs[:, 0], ccs[:, 1], ccs[:, 2], color=edge_col)
                    # tri = mpl3.art3d.Poly3DCollection(
                    #     [numpy.vstack((ccs, edge_midpoint))]
                    #     )
                    # tri.set_color(face_col)
                    # ax.add_collection3d(tri)
                elif len(ccs) == 1:
                    face_cc = self._get_face_circumcenter(face_id)
                    # tri = mpl3.art3d.Poly3DCollection(
                    #     [numpy.vstack((ccs[0], face_cc, edge_midpoint))]
                    #     )
                    # tri.set_color(face_col)
                    # ax.add_collection3d(tri)
                    ax.plot(
                        [ccs[0][0], face_cc[0]],
                        [ccs[0][1], face_cc[1]],
                        [ccs[0][2], face_cc[2]],
                        color=edge_col
                        )
                else:
                    raise RuntimeError('???')
        return

    def show_edge(self, edge_id):
        '''Displays edge with covolume.

        :param edge_id: Edge ID for which to show the covolume.
        :type edge_id: int
        '''
        fig = plt.figure()
        ax = fig.gca(projection='3d')
        plt.axis('equal')

        edge_nodes = self.node_coords[self.edges['nodes'][edge_id]]

        # plot all adjacent cells
        col = 'k'
        for cell_id in self.edges['cells'][edge_id]:
            for edge in self.cells['edges'][cell_id]:
                x = self.node_coords[self.edges['nodes'][edge]]
                ax.plot(x[:, 0], x[:, 1], x[:, 2], col)

        # make clear which is the edge
        ax.plot(edge_nodes[:, 0], edge_nodes[:, 1], edge_nodes[:, 2],
                color=col, linewidth=3.0)

        # get cell circumcenters
        cell_ccs = self.cell_circumcenters

        edge_midpoint = 0.5 * (edge_nodes[0] + edge_nodes[1])

        # plot faces in matching colors
        num_local_faces = len(self.edges['faces'][edge_id])
        for k, face_id in enumerate(self.edges['faces'][edge_id]):
            # get rainbow color
            h = float(k) / num_local_faces
            hsv_face_col = numpy.array([[[h, 1.0, 1.0]]])
            col = mpl.colors.hsv_to_rgb(hsv_face_col)[0][0]

            # paint the face
            import mpl_toolkits.mplot3d as mpl3
            face_nodes = self.node_coords[self.faces['nodes'][face_id]]
            tri = mpl3.art3d.Poly3DCollection([face_nodes])
            tri.set_color(mpl.colors.rgb2hex(col))
            # tri.set_alpha(0.5)
            ax.add_collection3d(tri)

            # mark face circumcenters
            face_cc = self._get_face_circumcenter(face_id)
            ax.plot([face_cc[0]], [face_cc[1]], [face_cc[2]],
                    marker='o', color=col)

        # plot covolume
        face_col = '0.7'
        col = 'k'
        for k, face_id in enumerate(self.edges['faces'][edge_id]):
            ccs = cell_ccs[self.faces['cells'][face_id]]
            if len(ccs) == 2:
                tri = mpl3.art3d.Poly3DCollection([
                    numpy.vstack((ccs, edge_midpoint))
                    ])
                tri.set_color(face_col)
                ax.add_collection3d(tri)
                ax.plot(ccs[:, 0], ccs[:, 1], ccs[:, 2], color=col)
            elif len(ccs) == 1:
                tri = mpl3.art3d.Poly3DCollection(
                    [numpy.vstack((ccs[0], face_cc, edge_midpoint))]
                    )
                tri.set_color(face_col)
                ax.add_collection3d(tri)
                ax.plot([ccs[0][0], face_cc[0]],
                        [ccs[0][1], face_cc[1]],
                        [ccs[0][2], face_cc[2]],
                        color=col)
            else:
                raise RuntimeError('???')

        # ax.plot([edge_midpoint[0]],
        #         [edge_midpoint[1]],
        #         [edge_midpoint[2]],
        #         'ro'
        #         )

        # highlight cells
        highlight_cells = []  # [3]
        col = 'r'
        for k in highlight_cells:
            cell_id = self.edges['cells'][edge_id][k]
            ax.plot([cell_ccs[cell_id, 0]],
                    [cell_ccs[cell_id, 1]],
                    [cell_ccs[cell_id, 2]],
                    color=col,
                    marker='o'
                    )
            for edge in self.cells['edges'][cell_id]:
                x = self.node_coords[self.edges['nodes'][edge]]
                ax.plot(x[:, 0], x[:, 1], x[:, 2], col, linestyle='dashed')
        return

    def compute_covolumes(self):
        # Precompute edges.
        edges = \
            self.node_coords[self.edges['nodes'][:, 1]] - \
            self.node_coords[self.edges['nodes'][:, 0]]

        # Build the equation system:
        # The equation
        #
        # |simplex| ||u||^2 = \sum_i \alpha_i <u,e_i> <e_i,u>
        #
        # has to hold for all vectors u in the plane spanned by the edges,
        # particularly by the edges themselves.
        cells_edges = edges[self.cells['edges']]
        # <http://stackoverflow.com/a/38110345/353337>
        A = numpy.einsum('ijk,ilk->ijl', cells_edges, cells_edges)
        # print(numpy.linalg.cond(A))
        A = A**2

        # Compute the RHS  cell_volume * <edge, edge>.
        # The dot product <edge, edge> is also on the diagonals of A (before
        # squaring), but simply computing it again is cheaper than extracting
        # it from A.
        edge_dot_edge = _row_dot(edges, edges)
        rhs = edge_dot_edge[self.cells['edges']] * self.cell_volumes[..., None]

        # Solve all k-by-k systems at once ("broadcast"). (`k` is the number of
        # edges per simplex here.)
        # If the matrix A is (close to) singular if and only if the cell is
        # (close to being) degenerate. Hence, it has volume 0, and so all the
        # edge coefficients are 0, too. Hence, do nothing.
        sol = numpy.linalg.solve(A, rhs)

        num_edges = len(self.edges['nodes'])
        self.covolumes = numpy.zeros(num_edges, dtype=float)
        numpy.add.at(
                self.covolumes,
                self.cells['edges'],
                sol
                )

        # Here, self.covolumes contains the covolume-edgelength ratios. Make
        # sure we end up with the covolumes.
        self.covolumes *= self.edge_lengths

        return

    def compute_covolumes2(self):
        # Precompute edges.
        edges = \
            self.node_coords[self.edges['nodes'][:, 1]] - \
            self.node_coords[self.edges['nodes'][:, 0]]

        scaled_edges = edges / self.edge_lengths[:, None]

        # Build the equation system:
        # The equation
        #
        # |simplex| ||u||^2 = \sum_i \alpha_i <u,e_i> <e_i,u>
        #
        # has to hold for all vectors u in the plane spanned by the edges,
        # particularly by the edges themselves.
        cells_edges = scaled_edges[self.cells['edges']]
        # <http://stackoverflow.com/a/38110345/353337>
        A = numpy.einsum('ijk,ilk->ijl', cells_edges, cells_edges)

        A = A**2

        # Compute the RHS  cell_volume * <edge, edge>.
        # The dot product <edge, edge> is also on the diagonals of A (before
        # squaring), but simply computing it again is cheaper than extracting
        # it from A.
        rhs = numpy.ones((len(self.cell_volumes), cells_edges.shape[1])) \
            * self.cell_volumes[..., None]

        # Solve all k-by-k systems at once ("broadcast"). (`k` is the number of
        # edges per simplex here.)
        # If the matrix A is (close to) singular if and only if the cell is
        # (close to being) degenerate. Hence, it has volume 0, and so all the
        # edge coefficients are 0, too. Hence, do nothing.
        sol = numpy.linalg.solve(A, rhs)

        num_edges = len(self.edges['nodes'])
        self.covolumes = numpy.zeros(num_edges, dtype=float)
        numpy.add.at(
                self.covolumes,
                self.cells['edges'],
                sol
                )

        # Here, self.covolumes contains the covolume-edgelength ratios. Make
        # sure we end up with the covolumes.
        self.covolumes /= self.edge_lengths

        return
