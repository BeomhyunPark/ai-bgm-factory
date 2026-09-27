# 위험 등록부

- 상태: Living document

| ID | 위험 | 가능성 | 영향 | 예방/완화 | Owner trigger |
|---|---|---:|---:|---|---|
| R-001 | 반복·대량생산형으로 판단되어 수익화 거절 | 높음 | 높음 | creative brief, similarity gate, 저빈도 pilot, human review | similarity 상승/정책 경고 |
| R-002 | AI 음악 상업 이용권 불명 | 중간 | 매우 높음 | provider evidence registry, rights gate, terms review | 약관/요금제 변경 |
| R-003 | Content ID 오탐 | 높음 | 높음 | private checks, provenance bundle, provider claim rate | claim 발생 |
| R-004 | 보컬/유명 melody 유입 | 중간 | 높음 | vocal/similarity detection, prompt block, sampling review | QC false negative |
| R-005 | secret/OAuth token 노출 | 중간 | 매우 높음 | ignored secrets, redaction, minimal scopes, rotation | scanner/비정상 비용 |
| R-006 | 예약 시각 오류로 즉시 공개 | 낮음 | 매우 높음 | future validation, 2h lead, timezone required, approval | `publishAt <= now` |
| R-007 | upload timeout 후 중복 영상 | 중간 | 중간 | idempotency record, remote reconciliation | unknown upload status |
| R-008 | 생성 비용 폭주 | 중간 | 높음 | daily/request budget, retry cap, kill switch | 예산 80% |
| R-009 | QC가 음악성을 훼손 | 중간 | 중간 | 원본 보존, calibration, human sample review | retention/complaint 저하 |
| R-010 | metadata/thumbnail가 오해 유발 | 중간 | 높음 | content alignment validator, claim blacklist | early retention 급락 |
| R-011 | Analytics 상관관계를 인과로 오해 | 높음 | 중간 | experiment registry, minimum sample/window | 자동 확대 제안 |
| R-012 | provider outage/API 변경 | 높음 | 중간 | adapter, capability checks, circuit breaker | error rate 상승 |
| R-013 | disk 부족으로 render 손상 | 중간 | 중간 | preflight space, temp+atomic rename, cleanup dry-run | free space threshold |
| R-014 | C2PA/disclosure metadata 유실 | 중간 | 중간 | inspect/preserve, description fallback, private verify | metadata mismatch |
| R-015 | 법률/플랫폼 정책 변경 | 중간 | 매우 높음 | 분기 검토, versioned policy decision, pause | 공식 변경 알림 |

## Severity 규칙

- 매우 높음: credential/법적 권리/공개 오작동/채널 제재 가능
- 높음: 게시 중단, 수익화 또는 반복 claim 위험
- 중간: 재작업·비용·품질 저하
- 낮음: 제한된 운영 불편

## Escalation

R-002, R-003, R-005, R-006, R-015가 발생하면 scheduler와 관련 provider를 즉시 pause한다. 자동화는 안전 조건이 회복될 때까지 재개하지 않는다.
