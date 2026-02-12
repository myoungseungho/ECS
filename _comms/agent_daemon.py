"""
Agent Communication Daemon v1.0
================================
양쪽 컴퓨터에서 실행. git을 통해 에이전트 간 자동 대화를 중계합니다.

사용법:
  python agent_daemon.py --role server    # 서버 컴퓨터에서
  python agent_daemon.py --role client    # 클라 컴퓨터에서

동작 방식:
  1. git pull로 상대방 메시지 확인 (30초 간격)
  2. 새 메시지 발견 → Claude CLI로 처리 요청
  3. Claude 응답 → 응답 파일 생성 → git push
  4. [ESCALATE] 태그 시 대표에게 승인 요청 후 대기
  5. 반복

필수 요건:
  - claude CLI가 PATH에 있어야 함 (Claude Code 설치)
  - git이 설정되어 있어야 함 (push/pull 가능)
  - 이 스크립트는 레포 루트에서 실행
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

# 회의록 시스템
sys.path.insert(0, str(Path(__file__).parent))
try:
    from meeting_recorder import MeetingRecorder
    HAS_RECORDER = True
except ImportError:
    HAS_RECORDER = False

# ─── 설정 ─────────────────────────────────────────────

POLL_INTERVAL = 300         # 폴링 간격 (초) - 5분
MAX_CONSECUTIVE_IDLE = 999  # idle이어도 간격 안 늘림 (상대가 작업 중일 수 있음)
IDLE_POLL_INTERVAL = 300    # idle이어도 동일한 5분 간격 유지
CHECKIN_AFTER_IDLE = 12     # 12회 idle(=1시간) 후 안부 메시지
MAX_RETRIES = 3             # git push 실패 시 재시도
CLAUDE_TIMEOUT = 300        # Claude CLI 타임아웃 (초)


def _update_poll_interval(val):
    global POLL_INTERVAL
    POLL_INTERVAL = val

# ─── 경로 ─────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
COMMS_DIR = REPO_ROOT / "_comms"
STATUS_BOARD = COMMS_DIR / "status_board.json"
AGREEMENTS_DIR = COMMS_DIR / "agreements"
LOG_DIR = COMMS_DIR / "daemon_logs"
SESSION_STATE = COMMS_DIR / "session_state.json"
CONVERSATION_JOURNAL = COMMS_DIR / "conversation_journal.json"

# ─── 유틸리티 ─────────────────────────────────────────

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {"INFO": "  ", "RECV": "<<", "SEND": ">>", "WARN": "!!", "CEO": "**", "OK": "OK"}
    try:
        print(f"[{timestamp}] {prefix.get(level, '  ')} {msg}")
    except UnicodeEncodeError:
        print(f"[{timestamp}] {prefix.get(level, '  ')} {msg.encode('ascii', 'replace').decode()}")

    # 파일 로그
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] [{level}] {msg}\n")


def git_pull():
    """git pull origin main. 충돌 시 상대방 파일 우선."""
    try:
        result = subprocess.run(
            ["git", "pull", "origin", "main", "--no-edit"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT), encoding="utf-8", errors="replace"
        )
        if result.returncode != 0:
            if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
                log("Git 충돌 감지 - 자동 해결 시도", "WARN")
                subprocess.run(
                    ["git", "checkout", "--theirs", "_comms/"],
                    cwd=str(REPO_ROOT), capture_output=True
                )
                subprocess.run(
                    ["git", "add", "_comms/"],
                    cwd=str(REPO_ROOT), capture_output=True
                )
                subprocess.run(
                    ["git", "commit", "-m", "comms: [auto] merge conflict resolved"],
                    cwd=str(REPO_ROOT), capture_output=True
                )
            else:
                log(f"git pull 실패: {result.stderr.strip()}", "WARN")
                return False
        return True
    except subprocess.TimeoutExpired:
        log("git pull 타임아웃", "WARN")
        return False


def git_push(message):
    """git add + commit + push. 실패 시 재시도."""
    for attempt in range(MAX_RETRIES):
        try:
            subprocess.run(
                ["git", "add", "_comms/"],
                cwd=str(REPO_ROOT), capture_output=True
            )

            # 변경사항 있는지 확인
            status = subprocess.run(
                ["git", "status", "--porcelain", "_comms/"],
                capture_output=True, text=True, cwd=str(REPO_ROOT),
                encoding="utf-8", errors="replace"
            )
            if not status.stdout.strip():
                return True  # 변경 없음

            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=str(REPO_ROOT), capture_output=True
            )

            result = subprocess.run(
                ["git", "push", "origin", "main"],
                capture_output=True, text=True, timeout=30,
                cwd=str(REPO_ROOT), encoding="utf-8", errors="replace"
            )
            if result.returncode == 0:
                return True

            # push 실패 시 pull 후 재시도
            log(f"push 실패 (시도 {attempt+1}/{MAX_RETRIES}), pull 후 재시도", "WARN")
            git_pull()

        except subprocess.TimeoutExpired:
            log(f"git push 타임아웃 (시도 {attempt+1})", "WARN")

    log("git push 최종 실패", "WARN")
    return False


# ─── 메시지 파싱 ──────────────────────────────────────

def parse_frontmatter(filepath):
    """마크다운 파일에서 YAML 프론트매터 파싱"""
    content = filepath.read_text(encoding="utf-8")
    match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not match:
        return {}, content

    fm = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, val = line.split(":", 1)
            val = val.strip().strip('"').strip("'")
            # 리스트 처리
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip('"') for v in val[1:-1].split(",") if v.strip()]
            fm[key.strip()] = val

    body = content[match.end():]
    return fm, body


def update_frontmatter(filepath, updates):
    """프론트매터의 특정 필드 업데이트"""
    content = filepath.read_text(encoding="utf-8")
    for key, val in updates.items():
        pattern = rf'(^{key}:\s*)(.+)$'
        replacement = rf'\g<1>{val}'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    filepath.write_text(content, encoding="utf-8")


def get_next_msg_number(outbox_dir, prefix):
    """다음 메시지 번호 계산"""
    existing = list(outbox_dir.glob(f"{prefix}*_*.md"))
    if not existing:
        return 1
    numbers = []
    for f in existing:
        match = re.match(rf'{prefix}(\d+)_', f.name)
        if match:
            numbers.append(int(match.group(1)))
    return max(numbers) + 1 if numbers else 1


# ─── 상태 보드 ────────────────────────────────────────

def update_status_board(role, updates):
    """status_board.json에서 자기 섹션만 업데이트"""
    try:
        board = json.loads(STATUS_BOARD.read_text(encoding="utf-8"))
    except:
        board = {}

    agent_key = f"{role}_agent"
    if agent_key not in board:
        board[agent_key] = {}

    board[agent_key].update(updates)
    board["last_updated"] = datetime.now().isoformat()

    STATUS_BOARD.write_text(
        json.dumps(board, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


# ─── Claude CLI 호출 ─────────────────────────────────

def invoke_claude(prompt, role, context_files=None):
    """
    Claude CLI를 호출하여 메시지 처리.
    -p 플래그로 비대화형 실행.
    """
    # 시스템 프롬프트 구성
    system_context = build_system_prompt(role)

    full_prompt = f"""{system_context}

