# Frontend Architecture: Intuitive Reference

**Module:** `frontend/src/` -- React 19 Single-Page Application

---

## 1. The Dashboard Metaphor

Think of the SIMA frontend as a **control room dashboard** for an actuarial engine. The engine (backend) does all the heavy computation -- fitting Lee-Carter models, computing premiums, aggregating SCR components. The dashboard's job is to let you see, interact with, and explore the results.

The dashboard has 6 screens (pages), each dedicated to a different aspect of the actuarial pipeline:

```
DASHBOARD SCREENS
=================

  /             -> Executive summary: live metrics, quick navigation
  /mortalidad   -> Mortality laboratory: data, graduation, model, projection
  /tarificacion -> Pricing workbench: form, premium result, reserve trajectory
  /scr          -> Capital control room: portfolio, risk modules, solvency gauge
  /sensibilidad -> What-if explorer: interest rate, mortality shocks, cross-country
  /metodologia  -> Theory reference: formulas, metrics, navigation links
```

---

## 2. How Data Flows: Browser to Backend and Back

```
FRONTEND DATA FLOW
===================

  User action (page load, button click, slider drag)
       |
       v
  Page component calls  useGet.execute()  or  usePost.execute(body)
       |
       v
  useApi hook:
    1. setState({ data: null, loading: true, error: null })
    2. axios.get/post('/api/endpoint', ...)
       |
       v  (Vite proxy in dev: /api/* -> http://localhost:8000/api/*)
  FastAPI backend processes request, returns JSON
       |
       v
  useApi hook:
    3. setState({ data: response, loading: false, error: null })
       |
       v
  React re-renders:
    - loading=true  ->  <LoadingState /> (gray uppercase text)
    - error!=null   ->  red error text
    - data!=null    ->  MetricBlocks + Charts + Tables
```

```
INTUITION
=========
Every API call has exactly 3 possible outcomes: loading, error, or data.
The UI renders exactly one of these states. There is no "stale data" --
when a new request starts, the old data is cleared to null.
```

---

## 3. The Hook Pattern: useGet and usePost

The two custom hooks are the backbone of all data fetching:

```
USE PATTERN
===========

// In a page component:
const lc = useGet<LeeCaterFitResponse>('/mortality/lee-carter');

// lc exposes:
//   lc.data      -> the response (or null)
//   lc.loading   -> boolean
//   lc.error     -> error message (or null)
//   lc.execute() -> triggers the API call

useEffect(() => {
  lc.execute();      // Fire on page mount
}, []);

// In JSX:
{lc.loading && <LoadingState />}
{lc.data && <LineChart traces={[...lc.data...]} />}
```

```
ROLE
====
The hooks replace what Redux/Zustand would do in a larger app.
Since each page fetches its own data independently, there is no
need for global state. Each useGet/usePost instance is a self-
contained {data, loading, error} mini-store.
```

---

## 4. Component Categories: Five Families

The 18 components belong to five families, each with a distinct role:

```
COMPONENT FAMILIES
==================

  charts/     ->  "What does the data look like?"
                  LineChart, FanChart, HeatmapChart,
                  MortalitySurface, WaterfallChart, SolvencyGauge

  data/       ->  "What are the key numbers and facts?"
                  MetricBlock, DataTable, FormulaBlock, DeepDiveLink

  forms/      ->  "What does the user want to compute?"
                  PremiumForm, PolicyForm, SliderInput

  layout/     ->  "Where are we in the app?"
                  TopNav, PageLayout, Footer

  common/     ->  "What's the current state?"
                  LanguageToggle, LoadingState
```

### Chart-to-Concept Mapping

Each chart type was chosen to match the actuarial concept it represents:

```
CHART           CONCEPT                   WHY THIS CHART TYPE
=========       =====================     ==================================
LineChart       a_x, b_x, k_t trends     Continuous functions of age or year
FanChart        k_t projection + CI       Central forecast needs uncertainty band
HeatmapChart    Age x Rate sensitivity    Two-dimensional continuous variable
MortalitySurface log(m_{x,t})             Three-dimensional age-year-rate surface
WaterfallChart  SCR decomposition         Shows how components add/subtract to total
SolvencyGauge   Solvency ratio            Single number on a pass/fail scale
```

