# Human Mortality Database Download Guide

SIMA uses HMD **period** 1x1 data for the USA and Spain. HMD requires account
registration and acceptance of its data-use terms, so raw files are not
redistributed by this repository.

## Currently used vintage

| Country | Coverage | HMD "Last modified" | Methods Protocol |
|---------|----------|---------------------|------------------|
| USA (`USA`) | 1933-2024 | 09 June 2026 | v6 (2017) |
| Spain (`ESP`) | 1908-2023 | 20 February 2025 | v6 (2017) |

Downloaded **2026-08-02**. Record the download date whenever you refresh these
files: HMD revises past years, so a "1933-2024" file from a later vintage is not
byte-identical to this one, and Lee-Carter parameters will shift slightly.

## Download

The fastest route is the per-country zip, which contains every table at once.

1. Create an account at <https://www.mortality.org/> and log in.
2. Open the country page (United States of America, or Spain) and download the
   full country zip: `USA.zip` / `ESP.zip`.
3. Extract it. Inside you get two top-level folders:

```text
USA/
├── InputDB/    # raw national inputs -- DO NOT COPY (see licence note below)
└── STATS/      # HMD-computed estimates -- this is what SIMA uses
```

4. Take exactly three files from `STATS/`, and rename them on the way in. The
   loader derives filenames from `HMD_SCHEMA` in
   `backend/engine/a06_mortality_data.py`, which expects the country **suffix**
   form -- not the `usa_Mx_1x1.txt` prefix form:

| From the zip | Save as |
|--------------|---------|
| `USA/STATS/Mx_1x1.txt` | `backend/data/hmd/usa/Mx_1x1_usa.txt` |
| `USA/STATS/Deaths_1x1.txt` | `backend/data/hmd/usa/Deaths_1x1_usa.txt` |
| `USA/STATS/Exposures_1x1.txt` | `backend/data/hmd/usa/Exposures_1x1_usa.txt` |
| `ESP/STATS/Mx_1x1.txt` | `backend/data/hmd/spain/Mx_1x1_spain.txt` |
| `ESP/STATS/Deaths_1x1.txt` | `backend/data/hmd/spain/Deaths_1x1_spain.txt` |
| `ESP/STATS/Exposures_1x1.txt` | `backend/data/hmd/spain/Exposures_1x1_spain.txt` |

Note the directory names are `usa` and `spain` (SIMA's internal keys), while the
HMD country codes are `USA` and `ESP`.

Resulting layout:

```text
backend/data/hmd/
├── usa/
│   ├── Mx_1x1_usa.txt
│   ├── Deaths_1x1_usa.txt
│   └── Exposures_1x1_usa.txt
└── spain/
    ├── Mx_1x1_spain.txt
    ├── Deaths_1x1_spain.txt
    └── Exposures_1x1_spain.txt
```

If you download the individual tables from the web UI instead of the zip, they
arrive already named `Mx_1x1.txt` etc. -- the same rename applies.

### Period, not cohort

`STATS/` also contains `cMx_1x1.txt`, `cDeaths_1x1.txt` and `cExposures_1x1.txt`.
The leading `c` means **cohort**. SIMA models period mortality: Lee-Carter is
fitted on a period age-year surface, and cohort tables are only complete for
generations that have (almost) died out, so they silently truncate recent years.
Use the files **without** the `c` prefix.

### Do not copy `InputDB/`

`InputDB/` holds the raw national inputs (`USAdeath.txt`, `USApop.txt`, ...) that
HMD received from the originating statistical offices. **These carry a stricter
licence than the HMD estimates.** The HMD estimates in `STATS/` -- death rates,
exposures, life tables -- are CC BY 4.0. The input data are not: they belong to
each national provider and may not be re-published or used commercially without
that provider's explicit permission. Copying `InputDB/` into this repository, or
into the GCS bucket, would be a licence violation. Keep it in the extracted zip
and leave it there.

## File format

The loader reads two metadata/header lines (`skiprows: 2`), then
whitespace-separated columns `Year`, `Age`, `Female`, `Male`, `Total`. The HMD
`110+` open-age label is handled. A missing value is `.`.

Line 1 of a genuine file looks like:

```text
The United States of America, Death rates (period 1x1),  Last modified: 09 juin 2026;  Methods Protocol: v6 (2017)
```

HMD serves that header in the locale of your account, so the month may be French
(`09 juin 2026`) or English. Nothing parses it; it is metadata.

## Verify

Format check:

```bash
.venv/bin/pytest backend/tests/test_mortality_data.py
```

Authenticity check -- this is the one that matters:

```bash
.venv/bin/pytest backend/tests/test_data_authenticity.py
```

Format tests only prove the file parses. Synthetic fixtures parse perfectly; that
is how generated data once reached production. The authenticity checks assert
properties of the real world that a generator cannot fake cheaply: the series must
start in 1933 (USA) / 1908 (Spain), summed exposures must imply a national
population near 330M / 47M, 2020 must show roughly +18% excess deaths, the
male/female mortality ratio at the ages 20-24 accident hump must be ~2.5-3.0, and
log death rates must be at least as rough as the Poisson floor sqrt(6/D). The same
checks gate the production deploy in `.github/workflows/deploy.yml`.

## Mock data for CI

`backend/data/mock/hmd/` holds small synthetic files, committed to git, so CI can
run the pipeline without HMD credentials. They are **deliberately** synthetic and
are wired only to the CI job -- never to a deploy. Do not "upgrade" them to real
data: HMD data is not redistributable, and the mock path is what keeps CI fast and
deterministic.

## Citation

Required in any published work or presentation using these data:

> HMD. Human Mortality Database. Max Planck Institute for Demographic Research
> (Germany), University of California, Berkeley (USA), and French Institute for
> Demographic Studies (France). Available at www.mortality.org.
> (Data downloaded 2026-08-02.)
