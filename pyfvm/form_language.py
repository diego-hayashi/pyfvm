import numpy as np
import sympy


class Subdomain:
    pass


class Boundary(Subdomain):
    is_boundary_only = True

    def is_inside(self, x):
        return np.ones(x.shape[1], dtype=bool)


class FvmProblem:
    pass


class Measure:
    pass


class ControlVolume(Measure):
    def __repr__(self):
        return "dV"


dV = ControlVolume()


class ControlVolumeSurface(Measure):
    def __repr__(self):
        return "dS"


dS = ControlVolumeSurface()


class CellSurface(Measure):
    pass


class EdgeKernel:
    pass


class n_dot_grad(sympy.Function):
    pass


class n_dot(sympy.Function):
    pass


dGamma = CellSurface()


def integrate(integrand, measure, subdomains=None):
    """Convenience function for IntegralSum. Just syntastic sugar."""
    return IntegralSum(integrand, measure, subdomains)


class Integral:
    def __init__(self, integrand, measure, subdomains):
        assert isinstance(measure, Measure)

        if subdomains is None:
            subdomains = set()
        elif not isinstance(subdomains, set):
            try:
                subdomains = set(subdomains)
            except TypeError:  # TypeError: 'D1' object is not iterable
                subdomains = {subdomains}

        assert (
            isinstance(measure, ControlVolumeSurface)
            or isinstance(measure, ControlVolume)
            or isinstance(measure, CellSurface)
        )

        self.integrand = integrand
        self.measure = measure
        self.subdomains = subdomains
        return

    def __repr__(self):
        x = sympy.Symbol("x")
        msg = "pyfvm.Integral({}, {}, {})".format(
            self.integrand(x), self.measure, self.subdomains
        )
        return msg


class IntegralSum:
    def __init__(self, integrand, measure, subdomains):
        self.integrals = [Integral(integrand, measure, subdomains)]
        return

    def __add__(self, other):
        self.integrals.extend(other.integrals)
        return self

    def __sub__(self, other):
        # flip the sign on the integrand of all 'other' integrands
        self.integrals += [
            Integral(
                lambda x: -integral.integrand(x), integral.measure, integral.subdomains
            )
            for integral in other.integrals
        ]
        return self

    def __pos__(self):
        return self

    def __neg__(self):
        # flip the sign on the integrand of all 'self' integrands
        self.integrals = [
            Integral(
                lambda x: -integral.integrand(x), integral.measure, integral.subdomains
            )
            for integral in self.integrals
        ]
        return self

    def __mul__(self, a):
        assert isinstance(a, float) or isinstance(a, int)
        self.integrals = [
            Integral(
                lambda x: a * integral.integrand(x),
                integral.measure,
                integral.subdomains,
            )
            for integral in self.integrals
        ]
        return self

    __rmul__ = __mul__

    def __repr__(self):
        msg = ["pyfvm.IntegralSum("]
        msg += ["  " + integral.__repr__() for integral in self.integrals]
        msg += [")"]
        return "\n".join(msg)
