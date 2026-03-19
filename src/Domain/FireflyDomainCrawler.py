import requests
import time
import json
from typing import List, Dict, Optional
import openpyxl
from openpyxl.utils import column_index_from_string
import argparse

class FireflyDomainCrawler:

    def __init__(
        self,
        token: str,
        base_url: str = "https://firefly-src.geekyoung.com",
        page_size: int = 20,
        timeout: int = 10,
        delay: float = 0.5
    ):
        """
        初始化爬虫
        
        :param token: 有效的 Bearer Token
        :param base_url: API 基础地址
        :param page_size: 每页数据条数
        :param timeout: 请求超时时间（秒）
        :param delay: 分页请求间隔（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.api_path = "/api/domain/list"
        self.token = token
        self.page_size = page_size
        self.timeout = timeout
        self.delay = delay
        
        # 请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0",
            "Te": "trailers"
        }
        
        # 存储抓取结果
        self.data: List[Dict] = []
        self.total: Optional[int] = None

    def _fetch_page(self, page: int) -> Optional[Dict]:
        """
        请求单页数据
        
        :param page: 页码，从1开始
        :return: 解析后的 JSON 字典，失败返回 None
        """
        url = f"{self.base_url}{self.api_path}"
        payload = {"page": page, "size": self.page_size}
        
        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"第 {page} 页请求失败: {e}")
            return None

    def fetch_all(self) -> List[Dict]:
        """
        循环获取所有页的数据，并返回合并后的列表
        
        :return: 所有域名数据的列表
        """
        page = 1
        self.data = []
        self.total = None

        while True:
            print(f"正在获取第 {page} 页...")
            result = self._fetch_page(page)
            if not result:
                break

            # 检查返回码
            code = result.get("code")
            if code != 200:
                print(f"第 {page} 页返回异常: {result.get('message', '未知错误')}")
                break

            data = result.get("data", [])
            if not data:
                print("没有更多数据，停止抓取。")
                break

            self.data.extend(data)

            # 记录总数（仅在第一次获取）
            if self.total is None:
                self.total = result.get("total", 0)
                print(f"总记录数: {self.total}")
                return self.data

            # 判断是否还有下一页
            if len(data) < self.page_size or len(self.data) >= self.total:
                break

            page += 1
            time.sleep(self.delay)

        print(f"抓取完成，共获取 {len(self.data)} 条数据。")
        return self.data

    def get_domains_set(self) -> set:
        """从抓取的数据中提取所有 domain，返回一个集合"""
        return {item.get('domain') for item in self.data if item.get('domain')}

    def save_json(self, filename: str = "domains.json"):
        """
        将抓取的数据保存为 JSON 文件
        
        :param filename: 输出文件名
        """
        if not self.data:
            print("没有数据可保存，请先调用 fetch_all() 获取数据。")
            return
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        print(f"数据已保存到 {filename}")

    def save_csv(self, filename: str = "domains.csv"):
        """
        将抓取的数据保存为 CSV 文件（UTF-8 with BOM）
        
        :param filename: 输出文件名
        """
        if not self.data:
            print("没有数据可保存，请先调用 fetch_all() 获取数据。")
            return
        
        import csv
        if not self.data:
            return
        keys = self.data[0].keys()
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(self.data)
        print(f"数据已保存到 {filename}")

    def find_missing_data(self,csv_set, xlsx_file, xlsx_sheet, xlsx_column, header=True):
        """
        将传入的 set 与 Excel 指定列的数据进行比对，返回在 set 中存在但在 Excel 中不存在的值。

        参数：
            csv_set (set): 包含待查找数据的集合（例如从 CSV 中提取的唯一值）
            xlsx_file (str): Excel (.xlsx) 文件路径
            xlsx_sheet (str): 要读取的 sheet 名称
            xlsx_column (str 或 int): 指定列。
                - 如果为字符串，则视为列字母，例如 'A', 'B', 'AA'。
                - 如果为整数，则视为从 1 开始的列索引（1 表示第一列）。
            header (bool, optional): 是否将第一行视为表头而跳过。默认 True（跳过表头）。

        返回：
            list: 缺失值的列表（已去重）
        """
        # 加载工作簿（仅读取数据，不加载公式计算结果以外的内容）
        wb = openpyxl.load_workbook(xlsx_file, data_only=True)
        ws = wb[xlsx_sheet]

        # 确定列索引（openpyxl 中列索引从 1 开始）
        if isinstance(xlsx_column, str):
            # 将列字母转换为数字索引，如 'A' -> 1
            col_idx = column_index_from_string(xlsx_column)
        elif isinstance(xlsx_column, int):
            # 直接使用传入的整数作为列索引（必须 >=1）
            if xlsx_column < 1:
                raise ValueError("整数列索引必须从 1 开始")
            col_idx = xlsx_column
        else:
            raise TypeError("xlsx_column 必须是列字母（字符串）或从 1 开始的列索引（整数）")

        # 确定数据起始行
        start_row = 2 if header else 1

        # 收集指定列的所有非空单元格值
        xlsx_values = set()
        for row in ws.iter_rows(min_row=start_row, max_col=col_idx, values_only=True):
            cell_value = row[0]  # 因为只取一列，row 是长度为 1 的元组
            if cell_value is not None:  # 忽略空单元格
                # 注意：如果希望统一类型比较，可以在此处转换为字符串，例如 str(cell_value)
                xlsx_values.add(cell_value)

        print(f"从 xlsx 中读取的主域名数量: {len(xlsx_values)}")
        # 计算差集
        missing = csv_set - xlsx_values

        # 返回列表形式
        return list(missing)

    def run(self, save_json: bool = True, save_csv: bool = False):
        """
        执行完整的抓取流程：获取数据并保存
        
        :param save_json: 是否保存 JSON 文件
        :param save_csv: 是否保存 CSV 文件
        """
        self.fetch_all()
        firefly_crawler_data = crawler.get_domains_set()
        #firefly_crawler_data = {"xfyun.com","xunfei.cn","xunfei.com","iflytek.com","iflytek.cn"}
        print("从 Firefly 爬取的域名数量:", firefly_crawler_data)

        print("从 Firefly 爬取的域名数量:", len(firefly_crawler_data))
        missing_items = self.find_missing_data(firefly_crawler_data,
            'D:\\work\\漏洞\\SRC列表.xlsx',
            '科大讯飞资产',
            'A',        # 列字母
            True             # 第一行是表头，从第二行开始读
        )
        print("缺失的数据:", missing_items)

        if save_json:
            self.save_json()
        if save_csv:
            self.save_csv()


# 使用示例
if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(description='这是一个示例程序')
    # 添加位置参数（必须按顺序提供）
    parser.add_argument('-t','--token', required=True, help='请输入Firefly的Bearer Token')
    # 解析参数
    args = parser.parse_args()
    crawler = FireflyDomainCrawler(args.token)
    crawler.run(save_json=False, save_csv=False)