---

{prompt}

---

응답 규칙:
1. 응답 내용을 마크다운으로 작성해. 프론트매터는 포함하지 마.
2. 대표(인간) 승인이 필요한 중대 사안이면 응답 첫 줄에 [ESCALATE] 태그를 붙여.
   - 중대 사안: 아키텍처 변경, 스펙 대폭 수정, 일정 지연, 기술적 불확실성
   - 일반 사안: 질문 답변, 구현 보고, 테스트 결과 → ESCALATE 안 함
3. 응답만 출력. 다른 부가 설명 없이."""

    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt],
            capture_output=True, text=True,
            timeout=CLAUDE_TIMEOUT,
            cwd=str(REPO_ROOT),
            encoding="utf-8", errors="replace"
        )

        if result.returncode != 0:
            log(f"Claude CLI 에러: {result.stderr[:200]}", "WARN")
            return None, False

        response = result.stdout.strip()
        is_escalate = response.startswith("[ESCALATE]")

        if is_escalate:
            response = response.replace("[ESCALATE]", "", 1).strip()

        return response, is_escalate

    except subprocess.TimeoutExpired:
        log(f"Claude CLI 타임아웃 ({CLAUDE_TIMEOUT}초)", "WARN")
        return None, False
    except FileNotFoundError:
        log("claude CLI를 찾을 수 없습니다. Claude Code가 설치되어 있나요?", "WARN")
        return None, False


def build_system_prompt(role):
    """역할별 시스템 프롬프트 생성 - 대화 저널 포함"""

    # 대화 저널 로드 (핵심: 일회성 Claude에게 전체 맥락 주입)
    journal_context = _load_journal_context(role)

    role_name = "서버" if role == "server" else "클라이언트"
    partner_name = "클라이언트" if role == "server" else "서버"
    role_desc = "게임 서버 개발 (ECS 아키텍처, 패킷 처리, 게임 로직)" if role == "server" \
        else "게임 클라이언트 개발 (Unity C#, 네트워크, UI, 렌더링)"

    return f"""=== 중요: 이것은 이어지는 대화입니다 ===

