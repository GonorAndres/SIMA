# Python Class Mechanics & Code Organization

## Actions

- Renamed backend engine files with numbered prefixes (a01-a05) for reading order
- Updated all import statements across engine modules and test files
- Added interest rate validation to CommutationFunctions.__init__
- Discussed Python class mechanics: self, __init__, @classmethod, @property, dunder methods
- Clarified N_x person-years concept and equivalence principle balance

## Outputs

- `backend/engine/a01_life_table.py` (renamed from life_table.py)
- `backend/engine/a02_commutation.py` (renamed, added validation)
- `backend/engine/a03_actuarial_values.py` (renamed)
- `backend/engine/a04_premiums.py` (renamed)
- `backend/engine/a05_reserves.py` (renamed)
- Updated `backend/engine/__init__.py`
- Updated test files with new import paths
- Updated `.claude/CLAUDE.md` with reading order section

## Chronology

* File Renaming for Learning Order

We renamed all engine module files from `life_table.py`, `commutation.py`, etc. to `a01_life_table.py`, `a02_commutation.py`, etc. This establishes a clear reading order based on dependency flow. We used the `a` prefix because Python imports cannot start with digits. The order reflects how each module builds on previous ones: life_table (foundation) -> commutation (adds interest) -> actuarial_values (ratios) -> premiums (equivalence) -> reserves (prospective method).

The task required updating all import statements in engine modules, __init__.py, and test files. Imports verified successful.

* Interest Rate Validation

We added input validation to `CommutationFunctions.__init__` in a02_commutation.py. The validation checks: (1) interest_rate is a number, (2) not negative, (3) not greater than 1 (likely user error - should be decimal like 0.05). This prevents silent failures where invalid rates would produce nonsense calculations. For detailed formulas see 02_equivalence_premiums_reserves_reference.md.

* Python Class Mechanics Discussion

We covered core Python OOP concepts for interview preparation:

| Concept | Purpose |
|---------|---------|
| `self` | Reference to instance, passed automatically |
| `__init__` | Constructor - initializes object state |
| `@classmethod` | Alternative constructor (factory pattern) |
| `cls` | Reference to class itself (for inheritance) |
| `@property` | Method that behaves like attribute |
| `@property.setter` | Validation on assignment |
| Dunder methods | Hooks for Python syntax (`__repr__`, `__len__`, etc.) |

Key insight: `@classmethod` + `cls` provides two orthogonal benefits - alternative input formats AND proper inheritance support.

* N_x Person-Years Intuition

We explored multiple mental models for understanding N_x:

1. Present value of all future person-years from age x
2. Total expected contributions to an annuity pool
3. "Discounted survival tickets" from x to omega
4. Insurer's liability for life annuity to group

Key insight discussed: D_x implicitly assigns different "values" to different ages, but the equivalence principle ensures premium calculations remain fair - younger people pay lower annual premiums for more years, older people pay higher premiums for fewer years. The math balances so APV(premiums) = APV(benefits) for everyone.

For detailed formulas see 05_commutation_deep_insights_reference.md.
