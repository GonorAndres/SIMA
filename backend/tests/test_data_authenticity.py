"""
Data Authenticity Tests
=======================

Every other test in this suite validates *format*: the right columns, no NaN,
m_x = d_x / L_x. Format is exactly what synthetic data satisfies. Until
2026-08-02 the files under ``backend/data/hmd/usa`` and ``backend/data/hmd/spain``
were Gompertz-Makeham curves produced by ``backend/scripts/generate_mock_hmd.py``,
and 216 green tests said nothing about it, because no test ever asked whether the
numbers were true.

These tests ask. Each one anchors on something a generator has no reason to
reproduce:

1. **Header provenance** -- the generator stamps "synthetic mock data for CI
   testing" into line 2. A real HMD extract carries
   "Last modified: ...; Methods Protocol: v6 (2017)".
2. **Implied national population** -- exposures summed over all ages must land
   near the country's actual population.
3. **A known event** -- any file covering 2020 must show COVID-19. The real
   series show +18.5% (USA) and +18.3% (Spain) deaths from 2019 to 2020; the
   synthetic ones show a smooth trend through it.
4. **Sex ratio at the young-adult accident hump** -- male mortality runs ~2.5-3x
   female around ages 20-24. A generator that applies a flat sex multiplier
   gives ~1.35.
5. **Poisson roughness** -- log death rates from finite counts cannot be smoother
   than sampling noise allows. sd(second differences) must be within reach of
   sqrt(6 / mean_deaths). Fitted curves are far below that floor.

Ported from the standalone verifier used during the 2026-08-02 data swap.

Skipping
--------
CI ships only the committed fixtures under ``backend/data/mock/``. Real HMD data
is not redistributable (CC BY 4.0 covers the estimates, but HMD asks that copies
not be redistributed) and real INEGI/CONAPO extracts are gitignored, so these
tests SKIP when the real files are absent and RUN when they are present. A skip
is not a pass -- see DATA.md for how to obtain the files.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"
HMD_DIR = DATA_DIR / "hmd"
REAL_DEATHS = DATA_DIR / "inegi" / "inegi_deaths.csv"
REAL_POP = DATA_DIR / "conapo" / "conapo_population.csv"

SYNTHETIC_MARKERS = ("synthetic", "mock")

# Real-world anchors. Sources: HMD country pages and the national statistics
# offices behind them. Deliberately loose -- the point is to separate "a real
# country" from "a curve", not to pin a figure.
EXPECTED = {
    "usa": {
        "series_starts_by": 1940,  # real USA series starts 1933
        "population_millions": 330,
        "probe_year": 2015,
    },
    "spain": {
        "series_starts_by": 1930,  # real Spain series starts 1908
        "population_millions": 47,
        "probe_year": 2015,
    },
}

POPULATION_TOLERANCE = 2.0  # implied population must be within this factor
COVID_MIN_EXCESS_PCT = 10.0  # real 2020 excess is ~18% in both countries
SEX_RATIO_BAND = (1.8, 4.5)  # real ages 20-24 sit at 2.6-2.9
ROUGHNESS_FLOOR_FRACTION = 0.35  # observed 1.07x (USA) and 0.75x (Spain) of the floor

HMD_KINDS = ("Mx", "Deaths", "Exposures")


# =============================================================================
# Helpers
# =============================================================================


def _header(path: Path) -> str:
    """First two lines of a file, lowercased."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        return "".join(next(fh, "") for _ in range(2)).lower()


def _looks_synthetic(path: Path) -> bool:
    return any(marker in _header(path) for marker in SYNTHETIC_MARKERS)


def _hmd_paths(country: str) -> dict[str, Path]:
    base = HMD_DIR / country
    return {kind: base / f"{kind}_1x1_{country}.txt" for kind in HMD_KINDS}


def _has_real_hmd(country: str) -> bool:
    """
    True when genuine-looking HMD files are on the real-data path.

    Deliberately content-based, not path-based. The whole failure being guarded
    against was a synthetic file sitting in the real-data directory, where a
    path check would have called it real and skipped nothing.
    """
    paths = _hmd_paths(country)
    return all(p.exists() for p in paths.values()) and not any(
        _looks_synthetic(p) for p in paths.values()
    )


