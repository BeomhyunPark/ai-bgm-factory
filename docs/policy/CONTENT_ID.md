# Content ID 오탐 및 저작권 claim 대응

- 상태: Operational / Policy
- 최종 검토일: 2026-09-27

## 원칙

- claim은 자동으로 “부당함”으로 판정하지 않는다.
- dispute와 appeal은 법적·채널 위험을 동반할 수 있으므로 사람이 근거를 확인한다.
- pipeline은 증거를 모으고 초안을 만들 수 있지만 제출 버튼을 자동으로 누르지 않는다.
- claim을 피하려고 음높이/속도만 바꾸거나 audio를 은폐하지 않는다.

Content ID claim은 영상의 시청 가능 지역이나 수익화에 영향을 줄 수 있다. YouTube는 claim에 대해 dispute/appeal을 할 수 있는 절차를 제공하지만, 분쟁 중 수익 데이터 처리 등 영향이 있을 수 있다. [Monetization during copyright claim disputes](https://support.google.com/youtube/answer/7000961)

## 대응 흐름

```text
Claim detected
  -> keep video private / pause schedule
  -> capture claim details
  -> identify claimed segment and asset lineage
  -> verify provider terms + generation evidence
  -> compare claimant reference if available
  -> human decision
       -> accept / replace / mute / dispute
  -> archive outcome and update risk controls
```

## 즉시 조치

1. 영상이 private면 그대로 유지한다.
2. 예약 공개가 있으면 해제 또는 보류한다.
3. claim ID, claimant, policy, territories, segment timestamp, detected asset를 기록한다.
4. 관련 `run_id`, track, provider request ID, source/final hash를 고정한다.
5. 원본 파일과 증거를 수정·삭제하지 않는다.

## 조사 checklist

- claim 구간이 어느 track/ambience에 대응하는가?
- provider에서 직접 생성한 원본 hash와 일치하는가?
- 외부 sample/loop가 섞였는가?
- 생성 시점 account tier와 commercial use 근거가 있는가?
- Content ID 등록 제한이 있는가?
- 같은 provider의 비독점/유사 생성물이 원인일 가능성이 있는가?
- claimant가 provider 또는 정당한 권리자일 가능성이 있는가?
- dispute 사유가 사실과 증거에 정확히 부합하는가?

## 결정 옵션

### Claim 수락

권리가 부족하거나 비용 대비 대응 가치가 낮고 claim 조건을 수용할 때. 공개/수익화 영향을 기록한다.

### Track 교체 또는 구간 제거

근거가 불충분하거나 반복 오탐 provider일 때 우선 고려한다. YouTube가 제공하는 편집 옵션이 있을 수 있으나 final local master와 remote video의 차이를 provenance에 남긴다. [Remove copyright-claimed content from videos](https://support.google.com/youtube/answer/2902117)

### Dispute

명확한 권리 근거와 정확한 사유가 있을 때만 운영자가 제출한다. 자동 생성 초안은 provider/model/request ID, 생성 시각, license 근거, segment 설명을 포함하되 과장하거나 저작권 소유를 단정하지 않는다.

### Appeal

더 높은 위험 단계다. 거절 결과와 채널 영향을 이해하고 필요하면 법률 검토 후 진행한다.

## 증거 package

```text
claims/<claim_id>/
├── claim.json
├── decision.md
├── provenance.json
├── qc-report.json
├── provider-response.redacted.json
├── terms-evidence/
├── hashes.txt
└── correspondence/
```

## Provider 위험 점수

provider/model별로 다음을 추적한다.

- private upload 대비 claim 발생률
- 같은 claimant 반복률
- 해결 방식과 소요 시간
- dispute 성공/실패 결과
- 약관 근거의 명확성

claim 비율이 내부 임계치를 넘으면 해당 adapter/model을 자동 pause하고 신규 생성에 사용하지 않는다.

## 금지

- 증거 없이 “I own all rights” 제출
- 허위 counter notification
- 같은 claim을 근거 보완 없이 반복 dispute
- 오탐을 유발할 수 있는 asset의 Content ID 등록
- claim 회피를 목적으로 한 변조 후 재업로드
