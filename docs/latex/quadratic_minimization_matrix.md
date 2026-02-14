# Quadratic Minimization in Matrix Form: From Sums to Systems

---

## Notation and Conventions

| Symbol | Meaning |
|:-------|:--------|
| $x$ | Scalar variable |
| $\mathbf{x}$ | Column vector ($n \times 1$) |
| $\mathbf{A}$ | Matrix ($n \times n$) |
| $f(\mathbf{x})$ | Objective function to minimize |
| $\nabla f$ | Gradient (vector of partial derivatives) |
| $\mathbf{A} \succ 0$ | $\mathbf{A}$ is positive definite |
| $\mathbf{x}'$ | Transpose of $\mathbf{x}$ |
| $\mathbf{A}^{-1}$ | Inverse of $\mathbf{A}$ |

---

## Scalar Warm-Up: $f(x) = ax^2 + bx + c$

> **\[FORMAL\]** Scalar Minimization
>
> $$f'(x) = 2ax + b = 0 \quad \Longrightarrow \quad x^* = -\frac{b}{2a}$$
>
> Requires $a > 0$ for a minimum.

> **\[INTUITION\]** The Parabola
>
> A parabola opening upward ($a > 0$). The bottom is at $x^* = -b/(2a)$. Taking the derivative and setting it to zero finds the bottom.
>
> This is the **entire template** -- everything below is this same idea with more variables.

---

## Two Variables: The 2D Bowl

> **\[FORMAL\]** Two Partial Derivatives
>
> $$f(x,y) = ax^2 + by^2 + cxy + dx + ey + \text{const}$$
>
> $$\frac{\partial f}{\partial x} = 2ax + cy + d = 0$$
>
> $$\frac{\partial f}{\partial y} = cx + 2by + e = 0$$
>
> In matrix form:
>
> $$\begin{bmatrix} 2a & c \\ c & 2b \end{bmatrix} \begin{bmatrix} x \\ y \end{bmatrix} = \begin{bmatrix} -d \\ -e \end{bmatrix}$$
>
> Two equations, two unknowns, one matrix system.

> **\[INTUITION\]** The Bowl in 3D
>
> The function is a bowl (elliptic paraboloid). The minimum is at the bottom. Two partial derivatives = finding where the bowl is flat in **both** $x$ and $y$ directions simultaneously. The shape (round vs elongated) depends on the coefficient matrix.

---

## General Case: $f(\mathbf{x}) = \mathbf{x}'\mathbf{A}\mathbf{x} + \mathbf{b}'\mathbf{x} + c$

> **\[FORMAL\]** The General Quadratic Form
>
> $\mathbf{x}$ is $n \times 1$. $\mathbf{A}$ is $n \times n$ symmetric. $\mathbf{b}$ is $n \times 1$.
>
> $$f(\mathbf{x}) = \mathbf{x}'\mathbf{A}\mathbf{x} + \mathbf{b}'\mathbf{x} + c$$
>
> $$\nabla f = 2\mathbf{A}\mathbf{x} + \mathbf{b}$$
>
> Set to zero:
>
> $$2\mathbf{A}\mathbf{x} + \mathbf{b} = \mathbf{0}$$
>
> Solution:
>
> $$\mathbf{x}^* = -\frac{1}{2}\mathbf{A}^{-1}\mathbf{b}$$
>
> Condition: $\mathbf{A}$ must be positive definite (minimum exists and is unique).

> **\[INTUITION\]** Same Parabola, $n$ Dimensions
>
> Positive definite means "the bowl opens upward in every direction." The gradient points uphill. Setting the gradient to zero finds the one flat spot at the bottom. Same logic as scalar, same logic as 2D. Just more dimensions.

