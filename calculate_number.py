import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime

URL = "https://wuk.168y.cloudns.org/"
LOG_FILE = "nibaba.json"
FETCH_INTERVAL = 300  # 5 分钟 = 300 秒

def fetch_latest_data():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[错误] 请求网页失败: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr")
    print(f"[调试] 抓到了 {len(rows)} 个 <tr> 标签")

    results = []
    for i, row in enumerate(rows):
        tds = row.find_all("td")
        if len(tds) != 2:
            continue

        issue = tds[0].text.strip()
        numbers_raw = tds[1].text.strip()

        # 替换中文逗号为英文逗号
        numbers_raw = numbers_raw.replace("，", ",")
        number_list = [n.strip() for n in numbers_raw.split(",") if n.strip().isdigit()]

        if len(issue) == 8 and issue.isdigit() and len(number_list) == 10:
            numbers = ",".join(number_list)
            results.append({"issue": issue, "numbers": numbers})

        # 只抓取前10条
        if len(results) >= 10:
            break

    return results

def save_to_log(data):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def print_results(results):
    print("=" * 30)
    for item in results:
        print(f"{item['issue']}:{item['numbers']}")
    print("=" * 30)

def wait_until_next_interval():
    now = datetime.now()
    seconds_to_next = 300 - ((now.minute % 5) * 60 + now.second)
    while seconds_to_next > 0:
        mins, secs = divmod(seconds_to_next, 60)
        print(f"\r等待下次抓取：{mins:02d}:{secs:02d}", end="", flush=True)
        time.sleep(1)
        seconds_to_next -= 1
    print()

def main():
    print("[初始化] 开始首次抓取")
    results = fetch_latest_data()
    if not results:
        print("[失败] 首次抓取未成功")
    else:
        save_to_log(results)
        print_results(results)

    while True:
        wait_until_next_interval()
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始抓取...")
        latest = fetch_latest_data()
        if latest:
            save_to_log(latest)
            print_results(latest)
        else:
            print("[警告] 本次抓取失败，保留上次记录")

try:
    main()
except Exception as e:
    print(f"[致命错误] 程序异常终止: {e}")
    input("按任意键退出...")
