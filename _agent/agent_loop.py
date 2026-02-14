"""
에이전트 자율 루프 — 클라이언트/서버 공용
===========================================
git push 감지 -> 새 메시지 처리 + 자기 할 일 진행 -> commit & push

사용법:
  python _agent/agent_loop.py --role client
  python _agent/agent_loop.py --role server

컨텍스트 보장:
  매 Claude 실행 시 반드시 주입하는 파일:
  1. _context/{role}_state.yaml  -- 영속 상태 (이전 세션 기억)
  2. CLAUDE.md                    -- 프로젝트 규칙
  3. _gdd/README.md               -- GDD 시스템 개요
  4. 새 메시지 파일 전문           -- 서버/클라 간 통신
"""

import argparse
import datetime
import os
import subprocess
import sys
import time

# Windows에서 리다이렉트 시 버퍼링 방지
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

# ============================================================
# 설정
# ============================================================

POLL_INTERVAL = 30          # 초 단위 -- git pull 주기
IDLE_WORK_INTERVAL = 300    # 초 단위 -- 메시지 없어도 자기 할 일 진행 주기
MAX_CLAUDE_TIMEOUT = 900    # 초 단위 -- Claude 실행 최대 시간 (15분)

ROLES = {
    "client": {
        "inbox": "_comms/server_to_client",
        "outbox": "_comms/client_to_server",
        "state_file": "_context/client_state.yaml",
        "claude_md": "UnityClient/GameClient/CLAUDE.md",
        "validate_cmd": "cd UnityClient/GameClient && python validate_all.py --skip-unity",
    },
    "server": {
        "inbox": "_comms/client_to_server",
        "outbox": "_comms/server_to_client",
        "state_file": "_context/server_state.yaml",
        "claude_md": "Servers/CLAUDE.md",
        "validate_cmd": None,
    },
}


# ============================================================
# Git 유틸
# ============================================================

def git_run(args, cwd):
    """git 명령 실행, 결과 반환"""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    stdout = result.stdout.strip() if result.stdout else ""
    stderr = result.stderr.strip() if result.stderr else ""
    return result.returncode, stdout, stderr


def git_pull(project_root):
    """git stash -> pull --rebase -> stash pop"""
    # unstaged 변경이 있으면 stash
    _, status_out, _ = git_run(["status", "--porcelain"], project_root)
    has_changes = bool(status_out.strip())
    if has_changes:
        git_run(["stash"], project_root)

    code, out, err = git_run(["pull", "--rebase"], project_root)
    if code != 0:
        print(f"  [WARN] git pull rebase 실패: {err}")
        git_run(["rebase", "--abort"], project_root)
        code, out, err = git_run(["pull"], project_root)

    if has_changes:
        pop_code, _, pop_err = git_run(["stash", "pop"], project_root)
        if pop_code != 0:
            print(f"  [WARN] stash pop 충돌: {pop_err}")

    return code == 0, out


def git_push(project_root, message):
    """add + commit + push"""
    git_run(["add", "-A"], project_root)

    code, out, _ = git_run(["status", "--porcelain"], project_root)
    if not out.strip():
        print("  [INFO] 변경사항 없음, push 스킵")
        return False

    git_run(["commit", "-m", message], project_root)
    code, out, err = git_run(["push"], project_root)
    if code != 0:
        print(f"  [WARN] push 실패: {err}")
        git_pull(project_root)
        code, out, err = git_run(["push"], project_root)
    return code == 0


# ============================================================
# 메시지 감지
# ============================================================

def get_processed_messages(state_file, project_root):
    """state 파일에서 processed_messages 목록 읽기"""
    path = os.path.join(project_root, state_file)
    if not os.path.exists(path):
        return set()

    processed = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith('- "') and line.endswith('"'):
                msg_id = line[3:-1]
                processed.add(msg_id)
    return processed


def scan_new_messages(inbox_dir, processed, project_root):
    """inbox에서 아직 처리 안 된 메시지 파일 찾기"""
    inbox_path = os.path.join(project_root, inbox_dir)
    if not os.path.exists(inbox_path):
        return []

    new_messages = []
    for fname in sorted(os.listdir(inbox_path)):
        if not fname.endswith(".md"):
            continue
        msg_id = fname.split("_")[0]
        if msg_id not in processed:
            full_path = os.path.join(inbox_dir, fname)
            new_messages.append((msg_id, full_path))

    return new_messages


# ============================================================
# Claude 실행 (컨텍스트 강제 주입)
# ============================================================

