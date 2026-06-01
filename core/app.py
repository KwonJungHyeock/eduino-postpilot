"""
Eduino_PostPilot - 메인 화면 (Streamlit)
------------------------------------------------------------
탭 구성
  ① 단건 작업      : 제품 하나 골라 통이미지 확인 → 생성 → 복사 발행 (기존 흐름)
  ② 자동 수집·일괄 : 쇼핑몰 카테고리에서 자동 수집 → 미작업 N편 일괄 생성
  ③ 작업 현황      : 작업됨/미작업 한눈에 보고 다음 할 일 구분

발행은 여전히 사람이 검토 후 수동으로 합니다(어뷰징 회피). 자동화는 '초안 재료
수집'과 '초안 생성'까지입니다. 실행은 루트의 run.bat 으로 합니다.
"""
import re
from datetime import datetime

import streamlit as st

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
    .block-container { padding-top: 2.2rem; max-width: 1320px; }

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
        padding: 6px 6px;
    }
    .stButton > button {
        border-radius:12px; font-weight:700; border:none;
        transition: transform .05s ease;
    }
    .stButton > button:active { transform: scale(.99); }
    .stCode { border-radius:10px; }
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


def generate_for(product) -> tuple[str, str]:
    """제품 폴더의 이미지 전부 → 추출 → 블로그 생성 → output 저장 → 상태=draft.

    반환: (블로그 본문, 저장 경로). 단건/일괄 양쪽에서 공통으로 사용.
    """
    imgs = image_loader.find_images(product.folder)
    if not imgs:
        raise RuntimeError("이 제품 폴더에 통이미지가 없습니다.")
    extract_md = vision.extract_from_paths(imgs)
    blog = generator.generate_blog(extract_md, product.name, product.code)

    out_file = config.OUTPUT_DIR / _output_filename(product.code, product.name)
    out_file.write_text(blog, encoding="utf-8")
    state.set_status(product.code, product.name, "draft")
    return blog, str(out_file)


# ============================================================
# 공유 스냅샷 — 제품 스캔/상태/이미지수를 한 번만 계산해 세 탭이 공유
#   (Streamlit은 매 rerun마다 탭 3개 본문을 모두 실행하므로, 따로 스캔하면
#    파일시스템 조회가 3중복으로 일어남. 한 번만 모아 전달해 속도 확보.)
# ============================================================
def build_snapshot() -> dict:
    products = image_loader.scan_products()
    codes = [p.code for p in products]
    return {
        "products": products,
        "status": state.get_status_map(codes),
        "updated": state.get_updated_map(codes),
        "img_count": {p.code: len(image_loader.find_images(p.folder)) for p in products},
    }


