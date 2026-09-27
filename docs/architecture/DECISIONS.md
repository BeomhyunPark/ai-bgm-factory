# 구현 결정 · 2026-09-27

## ADR-001 — Phase 1의 ready 상태와 blocked 권리

AC-006은 dummy 결과에도 `ready_for_review`를 요구하지만 PIPELINE의 일반 package gate는
검증되지 않은 권리를 차단한다. Phase 1은 `review_scope=local_test_only`와
`intended_for_testing_only=true`를 함께 기록한 **로컬 검토용 package**만 허용한다.
rights는 항상 `blocked`, `upload_eligible=false`다. 실제 provider의 권리 판정 규칙은 바꾸지 않는다.
업로드·공개·예약 명령은 실패 코드로 종료한다. Phase 2 이후도 이 테스트 예외를 사용할 수 없다.

## ADR-002 — 작동하는 기능과 미구현 검사의 분리

- 구현: PCM duration/peak/silence/RMS, 트랙별 RMS gain, crossfade, 2-pass loudnorm,
  master LUFS/true peak 측정, FFprobe codec/duration/A-V 및 전체 영상 decode.
- 미구현: 실제 음원 보컬 분류, spectral anomaly, 음원·영상 유사도와 독창성 평가.
  측정하지 않은 확률이나 점수를 0으로 만들지 않고 null/`not_evaluated`로 기록한다.
- 소스 test track 8개는 seed별로 전체 길이를 합성한다. 짧은 오디오 파일의 반복 조립은 사용하지 않는다.
- 테스트 배경은 코드로 만든 1280×720 정지 카드, 1 fps다. 채널용 디자인·음악 품질을 대표하지 않는다.
- 소스 wav, premaster, master를 보존한다. 자동 삭제 기능은 없다.

## ADR-003 — 실행/재개와 상태 저장

- CLI / 단일 Python process + SQLite + 로컬 filesystem. queue/server는 없다.
- 실행 디렉터리 생성 충돌 + POSIX flock으로 동일 run 동시 실행을 차단한다.
- stage별 attempt 디렉터리와 완료 파일 SHA-256을 보존한다.
- 실패 재개는 동일 config/implementation hash를 요구하고 완료 파일 모두를 재검증한다.
- 성공 run 재개는 검증 후 무변경 반환. 완료 파일의 누락·변조는 덮어쓰지 않고 실패한다.
- manifest는 실행 checkpoint, SQLite는 조회 인덱스다. manifest를 먼저 원자적으로 기록하고
  DB에 저장한다. crash 후 재개할 때 검증된 manifest에서 DB를 재동기화한다.
- `kill -9` 직후는 `running`이 남을 수 있으며 명시적 `--resume`에서 새 attempt로 이어간다.
- 파일 권한/디스크 오류로 최종 checkpoint 자체를 쓸 수 없는 경우는 수동 점검이 필요하다.

## ADR-004 — 오프라인 검증

일반 pytest는 Python socket/DNS를 차단한다. Linux acceptance runner는 libseccomp로
socket/connect/sendto syscall을 차단하며 모든 자식 FFmpeg/ffprobe에도 적용한다.
서로 다른 clean source export에서 전체 test + 기본 60분 smoke를 3회 연속 실행한다.
macOS에는 POSIX flock과 동일 CLI를 지원하도록 작성했지만 이번 실제 실행 검증은 Linux다.

## 범위와 열려 있는 결정

- Phase 1 비용은 0 USD / 외부 요청 0건. 생성 일일 한도와 실제 provider 예산은 Phase 2 전에 구현한다.
- 채널 콘셉트/이름, 음악 API와 요금제, 이미지 API는 아직 미결정이다.
- dummy disclosure는 실제 알고리즘 합성과 테스트 사실만 적는다. 사람 검토 완료를 허위로 쓰지 않는다.
- 제공받은 정책 문서는 보존했으며 이번 구현에서 최신 법률·플랫폼 정책을 재검토한 것은 아니다.
  실제 provider 승인/업로드 전에 공식 원문과 생성 시점 라이선스 근거를 확인해야 한다.
- production QC 또는 공개 가능성을 Phase 1 통과로 주장하지 않는다.


## 장시간 검증에서 보강한 부분

첫 장시간 실행에서 source WAV의 크기/hash가 기록과 달라져 인수 테스트가 실패했다.
파일 변경의 외부 원인은 단정하지 않았으며 실패 실행을 통과 횟수에 포함하지 않는다.
이후 source WAV를 임시 파일로 완성·fsync한 뒤 원자적으로 등록하고, 트랙 길이를 목표값과
비교하며, package gate에서 원본·기존 산출물 전체 hash를 재검증하도록 보강했다.
별도 임시 디렉터리의 clean source export에서 수정된 코드로 3회 연속 전체 검증에 성공했다.
