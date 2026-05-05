"""LaTeX table emission for the paper.

Given the classifications produced by ``verifier.classify_predicate``, this
module emits two kinds of LaTeX tables:

  - **Body classification tables** (``\\begin{table}...\\end{table}``):
    one row per predicate, listing the predicate, its inductive *type*
    (interior / boundary / non-inductive), and a robust-hardness check
    indicator. Loaded into the body of the paper via ``\\input{}``.

  - **Appendix witness tables** (``\\begin{longtable}...\\end{longtable}``):
    for every interior or boundary row, a witness consisting of the explicit
    distribution $\\lambda\\in\\Delta(P)$, the coordinate ordering, the
    inductive R-configuration parameters $(r_1,\\ldots,r_{k-1})$, and
    $\\det R$. Uses ``longtable`` so that long rows can break across pages.

  - **Farkas certificate table** (``\\begin{table}...\\end{table}``):
    for every non-inductive row, an exact rational dual $y$ certifying
    infeasibility of the balanced-staircase LP.

The single public entry points are :func:`emit_all_tables` (writes one file
per table to the requested directory) and :func:`emit_appendix_latex`
(writes all appendix tables concatenated into a single legacy file).
"""

from __future__ import annotations

import os
from fractions import Fraction

from predicates import TABLES
from verifier import classify_predicate


# =============================================================================
# Pretty-printing of bitstrings, fractions, predicates
# =============================================================================

def _format_bitstring_latex(s: str) -> str:
    return r"\texttt{" + s + r"}"


def _format_predicate_latex(predicate: list[str]) -> str:
    return r"\{" + ", ".join(_format_bitstring_latex(s) for s in predicate) + r"\}"


def _format_predicate_latex_row(row: dict) -> str:
    """Format the predicate of a row using its 'display' field if present, else full expansion."""
    strings = row.get("display", row["predicate"])
    return r"\{" + ", ".join(_format_bitstring_latex(s) for s in strings) + r"\}"


def _format_fraction_latex(f: Fraction) -> str:
    if f.denominator == 1:
        return str(f.numerator)
    if f < 0:
        return f"-{(-f).numerator}/{f.denominator}"
    return f"{f.numerator}/{f.denominator}"


def _format_permutation(perm: tuple[int, ...]) -> str:
    """Return a one-line representation of a permutation, e.g. (3,1,2,4).

    Positions are 1-indexed for readability in the paper. Returns an empty
    string when ``perm`` is the identity.
    """
    if all(perm[i] == i for i in range(len(perm))):
        return ""
    return "(" + ",".join(str(p + 1) for p in perm) + ")"


# =============================================================================
# Witness-row pieces
# =============================================================================

def _latex_lambda_support(predicate: list[str], lam: list[Fraction]) -> str:
    """Emit the small ``tabular`` of nonzero $(\\text{bitstring}, \\text{fraction})$ pairs."""
    lines = [r"\begin{tabular}[t]{@{}l@{\,:\,}l@{}}"]
    for n, p in enumerate(predicate):
        if lam[n] != 0:
            lines.append(
                f" {_format_bitstring_latex(p)} & {_format_fraction_latex(lam[n])} \\\\"
            )
    lines.append(r"\end{tabular}")
    return " ".join(lines)


def _latex_r_aligned(rs: tuple[Fraction, ...]) -> str:
    """Emit the right-most witness column: $(r_1, r_2, \\ldots, r_{k-1})$ aligned."""
    inner = " \\\\ ".join(
        f"r_{{{i+1}}} &= {_format_fraction_latex(rs[i])}" for i in range(len(rs))
    )
    return r"$\begin{aligned}[t] " + inner + r" \end{aligned}$"