def _read_hmd(path: Path) -> pd.DataFrame:
    """Parse an HMD 1x1 file into Year, Age, Female, Male, Total."""
    df = pd.read_csv(path, sep=r"\s+", skiprows=2, na_values=".")
    df["Age"] = pd.to_numeric(df["Age"].astype(str).str.replace("+", "", regex=False))
    return df


def _is_staged_ci_fixture(path: Path) -> bool:
    """
    True if `path` is byte-identical to the committed fixture of the same name.

    ci.yml copies backend/data/mock/hmd/* into backend/data/hmd/* so the
    HMD-dependent tests can run at all. Those staged copies are a known,
    reviewable artifact -- not a claim that the data is real -- and they are
    what the deploy gate (.github/scripts/data_gate.py) exists to reject.
    """
    mirror = DATA_DIR / "mock" / "hmd" / path.parent.name / path.name
    return mirror.exists() and mirror.read_bytes() == path.read_bytes()


@pytest.fixture(scope="module")
def hmd(request):
    """Parsed HMD frames for one country, or a skip when real data is absent."""
    country = request.param
    if not _has_real_hmd(country):
        pytest.skip(
            f"no real HMD extract for {country} under {HMD_DIR / country} "
            "(HMD data is not redistributable -- see DATA.md)"
        )
    frames: dict[str, object] = {"country": country}
    frames.update({kind: _read_hmd(path) for kind, path in _hmd_paths(country).items()})
    return frames


def _countries():
    return list(EXPECTED)


parametrize_country = pytest.mark.parametrize("hmd", _countries(), indirect=True)


# =============================================================================
# Check 1: no file may advertise itself as generated
# =============================================================================


@pytest.mark.parametrize("country", _countries())
def test_no_unknown_synthetic_file_on_the_real_data_path(country):
    """
    THEORY: provenance has to be readable from the artifact itself. A file whose
    own header says "synthetic mock data for CI testing" is not evidence about
    American or Spanish mortality and has no business on the path the production
    pipeline reads.

    One exception, and only one: ci.yml deliberately stages the committed
    fixtures there so the HMD-dependent tests can run without redistributable
    data. Those copies are byte-identical to backend/data/mock/hmd/, and the
    deploy gate rejects them before anything ships -- ci.yml even asserts that it
    does. Anything else carrying a synthetic marker is an unreviewed generated
    file sitting where real data belongs, which is exactly the state this project
    was in until 2026-08-02.

    Note what does NOT reach this test: an *unmarked* fabrication. That one is
    treated as real by the fixture above, so the five substantive checks run
    against it -- and fail.
    """
    paths = _hmd_paths(country)
    present = {kind: p for kind, p in paths.items() if p.exists()}
    if not present:
        pytest.skip(f"no HMD files for {country} (see DATA.md)")

    offenders = {
        kind: _header(p).strip()
        for kind, p in present.items()
        if _looks_synthetic(p) and not _is_staged_ci_fixture(p)
    }
    assert not offenders, (
        f"{country}: files on the real-data path declare themselves generated and do "
        f"not match any committed fixture: {offenders}. "
        "Synthetic data belongs under backend/data/mock/hmd/."
    )


def test_committed_mock_hmd_still_declares_itself_synthetic():
    """
    THEORY: the negative control. The mock fixtures must keep saying they are
    mock, otherwise the marker-based provenance check above (and the identical
    one in the API's precomputed loader) silently stops discriminating.
    """
    mock_dir = DATA_DIR / "mock" / "hmd"
    if not mock_dir.exists():
        pytest.skip("no committed mock HMD fixtures")
    files = sorted(mock_dir.glob("*/*_1x1_*.txt"))
    assert files, f"no mock HMD files under {mock_dir}"
    for path in files:
        assert _looks_synthetic(path), f"{path} lost its synthetic marker"


# =============================================================================
# Check 2: implied national population
# =============================================================================


