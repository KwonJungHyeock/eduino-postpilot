"""
Eduino_PostPilot - 쇼핑몰 자동 수집 (Cafe24 스토어프론트)
------------------------------------------------------------
자사 Cafe24 쇼핑몰에서 카테고리별 상품을 긁어와, 각 상품의 상세페이지
이미지(통이미지/상세설명 이미지)를 내려받아 기존 폴더 규칙으로 저장합니다.

    PRODUCTS_ROOT/[순번] 코드_제품명/detail_01.jpg ...

이렇게 저장하면 이후 단계(image_loader → vision → generator → state)가
수동 작업과 '완전히 동일하게' 동작합니다. 즉 이 모듈은 "사람이 폴더를
채우던 일"을 대신할 뿐, 나머지 파이프라인은 그대로 재사용됩니다.

--- 설계 메모 (확장성) -------------------------------------------------
수집원은 ProductSource 인터페이스로 분리돼 있습니다. 지금 구현체는
Cafe24StorefrontSource(공개 HTML 스크래핑)이며, 추후 더 안정적인
Cafe24 OpenAPI 연동이 필요하면 같은 인터페이스로 Cafe24ApiSource를
만들어 갈아끼우면 됩니다. 저장/오케스트레이션 코드는 바뀌지 않습니다.

--- 주의 ----------------------------------------------------------------
* 자사 쇼핑몰만 대상으로 합니다.
* 요청 사이 CRAWL_DELAY_SEC 만큼 쉬어 서버 부하를 주지 않습니다.
* 발행은 여전히 수동입니다. 이 모듈은 '초안 재료'만 모읍니다.

오프라인 파서 자가검증(네트워크 불필요):
    python crawler.py --selftest
"""
from __future__ import annotations

import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urljoin, urlparse

import requests

import config
import image_loader

# HTML에서 닫는 짝이 없는(void) 태그 — prdDetail 범위 추적 시 깊이를 올리지 않음
_VOID_TAGS = {
    "img", "br", "hr", "input", "meta", "link", "source",
    "wbr", "area", "base", "col", "embed", "param", "track",
}

# Cafe24 상세 URL: /product/<slug>/<product_no>/category/<cate_no>/...
_PRODUCT_NO_RE = re.compile(r"/product/[^/]+/(\d+)/")
# 짧은 표준형도 지원: /product/detail.html?product_no=1234
_PRODUCT_NO_QS_RE = re.compile(r"[?&]product_no=(\d+)")

# 디자인 스킨/배너 등 상세설명이 아닌 이미지를 거르는 힌트(폴백 경로에서 사용)
_SKIN_HINTS = ("/web/img/", "/web/upload/category", "/icon", "/btn_", "/banner")


@dataclass
class CrawledProduct:
    product_no: str
    name: str

    @property
    def code(self) -> str:
        """기존 폴더 규칙의 '코드' 자리. Cafe24 상품번호를 그대로 사용(고유·숫자)."""
        return self.product_no


@dataclass
class CollectResult:
    created: list[image_loader.Product] = field(default_factory=list)   # 새로 저장한 제품
    skipped: list[CrawledProduct] = field(default_factory=list)         # 이미 있어 건너뜀
    failed: list[tuple[CrawledProduct, str]] = field(default_factory=list)  # (제품, 사유)


# ============================================================
# 순수 파서 (네트워크 불필요 — 오프라인 단위테스트 가능)
# ============================================================
class _ListParser(HTMLParser):
    """상품목록 페이지에서 (상품번호, 상품명) 쌍을 뽑는다."""

    def __init__(self) -> None:
        super().__init__()
        self.items: list[tuple[str, str]] = []
        self._cur_no: str | None = None
        self._buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        m = _PRODUCT_NO_RE.search(href) or _PRODUCT_NO_QS_RE.search(href)
        if m:
            self._cur_no = m.group(1)
            self._buf = []

    def handle_data(self, data: str) -> None:
        if self._cur_no is not None:
            self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._cur_no is not None:
            name = " ".join("".join(self._buf).split())
            self.items.append((self._cur_no, name))
            self._cur_no = None
            self._buf = []


