import asyncio
import argparse
import csv
import time
import ujson
from icp.ymicp import beian
from datetime import datetime
from icp.mlog import logger

async def Page_traversal_temporary(icp, info , base_header ,total , proxies):
    # 分页获取所有数据，解决单页数量限制问题
    domain_list = []
    total_pages = (total + info['pageSize'] - 1) // info['pageSize']
    while info['pageNum'] <= total_pages:
        length = str(len(str(ujson.dumps(info, ensure_ascii=False)).encode("utf-8")))
        base_header.update({"Content-Length": length})
        async with icp.get_session(proxies) as session:
            async with session.post(icp.queryByCondition,
                                    data=ujson.dumps(info, ensure_ascii=False),
                                    headers=base_header,
                                    proxy=proxies if proxies else None) as req:
                res = await req.text()
        if "当前访问疑似黑客攻击" in res:
            print("当前访问已被创宇盾拦截")
        result = ujson.loads(res)
        domain_list.extend(get_domain_list_from_response(result))
        info['pageNum'] += 1
        time.sleep(5.0)  # 避免过快请求导致被封禁
    return domain_list

def get_domain_list_from_response(response):
    domain_list = []
    if response and 'params' in response and 'list' in response['params']:
        unitName_list = response['params']['list']
        for item in unitName_list:
            if item.get('domain') and item.get('serviceLicence'):
                domain_list.append([item['serviceLicence'], item['domain']])
            else:
                print("unitName or domain is None...")
    else:
        print(f"No domain found in {response}. Skipping...")
    return domain_list

async def execute_icp_query(query_args='科大讯飞股份有限公司'):
    logger.info(f"执行ICP查询: {query_args}")
    # 可选代理配置
    #proxies ="http://127.0.0.1:8080"
    proxies = None  # 如果不使用代理则设置为None

    icp = beian()
    try:
        #第一次查询，先请求验证码，获取token
        success, token, base_header = await icp.get_token(proxies)
        if not success:
            logger.error(f"获取token失败：{token}")
            return False, token,'','',''
        #获取验证码
        while True:
            success, p_uuid, token, sign, base_header = await icp.check_img(proxies)
            if not success:
                logger.error(f"打码失败：{p_uuid} ,重新尝试打码...")
            break
        #查询网站
        info = ujson.loads(icp.typj.get(0))     #0是查询网站
        info["pageNum"] = ''
        info["pageSize"] = ''
        info["unitName"] = query_args
        length = str(len(str(ujson.dumps(info, ensure_ascii=False)).encode("utf-8")))
        base_header.update({"Content-Length": length, "Uuid": p_uuid, "Token": token, "Sign": sign})
        async with icp.get_session(proxies) as session:
            async with session.post(icp.queryByCondition,
                                    data=ujson.dumps(info, ensure_ascii=False),
                                    headers=base_header,
                                    proxy=proxies if proxies else None) as req:
                res = await req.text()
                rci = req.headers.get('Rci', '')
        if "当前访问疑似黑客攻击" in res:
            print("当前访问已被创宇盾拦截")
        result = ujson.loads(res)
        domain_list = []
        if result is not None and result.get('success')== True:
            #取出第一次查询结果
            domain_list = get_domain_list_from_response(result)
            total = result['params'].get('total', 0)
            info["pageNum"] = 2
            info["pageSize"] = result['params'].get('pageSize', 0)
            print(f"查询结果总数: {total} , pageSize: {info['pageSize']}")
            if( total > info["pageSize"]):
                base_header.update({"Rci": rci})
                result = await Page_traversal_temporary(icp,info,base_header,total,proxies)
            #需要合并result和domainId_list
            domain_list.extend(result)
        return domain_list
    finally:
        await icp.cleanup()
        await asyncio.sleep(0.1)  # 确保清理完成

# 清理和过滤域名
def clean_domains(domains):
    """
    清理和过滤域名
    """
    cleaned = set()
    
    for domain in domains:
        if domain in cleaned:
            continue
        cleaned.add(domain)
    return cleaned

def save_subdomains(unit_name,domains,output_file=None):
    """
    保存子域名到文件
    """
    if len(domains)==0:
        print("[!] 无域名可保存")

    if output_file is None:
        now = datetime.datetime.now()
        date_str = f"{now.year}{now.month:02d}{now.day:02d}"
        output_file = f"{unit_name}_icp_domains_{date_str}.csv"
    # 保存到文本文件
    with open(output_file, 'w',newline="", encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(domains)   # 一次性写入多行
    print(f"[+] 域名已保存到: {output_file}")

#数据源为工信部服务平台：https://beian.miit.gov.cn/
#基于https://github.com/HG-ha/ICP_Query项目，由于网站接口经常变动，所以使用时关注项目更新，或者自行调整代码以适应接口变动
#py -3 .\src\Domain\ICPMainDomainFinder.py -n 科大讯飞股份有限公司
#py -3 .\src\Domain\ICPMainDomainFinder.py -n 皖ICP备05001217号
if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(description='这是一个示例程序')
    # 添加位置参数（必须按顺序提供）
    parser.add_argument('--unit_name','-n',required=True,help='单位名称')
    parser.add_argument('--output', '-o',default=f'icp_{datetime.now().strftime("%Y%m%d_%H%M%S")}_results.csv',help='输出文件')
    parser.add_argument('--verbose', '-v',action='store_true',help='详细输出')
    # 解析参数
    args = parser.parse_args()
    domain_list = asyncio.run(execute_icp_query(args.unit_name))
    print(f"ICP查询结果: {len(domain_list)} 个域名")
    save_subdomains(args.unit_name,domain_list,args.output)