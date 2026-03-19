import argparse
import datetime

from tools.TxtFileMerger import TxtFileMerger
from tools.TextDiff import TextDiff
from tools.xss_pdf import make_pdf

if __name__ == "__main__":
    # 创建解析器
    parser = argparse.ArgumentParser(
        description='这是一个参数解析示例',
        epilog='这是结尾的帮助信息'
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    #txt合并去重
    txt_merge_parser = subparsers.add_parser('txt_merge', help='TXT文件合并去重')
    txt_merge_parser.add_argument('--input_files','-i',   
                            nargs='+',
                            required=True,
                            help='输入的TXT文件列表')
    
    #txt差异项
    txt_diff_parser = subparsers.add_parser('txt_diff', help='TXT文件差异对比')
    txt_diff_parser.add_argument('--first_file','-f',  
                            required=True,
                            help='基准TXT文件')
    txt_diff_parser.add_argument('--second_file','-s',  
                            required=True,
                            help='参考TXT文件') 
        
    #xss_pdf 命令 (示例占位符)
    xss_pdf_parser = subparsers.add_parser('xss_pdf', help='生成含XSS的PDF文件')

    # 通用参数
    for subparser in [txt_merge_parser,txt_diff_parser,xss_pdf_parser]:
        subparser.add_argument('--output', '-o',
                               default=f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}_results.txt',
                              help='输出文件')
        subparser.add_argument('--verbose', '-v',
                              action='store_true',
                              help='详细输出')

    # 解析参数
    args = parser.parse_args()

    if args.command == 'txt_merge':
        merger = TxtFileMerger()
        print("执行TXT文件合并去重")
        merger.process(
            input_paths=args.input_files,
            output_file="merged_result.txt",
            deduplicate=True,
            sort_lines=True
        )
    elif args.command == 'txt_diff':
        print("执行TXT文件差异对比")
        diff = TextDiff(args.first_file)
        diff.save_diff(
            args.second_file,
            output_file="diff_result.txt"
        )
    elif args.command == 'xss_pdf':
        print("执行XSS PDF生成工具")
        make_pdf(args.output)
    else:
        parser.print_help()
    