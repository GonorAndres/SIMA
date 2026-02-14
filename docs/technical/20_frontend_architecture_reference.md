# Frontend Architecture: Technical Reference

**Module:** `frontend/src/` -- React 19 Single-Page Application

**Source files:** 42 TypeScript/TSX files, 10 CSS modules, 1 Vite config

---

## 1. Toolchain and Dependencies

| Tool | Version | Role |
|:-----|:--------|:-----|
| React | 19.2.0 | UI library (concurrent features, StrictMode) |
| TypeScript | 5.9.3 | Static typing (strict mode, erasableSyntaxOnly) |
| Vite | 7.2.4 | Build tool and dev server (HMR, proxy) |
| react-router-dom | 7.13.0 | Client-side routing (BrowserRouter, 6 routes) |
| axios | 1.13.5 | HTTP client (baseURL `/api`, JSON headers) |
| i18next | 25.8.4 | Internationalization (ES/EN, ~130 keys each) |
| react-i18next | 16.5.4 | React bindings for i18next (useTranslation hook) |
| plotly.js | 3.3.1 | Charting engine (scatter, surface, waterfall, heatmap) |
| react-plotly.js | 2.6.0 | React wrapper for Plotly |
| katex | 0.16.28 | LaTeX formula rendering (displayMode) |

### TypeScript Configuration

```
tsconfig.app.json:
  target: ES2022
  module: ESNext
  moduleResolution: bundler
  strict: true
  noUnusedLocals: true
  noUnusedParameters: true
  jsx: react-jsx
```

### Vite Proxy

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

All frontend requests to `/api/*` are proxied to the FastAPI backend at port 8000 during development. The axios client sets `baseURL: '/api'`, so endpoint calls like `api.get('/mortality/lee-carter')` resolve to `http://localhost:8000/api/mortality/lee-carter`.

---

## 2. Routes and Pages

| Route | Component | Description | API Endpoints Consumed |
|:------|:----------|:------------|:-----------------------|
| `/` | `Inicio` | Dashboard with live metrics, k_t chart, COVID teaser, navigation | `GET /mortality/lee-carter`, `POST /scr/compute` |
| `/mortalidad` | `Mortalidad` | Mortality analysis: graduation, surface, Lee-Carter fit, projection, validation | `GET /mortality/lee-carter`, `GET /mortality/projection`, `GET /mortality/validation` (x2), `GET /mortality/graduation`, `GET /mortality/surface`, `GET /mortality/diagnostics` |
| `/tarificacion` | `Tarificacion` | Premium calculator with reserve trajectory and interest rate sensitivity | `POST /pricing/premium`, `POST /pricing/reserve`, `POST /pricing/sensitivity` |
| `/scr` | `SCR` | SCR pipeline: portfolio management, BEL computation, risk module decomposition, solvency gauge | `GET /portfolio/summary`, `POST /portfolio/bel`, `POST /scr/compute`, `POST /portfolio/policy`, `POST /portfolio/reset` |
| `/sensibilidad` | `Sensibilidad` | 4-tab sensitivity analysis: interest rate, mortality shock, cross-country, COVID | `POST /pricing/sensitivity` (x4), `POST /sensitivity/mortality-shock`, `GET /sensitivity/cross-country`, `GET /sensitivity/covid-comparison` |
| `/metodologia` | `Metodologia` | Static methodology page with formulas, metrics, and navigation links | (none -- static content) |

---

## 3. Component Taxonomy

### 3.1. Chart Components (`components/charts/`)

| Component | Plotly Type | Actuarial Concept | Props |
|:----------|:-----------|:------------------|:------|
| `LineChart` | `scatter` (lines) | a_x, b_x, k_t trends, premium curves | `traces[]`, `xTitle`, `yTitle`, `height` |
| `FanChart` | `scatter` (fill + dashed) | k_t projection confidence intervals (95% CI) | `x`, `central`, `lower`, `upper`, `height` |
| `HeatmapChart` | `heatmap` | Premium sensitivity grid (age x interest rate) | `x`, `y`, `z[][]`, `title`, `height` |
| `MortalitySurface` | `surface` (3D) | log(m_{x,t}) surface across ages and years | `ages`, `years`, `values[][]`, `height` |
| `WaterfallChart` | `waterfall` | SCR decomposition (components -> diversification -> total) | `categories[]`, `values[]`, `title`, `height` |
| `SolvencyGauge` | custom HTML/CSS | Solvency ratio (green >=100%, red <100%) | `ratio` |

