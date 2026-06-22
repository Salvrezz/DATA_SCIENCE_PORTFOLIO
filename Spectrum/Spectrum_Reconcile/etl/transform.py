"""
transform.py — Transaction-level reconciliation engine.

METHODOLOGY (greedy 1:1 date+amount match, per location):
-----------------------------------------------------------
  Step 1: KiliMax side = Receive Payment, Debit(NGN) > 0  (done in extract.py)
  Step 2: PalmPay side = Successful transactions, deduplicated (done in extract.py)
  Step 3: For each location, for each calendar date, greedily match each
          KiliMax amount to the first unused PalmPay amount equal to it
          on that same date (1:1, no reuse).
  Step 4: Remaining unmatched KiliMax rows  → "KM Only (Unmatched)"
          Remaining unmatched PalmPay rows  → "PP Only (Unmatched)"

This produces a transaction-level audit trail per branch, matching the
approved methodology (see Formula_Guide sheet in the reference workbook).
"""

import pandas as pd
from collections import defaultdict


def match_location(pp_loc: pd.DataFrame, pos_loc: pd.DataFrame) -> pd.DataFrame:
    """
    Greedy date+amount 1:1 match between one location's PalmPay and POS rows.
    Returns a combined DataFrame with Status: MATCHED / KM Only / PP Only.
    """
    # Bucket POS rows by (date, amount) → list of row dicts, FIFO
    pos_buckets = defaultdict(list)
    for _, row in pos_loc.iterrows():
        key = (row["Document Date"], round(float(row["Debit(NGN)"]), 2))
        pos_buckets[key].append(row)

    matched_rows  = []
    pp_only_rows  = []
    used_pos_idx  = set()

    # Walk PalmPay rows in original order; try to match against POS bucket
    for _, pp_row in pp_loc.iterrows():
        key = (pp_row["Update Time"], round(float(pp_row["Order Amount"]), 2))
        bucket = pos_buckets.get(key)
        if bucket:
            pos_row = bucket.pop(0)  # consume one matching POS row (FIFO)
            matched_rows.append({
                "Date":             pp_row["Update Time"],
                "KiliMax Doc No":   pos_row["Document Number"],
                "KiliMax Partner":  pos_row["Business Partner"],
                "KiliMax Amt":      pos_row["Debit(NGN)"],
                "PalmPay Txn ID":   pp_row["Transaction Order No"],
                "PalmPay Payer":    None,  # not present in source; kept for schema parity
                "PalmPay Amt":      pp_row["Order Amount"],
                "PalmPay Type":     pp_row["Order Type"],
                "Diff":             0.0,
                "Status":           "MATCHED",
            })
        else:
            pp_only_rows.append({
                "Date":             pp_row["Update Time"],
                "KiliMax Doc No":   None,
                "KiliMax Partner":  None,
                "KiliMax Amt":      None,
                "PalmPay Txn ID":   pp_row["Transaction Order No"],
                "PalmPay Payer":    None,
                "PalmPay Amt":      pp_row["Order Amount"],
                "PalmPay Type":     pp_row["Order Type"],
                "Diff":             -pp_row["Order Amount"],
                "Status":           "PP Only (Unmatched)",
            })

    # Whatever remains in pos_buckets was never claimed → KM Only
    km_only_rows = []
    for key, remaining in pos_buckets.items():
        for pos_row in remaining:
            km_only_rows.append({
                "Date":             pos_row["Document Date"],
                "KiliMax Doc No":   pos_row["Document Number"],
                "KiliMax Partner":  pos_row["Business Partner"],
                "KiliMax Amt":      pos_row["Debit(NGN)"],
                "PalmPay Txn ID":   None,
                "PalmPay Payer":    None,
                "PalmPay Amt":      None,
                "PalmPay Type":     None,
                "Diff":             pos_row["Debit(NGN)"],
                "Status":           "KM Only (Unmatched)",
            })

    combined = pd.DataFrame(matched_rows + pp_only_rows + km_only_rows)
    return combined