# ============================================================
# 탭 ① 단건 작업
# ============================================================
def render_manual(snap: dict) -> None:
    left, right = st.columns([1, 1.4], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<span class="step-badge">① 제품 선택</span>', unsafe_allow_html=True)
            products = snap["products"]
            if not products:
                st.warning(
                    f"제품 폴더가 없습니다.\n\n`{config.PRODUCTS_ROOT}` 안에 "
                    "'[순번] 코드_제품명' 형식 폴더를 만들거나, [자동 수집·일괄] 탭에서 "
                    "쇼핑몰에서 수집하세요."
                )
                return

            status_map = snap["status"]

            def fmt(i: int) -> str:
                p = products[i]
                return f"{state.STATUS_LABEL.get(status_map.get(p.code, 'none'), '')}  {p.label}"

            idx = st.selectbox("제품 목록", range(len(products)), format_func=fmt)
            product = products[idx]

            st.write(f"**제품코드** : {product.code}")
            st.write(f"**제품명** : {product.name}")
            st.write(f"**상태** : {state.STATUS_LABEL.get(status_map.get(product.code, 'none'), '')}")

            imgs = image_loader.find_images(product.folder)
            if imgs:
                st.caption(f"통이미지 {len(imgs)}장")
                for ip in imgs:
                    st.image(str(ip), use_container_width=True)
            else:
                st.error("이 폴더에 통이미지가 없습니다.")

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
                        blog, saved = generate_for(product)
                        s.update(label="완료!", state="complete")
                    st.session_state["blog"] = blog
                    st.session_state["blog_for"] = product.code
                    st.session_state["saved_path"] = saved
                    st.rerun()   # 스냅샷 갱신(상태 🟡 즉시 반영). 결과는 세션에 보관됨
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
                _render_result(blog, product)


def _render_result(blog: str, product) -> None:
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
        st.success("발행 완료로 표시했습니다. (목록 상태가 🟢로 바뀝니다)")


# ============================================================
# 탭 ② 자동 수집 · 일괄 생성
# ============================================================
def render_auto(snap: dict) -> None:
    col1, col2 = st.columns(2, gap="large")

    # ---- 수집 ----
    with col1:
        with st.container(border=True):
            st.markdown('<span class="step-badge">A. 쇼핑몰에서 자동 수집</span>', unsafe_allow_html=True)
            st.caption(f"대상 쇼핑몰: {config.SHOP_BASE}")

            if config.CRAWL_CATEGORIES:
                name = st.selectbox("카테고리", list(config.CRAWL_CATEGORIES.keys()))
                cate_no = str(config.CRAWL_CATEGORIES[name])
                st.caption(f"카테고리 번호(cate_no): {cate_no}")
            else:
                cate_no = str(st.number_input(
                    "카테고리 번호 (cate_no)", min_value=1, value=247, step=1,
                    help="쇼핑몰 카테고리 페이지 주소의 cate_no= 뒤 숫자",
                ))

            count = st.number_input("수집할 상품 수", min_value=1, max_value=100, value=5, step=1)
            skip_existing = st.checkbox("이미 받은 상품은 건너뛰기", value=True)

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
                    # 방금 수집한 제품코드 기록 → '방금 수집분만 생성' 옵션에서 사용
                    st.session_state["collect_codes"] = [p.code for p in res.created]
                    # 방금 수집한 개수에 '생성 편수'를 맞춰 둠(수집=1이면 생성도 1로 제안)
                    if res.created:
                        st.session_state["gen_n"] = len(res.created)
                    st.rerun()   # 새 폴더 반영해 스냅샷 갱신(결과는 세션에 보관됨)
                except Exception as e:
                    st.session_state["collect_result"] = {"error": str(e)}

            _render_collect_result()

    # ---- 일괄 생성 ----
    with col2:
        with st.container(border=True):
            st.markdown('<span class="step-badge">B. 미작업 N편 일괄 생성</span>', unsafe_allow_html=True)

            products = snap["products"]
            status_map = snap["status"]
            img_count = snap["img_count"]

            todo_all = [p for p in products if status_map.get(p.code, "none") == "none"]
            gen_pool = [p for p in todo_all if img_count[p.code] > 0]   # 생성 가능(이미지 있음)
            no_img = [p for p in todo_all if img_count[p.code] == 0]    # 이미지 없는 폴더

            # '방금 수집한 것만 생성' 옵션 — 순번 빠른 빈 폴더가 먼저 잡히는 문제 방지
            collect_codes = [c for c in st.session_state.get("collect_codes", [])
                             if status_map.get(c, "none") == "none" and img_count.get(c, 0) > 0]
            only_new = False
            if collect_codes:
                only_new = st.checkbox(
                    f"방금 수집한 {len(collect_codes)}개만 생성", value=True,
                    help="끄면 미작업 전체를 순번 빠른 순서대로 생성합니다.",
                )
            target_pool = (
                [p for p in gen_pool if p.code in collect_codes] if only_new else gen_pool
            )

            st.write(f"미작업 **{len(todo_all)}개** · 생성 가능 **{len(target_pool)}개**")
            if no_img:
                st.caption(
                    f"⚠ 이미지 없는 미작업 {len(no_img)}개는 자동 생성에서 제외됩니다. "
                    "(빈 폴더 — 통이미지를 넣거나 [작업 현황]에서 확인하세요)"
                )
            else:
                st.caption("A에서 수집한 개수만큼 자동으로 맞춰집니다. 필요하면 직접 조절하세요.")

            # 생성 편수 기본값/클램프 (target_pool 변화로 max를 넘으면 에러나므로 보정)
            maxn = max(1, len(target_pool))
            if "gen_n" not in st.session_state:
                st.session_state["gen_n"] = 1
            if st.session_state["gen_n"] > maxn:
                st.session_state["gen_n"] = maxn

            n = st.number_input(
                "이번에 생성할 편수 (1회 N편)", min_value=1, max_value=maxn,
                step=1, key="gen_n", disabled=not target_pool,
            )
            est = int(n) * 200
            st.caption(f"⚠ 예상 과금 약 {est:,}원 (편당 약 200원 가정). 발행은 검토 후 수동입니다.")

            if st.button("✨ 미작업 N편 생성", type="primary",
                         disabled=not target_pool, use_container_width=True):
                targets = target_pool[: int(n)]
                done, fail = 0, []
                with st.status("일괄 생성 시작…", expanded=True) as s:
                    for i, p in enumerate(targets, start=1):
                        s.update(label=f"[{i}/{len(targets)}] '{p.name}' 생성 중…")
                        try:
                            generate_for(p)
                            done += 1
                        except Exception as e:
                            fail.append((p.label, str(e)))
                    s.update(label="일괄 생성 완료", state="complete")
                st.session_state["batch_result"] = {"done": done, "fail": fail}
                st.rerun()   # 상태 갱신(미작업→초안). 결과는 세션에 보관됨

            _render_batch_result()

        st.info(
            "생성된 초안은 [작업 현황] 탭에서 확인하고, [단건 작업] 탭에서 골라 검토·복사 후 "
            "네이버에 직접 발행하세요. 하루 1~2편 분산 발행을 권장합니다."
        )


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
# 탭 ③ 작업 현황 (대시보드)
# ============================================================
def render_worklist(snap: dict) -> None:
    with st.container(border=True):
        st.markdown('<span class="step-badge">📋 작업 현황</span>', unsafe_allow_html=True)
        products = snap["products"]
        if not products:
            st.info("아직 제품이 없습니다. [자동 수집·일괄] 탭에서 수집하거나 폴더를 추가하세요.")
            return

        codes = [p.code for p in products]
        status_map = snap["status"]
        updated_map = snap["updated"]
        img_count = snap["img_count"]

        n_none = sum(1 for c in codes if status_map.get(c, "none") == "none")
        n_draft = sum(1 for c in codes if status_map.get(c) == "draft")
        n_pub = sum(1 for c in codes if status_map.get(c) == "published")

        m1, m2, m3 = st.columns(3)
        m1.metric("⚪ 미작업", n_none)
        m2.metric("🟡 초안", n_draft)
        m3.metric("🟢 발행", n_pub)

        flt = st.radio(
            "보기", ["전체", "미작업", "초안", "발행"],
            horizontal=True, label_visibility="collapsed",
        )
        wanted = {"미작업": "none", "초안": "draft", "발행": "published"}.get(flt)

        rows = []
        for p in products:
            sts = status_map.get(p.code, "none")
            if wanted and sts != wanted:
                continue
            rows.append({
                "순번": p.order,
                "코드": p.code,
                "제품명": p.name,
                "상태": state.STATUS_LABEL.get(sts, sts),
                "이미지": img_count.get(p.code, 0),
                "갱신": updated_map.get(p.code, "-"),
            })

        if not rows:
            st.caption("해당 조건의 제품이 없습니다.")
        else:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("‘미작업’이 다음에 생성할 대상입니다. [자동 수집·일괄] 탭에서 일괄 생성하세요.")


# ============================================================
snap = build_snapshot()   # 제품 스캔/상태/이미지수를 한 번만 계산해 세 탭이 공유

tab_manual, tab_auto, tab_work = st.tabs(
    ["✍️ 단건 작업", "🛰️ 자동 수집·일괄", "📋 작업 현황"]
)
with tab_manual:
    render_manual(snap)
with tab_auto:
    render_auto(snap)
with tab_work:
    render_worklist(snap)
