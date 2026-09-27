# AI 생성 음악 권리와 provenance 정책

- 상태: Policy / Normative
- 최종 검토일: 2026-09-27
- 면책: 이 문서는 운영 통제안이며 법률 자문이 아니다.

## 핵심 원칙

`commercial use allowed`, 저작권 소유, 독점성, YouTube 수익화 적합성, Content ID 등록 가능성은 서로 다른 질문이다. 하나의 문구로 나머지를 추정하지 않는다.

## Provider 승인 전 확인

다음을 공식 약관·라이선스·요금제 문서에서 확인하고 evidence로 저장한다.

1. API/자동화 사용 허용 여부
2. 생성 당시 가입 tier에서 상업 이용 허용 여부
3. YouTube 광고 수익화 포함 여부
4. 해지 후 기존 생성물 사용 권리
5. 결과물의 독점/비독점 성격
6. provider의 결과물 재사용 및 유사 출력 가능성
7. Content ID 또는 타 독점 권리관리 등록 제한
8. 입력 prompt/sample에 필요한 권리
9. 결과물에 대한 provider 보증과 면책 범위
10. 지역·업종·규모·매출에 따른 제한

서비스의 marketing page만 보지 않고 실제 적용 Terms/License를 확인한다. 예를 들어 provider의 약관은 서비스와 API를 함께 규율할 수 있으므로 해당 계정·API에 적용되는 문서를 구분해 기록한다. [Stability AI Terms of Service](https://stability.ai/terms-of-service)

## 생성 시점 evidence bundle

각 request마다 다음을 남긴다.

- provider와 product 이름
- model 및 version(제공되지 않으면 `unknown`)
- account/subscription tier
- request ID/job ID
- 생성 시각과 timezone
- prompt, negative prompt, seed, generation parameters
- provider raw response의 redacted copy와 hash
- 다운로드한 source file hash
- 적용 Terms/License URL
- 약관 검토 시각과 snapshot hash 또는 보관 위치
- 결제 영수증/구독 증빙 reference(비밀·개인정보는 별도 보관)
- permitted use와 restrictions의 사람이 검토한 요약

URL만 저장하면 약관 변경 후 당시 근거를 재현할 수 없다. 허용되는 범위에서 snapshot 또는 PDF, 최소한 cryptographic hash와 검토 기록을 보관한다. 웹페이지 보관이 약관상 허용되지 않으면 screenshot/reference와 reviewer note를 남긴다.

## 권리 상태 gate

| 상태 | 의미 | YouTube 사용 |
|---|---|---|
| `verified_for_intended_use` | 계획된 commercial YouTube use 근거 확인 | private 후보 가능 |
| `restricted` | 일부 사용 또는 지역/채널 제한 | 제한을 만족할 때만 |
| `unverified` | 근거 미확인 | upload 금지 |
| `expired` | 당시/현재 약관 상태 불명 | 공개·재사용 중단 후 재검토 |
| `blocked` | 사용 불가 또는 test-only | upload 금지 |

## Prompt/IP 정책

- 살아 있거나 사망한 특정 아티스트의 스타일 모방을 요구하지 않는다.
- 유명 곡명, 가사, melody, stem을 reference input으로 넣지 않는다.
- 사용자 소유 또는 명시적 라이선스를 가진 sample만 사용한다.
- 브랜드/게임/영화의 공식 soundtrack처럼 보이게 이름 붙이지 않는다.
- 우연한 유사성 탐지를 위해 audio fingerprint/similarity gate를 둔다.

## Content ID 등록

기본 정책은 **AI 생성 track을 Content ID에 등록하지 않음**이다. 비독점 결과물, provider 약관, 유사 생성 가능성 때문에 타인의 정당한 사용을 오탐 claim할 위험이 있다. 등록을 검토하려면 별도 법률/배급사 검토와 독점권 증거가 필요하다.

## 파생물과 변환

normalize, EQ, crossfade, ambience overlay, trim을 했다는 사실만으로 새로운 권리나 독점성이 생긴다고 가정하지 않는다. 모든 source asset의 권리 chain이 통과해야 final master가 통과한다.

## 보존

- final published asset의 provenance: 최소 7년 권장
- provider raw response: 기본 1년, 개인정보/약관에 따라 조정
- terms/license evidence: 해당 asset이 공개된 동안 + 삭제 후 분쟁 대응 기간
- hash와 index: media 삭제 후에도 정책에 맞는 최소 기간 보관

삭제 요청, provider terms, 개인정보 보호 의무가 위 보존 기간보다 우선할 수 있다.

## 변경 감시

provider별로 `terms_reviewed_at`을 두고 최소 분기 1회, 또는 가격제/모델/약관 변경 알림 시 즉시 재검토한다. 변경이 확인되면 새 생성부터 adapter를 pause하고 기존 공개물 영향도 별도로 평가한다.