class _DetailImgParser(HTMLParser):
    """상세설명 영역(#prdDetail) 안의 <img> 주소만 순서대로 모은다.

    상세설명을 못 찾으면(in_detail이 끝까지 False) all_imgs 폴백을 쓴다.
    """

    def __init__(self) -> None:
        super().__init__()
        self.detail_imgs: list[str] = []
        self.all_imgs: list[str] = []
        self._in_detail = False
        self._depth = 0
        self._seen_detail = False

    def _img_src(self, attrs: list[tuple[str, str | None]]) -> str | None:
        d = dict(attrs)
        # 지연로딩(lazy)일 때 실제 주소는 data-src 계열에 들어있다
        return d.get("ec-data-src") or d.get("data-src") or d.get("src")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # <img ... /> 자가닫음도 처리
        self.handle_starttag(tag, attrs)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "img":
            src = self._img_src(attrs)
            if src:
                self.all_imgs.append(src)
                if self._in_detail:
                    self.detail_imgs.append(src)

        if self._in_detail:
            if tag not in _VOID_TAGS:
                self._depth += 1
            return

        if dict(attrs).get("id") == "prdDetail":
            self._in_detail = True
            self._seen_detail = True
            self._depth = 0

    def handle_endtag(self, tag: str) -> None:
        if not self._in_detail or tag in _VOID_TAGS:
            return
        if self._depth == 0:
            self._in_detail = False   # prdDetail 자신의 닫는 태그
        else:
            self._depth -= 1


def _clean_product_name(name: str) -> str:
    """목록에서 따라온 라벨/잡텍스트 정리. (예: 앞에 붙는 '상품명 :' 제거)"""
    name = re.sub(r"^\s*상품\s*명\s*[:：]?\s*", "", name)
    return name.strip()


def parse_product_list(html: str) -> list[CrawledProduct]:
    """목록 HTML → CrawledProduct 리스트(상품번호 기준 중복 제거, 등장순 유지)."""
    p = _ListParser()
    p.feed(html)
    by_no: dict[str, str] = {}
    for no, name in p.items:
        name = _clean_product_name(name)
        # 같은 상품의 썸네일/제목 링크가 여러 번 나올 수 있음 → 이름 있는 쪽을 채택
        if no not in by_no or (not by_no[no] and name):
            by_no[no] = name
    return [CrawledProduct(no, name) for no, name in by_no.items()]


def parse_detail_image_urls(html: str, base_url: str) -> list[str]:
    """상세 HTML → 절대 이미지 URL 리스트(순서 유지, 중복 제거)."""
    p = _DetailImgParser()
    p.feed(html)
    raw = p.detail_imgs if p.detail_imgs else _fallback_filter(p.all_imgs)

    out: list[str] = []
    seen: set[str] = set()
    for src in raw:
        absu = _absolute(src, base_url)
        if absu and absu not in seen:
            seen.add(absu)
            out.append(absu)
    return out


def _fallback_filter(urls: list[str]) -> list[str]:
    """#prdDetail를 못 찾았을 때: 디자인 스킨/배너로 보이는 이미지를 제외."""
    keep = []
    for u in urls:
        low = u.lower()
        if any(h in low for h in _SKIN_HINTS):
            continue
        keep.append(u)
    return keep


def _absolute(src: str, base_url: str) -> str:
    src = src.strip()
    if not src or src.startswith("data:"):
        return ""
    if src.startswith("//"):
        scheme = urlparse(base_url).scheme or "https"
        return f"{scheme}:{src}"
    return urljoin(base_url, src)


# ============================================================
# 수집원 인터페이스 + Cafe24 스토어프론트 구현
# ============================================================
class ProductSource:
    """수집원 추상 인터페이스. 다른 백엔드(예: Cafe24 OpenAPI)도 이 형태로 구현."""

    def list_products(self, category: str, limit: int) -> list[CrawledProduct]:
        raise NotImplementedError

    def fetch_detail_images(self, product: CrawledProduct) -> list[bytes]:
        raise NotImplementedError


