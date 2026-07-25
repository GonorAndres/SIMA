"""
Shared analytic fixtures for the *proposed* engine test suite.

Design principle (see DESIGN.md)
--------------------------------
Every fixture here builds a life table / mortality surface whose actuarial
quantities have a KNOWN CLOSED FORM, so tests can pin the engine to an
independently-derived number rather than to a re-derivation of the engine's
own formula. Two mortality laws are provided because they fail *different*
bugs:

  * Constant force of mortality (``constant_force_lt``):
        l_x = radix * p**x,   p = exp(-mu)   ->   q_x = 1 - p is age-constant.
    Makes the discounted survivors geometric (ratio beta = v*p), so D/N/C/M
    and all APVs collapse to geometric series. Catches discounting/indexing
    bugs.

  * De Moivre / uniform (``de_moivre_lt``):
        l_x = k * (W - x)     ->   d_x = k is constant,  q_x = 1/(W - x).
    A curve where q_x VARIES with age. Catches formula bugs that happen to
    pass under a constant q_x (e.g. a stray averaging or a wrong denominator).
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# Make ``backend`` importable when the suite is run from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.engine.a01_life_table import LifeTable
from backend.engine.a02_commutation import CommutationFunctions
from backend.engine.a03_actuarial_values import ActuarialValues
from backend.engine.a04_premiums import PremiumCalculator
from backend.engine.a05_reserves import ReserveCalculator

# --------------------------------------------------------------------------
# Data locations (present in the repo; HMD files are synthetic-but-valid)
# --------------------------------------------------------------------------
DATA_DIR = str(_REPO_ROOT / "backend" / "data")
HMD_DIR = str(_REPO_ROOT / "backend" / "data" / "hmd")
MOCK_DIR = str(_REPO_ROOT / "backend" / "data" / "mock")

# --------------------------------------------------------------------------
# Constant-force analytic constants (mirrors test_golden_values.py)
# --------------------------------------------------------------------------
MU = 0.03                 # constant force of mortality
INTEREST = 0.05           # annual effective interest
RADIX = 1_000_000
OMEGA = 130               # terminal age; engine forces q_OMEGA = 1

P = math.exp(-MU)         # age-independent one-year survival
Q = 1.0 - P
V = 1.0 / (1.0 + INTEREST)
BETA = V * P              # geometric ratio of discounted survivors
REL = 1e-9                # exact identities -> very tight tolerance


# --- Constant force --------------------------------------------------------
@pytest.fixture(scope="module")
def constant_force_lt():
    ages = list(range(0, OMEGA + 1))
    l_x = [RADIX * P**x for x in ages]
    return LifeTable(ages, l_x)


@pytest.fixture(scope="module")
def comm(constant_force_lt):
    return CommutationFunctions(constant_force_lt, interest_rate=INTEREST)


@pytest.fixture(scope="module")
def av(comm):
    return ActuarialValues(comm)


@pytest.fixture(scope="module")
def pc(comm):
    return PremiumCalculator(comm)


@pytest.fixture(scope="module")
def rc(comm):
    return ReserveCalculator(comm)


# --- De Moivre / uniform ---------------------------------------------------
DM_K = 1000.0
DM_W = 111        # l_x = DM_K * (DM_W - x); ages 0..110 -> no zero survivors
DM_MAX_AGE = 110


@pytest.fixture(scope="module")
def de_moivre_lt():
    ages = list(range(0, DM_MAX_AGE + 1))
    l_x = [DM_K * (DM_W - x) for x in ages]
    return LifeTable(ages, l_x)


# --- Analytic closed-form helpers (constant force) -------------------------
def cf_a_due(x):
    """Whole-life annuity-due under constant force, exact finite-table value.

    a-due_x = (1 - beta**(N+1)) / (1 - beta),  N = OMEGA - x.
    """
    n = OMEGA - x
    return (1.0 - BETA ** (n + 1)) / (1.0 - BETA)


def cf_A_x(x):
    """Whole-life insurance under constant force, exact finite-table value."""
    n = OMEGA - x
    return Q * V * (1.0 - BETA ** n) / (1.0 - BETA) + V ** (n + 1) * P ** n


# --------------------------------------------------------------------------
# Synthetic rank-1 Lee-Carter surface with KNOWN parameters
# --------------------------------------------------------------------------
def build_synthetic_lc_arrays():
    """Return (ages, years, ax, bx, kt, mx, dx, ex) for an exact rank-1 model.

    log(m_{x,t}) = a_x + b_x * k_t  EXACTLY (no noise), with the engine's
    identifiability constraints already satisfied:
        sum(b_x) = 1,  sum(k_t) = 0.
    Deaths are made consistent with the surface (d = e * m) so that k_t
    re-estimation must recover the same k_t.
    """
    ages = np.arange(40, 90)          # 50 ages
    years = np.arange(2000, 2020)     # 20 years
    n_ages, n_years = len(ages), len(years)

    # a_x: smooth increasing log-mortality shape
    ax = -9.0 + 0.06 * (ages - 40)

    # b_x: positive, decreasing, normalized to sum to exactly 1
    bx_raw = np.linspace(2.0, 0.5, n_ages)
    bx = bx_raw / bx_raw.sum()

    # k_t: linear declining trend, centered to sum exactly 0
    kt_raw = np.linspace(10.0, -10.0, n_years)
    kt = kt_raw - kt_raw.mean()

    log_mx = ax[:, None] + np.outer(bx, kt)
    mx = np.exp(log_mx)

    ex = np.full((n_ages, n_years), 100_000.0)   # arbitrary positive exposure
    dx = ex * mx                                  # deaths consistent with mx

    return ages, years, ax, bx, kt, mx, dx, ex
