#!/usr/bin/env python3
"""
unity_build_check.py — Unity Batch Mode 컴파일 체크

Unity CLI를 호출하여 컴파일 에러를 감지하고 결과를 파싱.

사용법: python unity_build_check.py [--unity-path "C:\\...\\Unity.exe"]
"""

import argparse
import io
import os
import re
import subprocess
import sys
import time

# Windows 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ━━━ 경로 설정 ━━━

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VALIDATION_DIR = os.path.join(SCRIPT_DIR, "_validation")
LOGS_DIR = os.path.join(VALIDATION_DIR, "logs")
BUILD_LOG = os.path.join(LOGS_DIR, "build.log")

# Unity 기본 경로 탐색 목록
UNITY_SEARCH_PATHS = [
    r"C:\Program Files\Unity\Hub\Editor\6000.3.4f1\Editor\Unity.exe",
    r"C:\Program Files\Unity\Hub\Editor",
]

# ━━━ 로그 파싱 패턴 ━━━

ERROR_RE = re.compile(r"(Assets[\\/].+?)\((\d+),(\d+)\):\s*error\s+(CS\d+):\s*(.+)")
WARNING_RE = re.compile(r"(Assets[\\/].+?)\((\d+),(\d+)\):\s*warning\s+(CS\d+):\s*(.+)")
SUCCESS_MARKER = "Compilations finished successfully"
FAILURE_MARKER = "Scripts have compiler errors"


def find_unity_exe():
    """Unity.exe 경로를 자동 탐색."""
    # 1) 고정 경로 확인
    fixed = UNITY_SEARCH_PATHS[0]
    if os.path.isfile(fixed):
        return fixed

    # 2) Hub Editor 폴더에서 최신 버전 탐색
    hub_dir = UNITY_SEARCH_PATHS[1]
    if os.path.isdir(hub_dir):
        versions = []
        for name in os.listdir(hub_dir):
            exe = os.path.join(hub_dir, name, "Editor", "Unity.exe")
            if os.path.isfile(exe):
                versions.append((name, exe))
        if versions:
            # 버전 문자열 정렬 (최신 우선)
            versions.sort(key=lambda x: x[0], reverse=True)
            return versions[0][1]

    return None


def ensure_log_dir():
    """로그 디렉토리가 없으면 생성."""
    os.makedirs(LOGS_DIR, exist_ok=True)


def run_unity_batch(unity_path):
    """Unity batch mode 실행. 반환: (성공여부, 로그파일 경로)."""
    ensure_log_dir()

    # 기존 로그 삭제
    if os.path.exists(BUILD_LOG):
        os.remove(BUILD_LOG)

    cmd = [
        unity_path,
        "-batchmode",
        "-projectPath", SCRIPT_DIR,
        "-logFile", BUILD_LOG,
        "-quit",
    ]

    print(f"[INFO] Unity 실행: {unity_path}")
    print(f"[INFO] 프로젝트: {SCRIPT_DIR}")
    print(f"[INFO] 로그: {BUILD_LOG}")
    print("[INFO] 컴파일 중... (수십 초 소요될 수 있음)")

    try:
        result = subprocess.run(
            cmd,
            timeout=300,  # 5분 타임아웃
            capture_output=True,
            text=True,
        )
        return result.returncode, BUILD_LOG
    except subprocess.TimeoutExpired:
        print("[FAIL] Unity 실행 타임아웃 (5분 초과)")
        return -1, BUILD_LOG
    except FileNotFoundError:
        print(f"[FAIL] Unity 실행 파일을 찾을 수 없음: {unity_path}")
        return -2, None
    except OSError as e:
        # Unity가 이미 열려있는 경우 등
        print(f"[FAIL] Unity 실행 오류: {e}")
        return -3, BUILD_LOG


def parse_build_log(log_path):
    """빌드 로그를 파싱하여 에러/경고 추출."""
    if not os.path.isfile(log_path):
        return {
            "success": False,
            "errors": [],
            "warnings": [],
            "raw_available": False,
        }

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except (OSError, IOError):
        return {
            "success": False,
            "errors": [],
            "warnings": [],
            "raw_available": False,
        }

    errors = []
    warnings = []
    seen_errors = set()
    seen_warnings = set()

    for line in content.splitlines():
        # 에러 파싱
        m = ERROR_RE.search(line)
        if m:
            key = (m.group(1), m.group(2), m.group(4))
            if key not in seen_errors:
                seen_errors.add(key)
                errors.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "col": int(m.group(3)),
                    "code": m.group(4),
                    "message": m.group(5).strip(),
                })

        # 경고 파싱
        m = WARNING_RE.search(line)
        if m:
            key = (m.group(1), m.group(2), m.group(4))
            if key not in seen_warnings:
                seen_warnings.add(key)
                warnings.append({
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "col": int(m.group(3)),
                    "code": m.group(4),
                    "message": m.group(5).strip(),
                })

    success = SUCCESS_MARKER in content
    has_errors = FAILURE_MARKER in content or len(errors) > 0

    return {
        "success": success and not has_errors,
        "errors": errors,
        "warnings": warnings,
        "raw_available": True,
    }


def run_build_check(unity_path=None):
    """빌드 체크 실행 및 결과 출력. 반환: 결과 dict."""
    print("━━━ Unity Batch Mode 컴파일 체크 ━━━\n")

    # Unity 경로 확인
    if unity_path is None:
        unity_path = find_unity_exe()

    if unity_path is None or not os.path.isfile(unity_path):
        print("[FAIL] Unity.exe를 찾을 수 없습니다.")
        print("       --unity-path 옵션으로 경로를 지정하세요.")
        print(f"       탐색 경로: {UNITY_SEARCH_PATHS[0]}")
        return {
            "passed": False,
            "errors": 0,
            "warnings": 0,
            "error_details": [],
            "warning_details": [],
            "unity_not_found": True,
        }

    # Unity 실행
    returncode, log_path = run_unity_batch(unity_path)

    # 로그 파싱
    if log_path and os.path.isfile(log_path):
        result = parse_build_log(log_path)
    else:
        print("[FAIL] 빌드 로그를 생성하지 못했습니다.")
        return {
            "passed": False,
            "errors": 0,
            "warnings": 0,
            "error_details": [],
            "warning_details": [],
            "unity_not_found": False,
        }

    # 결과 출력
    error_count = len(result["errors"])
    warning_count = len(result["warnings"])

    if result["success"]:
        print(f"\n[PASS] 컴파일 성공 ({error_count} errors, {warning_count} warnings)")
    else:
        print(f"\n[FAIL] 컴파일 실패:")
        for err in result["errors"]:
            print(f"  {err['file']}({err['line']},{err['col']}): error {err['code']}: {err['message']}")

    if warning_count > 0:
        print(f"\n경고 {warning_count}개:")
        for warn in result["warnings"]:
            print(f"  {warn['file']}({warn['line']},{warn['col']}): warning {warn['code']}: {warn['message']}")

    print(f"\n━━━ 컴파일 결과: {'PASS' if result['success'] else 'FAIL'} ({error_count} errors, {warning_count} warnings) ━━━")

    return {
        "passed": result["success"],
        "errors": error_count,
        "warnings": warning_count,
        "error_details": result["errors"],
        "warning_details": result["warnings"],
        "unity_not_found": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Unity Batch Mode 컴파일 체크")
    parser.add_argument(
        "--unity-path",
        help="Unity.exe 경로 (기본: 자동 탐색)",
        default=None,
    )
    args = parser.parse_args()

    result = run_build_check(args.unity_path)
    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
