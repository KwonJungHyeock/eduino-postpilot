"""
Eduino_PostPilot - 메인 화면 (Streamlit)
------------------------------------------------------------
한 화면 구성 (위 → 아래가 그대로 작업 순서)
  ① 현황 요약   : 자사 미작업/초안/발행 + 입점사 수를 한눈에
  ② 수집(접이식): 쇼핑몰 카테고리에서 제품 받아오기(폴더 채움)
  ③ 생성·검토   : 목록(자사만·미작업만 기본)에서 체크 → 한 번에 생성 → 검토·복사·발행
  ④ 작업 현황(접이식): 전체 진행 표

자사 / 입점사: 제품코드 앞글자가 config.OWN_CODE_PREFIXES(기본 A~E)면 '자사제품'
(블로그 작성 대상), 그 외는 '입점사 제품'으로 보고 기본 목록에서 숨깁니다.

발행은 여전히 사람이 검토 후 수동으로 합니다(어뷰징 회피). 자동화는 '초안 재료
수집'과 '초안 생성'까지입니다. 실행은 루트의 run.bat 으로 합니다.
"""
import html as html_lib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import config
import image_loader
import vision
import generator
import state
import crawler

st.set_page_config(page_title="Eduino_PostPilot", page_icon="📝", layout="wide")

