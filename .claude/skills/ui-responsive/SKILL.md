---
name: ui-responsive
description: SIMA frontend UI/UX standard — responsive layout, intuitive navigation, and clear copy, treating mobile and desktop as equally important. Use when building or reviewing anything in frontend/ (pages, components, CSS modules, navigation, charts, tables, forms, page titles), or when the user mentions responsive, mobile, UX, UI, navigation, layout, or copy clarity.
---

# SIMA Frontend UI/UX Standard

SIMA is a portfolio project for actuarial work. It is judged on two screens:
a recruiter's phone and an interviewer's laptop. **Mobile is not a degraded
desktop — it is a first-class target.** Neither view may be an afterthought.

The visual language is **Swiss / International Typographic Style**: black on
white, one accent red (`--color-accent: #C41E3A`), zero border-radius, Inter +
JetBrains Mono, generous whitespace, strict grid alignment. Every change must
preserve that language. Enhance, never restyle.

---

## 1. Non-negotiables

Apply these to every change. They are the review gate.

| Rule | Threshold |
|------|-----------|
| No horizontal page scroll | 320px viewport minimum |
| Touch targets | ≥ 44×44 px (`--tap-target`) for anything tappable |
| Body copy | ≥ 16px on mobile (prevents iOS input zoom) |
| Measure (line length) | 60–75 characters (`max-width: 720px` for prose) |
| Contrast | 4.5:1 body text, 3:1 large text and UI borders |
| Focus | Every interactive element has a visible `:focus-visible` ring |
| Motion | Respect `prefers-reduced-motion` |
| Fixed pixel widths | Forbidden on containers; use `%`, `fr`, `minmax()`, `clamp()` |

---

## 2. Layout method

**Mobile-first.** Write the small-screen rule as the base declaration; add
complexity upward with `min-width` queries. Do not write a desktop layout and
then tear it down with `max-width` overrides.

```css
/* base = mobile */
.grid { display: grid; gap: var(--space-md); }

/* enhance upward */
@media (min-width: 768px) {
  .grid { grid-template-columns: 1fr 1fr; }
}
```

**Prefer intrinsic layout over breakpoints.** A breakpoint you don't need is a
breakpoint you don't maintain:

```css
grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr));
```

The `min(240px, 100%)` guard is required — bare `minmax(240px, 1fr)` overflows
below 240px viewports.

**Breakpoints are content-driven, not device-driven.** Add one where the layout
actually breaks. The shared tokens are:

| Token | Value | Meaning |
|-------|-------|---------|
| `--bp-sm` | 480px | Large phone |
| `--bp-md` | 768px | Tablet / stacked→side-by-side |
| `--bp-lg` | 1024px | Laptop — where the full top nav fits on one row |
| `--max-width` | 1200px | Content cap |

CSS custom properties do not work inside `@media` conditions — write the literal
px value in the query and keep these tokens as the documented reference.

---

## 3. Navigation

Navigation must answer three questions on any screen: *where am I, where can I
go, how do I get back.*

- **Six destinations** (Inicio, Mortalidad, Tarificación, SCR, Sensibilidad,
  Metodología). Keep it flat — no nested menus.
- **Desktop**: horizontal top bar, current page marked with the accent underline.
- **Mobile**: hamburger → full-width drawer. The drawer must:
  - close on route change, on `Escape`, and on backdrop click
  - lock body scroll while open
  - set `aria-expanded` on the trigger and use `aria-current="page"` on the
    active link
  - use ≥ 44px row height
- **Active state is mandatory** in both views. A user must never have to guess
  which page they are on.
- Brand mark always returns to `/`.

---

## 4. Copy and page titles

The audience is technical. Copy is **concise, specific, and unpadded** — the
same discipline as the numbers on screen.

**Browser tab titles** use a pipe separator, most-specific-first, brand last:

```
Mortalidad | SIMA
Tarificación | SIMA
SIMA | Modelación Actuarial          ← home / fallback
```

Rules:
- Pipe (`|`) only. Never `--`, `—`, or `-`.
- ≤ 60 characters total.
- The unique page name leads; `SIMA` is the tail and is clipped first.
- Set titles through the shared `usePageTitle` hook — never assign
  `document.title` ad hoc in a page component.

**Body copy**: lead with the noun, drop filler ("con el fin de", "es importante
notar que"). Subtitles state what the page computes, not that it exists. Both
`es` and `en` strings in `src/i18n.ts` must be updated together and must be
equally terse — a translation that rambles breaks the layout it was measured for.

---

## 5. Shared primitives — use these, do not re-roll them

| Component | Use for | Rule |
|-----------|---------|------|
| `layout/PageLayout` | Every page shell | Owns the title, subtitle, gutters and tab title. No page sets `document.title` itself. |
| `layout/Section` | Every content block | Card with a header. `explainer` is **required** — a reader must never meet a chart without knowing what question it answers. `step` numbers long analytical pages. |
| `layout/SectionRail` | Pages with ≥6 sections | "On this page" nav, passed to `PageLayout`'s `rail` prop. Desktop: sticky right column. Mobile: a 2-column grid showing **every** section at once — never a horizontally-scrolling strip, which hides items. Each `Section` needs a matching `id`. |
| `forms/OptionGroup` | Any "choose one of N" control | Never ship a bare row of buttons. Always a `label`, usually a `hint` saying what changes when you press it. Renders a labelled `radiogroup`. |
| `common/EmptyState` | Any panel awaiting user input | Say what to do next, not just that nothing is here. A blank panel reads as broken. |
| `data/InsightCard` | Deeper theory / commentary | Goes *after* the data it comments on, not before. The Section explainer sets up the data; the InsightCard interprets it. |
| `data/MetricBlock` | Single figures | Value type is fluid and wraps; safe in a 320px column. |

## 6. Component rules

**Tables** — wrap in `overflow-x: auto` with `-webkit-overflow-scrolling: touch`.
Never shrink font below `--text-small` to force a fit. Right-align and
`tabular-nums` all numeric columns.

**Charts (Plotly)** — pass `config.responsive: true` *and* `useResizeHandler`;
`style={{ width: '100%' }}`. Container resizes (drawer open, orientation change)
do not fire `window.resize`, so config alone is not enough. Reduce margins and
hide the modebar under `--bp-md`. 3D surfaces need an explicit height and a
"rotate to explore" affordance on touch.

**Forms** — one column on mobile, label above field, `font-size: 16px` minimum
on inputs, correct `inputmode` for numerics, hint text below the field. Sliders
need a visible numeric readout; on touch the thumb must be ≥ 44px.

**Cards / metric blocks** — must survive both a 320px column and a 12-column
desktop grid without content clipping. Long figures wrap, never truncate.

---

## 7. Verification

Before calling frontend work done:

1. `npm run build` and `npm run lint` in `frontend/` — both clean.
2. Check at **320, 375, 768, 1024, 1440** px wide.
3. Confirm zero horizontal scroll at every width.
4. Tab through the page — focus order is logical and always visible.
5. Open the mobile drawer, navigate, confirm it closes and scroll is restored.
6. Read every new string aloud. If it takes a breath to finish, cut it.