def build_prompt(role_config, new_messages, project_root, trigger_reason):
    """Claude에게 보낼 프롬프트 생성. 컨텍스트 파일을 반드시 읽게 강제."""
    state_file = role_config["state_file"]
    claude_md = role_config["claude_md"]

    msg_files = "\n".join([f"  - {path}" for _, path in new_messages])
    if not msg_files:
        msg_files = "  (새 메시지 없음)"

    prompt = f"""
# 에이전트 자율 실행 -- 컨텍스트 복원 필수

## 0. 반드시 먼저 읽을 파일 (건너뛰지 마세요)

다음 파일들을 순서대로 읽고 내용을 완전히 이해한 후 작업을 시작하세요:

1. `{state_file}` -- 당신의 영속 상태 (이전 세션에서 뭘 했는지, 다음에 뭘 해야 하는지)
2. `{claude_md}` -- 프로젝트 코딩 규칙과 아키텍처
3. `_gdd/README.md` -- GDD 시스템 개요

## 1. 실행 이유

{trigger_reason}

## 2. 새 메시지

{msg_files}

새 메시지가 있으면 파일을 읽고 내용에 따라 작업하세요.

## 3. 작업 지침

1. state 파일의 `pending_tasks`에서 `blocked: false`인 것을 우선순위 순으로 작업
2. 코드 작성 후 반드시 검증 실행
3. 서버/클라 간 통신이 필요하면 `{role_config["outbox"]}/` 폴더에 메시지 파일 생성
4. 대표님(유저)의 결정이 필요하면 `_context/ask_user.yaml`에 질문 작성

## 4. 작업 완료 후 반드시 할 것

1. `{state_file}` 업데이트:
   - `last_session`: 현재 시각
   - `current_status`: 한 줄 요약
   - `completed`: 완료한 작업 추가
   - `pending_tasks`: 다음 할 일 업데이트
   - `processed_messages`: 처리한 메시지 ID 추가
   - `recent_decisions`: 중요 결정 추가
2. 검증 실행 결과가 0 FAIL인지 확인

## 5. 하지 말 것

- state 파일을 읽지 않고 작업 시작하지 마세요
- CLAUDE.md 규칙을 위반하지 마세요
- 유저에게 질문 없이 큰 방향 전환하지 마세요 (ask_user.yaml 사용)
- git push는 하지 마세요 (agent_loop.py가 합니다)
"""
    return prompt.strip()


def run_claude(prompt, project_root):
    """Claude CLI 비대화형 실행"""
    print(f"  [CLAUDE] 실행 시작 ({len(prompt)}자 프롬프트)")
    start = time.time()

    # 중첩 세션 차단 우회 -- agent_loop은 독립 프로세스
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--allowedTools",
             "Read,Write,Edit,Bash,Glob,Grep,Task"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=MAX_CLAUDE_TIMEOUT,
            env=env,
        )
        elapsed = time.time() - start
        print(f"  [CLAUDE] 완료 ({elapsed:.0f}초, exit={result.returncode})")

        log_path = os.path.join(project_root, "_agent", "last_run.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"=== {datetime.datetime.now().isoformat()} ===\n")
            f.write(f"Exit: {result.returncode}\n")
            f.write(f"Duration: {elapsed:.0f}s\n\n")
            f.write("=== STDOUT ===\n")
            f.write(result.stdout[:5000] if result.stdout else "(empty)")
            f.write("\n\n=== STDERR ===\n")
            f.write(result.stderr[:2000] if result.stderr else "(empty)")

        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  [CLAUDE] 타임아웃 ({MAX_CLAUDE_TIMEOUT}초)")
        return False
    except FileNotFoundError:
        print("  [ERROR] claude CLI를 찾을 수 없습니다. claude가 PATH에 있는지 확인하세요.")
        return False


# ============================================================
# 유저 알림
# ============================================================

def check_ask_user(project_root):
    """ask_user.yaml에 미답변 질문이 있으면 표시"""
    path = os.path.join(project_root, "_context", "ask_user.yaml")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "status: pending" in content:
        print("\n" + "=" * 50)
        print("  [!!] 유저 결정 필요! _context/ask_user.yaml 확인")
        print("=" * 50 + "\n")


# ============================================================
# 메인 루프
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="에이전트 자율 루프")
    parser.add_argument("--role", required=True, choices=["client", "server"])
    parser.add_argument("--project-root", default=None,
                        help="프로젝트 루트 (기본: 스크립트 위치의 상위 폴더)")
    parser.add_argument("--once", action="store_true",
                        help="한 번만 실행하고 종료")
    args = parser.parse_args()

    if args.project_root:
        project_root = args.project_root
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    role_config = ROLES[args.role]
    print(f"{'=' * 50}")
    print(f"  Agent Loop Start: {args.role}")
    print(f"  Project: {project_root}")
    print(f"  Inbox: {role_config['inbox']}")
    print(f"  Outbox: {role_config['outbox']}")
    print(f"  State: {role_config['state_file']}")
    print(f"  Poll: {POLL_INTERVAL}s")
    print(f"{'=' * 50}\n")

    last_work_time = 0

    while True:
        try:
            now = time.time()
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")

            # 1. git pull
            print(f"[{timestamp}] git pull...")
            success, pull_output = git_pull(project_root)
            if not success:
                print(f"  [WARN] git pull failed, retry in {POLL_INTERVAL}s")
                time.sleep(POLL_INTERVAL)
                continue

            # 2. 새 메시지 확인
            processed = get_processed_messages(role_config["state_file"], project_root)
            new_messages = scan_new_messages(role_config["inbox"], processed, project_root)

            trigger = None

            if new_messages:
                msg_names = [m[0] for m in new_messages]
                print(f"  [NEW] messages: {msg_names}")
                trigger = f"new messages: {', '.join(msg_names)}"

            elif now - last_work_time > IDLE_WORK_INTERVAL:
                print(f"  [IDLE] {IDLE_WORK_INTERVAL}s elapsed, working on pending_tasks")
                trigger = "idle work cycle -- pending_tasks"

            # 3. Claude 실행
            if trigger:
                prompt = build_prompt(role_config, new_messages, project_root, trigger)
                success = run_claude(prompt, project_root)

                if success:
                    commit_msg = f"auto({args.role}): {trigger[:60]}"
                    pushed = git_push(project_root, commit_msg)
                    if pushed:
                        print(f"  [PUSH] commit & push done")
                    last_work_time = now
                else:
                    print(f"  [WARN] Claude execution failed")

            else:
                print(f"  [WAIT] no new messages, waiting...")

            # 5. 유저 알림 체크
            check_ask_user(project_root)

            if args.once:
                print("\n[DONE] --once mode, exiting")
                break

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n[STOP] Ctrl+C -- agent loop stopped")
            break
        except Exception as e:
            print(f"  [ERROR] {e}")
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