All Plotly-based charts share defaults from `chartDefaults.ts`:

```typescript
defaultLayout: {
  font: { family: '"Inter", ...', size: 12, color: '#424242' },
  paper_bgcolor: 'transparent',
  plot_bgcolor: '#fff',
  margin: { t: 48, r: 24, b: 48, l: 56 },
  xaxis/yaxis: { gridcolor: '#E0E0E0', linecolor: '#E0E0E0' }
}
defaultConfig: {
  displaylogo: false,
  responsive: true,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d']
}
```

### 3.2. Data Display Components (`components/data/`)

| Component | Purpose | Key Props |
|:----------|:--------|:----------|
| `MetricBlock` | Large monospace number with uppercase label | `label`, `value`, `unit?` |
| `DataTable` | Sortable table with column definitions | `columns: Column[]`, `data: Record[]`, `sortable?` |
| `FormulaBlock` | KaTeX-rendered LaTeX formula in gray box | `latex`, `label?` |
| `DeepDiveLink` | Red arrow link to another page | `text`, `to` (route path) |

`DataTable` supports client-side sorting via `useMemo` + column click handlers. The `Column` interface defines per-column alignment, numeric flag, and optional format function.

### 3.3. Form Components (`components/forms/`)

| Component | Purpose | Controlled Fields |
|:----------|:--------|:-----------------|
| `PremiumForm` | Premium calculation input | product_type (select), age (slider), sum_assured (number), term (slider, conditional), interest_rate (slider) |
| `PolicyForm` | Add policy to portfolio | policy_id, product_type (4 options incl. annuity), issue_age, sum_assured/annual_pension (conditional), term (conditional), duration |
| `SliderInput` | Reusable range slider with label | `label`, `min`, `max`, `step`, `value`, `onChange`, `unit?` |

### 3.4. Layout Components (`components/layout/`)

| Component | Purpose | Behavior |
|:----------|:--------|:---------|
| `TopNav` | Sticky navigation bar | 6 NavLink items from `navItems` array, brand "SIMA", LanguageToggle. Active link gets red underline (`#C41E3A`). |
| `PageLayout` | Content wrapper | `max-width: 1200px`, `padding: 48px`, optional `title`/`subtitle` header |
| `Footer` | Copyright footer | Uppercase, gray text, dynamic year |

### 3.5. Common Components (`components/common/`)

| Component | Purpose |
|:----------|:--------|
| `LanguageToggle` | ES/EN toggle buttons; calls `i18n.changeLanguage()` |
| `LoadingState` | Centered uppercase "Cargando..." message (customizable) |

---

## 4. Custom Hooks (`hooks/useApi.ts`)

Two hooks wrap axios calls with `{data, loading, error}` state management:

```typescript
// Generic GET hook
function useGet<TRes>(endpoint: string) {
  // Returns: { data: TRes | null, loading: boolean, error: string | null, execute }
  // execute(params?) -> calls api.get(endpoint, { params })
}

// Generic POST hook
function usePost<TReq, TRes>(endpoint: string) {
  // Returns: { data: TRes | null, loading: boolean, error: string | null, execute }
  // execute(body: TReq) -> calls api.post(endpoint, body)
}
```

Key design decisions:
- **State reset on each call**: `setState({ data: null, loading: true, error: null })` clears previous results
- **useCallback** memoization on `execute` prevents unnecessary re-renders
- **No caching**: Each `execute()` call triggers a fresh API request
- **No global state**: Each hook instance is local to the component that calls it

### API Client (`api/client.ts`)

```typescript
const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});
```

Single axios instance shared across all hooks. The `/api` prefix is resolved by Vite's proxy during development.

---

## 5. TypeScript Interfaces (`types/index.ts`)

31 interfaces that mirror the backend Pydantic response schemas:

### Mortality Domain (7 interfaces)

