"""
Mortality Projection Module - Block 9
======================================

Projects Lee-Carter k_t forward using a Random Walk with Drift, generates
future mortality surfaces, and bridges to the existing LifeTable engine.

Theory Connection:
-----------------
After fitting Lee-Carter (a_x, b_x, k_t), we need to forecast future
mortality. The standard approach models k_t as a Random Walk with Drift:

    k_{T+h} = k_T + h * drift + sqrt(h) * sigma * Z,   Z ~ N(0,1)

Where:
    drift = (k_T - k_1) / (T - 1)     (average annual change)
    sigma = std(diff(k_t) - drift)     (volatility of changes)

This produces:
    - Central projection: k_T + h * drift (best estimate)
    - Stochastic paths: N simulations for confidence intervals

The Bridge to LifeTable:
    Projected m_x -> q_x via:  q_x = 1 - exp(-m_x)
    Then build l_x from q_x:   l_{x+1} = l_x * (1 - q_x)
    This creates a LifeTable that feeds directly into a02-a05.

Data Source:
-----------
HMD. Human Mortality Database. Max Planck Institute for Demographic Research
(Germany), University of California, Berkeley (USA), and French Institute for
Demographic Studies (France). Available at www.mortality.org.
"""

from typing import Dict, Tuple, Optional
import numpy as np

from .a08_lee_carter import LeeCarter
from .a01_life_table import LifeTable


