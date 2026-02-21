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
from .a11_portfolio import Policy, Portfolio
from .a12_scr import compute_scr_mortality, compute_scr_longevity, compute_scr_interest_rate, compute_scr_catastrophe, run_full_scr

__all__ = [
    'LifeTable',
    'CommutationFunctions',
    'ActuarialValues',
    'PremiumCalculator',
    'ReserveCalculator',
    'MortalityData',
    'GraduatedRates',
    'LeeCarter',
    'MortalityProjection',
    'MortalityComparison',
    'Policy',
    'Portfolio',
    'compute_scr_mortality',
    'compute_scr_longevity',
    'compute_scr_interest_rate',
    'compute_scr_catastrophe',
    'run_full_scr',
]
