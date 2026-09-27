# YouTube 업로드와 스케줄링

- 상태: Operational / Normative
- 최종 검토일: 2026-09-27

## Private-first 원칙

모든 API upload는 `status.privacyStatus=private`로 시작한다. CLI에서 다른 값을 전달해도 production validator가 거부한다. 공개/예약은 별도 상태 전이와 승인으로 수행한다.

YouTube 공식 upload 예시는 `privacyStatus`를 지정할 수 있고, API 문서는 unverified project의 upload가 private로 제한된다고 설명한다. [Upload a video](https://developers.google.com/youtube/v3/guides/uploading_a_video) [Video resource](https://developers.google.com/youtube/v3/docs/videos)

## 업로드 전 조건

- run status = `ready_for_review`
- final video/thumbnail/metadata/provenance hash 일치
- rights status = `verified_for_intended_use`
- QC/package/policy gates 통과
- channel ID allowlist 일치
- daily upload cap 미초과
- upload feature flag enabled
- explicit CLI command

## 업로드 request

- title, description, tags, category
- `privacyStatus=private`
- explicit audience setting
- 정책상 필요한 `containsSyntheticMedia`
- resumable upload와 exponential backoff

upload response와 video ID는 redacted raw response와 함께 저장한다.

## Scheduling

YouTube `status.publishAt`은 private이며 아직 공개된 적 없는 영상에 미래 ISO 8601 시각으로 설정한다. update 요청에서도 privacy status를 private로 함께 지정해야 할 수 있다. 과거 시각은 즉시 공개로 이어질 수 있으므로 최소 lead time과 미래 시각 검증을 강제한다. [Video resource: `status.publishAt`](https://developers.google.com/youtube/v3/docs/videos)

내부 조건:

- state = `uploaded_private`
- processing/check 완료
- active claim/policy block 없음
- approval record의 artifact/metadata hash 일치
- `publishAt >= now + 2h` 기본
- timezone offset 명시
- 동일 channel schedule collision 없음
- daily/weekly public cap 준수

## Approval

승인은 UI 또는 명시적 CLI action으로 만들고 다음을 저장한다.

- approver identity
- timestamp
- exact video/metadata/thumbnail hashes
- rights/QC/disclosure/claim check 결과
- intended publish time

승인 뒤 metadata나 asset이 바뀌면 승인을 무효화한다.

## Reconciliation

local DB만 믿지 않고 주기적으로 remote video state와 비교한다.

- local upload pending + remote exists → video ID 연결
- local private + remote public → incident
- local scheduled time != remote → schedule pause
- duplicate video hash → 추가 공개 금지

## Quota

YouTube Data API는 quota를 사용한다. 공식 quota 문서에서 기본 할당과 감사 절차를 확인하고, quota를 우회하기 위해 여러 project를 사용하지 않는다. [Quota and compliance audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits)

## Rollback

예약 전: private 유지 또는 schedule 제거.

공개 후: 자동 삭제하지 않는다. 문제 유형에 따라 private 전환, metadata 정정, edit/replace, 삭제를 사람이 결정하고 원격 상태와 증거를 보존한다.