@parametrize_country
def test_implied_population_matches_the_country(hmd):
    """
    THEORY: exposure is person-years lived. Summed over every age in a year it
    reconstructs the national population. A generator that only fits a mortality
    curve has no reason to land anywhere near the right headcount.
    """
    country = hmd["country"]
    spec = EXPECTED[country]
    exposures = hmd["Exposures"]
    year = spec["probe_year"]
    assert year in set(exposures["Year"]), f"{country}: {year} not covered"

    implied = float(exposures.loc[exposures["Year"] == year, "Total"].sum())
    expected = spec["population_millions"] * 1e6
    ratio = implied / expected
    assert 1 / POPULATION_TOLERANCE < ratio < POPULATION_TOLERANCE, (
        f"{country} {year}: implied population {implied / 1e6:.1f} M against "
        f"~{spec['population_millions']} M expected ({ratio:.2f}x)"
    )


@parametrize_country
def test_series_starts_where_the_real_one_does(hmd):
    """
    THEORY: coverage is provenance. HMD's USA series begins in 1933 and Spain's
    in 1908. The synthetic generator started both in 1990, because that is the
    window the pipeline happens to fit.
    """
    country = hmd["country"]
    first_year = int(hmd["Mx"]["Year"].min())
    assert first_year <= EXPECTED[country]["series_starts_by"], (
        f"{country}: series starts {first_year}; the real one starts no later "
        f"than {EXPECTED[country]['series_starts_by']}"
    )


# =============================================================================
# Check 3: a known event -- COVID-19 in 2020
# =============================================================================


@parametrize_country
def test_2020_shows_covid_excess_mortality(hmd):
    """
    THEORY: 2020 is the strongest identifiable shock in modern mortality data.
    Any genuine file whose range includes it must show it. A smooth trend
    through 2020 means the numbers were modelled, not observed.
    """
    country = hmd["country"]
    deaths = hmd["Deaths"]
    years = set(deaths["Year"])
    if not {2019, 2020} <= years:
        pytest.skip(f"{country}: series does not cover 2019-2020")

    d19 = float(deaths.loc[deaths["Year"] == 2019, "Total"].sum())
    d20 = float(deaths.loc[deaths["Year"] == 2020, "Total"].sum())
    excess_pct = (d20 / d19 - 1) * 100
    assert excess_pct > COVID_MIN_EXCESS_PCT, (
        f"{country}: 2019->2020 deaths moved {excess_pct:+.1f}%. A file covering "
        f"2020 must carry the pandemic (real: USA +18.5%, Spain +18.3%)."
    )


# =============================================================================
# Check 4: sex ratio at the young-adult accident hump
# =============================================================================


@parametrize_country
def test_sex_ratio_at_the_accident_hump(hmd):
    """
    THEORY: the accident hump is a behavioural, not biological, feature -- a bump
    in male mortality around ages 18-25 driven by violence and road deaths. It
    does not follow from a mortality law, so a Gompertz-Makeham curve with a
    single sex multiplier flattens it to about 1.35. Real data sits at 2.5-3.0.
    """
    country = hmd["country"]
    mx = hmd["Mx"]
    year = 2010 if 2010 in set(mx["Year"]) else int(mx["Year"].max())
    hump = mx[(mx["Year"] == year) & (mx["Age"].between(20, 24))]
    hump = hump[hump["Female"] > 0]
    assert len(hump) >= 3, f"{country}: too few ages in the hump window"

    ratio = float((hump["Male"] / hump["Female"]).mean())
    low, high = SEX_RATIO_BAND
    assert low < ratio < high, (
        f"{country} {year}: male/female m_x ratio at ages 20-24 is {ratio:.2f}, "
        f"outside [{low}, {high}]. A flat sex multiplier gives ~1.35."
    )


# =============================================================================
# Check 5: Poisson roughness floor
# =============================================================================


