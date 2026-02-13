"""
Multi-Agent Communication Daemon v1.0
======================================
6개 에이전트(server/client/db/design/qa/tool)가 메일박스 패턴으로
비동기 협업하는 시스템.

사용법:
  python multi_agent_daemon.py --role server     # 서버 에이전트
  python multi_agent_daemon.py --role client     # 클라 에이전트
  python multi_agent_daemon.py --role db         # DB 에이전트
  python multi_agent_daemon.py --role design     # 기획/밸런스 에이전트
  python multi_agent_daemon.py --role qa         # QA 에이전트
  python multi_agent_daemon.py --role tool       # 툴/인프라 에이전트

동작 방식:
  1. git pull로 최신 상태 가져오기
  2. 자기 mailbox/ 확인 (새 메시지?)
  3. boards/blocking.md 확인 (블로킹?)
  4. 메시지 처리 (Claude CLI 호출)
  5. 결과를 상대방 mailbox/에 작성
  6. conversation_journal.json 업데이트
  7. git commit + push
"""

import subprocess
import sys
import os
import json
import time
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple


# ─── 경로 ─────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
COMMS_DIR = REPO_ROOT / "_comms"
MAILBOX_DIR = COMMS_DIR / "mailbox"
BOARDS_DIR = COMMS_DIR / "boards"
CONTRACTS_DIR = COMMS_DIR / "contracts"
CONFIG_FILE = COMMS_DIR / "agent_config.json"
JOURNAL_FILE = COMMS_DIR / "conversation_journal.json"
LOG_DIR = COMMS_DIR / "daemon_logs"

VALID_ROLES = ["server", "client", "db", "design", "qa", "tool"]


# ─── 설정 로드 ────────────────────────────────────────

def load_config() -> dict:
    """agent_config.json 로드"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"agent_config.json not found: {CONFIG_FILE}")
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


# ─── 유틸리티 ─────────────────────────────────────────

def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix_map = {
        "INFO": "  ", "RECV": "<<", "SEND": ">>",
        "WARN": "!!", "OK": "OK", "BLOCK": "XX",
        "TEST": "TT"
    }
    prefix = prefix_map.get(level, "  ")
    try:
        print(f"[{timestamp}] {prefix} {msg}")
    except UnicodeEncodeError:
        print(f"[{timestamp}] {prefix} {msg.encode('ascii', 'replace').decode()}")

    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}_multi.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level}] {msg}\n")


def git_pull() -> bool:
    """git pull origin main"""
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main", "--no-edit"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT), encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            if "CONFLICT" in (result.stdout + result.stderr):
                log("Git 충돌 감지 - _comms/ 자동 해결", "WARN")
                subprocess.run(["git", "checkout", "--theirs", "_comms/"],
                               cwd=str(REPO_ROOT), capture_output=True)
                subprocess.run(["git", "add", "_comms/"],
                               cwd=str(REPO_ROOT), capture_output=True)
                subprocess.run(["git", "commit", "-m", "comms: [auto] merge conflict resolved"],
                               cwd=str(REPO_ROOT), capture_output=True)
            else:
                log(f"git pull 실패: {result.stderr.strip()[:200]}", "WARN")
                return False
        return True
    except subprocess.TimeoutExpired:
        log("git pull 타임아웃", "WARN")
        return False


def git_push(message: str) -> bool:
    """git add _comms/ + commit + push"""
    for attempt in range(3):
        try:
            subprocess.run(["git", "add", "_comms/"],
                           cwd=str(REPO_ROOT), capture_output=True)

            status = subprocess.run(
                ["git", "status", "--porcelain", "_comms/"],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
                encoding="utf-8", errors="replace"
            )
            if not status.stdout.strip():
                return True

            subprocess.run(["git", "commit", "-m", message],
                           cwd=str(REPO_ROOT), capture_output=True)

            result = subprocess.run(
                ["git", "push", "origin", "main"],
                capture_output=True, text=True, timeout=30,
                cwd=str(REPO_ROOT), encoding="utf-8", errors="replace"
            )
            if result.returncode == 0:
                return True

            log(f"push 실패 (시도 {attempt+1}/3), pull 후 재시도", "WARN")
            git_pull()
        except subprocess.TimeoutExpired:
            log(f"git push 타임아웃 (시도 {attempt+1})", "WARN")

    return False


# ─── 메시지 ───────────────────────────────────────────

class Message:
    """메일박스 메시지"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.frontmatter = {}
        self.body = ""
        self._parse()

    def _parse(self):
        content = self.filepath.read_text(encoding="utf-8")
        match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
        if match:
            for line in match.group(1).split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    val = val.strip().strip('"').strip("'")
                    if val.startswith("[") and val.endswith("]"):
                        val = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
                    self.frontmatter[key.strip()] = val
            self.body = content[match.end():]
        else:
            self.body = content

    @property
    def id(self) -> str:
        return self.frontmatter.get("id", self.filepath.stem)

    @property
    def sender(self) -> str:
        return self.frontmatter.get("from", "unknown")

    @property
    def msg_type(self) -> str:
        return self.frontmatter.get("type", "unknown")

    @property
    def priority(self) -> str:
        return self.frontmatter.get("priority", "P2")

    @property
    def status(self) -> str:
        return self.frontmatter.get("status", "pending")

    def update_status(self, new_status: str):
        content = self.filepath.read_text(encoding="utf-8")
        content = re.sub(
            r'(^status:\s*).+$', f'\\g<1>{new_status}',
            content, flags=re.MULTILINE
        )
        self.filepath.write_text(content, encoding="utf-8")
        self.frontmatter["status"] = new_status


