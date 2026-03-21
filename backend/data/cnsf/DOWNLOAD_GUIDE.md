# CNSF / EMSSA Regulatory Tables - Download Guide

## Sources

### CNSF 2000-I (General Population Table)
- **Authority**: Comision Nacional de Seguros y Fianzas (CNSF)
- **Circular**: CUSF Anexo 14.2.1
- **Use**: Life insurance reserves for general population products

### EMSSA-2009 (Social Security Table)
- **Authority**: CNSF / IMSS
- **Full name**: Experiencia Mexicana de Seguridad Social Actuarial 2009
- **Circular**: CUSF Anexo 14.2.2
- **Use**: Pension and social security reserve calculations

### CNSF 2013 (Updated General Population)
- **Authority**: CNSF
- **Use**: Updated version for newer products

## How to Obtain

These tables are published in CNSF regulatory circulars (PDF format).

1. Go to: https://www.gob.mx/cnsf
2. Navigate to "Marco Juridico" > "Circulares" or "Disposiciones"
3. Find the CUSF (Circular Unica de Seguros y Fianzas)
4. Look in Anexo 14 for mortality tables
5. Transcribe the q_x values from PDF tables to CSV

Alternative: Ask the CNSF for digital copies of the tables, or find
them in actuarial textbooks that reproduce them (e.g., "Matematicas
Actuariales" by various Mexican authors).

## Expected CSV Format

```
age,qx_male,qx_female
0,0.01550000,0.01280000
1,0.00696460,0.00575141
2,0.00312940,0.00258428
...
100,1.00000000,1.00000000
```

| Column | Description |
|--------|-------------|
| age | Integer age 0 to omega |
| qx_male | Male probability of death at age x |
| qx_female | Female probability of death at age x |

## Notes

- q_x values should be in decimal form (0.015, not 15 per thousand)
- Terminal age q_x must equal 1.0 (everyone dies at omega)
- Save as: `backend/data/cnsf/cnsf_2000_i.csv` or `backend/data/cnsf/emssa_2009.csv`
