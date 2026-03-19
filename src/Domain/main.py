import argparse
import datetime
from Domain.ICPMainDomainFinder import clean_subdomains, execute_icp_query, save_subdomains

if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(
        description='这是一个参数解析示例',
        epilog='这是结尾的帮助信息'
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    # icp 命令
    icp_parser = subparsers.add_parser('icp', help='ICP备案查询')
    icp_parser.add_argument('--unit_name','-n',
                            required=True,
                           help='单位名称')
    
    
    # 通用参数
    for subparser in [icp_parser]:
        subparser.add_argument('--output', '-o',
                               default=f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}_results.txt',
                              help='输出文件')
        subparser.add_argument('--verbose', '-v',
                              action='store_true',
                              help='详细输出')

    # 解析参数
    args = parser.parse_args()

    if args.command == 'icp':
        import asyncio
        domain_list = asyncio.run(execute_icp_query(args.unit_name))
        print(f"ICP查询结果: {len(domain_list)} 个域名")
        cleaned_domains = clean_subdomains(domain_list)
        print(f"清理后共有: {len(cleaned_domains)} 个唯一域名")
        save_subdomains(args.unit_name,cleaned_domains,args.output)
    else:
        parser.print_help()
    