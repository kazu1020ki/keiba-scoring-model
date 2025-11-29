import argparse
import time
from pathlib import Path
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options


# keiba-scoring-model/ を指す
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# assets/ を共通で参照
ASSETS = PROJECT_ROOT / "assets"


def get_race_result_selenium(race_id):
    """netkeiba の結果ページを Selenium でスクレイピング"""

    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

    print(f"🧲 公式結果ページを取得中：{url}")

    options = Options()
    options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.get(url)
    time.sleep(2)

    rows = driver.find_elements(By.CSS_SELECTOR, "table.RaceTable01 tr")

    results = []
    for row in rows[1:]:  # ヘッダーを除く
        cols = row.find_elements(By.TAG_NAME, "td")
        if len(cols) < 7:
            continue

        try:
            rank = cols[0].text.strip()     # 着順
            name = cols[3].text.strip()     # 馬名
            pop = cols[9].text.strip()      # 人気
            odds = cols[10].text.strip()    # オッズ
        except:
            continue

        if rank == "" or name == "":
            continue

        results.append({
            "馬名": name,
            "着順": int(rank),
            "人気": int(pop),
            "オッズ": float(odds)
        })

    driver.quit()
    print(f"✅ レース結果 {len(results)}頭 分を取得")

    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--race_id", required=True)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--course", required=True)
    args = parser.parse_args()

    # モデルの最終出力ファイル
    model_file = ASSETS / f"race_{args.race_id}_{args.distance}m_{args.course}_course.csv"
    if not model_file.exists():
        raise FileNotFoundError(f"モデル結果がありません: {model_file}")

    model_df = pd.read_csv(model_file)

    # コース適性スコアの列名
    col_score = f"{args.course}適性スコア"

    # モデル順位付け
    model_df["モデル順位"] = model_df[col_score].rank(ascending=False, method="dense").astype(int)

    # 実着順を取得
    result_df = get_race_result_selenium(args.race_id)

    # マージ
    merged = pd.merge(model_df, result_df, on="馬名", how="left")

    merged = merged.sort_values("モデル順位")

    print("\n===============================")
    print("🔍 モデル順位 vs 実着順 比較")
    print("===============================\n")

    for _, row in merged.iterrows():
        print(
            f"{row['モデル順位']:>2}位 | "
            f"{row['馬名']:<12} | "
            f"スコア: {row[col_score]:>6} | "
            f"実着順: {str(row['着順']):>2} | "
            f"人気: {str(row['人気']):>2} | "
            f"オッズ: {row['オッズ']}"
        )

    print("\n===============================")
    print("📊 簡易レポート")
    print("===============================\n")

    # 馬券内（3着以内）
    top3 = merged[merged["着順"] <= 3]["馬名"].tolist()

    print(f"🎯 モデル1位: {merged.iloc[0]['馬名']} （実着順: {merged.iloc[0]['着順']}）")
    print(f"🥇 馬券内の馬: {top3}")

    # モデル＞人気 の馬
    merged["人気順位"] = merged["人気"]
    merged["人気との乖離"] = merged["人気順位"] - merged["モデル順位"]

    print("\n💡 人気より評価が高い馬（狙い目）:")
    print(merged[merged["人気との乖離"] > 5][["馬名", "モデル順位", "人気", "人気との乖離"]].to_string(index=False))

    print("\n🏁 完了\n")


if __name__ == "__main__":
    main()
