# -*- coding: utf-8 -*-
import pyfvm
from pyfvm.form_language import Subdomain, integrate, n_dot_grad, dS, dV, dGamma

import meshzoo
from scipy.sparse import linalg
import voropy


def test():
    class D1(Subdomain):
        def is_inside(self, x):
            return x[1] < 0.5

        is_boundary_only = True

    class Poisson(object):
        def apply(self, u):
            return (
                integrate(lambda x: -n_dot_grad(u(x)), dS)
                + integrate(lambda x: 3.0, dGamma)
                - integrate(lambda x: 1.0, dV)
            )

        def dirichlet(self, u):
            return [(u, D1())]

    vertices, cells = meshzoo.rectangle(0.0, 1.0, 0.0, 1.0, 51, 51)
    mesh = voropy.mesh_tri.MeshTri(vertices, cells)

    matrix, rhs = pyfvm.discretize_linear(Poisson(), mesh)

    u = linalg.spsolve(matrix, rhs)

    mesh.write("out.vtk", point_data={"u": u})
    return


if __name__ == "__main__":
    test()
