# Testing Strategy: Intuitive Reference

**Source files:** `backend/tests/` (19 files, 191 tests)

---

## Philosophy: Tests as Proof of Understanding

```
INTUITION
  Most test suites verify "does the code work?"
  SIMA's test suite verifies "does the code satisfy actuarial theory?"

  Every test has a THEORY docstring that states the mathematical property
  being tested. Reading the test suite is equivalent to reading a textbook
  on actuarial mathematics -- each test is a theorem with a computer-checked proof.
```

---

## The Three Rings of Testing

```
                    +-------------------+
                    |   Integration     |  test_integration_*.py
                    |   (full pipeline) |  test_api/*.py
                    +-------------------+
                    |   Module          |  test_lee_carter.py
                    |   (one engine)    |  test_graduation.py
                    +-------------------+
                    |   Formula         |  test_commutation.py
                    |   (one equation)  |  test_premiums_reserves.py
                    +-------------------+
```

**Formula tests** verify individual equations: `D_x = v^x * l_x`, `P = SA * M_x / N_x`, `q_omega = 1.0`.

**Module tests** verify that an entire engine module (e.g., Lee-Carter) produces correct output from correct input: identifiability constraints hold, synthetic data is recovered, RMSE is reasonable.

**Integration tests** verify the full pipeline end-to-end: raw data in, premium out; or HTTP request in, JSON out.

---

## What Makes a Good Actuarial Test?

```
FORMULA
  Good test:   "Reserve increases monotonically with duration"
  Bad test:    "Reserve at t=5 equals $47,382.18"

  Good test:   "sum(b_x) = 1" (identifiability constraint)
  Bad test:    "b_x[50] = 0.013666" (depends on data)

  Good test:   "Term premium < Whole life premium"
  Bad test:    "Whole life premium at age 40 = $10,765"

INTUITION
  Actuarial tests check PROPERTIES, not VALUES.
  Properties are universal truths that hold for ANY valid data.
  Values depend on the specific mortality table and interest rate.
```

---

## Data Strategy: Three Sources

```
ANALOGY
  1. Hand-verifiable CSV (mini_table.csv, 6 ages)
     Like checking arithmetic with a calculator.
     You can manually compute every D_x, N_x, premium.

  2. Real HMD data (USA, Spain, 1990-2020)
     Like running a clinical trial on real patients.
     Tests that the code handles messy, real-world data.

  3. Synthetic data (Gompertz, mock INEGI)
     Like testing a drug on lab-grown cells.
     Controlled conditions where you know the "right" answer.
```

The mini table is the most powerful for learning. With only 6 ages (60-65) and l_x = [1000, 850, 700, 550, 370, 200], you can verify every computation by hand:

```
Age  l_x    d_x    q_x
60   1000   150    0.150
61    850   150    0.176
62    700   150    0.214
63    550   180    0.327
64    370   170    0.459
65    200   200    1.000  <- terminal: everyone dies
```

---

## The THEORY Docstring Pattern

Every test function documents what actuarial property it verifies. This pattern has three benefits:

```
ROLE
  1. DOCUMENTATION -- "What does this test prove?"
  2. LEARNING      -- the test suite IS a study guide
  3. TRACEABILITY  -- each test maps to a formula

USE
  When preparing for an interview, read the THEORY docstrings.
  They explain:
    - The formula being tested
    - WHY it must hold (actuarial reasoning)
    - What would break if it failed
```

Example from `test_premiums_reserves.py`:

```
THEORY: tV = SA * A_{x+t} - P * a_due_{x+t}

Verify the formula by computing each component.
The reserve at duration t equals the future benefit minus future premiums,
both evaluated at the attained age x+t.
```

---

## Integration Tests: Why They Matter

```
INTUITION
  Unit tests verify individual bricks.
  Integration tests verify the building stands up.

  test_full_pipeline_produces_valid_premiums:
    HMD files -> MortalityData -> GraduatedRates -> LeeCarter
    -> MortalityProjection -> LifeTable -> CommutationFunctions
    -> PremiumCalculator -> premium is positive and < SA

  If this test passes, every module's output is compatible with
  the next module's input. The chain is unbroken.
```

