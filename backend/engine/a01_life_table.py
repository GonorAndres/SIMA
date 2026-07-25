"""
Life Table Module - Block 1
============================

Implements the LifeTable class that provides the foundational mortality
primitives: l_x, d_x, q_x, p_x.

Theory Connection:
-----------------
The life table is the actuarial "source of truth" for mortality. From the
single column l_x (survivors at each age), we derive all other quantities:

    d_x = l_x - l_{x+1}    (deaths between age x and x+1)
    q_x = d_x / l_x        (probability of death at age x)
    p_x = 1 - q_x          (probability of survival at age x)

Key Validations:
---------------
1. Sum of all deaths equals initial population: sum(d_x) = l_0
2. Terminal age has 100% mortality: q_omega = 1.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List
import csv
import warnings

from .exceptions import ActuarialValidationError
from .validators import (
    MONO_REL_TOL,
    validate_age_in_table,
    validate_consecutive_ages,
    validate_lx_monotonic,
    validate_probabilities,
)


class LifeTable:
    """
    Life table containing mortality primitives.

    Attributes:
        min_age: First age in the table
        max_age: Last age (omega, ultimate age)
        l_x: Dict mapping age -> survivors
        d_x: Dict mapping age -> deaths
        q_x: Dict mapping age -> mortality rate
        p_x: Dict mapping age -> survival rate
    """

    def __init__(self, ages: List[int], l_x_values: List[float]):
        """
        Initialize life table from age and l_x arrays.

        Args:
            ages: List of ages (must be consecutive)
            l_x_values: List of survivors at each age

        Raises:
            ActuarialValidationError: If ages are not consecutive, l_x is
                negative or non-monotone, or lengths mismatch.
        """
        if len(ages) != len(l_x_values):
            raise ActuarialValidationError(
                f"Ages and l_x values must have the same length "
                f"(got {len(ages)} vs {len(l_x_values)})",
                field="ages/l_x",
                constraint="len(ages) == len(l_x_values)",
            )

        # Validate structure before storing anything.
        ages_list = list(ages)
        validate_consecutive_ages(ages_list)
        validate_lx_monotonic(list(l_x_values), ages=ages_list)

        # Store basic info
        self.min_age = ages_list[0]
        self.max_age = ages_list[-1]
        self._omega = self.max_age  # Ultimate age

        # Build l_x dictionary
        self.l_x: Dict[int, float] = {}
        for age, lx in zip(ages_list, l_x_values):
            self.l_x[age] = float(lx)

        # Derive d_x, q_x, p_x
        self._compute_derivatives()

    def _compute_derivatives(self) -> None:
        """Compute d_x, q_x, p_x from l_x."""
        self.d_x: Dict[int, float] = {}
        self.q_x: Dict[int, float] = {}
        self.p_x: Dict[int, float] = {}

        for age in range(self.min_age, self.max_age):
            l_current = self.l_x[age]
            l_next = self.l_x[age + 1]

            # Deaths: d_x = l_x - l_{x+1}. Clamp tiny negatives (float
            # recurrence noise) to zero rather than emitting negative deaths.
            d = l_current - l_next
            if d < 0 and abs(d) <= MONO_REL_TOL * max(abs(l_current), 1.0):
                d = 0.0
            self.d_x[age] = d

            # Mortality rate: q_x = d_x / l_x
            if l_current > 0:
                self.q_x[age] = self.d_x[age] / l_current
            else:
                # No survivors: mortality is undefined; we follow the
                # convention q_x = 1 (everyone remaining is dead) so the
                # subsequent p_x = 0 terminates survival correctly.
                self.q_x[age] = 1.0

            # Survival rate: p_x = 1 - q_x
            self.p_x[age] = 1.0 - self.q_x[age]

        # Validate computed probabilities are in [0,1] (guards against bad
        # l_x values that produced q_x > 1 through rounding).
        validate_probabilities(self.q_x.values())

        # Terminal age: everyone dies
        # d_omega = l_omega (all remaining die)
        self.d_x[self.max_age] = self.l_x[self.max_age]
        self.q_x[self.max_age] = 1.0
        self.p_x[self.max_age] = 0.0

    @classmethod
    def from_csv(cls, filepath: str) -> "LifeTable":
        """
        Load life table from CSV file.

        Expected CSV format:
            age,l_x
            60,1000.00
            61,850.00
            ...

        Args:
            filepath: Path to CSV file

        Returns:
            LifeTable instance
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Life table file not found: {filepath}")

        ages: List[int] = []
        l_x_values: List[float] = []

        with open(path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ages.append(int(row['age']))
                l_x_values.append(float(row['l_x']))

        return cls(ages, l_x_values)

    @classmethod
    def from_regulatory_table(
        cls,
        filepath: str,
        sex: str = "male",
        radix: float = 100_000.0,
    ) -> "LifeTable":
        """
        Load life table from a Mexican regulatory table (CNSF, EMSSA).

        These tables publish q_x (mortality rates) by sex. The method
        builds l_x via the recurrence: l_0 = radix, l_{x+1} = l_x * (1 - q_x).

        Expected CSV format:
            age,qx_male,qx_female
            0,0.01550000,0.01280000
            1,0.00696460,0.00575141
            ...

        Args:
            filepath: Path to CSV file with regulatory table
            sex: "male" or "female" -- selects the q_x column
            radix: Initial cohort size (l_0), default 100,000

        Returns:
            LifeTable instance
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Regulatory table file not found: {filepath}")

        col = f"qx_{sex}"

        ages: List[int] = []
        qx_values: List[float] = []

        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            other_col = "qx_female" if sex == "male" else "qx_male"
            identical_count = 0
            for row in reader:
                ages.append(int(row["age"]))
                q_this = float(row[col])
                qx_values.append(q_this)
                # Compare the *raw strings* of the two qx columns rather than
                # exact float equality: a trailing-zero formatting difference
                # (0.005 vs 0.0050) compares equal as floats but the previous
                # `==` check silently masked genuinely shared data. We detect
                # "truly identical published series" by string match, which is
                # what actually indicates the source did not differentiate by
                # sex.
                if other_col in row and str(row[col]).strip() == str(row[other_col]).strip():
                    identical_count += 1

        if identical_count == len(ages) and sex != "unisex":
            warnings.warn(
                f"Regulatory table {path.name} has identical qx_male and qx_female columns. "
                f"Sex-differentiated mortality data is required for accurate pricing.",
                stacklevel=2,
            )

        # Build l_x from q_x: l_0 = radix, l_{x+1} = l_x * (1 - q_x)
        l_x_values: List[float] = [radix]
        for qx in qx_values[:-1]:
            l_x_values.append(l_x_values[-1] * (1.0 - qx))

        return cls(ages, l_x_values)

    def subset(self, start_age: int, end_age: int) -> "LifeTable":
        """
        Create a subset of the life table for a specific age range.

        Args:
            start_age: First age to include
            end_age: Last age to include

        Returns:
            New LifeTable for the specified range
        """
        if start_age < self.min_age or end_age > self.max_age or start_age > end_age:
            raise ActuarialValidationError(
                f"Subset range [{start_age}, {end_age}] out of bounds "
                f"[{self.min_age}, {self.max_age}]",
                field="start_age/end_age",
                constraint=f"{self.min_age} <= start_age <= end_age <= {self.max_age}",
            )

        ages = list(range(start_age, end_age + 1))
        l_x_values = [self.l_x[age] for age in ages]

        return LifeTable(ages, l_x_values)

    def get_l(self, age: int) -> float:
        """Get l_x (survivors) at specified age."""
        if age not in self.l_x:
            validate_age_in_table(age, self.min_age, self.max_age)
            # Defensive: validate_age_in_table raises, so the next line is
            # only reached if the age is in-range but somehow missing.
            raise ActuarialValidationError(
                f"Survivor l_x not available for age {age}",
                field="age",
                constraint=f"age in [{self.min_age}, {self.max_age}]",
            )
        return self.l_x[age]

    def get_d(self, age: int) -> float:
        """Get d_x (deaths) at specified age."""
        if age not in self.d_x:
            validate_age_in_table(age, self.min_age, self.max_age)
            raise ActuarialValidationError(
                f"Deaths d_x not available for age {age}",
                field="age",
                constraint=f"age in [{self.min_age}, {self.max_age}]",
            )
        return self.d_x[age]

    def get_q(self, age: int) -> float:
        """Get q_x (mortality rate) at specified age."""
        if age not in self.q_x:
            validate_age_in_table(age, self.min_age, self.max_age)
            raise ActuarialValidationError(
                f"Mortality q_x not available for age {age}",
                field="age",
                constraint=f"age in [{self.min_age}, {self.max_age}]",
            )
        return self.q_x[age]

    def get_p(self, age: int) -> float:
        """Get p_x (survival rate) at specified age."""
        if age not in self.p_x:
            validate_age_in_table(age, self.min_age, self.max_age)
            raise ActuarialValidationError(
                f"Survival p_x not available for age {age}",
                field="age",
                constraint=f"age in [{self.min_age}, {self.max_age}]",
            )
        return self.p_x[age]

    def validate(self) -> Dict[str, bool]:
        """
        Validate life table consistency.

        Returns:
            Dict with validation results:
                - sum_deaths_equals_l0: True if sum(d_x) == l_0
                - terminal_mortality_is_one: True if q_omega == 1.0
                - all_rates_valid: True if all q_x in [0, 1]
        """
        results = {}

        # Validation 1: Sum of deaths equals initial population.
        # sum(d_x) from min_age to max_age should equal l_{min_age}. Use a
        # relative tolerance so large radices (e.g. 100,000) do not fail on
        # pure float-summation noise.
        total_deaths = sum(self.d_x.values())
        l_0 = self.l_x[self.min_age]
        tol = 1e-9 * max(abs(l_0), 1.0)
        results["sum_deaths_equals_l0"] = abs(total_deaths - l_0) <= tol

        # Validation 2: Terminal age has 100% mortality
        results["terminal_mortality_is_one"] = abs(self.q_x[self.max_age] - 1.0) <= 1e-9

        # Validation 3: All mortality rates are valid probabilities
        results["all_rates_valid"] = all(
            -1e-9 <= q <= 1.0 + 1e-9 for q in self.q_x.values()
        )

        return results

    @property
    def omega(self) -> int:
        """Ultimate age (maximum age in table)."""
        return self._omega

    @property
    def ages(self) -> List[int]:
        """List of all ages in the table."""
        return list(range(self.min_age, self.max_age + 1))

    def __repr__(self) -> str:
        return f"LifeTable(ages={self.min_age}-{self.max_age}, l_0={self.l_x[self.min_age]:.0f})"

    def summary(self) -> str:
        """Generate a summary of the life table."""
        lines = [
            f"Life Table Summary",
            f"=" * 40,
            f"Age range: {self.min_age} to {self.max_age}",
            f"Initial population: {self.l_x[self.min_age]:,.0f}",
            f"Final survivors: {self.l_x[self.max_age]:,.0f}",
            f"",
            f"First 5 ages:",
        ]

        for age in list(self.ages)[:5]:
            lines.append(
                f"  Age {age}: l_x={self.l_x[age]:>10,.2f}, "
                f"q_x={self.q_x[age]:.4f}"
            )

        validations = self.validate()
        lines.append("")
        lines.append("Validations:")
        for check, passed in validations.items():
            status = "PASS" if passed else "FAIL"
            lines.append(f"  {check}: {status}")

        return "\n".join(lines)
