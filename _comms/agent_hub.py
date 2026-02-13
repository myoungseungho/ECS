"""
Agent Hub v1.0 - 터미널 세션 내 멀티에이전트 허브
=================================================

이 스크립트는 Claude Code 터미널 안에서 백그라운드로 실행됩니다.
데몬(multi_agent_daemon.py)과 연동하여 하이브리드 모드를 구현합니다.

구조:
  [이 터미널 열려있을 때]
    agent_hub.py가 .hub_active 하트비트 유지
    → 데몬은 알림만 (notify 모드)
    → 허브가 메시지 스캔 → .hub_inbox.json에 결과 기록
    → 메인 에이전트(Opus)가 읽고 판단/처리

  [터미널 닫혔을 때]
    .hub_active가 만료됨 (10분+ 전)
    → 데몬이 자동으로 full 모드 전환
    → claude -p로 자체 처리

사용법:
  # 1회 스캔 (터미널에서 확인용)
  python _comms/agent_hub.py --scan

  # 폴링 루프 (백그라운드 실행용)
  python _comms/agent_hub.py --poll --interval 180

  # 하트비트만 갱신
  python _comms/agent_hub.py --heartbeat

  # 상태 확인
  python _comms/agent_hub.py --status
"""

import subprocess
import sys
import os
import json
import time
import re
from pathlib import Path
from datetime import datetime, timedelta

REPO_ROOT = Path(__file__).parent.parent
COMMS_DIR = REPO_ROOT / "_comms"
MAILBOX_DIR = COMMS_DIR / "mailbox"
BOARDS_DIR = COMMS_DIR / "boards"
HUB_ACTIVE_FILE = COMMS_DIR / ".hub_active"
HUB_INBOX_FILE = COMMS_DIR / ".hub_inbox.json"
LOG_DIR = COMMS_DIR / "daemon_logs"

HEARTBEAT_INTERVAL = 300  # 5분마다 하트비트
HEARTBEAT_TIMEOUT = 600   # 10분 지나면 만료

VALID_ROLES = ["server", "client", "db", "design", "qa", "tool"]


def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix_map = {"INFO": "  ", "NEW": ">>", "WARN": "!!", "HUB": "HB"}
    p = prefix_map.get(level, "  ")
    line = f"[{timestamp}] {p} {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode())
    LOG_DIR.mkdir(exist_ok=True)
    with open(LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}_hub.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


# ─── 하트비트 ─────────────────────────────────────────

def write_heartbeat():
    """하트비트 파일 생성/갱신 - '나 살아있어' 신호"""
    data = {
        "pid": os.getpid(),
        "timestamp": datetime.now().isoformat(),
        "type": "claude_code_session"
    }
    HUB_ACTIVE_FILE.write_text(json.dumps(data), encoding="utf-8")


def is_hub_active() -> bool:
    """허브(터미널 세션)가 살아있는지 확인"""
    if not HUB_ACTIVE_FILE.exists():
        return False
    try:
        data = json.loads(HUB_ACTIVE_FILE.read_text(encoding="utf-8"))
        ts = datetime.fromisoformat(data["timestamp"])
        age = (datetime.now() - ts).total_seconds()
        return age < HEARTBEAT_TIMEOUT
    except:
        return False


def remove_heartbeat():
    """허브 종료 시 하트비트 파일 제거"""
    if HUB_ACTIVE_FILE.exists():
        HUB_ACTIVE_FILE.unlink()


# ─── Git ──────────────────────────────────────────────

def git_pull() -> bool:
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main", "--no-edit"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT), encoding="utf-8", errors="replace"
        )
        return result.returncode == 0
    except:
        return False


# ─── 메일박스 스캔 ────────────────────────────────────

def scan_all_mailboxes() -> dict:
    """모든 에이전트의 mailbox를 스캔하여 pending 메시지 목록 반환"""
    result = {
        "scan_time": datetime.now().isoformat(),
        "hub_active": True,
        "new_messages": [],
        "total_pending": 0,
        "by_agent": {}
    }

    for role in VALID_ROLES:
        mailbox = MAILBOX_DIR / role
        if not mailbox.exists():
            continue

        pending = []
        for f in sorted(mailbox.glob("*.md")):
            if f.name == ".gitkeep":
                continue
            try:
                content = f.read_text(encoding="utf-8")
                match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
                if not match:
                    continue

                fm = {}
                for line in match.group(1).split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip()] = v.strip().strip('"').strip("'")

                if fm.get("status") == "pending":
                    body = content[match.end():]
                    first_line = ""
                    for bl in body.strip().split("\n"):
                        bl = bl.strip().lstrip("#").strip()
                        if bl:
                            first_line = bl[:100]
                            break

                    msg_info = {
                        "id": fm.get("id", f.stem),
                        "from": fm.get("from", "unknown"),
                        "to": f"{role}-agent",
                        "type": fm.get("type", "unknown"),
                        "priority": fm.get("priority", "P2"),
                        "subject": first_line,
                        "file": str(f),
                        "created": fm.get("created", "")
                    }
                    pending.append(msg_info)
            except Exception as e:
                log(f"파일 파싱 실패: {f.name}: {e}", "WARN")

        if pending:
            result["by_agent"][role] = pending
            result["new_messages"].extend(pending)

    result["total_pending"] = len(result["new_messages"])
    return result