def _latex_witness_row(predicate: list[str], cls: dict) -> str:
    """Emit one row of an appendix witness table (interior or boundary)."""
    type_label = cls["type"]
    pred_str = _format_predicate_latex(predicate)
    lam_str = _latex_lambda_support(predicate, cls["lambda"])
    r_str = _latex_r_aligned(cls["r"])
    det_str = "$" + _format_fraction_latex(cls["det_G"]) + "$"
    perm_str = _format_permutation(cls.get("permutation", tuple()))
    perm_cell = f"${perm_str}$" if perm_str else "identity"
    return (
        f"{type_label} & {pred_str} & {lam_str} & {perm_cell} & {r_str} & {det_str} \\\\"
    )


# =============================================================================
# Witness tables (longtable, for the appendix)
# =============================================================================

def _latex_witness_table(
    rows: list[dict],
    caption: str,
    label: str,
) -> str:
    """Emit an entire appendix witness table as a ``longtable``.

    The ``longtable`` environment lets witness rows break across pages cleanly.
    Returns an empty string if no row of ``rows`` is interior or boundary.
    """
    inductive_rows = []
    for row in rows:
        cls = classify_predicate(row["predicate"])
        if cls["type"] in ("interior", "boundary"):
            inductive_rows.append((row, cls))
    if not inductive_rows:
        return ""
    header_row = (
        r"Type & Predicate $P$ & $\lambda$ (support only) & "
        r"Permutation $\pi$ & $r=(r_1,\ldots,r_{k-1})$ & $\det R$ \\"
    )
    out = [
        r"\footnotesize",
        r"\renewcommand{\arraystretch}{1.1}",
        r"\begin{longtable}{|c|p{0.22\textwidth}|l|c|l|l|}",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}\\\\",
        r"\hline",
        header_row,
        r"\hline",
        r"\endfirsthead",
        r"\multicolumn{6}{c}{\tablename\ \thetable\ -- \emph{continued from previous page}}\\",
        r"\hline",
        header_row,
        r"\hline",
        r"\endhead",
        r"\hline",
        r"\multicolumn{6}{r}{\emph{continued on next page}}\\",
        r"\endfoot",
        r"\hline",
        r"\endlastfoot",
    ]
    for row, cls in inductive_rows:
        out.append(_latex_witness_row(row["predicate"], cls))
        out.append(r"\hline")
    out.append(r"\end{longtable}")
    return "\n".join(out)


# =============================================================================
# Body classification tables (Predicate / Type / Robust Hardness)
# =============================================================================

def _latex_body_table(
    rows: list[dict],
    caption: str,
    label: str,
) -> str:
    """Emit the main-body classification table: Predicate | Type | Robust Hardness."""
    out = [
        r"\begin{table}[H]",
        r"\centering",
        r"\footnotesize",
        r"\renewcommand{\arraystretch}{1.2}",
        r"\begin{tabular}{|p{0.55\textwidth}|c|c|}",
        r"\hline",
        r"Predicate $P$ & Type & Robust Hardness \\",
        r"\hline",
    ]
    for row in rows:
        cls = classify_predicate(row["predicate"])
        pred_str = _format_predicate_latex_row(row)
        type_label = cls["type"]
        # Every interior predicate gets a hardness checkmark; the paper's
        # \Cref{thm: no robust algo from interior R} applies to every balanced
        # interior inductive predicate (the orthogonal case is handled via
        # Regev--Klartag in the proof of the multivariate RHC theorem).
        hardness = r"$\checkmark$" if cls["type"] == "interior" else ""
        out.append(f"{pred_str} & {type_label} & {hardness} \\\\")
        out.append(r"\hline")
    out.append(r"\end{tabular}")
    out.append(f"\\caption{{{caption}}}")
    out.append(f"\\label{{{label}}}")
    out.append(r"\end{table}")
    return "\n".join(out)


# =============================================================================
# Farkas certificate table
# =============================================================================

def _latex_farkas_y(y: list[Fraction]) -> str:
    """Emit a Farkas dual vector $y$ as a one-line list."""
    return r"$(" + ", ".join(_format_fraction_latex(c) for c in y) + r")$"


