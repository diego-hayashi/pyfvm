# -*- coding: utf-8 -*-
#
import meshzoo
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
        assert mesh.check_delaunay()

        mesh.show(save_as='test.tex')

        mesh.write('test.vtu')

        mesh2, _, _ = pyfvm.reader.read('test.vtu')

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
        assert mesh.check_delaunay()

        mesh.show_control_volume(0)
        # mesh.show_edge(0)

        mesh.write('test.vtu')

        mesh2, _, _ = pyfvm.reader.read('test.vtu')

        for k in range(len(mesh.cells['nodes'])):
            self.assertEqual(
                    tuple(mesh.cells['nodes'][k]),
                    tuple(mesh2.cells['nodes'][k])
                    )
        return

if __name__ == '__main__':
    unittest.main()
