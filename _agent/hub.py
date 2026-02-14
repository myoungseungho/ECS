"""
이벤트 기반 에이전트 허브 v2.0
===============================
폴링 제거 → 이벤트 구동
idle 낭비 제거 → 스마트 스케줄링
태스크 소진 → 자기증식 (GDD 분해 + 창의적 아이디어)
단독 작업 → 협업 라운드 (서버-클라 티키타카)

사용법:
  python _agent/hub.py

동작 모드:
  RESPOND   — 상대방 메시지 수신 → 즉시 응답
  WORK      — pending_tasks 중 unblocked 작업 수행
  DECOMPOSE — 태스크 소진 → GDD에서 다음 섹션 분해
  IDEATE    — GDD 태스크 전부 완료 → 새 아이디어 창출 + GDD 확장
  COLLAB    — 서버가 제안 → 클라가 검토 → 합의 → 태스크 생성
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
import re

# Windows 리다이렉트 시 버퍼링 방지
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

# ============================================================
# 설정
# ============================================================

MAX_CLAUDE_TIMEOUT = 900   # 15분
IDLE_LONG_SLEEP = 1800     # 30분 — 극단적으로 할 일 없을 때만
COLLAB_INTERVAL = 5        # 5세션마다 협업 라운드
MAX_CONSECUTIVE_IDLE = 2   # 연속 idle 횟수 제한

ROLES = {
    "server": {
        "inbox": "_comms/client_to_server",
        "outbox": "_comms/server_to_client",
        "state_file": "_context/server_state.yaml",
        "claude_md": "Servers/CLAUDE.md",
    },
    "client": {
        "inbox": "_comms/server_to_client",
        "outbox": "_comms/client_to_server",
        "state_file": "_context/client_state.yaml",
        "claude_md": "UnityClient/GameClient/CLAUDE.md",
    },
}


# ============================================================
# Git 유틸
# ============================================================

def git_run(args, cwd):
    """git 명령 실행. 실패해도 안전 반환."""
    try:
        result = subprocess.run(
            ["git"] + args, cwd=cwd,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
        stdout = result.stdout.strip() if result.stdout else ""
        stderr = result.stderr.strip() if result.stderr else ""
        return result.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        return 1, "", "timeout"
    except Exception as e:
        return 1, "", str(e)


def fix_git_index(root):
    """git 인덱스 손상/잠김 자동 복구"""
    # 1. index.lock 삭제 (다른 git 프로세스가 남긴 잠금)
    lock_path = os.path.join(root, ".git", "index.lock")
    if os.path.exists(lock_path):
        try:
            os.remove(lock_path)
            log("  [FIX] removed .git/index.lock")
        except Exception as e:
            log(f"  [FIX] failed to remove index.lock: {e}")

    # 2. 진행 중인 merge/rebase 정리
    merge_head = os.path.join(root, ".git", "MERGE_HEAD")
    if os.path.exists(merge_head):
        git_run(["merge", "--abort"], root)
        log("  [FIX] aborted pending merge")

    rebase_dir = os.path.join(root, ".git", "rebase-merge")
    if os.path.exists(rebase_dir):
        git_run(["rebase", "--abort"], root)
        log("  [FIX] aborted pending rebase")

    # 3. 인덱스 리셋 (작업 트리는 유지, 인덱스만 HEAD로 복원)
    code, _, _ = git_run(["reset", "--mixed", "HEAD"], root)
    if code == 0:
        log("  [FIX] git index reset OK")
    else:
        # 최후 수단: 인덱스 파일 삭제 후 다시 reset
        index_path = os.path.join(root, ".git", "index")
        try:
            if os.path.exists(index_path):
                os.remove(index_path)
                log("  [FIX] deleted corrupted .git/index")
            git_run(["reset", "--mixed", "HEAD"], root)
            log("  [FIX] git index rebuilt from scratch")
        except Exception as e:
            log(f"  [FIX] last resort failed: {e}")


def detect_role_from_root(root):
    """이 머신이 client인지 server인지 판별"""
    client_state = os.path.join(root, "_context", "client_state.yaml")
    if os.path.exists(client_state):
        with open(client_state, "r", encoding="utf-8") as f:
            content = f.read()
        if os.path.basename(root).upper() in content.upper() or "client" in content[:200]:
            return "client"
    return "server"


def auto_resolve_conflicts(root):
    """충돌 파일을 소유권 기반으로 자동 해결"""
    code, status_out, _ = git_run(["status", "--porcelain"], root)
    if code != 0:
        return False

    my_role = detect_role_from_root(root)
    resolved_any = False

    for line in status_out.split("\n"):
        line = line.strip()
        if not line:
            continue

        # UU = both modified, AA = both added
        if not (line.startswith("UU ") or line.startswith("AA ")):
            continue

        fpath = line[3:].strip()
        resolved_any = True

        # 소유권 기반 전략
        if "client_state.yaml" in fpath:
            strategy = "ours" if my_role == "client" else "theirs"
        elif "server_state.yaml" in fpath:
            strategy = "ours" if my_role == "server" else "theirs"
        elif "conversation_journal" in fpath:
            strategy = "theirs"
        elif fpath.startswith("UnityClient/"):
            strategy = "ours" if my_role == "client" else "theirs"
        elif fpath.startswith("Servers/"):
            strategy = "ours" if my_role == "server" else "theirs"
        elif fpath.startswith("_comms/"):
            strategy = "theirs"
        else:
            strategy = "ours"

        log(f"  [RESOLVE] {fpath} -> {strategy}")
        git_run(["checkout", f"--{strategy}", fpath], root)
        git_run(["add", fpath], root)

    return resolved_any


def git_pull(root):
    """stash -> pull (merge) -> auto-resolve conflicts -> stash pop
    인덱스 손상 시 자동 복구 후 재시도."""

    # 0. 인덱스 상태 사전 점검
    pre_code, _, pre_err = git_run(["status", "--porcelain"], root)
    if pre_code != 0:
        log("  [FIX] git status failed — fixing index before pull")
        fix_git_index(root)

    # 1. unstaged 변경 stash (log 파일 등 제외하기 위해 tracked만)
    _, status_out, _ = git_run(["status", "--porcelain"], root)
    has_changes = bool(status_out.strip())
    if has_changes:
        git_run(["stash", "--include-untracked"], root)

    # 2. rebase 대신 merge 사용 (충돌 해결이 더 쉬움)
    code, out, err = git_run(["pull", "--no-rebase"], root)

    # 3. 충돌/에러 처리
    combined = f"{out} {err}"
    if code != 0:
        # 3a. 인덱스 손상 계열 에러 → 복구 후 재시도
        index_errors = ["could not write index", "index.lock", "unable to write",
                        "unmerged", "not possible", "unstaged"]
        if any(ie in combined.lower() for ie in index_errors):
            log(f"  [FIX] index error detected, auto-recovering...")
            fix_git_index(root)
            # stash 다시 (fix_git_index가 reset하면서 stash 상태가 바뀔 수 있음)
            _, status_out2, _ = git_run(["status", "--porcelain"], root)
            if status_out2 and status_out2.strip():
                git_run(["stash", "--include-untracked"], root)
                has_changes = True
            else:
                has_changes = False
            # pull 재시도
            code, out, err = git_run(["pull", "--no-rebase"], root)
            combined = f"{out} {err}"

        # 3b. merge 충돌 → 소유권 기반 자동 해결
        if code != 0 and ("CONFLICT" in combined or "conflict" in combined.lower()):
            log(f"  [CONFLICT] auto-resolving...")
            resolved = auto_resolve_conflicts(root)
            if resolved:
                git_run(["commit", "--no-edit", "-m", "auto-merge: conflict resolved by hub"], root)
                code = 0
            else:
                log(f"  [WARN] could not auto-resolve, aborting merge")
                git_run(["merge", "--abort"], root)

        # 3c. rebase 상태 잔존 → abort 후 merge로
        elif code != 0 and "rebase" in combined.lower():
            git_run(["rebase", "--abort"], root)
            code, out, err = git_run(["pull", "--no-rebase"], root)
            combined2 = f"{out} {err}"
            if code != 0 and ("CONFLICT" in combined2 or "conflict" in combined2.lower()):
                resolved = auto_resolve_conflicts(root)
                if resolved:
                    git_run(["commit", "--no-edit", "-m", "auto-merge: conflict resolved by hub"], root)
                    code = 0
                else:
                    git_run(["merge", "--abort"], root)

    # 4. stash pop (실패해도 무시 - 대부분 log 파일 충돌)
    if has_changes:
        pop_code, _, pop_err = git_run(["stash", "pop"], root)
        if pop_code != 0:
            log(f"  [WARN] stash pop failed, dropping stash")
            git_run(["checkout", "--", "."], root)
            git_run(["stash", "drop"], root)

    return code == 0


def git_push(root, message):
    """add -> commit -> push, 실패 시 pull+resolve 후 재시도"""
    git_run(["add", "-A"], root)
    code, out, _ = git_run(["status", "--porcelain"], root)
    if not out or not out.strip():
        return False

    git_run(["commit", "-m", message], root)

    # push 시도
    code, _, err = git_run(["push"], root)
    if code != 0:
        log(f"  [PUSH] rejected, pulling and retrying...")
        pull_ok = git_pull(root)
        if pull_ok:
            # pull 중 새 merge commit이 생겼을 수 있으므로 다시 add
            git_run(["add", "-A"], root)
            _, status_check, _ = git_run(["status", "--porcelain"], root)
            if status_check and status_check.strip():
                git_run(["commit", "-m", f"{message} (after merge)"], root)
            code, _, err = git_run(["push"], root)
            if code != 0:
                log(f"  [PUSH] still failed: {err[:100]}")
        else:
            log(f"  [PUSH] pull failed, cannot push")

    return code == 0


# ============================================================
# 로깅
# ============================================================

LOG_FILE = None

def log(msg):
    """콘솔 + 파일 동시 로깅"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    if LOG_FILE:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except:
            pass