def _latex_farkas_table(
    farkas_data: list[tuple[str, int, dict]],
    caption: str,
    label: str,
) -> str:
    """Emit the Farkas certificate table.

    ``farkas_data`` is a list of ``(source_table_label, row_index, cert_dict)``.
    """
    if not farkas_data:
        return ""
    out = [
        r"\begin{table}[H]",
        r"\centering",
        r"\footnotesize",
        r"\renewcommand{\arraystretch}{1.1}",
        r"\begin{tabular}{|l|p{0.78\textwidth}|}",
        r"\hline",
        r"Source & Farkas dual $y$ (with $y^\top A_{\mathrm{eq}}\geq 0$ and $y^\top b_{\mathrm{eq}}=-1$) \\",
        r"\hline",
    ]
    for source_label, row_idx, cert in farkas_data:
        out.append(
            f"{source_label} row {row_idx} & {_latex_farkas_y(cert['y'])} \\\\"
        )
        out.append(r"\hline")
    out.append(r"\end{tabular}")
    out.append(f"\\caption{{{caption}}}")
    out.append(f"\\label{{{label}}}")
    out.append(r"\end{table}")
    return "\n".join(out)


# =============================================================================
# Captions, labels, file-name metadata
# =============================================================================

BODY_TABLE_META = {
    14: {
        "name": "max_k_4",
        "caption": (
            "Maximal promise-useful predicates for $k=4$ "
            "(\\cite[Table~14]{austrin2026usefulness}); a~$\\texttt{*}$ indicates "
            "a coordinate that is free to take either value."
        ),
        "label": "tab: k4 max useful",
    },
    15: {
        "name": "min_k_4",
        "caption": (
            "Minimal promise-useless predicates for $k=4$ "
            "(\\cite[Table~15]{austrin2026usefulness})."
        ),
        "label": "tab: k4 min useless",
    },
    21: {
        "name": "min_k_5",
        "caption": (
            "Minimal predicates for $k=5$ with unknown promise-usefulness status "
            "(\\cite[Table~21]{austrin2026usefulness})."
        ),
        "label": "tab: k5 min unknown",
    },
    22: {
        "name": "max_k_5",
        "caption": (
            "Maximal predicates for $k=5$ with unknown promise-usefulness status "
            "(\\cite[Table~22]{austrin2026usefulness})."
        ),
        "label": "tab: k5 max unknown",
    },
}

APPENDIX_TABLE_META = {
    14: {
        "name": "app_max_k_4",
        "caption": (
            "Witnesses for the inductive rows of \\Cref{tab: k4 max useful} "
            "(maximal promise-useful, $k=4$)."
        ),
        "label": "app-tab: k4 max useful witnesses",
    },
    15: {
        "name": "app_min_k_4",
        "caption": (
            "Witnesses for the inductive rows of \\Cref{tab: k4 min useless} "
            "(minimal promise-useless, $k=4$)."
        ),
        "label": "app-tab: k4 min useless witnesses",
    },
    21: {
        "name": "app_min_k_5",
        "caption": (
            "Witnesses for the inductive rows of \\Cref{tab: k5 min unknown} "
            "(minimal unknown-status, $k=5$); non-inductive rows omitted."
        ),
        "label": "app-tab: k5 min unknown witnesses",
    },
    22: {
        "name": "app_max_k_5",
        "caption": (
            "Witnesses for the inductive rows of \\Cref{tab: k5 max unknown} "
            "(maximal unknown-status, $k=5$); non-inductive rows omitted."
        ),
        "label": "app-tab: k5 max unknown witnesses",
    },
}

