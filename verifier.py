"""Exact-arithmetic verification and calculation for the balanced-staircase
classification of Boolean predicates.

For a Boolean predicate $P\\subseteq\\{-1,+1\\}^k$ (encoded as bitstrings; see
``predicates.py``) this module decides whether $P$ is a *balanced (interior)
inductive predicate* in the sense of the paper, by:

  1. Solving the *balanced-staircase linear program* over $\\Delta(P)$ to find a
     distribution $\\lambda$ with first moments $\\mathbb{E}_\\lambda[a_i]=0$ and
     second moments forming a staircase pattern.
  2. Building the exact rational $k\\times k$ second-moment Gram matrix $R$ and
     computing all leading principal minors exactly.
  3. Classifying the predicate as
        - *interior*       if some coordinate ordering yields $\\det R > 0$;
        - *boundary*       if a balanced $\\lambda$ exists for some ordering but
                           every such ordering only gives $R\\succeq 0$
                           (rank-deficient);
        - *non-inductive*  if no coordinate ordering admits any feasible
                           balanced $\\lambda$. In this case we additionally
                           produce an exact rational *Farkas certificate* $y$
                           with $y^\\top A_{\\mathrm{eq}}\\geq 0$ component-wise
                           and $y^\\top b_{\\mathrm{eq}}=-1$, certifying
                           infeasibility of the LP.

All computations are performed in exact rational arithmetic
(``fractions.Fraction``); ``scipy.optimize.linprog`` is used only as a numerical
oracle for the support and rationalisation step.

The single public entry point is :func:`classify_predicate`, which iterates
over all $k!$ coordinate permutations and returns a dictionary describing the
classification together with all the data needed for the LaTeX appendix tables.
"""

from __future__ import annotations

import itertools
from fractions import Fraction
from typing import Optional

import numpy as np
from scipy.optimize import linprog


# =============================================================================
# Predicate -> +/-1 sign matrix
# =============================================================================

def _predicate_to_pm1(predicate: list[str]) -> np.ndarray:
    """Convert bitstrings ('0' -> -1, '1' -> +1) into an $(N, k)$ numpy array."""
    return np.array(
        [[1.0 if c == "1" else -1.0 for c in s] for s in predicate],
        dtype=float,
    )


def _predicate_to_pm1_exact(predicate: list[str]) -> list[list[Fraction]]:
    """Convert bitstrings into an $(N, k)$ list-of-lists of Fractions."""
    return [
        [Fraction(1) if c == "1" else Fraction(-1) for c in s]
        for s in predicate
    ]


# =============================================================================
# Exact rational linear-algebra primitives
# =============================================================================

def _frac_matvec(A: list[list[Fraction]], v: list[Fraction]) -> list[Fraction]:
    return [sum((row[j] * v[j] for j in range(len(v))), Fraction(0)) for row in A]


def _frac_dot(u: list[Fraction], v: list[Fraction]) -> Fraction:
    return sum((u[i] * v[i] for i in range(len(u))), Fraction(0))


def _frac_det(M: list[list[Fraction]]) -> Fraction:
    """Bareiss-style exact determinant for small matrices of Fractions."""
    n = len(M)
    if n == 0:
        return Fraction(1)
    A = [row[:] for row in M]
    sign = Fraction(1)
    for i in range(n):
        # Find pivot.
        pivot_row = None
        for r in range(i, n):
            if A[r][i] != 0:
                pivot_row = r
                break
        if pivot_row is None:
            return Fraction(0)
        if pivot_row != i:
            A[i], A[pivot_row] = A[pivot_row], A[i]
            sign = -sign
        pivot = A[i][i]
        for r in range(i + 1, n):
            if A[r][i] == 0:
                continue
            factor = A[r][i] / pivot
            for c in range(i, n):
                A[r][c] = A[r][c] - factor * A[i][c]
    out = sign
    for i in range(n):
        out *= A[i][i]
    return out


def _leading_principal_minors(G: list[list[Fraction]]) -> list[Fraction]:
    """Return all leading principal minors $\\det(G[:k,:k])$ for $k=1,\\ldots,n$."""
    n = len(G)
    return [_frac_det([row[:k] for row in G[:k]]) for k in range(1, n + 1)]


