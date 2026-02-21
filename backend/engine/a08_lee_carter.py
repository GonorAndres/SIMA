"""
Lee-Carter Model - Block 8
===========================

Fits the Lee-Carter (1992) mortality model to decompose a log-mortality
surface into age + trend components.

Theory Connection:
-----------------
The Lee-Carter model decomposes central death rates as:

    ln(m_{x,t}) = a_x + b_x * k_t + epsilon_{x,t}

Where:
    a_x = average log-mortality at age x (the "shape")
    b_x = age-specific sensitivity to the time trend
    k_t = time index capturing the general mortality level
    epsilon = random error

Fitting Procedure:
1. a_x = mean_t(ln(m_{x,t}))       -- row means of log-rate matrix
2. R = ln(m) - a_x                  -- residual matrix
3. SVD: R = U * S * V'              -- take first (largest) component
4. b_x = U[:,0] normalized so sum(b_x) = 1
5. k_t = S[0] * V[0,:] re-centered so sum(k_t) = 0
6. Re-estimate k_t to match observed total deaths per year

The re-estimation (step 6) is important: SVD optimizes in log-space,
but we want k_t that reproduces actual death counts. This requires
solving sum_x D_{x,t} = sum_x L_{x,t} * exp(a_x + b_x * k_t) for each t.

Identifiability Constraints:
    sum(b_x) = 1   -- normalizes scale between b_x and k_t
    sum(k_t) = 0   -- centers k_t so a_x captures the average level

Data Source:
-----------
HMD. Human Mortality Database. Max Planck Institute for Demographic Research
(Germany), University of California, Berkeley (USA), and French Institute for
Demographic Studies (France). Available at www.mortality.org.
"""

from typing import Dict, Optional, Union
import numpy as np
from scipy.optimize import brentq

from .a06_mortality_data import MortalityData


