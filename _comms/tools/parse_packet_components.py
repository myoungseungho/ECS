#!/usr/bin/env python3
"""
PacketComponents.h Parser — 서버 C++ 코드에서 패킷 프로토콜 추출

서버 에이전트가 제공하는 파싱 헬퍼.
클라이언트의 validate_protocol.py가 이 도구를 호출하여
서버 코드(PacketComponents.h)와 protocol.yaml의 일치 여부를 검증할 수 있다.

사용법:
    python parse_packet_components.py                        # JSON 출력 (stdout)
    python parse_packet_components.py --output result.json   # 파일 출력
    python parse_packet_components.py --compare              # yaml과 비교
    python parse_packet_components.py --compare --exclude-internal  # 서버내부 제외
"""

import re
import json
import sys
from pathlib import Path
from typing import Optional

# 프로젝트 루트 자동 탐지
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # _comms/tools/ → project root
PACKET_H = PROJECT_ROOT / "Components" / "PacketComponents.h"
PROTOCOL_YAML = SCRIPT_DIR.parent / "agreements" / "protocol.yaml"

# 서버 내부 전용 메시지 (protocol.yaml에 포함되지 않은 것들만)
# YAML에 포함된 것은 여기에 넣지 않는다 (STATS, FIELD_REGISTER 등은 YAML에 있음)
SERVER_INTERNAL_MESSAGES = {
    'EVENT_SUB_COUNT',       # 84 - 서버 내부 진단 (YAML 미포함)
    'FIELD_REGISTER_ACK',    # 132 - Gate→Field (YAML 미포함)
    'BUS_REGISTER',          # 140 - Server→Bus (YAML 미포함)
    'BUS_REGISTER_ACK',      # 141 - Bus→Server (YAML 미포함)
    'BUS_SUBSCRIBE',         # 142 - Server→Bus (YAML 미포함)
    'BUS_SUB_ACK',           # 143 - Bus→Server (YAML 미포함)
    'BUS_UNSUBSCRIBE',       # 144 - Server→Bus (YAML 미포함)
    'BUS_PUBLISH',           # 145 - Server→Bus (YAML 미포함)
    'BUS_MESSAGE',           # 146 - Bus→Server (YAML 미포함)
}

# ECHO/PING은 세션 주석 이전에 나오므로 수동 매핑
MANUAL_SESSION_MAP = {
    'ECHO': 1,
    'PING': 2,
}


def parse_header(source: str) -> dict:
    """패킷 헤더 상수 추출"""
    header = {}

    m = re.search(r'constexpr\s+int\s+PACKET_HEADER_SIZE\s*=\s*(\d+)', source)
    if m:
        header['header_size'] = int(m.group(1))

    m = re.search(r'constexpr\s+int\s+MAX_PACKET_SIZE\s*=\s*(\d+)', source)
    if m:
        header['max_packet'] = int(m.group(1))

    header['byte_order'] = 'little-endian'
    header['format'] = '[length:u32][msg_type:u16][payload:variable]'

    return header


