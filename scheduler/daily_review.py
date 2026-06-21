"""
Daily code review -> Telegram.

Runs once (intended for a 09:00 launchd trigger): asks Claude Code to review the
repo for bugs / things to fix and the next steps to take, then sends a short
Korean summary (<=300 chars) to Telegram. Credentials come from .env via config.

Run manually:  uv run python -m scheduler.daily_review
"""

import shutil
import subprocess
from pathlib import Path

from scheduler.notify import send_telegram

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_BIN = shutil.which("claude") or "claude"
CLAUDE_TIMEOUT = 600  # seconds
CHAR_LIMIT = 300

REVIEW_PROMPT = (
    "이 저장소(quant-trading)를 점검해줘. "
    "1) 오류나 당장 고쳐야 할 문제, 2) 다음으로 진행해야 할 스텝을 파악해. "
    "TODO.md와 최근 변경, 핵심 코드(strategy, backtest, scheduler)를 살펴봐. "
    "코드는 절대 수정하지 말고 읽기만 해. "
    "결과는 텔레그램으로 보낼 한국어 메시지 한 개로, 다른 말 없이 본문만 출력해. "
    "반드시 300자 이내. 형식 예시:\n"
    "[점검] <한줄 상태>\n"
    "⚠️ 고칠 것: <핵심 1~2개>\n"
    "👉 다음 스텝: <핵심 1~2개>"
)


def run_claude(prompt: str) -> str:
    """Run one read-only prompt headlessly in a fresh session."""
    cmd = [CLAUDE_BIN, "--dangerously-skip-permissions", "-p", prompt]
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"⏱️ 점검이 {CLAUDE_TIMEOUT}s 안에 끝나지 않았어요."
    out = (proc.stdout or "").strip()
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        return f"❌ 점검 실패 (exit {proc.returncode}).\n{err or out}"[:CHAR_LIMIT]
    return out or "(점검 결과 없음)"


def main() -> None:
    result = run_claude(REVIEW_PROMPT)
    if len(result) > CHAR_LIMIT:
        result = result[: CHAR_LIMIT - 1].rstrip() + "…"
    print(result)
    send_telegram(result)


if __name__ == "__main__":
    main()
