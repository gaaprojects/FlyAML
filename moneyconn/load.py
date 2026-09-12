"""Read the IBM synthetic AML transaction data with compact dtypes.

Two inputs, both from the Kaggle dataset
``ealtman2019/ibm-transactions-for-anti-money-laundering-aml`` (HI-Small variant):

``HI-Small_Trans.csv``
    ~5.08M transactions between ~515k accounts over ~10 simulated days,
    ~0.1% of them labelled as laundering.
``HI-Small_Patterns.txt``
    The subset of laundering transactions grouped into labelled attempts
    (fan-out, fan-in, gather-scatter, scatter-gather, cycle, random, bipartite,
    stack). Most laundering transactions are *not* in this file, so per-pattern
    analysis uses these rows only, while overall metrics use all
    ``is_laundering`` labels.

Gotchas baked in here:

* The CSV has two columns literally named ``Account``; pandas mangles the
  second one to ``Account.1``. Columns are renamed to snake_case immediately,
  so nothing downstream depends on that.
* Bank ids keep their file representation (``"011"`` stays ``"011"``) by being
  read as ``category`` rather than ``int``, because the account id is
  ``f"{bank}_{account}"`` and must round-trip to the source rows.
* ``src``/``dst`` are categoricals over one **shared** account universe, so
  ``df["src"].cat.codes`` and ``df["dst"].cat.codes`` are directly usable as
  igraph vertex ids in :mod:`moneyconn.graph`.

The 5M-row file never touches the dev laptop: this module is unit-tested on the
tiny CSV in ``tests/data/`` and run at scale from the Kaggle notebooks.
"""

from __future__ import annotations

import csv
import logging
import re
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd

LOGGER = logging.getLogger("moneyconn")

#: Raw CSV header (as pandas mangles it) -> canonical snake_case name.
TRANS_COLUMNS: dict[str, str] = {
    "Timestamp": "timestamp",
    "From Bank": "from_bank",
    "Account": "from_account",
    "To Bank": "to_bank",
    "Account.1": "to_account",
    "Amount Received": "amount_received",
    "Receiving Currency": "receiving_currency",
    "Amount Paid": "amount_paid",
    "Payment Currency": "payment_currency",
    "Payment Format": "payment_format",
    "Is Laundering": "is_laundering",
}

#: Column order of the raw rows, used for the patterns file (which has no header).
TRANS_FIELDS: tuple[str, ...] = tuple(TRANS_COLUMNS.values())

#: Compact dtypes, keyed by the *raw* column names that ``read_csv`` sees.
TRANS_DTYPES: dict[str, str] = {
    "From Bank": "category",
    "Account": "category",
    "To Bank": "category",
    "Account.1": "category",
    "Amount Received": "float32",
    "Receiving Currency": "category",
    "Amount Paid": "float32",
    "Payment Currency": "category",
    "Payment Format": "category",
    "Is Laundering": "int8",
}

TIMESTAMP_FORMAT = "%Y/%m/%d %H:%M"

_BEGIN_RE = re.compile(r"^\s*BEGIN\s+LAUNDERING\s+ATTEMPT\s*[-:]\s*(?P<pattern>.+?)\s*$", re.I)
_END_RE = re.compile(r"^\s*END\s+LAUNDERING\s+ATTEMPT", re.I)


# --------------------------------------------------------------------------- #
# Instrumentation (the P0 acceptance criteria ask for peak RAM per step)
# --------------------------------------------------------------------------- #
def peak_ram_mb() -> float | None:
    """Peak resident set size of this process in MiB, or ``None`` if unknown.

    Uses ``resource`` on POSIX (Kaggle), ``psutil`` or the Win32 API locally.
    """
    try:  # POSIX: Kaggle, Colab
        import resource

        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports KiB, macOS bytes.
        return peak / 1024 if sys.platform != "darwin" else peak / 1024**2
    except ImportError:
        pass

    try:
        import psutil  # optional

        return psutil.Process().memory_info().peak_wset / 1024**2  # type: ignore[attr-defined]
    except Exception:
        pass

    if sys.platform == "win32":  # dependency-free fallback
        try:
            import ctypes
            from ctypes import wintypes

            class _Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            # Explicit signatures matter: the default 32-bit restype mangles the
            # process pseudo-handle on 64-bit Windows and the call fails.
            kernel32.GetCurrentProcess.argtypes = []
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi.GetProcessMemoryInfo.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(_Counters),
                wintypes.DWORD,
            ]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

            counters = _Counters()
            counters.cb = ctypes.sizeof(_Counters)
            if psapi.GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
            ):
                return counters.PeakWorkingSetSize / 1024**2
        except Exception:
            pass
    return None


