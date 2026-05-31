"""
Eduino_PostPilot - 메인 화면 (Streamlit, 좌우 분할 / 밝은 테마 / 카드형)
------------------------------------------------------------
왼쪽 : 제품 선택 + 통이미지
오른쪽: ② 생성 → ③ 결과(제목후보/메타/본문/태그/링크/체크리스트)

기능: 글자수 · 원클릭 복사 · 제목 후보 선택 · 결과 저장 · 발행 상태 · 관련 링크
실행은 루트의 run.bat 으로 합니다.
"""
import re
from datetime import datetime

import streamlit as st

import config
import image_loader
import vision
import generator
import state

st.set_page_config(page_title="Eduino_PostPilot", page_icon="📝", layout="wide")

# ------------------------------------------------------------
# 스타일 (브랜드 헤더 · 카드 · 틸 악센트 · Pretendard)
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

    html, body, .stApp, [class*="st-"], button, input, textarea, select {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background:
            radial-gradient(circle at 1px 1px, #e6ecf3 1px, transparent 0) 0 0 / 22px 22px,
            #fafbfc;
    }
    .block-container { padding-top: 2.2rem; max-width: 1320px; }

    /* 기본 Streamlit 헤더 제목 숨김 (커스텀 헤더 사용) */
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

    /* 카드 (st.container(border=True)) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background:#ffffff; border-radius:18px; border:1px solid #e9eef4;
        box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 14px 30px rgba(15,23,42,.055);
        padding: 6px 6px;
    }
    /* 버튼 */
    .stButton > button {
        border-radius:12px; font-weight:700; border:none;
        transition: transform .05s ease;
    }
    .stButton > button:active { transform: scale(.99); }
    /* 코드블록(복사용) 살짝 다듬기 */
    .stCode { border-radius:10px; }
    label, .stMarkdown p { color:#334155; }
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


# ============================================================
left, right = st.columns([1, 1.4], gap="large")

# ---------------- 왼쪽: 제품 선택 ----------------
with left:
    with st.container(border=True):
        st.markdown('<span class="step-badge">① 제품 선택</span>', unsafe_allow_html=True)
        products = image_loader.scan_products()
        if not products:
            st.warning(
                f"제품 폴더가 없습니다.\n\n`{config.PRODUCTS_ROOT}` 안에 "
                "'[순번] 코드_제품명' 형식 폴더를 만들고 통이미지를 넣은 뒤 새로고침하세요."
            )
            st.stop()

        def fmt(i: int) -> str:
            p = products[i]
            return f"{state.STATUS_LABEL.get(state.get_status(p.code), '')}  {p.label}"

        idx = st.selectbox("제품 목록", range(len(products)), format_func=fmt)
        product = products[idx]

        st.write(f"**제품코드** : {product.code}")
        st.write(f"**제품명** : {product.name}")
        st.write(f"**상태** : {state.STATUS_LABEL.get(state.get_status(product.code), '')}")

        if product.image_path:
            st.image(str(product.image_path), caption="상세페이지 통이미지", use_container_width=True)
        else:
            st.error("이 폴더에 통이미지가 없습니다.")

# ---------------- 오른쪽: 생성 + 결과 ----------------
with right:
    with st.container(border=True):
        st.markdown('<span class="step-badge">② 블로그 생성</span>', unsafe_allow_html=True)
        run = st.button(
            "✨ 블로그 글 생성하기", type="primary",
            disabled=not product.image_path, use_container_width=True,
        )
        st.caption("⚠ 누르면 OpenAI API 과금이 발생합니다 (1편 약 150~250원).")

        if run:
            try:
                with st.status("통이미지 분석 중...", expanded=False) as s:
                    extract_md = vision.extract_from_image(product.image_path)
                    s.update(label="블로그 글 작성 중...")
                    blog = generator.generate_blog(extract_md, product.name, product.code)
                    s.update(label="완료!", state="complete")
                st.session_state["blog"] = blog
                st.session_state["blog_for"] = product.code
                ts = datetime.now().strftime("%Y%m%d_%H%M")
                safe = re.sub(r"[^\w가-힣A-Za-z0-9-]", "_", product.code)
                out_file = config.OUTPUT_DIR / f"{safe}_{ts}.md"
                out_file.write_text(blog, encoding="utf-8")
                st.session_state["saved_path"] = str(out_file)
                state.set_status(product.code, product.name, "draft")
            except Exception as e:
                st.error(f"생성 중 오류가 발생했습니다: {e}")

    with st.container(border=True):
        st.markdown('<span class="step-badge">③ 복사해서 발행</span>', unsafe_allow_html=True)

        blog = st.session_state.get("blog")
        if not blog or st.session_state.get("blog_for") != product.code:
            st.info("왼쪽에서 제품을 고르고 [블로그 글 생성하기]를 누르세요.")
        else:
            if st.session_state.get("saved_path"):
                st.caption(f"💾 저장됨: {st.session_state['saved_path']}")
            sec = split_sections(blog)

            titles = parse_title_candidates(sec["제목 후보"])
            st.markdown("**제목 후보** (클릭해 선택 → 복사)")
            chosen = st.radio("제목 선택", titles, label_visibility="collapsed")
            st.code(chosen, language=None)
            st.markdown(f'<span class="count-box">제목 {char_count(chosen)}자</span>', unsafe_allow_html=True)

            if sec["메타 디스크립션"]:
                st.markdown("**메타 디스크립션** (검색결과 요약)")
                st.code(sec["메타 디스크립션"], language=None)
                st.markdown(
                    f'<span class="count-box">메타 {char_count(sec["메타 디스크립션"])}자</span>',
                    unsafe_allow_html=True,
                )

            body = sec["본문"]
            img_slots = re.findall(r"\[이미지\s*\d+[:：][^\]]*\]", body)
            st.markdown("**본문** (📋 우측 복사)")
            st.code(body or "(본문 없음)", language=None)
            st.markdown(
                f'<span class="count-box">본문 {char_count(body)}자(공백포함)</span>'
                f'<span class="count-box">이미지 자리 {len(img_slots)}곳</span>',
                unsafe_allow_html=True,
            )
            if img_slots:
                with st.expander(f"🖼 이미지 자리 {len(img_slots)}곳 - 통이미지에서 캡처해 삽입", expanded=True):
                    for sslot in img_slots:
                        st.write("- " + sslot)

            if sec["추천 태그"]:
                st.markdown("**추천 태그** (📋 우측 복사)")
                st.code(sec["추천 태그"], language=None)

            st.markdown("**④ 관련 링크** (빈칸 직접 입력 후 본문 끝에 붙이기)")
            st.text_area("관련 링크", build_links_template(), height=170, label_visibility="collapsed")

            if sec["SEO 키워드"]:
                with st.expander("🔍 사용된 SEO 키워드"):
                    st.write(sec["SEO 키워드"])

            st.markdown("**발행 체크리스트**")
            k1, k2 = st.columns(2)
            with k1:
                st.checkbox("제목 선택·확인")
                st.checkbox("이미지 자리에 사진 삽입")
                st.checkbox("메타 디스크립션 입력")
            with k2:
                st.checkbox("관련 링크 채움")
                st.checkbox("태그 입력")
                st.checkbox("소스코드 코드블록 처리")

            if st.button("✅ 발행 완료로 표시", use_container_width=True):
                state.set_status(product.code, product.name, "published")
                st.success("발행 완료로 표시했습니다. (왼쪽 목록 상태가 🟢로 바뀝니다)")