| Interface | Backend Schema | Used By |
|:----------|:---------------|:--------|
| `MortalityDataSummary` | `MortalityDataSummaryResponse` | (not currently consumed) |
| `LeeCaterFitResponse` | `LeeCaterFitResponse` | Inicio, Mortalidad |
| `LifeTableResponse` | `LifeTableResponse` | (nested in ProjectionResponse) |
| `ProjectionResponse` | `ProjectionResponse` | Mortalidad |
| `ValidationResponse` | `ValidationResponse` | Mortalidad |
| `GraduationResponse` | `GraduationResponse` | Mortalidad |
| `MortalitySurfaceResponse` | `MortalitySurfaceResponse` | Mortalidad |
| `LCDiagnosticsResponse` | `LCDiagnosticsResponse` | Mortalidad |

### Sensitivity Domain (8 interfaces)

| Interface | Used By |
|:----------|:--------|
| `MortalityShockRequest` | Sensibilidad (tab 2) |
| `MortalityShockResponse` | Sensibilidad (tab 2) |
| `CrossCountryEntry`, `CrossCountryProfile`, `CrossCountryKtProfile`, `CrossCountryResponse` | Sensibilidad (tab 3) |
| `CovidPeriodData`, `CovidPremiumImpact`, `CovidComparisonResponse` | Sensibilidad (tab 4) |

### Pricing Domain (6 interfaces)

| Interface | Used By |
|:----------|:--------|
| `PremiumRequest`, `PremiumResponse` | Tarificacion |
| `ReservePoint`, `ReserveResponse` | Tarificacion |
| `SensitivityPoint`, `SensitivityResponse` | Tarificacion, Sensibilidad |

### Portfolio Domain (4 interfaces)

| Interface | Used By |
|:----------|:--------|
| `PolicyResponse` | SCR |
| `PortfolioSummaryResponse` | SCR |
| `BELBreakdownItem`, `PortfolioBELResponse` | SCR |

### SCR Domain (6 interfaces)

| Interface | Used By |
|:----------|:--------|
| `SCRComponentResult`, `SCRInterestRateResult`, `SCRCatastropheResult` | SCR |
| `SCRAggregationResult`, `RiskMarginResult`, `SolvencyResult` | SCR |
| `SCRResponse` | Inicio, SCR |

---

## 6. Swiss Design System

### 6.1. Color Tokens (`styles/tokens.ts`)

| Token | Hex | Usage |
|:------|:----|:------|
| `black` | `#000000` | Headings, primary text, nav brand |
| `gray700` | `#424242` | Body text, chart text, narrative prose |
| `gray500` | `#9E9E9E` | Labels, subtitles, disabled text |
| `gray200` | `#E0E0E0` | Borders, dividers, grid lines |
| `gray100` | `#F5F5F5` | Formula backgrounds, gauge track |
| `white` | `#FFFFFF` | Page background, plot background |
| `accent` | `#C41E3A` | CTAs, active nav, accent charts, links |
| `accentLight` | `#F5E6E8` | Heatmap low values, FanChart fill |

### 6.2. Typography

| Element | Font | Size | Weight | Extras |
|:--------|:-----|:-----|:-------|:-------|
| Body | Inter | 1rem (16px) | 400 | line-height: 1.6 |
| h1 | Inter | 2.441rem | 600 | letter-spacing: -0.01em |
| h2 | Inter | 1.953rem | 600 | letter-spacing: -0.01em |
| h3 | Inter | 1.563rem | 600 | letter-spacing: -0.01em |
| Labels | Inter | 0.8rem | 500 | uppercase, letter-spacing: 0.05em |
| Numbers | JetBrains Mono | 1.953rem | 600 | tabular-nums |
| Nav links | Inter | 0.875rem | 500 | uppercase, letter-spacing: 0.1em |

The type scale follows a 1.25 ratio (Major Third): 1 -> 1.25 -> 1.563 -> 1.953 -> 2.441.

### 6.3. Spacing System

| Token | Value | Usage |
|:------|:------|:------|
| `xs` | 4px | Inline gaps, label-value spacing |
| `sm` | 8px | Tight padding, slider margins |
| `md` | 16px | Component padding, form field margins |
| `lg` | 24px | Section padding, grid gutter, card padding |
| `xl` | 32px | Between major sections |
| `xxl` | 48px | Page padding, hero spacing, section dividers |

### 6.4. Grid and Layout

