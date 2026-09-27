# Phase 2 음악 API 후보 검토

- 상태: Draft — 기술 평가 우선순위이며 구매·권리 승인 아님
- last_reviewed_at: 2026-09-28 (Asia/Seoul)
- 검토 범위: 공식 API 문서, 가격, 공개 약관. 계정별 계약·청구·실제 음질은 미검증.
- 현재 결정: production provider 미선정, 모든 후보 `rights_status: blocked`.

## 결론

**Stable Audio 3.0을 첫 기술 평가 후보로 둔다.** 공개 API에 비동기 생성·seed·길이·WAV 출력이
명시되어 있고 건별 가격을 계산할 수 있기 때문이다. 실제 연결은 아래 권리·예산 항목을
확정한 뒤 진행한다. Mubert는 BGM 채널 용도와 API 계약을 확인할 대안이며,
Beatoven은 음악 중심 영상의 허용 범위를 먼저 확인해야 한다.

평가용 콘셉트 초안은 **야간 코딩용 ambient instrumental, 72~84 BPM, 부드러운 pad와 pluck**이다.
기존 dummy 콘셉트를 비교 기준으로만 사용한다. 채널 장르·이름을 확정한 것은 아니다.
타인의 이름·작품·상표를 prompt에 넣지 않는다.

## 후보 비교

| 항목 | Stability AI / Stable Audio 3.0 | Mubert API | Beatoven maestro API |
|---|---|---|---|
| 공식 자동화 경로 | HTTP 생성 + 결과 polling [S1] | 공식 v3 API [M1] | 공식 API 제공 [B1] |
| 길이·형식 | 요청 길이 1~380초, 44.1 kHz stereo, WAV/MP3 [S1] | 길이·WAV/MP3 요청 가능, 계정별 최대 길이 미확인 [M1] | API별 길이·형식 상한 미확인 |
| 가격 관측 | 성공 생성당 26 credits = $0.26 [S2] | Build 월 $49 할인 / $99 병기, 100회; Startup $199 할인 / $249 병기, 5,000회 [M2] | 확인한 공개 API 소개에 단가 없음 [B1] |
| 상업 사용 근거 | API를 포함하는 2025 약관 §4에서 제공자 보유 출력 권리를 조건부 양도 [S3] | Render FAQ는 functional music 채널 수익화에 Pro 이상 안내. API 계약에 그대로 적용하지 않음 [M3] | 약관 §6.1은 영상 등에 동기화된 이용을 허용. 음악 중심 영상 적용 미확인 [B2] |
| 해지 후 이용 | §12.e의 존속 조항과 출력 권리 관계를 계정 적용 약관으로 확인 필요 [S3] | Render는 기존 게시물 유지·수익화 가능, 해지 후 새 프로젝트 사용 불가. API 조건 별도 확인 [M3] | perpetual 표현과 계약 기간 조건이 함께 있어 해지 후 범위 확인 필요 [B2] |
| 독점·Content ID | 유사 출력 가능. Content ID 허용 근거 미확인 [S3] | 제공자 권리 보유, Content ID 등록 금지 안내 [M4] | 비독점, 유사 음악 제공 가능. Content ID 허용 근거 미확인 [B2] |
| 남은 결정 | 생성일 적용 약관·BGM 수익화·해지 후 권리·예산 | API용 BGM 채널 라이선스·해지 후 권리·최대 길이·결제 가격 | API 계약·가격·음악 중심 영상·해지 후 권리 |

가격은 세금·환율·추가 계약을 제외한 관측값이다. Mubert 할인은 갱신 가격으로 확정하지 않는다.
가격표의 아이콘이 텍스트 추출에서 사라질 수 있으므로 나열된 기능을 해당 플랜의 허용 근거로 쓰지 않는다.
모든 후보에서 Content ID 등록은 프로젝트 정책상 비활성으로 유지한다.

## 약관 검토에서 발견한 주의점

- **시행일:** Stability의 현재 약관 URL은 2026-09-30 시행본을 표시한다 [S4].
  검토일인 9월 28일에 이미 시행 중이라고 판단하지 않았다. 이전 버전 링크의
  2025-07-31 시행본 [S3]도 확인했으며, 실제 생성일의 계약과 부가 약관을 다시 확인해야 한다.
  모델 가중치용 Community License를 hosted API 계약의 대체 근거로 쓰지 않는다.
- **용도:** Mubert Render FAQ는 functional music 채널을 언급하지만 [M3],
  라이선스 안내는 독립 음악 유통을 제한한다 [M4]. API 생성곡으로 정지/느린 배경의
  60분 BGM 영상을 만들 수 있는지 적용 계약에 명시되어야 한다.
- **동기화:** Beatoven §6은 콘텐츠에 동기화된 이용과 비독점 권리를 규정하고,
  독립 음악 유통을 제한한다 [B2]. 단순 배경 그림을 붙이면 자동으로 허용된다고 추정하지 않는다.