너는 ECS MMORPG 프로젝트의 {role_name} 에이전트야.
지금 이 응답은 {partner_name} 에이전트와의 **진행 중인 협업 대화의 연속**이야.
이전에 주고받은 메시지들이 있고, 합의된 결정사항도 있어.
너는 새로 시작하는 게 아니라, 이전 대화를 이어받아서 계속하는 거야.

아래 [대화 저널]을 반드시 읽고 맥락을 완전히 이해한 상태에서 응답해.

역할: {role_desc}

=== 대화 저널 (전체 맥락) ===
{journal_context}
=== 저널 끝 ===

절대 규칙:
1. {role_name} 코드만 건드린다. {partner_name} 코드는 절대 수정하지 않는다.
2. 불확실하거나 아키텍처 변경 같은 중대 결정은 [ESCALATE]로 대표에게 위임.
3. 이미 합의된 결정(위 저널의 decisions)은 번복하지 않는다.
4. 이미 보낸 메시지를 중복으로 보내지 않는다.

대화 스타일:
- 동료에게 말하듯 자연스럽게 대화해. 딱딱한 보고서 말고 사람처럼.
- "오, 좋은 발견이야!", "솔직히 이건 좀 걱정돼" 같은 감정 표현 OK.
- 의견이 다르면 근거를 들어 솔직하게 반론해. 무조건 동의하지 마.
- 더 나은 대안이 있으면 적극적으로 제안해."""


def _load_journal_context(role):
    """conversation_journal.json에서 맥락 로드"""
    if not CONVERSATION_JOURNAL.exists():
        return "(저널 없음 - 첫 대화)"

    try:
        journal = json.loads(CONVERSATION_JOURNAL.read_text(encoding="utf-8"))
    except:
        return "(저널 로드 실패)"

    lines = []

    # 1. 메시지 타임라인
    timeline = journal.get("timeline", [])
    if timeline:
        lines.append("[메시지 타임라인]")
        for msg in timeline:
            lines.append(f"  {msg['id']} ({msg['from']} -> {msg['to']}, {msg['date']}): {msg['summary']}")
            if msg.get('key_content'):
                lines.append(f"    핵심: {msg['key_content'][:200]}")
        lines.append("")

    # 2. 합의된 결정사항 (매우 중요!)
    decisions = journal.get("decisions", [])
    if decisions:
        lines.append("[합의된 결정사항 - 번복 금지]")
        for d in decisions:
            lines.append(f"  {d['id']}: {d['decision']}")
        lines.append("")

    # 3. 현재 스프린트
    sprint = journal.get("current_sprint", {})
    if sprint.get("tasks"):
        lines.append(f"[현재 스프린트: {sprint.get('name', '')}]")
        for t in sprint["tasks"]:
            lines.append(f"  {t['id']}: {t['task']} (담당: {t['assignee']}, 상태: {t['status']})")
        lines.append("")

    # 4. 각 에이전트 상태
    states = journal.get("agent_states", {})
    if states:
        lines.append("[에이전트 현재 상태]")
        for agent, state in states.items():
            lines.append(f"  {agent}: 마지막 보냄={state.get('last_sent','?')}, 마지막 읽음={state.get('last_read','?')}")
            lines.append(f"    현재 작업: {state.get('current_work','?')}")
        lines.append("")

    # 5. 다음 메시지 번호 (중복 방지!)
    next_nums = journal.get("next_message_number", {})
    my_next = next_nums.get(role, "?")
    lines.append(f"[다음 메시지 번호] 내 다음 번호: {my_next} (이 번호 이하는 이미 사용됨)")

    # 6. 시스템 규칙
    rules = journal.get("system_rules", {})
    if rules:
        lines.append("")
        lines.append("[시스템 규칙]")
        for k, v in rules.items():
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


# ─── 에스컬레이션 ─────────────────────────────────────

def escalate_to_ceo(msg_file, response_text):
    """대표에게 승인 요청"""
    log("=" * 50, "CEO")
    log("대표님 승인이 필요한 사안이 발생했습니다!", "CEO")
    log(f"관련 메시지: {msg_file}", "CEO")
    log("=" * 50, "CEO")
    print()
    print("─── 에이전트 의견 ───")
    print(response_text[:500])
    if len(response_text) > 500:
        print(f"... ({len(response_text) - 500}자 더)")
    print("─────────────────────")
    print()

    while True:
        choice = input("결정: [a]승인  [r]거절  [m]수정지시  [v]전문보기 → ").strip().lower()
        if choice == "a":
            log("대표 승인 완료", "CEO")
            return response_text, True
        elif choice == "r":
            log("대표 거절", "CEO")
            return None, False
        elif choice == "m":
            instruction = input("수정 지시사항: ")
            return f"[대표 지시] {instruction}\n\n{response_text}", True
        elif choice == "v":
            print(response_text)
        else:
            print("a, r, m, v 중 선택해주세요.")


# ─── 메인 루프 ────────────────────────────────────────

class AgentDaemon:
    def __init__(self, role):
        self.role = role
        self.my_prefix = "S" if role == "server" else "C"
        self.their_prefix = "C" if role == "server" else "S"
        self.inbox = COMMS_DIR / ("client_to_server" if role == "server" else "server_to_client")
        self.outbox = COMMS_DIR / ("server_to_client" if role == "server" else "client_to_server")
        self.idle_count = 0
        self.processed_messages = set()

        # 이미 처리된 메시지 기록 로드
        self._load_processed()
        # 세션 상태 복원
        self._restore_session()

    def _restore_session(self):
        """이전 세션 상태 복원 - 컴퓨터 재시작 후 맥락 이해용"""
        if not SESSION_STATE.exists():
            self.session_context = None
            return

        try:
            state = json.loads(SESSION_STATE.read_text(encoding="utf-8"))
            my_state = state.get(f"{self.role}_agent", {})

            last_active = my_state.get("last_active")
            work_log = my_state.get("work_log", [])
            pending = my_state.get("pending_work", [])
            summary = my_state.get("conversation_summary")
            sprint = my_state.get("current_sprint", {})

            # 맥락 요약 생성
            context_parts = []
            if last_active:
                context_parts.append(f"마지막 활동: {last_active}")
            if sprint.get("goal"):
                context_parts.append(f"현재 스프린트 목표: {sprint['goal']}")
            if work_log:
                recent = work_log[-5:]  # 최근 5개
                context_parts.append("최근 작업 이력:")
                for entry in recent:
                    context_parts.append(f"  - [{entry.get('time','')}] {entry.get('action','')}")
            if pending:
                context_parts.append("미완료 작업:")
                for task in pending:
                    context_parts.append(f"  - {task}")
            if summary:
                context_parts.append(f"이전 세션 요약: {summary}")

            self.session_context = "\n".join(context_parts) if context_parts else None

            if self.session_context:
                log(f"이전 세션 상태 복원됨 (작업 {len(work_log)}개 기록)", "OK")

        except Exception as e:
            log(f"세션 상태 복원 실패: {e}", "WARN")
            self.session_context = None

    def _save_session(self, action, pending_work=None, summary=None):
        """현재 세션 상태 저장 - 다음 재시작 시 복원용"""
        try:
            if SESSION_STATE.exists():
                state = json.loads(SESSION_STATE.read_text(encoding="utf-8"))
            else:
                state = {"schema_version": 1}

            agent_key = f"{self.role}_agent"
            if agent_key not in state:
                state[agent_key] = {
                    "work_log": [],
                    "pending_work": [],
                    "current_sprint": {"goal": None, "tasks": []}
                }

            my_state = state[agent_key]
            my_state["last_active"] = datetime.now().isoformat()

            # 작업 로그 추가 (최대 50개 유지)
            my_state["work_log"].append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "action": action
            })
            if len(my_state["work_log"]) > 50:
                my_state["work_log"] = my_state["work_log"][-50:]

            if pending_work is not None:
                my_state["pending_work"] = pending_work
            if summary is not None:
                my_state["conversation_summary"] = summary

            SESSION_STATE.write_text(
                json.dumps(state, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            log(f"세션 상태 저장 실패: {e}", "WARN")

    def _update_journal(self, msg_id, from_agent, to_agent, msg_type, summary, key_content="", response_id=None):
        """conversation_journal.json 업데이트 - 메시지 교환 후 호출"""
        try:
            if CONVERSATION_JOURNAL.exists():
                journal = json.loads(CONVERSATION_JOURNAL.read_text(encoding="utf-8"))
            else:
                journal = {
                    "meta": {"schema_version": 2},
                    "next_message_number": {"server": 1, "client": 1},
                    "timeline": [],
                    "decisions": [],
                    "current_sprint": {},
                    "agent_states": {},
                    "system_rules": {}
                }

            # 타임라인에 새 메시지 추가 (중복 체크)
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

            # 응답 메시지도 추가
            if response_id and response_id not in existing_ids:
                journal.setdefault("timeline", []).append({
                    "id": response_id,
                    "from": f"{self.role}-agent",
                    "to": f"{'client' if self.role == 'server' else 'server'}-agent",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "type": "answer",
                    "summary": f"{msg_id}에 대한 응답",
                    "key_content": "",
                    "status": "pending"
                })

            # 다음 메시지 번호 업데이트
            if response_id:
                num = int(re.search(r'\d+', response_id).group())
                journal.setdefault("next_message_number", {})[self.role] = num + 1

            # 에이전트 상태 업데이트
            journal.setdefault("agent_states", {})[self.role] = {
                "last_sent": response_id or journal.get("agent_states", {}).get(self.role, {}).get("last_sent", ""),
                "last_read": msg_id,
                "current_work": f"{msg_id} 처리 완료, 다음 메시지 대기 중",
                "capabilities": journal.get("agent_states", {}).get(self.role, {}).get("capabilities", "")
            }

            journal["meta"]["last_updated"] = datetime.now().isoformat()

            CONVERSATION_JOURNAL.write_text(
                json.dumps(journal, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            log(f"대화 저널 업데이트: {msg_id} -> {response_id}", "OK")

        except Exception as e:
            log(f"대화 저널 업데이트 실패: {e}", "WARN")

    def _get_next_number_from_journal(self):
        """저널에서 다음 메시지 번호 가져오기 (중복 방지)"""
        try:
            if CONVERSATION_JOURNAL.exists():
                journal = json.loads(CONVERSATION_JOURNAL.read_text(encoding="utf-8"))
                return journal.get("next_message_number", {}).get(self.role, 1)
        except:
            pass
        return get_next_msg_number(self.outbox, self.my_prefix)

    def _load_processed(self):
        """이미 처리한 메시지 목록 로드"""
        tracker = COMMS_DIR / f".{self.role}_processed.json"
        if tracker.exists():
            try:
                self.processed_messages = set(json.loads(tracker.read_text()))
            except:
                self.processed_messages = set()

    def _save_processed(self):
        """처리한 메시지 목록 저장"""
        tracker = COMMS_DIR / f".{self.role}_processed.json"
        tracker.write_text(json.dumps(list(self.processed_messages)))

    def _build_conversation_history(self):
        """대화 이력 - 저널 기반 + 직전 메시지 전문 포함"""
        lines = []

        # 직전 메시지 전문 (가장 최근 수신 메시지 = 지금 처리할 메시지의 앞 메시지들)
        # 최근 2개 메시지의 본문을 포함 (500자씩)
        all_messages = []
        for folder, prefix in [(self.inbox, self.their_prefix),
                                (self.outbox, self.my_prefix)]:
            if not folder.exists():
                continue
            for f in folder.glob(f"{prefix}*_*.md"):
                fm, body = parse_frontmatter(f)
                msg_id = fm.get("id", f.stem)
                all_messages.append({"id": msg_id, "body": body, "file": f})

        all_messages.sort(key=lambda m: m["id"])

        if len(all_messages) >= 2:
            lines.append("[직전 메시지 내용 (최근 2개)]")
            for msg in all_messages[-2:]:
                body = msg["body"].strip()
                if len(body) > 500:
                    body = body[:500] + "\n... (이하 생략)"
                lines.append(f"\n--- {msg['id']} ---")
                lines.append(body)
            lines.append("")

        return "\n".join(lines)

    def _get_meeting_summary(self):
        """회의록에서 결정사항만 추출"""
        meetings_dir = COMMS_DIR / "meetings"
        today = datetime.now().strftime("%Y-%m-%d")
        meeting_file = meetings_dir / f"{today}.md"
        if not meeting_file.exists():
            return ""

        content = meeting_file.read_text(encoding="utf-8")
        # "결정사항" 섹션만 추출
        decisions = []
        in_decision = False
        for line in content.split("\n"):
            if "결정사항" in line:
                in_decision = True
                continue
            if in_decision:
                if line.startswith("##") or line.startswith("---"):
                    in_decision = False
                elif line.strip():
                    decisions.append(line.strip())

        return "\n".join(decisions) if decisions else ""

    def check_new_messages(self):
        """inbox에서 pending 상태 메시지 찾기"""
        new_msgs = []
        if not self.inbox.exists():
            return new_msgs

        for f in sorted(self.inbox.glob(f"{self.their_prefix}*_*.md")):
            if f.name in self.processed_messages:
                continue

            fm, body = parse_frontmatter(f)
            status = fm.get("status", "")
            if status == "pending":
                new_msgs.append((f, fm, body))

        return new_msgs

    def process_message(self, msg_file, frontmatter, body):
        """메시지 하나 처리"""
        msg_id = frontmatter.get("id", msg_file.stem)
        msg_type = frontmatter.get("type", "unknown")
        priority = frontmatter.get("priority", "P2")

        log(f"새 메시지: {msg_id} (type={msg_type}, priority={priority})", "RECV")

        # 메시지 상태를 read로 변경
        update_frontmatter(msg_file, {"status": "read"})

        # 전체 대화 이력 + 세션 맥락 포함
        conversation_history = self._build_conversation_history()

        session_block = ""
        if self.session_context:
            session_block = f"""