# =============================================================================
# Balanced-staircase LP setup (exact)
# =============================================================================

def _staircase_constraints_exact(
    A_pm: list[list[Fraction]],
) -> tuple[list[list[Fraction]], list[Fraction]]:
    """Build $(A_{\\mathrm{eq}}, b_{\\mathrm{eq}})$ for the balanced-staircase LP
    over $\\Delta(P)$ in exact rationals.

    Constraints:
      - Normalisation:  $\\sum_n \\lambda_n = 1$.
      - (Z)  $\\mathbb{E}[a_i] = 0$ for every $i = 1,\\ldots,k$
             (zero first moments / balanced condition).
      - (S2) $\\mathbb{E}[a_i a_{i+1}] = \\mathbb{E}[a_i a_j]$ for
             $i = 1,\\ldots,k-2$ and $j = i+2,\\ldots,k$
             (staircase pattern on second moments).

    Note: the constraint (S1) $\\mathbb{E}[a_i] = \\mathbb{E}[a_{i+1}]$ is
    subsumed by (Z), which is strictly stronger. A predicate is "balanced
    inductive" exactly when this system admits a feasible $\\lambda$ giving a
    strictly positive-definite $k\\times k$ second-moment matrix $R$.
    """
    N = len(A_pm)
    if N == 0:
        return [], []
    k = len(A_pm[0])
    rows: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    rows.append([Fraction(1)] * N)
    rhs.append(Fraction(1))
    # (Z): zero first moments (each mu_i = 0).
    for i in range(k):
        rows.append([A_pm[n][i] for n in range(N)])
        rhs.append(Fraction(0))
    # (S2): staircase on second moments.
    for i in range(k - 2):
        for j in range(i + 2, k):
            rows.append(
                [A_pm[n][i] * A_pm[n][i + 1] - A_pm[n][i] * A_pm[n][j] for n in range(N)]
            )
            rhs.append(Fraction(0))
    return rows, rhs


def _to_float_matrix(M: list[list[Fraction]]) -> np.ndarray:
    return np.array([[float(c) for c in row] for row in M], dtype=float)


def _to_float_vector(v: list[Fraction]) -> np.ndarray:
    return np.array([float(c) for c in v], dtype=float)


# =============================================================================
# Solve for an exact rational lambda via scipy + rationalisation + verification
# =============================================================================

def _rationalise(x: float, max_denominator: int = 100000) -> Fraction:
    return Fraction(x).limit_denominator(max_denominator)


def _verify_lambda_exact(
    lam: list[Fraction],
    A_eq: list[list[Fraction]],
    b_eq: list[Fraction],
) -> bool:
    if any(c < 0 for c in lam):
        return False
    Av = _frac_matvec(A_eq, lam)
    return all(Av[i] == b_eq[i] for i in range(len(b_eq)))


def _exact_lambda_from_support(
    support: list[int],
    A_eq: list[list[Fraction]],
    b_eq: list[Fraction],
    N: int,
) -> Optional[list[Fraction]]:
    """Solve $A_{\\mathrm{eq}}[:,\\text{support}]\\,x = b_{\\mathrm{eq}}$ exactly
    for $x$; embed into an $N$-vector.

    The solution $x$ is the minimum-norm (under a deterministic pivot rule)
    solution of the rational linear system. If the system is inconsistent or
    yields a negative entry, returns ``None``.
    """
    m = len(A_eq)
    s = len(support)
    if s == 0:
        return None
    aug = [[A_eq[i][j] for j in support] + [b_eq[i]] for i in range(m)]
    n_cols = s + 1
    pivot_col_for_row: list[Optional[int]] = [None] * m
    row = 0
    for col in range(s):
        pivot_row = None
        for r in range(row, m):
            if aug[r][col] != 0:
                pivot_row = r
                break
        if pivot_row is None:
            continue
        if pivot_row != row:
            aug[row], aug[pivot_row] = aug[pivot_row], aug[row]
        pivot = aug[row][col]
        aug[row] = [c / pivot for c in aug[row]]
        for r in range(m):
            if r == row or aug[r][col] == 0:
                continue
            f = aug[r][col]
            aug[r] = [aug[r][c] - f * aug[row][c] for c in range(n_cols)]
        pivot_col_for_row[row] = col
        row += 1
        if row == m:
            break
    # Consistency check: any all-zero LHS row with nonzero RHS => infeasible.
    for r in range(m):
        if all(aug[r][c] == 0 for c in range(s)) and aug[r][s] != 0:
            return None
    x = [Fraction(0)] * s
    for r in range(m):
        col = pivot_col_for_row[r]
        if col is not None:
            x[col] = aug[r][s]
    if any(v < 0 for v in x):
        return None
    out = [Fraction(0)] * N
    for j_idx, col in enumerate(support):
        out[col] = x[j_idx]
    return out