def run_transform(pp: pd.DataFrame, pos: pd.DataFrame):
    """
    Runs greedy match per location. Returns:
      - detail: full transaction-level table across all locations
      - branch_summary: per-location summary stats
      - overall_summary: company-wide summary stats
      - no_pos_summary: Palmpay shops with no POS sheet (excluded from match)
    """
    from etl.extract import NO_POS_SHEET

    locations = sorted(
        set(pp["Shop Name"].dropna().unique()) | set(pos["Location"].dropna().unique())
    )
    locations = [l for l in locations if l not in NO_POS_SHEET]

    all_detail = []
    branch_rows = []

    for loc in locations:
        pp_loc  = pp[pp["Shop Name"] == loc].sort_values("Update Time")
        pos_loc = pos[pos["Location"] == loc].sort_values("Document Date")

        if pp_loc.empty and pos_loc.empty:
            continue

        combined = match_location(pp_loc, pos_loc)
        combined.insert(0, "Location", loc)
        all_detail.append(combined)

        km_total = pos_loc["Debit(NGN)"].sum()
        pp_total = pp_loc["Order Amount"].sum()
        matched_total = combined.loc[combined["Status"] == "MATCHED", "KiliMax Amt"].sum()
        km_only_total = combined.loc[combined["Status"] == "KM Only (Unmatched)", "KiliMax Amt"].sum()
        pp_only_total = combined.loc[combined["Status"] == "PP Only (Unmatched)", "PalmPay Amt"].sum()
        matched_count = (combined["Status"] == "MATCHED").sum()
        km_only_count = (combined["Status"] == "KM Only (Unmatched)").sum()
        pp_only_count = (combined["Status"] == "PP Only (Unmatched)").sum()
        km_count_total = len(pos_loc)

        recon_rate = (matched_count / km_count_total * 100) if km_count_total else 0

        branch_rows.append({
            "Location":              loc,
            "KiliMax Total Debit":   km_total,
            "Palmpay Total Order":   pp_total,
            "Net Gap (KM-PP)":       km_total - pp_total,
            "Matched Txns":          matched_count,
            "Matched Amt":           matched_total,
            "KM Only Count":         km_only_count,
            "KM Only Amt":           km_only_total,
            "PP Only Count":         pp_only_count,
            "PP Only Amt":           pp_only_total,
            "KiliMax Txn Total":     km_count_total,
            "Reconciliation Rate %": round(recon_rate, 1),
        })

    detail = pd.concat(all_detail, ignore_index=True) if all_detail else pd.DataFrame()
    branch_summary = pd.DataFrame(branch_rows).sort_values("Location").reset_index(drop=True)

    overall = {
        "KiliMax Total Debit":  branch_summary["KiliMax Total Debit"].sum(),
        "Palmpay Total Order":  branch_summary["Palmpay Total Order"].sum(),
        "Net Gap (KM-PP)":      branch_summary["Net Gap (KM-PP)"].sum(),
        "Matched Txns":         branch_summary["Matched Txns"].sum(),
        "Matched Amt":          branch_summary["Matched Amt"].sum(),
        "KM Only Count":        branch_summary["KM Only Count"].sum(),
        "KM Only Amt":          branch_summary["KM Only Amt"].sum(),
        "PP Only Count":        branch_summary["PP Only Count"].sum(),
        "PP Only Amt":          branch_summary["PP Only Amt"].sum(),
        "KiliMax Txn Total":    branch_summary["KiliMax Txn Total"].sum(),
    }
    overall["Reconciliation Rate %"] = round(
        overall["Matched Txns"] / overall["KiliMax Txn Total"] * 100, 1
    ) if overall["KiliMax Txn Total"] else 0

    # No-POS-sheet shops summary
    no_pos_rows = []
    for loc in sorted(NO_POS_SHEET):
        pp_loc = pp[pp["Shop Name"] == loc]
        if not pp_loc.empty:
            no_pos_rows.append({
                "Location": loc,
                "Palmpay Txn Count": len(pp_loc),
                "Palmpay Total Order": pp_loc["Order Amount"].sum(),
                "Note": "No corresponding POS Terminal sheet in ERP export",
            })
    no_pos_summary = pd.DataFrame(no_pos_rows)

    print(f"[transform] {len(locations)} locations processed")
    print(f"[transform] Overall: {overall['Matched Txns']:,} matched "
          f"({overall['Reconciliation Rate %']}%), "
          f"{overall['KM Only Count']:,} KM-only, {overall['PP Only Count']:,} PP-only")

    return detail, branch_summary, overall, no_pos_summary
