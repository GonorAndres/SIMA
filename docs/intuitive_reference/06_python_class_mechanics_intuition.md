# Python Class Mechanics - Mental Models

---

## self = "This Specific Object"

```
WHAT:       First parameter of every instance method
PASSED:     Automatically by Python
REFERS TO:  The specific object calling the method

ANALOGY:    Like "I" or "me" in human language
            When you say "my name", you mean YOUR name
            When object says "self.name", it means ITS name
```

```python
table_A.get_l(60)   # self = table_A
table_B.get_l(60)   # self = table_B (different object, different data)
```

---

## @classmethod + cls = "Factory with Inheritance"

```
WHAT:       Alternative way to create objects
WHY:        Different inputs than __init__ allows
cls:        The class that called (not hardcoded)

ANALOGY:    Pizza ordering
            - __init__: "Here are ingredients, make pizza"
            - from_menu(): "I want 'Margherita'" (look up ingredients)
            - from_csv(): "Read recipe from file" (parse, then make)
```

| Pattern | When to Use |
|:--------|:------------|
| `return cls(...)` | Respects inheritance (subclass gets subclass) |
| `return ClassName(...)` | Always same class (breaks inheritance) |

---

## @property = "Computed Attribute"

```
WHAT:       Method that looks like an attribute (no parentheses)
WHY:        - Compute on access (not stored)
            - Read-only protection
            - Hide implementation

ANALOGY:    Asking someone's age
            - They don't store "age" directly
            - They compute: current_year - birth_year
            - To you, it looks like simple data
```

```python
# Without @property
table.get_ages()      # Method call - needs ()

# With @property
table.ages            # Looks like attribute - cleaner
```

---

## @property + setter = "Validated Assignment"

```
PROBLEM:    Anyone can set obj.value = garbage
SOLUTION:   Intercept assignment, validate first

ANALOGY:    Bank teller
            - You can't write directly on the balance sheet
            - Teller checks if transaction is valid
            - Then updates (or rejects)
```

```
obj.rate = -0.5
    |
    v
setter runs
    |
    v
if rate < 0: raise Error  --> STOPS HERE
    |
    v
self._rate = value        (never reached if invalid)
```

**Rule:** Setter requires getter first (`@property` then `@name.setter`)

---

## Dunder Methods = "Python Syntax Hooks"

```
WHAT:       Special methods Python calls for built-in syntax
NAME:       "dunder" = double underscore (__name__)
WHY:        Your objects work like native types

TRANSLATION TABLE:
    You write       Python calls
    ----------      ------------
    print(obj)  --> obj.__repr__()
    len(obj)    --> obj.__len__()
    obj[key]    --> obj.__getitem__(key)
    obj == x    --> obj.__eq__(x)
    obj + x     --> obj.__add__(x)
```

```
ANALOGY:    Universal remote control
            - Press "power" --> TV knows what to do
            - Press "volume" --> TV responds appropriately
            - Dunder methods = buttons your class responds to
```

---

## zip() = "Walk Two Lists in Parallel"

```
NOT:        Cartesian product (all combinations)
IS:         Positional pairing (by index)

VISUAL:
    ages:    [60]----[61]----[62]
              |       |       |
    values: [1000]--[900]---[800]
              |       |       |
    zip:   (60,1000) (61,900) (62,800)
```

| Math Concept | Python |
|:-------------|:-------|
| Function f: A -> B | Dictionary |
| Ordered pairs {(a,b)} | `zip(A, B)` |
| Cartesian A x B | `itertools.product(A, B)` |

**Warning:** Unequal lengths silently drops extras. Validate first.

---

## F-String Alignment (Not Inequality!)

```
f"{value:>12.4f}"
        ^  ^ ^
        |  | +-- 4 decimal places
        |  +---- 12 characters wide
        +------- > means RIGHT align (not greater-than!)

SYMBOLS:
    >   right-align   f"{42:>5}" = "   42"
    <   left-align    f"{42:<5}" = "42   "
    ^   center        f"{42:^5}" = " 42  "
```

---

## N_x Person-Years - Multiple Intuitions

```
FORMULA:    N_x = D_x + D_{x+1} + ... + D_omega
            N_x = sum of discounted survivors from x to omega
```

| Mental Model | N_x Is... |
|:-------------|:----------|
| Economic | Present value of future person-years |
| Pool | Total contributions to annuity fund |
| Tickets | Discounted "survival tickets" from x onward |
| Liability | Insurer's cost for annuity to group |

```
INSIGHT:    D_x gives different "values" to different ages
            (older = less, due to discounting + mortality)

            BUT premium P stays constant each year

            HOW?    Equivalence principle balances:
                    - Young: low P, many payments
                    - Old: high P, few payments
                    - Both satisfy: APV(premiums) = APV(benefits)
```

---

## Engine Files Reading Order

```
a01_life_table       FOUNDATION
      |              l_x, d_x, q_x, p_x
      v
a02_commutation      ADDS TIME VALUE
      |              D_x, N_x, C_x, M_x
      v
a03_actuarial_values RATIOS
      |              A_x = M/D, a_x = N/D
      +------+
      |      |
      v      v
a04_premiums    a05_reserves
EQUIVALENCE     PROSPECTIVE
P = SA*M/N      tV = SA*A - P*a
```

**Focus per file:**
- 01: `__init__`, `_compute_derivatives()`, `@classmethod from_csv()`
- 02: `__init__` stores LifeTable, backward recursion in `_compute_N()`
- 03: All methods are simple ratios using `self.comm.get_X()`
- 04: Creates `self.av`, D_x cancels in formulas
- 05: Creates both `self.av` and `self.pc`, prospective formula
