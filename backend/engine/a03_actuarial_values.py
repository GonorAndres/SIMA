"""
Actuarial Present Values Module - Block 4
==========================================

Implements standard actuarial present value functions for insurance
and annuities.

Theory Connection:
-----------------
Actuarial present values (APVs) are expected present values that
account for both mortality and interest. They answer: "What is the
fair value today of a contingent payment?"

Insurance Values (Death Benefits):
    A_x = M_x / D_x          Whole life insurance (pay $1 at death)
    A^1_{x:n|} = (M_x - M_{x+n}) / D_x   Term insurance (n years)

Annuity Values (Survival Benefits):
    a_due_x = N_x / D_x      Whole life annuity-due (pay $1/yr at start)
    a_imm_x = a_due_x - 1    Annuity-immediate (first payment in 1 year)
    a_{x:n|} = (N_x - N_{x+n}) / D_x    Temporary annuity (n payments)

Endowment Values:
    nE_x = D_{x+n} / D_x     Pure endowment (pay if survive n years)
    A_{x:n|} = A^1_{x:n|} + nE_x    Endowment insurance (death OR survival)

Key Insight:
-----------
D_x in the denominator normalizes "per person alive at age x".
This is why all these formulas are simple ratios.
"""

from typing import Optional, Dict
from .a02_commutation import CommutationFunctions


