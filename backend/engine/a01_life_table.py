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

from pathlib import Path
from typing import Optional, Dict, List
import csv


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
        """
        if len(ages) != len(l_x_values):
            raise ValueError("Ages and l_x values must have same length")

        if len(ages) < 2:
            raise ValueError("Life table must have at least 2 ages")

        # Store basic info
        self.min_age = min(ages)
        self.max_age = max(ages)
        self._omega = self.max_age  # Ultimate age

        # Build l_x dictionary
        self.l_x: Dict[int, float] = {}
        for age, lx in zip(ages, l_x_values):
            self.l_x[age] = lx

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

            # Deaths: d_x = l_x - l_{x+1}
            self.d_x[age] = l_current - l_next

            # Mortality rate: q_x = d_x / l_x
            if l_current > 0:
                self.q_x[age] = self.d_x[age] / l_current
            else:
                self.q_x[age] = 1.0  # Edge case: no survivors

            # Survival rate: p_x = 1 - q_x
            self.p_x[age] = 1.0 - self.q_x[age]

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

        with open(path, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ages.append(int(row['age']))
                qx_values.append(float(row[col]))

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
        if start_age < self.min_age or end_age > self.max_age:
            raise ValueError(
                f"Subset range [{start_age}, {end_age}] out of bounds "
                f"[{self.min_age}, {self.max_age}]"
            )

        ages = list(range(start_age, end_age + 1))
        l_x_values = [self.l_x[age] for age in ages]

        return LifeTable(ages, l_x_values)

    def get_l(self, age: int) -> float:
        """Get l_x (survivors) at specified age."""
        if age not in self.l_x:
            raise KeyError(f"Age {age} not in life table")
        return self.l_x[age]

    def get_d(self, age: int) -> float:
        """Get d_x (deaths) at specified age."""
        if age not in self.d_x:
            raise KeyError(f"Age {age} not in life table for d_x")
        return self.d_x[age]

    def get_q(self, age: int) -> float:
        """Get q_x (mortality rate) at specified age."""
        if age not in self.q_x:
            raise KeyError(f"Age {age} not in life table for q_x")
        return self.q_x[age]

    def get_p(self, age: int) -> float:
        """Get p_x (survival rate) at specified age."""
        if age not in self.p_x:
            raise KeyError(f"Age {age} not in life table for p_x")
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

        # Validation 1: Sum of deaths equals initial population
        # sum(d_x) from min_age to max_age should equal l_{min_age}
        total_deaths = sum(self.d_x.values())
        l_0 = self.l_x[self.min_age]
        results['sum_deaths_equals_l0'] = abs(total_deaths - l_0) < 1e-6

        # Validation 2: Terminal age has 100% mortality
        results['terminal_mortality_is_one'] = abs(self.q_x[self.max_age] - 1.0) < 1e-6

        # Validation 3: All mortality rates are valid probabilities
        results['all_rates_valid'] = all(
            0 <= q <= 1 for q in self.q_x.values()
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
