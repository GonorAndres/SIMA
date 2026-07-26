# SIMA Actuarial Engine
# Core calculation modules for life insurance valuations

from .a01_life_table import LifeTable
from .a02_commutation import CommutationFunctions
from .a03_actuarial_values import ActuarialValues
from .a04_premiums import PremiumCalculator
from .a05_reserves import ReserveCalculator
from .a06_mortality_data import MortalityData
from .a07_graduation import GraduatedRates
from .a08_lee_carter import LeeCarter
from .a09_projection import MortalityProjection
from .a10_validation import MortalityComparison
from .a11_portfolio import Policy, Portfolio, portfolio_remaining_duration
from .a12_scr import (
    calibrate_shocks_from_lee_carter,
    compute_scr_catastrophe,
    compute_scr_interest_rate,
    compute_scr_longevity,
    compute_scr_mortality,
    run_full_scr,
)

__all__ = [
    "ActuarialValues",
    "CommutationFunctions",
    "GraduatedRates",
    "LeeCarter",
    "LifeTable",
    "MortalityComparison",
    "MortalityData",
    "MortalityProjection",
    "Policy",
    "Portfolio",
    "PremiumCalculator",
    "ReserveCalculator",
    "calibrate_shocks_from_lee_carter",
    "compute_scr_catastrophe",
    "compute_scr_interest_rate",
    "compute_scr_longevity",
    "compute_scr_mortality",
    "portfolio_remaining_duration",
    "run_full_scr",
]
