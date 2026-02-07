"""
Premium Calculations Module - Block 5
======================================

Implements net premium calculations using the equivalence principle.

Theory Connection:
-----------------
The EQUIVALENCE PRINCIPLE states that at policy issue:

    APV(Premium Income) = APV(Benefit Outgo)
    P * a_{x:n|} = SA * A_{x:n|}

Solving for P:
    P = SA * A_{x:n|} / a_{x:n|}

Using commutation functions, this simplifies beautifully because
D_x cancels in numerator and denominator:

    Whole Life:    P = SA * (M_x/D_x) / (N_x/D_x) = SA * M_x / N_x
    Term n years:  P = SA * (M_x - M_{x+n}) / (N_x - N_{x+n})
    Endowment:     P = SA * (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n})

Why This Works:
--------------
The premium exactly balances expected benefits with expected contributions.
- At issue, the insurer has no accumulated assets for this policy
- Each premium collected builds reserves to pay future claims
- If mortality and interest match assumptions, no profit or loss occurs

LISF Compliance Note:
--------------------
Mexican regulations (LISF Art. 217) require net premium method for reserves.
These net premiums form the basis of reserve calculations.
"""

from typing import Optional
from .a02_commutation import CommutationFunctions
from .a03_actuarial_values import ActuarialValues


