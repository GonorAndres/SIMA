# SVD, Bilinear Decomposition, and Identifiability Constraints

**A Bridge Document for SIMA -- Lee-Carter Mortality Modeling**

---

## Abstract

This document develops the mathematical foundations connecting Singular Value Decomposition (SVD), bilinear parameter estimation, and identifiability constraints, culminating in the Lee-Carter mortality model. Each concept is presented in three layers: formal definition (blue/FORMAL), geometric intuition (green/INTUITION), and actuarial application (orange/APPLICATION). The treatment is at graduate level, emphasizing the structural reasons why SVD is the natural estimator for bilinear models and why constraints are mathematically necessary for unique parameterization.

---

## Notation and Conventions

| Symbol | Space | Meaning |
|:-------|:------|:--------|
| **A** in R^{m x n} | matrix | Arbitrary real matrix |
| **Z** in R^{A x T} | matrix | Lee-Carter residual matrix |
| **U** in R^{m x m} | orthogonal | Left singular vectors |
| **V** in R^{n x n} | orthogonal | Right singular vectors |
| **Sigma** in R^{m x n} | diagonal | Singular values sigma_1 >= sigma_2 >= ... >= 0 |
| **u**_i in R^m | column of U | i-th left singular vector |
| **v**_i in R^n | column of V | i-th right singular vector |
| sigma_i | scalar >= 0 | i-th singular value |
| \|\|.\|\|_F | norm | Frobenius norm: sqrt(sum of a_ij^2) |
| \|\|.\|\|_2 | norm | Spectral (operator) norm: sigma_1(A) |
| rank(A) | integer | Number of nonzero singular values |
| m_{x,t} | scalar > 0 | Central death rate, age x, year t |
| a_x, b_x, k_t | scalars | Lee-Carter parameters |

Convention: bold lowercase for vectors (**u**), bold uppercase for matrices (**A**), italic for scalars (sigma). Ages indexed by x in {x_1, ..., x_A}, years by t in {t_1, ..., t_T}.

---

## Bilinear Forms and the Parameter Product Problem

> **[FORMAL]** Definition: Bilinear Parametric Model
>
> A *bilinear parametric model* for a data matrix **Z** in R^{m x n} is a model of the form:
>
> ```
> Z_ij = SUM_{r=1}^{R} beta_i^(r) * gamma_j^(r) + epsilon_ij
> ```
>
> where **beta**^(r) in R^m and **gamma**^(r) in R^n are unknown parameter vectors, R is the number of factors, and epsilon_ij is noise.
>
> In matrix form:
>
> ```
> Z = B * G' + E
> ```
>
> where B = [beta^(1) ... beta^(R)] in R^{m x R} and G = [gamma^(1) ... gamma^(R)] in R^{n x R}.

> **[INTUITION]** Why "Bilinear"?
>
> The model is *linear in each factor separately*, but the factors enter as a product.
>
> - Fix **gamma**: the model Z_ij = beta_i * gamma_j is linear in beta_i
> - Fix **beta**: the model is linear in gamma_j
> - Together: *bilinear* -- linear in each, nonlinear jointly
>
> This is why OLS fails. Ordinary least squares assumes y = X * beta where X is known. Here both B and G are unknown. The "design matrix" is itself a parameter. There is no closed-form normal equation.

> **[APPLICATION]** Lee-Carter as a Rank-1 Bilinear Model
>
> The Lee-Carter model:
>
> ```
> ln(m_{x,t}) = a_x + b_x * k_t + epsilon_{x,t}
> ```
>
> After centering (subtracting a_x = mean of row x), the residual satisfies:
>
> ```
> Z_{x,t} = b_x * k_t + epsilon_{x,t}
> ```
>
> This is a bilinear model with R = 1, **beta** = **b** = (b_{x_1}, ..., b_{x_A})', **gamma** = **k** = (k_{t_1}, ..., k_{t_T})'.
>
> In matrix form: Z ≈ **b** * **k**', a rank-1 outer product.

### The Fundamental Indeterminacy of Bilinear Products

> **[FORMAL]** Proposition: Scale Indeterminacy
>
> Let Z = **b** * **k**'. For any c != 0, define **b*** = c * **b** and **k*** = **k** / c. Then:
>
> ```
> b* * (k*)' = c*b * (k'/c) = b * k' = Z
> ```
>
> The factorization is invariant under reciprocal scaling. The data cannot distinguish (**b**, **k**) from (c * **b**, **k** / c) for any c != 0.

