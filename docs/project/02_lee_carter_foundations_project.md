# Lee-Carter Foundations -- Session Log

## Actions

- Established m_x (central death rate) as the foundational observable for mortality modeling
- Explored the unit person-years and why it's the correct exposure measure
- Walked through the full Lee-Carter model: ln(m_{x,t}) = a_x + b_x * k_t
- Demonstrated SVD extraction of b_x and k_t from a 3-age x 4-year numerical example
- Traced the transformation chain: ln(m_x) -> m_x -> q_x and why each step exists
- Discussed edge cases where m_x > 1 and why the math remains valid

## Outputs

- `technical/07_lee_carter_foundations_reference.md` -- formulas, SVD procedure, transformation chain
- `intuitive_reference/07_lee_carter_foundations_intuition.md` -- mental models, analogies, key insights

## Chronology

* Definition of m_x and why it's preferred over q_x

We established that m_x = d_{x,t} / L_{x,t} (deaths divided by person-years of exposure) is the directly observable quantity from population data. Unlike q_x which requires assumptions about how deaths distribute within the year, m_x is a raw calculation from death certificates and census data. This makes it the natural starting point for any statistical model -- you model what you observe, then derive what you need.

We explored the unit "person-years" in depth: it's the product of persons and time observed, handling unequal observation windows (new policies, lapses, mid-year deaths) fairly. An insurance company's messy portfolio data reduces cleanly to person-years of exposure.

We worked through an edge case: 20 deaths from 100 people in one month at age 60, producing m_x = 2.667. This demonstrated that m_x is a rate (not a probability) and can exceed 1. The conversion q_x = 1 - exp(-m_x) = 0.93 remains valid regardless, since the exponential link guarantees q_x in (0,1) for any positive m_x.

* Lee-Carter model structure

We established the model ln(m_{x,t}) = a_x + b_x * k_t where a_x captures the average mortality shape by age, k_t is a single time index of mortality improvement, and b_x measures each age's sensitivity to that time trend. The key insight: all ages share one underlying trend, they just respond to it differently.

The logarithmic transformation was motivated by three needs: compressing data that spans 3-4 orders of magnitude, converting multiplicative mortality changes to additive shifts (a 10% improvement at any age shows the same log-shift), and guaranteeing positive rates upon back-transformation.

* SVD as the estimation method

We identified why OLS regression cannot estimate Lee-Carter: both b_x and k_t are unknown, making it a bilinear problem. SVD solves exactly this -- decomposing a matrix into the product of two lower-dimensional structures that minimize squared residuals (Eckart-Young theorem).

We walked through a numerical example (3 ages x 4 years): computed row means for a_x, subtracted to get residual matrix Z, applied SVD. The first singular value (sigma_1 = 0.358) was 60x larger than sigma_2 (0.006), capturing 99.9% of variance. The first left singular vector became b_x (age sensitivity), and sigma_1 times the first right singular vector became k_t (time index). After normalization (sum b_x = 1, sum k_t = 0), the parameters had clear demographic interpretation.

For detailed formulas see `technical/07_lee_carter_foundations_reference.md`.

* Transformation chain back to the actuarial engine

We traced how Lee-Carter output connects to the existing SIMA engine: ln(m_x) from the model -> exp() to recover m_x -> q_x = 1 - exp(-m_x) -> feeds into a01_life_table.py -> commutation functions -> premiums -> reserves. Each transformation narrows the range and guarantees validity for the next step.

This positions Lee-Carter as the first link in the actuarial chain, sitting before all existing Phase 2 code.