@contextmanager
def log_step(label: str, logger: logging.Logger | None = None) -> Iterator[None]:
    """Log wall time and peak RAM around a step.

    Usage::

        with log_step("load transactions"):
            df = load_transactions(path)
    """
    log = logger or LOGGER
    start = time.perf_counter()
    log.info("%s: start", label)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        peak = peak_ram_mb()
        peak_txt = f"{peak:,.0f} MiB" if peak is not None else "unknown"
        log.info("%s: done in %.1f s (peak RAM %s)", label, elapsed, peak_txt)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Send ``moneyconn`` logs to stdout. Convenience for notebooks."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S"))
    LOGGER.handlers = [handler]
    LOGGER.setLevel(level)
    LOGGER.propagate = False
    return LOGGER


# --------------------------------------------------------------------------- #
# Account ids
# --------------------------------------------------------------------------- #
def _as_category(values: pd.Series) -> pd.Series:
    return values if isinstance(values.dtype, pd.CategoricalDtype) else values.astype("category")


def _combine_ids(bank: pd.Series, account: pd.Series) -> pd.Categorical:
    """Build ``f"{bank}_{account}"`` as a categorical.

    Strings are materialised only for the *distinct* (bank, account) pairs, not
    once per row, which keeps the 5M-row case cheap.
    """
    bank, account = _as_category(bank), _as_category(account)
    bank_cats = pd.Index(bank.cat.categories).astype(str)
    acct_cats = pd.Index(account.cat.categories).astype(str)

    stride = np.int64(len(acct_cats) + 1)
    # Missing codes are -1; +1 keeps the combined key non-negative.
    key = (bank.cat.codes.to_numpy().astype(np.int64) + 1) * stride + (
        account.cat.codes.to_numpy().astype(np.int64) + 1
    )
    codes, uniques = pd.factorize(key)
    bank_idx = (uniques // stride) - 1
    acct_idx = (uniques % stride) - 1
    labels = [
        f"{bank_cats[b]}_{acct_cats[a]}" if b >= 0 and a >= 0 else ""
        for b, a in zip(bank_idx, acct_idx)
    ]
    return pd.Categorical.from_codes(codes, categories=pd.Index(labels))


def add_account_ids(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``src``/``dst`` account ids in place, as categoricals sharing one universe.

    Account id is ``f"{bank}_{account}"`` (spec 8.1): the same account number at
    two different banks is two different accounts.
    """
    src = _combine_ids(df["from_bank"], df["from_account"])
    dst = _combine_ids(df["to_bank"], df["to_account"])
    universe = pd.Index(src.categories).union(pd.Index(dst.categories))
    df["src"] = src.set_categories(universe)
    df["dst"] = dst.set_categories(universe)
    return df


def accounts(df: pd.DataFrame) -> pd.Index:
    """The shared account universe of ``src``/``dst``, sorted."""
    return pd.Index(df["src"].cat.categories, name="account")


# --------------------------------------------------------------------------- #
# Transactions
# --------------------------------------------------------------------------- #
def load_transactions(
    path: str | Path,
    *,
    nrows: int | None = None,
    with_account_ids: bool = True,
) -> pd.DataFrame:
    """Read ``HI-Small_Trans.csv`` (or a sibling variant) with compact dtypes.

    Parameters
    ----------
    path:
        Path to the transactions CSV.
    nrows:
        Read only the first ``nrows`` rows (smoke tests on Kaggle).
    with_account_ids:
        Also build the ``src``/``dst`` account ids.

    Returns
    -------
    DataFrame with columns ``timestamp`` (datetime64[s]), ``from_bank``,
    ``from_account``, ``to_bank``, ``to_account``, ``receiving_currency``,
    ``payment_currency``, ``payment_format`` (category), ``amount_received``,
    ``amount_paid`` (float32), ``is_laundering`` (int8) and, optionally,
    ``src``/``dst`` (category).
    """
    df = pd.read_csv(path, dtype=TRANS_DTYPES, nrows=nrows)
    missing = set(TRANS_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"{Path(path).name} is missing expected columns {sorted(missing)}; "
            f"found {list(df.columns)}"
        )
    df = df.rename(columns=TRANS_COLUMNS)[list(TRANS_COLUMNS.values())]
    df["timestamp"] = pd.to_datetime(df["timestamp"], format=TIMESTAMP_FORMAT).astype(
        "datetime64[s]"
    )
    if with_account_ids:
        add_account_ids(df)
    return df


# --------------------------------------------------------------------------- #
# Patterns file
# --------------------------------------------------------------------------- #
def parse_patterns(path: str | Path, *, with_account_ids: bool = True) -> pd.DataFrame:
    """Parse ``HI-Small_Patterns.txt`` into one row per pattern transaction.

    The file is a sequence of blocks::

        BEGIN LAUNDERING ATTEMPT - FAN-OUT
        <raw transaction line>
        ...
        END LAUNDERING ATTEMPT - FAN-OUT

    Returns
    -------
    DataFrame with the transaction columns plus ``attempt_id`` (int32, one per
    ``BEGIN`` block) and ``pattern`` (category, upper-cased). Rows keep their
    file order.
    """
    records: list[list[str]] = []
    attempt_ids: list[int] = []
    patterns: list[str] = []
    attempt_id = -1
    current: str | None = None

    with open(path, "r", encoding="utf-8", newline="") as handle:
        for lineno, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            begin = _BEGIN_RE.match(line)
            if begin:
                attempt_id += 1
                current = begin.group("pattern").strip().upper()
                continue
            if _END_RE.match(line):
                current = None
                continue
            if current is None:  # stray header / footer text
                continue
            row = next(csv.reader([line]))
            if len(row) != len(TRANS_FIELDS):
                raise ValueError(
                    f"{Path(path).name}:{lineno}: expected {len(TRANS_FIELDS)} fields, "
                    f"got {len(row)}"
                )
            records.append(row)
            attempt_ids.append(attempt_id)
            patterns.append(current)

    df = pd.DataFrame(records, columns=list(TRANS_FIELDS))
    df["attempt_id"] = pd.array(attempt_ids, dtype="int32")
    df["pattern"] = pd.Categorical(patterns)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format=TIMESTAMP_FORMAT).astype(
        "datetime64[s]"
    )
    for col in ("amount_received", "amount_paid"):
        df[col] = df[col].astype("float32")
    df["is_laundering"] = df["is_laundering"].astype("int8")
    for col in (
        "from_bank",
        "from_account",
        "to_bank",
        "to_account",
        "receiving_currency",
        "payment_currency",
        "payment_format",
    ):
        df[col] = df[col].astype("category")
    if with_account_ids:
        add_account_ids(df)
    return df


def pattern_counts(patterns: pd.DataFrame) -> pd.DataFrame:
    """Transactions and attempts per pattern type."""
    grouped = patterns.groupby("pattern", observed=True)
    out = pd.DataFrame(
        {
            "transactions": grouped.size(),
            "attempts": grouped["attempt_id"].nunique(),
        }
    )
    return out.sort_values("transactions", ascending=False)


# --------------------------------------------------------------------------- #
# Summaries (P0 acceptance criteria)
# --------------------------------------------------------------------------- #
def summarize_transactions(df: pd.DataFrame) -> dict[str, object]:
    """Headline numbers for the P0 acceptance criteria.

    Expected on HI-Small: ~5.08M transactions, ~515k accounts, laundering share
    ~0.1%.
    """
    n_rows = len(df)
    n_laundering = int(df["is_laundering"].sum())
    summary: dict[str, object] = {
        "transactions": n_rows,
        "laundering_transactions": n_laundering,
        "laundering_share": (n_laundering / n_rows) if n_rows else float("nan"),
        "banks": int(
            pd.concat([df["from_bank"].astype(str), df["to_bank"].astype(str)]).nunique()
        ),
        "currencies": int(df["payment_currency"].nunique()),
        "payment_formats": int(df["payment_format"].nunique()),
        "first_timestamp": df["timestamp"].min(),
        "last_timestamp": df["timestamp"].max(),
        "memory_mb": float(df.memory_usage(deep=True).sum() / 1024**2),
        "peak_ram_mb": peak_ram_mb(),
    }
    if "src" in df.columns:
        summary["accounts"] = int(len(accounts(df)))
    return summary


def account_tx_counts(df: pd.DataFrame) -> pd.DataFrame:
    """Per-account transaction counts: ``sent``, ``received``, ``total``.

    Transaction counts, not counterparty counts -- the degree distributions of
    the aggregated graph come later from :mod:`moneyconn.graph`. This is enough
    for the P0 sanity plot.
    """
    index = accounts(df)
    sent = df["src"].value_counts().reindex(index, fill_value=0)
    received = df["dst"].value_counts().reindex(index, fill_value=0)
    out = pd.DataFrame(
        {"sent": sent.astype("int64"), "received": received.astype("int64")}, index=index
    )
    out["total"] = out["sent"] + out["received"]
    return out.sort_values("total", ascending=False)
