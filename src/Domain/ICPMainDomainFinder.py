import asyncio

import ujson
from Domain.icp.ymicp import beian
from datetime import datetime

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
    return domain_list

def get_domain_list_from_response(response):
    domain_list = []
    if response and 'params' in response and 'list' in response['params']:
        unitName_list = response['params']['list']
        for item in unitName_list:
            if item.get('domain') and item.get('unitName'):
                if item['domain'] not in domain_list:
                    domain_list.append(item['domain'])
                else:
                    # 记录重复domainId到新日志
                    print(f"重复domain: {item['domainId']}\tunitName:{item['unitName']}\tdomain:{item['domain']}")
            else:
                print("unitName or domain is None...")
    else:
        print(f"No domain found in {response}. Skipping...")
    return domain_list

def query_from(query_url, search_data, id):

    params = {
        'search': search_data,
        'pageNum': 1,
        'pageSize': 10,
    }

    req = make_request(query_url, params, search_data)
    
    # 检查req是否为字典类型或是否包含所需的键
    if req and isinstance(req, dict) and 'params' in req:
        try:
            req_list = req['params']['list']
            if req_list and isinstance(req_list, list) and len(req_list) > 0:
                params['search'] = req_list[0]['unitName']
                req_unitName = make_request(query_url, params, params['search'])
                if req_unitName and isinstance(req_unitName, dict) and 'params' in req_unitName:
                    total = req_unitName['params']['total']
                    domain_list = Page_traversal_temporary(id, total, params, query_url, req_list)

                    if domain_list and isinstance(domain_list, list) and total != len(domain_list):
                        print(f"{search_data} 应提取出 {total} 条信息，实际为 {len(domain_list)} 条")
                    return total

        except Exception as e:
            print(f"{search_data} an error occurred: {str(e)}")
    return None

def query_from_file(query_url, filename, start_index):
    with open(filename, 'r', encoding='utf-8') as file:
        data_list = file.readlines()
        total_domains = len(data_list)
    if start_index < 1:
        start_index = 1
        print("输入异常, start_index 重置为 1")
    elif start_index > total_domains:
        start_index = total_domains
        print(f"输入异常, start_index 重置为 {total_domains}")
        
    for index in range(start_index-1, total_domains):
        data = data_list[index].strip()
        
        if data:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')
            Processing_Domain_output = f'Time: {current_time}, Schedule: {index+1}/{total_domains}, Domain: {data}'
            print("\n")
            print(f"Processing {Processing_Domain_output}")
            print("\n")
            total = query_from(query_url, data, index+1)
            if total is not None:
                Processing_Domain_output += f', Total: {total}'
                print(Processing_Domain_output, 'processing_Domain.log')   

async def execute_icp_query(query_args='科大讯飞股份有限公司'):
    print(f"执行ICP查询: {query_args}")
    # 可选代理配置
    proxies ="http://127.0.0.1:8080"
    #proxies = None  # 如果不使用代理则设置为None

    icp = beian()
    try:
        #第一次查询，先请求验证码，获取token
        success, token, base_header = await icp.get_token(proxies)
        if not success:
            print(f"获取token失败：{token}")
            return False, token,'','',''
        #获取验证码
        while True:
            success, p_uuid, token, sign, base_header = await icp.check_img(proxies)
            if not success:
                print(f"打码失败：{p_uuid} ,重新尝试打码...")
                continue
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

def save_subdomains(unit_name,subdomains,output_file=None):
    """
    保存子域名到文件
    """
    if len(subdomains)==0:
        print("[!] 无子域名可保存")

    if output_file is None:
        output_file = f"{unit_name}_icp_domains.txt"
    # 排序以便阅读
    sorted_subdomains = sorted(subdomains, key=lambda x: (len(x.split('.')), x))
    print(f"[+] 找到 {len(sorted_subdomains)} 个唯一子域名")
    # 保存到文本文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for subdomain in sorted_subdomains:
            f.write(f"{subdomain}\n")
    print(f"[+] 子域名已保存到: {output_file}")