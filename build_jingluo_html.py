# -*- coding: utf-8 -*-
"""
한의과대학 공통교재 경락학(1) 곽애춘·황룡상 정본 교감 마스터 HTML 빌더
"""
import os
import re
import html
import base64
import mimetypes
import markdown
from bs4 import BeautifulSoup

SOURCE_MD = r"C:\workspace\경혈학 공통교재\경락학_교감_마스터.md"
TEMPLATE_HTML = r"C:\workspace\classics\xueshushi-dagang.html"
OUT_ROOT_1 = r"C:\workspace\classics\jingluoxue-master.html"
OUT_ROOT_2 = r"C:\workspace\classics\경락학_교감_마스터.html"
OUT_SUB_1 = r"C:\workspace\classics\jingluoxue-master\index.html"
OUT_SUB_2 = r"C:\workspace\classics\경락학_교감_마스터\index.html"

def main():
    print("Reading source markdown...")
    with open(SOURCE_MD, "r", encoding="utf-8") as f:
        md_text = f.read()

    print("Reading template HTML...")
    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        tpl_text = f.read()

    # Extract CSS from template
    css_match = re.search(r"<style>(.*?)</style>", tpl_text, re.DOTALL)
    css_content = css_match.group(1) if css_match else ""

    # Extract JS from template (all scripts before </body>)
    js_match = re.search(r"</main>\s*<script>(.*?)</script>\s*</body>", tpl_text, re.DOTALL)
    if not js_match:
        # fallback regex
        js_match = re.search(r"<script>(/\* TCM 전자책.*?</script>)\s*</body>", tpl_text, re.DOTALL)
    if js_match:
        js_content = js_match.group(1)
        # Update DOC_KEY to jingluoxue_master_v3
        js_content = re.sub(
            r"const DOC_KEY = ['\"][^'\"]+['\"];",
            "const DOC_KEY = 'jingluoxue_master_v3';",
            js_content
        )
        js_content = re.sub(
            r"var DK = ['\"][^'\"]+['\"]",
            "var DK = 'jingluoxue_master_v3'",
            js_content
        )
    else:
        raise ValueError("Could not extract main script from template!")

    print("Converting Markdown to HTML...")
    # Markdown extensions
    md_exts = [
        'extra',
        'tables',
        'fenced_code',
        'toc',
        'attr_list',
        'def_list',
        'sane_lists'
    ]
    raw_html = markdown.markdown(md_text, extensions=md_exts)

    print("Parsing HTML and building TOC...")
    soup = BeautifulSoup(raw_html, "html.parser")

    # Add id to headers and collect TOC entries
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
    toc_items = []
    seen_ids = set()

    for idx, h in enumerate(headings):
        text = h.get_text().strip()
        tag_level = int(h.name[1])
        
        # generate slug
        slug = re.sub(r'[^\w\s-]', '', text).strip().replace(' ', '-')
        if not slug or slug in seen_ids:
            slug = f"{slug}_{idx}" if slug else f"heading_{idx}"
        seen_ids.add(slug)
        h['id'] = slug
        
        # We include h1, h2, h3, h4 in TOC
        if tag_level <= 4:
            toc_items.append({
                'id': slug,
                'title': text,
                'level': tag_level
            })

    # 본문 내부 목차 링크 보정: 마크다운 toc 슬러그(소문자·축약형)와
    # 위에서 부여한 heading id(대소문자 보존·전체형)가 어긋나는 경우를 맞춘다.
    lower_map = {i.lower(): i for i in seen_ids}
    for a in soup.find_all('a', href=True):
        href = a['href']
        if not href.startswith('#') or href[1:] in seen_ids:
            continue
        frag = href[1:].lower()
        target = lower_map.get(frag)
        if not target:
            cands = [i for i in seen_ids if i.lower().startswith(frag + '-')]
            target = cands[0] if len(cands) == 1 else None
        if target:
            a['href'] = '#' + target
        else:
            print(f"  [WARN] 내부 링크 대상 없음: {href}")

    # 이미지 인라인(base64): 루트·하위 폴더 사본 모두 경로 문제 없이 표시되도록
    # 다른 classics 페이지와 같은 방식으로 data URI로 넣는다.
    img_base = os.path.dirname(TEMPLATE_HTML)
    for img in soup.find_all('img', src=True):
        src = img['src']
        if src.startswith(('data:', 'http://', 'https://')):
            continue
        img_path = os.path.join(img_base, *src.split('/'))
        if not os.path.isfile(img_path):
            print(f"  [WARN] 이미지 없음: {src}")
            continue
        mime = mimetypes.guess_type(img_path)[0] or 'image/png'
        with open(img_path, 'rb') as imf:
            img['src'] = f"data:{mime};base64," + base64.b64encode(imf.read()).decode('ascii')

    # Wrap tables in .table-wrap
    for table in soup.find_all('table'):
        wrap = soup.new_tag('div', attrs={'class': 'table-wrap'})
        table.wrap(wrap)

    # Assign data-edit-id to top-level block elements in main
    block_idx = 0
    for el in soup.contents:
        if el.name in ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'div', 'ul', 'ol', 'hr']:
            el['data-edit-id'] = f"blk_{block_idx}"
            block_idx += 1

    # Build TOC HTML
    # 계층형 트리 구성
    toc_html_parts = ['<ul class="toc-root">']
    current_level = 1
    
    for item in toc_items:
        lvl = item['level']
        title = html.escape(item['title'])
        # Truncate very long titles for TOC
        short_title = title if len(title) <= 50 else title[:48] + '...'
        
        # Render item
        toc_html_parts.append(
            f'<li class="lvl-h{lvl}"><a href="#{item["id"]}">{short_title}</a></li>'
        )

    toc_html_parts.append('</ul>')
    toc_html_str = "\n".join(toc_html_parts)

    body_content_html = str(soup)

    title_str = "한의과대학 공통교재 경락학 (곽애춘·황룡상 정본 교감 전편 마스터)"

    def build_page(auth_src):
        tpl = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<script src="{{AUTH_SRC}}"></script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<style>
{{CSS_CONTENT}}
</style>
</head>
<body>
<div class="toolbar">
  <button class="tb-toc-toggle" onclick="toggleSidebarToc()" title="목차 열기/닫기">☰ 목차</button>
  <strong style="font-size:0.95em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; max-width:480px; font-family:'Noto Serif KR', serif;">
    경락학 교감 마스터 (Version 3.0)
  </strong>
  <span class="toolbar-spacer"></span>
  <span class="edit-status" id="edit-status"></span>
  <button onclick="changeFontSize(1)" title="글자 크게">가+</button>
  <button onclick="changeFontSize(-1)" title="글자 작게">가-</button>
  <button onclick="toggleDarkMode()" title="다크 모드 전환">🌓</button>
  <button onclick="toggleNotePanel()" title="메모/형광펜 패널">📝 <span id="note-count"></span></button>
  <button onclick="exportHTMLPrompt()" title="작업본 HTML 내보내기">💾 내보내기</button>
