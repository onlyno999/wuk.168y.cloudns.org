def fetch_latest_data(retries=3, delay=2):
    for attempt in range(retries):
        try:
            response = requests.get(URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"[错误] 请求失败: {e}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("tr")
        
        # 确保至少有两行（跳过第一行后还有内容）
        if len(rows) < 2:
            print(f"[警告] 没有抓取到有效行数，第 {attempt + 1} 次尝试...")
            time.sleep(delay)
            continue

        data_rows = rows[1:11]  # 跳过第1行

        results = []
        for row in data_rows:
            issue_tag = row.select_one(".issue")
            numbers_tag = row.select_one(".numbers")

            # 如果网页 class 没有这些名称，可使用 fallback 或打印 row 来调试
            if not issue_tag or not numbers_tag:
                continue

            issue = issue_tag.text.strip()
            numbers_raw = numbers_tag.text.strip()

            numbers = ",".join([
                "0" if n == "10" else n
                for n in numbers_raw.replace("，", ",").replace(" ", "").split(",")
                if n.strip()
            ])

            results.append({
                "issue": issue,
                "numbers": numbers
            })

        if results:
            return results
        else:
            print(f"[警告] 没有提取到期号和号码，第 {attempt + 1} 次尝试...")
            time.sleep(delay)

    print("[失败] 多次尝试后仍未抓取到数据。")
    return []
