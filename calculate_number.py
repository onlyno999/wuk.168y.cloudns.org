import requests
from bs4 import BeautifulSoup

url = "https://wuk.168y.cloudns.org/"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.RequestException as e:
    print(f"请求网页失败: {e}")
    exit()

soup = BeautifulSoup(response.text, "html.parser")

data_rows = soup.select("tr")[:10]

results = []

for row in data_rows:
    tds = row.find_all("td")
    if len(tds) >= 2:
        issue = tds[0].text.strip()
        numbers = tds[1].text.strip()
    else:
        issue = "未知期号"
        numbers = "未知号码"
    results.append(f"{issue}:{numbers}")

for result in results:
    print(result)

with open("lottery_data.txt", "w", encoding="utf-8") as f:
    for result in results:
        f.write(result + "\n")
