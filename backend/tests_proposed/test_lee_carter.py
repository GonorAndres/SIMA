"""
Lee-Carter (a08) -- exact rank-1 recovery.

The strongest possible test of an estimator: generate data from KNOWN
parameters with no noise and require the fit to recover them. We build a
rank-1 log-mortality surface with sum(b)=1, sum(k)=0 and check that a_x,
b_x, k_t come back (up to the engine's own constraints), that the model
reconstructs the input exactly, and that k_t re-estimation reproduces the
observed death totals.
"""

import numpy as np
import pytest

from backend.engine.a06_mortality_data import MortalityData
from backend.engine.a08_lee_carter import LeeCarter
from conftest import build_synthetic_lc_arrays, HMD_DIR


@pytest.fixture(scope="module")
def synthetic():
    ages, years, ax, bx, kt, mx, dx, ex = build_synthetic_lc_arrays()
    data = MortalityData("synthetic", "Male", ages, years, mx, dx, ex)
    return dict(ages=ages, ax=ax, bx=bx, kt=kt, mx=mx, data=data)


def test_recovers_known_parameters_without_reestimation(synthetic):
    # THEORY: for an exact rank-1 surface with the identifiability constraints
    # already satisfied, SVD must return the generating a_x, b_x, k_t.
    # Bug caught: a wrong normalization, sign flip, or centering offset.
    lc = LeeCarter.fit(synthetic["data"], reestimate_kt=False)
    assert np.allclose(lc.ax, synthetic["ax"], atol=1e-8)
    assert np.allclose(lc.bx, synthetic["bx"], atol=1e-8)
    assert np.allclose(lc.kt, synthetic["kt"], atol=1e-8)


def test_identifiability_constraints_hold(synthetic):
    # THEORY: sum(b_x) = 1 and sum(k_t) = 0 by construction of the estimator.
    lc = LeeCarter.fit(synthetic["data"], reestimate_kt=False)
    assert lc.bx.sum() == pytest.approx(1.0, abs=1e-9)
    assert lc.kt.sum() == pytest.approx(0.0, abs=1e-9)


def test_exact_reconstruction_and_full_variance(synthetic):
    # THEORY: a noiseless rank-1 surface is explained 100% by the first
    # component, and exp(a + b k) reproduces the input rates exactly.
    lc = LeeCarter.fit(synthetic["data"], reestimate_kt=False)
    assert lc.explained_variance == pytest.approx(1.0, abs=1e-10)
    assert np.allclose(lc.fitted_mx_matrix(), synthetic["mx"], rtol=1e-9)


def test_bx_sign_convention_positive(synthetic):
    # THEORY: the engine flips signs so b_x is predominantly positive
    # (mortality mostly moves with the trend). Bug caught: an unflipped SVD
    # sign would invert both b_x and the trend direction of k_t.
    lc = LeeCarter.fit(synthetic["data"], reestimate_kt=False)
    assert lc.bx.sum() > 0
    assert np.mean(lc.bx > 0) > 0.9


def test_kt_reestimation_matches_observed_deaths(synthetic):
    # THEORY: re-estimated k_t solves sum_x d_{x,t} = sum_x L_{x,t} e^{a+b k_t}
    # per year, so model-implied total deaths must equal observed totals.
    # This validates the root-finding step, not just the SVD.
    data = synthetic["data"]
    lc = LeeCarter.fit(data, reestimate_kt=True)
    fitted = lc.fitted_mx_matrix()
    implied_deaths = (data.ex * fitted).sum(axis=0)
    observed_deaths = data.dx.sum(axis=0)
    assert np.allclose(implied_deaths, observed_deaths, rtol=1e-6)


def test_fit_on_real_hmd_satisfies_constraints():
    # THEORY: on real (structurally valid) data the fitted model must still
    # obey its invariants and explain the dominant share of variance.
    lc = LeeCarter.fit_from_hmd(
        data_dir=HMD_DIR, country="usa", sex="Male",
        year_min=1990, year_max=2020, age_max=100,
    )
    v = lc.validate()
    assert v["bx_sums_to_one"] and v["kt_sums_to_zero"] and v["no_nan"]
    assert lc.explained_variance > 0.5
