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
    - Missing-value imputation (optional, linear by age within year)
    - Structured DataQualityReport / DataQualityError diagnostics
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .data_validation import (
    DataQualityReport,
    validate_age_year_range,
    validate_integer_columns,
    validate_mx_consistency,
    validate_no_missing_cells,
    validate_required_columns,
)
from .exceptions import DataQualityError

# Versioned file schema for HMD loaders.
HMD_SCHEMA = {
    "filename_patterns": {
        "mx": "Mx_1x1_{country}.txt",
        "dx": "Deaths_1x1_{country}.txt",
        "ex": "Exposures_1x1_{country}.txt",
    },
    "skiprows": 2,
    "sep": r"\s+",
    "sex_columns": ("Female", "Male", "Total"),
    "age_column": "Age",
    "year_column": "Year",
}

# Versioned file schema for INEGI/CONAPO loaders.
INEGI_SCHEMA = {
    "deaths": {
        "required_columns": ["Anio", "Edad", "Sexo", "Defunciones"],
        "year_column": "Anio",
        "age_column": "Edad",
        "value_column": "Defunciones",
    },
    "population": {
        "required_columns": ["Anio", "Edad", "Sexo", "Poblacion"],
        "year_column": "Anio",
        "age_column": "Edad",
        "value_column": "Poblacion",
    },
    "sex_values": ("Hombres", "Mujeres", "Total"),
}


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
    def shape(self) -> tuple[int, int]:
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

    def summary(self) -> dict:
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
        impute_missing: bool = False,
    ) -> MortalityData:
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
        impute_missing : bool
            If True, apply age-direction linear interpolation to a small
            number of missing cells before raising a DataQualityError.

        Returns
        -------
        MortalityData
            Structured mortality data with three aligned matrices.
        """
        report = cls._load_hmd_report(
            data_dir=data_dir,
            country=country,
            sex=sex,
            year_min=year_min,
            year_max=year_max,
            age_max=age_max,
            download_date=download_date,
            impute_missing=impute_missing,
        )
        return cls(**report.to_mortality_data_kwargs(download_date))

    @classmethod
    def _load_hmd_report(
        cls,
        data_dir: str,
        country: str,
        sex: str,
        year_min: int,
        year_max: int,
        age_max: int,
        download_date: str,
        impute_missing: bool,
    ) -> DataQualityReport:
        """Internal: parse HMD files and return a DataQualityReport."""
        if sex not in HMD_SCHEMA["sex_columns"]:
            raise DataQualityError(
                f"sex must be one of {HMD_SCHEMA['sex_columns']}, got {sex!r}",
                field="sex",
                constraint=f"sex in {HMD_SCHEMA['sex_columns']}",
            )
        if age_max < 0:
            raise DataQualityError(
                f"age_max must be non-negative, got {age_max}",
                field="age_max",
                constraint="age_max >= 0",
            )
        if year_min > year_max:
            raise DataQualityError(
                f"year_min ({year_min}) cannot exceed year_max ({year_max})",
                field="year_range",
                constraint="year_min <= year_max",
            )

        base = Path(data_dir) / country
        if not base.exists():
            raise DataQualityError(
                f"HMD data directory not found: {base}",
                field="data_dir",
                constraint=f"{data_dir}/{country} must exist",
            )

        # --- Schema: expected filenames and skiprows ---
        mx_file = base / HMD_SCHEMA["filename_patterns"]["mx"].format(country=country)
        dx_file = base / HMD_SCHEMA["filename_patterns"]["dx"].format(country=country)
        ex_file = base / HMD_SCHEMA["filename_patterns"]["ex"].format(country=country)
        for name, path in (("mx", mx_file), ("dx", dx_file), ("ex", ex_file)):
            if not path.exists():
                raise DataQualityError(
                    f"Missing HMD file for {country}: {path}",
                    field=name,
                    constraint=f"{HMD_SCHEMA['filename_patterns'][name]} must exist",
                )

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

        # --- Optional missing-value imputation (by age within each year) ---
        n_imputed = 0
        if impute_missing:
            mx_np, dx_np, ex_np, n_imputed = _impute_missing_hmd(
                mx_np, dx_np, ex_np, ages, years
            )

        # --- Validation ---
        _validate(mx_np, dx_np, ex_np, ages, years, country, sex)
        validate_age_year_range(
            ages, years, source=f"{country}/{sex}", age_min=0, year_min=year_min, year_max=year_max
        )
        validate_mx_consistency(mx_np, dx_np, ex_np, ages, years, source=f"{country}/{sex}")

        return DataQualityReport(
            country=country,
            sex=sex,
            ages=ages,
            years=years,
            mx=mx_np,
            dx=dx_np,
            ex=ex_np,
            missing_imputed=n_imputed,
            open_age_group=age_max,
            source="HMD",
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
        impute_missing: bool = False,
    ) -> MortalityData:
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
        impute_missing : bool
            If True, apply age-direction linear interpolation to a small
            number of missing cells before raising a DataQualityError.

        Returns
        -------
        MortalityData
            Structured mortality data with three aligned matrices.
        """
        report = cls._load_inegi_report(
            deaths_filepath=deaths_filepath,
            population_filepath=population_filepath,
            sex=sex,
            year_start=year_start,
            year_end=year_end,
            age_max=age_max,
            impute_missing=impute_missing,
        )
        return cls(**report.to_mortality_data_kwargs())

    @classmethod
    def _load_inegi_report(
        cls,
        deaths_filepath: str,
        population_filepath: str,
        sex: str,
        year_start: int,
        year_end: int,
        age_max: int,
        impute_missing: bool,
    ) -> DataQualityReport:
        """Internal: parse INEGI/CONAPO files and return a DataQualityReport."""
        if sex not in INEGI_SCHEMA["sex_values"]:
            raise DataQualityError(
                f"sex must be one of {INEGI_SCHEMA['sex_values']}, got {sex!r}",
                field="sex",
                constraint=f"sex in {INEGI_SCHEMA['sex_values']}",
            )
        if age_max < 0:
            raise DataQualityError(
                f"age_max must be non-negative, got {age_max}",
                field="age_max",
                constraint="age_max >= 0",
            )
        if year_start > year_end:
            raise DataQualityError(
                f"year_start ({year_start}) cannot exceed year_end ({year_end})",
                field="year_range",
                constraint="year_start <= year_end",
            )

        # --- Load and validate schemas ---
        dx_raw = _load_inegi_deaths(deaths_filepath, sex, year_start, year_end)
        ex_raw = _load_conapo_population(population_filepath, sex, year_start, year_end)

        # --- Cap ages: aggregate everything above age_max ---
        dx_capped = _cap_ages_sum(dx_raw, age_max)
        ex_capped = _cap_ages_sum(ex_raw, age_max)

        # --- Compute m_x = deaths / population ---
        # Merge on (Year, Age) to ensure alignment
        merged = pd.merge(
            dx_capped,
            ex_capped,
            on=["Year", "Age"],
            suffixes=("_dx", "_ex"),
        )

        # Validate: no zero or negative population
        if (merged["Value_ex"] <= 0).any():
            bad = merged[merged["Value_ex"] <= 0][["Year", "Age"]].head()
            raise DataQualityError(
                f"Mexico/{sex}: zero or negative population at "
                f"{list(bad.itertuples(index=False, name=None))}. "
                "Cannot compute m_x = D/P.",
                field="ex",
                constraint="population > 0",
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

        # --- Optional missing-value imputation (by age within each year) ---
        n_imputed = 0
        if impute_missing:
            mx_np, dx_np, ex_np, n_imputed = _impute_missing_hmd(
                mx_np, dx_np, ex_np, ages, years
            )

        # --- Validation ---
        _validate(mx_np, dx_np, ex_np, ages, years, "Mexico", sex)
        validate_age_year_range(
            ages,
            years,
            source=f"Mexico/{sex}",
            age_min=0,
            year_min=year_start,
            year_max=year_end,
        )
        validate_mx_consistency(mx_np, dx_np, ex_np, ages, years, source=f"Mexico/{sex}")

        return DataQualityReport(
            country="Mexico",
            sex=sex,
            ages=ages,
            years=years,
            mx=mx_np,
            dx=dx_np,
            ex=ex_np,
            missing_imputed=n_imputed,
            open_age_group=age_max,
            source="INEGI/CONAPO",
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
    if not filepath.exists():
        raise DataQualityError(
            f"HMD file not found: {filepath}",
            field="filepath",
            constraint=f"{filepath} must exist",
        )

    df = pd.read_csv(
        filepath,
        sep=HMD_SCHEMA["sep"],
        skiprows=HMD_SCHEMA["skiprows"],
        na_values=".",
    )

    required = [HMD_SCHEMA["year_column"], HMD_SCHEMA["age_column"], sex]
    validate_required_columns(df, required, filepath=filepath, source="HMD")
    validate_no_missing_cells(df, required, filepath=filepath, source="HMD")

    # Handle '110+' in Age column
    df["Age"] = df["Age"].astype(str).str.replace("+", "", regex=False)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["Year"] = pd.to_numeric(df["Year"], errors="coerce")

    validate_integer_columns(
        df,
        [HMD_SCHEMA["year_column"], HMD_SCHEMA["age_column"]],
        filepath=filepath,
        source="HMD",
    )

    df["Age"] = df["Age"].astype(int)
    df["Year"] = df["Year"].astype(int)

    if sex not in HMD_SCHEMA["sex_columns"]:
        raise DataQualityError(
            f"sex must be one of {HMD_SCHEMA['sex_columns']}, got {sex!r}",
            field="sex",
            constraint=f"sex in {HMD_SCHEMA['sex_columns']}",
        )

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


def _impute_missing_hmd(
    mx: np.ndarray,
    dx: np.ndarray,
    ex: np.ndarray,
    ages: np.ndarray,
    years: np.ndarray,
    max_ratio: float = 0.05,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """
    Impute a small number of missing cells in the HMD/INEGI matrices.

    Uses linear interpolation by age within each year column. If more than
    ``max_ratio`` of the cells are missing, raises a DataQualityError instead.
    """
    mx = mx.copy()
    dx = dx.copy()
    ex = ex.copy()
    n_cells = mx.size
    n_missing = int(np.isnan(mx).sum() + np.isnan(dx).sum() + np.isnan(ex).sum())
    if n_missing == 0:
        return mx, dx, ex, 0

    if n_missing / n_cells > max_ratio:
        raise DataQualityError(
            f"Too many missing values: {n_missing}/{n_cells} "
            f"({100 * n_missing / n_cells:.1f}%, limit {100 * max_ratio:.1f}%)",
            field="missing_values",
            constraint=f"missing ratio <= {max_ratio}",
        )

    n_imputed = 0
    for j in range(mx.shape[1]):
        for arr in (mx, dx, ex):
            col = arr[:, j]
            nan_mask = np.isnan(col)
            if nan_mask.any():
                n_imputed += int(nan_mask.sum())
                col[nan_mask] = np.interp(
                    ages[nan_mask], ages[~nan_mask], col[~nan_mask]
                )
    return mx, dx, ex, n_imputed


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
        raise DataQualityError(
            f"Shape mismatch: mx={mx.shape}, dx={dx.shape}, ex={ex.shape}",
            field="shape",
            constraint="mx.shape == dx.shape == ex.shape",
        )

    # No missing values
    for name, arr in [("mx", mx), ("dx", dx), ("ex", ex)]:
        n_nan = np.isnan(arr).sum()
        if n_nan > 0:
            raise DataQualityError(
                f"{country}/{sex}: {name} has {n_nan} NaN values. "
                "Check year/age range for data availability.",
                field=name,
                constraint=f"no NaN values in {name}",
            )

    # Positive rates (required for log transform in Lee-Carter)
    n_nonpos = np.sum(mx <= 0)
    if n_nonpos > 0:
        zero_locs = np.argwhere(mx <= 0)
        sample = zero_locs[:5]
        detail = [(int(ages[r]), int(years[c])) for r, c in sample]
        raise DataQualityError(
            f"{country}/{sex}: {n_nonpos} non-positive m_x values. "
            f"Sample (age, year): {detail}. "
            "Graduation (a07) may be needed, or adjust age/year range.",
            field="mx",
            constraint="mx > 0",
        )

    # Positive exposures
    if np.any(ex <= 0):
        raise DataQualityError(
            f"{country}/{sex}: exposure matrix has non-positive values.",
            field="ex",
            constraint="ex > 0",
        )

    # Consistency: d/L should approximate m_x
    mx_recomputed = dx / ex
    relative_error = np.abs(mx - mx_recomputed) / (mx + 1e-12)
    max_rel_error = np.max(relative_error)
    if max_rel_error > 0.01:  # 1% tolerance
        worst = np.unravel_index(np.argmax(relative_error), mx.shape)
        raise DataQualityError(
            f"{country}/{sex}: m_x inconsistent with d/L. "
            f"Max relative error: {max_rel_error:.4f} "
            f"at age {ages[worst[0]]}, year {years[worst[1]]}.",
            field="mx",
            constraint="mx ≈ dx / ex",
        )


def _load_inegi_deaths(filepath: str, sex: str, year_start: int, year_end: int) -> pd.DataFrame:
    """
    Load INEGI deaths file and filter by sex and year range.

    INEGI format: CSV with columns Anio, Edad, Sexo, Defunciones.
    Sex values are in Spanish: 'Hombres', 'Mujeres', 'Total'.

    Returns DataFrame with columns: Year, Age, Value (deaths).
    """
    df = pd.read_csv(filepath)
    schema = INEGI_SCHEMA["deaths"]
    validate_required_columns(
        df,
        schema["required_columns"],
        filepath=filepath,
        source="INEGI deaths",
    )
    validate_no_missing_cells(
        df,
        [schema["year_column"], schema["age_column"], "Sexo", schema["value_column"]],
        filepath=filepath,
        source="INEGI deaths",
    )
    validate_integer_columns(
        df,
        [schema["year_column"], schema["age_column"]],
        filepath=filepath,
        source="INEGI deaths",
    )

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
    schema = INEGI_SCHEMA["population"]
    validate_required_columns(
        df,
        schema["required_columns"],
        filepath=filepath,
        source="CONAPO population",
    )
    validate_no_missing_cells(
        df,
        [schema["year_column"], schema["age_column"], "Sexo", schema["value_column"]],
        filepath=filepath,
        source="CONAPO population",
    )
    validate_integer_columns(
        df,
        [schema["year_column"], schema["age_column"]],
        filepath=filepath,
        source="CONAPO population",
    )

    df = df[df["Sexo"] == sex]
    df = df[(df["Anio"] >= year_start) & (df["Anio"] <= year_end)]
    return df[["Anio", "Edad", "Poblacion"]].rename(
        columns={"Anio": "Year", "Edad": "Age", "Poblacion": "Value"}
    )
