# Phase 0–1 구현·검증 보고서

- 검증일: 2026-09-27 (Asia/Seoul)
- 결과: 오프라인 dummy 제작 파이프라인 인수 테스트 3회 연속 통과
- 검증 코드 commit: `df3a86b5507217ca4d8f43dbe3e7c3c62e2ee60d`
- 각 실행은 같은 commit의 새 Git archive에서 시작. 이전 data/cache 산출물 미사용.
- Python 3.12.14, FFmpeg/ffprobe 6.1.1, Linux x86_64.
- 설치와 installed CLI 도움말도 확인. macOS에서의 직접 실행은 아직 미검증.

## 실제 결과

| 실행 | 전체 테스트 | 영상 길이 | A/V 차이 | Master loudness | Master true peak | 테스트 총 소요 |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 45 passed | 3600.0 s | 0.000 s | -14.0 LUFS | -7.6 dBTP | 381.75 s |
| 2 | 45 passed | 3600.0 s | 0.000 s | -14.0 LUFS | -7.6 dBTP | 377.93 s |
| 3 | 45 passed | 3600.0 s | 0.000 s | -14.0 LUFS | -7.6 dBTP | 382.76 s |

각 실행에 doctor, lint, source secret scan, 44개 일반 테스트, 1개 60분 smoke test가 포함된다.
Linux libseccomp로 socket/connect/sendto를 막고 실제 EPERM을 확인한 뒤 테스트했다.
같은 제한이 FFmpeg/ffprobe 자식 process에도 적용된다. 테스트 완료 로그는 `run-1.log`~`run-3.log`다.
FFmpeg가 전체 final.mp4를 끝까지 decode한 뒤에만 성공 상태로 기록했다.

## 인수 기준 매핑

| 기준 | 확인 내용 |
|---|---|
| AC-001 | CLI generate의 기본 60분/seed 42 실행 및 새 run ID |
| AC-002 | 필수 5개 파일 존재 및 0 byte 아님 |
| AC-003 | 16:9 H.264/AAC, 48 kHz stereo, 길이·A/V 차이·전체 decode |
| AC-004 | 실제 timeline에서 만든 8개 chapter, 00:00 시작, private |
| AC-005 | dummy 명시, source/raw/final SHA-256, blocked 권리, secret scan |
| AC-006 | 10개 stage succeeded, 실제 파일 hash 일치, local-test ready 상태 |
| AC-007 | 부분 MP4 생성 후 실패 주입, failed 기록, final 미등록 |
| AC-008 | 같은 seed/config metadata 일치, 충돌 차단, 검증된 stage 재사용 |
| AC-009 | Linux kernel network denial 하에서 전체 생성 성공 |
| AC-010 | CLI/default config/README/schema/docs 링크 검증 |

## 배포 묶음 구성

- 프로젝트 코드, 23개 원본 문서 기반 정리본, 구현 결정, 다음 작업 인계.
- `verification/`: 실제 테스트 로그와 세 실행의 JSON/JSONL 증거.
- `sample/`: 첫 60분 테스트 영상, 썸네일, 메타데이터, provenance/manifest 사본.
- 대용량 source WAV/premaster/master는 전달 묶음에서 제외했다. 코드를 실행하면 재생성된다.
  따라서 sample/과 verification/의 manifest는 **검증 당시 기록 사본**이며,
  이 폴더를 data/runs로 옮겨 inspect/resume하는 용도가 아니다.
  원본 데이터가 필요한 검증은 새 generate run으로 수행한다.

## 완료 범위와 다음 단계

Phase 0 기반과 Phase 1 테스트용 pipeline을 구현·검증했다.
실제 음악 API, 보컬·유사도 분류기, 상업 권리 검증, YouTube 업로드와 예약은 미구현이다.
ready_for_review는 local_test_only이며 rights=blocked / upload_eligible=false를 유지한다.
음원·배경은 알고리즘 테스트 fixture로, 최종 채널 콘텐츠 품질을 대표하지 않는다.
음악 provider의 공식 API와 라이선스 검토·선택이 Phase 2의 첫 작업이다.

초기 장시간 실행의 source 파일 크기 불일치는 실패로 처리했고, 원자적 파일 등록과 최종 무결성 검사를 보강한 뒤 위 세 실행을 수행했다. 최초 실패는 통과 횟수에 포함하지 않았다.

이번 작업은 제공받은 정책 문서의 최신 법률·플랫폼 정책 검토를 수행한 것이 아니다.
