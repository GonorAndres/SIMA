"""
Data Validation Module - Schema / quality checks for mortality data loaders.

This module validates the structure and quality of demographic data files
*before* they are pivoted into the ``MortalityData`` matrices. It is used by
``a06_mortality_data.py`` to turn opaque ``ValueError`` / ``KeyError`` crashes
into structured, regulator-auditable :class:`DataQualityError` reports.

Checks:
    - required columns are present
    - ``Age`` / ``Year`` / ``Anio`` / ``Edad`` columns are parseable integers
    - no missing required cells (NaN / blank)
    - ``mx ≈ dx / ex`` tolerance (after capping/alignment)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .exceptions import DataQualityError

# Extra m_x-vs-dx/ex allowance granted to low-count cells, as a multiple of
# 1/sqrt(deaths). Empirically the HMD discrepancy sits at ~0.05/sqrt(dx) across
# USA + Spain 1990-2019; 0.15 leaves 3x headroom while still failing a cell whose
# rate genuinely disagrees with its own death and exposure counts.
_MX_COUNT_ALLOWANCE = 0.15


def validate_required_columns(
    df: pd.DataFrame,
    required: list[str],
    *,
    filepath: str | Path | None = None,
    source: str = "data",
) -> None:
    """Ensure ``df`` contains all required columns."""
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataQualityError(
            f"{source} file missing required columns: {missing}",
            field="columns",
            constraint=f"required columns: {required}",
        )


def validate_no_missing_cells(
    df: pd.DataFrame,
    columns: list[str],
    *,
    filepath: str | Path | None = None,
    source: str = "data",
) -> None:
    """Ensure selected columns contain no NaN / blank cells."""
    subset = df[columns]
    n_nan = int(subset.isna().sum().sum())
    if n_nan:
        raise DataQualityError(
            f"{source} file has {n_nan} missing values in columns {columns}",
            field="missing_values",
            constraint=f"no missing values in {columns}",
        )


def validate_integer_columns(
    df: pd.DataFrame,
    columns: list[str],
    *,
    filepath: str | Path | None = None,
    source: str = "data",
) -> None:
    """Ensure columns are coercible to integers with no loss."""
    for col in columns:
        coerced = pd.to_numeric(df[col], errors="coerce")
        if coerced.isna().any():
            bad = df[coerced.isna()][col].unique().tolist()
            raise DataQualityError(
                f"{source} column {col!r} contains non-numeric values: {bad[:5]}",
                field=col,
                constraint=f"{col} must be integer-parseable",
            )
        if not ((coerced == coerced.round()).all()):
            raise DataQualityError(
                f"{source} column {col!r} contains non-integer values",
                field=col,
                constraint=f"{col} must contain integers only",
            )


def validate_age_year_range(
    ages: np.ndarray,
    years: np.ndarray,
    *,
    source: str = "data",
    age_min: int | None = None,
    age_max: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
) -> None:
    """Ensure age and year ranges are non-empty and within expected bounds."""
    if len(ages) == 0:
        raise DataQualityError(
            f"{source}: age range is empty", field="age", constraint="len(ages) > 0"
        )
    if len(years) == 0:
        raise DataQualityError(
            f"{source}: year range is empty", field="year", constraint="len(years) > 0"
        )
    if age_min is not None and int(ages.min()) < age_min:
        raise DataQualityError(
            f"{source}: minimum age {int(ages.min())} below expected {age_min}",
            field="age",
            constraint=f"age >= {age_min}",
        )
    if age_max is not None and int(ages.max()) > age_max:
        raise DataQualityError(
            f"{source}: maximum age {int(ages.max())} above expected {age_max}",
            field="age",
            constraint=f"age <= {age_max}",
        )
    if year_min is not None and int(years.min()) < year_min:
        raise DataQualityError(
            f"{source}: minimum year {int(years.min())} below expected {year_min}",
            field="year",
            constraint=f"year >= {year_min}",
        )
    if year_max is not None and int(years.max()) > year_max:
        raise DataQualityError(
            f"{source}: maximum year {int(years.max())} above expected {year_max}",
            field="year",
            constraint=f"year <= {year_max}",
        )


def validate_mx_consistency(
    mx: np.ndarray,
    dx: np.ndarray,
    ex: np.ndarray,
    ages: np.ndarray,
    years: np.ndarray,
    *,
    source: str = "data",
    tolerance: float = 0.01,
) -> None:
    """
    Validate that ``mx`` is approximately ``dx / ex`` across all cells.

    Uses a relative tolerance for positive rates and an absolute tolerance for
    near-zero rates.
    """
    if mx.shape != dx.shape or mx.shape != ex.shape:
        raise DataQualityError(
            f"{source}: shape mismatch mx={mx.shape}, dx={dx.shape}, ex={ex.shape}",
            field="shape",
            constraint="mx.shape == dx.shape == ex.shape",
        )

    denom = np.where(ex == 0, np.nan, ex)
    recomputed = np.where(ex == 0, np.nan, dx / denom)

    # Compare where both mx and recomputed are finite.
    both_finite = np.isfinite(mx) & np.isfinite(recomputed)
    if not np.any(both_finite):
        raise DataQualityError(
            f"{source}: no finite overlapping mx/dx/ex cells to compare",
            field="mx",
            constraint="mx ≈ dx / ex",
        )

    # Relative error for positive cells; absolute error when mx is tiny.
    positive = (mx > 0) & both_finite
    abs_err = np.abs(mx - recomputed)
    rel_err = np.where(positive, abs_err / (mx + 1e-12), abs_err)

    # Published m_x is not literally dx/ex. HMD derives rates from Lexis triangles
    # and publishes all three series rounded independently, so recomputing dx/ex
    # reproduces m_x only up to that redistribution. Measured across USA + Spain
    # 1990-2019 (18,180 cells), the discrepancy is ~0.05/sqrt(dx): negligible where
    # deaths are plentiful, but several percent in cells with a handful of deaths
    # (worst observed: 2.84% at Spain/Female age 7, 2016, with 3 deaths).
    # A flat tolerance therefore cannot separate "small counts" from "wrong data" --
    # it was only ever satisfiable because the synthetic fixtures set dx = mx * ex
    # exactly. Scale the allowance by count and keep `tolerance` as the floor for
    # well-populated cells, where a real inconsistency would still be caught.
    with np.errstate(divide="ignore", invalid="ignore"):
        count_allowance = _MX_COUNT_ALLOWANCE / np.sqrt(np.where(dx > 0, dx, np.nan))
    cell_tolerance = np.where(np.isfinite(count_allowance), count_allowance, tolerance)
    cell_tolerance = np.maximum(cell_tolerance, tolerance)

    exceed = both_finite & (rel_err > cell_tolerance)
    if np.any(exceed):
        # Report the cell that overshoots its own allowance by the widest margin.
        overshoot = np.where(exceed, rel_err / cell_tolerance, -np.inf)
        worst = np.unravel_index(np.nanargmax(overshoot), mx.shape)
        raise DataQualityError(
            f"{source}: mx inconsistent with dx/ex. "
            f"Error {float(rel_err[worst]):.4f} exceeds allowance "
            f"{float(cell_tolerance[worst]):.4f} "
            f"({int(dx[worst])} deaths) "
            f"at age {int(ages[worst[0]])}, year {int(years[worst[1]])}",
            field="mx",
            constraint=(f"mx ≈ dx/ex within max({tolerance}, {_MX_COUNT_ALLOWANCE}/sqrt(dx))"),
        )


class DataQualityReport:
    """
    Structured report object returned by the mortality-data loaders.

    Carries the validated matrices, age/year labels, and a summary of the
    quality checks performed. If the loader could not impute all missing
    values, it raises :class:`DataQualityError` instead of returning a report
    with holes.
    """

    def __init__(
        self,
        *,
        country: str,
        sex: str,
        ages: np.ndarray,
        years: np.ndarray,
        mx: np.ndarray,
        dx: np.ndarray,
        ex: np.ndarray,
        missing_imputed: int = 0,
        open_age_group: int | None = None,
        source: str = "data",
    ):
        self.country = country
        self.sex = sex
        self.ages = ages
        self.years = years
        self.mx = mx
        self.dx = dx
        self.ex = ex
        self.missing_imputed = missing_imputed
        self.open_age_group = open_age_group
        self.source = source

    def to_mortality_data_kwargs(self, download_date: str = "") -> dict[str, Any]:
        """Return the keyword arguments accepted by ``MortalityData.__init__``."""
        return {
            "country": self.country,
            "sex": self.sex,
            "ages": self.ages,
            "years": self.years,
            "mx": self.mx,
            "dx": self.dx,
            "ex": self.ex,
            "download_date": download_date,
        }

    def summary(self) -> dict[str, Any]:
        """Human-readable summary of the data quality report."""
        return {
            "country": self.country,
            "sex": self.sex,
            "source": self.source,
            "shape": self.mx.shape,
            "age_range": (int(self.ages[0]), int(self.ages[-1])),
            "year_range": (int(self.years[0]), int(self.years[-1])),
            "n_missing_imputed": self.missing_imputed,
            "open_age_group": self.open_age_group,
            "mx_min": float(np.min(self.mx)),
            "mx_max": float(np.max(self.mx)),
            "any_non_positive_ex": bool(np.any(self.ex <= 0)),
        }
