"""종합 테스트 러너 - 세션 1~29 전체 점검"""
import subprocess, sys, os, time, re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORTS = [7777, 7778, 8888]  # Field1, Field2, Gate

# 테스트 대상 세션 목록
SESSIONS = list(range(1, 30))  # 1~29

def kill_all_servers():
    """모든 게임 서버 프로세스 정리"""
    for port in PORTS:
        try:
            result = subprocess.run(
                f'netstat -ano | findstr :{port} | findstr LISTENING',
                shell=True, capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    pid = line.strip().split()[-1]
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True,
                                 capture_output=True)
        except:
            pass
    # 프로세스 이름으로도 정리
    for name in ['FieldServer', 'GateServer', 'BusServer']:
        try:
            subprocess.run(f'taskkill /F /IM {name}.exe', shell=True,
                         capture_output=True)
        except:
            pass

def run_session_test(session_num):
    """개별 세션 테스트 실행 (서버 자체 관리)"""
    test_file = os.path.join(BASE_DIR, f"test_session{session_num}.py")
    if not os.path.exists(test_file):
        return None, f"테스트 파일 없음"

    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True, text=True, timeout=180,
            cwd=BASE_DIR)
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "타임아웃 (90초 초과)"
    except Exception as e:
        return -1, str(e)

def parse_result(output):
    """테스트 결과 파싱 - 여러 출력 형식 지원"""
    lines = output.strip().split('\n')
    passed = 0
    total = 0
    details = []

    for line in lines:
        stripped = line.strip()
        # [PASS], PASS:, [OK] 형식 모두 인식
        if '[PASS]' in stripped or 'PASS:' in stripped or '[OK]' in stripped:
            passed += 1
            total += 1
            details.append(('PASS', stripped))
        elif '[FAIL]' in stripped or 'FAIL:' in stripped:
            total += 1
            details.append(('FAIL', stripped))

    # Result/Results 라인에서 정확한 숫자 추출 (우선순위 높음)
    for line in lines:
        stripped = line.strip()
        # "Result: 12/12 PASSED" 또는 "Results: 12/12 passed" 형식
        m = re.search(r'Results?\s*:\s*(\d+)\s*/\s*(\d+)', stripped)
        if m:
            passed = int(m.group(1))
            total = int(m.group(2))

    return passed, total, details

# 세션별 실제 결과 저장
session_results = {}

def main():
    print("=" * 70)
    print("  ECS 게임서버 스켈레톤 - 종합 테스트")
    print("  세션 1 ~ 29 전체 점검")
    print("=" * 70)
    print()

    # 기존 서버 프로세스 정리
    kill_all_servers()
    time.sleep(0.5)

    total_sessions = 0
    passed_sessions = 0
    failed_sessions = []
    skipped_sessions = []
    total_tests = 0
    total_passed = 0

    for s in SESSIONS:
        test_file = os.path.join(BASE_DIR, f"test_session{s}.py")
        if not os.path.exists(test_file):
            skipped_sessions.append(s)
            continue

        total_sessions += 1
        print(f"{'─' * 60}")
        print(f"  세션 {s:02d} 테스트 실행중...")
        print(f"{'─' * 60}")

        # 포트 정리 후 실행
        kill_all_servers()
        time.sleep(0.5)

        returncode, output = run_session_test(s)

        if returncode is None:
            skipped_sessions.append(s)
            total_sessions -= 1
            continue

        # 결과 출력
        for line in output.strip().split('\n'):
            if line.strip():
                print(f"  {line}")

        passed, total, details = parse_result(output)
        total_tests += total
        total_passed += passed
        session_results[s] = (passed, total)

        if returncode == 0 and passed == total and total > 0:
            passed_sessions += 1
            print(f"  >>> 세션 {s:02d}: {passed}/{total} 통과 <<<")
        else:
            failed_sessions.append((s, passed, total, output))
            print(f"  >>> 세션 {s:02d}: {passed}/{total} 실패! <<<")

        print()

        # 서버 종료 대기
        kill_all_servers()
        time.sleep(0.5)

    # ━━━ 종합 결과 ━━━
    print()
    print("=" * 70)
    print("  종합 테스트 결과")
    print("=" * 70)
    print()
    print(f"  테스트 세션: {total_sessions}개 실행 / {len(skipped_sessions)}개 스킵")
    print(f"  개별 테스트: {total_passed}/{total_tests} 통과")
    print()

    # 세션별 결과 표
    print(f"  {'세션':>6} │ {'결과':>8} │ 상세")
    print(f"  {'─'*6}─┼─{'─'*8}─┼─{'─'*40}")

    for s in SESSIONS:
        test_file = os.path.join(BASE_DIR, f"test_session{s}.py")
        if not os.path.exists(test_file):
            print(f"  {s:>6} │ {'스킵':>6} │ 테스트 파일 없음")
            continue

        p, t = session_results.get(s, (0, 0))
        is_failed = any(fs == s for fs, _, _, _ in failed_sessions)
        if is_failed:
            print(f"  {s:>6} │ {'FAIL':>6} │ {p}/{t}")
        else:
            print(f"  {s:>6} │ {'PASS':>6} │ {p}/{t}")

    print()

    if failed_sessions:
        print("  실패한 세션 상세:")
        for s, p, t, out in failed_sessions:
            print(f"\n  [세션 {s}] {p}/{t}")
            for line in out.strip().split('\n'):
                if 'FAIL' in line:
                    print(f"    {line.strip()}")

    print()
    if not failed_sessions:
        print("  +================================================+")
        print(f"  |  ALL {total_sessions} SESSIONS PASSED!                      |")
        print(f"  |  {total_passed}/{total_tests} tests passed                         |")
        print("  +================================================+")
    else:
        print(f"  {len(failed_sessions)}개 세션 실패")

    print("=" * 70)

    # 포트 최종 정리
    kill_all_servers()

    sys.exit(0 if not failed_sessions else 1)

if __name__ == "__main__":
    main()
