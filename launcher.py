"""
Eduino PostPilot - 실행파일(.exe) 진입점
------------------------------------------------------------
PyInstaller로 패키징할 때의 시작점입니다. Streamlit 서버를 띄우고
core/app.py 를 실행합니다. 테마/서버 옵션은 환경변수로 고정해
어느 폴더에서 실행해도 동일하게 동작합니다.

일반(파이썬) 실행은 기존처럼 run.bat / `streamlit run core/app.py` 를 쓰세요.
"""
import os
import sys
from pathlib import Path


def _res(*parts: str) -> str:
    """번들(또는 소스) 안의 리소스 경로. PyInstaller면 _MEIPASS 기준."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def _suppress_first_run_prompt() -> None:
    """Streamlit 최초 실행 시 뜨는 '이메일 입력' 프롬프트를 억제.
    (없으면 새 PC의 콘솔에서 입력 대기로 멈춤) credentials 파일을 미리 만든다."""
    try:
        cred = Path.home() / ".streamlit" / "credentials.toml"
        if not cred.exists():
            cred.parent.mkdir(parents=True, exist_ok=True)
            cred.write_text('[general]\nemail = ""\n', encoding="utf-8")
    except Exception:
        pass


# core/ 의 모듈(config, vision, ...)을 'import config' 식으로 찾도록 경로 추가
sys.path.insert(0, _res("core"))
_suppress_first_run_prompt()

# 테마·서버 옵션을 환경변수로 고정 (.streamlit/config.toml 경로 의존 제거)
_ENV_DEFAULTS = {
    "STREAMLIT_GLOBAL_DEVELOPMENT_MODE": "false",
    "STREAMLIT_SERVER_HEADLESS": "false",          # 준비되면 브라우저 자동 오픈
    "STREAMLIT_SERVER_FILE_WATCHER_TYPE": "none",  # 패키징 환경에서 와처 비활성
    "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
    "STREAMLIT_THEME_BASE": "dark",
    "STREAMLIT_THEME_PRIMARY_COLOR": "#f0584d",
    "STREAMLIT_THEME_BACKGROUND_COLOR": "#0a0e16",
    "STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR": "#141b27",
    "STREAMLIT_THEME_TEXT_COLOR": "#e6edf3",
}
for k, v in _ENV_DEFAULTS.items():
    os.environ.setdefault(k, v)


# ── PyInstaller 의존성 추적용 (런타임에는 실행되지 않음) ──
# core/app.py 가 '실행 시점'에 import 하는 모듈들을 정적 분석이 놓치지 않도록 명시.
# (app.py 는 Streamlit이 파일로 읽어 exec 하므로 launcher 분석 그래프엔 안 잡힘)
if False:  # pragma: no cover
    import config, image_loader, vision, generator, state, crawler  # noqa: F401
    import openai, tiktoken, pandas, numpy, requests, dotenv  # noqa: F401
    import PIL.Image  # noqa: F401


def main() -> None:
    from streamlit.web import cli as stcli

    app_path = _res("core", "app.py")
    sys.argv = [
        "streamlit", "run", app_path,
        "--global.developmentMode=false",
        "--server.headless=false",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
