# 음악 HTTP transport 계약과 fixture

- 상태: Phase 2 준비용 offline 구현
- last_reviewed_at: 2026-09-28
- 관련 요구사항: FR-008, FR-020, FR-022, NFR-004, NFR-005, NFR-006
- 구현: `music_http.py`, `music_jobs.py`

## 연결 범위

`MusicTransport` protocol → `StableAudioFixtureAdapter` → `MusicJobRunner`를 연결했다.
실제 HTTP client, 인증키 로딩, 유료 생성, generate 연결은 없다.
`FixtureTransport`가 합성 응답을 반환하며 live transport 주입은 거부한다.
성공 시 26 cents는 테스트용 가상 비용이며 실제 청구 근거가 아니다.

[공식 API reference](https://platform.stability.ai/docs/api-reference)의 Stable Audio 3.0 규격을
기준으로 POST `/v2beta/audio/stable-audio/text-to-audio`, 202 응답의 generation ID,
GET `/v2beta/audio/results/{id}`, 진행 중 202와 완료 200의 매핑을 준비했다.
요청은 명시적 model, prompt, duration, seed, WAV 형식을 전달한다.
seed 0은 API에서 무작위 seed를 뜻하므로 이 계약은 거부한다. dummy의 seed 0 지원은 유지한다.
공식 문서 본문은 검색 색인으로 확인했다. 실제 연결 전 endpoint와 응답 형식을 다시 대조한다.

fixture는 `tests/fixtures/music_jobs/http.json`에 있고 실제 계정 응답을 수집한 자료가 아니다.
WAV 테스트 응답도 테스트에서 메모리로 만든다. WAV 서명 검사는 transport의 기본 형식 검사이며
음질·보컬·재생 가능성 QC를 대신하지 않는다.

## timeout과 재시도

- transport마다 요청 timeout(기본 10초)과 최대 응답 크기(기본 80 MB)를 전달한다.
  fixture는 이 인자를 기록하고 adapter는 반환 body의 크기를 확인한다.
  실제 client는 네트워크 읽기 중에도 이 제한을 강제해야 한다.
- 제출은 자동 재시도하지 않는다. timeout/거부/응답 형식 오류는 runner에서
  uncertain 상태와 비용 예약을 유지하여 중복 POST를 막는다.
- 조회 timeout, 429, 5xx는 재시도한다. 나머지 HTTP 오류는 terminal 실패다.
  redirect를 따라가지 않는다. 잘못된 음성 응답은 invalid로 차단한다.
- [RFC 9110 §10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after)의
  Retry-After 초 단위와 HTTP-date를 파싱한다. 형식이 틀리면 일반 backoff를 적용한다.
  이는 일반 HTTP 처리 정책이며 해당 API가 항상 이 헤더를 보낸다고 가정하지 않는다.
- 정상 backoff보다 긴 Retry-After는 그대로 지킨다. 현재 polling 시간 한도 안에 기다릴 수
  없으면 중단하고 나중에 재개하도록 한다. 재개하더라도 저장된 not_before 이전에는 조회하지 않는다.

## 응답 evidence와 비밀정보

응답마다 무작위 파일명으로 allowlist projection을 기록한다. 임의 헤더·쿠키·URL·이메일·오류
본문은 전부 제외하고 status, 원문 body SHA-256/크기, 수신 시각, 정규화한 Retry-After만 남긴다.
제출 evidence는 로컬 요청 ID, 조회 evidence는 generation ID로 ledger와 연결한다.
모델은 요청한 식별자, 세부 model version은 unknown으로 남긴다.
응답 원문은 저장하지 않으며 `body_retained=false`를 명시한다.
이 기록은 원문 보관 또는 완성된 상업 권리/provenance bundle을 뜻하지 않는다.

신규 `music_http_evidence.schema.json`은 **1.0.0**이다.
rights는 blocked/test-only이며 임의 문자열이 evidence로 유입되지 않도록 스키마와 secret scan을
함께 적용한다. timeout 예외 메시지는 static 문자열로 바꾸고 원문 diagnostic은 기록하지 않는다.
크기 제한이나 transport 구조 검사를 통과하지 못한 응답 body는 보관하지 않는다.
오류 상태와 duration은 runner의 structured event에 남는다.

## Ledger migration

전용 `jobs.db` user_version은 **2**다. 버전 1의 기존 요청·비용·완료 결과를 보존하며
nullable `not_before` Unix timestamp 열을 추가한다. migration은 트랜잭션과 공유 디렉터리 lock
안에서 실행한다. 기존 job receipt와 Phase 1 산출물 schema version은 바꾸지 않는다.

## 검증과 다음 단계

```bash
python -m pytest tests/test_music_http.py tests/test_music_jobs.py
```

성공·조회 중단·재시작 후 cooldown·중복 제출 차단·permanent error·잘못된 응답·응답 크기·
민감정보 canary 제거·v1 ledger migration을 네트워크 없이 검증한다.

실제 연결 전에는 계정별 API 계약과 BGM 채널 사용 권리, 서비스·예산을 확정해야 한다.
그 뒤 인증·multipart 전송·스트리밍 크기 제한을 갖춘 live transport, 실제 source 저장과
44.1→48 kHz 변환 provenance, 청구 대조를 구현하고 최소 20개 샘플을 검증한다.
현재 fake receipt를 실제 음악 생성 완료나 게시 승인으로 사용하지 않는다.
