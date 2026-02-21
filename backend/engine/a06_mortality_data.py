"""
Mortality Data Module - Block 6
================================

Loads and structures mortality data from multiple sources into the matrix
format required by Lee-Carter estimation.

Supported data sources:
    1. HMD (Human Mortality Database) - from_hmd()
    2. INEGI/CONAPO (Mexican official statistics) - from_inegi()

Data Sources:
------------
HMD. Human Mortality Database. Max Planck Institute for Demographic Research
(Germany), University of California, Berkeley (USA), and French Institute for
Demographic Studies (France). Available at www.mortality.org.

INEGI. Instituto Nacional de Estadistica y Geografia. Defunciones registradas.
CONAPO. Consejo Nacional de Poblacion. Proyecciones de poblacion.

Theory Connection:
-----------------
Lee-Carter requires three aligned matrices (ages x years):
    - m_{x,t} = d_{x,t} / L_{x,t}   (central death rates)
    - d_{x,t}                          (death counts, for k_t re-estimation)
    - L_{x,t}                          (exposure in person-years)

HMD provides these in long format (one row per age-year combination).
INEGI provides deaths and CONAPO provides population estimates separately.
This module pivots them into matrices and handles:
    - Age capping (aggregate ages above max_age into a single open group)
    - Year subsetting (select a relevant recent window)
    - Sex selection (separate models for Male/Female/Total)
    - Validation (no missing values, all rates positive)
"""

from pathlib import Path
from typing import Optional, Tuple, Dict
import numpy as np
import pandas as pd