> **\[DIMENSION CHECK\]**
>
> | Expression | Dimensions | Notes |
> |:-----------|:-----------|:------|
> | $\mathbf{x}$ | $n \times 1$ | |
> | $\mathbf{A}$ | $n \times n$ | symmetric |
> | $\mathbf{A}\mathbf{x}$ | $n \times 1$ | |
> | $\mathbf{b}$ | $n \times 1$ | |
> | $2\mathbf{A}\mathbf{x} + \mathbf{b}$ | $n \times 1$ | the gradient -- one equation per variable |

---

## Matrix Calculus: The Three Rules You Need

> **\[FORMAL\]** The Rules
>
> | # | Rule | Name |
> |:--|:-----|:-----|
> | 1 | $\frac{d}{d\mathbf{x}}(\mathbf{a}'\mathbf{x}) = \mathbf{a}$ | Linear form |
> | 2 | $\frac{d}{d\mathbf{x}}(\mathbf{x}'\mathbf{A}\mathbf{x}) = 2\mathbf{A}\mathbf{x}$ | Quadratic form ($\mathbf{A}$ symmetric) |
> | 3 | $\frac{d}{d\mathbf{x}}(\mathbf{x}'\mathbf{A}\mathbf{x} + \mathbf{b}'\mathbf{x}) = 2\mathbf{A}\mathbf{x} + \mathbf{b}$ | Combined |

> **\[INTUITION\]** They Are Just Scalar Rules in Disguise
>
> | Scalar | Matrix | Rule |
> |:-------|:-------|:-----|
> | $\frac{d}{dx}(ax) = a$ | $\frac{d}{d\mathbf{x}}(\mathbf{a}'\mathbf{x}) = \mathbf{a}$ | Rule 1 |
> | $\frac{d}{dx}(ax^2) = 2ax$ | $\frac{d}{d\mathbf{x}}(\mathbf{x}'\mathbf{A}\mathbf{x}) = 2\mathbf{A}\mathbf{x}$ | Rule 2 |
> | $\frac{d}{dx}(ax^2 + bx) = 2ax + b$ | $\frac{d}{d\mathbf{x}}(\mathbf{x}'\mathbf{A}\mathbf{x} + \mathbf{b}'\mathbf{x}) = 2\mathbf{A}\mathbf{x} + \mathbf{b}$ | Rule 3 |
>
> Replace scalar $a$ with matrix $\mathbf{A}$, scalar $x$ with vector $\mathbf{x}$, scalar $b$ with vector $\mathbf{b}$. The structure is **identical**. Matrix calculus for quadratics is just scalar calculus with bold letters.

> **\[FORMAL\]** Verification: $2 \times 2$ Example
>
> Let $\mathbf{A} = \begin{bmatrix} 3 & 1 \\ 1 & 2 \end{bmatrix}$, $\mathbf{x} = \begin{bmatrix} x_1 \\ x_2 \end{bmatrix}$
>
> $$\mathbf{x}'\mathbf{A}\mathbf{x} = 3x_1^2 + 2x_1 x_2 + 2x_2^2$$
>
> By hand:
>
> $$\frac{\partial}{\partial x_1} = 6x_1 + 2x_2, \qquad \frac{\partial}{\partial x_2} = 2x_1 + 4x_2$$
>
> As vector:
>
> $$\begin{bmatrix} 6x_1 + 2x_2 \\ 2x_1 + 4x_2 \end{bmatrix} = 2 \begin{bmatrix} 3 & 1 \\ 1 & 2 \end{bmatrix} \begin{bmatrix} x_1 \\ x_2 \end{bmatrix} = 2\mathbf{A}\mathbf{x}$$
>
> Rule 2 checks out.

---

## OLS as Quadratic Minimization

> **\[FORMAL\]** Ordinary Least Squares
>
> Objective:
>
> $$\min_{\boldsymbol{\beta}} \| \mathbf{y} - \mathbf{X}\boldsymbol{\beta} \|^2 = (\mathbf{y} - \mathbf{X}\boldsymbol{\beta})'(\mathbf{y} - \mathbf{X}\boldsymbol{\beta})$$
>
> Expand:
>
> $$\boldsymbol{\beta}'\mathbf{X}'\mathbf{X}\boldsymbol{\beta} - 2\mathbf{y}'\mathbf{X}\boldsymbol{\beta} + \mathbf{y}'\mathbf{y}$$
>
> Identify:
>
> $$\mathbf{A} = \mathbf{X}'\mathbf{X}, \qquad \mathbf{b} = -2\mathbf{X}'\mathbf{y}, \qquad c = \mathbf{y}'\mathbf{y}$$
>
> Gradient:
>
> $$2\mathbf{X}'\mathbf{X}\boldsymbol{\beta} - 2\mathbf{X}'\mathbf{y} = \mathbf{0}$$
>
> Solution (the normal equations):
>
> $$\boldsymbol{\beta}^* = (\mathbf{X}'\mathbf{X})^{-1}\mathbf{X}'\mathbf{y}$$

> **\[INTUITION\]** Fitting a Line Through Data
>
> The sum of squared residuals is a bowl in $\boldsymbol{\beta}$-space. Each coefficient is one axis. The bottom of the bowl is the best-fitting line. The normal equations find that bottom.

> **\[DIMENSION CHECK\]**
>
> | Expression | Dimensions | Role |
> |:-----------|:-----------|:-----|
> | $\mathbf{y}$ | $n \times 1$ | observations |
> | $\mathbf{X}$ | $n \times p$ | design matrix |
> | $\boldsymbol{\beta}$ | $p \times 1$ | coefficients |
> | $\mathbf{X}'\mathbf{X}$ | $p \times p$ | system matrix |
> | $\mathbf{X}'\mathbf{y}$ | $p \times 1$ | right-hand side |

---

## Whittaker-Henderson as Quadratic Minimization

> **\[FORMAL\]** Graduation
>
> Objective:
>
> $$\min_{\mathbf{g}} \; (\mathbf{g} - \mathbf{m})'\mathbf{W}(\mathbf{g} - \mathbf{m}) + \lambda \, \mathbf{g}'\mathbf{D}'\mathbf{D}\mathbf{g}$$
>
> Expand:
>
> $$\mathbf{g}'\mathbf{W}\mathbf{g} - 2\mathbf{m}'\mathbf{W}\mathbf{g} + \mathbf{m}'\mathbf{W}\mathbf{m} + \lambda\,\mathbf{g}'\mathbf{D}'\mathbf{D}\mathbf{g}$$
>
> $$= \mathbf{g}'(\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D})\mathbf{g} - 2\mathbf{m}'\mathbf{W}\mathbf{g} + \text{constant}$$
>
> Identify:
>
> $$\mathbf{A} = \mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D}, \qquad \mathbf{b} = -2\mathbf{W}\mathbf{m}$$
>
> Gradient:
>
> $$2(\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D})\mathbf{g} - 2\mathbf{W}\mathbf{m} = \mathbf{0}$$
>
> Solution:
>
> $$\mathbf{g}^* = (\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D})^{-1}\mathbf{W}\mathbf{m}$$

> **\[INTUITION\]** Same Bowl, Different Shape
>
> The bowl is the same concept as OLS -- just the shape is different. In OLS the bowl shape comes from $\mathbf{X}'\mathbf{X}$ (the data geometry). In graduation the bowl shape comes from $\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D}$ (data trust + smoothness penalty). The process of finding the bottom is **identical**.

> **\[DIMENSION CHECK\]**
>
> | Expression | Dimensions | Role |
> |:-----------|:-----------|:-----|
> | $\mathbf{g}$ | $n \times 1$ | graduated values (what we solve for) |
> | $\mathbf{m}$ | $n \times 1$ | observed values |
> | $\mathbf{W}$ | $n \times n$ | diagonal weight matrix |
> | $\mathbf{D}$ | $(n-z) \times n$ | difference matrix |
> | $\mathbf{D}'\mathbf{D}$ | $n \times n$ | penalty matrix |
> | $\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D}$ | $n \times n$ | system matrix |
> | $\mathbf{W}\mathbf{m}$ | $n \times 1$ | right-hand side |

---

## Ridge Regression as Quadratic Minimization

> **\[FORMAL\]** Ridge
>
> Objective:
>
> $$\min_{\boldsymbol{\beta}} \; \|\mathbf{y} - \mathbf{X}\boldsymbol{\beta}\|^2 + \lambda\|\boldsymbol{\beta}\|^2$$
>
> $$= \boldsymbol{\beta}'(\mathbf{X}'\mathbf{X} + \lambda\mathbf{I})\boldsymbol{\beta} - 2\mathbf{y}'\mathbf{X}\boldsymbol{\beta} + \text{constant}$$
>
> Solution:
>
> $$\boldsymbol{\beta}^* = (\mathbf{X}'\mathbf{X} + \lambda\mathbf{I})^{-1}\mathbf{X}'\mathbf{y}$$

> **\[APPLICATION\]** The Unified Pattern -- Three Methods, One Template
>
> | Method | System matrix $\mathbf{A}$ | Right-hand side | Solution |
> |:-------|:--------------------------|:----------------|:---------|
> | OLS | $\mathbf{X}'\mathbf{X}$ | $\mathbf{X}'\mathbf{y}$ | $(\mathbf{X}'\mathbf{X})^{-1}\mathbf{X}'\mathbf{y}$ |
> | Ridge | $\mathbf{X}'\mathbf{X} + \lambda\mathbf{I}$ | $\mathbf{X}'\mathbf{y}$ | $(\mathbf{X}'\mathbf{X} + \lambda\mathbf{I})^{-1}\mathbf{X}'\mathbf{y}$ |
> | WH Graduation | $\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D}$ | $\mathbf{W}\mathbf{m}$ | $(\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D})^{-1}\mathbf{W}\mathbf{m}$ |
>
> All three: solve $\mathbf{A}\mathbf{x} = \mathbf{b}$ for $\mathbf{x}$. The only difference is what goes into $\mathbf{A}$ and $\mathbf{b}$.

---

## Positive Definiteness: Why the Minimum Exists

> **\[FORMAL\]** Definition
>
> $\mathbf{A}$ is positive definite if $\mathbf{x}'\mathbf{A}\mathbf{x} > 0$ for all $\mathbf{x} \neq \mathbf{0}$.
>
> Equivalent: all eigenvalues of $\mathbf{A}$ are positive.
>
> Consequence: $\mathbf{A}$ is invertible, and the quadratic $f(\mathbf{x}) = \mathbf{x}'\mathbf{A}\mathbf{x} + \mathbf{b}'\mathbf{x} + c$ has exactly one minimum.

> **\[INTUITION\]** The Bowl Test
>
> Positive definite = bowl opens upward in **every** direction. No matter which way you walk from the bottom, you go uphill. This guarantees:
>
> - There **is** a minimum (not a saddle point).
> - There is **exactly one** minimum (not multiple).
> - The linear system $\mathbf{A}\mathbf{x} = \mathbf{b}$ has a unique solution.
>
> If $\mathbf{A}$ were not positive definite, the surface could be a saddle (goes up in some directions, down in others) or flat in some direction (infinitely many solutions).

> **\[APPLICATION\]** Why Each Method's Matrix is Positive Definite
>
> - **OLS:** $\mathbf{X}'\mathbf{X}$ is positive semi-definite always. Positive definite when $\mathbf{X}$ has full column rank (no redundant variables).
> - **Ridge:** $\mathbf{X}'\mathbf{X} + \lambda\mathbf{I}$ is **always** positive definite for $\lambda > 0$. The $\lambda\mathbf{I}$ term guarantees it. This is why ridge "fixes" ill-conditioned problems.
> - **WH Graduation:** $\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D}$ is positive definite when $\mathbf{W}$ has at least $z$ positive diagonal entries. Always satisfied in practice (you need at least $z$ ages with observed data).

