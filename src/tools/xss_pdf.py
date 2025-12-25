# FROM https://github.com/osnr/horrifying-pdf-experiments
from PyPDF2 import PdfReader, PdfWriter

def make_pdf(output_path):
    # 创建一个新的 PDF 文档
    output_pdf = PdfWriter()
    # 添加一个新页面
    page = output_pdf.add_blank_page(width=72, height=72)
    # 添加js代码
    output_pdf.add_js("app.alert('xss');")
    # 将新页面写入到新 PDF 文档中
    with open(output_path, "wb") as f:
        output_pdf.write(f)
