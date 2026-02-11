"""
Session Verification Tool
==========================
각 세션의 완료 기준을 자동 검증하고 증거(evidence)를 파일로 저장.

사용법:
  python _lostark_edu/tools/session_verify.py 1       # Session 1 검증
  python _lostark_edu/tools/session_verify.py 1 --dry  # 테스트 목록만 표시 (실행 안 함)
  python _lostark_edu/tools/session_verify.py status    # 전체 세션 상태 조회

검증 흐름:
  1. curriculum.json에서 해당 세션의 acceptance_criteria 로드
  2. 빌드 검증 (build.py 실행)
  3. 서버 기동 → 테스트 스크립트 실행 → 서버 종료
  4. 결과를 evidence/{session_id}_{timestamp}.json에 저장
  5. session_state.json 갱신
"""
import json
import subprocess
import sys
import os
import time
import socket
from pathlib import Path
from datetime import datetime

# ── 경로 설정 ──
PROJECT_ROOT = Path(__file__).parent.parent.parent  # GameServerSkeleton/
EDU_ROOT = PROJECT_ROOT / "_lostark_edu"
CURRICULUM = EDU_ROOT / "curriculum.json"
STATE_FILE = EDU_ROOT / "session_state.json"
EVIDENCE_DIR = EDU_ROOT / "evidence"
LOGS_DIR = EDU_ROOT / "logs"
BUILD_DIR = PROJECT_ROOT / "build"
EXE = BUILD_DIR / "FieldServer.exe"

EVIDENCE_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)


def load_curriculum():
    with open(CURRICULUM, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": {}}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def save_evidence(session_id, evidence):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = EVIDENCE_DIR / f"session{session_id}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, ensure_ascii=False)
    return path


# ── 검증 함수들 ──

def verify_build():
    """build.py 실행하여 빌드 검증"""
    print("  [BUILD] build.py 실행 중...")
    build_script = PROJECT_ROOT / "build.py"
    if not build_script.exists():
        return False, "build.py not found", ""

    result = subprocess.run(
        [sys.executable, str(build_script)],
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True,
        encoding='utf-8', errors='replace',
        timeout=120
    )

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    output = stdout + stderr
    success = result.returncode == 0 and "BUILD SUCCESS" in stdout

    if success:
        # MSVC 경고 패턴: ": warning C" (e.g., ": warning C4819:")
        warning_count = output.count(": warning C")
        if warning_count > 0:
            return False, f"Build succeeded but {warning_count} warnings found", output
        print("  [BUILD] OK - 0 errors, 0 warnings")
    else:
        print(f"  [BUILD] FAILED (exit code: {result.returncode})")

    return success, output[:2000], output


def verify_server_starts():
    """서버가 정상 기동되는지 확인"""
    if not EXE.exists():
        return False, "FieldServer.exe not found", None

    print("  [SERVER] Starting FieldServer.exe...")
    proc = subprocess.Popen(
        [str(EXE)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )
    time.sleep(2.5)

    if proc.poll() is not None:
        return False, f"Server exited immediately (code: {proc.returncode})", None

    # 접속 테스트
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 7777))
        sock.close()
        print("  [SERVER] OK - listening on port 7777")
        return True, "Server started and accepting connections", proc
    except Exception as e:
        proc.terminate()
        return False, f"Server started but connection failed: {e}", None


def stop_server(proc):
    """서버 종료"""
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except:
        proc.kill()
    print("  [SERVER] Stopped")


def run_test_script(script_name):
    """세션별 테스트 스크립트 실행"""
    script_path = PROJECT_ROOT / script_name
    if not script_path.exists():
        return False, f"Test script not found: {script_name}", ""

    print(f"  [TEST] Running {script_name}...")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True,
        encoding='utf-8', errors='replace',
        timeout=60
    )

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    output = stdout + stderr
    success = result.returncode == 0

    # 테스트 결과 파싱
    passed = output.count("[PASS]")
    failed = output.count("[FAIL]")

    if success and failed == 0:
        print(f"  [TEST] OK - {passed} passed, {failed} failed")
    else:
        print(f"  [TEST] FAILED - {passed} passed, {failed} failed")

    return success, {"passed": passed, "failed": failed, "output": output[:5000]}, output