---

## Summary Table

| Problem | Objective | $\mathbf{A}$ (system matrix) | $\mathbf{b}$ (RHS) | Solution |
|:--------|:---------|:----------------------------|:--------------------|:---------|
| Scalar | $ax^2 + bx$ | $a$ | $-b/2$ | $-b/(2a)$ |
| OLS | $\|\mathbf{y}-\mathbf{X}\boldsymbol{\beta}\|^2$ | $\mathbf{X}'\mathbf{X}$ | $\mathbf{X}'\mathbf{y}$ | $(\mathbf{X}'\mathbf{X})^{-1}\mathbf{X}'\mathbf{y}$ |
| Ridge | $\|\mathbf{y}-\mathbf{X}\boldsymbol{\beta}\|^2 + \lambda\|\boldsymbol{\beta}\|^2$ | $\mathbf{X}'\mathbf{X} + \lambda\mathbf{I}$ | $\mathbf{X}'\mathbf{y}$ | $(\mathbf{X}'\mathbf{X}+\lambda\mathbf{I})^{-1}\mathbf{X}'\mathbf{y}$ |
| WH Graduation | $(\mathbf{g}-\mathbf{m})'\mathbf{W}(\mathbf{g}-\mathbf{m}) + \lambda\,\mathbf{g}'\mathbf{D}'\mathbf{D}\mathbf{g}$ | $\mathbf{W} + \lambda\,\mathbf{D}'\mathbf{D}$ | $\mathbf{W}\mathbf{m}$ | $(\mathbf{W}+\lambda\,\mathbf{D}'\mathbf{D})^{-1}\mathbf{W}\mathbf{m}$ |

The pattern: **every row is the same template**. Identify $\mathbf{A}$ and $\mathbf{b}$, solve $\mathbf{A}\mathbf{x} = \mathbf{b}$.

---

## Key Identities and Properties

$$\frac{d}{d\mathbf{x}}(\mathbf{a}'\mathbf{x}) = \mathbf{a}$$

$$\frac{d}{d\mathbf{x}}(\mathbf{x}'\mathbf{A}\mathbf{x}) = 2\mathbf{A}\mathbf{x} \qquad (\mathbf{A} \text{ symmetric})$$

$$\frac{d}{d\mathbf{x}}(\mathbf{x}'\mathbf{A}\mathbf{x} + \mathbf{b}'\mathbf{x}) = 2\mathbf{A}\mathbf{x} + \mathbf{b}$$

$$(\mathbf{A}\mathbf{B})' = \mathbf{B}'\mathbf{A}'$$

$$\mathbf{A} \succ 0 \;\Longrightarrow\; \mathbf{A}^{-1} \text{ exists} \;\Longrightarrow\; \text{unique minimum}$$

$$f(\mathbf{x}) = \mathbf{x}'\mathbf{A}\mathbf{x} + \mathbf{b}'\mathbf{x} + c \text{ has minimum at } \mathbf{x}^* = -\tfrac{1}{2}\mathbf{A}^{-1}\mathbf{b}$$

$$\mathbf{X}'\mathbf{X} \text{ is always positive semi-definite}$$

$$\mathbf{X}'\mathbf{X} + \lambda\mathbf{I} \text{ is always positive definite for } \lambda > 0$$

---

## What This Document Does Not Cover (Yet)

- Non-quadratic optimization (Newton's method, gradient descent)
- Constrained optimization (Lagrange multipliers, KKT conditions)
- Numerical methods for solving $\mathbf{A}\mathbf{x} = \mathbf{b}$ (Cholesky, LU, banded solvers)
- Second-order conditions (Hessian analysis for non-quadratic functions)
- Pseudoinverse solutions when $\mathbf{A}$ is singular