> **[FORMAL]** Proposition: Location Indeterminacy in Lee-Carter
>
> In the uncentered model ln(m_{x,t}) = a_x + b_x * k_t, define for any constant d:
>
> ```
> a_x* = a_x + d * b_x,     k_t* = k_t - d
> ```
>
> Then:
>
> ```
> a_x* + b_x * k_t* = (a_x + d*b_x) + b_x*(k_t - d) = a_x + b_x*k_t
> ```
>
> The constant d shifts freely between a_x and k_t without changing the model output.

> **[INTUITION]** Geometric Picture of Indeterminacy
>
> A rank-1 matrix **b** * **k**' defines a *line* in parameter space, not a point. The line passes through the origin in (b, k)-space, parameterized by c.
>
> Every point on the line produces the same matrix Z. Without a constraint to pick one point on the line, the solution is a one-dimensional family, not unique.
>
> - Scale indeterminacy: a line through the origin (choose magnitude)
> - Location indeterminacy: a plane (choose where a_x ends and k_t begins)
> - Together: a two-parameter family of equivalent solutions

---

## Singular Value Decomposition

> **[FORMAL]** Theorem: Existence of SVD
>
> For any **A** in R^{m x n} with r = rank(A), there exist:
>
> - An orthogonal matrix **U** in R^{m x m} (columns **u**_1, ..., **u**_m)
> - An orthogonal matrix **V** in R^{n x n} (columns **v**_1, ..., **v**_n)
> - Singular values sigma_1 >= sigma_2 >= ... >= sigma_r > 0 = sigma_{r+1} = ...
>
> such that:
>
> ```
> A = U * Sigma * V' = SUM_{i=1}^{r} sigma_i * u_i * v_i'
> ```
>
> The outer product form shows A as a sum of r rank-1 matrices, each weighted by sigma_i.

> **[DIMENSION CHECK]**
>
> ```
> A         = U         * Sigma     * V'
> (m x n)   = (m x m)   * (m x n)   * (n x n)
>
> Outer product form: each u_i * v_i' is (m x 1)(1 x n) = m x n
>
> In Lee-Carter: m = A (number of ages), n = T (number of years)
>
> Z         = SUM sigma_i * u_i    * v_i'
> (A x T)                  (A x 1)  (1 x T)
> ```

> **[INTUITION]** SVD as Sequential Best Rank-1 Extraction
>
> Think of SVD as a greedy algorithm for pattern extraction:
>
> **Round 1:** Find the single rank-1 matrix sigma_1 * u_1 * v_1' that captures the maximum possible variance (Frobenius norm) of A. Subtract it from A.
>
> **Round 2:** From the residual, find the next best rank-1 matrix sigma_2 * u_2 * v_2', constrained to be orthogonal to the first. Subtract.
>
> **Round i:** Continue until the residual is zero (i = r) or negligible.
>
> Each sigma_i measures "how much pattern" was extracted in round i. If sigma_1 >> sigma_2, the first round captured almost everything.

### The Eckart-Young-Mirsky Theorem

> **[FORMAL]** Theorem: Eckart-Young-Mirsky (1936)
>
> Let **A** in R^{m x n} with SVD A = SUM sigma_i * u_i * v_i'. Define the rank-k truncation:
>
> ```
> A_k = SUM_{i=1}^{k} sigma_i * u_i * v_i',     k <= r
> ```
>
> Then for any matrix **B** with rank(B) <= k:
>
> ```
> ||A - A_k||_F <= ||A - B||_F
> ```
>
> The approximation error is:
>
> ```
> ||A - A_k||_F = sqrt(sigma_{k+1}^2 + sigma_{k+2}^2 + ... + sigma_r^2)
> ```

> **[FORMAL]** Proof Sketch (Frobenius norm)
>
> Since U and V are orthogonal, the Frobenius norm is invariant under orthogonal transformation:
>
> ```
> ||A - B||_F^2 = ||U'(A - B)V||_F^2 = ||Sigma - U'BV||_F^2
> ```
>
> Let C = U'BV. Since rank(C) = rank(B) <= k, at least r - k diagonal entries of Sigma cannot be matched by C. The minimum of SUM (sigma_i - C_ii)^2 + SUM_{i!=j} C_ij^2 is achieved by setting C_ii = sigma_i for i <= k and C_ij = 0 otherwise, giving the truncated SVD.

