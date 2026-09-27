# Provider adapter 설계

- 상태: Normative

## 목적

음악·이미지·텍스트 provider의 SDK, 요금, 모델명, 정책 변경을 core pipeline과 분리한다. 서비스 선택은 기능뿐 아니라 자동화 허용 여부와 상업 이용 근거를 함께 평가한다.

## 공통 interface

```python
class GenerationProvider(Protocol):
    def capabilities(self) -> ProviderCapabilities: ...
    def validate_request(self, request: GenerationRequest) -> None: ...
    def generate(self, request: GenerationRequest) -> GenerationResult: ...
    def get_rights_evidence(self) -> RightsEvidence: ...
```

`GenerationResult`는 최소한 다음을 포함한다.

- normalized asset location
- provider/model/model version
- request ID
- created timestamp
- seed(지원 시)
- usage/cost
- raw response reference
- provider moderation result

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
