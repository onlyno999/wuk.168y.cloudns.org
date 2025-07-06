import requests
from bs4 import BeautifulSoup

# 目标网页 URL
url = "https://wuk.168y.cloudns.org/"

# 发送 HTTP 请求
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # 检查请求是否成功
except requests.RequestException as e:
    print(f"请求网页失败: {e}")
    exit()

# 解析网页内容
soup = BeautifulSoup(response.text, "html.parser")

# 假设数据在表格中，每行包含期号和号码
# 你需要根据实际网页结构调整以下选择器
# 例如，假设期号和号码在 <tr> 标签中，期号在 class="issue"，号码在 class="numbers"
data_rows = soup.select("tr")[:10]  # 获取前10行（最新十期）

# 存储结果
results = []

for row in data_rows:
    # 提取期号（假设在 class="issue" 的元素中）
    issue = row.select_one(".issue").text.strip() if row.select_one(".issue") else "未知期号"
    # 提取号码（假设号码在 class="numbers" 的元素中，以逗号分隔）
    numbers = row.select_one(".numbers").text.strip() if row.select_one(".numbers") else "未知号码"
    # 格式化结果
    result = f"{issue}:{numbers}"
    results.append(result)

# 输出最新十期数据
for result in results:
    print(result)

# 可选：保存到文件
with open("lottery_data.txt", "w", encoding="utf-8") as f:
    for result in results:
        f.write(result + "\n")