```
INTUITION
=========
FanChart = "We don't know the future, but we know the range."
The filled area between the dashed lines is the 95% confidence interval:
central +/- 1.96 * sigma * sqrt(h), where h is years into the future.
The band widens over time because uncertainty compounds.

WaterfallChart = "Where does the capital requirement come from?"
Four risk modules stack up (mortality, longevity, interest rate, catastrophe),
then diversification removes some (negative bar), leaving the total SCR.
```

---

## 5. The Swiss Design System

The visual language is inspired by Swiss/International Typographic Style:

```
DESIGN PRINCIPLES
=================

1. ZERO BORDER-RADIUS
   All buttons, inputs, cards, sliders use border-radius: 0
   -> Creates a clean, architectural feel; no rounded corners anywhere

2. UPPERCASE LABELS
   All labels: text-transform: uppercase + letter-spacing: 0.05em
   -> Labels are metadata, not content; uppercase signals "this is a category"

3. MONOSPACE NUMBERS
   All numeric values: JetBrains Mono + tabular-nums
   -> Numbers in tables and metrics align perfectly vertically

4. MINIMAL PALETTE (8 colors)
   Black (#000)       -- headings, primary text
   Gray 700 (#424242) -- body text, chart text
   Gray 500 (#9E9E9E) -- labels, subtitles
   Gray 200 (#E0E0E0) -- borders, grid lines
   Gray 100 (#F5F5F5) -- formula backgrounds
   White (#FFF)       -- page background
   Accent (#C41E3A)   -- CTAs, active nav, links, chart accent
   Accent Light (#F5E6E8) -- heatmap low values

5. SECTION RHYTHM
   48px vertical padding between sections
   1px solid #E0E0E0 top border as separator
   -> Creates a consistent visual beat down the page
```

```
INTUITION
=========
The type scale uses a 1.25 ratio (Major Third):
  body = 1rem (16px)
  h3   = 1.563rem
  h2   = 1.953rem
  h1   = 2.441rem

This ratio was chosen by Robert Bringhurst and is standard in
Swiss typography -- each step is 25% larger, creating a subtle
but perceptible hierarchy.
```

---

## 6. How i18n Works

The app supports Spanish (default) and English:

```
TRANSLATION FLOW
================

1. i18n.ts defines all text in a nested object:
   { es: { translation: { nav: { mortalidad: 'MORTALIDAD' }, ... } },
     en: { translation: { nav: { mortalidad: 'MORTALITY' }, ... } } }

2. Every component calls:  const { t } = useTranslation();

3. Text is rendered as:  {t('nav.mortalidad')}
   -> Returns 'MORTALIDAD' (if language=es) or 'MORTALITY' (if language=en)

4. LanguageToggle component calls:  i18n.changeLanguage('en')
   -> All components re-render with new translations instantly
   -> No page reload, no API calls

TOTAL KEYS: ~130 per language
NAMESPACES: nav, inicio, mortalidad, tarificacion, scr, sensibilidad, metodologia, common
```

---

## 7. TypeScript Interfaces: The Contract

The frontend defines 31 TypeScript interfaces in `types/index.ts`. These mirror the backend Pydantic schemas exactly:

```
BACKEND (Pydantic)              FRONTEND (TypeScript)
====================            =====================
class LeeCaterFitResponse       interface LeeCaterFitResponse
  ages: List[int]                 ages: number[]
  ax: List[float]                 ax: number[]
  explained_variance: float       explained_variance: number
  ...                             ...

class SCRResponse               interface SCRResponse
  mortality: SCRComponentResult   mortality: SCRComponentResult
  solvency?: SolvencyResult       solvency?: SolvencyResult
  ...                             ...
```

```
INTUITION
=========
The TypeScript interfaces serve the same role as a Rosetta Stone:
they ensure the frontend "speaks the same language" as the backend.
If the backend adds a field, the TypeScript compiler will catch any
frontend code that doesn't handle it (thanks to strict mode).
```

---

## 8. Page-by-Page Architecture

### Inicio (Dashboard)

```
FORMULA: No computation -- displays live data from two API calls
USE:     Executive overview; first thing a visitor sees
DATA:    GET /mortality/lee-carter  ->  explained_var, drift, k_t chart
         POST /scr/compute          ->  SCR total, solvency ratio
PATTERN: useEffect fires both calls on mount; conditional rendering
```