The integration tests also verify **actuarial reasonableness**:

- Mortality improvement over time -> far-future premiums < near-future premiums
- CNSF table produces reasonable premiums at age 30 (< $100,000 for $1M SA)
- CNSF mortality > EMSSA mortality (general pop > insured pop)

These are domain-specific sanity checks that no amount of unit testing can replace.

---

## API Tests: Full Stack Verification

```
INTUITION
  API tests verify the ENTIRE stack:
    HTTP request -> Pydantic validation -> Router -> Service
    -> numpy conversion -> Engine computation -> JSON response

  They catch problems that unit tests miss:
    - numpy types that aren't JSON-serializable
    - Pydantic schema mismatches
    - Missing precomputed data at startup
    - CORS issues, route prefixes
```

The `conftest.py` creates a `TestClient` with `scope="module"` so the precomputed data (Lee-Carter fitting, Monte Carlo) is loaded once, not per-test.

---

## Coverage Matrix: What's Tested vs What's Not

```
TESTED (191 tests):
  [x] All 12 engine modules (a01 through a12)
  [x] Full HMD pipeline (USA, Spain)
  [x] Full Mexican pipeline (mock INEGI/CONAPO)
  [x] Regulatory table loading (CNSF, EMSSA)
  [x] 22 API endpoints
  [x] Portfolio CRUD operations
  [x] SCR: 4 risk modules + aggregation + solvency ratio
  [x] Error handling (invalid inputs)

NOT TESTED:
  [ ] Frontend (React components)
  [ ] Performance / load testing
  [ ] Real INEGI data (requires download)
  [ ] Concurrent API access
  [ ] Docker deployment
```

---

## Key Tests to Study for Interviews

| Test | File | Why It Matters |
|:-----|:-----|:--------------|
| `test_actuarial_identity` | `test_premiums_reserves.py` | Proves A_x + d*a_x = 1 (fundamental identity) |
| `test_reestimated_kt_matches_deaths` | `test_lee_carter.py` | Proves k_t re-estimation achieves death-matching |
| `test_synthetic_data_recovery` | `test_lee_carter.py` | Proves SVD correctly recovers known parameters |
| `test_mortality_improvement_lowers_premiums` | `test_integration_lee_carter.py` | Connects Lee-Carter projections to actuarial pricing |
| `test_aggregated_less_than_sum` | `test_scr.py` | Proves diversification benefit under correlation aggregation |
| `test_full_scr_pipeline` | `test_scr.py` | End-to-end: portfolio -> BEL -> 4 risks -> aggregation -> TP |

---

## Interview Q&A

**Q: If you had to add one more test, what would it be?**

A: A stress test for the `to_life_table()` bridge with extreme k_t values. The bridge converts projected m_x to q_x via `q_x = 1 - exp(-m_x)`. For very large m_x (e.g., m_x = 10), this should still produce q_x close to 1.0 without overflow. Currently the bridge is tested indirectly through integration tests, but a dedicated edge-case test would strengthen confidence.

**Q: How do you know the mock data produces realistic results?**

A: The mock data was generated using Gompertz-Makeham mortality (`mu(x) = A + B*c^x`) with an infant spike and young-adult hump, calibrated to approximate Mexican mortality patterns. The integration tests verify that this data flows through the entire pipeline and produces actuarially reasonable outputs (positive premiums, valid life tables, CNSF comparison ratios between 0.1 and 10).

**Q: Why not use property-based testing (Hypothesis)?**

A: The test suite already uses property-based assertions (e.g., "reserve is monotonically increasing" rather than exact values). Formal property-based testing with random generation would be valuable for the life table constructor (generating random l_x vectors and checking invariants), but the current approach of carefully chosen test cases with THEORY docstrings prioritizes educational value over exhaustive coverage.
