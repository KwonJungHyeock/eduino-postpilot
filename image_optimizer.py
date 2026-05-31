"""
Eduino_PostPilot - 통이미지 전처리
------------------------------------------------------------
긴 상세페이지 통이미지를 비전 API에 넣기 좋게 가공합니다.
  1) 폭 정규화 : 너무 크면 종횡비 유지하며 축소 (작으면 그대로, 업스케일 안 함)
  2) 세로 분할 : 일정 높이로 자르되 경계를 겹쳐(overlap) 코드/문장 잘림 방지

단독 실행(분할 미리보기):
    python image_optimizer.py "C:\\...\\detail.png"
  -> output/_slice_test/ 에 조각 png 저장 + 조각 정보 출력
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

import config


def load_image(path: str | Path) -> Image.Image:
    """이미지를 열고 RGB로 통일."""
    im = Image.open(path)
    if im.mode != "RGB":
        im = im.convert("RGB")
    return im


def normalize_width(im: Image.Image, target_width: int | None = None) -> Image.Image:
    """폭이 target보다 크면 종횡비 유지하며 축소. 작으면 그대로(업스케일 안 함)."""
    target_width = target_width or config.IMAGE_TARGET_WIDTH
    w, h = im.size
    if w <= target_width:
        return im
    new_h = round(h * target_width / w)
    return im.resize((target_width, new_h), Image.LANCZOS)


def slice_vertical(
    im: Image.Image,
    slice_height: int | None = None,
    overlap: int | None = None,
) -> list[Image.Image]:
    """세로로 분할. 경계에서 overlap만큼 겹쳐 코드/문장이 끊기지 않게 함."""
    slice_height = slice_height or config.IMAGE_SLICE_HEIGHT
    overlap = overlap or config.IMAGE_SLICE_OVERLAP
    w, h = im.size
    if h <= slice_height:
        return [im]

    step = slice_height - overlap
    slices: list[Image.Image] = []
    top = 0
    while top < h:
        bottom = min(top + slice_height, h)
        slices.append(im.crop((0, top, w, bottom)))
        if bottom >= h:
            break
        top += step
    return slices


def optimize(path: str | Path) -> list[Image.Image]:
    """통이미지 경로 -> [폭정규화 -> 세로분할] -> 조각 이미지 리스트."""
    im = load_image(path)
    im = normalize_width(im)
    return slice_vertical(im)


def save_slices(
    slices: list[Image.Image],
    out_dir: str | Path,
    prefix: str = "slice",
) -> list[Path]:
    """조각을 png로 저장 (분할 품질을 눈으로 확인하는 용도)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i, s in enumerate(slices, start=1):
        p = out_dir / f"{prefix}_{i:02d}.png"
        s.save(p)
        paths.append(p)
    return paths


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용법: python image_optimizer.py "<통이미지 경로>"')
        sys.exit(1)

    src_path = sys.argv[1]
    pieces = optimize(src_path)
    out = config.OUTPUT_DIR / "_slice_test"
    saved = save_slices(pieces, out)

    print(f"원본      : {src_path}")
    print(f"조각 수   : {len(pieces)}")
    for p in saved:
        ww, hh = Image.open(p).size
        print(f"  - {p.name}: {ww}x{hh}")
    print(f"저장 위치 : {out}")
