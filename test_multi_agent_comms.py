"""
Multi-Agent Communication System Test
======================================
6개 에이전트 메일박스 시스템의 전체 동작을 검증합니다.

Claude CLI 없이 순수 파이썬으로 메시지 라우팅/충돌방지/블로킹을 테스트합니다.

실행:
  python test_multi_agent_comms.py
"""

import sys
import os
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# 테스트용 경로 설정
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "_comms"))

# 테스트 격리를 위한 임시 디렉토리
TEST_DIR = None
ORIGINAL_COMMS = None

PASS = 0
FAIL = 0
TOTAL = 0


def setup_test_env():
    """테스트 환경 생성 - 실제 _comms를 건드리지 않고 격리"""
    global TEST_DIR, ORIGINAL_COMMS
    TEST_DIR = Path(tempfile.mkdtemp(prefix="multi_agent_test_"))

    # 최소 구조 생성
    comms = TEST_DIR / "_comms"
    comms.mkdir()

    for agent in ["server", "client", "db", "design", "qa", "tool"]:
        (comms / "mailbox" / agent).mkdir(parents=True)

    (comms / "boards").mkdir()
    (comms / "contracts").mkdir()
    (comms / "daemon_logs").mkdir()

    # agent_config.json 복사
    src_config = SCRIPT_DIR / "_comms" / "agent_config.json"
    if src_config.exists():
        shutil.copy2(src_config, comms / "agent_config.json")
    else:
        raise FileNotFoundError("agent_config.json not found")

    # blocking.md 초기화
    (comms / "boards" / "blocking.md").write_text(
        "# Blocking Issues\n\n## Active Blocks\n\n(none)\n\n## Resolved\n\n(none)\n",
        encoding="utf-8"
    )

    # 빈 저널
    journal = {
        "meta": {"schema_version": 3},
        "timeline": [],
        "decisions": [],
        "agent_states": {}
    }
    (comms / "conversation_journal.json").write_text(
        json.dumps(journal, indent=2), encoding="utf-8"
    )

    return comms


def teardown_test_env():
    """테스트 환경 정리"""
    global TEST_DIR
    if TEST_DIR and TEST_DIR.exists():
        shutil.rmtree(TEST_DIR, ignore_errors=True)


def test(name: str):
    """테스트 데코레이터"""
    def decorator(func):
        def wrapper():
            global PASS, FAIL, TOTAL
            TOTAL += 1
            try:
                func()
                PASS += 1
                print(f"  PASS  {TOTAL:02d}. {name}")
            except AssertionError as e:
                FAIL += 1
                print(f"  FAIL  {TOTAL:02d}. {name}: {e}")
            except Exception as e:
                FAIL += 1
                print(f"  ERROR {TOTAL:02d}. {name}: {type(e).__name__}: {e}")
        wrapper.__name__ = func.__name__
        wrapper._test_name = name
        return wrapper
    return decorator


# ─── 모듈 임포트 (테스트 환경에서) ─────────────────

def get_test_modules(comms_dir: Path):
    """테스트 환경용 모듈 함수들 (multi_agent_daemon.py의 핵심 로직 재현)"""
    import importlib.util

    # multi_agent_daemon.py를 임포트하되 경로를 오버라이드
    spec = importlib.util.spec_from_file_location(
        "multi_agent_daemon",
        str(SCRIPT_DIR / "_comms" / "multi_agent_daemon.py")
    )
    mod = importlib.util.module_from_spec(spec)

    # 경로 오버라이드
    mod.REPO_ROOT = comms_dir.parent
    mod.COMMS_DIR = comms_dir
    mod.MAILBOX_DIR = comms_dir / "mailbox"
    mod.BOARDS_DIR = comms_dir / "boards"
    mod.CONTRACTS_DIR = comms_dir / "contracts"
    mod.CONFIG_FILE = comms_dir / "agent_config.json"
    mod.JOURNAL_FILE = comms_dir / "conversation_journal.json"
    mod.LOG_DIR = comms_dir / "daemon_logs"

    spec.loader.exec_module(mod)

    # 다시 오버라이드 (모듈 로드 후)
    mod.REPO_ROOT = comms_dir.parent
    mod.COMMS_DIR = comms_dir
    mod.MAILBOX_DIR = comms_dir / "mailbox"
    mod.BOARDS_DIR = comms_dir / "boards"
    mod.CONTRACTS_DIR = comms_dir / "contracts"
    mod.CONFIG_FILE = comms_dir / "agent_config.json"
    mod.JOURNAL_FILE = comms_dir / "conversation_journal.json"
    mod.LOG_DIR = comms_dir / "daemon_logs"
    mod.HUB_ACTIVE_FILE = comms_dir / ".hub_active"
    mod.HUB_INBOX_FILE = comms_dir / ".hub_inbox.json"

    return mod


