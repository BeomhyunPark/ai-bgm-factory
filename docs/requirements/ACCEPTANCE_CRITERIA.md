# Phase 1 인수 기준

- 상태: Normative
- 대상: dummy end-to-end pipeline

## Given / When / Then

### AC-001 기본 실행

- Given: Python 3.12+, FFmpeg/ffprobe가 있고 외부 API 키가 없다.
- When: `python main.py generate`를 실행한다.
- Then: exit code 0과 새 `run_id`를 반환하며 `data/runs/<run_id>/`가 생성된다.

### AC-002 산출물 완전성

다음 파일이 모두 존재하고 0 byte가 아니어야 한다.

- `final.mp4`
- `thumbnail.jpg`
- `metadata.json`
- `provenance.json`
- `manifest.json`

### AC-003 영상 기술 규격

`ffprobe` 결과가 다음을 만족한다.

- duration: `3599s <= duration <= 3601s`
- video: 16:9, H.264
- audio: AAC, stereo, 48 kHz 권장
- A/V duration 차이: 100ms 이하
- decoder error 없음

### AC-004 메타데이터

- title과 description이 비어 있지 않다.
- tracklist에 시작 시각 `00:00`이 존재한다.
- 모든 chapter timestamp가 오름차순이고 영상 길이를 넘지 않는다.
- `privacy_status`는 `private`다.
- 금지된 과장 문구와 artist imitation 문구가 없다.

### AC-005 provenance

- `schema_version`, `run_id`, `created_at`, `code`, `inputs`, `assets`, `rights`, `transforms`가 존재한다.
- 각 source/final asset에 SHA-256이 있다.
- dummy provider가 명시되고 실제 상업 권리로 오인할 문구가 없다.
- secret-like key/value가 없다.

### AC-006 manifest와 상태

- 모든 stage가 `succeeded`다.
- artifact relative path와 hash가 실제 파일과 일치한다.
- 최종 상태는 `ready_for_review`이며 `published`가 아니다.

### AC-007 실패 원자성

렌더 중 실패를 주입하면 run은 `failed`가 되고 실패 단계와 원인이 기록된다. 불완전한 `final.mp4`는 ready artifact로 등록되지 않는다.

### AC-008 재현성과 충돌 방지

- 동일 seed/config는 동일한 concept/metadata input을 만든다.
- 새 실행은 별도 `run_id`를 사용한다.
- 기존 성공 run을 덮어쓰려면 명시적 별도 정책이 필요하며 Phase 1에서는 금지한다.

### AC-009 네트워크 격리

기본 configuration에서는 DNS/network를 차단해도 성공한다. YouTube, 생성 API, Analytics 호출이 없어야 한다.

### AC-010 문서 일치

`python main.py --help`, README 예시, `.env.example`, 실제 기본값이 일치한다.

## 인수 명령 초안

```bash
python main.py doctor
pytest
python main.py generate --seed 42 --duration-minutes 60
python main.py inspect <run_id>
ffprobe -v error -show_streams -show_format data/runs/<run_id>/final.mp4
```

## Phase 1 종료 판정

AC-001~010을 clean checkout에서 연속 3회 통과해야 한다. 수동 편집으로 산출물을 고친 실행은 통과로 세지 않는다.
