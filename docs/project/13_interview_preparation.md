# SIMA Interview Preparation Guide

## Key Numbers to Memorize

| Metric | Value | Context |
|--------|-------|---------|
| Explained variance (Mexico) | 77.7% | Lower than Spain (94.8%) due to demographic heterogeneity |
| Drift (pre-COVID) | -1.076/year | Mortality improving ~1% per year |
| Drift (full period) | -0.855/year | COVID slowed improvement by 20% |
| Spain drift | -2.89/year | 2.7x faster improvement than Mexico |
| SCR total | ~$568K | For sample portfolio |
| Diversification benefit | 14.4% | Mortality-longevity natural hedge |
| Interest rate SCR | 79.7% of total | Dominates because of long-duration discounting |
| BEL annuity share | 83% of total BEL | Annuities dominate liabilities |
| Interest rate premium spread | 101% | 2% to 8% on whole life age 40 |
| Mexico vs Spain premium gap | ~30% higher | Structural, all ages |
| COVID premium impact | +3-10% | Depends on age |
| Graduation roughness reduction | ~70% | Lambda = 10^5 |
| Tests | 238 | 205 unit + 33 API |
| Engine modules | 12 | a01 (LifeTable) through a12 (SCR) |
| API endpoints | 23 | Including compliance endpoint |

---

## Top 20 Interview Questions

### Mortality Modeling

1. **Why SVD instead of MLE for Lee-Carter?**
   SVD gives a closed-form solution: decompose the centered log-mortality matrix into a_x + b_x * k_t. MLE is iterative and can have convergence issues. SVD also naturally provides the rank-1 approximation that explains maximum variance. The tradeoff: SVD minimizes squared log-rate errors, while MLE maximizes the Poisson likelihood -- MLE is statistically more rigorous for count data.