# ═══════════════════════════════════════════════════════
# 테스트 케이스
# ═══════════════════════════════════════════════════════

@test("에이전트 설정 로드")
def test_01_load_config():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()
    assert "agents" in config
    assert len(config["agents"]) == 6
    for role in ["server", "client", "db", "design", "qa", "tool"]:
        assert role in config["agents"], f"{role} 없음"
        assert "prefix" in config["agents"][role]
        assert "can_message" in config["agents"][role]
    teardown_test_env()


@test("메일박스 디렉토리 구조 확인")
def test_02_mailbox_structure():
    comms = setup_test_env()
    for agent in ["server", "client", "db", "design", "qa", "tool"]:
        mailbox = comms / "mailbox" / agent
        assert mailbox.exists(), f"{agent} mailbox 없음"
        assert mailbox.is_dir(), f"{agent} mailbox가 디렉토리가 아님"
    teardown_test_env()


@test("메시지 생성 - 서버→클라")
def test_03_create_message():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    filepath = mod.create_message(
        sender="server",
        receiver="client",
        msg_id="S019",
        msg_type="spec",
        priority="P2",
        subject="새 패킷 추가",
        body="ADMIN_RELOAD 패킷이 추가되었습니다."
    )

    assert filepath.exists(), "메시지 파일이 생성되지 않음"
    assert filepath.parent.name == "client", "클라이언트 mailbox에 저장되어야 함"

    msg = mod.Message(filepath)
    assert msg.id == "S019"
    assert msg.sender == "server-agent"
    assert msg.msg_type == "spec"
    assert msg.status == "pending"
    teardown_test_env()


@test("메시지 생성 - DB→서버")
def test_04_db_to_server():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    filepath = mod.create_message(
        sender="db",
        receiver="server",
        msg_id="D001",
        msg_type="spec",
        priority="P1",
        subject="TCharacter 스키마 완성",
        body="CREATE TABLE TCharacter (...) 스키마가 확정되었습니다."
    )

    assert filepath.exists()
    assert filepath.parent.name == "server"
    msg = mod.Message(filepath)
    assert msg.id == "D001"
    assert msg.sender == "db-agent"
    teardown_test_env()


@test("메시지 생성 - 기획→QA")
def test_05_design_to_qa():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    filepath = mod.create_message(
        sender="design",
        receiver="qa",
        msg_id="G001",
        msg_type="task",
        priority="P2",
        subject="밸런스 변경 테스트 요청",
        body="monster_ai.json에서 boss_hp_mult를 2.0으로 변경했습니다. 보스전 테스트 부탁."
    )

    assert filepath.exists()
    assert filepath.parent.name == "qa"
    teardown_test_env()


@test("MultiAgentDaemon 초기화 - 모든 역할")
def test_06_daemon_init():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    for role in ["server", "client", "db", "design", "qa", "tool"]:
        daemon = mod.MultiAgentDaemon(role, config)
        assert daemon.role == role
        assert daemon.my_mailbox.exists()
    teardown_test_env()


