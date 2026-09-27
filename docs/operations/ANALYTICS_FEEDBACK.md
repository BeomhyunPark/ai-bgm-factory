# YouTube Analytics 피드백 루프

- 상태: Draft / Phase 9
- 최종 검토일: 2026-09-27

## 목적

Analytics는 “더 많이 찍어내기”가 아니라 어떤 청취 상황과 음악 구조가 장기 만족도를 높이는지 배우기 위해 사용한다. feedback은 다음 creative brief의 후보를 만들 뿐 자동 공개 결정을 하지 않는다.

YouTube Analytics API는 날짜, 영상, 국가, traffic source 등의 dimension과 views, average view duration, estimated minutes watched, likes, subscriber 변화 등 metrics를 제공한다. 지원 조합과 최신 가용성은 공식 문서를 따른다. [Dimensions](https://developers.google.com/youtube/analytics/dimensions) [Metrics](https://developers.google.com/youtube/analytics/metrics) [Reports query](https://developers.google.com/youtube/analytics/reference/reports/query)

## 수집 계층

### Daily video facts

- `day`, `video`
- `views`
- `estimatedMinutesWatched`
- `averageViewDuration`
- `likes`, `comments`, `shares`
- `subscribersGained`, `subscribersLost`
- 지원되는 경우 impression/CTR, retention 관련 지표

가장 최근 날짜는 보고 지연으로 누락될 수 있다. 누락 행을 0으로 채우지 않고 `not_available`로 둔다.

### Creative features

각 run에서 다음 feature를 join한다.

- use case, mood, genre, BPM range
- 평균/분산 energy와 track count
- visual motif, color family, thumbnail text density
- title pattern과 publish time
- provider/model, QC summary

민감한 demographic data는 필요가 입증되기 전 수집하지 않는다.

## 평가 창

- 24h: 기술적/metadata 문제 조기 감지용
- 7d: 초기 비교
- 28d: 기본 실험 판정
- 90d: evergreen BGM 장기 성과

서로 다른 기간의 영상을 같은 누적값으로 직접 비교하지 않는다.

## Guardrail metrics

성공 metric과 함께 아래를 본다.

- Content ID/policy issue rate
- dislike/negative feedback 가용 신호
- subscriber loss
- thumbnail-title mismatch에 대한 retention drop
- generation failure/cost
- channel-level similarity score

## Experiment 규칙

1. 한 번에 핵심 변수 하나만 바꾼다.
2. experiment ID와 hypothesis를 publish 전에 고정한다.
3. 최소 sample과 관찰 기간 전에 승자를 선언하지 않는다.
4. 작은 차이를 자동 확대 생산하지 않는다.
5. 계절, traffic source, publish time 같은 confounder를 기록한다.
6. 실패 결과도 보존한다.

예:

```json
{
  "experiment_id": "exp-bpm-001",
  "hypothesis": "Night coding 영상에서 78-84 BPM이 90-96 BPM보다 28일 averageViewDuration을 높인다.",
  "primary_metric": "averageViewDuration",
  "guardrails": ["subscribersLost", "claimRate"],
  "minimum_observation_days": 28,
  "status": "proposed"
}
```

## Feedback output

```text
analytics/feedback/<date>.json
```

포함 항목:

- evidence window와 query definitions
- sample sizes와 missing data
- observed associations(인과로 표현하지 않음)
- 유지/중단/추가 실험 후보
- 금지된 최적화 여부
- 사람이 승인할 다음 concept constraints

## 금지된 최적화

- 클릭만 높이고 시청 만족도를 낮추는 title/thumbnail
- 민감한 감정·건강 주장의 과장
- 데이터가 부족한데 winning pattern으로 단정
- 한 편의 성과를 근거로 대량 복제
- policy/claim 비용을 무시한 조회수 최적화
- Analytics 데이터를 prompt에 그대로 넣어 개인정보나 내부 식별자를 노출
