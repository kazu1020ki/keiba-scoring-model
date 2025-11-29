# 競馬予想モデル/crawl/crawl_shutuba.py
"""
ネット競馬から出走表＋各馬の直近レース（5走）をクロールして
assets/shutuba_with_past5.csv に出力するスクリプト
"""

import time
import csv
import logging
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# パス設定
# ==============================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = PROJECT_ROOT / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

CSV_FILENAME = ASSETS_DIR / "shutuba_with_past5.csv"

# ==============================
# 設定
# ==============================
# TODO: レースIDを引数から受け取るようにしても良い
RACE_URL = "https://race.netkeiba.com/race/shutuba.html?race_id=202505050812"
PAST_RACE_COUNT = 5

# ==============================
# ログ設定
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ==============================
# Selenium初期化
# ==============================
options = Options()
options.add_argument("--start-maximized")
# options.add_argument("--headless")  # 画面不要ならコメントアウト解除

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)


# ==============================
# 出走表取得
# ==============================
def get_shutuba_list(driver):
    logger.info("出走表ページへアクセス")
    driver.get(RACE_URL)
    time.sleep(3)

    horses = []
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.HorseList")

    for idx, row in enumerate(rows, 1):
        try:
            # 枠番
            waku = ""
            try:
                waku = row.find_element(By.CSS_SELECTOR, 'td[class^="Waku"]').text
            except Exception:
                logger.warning(f"{idx}行目: 枠番取得失敗")

            # 馬番
            num = ""
            try:
                num = row.find_element(By.CSS_SELECTOR, 'td[class^="Umaban"]').text
            except Exception:
                logger.warning(f"{idx}行目: 馬番取得失敗")

            # 馬名 + URL
            name_tag = row.find_element(By.CSS_SELECTOR, "span.HorseName a")
            name = name_tag.text.strip()
            url = name_tag.get_attribute("href")

            # オッズ
            odds = ""
            try:
                odds = row.find_element(By.CSS_SELECTOR, 'span[id^="odds-"]').text
            except Exception:
                logger.warning(f"{idx}行目: オッズ取得失敗")

            horses.append({
                "枠番": waku,
                "馬番": num,
                "馬名": name,
                "オッズ": odds,
                "URL": url
            })

            logger.info(f"取得: 枠{waku} 馬番{num} {name} ({odds})")

        except Exception as e:
            logger.error(f"{idx}行目: 出走表取得エラー: {e}")
            continue

    logger.info(f"✅ 出走馬 {len(horses)} 頭取得完了")
    return horses


# ==============================
# 馬詳細 → 直近レース取得
# ==============================
def get_recent_races(driver, horse_url, num_races=5):
    logger.info(f"詳細ページ遷移: {horse_url}")
    driver.get(horse_url)
    time.sleep(3)

    try:
        table = driver.find_element(By.CSS_SELECTOR, "table.db_h_race_results")
    except Exception:
        logger.error("成績テーブルが見つかりません")
        return []

    rows = table.find_elements(By.TAG_NAME, "tr")[1:num_races + 1]
    race_data = []

    for idx, row in enumerate(rows, 1):
        cols = row.find_elements(By.TAG_NAME, "td")

        if len(cols) < 24:  # 元コードより少し余裕持ってチェック
            logger.warning(f"{idx}行目: 列不足でスキップ")
            continue

        race_info = {
            "開催": cols[1].text,
            "距離": cols[14].text,
            "馬場": cols[16].text,
            "通過": cols[21].text,
            "タイム": cols[18].text,
            "上り": cols[23].text,
            "ペース": cols[22].text
        }

        race_data.append(race_info)

    return race_data


# ==============================
# CSV出力
# ==============================
def export_to_csv(data, filename: Path):
    if not data:
        logger.warning("CSVに出力するデータがありません")
        return

    fieldnames = data[0].keys()

    with filename.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    logger.info(f"✅ CSV出力完了: {filename}")


# ==============================
# メイン処理
# ==============================
def main():
    try:
        all_results = []

        # ① 出走表取得
        horses = get_shutuba_list(driver)

        # ② 馬ごとに詳細取得
        for i, horse in enumerate(horses, 1):
            logger.info(f"====== [{i}/{len(horses)}] {horse['馬名']} 処理開始 ======")

            base_data = {
                "枠番": horse["枠番"],
                "馬番": horse["馬番"],
                "馬名": horse["馬名"],
                "オッズ": horse["オッズ"]
            }

            try:
                races = get_recent_races(driver, horse["URL"], PAST_RACE_COUNT)

                # 5走未満なら空データで補完
                while len(races) < PAST_RACE_COUNT:
                    races.append({
                        "開催": "",
                        "距離": "",
                        "馬場": "",
                        "通過": "",
                        "タイム": "",
                        "上り": "",
                        "ペース": ""
                    })

                # 横持ち展開
                for idx, race in enumerate(races, 1):
                    for key, value in race.items():
                        base_data[f"{idx}走前_{key}"] = value

            except Exception as e:
                logger.error(f"{horse['馬名']} のデータ取得失敗: {e}")

                # 失敗時も空で埋める
                for idx in range(1, PAST_RACE_COUNT + 1):
                    for key in ["開催", "距離", "馬場", "通過", "タイム", "上り", "ペース"]:
                        base_data[f"{idx}走前_{key}"] = ""

            all_results.append(base_data)
            time.sleep(1)  # サーバー負荷対策

        # ③ CSV出力
        export_to_csv(all_results, CSV_FILENAME)

        logger.info("🎉 全処理完了！")

    finally:
        driver.quit()
        logger.info("Selenium 終了")


if __name__ == "__main__":
    main()