@test("메시지 수신 확인 - pending만 가져오기")
def test_07_check_messages():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 서버 mailbox에 메시지 2개 생성
    mod.create_message("client", "server", "C011", "question", "P2",
                       "질문1", "이거 어떻게 해?")
    mod.create_message("db", "server", "D001", "spec", "P1",
                       "스키마 완성", "CREATE TABLE...")

    daemon = mod.MultiAgentDaemon("server", config)
    msgs = daemon.check_messages()

    assert len(msgs) == 2, f"2개 메시지 예상, {len(msgs)}개 발견"
    ids = {m.id for m in msgs}
    assert "C011" in ids
    assert "D001" in ids
    teardown_test_env()


@test("메시지 상태 업데이트 - pending→read→resolved")
def test_08_status_update():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    filepath = mod.create_message("client", "server", "C012", "question", "P2",
                                  "테스트 질문", "테스트 본문")

    msg = mod.Message(filepath)
    assert msg.status == "pending"

    msg.update_status("read")
    msg2 = mod.Message(filepath)  # 다시 읽기
    assert msg2.status == "read"

    msg2.update_status("resolved")
    msg3 = mod.Message(filepath)
    assert msg3.status == "resolved"
    teardown_test_env()


@test("통신 권한 검증 - can_message")
def test_09_can_message():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    server = mod.MultiAgentDaemon("server", config)
    assert server.can_message("client") == True
    assert server.can_message("db") == True
    assert server.can_message("qa") == True

    tool = mod.MultiAgentDaemon("tool", config)
    assert tool.can_message("server") == True
    assert tool.can_message("qa") == True
    assert tool.can_message("client") == False  # tool → client 불가
    assert tool.can_message("design") == False  # tool → design 불가
    teardown_test_env()


@test("메시지 ID 자동 증가")
def test_10_msg_id_increment():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    # 서버 메시지 3개 생성
    mod.create_message("server", "client", "S019", "spec", "P2", "테스트1", "본문1")
    mod.create_message("server", "db", "S020", "task", "P2", "테스트2", "본문2")
    mod.create_message("server", "qa", "S021", "task", "P2", "테스트3", "본문3")

    next_id = mod.get_next_msg_id("server")
    assert next_id == "S022", f"S022 예상, {next_id} 반환"
    teardown_test_env()


@test("블로킹 보드 - 활성 블록 감지")
def test_11_blocking_board():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    # 블로킹 이슈 등록
    blocking_content = """# Blocking Issues

## Active Blocks

### [BLOCK-001] DB 스키마 미확정
- **등록자**: server-agent
- **등록일**: 2026-02-13
- **차단 대상**: server, client
- **이유**: TCharacter 스키마가 확정되지 않음
- **해제 조건**: db 에이전트가 스키마 확정
- **상태**: active

### [BLOCK-002] 기획 데이터 미완성
- **등록자**: design-agent
- **등록일**: 2026-02-13
- **차단 대상**: qa
- **이유**: 밸런스 데이터 작업 중
- **상태**: active

## Resolved

(none)
"""
    (comms / "boards" / "blocking.md").write_text(blocking_content, encoding="utf-8")

    # 서버: BLOCK-001에 의해 차단
    server_blocks = mod.get_active_blocks("server")
    assert len(server_blocks) == 1
    assert server_blocks[0]["id"] == "BLOCK-001"

    # 클라: BLOCK-001에 의해 차단
    client_blocks = mod.get_active_blocks("client")
    assert len(client_blocks) == 1

    # QA: BLOCK-002에 의해 차단
    qa_blocks = mod.get_active_blocks("qa")
    assert len(qa_blocks) == 1
    assert qa_blocks[0]["id"] == "BLOCK-002"

    # DB: 차단 없음
    db_blocks = mod.get_active_blocks("db")
    assert len(db_blocks) == 0

    # 기획: 차단 없음
    design_blocks = mod.get_active_blocks("design")
    assert len(design_blocks) == 0
    teardown_test_env()


