#!/usr/bin/env python3
"""
validate_all.py — 통합 검증 오케스트레이터

validate_client.py + unity_build_check.py를 순차 실행하고 결과를 집계.
Evidence JSON을 _validation/evidence/ 폴더에 저장.

사용법: python validate_all.py [--unity-path "C:\\...\\Unity.exe"] [--skip-unity]
"""

import argparse
import io
import json
import os
import sys
from datetime import datetime

# Windows 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 같은 디렉토리의 모듈 임포트
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from validate_client import run_all_checks as run_convention_checks
from unity_build_check import run_build_check

# ━━━ 경로 설정 ━━━

VALIDATION_DIR = os.path.join(SCRIPT_DIR, "_validation")
EVIDENCE_DIR = os.path.join(VALIDATION_DIR, "evidence")


def ensure_evidence_dir():
    """Evidence 디렉토리가 없으면 생성."""
    os.makedirs(EVIDENCE_DIR, exist_ok=True)


def save_evidence(result):
    """검증 결과를 JSON 파일로 저장."""
    ensure_evidence_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"validation_{timestamp}.json"
    filepath = os.path.join(EVIDENCE_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\n[INFO] Evidence 저장: {filepath}")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Unity Client 통합 검증")
    parser.add_argument(
        "--unity-path",
        help="Unity.exe 경로 (기본: 자동 탐색)",
        default=None,
    )
    parser.add_argument(
        "--skip-unity",
        action="store_true",
        help="Unity 컴파일 체크 건너뛰기 (컨벤션 검사만 실행)",
    )
    args = parser.parse_args()

    timestamp = datetime.now().isoformat()

    # ━━━ Step 1: 컨벤션 검사 (빠름) ━━━
    print("=" * 60)
    print("  Step 1/2: 컨벤션 검사")
    print("=" * 60 + "\n")

    convention_result = run_convention_checks()

    # FAIL이 있으면 여기서 중단
    if not convention_result["all_passed"]:
        print("\n" + "=" * 60)
        print("  컨벤션 검사 FAIL — Unity 컴파일 건너뜀")
        print("  컨벤션 위반을 먼저 수정하세요.")
        print("=" * 60)

        evidence = {
            "timestamp": timestamp,
            "all_passed": False,
            "stopped_at": "convention_check",
            "convention_check": {
                "passed": convention_result["passed"],
                "failed": convention_result["failed"],
                "warnings": convention_result["warnings"],
            },
            "compile_check": None,
            "details": convention_result["details"],
        }
        save_evidence(evidence)
        sys.exit(1)

    # ━━━ Step 2: Unity 컴파일 체크 (느림) ━━━
    if args.skip_unity:
        print("\n" + "=" * 60)
        print("  Step 2/2: Unity 컴파일 — 건너뜀 (--skip-unity)")
        print("=" * 60)

        evidence = {
            "timestamp": timestamp,
            "all_passed": True,
            "convention_check": {
                "passed": convention_result["passed"],
                "failed": convention_result["failed"],
                "warnings": convention_result["warnings"],
            },
            "compile_check": {"skipped": True},
            "details": convention_result["details"],
        }
        save_evidence(evidence)
        print("\n━━━ 전체 결과: PASS (컨벤션만, Unity 컴파일 생략) ━━━")
        sys.exit(0)

    print("\n" + "=" * 60)
    print("  Step 2/2: Unity 컴파일 체크")
    print("=" * 60 + "\n")

    compile_result = run_build_check(args.unity_path)

    # ━━━ 전체 결과 집계 ━━━
    all_passed = convention_result["all_passed"] and compile_result["passed"]

    evidence = {
        "timestamp": timestamp,
        "all_passed": all_passed,
        "convention_check": {
            "passed": convention_result["passed"],
            "failed": convention_result["failed"],
            "warnings": convention_result["warnings"],
        },
        "compile_check": {
            "passed": compile_result["passed"],
            "errors": compile_result["errors"],
            "warnings": compile_result["warnings"],
        },
        "details": convention_result["details"],
    }

    if not compile_result["passed"]:
        evidence["compile_errors"] = compile_result.get("error_details", [])

    save_evidence(evidence)

    print("\n" + "=" * 60)
    status = "PASS" if all_passed else "FAIL"
    print(f"  전체 결과: {status}")
    print(f"  컨벤션: {convention_result['passed']} PASS, {convention_result['failed']} FAIL, {convention_result['warnings']} WARN")
    if not args.skip_unity:
        print(f"  컴파일: {'PASS' if compile_result['passed'] else 'FAIL'} ({compile_result['errors']} errors, {compile_result['warnings']} warnings)")
    print("=" * 60)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
