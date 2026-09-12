"""Loader tests, on the miniature CSV in ``tests/data``.

The toy file has the real header -- including the two columns literally named
``Account`` -- 10 transactions, 5 accounts, 2 laundering rows and one self-loop.
"""

from __future__ import annotations

import logging

import pandas as pd
import pytest

from moneyconn import load

EXPECTED_ACCOUNTS = ["011_A1", "012_B2", "020_C3", "030_D4", "040_E5"]


# --------------------------------------------------------------------------- #
# Transactions
# --------------------------------------------------------------------------- #
def test_columns_are_canonical(toy_transactions):
    assert list(toy_transactions.columns) == [
        "timestamp",
        "from_bank",
        "from_account",
        "to_bank",
        "to_account",
        "amount_received",
        "receiving_currency",
        "amount_paid",
        "payment_currency",
        "payment_format",
        "is_laundering",
        "src",
        "dst",
    ]


def test_dtypes_are_compact(toy_transactions):
    dtypes = toy_transactions.dtypes
    assert dtypes["timestamp"] == "datetime64[s]"
    assert dtypes["amount_paid"] == "float32"
    assert dtypes["amount_received"] == "float32"
    assert dtypes["is_laundering"] == "int8"
    for col in ("from_bank", "from_account", "to_bank", "to_account", "payment_format", "src", "dst"):
        assert isinstance(dtypes[col], pd.CategoricalDtype), col


def test_second_account_column_becomes_to_account(toy_transactions):
    """The ``Account`` / ``Account.1`` gotcha: the 2nd one is the destination."""
    first = toy_transactions.iloc[0]
    assert first["from_account"] == "A1"
    assert first["to_account"] == "B2"


def test_timestamps_are_parsed(toy_transactions):
    assert toy_transactions["timestamp"].iloc[0] == pd.Timestamp("2022-09-01 00:00")
    assert toy_transactions["timestamp"].iloc[-1] == pd.Timestamp("2022-09-02 04:00")
    assert toy_transactions["timestamp"].is_monotonic_increasing


def test_account_id_is_bank_underscore_account(toy_transactions):
    assert toy_transactions["src"].iloc[0] == "011_A1"
    assert toy_transactions["dst"].iloc[0] == "012_B2"
    # Bank ids keep their leading zeros, so account ids round-trip to the file.
    assert all(account.split("_")[0].isdigit() for account in EXPECTED_ACCOUNTS)


def test_src_and_dst_share_one_category_universe(toy_transactions):
    src, dst = toy_transactions["src"], toy_transactions["dst"]
    assert list(src.cat.categories) == list(dst.cat.categories) == EXPECTED_ACCOUNTS
    # Shared categories mean the codes are usable directly as igraph vertex ids.
    assert src.cat.codes.iloc[0] == EXPECTED_ACCOUNTS.index("011_A1")
    assert dst.cat.codes.iloc[0] == EXPECTED_ACCOUNTS.index("012_B2")


def test_same_account_number_at_two_banks_is_two_accounts():
    """``f"{bank}_{account}"``, not the bare account number (spec 8.1)."""
    frame = pd.DataFrame(
        {
            "from_bank": ["011", "012"],
            "from_account": ["A1", "A1"],
            "to_bank": ["020", "020"],
            "to_account": ["C3", "C3"],
        }
    ).astype("category")
    load.add_account_ids(frame)
    assert list(frame["src"]) == ["011_A1", "012_A1"]


def test_accounts_returns_the_universe(toy_transactions):
    accounts = load.accounts(toy_transactions)
    assert list(accounts) == EXPECTED_ACCOUNTS
    assert accounts.name == "account"


def test_nrows_limits_the_read(toy_trans_path):
    assert len(load.load_transactions(toy_trans_path, nrows=3)) == 3


def test_account_ids_can_be_skipped(toy_trans_path):
    frame = load.load_transactions(toy_trans_path, with_account_ids=False)
    assert "src" not in frame.columns


