"""
Session Start Briefing Tool
=============================
세션 시작 전 브리핑: 이전 세션 검증 게이트 + 이번 세션 목표/기준 안내.

사용법:
  python _lostark_edu/tools/start_session.py 2    # Session 2 시작 브리핑

동작:
  1. 이전 세션 검증 상태 확인 (게이트 체크)
  2. 이번 세션 목표 표시
  3. 만들 것 목록
  4. "완료되면 할 수 있는 것" 표시
  5. 검증 기준 (구체적으로 어떻게 확인할지) 표시
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
EDU_ROOT = PROJECT_ROOT / "_lostark_edu"
CURRICULUM = EDU_ROOT / "curriculum.json"
STATE_FILE = EDU_ROOT / "session_state.json"


def load_curriculum():
    with open(CURRICULUM, "r", encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": {}}


def check_gate(session_id, state):
    """이전 세션 검증 여부 확인"""
    if session_id <= 1:
        return True, None

    prev_key = str(session_id - 1)
    prev = state.get("sessions", {}).get(prev_key, {})

    if prev.get("verified") == True:
        return True, prev
    else:
        return False, prev


def show_briefing(session_id):
    curriculum = load_curriculum()
    state = load_state()

    # 세션 데이터 찾기
    session_data = None
    for s in curriculum["sessions"]:
        if s["id"] == session_id:
            session_data = s
            break

    if session_data is None:
        print(f"ERROR: Session {session_id} not found")
        sys.exit(1)

    # ── 게이트 체크 ──
    gate_ok, prev_data = check_gate(session_id, state)

    print()
    print("=" * 60)

    if not gate_ok and session_id > 1:
        print(f"  GATE CHECK FAILED")
        print(f"  Session {session_id - 1} has not been verified yet!")
        print()
        if prev_data and prev_data.get("last_verification"):
            print(f"  Last attempt: {prev_data.get('passed', 0)}/{prev_data.get('total', '?')} passed")
            print(f"  Date: {prev_data['last_verification'][:10]}")
        else:
            print(f"  Session {session_id - 1} has never been verified.")
        print()
        print(f"  Run first:")
        print(f"    python _lostark_edu/tools/session_verify.py {session_id - 1}")
        print("=" * 60)
        sys.exit(1)

    if session_id > 1:
        print(f"  Gate: Session {session_id - 1} VERIFIED")
        print(f"         ({prev_data['passed']}/{prev_data['total']} passed, "
              f"{prev_data.get('last_verification', '')[:10]})")
        print()

    # ── 세션 브리핑 ──
    print(f"  SESSION {session_id}: {session_data['title']}")
    print(f"  {session_data['subtitle']}")
    print("=" * 60)
    print()

    # 목표
    print("  [GOAL]")
    print(f"  {session_data['goal']}")
    print()

    # 만들 것
    print("  [WHAT WE BUILD]")
    for item in session_data["what_you_build"]:
        print(f"    - {item}")
    print()

    # 완료 시 가능한 것
    print("  [WHEN DONE, YOU CAN]")
    lines = session_data["when_done_you_can"]
    # 긴 문장 줄바꿈
    import textwrap
    for line in textwrap.wrap(lines, width=55):
        print(f"    {line}")
    print()

    # 파일 목록 (있으면)
    if session_data.get("files"):
        print("  [FILES]")
        for f in session_data["files"]:
            fpath = PROJECT_ROOT / f
            exists = fpath.exists()
            icon = "OK" if exists else ".."
            print(f"    [{icon}] {f}")
        print()

    # 검증 기준
    print("  [ACCEPTANCE CRITERIA]")
    print(f"  (완료 조건: {session_data['success_criteria_summary']})")
    print()
    for i, ac in enumerate(session_data["acceptance_criteria"], 1):
        print(f"    {i}. {ac['name']} [{ac['id']}]")
        print(f"       {ac['verify']}")
        print(f"       -> {ac['how_to_check']}")
        print()

    # 검증 방법
    test_script = session_data.get("verification_test", "")
    print("  [HOW TO VERIFY]")
    if test_script:
        print(f"    python _lostark_edu/tools/session_verify.py {session_id}")
        print(f"    (internally runs: {test_script})")
    else:
        print(f"    python _lostark_edu/tools/session_verify.py {session_id}")
    print()
    print("-" * 60)
    print(f"  Ready to start Session {session_id}!")
    print("=" * 60)


def main():
    if len(sys.argv) < 2:
        print("Usage: python _lostark_edu/tools/start_session.py <session_number>")
        print()
        print("Examples:")
        print("  python _lostark_edu/tools/start_session.py 1    # Session 1 briefing")
        print("  python _lostark_edu/tools/start_session.py 2    # Session 2 (requires S1 verified)")
        sys.exit(1)

    try:
        session_id = int(sys.argv[1])
    except ValueError:
        print(f"ERROR: '{sys.argv[1]}' is not a valid session number")
        sys.exit(1)

    show_briefing(session_id)


if __name__ == "__main__":
    main()
