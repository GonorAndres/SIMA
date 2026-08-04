<!--
Under this repo's branch model, `dev` takes direct pushes, so in practice the
only pull request is the promotion: dev -> main. CI enforces that (see the
source-branch job); a PR into main from anything other than dev fails.

Open one with:  gh pr create --base main --head dev --fill
-->

## What is being promoted

<!-- One or two lines. What changes for a visitor to sima.gonor.me? -->

## Evidence it works

<!--
Dev runs the identical deploy path as production -- same image build, same data
gate, same candidate revision, same validate_production.py before any traffic
moves. So the honest answer here is usually a link to the green dev run.
-->

- [ ] CI green on `dev` (backend + frontend)
- [ ] `Deploy` workflow green on `dev` — candidate validated and promoted
- [ ] Checked the dev preview in a browser: https://dev.sima-7xu.pages.dev

## Anything reviewers should look at closely

<!-- Data/regulatory assumptions, actuarial figures that moved, or "nothing". -->

---

<sub>Production deploy runs automatically once CI passes on `main`. It builds a
candidate revision with **no traffic**, validates it, and only then cuts over —
a failed validation leaves production on the previous revision.</sub>
