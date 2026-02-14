#!/usr/bin/env python3
"""
validate_client.py — Unity Client 컨벤션 강제 검증기

Unity 없이 순수 텍스트 분석으로 규칙 위반 검출.
서버의 validate_project.py 패턴을 미러링.

사용법: python validate_client.py
"""

import io
import os
import re
import sys

# Windows 콘솔 UTF-8 출력 보장
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ━━━ 경로 설정 ━━━

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(SCRIPT_DIR, "Assets")
SCRIPTS_DIR = os.path.join(ASSETS_DIR, "Scripts")
MANAGERS_DIR = os.path.join(SCRIPTS_DIR, "Managers")
NETWORK_DIR = os.path.join(SCRIPTS_DIR, "Network")
EDITOR_DIR = os.path.join(ASSETS_DIR, "Editor")
INTERACTION_MAP = os.path.join(SCRIPTS_DIR, "interaction-map.yaml")
PROJECT_SETUP = os.path.join(EDITOR_DIR, "ProjectSetup.cs")

# ━━━ 결과 카운터 ━━━

_pass_count = 0
_fail_count = 0
_warn_count = 0
_details = []


def log_pass(msg):
    global _pass_count
    _pass_count += 1
    line = f"[PASS] {msg}"
    print(line)
    _details.append({"level": "PASS", "message": msg})


def log_fail(msg):
    global _fail_count
    _fail_count += 1
    line = f"[FAIL] {msg}"
    print(line)
    _details.append({"level": "FAIL", "message": msg})


def log_warn(msg):
    global _warn_count
    _warn_count += 1
    line = f"[WARN] {msg}"
    print(line)
    _details.append({"level": "WARN", "message": msg})


# ━━━ 유틸리티 ━━━