class MortalityProjection:
    """
    Mortality projection using Lee-Carter parameters with RWD on k_t.

    Generates projected mortality surfaces and creates LifeTable objects
    that bridge to the existing actuarial engine (commutations, premiums,
    reserves).

    Attributes:
        lee_carter: the fitted LeeCarter model
        horizon: number of years to project forward
        n_simulations: number of stochastic paths
        drift: estimated annual drift of k_t
        sigma: estimated volatility of k_t changes
        projected_years: array of future years
        kt_central: central (deterministic) k_t projection
        kt_simulated: matrix (n_simulations x horizon) of stochastic paths
    """

    def __init__(
        self,
        lee_carter: LeeCarter,
        horizon: int = 30,
        n_simulations: int = 1000,
        random_seed: int = 42,
    ):
        """
        Project mortality forward from a fitted Lee-Carter model.

        Parameters
        ----------
        lee_carter : LeeCarter
            Fitted Lee-Carter model with a_x, b_x, k_t.
        horizon : int
            Number of years to project forward.
        n_simulations : int
            Number of stochastic paths for confidence intervals.
        random_seed : int
            For reproducibility of stochastic simulations.
        """
        self.lee_carter = lee_carter
        self.horizon = horizon
        self.n_simulations = n_simulations
        self.random_seed = random_seed

        # Projected years: start from the year AFTER the last observed
        last_year = int(lee_carter.years[-1])
        self.projected_years = np.arange(last_year + 1, last_year + 1 + horizon)

        # Estimate drift and volatility from observed k_t
        self.drift, self.sigma = self._estimate_drift_and_sigma()

        # Generate projections
        self.kt_central = self._project_kt_central()
        self.kt_simulated = self._simulate_kt_paths()

    def _estimate_drift_and_sigma(self) -> Tuple[float, float]:
        """
        Estimate drift and volatility from observed k_t differences.

        drift = (k_T - k_1) / (T - 1)
        sigma = std(diff(k_t) - drift)

        The drift captures the secular trend (typically negative,
        meaning mortality is improving). Sigma captures how noisy
        the year-to-year changes are.
        """
        kt = self.lee_carter.kt
        n = len(kt)

        # Drift: total change divided by number of intervals
        drift = (kt[-1] - kt[0]) / (n - 1)

        # Volatility: standard deviation of innovations
        diffs = np.diff(kt)
        innovations = diffs - drift
        sigma = np.std(innovations, ddof=1)  # ddof=1 for sample std

        return float(drift), float(sigma)

    def _project_kt_central(self) -> np.ndarray:
        """
        Deterministic central projection: k_T + h * drift.

        This is the "best estimate" path, extending the observed
        linear trend into the future.
        """
        kt_last = self.lee_carter.kt[-1]
        h = np.arange(1, self.horizon + 1)
        return kt_last + h * self.drift

    def _simulate_kt_paths(self) -> np.ndarray:
        """
        Generate N stochastic paths of projected k_t.

        Each path: k_{T+h} = k_T + h*drift + sigma * cumsum(Z_h)
        where Z_h ~ N(0,1) are independent standard normals.

        Returns
        -------
        np.ndarray
            Matrix of shape (n_simulations, horizon).
        """
        rng = np.random.default_rng(self.random_seed)
        kt_last = self.lee_carter.kt[-1]

        # Generate random innovations
        innovations = rng.normal(0, 1, size=(self.n_simulations, self.horizon))

        # Build paths: cumulative sum gives the random walk component
        h = np.arange(1, self.horizon + 1)
        drift_component = h * self.drift
        random_component = self.sigma * np.cumsum(innovations, axis=1)

        return kt_last + drift_component + random_component

    def _validate_projection_year(self, year: int) -> int:
        """
        Validate that a year is within the projected range and return its index.

        Raises ValueError if the year is not in self.projected_years.
        """
        idx = np.searchsorted(self.projected_years, year)
        if idx >= len(self.projected_years) or self.projected_years[idx] != year:
            raise ValueError(
                f"Year {year} not in projection range "
                f"({int(self.projected_years[0])}-{int(self.projected_years[-1])})"
            )
        return int(idx)

    def get_projected_mx(self, age: int, year: int) -> float:
        """
        Get central projected death rate for a given age and future year.

        Uses: exp(a_x + b_x * k_t_central)
        """
        year_idx = self._validate_projection_year(year)
        kt = self.kt_central[year_idx]
        age_idx = np.searchsorted(self.lee_carter.ages, age)
        ax = self.lee_carter.ax[age_idx]
        bx = self.lee_carter.bx[age_idx]
        return float(np.exp(ax + bx * kt))

    def get_projected_mx_surface(self, kt_values: np.ndarray) -> np.ndarray:
        """
        Compute full mortality surface for given k_t values.

        Parameters
        ----------
        kt_values : np.ndarray
            k_t values (length = number of projection years).

        Returns
        -------
        np.ndarray
            Matrix (n_ages x len(kt_values)) of projected rates.
        """
        ax = self.lee_carter.ax
        bx = self.lee_carter.bx
        return np.exp(ax[:, np.newaxis] + np.outer(bx, kt_values))

    def get_confidence_interval(
        self,
        age: int,
        year: int,
        quantiles: Tuple[float, float] = (0.05, 0.95),
    ) -> Tuple[float, float]:
        """
        Get confidence interval for projected death rate at (age, year).

        Parameters
        ----------
        age : int
            Age to query.
        year : int
            Future year to query.
        quantiles : Tuple[float, float]
            Lower and upper quantiles (default: 90% CI).

        Returns
        -------
        Tuple[float, float]
            (lower_rate, upper_rate) at the specified quantiles.
        """
        year_idx = self._validate_projection_year(year)
        age_idx = np.searchsorted(self.lee_carter.ages, age)

        ax = self.lee_carter.ax[age_idx]
        bx = self.lee_carter.bx[age_idx]

        # Compute rate for each simulated k_t path at this horizon
        kt_sims = self.kt_simulated[:, year_idx]
        rates = np.exp(ax + bx * kt_sims)

        lower = float(np.quantile(rates, quantiles[0]))
        upper = float(np.quantile(rates, quantiles[1]))
        return lower, upper

    def to_life_table(
        self,
        year: int,
        radix: float = 100_000,
        age_min: Optional[int] = None,
        age_max: Optional[int] = None,
    ) -> LifeTable:
        """
        Convert projected mortality rates to a LifeTable for a specific year.

        THE BRIDGE METHOD: This connects the Lee-Carter projection back
        to the existing actuarial engine (a01 -> a02 -> a03 -> a04 -> a05).

        Steps:
        1. Get projected m_x for the year (central projection)
        2. Convert m_x -> q_x via: q_x = 1 - exp(-m_x)
        3. Build l_x from q_x: l_{x+1} = l_x * (1 - q_x)
        4. Force terminal q_omega = 1.0
        5. Return LifeTable(ages, l_x)

        Parameters
        ----------
        year : int
            Future year to project.
        radix : float
            Starting population (l_0). Default 100,000.
        age_min : int, optional
            First age (default: first age in Lee-Carter model).
        age_max : int, optional
            Last age (default: last age in Lee-Carter model).

        Returns
        -------
        LifeTable
            Ready to feed into CommutationFunctions -> Premiums -> Reserves.
        """
        year_idx = self._validate_projection_year(year)
        kt = self.kt_central[year_idx]

        ages = self.lee_carter.ages
        ax = self.lee_carter.ax
        bx = self.lee_carter.bx

        # Step 1: Projected central death rates
        mx = np.exp(ax + bx * kt)

        # Step 2: Convert m_x -> q_x (constant force assumption)
        qx = 1.0 - np.exp(-mx)

        # Step 3: Force terminal q = 1.0
        qx[-1] = 1.0

        # Step 4: Ensure q_x is in [0, 1]
        qx = np.clip(qx, 0.0, 1.0)

        # Step 5: Build l_x
        lx = np.zeros(len(ages))
        lx[0] = radix
        for i in range(len(ages) - 1):
            lx[i + 1] = lx[i] * (1.0 - qx[i])

        # Optional: subset ages
        if age_min is not None or age_max is not None:
            a_min = age_min if age_min is not None else int(ages[0])
            a_max = age_max if age_max is not None else int(ages[-1])
            mask = (ages >= a_min) & (ages <= a_max)
            ages = ages[mask]
            lx = lx[mask]

        return LifeTable(
            ages=list(ages.astype(int)),
            l_x_values=list(lx),
        )

    def to_life_table_with_ci(
        self,
        year: int,
        quantile_low: float = 0.05,
        quantile_high: float = 0.95,
        radix: float = 100_000,
    ) -> Tuple[LifeTable, LifeTable, LifeTable]:
        """
        Create three LifeTables: central, optimistic (low mortality),
        and pessimistic (high mortality).

        Parameters
        ----------
        year : int
            Future year.
        quantile_low : float
            Lower quantile for optimistic scenario.
        quantile_high : float
            Upper quantile for pessimistic scenario.
        radix : float
            Starting population.

        Returns
        -------
        Tuple of (central, optimistic, pessimistic) LifeTables.
        """
        year_idx = self._validate_projection_year(year)
        ages = self.lee_carter.ages
        ax = self.lee_carter.ax
        bx = self.lee_carter.bx

        # Central k_t
        kt_central = self.kt_central[year_idx]

        # Simulated k_t at this horizon
        kt_sims = self.kt_simulated[:, year_idx]
        kt_low = np.quantile(kt_sims, quantile_low)    # Lower k_t = lower mortality = optimistic
        kt_high = np.quantile(kt_sims, quantile_high)  # Higher k_t = higher mortality = pessimistic

        def _build_lt(kt_val):
            mx = np.exp(ax + bx * kt_val)
            qx = 1.0 - np.exp(-mx)
            qx[-1] = 1.0
            qx = np.clip(qx, 0.0, 1.0)
            lx = np.zeros(len(ages))
            lx[0] = radix
            for i in range(len(ages) - 1):
                lx[i + 1] = lx[i] * (1.0 - qx[i])
            return LifeTable(ages=list(ages.astype(int)), l_x_values=list(lx))

        return _build_lt(kt_central), _build_lt(kt_low), _build_lt(kt_high)

    def validate(self) -> Dict[str, bool]:
        """
        Validate projection results.

        Checks:
            drift_is_negative: mortality should be improving (drift < 0)
            sigma_positive: volatility must be positive
            central_extends_trend: last projected k_t < last observed
            no_nan_in_central: no NaN in central projection
        """
        return {
            "drift_is_negative": bool(self.drift < 0),
            "sigma_positive": bool(self.sigma > 0),
            "central_extends_trend": bool(self.kt_central[-1] < self.lee_carter.kt[-1]),
            "no_nan_in_central": bool(not np.any(np.isnan(self.kt_central))),
        }

    def summary(self) -> Dict:
        """Summary statistics for the projection."""
        return {
            "horizon": self.horizon,
            "n_simulations": self.n_simulations,
            "projected_years": (int(self.projected_years[0]), int(self.projected_years[-1])),
            "drift": self.drift,
            "sigma": self.sigma,
            "kt_central_range": (float(self.kt_central[0]), float(self.kt_central[-1])),
            "validations": self.validate(),
        }
