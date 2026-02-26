import argparse
from pathlib import Path

import pandas as pd


def calc_wide_ev(input_csv: Path, output_csv: Path, m_wide: float) -> None:
    df = pd.read_csv(input_csv)
    df["wide_odds"] = pd.to_numeric(df.get("wide_odds"), errors="coerce")
    df["p_wide"] = pd.to_numeric(df.get("p_wide"), errors="coerce")

    df["ev_wide"] = df["p_wide"] * df["wide_odds"] - 1
    df["decision"] = ""
    valid = df["ev_wide"].notna()
    df.loc[valid, "decision"] = df.loc[valid, "ev_wide"].ge(m_wide).map({True: "BUY", False: "NO_BUY"})

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", required=True)
    parser.add_argument("--output_csv", required=True)
    parser.add_argument("--m_wide", type=float, default=0.06)
    args = parser.parse_args()

    calc_wide_ev(Path(args.input_csv), Path(args.output_csv), args.m_wide)
    print(f"✅ ワイドEV再計算完了: {args.output_csv}")


if __name__ == "__main__":
    main()
