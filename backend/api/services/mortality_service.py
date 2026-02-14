"""
Mortality service: bridges API requests to engine modules a06-a10.
"""

import sys
from pathlib import Path
from typing import Optional

_project_dir = str(Path(__file__).parent.parent.parent.parent)
if _project_dir not in sys.path:
    sys.path.insert(0, _project_dir)

import numpy as np

from backend.engine.a10_validation import MortalityComparison
from backend.api.services.precomputed import (
    get_mortality_data,
    get_graduated,
    get_lee_carter,
    get_projection,
    get_regulatory_lt,
    get_projected_life_table,
)


def get_data_summary() -> dict:
    """Return summary of the loaded mortality data."""
    md = get_mortality_data()
    s = md.summary()
    return {
        "country": s["country"],
        "sex": s["sex"],
        "age_range": list(s["age_range"]),
        "year_range": list(s["year_range"]),
        "shape": list(s["shape"]),
        "mx_min": s["mx_min"],
        "mx_max": s["mx_max"],
        "mx_mean": s["mx_mean"],
    }


def get_lee_carter_params() -> dict:
    """Return Lee-Carter fitted parameters."""
    lc = get_lee_carter()
    proj = get_projection()

    return {
        "ages": [int(a) for a in lc.ages],
        "years": [int(y) for y in lc.years],
        "ax": [float(v) for v in lc.ax],
        "bx": [float(v) for v in lc.bx],
        "kt": [float(v) for v in lc.kt],
        "explained_variance": lc.explained_variance,
        "drift": proj.drift,
        "sigma": proj.sigma,
        "validations": lc.validate(),
    }


def get_projection_data(horizon: int = 30, projection_year: int = 2040) -> dict:
    """Return projection data including a projected life table."""
    proj = get_projection()

    # Build a life table for the requested year
    lt = None
    last_year = int(proj.projected_years[-1])
    first_year = int(proj.projected_years[0])

    if first_year <= projection_year <= last_year:
        lt_obj = proj.to_life_table(year=projection_year, radix=100_000)
        lt = {
            "ages": lt_obj.ages,
            "l_x": [lt_obj.l_x[a] for a in lt_obj.ages],
            "q_x": [lt_obj.q_x[a] for a in lt_obj.ages],
            "d_x": [lt_obj.d_x[a] for a in lt_obj.ages],
            "min_age": lt_obj.min_age,
            "max_age": lt_obj.max_age,
        }

    return {
        "projected_years": [int(y) for y in proj.projected_years[:horizon]],
        "kt_central": [float(v) for v in proj.kt_central[:horizon]],
        "drift": proj.drift,
        "sigma": proj.sigma,
        "life_table": lt,
    }


def get_life_table_data(
    table_type: str = "cnsf",
    sex: str = "male",
) -> dict:
    """Return life table data from regulatory tables."""
    lt = get_regulatory_lt(table_type, sex)
    return {
        "ages": lt.ages,
        "l_x": [lt.l_x[a] for a in lt.ages],
        "q_x": [lt.q_x[a] for a in lt.ages],
        "d_x": [lt.d_x[a] for a in lt.ages],
        "min_age": lt.min_age,
        "max_age": lt.max_age,
    }


def get_graduation_data() -> dict:
    """Return raw vs graduated mortality rates + diagnostics."""
    md = get_mortality_data()
    grad = get_graduated()

    ages = list(grad.ages)

    # Average raw mx across years (axis=1) for overlay
    raw_mx_avg = np.mean(md.mx, axis=1).tolist()

    # Average graduated mx across years
    grad_mx_avg = np.mean(grad.mx, axis=1).tolist()

    # Residuals in log-space
    residuals = []
    for r, g in zip(raw_mx_avg, grad_mx_avg):
        if r > 0 and g > 0:
            residuals.append(float(np.log(r) - np.log(g)))
        else:
            residuals.append(0.0)

    # Roughness metrics from summary
    summary = grad.summary()

    return {
        "ages": [int(a) for a in ages],
        "raw_mx": [float(v) for v in raw_mx_avg],
        "graduated_mx": [float(v) for v in grad_mx_avg],
        "residuals": residuals,
        "roughness_raw": float(summary["raw_roughness"]),
        "roughness_graduated": float(summary["graduated_roughness"]),
        "roughness_reduction": float(summary["roughness_reduction"]),
        "lambda_param": float(summary["lambda"]),
    }


def get_surface_data() -> dict:
    """Return 2D log(mx) matrix for 3D surface visualization."""
    grad = get_graduated()

    ages = [int(a) for a in grad.ages]
    years = [int(y) for y in grad.years]

    # log(mx) matrix: shape (n_ages, n_years)
    log_mx = np.log(grad.mx + 1e-10)
    log_mx = [[float(v) for v in row] for row in log_mx]

    return {
        "ages": ages,
        "years": years,
        "log_mx": log_mx,
    }


def get_diagnostics_data() -> dict:
    """Return Lee-Carter goodness-of-fit diagnostics."""
    lc = get_lee_carter()

    gof = lc.goodness_of_fit()

    # Compute residuals matrix manually: log_mx - fitted
    fitted_log = lc.ax[:, np.newaxis] + np.outer(lc.bx, lc.kt)
    residuals_matrix = lc.log_mx - fitted_log

    # Sample residuals (every 10th age, every 5th year for manageable size)
    residuals_sample = []
    for i in range(0, len(lc.ages), 10):
        for j in range(0, len(lc.years), 5):
            residuals_sample.append({
                "age": float(lc.ages[i]),
                "year": float(lc.years[j]),
                "residual": float(residuals_matrix[i, j]),
            })

    return {
        "rmse": float(gof["rmse"]),
        "max_abs_error": float(gof["max_abs_error"]),
        "mean_abs_error": float(gof["mean_abs_error"]),
        "explained_variance": float(lc.explained_variance),
        "residuals_sample": residuals_sample,
    }


def get_validation(projection_year: int = 2040, table_type: str = "cnsf") -> dict:
    """Compare projected life table against a regulatory benchmark."""
    proj = get_projection()
    last_year = int(proj.projected_years[-1])
    first_year = int(proj.projected_years[0])

    if not (first_year <= projection_year <= last_year):
        raise ValueError(
            f"projection_year must be between {first_year} and {last_year}"
        )

    projected_lt = proj.to_life_table(year=projection_year, radix=100_000)
    regulatory_lt = get_regulatory_lt(table_type, sex="male")

    comp = MortalityComparison(
        projected_lt, regulatory_lt,
        name=f"Projected-{projection_year} vs {table_type.upper()}"
    )
    summary = comp.summary()
    ratios = comp.qx_ratio()
    differences = comp.qx_difference()
    ages = comp.overlap_ages[:-1]

    return {
        "name": summary["name"],
        "rmse": summary["rmse"],
        "max_ratio": summary["max_ratio"],
        "min_ratio": summary["min_ratio"],
        "mean_ratio": summary["mean_ratio"],
        "n_ages": summary["n_ages"],
        "ages": [int(a) for a in ages],
        "qx_ratios": [float(r) for r in ratios],
        "qx_differences": [float(d) for d in differences],
    }
