# 보안과 secret 관리

- 상태: Normative / Operational

## 보호 대상

- 생성 provider API key
- Google OAuth client secret과 refresh/access token
- channel ID, 내부 cost/analytics data
- provider raw response의 signed URL/개인정보
- licensing invoice와 account tier 증빙

## 기본 규칙

- secret은 `.env.example`에 값 없이 이름만 둔다.
- 실제 `.env`, `secrets/`, OAuth token, provider evidence 원본은 `.gitignore` 대상이다.
- production은 OS keychain 또는 secret manager를 사용한다.
- key를 command line argument로 전달하지 않는다. process list/shell history에 남을 수 있다.
- log, exception, telemetry, provenance에 secret을 쓰지 않는다.
- 최소 scope와 별도 project/account를 사용한다.
- 개발/production credential을 분리한다.

## YouTube OAuth

- 최소 필요한 scope만 요청한다.
- upload와 analytics read credential의 분리를 검토한다.
- token file permission은 owner-only로 제한한다.
- OAuth callback/state를 검증한다.
- refresh token은 암호화 저장하고 백업·복사 범위를 제한한다.
- credential revoke 절차를 정기적으로 시험한다.

## Input/output 안전

- 모델이 반환한 path, filename, URL을 그대로 shell에 넣지 않는다.
- subprocess는 argument array로 실행하고 `shell=True`를 사용하지 않는다.
- output path는 run directory 내부로 normalize하고 traversal을 차단한다.
- MIME sniffing과 decoder 검증을 수행한다.
- 다운로드에는 size/time/type 제한을 둔다.
- metadata/description을 로그나 shell command에 interpolate하지 않는다.

## Redaction

다음 key pattern과 URL query를 자동 redact한다.

```text
authorization
api_key
access_token
refresh_token
client_secret
signed_url
x-goog-signature
```

secret scanner는 commit 전과 package gate 양쪽에서 실행한다.

## Rotation

- 노출 의심 즉시 key revoke/rotate
- 관련 log/artifact 접근 중단 및 영향 범위 확인
- Git history에 들어간 경우 단순 새 commit 삭제로 끝내지 않는다.
- 사건 기록에 secret 원문을 복사하지 않는다.

## Incident 절차

1. external side effect feature flags를 끈다.
2. credential을 revoke한다.
3. provider/Google audit log와 비용을 확인한다.
4. 노출된 저장소, artifact, log 범위를 파악한다.
5. 새 credential 발급과 least privilege를 적용한다.
6. 원인, 영향, 재발 방지를 기록한다.

## `.gitignore` 최소 항목

```gitignore
.env
.env.*
!.env.example
secrets/
data/
*.token.json
client_secret*.json
```
