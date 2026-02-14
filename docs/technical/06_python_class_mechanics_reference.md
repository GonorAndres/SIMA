# Python Class Mechanics Reference

## Method Types

| Type | Decorator | First Param | Called On | Purpose |
|:-----|:----------|:------------|:----------|:--------|
| Instance method | (none) | `self` | Object | Access instance state |
| Class method | `@classmethod` | `cls` | Class | Alternative constructor |
| Static method | `@staticmethod` | (none) | Class | Utility, no state access |
| Property | `@property` | `self` | Object | Computed attribute |

## self vs cls

| Parameter | Refers To | Passed By |
|:----------|:----------|:----------|
| `self` | The specific instance | Python (automatically) |
| `cls` | The class itself | Python (automatically) |

```python
# self usage
def get_value(self):
    return self._value    # Access instance attribute

# cls usage
@classmethod
def from_csv(cls, path):
    return cls(data)      # Create instance of calling class
```

## Property Pattern

```python
# Read-only property
@property
def name(self) -> Type:
    return self._name

# Property with setter (validation)
@property
def value(self) -> float:
    return self._value

@value.setter
def value(self, v: float):
    if v < 0:
        raise ValueError("Must be positive")
    self._value = v
```

| Access Pattern | Method Called |
|:---------------|:--------------|
| `obj.name` | Getter (`@property`) |
| `obj.name = x` | Setter (`@name.setter`) |

## Dunder Methods

### Object Lifecycle

| Method | Trigger | Purpose |
|:-------|:--------|:--------|
| `__init__(self, ...)` | `Class(...)` | Initialize instance |
| `__new__(cls, ...)` | Before `__init__` | Create instance (rare) |
| `__del__(self)` | Deletion | Cleanup (rare) |
| `__repr__(self)` | `print()`, `repr()` | String representation |
| `__str__(self)` | `str()` | User-friendly string |

### Comparison

| Method | Trigger |
|:-------|:--------|
| `__eq__(self, other)` | `==` |
| `__ne__(self, other)` | `!=` |
| `__lt__(self, other)` | `<` |
| `__le__(self, other)` | `<=` |
| `__gt__(self, other)` | `>` |
| `__ge__(self, other)` | `>=` |

### Container

| Method | Trigger |
|:-------|:--------|
| `__len__(self)` | `len(obj)` |
| `__getitem__(self, key)` | `obj[key]` |
| `__setitem__(self, key, val)` | `obj[key] = val` |
| `__contains__(self, item)` | `item in obj` |
| `__iter__(self)` | `for x in obj` |

### Math Operations

| Method | Trigger |
|:-------|:--------|
| `__add__(self, other)` | `+` |
| `__sub__(self, other)` | `-` |
| `__mul__(self, other)` | `*` |
| `__truediv__(self, other)` | `/` |

### Callable

| Method | Trigger |
|:-------|:--------|
| `__call__(self, ...)` | `obj(...)` |

## F-String Format Specifiers

| Spec | Meaning | Example | Output |
|:-----|:--------|:--------|:-------|
| `>n` | Right-align, n width | `f"{42:>5}"` | `"   42"` |
| `<n` | Left-align, n width | `f"{42:<5}"` | `"42   "` |
| `^n` | Center, n width | `f"{42:^5}"` | `" 42 "` |
| `.nf` | n decimal places | `f"{3.14159:.2f}"` | `"3.14"` |
| `>n.mf` | Combined | `f"{3.14159:>8.2f}"` | `"    3.14"` |
| `,` | Thousand separator | `f"{1000:,}"` | `"1,000"` |

## Built-in Functions

### zip()

```python
zip(A, B)  # Pairs by position, stops at shortest
```

| A | B | zip(A, B) |
|:--|:--|:----------|
| `[60, 61, 62]` | `[1000, 900, 800]` | `[(60,1000), (61,900), (62,800)]` |

**Not** Cartesian product. Positional pairing only.

| Behavior | Function |
|:---------|:---------|
| Stop at shortest | `zip(A, B)` |
| Error if mismatch | `zip(A, B, strict=True)` |
| Pad with None | `itertools.zip_longest(A, B)` |

## Engine Module Reading Order

| Order | File | Depends On |
|:------|:-----|:-----------|
| 01 | `a01_life_table.py` | (foundation) |
| 02 | `a02_commutation.py` | a01 |
| 03 | `a03_actuarial_values.py` | a02 |
| 04 | `a04_premiums.py` | a02, a03 |
| 05 | `a05_reserves.py` | a02, a03, a04 |
