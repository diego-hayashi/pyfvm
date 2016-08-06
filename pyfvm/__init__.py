# -*- coding: utf-8 -*-
#
from . import linear_fvm_problem
from . import meshTri
from . import meshTetra
from . import reader

from .discretize_linear import *

__all__ = [
    'linear_fvm_problem',
    'meshTri',
    'meshTetra',
    'reader'
    ]

__version__ = '0.1.0'
__author__ = 'Nico Schlömer'
__author_email__ = 'nico.schloemer@gmail.com'
