# 운영 런북

- 상태: Operational

## 일상 생성

1. 환경 점검

```bash
python main.py doctor
```

2. package 생성

```bash
python main.py generate
```

3. 결과 검토

```bash
python main.py inspect <run_id>
```

4. 다음을 사람이 확인한다.

- 60분 전체의 대표 구간과 track transition
- 보컬/음성/유명 melody 의심 구간
- thumbnail과 영상의 일치
- title/description/chapters 정확성
- provenance와 license evidence
- 최근 영상과 실질적 차별성
- AI disclosure

5. 통과 후에만 private upload

```bash
python main.py upload <run_id> --privacy private
```

## Private upload 후 checklist

- YouTube processing 완료
- SD/HD 재생과 audio sync 확인
- 자동 copyright checks/claim 상태 확인
- thumbnail 렌더와 mobile crop 확인
- chapter parsing 확인
- description link/attribution 확인
- disclosure field/표시 확인
- audience setting 확인

이 확인이 끝나기 전 schedule하지 않는다.

## 실패별 대응

### Provider timeout/rate limit

- 같은 request의 idempotency 상태 확인
- backoff 한도 내 retry
- 중복 job/result 여부 확인
- 비용 누적이 budget을 넘으면 중단

### 음악 QC 실패

- failed measurement와 classifier version 확인
- 해당 slot만 regenerate
- 반복 실패 시 prompt/provider/model을 quarantine
- threshold를 낮춰 통과시키지 않음

### FFmpeg 실패

- disk space, codec build, input hash 확인
- 임시 output을 ready artifact로 등록하지 않음
- 같은 input hash로 resume 가능 여부 확인

### Upload timeout

- local upload attempt와 remote channel을 먼저 조회
- video ID가 이미 있으면 재업로드 금지
- 없다는 근거가 있을 때만 retry

### Content ID claim

[Content ID 대응](../policy/CONTENT_ID.md)을 따르고 schedule을 중단한다.

### Analytics 데이터 없음

- 최근 날짜의 보고 지연 가능성 확인
- scope/channel/video filter 확인
- `rows`가 없는 응답을 0으로 저장하지 않음
- 다음 sync에서 재조회

## Pause 조건

다음 중 하나면 scheduler와 신규 외부 생성/업로드를 pause한다.

- credential leak 의심
- provider 약관/라이선스 변경 미검토
- 반복 Content ID claim
- QC false negative 발견
- YouTube 정책 경고/strike
- daily budget 이상
- 중복 업로드 발견
- 공개 승인 bypass

## 데이터 복구

- DB와 manifest 중 하나가 없으면 자동 추정으로 publish하지 않는다.
- file hash가 다르면 새 artifact로 취급하고 재검토한다.
- provenance 없는 final은 orphan으로 quarantine한다.
- DB backup 복구 후 remote YouTube state를 read-only reconciliation한다.

## 비용 점검

run별로 text token, music seconds, image count, render time, storage, API request count를 집계한다. 예상 비용을 초과한 run은 추가 재생성 전에 중단한다.

## 월간 운영 검토

- provider 약관/요금제와 evidence freshness
- claim/policy 경고
- QC threshold 성능
- 공개 빈도와 영상 간 유사성
- 비용과 실패율
- analytics experiment 결과
- secret rotation/권한
- retention 대상 삭제 후보(dry-run)
