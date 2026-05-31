"""
Eduino_PostPilot - 중앙 설정
------------------------------------------------------------
경로, 모델, 이미지 전처리 파라미터를 한 곳에서 관리합니다.
다른 모듈은 `import config` 로 이 값들을 가져다 씁니다.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env 로드 (없으면 환경변수/기본값 사용)
load_dotenv()

# ------------------------------------------------------------
# 경로
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"          # SQLite 등 로컬 데이터
OUTPUT_DIR = BASE_DIR / "output"      # 생성된 블로그 원고(.md)
PROMPTS_DIR = BASE_DIR / "prompts"    # 프롬프트 템플릿

# 상세페이지 통이미지 루트
#   - .env에 PRODUCTS_ROOT 값이 있으면 그것을 사용 (외부 폴더로 옮길 때)
#   - 비어있거나 없으면 프로젝트 내부 Product_eduino 폴더를 자동 사용
PRODUCTS_ROOT = Path(os.getenv("PRODUCTS_ROOT") or (BASE_DIR / "Product_eduino"))

# ------------------------------------------------------------
# OpenAI
# ------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")
# 정확한 모델 슬러그는 https://platform.openai.com/docs/models 에서 확인
MAX_OUTPUT_TOKENS = 4000   # 출력 상한 (max_completion_tokens, 비용 폭주 방지)
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")  # 추론 강도(none/minimal/low/medium/high) - low=비용 절감
OPENAI_IMAGE_DETAIL = os.getenv("OPENAI_IMAGE_DETAIL", "high")         # 이미지 디테일(low/high) - high=작은 글씨/코드 인식
GEN_MAX_TOKENS = int(os.getenv("GEN_MAX_TOKENS", "6000"))             # 블로그 글 생성 출력 상한 (추출보다 길게)

# ------------------------------------------------------------
# 쇼핑몰 (블로그 CTA / 고객 유입용)
# ------------------------------------------------------------
SHOP_NAME = os.getenv("SHOP_NAME", "에듀이노")
SHOP_URL = os.getenv("SHOP_URL", "https://eduino.kr")   # ⚠ 실제 쇼핑몰 주소로 .env에서 교체하세요

# ------------------------------------------------------------
# 이미지 전처리  (Step 2에서 실제 샘플 보고 튜닝 예정)
# ------------------------------------------------------------
IMAGE_TARGET_WIDTH = 1280    # 폭 정규화 기준(px)
IMAGE_SLICE_HEIGHT = 1500    # 세로 분할 높이(px)
IMAGE_SLICE_OVERLAP = 100    # 분할 경계 겹침(px) - 코드/문장 잘림 방지

# ------------------------------------------------------------
# 상태 DB
# ------------------------------------------------------------
STATE_DB = DATA_DIR / "state.db"

# ------------------------------------------------------------
# 폴더 자동 생성
# ------------------------------------------------------------
for _d in (DATA_DIR, OUTPUT_DIR, PROMPTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def validate() -> None:
    """필수 설정 점검. 문제가 있으면 명확한 메시지와 함께 예외 발생."""
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY가 비어 있습니다. .env 파일에 키를 입력했는지 확인하세요."
        )
    if not PRODUCTS_ROOT.exists():
        print(f"[경고] PRODUCTS_ROOT 경로가 아직 없습니다: {PRODUCTS_ROOT}")
    print(f"[OK] 모델={OPENAI_MODEL}, 이미지 루트={PRODUCTS_ROOT}")