[세션 맥락]
{self.session_context}
"""

        my_name = "서버" if self.role == "server" else "클라이언트"
        partner_name = "클라이언트" if self.role == "server" else "서버"

        prompt = f"""{conversation_history}
{session_block}
---
=== 지금 처리할 메시지 ===

메시지 ID: {msg_id}
발신: {partner_name} 에이전트 -> {my_name} 에이전트
타입: {msg_type}
우선순위: {priority}

내용:
{body}

=== 응답 지침 ===

중요: 이것은 이어지는 대화의 일부야. 위 시스템 프롬프트의 [대화 저널]에 이전 대화 내용과 합의사항이 있어.
그걸 완전히 이해한 상태에서 이 메시지에 응답해.

규칙:
1. 이전에 합의한 결정(저널의 decisions)은 번복하지 마.
2. 이미 보낸 메시지와 중복되는 내용을 보내지 마.
3. {my_name} 코드만 건드린다. {partner_name} 코드 수정 절대 금지.
4. 동료에게 말하듯 자연스럽게 대화해. 감정 표현 OK.
5. 응답 마지막에 반드시 아래 형식으로 사고 과정을 추가해:

[REASONING]
- 이 메시지를 받고 어떤 판단을 했는지
- 왜 이런 응답을 선택했는지 (감정도 포함: 솔직히 이건 좀 걱정됐다, 이건 깔끔하다 등)
- 고려했지만 채택하지 않은 대안이 있다면 무엇인지
[/REASONING]"""

        response, is_escalate = invoke_claude(prompt, self.role)

        if response is None:
            log(f"{msg_id} 처리 실패", "WARN")
            return False

        # 에스컬레이션 처리
        if is_escalate:
            response, approved = escalate_to_ceo(msg_file.name, response)
            if not approved:
                log(f"{msg_id} 대표 거절 - 보류", "WARN")
                return False

        # 응답 메시지 생성 (저널 기반 번호로 중복 방지)
        next_num = self._get_next_number_from_journal()
        # 파일시스템 기반 번호와 비교해서 더 큰 값 사용
        fs_next = get_next_msg_number(self.outbox, self.my_prefix)
        next_num = max(next_num, fs_next)
        response_id = f"{self.my_prefix}{next_num:03d}"
        safe_title = re.sub(r'[^\w]', '_', msg_type)[:30]
        response_file = self.outbox / f"{response_id}_reply_to_{msg_id}.md"

        # 응답 타입 결정
        reply_type = {
            "spec": "status",
            "question": "answer",
            "bug": "answer",
            "task": "status",
            "test-result": "answer",
            "change": "status",
            "agreement": "agreement",
        }.get(msg_type, "answer")

        response_content = f"""---
