# RHC-Inductive-Configuration-Verifier

Companion code for the paper *Multivariate Reverse Hypercontractivity on the Sphere with applications to promise CSPs*.

For every Boolean predicate $P$ in the four predicate families of
Austrin–Håstad–Martinsson [Tables 14, 15, 21, 22]([austrin2026usefulness]),
this code decides whether $P$ is a *balanced (interior) inductive predicate* in
the sense of the paper:

- **interior**: $P$ is a *balanced interior inductive predicate*. The paper's
  main hardness theorem then implies that $\operatorname{fiPCSP}(P,Q)$ admits
  *no* polynomial-time UG-robust algorithm for any non-trivial $Q\supseteq P$.
- **boundary**: $P$ is a *balanced boundary inductive predicate*.
- **non-inductive**: $P$ is not a balanced inductive predicate of either kind.
  In this case the script also produces an exact rational *Farkas certificate*
  $y$ with $y^\top A_{\mathrm{eq}} \geq 0$ component-wise and
  $y^\top b_{\mathrm{eq}} = -1$ for the staircase LP, certifying infeasibility.

All computations are performed in exact rational arithmetic
(`fractions.Fraction`); `scipy.optimize.linprog` is used only as a numerical
oracle for support detection and rationalisation.

## Repository layout

```
predicates.py        — The four predicate families (TABLE_14, _15, _21, _22).
verifier.py          — Exact-arithmetic verification & calculation
                       (LP solving, balanced-staircase Gram, Farkas certificates,
                       coordinate-permutation classifier).
tables.py            — LaTeX emission: body classification tables, appendix
                       witness tables (longtable), Farkas certificates.
generate_tables.py   — Entry point: classify everything and write LaTeX tables.
requirements.txt     — Python dependencies (numpy, scipy).
```

## Installation

Python 3.10+ is required.

```bash
pip install -r requirements.txt
```

## Usage

To regenerate every LaTeX table used in the paper (and print a console
summary):

```bash
python generate_tables.py
```

By default this writes the per-table files (`max_k_4.tex`, `min_k_4.tex`,
`min_k_5.tex`, `max_k_5.tex`, `app_max_k_4.tex`, `app_min_k_4.tex`,
`app_min_k_5.tex`, `app_max_k_5.tex`, `farkas.tex`) to `./tables/` (relative
to the current working directory).

Custom paths and extra options:

```bash
python generate_tables.py --out-dir ./out/tables --no-summary
```

## Programmatic use

To classify a single predicate:

```python
from verifier import classify_predicate

P = ["00111", "01001", "01010", "01101", "01110", "10011", "10100", "11000"]
result = classify_predicate(P)

print(result["type"])        # "interior", "boundary", or "non-inductive"
print(result["r"])           # tuple of Fractions, the staircase parameters
print(result["det_G"])       # Fraction, det R for the chosen ordering
print(result["lambda"])      # list of Fractions, the balanced distribution
print(result["permutation"]) # tuple, the coordinate ordering used
```

For non-inductive predicates the dict additionally contains a `"farkas"` key
with an exact rational certificate of infeasibility.

## How verification works

For each predicate $P\subseteq\{-1,+1\}^k$ (after applying a coordinate
permutation $\pi\in S_k$) the verifier sets up the *balanced-staircase LP*
over $\Delta(P)$:

- (Z) zero first moments: $\mathbb{E}_\lambda[a_i] = 0$ for all $i$.
- (S2) staircase second moments: $\mathbb{E}_\lambda[a_i a_{i+1}] =
  \mathbb{E}_\lambda[a_i a_j]$ for all $i+1 < j$.

If the LP is feasible, the script computes the resulting staircase parameters
$(r_1, \ldots, r_{k-1})$ and the $k \times k$ Gram matrix $R$, then checks
whether $\det R > 0$ (interior) or $\det R = 0$ (boundary), all in exact
rational arithmetic. If the LP is infeasible for every permutation, an exact
Farkas dual is computed.

## Reproducibility

Every entry of every table in the paper's appendix is produced verbatim by
`python generate_tables.py`. The script uses no random seeds and the LP solver
output is deterministic on a given platform, so the LaTeX output is
byte-identical between runs (modulo trailing whitespace).

## License

See [LICENSE](LICENSE).
