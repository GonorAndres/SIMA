/* ── Mortality ── */

export interface MortalityDataSummary {
  country: string;
  sex: string;
  age_range: number[];
  year_range: number[];
  shape: number[];
  mx_min: number;
  mx_max: number;
  mx_mean: number;
}

export interface LeeCaterFitResponse {
  ages: number[];
  years: number[];
  ax: number[];
  bx: number[];
  kt: number[];
  explained_variance: number;
  drift: number;
  sigma: number;
  validations: Record<string, boolean>;
}

export interface LifeTableResponse {
  ages: number[];
  l_x: number[];
  q_x: number[];
  d_x: number[];
  min_age: number;
  max_age: number;
}

export interface ProjectionResponse {
  projected_years: number[];
  kt_central: number[];
  drift: number;
  sigma: number;
  life_table?: LifeTableResponse;
}

export interface ValidationResponse {
  name: string;
  rmse: number;
  max_ratio: number;
  min_ratio: number;
  mean_ratio: number;
  n_ages: number;
  ages: number[];
  qx_ratios: number[];
  qx_differences: number[];
}

/* ── Graduation & Diagnostics ── */

export interface GraduationResponse {
  ages: number[];
  raw_mx: number[];
  graduated_mx: number[];
  residuals: number[];
  roughness_raw: number;
  roughness_graduated: number;
  roughness_reduction: number;
  lambda_param: number;
}

export interface MortalitySurfaceResponse {
  ages: number[];
  years: number[];
  log_mx: number[][];
}

export interface LCDiagnosticsResponse {
  rmse: number;
  max_abs_error: number;
  mean_abs_error: number;
  explained_variance: number;
  residuals_sample: { age: number; year: number; residual: number }[];
}

/* ── Sensitivity ── */

export interface MortalityShockRequest {
  age: number;
  sum_assured: number;
  product_type: string;
  factors: number[];
  term?: number;
}

export interface MortalityShockResponse {
  factors: number[];
  premiums: number[];
  base_premium: number;
  pct_changes: number[];
  age: number;
  product_type: string;
}

export interface CrossCountryEntry {
  country: string;
  drift: number;
  explained_var: number;
  sigma: number;
  q60: number;
  premium_age40: number;
}

export interface CrossCountryProfile {
  country: string;
  ages: number[];
  values: number[];
}

export interface CrossCountryKtProfile {
  country: string;
  years: number[];
  kt: number[];
}

export interface CrossCountryResponse {
  countries: CrossCountryEntry[];
  kt_profiles: CrossCountryKtProfile[];
  ax_profiles: CrossCountryProfile[];
  bx_profiles: CrossCountryProfile[];
}

export interface CovidPeriodData {
  drift: number;
  sigma: number;
  explained_var: number;
  kt: number[];
  years: number[];
}

export interface CovidPremiumImpact {
  age: number;
  pre_covid: number;
  full: number;
  pct_change: number;
}

export interface CovidComparisonResponse {
  pre_covid: CovidPeriodData;
  full_period: CovidPeriodData;
  premium_impact: CovidPremiumImpact[];
}

/* ── Pricing ── */

export interface PremiumRequest {
  product_type: string;
  age: number;
  sum_assured: number;
  interest_rate: number;
  term?: number;
}

export interface PremiumResponse {
  product_type: string;
  age: number;
  sum_assured: number;
  interest_rate: number;
  term?: number;
  annual_premium: number;
  premium_rate: number;
}

export interface ReservePoint {
  duration: number;
  age: number;
  reserve: number;
}

export interface ReserveResponse {
  product_type: string;
  issue_age: number;
  sum_assured: number;
  interest_rate: number;
  term?: number;
  annual_premium: number;
  trajectory: ReservePoint[];
}

export interface SensitivityPoint {
  interest_rate: number;
  annual_premium: number;
}

export interface SensitivityResponse {
  product_type: string;
  age: number;
  sum_assured: number;
  results: SensitivityPoint[];
}

/* ── Portfolio ── */

export interface PolicyResponse {
  policy_id: string;
  product_type: string;
  issue_age: number;
  attained_age: number;
  sum_assured: number;
  annual_pension: number;
  term?: number;
  duration: number;
  is_death_product: boolean;
  is_annuity: boolean;
}

export interface PortfolioSummaryResponse {
  n_policies: number;
  n_death: number;
  n_annuity: number;
  total_sum_assured: number;
  total_annual_pension: number;
  policies: PolicyResponse[];
}

export interface BELBreakdownItem {
  policy_id: string;
  product_type: string;
  issue_age: number;
  attained_age: number;
  duration: number;
  bel: number;
  sum_assured?: number;
  annual_pension?: number;
}

export interface PortfolioBELResponse {
  total_bel: number;
  death_bel: number;
  annuity_bel: number;
  n_policies: number;
  n_death: number;
  n_annuity: number;
  breakdown: BELBreakdownItem[];
}

/* ── SCR ── */

export interface SCRComponentResult {
  bel_base: number;
  bel_stressed: number;
  scr: number;
  shock?: number;
}

export interface SCRInterestRateResult {
  bel_base: number;
  bel_up: number;
  bel_down: number;
  scr: number;
  rate_up: number;
  rate_down: number;
}

export interface SCRCatastropheResult {
  scr: number;
  cat_shock_factor: number;
}

export interface SCRAggregationResult {
  scr_aggregated: number;
  sum_individual: number;
  diversification_benefit: number;
  diversification_pct?: number;
}

export interface RiskMarginResult {
  risk_margin: number;
  coc_rate: number;
  duration: number;
  annuity_factor: number;
}

export interface SolvencyResult {
  ratio: number;
  ratio_pct: number;
  available_capital: number;
  scr_total: number;
  is_solvent: boolean;
}

export interface SCRResponse {
  bel_base: number;
  bel_death: number;
  bel_annuity: number;
  mortality: SCRComponentResult;
  longevity: SCRComponentResult;
  interest_rate: SCRInterestRateResult;
  catastrophe: SCRCatastropheResult;
  life_aggregation: SCRAggregationResult;
  total_aggregation: SCRAggregationResult;
  risk_margin: RiskMarginResult;
  technical_provisions: number;
  solvency?: SolvencyResult;
}