> **[INTUITION]** Eckart-Young: Optimality Guarantee
>
> Eckart-Young says: "You cannot do better than SVD truncation for low-rank approximation."
>
> It is not merely *a* solution. It is *the* optimal solution.
>
> For k = 1 (Lee-Carter): among all possible outer products **b** * **k**', the one that minimizes ||Z - **b** * **k**'||_F^2 is exactly sigma_1 * u_1 * v_1'.
>
> The proportion of variance explained:
>
> ```
> rho = sigma_1^2 / SUM sigma_i^2 = 1 - ||Z - A_1||_F^2 / ||Z||_F^2
> ```
>
> When rho >= 0.90, retaining one factor is strongly justified.

> **[APPLICATION]** Lee-Carter: Rank-1 Optimality
>
> For the Lee-Carter residual matrix Z (ages x years):
>
> ```
> min_{b, k} SUM_{x,t} (Z_{x,t} - b_x * k_t)^2   <==>   min_{rank(M)=1} ||Z - M||_F^2
> ```
>
> The solution is M* = sigma_1 * u_1 * v_1', and we set:
>
> ```
> b_x^raw = u_{1,x}             (first left singular vector, age component)
> k_t^raw = sigma_1 * v_{1,t}   (scaled first right singular vector, time component)
> ```
>
> This is the least-squares bilinear estimator. SVD is not an ad hoc choice -- it is the unique solution to the optimization problem.

---

## Identifiability Constraints

> **[FORMAL]** Definition: Identifiability
>
> A parametric model f(theta) is *identifiable* if distinct parameter values produce distinct model outputs:
>
> ```
> f(theta_1) = f(theta_2)  ==>  theta_1 = theta_2
> ```
>
> A model that is not identifiable has an *equivalence class* of parameters that all produce the same fit. The set of equivalent parameters forms a manifold in parameter space.

> **[FORMAL]** Theorem: Lee-Carter Indeterminacy is Two-Dimensional
>
> The Lee-Carter model ln(m_{x,t}) = a_x + b_x * k_t has a two-parameter family of equivalent solutions. Given any solution (a_x, b_x, k_t), the full equivalence class is:
>
> ```
> E = { (a_x + d*c*b_x,  c*b_x,  k_t/c - d)  |  c != 0, d in R }
> ```
>
> **Proof.** Substituting:
>
> ```
> a_x* + b_x* * k_t* = (a_x + dc*b_x) + (c*b_x)(k_t/c - d)
>                     = a_x + dc*b_x + b_x*k_t - dc*b_x
>                     = a_x + b_x*k_t
> ```
>
> The parameter c controls scale (rescaling b and k inversely). The parameter d controls location (shifting between a and k). Two free parameters, hence a two-dimensional equivalence class.

> **[FORMAL]** Lee-Carter Normalization Constraints
>
> To select a unique representative from E, impose:
>
> ```
> (C1: scale)     SUM_x b_x = 1
> (C2: location)  SUM_t k_t = 0
> ```
>
> **C1** fixes c: if SUM b_x^raw = s, then c = 1/s gives SUM c*b_x^raw = 1.
>
> **C2** fixes d: if mean(k_t) = k_bar, then d = k_bar gives SUM(k_t - d) = 0, with compensation a_x -> a_x + b_x * k_bar.
>
> Two constraints for two degrees of freedom yields a unique solution.

> **[INTUITION]** Constraints as Coordinate Choices
>
> Think of the equivalence class as an infinite line of equivalent parameter sets. Each constraint slices away one degree of freedom:
>
> - SUM b_x = 1 chooses a specific "length" for **b**, pinning a point on the scale axis
> - SUM k_t = 0 chooses a specific "origin" for the time index, pinning a point on the location axis
>
> Together they select exactly one point from the two-dimensional equivalence manifold.
>
> The choice is conventional, not unique. Alternative valid constraints exist (e.g., SUM b_x^2 = 1, or k_{t_1} = 0). Different constraints give different parameter values but identical model output. The Lee-Carter convention is chosen for interpretability: b_x become proportions and a_x become true time-averages.

