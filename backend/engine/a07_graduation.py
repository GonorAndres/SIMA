"""
Graduation Module - Block 7
============================

Smooths raw mortality rates using Whittaker-Henderson graduation before
Lee-Carter fitting.

Theory Connection:
-----------------
Raw mortality data contains random noise, especially at extreme ages where
populations are small. Lee-Carter requires smooth log-rates for stable
SVD decomposition. Whittaker-Henderson graduation solves:

    minimize: sum_x w_x * (z_x - m_x)^2 + lambda * sum_x (Delta^h z_x)^2

Where:
    z_x     = graduated (smoothed) log-rate at age x
    m_x     = observed log-rate at age x
    w_x     = weight (typically exposure, so well-observed ages count more)
    lambda  = smoothing parameter (higher = smoother)
    Delta^h = h-th order difference operator (h=2 penalizes curvature)

The solution is a sparse linear system:
    z = (W + lambda * D'D)^{-1} * W * m

This module smooths each year column independently, producing a graduated
mortality surface with the same shape as the input.

Data Source:
-----------
HMD. Human Mortality Database. Max Planck Institute for Demographic Research
(Germany), University of California, Berkeley (USA), and French Institute for
Demographic Studies (France). Available at www.mortality.org.
"""

from typing import Dict, Optional
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from .a06_mortality_data import MortalityData


