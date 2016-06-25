# -*- coding: utf-8 -*-
#
import meshzoo
import unittest

import pyfvm


class TestLulz(unittest.TestCase):

    def setUp(self):
        return

    def test_io(self):
        vertices, cells = meshzoo.rectangle.create_mesh(
                0.0, 1.0, 0.0, 1.0,
                2, 2,
                zigzag=True
                )
        mesh = pyfvm.meshTri.meshTri(vertices, cells)
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
