"""
extract.py — Load and clean both source workbooks.

DATA RULES (confirmed against raw files):
-------------------------------------------
1. Palmpay Schedule (sheet1):
   - Use: Order Amount, Update Time (date), Shop Name, Order Type,
          Transaction Order No, Transaction Status
   - Filter: Transaction Status == 'Successful'   (we only reconcile successful txns)
   - Deduplicate exact duplicate rows (Txn ID + Amount + Date + Type)

2. POS Terminals (Kilimax ERP), one sheet per location:
   - Use: Document Number, Business Partner, Document Type, Document Date, Debit(NGN)
   - Filter: Document Type == 'Receive Payment' AND Debit(NGN) > 0
     (the Debit side is the actual cash inflow; Credit(NGN) rows on Receive
      Payment are contra/clearing entries and are excluded)

3. Two Palmpay shops have NO matching POS sheet — excluded from recon,
   reported separately: SPECTRUM IKOTUN, SPECTRUM ONLINE.
"""

import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

POS_SHEET_TO_LOCATION = {
    "agege":        "SPECTRUM AGEGE",
    "agric":        "SPECTRUM AGRIC",
    "ajah":         "SPECTRUM AJAH",
    "alaba":        "SPECTRUM ALABA",
    "ayobo":        "SPECTRUM AYOBO",
    "bariga":       "SPECTRUM BARIGA",
    "biz ikeja":    "SPECTRUM RETAIL IKEJA",
    "epe":          "SPECTRUM EPE",
    "ibadan":       "SPECTRUM IBADAN",
    "ikorodu":      "SPECTRUM IKORODU",
    "ikeja":        "SPECTRUM RETAIL IKEJA",
    "iyana ipaja":  "SPECTRUM IYANA IPAJA",
    "lagos island": "SPECTRUM LAGOS ISLAND",
    "magboro":      "SPECTRUM MAGBORO",
    "mushin":       "SPECTRUM MUSHIN",
    "oba akran":    "SPECTRUM OBA-AKRAN",
    "ojodu":        "SPECTRUM OJODU",
    "oju ore":      "SPECTRUM OJU ORE",
    "performance":  "SPECTRUM PERFORMANCE",
    "police post":  "SPECTRUM POLICE POST",
    "sabo":         "SPECTRUM SABO",
    "saka tinubu":  "SPECTRUM SAKA TINUBU",
    "sangotedo":    "SPECTRUM SANGOTEDO",
}

NO_POS_SHEET = {"SPECTRUM IKOTUN", "SPECTRUM ONLINE"}


def load_palmpay_schedule(filepath=None):
    filepath = filepath or RAW_DIR / "Palmpay_schedule.xlsx"
    raw = pd.read_excel(filepath, sheet_name="sheet1", dtype=str)

    keep = ["Order Type", "Transaction Order No", "Transaction Status",
            "Order Amount", "Update Time", "Shop Name"]
    raw = raw[keep].copy()
    raw["Order Amount"] = pd.to_numeric(raw["Order Amount"], errors="coerce")
    raw["Update Time"]  = pd.to_datetime(raw["Update Time"], errors="coerce").dt.date

    raw = raw[raw["Transaction Status"].str.strip().str.lower() == "successful"].copy()

    # Remove exact duplicate rows (same Txn ID + Amount + Date + Type)
    before = len(raw)
    raw = raw.drop_duplicates(
        subset=["Transaction Order No", "Order Amount", "Update Time", "Order Type"]
    )
    deduped = before - len(raw)

    raw.reset_index(drop=True, inplace=True)
    print(f"[extract] Palmpay loaded: {len(raw):,} successful rows "
          f"({deduped} exact duplicates removed)")
    return raw


def load_pos_terminals(filepath=None):
    filepath = filepath or RAW_DIR / "pos_terminals.xlsx"
    all_sheets = pd.read_excel(filepath, sheet_name=None, dtype=str)

    frames = []
    for sheet_name, df in all_sheets.items():
        canonical = POS_SHEET_TO_LOCATION.get(sheet_name.strip().lower())
        if canonical is None:
            continue

        df["Debit(NGN)"]    = pd.to_numeric(df.get("Debit(NGN)", 0), errors="coerce").fillna(0)
        df["Document Date"] = pd.to_datetime(
            df["Document Date"], format="%d/%m/%Y", errors="coerce"
        ).dt.date

        rp = df[
            (df["Document Type"].str.strip().str.lower() == "receive payment") &
            (df["Debit(NGN)"] > 0)
        ].copy()
        rp.dropna(subset=["Document Date"], inplace=True)

        rp["Location"]     = canonical
        rp["Source Sheet"] = sheet_name

        keep_cols = ["Document Number", "Business Partner", "Document Type",
                     "Document Date", "Debit(NGN)", "Location", "Source Sheet"]
        frames.append(rp[[c for c in keep_cols if c in rp.columns]])

    pos = pd.concat(frames, ignore_index=True)
    pos.reset_index(drop=True, inplace=True)

    print(f"[extract] POS loaded: {len(pos):,} Receive Payment (debit) rows "
          f"across {pos['Location'].nunique()} locations")
    return pos


if __name__ == "__main__":
    pp  = load_palmpay_schedule()
    pos = load_pos_terminals()
    print(pp.head())
    print(pos.head())