class Cafe24StorefrontSource(ProductSource):
    """공개 스토어프론트 HTML을 긁는 구현체."""

    def __init__(self, base: str | None = None) -> None:
        self.base = (base or config.SHOP_BASE).rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.CRAWL_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        })

    # --- 내부 HTTP 헬퍼 ---
    def _get_text(self, url: str) -> str:
        # 목록/상세 HTML은 쇼핑몰 서버 → 짧은 예의 딜레이
        r = self.session.get(url, timeout=config.CRAWL_TIMEOUT)
        r.raise_for_status()
        r.encoding = r.apparent_encoding or r.encoding
        time.sleep(config.CRAWL_HTML_DELAY)
        return r.text

    def _get_bytes(self, url: str) -> tuple[bytes, str]:
        # 이미지는 CDN(cafe24img) → 딜레이 없이(병렬 다운로드에서 호출)
        r = self.session.get(url, timeout=config.CRAWL_TIMEOUT)
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "")

    def _list_url(self, cate_no: str, page: int) -> str:
        return f"{self.base}/product/list.html?cate_no={cate_no}&page={page}"

    def _detail_url(self, product_no: str) -> str:
        # 짧은 표준형 — slug를 몰라도 상품번호만으로 상세에 접근 가능
        return f"{self.base}/product/detail.html?product_no={product_no}"

    def list_products(self, category: str, limit: int) -> list[CrawledProduct]:
        found: list[CrawledProduct] = []
        seen: set[str] = set()
        for page in range(1, config.CRAWL_MAX_PAGES + 1):
            html = self._get_text(self._list_url(category, page))
            page_items = parse_product_list(html)
            new = [p for p in page_items if p.product_no not in seen]
            if not new:
                break  # 더 이상 새 상품이 없으면 마지막 페이지
            for p in new:
                seen.add(p.product_no)
                found.append(p)
                if len(found) >= limit:
                    return found
        return found

    def fetch_detail_images(self, product: CrawledProduct) -> list[bytes]:
        html = self._get_text(self._detail_url(product.product_no))
        urls = parse_detail_image_urls(html, self.base)[: config.CRAWL_MAX_IMAGES]
        if not urls:
            return []

        def fetch_one(u: str) -> bytes | None:
            try:
                data, _ = self._get_bytes(u)
                return data or None
            except requests.RequestException:
                return None  # 이미지 한 장 실패는 건너뜀

        # CDN에서 병렬 다운로드. ex.map은 입력 순서를 보존 → 세로 이어붙임 순서 유지
        workers = max(1, min(config.CRAWL_IMG_WORKERS, len(urls)))
        with ThreadPoolExecutor(max_workers=workers) as ex:
            results = list(ex.map(fetch_one, urls))
        return [d for d in results if d]


# ============================================================
# 오케스트레이션 — 수집해서 PRODUCTS_ROOT에 저장
# ============================================================
_WIN_FORBIDDEN = re.compile(r'[\\/:*?"<>|]')


def _safe_name(name: str) -> str:
    """폴더명에 못 쓰는 문자 제거. '_'는 코드/이름 구분자라 공백으로 치환."""
    name = _WIN_FORBIDDEN.sub(" ", name).replace("_", " ")
    name = " ".join(name.split())
    return name or "제품"


def _ext_for(data: bytes, content_type: str) -> str:
    ct = (content_type or "").lower()
    if "png" in ct:
        return ".png"
    if "webp" in ct:
        return ".webp"
    if "gif" in ct:
        return ".gif"
    if "jpeg" in ct or "jpg" in ct:
        return ".jpg"
    # 시그니처로 보강
    if data[:8].startswith(b"\x89PNG"):
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return ".jpg"


def _existing_codes(root: Path) -> set[str]:
    return {p.code for p in image_loader.scan_products(root)}


def _next_order(root: Path) -> int:
    items = image_loader.scan_products(root)
    return (max((p.order for p in items), default=0)) + 1