def parse_payload_comment(comment: str) -> list:
    """
    주석에서 페이로드 필드 추출
    예: "[target_entity(8)]" -> [{"name": "target_entity", "size": 8, "type": "u64"}]
    예: "[count(1) {id(4) name(16)}...]" -> fixed fields + array entry
    """
    if not comment:
        return []

    if any(kw in comment for kw in ('빈 페이로드', 'empty', '빈 payload')):
        return []

    # 가변길이 문자열 패턴 체크: name_len(1) name(N)
    if '(N)' in comment and '_len(' in comment:
        return _parse_variable_string_payload(comment)

    fields = []

    # 배열 패턴: {field(size) ...}...
    array_match = re.search(r'\{(.+?)\}\.\.\.', comment)
    bracket_match = re.search(r'\[(.+?)\]', comment)

    if bracket_match:
        content = bracket_match.group(1)

        if array_match:
            # 배열 앞의 고정 필드
            before_array = content.split('{')[0].strip()
            fixed_fields = re.findall(r'(\w+)\((\d+)(?:\s+\w+)?\)', before_array)

            for name, size in fixed_fields:
                size = int(size)
                fields.append({
                    'name': name,
                    'size': size,
                    'type': _guess_type(name, size)
                })

            # 배열 엔트리 필드
            array_content = array_match.group(1)
            entry_fields = re.findall(r'(\w+)\((\d+)(?:\s+\w+)?\)', array_content)

            entry_size = 0
            entry_field_list = []
            for name, size in entry_fields:
                size = int(size)
                entry_size += size
                entry_field_list.append({
                    'name': name,
                    'size': size,
                    'type': _guess_type(name, size)
                })

            count_field = fixed_fields[-1][0] if fixed_fields else 'count'
            fields.append({
                'name': 'entries',
                'type': 'array',
                'count_field': count_field,
                'entry_size': entry_size,
                'entry_fields': entry_field_list
            })
        else:
            # 일반 고정 필드만
            all_fields = re.findall(r'(\w+)\((\d+)(?:\s+(\w+))?\)', content)
            for match in all_fields:
                name = match[0]
                size = int(match[1])
                type_hint = match[2] if match[2] else None
                fields.append({
                    'name': name,
                    'size': size,
                    'type': type_hint or _guess_type(name, size)
                })

    return fields


def _parse_variable_string_payload(comment: str) -> list:
    """가변길이 문자열이 포함된 페이로드 파싱"""
    bracket_match = re.search(r'\[(.+?)\]', comment)
    if not bracket_match:
        return []

    content = bracket_match.group(1)
    fields = []

    # 패턴: name_len(1) name(N) 또는 일반 필드 name(4)
    parts = re.findall(r'(\w+)\((\w+)(?:\s+\w+)?\)', content)
    for name, size_str in parts:
        if size_str == 'N':
            fields.append({
                'name': name,
                'type': 'string',
                'size': 'variable'
            })
        else:
            size = int(size_str)
            fields.append({
                'name': name,
                'size': size,
                'type': _guess_type(name, size)
            })

    return fields


def _guess_type(name: str, size: int) -> str:
    """필드 이름과 크기로 타입 추론"""
    # 이름 기반 힌트
    if 'entity' in name and size == 8:
        return 'u64'
    if name in ('result', 'type', 'equipped', 'stacks', 'filter', 'status',
                'found', 'root', 'state', 'priority'):
        return 'u8'

    # 크기 기반
    type_map = {1: 'u8', 2: 'u16', 4: 'u32', 8: 'u64'}
    if size in type_map:
        return type_map[size]

    # string_fixed
    if 'name' in name.lower() and size >= 16:
        return f'string_fixed({size})'

    return f'bytes({size})'


def parse_direction(comment: str) -> str:
    """주석에서 패킷 방향 추출"""
    # C→S 패턴 (유니코드 화살표 + ASCII)
    c2s = bool(re.search(r'C[→\->]S|클라이언트[→\->]서버', comment))
    s2c = bool(re.search(r'S[→\->]C|서버[→\->]클라이언트', comment))

    if c2s and s2c:
        return 'bidirectional'
    if c2s:
        return 'C2S'
    if s2c:
        return 'S2C'

    # 서버 내부
    if re.search(r'(Field|Server|Bus|Gate)[→\->]', comment):
        return 'server-internal'

    # C→Gate 등
    if re.search(r'C[→\->](Gate|게이트)', comment):
        return 'C2S'
    if re.search(r'(Gate|게이트)[→\->]C', comment):
        return 'S2C'

    return 'unknown'


