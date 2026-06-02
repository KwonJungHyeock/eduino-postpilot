# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 빌드 명세 — Eduino PostPilot 단독 실행파일(onedir).
빌드:  pyinstaller --noconfirm --clean EduinoPostPilot.spec
결과:  dist/EduinoPostPilot/  (이 폴더 전체를 압축해 배포)
"""
from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = [], [], []

# Streamlit 은 정적 자산(프론트엔드)·서브모듈이 많아 직접 추론이 어려우므로 통째 수집
d, b, h = collect_all("streamlit")
datas += d; binaries += b; hiddenimports += h

# 나머지(pandas/numpy/pyarrow/PIL/openai/tiktoken 등)는 PyInstaller 기본 훅 +
# launcher.py 의 분석 힌트 import 로 자동 포함된다. 여기선 보강용 hiddenimport만.
hiddenimports += [
    "tiktoken_ext", "tiktoken_ext.openai_public",   # tiktoken BPE 등록 플러그인
    "pandas", "numpy", "pyarrow", "PIL.Image",
    "altair", "openai", "tiktoken",
]

# importlib.metadata 로 버전을 조회하는 패키지들 — dist-info 동봉(없으면 런타임 오류)
# copy_metadata 는 import 하지 않고 메타데이터만 복사하므로 안전.
for _pkg in ("streamlit", "openai", "tiktoken", "pandas", "numpy", "pyarrow",
             "altair", "requests", "python-dotenv", "Pillow", "tornado",
             "packaging", "tenacity", "rich", "click", "blinker", "cachetools",
             "gitpython", "pydeck", "protobuf", "watchdog", "toml",
             "validators", "narwhals", "jsonschema"):
    try:
        datas += copy_metadata(_pkg)
    except Exception:
        pass

# 우리 앱 소스/리소스 — Streamlit이 파일로 읽어 실행하므로 실제 파일로 동봉
datas += [
    ("core", "core"),
    ("prompts", "prompts"),
]

a = Analysis(
    ["launcher.py"],
    pathex=["core"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="EduinoPostPilot",
    console=True,            # 검은 서버창 유지(로그·종료). 닫으면 프로그램 종료
    disable_windowed_traceback=False,
    icon="assets/app.ico",   # 실행파일·바로가기 아이콘
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, name="EduinoPostPilot",
)
