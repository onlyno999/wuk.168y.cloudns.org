import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, timedelta
import sys

URL = "https://wuk.168y.cloudns.org/"
OUTPUT_FILE = "nibaba.json"

def fetch_latest_data():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"\n[错误] 请求失败: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    data_rows = soup.select("tr")[1:11]  # 跳过第一行，取最新10条

    results = []

    for row in data_rows:
        issue_tag = row.select_one(".issue")
        numbers_tag = row.select_one(".numbers")

        if not issue_tag or not numbers_tag:
            continue

        issue = issue_tag.text.strip()
        numbers_raw = numbers_tag.text.strip()

        # 格式统一为 1,2,3,...,0（将10变为0）
        numbers = ",".join([
            "0" if n == "10" else n
            for n in numbers_raw.replace("，", ",").replace(" ", "").split(",")
            if n.strip()
        ])

        results.append({
            "issue": issue,
            "numbers": numbers
        })

    return results

def save_data_to_file(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data[:10], f, ensure_ascii=False, indent=2)

def print_data(data):
    print("\n[抓取结果] 最新十期数据：")
    for entry in data[:10]:
        print(f"{entry['issue']}:{entry['numbers']}")

def wait_until_next_5_min():
    now = datetime.now()
    minute = (now.minute // 5 + 1) * 5
    if minute >= 60:
        next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        next_time = now.replace(minute=minute, second=0, microsecond=0)

    while True:
        remaining = (next_time - datetime.now()).total_seconds()
        if remaining <= 0:
            break
        sys.stdout.write(f"\r[等待] 距离下一次抓取还有 {int(remaining)} 秒，将在 {next_time.strftime('%H:%M:%S')} 执行。")
        sys.stdout.flush()
        time.sleep(1)
    print()

def main():
    print("[启动] 正在进行首次抓取...")
    data = fetch_latest_data()
    if data:
        save_data_to_file(data)
        print_data(data)

    while True:
        wait_until_next_5_min()
        print(f"\n[时间] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 自动抓取开始...")
        data = fetch_latest_data()
        if data:
            save_data_to_file(data)
            print_data(data)

if __name__ == "__main__":
    main()