2. **What happens if b_x has negative values?**
   The k_t re-estimation step (Brent's method) can fail because the death residual function becomes non-monotone (U-shaped). This happened with graduated Mexican data at ages 77, 78, 85. Solution: use adaptive bracket search or skip re-estimation (SVD k_t is consistent with the log-bilinear formulation).

3. **Why does Mexico have lower explained variance than Spain?**
   Mexico's mortality has more age-specific noise: the young-adult mortality hump (violence/accidents at ages 15-35), regional disparities, and the differentiated COVID impact. Spain's mortality follows a more regular Gompertz pattern with uniform improvement across ages.

4. **What is the graduation-reestimation incompatibility?**
   Whittaker-Henderson graduation can create negative b_x values (graduation inverts relative mortality at certain ages). The k_t re-estimation assumes b_x > 0 everywhere for monotonicity. Solution: either don't re-estimate k_t with graduated data, or use the adaptive bracket approach.

5. **How would you validate the Lee-Carter model?**
   (a) Explained variance > 70%, (b) k_t should be approximately linear (RWD assumption), (c) out-of-sample forecast comparison, (d) residual analysis (no systematic age or period patterns), (e) comparison against regulatory tables (CNSF, EMSSA).

### Pricing & Reserves

6. **What is the equivalence principle?**
   PV(premiums) = PV(benefits). The insurer charges exactly enough to cover expected claims. No profit loading in net premiums. The net premium is the minimum fair price.

7. **Why do reserves exist if premiums are fair?**
   Level premiums: same payment every year, but mortality risk increases with age. Early premiums exceed the current-year risk cost, building up a reserve. Later, premiums fall short of the risk cost, and the reserve is drawn down. At policy maturity, reserve = 0.

8. **How do commutation functions simplify premium formulas?**
   D_x = v^x * l_x absorbs both discounting and survivorship. N_x = sum of D from x to omega. M_x = sum of C from x to omega (where C_x = v^(x+1) * d_x). Then A_x = M_x/D_x, a_x = N_x/D_x, and P = SA * M_x/N_x. One division instead of a sum over all future ages.

9. **Why does interest rate dominate premium sensitivity?**
   Discounting compounds exponentially: v^t = 1/(1+i)^t. For a whole-life policy, you're discounting cash flows 40+ years into the future. A 1% change in i causes a v^40 change of ~33%. Mortality changes only affect the probability weights, which are much smaller in magnitude.

10. **What is the mortality-premium convexity?**
    +30% mortality shock -> +16.2% premium. -30% improvement -> -18.2% premium decrease. The asymmetry arises because q_x enters the premium formula nonlinearly (through the life table l_x = product of (1-q_x)). Improvements compound multiplicatively, producing larger effects than deteriorations.

### Capital Requirements (SCR/RCS)

11. **What is the SCR and why does it exist?**
    The Solvency Capital Requirement is the capital buffer an insurer must hold to absorb a 1-in-200-year loss event (VaR at 99.5%, 1-year horizon). It exists because insurance is a promise to pay in the future, and the insurer must have enough capital to honor that promise even under severe stress.

12. **How does the LISF/CUSF framework relate to Solvency II?**
    Mexico adopted Solvency II principles through the LISF (2013). The RCS = SCR. Technical provisions = BEL + risk margin. The CUSF specifies the standard formula parameters (shock levels, correlation matrices) adapted to the Mexican market. Key difference: Mexico uses official mortality tables (CNSF, EMSSA) that Europe doesn't have.

13. **Why is mortality-longevity correlation negative?**
    They are natural opposites: a pandemic (higher mortality) increases death claims but reduces annuity obligations (people die sooner). An insurer writing both product types has a natural hedge. The Solvency II standard correlation is -0.25.

14. **What does the 14.4% diversification benefit mean?**
    If you sum the four individual SCR components, you get X. But the correlation-aggregated SCR is 14.4% less than X. This is the capital saved by the natural hedge between mortality and longevity risk. It's why diversified insurers are more capital-efficient.

15. **How is the catastrophe shock calibrated?**
    COVID-calibrated: the Lee-Carter k_t reversed ~6.76 units above trend during 2020-2021. Conservative estimate: +35% one-year mortality spike at working ages. Unlike the permanent +15% mortality shock, catastrophe is a one-year spike affecting only first-year excess deaths.

### Architecture & Engineering

16. **Why FastAPI over Django/Flask?**
    Automatic Pydantic validation, async support, OpenAPI docs out of the box, type hints throughout. The actuarial engine returns dicts that map naturally to Pydantic models. Performance is adequate -- the bottleneck is computation, not I/O.

17. **How does the precomputed service work?**
    At startup, `load_all()` runs the full pipeline: INEGI data -> graduation -> Lee-Carter -> projection -> life table for each sex (male/female/unisex). Results are cached in module-level variables. API endpoints just read from the cache. This gives sub-millisecond response times for read endpoints.

18. **Why separate pipelines per sex?**
    Male and female mortality differ significantly: males have higher mortality at all ages, especially the young-adult hump (violence). Unisex uses "Total" INEGI data. Lee-Carter parameters (a_x, b_x, k_t) differ meaningfully between sexes -- fitting a single model would lose information.

19. **How does the to_life_table() bridge work?**
    MortalityProjection produces projected m_x (central death rates). Convert: q_x = 1 - exp(-m_x). Build l_x from q_x with a radix of 100,000. This produces a LifeTable that plugs directly into CommutationFunctions -> Premiums -> Reserves -> SCR. The bridge connects the empirical pipeline to the theoretical engine.

20. **What would you do differently in production?**
    (a) Per-user portfolio state (database, not global variable), (b) full yield curve for interest rate risk (not parallel shift), (c) lapse and expense risk modules, (d) operational risk, (e) policy-level underwriting adjustments, (f) full run-off risk margin (not simplified constant-SCR approach), (g) real-time data feeds from INEGI, (h) multi-decrement models.

---

## Architecture Decisions and Tradeoffs

| Decision | Rationale | Alternative |
|----------|-----------|-------------|
| SVD over MLE for Lee-Carter | Closed-form, stable, fast | MLE: better for count data, but iterative |
| Whittaker-Henderson over splines | Explicit fidelity-smoothness tradeoff, sparse matrices, O(n) | Splines: more flexible, but less interpretable |
| Precomputed cache over on-demand | Sub-ms response, predictable memory | On-demand: lower memory, but slower first request |
| Single life table per sex | Separates biological mortality patterns | Policy-level: more accurate, but requires underwriting data |
| Prospective reserve method | Standard, matches BEL definition | Retrospective: equivalent for net premiums, but harder to explain |
| Correlation aggregation over copulas | Standard formula, transparent | Copulas: more realistic tail dependence, but harder to calibrate |
