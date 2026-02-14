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
from typing import List

from backend.engine.a01_life_table import LifeTable


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

        self.overlap_ages: List[int] = overlap

    def qx_ratio(self) -> np.ndarray:
        """
        Compute projected_qx / regulatory_qx for each overlapping age.

        Excludes the terminal age of the overlap range (where q_x = 1.0
        in both tables, making the ratio trivially 1.0).

        Returns:
            Array of q_x ratios for non-terminal overlapping ages
        """
        # Exclude the last overlapping age (terminal for the overlap)
        ages = self.overlap_ages[:-1]

        proj_qx = np.array([self.projected.get_q(a) for a in ages])
        reg_qx = np.array([self.regulatory.get_q(a) for a in ages])

        return proj_qx / reg_qx

    def qx_difference(self) -> np.ndarray:
        """
        Compute projected_qx - regulatory_qx for each overlapping age.

        Excludes the terminal age (where both q_x = 1.0, difference = 0).

        Returns:
            Array of q_x differences for non-terminal overlapping ages
        """
        ages = self.overlap_ages[:-1]

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
        ages = [a for a in self.overlap_ages if age_start <= a <= age_end]

        proj_qx = np.array([self.projected.get_q(a) for a in ages])
        reg_qx = np.array([self.regulatory.get_q(a) for a in ages])

        diff = proj_qx - reg_qx
        return float(np.sqrt(np.mean(diff ** 2)))

    def summary(self) -> dict:
        """
        Return summary statistics for the comparison.

        Returns:
            Dict with keys: name, rmse, max_ratio, min_ratio, mean_ratio, n_ages
        """
        ratios = self.qx_ratio()

        return {
            "name": self.name,
            "rmse": self.rmse(),
            "max_ratio": float(np.max(ratios)),
            "min_ratio": float(np.min(ratios)),
            "mean_ratio": float(np.mean(ratios)),
            "n_ages": len(self.overlap_ages),
        }