# ============================================================
# 상태 스캔
# ============================================================

def get_processed_messages(state_file, root):
    """state.yaml에서 processed_messages 읽기"""
    path = os.path.join(root, state_file)
    if not os.path.exists(path):
        return set()
    processed = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith('- "') and line.endswith('"'):
                processed.add(line[3:-1])
    return processed


def scan_new_messages(role, root):
    """새 메시지 스캔"""
    config = ROLES[role]
    processed = get_processed_messages(config["state_file"], root)
    inbox_path = os.path.join(root, config["inbox"])
    if not os.path.exists(inbox_path):
        return []

    new_msgs = []
    for fname in sorted(os.listdir(inbox_path)):
        if not fname.endswith(".md"):
            continue
        msg_id = fname.split("_")[0]
        if msg_id not in processed:
            new_msgs.append((msg_id, os.path.join(config["inbox"], fname)))
    return new_msgs


def get_unblocked_tasks(role, root):
    """state.yaml에서 blocked: false인 태스크 확인"""
    config = ROLES[role]
    path = os.path.join(root, config["state_file"])
    if not os.path.exists(path):
        return []

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 간단 파싱: blocked: false인 태스크 찾기
    tasks = []
    in_pending = False
    current_task = {}
    for line in content.split("\n"):
        if "pending_tasks:" in line:
            in_pending = True
            continue
        if in_pending:
            if line.strip().startswith("- id:"):
                if current_task and not current_task.get("blocked", False):
                    tasks.append(current_task)
                current_task = {"id": line.split(":", 1)[1].strip().strip('"')}
            elif "blocked: false" in line:
                current_task["blocked"] = False
            elif "blocked: true" in line:
                current_task["blocked"] = True
            elif line.strip().startswith("desc:"):
                current_task["desc"] = line.split(":", 1)[1].strip().strip('"')
            elif line.strip() and not line.strip().startswith("-") and not line.strip().startswith("#") and ":" in line and not line.startswith(" "):
                # 새 섹션 시작 → pending_tasks 끝
                if current_task and not current_task.get("blocked", False):
                    tasks.append(current_task)
                in_pending = False

    if in_pending and current_task and not current_task.get("blocked", False):
        tasks.append(current_task)

    # respond_to_client 같은 수동 응답 태스크 제외
    return [t for t in tasks if "respond" not in t.get("id", "")]


