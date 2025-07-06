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

# 选取表格的前10行
data_rows = soup.select("tr")[:10]

results = []

# 调试打印前几行结构，方便确认网页结构（可以注释掉）
for i, row in enumerate(data_rows):
    print(f"第{i+1}行内容:\n{row.prettify()}\n{'-'*40}")

for row in data_rows:
    tds = row.find_all("td")
    if len(tds) >= 3:
        issue = tds[0].text.strip()        # 第1个td，期号
        date = tds[1].text.strip()         # 第2个td，时间
        numbers = ",".join(td.text.strip() for td in tds[2:])  # 第3个td开始，所有号码合并
    else:
        issue = "未知期号"
        date = ""
        numbers = "未知号码"

    result = f"{issue} {date} {numbers}"
    results.append(result)

for res in results:
    print(res)

with open("lottery_data.txt", "w", encoding="utf-8") as f:
    for res in results:
        f.write(res + "\n")
