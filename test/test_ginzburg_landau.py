# -*- coding: utf-8 -*-
#
"""
These tests are against the reference values from pynosh.
"""
import os
import shutil

import pyfvm

import requests
import pykry
import meshplex
import numpy
import pytest


def download_mesh(name):
    filename = os.path.join("/tmp", name)
    if not os.path.exists(filename):
        print("Downloading {}...".format(name))
        url = "https://github.com/nschloe/pynosh/raw/master/test/"
        r = requests.get(url + name, stream=True)
        if not r.ok:
            raise RuntimeError(
                "Download error ({}, return code {}).".format(r.url, r.status_code)
            )
        # save the mesh in /tmp
        with open(filename, "wb") as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

    return filename


class Energy(object):
    """Specification of the kinetic energy operator.
    """

    def __init__(self, mu):
        self.magnetic_field = mu * numpy.array([0.0, 0.0, 1.0])
        self.subdomains = [None]

        return

    def eval(self, mesh, cell_mask):
        nec = mesh.idx_hierarchy[..., cell_mask]
        X = mesh.node_coords[nec]

        edge_midpoint = 0.5 * (X[0] + X[1])
        edge = X[1] - X[0]
        edge_ce_ratio = mesh.ce_ratios[..., cell_mask]

        # project the magnetic potential on the edge at the midpoint
        magnetic_potential = 0.5 * numpy.cross(self.magnetic_field, edge_midpoint)

        # The dot product <magnetic_potential, edge>, executed for many
        # points at once; cf. <http://stackoverflow.com/a/26168677/353337>.
        beta = numpy.einsum("...k,...k->...", magnetic_potential, edge)

        return numpy.array(
            [
                [edge_ce_ratio, -edge_ce_ratio * numpy.exp(-1j * beta)],
                [-edge_ce_ratio * numpy.exp(1j * beta), edge_ce_ratio],
            ]
        )

    # This eval does as if the magnetic vector potential was defined only in the
    # nodes, and interpolates from there. This is what nosh/pynosh do, and it's
    # equivalent to what the above eval() does since the potential is linear.
    #
    # def eval(self, mesh, cell_mask):
    #     nec = mesh.idx_hierarchy[..., cell_mask]
    #     X = mesh.node_coords[nec]
    #
    #     magnetic_potential = numpy.array(
    #         [0.5 * numpy.cross(self.magnetic_field, x) for x in mesh.node_coords]
    #     )
    #
    #     edge = X[1] - X[0]
    #     edge_ce_ratio = mesh.ce_ratios[..., cell_mask]
    #
    #     # The dot product <magnetic_potential, edge>, executed for many
    #     # points at once; cf. <http://stackoverflow.com/a/26168677/353337>.
    #     # beta = numpy.einsum("ijk,ijk->ij", magnetic_potential.T, edge.T)
    #     mp_edge = 0.5 * (magnetic_potential[nec[0]] + magnetic_potential[nec[1]])
    #     beta = numpy.einsum("...k,...k->...", mp_edge, edge)
    #
    #     return numpy.array(
    #         [
    #             [edge_ce_ratio, -edge_ce_ratio * numpy.exp(-1j * beta)],
    #             [-edge_ce_ratio * numpy.exp(1j * beta), edge_ce_ratio],
    #         ]
    #     )


@pytest.mark.parametrize(
    "filename, control_values",
    [
        ("rectanglesmall.e", [0.0063121712308067401, 10.224658806561596]),
        ("pacman.e", [0.37044264296585938, 10.000520856079092]),
        # geometric ce_ratios
        ("cubesmall.e", [0.00012499993489764605, 10.062484361987309]),
        ("brick-w-hole.e", [0.167357712543159, 12.05581968511059]),
        # # Algebraic ce_ratios:
        # ("cubesmall.e", [8.3541623155714007e-05, 10.058364522531498]),
        # ("brick-w-hole.e", [0.16763276012920181, 15.131119904340618]),
    ],
)
def test_keo(filename, control_values):
    filename = download_mesh(filename)
    mu = 1.0e-2

    # read the mesh
    mesh, point_data, field_data, _ = meshplex.read(filename)

    keo = pyfvm.get_fvm_matrix(mesh, edge_kernels=[Energy(mu)])

    tol = 1.0e-13

    # Check that the matrix is Hermitian.
    KK = keo - keo.H
    assert abs(KK.sum()) < tol

    # Check the matrix sum.
    assert abs(control_values[0] - keo.sum()) < tol

    # Check the 1-norm of the matrix |Re(K)| + |Im(K)|.
    # This equals the 1-norm of the matrix defined by the block
    # structure
    #   Re(K) -Im(K)
    #   Im(K)  Re(K).
    K = abs(keo.real) + abs(keo.imag)
    assert abs(control_values[1] - numpy.max(K.sum(0))) < tol
    return