def get_ecs_stats():
    """서버에 __STATS__ 명령을 보내 ECS 내부 상태 조회"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 7777))
        time.sleep(0.5)

        sock.sendall(b"__STATS__")
        raw = sock.recv(4096)
        text = raw.decode('utf-8')

        stats = {}
        parts = text.split('|')
        for part in parts[1:]:
            if '=' in part:
                k, v = part.split('=', 1)
                stats[k] = int(v)

        sock.close()
        return True, stats
    except Exception as e:
        return False, str(e)


# ── 세션별 검증 로직 ──

def verify_session_1():
    """Session 1: ECS Core + IOCP Echo 검증"""
    results = []
    full_log = []

    # S1-BUILD: 빌드
    success, detail, log = verify_build()
    results.append({"id": "S1-BUILD", "passed": success, "detail": str(detail)[:500]})
    full_log.append(f"=== BUILD ===\n{log}\n")

    if not success:
        # 빌드 실패 시 나머지 검증 불가
        for cid in ["S1-ECHO", "S1-ECS-ENTITY", "S1-ECS-COMPONENT", "S1-LIFECYCLE", "S1-MULTI", "S1-CLEAN"]:
            results.append({"id": cid, "passed": False, "detail": "Build failed, cannot run"})
        return results, "\n".join(full_log)

    # 나머지: test_session1.py로 통합 검증
    test_ok, test_detail, test_log = run_test_script("test_session1.py")
    full_log.append(f"=== TEST_SESSION1 ===\n{test_log}\n")

    if test_ok:
        # 전부 통과
        for cid in ["S1-ECHO", "S1-ECS-ENTITY", "S1-ECS-COMPONENT", "S1-LIFECYCLE", "S1-MULTI", "S1-CLEAN"]:
            results.append({"id": cid, "passed": True, "detail": "Verified by test_session1.py"})
    else:
        # 테스트 출력에서 개별 결과 파싱
        output = test_detail.get("output", "") if isinstance(test_detail, dict) else str(test_detail)

        criteria_map = {
            "S1-ECHO": ["에코", "echo", "Echo"],
            "S1-ECS-ENTITY": ["Entity가 1개 생성", "entity_count"],
            "S1-ECS-COMPONENT": ["SessionComponent 부착", "RecvBufferComponent 부착"],
            "S1-LIFECYCLE": ["Entity 생명주기", "접속해제", "감소"],
            "S1-MULTI": ["멀티 클라이언트", "독립 에코", "5명"],
            "S1-CLEAN": ["메모리 누수", "전원 접속해제"],
        }

        for cid, keywords in criteria_map.items():
            # 해당 키워드가 포함된 줄에서 PASS/FAIL 확인
            passed = False
            for kw in keywords:
                for line in output.split("\n"):
                    if kw in line and "[PASS]" in line:
                        passed = True
                        break
            results.append({
                "id": cid,
                "passed": passed,
                "detail": f"{'PASS' if passed else 'FAIL'} in test_session1.py"
            })

    return results, "\n".join(full_log)


def verify_session_2():
    """Session 2: Packet Protocol + Message Dispatch 검증"""
    results = []
    full_log = []

    # S2-BUILD: 빌드
    success, detail, log = verify_build()
    results.append({"id": "S2-BUILD", "passed": success, "detail": str(detail)[:500]})
    full_log.append(f"=== BUILD ===\n{log}\n")

    if not success:
        for cid in ["S2-PACKET-ASSEMBLE", "S2-PACKET-MULTI", "S2-DISPATCH", "S2-UNKNOWN-TYPE"]:
            results.append({"id": cid, "passed": False, "detail": "Build failed, cannot run"})
        return results, "\n".join(full_log)

    # test_session2.py로 통합 검증
    test_ok, test_detail, test_log = run_test_script("test_session2.py")
    full_log.append(f"=== TEST_SESSION2 ===\n{test_log}\n")

    if test_ok:
        for cid in ["S2-PACKET-ASSEMBLE", "S2-PACKET-MULTI", "S2-DISPATCH", "S2-UNKNOWN-TYPE"]:
            results.append({"id": cid, "passed": True, "detail": "Verified by test_session2.py"})
    else:
        output = test_detail.get("output", "") if isinstance(test_detail, dict) else str(test_detail)

        criteria_map = {
            "S2-PACKET-ASSEMBLE": ["Split send", "reassembled", "chunks"],
            "S2-PACKET-MULTI": ["concatenated", "separated", "3 payloads"],
            "S2-DISPATCH": ["PING", "PONG", "dispatch", "STATS"],
            "S2-UNKNOWN-TYPE": ["Unknown type", "server alive", "still running"],
        }

        for cid, keywords in criteria_map.items():
            cid_passed = False
            for kw in keywords:
                for line in output.split("\n"):
                    if kw in line and "[PASS]" in line:
                        cid_passed = True
                        break
            results.append({
                "id": cid,
                "passed": cid_passed,
                "detail": f"{'PASS' if cid_passed else 'FAIL'} in test_session2.py"
            })

    return results, "\n".join(full_log)


# 세션별 검증 함수 매핑
SESSION_VERIFIERS = {
    1: verify_session_1,
    2: verify_session_2,
    # 3~10: 해당 세션 구현 시 추가
}


# ── 메인 실행 ──

def print_criteria(session_data):
    """검증 기준 표시 (--dry 모드)"""
    print()
    print(f"  Session {session_data['id']}: {session_data['title']}")
    print(f"  {session_data['subtitle']}")
    print()
    print(f"  목표: {session_data['goal']}")
    print()
    print("  완료 시 가능한 것:")
    print(f"    {session_data['when_done_you_can']}")
    print()
    print("  검증 기준:")
    for i, ac in enumerate(session_data["acceptance_criteria"], 1):
        print(f"    [{i}] {ac['id']}: {ac['name']}")
        print(f"        검증: {ac['verify']}")
        print(f"        방법: {ac['how_to_check']}")
        print()
    print(f"  성공 조건: {session_data['success_criteria_summary']}")


def run_verification(session_id):
    """세션 검증 실행"""
    curriculum = load_curriculum()
    state = load_state()

    # 세션 데이터 찾기
    session_data = None
    for s in curriculum["sessions"]:
        if s["id"] == session_id:
            session_data = s
            break

    if session_data is None:
        print(f"ERROR: Session {session_id} not found in curriculum")
        return False

    print()
    print("=" * 60)
    print(f"  Session {session_id} Verification")
    print(f"  {session_data['title']}")
    print("=" * 60)
    print()

    # 이전 세션 검증 확인
    if session_id > 1:
        prev_key = str(session_id - 1)
        prev = state.get("sessions", {}).get(prev_key, {})
        if prev.get("verified") != True:
            print(f"  WARNING: Session {session_id - 1} has not been verified yet!")
            print(f"  Run: python _lostark_edu/tools/session_verify.py {session_id - 1}")
            print()

    # 검증 함수 실행
    verifier = SESSION_VERIFIERS.get(session_id)
    if verifier is None:
        print(f"  Session {session_id} verifier not implemented yet.")
        print(f"  (Session {session_id}의 코드를 먼저 구현해야 합니다)")
        return False

    print(f"  Running {len(session_data['acceptance_criteria'])} checks...")
    print()

    start_time = time.time()
    results, full_log = verifier()
    elapsed = time.time() - start_time

    # 결과 표시
    print()
    print("-" * 60)
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)

    for r in results:
        icon = "PASS" if r["passed"] else "FAIL"
        print(f"  [{icon}] {r['id']}: {r.get('detail', '')[:80]}")

    print()
    print(f"  Result: {passed_count}/{total_count} PASSED ({elapsed:.1f}s)")
    all_passed = passed_count == total_count

    # Evidence 저장
    evidence = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 1),
        "all_passed": all_passed,
        "passed": passed_count,
        "total": total_count,
        "results": results,
    }
    ev_path = save_evidence(session_id, evidence)
    print(f"  Evidence saved: {ev_path.relative_to(PROJECT_ROOT)}")

    # 로그 저장
    log_path = LOGS_DIR / f"session{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(f"Session {session_id} Verification Log\n")
        f.write(f"Time: {datetime.now().isoformat()}\n")
        f.write(f"Result: {passed_count}/{total_count}\n")
        f.write("=" * 60 + "\n\n")
        f.write(full_log)
    print(f"  Log saved: {log_path.relative_to(PROJECT_ROOT)}")

    # State 갱신
    session_key = str(session_id)
    if "sessions" not in state:
        state["sessions"] = {}
    state["sessions"][session_key] = {
        "verified": all_passed,
        "last_verification": datetime.now().isoformat(),
        "passed": passed_count,
        "total": total_count,
        "evidence_file": str(ev_path.relative_to(PROJECT_ROOT)),
    }
    save_state(state)

    # 최종 배너
    print()
    if all_passed:
        print("  +-------------------------------------------+")
        print(f"  | SESSION {session_id} VERIFIED: ALL {total_count} CHECKS PASSED  |")
        print("  |                                           |")
        print(f"  | Ready to start Session {session_id + 1}!                |")
        print("  +-------------------------------------------+")
    else:
        print("  +-------------------------------------------+")
        print(f"  | SESSION {session_id}: {total_count - passed_count} CHECK(S) FAILED           |")
        print("  | Fix issues and re-run verification.       |")
        print("  +-------------------------------------------+")

    print("=" * 60)
    return all_passed


def show_status():
    """전체 세션 상태 표시"""
    curriculum = load_curriculum()
    state = load_state()

    print()
    print("=" * 60)
    print("  Session Verification Status")
    print("=" * 60)
    print()

    for s in curriculum["sessions"]:
        sid = str(s["id"])
        sdata = state.get("sessions", {}).get(sid, {})

        if sdata.get("verified"):
            icon = "[OK]"
            detail = f"{sdata['passed']}/{sdata['total']} passed ({sdata.get('last_verification', '?')[:10]})"
        elif sdata.get("last_verification"):
            icon = "[!!]"
            detail = f"{sdata.get('passed', 0)}/{sdata.get('total', '?')} passed (INCOMPLETE)"
        else:
            icon = "[  ]"
            detail = "Not verified"

        print(f"  {icon} Session {s['id']:2d}: {s['title']}")
        print(f"             {detail}")
        print()

    # 다음 할 일
    next_session = None
    for s in curriculum["sessions"]:
        sid = str(s["id"])
        if not state.get("sessions", {}).get(sid, {}).get("verified"):
            next_session = s["id"]
            break

    if next_session:
        print(f"  Next: python _lostark_edu/tools/session_verify.py {next_session}")
    else:
        print("  All sessions verified! Project complete.")

    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python _lostark_edu/tools/session_verify.py <session_number>")
        print("  python _lostark_edu/tools/session_verify.py <session_number> --dry")
        print("  python _lostark_edu/tools/session_verify.py status")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "status":
        show_status()
        return

    try:
        session_id = int(arg)
    except ValueError:
        print(f"ERROR: '{arg}' is not a valid session number")
        sys.exit(1)

    if session_id < 1 or session_id > 10:
        print("ERROR: Session number must be 1-10")
        sys.exit(1)

    # --dry 모드: 기준만 표시
    if len(sys.argv) > 2 and sys.argv[2] == "--dry":
        curriculum = load_curriculum()
        for s in curriculum["sessions"]:
            if s["id"] == session_id:
                print_criteria(s)
                return
        return

    # 검증 실행
    success = run_verification(session_id)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
