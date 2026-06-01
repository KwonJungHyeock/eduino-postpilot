"""
Eduino_PostPilot - 메인 화면 (Streamlit)
------------------------------------------------------------
탭 구성
  🛰️ 수집     : 쇼핑몰 카테고리에서 제품을 받아오기만(폴더 채움)
  ✍️ 생성     : 목록에서 여러 제품을 골라 한 번에 생성 → 검토·복사·발행
  📋 작업 현황 : 작업됨/미작업 한눈에 보고 다음 할 일 구분

발행은 여전히 사람이 검토 후 수동으로 합니다(어뷰징 회피). 자동화는 '초안 재료
수집'과 '초안 생성'까지입니다. 실행은 루트의 run.bat 으로 합니다.
"""
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

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
# 공유 스냅샷 — 제품 스캔/상태/이미지수를 한 번만 계산해 세 탭이 공유
#   (Streamlit은 매 rerun마다 탭 3개 본문을 모두 실행하므로, 따로 스캔하면
#    파일시스템 조회가 3중복으로 일어남. 한 번만 모아 전달해 속도 확보.)
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
# 탭 ✍️ 생성 — 목록에서 선택해 생성 + 검토·복사·발행
# ============================================================
def render_generate(snap: dict) -> None:
    products = snap["products"]
    if not products:
        st.info(
            f"아직 제품이 없습니다. [🛰️ 수집] 탭에서 쇼핑몰에서 받아오거나, "
            f"`{config.PRODUCTS_ROOT}` 에 '[순번] 코드_제품명' 폴더를 직접 넣으세요."
        )
        return

    status_map = snap["status"]
    img_count = snap["img_count"]
    left, right = st.columns([1, 1.25], gap="large")

    # ---- 왼쪽: 목록에서 선택 → 생성 ----
    with left:
        with st.container(border=True):
            st.markdown('<span class="step-badge">① 생성할 제품 선택</span>', unsafe_allow_html=True)
            only_todo = st.checkbox("미작업만 보기", value=True)
            view = [p for p in products
                    if not only_todo or status_map.get(product_key(p), "none") == "none"]

            if not view:
                st.success("미작업 제품이 없습니다. 모두 생성됐어요! (전체 보기를 끄면 다시 보입니다)")
            else:
                rows = [{
                    "선택": False,
                    "순번": p.order,
                    "코드": p.code,
                    "제품명": p.name,
                    "상태": state.STATUS_LABEL.get(status_map.get(product_key(p), "none"), ""),
                    "이미지": img_count.get(product_key(p), 0),
                } for p in view]
                edited = st.data_editor(
                    rows, hide_index=True, use_container_width=True,
                    column_config={"선택": st.column_config.CheckboxColumn(required=False)},
                    disabled=["순번", "코드", "제품명", "상태", "이미지"],
                    key="gen_select",
                )
                selected = [view[i] for i, r in enumerate(edited) if r["선택"]]
                gen_targets = [p for p in selected if img_count.get(product_key(p), 0) > 0]
                no_img_sel = [p for p in selected if img_count.get(product_key(p), 0) == 0]

                est = len(gen_targets) * 200
                st.caption(
                    f"선택 {len(selected)}개 · 생성 대상 {len(gen_targets)}개 · "
                    f"예상 과금 약 {est:,}원 (편당 약 200원). 동시 {config.GEN_WORKERS}개 병렬."
                )
                if no_img_sel:
                    st.caption(f"⚠ 이미지 없는 {len(no_img_sel)}개는 제외됩니다.")

                if st.button(f"✨ 선택한 {len(gen_targets)}개 생성", type="primary",
                             disabled=not gen_targets, use_container_width=True):
                    _run_batch(gen_targets)
                    st.rerun()   # 상태 갱신. 결과는 세션에 보관됨

            _render_batch_result()

    # ---- 오른쪽: 검토 · 복사 · 발행 ----
    with right:
        with st.container(border=True):
            st.markdown('<span class="step-badge">② 검토 · 복사 · 발행</span>', unsafe_allow_html=True)
            reviewable = [p for p in products
                          if status_map.get(product_key(p), "none") in ("draft", "published")]
            if not reviewable:
                st.info("생성된 초안이 없습니다. 왼쪽에서 제품을 골라 생성하세요.")
            else:
                def rfmt(i: int) -> str:
                    p = reviewable[i]
                    return f"{state.STATUS_LABEL.get(status_map.get(product_key(p), 'none'), '')}  {p.label}"

                ridx = st.selectbox("검토할 제품", range(len(reviewable)), format_func=rfmt)
                product = reviewable[ridx]
                blog, path = load_draft(product)
                if not blog:
                    st.warning("초안 파일을 찾을 수 없습니다. 다시 생성해 주세요.")
                else:
                    if path:
                        st.caption(f"💾 저장됨: {path}")
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
        state.set_status(product_key(product), product.name, "published")
        st.success("발행 완료로 표시했습니다. (목록 상태가 🟢로 바뀝니다)")


# ============================================================
# 탭 🛰️ 수집 — 쇼핑몰에서 받아오기만
# ============================================================
def render_collect(snap: dict) -> None:
    left, right = st.columns([1, 1], gap="large")

    with left:
        with st.container(border=True):
            st.markdown('<span class="step-badge">쇼핑몰에서 자동 수집</span>', unsafe_allow_html=True)
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
                    st.rerun()   # 새 폴더 반영해 스냅샷 갱신(결과는 세션에 보관됨)
                except Exception as e:
                    st.session_state["collect_result"] = {"error": str(e)}

            _render_collect_result()

    with right:
        with st.container(border=True):
            st.markdown('<span class="step-badge">수집 현황</span>', unsafe_allow_html=True)
            products = snap["products"]
            status_map = snap["status"]
            todo = sum(1 for p in products if status_map.get(product_key(p), "none") == "none")
            st.metric("수집된 제품(폴더)", len(products))
            st.metric("그중 미작업", todo)
            st.info(
                "수집은 폴더만 채웁니다. 생성·검토·발행은 [✍️ 생성] 탭에서 하세요. "
                "발행은 검토 후 수동, 하루 1~2편 분산을 권장합니다."
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
            st.info("아직 제품이 없습니다. [🛰️ 수집] 탭에서 수집하거나 폴더를 추가하세요.")
            return

        status_map = snap["status"]
        updated_map = snap["updated"]
        img_count = snap["img_count"]
        keys = [product_key(p) for p in products]

        n_none = sum(1 for k in keys if status_map.get(k, "none") == "none")
        n_draft = sum(1 for k in keys if status_map.get(k) == "draft")
        n_pub = sum(1 for k in keys if status_map.get(k) == "published")

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
            k = product_key(p)
            sts = status_map.get(k, "none")
            if wanted and sts != wanted:
                continue
            rows.append({
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
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("‘미작업’이 다음에 생성할 대상입니다. [✍️ 생성] 탭에서 골라 생성하세요.")


# ============================================================
snap = build_snapshot()   # 제품 스캔/상태/이미지수를 한 번만 계산해 세 탭이 공유

tab_collect, tab_gen, tab_work = st.tabs(
    ["🛰️ 수집", "✍️ 생성", "📋 작업 현황"]
)
with tab_collect:
    render_collect(snap)
with tab_gen:
    render_generate(snap)
with tab_work:
    render_worklist(snap)
