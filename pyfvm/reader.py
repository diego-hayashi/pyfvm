# -*- coding: utf-8 -*-
#
'''
Module for reading unstructured grids (and related data) from various file
formats.

.. moduleauthor:: Nico Schlömer <nico.schloemer@gmail.com>
'''
import os
import meshio
import numpy
import pyfvm

__all__ = ['read']


def read(filename, timestep=None):
    '''Reads an unstructured mesh with added data.

    :param filenames: The files to read from.
    :type filenames: str
    :param timestep: Time step to read from, in case of an Exodus input mesh.
    :type timestep: int, optional
    :returns mesh{2,3}d: The mesh data.
    :returns point_data: Point data read from file.
    :type point_data: dict
    :returns field_data: Field data read from file.
    :type field_data: dict
    '''
    points, cells_nodes, point_data, cell_data, field_data = \
        meshio.read(filename)

    if 'triangle' in cells_nodes:
        return pyfvm.meshTri.meshTri(points, cells_nodes['triangle']), \
               point_data, field_data
    elif 'tetrahedra' in cells_nodes:
        return pyfvm.meshTetra.meshTetra(points, cells_nodes), \
               point_data, field_data
    else:
        raise RuntimeError('Unknown mesh type.')
    return