def read_file(path):
    """파일 내용을 읽어 반환. 실패 시 None."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read()
    except (OSError, IOError):
        return None


def get_cs_files(directory):
    """디렉토리 내 .cs 파일 목록 반환."""
    if not os.path.isdir(directory):
        return []
    return [f for f in os.listdir(directory) if f.endswith(".cs")]


def parse_managers_from_yaml(yaml_path):
    """
    interaction-map.yaml에서 managers 섹션의 name 목록을 추출.
    PyYAML 의존성을 피하기 위해 간단한 regex 파싱.
    """
    content = read_file(yaml_path)
    if content is None:
        return None

    managers = []
    in_managers = False
    for line in content.splitlines():
        stripped = line.strip()
        # managers: 섹션 시작 (최상위 레벨 = 들여쓰기 없음)
        if stripped == "managers:" and not line[0].isspace():
            in_managers = True
            continue
        # 다른 최상위 섹션 시작 시 종료 (들여쓰기 없는 key:)
        if in_managers and line and not line[0].isspace() and re.match(r"^[a-z_]+:", stripped):
            break
        # manager name 추출
        if in_managers:
            m = re.match(r"-\s*name:\s*(\w+)", stripped)
            if m:
                managers.append(m.group(1))

    return managers


def parse_managers_from_projectsetup(setup_path):
    """
    ProjectSetup.cs에서 CreateManagerObject 호출로 등록된 매니저 목록 추출.
    패턴: CreateManagerObject("ManagerName", typeof(...))
    """
    content = read_file(setup_path)
    if content is None:
        return None

    managers = []
    for m in re.finditer(r'CreateManagerObject\(\s*"(\w+)"', content):
        managers.append(m.group(1))
    return managers


# ━━━ 검사 항목 ━━━

def check_interaction_map_sync():
    """interaction-map.yaml에 등록된 Manager ↔ 실제 Manager 파일 일치."""
    yaml_managers = parse_managers_from_yaml(INTERACTION_MAP)
    if yaml_managers is None:
        log_fail("interaction-map.yaml 파일을 찾을 수 없음")
        return

    actual_files = get_cs_files(MANAGERS_DIR)
    actual_names = {f.replace(".cs", "") for f in actual_files}
    yaml_set = set(yaml_managers)

    # NetworkManager는 Network/ 폴더에 있으므로 별도 처리
    network_files = get_cs_files(NETWORK_DIR)
    network_names = {f.replace(".cs", "") for f in network_files}

    # EntityPool은 Utils/에 있을 수 있음
    utils_dir = os.path.join(SCRIPTS_DIR, "Utils")
    utils_files = get_cs_files(utils_dir)
    utils_names = {f.replace(".cs", "") for f in utils_files}

    # JobChangeUI 등 일부 싱글톤은 UI/에 위치
    ui_dir = os.path.join(SCRIPTS_DIR, "UI")
    ui_files = get_cs_files(ui_dir)
    ui_names = {f.replace(".cs", "") for f in ui_files}

    all_actual = actual_names | network_names | utils_names | ui_names

    # yaml에 있는데 파일이 없는 것
    missing_files = yaml_set - all_actual
    # 파일은 있는데 yaml에 없는 매니저 (Managers/ 폴더 기준)
    unregistered = actual_names - yaml_set

    if missing_files:
        for name in sorted(missing_files):
            log_fail(f"interaction-map.yaml에 등록되었으나 파일 없음 — {name}")
    if unregistered:
        for name in sorted(unregistered):
            log_fail(f"interaction-map.yaml에 미등록 — {name}.cs")

    registered_count = len(yaml_set - missing_files)
    total = len(yaml_set)
    if not missing_files and not unregistered:
        log_pass(f"interaction-map.yaml 동기화 — {registered_count}/{total} 매니저 등록됨")


def check_singleton_pattern():
    """모든 Manager에 싱글톤 패턴 존재 확인."""
    yaml_managers = parse_managers_from_yaml(INTERACTION_MAP)
    if yaml_managers is None:
        return

    singleton_re = re.compile(r"public\s+static\s+\w+\s+Instance\s*\{")

    for name in yaml_managers:
        # 파일 찾기
        path = _find_manager_file(name)
        if path is None:
            # 파일 누락은 다른 검사에서 처리
            continue

        content = read_file(path)
        if content is None:
            continue

        if singleton_re.search(content):
            log_pass(f"싱글톤 패턴 — {name}.cs")
        else:
            log_fail(f"싱글톤 패턴 누락 — {name}.cs")


def check_ondestroy():
    """모든 Manager에 OnDestroy() 이벤트 해제 존재 확인."""
    yaml_managers = parse_managers_from_yaml(INTERACTION_MAP)
    if yaml_managers is None:
        return

    ondestroy_re = re.compile(r"(private|protected|public|void)\s+.*OnDestroy\s*\(")

    for name in yaml_managers:
        path = _find_manager_file(name)
        if path is None:
            continue

        content = read_file(path)
        if content is None:
            continue

        # subscribes_to가 비어있는 매니저는 OnDestroy 불필요할 수 있음
        # 하지만 규칙상 모든 Manager에 OnDestroy 요구
        if ondestroy_re.search(content):
            log_pass(f"OnDestroy 존재 — {name}.cs")
        else:
            log_fail(f"OnDestroy 누락 — {name}.cs")


def check_network_namespace():
    """Scripts/Network/ 파일은 namespace Network 사용."""
    if not os.path.isdir(NETWORK_DIR):
        log_fail("Scripts/Network/ 디렉토리 없음")
        return

    namespace_re = re.compile(r"namespace\s+Network\b")

    for fname in get_cs_files(NETWORK_DIR):
        path = os.path.join(NETWORK_DIR, fname)
        content = read_file(path)
        if content is None:
            continue

        if namespace_re.search(content):
            log_pass(f"namespace Network — {fname}")
        else:
            log_fail(f"namespace Network 누락 — {fname}")


def check_find_usage():
    """런타임 코드에 Find(, FindObjectOfType( 금지 (Editor 폴더 제외)."""
    find_re = re.compile(r"\b(Find|FindObjectOfType|FindObjectsOfType)\s*\(")
    editor_dir_normalized = os.path.normpath(EDITOR_DIR).lower()

    violations = []
    for root, dirs, files in os.walk(SCRIPTS_DIR):
        # Editor 폴더 제외
        norm_root = os.path.normpath(root).lower()
        if norm_root.startswith(editor_dir_normalized):
            continue

        for fname in files:
            if not fname.endswith(".cs"):
                continue
            path = os.path.join(root, fname)
            content = read_file(path)
            if content is None:
                continue

            for i, line in enumerate(content.splitlines(), 1):
                # 주석 라인 무시
                stripped = line.strip()
                if stripped.startswith("//"):
                    continue
                m = find_re.search(line)
                if m:
                    violations.append((fname, i, m.group(1)))

    if violations:
        for fname, lineno, func in violations:
            log_fail(f"런타임 Find 사용 금지 — {fname}:{lineno} ({func})")
    else:
        log_pass("런타임 Find/FindObjectOfType 사용 없음")


def check_public_fields():
    """MonoBehaviour 스크립트에서 public 필드 대신 [SerializeField] private 사용 권장 (경고).
    데이터 클래스/구조체(DTO)는 검사 대상에서 제외."""
    # public 타입 변수명 패턴 (이벤트, 프로퍼티, 메서드, const, static, enum 제외)
    public_field_re = re.compile(
        r"^\s*public\s+"
        r"(?!static\s|event\s|delegate\s|enum\s|class\s|interface\s|struct\s|override\s|virtual\s|abstract\s|const\s)"
        r"(\w+[\w<>\[\],\s]*?)\s+(\w+)\s*[=;]"
    )
    # 프로퍼티 패턴 (get/set이 있으면 프로퍼티)
    property_re = re.compile(r"\{.*get")
    # MonoBehaviour 상속 패턴
    monobehaviour_re = re.compile(r"class\s+\w+\s*:\s*MonoBehaviour")

    editor_dir_normalized = os.path.normpath(EDITOR_DIR).lower()

    # MonoBehaviour를 상속하는 스크립트만 검사 (데이터 클래스/구조체 제외)
    for root, dirs, files in os.walk(SCRIPTS_DIR):
        norm_root = os.path.normpath(root).lower()
        if norm_root.startswith(editor_dir_normalized):
            continue

        for fname in files:
            if not fname.endswith(".cs"):
                continue
            path = os.path.join(root, fname)
            content = read_file(path)
            if content is None:
                continue

            # MonoBehaviour를 상속하지 않으면 검사 스킵
            if not monobehaviour_re.search(content):
                continue

            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("//"):
                    continue

                m = public_field_re.match(stripped)
                if m:
                    # 같은 줄에 { get 이 있으면 프로퍼티이므로 무시
                    if property_re.search(stripped):
                        continue
                    # => 가 있으면 expression-bodied 프로퍼티이므로 무시
                    if "=>" in stripped:
                        continue
                    field_name = m.group(2)
                    log_warn(f"public 필드 - {fname}:{i} ({field_name})")


def check_file_length():
    """파일 500줄 초과 시 경고."""
    for root, dirs, files in os.walk(SCRIPTS_DIR):
        for fname in files:
            if not fname.endswith(".cs"):
                continue
            path = os.path.join(root, fname)
            content = read_file(path)
            if content is None:
                continue

            line_count = len(content.splitlines())
            if line_count > 500:
                log_warn(f"파일 500줄 초과 — {fname} ({line_count}줄)")


def check_projectsetup_sync():
    """ProjectSetup.cs에 등록된 Manager 목록 ↔ 실제 Manager 파일 일치."""
    setup_managers = parse_managers_from_projectsetup(PROJECT_SETUP)
    if setup_managers is None:
        log_fail("ProjectSetup.cs 파일을 찾을 수 없음")
        return

    yaml_managers = parse_managers_from_yaml(INTERACTION_MAP)
    if yaml_managers is None:
        return

    setup_set = set(setup_managers)
    yaml_set = set(yaml_managers)

    # yaml에 있는데 ProjectSetup에 없는 것
    missing_in_setup = yaml_set - setup_set
    # ProjectSetup에 있는데 yaml에 없는 것
    extra_in_setup = setup_set - yaml_set

    if missing_in_setup:
        for name in sorted(missing_in_setup):
            log_fail(f"ProjectSetup.cs에 미등록 — {name}")
    if extra_in_setup:
        for name in sorted(extra_in_setup):
            log_warn(f"ProjectSetup.cs에 있으나 yaml에 미등록 — {name}")

    if not missing_in_setup and not extra_in_setup:
        log_pass(f"ProjectSetup.cs 동기화 — {len(setup_set)}/{len(yaml_set)} 매니저 등록됨")


# ━━━ 헬퍼 ━━━

def _find_manager_file(name):
    """매니저 이름으로 .cs 파일 경로를 찾는다. Managers/, Network/, Utils/ 순서."""
    candidates = [
        os.path.join(MANAGERS_DIR, f"{name}.cs"),
        os.path.join(NETWORK_DIR, f"{name}.cs"),
        os.path.join(SCRIPTS_DIR, "Utils", f"{name}.cs"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


# ━━━ 메인 ━━━

def run_all_checks():
    """모든 검사를 실행하고 결과를 반환."""
    global _pass_count, _fail_count, _warn_count, _details
    _pass_count = 0
    _fail_count = 0
    _warn_count = 0
    _details = []

    print("━━━ Unity Client 컨벤션 검증 시작 ━━━\n")

    check_interaction_map_sync()
    check_singleton_pattern()
    check_ondestroy()
    check_network_namespace()
    check_find_usage()
    check_public_fields()
    check_file_length()
    check_projectsetup_sync()

    print(f"\n━━━ 결과: {_pass_count} PASS, {_fail_count} FAIL, {_warn_count} WARN ━━━")

    return {
        "passed": _pass_count,
        "failed": _fail_count,
        "warnings": _warn_count,
        "all_passed": _fail_count == 0,
        "details": list(_details),
    }


def main():
    result = run_all_checks()
    sys.exit(0 if result["all_passed"] else 1)


if __name__ == "__main__":
    main()
