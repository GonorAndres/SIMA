"""
Mortality Comparison / Validation Module - Block 10
=====================================================

Implements the MortalityComparison class for comparing projected mortality
tables against regulatory benchmarks (e.g., Lee-Carter vs EMSSA-2009).

Theory Connection:
-----------------
When an actuary builds a mortality projection (Lee-Carter, CBD, etc.),
the regulator requires validation against approved tables. The key
metrics are:

    q_x ratio = projected_qx / regulatory_qx
        Measures multiplicative loading. Ratio > 1 means projection
        is more conservative (higher mortality).

    RMSE = sqrt(mean((proj_qx - reg_qx)^2))
        Root mean squared error over a specified age range.
        Lower RMSE means better fit to the regulatory benchmark.

    q_x difference = projected_qx - regulatory_qx
        Signed deviation at each age. Positive means projection
        predicts higher mortality than the benchmark.

Regulatory Context:
------------------
Under LISF/CUSF, Mexican insurers must demonstrate that their
mortality assumptions are consistent with EMSSA-2009 or justify
deviations with statistical evidence. This class provides the
tools for that comparison.
"""

import numpy as np

from .a01_life_table import LifeTable
from .exceptions import ActuarialValidationError


class MortalityComparison:
    """
    Compare two LifeTables: a projected table vs a regulatory benchmark.

    Attributes:
        projected: The projected LifeTable (e.g., from Lee-Carter)
        regulatory: The regulatory benchmark LifeTable (e.g., EMSSA-2009)
        name: Identifier for this comparison
        overlap_ages: Ages present in both tables
    """

    def __init__(self, projected: LifeTable, regulatory: LifeTable, name: str = ""):
        """
        Initialize comparison between two LifeTables.

        Args:
            projected: Projected mortality table
            regulatory: Regulatory benchmark table
            name: Name/label for this comparison

        Raises:
            ValueError: If tables have no overlapping ages
        """
        self.projected = projected
        self.regulatory = regulatory
        self.name = name

        # Find overlapping ages
        proj_ages = set(projected.ages)
        reg_ages = set(regulatory.ages)
        overlap = sorted(proj_ages & reg_ages)

        if len(overlap) < 2:
            raise ValueError(
                f"Tables must have at least 2 overlapping ages, "
                f"but overlap is {overlap}. "
                f"Projected: [{projected.min_age}, {projected.max_age}], "
                f"Regulatory: [{regulatory.min_age}, {regulatory.max_age}]"
            )

        self.overlap_ages: list[int] = overlap

    def _ages_in_range(self, age_start: int, age_end: int) -> list[int]:
        """Return overlapping ages within [age_start, age_end] (inclusive)."""
        if age_start > age_end:
            raise ActuarialValidationError(
                f"age_start ({age_start}) cannot exceed age_end ({age_end})",
                field="age_range",
                constraint="age_start <= age_end",
            )
        return [a for a in self.overlap_ages if age_start <= a <= age_end]

    def qx_ratio(self, *, include_terminal: bool = False) -> np.ndarray:
        """
        Compute projected_qx / regulatory_qx for each overlapping age.

        By default excludes the terminal age of the overlap range (where q_x =
        1.0 in both tables, making the ratio trivially 1.0).

        Args:
            include_terminal: if True, include the terminal overlapping age.

        Returns:
            Array of q_x ratios. Ages where regulatory q_x = 0 are returned as
            NaN to avoid division-by-zero artifacts.
        """
        ages = self.overlap_ages if include_terminal else self.overlap_ages[:-1]

        proj_qx = np.array([self.projected.get_q(a) for a in ages])
        reg_qx = np.array([self.regulatory.get_q(a) for a in ages])

        # Guard against division by zero at ages where regulatory q_x = 0.
        # The caller can use np.nanmean / np.nanmax if needed.
        safe_reg_qx = np.where(reg_qx == 0, np.nan, reg_qx)
        return proj_qx / safe_reg_qx

    def qx_difference(self, *, include_terminal: bool = False) -> np.ndarray:
        """
        Compute projected_qx - regulatory_qx for each overlapping age.

        By default excludes the terminal age (where both q_x = 1.0,
        difference = 0).

        Returns:
            Array of q_x differences.
        """
        ages = self.overlap_ages if include_terminal else self.overlap_ages[:-1]

        proj_qx = np.array([self.projected.get_q(a) for a in ages])
        reg_qx = np.array([self.regulatory.get_q(a) for a in ages])

        return proj_qx - reg_qx

    def rmse(self, age_start: int = 20, age_end: int = 80) -> float:
        """
        Root mean squared error of q_x over [age_start, age_end].

        RMSE = sqrt(mean((proj_qx - reg_qx)^2))

        Args:
            age_start: First age to include (default 20)
            age_end: Last age to include (default 80)

        Returns:
            RMSE value (float)
        """
        ages = self._ages_in_range(age_start, age_end)
        if len(ages) == 0:
            return float("nan")

        proj_qx = np.array([self.projected.get_q(a) for a in ages])
        reg_qx = np.array([self.regulatory.get_q(a) for a in ages])

        diff = proj_qx - reg_qx
        return float(np.sqrt(np.mean(diff**2)))

    def weighted_rmse(
        self, age_start: int = 20, age_end: int = 80, *, weights: np.ndarray | None = None
    ) -> float:
        """
        Weighted RMSE over [age_start, age_end].

        Args:
            weights: Per-age weights. If None, uniform weights are used.

        Returns:
            Weighted RMSE value.
        """
        ages = self._ages_in_range(age_start, age_end)
        if len(ages) == 0:
            return float("nan")

        proj_qx = np.array([self.projected.get_q(a) for a in ages])
        reg_qx = np.array([self.regulatory.get_q(a) for a in ages])
        w = np.ones_like(proj_qx) if weights is None else np.asarray(weights)
        if len(w) != len(proj_qx):
            raise ActuarialValidationError(
                f"weights length ({len(w)}) does not match age count ({len(proj_qx)})",
                field="weights",
                constraint="len(weights) == len(ages)",
            )
        diff = proj_qx - reg_qx
        return float(np.sqrt(np.sum(w * diff**2) / np.sum(w)))

    def bias(self, age_start: int = 20, age_end: int = 80) -> float:
        """
        Mean signed error (bias) over [age_start, age_end].

        Returns:
            Bias = mean(proj_qx - reg_qx).
        """
        ages = self._ages_in_range(age_start, age_end)
        if len(ages) == 0:
            return float("nan")

        proj_qx = np.array([self.projected.get_q(a) for a in ages])
        reg_qx = np.array([self.regulatory.get_q(a) for a in ages])
        return float(np.mean(proj_qx - reg_qx))

    def summary(self, age_start: int = 20, age_end: int = 80) -> dict:
        """
        Return summary statistics for the comparison.

        Args:
            age_start: First age to include (default 20)
            age_end: Last age to include (default 80)

        Returns:
            Dict with name, rmse, bias, max_ratio, min_ratio, mean_ratio,
            n_ages, plus NaN-aware ratio statistics.
        """
        ratios = self.qx_ratio()
        ratios_finite = ratios[np.isfinite(ratios)]

        return {
            "name": self.name,
            "rmse": self.rmse(age_start, age_end),
            "bias": self.bias(age_start, age_end),
            "max_ratio": float(np.nanmax(ratios)) if ratios_finite.size else float("nan"),
            "min_ratio": float(np.nanmin(ratios)) if ratios_finite.size else float("nan"),
            "mean_ratio": float(np.nanmean(ratios)) if ratios_finite.size else float("nan"),
            "n_ages": len(self.overlap_ages),
        }