FARKAS_CAPTION = (
    "Exact rational Farkas certificates for the non-inductive rows of "
    "\\Cref{tab: k5 min unknown}. For each predicate $P$ the displayed $y$ "
    "satisfies $y^\\top A_{\\mathrm{eq}}\\geq 0$ component-wise and "
    "$y^\\top b_{\\mathrm{eq}}=-1$ for the identity-permutation LP, "
    "certifying its infeasibility; analogous certificates for each of the "
    "$k!$ coordinate permutations (verified by the script) establish that "
    "$P$ is non-inductive under the balanced-staircase condition."
)
FARKAS_LABEL = "app-tab: farkas"

_TABLE_LABEL_MAP = {
    14: r"\Cref{tab: k4 max useful}",
    15: r"\Cref{tab: k4 min useless}",
    21: r"\Cref{tab: k5 min unknown}",
    22: r"\Cref{tab: k5 max unknown}",
}


# =============================================================================
# Public entry points: write tables to disk
# =============================================================================

def _gather_farkas_data() -> list[tuple[str, int, dict]]:
    """Scan all tables for non-inductive rows and collect their Farkas certs."""
    data: list[tuple[str, int, dict]] = []
    for table_id, rows in TABLES.items():
        for row in rows:
            cls = classify_predicate(row["predicate"])
            if cls["type"] == "non-inductive" and cls.get("farkas") is not None:
                data.append((_TABLE_LABEL_MAP[table_id], row["index"], cls["farkas"]))
    return data


def emit_all_tables(out_dir: str = "tables") -> None:
    """Emit all body and appendix tables as individual LaTeX files.

    Writes to ``out_dir/``:

      - ``max_k_4.tex``, ``min_k_4.tex``, ``min_k_5.tex``, ``max_k_5.tex``
        (body classification tables);
      - ``app_max_k_4.tex``, ``app_min_k_4.tex``, ``app_min_k_5.tex``,
        ``app_max_k_5.tex`` (appendix witness tables);
      - ``farkas.tex`` (Farkas certificates for non-inductive predicates).

    Each file contains exactly one LaTeX table or longtable environment with a
    caption and label, ready to be ``\\input{}``-ed from the paper's main file.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Body tables.
    for table_id, rows in TABLES.items():
        meta = BODY_TABLE_META[table_id]
        body = _latex_body_table(rows, meta["caption"], meta["label"])
        with open(os.path.join(out_dir, f"{meta['name']}.tex"), "w") as f:
            f.write(body + "\n")

    # Appendix witness tables.
    for table_id, rows in TABLES.items():
        meta = APPENDIX_TABLE_META[table_id]
        body = _latex_witness_table(rows, meta["caption"], meta["label"])
        if body:
            with open(os.path.join(out_dir, f"{meta['name']}.tex"), "w") as f:
                f.write(body + "\n")

    # Farkas table.
    farkas_data = _gather_farkas_data()
    if farkas_data:
        body = _latex_farkas_table(farkas_data, FARKAS_CAPTION, FARKAS_LABEL)
        with open(os.path.join(out_dir, "farkas.tex"), "w") as f:
            f.write(body + "\n")


# =============================================================================
# Console summary (for human inspection on the command line)
# =============================================================================

def print_classification_summary() -> None:
    """Console summary: classify every row, print type and key data."""
    for table_id, rows in TABLES.items():
        print(f"=== Table {table_id}: {len(rows)} rows ===")
        for row in rows:
            cls = classify_predicate(row["predicate"])
            tag = f"  {row['index']:2d}. |P|={len(row['predicate']):2d}"
            if cls["type"] == "non-inductive":
                cert_ok = cls["farkas"] is not None
                print(f"{tag}  non-inductive  Farkas cert: {'OK' if cert_ok else 'MISSING'}")
            else:
                r_str = "(" + ", ".join(_format_fraction_latex(c) for c in cls["r"]) + ")"
                print(
                    f"{tag}  {cls['type']:8s}  "
                    f"|supp(λ)|={len(cls['support']):2d}  "
                    f"det R = {_format_fraction_latex(cls['det_G'])}  r={r_str}"
                )
        print()