</div>

<!-- 메모/마킹 목록 사이드 패널 -->
<div id="note-panel" class="note-panel">
  <div class="np-header">
    <div class="np-title">메모 및 마킹 목록 <span id="np-count-detail" style="font-size:0.8em; font-weight:normal; color:var(--np-muted);"></span></div>
    <button class="np-close" onclick="toggleNotePanel()">×</button>
  </div>
  <div class="np-tabs">
    <button class="np-tab active" data-tab="all" onclick="switchNoteTab('all')">전체</button>
    <button class="np-tab" data-tab="memo" onclick="switchNoteTab('memo')">메모</button>
    <button class="np-tab" data-tab="mark" onclick="switchNoteTab('mark')">형광펜·밑줄</button>
  </div>
  <div class="np-search-wrap">
    <input type="text" id="np-search" placeholder="메모 또는 인용문 검색..." oninput="renderNotePanel()">
  </div>
  <div class="np-list" id="np-list"></div>
</div>

<aside class="sidebar-toc">
  <h2>목차 (Table of Contents)</h2>
  <div class="toc-controls">
    <button onclick="tocExpandAll()">모두 펼치기</button>
    <button onclick="tocCollapseAll()">모두 접기</button>
  </div>
  <div class="toc-search-wrap" style="margin-bottom:10px;">
    <input type="text" id="toc-search" placeholder="목차 검색..." oninput="filterToc(this.value)" style="width:100%; padding:4px 8px; font-size:12px; border:1px solid var(--rule); border-radius:3px; background:var(--card); color:var(--fg);">
  </div>
  {{TOC_HTML}}
