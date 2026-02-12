"""
Meeting Recorder v1.0
======================
에이전트 간 대화를 인간 회의록 형태로 자동 기록합니다.

회의록 구조:
- 각 메시지 교환이 하나의 "안건"
- 발언자별 주장/근거/제안 정리
- 합의사항, 미합의 사항, 다음 액션 추적
- 대표 에스컬레이션 이력도 기록

사용법:
  from meeting_recorder import MeetingRecorder
  recorder = MeetingRecorder()
  recorder.record_exchange(sender, receiver, message, response, decision)
  recorder.close_meeting(summary)
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

COMMS_DIR = Path(__file__).parent
MEETINGS_DIR = COMMS_DIR / "meetings"
MEETINGS_DIR.mkdir(exist_ok=True)


class MeetingRecorder:

    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.meeting_file = MEETINGS_DIR / f"{self.today}.md"
        self.meta_file = MEETINGS_DIR / "meeting_index.json"
        self._ensure_meeting_header()

    def _load_index(self):
        if self.meta_file.exists():
            try:
                return json.loads(self.meta_file.read_text(encoding="utf-8"))
            except:
                pass
        return {"meetings": [], "total_agendas": 0, "total_decisions": 0}

    def _save_index(self, index):
        self.meta_file.write_text(
            json.dumps(index, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def _ensure_meeting_header(self):
        """오늘 회의록 파일이 없으면 헤더 생성"""
        if not self.meeting_file.exists():
            meeting_num = len(list(MEETINGS_DIR.glob("2*.md"))) + 1
            header = f"""# 회의록 #{meeting_num:03d} - {self.today}

| 항목 | 내용 |
|------|------|
| **일시** | {self.today} |
| **참석자** | 서버 에이전트, 클라이언트 에이전트 |
| **회의 방식** | Git 비동기 통신 (_comms/) |
| **기록 방식** | 자동 기록 (meeting_recorder.py) |

---

## 안건 목록

| # | 시간 | 발신 | 안건 | 결과 |
|---|------|------|------|------|

---

"""
            self.meeting_file.write_text(header, encoding="utf-8")

            # 인덱스 업데이트
            index = self._load_index()
            index["meetings"].append({
                "number": meeting_num,
                "date": self.today,
                "file": self.meeting_file.name,
                "agendas": 0,
                "status": "in_progress"
            })
            self._save_index(index)

    def _count_agendas(self):
        """현재 회의록의 안건 수"""
        content = self.meeting_file.read_text(encoding="utf-8")
        return content.count("## 안건 ")  # "## 안건 목록" 제외

    def record_exchange(self, msg_id, sender, receiver, msg_type,
                        message_summary, response_summary,
                        sender_reasoning=None, responder_reasoning=None,
                        decision=None, next_actions=None,
                        escalated=False, ceo_decision=None):
        """
        메시지 교환을 회의 안건으로 기록

        Args:
            msg_id: 원본 메시지 ID (예: "C001")
            sender: 발신자 ("server-agent" or "client-agent")
            receiver: 수신자
            msg_type: 메시지 유형 (spec, question, answer 등)
            message_summary: 발신 메시지 핵심 요약
            response_summary: 응답 메시지 핵심 요약
            sender_reasoning: 발신자의 사고 과정
            responder_reasoning: 응답자의 사고 과정
            decision: 합의된 결정사항
            next_actions: 다음 액션 목록
            escalated: 대표 에스컬레이션 여부
            ceo_decision: 대표 결정 내용
        """
        now = datetime.now().strftime("%H:%M")
        agenda_num = self._count_agendas() + 1

        sender_name = "서버" if "server" in sender else "클라"
        receiver_name = "클라" if "server" in sender else "서버"

        # 안건 상태 결정
        if decision:
            result = "합의"
        elif escalated:
            result = "대표 에스컬레이션"
        else:
            result = "진행중"

        # 안건 목록 테이블에 행 추가
        content = self.meeting_file.read_text(encoding="utf-8")
        table_row = f"| {agenda_num} | {now} | {sender_name} | {message_summary[:40]} | {result} |\n"

        # 테이블 끝(--- 구분선 바로 앞)에 행 삽입
        # "---\n\n" 패턴을 찾아서 그 앞에 삽입
        table_end_marker = "\n---\n\n"
        first_marker_pos = content.find(table_end_marker)
        if first_marker_pos >= 0:
            content = (content[:first_marker_pos] +
                      "\n" + table_row +
                      content[first_marker_pos:])

        # 안건 상세 내용 추가
        agenda_detail = f"""
## 안건 {agenda_num}: {message_summary} [{msg_id}]

**시간**: {now} | **유형**: {msg_type} | **우선순위 흐름**: {sender_name} -> {receiver_name}

### {sender_name} 에이전트 발언

{message_summary}

"""
        if sender_reasoning:
            agenda_detail += f"""**사고 과정**:
{sender_reasoning}

