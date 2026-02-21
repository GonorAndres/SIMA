"""
Reserve Calculations Module - Block 6
======================================

Implements policy reserve calculations using the prospective method.

Theory Connection:
-----------------
The RESERVE at duration t (denoted tV_x) answers:
    "How much must the insurer hold NOW to cover future obligations?"

PROSPECTIVE METHOD:
    tV_x = APV(Future Benefits) - APV(Future Premiums)
         = SA * A_{x+t} - P * a_due_{x+t}

Using commutation functions:
    tV_x = SA * (M_{x+t}/D_{x+t}) - P * (N_{x+t}/D_{x+t})
         = (SA * M_{x+t} - P * N_{x+t}) / D_{x+t}

Key Properties:
--------------
1. 0V_x = 0  (at issue, reserve is zero - equivalence principle)
2. Reserve increases over time (premiums accumulate)
3. At omega, reserve approaches SA (certain death)

LISF Compliance:
---------------
Mexican regulations (LISF Art. 217) require reserves calculated
using the net premium method, which is exactly what we implement.
"""

from typing import List, Dict, Tuple
from .a02_commutation import CommutationFunctions
from .a03_actuarial_values import ActuarialValues
from .a04_premiums import PremiumCalculator


class ReserveCalculator:
    """
    Policy reserve calculator using prospective method.

    Reserves represent the liability the insurer must hold to
    cover future benefit payments, net of future premium income.
    """

    def __init__(self, commutation: CommutationFunctions):
        """
        Initialize with commutation functions.

        Args:
            commutation: CommutationFunctions instance
        """
        self.comm = commutation
        self.av = ActuarialValues(commutation)
        self.pc = PremiumCalculator(commutation)

    def reserve_whole_life(self, SA: float, x: int, t: int) -> float:
        """
        Reserve at duration t for whole life policy issued at age x.

        tV_x = SA * A_{x+t} - P * a_due_{x+t}

        WHERE:
            SA = Sum Assured (death benefit)
            x = issue age
            t = years since issue (duration)
            x+t = current attained age
            P = annual premium (calculated at issue)
            A_{x+t} = insurance value at attained age
            a_due_{x+t} = annuity value at attained age

        Args:
            SA: Sum Assured
            x: Issue age
            t: Duration (years since issue)

        Returns:
            Reserve amount at duration t
        """
        # Current attained age
        attained_age = x + t

        # Check bounds
        if attained_age > self.comm.max_age:
            # Beyond omega - return SA (everyone has died)
            return SA

        # Step 1: Get the premium that was set at issue
        # This P was calculated to satisfy equivalence at age x
        P = self.pc.whole_life(SA, x)

        # Step 2: Get actuarial values at CURRENT age (x+t)
        # These reflect the remaining lifetime from now
        A_attained = self.av.A_x(attained_age)          # Future death benefit PV
        a_due_attained = self.av.a_due(attained_age)    # Future premium collection PV

        # Step 3: Apply prospective formula
        # Reserve = Future Benefits - Future Premiums
        reserve = SA * A_attained - P * a_due_attained

        return reserve

    def reserve_term(self, SA: float, x: int, n: int, t: int) -> float:
        """
        Reserve at duration t for n-year term policy issued at age x.

        For t < n:
            tV = SA * A^1_{x+t:n-t|} - P * a_{x+t:n-t|}

        For t >= n:
            tV = 0 (policy has expired)

        Args:
            SA: Sum Assured
            x: Issue age
            n: Original term length
            t: Duration (years since issue)

        Returns:
            Reserve amount at duration t
        """
        # Policy expired?
        if t >= n:
            return 0.0

        attained_age = x + t
        remaining_term = n - t

        if attained_age > self.comm.max_age:
            return 0.0

        # Premium set at issue (for full n-year term)
        P = self.pc.term(SA, x, n)

        # Future values for REMAINING term
        A_term_remaining = self.av.A_term(attained_age, remaining_term)
        a_due_remaining = self.av.a_due_temporary(attained_age, remaining_term)

        # Prospective reserve
        reserve = SA * A_term_remaining - P * a_due_remaining

        return reserve

    def reserve_endowment(self, SA: float, x: int, n: int, t: int) -> float:
        """
        Reserve at duration t for n-year endowment issued at age x.

        For t < n:
            tV = SA * A_{x+t:n-t|} - P * a_{x+t:n-t|}

        At t = n:
            tV = SA (policy matures, full amount due)

        Args:
            SA: Sum Assured
            x: Issue age
            n: Endowment period
            t: Duration (years since issue)

        Returns:
            Reserve amount at duration t
        """
        # At maturity, reserve equals SA
        if t >= n:
            return SA

        attained_age = x + t
        remaining_term = n - t

        if attained_age > self.comm.max_age:
            return SA

        # Premium set at issue
        P = self.pc.endowment(SA, x, n)

        # Future values for remaining period
        A_endow_remaining = self.av.A_endowment(attained_age, remaining_term)
        a_due_remaining = self.av.a_due_temporary(attained_age, remaining_term)

        # Prospective reserve
        reserve = SA * A_endow_remaining - P * a_due_remaining

        return reserve

    def reserve_pure_endowment(self, SA: float, x: int, n: int, t: int) -> float:
        """
        Reserve at duration t for n-year pure endowment issued at age x.

        For t < n:
            tV = SA * nE_{x+t:n-t|} - P * a_{x+t:n-t|}

        At t = n:
            tV = SA (policyholder survived, payment due)

        Args:
            SA: Sum Assured (survival benefit)
            x: Issue age
            n: Survival period
            t: Duration (years since issue)

        Returns:
            Reserve amount at duration t
        """
        if t >= n:
            return SA

        attained_age = x + t
        remaining_term = n - t

        if attained_age > self.comm.max_age:
            return 0.0

        # Premium set at issue
        P = self.pc.pure_endowment(SA, x, n)

        # Future values for remaining period
        nE_remaining = self.av.nE_x(attained_age, remaining_term)
        a_due_remaining = self.av.a_due_temporary(attained_age, remaining_term)

        # Prospective reserve
        reserve = SA * nE_remaining - P * a_due_remaining

        return reserve

    def reserve_trajectory(self, SA: float, x: int,
                          product: str = "whole_life",
                          n: int = None) -> List[Tuple[int, float]]:
        """
        Calculate reserve at each duration from 0 to end of policy.

        Returns list of (duration, reserve) pairs showing how
        reserve builds over the policy lifetime.

        Args:
            SA: Sum Assured
            x: Issue age
            product: "whole_life", "term", or "endowment"
            n: Term/endowment period (required for term/endowment)

        Returns:
            List of (t, tV) tuples
        """
        trajectory = []

        if product == "whole_life":
            max_t = self.comm.max_age - x
            for t in range(max_t + 1):
                reserve = self.reserve_whole_life(SA, x, t)
                trajectory.append((t, reserve))

        elif product == "term":
            if n is None:
                raise ValueError("Term product requires n")
            for t in range(n + 1):
                reserve = self.reserve_term(SA, x, n, t)
                trajectory.append((t, reserve))

        elif product == "endowment":
            if n is None:
                raise ValueError("Endowment product requires n")
            for t in range(n + 1):
                reserve = self.reserve_endowment(SA, x, n, t)
                trajectory.append((t, reserve))

        elif product == "pure_endowment":
            if n is None:
                raise ValueError("Pure endowment product requires n")
            for t in range(n + 1):
                reserve = self.reserve_pure_endowment(SA, x, n, t)
                trajectory.append((t, reserve))

        else:
            raise ValueError(f"Unknown product: {product}")

        return trajectory

    def validate_zero_reserve(self, SA: float, x: int,
                             product: str = "whole_life",
                             n: int = None) -> Dict:
        """
        Validate that reserve at issue (t=0) equals zero.

        This is a fundamental check of the equivalence principle:
        if P was calculated correctly, then at t=0:
            APV(Premiums) = APV(Benefits)
            => 0V = 0

        Args:
            SA: Sum Assured
            x: Issue age
            product: Product type
            n: Term (if applicable)

        Returns:
            Dict with validation details
        """
        if product == "whole_life":
            reserve_0 = self.reserve_whole_life(SA, x, 0)
            P = self.pc.whole_life(SA, x)
        elif product == "term":
            reserve_0 = self.reserve_term(SA, x, n, 0)
            P = self.pc.term(SA, x, n)
        elif product == "endowment":
            reserve_0 = self.reserve_endowment(SA, x, n, 0)
            P = self.pc.endowment(SA, x, n)
        else:
            raise ValueError(f"Unknown product: {product}")

        return {
            'product': product,
            'issue_age': x,
            'sum_assured': SA,
            'premium': P,
            'reserve_at_0': reserve_0,
            'is_zero': abs(reserve_0) < 0.01,
            'explanation': (
                "0V = 0 confirms equivalence principle: "
                "at issue, APV(premiums) = APV(benefits)"
            )
        }

    def summary(self, SA: float, x: int, product: str = "whole_life",
                n: int = None) -> str:
        """
        Generate reserve summary for a policy.

        Args:
            SA: Sum Assured
            x: Issue age
            product: Product type
            n: Term (if applicable)

        Returns:
            Formatted summary string
        """
        lines = [
            f"Reserve Summary: {product.replace('_', ' ').title()}",
            f"=" * 50,
            f"Sum Assured: ${SA:,.2f}",
            f"Issue Age: {x}",
            f"Interest Rate: {self.comm.i:.2%}",
        ]

        if n is not None:
            lines.append(f"Term: {n} years")

        # Get premium
        if product == "whole_life":
            P = self.pc.whole_life(SA, x)
        elif product == "term":
            P = self.pc.term(SA, x, n)
        elif product == "endowment":
            P = self.pc.endowment(SA, x, n)

        lines.append(f"Annual Premium: ${P:,.2f}")
        lines.append("")
        lines.append("Reserve Trajectory:")
        lines.append(f"{'Duration':>10} {'Age':>6} {'Reserve':>15}")
        lines.append("-" * 35)

        trajectory = self.reserve_trajectory(SA, x, product, n)

        # Show first few and last few
        if len(trajectory) <= 10:
            for t, reserve in trajectory:
                lines.append(f"{t:>10} {x+t:>6} ${reserve:>14,.2f}")
        else:
            for t, reserve in trajectory[:5]:
                lines.append(f"{t:>10} {x+t:>6} ${reserve:>14,.2f}")
            lines.append(f"{'...':>10}")
            for t, reserve in trajectory[-3:]:
                lines.append(f"{t:>10} {x+t:>6} ${reserve:>14,.2f}")

        # Validation
        lines.append("")
        validation = self.validate_zero_reserve(SA, x, product, n)
        lines.append(f"0V = ${validation['reserve_at_0']:.2f} (should be ~0)")

        return "\n".join(lines)