def check_ask_user_pending(root):
    """ask_user.yaml에 미답변 질문 있는지 (주석 제외)"""
    path = os.path.join(root, "_context", "ask_user.yaml")
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "status: pending" in stripped:
                return True
    return False


# ============================================================
# Claude 실행
# ============================================================

def run_claude(prompt, root, label=""):
    """Claude CLI 비대화형 실행"""
    log(f"  CLAUDE [{label}] start ({len(prompt)} chars)")
    start = time.time()

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--allowedTools",
             "Read,Write,Edit,Bash,Glob,Grep,Task"],
            cwd=root,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=MAX_CLAUDE_TIMEOUT,
            env=env,
        )
        elapsed = time.time() - start
        log(f"  CLAUDE [{label}] done ({elapsed:.0f}s, exit={result.returncode})")

        # 로그 저장
        log_path = os.path.join(root, "_agent", "last_run.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"=== {datetime.datetime.now().isoformat()} ===\n")
            f.write(f"Label: {label}\n")
            f.write(f"Exit: {result.returncode}\n")
            f.write(f"Duration: {elapsed:.0f}s\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout[:8000] if result.stdout else "(empty)")
            f.write("\n\n=== STDERR ===\n")
            f.write(result.stderr[:3000] if result.stderr else "(empty)")

        return result.returncode == 0, result.stdout or ""
    except subprocess.TimeoutExpired:
        log(f"  CLAUDE [{label}] TIMEOUT ({MAX_CLAUDE_TIMEOUT}s)")
        return False, ""
    except FileNotFoundError:
        log("  [ERROR] claude CLI not found in PATH")
        return False, ""


# ============================================================
# 프롬프트 빌더
# ============================================================

def build_agent_prompt(role, trigger, root):
    """에이전트 실행 프롬프트 (RESPOND / WORK)"""
    config = ROLES[role]
    new_msgs = scan_new_messages(role, root)
    msg_files = "\n".join([f"  - {p}" for _, p in new_msgs]) if new_msgs else "  (없음)"

    return f"""
# 에이전트 자율 실행 -- 컨텍스트 복원 필수

## 0. 반드시 먼저 읽을 파일
1. `{config["state_file"]}` -- 영속 상태
2. `{config["claude_md"]}` -- 프로젝트 규칙
3. `_gdd/README.md` -- GDD 시스템 개요

## 1. 실행 이유
{trigger}

## 2. 새 메시지
{msg_files}

## 3. 작업 지침
1. state 파일의 pending_tasks에서 blocked: false인 것을 우선순위 순으로 작업
2. 코드 작성 후 반드시 검증 실행
3. 서버/클라 간 통신이 필요하면 `{config["outbox"]}/` 폴더에 메시지 파일 생성
4. 대표님 결정이 필요하면 `_context/ask_user.yaml`에 질문 작성

## 4. 완료 후 반드시 할 것
1. `{config["state_file"]}` 업데이트 (last_session, current_status, completed, pending_tasks, processed_messages)
2. 새로 생긴 할 일이 있으면 pending_tasks에 추가
3. 상대방에게 전달할 내용이 있으면 outbox에 메시지 생성

## 5. 하지 말 것
- state 파일 읽지 않고 작업 시작
- git push (hub.py가 합니다)
""".strip()


def build_decompose_prompt(role, root):
    """태스크 분해 프롬프트 — GDD에서 미완료 섹션 찾아서 세부 태스크 생성"""
    config = ROLES[role]
    return f"""
# 태스크 자동 분해 — {role} 에이전트

## 0. 먼저 읽을 파일
1. `{config["state_file"]}` -- 현재 상태 (completed + pending_tasks 확인)
2. `_gdd/game_design.yaml` -- 전체 게임 설계
3. `_gdd/README.md` -- GDD 구조

## 1. 목표
현재 pending_tasks가 전부 완료되었거나 blocked 상태입니다.
GDD에서 아직 구현되지 않은 {role} 태스크를 찾아 세부 서브태스크로 분해하세요.

## 2. 작업 방법
1. `_gdd/game_design.yaml`에서 {role}_tasks를 전수 스캔
2. `{config["state_file"]}`의 completed 목록과 대조
3. 미완료 태스크를 찾아 각각 5~15개의 구체적 서브태스크로 분해
4. 각 서브태스크는 Claude 1세션(15분 이내)에 완료 가능한 크기
5. pending_tasks에 추가 (blocked: false)

## 3. 서브태스크 형식
- id: "원본ID_sub01"
- desc: "구체적인 작업 내용 (파일명, 함수명 포함)"
- priority: P0/P1/P2
- blocked: false
- estimated_minutes: 10

## 4. 상대방 작업도 확인
{role}의 태스크를 분해하면서, 상대방에게 필요한 작업이 있으면
outbox에 메시지로 요청하세요.

## 5. state 파일 업데이트 필수
""".strip()


def build_ideate_prompt(root):
    """창의적 아이디어 생성 프롬프트 — 게임을 사랑하는 디자이너 모드"""
    return """
# 게임 디자이너 브레인스토밍 세션

## 당신의 역할
당신은 이 게임(무협 MMORPG)을 진심으로 사랑하는 시니어 게임 디자이너입니다.
플레이어로서 "이 게임에 이런 게 있으면 진짜 재밌겠다!"라는 관점에서 생각하세요.

## 0. 먼저 읽을 파일
1. `_gdd/game_design.yaml` -- 현재 게임 설계 전체
2. `_gdd/rules/` 폴더의 모든 yaml 파일 -- 세부 규칙
3. `_context/server_state.yaml` -- 서버 진행 현황
4. `_context/client_state.yaml` -- 클라이언트 진행 현황

## 1. 아이디어 발상 관점 (최소 3개, 최대 5개)

다음 중에서 골라서 아이디어를 내세요:

### 재미 요소
- 플레이어가 "와 이거 뭐야" 할 만한 서프라이즈
- 중독성 있는 루프 (수집, 성장, 경쟁)
- 친구랑 같이 하면 더 재밌는 요소

### 시스템 시너지
- 기존 시스템끼리 연결하면 새로운 재미가 나는 조합
  (예: PvP 랭킹 + 문파전, 제작 + 거래소, 탐험 + 도감)
- "이 시스템이 있으니까 저 시스템이 더 의미있어지는" 구조

### 리텐션 (계속 접속하게 만드는 것)
- 일일/주간/월간 콘텐츠
- "내일 또 해야지" 하게 만드는 동기
- 장기 목표 + 단기 보상의 밸런스

### 감성
- 무협 세계관에 몰입하게 하는 요소
- 내 캐릭터에 애착이 생기는 시스템
- "내가 이 세계의 협객이다" 느낌

## 2. 아이디어를 GDD에 반영

각 아이디어마다:
1. `_gdd/game_design.yaml`에 새 섹션 추가 (Phase 적절히 배치)
2. server_tasks와 client_tasks 모두 작성
3. 관련 있는 `_gdd/rules/*.yaml`에 규칙 추가
4. 필요하면 `_gdd/data/` 에 데이터 파일 추가

## 3. 태스크 생성

아이디어를 구현할 구체적인 태스크를 서버/클라 각각 생성:
- `_context/server_state.yaml`의 pending_tasks에 추가
- `_context/client_state.yaml`의 pending_tasks에 추가
- 각 태스크는 15분 이내 완료 가능한 크기

## 4. 상대방에게 알림

- `_comms/server_to_client/`에 "새 아이디어 + 클라 태스크" 메시지 생성
- `_comms/client_to_server/`에 "새 아이디어 + 서버 태스크" 메시지 생성

## 5. 중요 원칙
- 기존 시스템과 모순되지 않게 (GDD 교차 일관성 확인)
- 구현 가능한 수준으로 (환상적이지만 현실적인)
- 무협 세계관에 맞게
- state 파일 업데이트 필수

## 6. git push는 하지 마세요 (hub.py가 합니다)
""".strip()


def build_collab_prompt(proposer, reviewer, topic, root):
    """협업 라운드 — 제안자 프롬프트"""
    config = ROLES[proposer]
    return f"""
# 협업 라운드 — {proposer}의 제안

## 0. 먼저 읽을 파일
1. `{config["state_file"]}`
2. `_gdd/game_design.yaml`
3. 최근 상대방 메시지 (있으면)

## 1. 당신의 역할
{proposer} 에이전트로서, 현재 게임 개발 상황을 보고
{reviewer}에게 다음을 제안하세요:

- 현재 진행 중인 작업에서 개선할 점
- 서로의 작업이 잘 맞물리도록 조율할 점
- 새로운 기능이나 시스템 아이디어

## 2. 제안서 작성
`{ROLES[proposer]["outbox"]}/` 폴더에 메시지 파일을 생성하세요.
형식: [다음번호]_collab_proposal.md

내용:
- 제안 배경 (왜 이게 필요한지)
- 구체적인 제안 내용
- {reviewer}에게 요청하는 것
- 예상 일정

## 3. state 파일 업데이트
""".strip()


# ============================================================
# 스케줄러
# ============================================================

class Action:
    """실행할 액션"""
    def __init__(self, mode, role, data=None):
        self.mode = mode    # RESPOND, WORK, DECOMPOSE, IDEATE, COLLAB
        self.role = role    # "server", "client", "both"
        self.data = data    # 추가 정보

    def __str__(self):
        return f"{self.mode}({self.role})"


def schedule(root, session_count, consecutive_idle):
    """다음 액션 결정 — 우선순위 기반"""

    # Priority 1: 유저 질문 대기 중이면 건너뛰기
    if check_ask_user_pending(root):
        log("  [!!] ask_user.yaml pending -- waiting for user answer")
        return None

    # Priority 2: 새 메시지 응답 (즉시 반응)
    # 이 머신의 역할을 먼저 처리
    my_role = detect_role_from_root(root)
    role_order = [my_role, "server" if my_role == "client" else "client"]
    for role in role_order:
        msgs = scan_new_messages(role, root)
        if msgs:
            msg_ids = [m[0] for m in msgs]
            return Action("RESPOND", role, msg_ids)

    # Priority 3: unblocked 태스크 작업
    for role in role_order:
        tasks = get_unblocked_tasks(role, root)
        if tasks:
            return Action("WORK", role, tasks)

    # Priority 4: 태스크 분해 (태스크 소진 시)
    # 양쪽 다 할 일 없으면 → 분해 시도
    return Action("DECOMPOSE", "server")


def schedule_after_decompose(root, session_count):
    """분해 후에도 할 일 없으면 → 아이디어 or 협업"""

    # 분해로 새 태스크가 생겼는지 확인
    for role in ["server", "client"]:
        tasks = get_unblocked_tasks(role, root)
        if tasks:
            return Action("WORK", role, tasks)

    # 협업 라운드 (N세션마다)
    if session_count % COLLAB_INTERVAL == 0 and session_count > 0:
        return Action("COLLAB", "both")

    # 최종: 창의적 아이디어 생성
    return Action("IDEATE", "both")


# ============================================================
# 메인 허브
# ============================================================

class Hub:
    def __init__(self, root):
        self.root = root
        self.session_count = 0
        self.consecutive_idle = 0
        self.start_time = time.time()
        self.stats = {
            "total_sessions": 0,
            "respond": 0,
            "work": 0,
            "decompose": 0,
            "ideate": 0,
            "collab": 0,
            "pushes": 0,
            "errors": 0,
        }

    def run(self):
        """메인 이벤트 루프"""
        self.print_banner()

        while True:
            try:
                action = self.tick()
                if action:
                    self.consecutive_idle = 0
                else:
                    self.consecutive_idle += 1
                    if self.consecutive_idle >= MAX_CONSECUTIVE_IDLE:
                        # 연속 idle → 분해/아이디어로 전환
                        self.force_creative()
                        self.consecutive_idle = 0
                    else:
                        wait = 60  # 유저 답변 대기 등
                        log(f"  [WAIT] {wait}s...")
                        time.sleep(wait)

            except KeyboardInterrupt:
                self.shutdown()
                break
            except Exception as e:
                log(f"  [ERROR] {e}")
                self.stats["errors"] += 1
                time.sleep(30)

    def tick(self):
        """한 사이클"""
        log("=" * 50)
        elapsed_h = (time.time() - self.start_time) / 3600
        log(f"SESSION #{self.session_count} | {elapsed_h:.1f}h elapsed | "
            f"pushes: {self.stats['pushes']}")

        # 1. Git pull (실패 시 인덱스 복구 후 1회 재시도)
        log("git pull...")
        if not git_pull(self.root):
            log("[WARN] git pull failed, attempting index recovery...")
            fix_git_index(self.root)
            if not git_pull(self.root):
                log("[WARN] git pull still failed after recovery")
                time.sleep(10)
                return None

        # 2. 스케줄
        action = schedule(self.root, self.session_count, self.consecutive_idle)
        if not action:
            return None

        log(f">> {action}")

        # 3. 실행
        success = self.execute(action)

        # 4. Git push
        if success:
            commit_msg = f"hub({action.role}): {action.mode.lower()}"
            if action.data:
                detail = str(action.data)[:50]
                commit_msg += f" -- {detail}"

            pushed = git_push(self.root, commit_msg)
            if pushed:
                self.stats["pushes"] += 1
                log(f"  [PUSH] done")

        self.session_count += 1
        self.stats["total_sessions"] += 1
        self.stats[action.mode.lower()] = self.stats.get(action.mode.lower(), 0) + 1

        return action

    def execute(self, action):
        """액션 실행"""
        if action.mode == "RESPOND":
            msg_ids = action.data
            trigger = f"new messages: {', '.join(msg_ids)}"
            prompt = build_agent_prompt(action.role, trigger, self.root)
            ok, _ = run_claude(prompt, self.root, f"{action.role}/RESPOND")
            return ok

        elif action.mode == "WORK":
            task_descs = [t.get("desc", t.get("id", "?")) for t in action.data[:3]]
            trigger = f"continue work: {'; '.join(task_descs)}"
            prompt = build_agent_prompt(action.role, trigger, self.root)
            ok, _ = run_claude(prompt, self.root, f"{action.role}/WORK")
            return ok

        elif action.mode == "DECOMPOSE":
            # 서버 먼저, 그 다음 클라
            ok1, _ = run_claude(
                build_decompose_prompt("server", self.root),
                self.root, "server/DECOMPOSE"
            )
            if ok1:
                git_push(self.root, "hub(server): decompose tasks")

            ok2, _ = run_claude(
                build_decompose_prompt("client", self.root),
                self.root, "client/DECOMPOSE"
            )

            # 분해 후 다시 스케줄
            if ok1 or ok2:
                next_action = schedule_after_decompose(self.root, self.session_count)
                if next_action and next_action.mode in ("WORK", "COLLAB", "IDEATE"):
                    return self.execute(next_action)
            return ok1 or ok2

        elif action.mode == "IDEATE":
            prompt = build_ideate_prompt(self.root)
            ok, _ = run_claude(prompt, self.root, "IDEATE")
            return ok

        elif action.mode == "COLLAB":
            return self.run_collaboration()

        return False

    def run_collaboration(self):
        """협업 라운드: 서버 제안 → 클라 검토"""
        log("  [COLLAB] server proposes...")
        prompt1 = build_collab_prompt("server", "client", "game improvement", self.root)
        ok1, _ = run_claude(prompt1, self.root, "server/COLLAB-propose")

        if ok1:
            git_push(self.root, "hub(server): collab proposal")
            git_pull(self.root)

            log("  [COLLAB] client reviews...")
            # 클라이언트는 일반 RESPOND로 서버 메시지에 응답
            msgs = scan_new_messages("client", self.root)
            if msgs:
                trigger = f"review server proposal: {[m[0] for m in msgs]}"
                prompt2 = build_agent_prompt("client", trigger, self.root)
                ok2, _ = run_claude(prompt2, self.root, "client/COLLAB-review")
                return ok2

        return ok1

    def force_creative(self):
        """연속 idle 시 강제 창의 모드"""
        log("  [FORCE] consecutive idle -> creative mode")

        # 먼저 분해 시도
        action = Action("DECOMPOSE", "server")
        success = self.execute(action)

        if success:
            git_push(self.root, "hub: force decompose after idle")
        else:
            # 분해도 안 되면 아이디어
            action = Action("IDEATE", "both")
            success = self.execute(action)
            if success:
                git_push(self.root, "hub: force ideation after idle")

    def print_banner(self):
        log("=" * 60)
        log("  Event-Driven Agent Hub v2.0")
        log(f"  Project: {self.root}")
        log(f"  Modes: RESPOND > WORK > DECOMPOSE > IDEATE > COLLAB")
        log(f"  Collab every {COLLAB_INTERVAL} sessions")
        log(f"  Max Claude timeout: {MAX_CLAUDE_TIMEOUT}s")
        log("=" * 60)

    def shutdown(self):
        elapsed_h = (time.time() - self.start_time) / 3600
        log("\n" + "=" * 60)
        log("  Hub shutting down")
        log(f"  Ran for: {elapsed_h:.1f} hours")
        log(f"  Stats: {json.dumps(self.stats, indent=2)}")
        log("=" * 60)

        # 통계 저장
        stats_path = os.path.join(self.root, "_agent", "hub_stats.json")
        try:
            with open(stats_path, "w", encoding="utf-8") as f:
                self.stats["elapsed_hours"] = round(elapsed_h, 2)
                self.stats["ended_at"] = datetime.datetime.now().isoformat()
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except:
            pass


# ============================================================
# 엔트리포인트
# ============================================================

def main():
    global LOG_FILE

    parser = argparse.ArgumentParser(description="Event-Driven Agent Hub v2.0")
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    args = parser.parse_args()

    if args.project_root:
        root = args.project_root
    else:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    LOG_FILE = os.path.join(root, "_agent", "hub.log")

    hub = Hub(root)

    if args.once:
        hub.tick()
        hub.shutdown()
    else:
        hub.run()


if __name__ == "__main__":
    main()