def _solve_lambda_relative_interior_float(
    A_eq_f: np.ndarray, b_eq_f: np.ndarray, N: int, atol: float
) -> Optional[np.ndarray]:
    """Find a relative-interior point of
    $\\{\\lambda \\geq 0 : A_{\\mathrm{eq}}\\,\\lambda = b_{\\mathrm{eq}}\\}$
    via the average of per-coordinate maximisers, returned as floats.
    """
    bounds = [(0.0, None)] * N
    res0 = linprog(np.zeros(N), A_eq=A_eq_f, b_eq=b_eq_f, bounds=bounds, method="highs")
    if not res0.success:
        return None
    feasible = [res0.x]
    for n in range(N):
        c_n = np.zeros(N)
        c_n[n] = -1.0
        res_n = linprog(c_n, A_eq=A_eq_f, b_eq=b_eq_f, bounds=bounds, method="highs")
        if res_n.success and res_n.x[n] > atol:
            feasible.append(res_n.x)
    lam = np.mean(feasible, axis=0)
    lam = np.clip(lam, 0.0, None)
    s = lam.sum()
    if s <= atol:
        return None
    return lam / s


def solve_inductive_lambda_exact(
    predicate: list[str],
    atol: float = 1e-9,
    max_denom: int = 200000,
) -> Optional[dict]:
    """Find an exact rational distribution $\\lambda$ on $P$ with staircase moments.

    Strategy:
      1. Solve the LP numerically via scipy to find a relative-interior support.
      2. Rationalise the float solution and verify exactly.
      3. If verification fails, refine: solve the rational linear system on
         the detected support exactly (Gauss-Jordan over Fractions).
      4. Build the exact $k\\times k$ second-moment Gram $R$ and compute all
         leading principal minors exactly.

    Returns
    -------
    ``None`` if no feasible $\\lambda$ exists (i.e. $P$ is non-inductive under
    the identity coordinate ordering). Otherwise a dict with keys

      "lambda"         : list[Fraction] of length $|P|$.
      "support"        : list[int] indices of nonzero entries.
      "r"              : tuple[Fraction] of length $k-1$ giving $(r_1, \\ldots, r_{k-1})$.
      "gram"           : list[list[Fraction]] -- the $k\\times k$ second-moment Gram $R$.
      "leading_minors" : list[Fraction] of length $k$.
      "det_G"          : Fraction (the last leading minor, $\\det R$).
      "interior"       : bool ($\\det R > 0$).
    """
    A_pm_exact = _predicate_to_pm1_exact(predicate)
    N = len(A_pm_exact)
    if N == 0:
        return None
    k = len(A_pm_exact[0])

    A_eq_exact, b_eq_exact = _staircase_constraints_exact(A_pm_exact)
    A_eq_f = _to_float_matrix(A_eq_exact)
    b_eq_f = _to_float_vector(b_eq_exact)

    lam_f = _solve_lambda_relative_interior_float(A_eq_f, b_eq_f, N, atol)
    if lam_f is None:
        return None

    support = [n for n in range(N) if lam_f[n] > atol]
    if not support:
        return None

    # Try direct rationalisation first.
    lam_rational = [Fraction(0)] * N
    for n in support:
        lam_rational[n] = _rationalise(float(lam_f[n]), max_denominator=max_denom)
    s_total = sum(lam_rational, Fraction(0))
    if s_total != 0:
        lam_rational = [c / s_total for c in lam_rational]

    if not _verify_lambda_exact(lam_rational, A_eq_exact, b_eq_exact):
        # Refine: solve the rational system exactly on the detected support.
        lam_exact = _exact_lambda_from_support(support, A_eq_exact, b_eq_exact, N)
        if lam_exact is None or not _verify_lambda_exact(lam_exact, A_eq_exact, b_eq_exact):
            return None
        lam_rational = lam_exact

    # Compute exact moments.
    # (Z) forces all first moments to zero; we just verify.
    for i in range(k):
        mu_i = sum(
            (lam_rational[n] * A_pm_exact[n][i] for n in range(N)),
            Fraction(0),
        )
        assert mu_i == 0, f"first moment mu_{i} = {mu_i} is not zero"
    # Second-moment staircase parameters (r_1, ..., r_{k-1}).
    rs: list[Fraction] = []
    for i in range(k - 1):
        beta = sum(
            (
                lam_rational[n] * A_pm_exact[n][i] * A_pm_exact[n][i + 1]
                for n in range(N)
            ),
            Fraction(0),
        )
        rs.append(beta)

    # Build the k x k second-moment Gram R of (v_1, ..., v_k) on v_0^perp.
    # R_{ii} = 1, R_{ij} = r_{min(i,j)} for i != j (staircase form).
    R: list[list[Fraction]] = [[Fraction(0)] * k for _ in range(k)]
    for i in range(k):
        R[i][i] = Fraction(1)
    for i in range(k):
        for j in range(i + 1, k):
            R[i][j] = R[j][i] = rs[i]

    minors = _leading_principal_minors(R)
    det_R = minors[-1]
    interior = det_R > 0

    return {
        "lambda": lam_rational,
        "support": [n for n in range(N) if lam_rational[n] != 0],
        "r": tuple(rs),
        "gram": R,
        "leading_minors": minors,
        "det_G": det_R,  # historically named det_G; tables module reads this key
        "interior": interior,
    }


