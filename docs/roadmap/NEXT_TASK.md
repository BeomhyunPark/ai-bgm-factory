# 다음 작업 인계

## 현재 위치

Phase 0 + Phase 1 오프라인 코드와 GitHub main 업로드가 완료되어 있다.
Linux 검증은 `verification/REPORT.md`, 맥북 설치와 1분 검증은
`verification/MACOS_REPORT.md`를 확인한다. 맥북 60분 smoke 포함 49개 전체 테스트도
1회 통과했다. source commit과 구현 hash는 검증 증거에 기록한다.

## 구성된 사용자 맥북에서 실행

```bash
cd ai-bgm-factory
source .venv/bin/activate
python main.py doctor
python main.py generate --duration-minutes 1
```

Python 3.12, FFmpeg, `.venv`와 dummy `.env`가 구성되어 있으며 API 키 없이 동작한다.
새 머신 설치는 [로컬 개발 가이드](../operations/LOCAL_DEVELOPMENT.md)를 따른다.
생성 음원·영상, `.env`, 인증 파일, 캐시는 Git에서 제외한다.

## Phase 2 착수 순서

1. 먼저 채널 청취 목적/장르 1개를 정한다. 예산이 미정이면 비교표를 먼저 만들고 결제는 하지 않는다.
2. 음악 생성 서비스 후보의 **공식 API 지원**, 자동화 허용, 현재 플랜의 YouTube 상업 이용,
   해지 후 기존 생성물 권리, Content ID 제한을 공식 문서로 확인한다.
3. 선택한 서비스의 terms snapshot/reference와 계정 tier를 evidence bundle로 남긴다.
4. adapter contract fixture, job polling, timeout/idempotency, 비용·일일 한도부터 구현한다.
5. 오류·중복 요청 시나리오와 20개 sandbox sample을 검증한다.
6. 실제 음원에 dummy QC를 적용해 게시 가능하다고 표시하지 않는다. Phase 3~4가 필요하다.
7. YouTube upload는 Phase 7까지 disabled를 유지한다.

## 코딩 에이전트 시작 프롬프트

이 저장소의 AGENTS.md, README.md, docs/architecture/DECISIONS.md와
검증 보고서를 먼저 읽고 현재 코드를 확인하라. Phase 1을 다시 만들지 말고 Phase 2 준비를 진행하라.
실제 음악 provider는 아직 정하지 않았다. 현재 공식 API·약관·상업 이용 근거를 확인한 비교 결과를
먼저 제시하고, 선택 후 기존 GenerationProvider 인터페이스와 contract tests를 확장하라.
권리 상태를 추정하거나 dummy 테스트 예외를 실제 음악에 적용하지 말라.
비용 발생 전에 선택한 서비스와 예산을 확정하고, 업로드/공개 기능을 활성화하지 말라.