@test("블로킹 해제 - resolved 상태")
def test_12_blocking_resolved():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    blocking_content = """# Blocking Issues

## Active Blocks

### [BLOCK-001] DB 스키마 미확정
- **차단 대상**: server, client
- **상태**: resolved

## Resolved

(resolved above)
"""
    (comms / "boards" / "blocking.md").write_text(blocking_content, encoding="utf-8")

    server_blocks = mod.get_active_blocks("server")
    assert len(server_blocks) == 0, "resolved된 블록은 반환하지 않아야 함"
    teardown_test_env()


@test("저널 업데이트 - 메시지 기록")
def test_13_journal_update():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    mod.update_journal("S019", "server-agent", "client-agent", "spec",
                       "새 패킷 추가", "ADMIN_RELOAD 패킷")
    mod.update_journal("D001", "db-agent", "server-agent", "spec",
                       "스키마 완성", "TCharacter 테이블")

    journal = json.loads((comms / "conversation_journal.json").read_text(encoding="utf-8"))
    timeline = journal["timeline"]
    assert len(timeline) == 2
    assert timeline[0]["id"] == "S019"
    assert timeline[1]["id"] == "D001"
    teardown_test_env()


@test("저널 중복 방지")
def test_14_journal_dedup():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    mod.update_journal("S019", "server-agent", "client-agent", "spec", "테스트", "")
    mod.update_journal("S019", "server-agent", "client-agent", "spec", "테스트", "")
    mod.update_journal("S019", "server-agent", "client-agent", "spec", "테스트", "")

    journal = json.loads((comms / "conversation_journal.json").read_text(encoding="utf-8"))
    s019_count = sum(1 for m in journal["timeline"] if m["id"] == "S019")
    assert s019_count == 1, f"중복: S019가 {s019_count}개"
    teardown_test_env()


@test("daemon.send_message - 통신 가능한 에이전트")
def test_15_daemon_send():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    server = mod.MultiAgentDaemon("server", config)
    msg_id = server.send_message("client", "spec", "패킷 변경 안내",
                                 "ADMIN_RELOAD 패킷이 추가되었습니다.")

    assert msg_id is not None
    assert msg_id.startswith("S")

    # 클라이언트 mailbox에 파일이 있는지 확인
    client_msgs = list((comms / "mailbox" / "client").glob("*.md"))
    assert len(client_msgs) == 1
    teardown_test_env()


@test("daemon.send_message - 통신 불가능한 에이전트 거부")
def test_16_daemon_send_blocked():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    tool = mod.MultiAgentDaemon("tool", config)
    msg_id = tool.send_message("client", "spec", "불가능한 메시지", "이건 안 됨")

    assert msg_id is None, "tool→client 메시지가 차단되어야 함"

    # 클라이언트 mailbox에 파일이 없어야 함
    client_msgs = list((comms / "mailbox" / "client").glob("*.md"))
    assert len(client_msgs) == 0
    teardown_test_env()


@test("E2E 시나리오 - 기획→서버→클라 전파")
def test_17_e2e_design_to_server_to_client():
    """기획이 밸런스 변경 → 서버에 통보 → 서버가 클라에 전파"""
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 1. 기획 에이전트가 서버에게 밸런스 변경 통보
    design = mod.MultiAgentDaemon("design", config)
    g_id = design.send_message("server", "spec", "보스 HP 변경",
        "monster_ai.json에서 boss_hp_mult를 2.0으로 변경했습니다.\n서버 GameConfig 반영 필요.")

    assert g_id is not None

    # 2. 서버 에이전트가 mailbox 확인
    server = mod.MultiAgentDaemon("server", config)
    msgs = server.check_messages()
    assert len(msgs) == 1
    assert msgs[0].sender == "design-agent"

    # 3. 서버가 처리 후 클라에게 전파
    s_id = server.send_message("client", "spec", "보스 HP 표시 변경",
        "GameConfig에 boss_hp_mult=2.0 반영 완료.\n클라 UI에서 보스 HP바 업데이트 필요.")

    assert s_id is not None

    # 4. 클라이언트 mailbox에 서버 메시지 도착
    client = mod.MultiAgentDaemon("client", config)
    client_msgs = client.check_messages()
    assert len(client_msgs) == 1
    assert client_msgs[0].sender == "server-agent"

    # 5. 저널에 2개 메시지 기록
    journal = json.loads((comms / "conversation_journal.json").read_text(encoding="utf-8"))
    assert len(journal["timeline"]) == 2
    teardown_test_env()


