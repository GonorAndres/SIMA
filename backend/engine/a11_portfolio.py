"""
Portfolio Module - Block 11
============================

Implements Policy and Portfolio classes for managing insurance portfolios
and computing Best Estimate Liabilities (BEL) under Solvency II / CNSF.

Theory Connection:
-----------------
The Best Estimate Liability (BEL) is the probability-weighted average of
future cash flows, discounted at the risk-free rate. Under Solvency II
(and the Mexican CUSF), BEL is the central building block of technical
provisions (Reservas Tecnicas).

For DEATH products (whole life, term, endowment):
    BEL = tV = SA * A_{x+t} - P * a_due_{x+t}
    This is IDENTICAL to the prospective reserve (our ReserveCalculator).

For ANNUITY products (life annuity):
    BEL = annual_pension * a_due(attained_age)
    No future premiums to subtract -- the insurer simply owes payments.

Key Properties:
--------------
1. BEL at issue for death products ~ 0 (equivalence principle: premiums
   are priced to match expected benefits exactly).
2. BEL for in-force death products > 0 (reserve has accumulated).
3. BEL for annuities > 0 ALWAYS (insurer owes from day one).

LISF Compliance:
---------------
Mexican regulation (LISF Art. 217, CUSF) requires insurers to compute
BEL as the present value of future obligations less future premium income,
using best-estimate mortality assumptions and risk-free discount rates.
"""

from typing import List, Dict, Optional

from .a01_life_table import LifeTable
from .a02_commutation import CommutationFunctions
from .a03_actuarial_values import ActuarialValues
from .a04_premiums import PremiumCalculator
from .a05_reserves import ReserveCalculator


class Policy:
    """
    Represents a single insurance policy.

    Attributes:
        policy_id: Unique identifier
        product_type: "whole_life", "term", "endowment", or "annuity"
        issue_age: Age at policy issue
        SA: Sum assured (death benefit) for death products
        annual_pension: Annual payment for annuity products
        n: Term in years (term/endowment only)
        duration: Years since issue (0 = newly issued)
    """

    DEATH_PRODUCTS = {"whole_life", "term", "endowment"}
    ANNUITY_PRODUCTS = {"annuity"}
    VALID_PRODUCTS = DEATH_PRODUCTS | ANNUITY_PRODUCTS

    def __init__(
        self,
        policy_id: str,
        product_type: str,
        issue_age: int,
        SA: float = 0.0,
        annual_pension: float = 0.0,
        n: Optional[int] = None,
        duration: int = 0,
    ):
        if product_type not in self.VALID_PRODUCTS:
            raise ValueError(
                f"Unknown product_type '{product_type}'. "
                f"Must be one of: {sorted(self.VALID_PRODUCTS)}"
            )

        if product_type in ("term", "endowment") and n is None:
            raise ValueError(f"{product_type} requires n (term length)")

        self.policy_id = policy_id
        self.product_type = product_type
        self.issue_age = issue_age
        self.SA = SA
        self.annual_pension = annual_pension
        self.n = n
        self.duration = duration

    @property
    def is_death_product(self) -> bool:
        """True for whole_life, term, endowment."""
        return self.product_type in self.DEATH_PRODUCTS

    @property
    def is_annuity(self) -> bool:
        """True for annuity products."""
        return self.product_type in self.ANNUITY_PRODUCTS

    @property
    def attained_age(self) -> int:
        """Current age = issue_age + duration."""
        return self.issue_age + self.duration

    def __repr__(self) -> str:
        if self.is_death_product:
            return (
                f"Policy({self.policy_id}, {self.product_type}, "
                f"age={self.issue_age}, SA={self.SA:,.0f}, dur={self.duration})"
            )
        else:
            return (
                f"Policy({self.policy_id}, annuity, "
                f"age={self.issue_age}, pension={self.annual_pension:,.0f}, "
                f"dur={self.duration})"
            )


def compute_policy_bel(
    policy: Policy,
    life_table: LifeTable,
    interest_rate: float,
) -> float:
    """
    Compute BEL for a single policy.

    For death products: BEL = prospective reserve at current duration.
    For annuities: BEL = annual_pension * a_due(attained_age).

    Args:
        policy: The Policy instance
        life_table: Mortality table to use (best-estimate)
        interest_rate: Risk-free discount rate

    Returns:
        BEL amount (float)
    """
    comm = CommutationFunctions(life_table, interest_rate=interest_rate)

    if policy.is_death_product:
        rc = ReserveCalculator(comm)
        if policy.product_type == "whole_life":
            return rc.reserve_whole_life(
                SA=policy.SA, x=policy.issue_age, t=policy.duration
            )
        elif policy.product_type == "term":
            return rc.reserve_term(
                SA=policy.SA, x=policy.issue_age, n=policy.n, t=policy.duration
            )
        elif policy.product_type == "endowment":
            return rc.reserve_endowment(
                SA=policy.SA, x=policy.issue_age, n=policy.n, t=policy.duration
            )
    else:
        # Annuity: BEL = pension * a_due(attained_age)
        av = ActuarialValues(comm)
        return policy.annual_pension * av.a_due(policy.attained_age)


