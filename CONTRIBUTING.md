# 기여 가이드

## 작업 원칙

1. 한 변경은 하나의 명확한 목적만 가진다.
2. 외부 서비스는 adapter 뒤에 숨기고 domain code에서 SDK를 직접 호출하지 않는다.
3. 기본 실행은 오프라인·재현 가능해야 한다. 테스트에서 실제 유료 API를 호출하지 않는다.
4. 사용자 입력, 모델 출력, 외부 API 응답은 신뢰하지 않고 schema validation을 거친다.
5. 실패를 성공으로 위장하지 않는다. 부분 산출물은 상태를 `failed` 또는 `partial`로 기록한다.
6. 공개 상태 변경은 별도 명령과 명시적 승인 없이는 수행하지 않는다.

## 개발 흐름

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
python main.py doctor
pytest
```

실제 패키지와 명령은 구현 과정에서 확정하되, README와 운영 문서를 동시에 갱신한다.

## 완료 정의

- 요구사항 ID 또는 Phase exit criteria가 변경 설명에 연결되어 있다.
- unit test와 관련 integration test가 통과한다.
- 외부 API 호출은 fixture 또는 fake adapter로 재현 가능하다.
- 생성 파일의 hash와 입력 설정이 manifest/provenance에 기록된다.
- 로그에 secret, OAuth token, 원문 자격 증명이 노출되지 않는다.
- 새 환경 변수는 `.env.example`과 환경 설명 문서에 같이 추가된다.
- 정책 또는 권리 판단에 영향을 주는 변경은 `docs/policy/`를 갱신한다.
- 실패·재시도·idempotency 동작을 검증한다.

## 테스트 계층

| 계층 | 목적 | 외부 호출 |
|---|---|---|
| Unit | 순수 로직, schema, prompt builder, QC threshold | 금지 |
| Contract | provider request/response fixture 검증 | 금지 |
| Integration | FFmpeg, filesystem, SQLite, fake provider | 기본 금지 |
| Sandbox | provider test account와 private YouTube upload | 명시적 opt-in |
| Smoke | 60분 최종 산출물과 재생 가능성 검증 | 필요 시 허용 |

## 커밋과 리뷰

- 식별 가능한 secret과 생성 media binary는 커밋하지 않는다.
- 대용량 샘플은 작은 fixture나 생성 script로 대체한다.
- migration은 역방향 호환 또는 명시적 변환 절차를 제공한다.
- PR 설명에는 `무엇`, `왜`, `검증`, `운영/정책 영향`을 적는다.

## 정책 관련 변경

다음 변경은 사람의 검토가 필요하다.

- 기본 privacy를 `private` 이외로 바꾸는 변경
- AI disclosure 자동 판단 기준 변경
- 라이선스 허용/차단 규칙 변경
- Content ID claim 자동 처리 변경
- QC threshold 완화
- 일일 생성·업로드 한도 증가
