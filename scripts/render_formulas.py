#!/usr/bin/env python3
"""
Pre-compile LaTeX formulas to transparent PNG images.

Uses pdflatex (standalone document class) + ghostscript to render each formula
as a tightly-cropped, retina-crisp (300 DPI) PNG with transparent background.

Output: frontend/public/formulas/*.png
These are served by Vite at /formulas/<name>.png
"""

import os
import subprocess
import tempfile
from pathlib import Path

# All formulas used across the frontend
FORMULAS = {
    "central_death_rate": r"m_{x,t} = \frac{D_{x,t}}{E_{x,t}}",
    "whittaker_henderson": r"\hat{g} = \left(W + \lambda D'D\right)^{-1} W \, m",
    "lee_carter": r"\ln(m_{x,t}) = a_x + b_x \cdot k_t + \varepsilon_{x,t}",
    "rwd": r"k_{t+1} = k_t + d + \sigma\, Z_t, \quad Z_t \sim N(0,1)",
    "whole_life_premium": r"P = SA \cdot \frac{M_x}{N_x}",
    "prospective_reserve": r"{}_tV = SA \cdot A_{x+t} - P \cdot \ddot{a}_{x+t}",
    "scr_aggregation": r"SCR = \sqrt{\vec{S}^T \cdot C \cdot \vec{S}}",
    "rcs_aggregation": r"RCS = \sqrt{\vec{S}^{\,T} \cdot C \cdot \vec{S}}",
    "term_premium": r"P = SA \cdot \frac{M_x - M_{x+n}}{N_x - N_{x+n}}",
    "endowment_premium": r"P = SA \cdot \frac{M_x - M_{x+n} + D_{x+n}}{N_x - N_{x+n}}",
}

LATEX_TEMPLATE = r"""\documentclass[border=2pt,varwidth]{standalone}
\usepackage{amsmath}
\usepackage{amssymb}
\begin{document}
$\displaystyle FORMULA_PLACEHOLDER $
\end{document}
"""

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "frontend" / "public" / "formulas"


def render_formula(name: str, latex: str, output_dir: Path) -> bool:
    """Render a single LaTeX formula to PNG via pdflatex + ghostscript."""
    output_png = output_dir / f"{name}.png"

    tex_content = LATEX_TEMPLATE.replace("FORMULA_PLACEHOLDER", latex)

    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "formula.tex")
        pdf_path = os.path.join(tmpdir, "formula.pdf")

        with open(tex_path, "w") as f:
            f.write(tex_content)

        # Step 1: pdflatex -> PDF
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tmpdir, tex_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"  FAIL pdflatex for {name}:")
            print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
            return False

        if not os.path.exists(pdf_path):
            print(f"  FAIL: PDF not created for {name}")
            return False

        # Step 2: ghostscript -> transparent PNG at 300 DPI
        gs_result = subprocess.run(
            [
                "gs",
                "-sDEVICE=pngalpha",
                "-r300",
                "-dBATCH",
                "-dNOPAUSE",
                "-dQUIET",
                f"-sOutputFile={output_png}",
                pdf_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if gs_result.returncode != 0:
            print(f"  FAIL ghostscript for {name}:")
            print(gs_result.stderr)
            return False

    return True


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Rendering {len(FORMULAS)} formulas to {OUTPUT_DIR}/\n")

    success = 0
    fail = 0

    for name, latex in FORMULAS.items():
        print(f"  {name}...", end=" ")
        if render_formula(name, latex, OUTPUT_DIR):
            size = (OUTPUT_DIR / f"{name}.png").stat().st_size
            print(f"OK ({size:,} bytes)")
            success += 1
        else:
            fail += 1

    print(f"\nDone: {success} OK, {fail} failed")
    if fail > 0:
        exit(1)


if __name__ == "__main__":
    main()
