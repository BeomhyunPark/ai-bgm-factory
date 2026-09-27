# 개발 로드맵: Phase 0~9

- 상태: Normative
- 진행 규칙: 앞 Phase의 exit criteria를 통과하기 전 다음 Phase의 production feature를 켜지 않는다.

## 현재 구현 상태

2026-09-27: Phase 0 기반과 Phase 1 오프라인 구현 완료. 동일 소스의 깨끗한 export 3개에서
45개 테스트(60분 smoke 포함)가 네트워크 차단 상태로 연속 통과했다.
상세 기록은 전달 묶음의 verification/REPORT.md를 확인한다. Phase 2 실제 provider는 미선정이다.

2026-09-28: macOS에서 FFmpeg 9 호환성 수정 후 60분 smoke 포함 전체 테스트
49개를 1회 통과했다. 영상 3600초, A/V 차이 0초, -14 LUFS이며 전체 디코딩과
inspect/resume를 확인했다. 이는 맥북 실행 검증이며 clean checkout 3회 및
커널 네트워크 차단 인수 검증을 대체하지 않는다.
상세 결과: [macOS 보고서](../../verification/MACOS_REPORT.md).

2026-09-28: [Phase 2 음악 API 후보 비교](MUSIC_PROVIDER_COMPARISON.md) 완료.
Stable Audio 3.0을 첫 기술 평가 후보로 기록했다. 실제 provider 승인·연결과 유료 호출은 미실시다.

2026-09-28: [오프라인 음악 job 계약](../architecture/MUSIC_JOBS.md) 구현.
fake adapter, 영속화된 조회 재개, 비용 예약·일일 한도와 오류 fixture를 추가했다.
기존 generate와 분리되어 있으며 실제 음악 API 및 Phase 2 exit criteria는 미완료다.

2026-09-28: 음악 provider 주입을 text/image와 분리하고 capability 기반 8~12트랙 계획을
generate에 적용했다. 기본 8트랙, crossfade 2초는 유지한다. 실제 provider 연결은 아직 비활성이다.
macOS에서 60분 smoke 포함 **101개 테스트 통과(212.07초)**.
[검증 결과](../../verification/TRACK_PLANNING_REPORT.json)에 구현 hash와 음성·영상 측정값을 기록했다.

## 전체 요약

| Phase | 목표 | 외부 side effect |
|---:|---|---|
| 0 | 기반·계약·정책 확정 | 없음 |
| 1 | dummy end-to-end pipeline | 없음 |
| 2 | 실제 음악 API adapter | 음악 생성만 |
| 3 | audio QC와 mastering | 없음 |
| 4 | provenance와 rights gate | 없음 |
| 5 | visual/thumbnail 생성과 render 강화 | 이미지 생성만 |
| 6 | metadata와 차별성 검증 | text 생성만 |
| 7 | YouTube private upload | private upload |
| 8 | scheduler와 승인 기반 예약 | 승인된 예약 공개 |
| 9 | Analytics feedback loop | read-only analytics |

## Phase 0 — Foundation & Contracts

### 목표

문서, project skeleton, config, domain model, JSON schema, CLI surface를 확정한다.

### Deliverables

- README/CONTRIBUTING/AGENTS와 `docs/`
- `pyproject.toml`, package structure, test setup
- `.env.example`, config validation
- manifest/metadata/provenance/QC JSON Schema
- `doctor`와 빈 CLI command
- SQLite migration framework

### Exit criteria

- 문서 링크와 schema example이 일치
- default config는 network side effect 없음
- secret scan과 lint/test command 정의
- architecture decision과 open question 목록 검토

## Phase 1 — Dummy End-to-End Pipeline

### 목표

`python main.py generate` 한 번으로 외부 API 없이 60분 완성 package를 만든다.

### Deliverables

- deterministic dummy concept/text/music/image providers
- algorithmic instrumental test audio 8~12개
- 기본 normalize/crossfade
- static/slow-motion visual render
- thumbnail과 metadata
- test-only provenance와 manifest
- resume/error injection/E2E tests

### Exit criteria

[Phase 1 인수 기준](../requirements/ACCEPTANCE_CRITERIA.md) AC-001~010을 clean checkout에서 3회 연속 통과한다.

## Phase 2 — Music API

### 목표

승인된 provider adapter로 실제 instrumental candidate를 생성한다.

### Deliverables

- provider capability/contract tests
- async polling, timeout, retry, idempotency
- per-run cost and quota guard
- prompt policy: no vocals/no artist imitation
- raw response redaction/storage
- provider sandbox fixtures

### Exit criteria

- 20개 이상 sandbox sample 생성
- automation/commercial use terms 검토 완료
- model/request IDs와 source hashes 기록
- 오류/중복 청구/timeout 시나리오 검증
- YouTube upload는 여전히 disabled