def parse_msgtype_enum(source: str) -> list:
    """MsgType enum 전체 파싱"""
    messages = []
    current_session = 0

    # 세션 주석 패턴: "// Session N:" 또는 "Session N"
    session_pattern = re.compile(r'Session\s+(\d+)')

    # 줄별 세션 번호 추적
    lines = source.split('\n')
    line_sessions = {}
    for i, line in enumerate(lines):
        sm = session_pattern.search(line)
        if sm:
            current_session = int(sm.group(1))
        line_sessions[i] = current_session

    # enum 멤버: NAME = VALUE, // 주석
    member_pattern = re.compile(
        r'^\s*(\w+)\s*=\s*(\d+)\s*,?\s*//\s*(.+)$',
        re.MULTILINE
    )

    for match in member_pattern.finditer(source):
        name = match.group(1)
        msg_id = int(match.group(2))
        comment = match.group(3).strip()

        # 줄 번호로 세션 결정
        line_num = source[:match.start()].count('\n')
        session = line_sessions.get(line_num, 0)

        # 수동 매핑 오버라이드 (ECHO, PING 등)
        if name in MANUAL_SESSION_MAP:
            session = MANUAL_SESSION_MAP[name]

        # 서버 내부 여부
        is_internal = name in SERVER_INTERNAL_MESSAGES

        direction = parse_direction(comment)
        payload = parse_payload_comment(comment)
        total_size = _calc_payload_size(payload)

        msg = {
            'name': name,
            'id': msg_id,
            'session': session,
            'direction': direction,
            'comment': comment,
            'payload': payload,
            'is_internal': is_internal,
        }

        if total_size is not None:
            msg['payload_size'] = total_size

        # 주석에 명시된 바이트 크기 (더 정확)
        size_match = re.search(r'=\s*(\d+)\s*바이트', comment)
        if size_match:
            msg['payload_size'] = int(size_match.group(1))

        messages.append(msg)

    return messages


def _calc_payload_size(payload: list) -> Optional[int]:
    """고정 페이로드 크기 계산 (가변이면 None)"""
    if not payload:
        return 0

    total = 0
    for field in payload:
        ftype = field.get('type', '')
        if ftype == 'array':
            return None
        if ftype in ('bytes', 'variable', 'string'):
            return None
        if isinstance(ftype, str) and ftype.startswith('bytes('):
            return None
        if field.get('size') == 'variable':
            return None
        total += field.get('size', 0)

    return total


def parse_full(source: str) -> dict:
    """전체 파싱 결과"""
    messages = parse_msgtype_enum(source)
    client_msgs = [m for m in messages if not m['is_internal']]
    internal_msgs = [m for m in messages if m['is_internal']]

    return {
        'source_file': 'Components/PacketComponents.h',
        'header': parse_header(source),
        'messages': messages,
        'message_count': len(messages),
        'client_facing_count': len(client_msgs),
        'server_internal_count': len(internal_msgs),
        'server_internal_names': [m['name'] for m in internal_msgs],
    }


def compare_with_yaml(parsed: dict, yaml_path: str,
                      exclude_internal: bool = True) -> dict:
    """protocol.yaml과 비교"""
    try:
        import yaml as yaml_lib
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml_lib.safe_load(f)
        return _do_compare_full(parsed, yaml_data, exclude_internal)
    except ImportError:
        return _compare_simple(parsed, yaml_path, exclude_internal)