이 문서는 공개 자료의 검토 메모다. 약관 원문 snapshot/hash, 계정 tier, 계약/영수증,
검토자 및 허용 용도가 포함된 생성 시점 evidence bundle을 대신하지 않는다.

## 60분 제작과 비용 계산

비교 당시 코드는 8트랙 고정이었다. crossfade 손실까지 포함하면 트랙당 450초보다 길어
Stable Audio 3.0의 요청 상한 380초로는 그대로 사용할 수 없다 [S1].
이후 FR-003의 8~12트랙 범위에서 capability 기반 길이 계획을 구현했다.

계산 예시(설계 가정): crossfade 5초, 10트랙이면 `(3600 + 9 × 5) / 10 = 364.5초`다.
실제 요청은 API의 길이 정밀도를 검증하고 여유 있게 생성한 뒤 master를 정확히 trim한다.
44.1 kHz 소스는 48 kHz로 변환하고 원본과 변환 해시를 모두 남긴다.

Stable Audio 3.0 공개 단가 [S2]를 적용한 산술 추정:

- 10개 성공 후보: $2.60. QC 탈락·재생성·세금 제외.
- 20개 sandbox 성공 샘플: $5.20. 실패 무료 안내가 있어도 응답 유실을 무료로 단정하지 않는다.
- 예산 **제안**: 첫 평가 총 $10, 하루 20건, 동시 요청 1건. 현재 승인 예산은 미정이다.
  구매 최소액·잔액 유효기간은 별도 확인하며, 이 문서로 결제나 API 호출을 승인하지 않는다.

## 구현 순서와 완료 조건

| 작업 | 요구사항 | 완료 조건 |
|---|---|---|
| 음악 provider 분리·길이 계획 | FR-003, FR-022 | text/image dummy 유지, 선택한 음악 capability 안에서 60분 구성; 기존 dummy 기본값 보존 |
| fake job adapter·fixture | FR-020, NFR-005 | queued/running/succeeded/failed, malformed response, 429, timeout, 재개 시나리오를 네트워크 없이 검증 |
| 요청 식별·비용 예약 | NFR-006, FR-020 | 요청 전 예산 예약과 로컬 요청 ID 저장; job ID가 있으면 polling 재개; 제출 결과 불명이면 무조건 재제출하지 않음 |
| provenance·응답 redaction | FR-008, NFR-004 | prompt/seed/model/request ID/생성 시각/raw reference/source hash/약관 근거 저장; 서명 URL·인증값 제거 |
| 실제 adapter·20개 샘플 | Phase 2 exit criteria | 서비스·예산·권리 근거 확정 후 시행; 실패·중복 청구·timeout 결과와 실제 비용 보고 |

provider가 idempotency key를 지원하는지는 별도 검증한다. 로컬 ID만으로 원격 중복 청구가
방지된다고 주장하지 않는다. 실제 음악에 dummy의 `local_test_only` 권리 예외를 적용하지 않는다.
보컬·유사도 QC는 Phase 3, 권리 gate 강화는 Phase 4이며 업로드는 계속 disabled다.

2026-09-28 업데이트: [fake job adapter와 재시도·비용 계약 테스트](../architecture/MUSIC_JOBS.md)를
기존 generate와 분리해 구현했다. 음악 provider 분리와 길이 계획도 generate에 적용했다.
[HTTP fixture/transport 계약](../architecture/MUSIC_HTTP.md)도 job runner에 연결했다.
다음은 서비스·예산·권리 근거 확정과 live transport·원본 음원 보관 구현이다.
실제 provider를 활성화하기 전에 채널 용도, 적용 API 계약과 계정 tier, 예산을 확정한다.
API 키는 채팅·문서·fixture에 기록하지 않는다.

## 공식 출처

모두 2026-09-28 확인. S1·S2는 동적 페이지 본문 추출이 비어 검색 색인에 표시된
공식 문서 내용을 참조했다. 실제 연결 전 해당 endpoint와 가격을 다시 대조한다.

- [S1: Stability API reference](https://platform.stability.ai/docs/api-reference) — Stable Audio 3.0 Text-to-Audio.
- [S2: Stability API pricing](https://platform.stability.ai/pricing) — 1 credit = $0.01, 3.0 = 26 credits.
- [S3: Stability 2025 Terms](https://stability.ai/2025-terms-of-service) — 시행일 2025-07-31, §4, §12.
- [S4: Stability Terms](https://stability.ai/terms-of-service) — 표시 시행일 2026-09-30.
- [M1: Mubert API docs](https://mubert.com/api/docs) — v3 tracks 생성.
- [M2: Mubert API plans](https://mubert.com/api/plans) — API 전용 가격.
- [M3: Mubert Render FAQ](https://mubert.com/render/faq) — functional music, 해지 후 이용.
- [M4: Mubert license](https://mubert.com/render/license) — 권리 보유·유통·Content ID 제한 안내.
- [B1: Beatoven API](https://www.beatoven.ai/api) — maestro API 소개, 가격·계약 확정 자료 아님.
- [B2: Beatoven Terms](https://www.beatoven.ai/tos) — 표시 개정일 2024-06-05, §6.