class GraduatedRates:
    """
    Graduated (smoothed) mortality rates via Whittaker-Henderson.

    Applies penalized least squares smoothing to log-rates for each year
    independently, then exponentiates back to produce smooth death rates.

    Attributes:
        ages: numpy array of integer ages (same as input)
        years: numpy array of integer years (same as input)
        mx: numpy 2D array (n_ages x n_years) of graduated death rates
        dx: numpy 2D array (n_ages x n_years) of death counts (from input, unchanged)
        ex: numpy 2D array (n_ages x n_years) of exposures (from input, unchanged)
        raw_mx: original unsmoothed death rates for comparison
        lambda_param: smoothing parameter used
        diff_order: difference order used
    """

    def __init__(
        self,
        mortality_data: MortalityData,
        lambda_param: float = 1e5,
        diff_order: int = 2,
        weight_by_exposure: bool = True,
    ):
        """
        Graduate mortality rates from a MortalityData object.

        Parameters
        ----------
        mortality_data : MortalityData
            Raw mortality data with mx, dx, ex matrices.
        lambda_param : float
            Smoothing parameter. Higher = smoother.
            lambda=0 returns raw data; large lambda -> near-polynomial.
        diff_order : int
            Order of the difference penalty (2 = curvature penalty).
        weight_by_exposure : bool
            If True, weight each age by its exposure (person-years).
            Ages with more data get more influence on the fit.
        """
        self.mortality_data = mortality_data
        self.ages = mortality_data.ages.copy()
        self.years = mortality_data.years.copy()
        self.raw_mx = mortality_data.mx.copy()
        self.dx = mortality_data.dx.copy()
        self.ex = mortality_data.ex.copy()
        self.lambda_param = lambda_param
        self.diff_order = diff_order
        self.weight_by_exposure = weight_by_exposure

        # Graduate all year columns
        self.mx = self._graduate_all_years()

    @property
    def n_ages(self) -> int:
        return len(self.ages)

    @property
    def n_years(self) -> int:
        return len(self.years)

    @property
    def shape(self):
        return (self.n_ages, self.n_years)

    @staticmethod
    def _build_difference_matrix(n: int, order: int = 2) -> sparse.csc_matrix:
        """
        Build the h-th order difference matrix D of size (n-h) x n.

        The difference matrix encodes the discrete derivative operator:
            order=1: D[i] = [-1, 1, 0, ...]  (first differences)
            order=2: D[i] = [1, -2, 1, 0, ...]  (second differences)

        Built recursively: D_h = D_1 @ D_{h-1}

        Parameters
        ----------
        n : int
            Number of data points (rows in the original vector).
        order : int
            Difference order (typically 2 for curvature penalty).

        Returns
        -------
        scipy.sparse.csc_matrix
            Sparse difference matrix of shape (n - order, n).
        """
        # Base case: first-order difference matrix
        D = sparse.diags([1.0, -1.0], [0, 1], shape=(n - 1, n), format="csc")

        # Apply recursively for higher orders
        for _ in range(1, order):
            n_rows = D.shape[0] - 1
            D1 = sparse.diags([1.0, -1.0], [0, 1], shape=(n_rows, D.shape[0]), format="csc")
            D = D1 @ D

        return D

    def _whittaker_henderson_1d(
        self,
        log_rates: np.ndarray,
        weights: np.ndarray,
    ) -> np.ndarray:
        """
        Apply Whittaker-Henderson smoothing to a single vector of log-rates.

        Solves: z = (W + lambda * D'D)^{-1} * W * m

        Parameters
        ----------
        log_rates : np.ndarray
            Observed log death rates (length n_ages).
        weights : np.ndarray
            Weights for each age (typically exposure).

        Returns
        -------
        np.ndarray
            Graduated log-rates (same length as input).
        """
        n = len(log_rates)

        # Weight matrix (diagonal)
        W = sparse.diags(weights, 0, format="csc")

        # Difference matrix
        D = self._build_difference_matrix(n, self.diff_order)

        # Penalty matrix: lambda * D'D
        penalty = self.lambda_param * (D.T @ D)

        # Solve: (W + lambda * D'D) * z = W * m
        A = W + penalty
        b = W @ log_rates

        return spsolve(A, b)

    def _graduate_all_years(self) -> np.ndarray:
        """
        Apply Whittaker-Henderson smoothing to each year column independently.

        Works in log-space: log(mx) -> smooth -> exp() back to rate space.
        This ensures graduated rates are always positive.

        Returns
        -------
        np.ndarray
            Graduated death rates matrix (n_ages x n_years).
        """
        log_mx = np.log(self.raw_mx)
        graduated_log_mx = np.empty_like(log_mx)

        for j in range(self.n_years):
            log_col = log_mx[:, j]

            # Weights: use exposure for this year, or uniform
            if self.weight_by_exposure:
                w = self.ex[:, j]
            else:
                w = np.ones(self.n_ages)

            graduated_log_mx[:, j] = self._whittaker_henderson_1d(log_col, w)

        # Exponentiate back to rate space (guarantees positivity)
        return np.exp(graduated_log_mx)

    def get_graduated_mx(self, age: int, year: int) -> float:
        """Get a single graduated death rate by age and year."""
        age_idx = np.searchsorted(self.ages, age)
        if age_idx >= len(self.ages) or self.ages[age_idx] != age:
            raise ValueError(
                f"Age {age} not in graduated data (range: {self.ages[0]}-{self.ages[-1]})"
            )
        year_idx = np.searchsorted(self.years, year)
        if year_idx >= len(self.years) or self.years[year_idx] != year:
            raise ValueError(
                f"Year {year} not in graduated data (range: {self.years[0]}-{self.years[-1]})"
            )
        return float(self.mx[age_idx, year_idx])

    def residuals(self) -> np.ndarray:
        """
        Compute residuals: log(raw) - log(graduated) for diagnostics.

        Residuals should be roughly centered around zero with no
        systematic pattern if the smoothing is appropriate.
        """
        return np.log(self.raw_mx) - np.log(self.mx)

    def roughness(self, rates: np.ndarray) -> float:
        """
        Measure roughness as sum of squared second differences across ages.

        Lower roughness = smoother curve. Used to verify graduation
        actually reduces noise.
        """
        total = 0.0
        for j in range(rates.shape[1]):
            col = np.log(rates[:, j])
            d2 = np.diff(col, n=2)
            total += np.sum(d2 ** 2)
        return total

    def validate(self) -> Dict[str, bool]:
        """
        Validate graduated rates for consistency.

        Returns dict with:
            - no_nan: True if no NaN in graduated rates
            - all_positive: True if all graduated rates > 0
            - smoother_than_raw: True if graduated rates are less rough
            - residual_mean_near_zero: True if mean residual close to 0
        """
        results = {}
        results["no_nan"] = bool(not np.any(np.isnan(self.mx)))
        results["all_positive"] = bool(np.all(self.mx > 0))
        results["smoother_than_raw"] = bool(
            self.roughness(self.mx) < self.roughness(self.raw_mx)
        )
        resid = self.residuals()
        results["residual_mean_near_zero"] = bool(abs(np.mean(resid)) < 0.1)
        return results

    def summary(self) -> Dict:
        """Summary statistics for quick inspection."""
        resid = self.residuals()
        return {
            "shape": self.shape,
            "lambda": self.lambda_param,
            "diff_order": self.diff_order,
            "raw_roughness": self.roughness(self.raw_mx),
            "graduated_roughness": self.roughness(self.mx),
            "roughness_reduction": 1.0 - self.roughness(self.mx) / self.roughness(self.raw_mx),
            "residual_mean": float(np.mean(resid)),
            "residual_std": float(np.std(resid)),
            "validations": self.validate(),
        }

    @classmethod
    def from_hmd(
        cls,
        data_dir: str,
        country: str,
        sex: str = "Male",
        year_min: int = 1990,
        year_max: int = 2023,
        age_max: int = 100,
        lambda_param: float = 1e5,
        diff_order: int = 2,
        weight_by_exposure: bool = True,
        download_date: str = "",
    ) -> "GraduatedRates":
        """
        Convenience: load HMD data and graduate in one step.

        Parameters
        ----------
        data_dir : str
            Path to HMD data directory.
        country : str
            Country subfolder name.
        sex : str
            'Female', 'Male', or 'Total'.
        year_min, year_max : int
            Year range to load.
        age_max : int
            Maximum age (higher ages aggregated).
        lambda_param : float
            Smoothing parameter.
        diff_order : int
            Difference order for penalty.
        weight_by_exposure : bool
            Weight by exposure-years.
        download_date : str
            For HMD citation compliance.

        Returns
        -------
        GraduatedRates
            Graduated mortality rates ready for Lee-Carter.
        """
        data = MortalityData.from_hmd(
            data_dir=data_dir,
            country=country,
            sex=sex,
            year_min=year_min,
            year_max=year_max,
            age_max=age_max,
            download_date=download_date,
        )
        return cls(
            mortality_data=data,
            lambda_param=lambda_param,
            diff_order=diff_order,
            weight_by_exposure=weight_by_exposure,
        )