@parametrize_country
def test_log_rates_are_not_smoother_than_poisson_noise_allows(hmd):
    """
    THEORY: d_x is a count. Its sampling error is Poisson, so log(m_x) carries
    noise of roughly 1/sqrt(d_x). Second-differencing along age amplifies that by
    sqrt(6), giving a floor of sqrt(6 / mean_deaths) on the roughness of any
    genuine unsmoothed series.

    A fitted curve has no sampling error at all and falls far below the floor --
    which is the tell, and the reason graduation (a07) exists in the first place:
    you cannot smooth data that was never rough.

    Observed on the real files: 1.07x the floor (USA), 0.75x (Spain).
    """
    country = hmd["country"]
    mx, deaths = hmd["Mx"], hmd["Deaths"]
    year = 2010 if 2010 in set(mx["Year"]) else int(mx["Year"].max())

    # Ages 30-50: past the accident hump, before the old-age curvature, so the
    # underlying log-rate is close to linear in age and second differences are
    # dominated by noise rather than by shape.
    rates = mx[(mx["Year"] == year) & (mx["Age"].between(30, 50))].sort_values("Age")
    counts = deaths[(deaths["Year"] == year) & (deaths["Age"].between(30, 50))].sort_values("Age")
    assert len(rates) > 5 and (rates["Total"] > 0).all()

    log_mx = np.log(rates["Total"].to_numpy(dtype=float))
    second_diff = log_mx[2:] - 2 * log_mx[1:-1] + log_mx[:-2]
    observed = float(np.std(second_diff))

    mean_deaths = float(counts["Total"].mean())
    floor = math.sqrt(6.0 / mean_deaths)
    assert observed > ROUGHNESS_FLOOR_FRACTION * floor, (
        f"{country} {year}: roughness of log m_x is {observed:.4f} against a Poisson "
        f"floor of {floor:.4f} at {mean_deaths:.0f} deaths/age. Real counts cannot "
        "be this smooth -- the series looks fitted."
    )


# =============================================================================
# The Mexican files: same idea, different anchors
# =============================================================================

real_mexico = pytest.mark.skipif(
    not (REAL_DEATHS.exists() and REAL_POP.exists()),
    reason="real INEGI/CONAPO files not present (gitignored -- see DATA.md)",
)


def _mexico_deaths_by_year() -> pd.Series:
    """Total registered deaths per year, with the "85 y mas" open group removed."""
    df = pd.read_csv(REAL_DEATHS)
    df = df[df["Sexo"] == "Total"]
    # NOT the rule the loader applies. The loader identifies the aggregate by
    # the open-group identity (candidate == single age + sum of the ages above
    # it) and refuses to guess when that does not hold -- see
    # a06._is_open_interval_row, whose docstring explicitly rejects "pick the
    # maximum" as vacuous. Here we only need a total-deaths series for a COVID
    # excess check, so the cruder max rule is adequate and deliberately
    # independent of the loader: if this helper reused the loader's logic, the
    # test could not catch the loader getting it wrong.
    open_group = df[df.duplicated(["Anio", "Edad"], keep=False)]
    drop_idx = open_group.loc[open_group.groupby(["Anio", "Edad"])["Defunciones"].idxmax()].index
    return df.drop(index=drop_idx).groupby("Anio")["Defunciones"].sum()


@real_mexico
def test_mexico_2020_shows_covid_excess_mortality():
    """
    THEORY: Mexico's pandemic signal is larger than either HMD country's. If the
    INEGI file does not show it, it is not INEGI.
    """
    by_year = _mexico_deaths_by_year()
    assert {2019, 2020} <= set(by_year.index)
    excess_pct = (by_year[2020] / by_year[2019] - 1) * 100
    assert excess_pct > 30.0, (
        f"2019->2020 registered deaths moved {excess_pct:+.1f}%; the real INEGI "
        "series moves +45.4% (743,639 -> 1,081,131)."
    )


@real_mexico
def test_mexico_death_registrations_are_in_the_right_order_of_magnitude():
    """
    THEORY: an order-of-magnitude anchor. Mexico registers on the order of
    half a million deaths a year in the 1990s and around 800 thousand today;
    anything outside that band is a different country or a different unit.
    """
    by_year = _mexico_deaths_by_year()
    assert 300_000 < by_year[1990] < 600_000, by_year[1990]
    assert 600_000 < by_year[by_year.index.max()] < 1_300_000, by_year.iloc[-1]


@real_mexico
def test_conapo_population_matches_the_national_total():
    """
    THEORY: CONAPO's projected population summed over all ages must reconstruct
    the national total. The 2020 census counted 126.0 million; CONAPO's
    projection for the same year is close to it by construction.
    """
    pop = pd.read_csv(REAL_POP)
    total_2020 = float(pop[(pop["Sexo"] == "Total") & (pop["Anio"] == 2020)]["Poblacion"].sum())
    assert 110e6 < total_2020 < 145e6, f"CONAPO 2020 total = {total_2020 / 1e6:.1f} M"
