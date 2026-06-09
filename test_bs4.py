from bs4 import BeautifulSoup

html = '<div class=""><span title="D-NTI8-35207-00" class="badge badge-light text-crimson">35207-00 <span class="text-muted">/</span> 113-2</span> 智慧物聯網概論-網 <span class="badge badge-light">92</span></div>'
soup = BeautifulSoup(html, 'html.parser')
div = soup.find('div')

print("Using get_text:")
course_text = div.get_text(separator='|', strip=True)
parts = course_text.split('|')
print(parts)

print("\nUsing children and checking name is None:")
parts2 = [str(child).strip() for child in div.children if child.name is None and str(child).strip()]
print(parts2)
