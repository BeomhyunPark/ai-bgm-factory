# 문서 인덱스

## 1. 요구사항

- [PRD](requirements/PRD.md): 문제, 사용자, 범위, 성공 기준
- [기능 요구사항](requirements/FUNCTIONAL_REQUIREMENTS.md): 추적 가능한 `FR-*`, `NFR-*`
- [인수 기준](requirements/ACCEPTANCE_CRITERIA.md): 첫 `generate` 목표의 검증 규칙

## 2. 아키텍처

- [시스템 개요](architecture/SYSTEM_OVERVIEW.md): 컴포넌트, 경계, 상태 모델
- [파이프라인](architecture/PIPELINE.md): 단계별 입출력, 실패·재시도
- [데이터 계약](architecture/DATA_CONTRACTS.md): manifest, metadata, provenance schema 초안
- [Provider adapter](architecture/PROVIDER_ADAPTERS.md): 외부 생성 서비스 교체 규칙
- [오프라인 음악 job 계약](architecture/MUSIC_JOBS.md): fake adapter, 재개, 비용 예약
- [음악 HTTP 계약](architecture/MUSIC_HTTP.md): 응답 fixture, Retry-After, evidence

## 3. 정책

- [YouTube 및 수익화](policy/YOUTUBE_MONETIZATION.md)
- [AI 음악 권리와 provenance](policy/AI_MUSIC_RIGHTS.md)
- [Content ID 대응](policy/CONTENT_ID.md)
- [AI disclosure](policy/AI_DISCLOSURE.md)
- [보안과 secret](policy/SECURITY.md)

## 4. 운영

- [로컬 개발](operations/LOCAL_DEVELOPMENT.md)
- [환경 변수](operations/ENVIRONMENT.md)
- [운영 런북](operations/RUNBOOK.md)
- [업로드와 스케줄링](operations/UPLOAD_SCHEDULING.md)
- [Analytics 피드백 루프](operations/ANALYTICS_FEEDBACK.md)

## 5. 로드맵

- [Phase 0~9](roadmap/PHASES.md)
- [음악 API 후보 비교와 Phase 2 구현 순서](roadmap/MUSIC_PROVIDER_COMPARISON.md)
- [위험 등록부](roadmap/RISK_REGISTER.md)

## 문서 상태 표기

- `Normative`: 구현이 따라야 하는 계약
- `Draft`: 구현 전 검증이 필요한 초안
- `Operational`: 실제 운영 중 따라야 하는 절차
- `Policy`: 공식 정책 및 내부 안전 기준

정책 원문은 변경될 수 있다. 각 정책 문서의 `최종 검토일`과 공식 링크를 정기적으로 확인한다.


## 구현 기록

- [구현 결정과 미결정 사항](architecture/DECISIONS.md)
