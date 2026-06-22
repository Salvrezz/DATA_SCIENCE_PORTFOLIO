"""
main.py — Spectrum All-Branches Reconciliation Pipeline (KiliMax ↔ PalmPay)

Usage:
    python main.py
    python main.py --palmpay data/raw/Palmpay_schedule.xlsx \
                   --pos     data/raw/pos_terminals.xlsx \
                   --output  data/processed/Spectrum_AllBranches_Reconciliation.xlsx
"""

import argparse, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from etl.extract   import load_palmpay_schedule, load_pos_terminals
from etl.transform import run_transform
from etl.load      import write_reconciliation_workbook


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--palmpay", default="data/raw/Palmpay_schedule.xlsx")
    p.add_argument("--pos",     default="data/raw/pos_terminals.xlsx")
    p.add_argument("--output",  default="data/processed/Spectrum_AllBranches_Reconciliation.xlsx")
    return p.parse_args()


def main():
    args  = parse_args()
    start = time.time()

    print("=" * 65)
    print("  SPECTRUM ALL-BRANCHES RECONCILIATION  (KiliMax ↔ PalmPay)")
    print("=" * 65)

    print("\n[STEP 1/3] EXTRACT")
    palmpay = load_palmpay_schedule(args.palmpay)
    pos     = load_pos_terminals(args.pos)

    print("\n[STEP 2/3] TRANSFORM — transaction-level greedy match per branch")
    detail, branch_summary, overall, no_pos = run_transform(palmpay, pos)

    print("\n[STEP 3/3] LOAD")
    out = write_reconciliation_workbook(detail, branch_summary, overall, no_pos, args.output)

    elapsed = time.time() - start
    print("\n" + "=" * 65)
    print(f"  COMPLETE  ({elapsed:.1f}s)")
    print(f"  Output → {out}")
    print("=" * 65)

    print(f"\n  Branches processed            : {len(branch_summary):>8,}")
    print(f"  KiliMax total debit (NGN)     : {overall['KiliMax Total Debit']:>16,.2f}")
    print(f"  Palmpay total order (NGN)     : {overall['Palmpay Total Order']:>16,.2f}")
    print(f"  Net gap KM-PP (NGN)           : {overall['Net Gap (KM-PP)']:>16,.2f}")
    print(f"  ✅ Matched transactions        : {overall['Matched Txns']:>8,}  ({overall['Reconciliation Rate %']}%)")
    print(f"  🟡 KM only (unmatched)         : {overall['KM Only Count']:>8,}  (₦{overall['KM Only Amt']:,.0f})")
    print(f"  🔴 PP only (unmatched)         : {overall['PP Only Count']:>8,}  (₦{overall['PP Only Amt']:,.0f})\n")


if __name__ == "__main__":
    main()