### Mortalidad (Mortality Laboratory)

```
FORMULA: ln(m_{x,t}) = a_x + b_x * k_t + epsilon_{x,t}
USE:     Full mortality pipeline visualization (7 API calls)
DATA:    graduation, surface, lee-carter, diagnostics, projection,
         validation (CNSF), validation (EMSSA)
PATTERN: All 7 calls fire on mount; page renders top-to-bottom as data arrives
         Tab state for CNSF/EMSSA validation comparison
```

### Tarificacion (Pricing Workbench)

```
FORMULA: P = SA * M_x / N_x  (whole life)
         tV = SA * A_{x+t} - P * a_due_{x+t}  (reserve)
USE:     Interactive premium calculator
DATA:    POST /pricing/premium   -> annual premium, rate
         POST /pricing/reserve   -> trajectory [{duration, reserve}]
         POST /pricing/sensitivity -> [{rate, premium}] at 7 rates
PATTERN: Form submission triggers 3 parallel API calls
```

### SCR (Capital Control Room)

```
FORMULA: SCR = sqrt(vec' * C * vec)
USE:     Full SCR pipeline with portfolio management
DATA:    GET /portfolio/summary  -> policy listing
         POST /scr/compute       -> 4 risk modules, aggregation, solvency
         POST /portfolio/bel     -> per-policy BEL breakdown
PATTERN: Portfolio loads on mount; SCR computation triggered by button click
         PolicyForm adds policies; Reset clears portfolio
         WaterfallChart decomposes SCR; SolvencyGauge shows ratio
```

### Sensibilidad (What-If Explorer)

```
USE:     Four-tab exploration of mortality and pricing sensitivity
TABS:    1. Interest Rate  -> 3 premium curves + heatmap
         2. Mortality Shock -> configurable age/product shock response
         3. Cross-Country  -> Mexico/USA/Spain comparison (table + 3 charts)
         4. COVID-19       -> pre-COVID vs full period drift + premium impact
PATTERN: Tabs 3 and 4 load on mount (GET); Tabs 1 and 2 load on button click (POST)
```

### Metodologia (Theory Reference)

```
USE:     Static page -- no API calls
CONTENT: 8 numbered sections with FormulaBlock + MetricBlock + DeepDiveLink
         Covers: Data, Graduation, Lee-Carter, Projection, Pricing, Reserves, SCR, Resources
PATTERN: Pure component with no hooks except useTranslation
```

---

## 9. Interview Q&A

**Q: "Why no global state management like Redux?"**

A: "Each page in SIMA is self-contained -- it fetches its own data from the API when it mounts, and there is no cross-page state sharing. The portfolio state lives on the backend (server-side in-memory), and language state is managed by i18next's singleton. With only local `useState` and custom hooks, adding Redux would introduce complexity without solving any actual problem. The `useGet`/`usePost` hooks give each component its own `{data, loading, error}` mini-store, which is all we need."

**Q: "How does the frontend communicate with the backend?"**

A: "Through a single axios instance with `baseURL: '/api'`. During development, Vite proxies all `/api/*` requests to `http://localhost:8000`, where FastAPI is running. In production, you'd configure nginx or a similar reverse proxy. Two custom hooks -- `useGet` for GET requests and `usePost` for POST requests -- wrap axios with React state management: they track loading, error, and data states automatically."

**Q: "Why Plotly instead of D3 or Chart.js?"**

A: "Plotly was chosen for three specific capabilities: 3D surface plots (for the mortality surface), waterfall charts (for SCR decomposition), and built-in interactivity (zoom, pan, hover tooltips) without any custom code. D3 would require building every chart type from scratch, and Chart.js doesn't support 3D surfaces. The tradeoff is bundle size (~3MB for Plotly), but for a data-heavy actuarial dashboard, the interactive features justify it."

**Q: "Explain your design system."**

A: "SIMA uses a Swiss-inspired design system with 8 colors, zero border-radius, and a Major Third type scale (1.25 ratio). All labels are uppercase with letter-spacing for hierarchical clarity. Numbers use JetBrains Mono with tabular-nums so they align vertically in tables and metric blocks. The accent color (crimson #C41E3A) is used only for calls-to-action, active navigation, and chart highlights -- never for body text. The result is a clean, data-first interface where numbers and charts take precedence over decorative elements."
