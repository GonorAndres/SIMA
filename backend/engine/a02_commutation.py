"""
Commutation Functions Module - Blocks 2 & 3
=============================================

Implements the four fundamental commutation functions: D, N, C, M.

Theory Connection:
-----------------
Commutation functions pre-compute discounted survival/death values to
simplify actuarial calculations. They encode both time-value-of-money
and mortality in single values:

    D_x = v^x * l_x       (discounted survivors at age x)
    N_x = sum(D_y, y=x to omega)   (sum of future discounted survivors)
    C_x = v^{x+1} * d_x   (discounted deaths at age x)
    M_x = sum(C_y, y=x to omega)   (sum of future discounted deaths)

Computational Strategy:
----------------------
We compute backwards from omega (ultimate age):
    - N_omega = D_omega
    - N_x = D_x + N_{x+1}

    - M_omega = C_omega
    - M_x = C_x + M_{x+1}

This avoids repeated summation (O(n) instead of O(n^2)).

Normalization Note:
------------------
We normalize to the starting age of the table, so:
    D_x = v^{x - min_age} * l_x

This keeps values manageable and is mathematically equivalent
for ratio-based calculations (A_x = M_x/D_x, etc).
"""

from __future__ import annotations

import warnings
from typing import Dict

from .a01_life_table import LifeTable
from .exceptions import ActuarialValidationError
from .validators import validate_interest_rate