# ------------------------------------------------------------
# 스타일 (브랜드 헤더 · 카드 · 틸 악센트 · Pretendard)
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

    /* 본문 폰트는 상속으로 적용. [class*="st-"]로 전 요소를 직접 지정하면
       머티리얼 아이콘 <span>까지 덮어써 아이콘이 'check' 글자로 깨지므로 제외 */
    html, body, .stApp, button, input, textarea, select {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background:
            radial-gradient(circle at 1px 1px, #e6ecf3 1px, transparent 0) 0 0 / 22px 22px,
            #fafbfc;
    }
    .block-container { padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1240px; }

    .app-header {
        display:flex; align-items:center; gap:16px;
        padding: 4px 0 18px; margin-bottom: 14px;
        border-bottom: 2px solid #e7edf3;
    }
    .brand-mark {
        width:54px; height:54px; border-radius:15px;
        background: linear-gradient(135deg, #06b6d4, #0e7490);
        color:#fff; font-weight:800; font-size:30px;
        display:flex; align-items:center; justify-content:center;
        box-shadow: 0 8px 20px rgba(8,145,178,.32);
        flex-shrink:0;
    }
    .brand-title { font-size:30px; font-weight:800; color:#0f172a; letter-spacing:-.6px; line-height:1.1; }
    .brand-accent { color:#0e7490; }
    .brand-sub { font-size:13.5px; color:#64748b; margin-top:4px; }

    .step-badge {
        display:inline-block; background: linear-gradient(135deg, #06b6d4, #0e7490);
        color:#fff; border-radius:999px; padding:5px 16px;
        font-size:.82rem; font-weight:700; margin-bottom:14px;
        box-shadow: 0 3px 10px rgba(8,145,178,.28); letter-spacing:.2px;
    }
    .count-box {
        background:#ecfeff; border:1px solid #cff7fb; border-radius:9px;
        padding:5px 12px; font-size:.82rem; color:#0e7490;
        display:inline-block; margin:2px 6px 2px 0; font-weight:600;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background:#ffffff; border-radius:18px; border:1px solid #e9eef4;
        box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 14px 30px rgba(15,23,42,.055);
        padding: 0 20px 18px;
    }

    /* 구간 헤더 — 카드 위쪽에 전체 폭 색 띠 + 컬러 아이콘 배지로 대비 강화 */
    .sec {
        display:flex; align-items:center; gap:11px;
        margin: 0 -20px 16px; padding: 14px 20px;
        background:#f1f5f9; border-bottom: 2px solid #cbd5e1;
        border-radius: 18px 18px 0 0;
    }
    .sec .ic {
        width:30px; height:30px; border-radius:9px; flex-shrink:0;
        display:flex; align-items:center; justify-content:center;
        color:#fff; font-weight:800; font-size:15px;
        background:var(--tone,#64748b); box-shadow:0 3px 7px rgba(0,0,0,.18);
    }
    .sec .t  { font-weight:800; color:#0f172a; font-size:1.06rem; letter-spacing:-.2px; }
    .sec .d  { color:#475569; font-size:.8rem; margin-left:auto; text-align:right; }

    /* 섹션 톤별 색 — 좌측 굵은 컬러 보더 + 진한 헤더 틴트 (대비 ↑) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.sec-summary){ border-left:6px solid #6366f1; }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.sec-gen){ border-left:6px solid #0891b2; }
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.sec-review){ border-left:6px solid #7c3aed; }
    .sec-summary{ --tone:#6366f1; background:#e0e7ff; border-bottom-color:#a5b4fc; }
    .sec-gen{ --tone:#0891b2; background:#cffafe; border-bottom-color:#67e8f9; }
    .sec-review{ --tone:#7c3aed; background:#f3e8ff; border-bottom-color:#d8b4fe; }

    /* 검토 패널 내부 소영역 카드 — 흰 큰 카드 안에서 묶음을 가볍게 구분
       (.sec 를 포함한 '큰 카드'는 제외해 헤더 카드 스타일이 깨지지 않게) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.subcard):not(:has(.sec)){
        box-shadow:none; border:1px solid #e8edf3; background:#fbfcff;
        border-radius:12px; padding: 2px 15px 12px;
    }
    .blk { display:flex; align-items:center; gap:8px; margin:12px 0 8px;
           font-weight:800; color:#0f172a; font-size:.94rem; }
    .blk .dot { width:11px; height:11px; border-radius:3px; background:var(--bc,#94a3b8); flex-shrink:0; }
    .blk small { font-weight:600; color:#94a3b8; font-size:.8rem; }

    /* 자동화 파이프라인 스테퍼 — 수집→생성→검토→발행 흐름을 한 줄에 시각화 */
    .pipe { display:flex; align-items:stretch; margin:4px 0 14px; }
    .pipe .stage {
        flex:1; padding:14px 16px; background:#fff;
        border:1px solid #eef2f7; border-top:3px solid var(--c);
        border-radius:13px; position:relative;
        box-shadow:0 1px 2px rgba(15,23,42,.04);
    }
    .pipe .stage + .stage { margin-left:26px; }
    .pipe .stage::after {
        content:'›'; position:absolute; right:-19px; top:50%;
        transform:translateY(-50%); color:#cbd5e1; font-size:22px; font-weight:800;
    }
    .pipe .stage:last-child::after { content:''; }
    .pipe .lbl { font-size:.82rem; color:#64748b; font-weight:700; display:flex; align-items:center; gap:6px; }
    .pipe .num { font-size:1.7rem; font-weight:800; color:var(--c); line-height:1.15; }
    .pipe .num small { font-size:.78rem; color:#94a3b8; font-weight:600; }

    /* 현황 지표 칩 — 흰 카드 위에서도 구분되도록 옅은 회색 칩 */
    div[data-testid="stMetric"] {
        background:#f8fafc; border:1px solid #eef2f7; border-radius:14px;
        padding: 12px 16px;
    }
    .stButton > button {
        border-radius:12px; font-weight:700; border:none;
        transition: transform .05s ease;
    }
    .stButton > button:active { transform: scale(.99); }
    .stCode { border-radius:10px; }
    /* 코드블록 복사 버튼 — 평소 은은하게 보이고(0.5), 올리면 또렷(1). 박스로 튀지 않게 */
    div[data-testid="stCode"] button,
    [data-testid="stCodeCopyButton"] { opacity:.5 !important; transition:opacity .12s; }
    div[data-testid="stCode"]:hover button,
    div[data-testid="stCode"]:hover [data-testid="stCodeCopyButton"] { opacity:1 !important; }
    label, .stMarkdown p { color:#334155; }

    /* 아이콘 폰트 복구 — 위의 전역 Pretendard 적용이 머티리얼 아이콘 폰트를
       덮어써서 체크/화살표가 'check', 'keyboard_arrow_right' 글자로 깨지는 것 방지 */
    span[data-testid="stIconMaterial"],
    [data-testid="stExpanderToggleIcon"],
    [data-testid="stStatusWidget"] span[data-testid^="stIcon"],
    .material-icons, .material-icons-outlined,
    .material-symbols-outlined, .material-symbols-rounded {
        font-family: 'Material Symbols Outlined', 'Material Symbols Rounded',
                     'Material Icons', 'Material Icons Outlined' !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 브랜드 헤더
st.markdown(
    """
    <div class="app-header">
      <div class="brand-mark">E</div>
      <div>
        <div class="brand-title">Eduino <span class="brand-accent">PostPilot</span></div>
        <div class="brand-sub">상세페이지 통이미지를 네이버 블로그 초안으로 — 검토 후 직접 발행</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 공통 헬퍼
# ============================================================
def section_header(icon: str, title: str, desc: str = "", tone: str = "") -> None:
    """카드 상단 전체 폭 색 띠 헤더 — 구간을 색감으로 또렷하게 구분.

    tone: ""|"summary"|"gen"|"review" — 헤더 띠/카드 좌측 보더 색을 결정.
    """
    cls = f"sec sec-{tone}" if tone else "sec"
    d = f'<span class="d">{desc}</span>' if desc else ""
    st.markdown(
        f'<div class="{cls}"><span class="ic">{icon}</span>'
        f'<span class="t">{title}</span>{d}</div>',
        unsafe_allow_html=True,
    )


def block_label(text: str, color: str = "#94a3b8", note: str = "") -> None:
    """검토 패널 소카드용 라벨 — 색 점 + 제목으로 어떤 영역인지 즉시 인지.

    호출한 컨테이너 안에 .subcard 마커를 심어 그 컨테이너를 '소카드'로 스타일링.
    """
    n = f' <small>{note}</small>' if note else ""
    st.markdown(
        f'<span class="subcard"></span>'
        f'<div class="blk"><span class="dot" style="background:{color}"></span>{text}{n}</div>',
        unsafe_allow_html=True,
    )


_IMG_LINE = re.compile(r"^\[이미지\s*\d+", re.IGNORECASE)


def _is_heading_line(s: str) -> bool:
    """짧고 문장부호/종결어미로 끝나지 않는 줄 = 소제목으로 보고 볼드 처리."""
    if len(s) > 22 or "," in s:
        return False
    return not re.search(r"(다|요|죠|함|음|까|네|죠|니다|세요|어요|아요)[.!?…]?$|[.!?…]$", s)


def _parse_body(body: str) -> list[tuple[str, str]]:
    """본문을 (종류, 텍스트) 줄 목록으로. 종류: img | head | para."""
    out: list[tuple[str, str]] = []
    for raw in body.splitlines():
        s = raw.strip()
        if not s:
            continue
        if _IMG_LINE.match(s):
            out.append(("img", s))
        elif _is_heading_line(s):
            out.append(("head", s))
        else:
            out.append(("para", s))
    return out


def _body_copy_text(parsed: list[tuple[str, str]]) -> str:
    """네이버에 붙여넣을 정리된 본문 — 이미지 자리/소제목 위아래로 빈 줄 확보."""
    buf: list[str] = []
    for kind, text in parsed:
        if kind in ("img", "head"):
            if buf and buf[-1] != "":
                buf.append("")
            buf.append(text)
            buf.append("")
        else:
            buf.append(text)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(buf)).strip()


def render_body_card(body: str) -> None:
    """본문을 가독성 있게(이미지 자리 여백·소제목 볼드) 렌더 + 우측 상단 복사 버튼."""
    parsed = _parse_body(body)
    rows = []
    for kind, text in parsed:
        esc = html_lib.escape(text)
        if kind == "img":
            rows.append(f'<div class="imgrow">🖼 {esc}</div>')
        elif kind == "head":
            rows.append(f'<p class="hd">{esc}</p>')
        else:
            rows.append(f"<p>{esc}</p>")
    inner = "".join(rows) or "<p>(본문 없음)</p>"
    copy_js = json.dumps(_body_copy_text(parsed))

    html = f"""
    <div id="bw">
      <div id="bar"><button id="cpy" onclick="cp()">📋 본문 복사</button></div>
      <div id="bd">{inner}</div>
    </div>
    <script>
    function cp() {{
      const t = {copy_js};
      const done = () => {{ const b=document.getElementById('cpy');
        b.textContent='✓ 복사됨'; b.classList.add('ok');
        setTimeout(()=>{{b.textContent='📋 본문 복사'; b.classList.remove('ok');}},1500); }};
      if (navigator.clipboard && window.isSecureContext) {{
        navigator.clipboard.writeText(t).then(done).catch(()=>fallback(t,done));
      }} else {{ fallback(t,done); }}
    }}
    function fallback(t,done) {{
      const ta=document.createElement('textarea'); ta.value=t;
      ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta);
      ta.select(); try{{document.execCommand('copy');}}catch(e){{}}
      document.body.removeChild(ta); done();
    }}
    </script>
    <style>
      * {{ font-family:'Pretendard',-apple-system,sans-serif; box-sizing:border-box; }}
      #bw {{ position:relative; }}
      #bar {{ display:flex; justify-content:flex-end; margin-bottom:8px; }}
      #cpy {{ cursor:pointer; background:#7c3aed; color:#fff; border:none; border-radius:9px;
              padding:7px 15px; font-weight:700; font-size:13px;
              box-shadow:0 3px 8px rgba(124,58,237,.35); }}
      #cpy.ok {{ background:#16a34a; }}
      #bd {{ max-height:540px; overflow:auto; padding:2px 14px 2px 2px;
             color:#1f2937; font-size:14px; line-height:1.85; }}
      #bd p {{ margin:0 0 11px; }}
      #bd p.hd {{ font-weight:800; color:#0f172a; margin:18px 0 9px; font-size:14.5px; }}
      #bd .imgrow {{ margin:16px 0; padding:9px 13px; background:#f1f5f9;
                     border:1px dashed #b6c2d3; border-radius:9px;
                     color:#475569; font-size:13px; font-family:ui-monospace,monospace; }}
    </style>
    """
    components.html(html, height=620, scrolling=False)


def char_count(text: str) -> int:
    return len(text or "")


def split_sections(blog: str) -> dict:
    keys = ["제목 후보", "메타 디스크립션", "본문", "추천 태그", "SEO 키워드"]
    parts = {k: "" for k in keys}
    pattern = re.compile(
        r"\[(제목\s*후보|메타\s*디스크립션|본문|추천\s*태그|SEO\s*키워드)\]\s*",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(blog))
    for i, m in enumerate(matches):
        raw = re.sub(r"\s+", " ", m.group(1)).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(blog)
        if raw in parts:
            parts[raw] = blog[start:end].strip()
    if not any(parts.values()):
        parts["본문"] = blog.strip()
    return parts


def parse_title_candidates(text: str) -> list[str]:
    out = []
    for line in text.splitlines():
        m = re.match(r"\s*\d+[.)]\s*(.+)", line)
        if m:
            out.append(m.group(1).strip())
    return out or ([text.strip()] if text.strip() else [])


def build_links_template() -> str:
    lines = [f"▶ {name} : " for name in config.LINK_MANUAL]
    lines.append("")
    lines += [f"▶ {name} : {url}" for name, url in config.LINK_FIXED.items()]
    return "\n".join(lines)


def _output_filename(code: str, name: str) -> str:
    """출력 파일명을 '제품코드_상품명_타임스탬프.md' 양식으로 통일.

    예) A-1_아두이노 UNO R3 SMD 호환보드_20260601_1530.md
    경로 금지문자만 제거하고 한글·공백은 유지(가독성), 길이는 제한.
    """
    base = f"{code}_{name}".strip()
    base = re.sub(r'[\\/:*?"<>|\n\r\t]+', " ", base)   # 윈도우 파일명 금지문자
    base = re.sub(r"\s+", " ", base).strip()
    base = base[:80].rstrip(" _-")                      # 너무 긴 이름 제한
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{base}_{ts}.md"


def produce_blog(product) -> str:
    """제품 폴더의 이미지 전부 → 추출 → 블로그 생성. (API 작업만; 저장 안 함)

    스레드에서 병렬 실행 가능하도록 파일/DB 쓰기와 분리. st.* 호출 없음.
    """
    imgs = image_loader.find_images(product.folder)
    if not imgs:
        raise RuntimeError("이 제품 폴더에 통이미지가 없습니다.")
    extract_md = vision.extract_from_paths(imgs)
    return generator.generate_blog(extract_md, product.name, product.code)


def save_blog(product, blog: str) -> str:
    """블로그를 output에 저장하고 상태를 draft + 파일경로 기록. (메인 스레드에서 호출)"""
    out_file = config.OUTPUT_DIR / _output_filename(product.code, product.name)
    out_file.write_text(blog, encoding="utf-8")
    key = product_key(product)
    state.set_status(key, product.name, "draft", output_path=str(out_file))
    st.session_state.setdefault("drafts", {})[key] = blog   # 이번 세션 검토용
    return str(out_file)


def load_draft(product) -> tuple[str | None, str | None]:
    """검토용 초안 본문 로드. 이번 세션 생성분 우선, 없으면 저장된 파일에서 재로딩."""
    key = product_key(product)
    blog = st.session_state.get("drafts", {}).get(key)
    path = state.get_output_path(key)
    if blog is None and path and Path(path).exists():
        blog = Path(path).read_text(encoding="utf-8")
    return blog, path


# ============================================================
# 공유 스냅샷 — 제품 스캔/상태/이미지수를 한 번만 계산해 화면 전체가 공유
#   (한 페이지 안에서 요약/생성/현황이 같은 데이터를 보므로, 각자 스캔하면
#    파일시스템 조회가 중복됨. 한 번만 모아 전달해 속도 확보.)
# ============================================================
def product_key(p) -> str:
    """작업 상태 식별 키. 코드는 (수동/크롤링 간) 겹칠 수 있으므로 '폴더명'으로 고유 식별."""
    return p.folder.name


def build_snapshot() -> dict:
    products = image_loader.scan_products()
    keys = [product_key(p) for p in products]
    return {
        "products": products,
        "status": state.get_status_map(keys),
        "updated": state.get_updated_map(keys),
        "img_count": {product_key(p): len(image_loader.find_images(p.folder)) for p in products},
    }


# ============================================================
# 생성·검토 — 목록에서 선택해 생성 + 검토·복사·발행
# ============================================================
def render_generate(snap: dict) -> None:
    products = snap["products"]
    if not products:
        st.info(
            f"아직 제품이 없습니다. 위 [🛰️ 쇼핑몰에서 제품 수집]을 열어 받아오거나, "
            f"`{config.PRODUCTS_ROOT}` 에 '[순번] 코드_제품명' 폴더를 직접 넣으세요."
        )
        return

    status_map = snap["status"]
    img_count = snap["img_count"]

    # ---- ① 목록에서 선택 → 생성 (전체 폭: 제품명이 길어 좌우 분할 시 잘림) ----
    with st.container(border=True):
        section_header("1", "생성할 제품 선택", "체크 → 선택한 만큼 한 번에 생성", tone="gen")
        f1, f2 = st.columns(2)
        own_only = f1.checkbox("자사제품만 보기", value=True,
                               help=f"코드 앞글자 {'·'.join(config.OWN_CODE_PREFIXES)} = 자사. "
                                    "입점사 제품은 블로그 작성 대상이 아닙니다.")
        only_todo = f2.checkbox("미작업만 보기", value=True)
        view = [p for p in products
                if (not own_only or config.is_own_code(p.code))
                and (not only_todo or status_map.get(product_key(p), "none") == "none")]

        if not view:
            st.success("조건에 맞는 제품이 없습니다. (위 필터를 꺼서 더 볼 수 있어요)")
        else:
            rows = [{
                "선택": False,
                "구분": "자사" if config.is_own_code(p.code) else "입점사",
                "순번": p.order,
                "코드": p.code,
                "제품명": p.name,
                "상태": state.STATUS_LABEL.get(status_map.get(product_key(p), "none"), ""),
                "이미지": img_count.get(product_key(p), 0),
            } for p in view]
            edited = st.data_editor(
                rows, hide_index=True, use_container_width=True,
                height=min(560, 80 + 35 * len(rows)),   # 행 수에 맞춰 높이 확보(스크롤 최소화)
                column_config={
                    "선택": st.column_config.CheckboxColumn(required=False, width="small"),
                    "구분": st.column_config.TextColumn(width="small", help="자사 = 블로그 작성 대상"),
                    "순번": st.column_config.NumberColumn(width="small"),
                    "코드": st.column_config.TextColumn(width="small"),
                    "제품명": st.column_config.TextColumn(width="large"),   # 가장 넓게
                    "상태": st.column_config.TextColumn(width="medium"),
                    "이미지": st.column_config.NumberColumn("이미지", width="small", help="통이미지 장수"),
                },
                disabled=["구분", "순번", "코드", "제품명", "상태", "이미지"],
                key="gen_select",
            )
            selected = [view[i] for i, r in enumerate(edited) if r["선택"]]
            gen_targets = [p for p in selected if img_count.get(product_key(p), 0) > 0]
            no_img_sel = [p for p in selected if img_count.get(product_key(p), 0) == 0]

            est = len(gen_targets) * 200
            c1, c2 = st.columns([2, 1])
            with c1:
                st.caption(
                    f"선택 {len(selected)}개 · 생성 대상 {len(gen_targets)}개 · "
                    f"예상 과금 약 {est:,}원 (편당 약 200원). 동시 {config.GEN_WORKERS}개 병렬."
                )
                if no_img_sel:
                    st.caption(f"⚠ 이미지 없는 {len(no_img_sel)}개는 제외됩니다.")
            with c2:
                if st.button(f"✨ 선택한 {len(gen_targets)}개 생성", type="primary",
                             disabled=not gen_targets, use_container_width=True):
                    _run_batch(gen_targets)
                    st.rerun()   # 상태 갱신. 결과는 세션에 보관됨

        _render_batch_result()

    # ---- ② 검토 · 복사 · 발행 ----
    with st.container(border=True):
        section_header("2", "검토 · 복사 · 발행", "초안을 골라 네이버에 붙여넣고 발행", tone="review")
        reviewable = [p for p in products
                      if status_map.get(product_key(p), "none") in ("draft", "published")]
        if not reviewable:
            st.info("생성된 초안이 없습니다. 위에서 제품을 골라 생성하세요.")
        else:
            def rfmt(i: int) -> str:
                p = reviewable[i]
                return f"{state.STATUS_LABEL.get(status_map.get(product_key(p), 'none'), '')}  {p.label}"

            sb_col, _ = st.columns([3, 2])   # 드롭다운이 화면 끝까지 늘어지지 않게
            ridx = sb_col.selectbox("검토할 제품", range(len(reviewable)), format_func=rfmt)
            product = reviewable[ridx]
            blog, path = load_draft(product)
            if not blog:
                st.warning("초안 파일을 찾을 수 없습니다. 다시 생성해 주세요.")
            else:
                if path:
                    sb_col.caption(f"💾 {path}")
                _render_result(blog, product)


def _run_batch(targets: list) -> None:
    """선택한 제품들을 병렬 생성(추출+작성)하고 메인 스레드에서 저장·상태기록."""
    done, fail = 0, []
    total = len(targets)
    workers = max(1, min(config.GEN_WORKERS, total))
    with st.status(f"생성 시작… (동시 {workers}개)", expanded=True) as s:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(produce_blog, p): p for p in targets}
            for fut in as_completed(futures):
                p = futures[fut]
                try:
                    save_blog(p, fut.result())
                    done += 1
                except Exception as e:
                    fail.append((p.label, str(e)))
                s.update(label=f"[{done + len(fail)}/{total}] 완료 — '{p.name}'")
        s.update(label="생성 완료", state="complete")
    st.session_state["batch_result"] = {"done": done, "fail": fail}


def _render_result(blog: str, product) -> None:
    sec = split_sections(blog)
    body = sec["본문"]
    img_slots = re.findall(r"\[이미지\s*\d+[:：][^\]]*\]", body)

    # 본문은 길고, 나머지(제목·메타·태그·링크)는 짧음 → 좌(메타) / 우(본문) 2단.
    # 본문 쪽을 넓게(가운데 여백 축소) 잡고, 각 항목을 색 점 라벨 소카드로 묶는다.
    left, right = st.columns([4, 7], gap="small")

    with left:
        with st.container(border=True):
            block_label("제목 후보", "#06b6d4", "클릭해 선택 → 복사")
            titles = parse_title_candidates(sec["제목 후보"])
            chosen = st.radio("제목 선택", titles, label_visibility="collapsed")
            st.code(chosen, language=None)
            st.markdown(f'<span class="count-box">제목 {char_count(chosen)}자</span>', unsafe_allow_html=True)

        if sec["메타 디스크립션"]:
            with st.container(border=True):
                block_label("메타 디스크립션", "#3b82f6", "검색결과 요약")
                st.code(sec["메타 디스크립션"], language=None)
                st.markdown(
                    f'<span class="count-box">메타 {char_count(sec["메타 디스크립션"])}자</span>',
                    unsafe_allow_html=True,
                )

        if sec["추천 태그"]:
            with st.container(border=True):
                block_label("추천 태그", "#14b8a6", "📋 복사")
                st.code(sec["추천 태그"], language=None)

        with st.container(border=True):
            block_label("관련 링크", "#f59e0b", "빈칸 채워 본문 끝에 붙이기")
            st.text_area("관련 링크", build_links_template(), height=160, label_visibility="collapsed")

        if sec["SEO 키워드"]:
            with st.expander("🔍 사용된 SEO 키워드"):
                st.write(sec["SEO 키워드"])

    with right:
        with st.container(border=True):
            block_label("본문", "#7c3aed", "우측 상단 버튼으로 복사 · 이미지 자리는 위아래 여백, 소제목은 볼드 자동 적용")
            render_body_card(body or "")
            st.markdown(
                f'<span class="count-box">본문 {char_count(body)}자(공백포함)</span>'
                f'<span class="count-box">이미지 자리 {len(img_slots)}곳</span>',
                unsafe_allow_html=True,
            )

    # 발행 영역 — 구분선으로 분리
    st.divider()
    st.markdown("**발행 체크리스트**")
    k1, k2, k3 = st.columns(3)
    with k1:
        st.checkbox("제목 선택·확인")
        st.checkbox("이미지 자리에 사진 삽입")
    with k2:
        st.checkbox("메타 디스크립션 입력")
        st.checkbox("관련 링크 채움")
    with k3:
        st.checkbox("태그 입력")
        st.checkbox("소스코드 코드블록 처리")

    pub_col, _ = st.columns([2, 3])   # 버튼이 화면 전체로 늘어지지 않게
    if pub_col.button("✅ 발행 완료로 표시", type="primary", use_container_width=True):
        state.set_status(product_key(product), product.name, "published")
        st.success("발행 완료로 표시했습니다. (목록 상태가 🟢로 바뀝니다)")


# ============================================================
# 상단 현황 — 자동화 파이프라인(수집→생성→검토→발행) 한눈에
# ============================================================
def render_summary(snap: dict) -> None:
    products = snap["products"]
    status_map = snap["status"]
    own = [p for p in products if config.is_own_code(p.code)]
    ext = len(products) - len(own)

    def cnt(sts: str) -> int:
        return sum(1 for p in own if status_map.get(product_key(p), "none") == sts)

    collected = len(products)
    todo, draft, pub = cnt("none"), cnt("draft"), cnt("published")

    with st.container(border=True):
        section_header(
            "📊", "자동화 현황",
            f"코드 앞글자 {'·'.join(config.OWN_CODE_PREFIXES)} = 자사 · 입점사 {ext}개",
            tone="summary",
        )
        stages = [
            ("#f59e0b", "🛰️ 수집", collected, "제품"),
            ("#06b6d4", "✍️ 생성 대기", todo, "미작업"),
            ("#8b5cf6", "📝 검토", draft, "초안"),
            ("#22c55e", "✅ 발행", pub, "완료"),
        ]
        cells = "".join(
            f'<div class="stage" style="--c:{c}">'
            f'<div class="lbl">{lbl}</div>'
            f'<div class="num">{n}<small> {unit}</small></div></div>'
            for c, lbl, n, unit in stages
        )
        st.markdown(f'<div class="pipe">{cells}</div>', unsafe_allow_html=True)

        total = len(own)
        if total:
            ratio = pub / total
            st.progress(ratio, text=f"자사 {total}개 중 {pub}개 발행 완료 · {ratio*100:.0f}%")


# ============================================================
# 수집 — 쇼핑몰에서 제품 받아오기 (한 화면 상단 expander 안에 배치)
# ============================================================
def render_collect(snap: dict) -> None:
    st.caption(
        f"대상 쇼핑몰: {config.SHOP_BASE} — 수집은 제품 폴더(상세이미지)만 채웁니다. "
        "블로그 작성은 아래 [생성]에서 합니다."
    )
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        if config.CRAWL_CATEGORIES:
            name = st.selectbox("카테고리", list(config.CRAWL_CATEGORIES.keys()))
            cate_no = str(config.CRAWL_CATEGORIES[name])
            st.caption(f"카테고리 번호(cate_no): {cate_no}")
        else:
            cate_no = str(st.number_input(
                "카테고리 번호 (cate_no)", min_value=1, value=247, step=1,
                help="쇼핑몰 카테고리 페이지 주소의 cate_no= 뒤 숫자",
            ))
    with c2:
        count = st.number_input("수집할 상품 수", min_value=1, max_value=100, value=5, step=1)
    with c3:
        st.write("")  # 버튼 세로 정렬용 여백
        st.write("")
        skip_existing = st.checkbox("기존 건너뛰기", value=True)

    if st.button("🛰️ 수집 시작", type="primary", use_container_width=True):
        try:
            with st.status("수집 준비 중…", expanded=True) as s:
                res = crawler.collect_category(
                    cate_no, int(count),
                    skip_existing=skip_existing,
                    on_progress=lambda m: s.update(label=m),
                )
                s.update(label="수집 완료", state="complete")
            # 결과를 세션에 저장해 rerun(다른 위젯 조작) 후에도 화면에 유지
            st.session_state["collect_result"] = {
                "created": [p.label for p in res.created],
                "skipped": len(res.skipped),
                "failed": [(prod.name or prod.product_no, why)
                           for prod, why in res.failed],
            }
            st.rerun()   # 새 폴더 반영해 스냅샷 갱신(결과는 세션에 보관됨)
        except Exception as e:
            st.session_state["collect_result"] = {"error": str(e)}

    _render_collect_result()


def _render_collect_result() -> None:
    """수집 결과를 세션에서 읽어 표시(rerun 후에도 유지)."""
    r = st.session_state.get("collect_result")
    if not r:
        return
    if "error" in r:
        st.error(
            f"수집 중 오류: {r['error']}\n\n"
            "쇼핑몰 접근이 막혔거나(봇 차단) 카테고리 번호가 틀렸을 수 있습니다. "
            "잠시 후 다시 시도하거나 cate_no를 확인하세요."
        )
        return
    st.success(
        f"신규 {len(r['created'])}개 저장 · 건너뜀 {r['skipped']}개 · 실패 {len(r['failed'])}개"
    )
    if r["created"]:
        st.write("**새로 받은 제품**")
        for label in r["created"]:
            st.write(f"- {label}")
    if r["failed"]:
        with st.expander(f"⚠ 실패 {len(r['failed'])}건"):
            for name, why in r["failed"]:
                st.write(f"- {name}: {why}")


def _render_batch_result() -> None:
    """일괄 생성 결과를 세션에서 읽어 표시(rerun 후에도 유지)."""
    r = st.session_state.get("batch_result")
    if not r:
        return
    if r["done"]:
        st.success(f"{r['done']}편 생성 완료. (output 폴더 저장 · 상태 🟡 초안)")
    elif not r["fail"]:
        st.info("생성된 편이 없습니다. (미작업이 없거나 편수가 0)")
    if r["fail"]:
        with st.expander(f"⚠ 실패 {len(r['fail'])}건", expanded=r["done"] == 0):
            for label, why in r["fail"]:
                st.write(f"- {label}: {why}")


# ============================================================
# 작업 현황 (접이식 대시보드)
# ============================================================
def render_worklist(snap: dict) -> None:
    products = snap["products"]
    if not products:
        st.info("아직 제품이 없습니다. 위 [🛰️ 쇼핑몰에서 제품 수집]에서 받아오거나 폴더를 추가하세요.")
        return

    status_map = snap["status"]
    updated_map = snap["updated"]
    img_count = snap["img_count"]

    own_only = st.checkbox("자사제품만", value=True, key="work_own_only")
    flt = st.radio(
        "보기", ["전체", "미작업", "초안", "발행"],
        horizontal=True, label_visibility="collapsed",
    )
    wanted = {"미작업": "none", "초안": "draft", "발행": "published"}.get(flt)

    rows = []
    for p in products:
        if own_only and not config.is_own_code(p.code):
            continue
        k = product_key(p)
        sts = status_map.get(k, "none")
        if wanted and sts != wanted:
            continue
        rows.append({
            "구분": "자사" if config.is_own_code(p.code) else "입점사",
            "순번": p.order,
            "코드": p.code,
            "제품명": p.name,
            "상태": state.STATUS_LABEL.get(sts, sts),
            "이미지": img_count.get(k, 0),
            "갱신": updated_map.get(k, "-"),
        })

    if not rows:
        st.caption("해당 조건의 제품이 없습니다.")
    else:
        st.dataframe(
            _style_worklist(rows), use_container_width=True, hide_index=True,
            column_config={"제품명": st.column_config.TextColumn(width="large")},
        )
    st.caption("‘미작업’ 자사제품이 다음에 생성할 대상입니다. 위 [생성]에서 골라 만드세요.")


# 상태/구분 칸을 색 배지로 — 한눈에 진행도 파악
_BADGE_CSS = {
    "⚪ 미작업": "background:#eef2f7;color:#475569;",
    "🟡 초안 생성됨": "background:#fef9c3;color:#854d0e;",
    "🟢 발행 완료": "background:#dcfce7;color:#166534;",
    "자사": "background:#cffafe;color:#0e7490;font-weight:700;",
    "입점사": "background:#f1f5f9;color:#94a3b8;",
}


def _style_worklist(rows: list[dict]):
    """현황 표를 pandas Styler로 — 상태/구분 칸에 색 배지를 입힌다."""
    import pandas as pd

    df = pd.DataFrame(rows)

    def cell(val):
        base = "border-radius:8px;padding:3px 10px;font-weight:600;"
        return base + _BADGE_CSS.get(val, "") if val in _BADGE_CSS else ""

    styler = df.style.map(cell, subset=["구분", "상태"])
    return styler


# ============================================================
# 한 화면 구성: 위에서 아래로 보면 그대로 작업 순서가 됩니다.
#   ① 현황 요약  →  ② 수집(접이식)  →  ③ 생성·검토  →  ④ 작업 현황(접이식)
# ============================================================
snap = build_snapshot()   # 제품 스캔/상태/이미지수를 한 번만 계산해 화면 전체가 공유

render_summary(snap)

with st.expander("🛰️ 쇼핑몰에서 제품 수집 (필요할 때만 펼치기)", expanded=not snap["products"]):
    render_collect(snap)

st.markdown("#### ✍️ 블로그 생성 · 검토")
render_generate(snap)

with st.expander("📋 작업 현황 전체 보기", expanded=False):
    render_worklist(snap)
