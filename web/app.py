from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

from preprocess.race_filename import parse_race_meta_from_filename

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent / "templates"),
    static_folder=str(Path(__file__).resolve().parent / "static"),
)


def _find_course_score_csv(race_id: str) -> Path:
    candidates = list(ASSETS_DIR.glob(f"race_{race_id}_*_course_scores.csv"))
    if not candidates:
        raise FileNotFoundError("course_scores.csv が見つかりません")
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _run_pipeline(race_id: str) -> tuple[int, str]:
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "run_pipeline_with_report.py"),
        "--race_id",
        race_id,
    ]
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    log = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode, log.strip()


def _build_result(csv_path: Path) -> dict:
    meta = parse_race_meta_from_filename(csv_path.name)
    df = pd.read_csv(csv_path)

    score_cols = [c for c in df.columns if c.endswith("適性スコア")]
    if not score_cols:
        raise ValueError("適性スコア列が見つかりません")

    score_col = score_cols[0]
    result_df = df[["馬名", score_col]].dropna().copy()
    result_df["モデル順位"] = result_df[score_col].rank(
        ascending=False, method="dense"
    ).astype(int)
    result_df = result_df.sort_values(["モデル順位", score_col], ascending=[True, False])

    ranking = [
        {
            "rank": int(row["モデル順位"]),
            "horse": row["馬名"],
            "score": round(float(row[score_col]), 3),
        }
        for _, row in result_df.iterrows()
    ]

    return {
        "race": {
            "race_id": meta["race_id"],
            "course": meta["course"],
            "surface": meta["surface"],
            "distance": meta["distance"],
        },
        "score_column": score_col,
        "ranking": ranking,
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/predict")
def predict():
    payload = request.get_json(silent=True) or {}
    race_id = str(payload.get("race_id", "")).strip()

    if not race_id.isdigit():
        return jsonify({"error": "race_id は数字のみで入力してください"}), 400

    code, log = _run_pipeline(race_id)
    if code != 0:
        return (
            jsonify(
                {
                    "error": "パイプライン実行に失敗しました",
                    "log": log,
                }
            ),
            500,
        )

    try:
        csv_path = _find_course_score_csv(race_id)
        result = _build_result(csv_path)
    except Exception as exc:
        return jsonify({"error": str(exc), "log": log}), 500

    result["log"] = log
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