- 12-column grid with 24px gutter
- Max content width: 1200px, centered with `margin: 0 auto`
- Page margin: 48px horizontal padding
- Sticky nav bar: 64px height, `z-index: 100`
- Section dividers: 1px solid `#E0E0E0` top border

### 6.5. Design Principles

- **Zero border-radius**: All buttons, inputs, cards use `border-radius: 0`
- **Uppercase labels**: All labels use `text-transform: uppercase` with `letter-spacing: 0.05em`
- **Monospace numbers**: All numeric values use JetBrains Mono with `font-variant-numeric: tabular-nums` for alignment
- **Minimal palette**: Only 8 colors total; accent used sparingly for CTAs and active states
- **Section rhythm**: Consistent 48px vertical padding between sections with 1px border separators

---

## 7. Internationalization (i18n)

### Setup (`i18n.ts`)

```typescript
i18n.use(initReactI18next).init({
  resources: { es: { translation: {...} }, en: { translation: {...} } },
  lng: 'es',            // Default language
  fallbackLng: 'es',
  interpolation: { escapeValue: false },
});
```

### Key Structure

Translation keys are organized by page namespace:

| Namespace | Key Count (approx.) | Example Key |
|:----------|:-------------------:|:------------|
| `nav` | 6 | `nav.mortalidad` |
| `inicio` | 22 | `inicio.covidTeaserDrift` |
| `mortalidad` | 24 | `mortalidad.graduationTitle` |
| `tarificacion` | 8 | `tarificacion.annualPremium` |
| `scr` | 22 | `scr.belBreakdown` |
| `sensibilidad` | 30 | `sensibilidad.covidKtComparison` |
| `metodologia` | 28 | `metodologia.metrics.interestRateRisk` |
| `common` | 5 | `common.retry` |

Total: approximately 130 keys per language (ES and EN).

### Language Toggle

The `LanguageToggle` component calls `i18n.changeLanguage('es'|'en')`. Active language gets black background; inactive gets transparent with gray text. No page reload -- React re-renders all translated text immediately.

---

## 8. Chart-to-Concept Mapping

| Chart Component | Actuarial Concept | Page | Data Source |
|:----------------|:------------------|:-----|:-----------|
| `LineChart` | Lee-Carter parameters (a_x, b_x, k_t) | Mortalidad | `/mortality/lee-carter` |
| `LineChart` | Graduation overlay (raw vs graduated m_x in log-space) | Mortalidad | `/mortality/graduation` |
| `LineChart` | Reserve trajectory (tV over policy duration) | Tarificacion | `/pricing/reserve` |
| `LineChart` | Premium vs interest rate (3 products) | Sensibilidad | `/pricing/sensitivity` |
| `LineChart` | Mortality shock response curve | Sensibilidad | `/sensitivity/mortality-shock` |
| `LineChart` | Cross-country k_t, a_x, b_x overlays | Sensibilidad | `/sensitivity/cross-country` |
| `LineChart` | COVID k_t comparison (pre-COVID vs full period) | Sensibilidad | `/sensitivity/covid-comparison` |
| `FanChart` | k_t projection with 95% CI (central +/- 1.96*sigma*sqrt(h)) | Mortalidad | `/mortality/projection` |
| `HeatmapChart` | Premium heatmap: age (rows) x interest rate (columns) | Sensibilidad | `/pricing/sensitivity` (x5 ages) |
| `MortalitySurface` | 3D log(m_{x,t}) surface | Mortalidad | `/mortality/surface` |
| `WaterfallChart` | SCR decomposition (4 risk modules - diversification = total) | SCR | `/scr/compute` |
| `SolvencyGauge` | Solvency ratio (available capital / SCR) | SCR | `/scr/compute` |

---

## 9. State Management

The frontend uses **no global state management** (no Redux, Zustand, or Context API for application state). All state is local to each page component:

| State Pattern | Implementation | Example |
|:-------------|:---------------|:--------|
| API data | `useGet`/`usePost` hooks (local `useState`) | `const lc = useGet<LeeCaterFitResponse>(...)` |
| Form inputs | Component-local `useState` | `const [age, setAge] = useState(40)` |
| UI toggles | Component-local `useState` | `const [validationTab, setValidationTab] = useState('cnsf')` |
| Language | i18next singleton (external to React state) | `i18n.changeLanguage('en')` |

