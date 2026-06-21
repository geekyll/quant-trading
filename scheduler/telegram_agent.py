"""
Telegram -> Claude Code bridge.

Long-polls Telegram for messages from the authorized chat, runs each message
as a Claude Code task in this repo (code edits, tests, etc.), and replies with
the result. Credentials are loaded from .env via config.py.

Run:  uv run python -m scheduler.telegram_agent
"""

import shutil
import subprocess
import time
from pathlib import Path

import requests

from config import TelegramConfig
from scheduler.notify import send_telegram

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_BIN = shutil.which("claude") or "claude"
CLAUDE_TIMEOUT = 900  # seconds; code edits + tests can be slow
POLL_TIMEOUT = 30  # long-poll seconds
TELEGRAM_LIMIT = 4000  # leave headroom under the 4096 hard limit
SUMMARIZE_THRESHOLD = 1500  # responses longer than this get summarized first

# Appended to every task: do the work, commit any changes, report in Korean.
TASK_SUFFIX = (
    "\n\n---\n"
    "위 작업을 수행해줘. 코드나 파일을 변경했다면 작업을 마친 뒤 git add 후 commit까지 해줘 "
    "(커밋 메시지는 변경 내용을 한 줄로 요약). 변경한 게 없으면 커밋하지 마. "
    "마지막에 무엇을 했는지 한국어로 보고해줘."
)

# Used to compress long results into a Telegram-friendly summary.
SUMMARIZE_PREFIX = (
    "다음은 방금 끝난 작업의 실행 결과야. 텔레그램으로 보낼 수 있게 한국어로 핵심만 "
    "1500자 이내로 요약해줘. 무엇을 했는지, 커밋 여부, 테스트 결과 위주로. 다른 말은 붙이지 마:\n\n"
)


def run_claude(prompt: str) -> str:
    """Run one prompt headlessly in its own fresh session.

    Each message is a standalone run (no --continue): concurrent claude
    processes in the same repo would otherwise deadlock on the shared
    most-recent-session file.
    """
    cmd = [
        CLAUDE_BIN,
        "--dangerously-skip-permissions",
        "-p",
        prompt,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"⏱️ Claude timed out after {CLAUDE_TIMEOUT}s."
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return f"❌ Claude exited with {proc.returncode}.\n{err or out}"
    return out or "(no output)"


def reply(text: str) -> None:
    """Send a reply, chunked to fit Telegram's message size limit."""
    for i in range(0, len(text), TELEGRAM_LIMIT):
        send_telegram(text[i : i + TELEGRAM_LIMIT])


def main() -> None:
    token = TelegramConfig.bot_token
    authorized = str(TelegramConfig.chat_id)
    if not token or not authorized:
        raise SystemExit("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in .env")

    base = f"https://api.telegram.org/bot{token}"
    offset = None
    print(f"[telegram_agent] listening (chat_id={authorized}, repo={REPO_ROOT})")

    while True:
        try:
            params = {"timeout": POLL_TIMEOUT}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(f"{base}/getUpdates", params=params, timeout=POLL_TIMEOUT + 10)
            updates = resp.json().get("result", [])
        except Exception as e:  # network hiccup — back off and retry
            print(f"[telegram_agent] poll error: {e}")
            time.sleep(5)
            continue

        for upd in updates:
            offset = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("edited_message")
            if not msg:
                continue
            chat_id = str(msg.get("chat", {}).get("id", ""))
            text = (msg.get("text") or "").strip()
            if chat_id != authorized:
                print(f"[telegram_agent] ignoring chat_id={chat_id}")
                continue
            if not text:
                continue

            print(f"[telegram_agent] >> {text}")
            reply("🤖 작업 중...")
            result = run_claude(text + TASK_SUFFIX)
            if len(result) > SUMMARIZE_THRESHOLD:
                print(f"[telegram_agent] result {len(result)} chars — summarizing")
                result = run_claude(SUMMARIZE_PREFIX + result)
            print(f"[telegram_agent] << {result[:200]}")
            reply(result)


if __name__ == "__main__":
    main()