# =============================================================================
# Farkas certificate for non-inductive predicates (exact)
# =============================================================================

def _solve_farkas_float(A_eq_f: np.ndarray, b_eq_f: np.ndarray) -> Optional[np.ndarray]:
    """Find a Farkas certificate $y$ for infeasibility of
    $\\{A_{\\mathrm{eq}}\\,\\lambda = b_{\\mathrm{eq}},\\ \\lambda \\geq 0\\}$.

    By Farkas, infeasibility is equivalent to the existence of $y$ with
        $A_{\\mathrm{eq}}^\\top y \\geq 0$ (component-wise),
        $b_{\\mathrm{eq}}^\\top y < 0$.
    We find it by solving the LP
        max  $-b_{\\mathrm{eq}}^\\top y$
         s.t. $-A_{\\mathrm{eq}}^\\top y \\leq 0$, no other bounds on $y$.
    If the original LP is infeasible, this LP is unbounded above; HiGHS then
    returns a ray. If it is bounded, the certificate $y$ returned is normalised
    so that $b_{\\mathrm{eq}}^\\top y = -1$.
    """
    m, N = A_eq_f.shape
    # Variables y in R^m, free.
    c = b_eq_f  # minimise b^T y
    A_ub = -A_eq_f.T  # -A^T y <= 0
    b_ub = np.zeros(N)
    bounds = [(None, None)] * m
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if res.status == 3:  # unbounded -- HiGHS may not return ray here
        # Fall back to a normalised version: maximise -b^T y subject to b^T y = -1.
        A_eq_extra = np.array([b_eq_f])
        b_eq_extra = np.array([-1.0])
        res2 = linprog(
            np.zeros(m),
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=A_eq_extra,
            b_eq=b_eq_extra,
            bounds=bounds,
            method="highs",
        )
        if res2.success:
            return res2.x
        return None
    if res.success and (b_eq_f @ res.x) < -1e-9:
        return res.x
    # Try the normalised LP unconditionally.
    A_eq_extra = np.array([b_eq_f])
    b_eq_extra = np.array([-1.0])
    res2 = linprog(
        np.zeros(m),
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq_extra,
        b_eq=b_eq_extra,
        bounds=bounds,
        method="highs",
    )
    if res2.success:
        return res2.x
    return None