class LeeCarter:
    """
    Fitted Lee-Carter mortality model.

    After fitting, provides:
        a_x: age pattern (average log-mortality)
        b_x: age sensitivity to trend
        k_t: time index of mortality level
        fitted rates via exp(a_x + b_x * k_t)

    Attributes:
        ages: numpy array of ages
        years: numpy array of years
        ax: numpy array of a_x values (length n_ages)
        bx: numpy array of b_x values (length n_ages, sum=1)
        kt: numpy array of k_t values (length n_years, sum=0)
        log_mx: original log death rate matrix used for fitting
        explained_variance: fraction of variance explained by first SVD component
    """

    def __init__(
        self,
        ages: np.ndarray,
        years: np.ndarray,
        ax: np.ndarray,
        bx: np.ndarray,
        kt: np.ndarray,
        log_mx: np.ndarray,
        explained_variance: float,
    ):
        self.ages = ages.copy()
        self.years = years.copy()
        self.ax = ax.copy()
        self.bx = bx.copy()
        self.kt = kt.copy()
        self.log_mx = log_mx.copy()
        self.explained_variance = explained_variance

    @property
    def n_ages(self) -> int:
        return len(self.ages)

    @property
    def n_years(self) -> int:
        return len(self.years)

    @classmethod
    def fit(
        cls,
        data: Union[MortalityData, "GraduatedRates"],
        reestimate_kt: bool = True,
    ) -> "LeeCarter":
        """
        Fit Lee-Carter model to mortality data.

        Parameters
        ----------
        data : MortalityData or GraduatedRates
            Must expose .mx, .dx, .ex, .ages, .years attributes.
        reestimate_kt : bool
            If True, re-estimate k_t to match observed total deaths.

        Returns
        -------
        LeeCarter
            Fitted model with a_x, b_x, k_t parameters.
        """
        log_mx = np.log(data.mx)

        # Step 1: a_x = row means of log-rate matrix
        ax = cls._compute_ax(log_mx)

        # Step 2: Residual matrix
        residual = log_mx - ax[:, np.newaxis]

        # Step 3-5: SVD decomposition with constraints
        bx, kt, explained_var, kt_offset = cls._svd_decomposition(residual)

        # Absorb k_t centering offset into a_x so that
        # a_x + b_x * k_t exactly reconstructs the first SVD component
        ax = ax + bx * kt_offset

        # Step 6: Re-estimate k_t to match observed deaths
        if reestimate_kt:
            kt, kt_reest_offset = cls._reestimate_kt(ax, bx, data.dx, data.ex)
            # Absorb centering offset into a_x for model self-consistency
            ax = ax + bx * kt_reest_offset

        return cls(
            ages=data.ages,
            years=data.years,
            ax=ax,
            bx=bx,
            kt=kt,
            log_mx=log_mx,
            explained_variance=explained_var,
        )

    @staticmethod
    def _compute_ax(log_mx: np.ndarray) -> np.ndarray:
        """
        Compute a_x as row means of log-mortality matrix.

        a_x = (1/T) * sum_t ln(m_{x,t})

        This captures the average mortality "shape" across all years.
        """
        return np.mean(log_mx, axis=1)

    @staticmethod
    def _svd_decomposition(residual: np.ndarray):
        """
        Extract b_x, k_t from the first SVD component of the residual matrix.

        SVD: R = U * S * V'
        First component: R ≈ S[0] * U[:,0] * V[0,:]

        Constraints applied:
            sum(b_x) = 1   (normalize U column)
            sum(k_t) = 0   (re-center V row)

        Returns
        -------
        bx : np.ndarray
            Normalized first left singular vector (length n_ages).
        kt : np.ndarray
            Scaled and centered first right singular vector (length n_years).
        explained_variance : float
            Fraction of total variance explained by first component.
        """
        U, S, Vt = np.linalg.svd(residual, full_matrices=False)

        # Explained variance: S[0]^2 / sum(S^2)
        explained_var = S[0] ** 2 / np.sum(S ** 2)

        # Raw components
        bx_raw = U[:, 0]
        kt_raw = S[0] * Vt[0, :]

        # Apply identifiability constraints
        bx, kt, kt_offset = LeeCarter._apply_constraints(bx_raw, kt_raw)

        return bx, kt, explained_var, kt_offset

    @staticmethod
    def _apply_constraints(bx_raw: np.ndarray, kt_raw: np.ndarray):
        """
        Apply identifiability constraints:
            sum(b_x) = 1
            sum(k_t) = 0

        Since b_x * k_t is invariant under b_x -> c*b_x, k_t -> k_t/c,
        we normalize b_x to sum to 1 and scale k_t accordingly.

        Then we center k_t by subtracting its mean. The offset is returned
        so that a_x can be adjusted: a_x_new = a_x + b_x * kt_offset.
        This ensures the fitted rates a_x + b_x * k_t exactly reconstruct
        the first SVD component of the log-mortality matrix.
        """
        # Normalize b_x to sum to 1
        bx_sum = np.sum(bx_raw)

        # Handle sign: convention is b_x should be mostly positive
        # (mortality sensitivity is positive for most ages)
        if bx_sum < 0:
            bx_raw = -bx_raw
            kt_raw = -kt_raw
            bx_sum = -bx_sum

        bx = bx_raw / bx_sum
        kt = kt_raw * bx_sum

        # Center k_t to sum to 0, capturing the offset for a_x adjustment
        kt_offset = np.mean(kt)
        kt = kt - kt_offset

        return bx, kt, kt_offset

    @staticmethod
    def _reestimate_kt(
        ax: np.ndarray,
        bx: np.ndarray,
        dx: np.ndarray,
        ex: np.ndarray,
    ) -> np.ndarray:
        """
        Re-estimate k_t to match observed total deaths per year.

        For each year t, solve:
            sum_x d_{x,t} = sum_x L_{x,t} * exp(a_x + b_x * k_t)

        This is a 1D root-finding problem solved with Brent's method.

        The re-estimation is important because SVD minimizes error in
        log-space, but actuarial applications need accurate death counts.

        When b_x has negative components (some ages improve opposite to
        the general trend), the death_residual(k) function may be
        non-monotone. In this case a fixed bracket may fail, so we
        search adaptively for a sign change.
        """
        n_years = dx.shape[1]
        kt_new = np.zeros(n_years)

        for t in range(n_years):
            observed_deaths = np.sum(dx[:, t])
            exposures_t = ex[:, t]

            def death_residual(k):
                """Difference between model-implied and observed deaths."""
                model_rates = np.exp(ax + bx * k)
                model_deaths = np.sum(exposures_t * model_rates)
                return model_deaths - observed_deaths

            try:
                kt_new[t] = brentq(death_residual, -500, 500)
            except ValueError:
                # Fixed bracket failed. Search adaptively for a sign change.
                # With negative b_x, the function is U-shaped: large positive
                # at extreme k, with a minimum somewhere in the middle.
                # We sample the function to find where it crosses zero.
                found = False
                k_candidates = np.linspace(-500, 500, 201)
                f_vals = np.array([death_residual(k) for k in k_candidates])

                for i in range(len(f_vals) - 1):
                    if f_vals[i] * f_vals[i + 1] < 0:
                        kt_new[t] = brentq(
                            death_residual, k_candidates[i], k_candidates[i + 1]
                        )
                        found = True
                        break

                if not found:
                    # No sign change found: the model-implied deaths never
                    # reach the observed count. Use the k that minimizes
                    # |residual| as best approximation.
                    best_idx = np.argmin(np.abs(f_vals))
                    kt_new[t] = k_candidates[best_idx]

        # Re-center to sum=0, return offset for a_x adjustment
        kt_offset = np.mean(kt_new)
        kt_new = kt_new - kt_offset

        return kt_new, kt_offset

    def get_ax(self, age: int) -> float:
        """Get a_x for a specific age."""
        idx = np.searchsorted(self.ages, age)
        if idx >= len(self.ages) or self.ages[idx] != age:
            raise ValueError(
                f"Age {age} not in model (range: {self.ages[0]}-{self.ages[-1]})"
            )
        return float(self.ax[idx])

    def get_bx(self, age: int) -> float:
        """Get b_x for a specific age."""
        idx = np.searchsorted(self.ages, age)
        if idx >= len(self.ages) or self.ages[idx] != age:
            raise ValueError(
                f"Age {age} not in model (range: {self.ages[0]}-{self.ages[-1]})"
            )
        return float(self.bx[idx])

    def get_kt(self, year: int) -> float:
        """Get k_t for a specific year."""
        idx = np.searchsorted(self.years, year)
        if idx >= len(self.years) or self.years[idx] != year:
            raise ValueError(
                f"Year {year} not in model (range: {self.years[0]}-{self.years[-1]})"
            )
        return float(self.kt[idx])

    def fitted_rate(self, age: int, year: int) -> float:
        """
        Compute fitted death rate: exp(a_x + b_x * k_t).

        This is the model's estimate of the central death rate at
        a given age and year.
        """
        ax = self.get_ax(age)
        bx = self.get_bx(age)
        kt = self.get_kt(year)
        return float(np.exp(ax + bx * kt))

    def fitted_mx_matrix(self) -> np.ndarray:
        """
        Compute the full matrix of fitted death rates.

        Returns
        -------
        np.ndarray
            Matrix (n_ages x n_years) of exp(a_x + b_x * k_t).
        """
        return np.exp(self.ax[:, np.newaxis] + np.outer(self.bx, self.kt))

    def goodness_of_fit(self) -> Dict:
        """
        Compute goodness-of-fit metrics.

        Returns:
            explained_variance: fraction of variance in log(mx) explained
            rmse: root mean squared error in log-space
            max_abs_error: maximum absolute error in log-space
        """
        fitted_log = self.ax[:, np.newaxis] + np.outer(self.bx, self.kt)
        errors = self.log_mx - fitted_log

        return {
            "explained_variance": self.explained_variance,
            "rmse": float(np.sqrt(np.mean(errors ** 2))),
            "max_abs_error": float(np.max(np.abs(errors))),
            "mean_abs_error": float(np.mean(np.abs(errors))),
        }

    def validate(self) -> Dict[str, bool]:
        """
        Validate Lee-Carter parameter constraints.

        Returns dict with:
            bx_sums_to_one: sum(b_x) ≈ 1
            kt_sums_to_zero: sum(k_t) ≈ 0
            no_nan: no NaN in any parameter
            explained_var_reasonable: explained variance > 50%
        """
        return {
            "bx_sums_to_one": bool(abs(np.sum(self.bx) - 1.0) < 1e-6),
            "kt_sums_to_zero": bool(abs(np.sum(self.kt)) < 1e-6),
            "no_nan": bool(
                not np.any(np.isnan(self.ax))
                and not np.any(np.isnan(self.bx))
                and not np.any(np.isnan(self.kt))
            ),
            "explained_var_reasonable": bool(self.explained_variance > 0.5),
        }

    def summary(self) -> Dict:
        """Summary statistics for the fitted model."""
        gof = self.goodness_of_fit()
        return {
            "n_ages": self.n_ages,
            "n_years": self.n_years,
            "age_range": (int(self.ages[0]), int(self.ages[-1])),
            "year_range": (int(self.years[0]), int(self.years[-1])),
            "explained_variance": self.explained_variance,
            "rmse": gof["rmse"],
            "kt_trend": "decreasing" if self.kt[-1] < self.kt[0] else "increasing",
            "kt_range": (float(np.min(self.kt)), float(np.max(self.kt))),
            "validations": self.validate(),
        }

    @classmethod
    def fit_from_hmd(
        cls,
        data_dir: str,
        country: str,
        sex: str = "Male",
        year_min: int = 1990,
        year_max: int = 2023,
        age_max: int = 100,
        graduate: bool = False,
        lambda_param: float = 1e5,
        reestimate_kt: bool = True,
        download_date: str = "",
    ) -> "LeeCarter":
        """
        Convenience: load HMD data, optionally graduate, and fit Lee-Carter.

        Parameters
        ----------
        data_dir : str
            Path to HMD data directory.
        country : str
            Country subfolder name.
        sex : str
            'Female', 'Male', or 'Total'.
        year_min, year_max : int
            Year range.
        age_max : int
            Maximum age.
        graduate : bool
            If True, apply Whittaker-Henderson smoothing before fitting.
        lambda_param : float
            Smoothing parameter (only used if graduate=True).
        reestimate_kt : bool
            If True, re-estimate k_t to match observed deaths.
        download_date : str
            For HMD citation.

        Returns
        -------
        LeeCarter
            Fitted model.
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

        if graduate:
            from .a07_graduation import GraduatedRates
            data = GraduatedRates(data, lambda_param=lambda_param)

        return cls.fit(data, reestimate_kt=reestimate_kt)
