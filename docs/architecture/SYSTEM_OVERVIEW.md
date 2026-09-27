# 시스템 아키텍처 개요

- 상태: Draft → Phase 1에서 확정

## 논리 구조

```text
CLI / Scheduler
      |
      v
Pipeline Orchestrator ---- Run Store (SQLite + filesystem)
      |
      +--> Concept Service ------ Text Provider
      +--> Music Service -------- Music Provider
      +--> Audio QC ------------ ffmpeg/librosa/classifier
      +--> Provenance Service --- hashes/terms/license snapshots
      +--> Visual Service ------- Image Provider
      +--> Render Service ------- FFmpeg
      +--> Metadata Service ----- Text Provider + validators
      +--> Publish Service ------ YouTube Data API
      +--> Analytics Service ---- YouTube Analytics API
      +--> Feedback Service ----- aggregated experiment inputs
```

## 권장 코드 구조

```text
src/ai_bgm_factory/
├── cli.py
├── config.py
├── domain/
│   ├── models.py
│   ├── states.py
│   └── policies.py
├── pipeline/
│   ├── orchestrator.py
│   └── stages/
├── providers/
│   ├── text/
│   ├── music/
│   ├── image/
│   └── youtube/
├── media/
│   ├── audio_qc.py
│   ├── mixer.py
│   └── renderer.py
├── provenance/
├── metadata/
├── analytics/
├── storage/
└── observability/
```

## 경계

### Domain

provider SDK나 filesystem 세부사항을 모른다. `Concept`, `Track`, `RightsEvidence`, `QcReport`, `PublicationDecision` 같은 안정된 모델과 정책을 가진다.

### Application/Pipeline

stage 순서, 상태 전이, retry, compensation을 담당한다. 어떤 음악 모델을 쓰는지는 adapter 설정으로 결정한다.

### Infrastructure

FFmpeg, SQLite, YouTube API, 생성 provider SDK, local filesystem을 구현한다. provider 원본 응답은 정규화 데이터와 분리 보관한다.

## 저장 모델

- SQLite: run/stage 상태, 비용, 외부 ID, 승인, analytics index
- Filesystem: audio/image/video, JSON report, provider raw response
- 장기 backup: 운영 단계에서 encrypted object storage를 선택 가능

Phase 1 실행 checkpoint의 기준은 원자적으로 저장한 manifest이며 SQLite는 조회 인덱스다.
파일 hash는 DB와 manifest 양쪽에 저장한다. 재개 시 파일을 검증한 후 DB를 재동기화한다.
실제 외부 action의 상태 저장 모델은 해당 Phase에서 별도로 확정한다.

## 실행 상태 머신

```text
created
  -> generating
  -> qc_pending
  -> rendering
  -> ready_for_review
  -> upload_pending
  -> uploaded_private
  -> publish_approved
  -> scheduled
  -> published
  -> analytics_active
```

어느 단계에서든 `failed`, 정책 위반 시 `blocked`, 운영자 중단 시 `cancelled`로 갈 수 있다. `uploaded_private`에서 자동으로 `published`로 건너뛸 수 없다.

## Trust boundary

- Untrusted: model output, provider response text, uploaded metadata, Analytics comments, external URLs
- Sensitive: API keys, OAuth refresh token, client secret, channel identifiers
- Durable evidence: terms URL/snapshot hash, invoice/subscription reference, request ID, generated asset hash, approval
- Public candidates: title, description, tags, thumbnail, rendered video

모델 출력은 shell command, path, URL, privacy setting을 직접 결정하지 못한다. allowlist와 schema validation을 거친다.

## 배포 형태

Phase 1~7은 단일 host의 CLI + SQLite로 시작한다. Phase 8부터 scheduler process를 추가한다. queue/worker/object storage는 실제 처리량과 장애 데이터가 필요하다고 증명될 때만 도입한다.