def _compare_simple(parsed: dict, yaml_path: str,
                    exclude_internal: bool = True) -> dict:
    """PyYAML 없이 regex 기반 비교"""
    yaml_ids = {}
    current_msg = None

    with open(yaml_path, 'r', encoding='utf-8') as f:
        for line in f:
            msg_match = re.match(r'^  (\w+):\s*$', line)
            if msg_match:
                current_msg = msg_match.group(1)

            id_match = re.match(r'^    id:\s*(\d+)', line)
            if id_match and current_msg:
                yaml_ids[current_msg] = int(id_match.group(1))

    # C++ 메시지 (옵션에 따라 내부 메시지 제외)
    cpp_msgs = {}
    for m in parsed['messages']:
        if exclude_internal and m['is_internal']:
            continue
        cpp_msgs[m['name']] = m

    mismatches = []
    matched = []

    # YAML에 있는 것 vs C++
    for name, yaml_id in yaml_ids.items():
        if name in cpp_msgs:
            cpp_id = cpp_msgs[name]['id']
            if cpp_id != yaml_id:
                mismatches.append({
                    'message': name,
                    'field': 'id',
                    'cpp': cpp_id,
                    'yaml': yaml_id,
                    'severity': 'HIGH'
                })
            else:
                matched.append(name)
        else:
            mismatches.append({
                'message': name,
                'issue': 'YAML에만 존재 (C++에 없음)',
                'severity': 'MEDIUM'
            })

    # C++에 있는데 YAML에 없는 것
    for name in cpp_msgs:
        if name not in yaml_ids:
            mismatches.append({
                'message': name,
                'issue': 'C++에만 존재 (YAML에 없음)',
                'cpp_id': cpp_msgs[name]['id'],
                'severity': 'MEDIUM'
            })

    total = max(len(yaml_ids), len(cpp_msgs), 1)
    match_pct = len(matched) / total * 100

    return {
        'cpp_count': len(cpp_msgs),
        'yaml_count': len(yaml_ids),
        'matched_count': len(matched),
        'mismatches': mismatches,
        'match_rate': f"{match_pct:.1f}%",
        'exclude_internal': exclude_internal,
        'excluded_internal_msgs': list(SERVER_INTERNAL_MESSAGES) if exclude_internal else [],
    }