@test("E2E 시나리오 - DB 스키마 블로킹→해제→작업 재개")
def test_18_e2e_blocking_flow():
    """DB 스키마 미완성으로 서버 차단 → 완성 후 해제"""
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 1. 블로킹 등록
    blocking = """# Blocking Issues

## Active Blocks

### [BLOCK-001] DB 스키마 미확정
- **차단 대상**: server, client
- **상태**: active
"""
    (comms / "boards" / "blocking.md").write_text(blocking, encoding="utf-8")

    # 2. 서버가 차단됨을 확인
    server = mod.MultiAgentDaemon("server", config)
    blocks = server.check_blocks()
    assert len(blocks) == 1

    # 3. DB 에이전트가 스키마 완성 후 서버에 알림
    db = mod.MultiAgentDaemon("db", config)
    db.send_message("server", "spec", "TCharacter 스키마 확정",
        "CREATE TABLE TCharacter (CharUID INT, Name NVARCHAR(32), ...);\n"
        "저장 프로시저: gp_SaveCharacter, gp_LoadCharacter 준비 완료.")

    # 4. 블로킹 해제
    blocking_resolved = blocking.replace("active", "resolved")
    (comms / "boards" / "blocking.md").write_text(blocking_resolved, encoding="utf-8")

    # 5. 서버가 차단 해제 확인
    blocks_after = server.check_blocks()
    assert len(blocks_after) == 0

    # 6. 서버 mailbox에 DB 메시지 대기 중
    msgs = server.check_messages()
    assert len(msgs) == 1
    assert msgs[0].sender == "db-agent"
    teardown_test_env()


@test("E2E 시나리오 - QA 버그 리포트 라운드트립")
def test_19_e2e_qa_bug_roundtrip():
    """QA가 버그 발견 → 서버에 보고 → 서버가 수정 후 QA에 확인 요청"""
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 1. QA가 서버에 버그 보고
    qa = mod.MultiAgentDaemon("qa", config)
    q_id = qa.send_message("server", "bug", "파티 던전 입장 크래시",
        "## 재현 조건\n1. 파티원 5명 구성\n2. 던전 입장 시도\n3. 서버 크래시\n\n"
        "## 로그\n```\nNullPointerException at DungeonSystem.h:142\n```")

    assert q_id is not None

    # 2. 서버가 버그 확인
    server = mod.MultiAgentDaemon("server", config)
    msgs = server.check_messages()
    assert len(msgs) == 1
    assert msgs[0].msg_type == "bug"

    # 3. 서버가 수정 후 QA에 재테스트 요청
    s_id = server.send_message("qa", "task", "던전 입장 수정 완료 - 재테스트 요청",
        "DungeonSystem.h:142에서 nullptr 체크 추가.\n"
        "파티원 5명 던전 입장 테스트 부탁.")

    assert s_id is not None

    # 4. QA mailbox에 서버 응답 도착
    qa_msgs = qa.check_messages()
    assert len(qa_msgs) == 1
    assert qa_msgs[0].msg_type == "task"
    teardown_test_env()