</aside>

<main style="max-width:960px; margin:0 auto; padding:24px 20px 100px; line-height:1.9;">
{{BODY_CONTENT}}
</main>

<script>
// 목차 실시간 검색 필터 함수
function filterToc(keyword) {
  var kw = (keyword || '').trim().toLowerCase();
  var lis = document.querySelectorAll('aside.sidebar-toc li');
  lis.forEach(function(li) {
    var a = li.querySelector('a');
    if (!a) return;
    var match = kw === '' || a.textContent.toLowerCase().includes(kw);
    li.style.display = match ? '' : 'none';
  });
}

{{JS_CONTENT}}
</script>
</body>
</html>
"""
        return tpl.replace("{{AUTH_SRC}}", auth_src)\
                  .replace("{{TITLE}}", title_str)\
                  .replace("{{CSS_CONTENT}}", css_content)\
                  .replace("{{TOC_HTML}}", toc_html_str)\
                  .replace("{{BODY_CONTENT}}", body_content_html)\
                  .replace("{{JS_CONTENT}}", js_content)

    print("Generating output files...")
    # Root level (auth.js)
    root_html = build_page("auth.js")
    with open(OUT_ROOT_1, "w", encoding="utf-8") as f:
        f.write(root_html)
    print(f"Written: {OUT_ROOT_1} ({len(root_html):,} bytes)")

    with open(OUT_ROOT_2, "w", encoding="utf-8") as f:
        f.write(root_html)
    print(f"Written: {OUT_ROOT_2} ({len(root_html):,} bytes)")

    # Subdirectory level (../auth.js)
    sub_html = build_page("../auth.js")
    with open(OUT_SUB_1, "w", encoding="utf-8") as f:
        f.write(sub_html)
    print(f"Written: {OUT_SUB_1} ({len(sub_html):,} bytes)")

    with open(OUT_SUB_2, "w", encoding="utf-8") as f:
        f.write(sub_html)
    print(f"Written: {OUT_SUB_2} ({len(sub_html):,} bytes)")

    # Write README.md in subdirectories
    readme_content = f"""# 한의과대학 공통교재 『경락학』 곽애춘·황룡상 정본 교감 마스터

- **원전 및 판본**:
  1. 곽애춘 주편, 《황제내경소문교주어역》 & 《황제내경영추교주어역》 (2026년 정본 한국어 번역본)
  2. 한의과대학 공통교재 편찬위원회, 《경락학(1)》 (인쇄본 p.1~762 전편)
  3. 황룡상 주편, 《중국침구경락통감》 (전5부 39편 전권 고증 DB) & 《중국침구혈위통감》
- **판본 버전**: Version 3.0 Dual SSOT 통합판
- **웹 뷰어**: [jingluoxue-master.html](../jingluoxue-master.html) 또는 [index.html](index.html)
- **보안**: `auth.js` 패스워드 보호 적용
"""
    with open(r"C:\workspace\classics\jingluoxue-master\README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    with open(r"C:\workspace\classics\경락학_교감_마스터\README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("README.md created in subdirectories.")

if __name__ == "__main__":
    main()
