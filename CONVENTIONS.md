# Code Conventions (AI 에이전트 헌법)

> AI 에이전트가 코드를 생성/수정할 때 따르는 규칙.
> `validate_project.py`가 자동 검증한다.

## 🔴 필수 (위반 시 에러)

- 모듈 폴더에 **MANIFEST.yaml** 필수. 파일 추가/삭제 시 동기화
- System 추가 시 **interaction-map.yaml** 동기화 필수
- Component = struct, **멤버 함수 금지** (생성자/소멸자 제외)
- System = ISystem 상속, **상태(멤버 변수) 금지** (ECS 바깥 인프라 참조 제외)
- System 간 직접 호출 금지, 싱글턴 금지

## 🟡 권장 (위반 시 경고)

- 파일이 500줄 넘으면 분리 검토 (자연스러우면 OK)
- 주석은 "왜"만 기록
- 매직 넘버 대신 constexpr 상수

## 검증 실행

```bash
python _lostark_edu/tools/validate_project.py
```