class MortalityData:
    """
    Structured mortality data ready for Lee-Carter estimation.

    Stores three aligned matrices (ages as rows, years as columns):
        mx: central death rates m_{x,t}
        dx: death counts d_{x,t}
        ex: exposure (person-years) L_{x,t}

    Also stores the age and year labels for each axis.

    Attributes:
        country: Country identifier (e.g., 'usa', 'spain')
        sex: Which sex column was used ('Female', 'Male', 'Total')
        ages: numpy array of integer ages (row labels)
        years: numpy array of integer years (column labels)
        mx: numpy 2D array (n_ages x n_years) of death rates
        dx: numpy 2D array (n_ages x n_years) of death counts
        ex: numpy 2D array (n_ages x n_years) of exposures
        download_date: date noted for HMD citation compliance
    """

    def __init__(
        self,
        country: str,
        sex: str,
        ages: np.ndarray,
        years: np.ndarray,
        mx: np.ndarray,
        dx: np.ndarray,
        ex: np.ndarray,
        download_date: str = "",
    ):
        self.country = country
        self.sex = sex
        self.ages = ages
        self.years = years
        self.mx = mx
        self.dx = dx
        self.ex = ex
        self.download_date = download_date

    @property
    def n_ages(self) -> int:
        """Number of age groups."""
        return len(self.ages)

    @property
    def n_years(self) -> int:
        """Number of calendar years."""
        return len(self.years)

    @property
    def shape(self) -> Tuple[int, int]:
        """Matrix shape (n_ages, n_years)."""
        return (self.n_ages, self.n_years)

    def _validate_age(self, age: int) -> int:
        """Validate and return array index for an age."""
        idx = np.searchsorted(self.ages, age)
        if idx >= len(self.ages) or self.ages[idx] != age:
            raise ValueError(
                f"Age {age} not in data (range: {self.ages[0]}-{self.ages[-1]})"
            )
        return idx

    def _validate_year(self, year: int) -> int:
        """Validate and return array index for a year."""
        idx = np.searchsorted(self.years, year)
        if idx >= len(self.years) or self.years[idx] != year:
            raise ValueError(
                f"Year {year} not in data (range: {self.years[0]}-{self.years[-1]})"
            )
        return idx

    def get_mx(self, age: int, year: int) -> float:
        """Get a single death rate by age and year."""
        age_idx = self._validate_age(age)
        year_idx = self._validate_year(year)
        return float(self.mx[age_idx, year_idx])

    def year_slice(self, year: int) -> np.ndarray:
        """Get all death rates for a single year (vector of ages)."""
        year_idx = self._validate_year(year)
        return self.mx[:, year_idx]

    def age_slice(self, age: int) -> np.ndarray:
        """Get all death rates for a single age (vector across years)."""
        age_idx = self._validate_age(age)
        return self.mx[age_idx, :]

    def summary(self) -> Dict:
        """Summary statistics for quick inspection."""
        return {
            "country": self.country,
            "sex": self.sex,
            "shape": self.shape,
            "age_range": (int(self.ages[0]), int(self.ages[-1])),
            "year_range": (int(self.years[0]), int(self.years[-1])),
            "mx_min": float(np.min(self.mx)),
            "mx_max": float(np.max(self.mx)),
            "mx_mean": float(np.mean(self.mx)),
            "any_zeros": bool(np.any(self.mx <= 0)),
            "download_date": self.download_date,
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
        download_date: str = "",
    ) -> "MortalityData":
        """
        Load mortality data from HMD text files.

        Parameters
        ----------
        data_dir : str
            Path to HMD data directory containing country subfolders.
            Expected structure: data_dir/{country}/Mx_1x1_{country}.txt
        country : str
            Country subfolder name (e.g., 'usa', 'spain').
        sex : str
            Column to extract: 'Female', 'Male', or 'Total'.
        year_min : int
            First year to include.
        year_max : int
            Last year to include.
        age_max : int
            Maximum age. Ages above this are aggregated into age_max+ group.
        download_date : str
            Date of download for citation compliance.

        Returns
        -------
        MortalityData
            Structured mortality data with three aligned matrices.
        """
        base = Path(data_dir) / country

        # --- Load the three HMD files ---
        mx_file = base / f"Mx_1x1_{country}.txt"
        dx_file = base / f"Deaths_1x1_{country}.txt"
        ex_file = base / f"Exposures_1x1_{country}.txt"

        mx_raw = _load_hmd_file(mx_file, sex)
        dx_raw = _load_hmd_file(dx_file, sex)
        ex_raw = _load_hmd_file(ex_file, sex)

        # --- Filter years ---
        mx_raw = mx_raw[(mx_raw["Year"] >= year_min) & (mx_raw["Year"] <= year_max)]
        dx_raw = dx_raw[(dx_raw["Year"] >= year_min) & (dx_raw["Year"] <= year_max)]
        ex_raw = ex_raw[(ex_raw["Year"] >= year_min) & (ex_raw["Year"] <= year_max)]

        # --- Cap ages: aggregate everything above age_max ---
        mx_raw = _cap_ages(mx_raw, dx_raw, ex_raw, age_max)
        dx_raw = _cap_ages_sum(dx_raw, age_max)
        ex_raw = _cap_ages_sum(ex_raw, age_max)

        # --- Pivot to matrices (ages x years) ---
        mx_matrix = mx_raw.pivot(index="Age", columns="Year", values="Value")
        dx_matrix = dx_raw.pivot(index="Age", columns="Year", values="Value")
        ex_matrix = ex_raw.pivot(index="Age", columns="Year", values="Value")

        ages = mx_matrix.index.values.astype(int)
        years = mx_matrix.columns.values.astype(int)

        mx_np = mx_matrix.values.astype(float)
        dx_np = dx_matrix.values.astype(float)
        ex_np = ex_matrix.values.astype(float)

        # --- Validation ---
        _validate(mx_np, dx_np, ex_np, ages, years, country, sex)

        return cls(
            country=country,
            sex=sex,
            ages=ages,
            years=years,
            mx=mx_np,
            dx=dx_np,
            ex=ex_np,
            download_date=download_date,
        )

    @classmethod
    def from_inegi(
        cls,
        deaths_filepath: str,
        population_filepath: str,
        sex: str = "Total",
        year_start: int = 1990,
        year_end: int = 2023,
        age_max: int = 100,
    ) -> "MortalityData":
        """
        Load mortality data from INEGI deaths and CONAPO population files.

        INEGI provides registered deaths by age, year, and sex.
        CONAPO provides mid-year population estimates used as exposure.
        Central death rate is computed as m_{x,t} = D_{x,t} / P_{x,t}.

        Parameters
        ----------
        deaths_filepath : str
            Path to INEGI deaths CSV. Expected columns:
            Anio, Edad, Sexo, Defunciones
        population_filepath : str
            Path to CONAPO population CSV. Expected columns:
            Anio, Edad, Sexo, Poblacion
        sex : str
            Sex filter: 'Hombres', 'Mujeres', or 'Total'.
        year_start : int
            First year to include (inclusive).
        year_end : int
            Last year to include (inclusive).
        age_max : int
            Maximum age. Ages above this are aggregated into age_max group.

        Returns
        -------
        MortalityData
            Structured mortality data with three aligned matrices.
        """
        if sex not in ("Hombres", "Mujeres", "Total"):
            raise ValueError(
                f"sex must be 'Hombres', 'Mujeres', or 'Total', got '{sex}'"
            )

        # --- Load and filter ---
        dx_raw = _load_inegi_deaths(deaths_filepath, sex, year_start, year_end)
        ex_raw = _load_conapo_population(population_filepath, sex, year_start, year_end)

        # --- Cap ages: aggregate everything above age_max ---
        dx_capped = _cap_ages_sum(dx_raw, age_max)
        ex_capped = _cap_ages_sum(ex_raw, age_max)

        # --- Compute m_x = deaths / population ---
        # Merge on (Year, Age) to ensure alignment
        merged = pd.merge(
            dx_capped, ex_capped,
            on=["Year", "Age"],
            suffixes=("_dx", "_ex"),
        )

        # Validate: no zero or negative population
        if (merged["Value_ex"] <= 0).any():
            bad = merged[merged["Value_ex"] <= 0][["Year", "Age"]].head()
            raise ValueError(
                f"Mexico/{sex}: zero or negative population at "
                f"{list(bad.itertuples(index=False, name=None))}. "
                f"Cannot compute m_x = D/P."
            )

        merged["mx"] = merged["Value_dx"] / merged["Value_ex"]

        # Build mx DataFrame in long format for pivoting
        mx_long = merged[["Year", "Age", "mx"]].rename(columns={"mx": "Value"})

        # --- Pivot to matrices (ages x years) ---
        mx_matrix = mx_long.pivot(index="Age", columns="Year", values="Value")
        dx_matrix = dx_capped.pivot(index="Age", columns="Year", values="Value")
        ex_matrix = ex_capped.pivot(index="Age", columns="Year", values="Value")

        ages = mx_matrix.index.values.astype(int)
        years = mx_matrix.columns.values.astype(int)

        mx_np = mx_matrix.values.astype(float)
        dx_np = dx_matrix.values.astype(float)
        ex_np = ex_matrix.values.astype(float)

        # --- Validation ---
        _validate(mx_np, dx_np, ex_np, ages, years, "Mexico", sex)

        return cls(
            country="Mexico",
            sex=sex,
            ages=ages,
            years=years,
            mx=mx_np,
            dx=dx_np,
            ex=ex_np,
        )


