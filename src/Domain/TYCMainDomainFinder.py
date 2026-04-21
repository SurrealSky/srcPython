import asyncio
import argparse
import csv
import math
import time
from typing import Dict, List, Optional
import requests
import ujson
from datetime import datetime
from icp.mlog import logger
import openpyxl
from openpyxl.utils import column_index_from_string
from bs4 import BeautifulSoup

class TYCDomainCrawler:

    def __init__(
        self,
        craw: bool = True,
        base_url: str = "https://beian.tianyancha.com",
        query: str = "",
        page_size: int = 20,
        total: int = 0,
        proxies: str = None,
        cookie: str = "",
        timeout: int = 10,
        delay: float = 5.0
    ):
        """
        初始化爬虫
        """
        self.base_url = base_url.rstrip('/')
        self.proxies = proxies
        self.query = query
        self.cookie = cookie
        self.api_path = "/search/"
        self.craw = craw
        self.timeout = timeout
        self.delay = delay
        
        # 请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0",
            "Accept": "text/html,application/xhtml+xml,application/xml, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,zh-TW;q=0.8,zh-HK;q=0.7,en-US;q=0.6,en;q=0.5",
            "Content-Type": "application/json",
            "Cookie": "" + self.cookie,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin"
        }
        
        # 存储抓取结果
        self.data: List[Dict] = []
        self.total: Optional[int] = None

    def get_domain_list_from_response(self,response):        
        # 1. 解析 HTML
        soup = BeautifulSoup(response.text, "lxml")
        # 2. 定位表格
        table = soup.find("table", class_="table")  # 或者使用 "table -ranking"，但 class 可能包含多个
        if not table:
            table = soup.find("table", class_="ranking")  # 备选
        # 实际页面中 class="table -ranking"，用 CSS 选择器更稳妥
        table = soup.select_one("table.table.-ranking")
        # 3. 提取数据行
        domain_list = []
        tbody = table.find("tbody")
        for tr in tbody.find_all("tr"):
            # 每个 tr 中有多个 td
            tds = tr.find_all("td")
            if len(tds) < 6:   # 至少6列：序号、备案号、主办单位、网站名称、域名、审核时间
                continue
            row = [
                tds[1].get_text(strip=True),
                tds[4].get_text(strip=True),
            ]
            domain_list.append(row)
        return domain_list

    def get_pages_from_response(self, response):
        soup = BeautifulSoup(response.text, "lxml")
        pagination_ul = soup.find("ul", class_="pagination")
        self.total = int(pagination_ul.get("page-total"))  # 183
        self.page_size = 20  # 每页条数，可通过观察或从页面统计得到
        total_pages = math.ceil(self.total / self.page_size)  # 10
        print(f"总页数: {total_pages}")  # 10
        return total_pages

    def _fetch_page(self, page: str) -> Optional[Dict]:
        """
        请求单页数据
        """
        url=''
        if len(page) > 0:
            url = f"{self.base_url}{self.api_path}{self.query}/{page}"
        else:
            url = f"{self.base_url}{self.api_path}{self.query}"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                proxies={"http": self.proxies, "https": self.proxies} if self.proxies else None,
                verify=False  # 如果需要忽略 SSL 验证，可以设置为 False
            )
            response.raise_for_status()
            return response
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
            if page == 1:
                response = self._fetch_page("")  # 第1页不带页码参数")
            else:
                response = self._fetch_page(f"p{page}")
            if not response:
                break
            domain_list = self.get_domain_list_from_response(response)
            if len(self.data) == 0 and self.total is None:
                pages = self.get_pages_from_response(response)
                print(f"总记录数: {self.total} 条，")
            print(f"第 {page} 页获取到 {len(domain_list)} 条数据，总页数: {pages}")
            self.data.extend(domain_list)
            if page >= pages :  # 已经获取到最后一页
                break
            page += 1
            time.sleep(self.delay)

    def get_domains_set(self) -> set:
        """从抓取的数据中提取所有 domain，返回一个集合"""
        return {item.get('domain') for item in self.data if item.get('domain')}

    def save_csv(self,output_file,domains):
        """
        将抓取的数据保存为 CSV 文件（UTF-8 with BOM）
        
        :param filename: 输出文件名
        """
        if len(domains)==0:
            print("[!] 无域名可保存")

        if output_file is None:
            now = datetime.datetime.now()
            date_str = f"{now.year}{now.month:02d}{now.day:02d}"
            output_file = f"icp_domains_{date_str}.csv"
        # 保存到文本文件
        with open(output_file, 'w',newline="", encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(domains)   # 一次性写入多行
        print(f"[+] 域名已保存到: {output_file}")

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

    def run(self,outfile):
        """
        执行完整的抓取流程：获取数据并保存
        
        :param save_json: 是否保存 JSON 文件
        :param save_csv: 是否保存 CSV 文件
        """
        firefly_crawler_data = set()
        if self.craw is True:
            self.fetch_all()
            self.save_csv(outfile,self.data)
            #firefly_crawler_data = self.get_domains_set()
        else:
            print("跳过数据抓取,从本地文件读取")
            #从文件中读取数据
            with open('domains.csv', mode='r', encoding='utf-8') as crawfile:
                reader = csv.reader(crawfile)
                next(reader)  # 跳过表头
                for row in reader:
                    firefly_crawler_data.add(row[0])  # 假设 domain 在第一列

#py -3 .\src\Domain\TYCMainDomainFinder.py -n 科大讯飞股份有限公司 --cokie ""
#py -3 .\src\Domain\TYCMainDomainFinder.py -n 皖ICP备05001217号 --cokie ""
if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(description='这是一个示例程序')
    # 添加位置参数（必须按顺序提供）
    parser.add_argument('--unit_name','-n',required=True,help='单位名称')
    parser.add_argument('--cookie', '-c', required=True, help='访问cookie，格式为 "key=value; key2=value2"')
    parser.add_argument('--output', '-o',default=f'tyc_{datetime.now().strftime("%Y%m%d_%H%M%S")}_results.csv',help='输出文件')
    parser.add_argument('--verbose', '-v',action='store_true',help='详细输出')
   
    # 解析参数
    args = parser.parse_args()
    
    #proxies ="192.168.1.7:8080"
    proxies = None  # 如果不使用代理则设置为None
    crawler = TYCDomainCrawler(craw=True,proxies=proxies,cookie=args.cookie,query=args.unit_name)
    crawler.run(args.output)