# -*- coding: utf-8 -*-
#
import meshzoo
import tempfile
import unittest

import pyfvm


class TestIo(unittest.TestCase):

    def setUp(self):
        return

    def test_io_2d(self):
        vertices, cells = meshzoo.rectangle.create_mesh(
                0.0, 1.0, 0.0, 1.0,
                2, 2,
                zigzag=True
                )
        mesh = pyfvm.meshTri.meshTri(vertices, cells)
        # mesh, _, _, _ = pyfvm.reader.read('pacman.vtu')

        self.assertEqual(mesh.num_delaunay_violations(), 0)

        mesh.show()
        mesh.show_vertex(0)
        # import matplotlib.pyplot as plt
        # plt.show()

        _, fname = tempfile.mkstemp(suffix='.vtu')
        mesh.write(fname)

        mesh2, _, _, _ = pyfvm.reader.read(fname)

        for k in range(len(mesh.cells['nodes'])):
            self.assertEqual(
                    tuple(mesh.cells['nodes'][k]),
                    tuple(mesh2.cells['nodes'][k])
                    )
        return

    def test_io_3d(self):
        vertices, cells = meshzoo.cube.create_mesh(
                0.0, 1.0, 0.0, 1.0, 0.0, 1.0,
                2, 2, 2
                )
        mesh = pyfvm.meshTetra.meshTetra(vertices, cells)

        self.assertEqual(mesh.num_delaunay_violations(), 0)

        # mesh.show_control_volume(0)
        # mesh.show_edge(0)
        # import matplotlib.pyplot as plt
        # plt.show()

        mesh.write('test.vtu')

        mesh2, _, _, _ = pyfvm.reader.read('test.vtu')

        for k in range(len(mesh.cells['nodes'])):
            self.assertEqual(
                    tuple(mesh.cells['nodes'][k]),
                    tuple(mesh2.cells['nodes'][k])
                    )
        return

if __name__ == '__main__':
    unittest.main()