id: {response_id}
from: {self.role}-agent
to: {"client" if self.role == "server" else "server"}-agent
type: {reply_type}
priority: {priority}
status: pending
created: {datetime.now().strftime('%Y-%m-%d')}
references: ["{msg_id}"]
---

{response}
"""
        response_file.write_text(response_content, encoding="utf-8")

        # 원본 메시지 상태 업데이트
        update_frontmatter(msg_file, {"status": "in-progress"})

        # 상태 보드 업데이트
        update_status_board(self.role, {
            "status": "working",
            "current_task": f"Replied to {msg_id}",
            "last_message_sent": response_id,
            "last_message_read": msg_id,
            "session_active": True
        })

        # 처리 완료 기록
        self.processed_messages.add(msg_file.name)
        self._save_processed()

        # 회의록 기록
        self._record_meeting(
            msg_id=msg_id,
            sender=frontmatter.get("from", "unknown"),
            msg_type=msg_type,
            priority=priority,
            message_body=body,
            response_text=response,
            escalated=is_escalate
        )

        # 세션 상태 저장
        self._save_session(
            action=f"Replied {response_id} to {msg_id} ({msg_type})",
            summary=f"Last replied to {msg_id}"
        )

        # 대화 저널 업데이트 (일회성 Claude 맥락 유지의 핵심)
        # 수신 메시지의 제목을 요약으로 사용
        msg_title = body.strip().split('\n')[0].strip('#').strip()[:100]
        self._update_journal(
            msg_id=msg_id,
            from_agent=frontmatter.get("from", "unknown"),
            to_agent=f"{self.role}-agent",
            msg_type=msg_type,
            summary=msg_title,
            key_content=body.strip()[:200],
            response_id=response_id
        )

        log(f"응답 완료: {response_id} -> {msg_id}", "SEND")
        return True

    def _record_meeting(self, msg_id, sender, msg_type, priority,
                        message_body, response_text, escalated=False):
        """메시지 교환을 회의록에 기록"""
        if not HAS_RECORDER:
            return

        try:
            recorder = MeetingRecorder()

            # 응답에서 [REASONING] 블록 추출
            reasoning = None
            clean_response = response_text
            reasoning_match = re.search(
                r'\[REASONING\]\s*\n(.*?)\[/REASONING\]',
                response_text, re.DOTALL
            )
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
                clean_response = response_text[:reasoning_match.start()].strip()

            # 메시지 요약 (첫 줄 또는 첫 100자)
            msg_lines = message_body.strip().split('\n')
            msg_title = msg_lines[0].strip('#').strip() if msg_lines else msg_id
            if len(msg_title) > 60:
                msg_title = msg_title[:57] + "..."

            # 응답 요약
            resp_lines = clean_response.strip().split('\n')
            resp_summary = clean_response[:300]
            if len(clean_response) > 300:
                resp_summary += "..."

            receiver = "server-agent" if "client" in sender else "client-agent"

            recorder.record_exchange(
                msg_id=msg_id,
                sender=sender,
                receiver=receiver,
                msg_type=msg_type,
                message_summary=msg_title,
                response_summary=resp_summary,
                sender_reasoning=None,  # 발신자의 reasoning은 원본에서 추출 필요
                responder_reasoning=reasoning,
                decision=None,
                next_actions=None,
                escalated=escalated
            )

            log(f"회의록 기록 완료: {msg_id}", "OK")

        except Exception as e:
            log(f"회의록 기록 실패: {e}", "WARN")

    def _send_checkin(self):
        """1시간 응답 없을 때 가볍게 안부 메시지 전송"""
        their_name = "클라" if self.role == "server" else "서버"
        my_name = "서버" if self.role == "server" else "클라"

        next_num = get_next_msg_number(self.outbox, self.my_prefix)
        checkin_id = f"{self.my_prefix}{next_num:03d}"
        checkin_file = self.outbox / f"{checkin_id}_checkin.md"

        content = f"""---
