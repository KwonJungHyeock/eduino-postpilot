"""
Eduino_PostPilot - 담당자용 화면 (Streamlit)
------------------------------------------------------------
제품 선택 -> 통이미지 미리보기 -> [추출+생성] -> 글 검토/복사

실행:
    streamlit run app.py
사내 공유(같은 망의 다른 PC에서 접속):
    streamlit run app.py --server.address 0.0.0.0
"""
import re

import streamlit as st

import config
import image_loader
import vision
import generator

st.set_page_config(page_title="Eduino_PostPilot", layout="wide")
st.title("Eduino_PostPilot")
st.caption("상세페이지 통이미지 → 네이버 블로그 초안 생성 · 검토 후 직접 발행")

# ------------------------------------------------------------
# 사이드바: 제품 선택
# ------------------------------------------------------------
products = image_loader.scan_products()

with st.sidebar:
    st.header("제품 선택")
    st.caption(f"폴더: {config.PRODUCTS_ROOT}")
    if not products:
        st.warning(
            "제품 폴더가 없습니다.\n\n"
            "'[순번] 코드_제품명' 형식 폴더를 만들고 통이미지를 넣은 뒤 새로고침하세요."
        )
        st.stop()
    idx = st.radio(
        "제품 목록",
        range(len(products)),
        format_func=lambda i: products[i].label,
    )

product = products[idx]

# ------------------------------------------------------------
# 본문: 좌(통이미지) / 우(생성 결과)
# ------------------------------------------------------------
col_img, col_out = st.columns([1, 1.3])

with col_img:
    st.subheader("통이미지")
    if product.image_path:
        st.image(str(product.image_path), use_container_width=True)
    else:
        st.error("이 폴더에 통이미지가 없습니다.")
    run = st.button(
        "추출 + 블로그 생성",
        type="primary",
        disabled=not product.image_path,
        use_container_width=True,
    )
    st.caption("⚠ 누르면 OpenAI API 과금이 발생합니다 (1편 약 100~200원).")

with col_out:
    st.subheader("생성 결과")

    if run:
        try:
            with st.spinner("통이미지 분석 중... (추출)"):
                extract_md = vision.extract_from_image(product.image_path)
            with st.spinner("블로그 글 작성 중... (생성)"):
                blog = generator.generate_blog(extract_md, product.name, product.code)
            st.session_state["blog"] = blog
            st.session_state["blog_for"] = product.label
        except Exception as e:
            st.error(f"생성 중 오류가 발생했습니다: {e}")

    blog = st.session_state.get("blog")
    if blog:
        st.caption(f"대상 제품: {st.session_state.get('blog_for', '')}")

        # 이미지 자리 안내 (통이미지에서 캡처해 삽입)
        img_slots = re.findall(r"\[이미지\s*\d+[:：][^\]]*\]", blog)
        if img_slots:
            with st.expander(f"🖼 이미지 자리 {len(img_slots)}곳 — 왼쪽 통이미지에서 캡처해 삽입", expanded=True):
                for s in img_slots:
                    st.write("- " + s)

        st.text_area(
            "블로그 글 (검토·수정 후 복사 → 네이버에 붙여넣기)",
            blog,
            height=460,
            key="blog_edit",
        )

        # 발행 체크리스트
        st.markdown("**발행 체크리스트**")
        c1, c2 = st.columns(2)
        with c1:
            st.checkbox("제목 확인")
            st.checkbox("이미지 자리에 사진 삽입")
        with c2:
            st.checkbox("CTA(쇼핑몰 링크) 확인")
            st.checkbox("태그 입력")
    else:
        st.info("왼쪽에서 제품을 선택하고 [추출 + 블로그 생성]을 누르세요.")