@test("E2E 시나리오 - 6에이전트 동시 메시지")
def test_20_e2e_all_agents_communicate():
    """모든 에이전트가 동시에 메시지를 주고받는 시뮬레이션"""
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    daemons = {}
    for role in ["server", "client", "db", "design", "qa", "tool"]:
        daemons[role] = mod.MultiAgentDaemon(role, config)

    # 서버 → 클라, DB, QA
    daemons["server"].send_message("client", "spec", "패킷 변경", "새 패킷 3종 추가")
    daemons["server"].send_message("db", "task", "스키마 요청", "캐릭터 저장 테이블 필요")
    daemons["server"].send_message("qa", "task", "테스트 요청", "세션 38 테스트 부탁")

    # 기획 → 서버, QA
    daemons["design"].send_message("server", "spec", "밸런스 변경", "몬스터 HP 조정")
    daemons["design"].send_message("qa", "task", "밸런스 테스트", "보스전 밸런스 확인")

    # DB → 서버
    daemons["db"].send_message("server", "spec", "스키마 완성", "TCharacter 완료")

    # QA → 서버, 클라
    daemons["qa"].send_message("server", "bug", "버그 1", "서버 크래시")
    daemons["qa"].send_message("client", "bug", "버그 2", "UI 렌더링 깨짐")

    # 툴 → 서버
    daemons["tool"].send_message("server", "status", "어드민 툴 완성", "ADMIN_RELOAD UI 완료")

    # 각 에이전트별 수신 확인
    server_msgs = daemons["server"].check_messages()
    client_msgs = daemons["client"].check_messages()
    db_msgs = daemons["db"].check_messages()
    qa_msgs = daemons["qa"].check_messages()

    assert len(server_msgs) == 4, f"서버: 4개 예상, {len(server_msgs)}개"  # design, db, qa, tool
    assert len(client_msgs) == 2, f"클라: 2개 예상, {len(client_msgs)}개"  # server, qa
    assert len(db_msgs) == 1, f"DB: 1개 예상, {len(db_msgs)}개"           # server
    assert len(qa_msgs) == 2, f"QA: 2개 예상, {len(qa_msgs)}개"           # server, design
    teardown_test_env()


@test("파일 소유권 충돌 방지 - 같은 mailbox에 다른 발신자")
def test_21_no_file_collision():
    """여러 에이전트가 같은 mailbox에 동시에 쓸 때 파일명 충돌 없음"""
    comms = setup_test_env()
    mod = get_test_modules(comms)

    # 서버 mailbox에 3개 다른 에이전트가 메시지 작성
    mod.create_message("client", "server", "C011", "question", "P2", "질문", "내용1")
    mod.create_message("db", "server", "D001", "spec", "P1", "스키마", "내용2")
    mod.create_message("design", "server", "G001", "spec", "P2", "밸런스", "내용3")

    server_files = list((comms / "mailbox" / "server").glob("*.md"))
    assert len(server_files) == 3, "파일명 충돌 없이 3개 모두 생성"

    # 파일명에 발신자가 포함되어 구분 가능
    filenames = [f.name for f in server_files]
    assert any("from_client" in f for f in filenames)
    assert any("from_db" in f for f in filenames)
    assert any("from_design" in f for f in filenames)
    teardown_test_env()


@test("processed 추적 - 같은 메시지 2번 처리 방지")
def test_22_no_double_processing():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 메시지 생성
    mod.create_message("client", "server", "C011", "question", "P2", "질문", "내용")

    server = mod.MultiAgentDaemon("server", config)

    # 첫 번째 확인: 1개
    msgs1 = server.check_messages()
    assert len(msgs1) == 1

    # 처리 완료 표시
    server.processed.add(msgs1[0].filepath.name)
    server._save_processed()

    # 두 번째 확인: 0개 (이미 처리됨)
    msgs2 = server.check_messages()
    assert len(msgs2) == 0, "이미 처리된 메시지가 다시 나타남"
    teardown_test_env()