## Phase 3 — Audio QC & Mastering

### 목표

사람이 전체를 듣지 않아도 명백한 기술·보컬·중복 문제를 자동 차단한다.

### Deliverables

- duration, silence, clipping, LUFS, true peak
- vocal probability와 calibration dataset
- spectral anomaly와 duplicate similarity
- regenerate budget와 quarantine
- loudness normalization, crossfade, exact-duration master
- QC report versioning

### Exit criteria

- labeled evaluation set의 false negative/positive를 보고
- vocal 포함·clipped·silent fixture 모두 차단
- final master `-14 LUFS ±1`, `<= -1 dBTP`
- threshold 완화 없이 retry exhaustion 처리

## Phase 4 — Provenance & Rights Gate

### 목표

모든 source에서 final까지 설명 가능한 evidence chain을 만들고 권리 불명 asset을 차단한다.

### Deliverables

- provenance service와 schema migration
- terms/license evidence registry
- file/content/config/prompt hash
- code commit/tool version/transform 기록
- rights state machine과 expiry/review alerts
- claim evidence export command

### Exit criteria

- final artifact에서 모든 source로 역추적 가능
- evidence 누락 시 package/upload 차단
- secret redaction test 통과
- provider 약관 변경 시 adapter pause 가능

## Phase 5 — Visual, Thumbnail & Render

### 목표

콘셉트별 고유한 background와 thumbnail을 만들고 안정적으로 60분 영상에 결합한다.

### Deliverables

- image provider adapter와 safety checks
- brand/style constraints without artist imitation
- background motion preset
- thumbnail composition/readability checks
- perceptual similarity/novelty gate
- render resume, temp file, ffprobe/decode validation
- C2PA preservation/inspection where available

### Exit criteria

- 10개 concept의 visual differentiation review
- 60분 render 5회 연속 성공
- A/V sync와 codec 기준 통과
- misleading/duplicate thumbnail negative test

## Phase 6 — Metadata & Originality

### 목표

실제 영상과 일치하고 채널 고유성을 설명하는 metadata package를 만든다.

### Deliverables

- title/description/tag/chapter generator
- exact timeline-derived chapters
- disclosure/attribution insertion
- keyword stuffing/claims/artist-name filter
- 최근 영상과 semantic similarity gate
- creative distinctiveness record

### Exit criteria

- 20개 fixture에서 chapter mismatch 0
- 금지 claim/artist imitation test 차단
- 10개 pilot package의 사람 검토 통과
- 한 문장 고유성 설명이 없는 candidate 차단

## Phase 7 — YouTube Private Upload

### 목표

승인된 package를 idempotent하게 private upload하고 remote 상태를 추적한다.

### Deliverables

- OAuth 최소 scope와 secure token store
- resumable `videos.insert`
- hard-coded policy guard for private
- thumbnail set, metadata update
- processing/check polling과 reconciliation
- quota/cost/error handling

### Exit criteria

- test channel에서 private upload 10회
- timeout/retry에도 duplicate upload 0
- `public`/`unlisted` direct upload negative test
- claims/disclosure/audience 확인 runbook 검증

## Phase 8 — Scheduler & Publication Approval

### 목표

private staging과 사람 승인을 거친 영상만 안전하게 예약 공개한다.

### Deliverables

- scheduler lock, timezone, missed-run behavior
- immutable approval record with hashes
- `publishAt` validator and minimum lead time
- daily/weekly cap, kill switch
- remote/local reconciliation
- incident pause/rollback controls

### Exit criteria

- 승인 없거나 hash 변경된 영상 schedule 차단
- 과거 시각/잘못된 timezone 차단
- double scheduler에서도 중복 action 없음
- 4주간 제한된 pilot 운영 후 리뷰

## Phase 9 — Analytics Feedback Loop

### 목표

YouTube Analytics를 읽어 검증 가능한 다음 실험 후보를 만든다.

### Deliverables

- read-only Analytics adapter
- daily/video metric warehouse
- data lag/missing handling
- creative feature join
- experiment registry와 24h/7d/28d/90d views
- feedback proposal generator
- policy/claim/cost guardrails

### Exit criteria

- 공식 API fixture와 실제 test channel sync 검증
- 누락 데이터를 0으로 오인하지 않음
- feedback이 자동 publish/generation scale을 트리거하지 않음
- 최소 한 개의 28일 experiment를 사람 검토로 종료

## 향후 후보(Phase 10 이후)

- object storage/worker queue
- channel brand kit와 richer motion
- multi-language metadata
- automated terms-change monitoring
- human review UI

필요가 실제 지표로 확인되기 전 구현하지 않는다.
