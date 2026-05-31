# Eduino_PostPilot

상세페이지 통이미지를 분석해 **네이버 블로그 초안을 자동 생성**하는 도구입니다.
에듀이노 제품 상세페이지(아두이노 실습 가이드가 담긴 긴 통이미지)를 넣으면,
SEO에 최적화된 블로그 글 초안을 만들어 검토 후 직접 발행할 수 있게 합니다.

> 운영 방법·발행 주기 등 실제 사용 수칙은 OPERATION_GUIDE.md 를 참고하세요.

---

## 1. 기획 배경 · 목적

에듀이노는 아두이노 기반 교육용 제품을 판매하며, 제품마다 실습 코드·가이드가 담긴
상세페이지(통이미지)를 운영합니다. 이 자산을 블로그 콘텐츠로 재활용해 네이버 검색 노출을 늘리고,
콘텐츠를 꾸준히 활성화하며, 에듀이노 쇼핑몰로 고객을 유입하는 것이 목표입니다.
통이미지 입력만으로 초안이 나오도록 자동화했습니다.

---

## 2. 핵심 설계 결정

| 항목 | 선택 | 이유 |
|---|---|---|
| 발행 방식 | 반자동 (생성 자동 + 사람 검토 후 수동 발행) | 네이버는 자동 발행을 어뷰징으로 탐지해 저품질·제재 위험 |
| LLM | OpenAI GPT-5.4 | 비용/품질 균형, 한글+코드 이미지 인식에 적합 |
| 이미지 처리 | 폭 정규화 + 세로 분할 | 긴 통이미지의 작은 글씨·소스코드 인식률 확보 |
| 글 서식 | 마크다운 강조 기호 제거 | 네이버 에디터 비호환 + AI 양산형 티 제거 |
| 이미지 삽입 | 자리표시 방식 [이미지 N] | 글에는 자리만, 검토 후 사진 삽입 |
| 실행 | run.bat 더블클릭 (개인 PC 전용) | 명령어 없이 바로 실행 |

---

## 3. 폴더 구조

```
eduino-postpilot/
├─ run.bat               ▶ 더블클릭 실행
├─ .env                  🔑 API 키 (직접 생성, git 제외)
├─ Product_eduino/       📁 제품 통이미지 넣는 곳 (git 제외)
├─ output/               📁 생성 결과 .md (git 제외)
├─ core/                 프로그램 코드
│   ├─ app.py            화면 (Streamlit)
│   ├─ config.py         설정
│   ├─ image_loader.py   제품 폴더 스캔
│   ├─ image_optimizer.py 통이미지 분할
│   ├─ vision.py         GPT-5.4 추출
│   ├─ generator.py      블로그 생성
│   └─ state.py          발행 상태
├─ prompts/              extract.txt · blog.txt
├─ .streamlit/config.toml  테마/서버 설정
├─ README.md · OPERATION_GUIDE.md · requirements.txt · .gitignore
```

---

## 4. 최초 설치 (기기당 1회)

요구사항: Windows 11, Python 3.11+

```cmd
:: 1) 가상환경 생성·활성화
python -m venv .venv
.venv\Scripts\activate

:: 2) 패키지 설치
pip install -r requirements.txt

:: 3) .env 생성 후 키 입력
copy .env.example .env
notepad .env
```

.env 입력값:

| 키 | 설명 |
|---|---|
| OPENAI_API_KEY | OpenAI API 키 (앞에 sk- 한 번만) |
| OPENAI_MODEL | 기본 gpt-5.4 |
| SHOP_URL | (선택) 기본값 https://eduino.kr/index.html |
| PRODUCTS_ROOT | (선택) 비우면 Product_eduino 자동 사용 |

설치 점검:
```cmd
cd core
python -c "import config; config.validate()"
cd ..
```

---

## 5. 사용법

### 제품 준비
`Product_eduino` 아래에 `[순번] 코드_제품명` 형식 폴더를 만들고 통이미지를 넣습니다.
```
Product_eduino\[1] A-1_아두이노 UNO R3 SMD 호환보드\detail.png
```

### 실행
`run.bat` 더블클릭 → 잠시 후 브라우저에 화면이 열립니다.
(검은 창은 서버이므로 켜둔 채로 두고, 닫으면 종료됩니다.)

### 작업 흐름
1. 왼쪽에서 제품 선택 → 통이미지 확인
2. [블로그 글 생성하기] 클릭 (OpenAI 과금)
3. 제목 후보 선택, 본문·메타·태그 원클릭 복사
4. 관련 링크 빈칸 채우기
5. 네이버에 붙여넣고 [이미지 N] 자리에 사진 삽입 → 발행
6. [발행 완료로 표시] 클릭 → 상태 갱신

---

## 6. 비용 · 보안

| 항목 | 내용 |
|---|---|
| 비용 | 1편 약 150~250원 (통이미지 길이·모델에 따라) |
| API 키 | .env 에만 보관, git 제외. 노출 시 즉시 재발급 |
| 결과 | output 폴더에 자동 저장 |

---

## 7. 향후 고도화 후보

- 섹션 자동 크롭 (이미지 자리별 사진 자동 분리)
- 네이버 검색광고 API (실검색량 기반 키워드)
- 여러 기기 동기화 (필요 시 Docker 전환)
