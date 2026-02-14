# 09 -- Whittaker-Henderson Graduation Intuition

## The Problem

```
SITUATION:  Raw m_x is noisy, especially at old ages (small populations).
            ln(0) = -infinity (crashes Lee-Carter).
            Even without zeros, noise corrupts SVD.

GOAL:       Find smooth rates g_x that:
            1. Stay close to observed m_x (respect data)
            2. Don't wiggle (be biologically plausible)
```

---

## Finite Differences -- The Core Idea

```
WHAT:       Repeated subtraction of neighbors.
            Do it once: slope. Again: curvature. Again: jerk.

FIRST DIFFERENCE (slope):
  delta^1 g_x = g_{x+1} - g_x
  "How much did it change in one step?"
  All zero --> horizontal line

SECOND DIFFERENCE (curvature):
  delta^2 g_x = g_{x+2} - 2*g_{x+1} + g_x
  "How much did the SLOPE change?"
  All zero --> straight line

THIRD DIFFERENCE (jerk):
  delta^3 g_x = g_{x+3} - 3*g_{x+2} + 3*g_{x+1} - g_x
  "How much did the CURVATURE change?"
  All zero --> parabola

COEFFICIENTS:  Pascal's triangle with alternating signs
  Order 1:   1  -1
  Order 2:   1  -2   1
  Order 3:   1  -3   3  -1
```

```
WHY z=3 FOR MORTALITY:
  Mortality genuinely curves upward with age.
  z=2 would penalize this natural curvature.
  z=3 allows curvature but penalizes SUDDEN changes in curvature.
  Sudden changes = noise. Smooth changes = biology.
```

---

## The Objective -- Two Forces Fighting

```
FORMULA:    Minimize  F + lambda * S

F = SUM w_x * (g_x - m_x)^2      "stay close to data"
S = SUM (delta^z g_x)^2            "don't wiggle"

lambda:  the balance knob
  lambda = 0:     g = m (no smoothing, pure data)
  lambda small:   slight smoothing, follows data closely
  lambda large:   heavy smoothing, nearly polynomial
  lambda = inf:   polynomial of degree z-1
```

---

## Three Analogies

```
SPRING AND ROD:
  - Flexible metal rod = graduated curve
  - Springs at each age pull toward observed data
  - Spring strength = w_x (exposure = trust)
  - Rod stiffness = lambda
  - Equilibrium = graduated curve g*

  Stiff rod + weak springs = smooth (ignores noisy data)
  Soft rod + strong springs = noisy (follows every bump)

AUDIO FILTER:
  - Observed m_x = voice + static
  - Graduation = low-pass filter
  - z = frequency cutoff
  - lambda = filter aggressiveness

NONPARAMETRIC SMOOTHER:
  - NOT a polynomial fit (no assumed formula)
  - Every age gets its own value
  - Only constraint: don't wiggle too much
  - More flexible than any parametric model
```

---

## w_x -- Where It Comes From

```
NOT A PARAMETER:  You don't tune w_x. It comes from data.

w_x = L_x (exposure at age x)

  age 40:  L = 2,000,000  -->  w = 2,000,000  (very reliable, respect it)
  age 98:  L = 3,000       -->  w = 3,000      (noisy, ok to smooth through)

INTUITION:  More people observed = more reliable rate = stronger spring
            The data tells you how much to trust each point.
            Lambda is the only knob you turn.
```

---

## The Matrix Solution

```
SYSTEM:     (W + lambda*D'D) * g = W * m

SOLUTION:   g = (W + lambda*D'D)^{-1} * W * m

WHAT IT MEANS:
  Every g_x depends on ALL m_x values.
  Not g_50 = f(m_50) alone.
  The matrix inverse mixes all ages together.
  Nearby ages contribute most. Distant ages contribute little.

SMOOTHER MATRIX:
  H = (W + lambda*D'D)^{-1} * W
  g = H * m

  Each row of H is a weighted average centered at that age.
  Lambda controls how wide the average spreads.
```

---

## The Quadratic Minimization Template

```
EVERY method follows the same 4 steps:

1. Write objective as x'Ax + b'x + constant
2. Gradient = 2Ax + b
3. Set to zero: 2Ax + b = 0
4. Solve: x = A^{-1} * (-b/2)

WHAT CHANGES:

  Scalar:      A = a,                    b = b
  OLS:         A = X'X,                  b = -2X'y
  Ridge:       A = X'X + lambda*I,       b = -2X'y
  WH Grad:     A = W + lambda*D'D,       b = -2Wm

  Same engine, different fuel.
```

```
MATRIX CALCULUS (three rules, same as scalar):

  Scalar:  d/dx(ax)    = a       Matrix:  d/dx(a'x)    = a
  Scalar:  d/dx(ax^2)  = 2ax     Matrix:  d/dx(x'Ax)   = 2Ax
  Scalar:  d/dx(ax^2+bx) = 2ax+b Matrix:  d/dx(x'Ax+b'x) = 2Ax+b

  Replace a with A, x with x, b with b. Same rules, bold letters.
```

---

## Connection to Lee-Carter Pipeline

```
a06 output: raw m_{x,t}, d_{x,t}, L_{x,t}
     |
     v
a07: Whittaker-Henderson graduation
     - Build W from L_{x,t}
     - Build D for order z=3
     - Solve (W + lambda*D'D)g = Wm for each year
     - Output: smoothed m_{x,t}
     |
     v
a08: Lee-Carter (SVD on log of smoothed rates)
     - Cleaner input --> cleaner a_x, b_x, k_t
     - No zeros --> ln() is safe
     - Less noise --> SVD captures signal, not artifacts
```
