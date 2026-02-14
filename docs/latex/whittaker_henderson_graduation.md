# Whittaker-Henderson Graduation: From Bending Rods to Smooth Mortality

---

## Notation and Conventions

| Symbol | Meaning |
|:-------|:--------|
| $m_x$ | Observed mortality rate at age $x$ |
| $g_x$ | Graduated (smoothed) mortality rate at age $x$ |
| $w_x$ | Weight assigned to age $x$ (trust in that observation) |
| $\lambda$ | Smoothing parameter (controls fit vs smoothness tradeoff) |
| $z$ | Difference order (what "smooth" means) |
| $D$ | Difference matrix (computes all $z$-th differences at once) |
| $W$ | Diagonal weight matrix with $w_x$ on the diagonal |
| $n$ | Number of ages in the data |

---

## The Problem: Why Smooth?

> **[FORMAL]** The Smoothing Problem
>
> Observed $m_x$ is a noisy realization of unknown true mortality $\mu_x$:
> $$m_x = \mu_x + \text{noise}_x$$
> **Goal:** estimate $\mu_x$ from $m_x$ by removing noise while preserving signal.

> **[INTUITION]** Drawing Through Dots
>
> You have 101 scatter dots on a page (one per age). Some jump around wildly -- especially at old ages where populations are tiny and a single extra death swings the rate. If you were drawing by hand, you would sketch a smooth curve that follows the overall trend but ignores the individual bumps. Graduation teaches a computer to do the same thing.

> **[APPLICATION]** Why Lee-Carter Needs This
>
> - $\ln(0) = -\infty$: zeros in the mortality data crash the log transform entirely.
> - Even without zeros: noisy old-age rates corrupt the SVD decomposition. Noise looks like signal to the algorithm, and it ends up embedded in $b_x$ and $k_t$.
> - Smoother input leads to cleaner, more interpretable Lee-Carter parameters.

---

## Finite Differences: Measuring Roughness

> **[FORMAL]** Definitions
>
> $$\Delta^1 g_x = g_{x+1} - g_x$$
> $$\Delta^2 g_x = g_{x+2} - 2\,g_{x+1} + g_x$$
> $$\Delta^3 g_x = g_{x+3} - 3\,g_{x+2} + 3\,g_{x+1} - g_x$$

> **[INTUITION]** Geometric Meaning
>
> **FIRST DIFFERENCE = SLOPE**
>
> "How steep is the climb at this step?"
>
> Walking uphill: the slope tells you how hard each step is. If all first differences are zero, you are on a flat horizontal line.
>
> **SECOND DIFFERENCE = CURVATURE**
>
> "How much is the road turning?"
>
> Driving a car: the second difference is the steering wheel angle. Zero means a straight road. Positive means curving one way. Negative means curving the other. If all second differences are zero, you are on a straight line (constant slope).
>
> **THIRD DIFFERENCE = JERK (rate of change of curvature)**
>
> "How quickly does the road go from straight to curving?"
>
> A gentle highway on-ramp vs a sharp sudden turn. If all third differences are zero, you are on a parabola (constant curvature).
>
> | $\Delta^z = 0$ everywhere | Resulting curve |
> |:--------------------------|:---------------|
> | $z = 1$ | Horizontal line (constant) |
> | $z = 2$ | Straight line (linear) |
> | $z = 3$ | Parabola (quadratic) |
>
> Penalizing $\Delta^z$ forces the curve to be "locally almost" a degree $z-1$ polynomial.

> **[INTUITION]** Connection to Taylor Polynomials
>
> From Taylor expansion:
> $$f(x+h) \approx f(x) + f'(x)\,h + \frac{f''(x)}{2}\,h^2 + \cdots$$
>
> Rearranging:
> $$f''(x) \approx \frac{f(x+h) - 2f(x) + f(x-h)}{h^2}$$
>
> The second difference IS the discrete second derivative (times $h^2$). So:
> - Penalizing second differences $\approx$ penalizing curvature.
> - Penalizing third differences $\approx$ penalizing rate of change of curvature.
>
> Whittaker-Henderson uses the discrete version of what calculus does with derivatives.