class PremiumCalculator:
    """
    Net premium calculator using equivalence principle.

    All premiums are NET premiums (no expense loading, no profit margin).
    These represent the theoretical minimum premium to cover mortality
    and interest.
    """

    def __init__(self, commutation: CommutationFunctions):
        """
        Initialize with commutation functions.

        Args:
            commutation: CommutationFunctions instance
        """
        self.comm = commutation
        self.av = ActuarialValues(commutation)

    def whole_life(self, SA: float, x: int) -> float:
        """
        Net annual premium for whole life insurance.

        P = SA * M_x / N_x

        This is paid annually at the start of each year while
        the policyholder survives.

        Args:
            SA: Sum Assured (face amount / death benefit)
            x: Issue age

        Returns:
            Net annual premium (in same units as SA)

        Example:
            SA = $100,000, age 60
            P = 100,000 * M_60 / N_60 = 100,000 * 0.2489 = $24,890/year
        """
        M_x = self.comm.get_M(x)
        N_x = self.comm.get_N(x)

        return SA * (M_x / N_x)

    def term(self, SA: float, x: int, n: int) -> float:
        """
        Net annual premium for term insurance.

        P = SA * (M_x - M_{x+n}) / (N_x - N_{x+n})

        Coverage expires after n years. Premium payments also stop
        after n years.

        Args:
            SA: Sum Assured
            x: Issue age
            n: Term length in years

        Returns:
            Net annual premium

        Note:
            If n extends beyond omega, returns whole life premium.
        """
        x_plus_n = x + n

        if x_plus_n > self.comm.max_age:
            # Term extends beyond omega, equivalent to whole life
            return self.whole_life(SA, x)

        M_x = self.comm.get_M(x)
        M_x_n = self.comm.get_M(x_plus_n)
        N_x = self.comm.get_N(x)
        N_x_n = self.comm.get_N(x_plus_n)

        numerator = M_x - M_x_n
        denominator = N_x - N_x_n

        return SA * (numerator / denominator)

    def endowment(self, SA: float, x: int, n: int) -> float:
        """
        Net annual premium for endowment insurance.

        P = SA * (M_x - M_{x+n} + D_{x+n}) / (N_x - N_{x+n})

        Pays SA at death (if within n years) OR at survival to age x+n.
        Premium payments are for n years.

        Args:
            SA: Sum Assured
            x: Issue age
            n: Endowment period in years

        Returns:
            Net annual premium

        Note:
            Endowment premiums are higher than term premiums because
            the insurer WILL pay the SA either way (death or survival).
        """
        x_plus_n = x + n

        if x_plus_n > self.comm.max_age:
            # Beyond omega, just whole life
            return self.whole_life(SA, x)

        M_x = self.comm.get_M(x)
        M_x_n = self.comm.get_M(x_plus_n)
        D_x_n = self.comm.get_D(x_plus_n)
        N_x = self.comm.get_N(x)
        N_x_n = self.comm.get_N(x_plus_n)

        # Numerator: death benefit + survival benefit (pure endowment)
        numerator = (M_x - M_x_n) + D_x_n

        # Denominator: n years of premium payments
        denominator = N_x - N_x_n

        return SA * (numerator / denominator)

    def pure_endowment(self, SA: float, x: int, n: int) -> float:
        """
        Net annual premium for pure endowment.

        P = SA * D_{x+n} / (N_x - N_{x+n})

        Pays SA ONLY if policyholder survives n years. No death benefit.

        Args:
            SA: Sum Assured (paid at survival)
            x: Issue age
            n: Survival period in years

        Returns:
            Net annual premium
        """
        x_plus_n = x + n

        if x_plus_n > self.comm.max_age:
            # Cannot survive beyond omega
            return 0.0

        D_x_n = self.comm.get_D(x_plus_n)
        N_x = self.comm.get_N(x)
        N_x_n = self.comm.get_N(x_plus_n)

        numerator = D_x_n
        denominator = N_x - N_x_n

        return SA * (numerator / denominator)

    def limited_pay_whole_life(self, SA: float, x: int, m: int) -> float:
        """
        Net annual premium for whole life with limited premium payments.

        mP_x = SA * M_x / (N_x - N_{x+m})

        Coverage is whole life, but premiums are paid only for m years.

        Args:
            SA: Sum Assured
            x: Issue age
            m: Premium payment period in years

        Returns:
            Net annual premium (higher than regular whole life)

        Note:
            Since fewer premiums are collected, each premium is larger.
        """
        x_plus_m = x + m

        if x_plus_m > self.comm.max_age:
            # Payment period extends beyond omega, just regular whole life
            return self.whole_life(SA, x)

        M_x = self.comm.get_M(x)
        N_x = self.comm.get_N(x)
        N_x_m = self.comm.get_N(x_plus_m)

        numerator = M_x
        denominator = N_x - N_x_m

        return SA * (numerator / denominator)

    def single_premium(self, SA: float, x: int, product: str = "whole_life") -> float:
        """
        Single premium (one-time payment at issue).

        pi = SA * A_x  (for whole life)

        Args:
            SA: Sum Assured
            x: Issue age
            product: "whole_life" or other product type

        Returns:
            Single premium amount
        """
        if product == "whole_life":
            return SA * self.av.A_x(x)
        else:
            raise ValueError(f"Unknown product type: {product}")

    def premium_per_unit(self, x: int, product: str = "whole_life",
                         n: Optional[int] = None) -> float:
        """
        Calculate premium per $1 of sum assured (unit premium).

        This is the "rate" that gets multiplied by SA.

        Args:
            x: Issue age
            product: "whole_life", "term", "endowment", "pure_endowment"
            n: Term/endowment period (required for term/endowment)

        Returns:
            Premium rate per $1 of coverage
        """
        if product == "whole_life":
            return self.whole_life(1.0, x)
        elif product == "term":
            if n is None:
                raise ValueError("Term product requires n (term length)")
            return self.term(1.0, x, n)
        elif product == "endowment":
            if n is None:
                raise ValueError("Endowment product requires n (term length)")
            return self.endowment(1.0, x, n)
        elif product == "pure_endowment":
            if n is None:
                raise ValueError("Pure endowment requires n (term length)")
            return self.pure_endowment(1.0, x, n)
        else:
            raise ValueError(f"Unknown product type: {product}")

    def summary(self, SA: float, x: int, n: int = 10) -> str:
        """
        Generate premium comparison for all products.

        Args:
            SA: Sum Assured
            x: Issue age
            n: Term/endowment period

        Returns:
            Formatted summary string
        """
        lines = [
            f"Net Premium Summary",
            f"=" * 50,
            f"Sum Assured: ${SA:,.2f}",
            f"Issue Age: {x}",
            f"Interest Rate: {self.comm.i:.2%}",
            f"",
            f"Annual Premiums:",
            f"  Whole Life:           ${self.whole_life(SA, x):>12,.2f}",
            f"  Term ({n} years):       ${self.term(SA, x, n):>12,.2f}",
            f"  Endowment ({n} years):  ${self.endowment(SA, x, n):>12,.2f}",
            f"  Pure Endowment ({n}y):  ${self.pure_endowment(SA, x, n):>12,.2f}",
            f"  Limited Pay ({n}y) WL:  ${self.limited_pay_whole_life(SA, x, n):>12,.2f}",
            f"",
            f"Single Premium (Whole Life): ${self.single_premium(SA, x):>12,.2f}",
            f"",
            f"Premium Rates (per $1 SA):",
            f"  Whole Life:           {self.premium_per_unit(x, 'whole_life'):.6f}",
            f"  Term ({n}y):            {self.premium_per_unit(x, 'term', n):.6f}",
            f"  Endowment ({n}y):       {self.premium_per_unit(x, 'endowment', n):.6f}",
        ]

        return "\n".join(lines)

    def verify_equivalence(self, SA: float, x: int) -> dict:
        """
        Verify equivalence principle holds for whole life.

        At issue: APV(Premiums) = APV(Benefits)

        Returns dict with both sides of equation.
        """
        P = self.whole_life(SA, x)
        a_due = self.av.a_due(x)
        A = self.av.A_x(x)

        apv_premiums = P * a_due
        apv_benefits = SA * A

        return {
            'premium': P,
            'apv_premiums': apv_premiums,
            'apv_benefits': apv_benefits,
            'difference': abs(apv_premiums - apv_benefits),
            'balanced': abs(apv_premiums - apv_benefits) < 0.01
        }