def _load_hmd_file(filepath: Path, sex: str) -> pd.DataFrame:
    """
    Load a single HMD text file and extract one sex column.

    HMD format: 2 header lines, then whitespace-separated columns:
    Year  Age  Female  Male  Total

    The Age column contains '110+' for the open interval, which we
    convert to integer 110.

    Returns DataFrame with columns: Year, Age, Value
    """
    df = pd.read_csv(filepath, sep=r"\s+", skiprows=2, na_values=".")

    # Handle '110+' in Age column
    df["Age"] = df["Age"].astype(str).str.replace("+", "", regex=False)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").astype(int)
    df["Year"] = df["Year"].astype(int)

    if sex not in ("Female", "Male", "Total"):
        raise ValueError(f"sex must be 'Female', 'Male', or 'Total', got '{sex}'")

    return df[["Year", "Age", sex]].rename(columns={sex: "Value"})


def _cap_ages_sum(df: pd.DataFrame, age_max: int) -> pd.DataFrame:
    """
    For death counts and exposures: sum all ages > age_max into age_max.

    Example with age_max=100:
        Ages 100, 101, 102, ..., 110 all collapse into age 100.
        Their death counts (or exposures) are summed.
    """
    df = df.copy()
    df.loc[df["Age"] > age_max, "Age"] = age_max
    return df.groupby(["Year", "Age"], as_index=False)["Value"].sum()


def _cap_ages(
    mx_df: pd.DataFrame,
    dx_df: pd.DataFrame,
    ex_df: pd.DataFrame,
    age_max: int,
) -> pd.DataFrame:
    """
    For death rates: recompute m_x for the capped age group as d/L.

    We can't just average m_x across ages 100-110 because that ignores
    population weights. Instead: sum deaths, sum exposure, divide.
    This gives the correct exposure-weighted rate for the group.
    """
    # Separate: ages within range vs ages to aggregate
    keep = mx_df[mx_df["Age"] <= age_max].copy()
    keep = keep[keep["Age"] < age_max]  # Exclude age_max (will be recomputed)

    # Aggregate d and L for ages >= age_max
    dx_agg = dx_df[dx_df["Age"] >= age_max].groupby("Year")["Value"].sum()
    ex_agg = ex_df[ex_df["Age"] >= age_max].groupby("Year")["Value"].sum()
    mx_agg = (dx_agg / ex_agg).reset_index()
    mx_agg.columns = ["Year", "Value"]
    mx_agg["Age"] = age_max

    return pd.concat([keep, mx_agg[["Year", "Age", "Value"]]], ignore_index=True)


