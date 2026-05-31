"""
Eduino_PostPilot - 중앙 설정
------------------------------------------------------------
코드는 core/ 안에 있고, 입력/출력/키는 프로젝트 루트에 둡니다.
경로는 모두 자동 계산되므로 사용자가 직접 만질 필요가 없습니다.
"""
import os
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
# OpenAI
# ------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
MAX_OUTPUT_TOKENS = 4000
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")
OPENAI_IMAGE_DETAIL = os.getenv("OPENAI_IMAGE_DETAIL", "high")
GEN_MAX_TOKENS = int(os.getenv("GEN_MAX_TOKENS", "6000"))

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