> **[APPLICATION]** Implementation: Constraint Enforcement
>
> After SVD gives raw estimates:
>
> 1. b_x^raw = u_{1,x},  k_t^raw = sigma_1 * v_{1,t}
> 2. s = SUM_x b_x^raw
> 3. b_x = b_x^raw / s,  k_t = k_t^raw * s           --> (C1 enforced)
> 4. k_bar = (1/T) * SUM_t k_t
> 5. k_t <- k_t - k_bar,  a_x <- a_x + b_x * k_bar   --> (C2 enforced)
>
> Note: step 5 modifies a_x. After this, a_x is no longer the simple row mean of ln(m_{x,t}) -- it has absorbed the mean level of k_t.

---

## Variance Decomposition and the One-Factor Justification

> **[FORMAL]** Variance Partition via Singular Values
>
> The total variance (sum of squared entries) of the residual matrix Z satisfies:
>
> ```
> ||Z||_F^2 = SUM_{i=1}^{r} sigma_i^2
> ```
>
> The proportion attributed to factor i is:
>
> ```
> rho_i = sigma_i^2 / SUM_{j=1}^{r} sigma_j^2
> ```
>
> For Lee-Carter, one retains only factor 1. The unexplained proportion is 1 - rho_1.

> **[INTUITION]** Why Does One Factor Suffice for Mortality?
>
> Mortality improvement across ages is driven by shared macro-level forces: advances in medicine, sanitation, nutrition, public health infrastructure.
>
> If each age improved independently (age 40 from antibiotics, age 70 from cardiac surgery, with no correlation), the residual matrix would have several large singular values. No single factor would dominate.
>
> But empirically, rho_1 >= 0.90 for virtually all national populations. This reflects a biological and sociological reality: the forces that reduce mortality are broad, systemic, and correlated across ages. One underlying process drives most of the change.
>
> When this assumption breaks (HIV epidemic affecting ages 20-40 disproportionately, or infant mortality declining while elderly mortality stagnates), extended models with R = 2 or more factors (Renshaw-Haberman, Cairns-Blake-Dowd) become necessary.

---

## From SVD to the Full Lee-Carter Procedure

> **[APPLICATION]** Complete Estimation Pipeline
>
> **Input:** Matrix **M** in R^{A x T} of observed central death rates m_{x,t} > 0.
>
> 1. **Log transform:** Y_{x,t} = ln(m_{x,t})
> 2. **Estimate a_x:** a_x_hat = (1/T) * SUM_t Y_{x,t}
> 3. **Compute residuals:** Z_{x,t} = Y_{x,t} - a_x_hat
> 4. **SVD:** Z = U * Sigma * V'
> 5. **Extract rank-1:** b_x^raw = u_{1,x},  k_t^raw = sigma_1 * v_{1,t}
> 6. **Normalize:** enforce SUM b_x = 1, SUM k_t = 0 (adjust a_x)
> 7. **Re-estimate k_t** (optional but recommended): solve SUM_x d_{x,t} = SUM_x L_{x,t} * exp(a_x_hat + b_x_hat * k_t) for each t
> 8. **Forecast k_t:** fit ARIMA (typically random walk with drift) to {k_t}
> 9. **Project:** ln(m_hat_{x,t*}) = a_x_hat + b_x_hat * k_t_hat for future t*
> 10. **Convert:** q_hat_{x,t*} = 1 - exp(-m_hat_{x,t*})

> **[DIMENSION CHECK]**
>
> ```
> M         in R^{A x T}_{>0}    (raw rates)
> Y         in R^{A x T}         (log rates)
> a_hat     in R^{A}             (one per age)
> Z         in R^{A x T}         (residuals, same shape as Y)
> U         in R^{A x A}         (age singular vectors)
> Sigma     in R^{A x T}         (diagonal, min(A,T) values)
> V         in R^{T x T}         (year singular vectors)
> b_hat     in R^{A}             (one per age, from u_1)
> k_hat     in R^{T}             (one per year, from sigma_1 * v_1)
> b_hat*k_hat'  in R^{A x T}    (rank-1 approximation of Z)
> ```

---

## The Observable: Why m_x, Not q_x

> **[FORMAL]** Definition: Central Death Rate
>
> ```
> m_{x,t} = d_{x,t} / L_{x,t}
> ```
>
> where d_{x,t} is the count of deaths at age x in year t, and L_{x,t} is the person-years of exposure at age x in year t.
>
> Unit: deaths per person-year. Domain: (0, +infinity).