def create_message(
    sender: str,
    receiver: str,
    msg_id: str,
    msg_type: str,
    priority: str,
    subject: str,
    body: str,
    references: list = None
) -> Path:
    """메시지 파일 생성 → 수신자의 mailbox에 저장"""
    config = load_config()
    sender_prefix = config["agents"][sender]["prefix"]
    mailbox = MAILBOX_DIR / receiver

    safe_subject = re.sub(r'[^\w\-]', '_', subject)[:40]
    filename = f"{msg_id}_from_{sender}_{safe_subject}.md"
    filepath = mailbox / filename

    refs_str = json.dumps(references or [])
    content = f"""---
id: {msg_id}
from: {sender}-agent
to: {receiver}-agent
type: {msg_type}
priority: {priority}
status: pending
created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
references: {refs_str}
---

# {subject}

{body}
"""
    filepath.write_text(content, encoding="utf-8")
    return filepath


def get_next_msg_id(role: str) -> str:
    """다음 메시지 ID 계산"""
    config = load_config()
    prefix = config["agents"][role]["prefix"]

    # mailbox들 전체 스캔해서 최대 번호 찾기
    max_num = 0
    for agent_dir in MAILBOX_DIR.iterdir():
        if agent_dir.is_dir():
            for f in agent_dir.glob(f"{prefix}*_*.md"):
                m = re.search(rf'{prefix}(\d+)', f.name)
                if m:
                    max_num = max(max_num, int(m.group(1)))

    # 레거시 디렉토리도 확인
    for legacy_dir in [COMMS_DIR / "server_to_client", COMMS_DIR / "client_to_server"]:
        if legacy_dir.exists():
            for f in legacy_dir.glob(f"{prefix}*_*.md"):
                m = re.search(rf'{prefix}(\d+)', f.name)
                if m:
                    max_num = max(max_num, int(m.group(1)))

    return f"{prefix}{max_num + 1:03d}"


# ─── 블로킹 보드 ─────────────────────────────────────

def get_active_blocks(my_role: str) -> List[dict]:
    """나를 차단하는 활성 블록 목록"""
    blocking_file = BOARDS_DIR / "blocking.md"
    if not blocking_file.exists():
        return []

    content = blocking_file.read_text(encoding="utf-8")
    blocks = []

    # ### [BLOCK-xxx] 패턴 파싱
    current_block = None
    for line in content.split("\n"):
        block_match = re.match(r'### \[BLOCK-(\d+)\] (.+)', line)
        if block_match:
            if current_block and current_block.get("status") == "active":
                blocks.append(current_block)
            current_block = {
                "id": f"BLOCK-{block_match.group(1)}",
                "title": block_match.group(2),
                "blocked_agents": [],
                "status": "active"
            }
        elif current_block:
            if "차단 대상" in line:
                agents = re.findall(r'(server|client|db|design|qa|tool)', line)
                current_block["blocked_agents"] = agents
            elif "상태" in line:
                if "resolved" in line.lower():
                    current_block["status"] = "resolved"

    if current_block and current_block.get("status") == "active":
        blocks.append(current_block)

    return [b for b in blocks if my_role in b.get("blocked_agents", [])]


# ─── 저널 ─────────────────────────────────────────────