def find_farkas_certificate_exact(
    predicate: list[str],
    atol: float = 1e-9,
    max_denom: int = 200000,
) -> Optional[dict]:
    """Find an exact rational Farkas certificate for a non-inductive predicate.

    Returns
    -------
    ``None`` if no certificate is found (e.g., the LP is actually feasible).
    Otherwise a dict with keys

      "y"   : list[Fraction] -- the dual variables.
      "Aty" : list[Fraction] -- $A_{\\mathrm{eq}}^\\top y$, all entries $\\geq 0$.
      "bty" : Fraction -- $y^\\top b_{\\mathrm{eq}}$, strictly negative
              (normalised to $-1$).
    """
    A_pm_exact = _predicate_to_pm1_exact(predicate)
    N = len(A_pm_exact)
    if N == 0:
        return None
    A_eq_exact, b_eq_exact = _staircase_constraints_exact(A_pm_exact)
    A_eq_f = _to_float_matrix(A_eq_exact)
    b_eq_f = _to_float_vector(b_eq_exact)

    y_float = _solve_farkas_float(A_eq_f, b_eq_f)
    if y_float is None:
        return None

    # Rationalise.
    y_rational = [_rationalise(float(c), max_denominator=max_denom) for c in y_float]

    # Compute A_eq^T y exactly.
    m = len(A_eq_exact)
    Aty: list[Fraction] = [
        sum((A_eq_exact[i][j] * y_rational[i] for i in range(m)), Fraction(0))
        for j in range(N)
    ]
    bty: Fraction = sum(
        (b_eq_exact[i] * y_rational[i] for i in range(m)), Fraction(0)
    )

    if any(c < 0 for c in Aty) or bty >= 0:
        # Rationalisation lost the certificate; signal failure.
        return None

    # Normalise so that bty = -1 (positive scaling preserves the certificate).
    if bty != -1:
        scale = Fraction(-1) / bty
        y_rational = [c * scale for c in y_rational]
        Aty = [c * scale for c in Aty]
        bty = Fraction(-1)

    return {"y": y_rational, "Aty": Aty, "bty": bty}


# =============================================================================
# Classification driver
# =============================================================================

def _permute_predicate(predicate: list[str], perm: tuple[int, ...]) -> list[str]:
    """Apply a coordinate permutation to every bitstring in the predicate.

    If $\\pi = (\\pi_1, \\ldots, \\pi_k)$, each string $s = s_1 \\cdots s_k$ is
    mapped to $s_{\\pi_1} s_{\\pi_2} \\cdots s_{\\pi_k}$. The returned list
    preserves the order of ``predicate`` (so $\\lambda$ values assigned to
    position $n$ correspond to ``predicate[n]``, not to the permuted string).
    """
    return [
        "".join(s[perm[i]] for i in range(len(perm)))
        for s in predicate
    ]


def classify_predicate(predicate: list[str]) -> dict:
    """Classify a predicate as *interior*, *boundary*, or *non-inductive*.

    The staircase condition on second moments is ordering-dependent, so we
    iterate over all $k!$ coordinate permutations. A predicate is classified
    *interior* if any permutation produces a strictly positive-definite
    second-moment Gram ($\\det R > 0$), *boundary* if some permutation admits
    a balanced $\\lambda$ but the Gram is only PSD for every such permutation,
    and *non-inductive* if no permutation has a feasible balanced $\\lambda$.
    """
    N = len(predicate)
    if N == 0:
        return {
            "type": "non-inductive", "farkas": None,
            "permutation": tuple(), "original_predicate": predicate,
        }
    k = len(predicate[0])

    best_interior: Optional[dict] = None
    best_boundary: Optional[dict] = None
    for perm in itertools.permutations(range(k)):
        permuted = _permute_predicate(predicate, perm)
        result = solve_inductive_lambda_exact(permuted)
        if result is None:
            continue
        if result["interior"]:
            entry = {
                "type": "interior",
                "permutation": perm,
                "original_predicate": predicate,
                **result,
            }
            if best_interior is None:
                best_interior = entry
        else:
            if best_boundary is None:
                best_boundary = {
                    "type": "boundary",
                    "permutation": perm,
                    "original_predicate": predicate,
                    **result,
                }

    if best_interior is not None:
        return best_interior
    if best_boundary is not None:
        return best_boundary

    cert = find_farkas_certificate_exact(predicate)
    return {
        "type": "non-inductive",
        "farkas": cert,
        "permutation": tuple(range(k)),
        "original_predicate": predicate,
    }
