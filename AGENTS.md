# AGENTS.md

이 저장소에서 작업하는 AI coding agent와 사람 기여자가 따라야 할 규칙이다.

## 목표

현재 최우선 목표는 `python main.py generate`가 외부 API 없이도 deterministic dummy pipeline을 실행하여 60분 `final.mp4`, `thumbnail.jpg`, `metadata.json`, `provenance.json`, `manifest.json`을 생성하게 만드는 것이다.

## 작업 순서

1. [docs/roadmap/PHASES.md](docs/roadmap/PHASES.md)의 현재 Phase와 exit criteria를 확인한다.
2. 관련 요구사항 ID를 확인하고 작은 단위로 구현한다.
3. fake adapter와 fixture를 먼저 만들고 실제 provider adapter를 추가한다.
4. 테스트와 `doctor`를 실행한다.
5. 문서, `.env.example`, schema version을 코드와 함께 갱신한다.

## 필수 제약

- Python 3.12+와 FFmpeg/ffprobe를 기준으로 한다.
- 외부 provider는 protocol/interface 기반 adapter로 구현한다.
- 동일 `run_id`에 대한 재실행은 idempotent해야 하며 기존 완료 산출물을 조용히 덮어쓰지 않는다.
- 모든 생성 단계는 structured event와 duration을 기록한다.
- prompt, seed, model/version, request ID, 원본 응답 위치, 약관 URL, 생성 시각, file hash를 provenance에 남긴다.
- provider license를 추정하지 않는다. 근거가 없으면 `rights_status: blocked`다.
- 공개 업로드를 구현하거나 실행하지 않는다. 업로드 기본값은 `private`다.
- `unlisted`나 `public` 변경에는 사람이 확인 가능한 approval record가 필요하다.
- Content ID 이의제기를 자동 제출하지 않는다.
- 타인의 이름·상표·작품명을 스타일 프롬프트에 넣지 않는다.
- secret을 코드, fixture, prompt, 로그, exception, test snapshot에 넣지 않는다.
- 데이터 삭제는 retention policy와 명시적 dry-run을 제공한 뒤 구현한다.

## 품질 게이트

- 음악: instrumental, 목표 duration, no unexpected silence, no clipping, loudness/true peak 기준, duplicate similarity 기준.
- 영상: 60분 허용 오차, 16:9, H.264/AAC baseline target, A/V duration 일치, 재생 가능.
- 썸네일: 16:9, 파일 크기 제한, 작은 화면 가독성, 오해를 유도하지 않는 내용.
- 메타데이터: 과장·키워드 stuffing 금지, 실제 트랙리스트와 일치.
- provenance: 필수 필드와 SHA-256 hash 존재, 비밀값 없음.
- 정책: 차별성 점수 및 human publish gate 기록.

## 구현하지 말아야 할 것

- CAPTCHA 우회, 계정 farming, 인위적 engagement
- 권리 없는 Content ID 등록
- 다른 아티스트와 혼동시키는 제목·썸네일·프롬프트
- validation 우회용 하드코딩
- 테스트 통과를 위해 오류를 숨기는 fallback
- 공개 전환을 cron의 단순 후속 단계로 연결하는 구현

## 문서 불일치

구현과 문서가 충돌하면 안전성이 더 높은 쪽을 적용하고, 같은 변경에서 불일치를 수정한다. 법률·플랫폼 정책은 변경될 수 있으므로 공식 원문을 재확인하고 `last_reviewed_at`을 갱신한다.