class ActuarialValues:
    """
    Calculator for actuarial present values.

    Uses commutation functions to compute insurance and annuity values.
    """

    def __init__(self, commutation: CommutationFunctions):
        """
        Initialize with commutation functions.

        Args:
            commutation: CommutationFunctions instance
        """
        self.comm = commutation

    # =========================================================================
    # INSURANCE VALUES (Death Benefits)
    # =========================================================================

    def A_x(self, x: int) -> float:
        """
        Whole life insurance APV at age x.

        A_x = M_x / D_x

        Interpretation: Expected PV of $1 paid at death for a life aged x.
        Range: 0 < A_x < 1 (increases with age, approaches 1 near omega)

        Args:
            x: Age

        Returns:
            APV of whole life insurance (per $1 benefit)
        """
        return self.comm.get_M(x) / self.comm.get_D(x)

    def A_term(self, x: int, n: int) -> float:
        """
        Term insurance APV at age x for n years.

        A^1_{x:n|} = (M_x - M_{x+n}) / D_x

        Interpretation: Expected PV of $1 paid if death occurs within n years.
        Range: 0 < A^1 < A_x (always less than whole life)

        Args:
            x: Issue age
            n: Term length in years

        Returns:
            APV of term insurance (per $1 benefit)
        """
        x_plus_n = x + n
        if x_plus_n > self.comm.max_age:
            # Term extends beyond omega, equivalent to whole life from x
            return self.A_x(x)

        M_x = self.comm.get_M(x)
        M_x_n = self.comm.get_M(x_plus_n)
        D_x = self.comm.get_D(x)

        return (M_x - M_x_n) / D_x

    # =========================================================================
    # ANNUITY VALUES (Survival Benefits)
    # =========================================================================

    def a_due(self, x: int) -> float:
        """
        Whole life annuity-due APV at age x.

        a_due_x = N_x / D_x

        Interpretation: Expected PV of $1/year paid at start of each year
        while the life survives.

        Args:
            x: Age

        Returns:
            APV of whole life annuity-due (per $1/year)
        """
        return self.comm.get_N(x) / self.comm.get_D(x)

    def a_immediate(self, x: int) -> float:
        """
        Whole life annuity-immediate APV at age x.

        a_imm_x = a_due_x - 1 = (N_x / D_x) - 1 = (N_x - D_x) / D_x
                = N_{x+1} / D_x

        Interpretation: Expected PV of $1/year paid at END of each year.
        First payment is 1 year from now.

        Args:
            x: Age

        Returns:
            APV of whole life annuity-immediate (per $1/year)
        """
        return self.a_due(x) - 1.0

    def a_due_temporary(self, x: int, n: int) -> float:
        """
        Temporary annuity-due APV at age x for n years.

        a_{x:n|} = (N_x - N_{x+n}) / D_x

        Interpretation: Expected PV of up to n payments of $1/year,
        paid at start of year while life survives.

        Args:
            x: Issue age
            n: Maximum number of payments

        Returns:
            APV of temporary annuity-due (per $1/year)
        """
        x_plus_n = x + n
        if x_plus_n > self.comm.max_age:
            # Term extends beyond omega, equivalent to whole life from x
            return self.a_due(x)

        N_x = self.comm.get_N(x)
        N_x_n = self.comm.get_N(x_plus_n)
        D_x = self.comm.get_D(x)

        return (N_x - N_x_n) / D_x

    # =========================================================================
    # ENDOWMENT VALUES (Survival + Death)
    # =========================================================================

    def nE_x(self, x: int, n: int) -> float:
        """
        Pure endowment APV at age x for n years.

        nE_x = D_{x+n} / D_x

        Interpretation: Expected PV of $1 paid if life survives n years.
        Combines survival probability with interest discount.

        Args:
            x: Issue age
            n: Years to survive

        Returns:
            APV of pure endowment (per $1 benefit)
        """
        x_plus_n = x + n
        if x_plus_n > self.comm.max_age:
            # Cannot survive beyond omega
            return 0.0

        return self.comm.get_D(x_plus_n) / self.comm.get_D(x)

    def A_endowment(self, x: int, n: int) -> float:
        """
        Endowment insurance APV at age x for n years.

        A_{x:n|} = A^1_{x:n|} + nE_x
                 = (M_x - M_{x+n} + D_{x+n}) / D_x

        Interpretation: Expected PV of $1 paid either at death (if within n years)
        OR at survival to age x+n.

        This is the sum of term insurance + pure endowment.

        Args:
            x: Issue age
            n: Term/endowment period

        Returns:
            APV of endowment insurance (per $1 benefit)
        """
        x_plus_n = x + n
        if x_plus_n > self.comm.max_age:
            # Term extends beyond omega, just whole life
            return self.A_x(x)

        M_x = self.comm.get_M(x)
        M_x_n = self.comm.get_M(x_plus_n)
        D_x = self.comm.get_D(x)
        D_x_n = self.comm.get_D(x_plus_n)

        return (M_x - M_x_n + D_x_n) / D_x

    # =========================================================================
    # SUMMARY AND UTILITIES
    # =========================================================================

    def summary(self, x: int, n: int = 10) -> str:
        """
        Generate summary of actuarial values at age x.

        Args:
            x: Age
            n: Term length for temporary products

        Returns:
            Formatted string summary
        """
        lines = [
            f"Actuarial Present Values at Age {x}",
            f"=" * 50,
            f"Interest rate: {self.comm.i:.2%}",
            f"",
            f"Insurance (Death Benefits):",
            f"  A_{x} (whole life)      = {self.A_x(x):.6f}",
            f"  A^1_{x}:{n}| (term {n}y)    = {self.A_term(x, n):.6f}",
            f"",
            f"Annuities (Survival Benefits):",
            f"  a_due_{x} (annuity-due)  = {self.a_due(x):.6f}",
            f"  a_imm_{x} (ann-immed)    = {self.a_immediate(x):.6f}",
            f"  a_{x}:{n}| (temp {n}y)     = {self.a_due_temporary(x, n):.6f}",
            f"",
            f"Endowments:",
            f"  {n}E_{x} (pure endow)    = {self.nE_x(x, n):.6f}",
            f"  A_{x}:{n}| (endow ins)   = {self.A_endowment(x, n):.6f}",
            f"",
            f"Verification:",
            f"  A_x + d*a_due_x = 1?     {self.A_x(x) + (self.comm.i / (1+self.comm.i)) * self.a_due(x):.6f}",
        ]

        return "\n".join(lines)
