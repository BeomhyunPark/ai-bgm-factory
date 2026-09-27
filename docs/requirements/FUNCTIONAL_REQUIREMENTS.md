# 기능 및 비기능 요구사항

- 상태: Normative

## 기능 요구사항

| ID | 요구사항 | 검증 요약 |
|---|---|---|
| FR-001 | `generate`는 고유 `run_id`를 생성하고 설정 snapshot을 저장한다. | manifest fixture |
| FR-002 | 콘셉트 단계는 audience, use case, mood, BPM range, genre, visual brief, novelty anchors를 생성한다. | JSON schema |
| FR-003 | 음악 단계는 목표 길이를 만족하도록 8~12개의 instrumental track 후보를 생성한다. | track manifest |
| FR-004 | 금지 prompt(artist imitation, vocals, trademark confusion)를 generation 전에 차단한다. | policy unit test |
| FR-005 | 각 track은 duration, silence, clipping/true peak, loudness, vocal probability, spectral anomaly, similarity 검사를 받는다. | QC report |
| FR-006 | 실패한 track은 제한된 횟수로 재생성하며 원인과 횟수를 기록한다. | retry test |
| FR-007 | 통과 track을 normalize하고 crossfade하여 정확한 목표 길이의 master audio를 만든다. | ffprobe + loudness report |
| FR-008 | provenance는 입력, provider, model/version, seed, request ID, terms URL, license tier, timestamps, hashes, transforms를 기록한다. | schema + hash check |
| FR-009 | 시각 단계는 배경과 별도 thumbnail을 생성하고 실제 콘셉트와 일치하는지 검증한다. | artifact + review record |
| FR-010 | renderer는 16:9 H.264 video와 AAC audio를 가진 60분 MP4를 만든다. | ffprobe |
| FR-011 | metadata는 title, description, tags, chapters, disclosure note, content settings를 생성한다. | schema + chapter check |
| FR-012 | tracklist timestamp가 실제 audio timeline과 일치해야 한다. | timeline test |
| FR-013 | `generate`는 외부 upload 없이 완성 package를 `ready_for_review`로 만든다. | E2E test |
| FR-014 | uploader는 기본 `privacyStatus=private`를 강제하고 idempotency key를 사용한다. | fake API contract |
| FR-015 | 업로드 후 video ID, upload response, processing/check 상태를 저장한다. | persistence test |
| FR-016 | scheduler는 승인된 private video에만 미래 `publishAt`을 설정한다. | state-machine test |
| FR-017 | `public` 또는 `unlisted` 전환 전에 human approval, rights, QC, disclosure, claim gate를 재검증한다. | negative tests |
| FR-018 | Analytics sync는 channel-owned video만 대상으로 날짜·video별 metrics를 저장한다. | API fixture |
| FR-019 | feedback builder는 집계·최소 표본·실험 제약을 적용하여 다음 creative brief 후보만 만든다. | deterministic test |
| FR-020 | 실패 run은 resume 가능하며 완료 단계의 검증된 artifact를 재사용한다. | interruption test |
| FR-021 | `doctor`는 Python, FFmpeg, directory, config, credential presence를 side effect 없이 검사한다. | CLI test |
| FR-022 | 모든 외부 side effect는 feature flag와 명시적 command로만 활성화된다. | configuration test |

## 비기능 요구사항

| ID | 범주 | 요구사항 |
|---|---|---|
| NFR-001 | 안전 | default config로 network upload/publish가 발생하지 않는다. |
| NFR-002 | 재현성 | config, prompt template version, seed, code commit, provider metadata가 기록된다. |
| NFR-003 | 감사성 | 각 최종 파일에서 사용된 모든 source asset으로 역추적할 수 있다. |
| NFR-004 | 보안 | secret은 source, log, provenance, exception에 포함되지 않는다. |
| NFR-005 | 복원력 | transient provider error에 exponential backoff+jitter를 적용하고 영구 오류는 즉시 중단한다. |
| NFR-006 | 비용 | run별 예상/실제 비용과 token/seconds/requests를 기록하고 budget 초과 전에 중단한다. |
| NFR-007 | 성능 | reference machine 기준 렌더 시간과 peak disk/memory를 계측한다. 초기 hard SLA는 두지 않는다. |
| NFR-008 | 이식성 | macOS/Linux에서 동일 CLI 계약을 유지한다. |
| NFR-009 | 관측성 | structured JSON log에 `run_id`, `stage`, `attempt`, `duration_ms`, `status`를 포함한다. |
| NFR-010 | 개인정보 | 필요한 최소 OAuth scope만 사용하고 개인 데이터 수집을 최소화한다. |
| NFR-011 | 호환성 | persisted JSON에는 `schema_version`을 포함하고 migration을 제공한다. |
| NFR-012 | 접근성 | thumbnail text는 작은 화면에서도 읽을 수 있고 색 대비를 수동 검토한다. |

## 초기 QC 기준

초기값이며 Phase 3 calibration 후 확정한다.

| 검사 | 초기 기준 | 실패 처리 |
|---|---|---|
| Track duration | provider target의 ±5% | regenerate |
| Vocal probability | `<= 0.15` | reject/regenerate |
| Integrated loudness | `-14 LUFS ± 1 LU` after master | re-normalize |
| True peak | `<= -1.0 dBTP` | re-limit or reject |
| Unexpected silence | 연속 `> 3s` 없음(의도 구간 제외) | inspect/reject |
| Audio similarity | 기존/동일 run과 `< 0.92` | reject |
| Final duration | `3600s ± 1s` | render fail |
| A/V delta | `<= 100ms` | render fail |
| Visual novelty | 내부 score `>= 0.60` | review/recreate |

점수는 법적 독창성이나 YouTube 수익화 승인을 증명하지 않는다. 내부 위험 신호일 뿐이다.
