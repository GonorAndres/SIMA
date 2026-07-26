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

Optional Gross-Premium Hooks (Net-Premium by Default):
------------------------------------------------------
Each policy can carry optional ``expense_loading``, ``lapse_rate`` and
``commission`` fields. They default to no-op values (0.0 expense, 0.0
lapse, 0.0 commission) so the engine remains a NET-premium BEL engine;
they exist purely as a stable API surface so future gross-premium work
can attach assumptions without changing the constructor signature or
breaking downstream callers. They are NOT used by the current BEL/SCR
pipeline.

LISF Compliance:
---------------
Mexican regulation (LISF Art. 217, CUSF) requires insurers to compute
BEL as the present value of future obligations less future premium income,
using best-estimate mortality assumptions and risk-free discount rates.
"""

from __future__ import annotations

import warnings
from typing import ClassVar

from .a01_life_table import LifeTable
from .a02_commutation import CommutationFunctions
from .a03_actuarial_values import ActuarialValues
from .a04_premiums import PremiumCalculator
from .a05_reserves import ReserveCalculator
from .exceptions import ActuarialValidationError
from .validators import (
    validate_non_negative_amount,
    validate_term_bounds,
)


def _validate_int(value: object, name: str, *, minimum: int | None = None) -> None:
    """Validate that ``value`` is a plain integer (not a bool) in range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ActuarialValidationError(
            f"{name} must be an integer (got {type(value).__name__})",
            field=name,
            constraint=f"{name}: int",
        )
    if minimum is not None and value < minimum:
        raise ActuarialValidationError(
            f"{name} cannot be below {minimum} (got {value})",
            field=name,
            constraint=f"{name} >= {minimum}",
        )


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
        expense_loading: Optional fractional expense loading (no-op default).
        lapse_rate: Optional annual lapse rate (no-op default).
        commission: Optional fractional commission (no-op default).
    """

    DEATH_PRODUCTS: ClassVar[frozenset[str]] = frozenset({"whole_life", "term", "endowment"})
    ANNUITY_PRODUCTS: ClassVar[frozenset[str]] = frozenset({"annuity"})
    VALID_PRODUCTS: ClassVar[frozenset[str]] = DEATH_PRODUCTS | ANNUITY_PRODUCTS

    def __init__(
        self,
        policy_id: str,
        product_type: str,
        issue_age: int,
        SA: float = 0.0,
        annual_pension: float = 0.0,
        n: int | None = None,
        duration: int = 0,
        *,
        expense_loading: float = 0.0,
        lapse_rate: float = 0.0,
        commission: float = 0.0,
        annual_premium: float | None = None,
    ):
        if product_type not in self.VALID_PRODUCTS:
            raise ValueError(
                f"Unknown product_type '{product_type}'. "
                f"Must be one of: {sorted(self.VALID_PRODUCTS)}"
            )

        if product_type in ("term", "endowment") and n is None:
            raise ValueError(f"{product_type} requires n (term length)")

        # Structural integer validation -- raises ActuarialValidationError.
        _validate_int(issue_age, "issue_age", minimum=0)
        _validate_int(duration, "duration", minimum=0)
        if n is not None:
            _validate_int(n, "n", minimum=0)

        # Non-negative monetary amounts (engines assert these downstream too,
        # but validating at the boundary catches construction-time bugs).
        validate_non_negative_amount(float(SA), "SA")
        validate_non_negative_amount(float(annual_pension), "annual_pension")

        # Optional gross-premium / lapse hooks. Currently informational only;
        # validated for shape so a downstream consumer can rely on them.
        validate_non_negative_amount(float(expense_loading), "expense_loading")
        validate_non_negative_amount(float(lapse_rate), "lapse_rate")
        validate_non_negative_amount(float(commission), "commission")
        if annual_premium is not None:
            validate_non_negative_amount(float(annual_premium), "annual_premium")
        if lapse_rate > 1.0:
            raise ActuarialValidationError(
                f"lapse_rate must be a probability in [0,1] (got {lapse_rate})",
                field="lapse_rate",
                constraint="0 <= lapse_rate <= 1",
            )

        # Cross-field rule: duration <= n for finite-horizon products. We keep
        # this as a construction-time warning (an "expired" policy is still a
        # legal object -- the SCR engine explicitly models expired policies
        # -- but constructing one with duration>n for endowment/term is almost
        # always a data mistake).
        if product_type in ("term", "endowment") and n is not None and duration > n:
            warnings.warn(
                f"Policy {policy_id!r} ({product_type}, term {n}) constructed with "
                f"duration={duration} > n -- it is expired/matured.",
                UserWarning,
                stacklevel=2,
            )

        self.policy_id = policy_id
        self.product_type = product_type
        self.issue_age = issue_age
        self.SA = float(SA)
        self.annual_pension = float(annual_pension)
        self.n = n
        self.duration = duration
        # No-op hook fields (see class docstring).
        self.expense_loading = float(expense_loading)
        self.lapse_rate = float(lapse_rate)
        self.commission = float(commission)
        self.annual_premium = None if annual_premium is None else float(annual_premium)

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

    @property
    def remaining_term(self) -> int | None:
        """Remaining cover years for finite-horizon products, else None."""
        if self.product_type in ("term", "endowment") and self.n is not None:
            return max(self.n - self.duration, 0)
        return None

    @property
    def is_expired(self) -> bool:
        """True once a finite policy has no unpaid contractual benefit."""
        if self.n is None:
            return False
        if self.product_type == "term":
            return self.duration >= self.n
        if self.product_type == "endowment":
            return self.duration > self.n
        return False

    @property
    def is_matured(self) -> bool:
        """True for an endowment exactly at its benefit-payment duration."""
        return self.product_type == "endowment" and self.n is not None and self.duration == self.n

    def __repr__(self) -> str:
        if self.is_death_product:
            return (
                f"Policy({self.policy_id}, {self.product_type}, "
                f"age={self.issue_age}, SA={self.SA:,.0f}, dur={self.duration})"
            )
        return (
            f"Policy({self.policy_id}, annuity, "
            f"age={self.issue_age}, pension={self.annual_pension:,.0f}, "
            f"dur={self.duration})"
        )


def resolve_policy_annual_premium(
    policy: Policy,
    comm: CommutationFunctions,
) -> float | None:
    """Return the contractual annual premium for a death policy.

    A premium explicitly stored on the policy takes precedence. Otherwise it
    is derived once from the supplied issue basis. SCR callers must resolve it
    from the base basis and pass it unchanged into stressed BEL calculations.
    """
    if not policy.is_death_product:
        return None
    if policy.annual_premium is not None:
        return policy.annual_premium
    pc = PremiumCalculator(comm)
    if policy.product_type == "whole_life":
        return pc.whole_life(policy.SA, policy.issue_age)
    assert policy.n is not None
    if policy.product_type == "term":
        return pc.term(policy.SA, policy.issue_age, policy.n)
    return pc.endowment(policy.SA, policy.issue_age, policy.n)


def compute_policy_bel(
    policy: Policy,
    life_table: LifeTable,
    interest_rate: float,
    comm: CommutationFunctions | None = None,
    annual_premium: float | None = None,
) -> float:
    """
    Compute BEL for a single policy.

    For death products: BEL = prospective reserve at current duration.
    For annuities: BEL = annual_pension * a_due(attained_age).

    Expired/matured finite-horizon policies have BEL = 0 by definition
    (no future benefits owed, no future premiums due).

    Args:
        policy: The Policy instance
        life_table: Mortality table to use (best-estimate)
        interest_rate: Risk-free discount rate
        comm: Optional shared CommutationFunctions instance (performance)

    Returns:
        BEL amount (float)
    """
    if comm is None:
        comm = CommutationFunctions(life_table, interest_rate=interest_rate)

    # Expired term / already-paid endowment: no future obligation. An
    # endowment exactly at maturity still carries the benefit immediately due.
    if policy.is_expired:
        return 0.0

    if policy.is_death_product:
        rc = ReserveCalculator(comm)
        contractual_premium = (
            resolve_policy_annual_premium(policy, comm)
            if annual_premium is None
            else annual_premium
        )
        if policy.product_type == "whole_life":
            return rc.reserve_whole_life(
                SA=policy.SA,
                x=policy.issue_age,
                t=policy.duration,
                annual_premium=contractual_premium,
            )
        elif policy.product_type == "term":
            assert policy.n is not None  # validated at construction (term requires n)
            return rc.reserve_term(
                SA=policy.SA,
                x=policy.issue_age,
                n=policy.n,
                t=policy.duration,
                annual_premium=contractual_premium,
            )
        elif policy.product_type == "endowment":
            assert policy.n is not None  # validated at construction
            return rc.reserve_endowment(
                SA=policy.SA,
                x=policy.issue_age,
                n=policy.n,
                t=policy.duration,
                annual_premium=contractual_premium,
            )
    else:
        # Annuity: BEL = pension * a_due(attained_age)
        av = ActuarialValues(comm)
        return policy.annual_pension * av.a_due(policy.attained_age)

    # Should be unreachable due to construction-time product_type validation.
    raise ActuarialValidationError(
        f"Unsupported product_type {policy.product_type!r} reached BEL computation",
        field="product_type",
        constraint="product_type in DEATH_PRODUCTS | ANNUITY_PRODUCTS",
    )


def policy_remaining_horizon(
    policy: Policy,
    life_table: LifeTable,
    interest_rate: float,
) -> float:
    """
    Estimate the remaining actuarial horizon (years) for a single policy.

    For term / endowment: the contractual remaining term ``n - duration``
    (clamped at 0).

    For whole life / annuity: the undiscounted curtate expectation of life at
    attained age, ``sum_{k>=1} k_p_x``, computed directly from survivor counts.
    """
    if policy.is_expired or policy.is_matured:
        return 0.0

    if policy.product_type in ("term", "endowment") and policy.n is not None:
        return float(max(policy.n - policy.duration, 0))

    # Whole life / annuity: undiscounted curtate expectation of life,
    # e_x = sum_{k>=1} k_p_x. The policy is already known to be in force at
    # attained age, so survival is conditional from that age.
    attained = policy.attained_age
    if attained > life_table.max_age:
        return 0.0
    l_attained = life_table.get_l(attained)
    if l_attained <= 0:
        return 0.0
    return float(
        sum(
            life_table.get_l(age) / l_attained
            for age in range(attained + 1, life_table.max_age + 1)
        )
    )


def portfolio_remaining_duration(
    portfolio: Portfolio,
    life_table: LifeTable,
    interest_rate: float,
) -> float:
    """
    BEL-weighted average remaining horizon of the portfolio in years.

    Used by the SCR risk-margin computation to replace the previous
    hardcoded ``portfolio_duration = 15`` constant with a portfolio-specific
    figure. Degenerate portfolios (zero BEL, all expired) return 0.0.
    """
    total_bel = 0.0
    weighted = 0.0
    for p in portfolio.policies:
        bel = compute_policy_bel(p, life_table, interest_rate)
        horizon = policy_remaining_horizon(p, life_table, interest_rate)
        total_bel += bel
        weighted += bel * horizon
    if total_bel <= 0.0:
        # No liability -> the duration is undefined; fall back to the simple
        # average of in-force remaining horizons (or 0 if none in force).
        horizons = [
            policy_remaining_horizon(p, life_table, interest_rate)
            for p in portfolio.policies
            if not p.is_expired
        ]
        return float(sum(horizons) / len(horizons)) if horizons else 0.0
    return weighted / total_bel


class Portfolio:
    """
    A collection of insurance policies.

    Provides filtering (death vs annuity), aggregate BEL computation,
    and per-policy breakdown.
    """

    def __init__(self, policies: list[Policy]):
        self.policies = list(policies)
        self._validate_unique_ids()

    def _validate_unique_ids(self) -> None:
        seen: set[str] = set()
        for p in self.policies:
            if p.policy_id in seen:
                raise ActuarialValidationError(
                    f"Duplicate policy_id {p.policy_id!r} in portfolio",
                    field="policy_id",
                    constraint="policy_id unique within a Portfolio",
                )
            seen.add(p.policy_id)

    def validate_non_empty(self) -> None:
        """Require at least one policy for BEL or SCR calculations."""
        if not self.policies:
            raise ActuarialValidationError(
                "Portfolio must contain at least one policy for BEL/SCR computation",
                field="portfolio",
                constraint="len(portfolio.policies) > 0",
            )

    @property
    def death_products(self) -> list[Policy]:
        """All death-benefit policies (whole_life, term, endowment)."""
        return [p for p in self.policies if p.is_death_product]

    @property
    def annuity_products(self) -> list[Policy]:
        """All annuity policies."""
        return [p for p in self.policies if p.is_annuity]

    def validate_against_life_table(self, life_table: LifeTable) -> None:
        """
        Cross-validate every in-force policy against a life table.

        Ensures the attained age fits inside ``[min_age, max_age]`` and
        that finite-horizon durations are within ``n``. Expired policies
        (``duration >= n``) are accepted and skipped silently.
        """
        min_age, max_age = life_table.min_age, life_table.max_age
        for p in self.policies:
            if p.is_expired:
                continue
            if p.attained_age < min_age or p.attained_age > max_age:
                raise ActuarialValidationError(
                    f"Policy {p.policy_id!r} attained age {p.attained_age} is outside "
                    f"the life table range [{min_age}, {max_age}]",
                    field="attained_age",
                    constraint=f"min_age <= attained_age <= max_age ({max_age})",
                )
            validate_term_bounds(
                p.n if p.product_type in ("term", "endowment") else None,
                t=p.duration,
                product_type=p.product_type if p.product_type != "annuity" else "whole_life",
            )

    def compute_bel(self, life_table: LifeTable, interest_rate: float) -> float:
        """
        Total BEL for the entire portfolio.

        Args:
            life_table: Best-estimate mortality table
            interest_rate: Risk-free discount rate

        Returns:
            Aggregate BEL (sum of individual policy BELs)
        """
        self.validate_non_empty()
        self.validate_against_life_table(life_table)
        comm = CommutationFunctions(life_table, interest_rate=interest_rate)
        return sum(
            compute_policy_bel(p, life_table, interest_rate, comm=comm) for p in self.policies
        )

    def compute_bel_breakdown(
        self, life_table: LifeTable, interest_rate: float
    ) -> list[dict[str, object]]:
        """
        Per-policy BEL breakdown.

        Returns:
            List of dicts with policy details and individual BEL.
        """
        self.validate_non_empty()
        self.validate_against_life_table(life_table)
        breakdown = []
        comm = CommutationFunctions(life_table, interest_rate=interest_rate)
        for p in self.policies:
            bel = compute_policy_bel(p, life_table, interest_rate, comm=comm)
            entry: dict[str, object] = {
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

    def compute_bel_by_type(self, life_table: LifeTable, interest_rate: float) -> dict[str, float]:
        """
        BEL split by product category: death vs annuity.

        Returns:
            Dict with "death_bel", "annuity_bel", "total_bel".
        """
        self.validate_non_empty()
        self.validate_against_life_table(life_table)
        comm = CommutationFunctions(life_table, interest_rate=interest_rate)
        death_bel = sum(
            compute_policy_bel(p, life_table, interest_rate, comm=comm) for p in self.death_products
        )
        annuity_bel = sum(
            compute_policy_bel(p, life_table, interest_rate, comm=comm)
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
        lines.append(
            f"{'ID':>5} {'Type':>12} {'Issue':>6} {'Att':>5} {'Dur':>4} {'SA/Pension':>14}"
        )
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