def _do_compare_full(parsed: dict, yaml_data: dict,
                     exclude_internal: bool = True) -> dict:
    """PyYAML 기반 상세 비교"""
    yaml_msgs = yaml_data.get('messages', {})

    cpp_msgs = {}
    for m in parsed['messages']:
        if exclude_internal and m['is_internal']:
            continue
        cpp_msgs[m['name']] = m

    mismatches = []
    matched = []

    for name, ydef in yaml_msgs.items():
        if name in cpp_msgs:
            cdef = cpp_msgs[name]

            # ID 비교
            if cdef['id'] != ydef.get('id'):
                mismatches.append({
                    'message': name,
                    'field': 'id',
                    'cpp': cdef['id'],
                    'yaml': ydef.get('id'),
                    'severity': 'HIGH'
                })
            else:
                matched.append(name)

            # 세션 비교 (불일치는 LOW)
            yaml_session = ydef.get('session', 0)
            if cdef['session'] != yaml_session and yaml_session != 0:
                mismatches.append({
                    'message': name,
                    'field': 'session',
                    'cpp': cdef['session'],
                    'yaml': yaml_session,
                    'severity': 'LOW'
                })

            # 페이로드 크기 비교 (있으면)
            cpp_size = cdef.get('payload_size')
            yaml_payload = ydef.get('payload', [])
            if cpp_size is not None and yaml_payload:
                yaml_size = sum(
                    f.get('size', 0) for f in yaml_payload
                    if isinstance(f, dict) and isinstance(f.get('size'), int)
                )
                if yaml_size > 0 and cpp_size != yaml_size:
                    mismatches.append({
                        'message': name,
                        'field': 'payload_size',
                        'cpp': cpp_size,
                        'yaml': yaml_size,
                        'severity': 'MEDIUM'
                    })
        else:
            mismatches.append({
                'message': name,
                'issue': 'YAML에만 존재',
                'severity': 'MEDIUM'
            })

    for name in cpp_msgs:
        if name not in yaml_msgs:
            mismatches.append({
                'message': name,
                'issue': 'C++에만 존재',
                'cpp_id': cpp_msgs[name]['id'],
                'severity': 'MEDIUM'
            })

    total = max(len(yaml_msgs), len(cpp_msgs), 1)
    match_pct = len(matched) / total * 100

    return {
        'cpp_count': len(cpp_msgs),
        'yaml_count': len(yaml_msgs),
        'matched_count': len(matched),
        'mismatches': mismatches,
        'match_rate': f"{match_pct:.1f}%",
        'exclude_internal': exclude_internal,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='PacketComponents.h Parser - 서버 C++ 코드에서 패킷 프로토콜 추출'
    )
    parser.add_argument('--source', default=str(PACKET_H),
                        help='PacketComponents.h 경로')
    parser.add_argument('--output', '-o', help='출력 JSON 파일 경로')
    parser.add_argument('--compare', '-c', nargs='?', const=str(PROTOCOL_YAML),
                        help='protocol.yaml과 비교 (경로 생략 시 기본 위치)')
    parser.add_argument('--exclude-internal', action='store_true', default=True,
                        help='서버 내부 메시지 비교에서 제외 (기본: True)')
    parser.add_argument('--include-internal', action='store_true',
                        help='서버 내부 메시지도 비교에 포함')
    parser.add_argument('--pretty', action='store_true', default=True,
                        help='JSON 보기 좋게 출력')

    args = parser.parse_args()
    exclude_internal = not args.include_internal

    # 소스 읽기
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"ERROR: {source_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(source_path, 'r', encoding='utf-8') as f:
        source = f.read()

    # 파싱
    result = parse_full(source)

    # 비교 모드
    if args.compare:
        yaml_path = Path(args.compare)
        if not yaml_path.exists():
            print(f"ERROR: {yaml_path} not found", file=sys.stderr)
            sys.exit(1)

        comparison = compare_with_yaml(result, str(yaml_path), exclude_internal)
        result['comparison'] = comparison

        # 결과 요약 (stderr)
        print(f"\n{'='*50}", file=sys.stderr)
        print(f"PacketComponents.h vs protocol.yaml", file=sys.stderr)
        print(f"{'='*50}", file=sys.stderr)
        print(f"C++ messages (client-facing): {comparison['cpp_count']}", file=sys.stderr)
        print(f"YAML messages:                {comparison['yaml_count']}", file=sys.stderr)
        print(f"Matched:                      {comparison['matched_count']}", file=sys.stderr)
        print(f"Match rate:                   {comparison['match_rate']}", file=sys.stderr)

        if exclude_internal:
            print(f"Server-internal excluded:     {result['server_internal_count']} "
                  f"({', '.join(result['server_internal_names'][:5])}...)", file=sys.stderr)

        high = [m for m in comparison['mismatches'] if m.get('severity') == 'HIGH']
        medium = [m for m in comparison['mismatches'] if m.get('severity') == 'MEDIUM']
        low = [m for m in comparison['mismatches'] if m.get('severity') == 'LOW']

        if high:
            print(f"\n[HIGH] ID Mismatches ({len(high)}):", file=sys.stderr)
            for mm in high:
                print(f"  {mm['message']}.{mm['field']}: C++={mm['cpp']} vs YAML={mm['yaml']}",
                      file=sys.stderr)

        if medium:
            print(f"\n[MEDIUM] Missing Messages ({len(medium)}):", file=sys.stderr)
            for mm in medium:
                if 'field' in mm:
                    print(f"  {mm['message']}.{mm['field']}: C++={mm['cpp']} vs YAML={mm['yaml']}",
                          file=sys.stderr)
                else:
                    extra = f" (id={mm['cpp_id']})" if 'cpp_id' in mm else ''
                    print(f"  {mm['message']}: {mm['issue']}{extra}", file=sys.stderr)

        if low:
            print(f"\n[LOW] Minor ({len(low)}):", file=sys.stderr)
            for mm in low:
                print(f"  {mm['message']}.{mm['field']}: C++={mm['cpp']} vs YAML={mm['yaml']}",
                      file=sys.stderr)

        if not comparison['mismatches']:
            print(f"\nAll messages match!", file=sys.stderr)

        print(f"{'='*50}", file=sys.stderr)

    # JSON 출력
    indent = 2 if args.pretty else None
    json_str = json.dumps(result, indent=indent, ensure_ascii=False)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"\nSaved: {args.output}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == '__main__':
    main()
