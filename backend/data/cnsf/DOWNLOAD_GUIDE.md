# CNSF Regulatory Mortality Tables - Download Guide

The whole CUSF corpus, annex by annex, is browsable here:

- **https://lisfcusf.cnsf.gob.mx/CUSF/** -- e.g. `.../CUSF/A_5_3_3_A` for Anexo 5.3.3-a

Chapter numbering matters when citing: **Capitulo 5 is "DE LAS RESERVAS TECNICAS"**
(reserves) and **Capitulo 6 is "DE LOS REQUERIMIENTOS DE CAPITAL"** (capital / RCS,
annexes 6.3.x, 6.4.11, 6.5.x). Mortality tables used for reserving live under 5.3.3;
capital requirements are cited from Capitulo 6, not from Titulo 5.

---

## Files in this directory

| File | Table | Annex | Ages | Sex |
|------|-------|-------|------|-----|
| `cnsf_2013.csv` | CNSF M 2013 (mixta) + 99.5th percentile | Anexo 5.3.3-a | 0-110 | **unisex** |
| `emssah_emssam_97.csv` | EMSSAH-97 / EMSSAM-97 | Anexo 14.2.4-a | 15-110 | male + female |
| `cnsf_2000_i.csv` | CNSF 2000-I | Anexo 14.2.1 (**unverified**) | 12-100 | male + female |
| `cnsf_2000_g.csv` | CNSF 2000-G | Anexo 14.2.1 (**unverified**) | 12-100 | male + female |

---

## CNSF M 2013 -- CUSF Anexo 5.3.3-a

- **Official title**: "CNSFM 2013 - Experiencia demografica de mortalidad MIXTA
  (hombres y mujeres)"
- **PDF**: https://www.gob.mx/cms/uploads/attachment/file/73530/ANEXO_5.3.3-a.pdf
- **Browsable**: https://lisfcusf.cnsf.gob.mx/CUSF/A_5_3_3_A
- **Use**: reserving basis for general-population life products

### It is UNISEX. There is no official male/female split.

The annex publishes **one** q_x column for ages 0-110, applied to hombres y mujeres
alike. `cnsf_2013.csv` therefore stores that single published series three times:

```
age,qx_unisex,qx_male,qx_female,qx_p995
0,0.000433,0.000433,0.000433,0.000654
65,0.006119,0.006119,0.006119,0.009222
110,0.758991,0.758991,0.758991,0.834611
```

| Column | Description |
|--------|-------------|
| `age` | Integer age, 0 to 110 |
| `qx_unisex` | **The published value.** Read this one. |
| `qx_male`, `qx_female` | Verbatim copies of `qx_unisex`, so `from_regulatory_table(sex=...)` keeps working. **Not a sex split.** |
| `qx_p995` | The same table at the **99.5th percentile**, also published in the annex |

`LifeTable.from_regulatory_table(path, sex="unisex")` reads `qx_unisex` and is the
correct call. Loading it with `sex="male"` or `sex="female"` returns the same
(correct) numbers but raises a `UserWarning` saying the columns are identical --
that warning is accurate and should not be silenced.

### The 99.5th percentile column

`qx_p995` is the regulator's own 1-in-200 mortality calibration: roughly 1.51x the
central rate up to age 80, tapering to about 1.10 at age 110 (q_x cannot be scaled
freely once it approaches 1). It is a genuine CUSF-prescribed stress and is a better
basis for the SCR mortality module than a generic Solvency II shock factor. Kept in
the file for that purpose.

### Do not reconstruct a sex split

Before 2026-08-02 this file carried `qx_male` / `qx_female` columns whose arithmetic
mean reproduced the official value to 6 decimal places at every one of the 111 ages:
the real table, split by an invented ratio running from 0.638 to 5.138. At some ages
it made female mortality *higher* than male. Male q_65 read 0.010039 against the
published 0.006119 -- 64% too high. If sex-differentiated reserving mortality is
needed, use a table the regulator actually published as sex-differentiated.

---

## EMSSAH-97 / EMSSAM-97 -- CUSF Anexo 14.2.4-a

- **PDF**: https://www.gob.mx/cms/uploads/attachment/file/74206/ANEXO_14.2.4-a.pdf
- **Ages**: **15-110 only** -- these price working-life and pension obligations, so
  childhood ages are out of scope by design
- **Sex**: genuinely differentiated (EMSSAH = hombres, EMSSAM = mujeres)
- **Published units**: per mille in the annex; `emssah_emssam_97.csv` stores decimals

```
age,qx_male,qx_female
15,0.000430,0.000150
110,1.000000,1.000000
```

### There is no "EMSSA 2009"

The CUSF annex index contains no table by that name. The file that used to sit at
`emssa_2009.csv` disagreed with Anexo 14.2.4-a at effectively every age -- ratios
swinging from 0.159x to 2.733x, and a single coincidental exact match at age 31
(0.00151) plus the trivial q = 1.0 at age 110 -- and it invented ages 0-14 that the
published table does not cover. It was deleted on 2026-08-02. Anything reintroducing
that filename is reintroducing a fabrication.

(An earlier revision of this guide said "matched at no age". Two of 96 ages do match;
the conclusion is unchanged, but the stronger claim was not true as written.)

---

## CNSF 2000-I / CNSF 2000-G -- CUSF Anexo 14.2.1

Not re-verified against the annex during the 2026-08-02 data audit. Treat their
provenance as unconfirmed until someone checks them against the published PDF the
same way the two tables above were checked.

---

## Verifying a transcription

Whatever you transcribe, check it before committing:

1. q_x must be a decimal in (0, 1], not per mille -- divide by 1000 if the annex
   prints "0.43" meaning 0.43 per thousand
2. q_x must increase monotonically above roughly age 30
3. Spot-check at least four ages spread across the range against the PDF
4. Record the source URL, the annex number and the retrieval date in `DATA.md`
5. Run `pytest backend/tests/test_regulatory_tables.py`
