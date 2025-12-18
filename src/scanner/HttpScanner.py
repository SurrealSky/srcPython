#!/usr/bin/env python3
"""
HTTP扫描器
对域名进行常见端口扫描，检测特定的HTTP状态码
重点关注：200, 401, 403, 500, 503, 429, 400, 301, 302, 307, 308
"""

import requests
import concurrent.futures
import sys
import time
import signal
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Tuple
import argparse
from bs4 import BeautifulSoup
import re

# 忽略SSL警告
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

class GracefulExit:
    """优雅退出处理器"""
    def __init__(self):
        self.exit_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, signum, frame):
        print(f"\n[!] 接收到退出信号，正在终止扫描...")
        self.exit_now = True

class HttpScanner:
    def __init__(self, timeout: int = 5, max_workers: int = 10):
        """
        初始化HTTP扫描器
        
        Args:
            timeout: 请求超时时间（秒）
            max_workers: 最大并发线程数
        """
        self.timeout = timeout
        self.max_workers = max_workers
        self.exit_handler = GracefulExit()
        
        # 重点关注的状态码及其描述
        self.target_status_codes = {
            200: "200 OK - 正常访问",
            301: "301 Moved Permanently - 永久重定向",
            302: "302 Found - 临时重定向",
            307: "307 Temporary Redirect - 临时重定向(保持方法)",
            308: "308 Permanent Redirect - 永久重定向(保持方法)",
            400: "400 Bad Request - 请求错误，可能有参数注入点",
            401: "401 Unauthorized - 需要认证，可能有弱口令",
            403: "403 Forbidden - 禁止访问，目录/文件存在",
            429: "429 Too Many Requests - 频率限制",
            500: "500 Internal Server Error - 服务器错误，可能有漏洞",
            503: "503 Service Unavailable - 服务不可用(负载均衡/维护)",
        }
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'close',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 常见的HTTP/HTTPS端口
        self.common_ports = [
            (80, 'http'),
            (443, 'https'),
            (8080, 'http'),
            (8443, 'https'),
            (8888, 'http'),
            (8000, 'http'),
            (8081, 'http'),
            (8444, 'https'),
            (9000, 'http'),
            (9080, 'http'),
        ]
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def normalize_domain(self, domain: str) -> str:
        """
        规范化域名
        """
        domain = domain.strip()
        # 移除http://或https://前缀
        if domain.startswith(('http://', 'https://')):
            parsed = urlparse(domain)
            domain = parsed.netloc or parsed.path
        # 移除末尾的/
        domain = domain.rstrip('/')
        return domain

    def extract_title(self, response_content: bytes, response_headers) -> str:
        """
        从响应内容中提取页面标题
        """
        title = ""
        
        # 检查Content-Type，只处理HTML内容
        content_type = response_headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type:
            return "非HTML内容"
        
        try:
            # 尝试多种编码
            encodings = ['utf-8', 'gbk', 'gb2312', 'iso-8859-1', 'big5']
            html_content = None
            
            for encoding in encodings:
                try:
                    html_content = response_content.decode(encoding, errors='ignore')
                    break
                except:
                    continue
            
            if html_content:
                # 使用BeautifulSoup提取标题
                soup = BeautifulSoup(html_content, 'html.parser')
                title_tag = soup.title
                if title_tag and title_tag.string:
                    title = title_tag.string.strip()
                    # 清理标题中的空白字符
                    title = re.sub(r'\s+', ' ', title)
                    # 截断过长的标题
                    if len(title) > 50:
                        title = title[:47] + "..."
                else:
                    title = "无标题"
        except Exception:
            title = "标题提取失败"
        
        return title

    def get_status_color(self, status_code: int) -> str:
        """
        根据状态码获取显示颜色
        """
        colors = {
            200: '\033[92m',  # 绿色 - 成功
            301: '\033[94m',  # 蓝色 - 重定向
            302: '\033[94m',  # 蓝色 - 重定向
            307: '\033[94m',  # 蓝色 - 重定向
            308: '\033[94m',  # 蓝色 - 重定向
            400: '\033[93m',  # 黄色 - 客户端错误
            401: '\033[93m',  # 黄色 - 客户端错误
            403: '\033[93m',  # 黄色 - 客户端错误
            429: '\033[93m',  # 黄色 - 客户端错误
            500: '\033[91m',  # 红色 - 服务器错误
            503: '\033[91m',  # 红色 - 服务器错误
        }
        return colors.get(status_code, '\033[0m')

    def test_url(self, url: str) -> Tuple[bool, int, str, str, str, str]:
        """
        测试单个URL并提取标题和跳转信息
        
        Returns:
            (是否成功, 状态码, URL, 标题, 跳转URL, 错误信息)
        """
        # 检查是否收到退出信号
        if self.exit_handler.exit_now:
            return False, 0, url, "", "", "扫描已终止"
        
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                verify=False,  # 忽略SSL证书验证
                allow_redirects=False,  # 禁用自动跳转，以便获取跳转URL
                stream=True  # 流式传输，避免下载大文件
            )
            
            # 检查是否为目标状态码
            if response.status_code in self.target_status_codes:
                # 提取跳转URL（如果存在）
                redirect_url = ""
                if response.status_code in [301, 302, 307, 308]:
                    # 从响应头中获取跳转URL
                    location = response.headers.get('Location', '')
                    if location:
                        # 处理相对路径的跳转
                        if location.startswith('/'):
                            redirect_url = urljoin(url, location)
                        elif location.startswith(('http://', 'https://')):
                            redirect_url = location
                        else:
                            redirect_url = urljoin(url, '/' + location.lstrip('/'))
                
                # 读取部分内容来提取标题（对于200状态码）
                title = ""
                if response.status_code == 200:
                    content = b""
                    content_length = 0
                    max_content_length = 1024 * 1024  # 最多读取1MB
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        content += chunk
                        content_length += len(chunk)
                        if content_length >= max_content_length:
                            break
                    
                    title = self.extract_title(content, response.headers)
                
                return True, response.status_code, url, title, redirect_url, ""
            else:
                return False, response.status_code, url, "", "", ""
                
        except requests.exceptions.Timeout:
            return False, 0, url, "", "", "超时"
        except requests.exceptions.ConnectionError:
            return False, 0, url, "", "", "连接失败"
        except Exception:
            return False, 0, url, "", "", "请求失败"

    def scan_domain(self, domain: str) -> List[Dict]:
        """
        扫描单个域名的所有常见端口
        
        Returns:
            成功的结果列表
        """
        results = []
        domain = self.normalize_domain(domain)
        
        # 检查是否收到退出信号
        if self.exit_handler.exit_now:
            return results
        
        domain_printed = False
        
        for port, protocol in self.common_ports:
            # 检查是否收到退出信号
            if self.exit_handler.exit_now:
                break
                
            # 构建URL
            if protocol == 'https':
                url = f"https://{domain}:{port}"
            else:
                url = f"http://{domain}:{port}"
            
            success, status_code, test_url, title, redirect_url, error = self.test_url(url)
            
            if success:
                result = {
                    'domain': domain,
                    'url': test_url,
                    'status_code': status_code,
                    'title': title,
                    'redirect_url': redirect_url,
                    'port': port,
                    'protocol': protocol,
                    'description': self.target_status_codes[status_code]
                }
                results.append(result)
                
                # 一行显示结果
                status_color = self.get_status_color(status_code)
                reset_color = "\033[0m"
                
                # 格式化显示：在一行内显示完整信息
                if not domain_printed:
                    print(f"[+] 域名: {domain}")
                    domain_printed = True
                
                # 根据状态码构建显示信息
                status_display = f"{status_color}[{status_code}]{reset_color}"
                url_display = test_url.ljust(45)
                
                # 对于不同状态码，显示不同信息
                if status_code == 200:
                    display_title = title if title else "无标题"
                    print(f"    {status_display} {url_display} | {display_title}")
                elif status_code in [301, 302, 307, 308]:
                    if redirect_url:
                        print(f"    {status_display} {url_display} | 跳转到: {redirect_url}")
                    else:
                        print(f"    {status_display} {url_display} | 重定向")
                else:
                    print(f"    {status_display} {url_display} | {self.target_status_codes[status_code].split(' - ')[1]}")
        
        return results

    def scan_from_file(self, input_file: str) -> Dict[int, List[Dict]]:
        """
        从文件读取域名并扫描
        
        Returns:
            按状态码分类的结果字典
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                domains = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"错误: 文件 '{input_file}' 不存在！")
            sys.exit(1)
        except Exception as e:
            print(f"读取文件时出错: {str(e)}")
            sys.exit(1)
        
        if not domains:
            print("警告: 输入文件为空！")
            return {}
        
        print(f"[*] 读取到 {len(domains)} 个域名")
        print(f"[*] 开始扫描... (重点关注状态码: {', '.join(map(str, sorted(self.target_status_codes.keys())))})")
        print("[!] 按 Ctrl+C 可随时终止扫描")
        print("="*80)
        
        all_results = []
        
        try:
            # 使用线程池并发扫描
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_domain = {}
                
                # 提交所有任务
                for domain in domains:
                    # 检查是否收到退出信号
                    if self.exit_handler.exit_now:
                        print("\n[!] 正在终止任务提交...")
                        break
                    
                    future = executor.submit(self.scan_domain, domain)
                    future_to_domain[future] = domain
                
                # 处理完成的任务
                for future in concurrent.futures.as_completed(future_to_domain):
                    # 检查是否收到退出信号
                    if self.exit_handler.exit_now:
                        print("\n[!] 正在终止扫描...")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
                    
                    domain = future_to_domain[future]
                    try:
                        results = future.result(timeout=self.timeout * 2)
                        if results:
                            all_results.extend(results)
                    except concurrent.futures.TimeoutError:
                        print(f"[!] 扫描 {domain} 超时")
                    except Exception as e:
                        if not self.exit_handler.exit_now:
                            print(f"[!] 扫描 {domain} 出错: {str(e)}")
        
        except KeyboardInterrupt:
            print("\n[!] 用户中断，正在停止扫描...")
            self.exit_handler.exit_now = True
        
        # 按状态码分类结果
        classified_results = {}
        for result in all_results:
            status = result['status_code']
            if status not in classified_results:
                classified_results[status] = []
            classified_results[status].append(result)
        
        return classified_results

    def save_results(self, results: Dict[int, List[Dict]], output_file: str):
        """
        保存所有结果到一个文件，按状态码分类
        
        Args:
            results: 按状态码分类的结果字典
            output_file: 输出文件名
        """
        if not results:
            print("[!] 没有结果需要保存")
            return
        
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入文件头
            f.write("="*80 + "\n")
            f.write(f"HTTP扫描结果 - {timestamp}\n")
            f.write(f"扫描目标状态码: {', '.join(map(str, sorted(self.target_status_codes.keys())))}\n")
            f.write("="*80 + "\n\n")
            
            # 按状态码顺序写入结果
            status_order = [200, 401, 403, 500, 503, 429, 400, 301, 302, 307, 308]
            
            total_count = 0
            for status_code in status_order:
                if status_code in results:
                    result_list = results[status_code]
                    count = len(result_list)
                    total_count += count
                    
                    f.write(f"\n{'='*60}\n")
                    f.write(f"状态码 {status_code}: {self.target_status_codes[status_code]}\n")
                    f.write(f"发现数量: {count}\n")
                    f.write(f"{'='*60}\n\n")
                    
                    for result in result_list:
                        if status_code == 200:
                            f.write(f"URL: {result['url']}\n")
                            f.write(f"标题: {result['title']}\n")
                            f.write(f"端口: {result['port']} ({result['protocol']})\n")
                        elif status_code in [301, 302, 307, 308]:
                            f.write(f"URL: {result['url']}\n")
                            if result['redirect_url']:
                                f.write(f"跳转到: {result['redirect_url']}\n")
                            f.write(f"端口: {result['port']} ({result['protocol']})\n")
                        else:
                            f.write(f"URL: {result['url']}\n")
                            f.write(f"端口: {result['port']} ({result['protocol']})\n")
                        f.write("-"*60 + "\n")
            
            # 写入统计信息
            f.write(f"\n{'='*80}\n")
            f.write("统计信息\n")
            f.write(f"{'='*80}\n")
            f.write(f"扫描完成时间: {timestamp}\n")
            f.write(f"总共发现: {total_count} 个有效响应\n\n")
            
            for status_code in status_order:
                if status_code in results:
                    count = len(results[status_code])
                    percentage = (count / total_count * 100) if total_count > 0 else 0
                    f.write(f"状态码 {status_code}: {count} 个 ({percentage:.1f}%)\n")
        
        print(f"[*] 所有结果已保存到: {output_file}")
        
        # 同时生成一个简化的URL列表文件
        url_file = "urls_list.txt"
        with open(url_file, 'w', encoding='utf-8') as f:
            for status_code in status_order:
                if status_code in results:
                    for result in results[status_code]:
                        f.write(f"{result['url']}\n")
        
        print(f"[*] URL列表已保存到: {url_file}")
        
        return total_count

    def run(self,input_file: str, output_file: str = "http_scanner_results.txt", timeout: int = 5, max_workers: int = 10):
        try:
            results = self.scan_from_file(input_file)
        except KeyboardInterrupt:
            print("\n[!] 扫描被用户终止")
            sys.exit(0)
        except Exception as e:
            print(f"\n[!] 扫描过程中发生错误: {str(e)}")
            sys.exit(1)
            
        print("\n" + "="*80)
        print("扫描完成！统计信息:")
        print("="*80)
        
        if results:
            total_count = self.save_results(results, output_file)
            
            print(f"\n扫描结果总结:")
            status_order = [200, 401, 403, 500, 503, 429, 400, 301, 302, 307, 308]
            for status_code in status_order:
                if status_code in results:
                    count = len(results[status_code])
                    description = self.target_status_codes[status_code].split(' - ')[1]
                    print(f"  {status_code}: {count} 个 ({description})")
            
            print(f"\n总共发现 {total_count} 个有效响应")
        else:
            print("未发现任何目标状态码的响应")