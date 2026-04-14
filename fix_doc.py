import re

with open('backend/services/document_processor.py', 'r') as f:
    content = f.read()

# The second process_pdf starts with:
#     def process_pdf(self, file_path: str) -> Optional[Dict[str, Any]]:
#         """处理PDF文件
#         
#         优先使用PyMuPDF（fitz）进行解析，以获得更好的CJK字符支持。

# We want to remove the second process_pdf and process_docx, but keep process_xlsx.
# Let's find the string and replace it.

pattern_to_remove = re.compile(
    r'    def process_pdf\(self, file_path: str\) -> Optional\[Dict\[str, Any\]\]:\n\s+"""处理PDF文件\n\s+优先使用PyMuPDF.*?def process_xlsx',
    re.DOTALL
)

new_content = pattern_to_remove.sub('    def process_xlsx', content)

with open('backend/services/document_processor.py', 'w') as f:
    f.write(new_content)

print("Done")