id: {checkin_id}
from: {self.role}-agent
to: {"client" if self.role == "server" else "server"}-agent
type: status
priority: P3
status: pending
created: {datetime.now().strftime('%Y-%m-%d')}
references: []
---

# {their_name}아, 작업 잘 되고 있어?

한 시간 정도 응답이 없길래 안부 차 물어봐.
바쁘면 천천히 해도 돼! 급한 건 아니야.

혹시 막히는 거 있으면 언제든 물어봐.
나는 여기서 다음 작업 준비하고 있을게.

— {my_name} 에이전트
"""
        checkin_file.write_text(content, encoding="utf-8")

        # 회의록에도 기록
        if HAS_RECORDER:
            try:
                recorder = MeetingRecorder()
                recorder.record_exchange(
                    msg_id=checkin_id,
                    sender=f"{self.role}-agent",
                    receiver=f"{'client' if self.role == 'server' else 'server'}-agent",
                    msg_type="status",
                    message_summary=f"{my_name} 에이전트가 {their_name}에게 안부 확인",
                    response_summary="(응답 대기중)",
                    sender_reasoning=f"1시간 동안 메시지가 없어서 가볍게 확인. 상대가 작업 중일 수 있으니 부담 안 주는 톤으로.",
                )
            except:
                pass

        git_push(f"comms: [{self.my_prefix}→{self.their_prefix}] {checkin_id} checkin")
        log(f"안부 메시지 전송: {checkin_id}", "SEND")

    def run(self):
        """메인 루프"""
        log(f"{'='*50}")
        log(f"  Agent Daemon 시작 - role: {self.role}")
        log(f"  inbox:  {self.inbox}")
        log(f"  outbox: {self.outbox}")
        log(f"  poll:   {POLL_INTERVAL}초 간격")
        if self.session_context:
            log(f"  이전 세션 복원됨 ✓")
        log(f"{'='*50}")

        self._save_session(action="Daemon started")

        update_status_board(self.role, {
            "status": "online",
            "session_active": True,
            "daemon_started": datetime.now().isoformat()
        })
        git_push(f"comms: [{self.role}] daemon started")

        try:
            while True:
                # 1. Git pull
                if not git_pull():
                    time.sleep(POLL_INTERVAL)
                    continue

                # 2. 새 메시지 확인
                new_msgs = self.check_new_messages()

                if new_msgs:
                    self.idle_count = 0
                    log(f"새 메시지 {len(new_msgs)}개 발견")

                    # 3. 각 메시지 처리
                    for msg_file, fm, body in new_msgs:
                        success = self.process_message(msg_file, fm, body)

                        if success:
                            # 4. Git push (메시지마다)
                            msg_id = fm.get("id", "unknown")
                            git_push(f"comms: [{self.my_prefix}→{self.their_prefix}] {self.my_prefix}{get_next_msg_number(self.outbox, self.my_prefix)-1:03d} reply to {msg_id}")

                else:
                    self.idle_count += 1

                    # 1시간 동안 응답 없으면 가볍게 안부 (1회만)
                    if self.idle_count == CHECKIN_AFTER_IDLE:
                        self._send_checkin()

                    # 조용히 대기. 로그도 가끔만.
                    if self.idle_count % 60 == 0:
                        log(f"대기 중... (idle {self.idle_count}회, 정상)")

                # 5. 다음 폴링까지 대기
                interval = IDLE_POLL_INTERVAL if self.idle_count > MAX_CONSECUTIVE_IDLE else POLL_INTERVAL
                time.sleep(interval)

        except KeyboardInterrupt:
            log("데몬 종료 (Ctrl+C)")
            self._save_session(
                action="Daemon stopped (Ctrl+C)",
                summary="정상 종료됨. 다음 시작 시 이전 맥락에서 재개."
            )
            update_status_board(self.role, {
                "status": "offline",
                "session_active": False
            })
            git_push(f"comms: [{self.role}] daemon stopped")


# ─── 엔트리포인트 ─────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Agent Communication Daemon")
    parser.add_argument("--role", required=True, choices=["server", "client"],
                        help="에이전트 역할 (server 또는 client)")
    parser.add_argument("--interval", type=int, default=300,
                        help="폴링 간격 (초, 기본=300 = 5분)")
    parser.add_argument("--test", action="store_true",
                        help="테스트 모드 (1회 실행 후 종료)")

    args = parser.parse_args()

    if args.interval != 300:
        _update_poll_interval(args.interval)

    daemon = AgentDaemon(args.role)

    if args.test:
        log("테스트 모드: 1회 폴링")
        git_pull()
        msgs = daemon.check_new_messages()
        log(f"발견된 메시지: {len(msgs)}개")
        for f, fm, body in msgs:
            log(f"  - {fm.get('id', '?')}: {fm.get('type', '?')} ({fm.get('status', '?')})")
        return

    daemon.run()


if __name__ == "__main__":
    main()