def collect_category(
    category: str,
    limit: int,
    *,
    source: ProductSource | None = None,
    root: Path | None = None,
    skip_existing: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> CollectResult:
    """카테고리에서 최대 limit개의 '새' 상품을 수집해 PRODUCTS_ROOT에 저장.

    on_progress: 진행상황 문자열 콜백(Streamlit 상태표시용). 없으면 무시.
    """
    src = source or Cafe24StorefrontSource()
    root = root or config.PRODUCTS_ROOT
    root.mkdir(parents=True, exist_ok=True)

    def log(msg: str) -> None:
        if on_progress:
            on_progress(msg)

    result = CollectResult()
    existing = _existing_codes(root) if skip_existing else set()
    order = _next_order(root)

    log(f"상품 목록 불러오는 중… (카테고리 {category})")
    # 이미 있는 건 빼고 새 상품을 limit개 모으기 위해 넉넉히 가져옴
    candidates = src.list_products(category, limit + len(existing))
    fresh = [p for p in candidates if p.product_no not in existing][:limit]

    if not fresh:
        log("새로 수집할 상품이 없습니다.")
        result.skipped = [p for p in candidates if p.product_no in existing]
        return result

    for i, prod in enumerate(fresh, start=1):
        clean = _safe_name(_clean_product_name(prod.name))   # 라벨 정리 + 폴더명 안전화
        label = clean or f"상품 {prod.product_no}"
        log(f"[{i}/{len(fresh)}] '{label}' 상세이미지 수집 중…")
        try:
            blobs = src.fetch_detail_images(prod)
        except requests.RequestException as e:
            result.failed.append((prod, f"상세 페이지 요청 실패: {e}"))
            continue
        if not blobs:
            result.failed.append((prod, "상세 이미지를 찾지 못함"))
            continue

        folder = root / f"[{order}] {prod.code}_{clean}"
        folder.mkdir(parents=True, exist_ok=True)
        for n, (blob, ct) in enumerate(_with_types(blobs), start=1):
            (folder / f"detail_{n:02d}{_ext_for(blob, ct)}").write_bytes(blob)

        saved = image_loader.Product(
            folder=folder, order=order, code=prod.code, name=clean,
            image_path=image_loader.find_image(folder),
        )
        result.created.append(saved)
        order += 1

    log(f"완료: 신규 {len(result.created)}개 저장, 실패 {len(result.failed)}개")
    return result


def _with_types(blobs: Iterable[bytes]) -> list[tuple[bytes, str]]:
    # fetch_detail_images는 content-type을 버리므로 시그니처 기반으로만 확장자 추정
    return [(b, "") for b in blobs]


# ============================================================
# 오프라인 자가검증
# ============================================================
def _selftest() -> None:
    list_html = """
    <ul class="prdList">
      <li><div class="description">
        <strong class="name">
          <a href="/product/아두이노-우노-r3/1234/category/247/display/1/">아두이노 우노 R3 호환보드</a>
        </strong></div></li>
      <li><div class="description">
        <strong class="name">
          <a href="/product/detail.html?product_no=5678&cate_no=247">초음파센서 HC-SR04</a>
        </strong></div></li>
      <li><div class="description">
        <strong class="name">
          <a href="/product/아두이노-우노-r3/1234/category/247/display/1/">아두이노 우노 R3 호환보드</a>
        </strong></div></li>
    </ul>
    """
    prods = parse_product_list(list_html)
    assert [p.product_no for p in prods] == ["1234", "5678"], prods
    assert prods[0].name == "아두이노 우노 R3 호환보드", prods[0].name

    detail_html = """
    <html><body>
      <div id="header"><img src="/web/img/logo.png"></div>
      <div id="prdDetail" class="cont">
        <p>상세설명</p>
        <div><img ec-data-src="//eduino.cafe24img.com/web/upload/d1.jpg" src="/web/img/blank.gif"></div>
        <img src="https://ecimg.cafe24img.com/web/upload/d2.png"/>
      </div>
      <div id="footer"><img src="/web/img/footer.png"></div>
    </body></html>
    """
    urls = parse_detail_image_urls(detail_html, "https://eduino.cafe24.com")
    assert urls == [
        "https://eduino.cafe24img.com/web/upload/d1.jpg",
        "https://ecimg.cafe24img.com/web/upload/d2.png",
    ], urls

    # #prdDetail가 없을 때 폴백: 스킨/배너 제외하고 업로드 이미지만
    nodetail = """
    <body>
      <img src="/web/img/logo.png">
      <img src="//x/web/upload/big/aa.jpg">
    </body>
    """
    urls2 = parse_detail_image_urls(nodetail, "https://eduino.cafe24.com")
    assert urls2 == ["https://x/web/upload/big/aa.jpg"], urls2

    assert _clean_product_name("상품명 : 아두이노 우노") == "아두이노 우노"
    assert _clean_product_name("상품명아두이노 우노") == "아두이노 우노"
    assert _safe_name("센서/모듈_키트 A:B") == "센서 모듈 키트 A B", _safe_name("센서/모듈_키트 A:B")
    assert _ext_for(b"\x89PNG\r\n", "") == ".png"
    assert _ext_for(b"\xff\xd8\xff", "image/jpeg") == ".jpg"

    print("selftest OK — 파서/유틸 검증 통과")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
        sys.exit(0)
    print("사용법:")
    print("  python crawler.py --selftest        # 오프라인 파서 검증")
    print("  (실수집은 app.py의 '자동 수집' 탭에서 실행)")
