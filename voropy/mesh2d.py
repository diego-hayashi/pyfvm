# -*- coding: utf-8 -*-
# ==============================================================================
__all__ = ['mesh2d']

import numpy as np
from base import _base_mesh
# ==============================================================================
class mesh2d(_base_mesh):
    # --------------------------------------------------------------------------
    def __init__(self, nodes, cells):
        '''Initialization.
        '''
        super(mesh2d, self).__init__(nodes, cells)
        self.node_coords = nodes
        self.edges = None

        # Wait for Numpy 1.6.1 for this
        #     self.cells = np.array(cells, dtype=np.dtype([('nodes', (int, 3))]))
        # to work. Check out
        # http://stackoverflow.com/questions/9467547/how-to-properly-initialize-numpy-array-with-named-fields
        num_cells = len(cells)
        self.cells = np.empty(num_cells, dtype=np.dtype([('nodes', (int, 3))]))
        self.cells['nodes'] = cells

        self.cells_volume = None
        self.cell_circumcenters = None
        self.control_volumes = None
        return
    # --------------------------------------------------------------------------
    def create_cells_volume(self):
        '''Returns the area of triangle spanned by the two given edges.'''
        import vtk
        num_cells = len(self.cells['nodes'])
        self.cells_volume = np.empty(num_cells, dtype=float)
        for cell_id, cell in enumerate(self.cells):
            #edge0 = node0 - node1
            #edge1 = node1 - node2
            #self.cells_volume[cell_id] = 0.5 * np.linalg.norm( np.cross( edge0, edge1 ) )
            # Append a third component.
            z = np.zeros((3, 1))
            x = np.c_[self.node_coords[cell['nodes']], z]
            self.cells_volume[cell_id] = \
               abs(vtk.vtkTriangle.TriangleArea(x[0], x[1], x[2]))
        return
    # --------------------------------------------------------------------------
    def create_cell_circumcenters( self ):
        '''Computes the center of the circumsphere of each cell.
        '''
        import vtk
        num_cells = len(self.cells['nodes'])
        self.cell_circumcenters = np.empty(num_cells, dtype=np.dtype((float, 2)))
        for cell_id, cell in enumerate(self.cells):
            x = self.node_coords[cell['nodes']]
            vtk.vtkTriangle.Circumcircle(x[0], x[1], x[2],
                                         self.cell_circumcenters[cell_id])

        return
    # --------------------------------------------------------------------------
    def create_adjacent_entities( self ):
        '''Setup edge-node and edge-cell relations.
        '''
        if self.edges is not None:
            return

        # Get upper bound for number of edges; trim later.
        max_num_edges = 3 * len(self.cells['nodes'])

        dt = np.dtype([('nodes', (int, 2)), ('cells', np.object)])
        self.edges = np.empty(max_num_edges, dtype=dt)
        # To create an array of empty lists, do what's described at
        # http://mail.scipy.org/pipermail/numpy-discussion/2009-November/046566.html
        filler = np.frompyfunc(lambda x: list(), 1, 1)
        self.edges['cells'] = filler(self.edges['cells'])

        # Extend the self.cells array by the 'edges' "keyword".
        dt = np.dtype([('nodes', (int, 3)), ('edges', (int, 3))])
        cells = self.cells['nodes']
        self.cells = np.empty(len(cells), dtype=dt)
        self.cells['nodes'] = cells

        # The (sorted) dictionary edges keeps track of how nodes and edges
        # are connected.
        # If  node_edges[(3,4)] == 17  is true, then the nodes (3,4) are
        # connected  by edge 17.
        registered_edges = {}

        new_edge_gid = 0
        # Loop over all elements.
        for cell_id, cell in enumerate(self.cells):
            # We're treating simplices so loop over all combinations of
            # local nodes.
            # Make sure cellNodes are sorted.
            self.cells['nodes'][cell_id] = np.sort(self.cells['nodes'][cell_id])
            for k in xrange(len(cell['nodes'])):
                # Remove the k-th element. This makes sure that the k-th
                # edge is opposite of the k-th node. Useful later in
                # in construction of edge (face) normals.
                indices = tuple(cell['nodes'][:k]) \
                        + tuple(cell['nodes'][k+1:])
                if indices in registered_edges:
                    edge_gid = registered_edges[indices]
                    self.edges[edge_gid]['cells'].append( cell_id )
                    self.cells[cell_id]['edges'][k] = edge_gid
                else:
                    # add edge
                    # The alternative
                    #   self.edges[new_edge_gid]['nodes'] = indices
                    # doesn't work here. Check out
                    # http://projects.scipy.org/numpy/ticket/2068
                    self.edges['nodes'][new_edge_gid] = indices
                    # edge['cells'] is also always ordered.
                    self.edges['cells'][new_edge_gid].append( cell_id )
                    self.cells['edges'][cell_id][k] = new_edge_gid
                    registered_edges[indices] = new_edge_gid
                    new_edge_gid += 1

        # trim edges
        self.edges = self.edges[:new_edge_gid]

        return
    # --------------------------------------------------------------------------
    def refine( self ):
        '''Canonically refine a mesh by inserting nodes at all edge midpoints
        and make four triangular elements where there was one.'''
        if self.edges is None:
            raise RuntimeError('Edges must be defined to do refinement.')

        # Record the newly added nodes.
        num_new_nodes = len(self.edges['nodes'])
        new_nodes = np.empty(num_new_nodes, dtype=np.dtype((float, 2)))
        self.node_coords = np.append(self.node_coords, new_nodes, axis=0)
        new_node_gid = len(self.node_coords)

        # After the refinement step, all previous edge-node associations will
        # be obsolete, so record *all* the new edges.
        num_new_edges = 2 * len(self.edges['nodes']) \
                      + 3 * len(self.cells['nodes'])
        new_edges_nodes = np.empty(num_new_edges, dtype=np.dtype((int, 2)))
        new_edge_gid = 0

        # After the refinement step, all previous cell-node associations will
        # be obsolete, so record *all* the new cells.
        num_new_cells = 4 * len(self.cells['nodes'])
        new_cells_nodes = np.empty(num_new_cells, dtype=np.dtype((int, 3)))
        new_cells_edges = np.empty(num_new_cells, dtype=np.dtype((int, 3)))
        new_cell_gid = 0

        num_edges = len(self.edges['nodes'])
        is_edge_divided = np.zeros(num_edges, dtype=bool)
        edge_midpoint_gids = np.empty(num_edges, dtype=int)
        edge_newedges_gids = np.empty(num_edges, dtype=np.dtype((int, 2)))
        # Loop over all elements.
        for cell_id, cell in enumerate(self.cells):
            # Divide edges.
            local_edge_midpoint_gids = np.empty(3, dtype=int)
            local_edge_newedges = np.empty(3, dtype=np.dtype((int, 2)))
            local_neighbor_midpoints = [ [], [], [] ]
            local_neighbor_newedges = [ [], [], [] ]
            for k, edge_gid in enumerate(cell['edges']):
                edgenodes_gids = self.edges['nodes'][edge_gid]
                if is_edge_divided[edge_gid]:
                    # Edge is already divided. Just keep records
                    # for the cell creation.
                    local_edge_midpoint_gids[k] = \
                        edge_midpoint_gids[edge_gid]
                    local_edge_newedges[k] = edge_midpoint_gids[edge_gid]
                else:
                    # Create new node at the edge midpoint.
                    self.node_coords[new_node_gid] = \
                        0.5 * (self.node_coords[edgenodes_gids[0]] \
                              +self.node_coords[edgenodes_gids[1]])
                    local_edge_midpoint_gids[k] = new_node_gid
                    new_node_gid += 1
                    edge_midpoint_gids[edge_gid] = \
                        local_edge_midpoint_gids[k]

                    # Divide edge into two.
                    new_edges_nodes[new_edge_gid] = \
                        np.array([edgenodes_gids[0], local_edge_midpoint_gids[k]])
                    new_edge_gid += 1
                    new_edges_nodes[new_edge_gid] = \
                        np.array([local_edge_midpoint_gids[k], edgenodes_gids[1]])
                    new_edge_gid += 1

                    local_edge_newedges[k] = [new_edge_gid-2, new_edge_gid-1]
                    edge_newedges_gids[edge_gid] = \
                        local_edge_newedges[k]
                    # Do the household.
                    is_edge_divided[edge_gid] = True
                # Keep a record of the new neighbors of the old nodes.
                # Get local node IDs.
                edgenodes_lids = [np.nonzero(cell['nodes'] == edgenodes_gids[0])[0][0],
                                  np.nonzero(cell['nodes'] == edgenodes_gids[1])[0][0]]
                local_neighbor_midpoints[edgenodes_lids[0]] \
                    .append( local_edge_midpoint_gids[k] )
                local_neighbor_midpoints[edgenodes_lids[1]]\
                    .append( local_edge_midpoint_gids[k] )
                local_neighbor_newedges[edgenodes_lids[0]] \
                    .append( local_edge_newedges[k][0] )
                local_neighbor_newedges[edgenodes_lids[1]] \
                    .append( local_edge_newedges[k][1] )

            new_edge_opposite_of_local_node = np.empty(3, dtype=int)
            # New edges: Connect the three midpoints.
            for k in xrange(3):
                new_edges_nodes[new_edge_gid] = local_neighbor_midpoints[k]
                new_edge_opposite_of_local_node[k] = new_edge_gid
                new_edge_gid += 1

            # Create new elements.
            # Center cell:
            new_cells_nodes[new_cell_gid] = local_edge_midpoint_gids
            new_cells_edges[new_cell_gid] = new_edge_opposite_of_local_node
            new_cell_gid += 1
            # The three corner elements:
            for k in xrange(3):
                new_cells_nodes[new_cell_gid] = \
                    np.array([self.cells['nodes'][cell_id][k],
                              local_neighbor_midpoints[k][0],
                              local_neighbor_midpoints[k][1]])
                new_cells_edges[new_cell_gid] = \
                    np.array([new_edge_opposite_of_local_node[k],
                              local_neighbor_newedges[k][0],
                              local_neighbor_newedges[k][1]])
                new_cell_gid += 1

        self.edges['nodes'] = new_edges_nodes
        self.cells['nodes'] = new_cells_nodes
        self.cells['edges'] = new_cells_edges
        return
    # --------------------------------------------------------------------------
    def compute_control_volumes( self ):
        '''Compute the control volumes.
        '''
        num_nodes = len(self.node_coords)
        self.control_volumes = np.zeros((num_nodes, 1), dtype = float)

        # compute cell circumcenters
        if self.cell_circumcenters is None:
            self.create_cell_circumcenters()

        if self.edges is None:
            self.create_adjacent_entities()

        # Compute covolumes and control volumes.
        num_edges = len(self.edges['nodes'])
        for edge_id in xrange(num_edges):
            # Move the system such that one of the two end points is in the
            # origin. Deliberately take self.edges['nodes'][edge_id][0].
            node = self.node_coords[self.edges['nodes'][edge_id][0]]

            # The orientation of the coedge needs gauging.
            # Do it in such as a way that the control volume contribution
            # is positive if and only if the area of the triangle
            # (node, other0, edge_midpoint) (in this order) is positive.
            # Equivalently, the triangle (node, edge_midpoint, other1) could
            # be considered.
            # other{0,1} refer to that one node of the adjacent.
            # Get the opposing node of the first adjacent cell.
            cell0 = self.edges['cells'][edge_id][0]
            edge_idx = np.nonzero(self.cells['edges'][cell0] == edge_id)[0][0]
            # This makes use of the fact that cellsEdges and cellsNodes
            # are coordinated such that in cell #i, the edge cellsEdges[i][k]
            # opposes cellsNodes[i][k].
            other0 = self.node_coords[self.cells['nodes'][cell0][edge_idx]] \
                   - node
            node_ids = self.edges['nodes'][edge_id]
            node_coords = self.node_coords[node_ids]
            edge_midpoint = 0.5 * (node_coords[0] + node_coords[1]) \
                          - node
            # Computing the triangle volume like this is called the shoelace
            # formula and can be interpreted as the z-component of the
            # cross-product of other0 and edge_midpoint.
            gauge = other0[0] * edge_midpoint[1] \
                  - other0[1] * edge_midpoint[0]

            # Get the circumcenters of the adjacent cells.
            cc = self.cell_circumcenters[self.edges['cells'][edge_id]] \
               - node
            if len(cc) == 2: # interior edge
                self.control_volumes[node_ids] += np.sign(gauge) \
                                                * 0.5 * (cc[0][0] * cc[1][1] \
                                                        -cc[0][1] * cc[1][0])
            elif len(cc) == 1: # boundary edge
                self.control_volumes[node_ids] += np.sign(gauge) \
                                                * 0.5 * (cc[0][0] * edge_midpoint[1]
                                                        -cc[0][1] * edge_midpoint[0])
            else:
                raise RuntimeError('An edge should have either 1 or two adjacent cells.')

        return
    # --------------------------------------------------------------------------
    def compute_edge_normals(self):
        '''Compute the edge normals, pointing either in the direction of the
        cell with larger GID (for interior edges), or towards the outside of
        the domain (for boundary edges).'''
        num_edges = len(self.edges['nodes'])
        edge_normals = np.empty(num_edges, dtype=np.dtype((float, 2)))
        for cell_id, cell in enumerate(self.cells):
            # Loop over the local faces.
            for k in xrange(3):
                edge_id = cell['edges'][k]
                # Compute the normal in the direction of the higher cell ID,
                # or if this is a boundary face, to the outside of the domain.
                neighbor_cell_ids = self.edges['cells'][edge_id]
                if cell_id == neighbor_cell_ids[0]:
                    edge_nodes = self.node_coords[self.edges['nodes'][edge_id]]
                    edge = (edge_nodes[1] - edge_node[0])
                    edge_normals[edge_id] = np.array([-edge[1], edge[0]])
                    edge_normals[edge_id] /= \
                        np.linalg.norm(edge_normals[edge_id])

                    # Make sure the normal points in the outward direction.
                    other_node_id = self.cells['nodes'][cell_id][k]
                    other_node_coords = self.node_coords[other_node_id]
                    if np.dot(edge_node[0]-other_node_coords,
                              edge_normals[edge_id]) < 0.0:
                        edge_normals[edge_id] *= -1

        return edge_normals
    # --------------------------------------------------------------------------
    def show(self, show_covolumes = True):
        '''Plot the mesh.'''
        if self.edges['nodes'] is None:
            self.create_adjacent_entities()

        import matplotlib.pyplot as plt

        fig = plt.figure()
        #ax = fig.gca(projection='3d')
        ax = fig.gca()
        plt.axis('equal')

        # plot edges
        col = 'k'
        for node_ids in self.edges['nodes']:
            x = self.node_coords[node_ids]
            ax.plot(x[:, 0],
                    x[:, 1],
                    col)

        # Highlight covolumes.
        if show_covolumes:
            if self.cell_circumcenters is None:
                self.create_cell_circumcenters()
            covolume_col = '0.5'
            for edge_id in xrange(len(self.edges['cells'])):
                ccs = self.cell_circumcenters[self.edges['cells'][edge_id]]
                if len(ccs) == 2:
                    p = ccs.T
                elif len(ccs) == 1:
                    edge_midpoint = 0.5 * (self.node_coords[self.edges['nodes'][edge_id][0]]
                                          +self.node_coords[self.edges['nodes'][edge_id][1]])
                    p = np.c_[ccs[0], edge_midpoint]
                else:
                    raise RuntimeError('An edge has to have either 1 or 2 adjacent cells.')
                ax.plot(p[0], p[1], color = covolume_col)

        plt.show()
        return
    # --------------------------------------------------------------------------
    def show_node(self, node_id, show_covolume = True):
        '''Plot the vicinity of a node and its covolume.'''
        if self.edges['nodes'] is None:
            self.create_adjacent_entities()

        import matplotlib.pyplot as plt

        fig = plt.figure()
        #ax = fig.gca(projection='3d')
        ax = fig.gca()
        plt.axis('equal')

        # plot edges
        col = 'k'
        for node_ids in self.edges['nodes']:
            if node_id in node_ids:
                x = self.node_coords[node_ids]
                ax.plot(x[:, 0],
                        x[:, 1],
                        col)

        # Highlight covolumes.
        if show_covolume:
            if self.cell_circumcenters is None:
                self.create_cell_circumcenters()
            covolume_boundary_col = '0.5'
            covolume_area_col = '0.7'
            for edge_id in xrange(len(self.edges['cells'])):
                node_ids = self.edges['nodes'][edge_id]
                if node_id in node_ids:
                    ccs = self.cell_circumcenters[self.edges['cells'][edge_id]]
                    if len(ccs) == 2:
                        p = ccs.T
                        q = np.c_[ccs[0], ccs[1], self.node_coords[node_id]]
                    elif len(ccs) == 1:
                        edge_midpoint = 0.5 * (self.node_coords[node_ids[0]]
                                              +self.node_coords[node_ids[1]])
                        p = np.c_[ccs[0], edge_midpoint]
                        q = np.c_[ccs[0], edge_midpoint, self.node_coords[node_id]]
                    else:
                        raise RuntimeError('An edge has to have either 1 or 2 adjacent cells.')
                    ax.fill(q[0], q[1], color = covolume_area_col)
                    ax.plot(p[0], p[1], color = covolume_boundary_col)

        plt.show()
        return
    # --------------------------------------------------------------------------
# ==============================================================================
