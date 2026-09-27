# 오프라인 음악 job 계약

- 상태: Phase 2 준비용 구현, production 연결 없음
- 관련 요구사항: FR-020, FR-022, NFR-004, NFR-005, NFR-006, NFR-009, NFR-011
- 구현: `src/ai_bgm_factory/music_jobs.py`

## 범위

`MusicJobProvider` protocol과 `FakeMusicJobProvider`, `MusicJobRunner`를 제공한다.
기존 `generate`와 분리된 job 수명주기 실험이며 음악 파일을 만들지 않는다.
외부 API, credential, 결제, 업로드를 사용하지 않는다. fake의 cents는 테스트용 숫자다.
실제 adapter의 가격·권리 승인을 나타내지 않는다.

## 상태와 재개

| 상태 | 재실행 동작 |
|---|---|
| reserved | 제출 전 비용 예약 완료. 제출을 시작할 수 있음 |
| submitting | 제출 직전 영속화. 중단 후 원격 결과 불명이므로 자동 재제출 금지 |
| queued / running | 저장된 job ID를 조회하며 재개 |
| succeeded | 기존 schema 검증된 receipt 반환, provider 호출 없음 |
| uncertain | 제출 예외 또는 잘못된 job ID. 수동 대조 필요 |
| failed | provider의 명시적 실패. 같은 요청 재제출 금지 |
| invalid | 잘못된 조회 응답 또는 예약액 초과. 수동 대조 필요 |

같은 run ID와 slot은 하나의 요청을 가리킨다. provider 이름, 입력, 예약액이 달라지면 실패한다.
submit은 한 번만 호출하고 모든 제출 예외를 결과 불명으로 처리한다.
조회에서 명시적인 `RetryablePollError`만 재시도한다. fake의 429/timeout/503 fixture가 이에 해당한다.
지수 backoff와 jitter, 호출 횟수 및 polling 경과 시간 한도를 적용한다.
한도 소진은 job ID와 예약액을 유지하므로 다음 실행에서 조회를 이어갈 수 있다.

실험 runner의 시간 제한은 **조회 사이의 대기와 다음 조회 시작**을 제한한다.
진행 중인 Python 호출을 강제로 중단하지 않는다. 실제 HTTP adapter에는 별도의 요청 timeout과
서버 Retry-After 처리, 원격 idempotency capability 검증이 필요하다.

## 비용과 동시 실행

- 모든 runner는 동일한 ledger 디렉터리를 공유해야 한다. run마다 별도 ledger를 만들면
  run 간 일일 한도가 합산되지 않는다.
- SQLite commit 후에만 submit한다. 금액은 정수 USD cents로 전달한다.
- run별 예산, Asia/Seoul 날짜별 예산·요청 수를 예약 시 검사한다.
- 성공 후에도 보수적으로 `max(예약액, 확인된 실제액)`을 한도에서 차감한다.
  실패·불명 상태는 예약액을 돌려주지 않는다. 실제액이 예약액보다 크면 기록하고 차단한다.
- 디렉터리 flock으로 runner 호출을 직렬화한다. pending/불명/invalid job이 있으면
  다른 요청의 예약도 차단하여 하나의 미해결 job만 허용한다.
- 수동 대조/환불 반영 command는 아직 없다. 원격 idempotency나 청구 방지를 보장하는 구현이 아니다.

## 저장 계약

전용 `jobs.db`의 `PRAGMA user_version=1`을 사용하며 Phase 1의 `app.db`와 분리한다.
알 수 없는 ledger 버전은 변경하지 않고 거부한다. jobs는 입력 원문 대신 identity hash,
run ID, 요청 ID, job ID, 예약일, 금액과 상태를 보관한다.
`events`에는 run/request ID, stage(reserve/submit/poll), stage별 event 순번인 attempt,
timestamp, status, duration_ms가 남는다. 강제 종료 시 마지막 완료 event가 없을 수 있으며,
영속화된 submitting 상태가 재제출을 막는다.

성공 receipt의 새 JSON Schema는 `music_job.schema.json` version **1.0.0**이다.
`rights_status=blocked`, `intended_for_testing_only=true`, `upload_eligible=false`를 강제한다.
기존 manifest/metadata/provenance/QC schema와 `.env` 기본값은 유지한다.
receipt는 음원 산출물이나 provenance evidence bundle이 아니다.
provider 예외의 원문은 출력·이벤트에 기록하지 않는다.

## 검증

```bash
python -m pytest tests/test_music_jobs.py
python -m pytest
python main.py doctor
python -m ruff check .
python scripts/scan_secrets.py
```

fixture는 `tests/fixtures/music_jobs/lifecycle.json`에 있다. 테스트는 socket/DNS 차단 아래
성공·영구 실패·잘못된 응답·일시 오류·timeout·제출 중단·재개·예산·일일 한도·동시 실행을 검증한다.
가상 clock으로 backoff와 날짜 경계를 확인하여 실제 대기나 유료 호출이 없다.

## 다음 구현

음악 provider 분리와 capability에 맞는 8~12트랙 길이 계획을 준비한다.
실제 HTTP adapter 연결 전 서비스·예산·권리 승인, 원본 응답 redaction과 evidence 저장,
계정별 청구 대조, request timeout과 Retry-After를 완성해야 한다.
