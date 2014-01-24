# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 Nico Schlömer
#
# This file is part of VoroPy.
#
# VoroPy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# VoroPy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with VoroPy.  If not, see <http://www.gnu.org/licenses/>.
#
import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='voropy',
      version='0.0.2',
      author='Nico Schlömer',
      author_email='nico.schloemer@gmail.com',
      packages=['voropy', 'tests'],
      description='Delaunay meshes, Voronoi regions',
      long_description=read('README.md'),
      url='https://github.com/nschloe/VoroPy',
      download_url=None,
      license='GNU Lesser General Public License (LGPL), Version 3',
      platforms='any',
      requires=['numpy', 'scipy', 'vtk'],
      classifiers=['Development Status :: 3 - Alpha',
                   'Topic :: Utilities'
                   ],
      scripts=['examples/ball',
               'examples/convert_mesh',
               'examples/cube',
               'examples/cylinder_tri',
               'examples/delaunay_checker',
               'examples/delaunay_maker',
               'examples/ellipse',
               'examples/hexagon',
               'examples/lshape',
               'examples/lshape3d',
               'examples/moebius2_tri',
               'examples/moebius_tri',
               'examples/moebius_tri_alt',
               'examples/pacman',
               'examples/pseudomoebius',
               'examples/rectangle',
               'examples/rectangle_with_hole',
               'examples/simple_arrow',
               'examples/sphere',
               'examples/tetrahedron',
               'examples/triangle',
               'examples/tube'],
      )
# Don't install test files.
#        data_files=[('tests', ['tests/cubesmall.e',
#                               'tests/pacman.e',
#                               'tests/rectanglesmall.e',
#                               'tests/test.e',
#                               'tests/tetrahedron.e'])]
