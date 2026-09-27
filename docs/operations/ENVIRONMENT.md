# `.env.example` 설명

- 상태: Operational

실제 값은 `.env` 또는 secret manager에 넣고 Git에 커밋하지 않는다. Boolean은 `true`/`false`, 시간은 timezone이 포함된 ISO 8601을 사용한다.

## Runtime

| 변수 | 의미 | 안전한 기본값 |
|---|---|---|
| `APP_ENV` | `development`, `test`, `production` | `development` |
| `LOG_LEVEL` | 로그 수준 | `INFO` |
| `DATA_DIR` | DB와 run output root | `./data` |
| `TIMEZONE` | 표시/스케줄 timezone | `Asia/Seoul` |
| `DEFAULT_DURATION_MINUTES` | 목표 영상 길이 | `60` |
| `MIN_TRACK_COUNT` | 최소 소스 수, 8~12 정수; provider 상한에 따라 증가 | `8` |
| `CROSSFADE_SECONDS` | 인접 소스 겹침 길이, 양수이며 48 kHz 샘플 단위 | `2` |
| `DEFAULT_PRIVACY_STATUS` | YouTube upload privacy | 반드시 `private` |
| `MAX_DAILY_GENERATIONS` | 비용/대량생산 guard | `1` |
| `MAX_DAILY_UPLOADS` | 업로드 guard | `1` |

production에서도 `DEFAULT_PRIVACY_STATUS=private`를 유지한다. 다른 값은 config validation에서 거부하는 것을 권장한다.

## Feature flags

`ENABLE_MUSIC_API`, `ENABLE_IMAGE_API`, `ENABLE_YOUTUBE_UPLOAD`, `ENABLE_SCHEDULER`, `ENABLE_ANALYTICS_SYNC`는 외부 side effect를 단계적으로 켠다. 기본은 전부 `false`다. `ENABLE_YOUTUBE_UPLOAD=true`여도 CLI의 upload 명령 없이는 업로드하지 않는다.

## Text provider

- `TEXT_PROVIDER`: `dummy` 또는 승인된 adapter 이름
- `OPENAI_API_KEY`: OpenAI adapter 사용 시 secret
- `OPENAI_TEXT_MODEL`: allowlist에 등록한 model ID

model 이름을 비워 두면 adapter가 임의 최신 모델을 선택하지 않고 validation error를 내도록 한다.

## Music provider

- `MUSIC_PROVIDER`: 기본 `dummy`
- `MUSIC_API_KEY`: secret
- `MUSIC_MODEL`: 정확한 model ID
- `MUSIC_LICENSE_TIER`: 생성 당시 요금제/권리 tier
- `MUSIC_TERMS_URL`: 검토한 약관 URL

환경 변수 값만으로 권리가 검증되는 것은 아니다. evidence bundle과 reviewer record가 있어야 `rights.status`를 통과시킨다.

## Image provider

음악과 동일하게 provider/model/license tier/terms URL을 명시한다. 음악과 이미지 key가 같더라도 변수와 adapter를 분리한다.

## YouTube

| 변수 | 의미 |
|---|---|
| `YOUTUBE_CLIENT_SECRETS_FILE` | OAuth client configuration path |
| `YOUTUBE_TOKEN_FILE` | OAuth token path |
| `YOUTUBE_CHANNEL_ID` | 대상 channel allowlist |
| `YOUTUBE_CATEGORY_ID` | 기본 category; 음악은 보통 `10`, 실제 channel 정책 확인 |
| `YOUTUBE_DEFAULT_LANGUAGE` | metadata 기본 언어 |
| `YOUTUBE_CONTAINS_SYNTHETIC_MEDIA` | AI disclosure decision의 안전한 기본값 |

token과 client secret은 `./secrets/` 같은 ignored directory에 두고 파일 permission을 제한한다.

## QC

- `TARGET_LUFS`: master integrated loudness target
- `LOUDNESS_TOLERANCE_LU`: 허용 오차
- `MAX_TRUE_PEAK_DBTP`: true peak 상한
- `MAX_SILENCE_SECONDS`: 의도되지 않은 연속 silence 상한
- `MAX_VOCAL_PROBABILITY`: 보컬 분류기 상한
- `MAX_AUDIO_SIMILARITY`: 기존 asset과 similarity 상한
- `MIN_VISUAL_NOVELTY_SCORE`: 내부 visual novelty 하한

threshold 변경은 versioning하고 기존 run에 소급 적용하지 않는다. calibration dataset 없이 기준을 완화하지 않는다.

## Operations

- `DATABASE_URL`: 초기에는 SQLite
- `SCHEDULE_CRON`: scheduler wake-up 주기; 이것이 곧 공개 주기는 아니다.
- `ANALYTICS_LOOKBACK_DAYS`: 재수집 기간
- `PROVENANCE_RETENTION_DAYS`: provenance 보존 기간
- `RAW_PROVIDER_RESPONSE_RETENTION_DAYS`: redacted raw response 보존 기간
- `HUMAN_APPROVAL_REQUIRED`: production에서 항상 `true`

## Production validation

다음 조합은 시작 단계에서 거부한다.

- `DEFAULT_PRIVACY_STATUS != private`
- `HUMAN_APPROVAL_REQUIRED=false`
- upload enabled + channel allowlist 없음
- external provider enabled + key/model/rights evidence 없음
- scheduler enabled + upload disabled 또는 approval store 없음



## Phase 1 지원 범위

현재 읽는 변수는 루트 `.env.example`에 있는 Runtime/Provider/Feature flag다.
APP_ENV, DATA_DIR, TIMEZONE, DEFAULT_DURATION_MINUTES, DEFAULT_PRIVACY_STATUS,
MIN_TRACK_COUNT, CROSSFADE_SECONDS,
HUMAN_APPROVAL_REQUIRED, TEXT_PROVIDER/MUSIC_PROVIDER/IMAGE_PROVIDER와 5개 ENABLE_*을 검증한다.
비밀값은 필요하지 않으며 config snapshot에 넣지 않는다. 모든 provider는 dummy만 허용한다.
이 문서의 나머지 모델/예산/YouTube/QC/Operations 변수는 후속 Phase 설계이며 현재 동작을 바꾸지 않는다.
QC는 버전이 고정된 코드 기준으로 적용하고 임계값을 환경 변수로 완화하지 않는다.

`generate --min-tracks`는 MIN_TRACK_COUNT보다 우선한다. 재개 시 저장된 최소 트랙 수와
crossfade를 복구하며, 명시한 --min-tracks가 저장값과 다르면 거부한다.
생성 전 길이 계획에서 source 상한과 겹침 조건을 검증한다.