@test("에이전트 프리픽스 고유성")
def test_23_unique_prefixes():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    prefixes = set()
    for role, agent in config["agents"].items():
        p = agent["prefix"]
        assert p not in prefixes, f"프리픽스 {p} 중복! ({role})"
        prefixes.add(p)

    assert len(prefixes) == 6
    teardown_test_env()


@test("대규모 메시지 - 50개 메시지 라우팅")
def test_24_bulk_messages():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 50개 메시지를 각 에이전트에 분산 전송
    agents = ["server", "client", "db", "design", "qa", "tool"]
    message_counts = {a: 0 for a in agents}

    for i in range(50):
        sender = agents[i % 6]
        # can_message 목록에서 수신자 선택
        can_msg = config["agents"][sender]["can_message"]
        if not can_msg:
            continue
        receiver = can_msg[i % len(can_msg)]

        daemon = mod.MultiAgentDaemon(sender, config)
        msg_id = daemon.send_message(receiver, "status", f"메시지 {i}", f"본문 {i}")
        if msg_id:
            message_counts[receiver] += 1

    # 모든 메시지가 올바른 mailbox에 도착했는지 확인
    total_delivered = 0
    for agent in agents:
        mailbox = comms / "mailbox" / agent
        files = list(mailbox.glob("*.md"))
        total_delivered += len(files)
        expected = message_counts[agent]
        assert len(files) == expected, \
            f"{agent}: {expected}개 예상, {len(files)}개 발견"

    assert total_delivered > 0, "메시지가 하나도 전달되지 않음"
    teardown_test_env()


# ═══════════════════════════════════════════════════════
# 하이브리드 모드 테스트
# ═══════════════════════════════════════════════════════

@test("하이브리드 - hub_active 하트비트 감지")
def test_25_hub_heartbeat():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    # 하트비트 없을 때
    assert mod.is_hub_active() == False

    # 하트비트 생성
    hub_file = comms / ".hub_active"
    hub_file.write_text(json.dumps({
        "pid": 12345,
        "timestamp": datetime.now().isoformat(),
        "type": "claude_code_session"
    }), encoding="utf-8")

    assert mod.is_hub_active() == True

    # 만료된 하트비트 (11분 전)
    old_time = datetime.now() - timedelta(minutes=11)
    hub_file.write_text(json.dumps({
        "pid": 12345,
        "timestamp": old_time.isoformat(),
        "type": "claude_code_session"
    }), encoding="utf-8")

    assert mod.is_hub_active() == False
    teardown_test_env()


@test("하이브리드 - auto 모드: hub 살아있으면 알림만")
def test_26_auto_mode_notify():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 허브 활성 상태 만들기
    hub_file = comms / ".hub_active"
    hub_file.write_text(json.dumps({
        "pid": 12345,
        "timestamp": datetime.now().isoformat(),
        "type": "claude_code_session"
    }), encoding="utf-8")

    daemon = mod.MultiAgentDaemon("server", config, mode="auto")
    assert daemon._should_process() == False, "허브 활성 시 알림만 해야 함"
    teardown_test_env()


@test("하이브리드 - auto 모드: hub 죽으면 직접 처리")
def test_27_auto_mode_full():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 허브 없음
    daemon = mod.MultiAgentDaemon("server", config, mode="auto")
    assert daemon._should_process() == True, "허브 없으면 직접 처리해야 함"
    teardown_test_env()


@test("하이브리드 - full 모드: 항상 직접 처리")
def test_28_full_mode():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 허브 활성이어도 full이면 직접 처리
    hub_file = comms / ".hub_active"
    hub_file.write_text(json.dumps({
        "pid": 12345,
        "timestamp": datetime.now().isoformat()
    }), encoding="utf-8")

    daemon = mod.MultiAgentDaemon("server", config, mode="full")
    assert daemon._should_process() == True, "full 모드는 항상 직접 처리"
    teardown_test_env()


@test("하이브리드 - notify 모드: 항상 알림만")
def test_29_notify_mode():
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    # 허브 없어도 notify면 알림만
    daemon = mod.MultiAgentDaemon("server", config, mode="notify")
    assert daemon._should_process() == False, "notify 모드는 항상 알림만"
    teardown_test_env()


