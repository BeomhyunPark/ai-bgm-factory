# 제작 파이프라인

- 상태: Normative

## 전체 흐름

```text
Config -> Concept -> Music Candidates -> Audio QC -> Master Audio
       -> Rights/Provenance Gate -> Background/Thumbnail -> Render
       -> Metadata -> Package Validation -> Human Review
       -> Private Upload -> Platform Checks -> Approval -> Schedule
       -> Analytics -> Feedback Candidate
```

## Stage 계약

| Stage | 주요 입력 | 주요 출력 | 대표 실패 |
|---|---|---|---|
| `initialize` | config, seed | run, config snapshot | invalid config |
| `concept` | channel profile, history | `concept.json` | unsafe/unoriginal prompt |
| `music_generate` | track briefs | source audio, raw responses | timeout, license unknown |
| `audio_qc` | source audio | per-track QC | vocal, clipping, silence |
| `audio_master` | passed tracks | `master.wav`, timeline | duration/loudness fail |
| `provenance_gate` | all source evidence | `provenance.json` | missing rights evidence |
| `visual_generate` | visual brief | background, thumbnail | unsafe/misleading output |
| `render` | master + background | `final.mp4` | FFmpeg/space error |
| `metadata` | concept + timeline | `metadata.json` | mismatch/keyword stuffing |
| `package_validate` | all artifacts | manifest ready state | hash/schema mismatch |
| `upload_private` | approved package | YouTube video ID | auth/quota/network |
| `platform_check` | video ID | processing/claim review | claim/restriction |
| `schedule` | explicit approval | `publishAt` | invalid state/date |
| `analytics_sync` | channel/video IDs | metric rows | auth/data lag |
| `feedback` | aggregated metrics | experiment candidate | insufficient sample |

## Idempotency

- 각 stage key는 `run_id + stage_name + input_hash + implementation_version`이다.
- 성공 artifact의 hash가 일치하면 재사용할 수 있다.
- 외부 생성 요청은 provider가 지원하면 idempotency key를 보낸다.
- YouTube upload 전 `upload_attempt`와 file hash를 저장하며, timeout 후 무조건 재업로드하지 않고 기존 video를 먼저 조회한다.
- metadata update와 schedule은 현재 remote state를 읽고 desired state와 비교한다.

## Retry

Retry 가능: timeout, 429, 일부 5xx, 일시적 filesystem lock.

Retry 금지: validation failure, policy block, invalid credential, license evidence missing, quota policy violation.

기본은 exponential backoff + jitter이며 최대 시도와 비용 한도를 stage별로 둔다. 재생성은 원 asset을 삭제하지 않고 새 attempt로 남긴다.

## QC와 재생성

```text
candidate
  -> technical QC
  -> vocal detection
  -> similarity QC
  -> policy/rights gate
  -> accepted
```

한 track이 실패하면 전체 run을 즉시 버리지 않고 해당 slot만 제한 횟수 재생성한다. 한도 초과 시 run을 `blocked` 또는 `failed`로 종료한다. 기준을 자동 완화해서 통과시키지 않는다.

## 음악 조립

- 목표 track 수: 8~12
- crossfade는 실제 track chapter 시작점과 함께 계산한다.
- master 전에 track 단위 normalize를 수행하되 지나친 dynamics 손상을 피한다.
- 마지막 track은 정확한 60분을 위해 trim/fade할 수 있고 provenance에 기록한다.
- 짧은 한 곡의 단순 반복으로 60분을 채우지 않는다.

## 렌더 전략

초기에는 정지 이미지 + 매우 느린 zoom/pan + 제한된 ambient overlay를 사용한다. visual effect가 음악 감상을 방해하지 않도록 하고 photosensitive 위험이 있는 flashing을 금지한다.

임시 파일에 render한 뒤 ffprobe와 decode smoke test를 통과한 경우에만 atomic rename으로 `final.mp4`를 등록한다.

## Package gate

다음 중 하나라도 실패하면 `ready_for_review`가 될 수 없다.

- final duration/codec/A-V sync
- thumbnail dimensions/size/readability review
- metadata/timeline mismatch
- missing or unverified rights record
- duplicate/similarity threshold
- secret scan
- schema/hash mismatch
- policy decision missing

## 공개 게이트

생성 성공과 공개 적합성은 별도다. `ready_for_review`는 로컬 package가 완성됐다는 뜻일 뿐이다. `publish_approved`에는 운영자, 시각, 검사 결과, 정확한 artifact hash가 포함되어야 한다.



## Phase 1 테스트 전용 예외

AC-006의 로컬 인수를 위한 test-only package는 rights=blocked를 유지하면서
ready_for_review가 될 수 있다. review_scope=local_test_only / upload_eligible=false가 필수다.
검사하지 않은 production QC를 통과한 것으로 표시하지 않는다.
자세한 조건은 [구현 결정](DECISIONS.md)에 있으며 실제 provider에는 이 예외를 적용하지 않는다.