def update_journal(
    msg_id: str,
    from_agent: str,
    to_agent: str,
    msg_type: str,
    summary: str,
    key_content: str = ""
):
    """conversation_journal.json에 메시지 기록"""
    try:
        if JOURNAL_FILE.exists():
            journal = json.loads(JOURNAL_FILE.read_text(encoding="utf-8"))
        else:
            journal = {
                "meta": {"schema_version": 3, "description": "멀티에이전트 대화 저널"},
                "timeline": [],
                "decisions": [],
                "agent_states": {}
            }

        existing_ids = {m["id"] for m in journal.get("timeline", [])}
        if msg_id not in existing_ids:
            journal.setdefault("timeline", []).append({
                "id": msg_id,
                "from": from_agent,
                "to": to_agent,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "type": msg_type,
                "summary": summary[:200],
                "key_content": key_content[:300],
                "status": "pending"
            })

        journal["meta"]["last_updated"] = datetime.now().isoformat()
        JOURNAL_FILE.write_text(
            json.dumps(journal, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        log(f"저널 업데이트 실패: {e}", "WARN")


# ─── 멀티에이전트 데몬 ───────────────────────────────

class MultiAgentDaemon:
    """6-agent 메일박스 데몬"""

    def __init__(self, role: str, config: dict, poll_interval: int = 300):
        if role not in VALID_ROLES:
            raise ValueError(f"유효하지 않은 역할: {role}. 가능: {VALID_ROLES}")

        self.role = role
        self.config = config
        self.agent_config = config["agents"][role]
        self.prefix = self.agent_config["prefix"]
        self.poll_interval = poll_interval
        self.idle_count = 0
        self.processed = set()
        self.my_mailbox = MAILBOX_DIR / role

        self.my_mailbox.mkdir(parents=True, exist_ok=True)
        self._load_processed()

    def _load_processed(self):
        tracker = COMMS_DIR / f".{self.role}_multi_processed.json"
        if tracker.exists():
            try:
                self.processed = set(json.loads(tracker.read_text()))
            except:
                self.processed = set()

    def _save_processed(self):
        tracker = COMMS_DIR / f".{self.role}_multi_processed.json"
        tracker.write_text(json.dumps(list(self.processed)))

    def check_messages(self) -> List[Message]:
        """내 mailbox에서 pending 메시지 찾기"""
        msgs = []
        if not self.my_mailbox.exists():
            return msgs

        for f in sorted(self.my_mailbox.glob("*.md")):
            if f.name in self.processed:
                continue
            msg = Message(f)
            if msg.status == "pending":
                msgs.append(msg)

        return msgs

    def check_blocks(self) -> List[dict]:
        """나를 차단하는 블로킹 이슈 확인"""
        return get_active_blocks(self.role)

    def can_message(self, target: str) -> bool:
        """target에게 메시지를 보낼 수 있는지"""
        return target in self.agent_config.get("can_message", [])

    def send_message(
        self,
        receiver: str,
        msg_type: str,
        subject: str,
        body: str,
        priority: str = "P2",
        references: list = None
    ) -> Optional[str]:
        """메시지 발송"""
        if not self.can_message(receiver):
            log(f"{self.role} → {receiver} 통신 불가 (agent_config 확인)", "WARN")
            return None

        msg_id = get_next_msg_id(self.role)
        filepath = create_message(
            sender=self.role,
            receiver=receiver,
            msg_id=msg_id,
            msg_type=msg_type,
            priority=priority,
            subject=subject,
            body=body,
            references=references
        )

        update_journal(
            msg_id=msg_id,
            from_agent=f"{self.role}-agent",
            to_agent=f"{receiver}-agent",
            msg_type=msg_type,
            summary=subject,
            key_content=body[:200]
        )

        log(f"메시지 발송: {msg_id} → {receiver} [{msg_type}] {subject}", "SEND")
        return msg_id

    def process_message(self, msg: Message) -> bool:
        """메시지 처리 (Claude CLI 호출)"""
        log(f"수신: {msg.id} from {msg.sender} [{msg.msg_type}] (우선순위: {msg.priority})", "RECV")

        msg.update_status("read")

        # Claude CLI로 처리
        response = self._invoke_claude(msg)
        if response is None:
            log(f"{msg.id} 처리 실패", "WARN")
            return False

        # 응답 메시지 생성
        sender_role = msg.sender.replace("-agent", "")
        reply_id = self.send_message(
            receiver=sender_role,
            msg_type="answer",
            subject=f"Re: {msg.id}",
            body=response,
            priority=msg.priority,
            references=[msg.id]
        )

        if reply_id:
            msg.update_status("resolved")
            self.processed.add(msg.filepath.name)
            self._save_processed()
            log(f"응답 완료: {reply_id} → {sender_role}", "SEND")
            return True

        return False

    def _invoke_claude(self, msg: Message) -> Optional[str]:
        """Claude CLI 호출"""
        agent_name = self.agent_config["name"]
        agent_role = self.agent_config["role"]

        prompt = f"""너는 ECS MMORPG 프로젝트의 {agent_name}야.
역할: {agent_role}

=== 수신 메시지 ===
ID: {msg.id}
발신: {msg.sender}
타입: {msg.msg_type}
우선순위: {msg.priority}

{msg.body}

=== 응답 규칙 ===
1. {agent_name} 역할에 맞게 응답
2. 다른 에이전트 영역 코드를 직접 수정하지 않음
3. 동료에게 말하듯 자연스럽게
4. 불확실한 건 [ESCALATE]로 대표에게 위임"""

        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True, text=True,
                timeout=300, cwd=str(REPO_ROOT),
                encoding="utf-8", errors="replace"
            )
            if result.returncode == 0:
                return result.stdout.strip()
            log(f"Claude CLI 에러: {result.stderr[:200]}", "WARN")
            return None
        except FileNotFoundError:
            log("claude CLI 미설치", "WARN")
            return None
        except subprocess.TimeoutExpired:
            log("Claude CLI 타임아웃 (300초)", "WARN")
            return None

    def run(self):
        """메인 폴링 루프"""
        agent_name = self.agent_config["name"]
        log(f"{'='*50}")
        log(f"  Multi-Agent Daemon 시작")
        log(f"  역할: {self.role} ({agent_name})")
        log(f"  mailbox: {self.my_mailbox}")
        log(f"  poll: {self.poll_interval}초")
        log(f"  통신 가능: {self.agent_config['can_message']}")
        log(f"{'='*50}")

        try:
            while True:
                # 1. git pull
                if not git_pull():
                    time.sleep(self.poll_interval)
                    continue

                # 2. 블로킹 확인
                blocks = self.check_blocks()
                if blocks:
                    for b in blocks:
                        log(f"[{b['id']}] {b['title']} - 작업 대기 중", "BLOCK")
                    time.sleep(self.poll_interval)
                    continue

                # 3. 새 메시지 확인
                msgs = self.check_messages()

                if msgs:
                    self.idle_count = 0
                    log(f"새 메시지 {len(msgs)}개 발견")

                    for msg in msgs:
                        success = self.process_message(msg)
                        if success:
                            git_push(f"comms: [{self.role}] replied to {msg.id}")
                else:
                    self.idle_count += 1
                    if self.idle_count % 12 == 0:
                        log(f"대기 중... (idle {self.idle_count}회)")

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            log(f"{agent_name} 데몬 종료 (Ctrl+C)")


# ─── 엔트리포인트 ─────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Communication Daemon")
    parser.add_argument("--role", required=True, choices=VALID_ROLES,
                        help="에이전트 역할")
    parser.add_argument("--interval", type=int, default=300,
                        help="폴링 간격 (초)")
    parser.add_argument("--test", action="store_true",
                        help="테스트 모드 (1회 폴링)")
    parser.add_argument("--send", nargs=3, metavar=("TO", "TYPE", "SUBJECT"),
                        help="메시지 보내기 (예: --send client spec '새 패킷 추가')")
    parser.add_argument("--body", default="",
                        help="--send 시 메시지 본문")

    args = parser.parse_args()
    config = load_config()
    daemon = MultiAgentDaemon(args.role, config, args.interval)

    if args.send:
        to, msg_type, subject = args.send
        msg_id = daemon.send_message(to, msg_type, subject, args.body or subject)
        if msg_id:
            git_push(f"comms: [{args.role}→{to}] {msg_id} {subject[:30]}")
            log(f"발송 완료: {msg_id}")
        return

    if args.test:
        log("테스트 모드: 1회 폴링")
        git_pull()
        blocks = daemon.check_blocks()
        msgs = daemon.check_messages()
        log(f"블로킹: {len(blocks)}건, 메시지: {len(msgs)}건")
        for b in blocks:
            log(f"  BLOCK: [{b['id']}] {b['title']}", "BLOCK")
        for m in msgs:
            log(f"  MSG: {m.id} from {m.sender} [{m.msg_type}]", "RECV")
        return

    daemon.run()


if __name__ == "__main__":
    main()
