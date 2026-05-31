"""
Eduino_PostPilot - 비전 추출
------------------------------------------------------------
분할된 통이미지 조각들을 GPT-5.4 비전에 한 번에 보내,
제품 정보 / 스펙 / 소스코드를 구조화된 마크다운으로 추출합니다.

- 프롬프트: prompts/extract.txt
- 모델/디테일/추론강도: config 에서 설정

단독 실행(추출 테스트, ⚠ 실제 OpenAI API 과금 발생):
    python vision.py "C:\\...\\detail.png"
  -> output/_extract_test.md 저장 + 콘솔 출력
"""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

from openai import OpenAI
from PIL import Image

import config
import image_optimizer


def _client() -> OpenAI:
    """API 키 검증 후 클라이언트 생성 (지연 초기화)."""
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 없습니다. .env를 확인하세요.")
    return OpenAI(api_key=config.OPENAI_API_KEY)


def _load_prompt() -> str:
    p = config.PROMPTS_DIR / "extract.txt"
    if not p.exists():
        raise FileNotFoundError(f"추출 프롬프트가 없습니다: {p}")
    return p.read_text(encoding="utf-8")


def _encode_png(im: Image.Image) -> str:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def extract_from_slices(slices: list[Image.Image]) -> str:
    """조각 이미지 리스트 -> 구조화된 마크다운 추출 결과."""
    system_prompt = _load_prompt()

    # 사용자 메시지 = 안내 텍스트 + 조각 이미지들 (순서대로)
    content: list[dict] = [{
        "type": "text",
        "text": (
            f"아래는 상세페이지를 위에서 아래로 자른 {len(slices)}장의 조각입니다. "
            "순서대로 이어붙여 하나의 페이지로 분석하세요."
        ),
    }]
    for im in slices:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{_encode_png(im)}",
                "detail": config.OPENAI_IMAGE_DETAIL,
            },
        })

    resp = _client().chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        max_completion_tokens=config.MAX_OUTPUT_TOKENS,
        reasoning_effort=config.OPENAI_REASONING_EFFORT,
    )
    return resp.choices[0].message.content or ""


def extract_from_image(path: str | Path) -> str:
    """통이미지 경로 -> 분할 -> 추출."""
    slices = image_optimizer.optimize(path)
    return extract_from_slices(slices)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용법: python vision.py "<통이미지 경로>"')
        sys.exit(1)

    config.validate()
    src_path = sys.argv[1]
    print(f"[추출 시작] {src_path}")
    print(f"  모델={config.OPENAI_MODEL}, detail={config.OPENAI_IMAGE_DETAIL}, "
          f"reasoning={config.OPENAI_REASONING_EFFORT}")

    result = extract_from_image(src_path)

    out_path = config.OUTPUT_DIR / "_extract_test.md"
    out_path.write_text(result, encoding="utf-8")

    print("\n" + "=" * 60)
    print(result)
    print("=" * 60)
    print(f"\n[저장] {out_path}")