> **[APPLICATION]** Why $z=3$ for Mortality
>
> Mortality has genuine curvature -- it rises with age, and it rises faster at older ages. Using $z=2$ would penalize this natural curvature, fighting against biology. Using $z=3$ allows curvature but penalizes sudden changes in curvature -- which IS the noise signature.

---

## The Objective Function

> **[FORMAL]** The Optimization Problem
>
> $$\min_{g} \quad F + \lambda \cdot S$$
>
> where:
>
> $$F = \sum_x w_x\,(g_x - m_x)^2 \qquad \text{(fidelity -- stay near data)}$$
>
> $$S = \sum_x \left(\Delta^z g_x\right)^2 \qquad \text{(smoothness -- don't wiggle)}$$

> **[INTUITION]** The Spring and Rod
>
> Imagine a physical device:
> - A **flexible metal rod** is the graduated curve.
> - **101 springs**, one per age, pull the rod toward observed $m_x$.
> - Spring strength = $w_x$. More exposure at that age means a stronger spring means more trust.
> - Rod stiffness = $\lambda$.
>
> ```
> observed:    *        *     *
>              |        |     |    <-- springs pull toward data
>              |   *    |     |
> rod:    ~~~~~~~~~~~~~~~~~~~~~~~~  <-- flexible rod resists bending
>                  |
>                  *
> ```
>
> - $\lambda$ small: soft rod, follows every spring, noisy result.
> - $\lambda$ large: stiff rod, ignores weak springs, over-smooth result.
> - Right $\lambda$: follows strong springs (reliable ages), smooths past weak ones (noisy ages).
>
> The equilibrium position of the rod is the graduated curve. The total energy (spring tension + bending energy) is minimized.

> **[INTUITION]** Audio Filter Perspective
>
> - Observed mortality = biological signal + sampling noise.
> - Graduation = low-pass filter.
> - $z$ = frequency cutoff (what counts as "high frequency noise").
> - $\lambda$ = filter aggressiveness.
>
> Like removing static from a voice recording without distorting the speech.

> **[APPLICATION]** Choosing $\lambda$ for Mortality
>
> Typical range: 1 to 10,000.
> - Too small: keeps noise, SVD picks up artifacts in $b_x$.
> - Too large: smooths away the accident hump at ages 18--25 (a real feature for males).
> - Selection methods: cross-validation or actuarial judgment.

---

## The Difference Matrix $D$

> **[FORMAL]** Construction
>
> For $z=2$, $n=5$ ages:
>
> $$D = \begin{bmatrix} 1 & -2 & 1 & 0 & 0 \\ 0 & 1 & -2 & 1 & 0 \\ 0 & 0 & 1 & -2 & 1 \end{bmatrix} \qquad \text{shape: } (n-z) \times n = 3 \times 5$$
>
> For $z=3$, $n=6$ ages:
>
> $$D = \begin{bmatrix} 1 & -3 & 3 & -1 & 0 & 0 \\ 0 & 1 & -3 & 3 & -1 & 0 \\ 0 & 0 & 1 & -3 & 3 & -1 \end{bmatrix} \qquad \text{shape: } (n-z) \times n = 3 \times 6$$
>
> **Pattern:** each row contains binomial coefficients with alternating signs, shifted one position to the right. The coefficients for order $z$ are:
>
> $$(-1)^k \binom{z}{k} \quad \text{for } k = 0, 1, \ldots, z$$

> **[DIMENSION CHECK]**
>
> | Object | Dimensions | Notes |
> |:-------|:-----------|:------|
> | $D$ | $(n-z) \times n$ | Each row computes one $z$-th difference |
> | $\mathbf{g}$ | $n \times 1$ | Vector of graduated rates |
> | $D\mathbf{g}$ | $(n-z) \times 1$ | Vector of all $z$-th differences |
> | $D^\top D$ | $n \times n$ | Penalty matrix (symmetric, banded) |
> | $W$ | $n \times n$ | Diagonal weight matrix |
> | $W + \lambda D^\top D$ | $n \times n$ | System matrix (symmetric, positive definite) |

> **[INTUITION]** What $D$ Does
>
> Each row of $D$ computes one finite difference at one age. Multiplying $D\mathbf{g}$ gives ALL the differences at once as a single matrix-vector product. Then $D^\top D\,\mathbf{g}$ computes each point's total contribution to roughness, spreading the penalty to its neighbors through the transpose.

---

## The Closed-Form Solution

> **[FORMAL]** Derivation
>
> Write the total objective in matrix form:
>
> $$\text{Total} = (\mathbf{g} - \mathbf{m})^\top W (\mathbf{g} - \mathbf{m}) + \lambda\,\mathbf{g}^\top D^\top D\,\mathbf{g}$$
>
> Take the derivative with respect to $\mathbf{g}$ and set to zero:
>
> $$2\,W(\mathbf{g} - \mathbf{m}) + 2\,\lambda\,D^\top D\,\mathbf{g} = \mathbf{0}$$
>
> $$(W + \lambda\,D^\top D)\,\mathbf{g} = W\,\mathbf{m}$$
>
> **Solution:**
>
> $$\boxed{\mathbf{g} = (W + \lambda\,D^\top D)^{-1}\,W\,\mathbf{m}}$$
>
> A unique solution exists whenever $W$ has at least $z$ positive diagonal entries.

> **[INTUITION]** This IS Regularized Regression
>
> Compare the two systems side by side:
>
> | Method | Normal equation |
> |:-------|:---------------|
> | Ridge regression | $(X^\top X + \lambda I)\,\boldsymbol{\beta} = X^\top \mathbf{y}$ |
> | WH graduation | $(W + \lambda\,D^\top D)\,\mathbf{g} = W\,\mathbf{m}$ |
>
> Same structure: data term plus penalty term. Ridge penalizes coefficient magnitude. WH penalizes roughness. Both are regularization -- accepting a small bias in exchange for a large reduction in variance.

> **[APPLICATION]** Computational Efficiency
>
> $(W + \lambda\,D^\top D)$ is banded -- only $2z+1$ diagonals are nonzero. This means it can be solved in $O(n)$ time using banded Cholesky or LU solvers. For 101 ages: essentially instant, even on modest hardware.

---

## Worked Example (5 Ages)

We walk through every computation with concrete numbers.

**Setup:**
- $\mathbf{m} = [0.010,\; 0.015,\; 0.012,\; 0.018,\; 0.020]$
- $z = 2$, $\lambda = 10$, $W = I$ (equal trust in all ages)

### Step 1: Build the Difference Matrix $D$

For $z=2$, $n=5$:

$$D = \begin{bmatrix} 1 & -2 & 1 & 0 & 0 \\ 0 & 1 & -2 & 1 & 0 \\ 0 & 0 & 1 & -2 & 1 \end{bmatrix}$$

### Step 2: Compute $D^\top D$

$$D^\top D = \begin{bmatrix} 1 & -2 & 1 & 0 & 0 \\ -2 & 5 & -4 & 1 & 0 \\ 1 & -4 & 6 & -4 & 1 \\ 0 & 1 & -4 & 5 & -2 \\ 0 & 0 & 1 & -2 & 1 \end{bmatrix}$$

Notice the symmetry, the banded structure (bandwidth $2z+1 = 5$), and how the largest values sit on the diagonal.

### Step 3: Form the System Matrix $(I + 10\,D^\top D)$

$$I + 10\,D^\top D = \begin{bmatrix} 11 & -20 & 10 & 0 & 0 \\ -20 & 51 & -40 & 10 & 0 \\ 10 & -40 & 61 & -40 & 10 \\ 0 & 10 & -40 & 51 & -20 \\ 0 & 0 & 10 & -20 & 11 \end{bmatrix}$$

### Step 4: Solve the Linear System

We need $\mathbf{g}$ such that:

$$(I + 10\,D^\top D)\,\mathbf{g} = \mathbf{m}$$

This is a $5 \times 5$ banded symmetric positive definite system. Using a numerical solver:

### Step 5: Result

$$\mathbf{g} \approx [0.0116,\; 0.0136,\; 0.0150,\; 0.0170,\; 0.0192]$$

### Step 6: Interpretation

Look at what happened:
- The dip at age 2 (original $m_2 = 0.012$) got pulled up to $g_2 \approx 0.015$.
- The graduated curve is now monotonically increasing -- biologically plausible for adult ages.
- No single point moved dramatically, but the overall shape is much cleaner.

The rod bent toward the data but refused to follow the implausible dip. That is graduation in action.

---

## Connections to Splines and Modern Methods

> **[FORMAL]** Equivalences
>
> - WH with $z=2$ is exactly the **Hodrick-Prescott filter**, widely used in macroeconomics for trend extraction.
> - WH can be viewed as **P-splines of degree 0** (Eilers and Marx, 1996): B-spline basis with a difference penalty on coefficients.
> - Classical spline smoothing uses derivatives in continuous calculus. WH uses finite differences in discrete arithmetic. For equally spaced data (single-year ages), the two are essentially equivalent.

> **[INTUITION]** Discrete vs Continuous
>
> WH is the discrete version of spline smoothing. Splines live in continuous calculus land, working with integrals of squared derivatives. WH lives in discrete difference land, working with sums of squared differences. Same principle, different tools. For mortality data on a regular age grid (age 0, 1, 2, ..., 100), the distinction is academic -- the results are nearly identical.

---

## Summary Table

| Component | Symbol | Role | Analogy |
|:----------|:-------|:-----|:--------|
| Observed data | $m_x$ | What was measured | The noisy dots |
| Graduated data | $g_x$ | What we believe | The smooth curve |
| Weights | $w_x$ | Trust per age | Spring strength |
| Difference order | $z$ | What "smooth" means | Frequency cutoff |
| Smoothing parameter | $\lambda$ | Fit vs smooth balance | Rod stiffness |
| Difference matrix | $D$ | Computes roughness | Curvature meter |
| Penalty matrix | $D^\top D$ | Spreads roughness penalty | Stiffness matrix of the rod |

---

## Key Identities and Properties

1. $\Delta^z$ coefficients are binomial with alternating signs: $(-1)^k \binom{z}{k}$.

2. $(W + \lambda\,D^\top D)$ is always symmetric positive definite, so there is always a unique solution.

3. $\lambda = 0 \implies \mathbf{g} = \mathbf{m}$. No smoothing at all; pure data.

4. $\lambda \to \infty \implies \mathbf{g}$ converges to a polynomial of degree $z-1$. Maximum smoothing.

5. WH with $z=2$ is the Hodrick-Prescott filter from macroeconomics.

6. $D^\top D$ is banded with bandwidth $2z+1$, giving $O(n)$ solve time.

7. Penalizing $\Delta^z \approx$ penalizing the $z$-th derivative (discrete vs continuous versions of the same idea).

---

## What This Document Does Not Cover (Yet)

- Two-dimensional smoothing (age $\times$ year surface for Lee-Carter input)
- Automatic $\lambda$ selection (cross-validation, AIC, BIC)
- Bayesian interpretation of graduation (prior on smoothness, posterior = graduated rates)
- Other smoothing methods (kernel smoothing, spline regression, GAMs)
- Constrained graduation (e.g., forcing monotonicity or positivity)
