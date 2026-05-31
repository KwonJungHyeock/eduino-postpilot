"""
Eduino_PostPilot - 블로그 글 생성
------------------------------------------------------------
비전 추출 결과(구조화 마크다운)를 입력받아,
SEO 최적화된 네이버 블로그 글을 생성합니다.

- 프롬프트: prompts/blog.txt
- 쇼핑몰 CTA 정보: config.SHOP_NAME / config.SHOP_URL

단독 실행(생성 테스트, ⚠ 실제 OpenAI API 과금 발생):
    python generator.py
  -> output/_extract_test.md 를 읽어 블로그 생성
  -> output/_blog_test.md 저장 + 콘솔 출력
"""
from __future__ import annotations

import sys
from pathlib import Path

from openai import OpenAI

import config


def _client() -> OpenAI:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 없습니다. .env를 확인하세요.")
    return OpenAI(api_key=config.OPENAI_API_KEY)


def _load_prompt() -> str:
    p = config.PROMPTS_DIR / "blog.txt"
    if not p.exists():
        raise FileNotFoundError(f"생성 프롬프트가 없습니다: {p}")
    return p.read_text(encoding="utf-8")


def generate_blog(
    extract_md: str,
    product_name: str | None = None,
    product_code: str | None = None,
) -> str:
    """추출 마크다운 -> SEO 블로그 글(마크다운)."""
    system_prompt = _load_prompt()

    meta_lines = [
        f"쇼핑몰 이름: {config.SHOP_NAME}",
        f"쇼핑몰 URL: {config.SHOP_URL}",
    ]
    if product_name:
        meta_lines.append(f"제품명: {product_name}")
    if product_code:
        meta_lines.append(f"제품코드: {product_code}")

    user_msg = (
        "\n".join(meta_lines)
        + "\n\n아래는 이 제품 상세페이지에서 추출한 정보입니다. "
        "이 정보만 사용해 블로그 글을 작성하세요.\n\n"
        "----- 추출 정보 시작 -----\n"
        + extract_md
        + "\n----- 추출 정보 끝 -----"
    )

    resp = _client().chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        max_completion_tokens=config.GEN_MAX_TOKENS,
        reasoning_effort=config.OPENAI_REASONING_EFFORT,
    )
    return resp.choices[0].message.content or ""


if __name__ == "__main__":
    config.validate()

    extract_path = config.OUTPUT_DIR / "_extract_test.md"
    if not extract_path.exists():
        print(f"추출 결과가 없습니다: {extract_path}")
        print("먼저 vision.py로 추출을 실행하세요.")
        sys.exit(1)

    extract_md = extract_path.read_text(encoding="utf-8")
    print(f"[생성 시작] 입력={extract_path.name}, 모델={config.OPENAI_MODEL}")
    print(f"  쇼핑몰: {config.SHOP_NAME} ({config.SHOP_URL})")

    blog = generate_blog(extract_md)

    out_path = config.OUTPUT_DIR / "_blog_test.md"
    out_path.write_text(blog, encoding="utf-8")

    print("\n" + "=" * 60)
    print(blog)
    print("=" * 60)
    print(f"\n[저장] {out_path}")