class Portfolio:
    """
    A collection of insurance policies.

    Provides filtering (death vs annuity), aggregate BEL computation,
    and per-policy breakdown.
    """

    def __init__(self, policies: List[Policy]):
        self.policies = list(policies)

    @property
    def death_products(self) -> List[Policy]:
        """All death-benefit policies (whole_life, term, endowment)."""
        return [p for p in self.policies if p.is_death_product]

    @property
    def annuity_products(self) -> List[Policy]:
        """All annuity policies."""
        return [p for p in self.policies if p.is_annuity]

    def compute_bel(self, life_table: LifeTable, interest_rate: float) -> float:
        """
        Total BEL for the entire portfolio.

        Args:
            life_table: Best-estimate mortality table
            interest_rate: Risk-free discount rate

        Returns:
            Aggregate BEL (sum of individual policy BELs)
        """
        return sum(
            compute_policy_bel(p, life_table, interest_rate)
            for p in self.policies
        )

    def compute_bel_breakdown(
        self, life_table: LifeTable, interest_rate: float
    ) -> List[Dict]:
        """
        Per-policy BEL breakdown.

        Returns:
            List of dicts with policy details and individual BEL.
        """
        breakdown = []
        for p in self.policies:
            bel = compute_policy_bel(p, life_table, interest_rate)
            entry = {
                "policy_id": p.policy_id,
                "product_type": p.product_type,
                "issue_age": p.issue_age,
                "attained_age": p.attained_age,
                "duration": p.duration,
                "bel": bel,
            }
            if p.is_death_product:
                entry["SA"] = p.SA
            else:
                entry["annual_pension"] = p.annual_pension
            breakdown.append(entry)
        return breakdown

    def compute_bel_by_type(
        self, life_table: LifeTable, interest_rate: float
    ) -> Dict[str, float]:
        """
        BEL split by product category: death vs annuity.

        Returns:
            Dict with "death_bel", "annuity_bel", "total_bel".
        """
        death_bel = sum(
            compute_policy_bel(p, life_table, interest_rate)
            for p in self.death_products
        )
        annuity_bel = sum(
            compute_policy_bel(p, life_table, interest_rate)
            for p in self.annuity_products
        )
        return {
            "death_bel": death_bel,
            "annuity_bel": annuity_bel,
            "total_bel": death_bel + annuity_bel,
        }

    def summary(self) -> str:
        """Portfolio summary: counts and totals by product type."""
        lines = [
            "Portfolio Summary",
            "=" * 50,
            f"Total policies: {len(self.policies)}",
            f"  Death products: {len(self.death_products)}",
            f"  Annuity products: {len(self.annuity_products)}",
            "",
        ]

        total_sa = sum(p.SA for p in self.death_products)
        total_pension = sum(p.annual_pension for p in self.annuity_products)
        lines.append(f"Total sum assured (death): ${total_sa:,.0f}")
        lines.append(f"Total annual pension (annuity): ${total_pension:,.0f}")

        lines.append("")
        lines.append(f"{'ID':>5} {'Type':>12} {'Issue':>6} {'Att':>5} "
                      f"{'Dur':>4} {'SA/Pension':>14}")
        lines.append("-" * 55)
        for p in self.policies:
            amount = f"${p.SA:,.0f}" if p.is_death_product else f"${p.annual_pension:,.0f}/yr"
            lines.append(
                f"{p.policy_id:>5} {p.product_type:>12} {p.issue_age:>6} "
                f"{p.attained_age:>5} {p.duration:>4} {amount:>14}"
            )

        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.policies)

    def __repr__(self) -> str:
        return (
            f"Portfolio({len(self.policies)} policies: "
            f"{len(self.death_products)} death, "
            f"{len(self.annuity_products)} annuity)"
        )


def create_sample_portfolio() -> Portfolio:
    """
    Create a sample Mexican insurance portfolio with 12 policies.

    Mix of whole life, term, endowment, and life annuity products
    at various ages and durations. Sums in MXN.

    This portfolio is designed to demonstrate SCR computation:
    - Death products generate mortality and catastrophe risk
    - Annuities generate longevity risk
    - All products generate interest rate risk
    - The mix creates diversification benefits
    """
    policies = [
        # Whole life policies (4)
        Policy("WL-01", "whole_life", issue_age=25, SA=2_000_000, duration=10),
        Policy("WL-02", "whole_life", issue_age=35, SA=1_500_000, duration=5),
        Policy("WL-03", "whole_life", issue_age=45, SA=1_000_000, duration=5),
        Policy("WL-04", "whole_life", issue_age=55, SA=500_000, duration=0),
        # Term policies (3)
        Policy("TM-05", "term", issue_age=30, SA=3_000_000, n=20, duration=5),
        Policy("TM-06", "term", issue_age=40, SA=2_000_000, n=20, duration=10),
        Policy("TM-07", "term", issue_age=50, SA=1_000_000, n=20, duration=3),
        # Endowment policies (2)
        Policy("EN-08", "endowment", issue_age=30, SA=1_500_000, n=20, duration=8),
        Policy("EN-09", "endowment", issue_age=40, SA=1_000_000, n=20, duration=5),
        # Life annuity policies (3)
        Policy("AN-10", "annuity", issue_age=60, annual_pension=120_000, duration=0),
        Policy("AN-11", "annuity", issue_age=65, annual_pension=150_000, duration=0),
        Policy("AN-12", "annuity", issue_age=70, annual_pension=100_000, duration=0),
    ]
    return Portfolio(policies)