> **[FORMAL]** Conversion to Probability
>
> Under constant force assumption (mu_{x+s} = m_x for 0 <= s < 1):
>
> ```
> q_x = 1 - exp(-m_x)
> ```
>
> Under UDD assumption:
>
> ```
> q_x = m_x / (1 + 0.5 * m_x)
> ```
>
> For m_x < 0.1 both yield q_x approx m_x with relative error < 5%.

> **[INTUITION]** The Observation Hierarchy
>
> | Level | Quantity | Status |
> |:------|:---------|:-------|
> | 1 | Deaths d_{x,t} and exposure L_{x,t} | Raw data (certificates, census) |
> | 2 | m_{x,t} = d_{x,t} / L_{x,t} | Direct calculation |
> | 3 | q_{x,t} = f(m_{x,t}) | Requires distributional assumption |
> | 4 | l_x, d_x, D_x, N_x, ... | Requires full life table construction |
>
> Each level adds assumptions. Lee-Carter models at level 2: the closest to raw data that still produces a clean mathematical object. This minimizes modeling risk and maximizes connection to what is actually observed.

> **[APPLICATION]** Transformation Guarantees
>
> The chain ln(m_x) --exp()--> m_x --1-exp(-)--> q_x provides:
>
> - ln(m_x) in R: unconstrained for SVD, ARIMA, any linear method
> - m_x = exp(ln(m_x)) > 0: positivity guaranteed
> - q_x = 1 - exp(-m_x) in (0, 1): valid probability guaranteed
>
> No post-processing, clipping, or projection needed. The transformation chain is structurally safe for any output of the Lee-Carter model.

---

## Summary Table

| Operation | Mathematics | Dimensions | Purpose |
|:----------|:-----------|:-----------|:--------|
| Log transform | Y_{x,t} = ln(m_{x,t}) | A x T | Unconstrained space |
| Row centering | Z_{x,t} = Y_{x,t} - mean(Y_x) | A x T | Extract a_x, isolate trend |
| SVD | Z = U * Sigma * V' | AxA, diag, TxT | Optimal decomposition |
| Rank-1 truncation | Z approx sigma_1 * u_1 * v_1' | A x T | Single-factor approximation |
| Extract b_x | b_x = u_{1,x} / SUM u_{1,x} | A x 1 | Age sensitivity |
| Extract k_t | k_t = sigma_1 * v_{1,t} * SUM u_{1,x} | 1 x T | Time index |
| Normalize | SUM b_x = 1, SUM k_t = 0 | --- | Unique identification |
| Forecast k_t | k_{t+1} = k_t + delta + epsilon | scalar series | Project mortality |
| Back-transform | m_x = exp(a_x + b_x * k_t) | A x T | Recover rates |
| Convert | q_x = 1 - exp(-m_x) | A x T | Probability for life table |

---

## Key Identities and Properties

1. **SVD existence:** Every real matrix has an SVD (not unique if singular values coincide).
2. **Eckart-Young:** A_k = argmin_{rank(B)<=k} ||A - B||_F.
3. **Frobenius norm via singular values:** ||A||_F^2 = SUM sigma_i^2.
4. **Orthogonal invariance:** ||Q*A*R||_F = ||A||_F for orthogonal Q, R.
5. **Bilinear indeterminacy:** **b** * **k**' = (c * **b**) * (**k** / c)' for all c != 0.
6. **Constraint count = indeterminacy dimension:** 2 constraints for 2 free parameters.
7. **Positivity guarantee:** exp: R -> R_{>0} and 1 - exp(-x): R_{>0} -> (0,1).

---

## What This Document Does Not Cover (Yet)

- **k_t re-estimation:** Newton-Raphson adjustment to match observed death counts
- **ARIMA forecasting of k_t:** random walk with drift, confidence intervals, fan charts
- **Poisson GLM alternative:** MLE under Poisson death counts (Brouhns, Denuit, Vermunt, 2002)
- **Multi-factor extensions:** Renshaw-Haberman (cohort effect), CBD (logit of q_x), APC models
- **Whittaker-Henderson graduation:** smoothing raw m_x before Lee-Carter estimation
- **Mexican regulatory context:** CNSF/LISF requirements for mortality projection
