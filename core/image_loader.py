"""
Eduino_PostPilot - 제품 폴더 로더
------------------------------------------------------------
PRODUCTS_ROOT 아래의 제품 폴더를 스캔하고, 폴더명을 파싱하고,
각 폴더의 통이미지 경로를 찾습니다.

폴더명 규칙:  [순번] 코드_제품명
  예) [1] A-1_아두이노 UNO R3 SMD 호환보드
      -> 순번=1, 코드=A-1, 제품명=아두이노 UNO R3 SMD 호환보드
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import config

# [순번] 코드_제품명  (코드는 첫 '_' 전까지, 그 뒤 전부가 제품명)
_PATTERN = re.compile(r"^\[(\d+)\]\s*([^_]+)_(.+)$")

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass
class Product:
    folder: Path
    order: int                 # 순번
    code: str                  # 제품코드 (예: A-1)
    name: str                  # 제품명
    image_path: Path | None    # 통이미지 경로 (없으면 None)

    @property
    def label(self) -> str:
        return f"[{self.order}] {self.code}_{self.name}"


def parse_folder_name(folder_name: str) -> tuple[int, str, str] | None:
    """'[1] A-1_제품명' -> (1, 'A-1', '제품명'). 규칙에 안 맞으면 None."""
    m = _PATTERN.match(folder_name)
    if not m:
        return None
    return int(m.group(1)), m.group(2).strip(), m.group(3).strip()


def find_image(folder: Path) -> Path | None:
    """폴더 안의 첫 번째 이미지 파일 경로."""
    for p in sorted(folder.iterdir()):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            return p
    return None


def scan_products(root: Path | None = None) -> list[Product]:
    """제품 폴더들을 순번순으로 스캔."""
    root = root or config.PRODUCTS_ROOT
    products: list[Product] = []
    if not root.exists():
        return products

    for folder in sorted(root.iterdir()):
        if not folder.is_dir() or folder.name.startswith("_"):
            continue
        parsed = parse_folder_name(folder.name)
        if not parsed:
            continue  # 명명 규칙에 안 맞는 폴더는 건너뜀
        order, code, name = parsed
        products.append(Product(folder, order, code, name, find_image(folder)))

    products.sort(key=lambda p: p.order)
    return products


if __name__ == "__main__":
    items = scan_products()
    if not items:
        print(f"제품 폴더가 없습니다: {config.PRODUCTS_ROOT}")
    for p in items:
        img = p.image_path.name if p.image_path else "(이미지 없음)"
        print(f"순번={p.order} | 코드={p.code} | 제품명={p.name} | 이미지={img}")
