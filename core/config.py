"""
Eduino_PostPilot - 중앙 설정
------------------------------------------------------------
코드는 core/ 안에 있고, 입력/출력/키는 프로젝트 루트에 둡니다.
경로는 모두 자동 계산되므로 사용자가 직접 만질 필요가 없습니다.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# ------------------------------------------------------------
# 경로 (core/ 의 부모 = 프로젝트 루트)
# ------------------------------------------------------------
CORE_DIR = Path(__file__).resolve().parent     # .../eduino-postpilot/core
PROJECT_ROOT = CORE_DIR.parent                  # .../eduino-postpilot

# .env 는 프로젝트 루트에서 로드
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"        # SQLite 등
OUTPUT_DIR = PROJECT_ROOT / "output"    # 생성 결과
PROMPTS_DIR = PROJECT_ROOT / "prompts"  # 프롬프트 템플릿

# 상세페이지 통이미지 루트
#   - .env에 PRODUCTS_ROOT 값이 있으면 그것을 사용
#   - 비어있으면 프로젝트 루트의 Product_eduino 폴더를 자동 사용
PRODUCTS_ROOT = Path(os.getenv("PRODUCTS_ROOT") or (PROJECT_ROOT / "Product_eduino"))

# ------------------------------------------------------------
# 사용자별 설정 저장 (최초 1회 키 입력 → 이 PC에 저장 → 다음부터 자동)
#   위치: 사용자 홈 폴더의 .eduino_postpilot/config.json
#   (앱 폴더와 분리 → 프로그램을 옮기거나 업데이트해도 키가 유지됨)
# ------------------------------------------------------------
USER_CONFIG_DIR = Path.home() / ".eduino_postpilot"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.json"


def load_saved_config() -> dict:
    """이 PC에 저장된 설정(키·모델)을 읽어옵니다. 없으면 빈 dict."""
    try:
        return json.loads(USER_CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


_saved = load_saved_config()

# ------------------------------------------------------------
# OpenAI
#   키/모델 우선순위: 환경변수(.env) > 이 PC에 저장된 값 > 기본값
# ------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or _saved.get("OPENAI_API_KEY") or None
OPENAI_MODEL = os.getenv("OPENAI_MODEL") or _saved.get("OPENAI_MODEL") or "gpt-5.4"


def save_api_key(key: str, model: str | None = None) -> None:
    """입력받은 키(와 선택적 모델)를 이 PC에 저장하고, 실행 중인 값도 즉시 갱신.
    클라이언트가 호출 시점에 config.OPENAI_API_KEY를 읽으므로 재시작 없이 바로 적용됩니다."""
    global OPENAI_API_KEY, OPENAI_MODEL
    key = (key or "").strip()
    cfg = load_saved_config()
    cfg["OPENAI_API_KEY"] = key
    if model:
        cfg["OPENAI_MODEL"] = model.strip()
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    USER_CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        USER_CONFIG_FILE.chmod(0o600)   # 가능한 OS에서는 본인만 읽기
    except Exception:
        pass
    OPENAI_API_KEY = key
    os.environ["OPENAI_API_KEY"] = key
    if model:
        OPENAI_MODEL = model.strip()


def clear_api_key() -> None:
    """저장된 키를 삭제(초기화)합니다. 다음 실행 시 다시 입력 화면이 뜹니다."""
    global OPENAI_API_KEY
    cfg = load_saved_config()
    cfg.pop("OPENAI_API_KEY", None)
    try:
        USER_CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    OPENAI_API_KEY = None
    os.environ.pop("OPENAI_API_KEY", None)


def has_api_key() -> bool:
    return bool(OPENAI_API_KEY)


def mask_key(key: str | None = None) -> str:
    """화면 표시용 마스킹: sk-abcd…WXYZ 형태."""
    k = key or OPENAI_API_KEY or ""
    return f"{k[:7]}…{k[-4:]}" if len(k) > 12 else "****"
MAX_OUTPUT_TOKENS = 4000
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")
OPENAI_IMAGE_DETAIL = os.getenv("OPENAI_IMAGE_DETAIL", "high")
GEN_MAX_TOKENS = int(os.getenv("GEN_MAX_TOKENS", "6000"))
# 일괄 생성 동시 처리 수(스레드). API 호출은 I/O 대기라 병렬로 벽시계 시간 단축.
# 너무 높이면 OpenAI 레이트리밋/순간비용↑. 기본 3.
GEN_WORKERS = int(os.getenv("GEN_WORKERS", "3"))

# ------------------------------------------------------------
# 자사 / 입점사 구분
#   제품코드 맨 앞 글자가 아래 목록이면 '자사제품'(블로그 작성 대상),
#   그 외(예: P-AY15)는 '입점사 제품'으로 보고 기본 목록에서 숨깁니다.
#   .env 의 OWN_CODE_PREFIXES="A,B,C,D,E" 로 조정할 수 있습니다.
# ------------------------------------------------------------
OWN_CODE_PREFIXES = tuple(
    p.strip().upper()
    for p in os.getenv("OWN_CODE_PREFIXES", "A,B,C,D,E").split(",")
    if p.strip()
)


def is_own_code(code: str | None) -> bool:
    """제품코드가 자사제품(블로그 작성 대상)인지. 맨 앞 글자로 판별."""
    if not code:
        return False
    return code.strip()[:1].upper() in OWN_CODE_PREFIXES

# ------------------------------------------------------------
# 쇼핑몰 (블로그 CTA)
# ------------------------------------------------------------
SHOP_NAME = os.getenv("SHOP_NAME", "에듀이노")
SHOP_URL = os.getenv("SHOP_URL", "https://eduino.kr/index.html")

# ------------------------------------------------------------
# 관련 링크 (블로그 하단, 직접 입력방식)
#   - LINK_MANUAL : 제품마다 다름 → 빈칸으로 표시(직접 입력)
#   - LINK_FIXED  : 고정 채널 → 자동으로 채워짐
# ------------------------------------------------------------
LINK_MANUAL = [
    "에듀이노 제품 구매하기",
    "에듀이노 관련 추천 제품",
]
LINK_FIXED = {
    "에듀이노 공식몰": "https://eduino.kr/index.html",
    "에듀이노 카페": "https://cafe.naver.com/arduinostory",
    "에듀이노 인스타그램": "https://www.instagram.com/eduino_lab/",
    "에듀이노 유튜브": "https://www.youtube.com/@eduino2822",
}

# ------------------------------------------------------------
# 이미지 전처리
# ------------------------------------------------------------
IMAGE_TARGET_WIDTH = 1280
IMAGE_SLICE_HEIGHT = 1500
IMAGE_SLICE_OVERLAP = 100

# ------------------------------------------------------------
# 크롤링 (Cafe24 스토어프론트 자동 수집)
#   - 쇼핑몰이 Cafe24 기반이라 표준 URL로 상품목록/상세를 수집합니다.
#   - 지금은 스토어프론트 HTML 스크래핑. 추후 Cafe24 OpenAPI 소스로 교체 가능
#     (crawler.py 의 ProductSource 인터페이스만 갈아끼우면 됨).
#   - ⚠ 자사 쇼핑몰만 대상으로, HTML 요청에는 짧은 간격(CRAWL_HTML_DELAY)을 둡니다.
#   - 균형 모드: 쇼핑몰 서버(목록/상세 HTML)에는 0.5초 예의 딜레이, 이미지는 CDN
#     (cafe24img)에서 받으므로 딜레이 없이 병렬 다운로드해 속도를 확보합니다.
# ------------------------------------------------------------
SHOP_BASE = os.getenv("SHOP_BASE", "https://eduino.cafe24.com").rstrip("/")
CRAWL_USER_AGENT = os.getenv(
    "CRAWL_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)
CRAWL_HTML_DELAY = float(os.getenv("CRAWL_HTML_DELAY", "0.5"))  # 목록/상세 HTML 요청 사이 대기(초)
CRAWL_IMG_WORKERS = int(os.getenv("CRAWL_IMG_WORKERS", "8"))    # 상세이미지 병렬 다운로드 수
CRAWL_TIMEOUT = int(os.getenv("CRAWL_TIMEOUT", "20"))          # HTTP 타임아웃(초)
CRAWL_MAX_PAGES = int(os.getenv("CRAWL_MAX_PAGES", "20"))      # 목록 페이지 탐색 상한
CRAWL_MAX_IMAGES = int(os.getenv("CRAWL_MAX_IMAGES", "25"))    # 상세이미지 다운로드 상한/제품
# (구) CRAWL_DELAY_SEC — 하위호환. HTML 딜레이는 이제 CRAWL_HTML_DELAY 사용
CRAWL_DELAY_SEC = float(os.getenv("CRAWL_DELAY_SEC", "0.5"))

# 카테고리 프리셋(선택): "표시이름": cate_no.  비워두면 화면에서 번호 직접 입력.
CRAWL_CATEGORIES: dict[str, int] = {}

STATE_DB = DATA_DIR / "state.db"

# 폴더 자동 생성
for _d in (DATA_DIR, OUTPUT_DIR, PROMPTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def validate() -> None:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY가 비어 있습니다. .env 파일에 키를 입력했는지 확인하세요.")
    if not PRODUCTS_ROOT.exists():
        print(f"[경고] PRODUCTS_ROOT 경로가 아직 없습니다: {PRODUCTS_ROOT}")
    print(f"[OK] 모델={OPENAI_MODEL}, 이미지 루트={PRODUCTS_ROOT}")