"""

        agenda_detail += f"""### {receiver_name} 에이전트 응답

{response_summary}

"""
        if responder_reasoning:
            agenda_detail += f"""**사고 과정**:
{responder_reasoning}

"""

        if escalated:
            agenda_detail += f"""### 대표 에스컬레이션

이 안건은 에이전트 간 자율 결정 범위를 넘어 **대표에게 보고**되었습니다.

"""
            if ceo_decision:
                agenda_detail += f"""**대표 결정**: {ceo_decision}

"""

        if decision:
            agenda_detail += f"""### 결정사항

{decision}

"""

        if next_actions:
            agenda_detail += "### 다음 액션\n\n"
            for i, action in enumerate(next_actions, 1):
                owner = action.get("owner", "미정")
                task = action.get("task", "")
                deadline = action.get("deadline", "")
                agenda_detail += f"- [ ] **[{owner}]** {task}"
                if deadline:
                    agenda_detail += f" (기한: {deadline})"
                agenda_detail += "\n"
            agenda_detail += "\n"

        agenda_detail += "---\n"

        content += agenda_detail
        self.meeting_file.write_text(content, encoding="utf-8")

        # 인덱스 업데이트
        index = self._load_index()
        index["total_agendas"] += 1
        if decision:
            index["total_decisions"] += 1
        for m in index["meetings"]:
            if m["date"] == self.today:
                m["agendas"] = agenda_num
        self._save_index(index)

        return agenda_num

    def record_discussion_round(self, agenda_num, speaker, content_text, reasoning=None):
        """
        기존 안건에 추가 토론 라운드 기록 (여러 번 왔다갔다 할 때)
        """
        now = datetime.now().strftime("%H:%M")
        speaker_name = "서버" if "server" in speaker else "클라"

        addition = f"""
#### [{now}] {speaker_name} 에이전트 추가 발언

{content_text}

"""
        if reasoning:
            addition += f"""**사고 과정**: {reasoning}

"""

        content = self.meeting_file.read_text(encoding="utf-8")
        # 해당 안건의 마지막 --- 앞에 삽입
        # 안건의 끝을 찾기: "## 안건 {다음번호}" 또는 파일 끝
        next_agenda = f"## 안건 {agenda_num + 1}"
        insert_pos = content.find(next_agenda)
        if insert_pos < 0:
            # 마지막 안건이면 파일 끝의 --- 앞에
            last_sep = content.rfind("\n---\n")
            if last_sep >= 0:
                content = content[:last_sep] + addition + content[last_sep:]
            else:
                content += addition
        else:
            content = content[:insert_pos] + addition + content[insert_pos:]

        self.meeting_file.write_text(content, encoding="utf-8")

    def close_meeting(self, summary, key_decisions=None, unresolved=None):
        """
        오늘 회의 마무리
        """
        closing = f"""

---

## 회의 마무리

**요약**: {summary}

"""
        if key_decisions:
            closing += "### 주요 결정사항\n\n"
            for i, d in enumerate(key_decisions, 1):
                closing += f"{i}. {d}\n"
            closing += "\n"

        if unresolved:
            closing += "### 미해결 사항 (다음 회의로 이월)\n\n"
            for i, u in enumerate(unresolved, 1):
                closing += f"{i}. {u}\n"
            closing += "\n"

        closing += f"""
---

*이 회의록은 meeting_recorder.py에 의해 자동 생성되었습니다.*
*수정이 필요한 경우 대표가 직접 편집할 수 있습니다.*
"""

        content = self.meeting_file.read_text(encoding="utf-8")
        content += closing
        self.meeting_file.write_text(content, encoding="utf-8")

        # 인덱스 상태 업데이트
        index = self._load_index()
        for m in index["meetings"]:
            if m["date"] == self.today:
                m["status"] = "closed"
        self._save_index(index)


def get_meeting_summary():
    """전체 회의 이력 요약"""
    meta_file = MEETINGS_DIR / "meeting_index.json"
    if not meta_file.exists():
        return "회의 기록 없음"

    index = json.loads(meta_file.read_text(encoding="utf-8"))

    lines = [
        "=== 회의 이력 ===",
        f"총 회의: {len(index['meetings'])}회",
        f"총 안건: {index['total_agendas']}건",
        f"총 결정: {index['total_decisions']}건",
        ""
    ]

    for m in index["meetings"]:
        status_icon = "OK" if m["status"] == "closed" else ".."
        lines.append(f"  [{status_icon}] #{m['number']:03d} {m['date']} - {m['agendas']}건 논의")

    return "\n".join(lines)


# CLI 사용
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        print(get_meeting_summary())
    else:
        print("Meeting Recorder v1.0")
        print("Usage:")
        print("  python meeting_recorder.py --summary    # 회의 이력 요약")
        print()
        print("In code:")
        print("  from meeting_recorder import MeetingRecorder")
        print("  recorder = MeetingRecorder()")
        print("  recorder.record_exchange(...)")