@pytest.mark.parametrize(
    "filename, control_values",
    [
        ("rectanglesmall.e", [20.0126243424616, 20.0063121712308, 0.00631217123080606]),
        ("pacman.e", [605.78628672795264, 605.41584408498682, 0.37044264296586299]),
        # Geometric ce_ratios:
        (
            "cubesmall.e",
            [20.000249999869794, 20.000124999934897, 0.00012499993489734074],
        ),
        ("brick-w-hole.e", [777.7072988143686, 777.5399411018254, 0.16735771254316]),
        (
            "tetrahedron.e",
            [128.3145663425826, 128.3073117169993, 0.0072546255832996644],
        ),
        ("tet.e", [128.316760714389, 128.30840983471703, 0.008350879671951375]),
        # Algebraic ce_ratios:
        # (
        #     "cubesmall.e",
        #     [20.000167083246311, 20.000083541623155, 8.3541623155658495e-05],
        # ),
        # (
        #     "brick-w-hole.e",
        #     [777.70784890954064, 777.54021614941144, 0.16763276012921419],
        # ),
        # (
        #     "tetrahedron.e",
        #     [128.31647020288861, 128.3082636471523, 0.0082065557362998032],
        # ),
        # ("tet.e", [128.31899139655067, 128.30952517579789, 0.0094662207527960365]),
    ],
)
def test_jacobian(filename, control_values):
    filename = download_mesh(filename)
    mu = 1.0e-2

    mesh, point_data, field_data, _ = meshplex.read(filename)

    psi = point_data["psi"][:, 0] + 1j * point_data["psi"][:, 1]

    V = -1.0
    g = 1.0
    keo = pyfvm.get_fvm_matrix(mesh, edge_kernels=[Energy(mu)])

    def jacobian(psi):
        def _apply_jacobian(phi):
            cv = mesh.control_volumes
            y = keo * phi / cv + alpha * phi + gPsi0Squared * phi.conj()
            return y

        alpha = V + g * 2.0 * (psi.real ** 2 + psi.imag ** 2)
        gPsi0Squared = g * psi ** 2

        num_unknowns = len(mesh.node_coords)
        return pykry.LinearOperator(
            (num_unknowns, num_unknowns),
            complex,
            dot=_apply_jacobian,
            dot_adj=_apply_jacobian,
        )

    # Get the Jacobian
    J = jacobian(psi)

    tol = 1.0e-12

    num_unknowns = psi.shape[0]

    # [1+i, 1+i, 1+i, ... ]
    phi = numpy.full(num_unknowns, 1 + 1j)
    val = numpy.vdot(phi, mesh.control_volumes * (J * phi)).real
    assert abs(control_values[0] - val) < tol

    # [1, 1, 1, ... ]
    phi = numpy.full(num_unknowns, 1.0, dtype=complex)
    val = numpy.vdot(phi, mesh.control_volumes * (J * phi)).real
    assert abs(control_values[1] - val) < tol

    # [i, i, i, ... ]
    phi = numpy.full(num_unknowns, 1j, dtype=complex)
    val = numpy.vdot(phi, mesh.control_volumes * (J * phi)).real
    assert abs(control_values[2] - val) < tol
    return


@pytest.mark.parametrize(
    "filename, control_values",
    [
        (
            "rectanglesmall.e",
            [0.50126061034211067, 0.24749434381636057, 0.12373710977782607],
        ),
        ("pacman.e", [0.71366475047893463, 0.12552206259336218, 0.055859319123267033]),
        # Geometric ce_ratios
        (
            "cubesmall.e",
            [0.00012499993489764605, 4.419415080700124e-05, 1.5624991863028015e-05],
        ),
        (
            "brick-w-hole.e",
            [1.8317481239998066, 0.15696030933066502, 0.029179895038465554],
        ),
        # Algebraic ce_ratios
        # (
        #     "cubesmall.e",
        #     [8.3541623156163313e-05, 2.9536515963905867e-05, 1.0468744547749431e-05],
        # ),
        # (
        #     "brick-w-hole.e",
        #     [1.8084716102419285, 0.15654267585120338, 0.03074423493622647],
        # ),
    ],
)
def test_f(filename, control_values):
    filename = download_mesh(filename)
    mesh, point_data, field_data, _ = meshplex.read(filename)

    mu = 1.0e-2
    V = -1.0
    g = 1.0

    keo = pyfvm.get_fvm_matrix(mesh, edge_kernels=[Energy(mu)])

    # compute the Ginzburg-Landau residual
    psi = point_data["psi"][:, 0] + 1j * point_data["psi"][:, 1]
    cv = mesh.control_volumes
    # One divides by the control volumes here. No idea why this has been done in pynosh.
    # Perhaps to make sure that even the small control volumes have a significant
    # contribution to the residual?
    r = keo * psi / cv + psi * (V + g * abs(psi) ** 2)

    # scale with D for compliance with the Nosh (C++) tests
    if mesh.control_volumes is None:
        mesh.compute_control_volumes()
    r *= mesh.control_volumes

    tol = 1.0e-13
    # For C++ Nosh compatibility:
    # Compute 1-norm of vector (Re(psi[0]), Im(psi[0]), Re(psi[1]), ... )
    alpha = numpy.linalg.norm(r.real, ord=1) + numpy.linalg.norm(r.imag, ord=1)
    assert abs(control_values[0] - alpha) < tol
    assert abs(control_values[1] - numpy.linalg.norm(r, ord=2)) < tol
    # For C++ Nosh compatibility:
    # Compute inf-norm of vector (Re(psi[0]), Im(psi[0]), Re(psi[1]), ... )
    alpha = max(
        numpy.linalg.norm(r.real, ord=numpy.inf),
        numpy.linalg.norm(r.imag, ord=numpy.inf),
    )
    assert abs(control_values[2] - alpha) < tol
    return
