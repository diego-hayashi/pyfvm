import meshplex
import meshzoo
import numpy as np
from scipy.sparse import linalg

import pyfvm
from pyfvm.form_language import Boundary, dS, dV, integrate, n_dot, n_dot_grad


def test():
    class DC:
        def apply(self, u):
            a = np.array([2, 1])
            return integrate(
                lambda x: -n_dot_grad(u(x)) + n_dot(a) * u(x), dS
            ) - integrate(lambda x: 1.0, dV)

        def dirichlet(self, u):
            return [(u, Boundary())]

    vertices, cells = meshzoo.rectangle_tri(
        np.linspace(0.0, 2.0, 101), np.linspace(0.0, 1.0, 51)
    )
    mesh = meshplex.Mesh(vertices, cells)

    matrix, rhs = pyfvm.discretize_linear(DC(), mesh)

    u = linalg.spsolve(matrix, rhs)

    mesh.write("out.vtk", point_data={"u": u})


if __name__ == "__main__":
    test()