This is possible because:
1. No cross-page state sharing is needed (each page fetches its own data)
2. The backend holds the portfolio state (policies persist server-side in memory)
3. Language is global but managed by i18next, not React state

---

## 10. File Structure

```
frontend/
  package.json              # Dependencies, scripts (dev, build, lint, preview)
  vite.config.ts            # React plugin, /api proxy to :8000
  tsconfig.json             # References app + node configs
  tsconfig.app.json         # Strict TS for src/ (ES2022, bundler resolution)
  tsconfig.node.json        # TS for vite.config.ts (ES2023)
  src/
    main.tsx                # Entry: createRoot, StrictMode, imports i18n + global.css
    App.tsx                 # BrowserRouter, TopNav, Routes (6), Footer
    i18n.ts                 # i18next init with ES/EN resources (~130 keys each)
    api/
      client.ts             # Axios instance (baseURL: '/api')
    hooks/
      useApi.ts             # useGet<T>, usePost<TReq, TRes> hooks
    types/
      index.ts              # 31 TypeScript interfaces mirroring Pydantic schemas
    styles/
      tokens.ts             # Design tokens (colors, fonts, typeScale, spacing, grid)
      global.css            # CSS reset, typography, utility classes
      swiss.module.css       # Swiss design utility classes (grid, buttons, cards)
    components/
      charts/
        chartDefaults.ts    # Shared Plotly layout + config
        LineChart.tsx        # Multi-trace line chart
        FanChart.tsx         # Central + CI band (projection)
        HeatmapChart.tsx     # 2D color grid (sensitivity)
        MortalitySurface.tsx # 3D surface plot
        WaterfallChart.tsx   # Stacked bar with totals (SCR decomposition)
        SolvencyGauge.tsx    # Custom HTML gauge (ratio bar + 100% marker)
      data/
        DataTable.tsx        # Sortable table with Column interface
        DataTable.module.css
        MetricBlock.tsx      # Large number + label display
        FormulaBlock.tsx     # KaTeX-rendered LaTeX formula
        DeepDiveLink.tsx     # Internal navigation arrow link
      forms/
        PremiumForm.tsx      # Premium calculation form
        PremiumForm.module.css
        PolicyForm.tsx       # Policy addition form (SCR page)
        SliderInput.tsx      # Reusable range slider
      layout/
        TopNav.tsx           # Sticky nav bar with NavLink items
        TopNav.module.css
        PageLayout.tsx       # Content wrapper (1200px max, 48px padding)
        Footer.tsx           # Copyright footer
      common/
        LanguageToggle.tsx   # ES/EN toggle
        LoadingState.tsx     # Loading spinner text
    pages/
      Inicio.tsx             # Dashboard (+ Inicio.module.css)
      Mortalidad.tsx         # Mortality analysis (+ Mortalidad.module.css)
      Tarificacion.tsx       # Pricing (+ Tarificacion.module.css)
      SCR.tsx                # Capital requirements (+ SCR.module.css)
      Sensibilidad.tsx       # Sensitivity analysis (+ Sensibilidad.module.css)
      Metodologia.tsx        # Methodology (+ Metodologia.module.css)
```

---

## 11. Page Architecture Patterns

### Data Loading Pattern

All pages that consume API data follow the same pattern:

```typescript
export default function PageName() {
  const apiCall = useGet<ResponseType>('/endpoint');

  useEffect(() => {
    apiCall.execute(params);
  }, []);

  return (
    <PageLayout>
      {apiCall.loading && <LoadingState message="..." />}
      {apiCall.error && <p>Error: {apiCall.error}</p>}
      {apiCall.data && (
        // Render data
      )}
    </PageLayout>
  );
}
```

### Conditional Rendering Pattern

Each API call independently manages its loading/error/data states. Components render conditionally based on `data !== null`:

```
loading -> LoadingState
error   -> Error message (red text)
data    -> MetricBlock + charts + tables
```

### Multi-Tab Pattern (Sensibilidad, Mortalidad)

Tab state is managed with `useState<TabKey>('default_tab')`. Each tab's content is conditionally rendered based on `activeTab === 'key'`. API calls for all tabs are initiated on mount, so data is ready when the user switches tabs.