def _validate(
    mx: np.ndarray,
    dx: np.ndarray,
    ex: np.ndarray,
    ages: np.ndarray,
    years: np.ndarray,
    country: str,
    sex: str,
) -> None:
    """
    Validate the three matrices for consistency and completeness.

    Checks:
    1. No NaN values in any matrix
    2. All death rates are positive (required for log transform)
    3. All exposures are positive
    4. Matrices have matching shapes
    5. Recomputed rates d/L are close to provided m_x
    """
    # Shape consistency
    if not (mx.shape == dx.shape == ex.shape):
        raise ValueError(
            f"Shape mismatch: mx={mx.shape}, dx={dx.shape}, ex={ex.shape}"
        )

    # No missing values
    for name, arr in [("mx", mx), ("dx", dx), ("ex", ex)]:
        n_nan = np.isnan(arr).sum()
        if n_nan > 0:
            raise ValueError(
                f"{country}/{sex}: {name} has {n_nan} NaN values. "
                f"Check year/age range for data availability."
            )

    # Positive rates (required for log transform in Lee-Carter)
    n_nonpos = np.sum(mx <= 0)
    if n_nonpos > 0:
        zero_locs = np.argwhere(mx <= 0)
        sample = zero_locs[:5]
        detail = [(int(ages[r]), int(years[c])) for r, c in sample]
        raise ValueError(
            f"{country}/{sex}: {n_nonpos} non-positive m_x values. "
            f"Sample (age, year): {detail}. "
            f"Graduation (a07) may be needed, or adjust age/year range."
        )

    # Positive exposures
    if np.any(ex <= 0):
        raise ValueError(f"{country}/{sex}: exposure matrix has non-positive values.")

    # Consistency: d/L should approximate m_x
    mx_recomputed = dx / ex
    relative_error = np.abs(mx - mx_recomputed) / (mx + 1e-12)
    max_rel_error = np.max(relative_error)
    if max_rel_error > 0.01:  # 1% tolerance
        worst = np.unravel_index(np.argmax(relative_error), mx.shape)
        raise ValueError(
            f"{country}/{sex}: m_x inconsistent with d/L. "
            f"Max relative error: {max_rel_error:.4f} "
            f"at age {ages[worst[0]]}, year {years[worst[1]]}."
        )


def _load_inegi_deaths(
    filepath: str, sex: str, year_start: int, year_end: int
) -> pd.DataFrame:
    """
    Load INEGI deaths file and filter by sex and year range.

    INEGI format: CSV with columns Anio, Edad, Sexo, Defunciones.
    Sex values are in Spanish: 'Hombres', 'Mujeres', 'Total'.

    Returns DataFrame with columns: Year, Age, Value (deaths).
    """
    df = pd.read_csv(filepath)
    df = df[df["Sexo"] == sex]
    df = df[(df["Anio"] >= year_start) & (df["Anio"] <= year_end)]
    return df[["Anio", "Edad", "Defunciones"]].rename(
        columns={"Anio": "Year", "Edad": "Age", "Defunciones": "Value"}
    )


def _load_conapo_population(
    filepath: str, sex: str, year_start: int, year_end: int
) -> pd.DataFrame:
    """
    Load CONAPO population file and filter by sex and year range.

    CONAPO format: CSV with columns Anio, Edad, Sexo, Poblacion.
    Sex values are in Spanish: 'Hombres', 'Mujeres', 'Total'.

    Returns DataFrame with columns: Year, Age, Value (population).
    """
    df = pd.read_csv(filepath)
    df = df[df["Sexo"] == sex]
    df = df[(df["Anio"] >= year_start) & (df["Anio"] <= year_end)]
    return df[["Anio", "Edad", "Poblacion"]].rename(
        columns={"Anio": "Year", "Edad": "Age", "Poblacion": "Value"}
    )
