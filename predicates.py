"""Boolean predicate families from Austrin--H{\aa}stad--Martinsson (SODA 2026).

We reproduce four tables of predicates from~\\cite{austrin2026usefulness}:

  - ``TABLE_14``  Maximal promise-useful predicates of arity $k=4$.
  - ``TABLE_15``  Minimal promise-useless predicates of arity $k=4$.
  - ``TABLE_21``  Minimal predicates of arity $k=5$ with unknown promise-usefulness status.
  - ``TABLE_22``  Maximal predicates of arity $k=5$ with unknown promise-usefulness status.

Each row is a dictionary with at least the keys ``index`` (1-based row index in
the source paper) and ``predicate`` (the explicit set of accepted bitstrings,
one bitstring per element of $P$). Optional keys carry display data used by the
LaTeX table generator (see ``tables.py``):

  - ``display``  An abbreviated representation of $P$ using ``*`` wildcards.
  - ``maj``      Whether $P$ admits a majority polymorphism.
  - ``par``      Whether $P$ admits a parity polymorphism.
  - ``dep``      The reference's "dep" descriptor for the row.

Bitstring convention: ``0`` and ``1`` denote the two Boolean values; the
verifier maps ``0 -> -1`` and ``1 -> +1`` when computing first/second moments.
"""

from __future__ import annotations


TABLE_14: list[dict] = [
    {
        "index": 1,
        "predicate": [
            "0000", "0001", "0010", "0011",
            "0100", "0101", "0110", "0111",
            "1000", "1001", "1010", "1011",
        ],
        "display": ["00**", "01**", "10**"],
        "maj": True, "par": False, "dep": "91/216",
    },
    {
        "index": 2,
        "predicate": [
            "0000", "0001", "0010", "0011",
            "0100", "0101", "0110",
            "1000", "1001", "1010", "1100",
        ],
        "maj": True, "par": False, "dep": "8/132",
    },
    {
        "index": 3,
        "predicate": [
            "0000", "0001",
            "0110", "0111",
            "1010", "1011",
            "1100", "1101",
        ],
        "display": ["000*", "011*", "101*", "110*"],
        "maj": False, "par": True, "dep": "3/21",
    },
    {
        "index": 4,
        "predicate": [
            "0001", "0010", "0100", "0111",
            "1000", "1011", "1101", "1110",
        ],
        "maj": False, "par": True, "dep": "1/15",
    },
]


TABLE_15: list[dict] = [
    {"index": 1, "predicate": ["0000", "0111", "1001", "1010", "1100"], "dep": "19/132"},
    {"index": 2, "predicate": ["0001", "0010", "0011", "0111", "1001", "1010", "1100"], "dep": "3/105"},
    {"index": 3, "predicate": ["0011", "0100", "0111", "1001", "1010", "1100"], "dep": "10/138"},
    {"index": 4, "predicate": ["0011", "0101", "0110", "0111", "1000", "1001", "1010", "1100"], "dep": "1/39"},
    {"index": 5, "predicate": ["0011", "0100", "0110", "0111", "1000", "1001", "1011", "1100"], "dep": "1/29"},
]


TABLE_21: list[dict] = [
    {"index": 1, "predicate": ["00011", "01101", "01110", "10011", "10100", "11000"], "dep": "13/18"},
    {"index": 2, "predicate": ["00110", "00111", "01001", "01101", "01110", "10011", "10100", "11000"], "dep": "2/16"},
    {"index": 3, "predicate": ["00111", "01001", "01010", "01101", "01110", "10011", "10100", "11000"], "dep": "3/14"},
    {"index": 4, "predicate": ["00110", "01001", "01100", "01101", "01110", "10011", "10100", "11000"], "dep": "1/12"},
    {"index": 5, "predicate": ["00110", "01010", "01101", "01111", "10000", "10011", "10100", "11000"], "dep": "1/1"},
    {"index": 6, "predicate": ["00110", "01001", "01101", "01110", "10001", "10011", "10100", "11000"], "dep": "2/14"},
    {"index": 7, "predicate": ["00111", "01010", "01101", "01110", "10001", "10011", "10100", "11000"], "dep": "6/24"},
    {"index": 8, "predicate": ["00111", "01011", "01100", "01101", "01110", "10001", "10010", "10011", "10100", "11000"], "dep": "1/4"},
    {"index": 9, "predicate": ["00111", "01000", "01100", "01110", "01111", "10000", "10001", "10011", "10111", "11000"], "dep": "1/1"},
]


TABLE_22: list[dict] = [
    {"index": 1, "predicate": ["00011", "00110", "00111", "01001", "01100", "01101", "01110", "10011", "10100", "11000"], "dep": "6/17"},
    {"index": 2, "predicate": ["00011", "00111", "01001", "01010", "01100", "01101", "01110", "10011", "10100", "11000"], "dep": "4/14"},
    {"index": 3, "predicate": ["00110", "01010", "01101", "01111", "10000", "10011", "10100", "11000"], "dep": "1/1"},
    {"index": 4, "predicate": ["00101", "00110", "00111", "01011", "01100", "01101", "01110", "10001", "10010", "10011", "10100", "11000"], "dep": "8/19"},
    {"index": 5, "predicate": ["00110", "00111", "01001", "01011", "01100", "01101", "01110", "10001", "10010", "10011", "10100", "11000"], "dep": "16/27"},
    {"index": 6, "predicate": ["00111", "01001", "01011", "01100", "01110", "10010", "10011", "10100", "10101", "11000"], "dep": "1/4"},
    {"index": 7, "predicate": ["00111", "01000", "01100", "01110", "01111", "10000", "10001", "10011", "10111", "11000"], "dep": "1/1"},
]


# Convenience: dictionary keyed by source-paper table number.
TABLES: dict[int, list[dict]] = {
    14: TABLE_14,
    15: TABLE_15,
    21: TABLE_21,
    22: TABLE_22,
}