def save_inbox(scan_result: dict):
    """스캔 결과를 .hub_inbox.json에 저장 - 메인 에이전트가 읽을 파일"""
    HUB_INBOX_FILE.write_text(
        json.dumps(scan_result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def read_inbox() -> dict:
    """저장된 스캔 결과 읽기"""
    if not HUB_INBOX_FILE.exists():
        return {"total_pending": 0, "new_messages": [], "by_agent": {}}
    try:
        return json.loads(HUB_INBOX_FILE.read_text(encoding="utf-8"))
    except:
        return {"total_pending": 0, "new_messages": [], "by_agent": {}}


# ─── 폴링 루프 ───────────────────────────────────────

def poll_loop(interval: int = 180):
    """
    백그라운드 폴링 루프.
    - 하트비트 유지
    - git pull + mailbox 스캔
    - 결과를 .hub_inbox.json에 기록
    """
    log(f"Agent Hub 폴링 시작 (간격: {interval}초)", "HUB")
    write_heartbeat()

    cycle = 0
    try:
        while True:
            cycle += 1

            # 하트비트 갱신
            write_heartbeat()

            # git pull
            git_pull()

            # 스캔
            result = scan_all_mailboxes()
            save_inbox(result)

            if result["total_pending"] > 0:
                log(f"[Cycle {cycle}] 새 메시지 {result['total_pending']}건 발견!", "NEW")
                for msg in result["new_messages"]:
                    log(f"  {msg['id']} from {msg['from']} → {msg['to']} [{msg['type']}] {msg['subject'][:50]}", "NEW")
            else:
                if cycle % 10 == 0:  # 10사이클마다 로그
                    log(f"[Cycle {cycle}] 새 메시지 없음. 대기 중...")

            time.sleep(interval)

    except KeyboardInterrupt:
        log("Hub 폴링 종료", "HUB")
        remove_heartbeat()


# ─── 상태 확인 ────────────────────────────────────────

def show_status():
    """현재 시스템 상태 출력"""
    hub_status = "ACTIVE" if is_hub_active() else "INACTIVE"

    if HUB_ACTIVE_FILE.exists():
        try:
            data = json.loads(HUB_ACTIVE_FILE.read_text(encoding="utf-8"))
            ts = datetime.fromisoformat(data["timestamp"])
            age = int((datetime.now() - ts).total_seconds())
            hub_detail = f"(마지막 하트비트: {age}초 전, PID: {data.get('pid', '?')})"
        except:
            hub_detail = ""
    else:
        hub_detail = "(하트비트 파일 없음)"

    print(f"\n{'='*50}")
    print(f"  Multi-Agent Hub Status")
    print(f"{'='*50}")
    print(f"  Hub: {hub_status} {hub_detail}")

    inbox = read_inbox()
    print(f"  Pending: {inbox.get('total_pending', 0)}건")

    if inbox.get("by_agent"):
        for agent, msgs in inbox["by_agent"].items():
            print(f"    {agent}: {len(msgs)}건")
            for m in msgs[:3]:
                print(f"      - {m['id']} from {m['from']} [{m['type']}]")

    print(f"{'='*50}\n")


# ─── 엔트리포인트 ─────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Hub - Terminal Session Controller")
    parser.add_argument("--scan", action="store_true", help="1회 스캔 후 결과 출력")
    parser.add_argument("--poll", action="store_true", help="폴링 루프 시작")
    parser.add_argument("--interval", type=int, default=180, help="폴링 간격 (초, 기본=180)")
    parser.add_argument("--heartbeat", action="store_true", help="하트비트만 갱신")
    parser.add_argument("--status", action="store_true", help="현재 상태 확인")
    parser.add_argument("--stop", action="store_true", help="하트비트 제거 (데몬에게 위임)")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.heartbeat:
        write_heartbeat()
        log("하트비트 갱신됨", "HUB")
    elif args.stop:
        remove_heartbeat()
        log("하트비트 제거됨 - 데몬이 full 모드로 전환됩니다", "HUB")
    elif args.scan:
        git_pull()
        result = scan_all_mailboxes()
        save_inbox(result)
        if result["total_pending"] > 0:
            print(f"\n새 메시지 {result['total_pending']}건:")
            for msg in result["new_messages"]:
                print(f"  {msg['id']} from {msg['from']} → {msg['to']} [{msg['type']}] {msg['subject'][:60]}")
        else:
            print("\n새 메시지 없음.")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.poll:
        poll_loop(args.interval)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
