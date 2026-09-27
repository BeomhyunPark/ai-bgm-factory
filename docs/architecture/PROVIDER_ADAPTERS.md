# Provider adapter 설계

- 상태: Normative

## 목적

음악·이미지·텍스트 provider의 SDK, 요금, 모델명, 정책 변경을 core pipeline과 분리한다. 서비스 선택은 기능뿐 아니라 자동화 허용 여부와 상업 이용 근거를 함께 평가한다.

## 공통 interface

```python
class GenerationProvider(Protocol):
    def capabilities(self) -> dict: ...
    def validate_request(self, request: GenerationRequest) -> None: ...
    def generate(self, request: GenerationRequest, output: Path) -> dict: ...
    def get_rights_evidence(self) -> dict: ...
```

생성 응답 dict의 목표 계약은 최소한 다음을 포함한다.

- normalized asset location
- provider/model/model version
- request ID
- created timestamp
- seed(지원 시)
- usage/cost
- raw response reference
- provider moderation result

## 현재 pipeline 주입과 길이 계획

`Pipeline(config, provider=..., music_provider=...)`에서 `provider`는 text/image,
`music_provider`는 audio만 담당한다. 둘의 기본값은 각각 별도 DummyProvider다.
기존 단일 provider 주입을 사용하던 코드는 음악용 인자를 명시해야 한다.
현재는 network_required=false, blocked/test-only rights만 생성 전에 허용하며,
provenance의 dummy 전용 계약도 유지한다. 실제 provider 연결 권한을 열지 않는다.

음악 capability에는 `min_duration_seconds`와 `max_duration_seconds`가 필요하다.
planner는 최소 8개(설정값)부터 최대 12개 사이에서 가능한 가장 작은 개수를 고른다.
전체 source 프레임 합은 `목표 프레임 + crossfade 프레임 × (트랙 수 - 1)`이다.
나머지 프레임을 앞 트랙부터 1개씩 배분해 목표 길이를 정확히 맞추고,
각 source가 두 crossfade보다 길어야 한다. 상한은 내림, 하한은 올림하여 지킨다.
불가능한 길이·겹침 구성은 run 생성이나 provider 호출 전에 실패한다.

예: 3600초, 상한 380초, crossfade 2초이면 10트랙(각 361.8초)이다.
crossfade 5초이면 10트랙(각 364.5초)이다. 이는 길이 계산이며 실제 음질 검증이 아니다.
현재 QC 입력은 48 kHz stereo PCM fixture만 지원한다. 실제 44.1 kHz provider를 연결할 때는
별도의 resample 및 원본·변환 provenance가 필요하다.

계획은 initialize의 `track-plan.json`과 config snapshot에 저장한다.
chapter는 계획의 시작 프레임에서 만들고 mastering은 같은 timeline crossfade를 읽는다.
provider class/capability/rights와 계획을 config hash에 포함하여 설정이 달라진 재개를 막는다.
같은 구현의 offline adapter 재개에는 같은 adapter와 capability를 다시 주입해야 한다.
job lifecycle 모듈은 아직 별도이며 유료/비동기 API bridge는 후속 작업이다.

## 음악 provider 선택 체크리스트

- API 또는 약관이 automated generation을 허용하는가?
- 현재 요금제에서 commercial YouTube use/monetization을 허용하는가?
- 다운로드/생성 시점의 권리가 해지 이후에도 유지되는가?
- 독점권을 주는가, 비독점인가?
- 결과물의 저작권 성립을 보장하지 않는다는 조항이 있는가?
- provider가 결과물을 재사용하거나 유사 결과를 타인에게 줄 수 있는가?
- Content ID 등록을 금지하거나 제한하는가?
- prompt/input에 대한 권리가 필요한가?
- 유명 아티스트 모방이나 protected material 관련 제한은 무엇인가?
- 생성 로그, 영수증, account tier를 export할 수 있는가?

하나라도 불명확하면 production adapter를 활성화하지 않는다.

## Capability discovery

고정 가정 대신 adapter가 다음을 선언한다.

```text
max_duration_seconds
supports_seed
supports_negative_prompt
supports_instrumental_flag
supports_async_job
supports_idempotency_key
returns_model_version
commercial_use_status
content_id_registration_status
```

## Dummy provider

Phase 1 dummy adapter는 테스트 tone/algorithmic instrumental과 생성 이미지 placeholder를 로컬에서 만든다. 이것은 상업 공개용 asset이 아니며 provenance에 `rights.status=blocked` 또는 `intended_for_testing_only=true`를 기록한다.

## Raw response 보관

provider 응답은 실행 시점의 증거지만 비밀값이나 개인 정보를 포함할 수 있다. 저장 전에 authorization header, signed URL, token, 이메일을 redact한다. 원본 응답의 보관 기간과 암호화를 설정한다.

## Provider 교체 기준

- adapter contract test 통과
- 20개 이상의 sandbox sample QC 분포 확보
- 약관과 요금제 검토 기록
- 예상 단가와 quota/budget guard
- 장애·rate limit·삭제 정책 확인
- 기존과의 similarity/quality 비교
