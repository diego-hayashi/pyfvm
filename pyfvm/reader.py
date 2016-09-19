# -*- coding: utf-8 -*-
#
'''
Module for reading unstructured grids (and related data) from various file
formats.

.. moduleauthor:: Nico Schlömer <nico.schloemer@gmail.com>
'''
import meshio
import pyfvm

__all__ = ['read']


def read(filename):
    '''Reads an unstructured mesh with added data.

    :param filenames: The files to read from.
    :type filenames: str
    :returns mesh{2,3}d: The mesh data.
    :returns point_data: Point data read from file.
    :type point_data: dict
    :returns field_data: Field data read from file.
    :type field_data: dict
    '''
    points, cells_nodes, point_data, cell_data, field_data = \
        meshio.read(filename)

    if 'tetra' in cells_nodes:
        return pyfvm.mesh_tetra.MeshTetra(points, cells_nodes['tetra']), \
               point_data, cell_data, field_data
    elif 'triangle' in cells_nodes:
        return pyfvm.mesh_tri.MeshTri(points, cells_nodes['triangle']), \
               point_data, cell_data, field_data
    else:
        raise RuntimeError('Unknown mesh type.')