def test_missing_columns_raise(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Timestamp,From Bank,Account\n2022/09/01 00:00,011,A1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing expected columns"):
        load.load_transactions(bad)


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #
def test_summarize_transactions(toy_transactions):
    summary = load.summarize_transactions(toy_transactions)
    assert summary["transactions"] == 10
    assert summary["laundering_transactions"] == 2
    assert summary["laundering_share"] == pytest.approx(0.2)
    assert summary["accounts"] == 5
    assert summary["banks"] == 5
    assert summary["payment_formats"] == 5
    assert summary["first_timestamp"] == pd.Timestamp("2022-09-01 00:00")
    assert summary["memory_mb"] > 0


def test_account_tx_counts(toy_transactions):
    counts = load.account_tx_counts(toy_transactions)
    assert list(counts.index) == ["011_A1", "012_B2", "020_C3", "030_D4", "040_E5"]
    assert counts.loc["011_A1", "sent"] == 3  # incl. the self-loop
    assert counts.loc["011_A1", "received"] == 3
    assert counts.loc["040_E5", "total"] == 2
    # Every transaction contributes one sent and one received leg.
    assert counts["sent"].sum() == counts["received"].sum() == len(toy_transactions)
    assert counts["total"].is_monotonic_decreasing


def test_peak_ram_is_reported_or_explicitly_unknown():
    peak = load.peak_ram_mb()
    assert peak is None or peak > 0


def test_log_step_logs_timing(caplog):
    with caplog.at_level(logging.INFO, logger="moneyconn"):
        with load.log_step("toy step"):
            pass
    messages = [record.getMessage() for record in caplog.records]
    assert any("toy step: start" in message for message in messages)
    assert any("toy step: done" in message for message in messages)


# --------------------------------------------------------------------------- #
# Patterns file
# --------------------------------------------------------------------------- #
def test_parse_patterns_rows_and_attempts(toy_patterns):
    assert len(toy_patterns) == 5
    assert toy_patterns["attempt_id"].tolist() == [0, 0, 1, 1, 1]
    assert toy_patterns["pattern"].tolist() == ["FAN-OUT"] * 2 + ["CYCLE"] * 3
    assert toy_patterns["is_laundering"].eq(1).all()


def test_parse_patterns_dtypes_and_ids(toy_patterns):
    assert toy_patterns["timestamp"].iloc[0] == pd.Timestamp("2022-09-01 01:10")
    assert toy_patterns["amount_paid"].dtype == "float32"
    assert toy_patterns["src"].iloc[0] == "020_C3"
    assert toy_patterns["dst"].iloc[0] == "030_D4"
    assert toy_patterns["amount_paid"].iloc[2] == pytest.approx(1000.0)
    assert toy_patterns["receiving_currency"].iloc[2] == "Euro"


def test_pattern_counts(toy_patterns):
    counts = load.pattern_counts(toy_patterns)
    assert counts.loc["CYCLE", "transactions"] == 3
    assert counts.loc["CYCLE", "attempts"] == 1
    assert counts.loc["FAN-OUT", "transactions"] == 2
    assert counts["transactions"].sum() == len(toy_patterns)


def test_pattern_accounts_are_a_subset_of_the_transaction_accounts(toy_patterns):
    involved = set(toy_patterns["src"]) | set(toy_patterns["dst"])
    assert involved <= set(EXPECTED_ACCOUNTS)


def test_blank_lines_and_stray_text_are_skipped(tmp_path):
    path = tmp_path / "patterns.txt"
    path.write_text(
        "some header line\n"
        "\n"
        "BEGIN LAUNDERING ATTEMPT - STACK\n"
        "2022/09/01 00:00,011,A1,012,B2,1.00,US Dollar,1.00,US Dollar,Cheque,1\n"
        "END LAUNDERING ATTEMPT - STACK\n"
        "\n",
        encoding="utf-8",
    )
    frame = load.parse_patterns(path)
    assert len(frame) == 1
    assert frame["pattern"].iloc[0] == "STACK"


def test_malformed_pattern_row_raises(tmp_path):
    path = tmp_path / "patterns.txt"
    path.write_text(
        "BEGIN LAUNDERING ATTEMPT - STACK\n2022/09/01 00:00,011,A1\nEND LAUNDERING ATTEMPT\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="expected 11 fields"):
        load.parse_patterns(path)
