from bs4 import BeautifulSoup
import requests


def extract_list_data(soup, class_name=None):
    """
    提取所有指定或所有div元素中的文本内容。

    参数:
    - soup: BeautifulSoup 对象
    - class_name: 可选，指定特定类名的div元素

    返回:
    - data: 包含所有提取文本的列表
    """
    # 查找指定类名的div，或者所有div
    divs = soup.find_all('div', class_=class_name) if class_name else soup.find_all('div')

    if not divs:
        print("No div elements found on the page.")
        return []

    data = []
    for index, div in enumerate(divs):
        print(f"Processing div element {index + 1}")
        div_data = {}

        # 遍历直接子元素，提取文本
        for child in div.find_all(recursive=False):
            text = child.get_text(strip=True)
            if text:
                # 使用子元素的标签名作为键，文本作为值
                div_data.setdefault(child.name, []).append(text)

        # 如果有数据，添加到结果列表
        if div_data:
            data.append(div_data)

    return data


if __name__ == "__main__":
    url = input("Please enter the URL of the page you want to scrape: ")
    class_name = input("Please enter the class name of the div (if you know it, leave it blank otherwise): ")
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 提取所有文本
    data = extract_list_data(soup, class_name if class_name else None)
    print("Data scraped:", data)
