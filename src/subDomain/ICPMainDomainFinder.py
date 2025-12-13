import requests
import json
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any
from urllib3.exceptions import InsecureRequestWarning

# 禁用SSL警告
warnings.filterwarnings("ignore", category=InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class ICPQueryClient:
    """ICP备案查询客户端类"""
    
    def __init__(self, 
                 uuid: str, 
                 sign: str, 
                 token: str,
                 proxies: Optional[Dict] = None,
                 verify_ssl: bool = False):
        """
        初始化ICP查询客户端
        
        Args:
            uuid: 请求UUID
            sign: 签名
            token: 令牌
            proxies: 代理配置
            verify_ssl: 是否验证SSL证书
        """
        self.uuid = uuid
        self.sign = sign
        self.token = token
        self.verify_ssl = verify_ssl
        self.proxies = proxies or {}
        
        # 基础URL
        self.base_url = "https://hlwicpfwc.miit.gov.cn/icpproject_query/api"
        
        # 通用请求头
        self.headers = {
            "Cookie": "__jsluid_s=49d48f039b095230d693ffc46fd6fafe",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2",
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
            "Origin": "https://beian.miit.gov.cn",
            "Referer": "https://beian.miit.gov.cn/"
        }
        
        # 动态请求头（每次请求时会更新）
        self._update_dynamic_headers()
    
    def _update_dynamic_headers(self):
        """更新动态请求头"""
        self.headers.update({
            "Uuid": self.uuid,
            "Sign": self.sign,
            "Token": self.token
        })
    
    def _make_request(self, 
                     endpoint: str, 
                     data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送HTTP POST请求
        
        Args:
            endpoint: API端点路径
            data: 请求数据
            
        Returns:
            JSON响应数据
        """
        url = f"{self.base_url}/{endpoint}"
        
        # 压缩JSON字符串（移除空格）
        json_data = json.dumps(data, separators=(',', ':'))
        
        response = requests.post(
            url=url,
            data=json_data,
            headers=self.headers,
            proxies=self.proxies,
            verify=self.verify_ssl
        )
        
        # 检查响应状态
        response.raise_for_status()
        
        return response.json()
    
    def query_by_condition(self, 
                          page: int, 
                          page_size: int = 10,
                          unit_name: str = "科大讯飞股份有限公司",
                          service_type: int = 1) -> Dict[str, Any]:
        """
        按条件查询备案信息
        
        Args:
            page: 页码
            page_size: 每页数量
            unit_name: 单位名称
            service_type: 服务类型
            
        Returns:
            查询结果
        """
        endpoint = "icpAbbreviateInfo/queryByCondition"
        data = {
            "pageNum": page,
            "pageSize": page_size,
            "unitName": unit_name,
            "serviceType": service_type
        }
        
        return self._make_request(endpoint, data)
    
    def query_detail(self, 
                    main_id: str, 
                    domain_id: str, 
                    service_id: str) -> Dict[str, Any]:
        """
        查询备案详细信息
        
        Args:
            main_id: 主ID
            domain_id: 域名ID
            service_id: 服务ID
            
        Returns:
            详细信息
        """
        endpoint = "icpAbbreviateInfo/queryDetailByServiceIdAndDomainId"
        data = {
            "mainId": main_id,
            "domainId": domain_id,
            "serviceId": service_id
        }
        
        return self._make_request(endpoint, data)
    
    def query_all_pages(self, 
                       unit_name: str = "科大讯飞股份有限公司",
                       service_type: int = 1,
                       page_size: int = 10,
                       max_workers: int = 5) -> List[Dict[str, Any]]:
        """
        查询所有页面的备案信息
        
        Args:
            unit_name: 单位名称
            service_type: 服务类型
            page_size: 每页数量
            max_workers: 最大线程数（用于并发查询）
            
        Returns:
            所有备案信息列表
        """
        all_records = []
        
        # 首先查询第一页获取总页数
        first_page_data = self.query_by_condition(
            page=1,
            page_size=page_size,
            unit_name=unit_name,
            service_type=service_type
        )
        
        if first_page_data.get('code') != 200:
            print(f"查询失败: {first_page_data.get('msg', '未知错误')}")
            return all_records
        
        params = first_page_data.get('params', {})
        first_page = params.get('firstPage', 1)
        last_page = params.get('lastPage', 1)
        
        print(f"总页数: {last_page}")
        
        # 添加第一页数据
        all_records.extend(params.get('list', []))
        
        # 如果需要查询更多页面
        if last_page > first_page:
            # 使用线程池并发查询后续页面
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有后续页面的查询任务
                future_to_page = {
                    executor.submit(
                        self.query_by_condition,
                        page=page,
                        page_size=page_size,
                        unit_name=unit_name,
                        service_type=service_type
                    ): page for page in range(first_page + 1, last_page + 1)
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        page_data = future.result()
                        if page_data.get('code') == 200:
                            page_records = page_data.get('params', {}).get('list', [])
                            all_records.extend(page_records)
                            print(f"第 {page_num} 页查询完成，获取 {len(page_records)} 条记录")
                        else:
                            print(f"第 {page_num} 页查询失败: {page_data.get('msg')}")
                    except Exception as e:
                        print(f"第 {page_num} 页查询异常: {str(e)}")
        
        return all_records
    
    def get_domains_from_records(self, records: List[Dict[str, Any]]) -> List[str]:
        """
        从记录中提取域名列表
        
        Args:
            records: 备案记录列表
            
        Returns:
            域名列表
        """
        domains = []
        for record in records:
            domain = record.get('domain')
            if domain:
                domains.append(domain)
        return domains
    
    def print_domains(self, 
                     unit_name: str = "科大讯飞股份有限公司",
                     with_details: bool = False):
        """
        打印查询到的域名信息
        
        Args:
            unit_name: 单位名称
            with_details: 是否查询详细信息
        """
        print(f"正在查询 {unit_name} 的备案信息...")
        
        # 查询所有记录
        records = self.query_all_pages(unit_name=unit_name)
        
        if not records:
            print("未查询到任何备案信息")
            return
        
        print(f"\n共查询到 {len(records)} 个备案域名：")
        print("-" * 50)
        
        for i, record in enumerate(records, 1):
            domain = record.get('domain', '未知域名')
            print(f"{i}. {domain}")
            
            # 如果需要详细信息
            if with_details:
                main_id = record.get('mainId')
                domain_id = record.get('domainId')
                service_id = record.get('serviceId')
                
                if all([main_id, domain_id, service_id]):
                    try:
                        detail = self.query_detail(main_id, domain_id, service_id)
                        if detail.get('code') == 200:
                            detail_domain = detail.get('params', {}).get('domain', '未知')
                            print(f"   详细信息: {detail_domain}")
                        else:
                            print(f"   详情查询失败: {detail.get('msg')}")
                    except Exception as e:
                        print(f"   详情查询异常: {str(e)}")
        
        print("-" * 50)