@test("하이브리드 - notify_hub 함수: inbox 파일 생성")
def test_30_notify_hub_creates_inbox():
    comms = setup_test_env()
    mod = get_test_modules(comms)

    msgs = [
        {"id": "C011", "from": "client-agent", "to_role": "server",
         "to": "server-agent", "type": "question", "priority": "P2",
         "subject": "이거 어떻게 해?", "file": "test.md"},
        {"id": "D001", "from": "db-agent", "to_role": "server",
         "to": "server-agent", "type": "spec", "priority": "P1",
         "subject": "스키마 완성", "file": "test2.md"}
    ]

    mod.notify_hub(msgs)

    inbox_file = comms / ".hub_inbox.json"
    assert inbox_file.exists(), ".hub_inbox.json이 생성되어야 함"

    inbox = json.loads(inbox_file.read_text(encoding="utf-8"))
    assert inbox["total_pending"] == 2
    assert "server" in inbox["by_agent"]
    assert len(inbox["by_agent"]["server"]) == 2
    teardown_test_env()


@test("E2E - 허브↔데몬 전환 시나리오")
def test_31_hub_daemon_handoff():
    """허브 활성→데몬 알림만 → 허브 종료 → 데몬 자체 처리"""
    comms = setup_test_env()
    mod = get_test_modules(comms)
    config = mod.load_config()

    hub_file = comms / ".hub_active"

    # 1. 허브 활성 상태
    hub_file.write_text(json.dumps({
        "pid": 99999, "timestamp": datetime.now().isoformat()
    }), encoding="utf-8")

    daemon = mod.MultiAgentDaemon("server", config, mode="auto")
    assert daemon._should_process() == False  # 알림만

    # 2. 허브 종료 (하트비트 제거)
    hub_file.unlink()
    assert daemon._should_process() == True   # 직접 처리

    # 3. 허브 다시 시작
    hub_file.write_text(json.dumps({
        "pid": 99998, "timestamp": datetime.now().isoformat()
    }), encoding="utf-8")
    assert daemon._should_process() == False  # 다시 알림만

    teardown_test_env()


# ═══════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════

def main():
    print()
    print("=" * 60)
    print("  Multi-Agent Communication System Test")
    print("  6-Agent Mailbox Pattern Verification")
    print("=" * 60)
    print()

    tests = [
        test_01_load_config,
        test_02_mailbox_structure,
        test_03_create_message,
        test_04_db_to_server,
        test_05_design_to_qa,
        test_06_daemon_init,
        test_07_check_messages,
        test_08_status_update,
        test_09_can_message,
        test_10_msg_id_increment,
        test_11_blocking_board,
        test_12_blocking_resolved,
        test_13_journal_update,
        test_14_journal_dedup,
        test_15_daemon_send,
        test_16_daemon_send_blocked,
        test_17_e2e_design_to_server_to_client,
        test_18_e2e_blocking_flow,
        test_19_e2e_qa_bug_roundtrip,
        test_20_e2e_all_agents_communicate,
        test_21_no_file_collision,
        test_22_no_double_processing,
        test_23_unique_prefixes,
        test_24_bulk_messages,
        # 하이브리드 모드
        test_25_hub_heartbeat,
        test_26_auto_mode_notify,
        test_27_auto_mode_full,
        test_28_full_mode,
        test_29_notify_mode,
        test_30_notify_hub_creates_inbox,
        test_31_hub_daemon_handoff,
    ]

    for t in tests:
        t()

    print()
    print("-" * 60)
    print(f"  결과: {PASS} PASS / {FAIL} FAIL / {TOTAL} TOTAL")
    if FAIL == 0:
        print("  ALL TESTS PASSED!")
    else:
        print(f"  {FAIL}개 테스트 실패")
    print("-" * 60)
    print()

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