class CommutationFunctions:
    """
    Commutation function calculator.

    Computes D, N, C, M values from a life table and interest rate.

    NORMALIZATION: This implementation uses v^(x - min_age) instead of
    the standard textbook v^x. This keeps values manageable and avoids
    extreme underflow for high ages. Since all actuarial values (A_x, a_x,
    nE_x, premiums, reserves) are ratios of commutation functions, the
    normalization constant cancels exactly. However, the absolute D, N, C, M
    values are NOT directly comparable to published commutation tables that
    use the standard v^x convention.

    ZERO INTEREST (i = 0): When ``interest_rate == 0`` we set ``v = 1`` and
    the commutation functions reduce to undiscounted survivor/death sums:

        D_x = l_x,   N_x = sum_{y>=x} l_y,   C_x = d_x,   M_x = sum_{y>=x} d_y

    All ratios (A_x, a_x, premiums, reserves) remain mathematically correct.

    Attributes:
        life_table: Source LifeTable
        i: Interest rate (e.g., 0.05 for 5%)
        v: Discount factor = 1/(1+i)
        D: Dict mapping age -> D_x
        N: Dict mapping age -> N_x
        C: Dict mapping age -> C_x
        M: Dict mapping age -> M_x
    """

    def __init__(self, life_table: LifeTable, interest_rate: float):
        """
        Initialize commutation functions from life table.

        Args:
            life_table: LifeTable instance (must be non-empty)
            interest_rate: Annual interest rate (e.g., 0.05 for 5%).
                ``0.0`` is explicitly allowed. Rates above ``1`` are allowed
                with a warning (they may be a misplaced percentage) up to a
                sanity ceiling.

        Raises:
            ActuarialValidationError: If the life table is empty or the
                interest rate is invalid (negative, non-finite, or absurd).
        """
        if len(life_table.ages) == 0:
            raise ActuarialValidationError(
                "Life table is empty; cannot build commutation functions",
                field="life_table",
                constraint="len(life_table.ages) > 0",
            )

        # Validate interest rate. allow_above_one=True so decimal-form rates
        # above 1 (e.g. a 120% hyperinflation scenario) are accepted with a
        # warning rather than rejected outright.
        validate_interest_rate(interest_rate, allow_above_one=True)
        if interest_rate > 1.0:
            warnings.warn(
                f"Interest rate {interest_rate} > 1; treating as a decimal. "
                f"Pass 0.05 for 5% if you meant a percentage.",
                stacklevel=2,
            )

        self.life_table = life_table
        self.i = float(interest_rate)
        # Explicit zero-interest fast path: v = 1 exactly (avoids any 1/(1+0)
        # rounding surprise and signals "undiscounted" to readers).
        self.v = 1.0 if self.i == 0.0 else 1.0 / (1.0 + self.i)

        # Storage for commutation values
        self.D: Dict[int, float] = {}
        self.N: Dict[int, float] = {}
        self.C: Dict[int, float] = {}
        self.M: Dict[int, float] = {}

        # Compute all values
        self._compute_D()
        self._compute_N()
        self._compute_C()
        self._compute_M()

    def _compute_D(self) -> None:
        """
        Compute D_x = v^(x - min_age) * l_x for all ages.

        Note: We normalize to min_age so D values don't become tiny
        for high ages. This is mathematically valid since all actuarial
        values are ratios that cancel out the normalization.
        """
        min_age = self.life_table.min_age

        for age in self.life_table.ages:
            # Normalized exponent: years from table start
            exponent = age - min_age
            self.D[age] = (self.v ** exponent) * self.life_table.get_l(age)

    def _compute_N(self) -> None:
        """
        Compute N_x = sum(D_y, y=x to omega) using backward recursion.

        Algorithm:
            N_omega = D_omega
            N_x = D_x + N_{x+1}  for x < omega
        """
        omega = self.life_table.omega

        # Start at terminal age
        self.N[omega] = self.D[omega]

        # Work backwards
        for age in range(omega - 1, self.life_table.min_age - 1, -1):
            self.N[age] = self.D[age] + self.N[age + 1]

    def _compute_C(self) -> None:
        """
        Compute C_x = v^(x+1 - min_age) * d_x for all ages.

        The extra power of v compared to D_x reflects that deaths
        at age x result in payment at age x+1 (end of year).
        """
        min_age = self.life_table.min_age

        for age in self.life_table.ages:
            # Exponent is one more than for D (death benefit paid at end of year)
            exponent = age + 1 - min_age
            self.C[age] = (self.v ** exponent) * self.life_table.get_d(age)

    def _compute_M(self) -> None:
        """
        Compute M_x = sum(C_y, y=x to omega) using backward recursion.

        Algorithm:
            M_omega = C_omega
            M_x = C_x + M_{x+1}  for x < omega
        """
        omega = self.life_table.omega

        # Start at terminal age
        self.M[omega] = self.C[omega]

        # Work backwards
        for age in range(omega - 1, self.life_table.min_age - 1, -1):
            self.M[age] = self.C[age] + self.M[age + 1]

    def get_D(self, age: int) -> float:
        """Get D_x at specified age."""
        if age not in self.D:
            raise ActuarialValidationError(
                f"D_x not available for age {age}; table covers "
                f"[{self.min_age}, {self.max_age}]",
                field="age",
                constraint=f"age in [{self.min_age}, {self.max_age}]",
            )
        return self.D[age]

    def get_N(self, age: int) -> float:
        """Get N_x at specified age."""
        if age not in self.N:
            raise ActuarialValidationError(
                f"N_x not available for age {age}; table covers "
                f"[{self.min_age}, {self.max_age}]",
                field="age",
                constraint=f"age in [{self.min_age}, {self.max_age}]",
            )
        return self.N[age]

    def get_C(self, age: int) -> float:
        """Get C_x at specified age."""
        if age not in self.C:
            raise ActuarialValidationError(
                f"C_x not available for age {age}; table covers "
                f"[{self.min_age}, {self.max_age}]",
                field="age",
                constraint=f"age in [{self.min_age}, {self.max_age}]",
            )
        return self.C[age]

    def get_M(self, age: int) -> float:
        """Get M_x at specified age."""
        if age not in self.M:
            raise ActuarialValidationError(
                f"M_x not available for age {age}; table covers "
                f"[{self.min_age}, {self.max_age}]",
                field="age",
                constraint=f"age in [{self.min_age}, {self.max_age}]",
            )
        return self.M[age]

    @property
    def min_age(self) -> int:
        """Minimum age in table."""
        return self.life_table.min_age

    @property
    def max_age(self) -> int:
        """Maximum age (omega) in table."""
        return self.life_table.max_age

    def summary(self) -> str:
        """Generate summary of commutation functions."""
        lines = [
            f"Commutation Functions Summary",
            f"=" * 50,
            f"Interest rate: {self.i:.2%}",
            f"Discount factor (v): {self.v:.6f}",
            f"Age range: {self.min_age} to {self.max_age}",
            f"",
            f"{'Age':>5} {'D_x':>12} {'N_x':>12} {'C_x':>12} {'M_x':>12}",
            f"-" * 55,
        ]

        for age in self.life_table.ages:
            lines.append(
                f"{age:>5} "
                f"{self.D[age]:>12.4f} "
                f"{self.N[age]:>12.4f} "
                f"{self.C[age]:>12.4f} "
                f"{self.M[age]:>12.4f}"
            )

        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"CommutationFunctions(ages={self.min_age}-{self.max_age}, "
            f"i={self.i:.2%})"
        )
