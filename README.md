# AI BGM Factory

AI를 이용해 **무보컬 작업용 BGM 영상**을 기획·생성·검수·렌더링하고, YouTube에 안전하게 비공개 업로드한 뒤 성과 데이터를 다음 기획에 반영하는 자동화 프로젝트다.

> 핵심 원칙: 자동화는 제작 속도를 높이기 위한 수단이다. 권리 확인, 채널 고유성, 품질 기준, 공개 전 최종 판단을 생략하기 위한 수단이 아니다.

## 첫 개발 목표

```bash
python main.py generate
```

한 번의 실행으로 로컬에 다음 산출물을 만든다.

```text
data/runs/<run_id>/
├── final.mp4             # 60분 완성 영상
├── thumbnail.jpg         # YouTube 썸네일
├── metadata.json         # 제목, 설명, 태그, 트랙리스트, 공개 설정 후보
├── provenance.json       # 모델·프롬프트·라이선스·해시·변환 이력
├── manifest.json         # 실행 상태와 모든 산출물 인덱스
└── logs/
```

Phase 1에서는 외부 API 없이 dummy asset으로 이 계약을 먼저 완성한다. 실제 음악 API, QC, provenance 강화, 비주얼, 메타데이터, 업로드, 스케줄러, Analytics는 Phase 2~9에서 순서대로 교체·확장한다.

## 안전한 기본값

- 업로드는 언제나 `private`가 기본이다.
- `generate`는 파일만 생성하며 자동 공개하지 않는다.
- `public`/`unlisted` 전환은 별도 승인 게이트를 통과해야 한다.
- 생성물마다 상업 이용 근거와 원본 응답을 provenance에 남긴다.
- 보컬 감지, clipping, silence, loudness, 길이, 중복도 검사를 통과하지 못하면 실패 처리한다.
- 영상 간 콘셉트·음악·이미지·구성의 실질적 차이가 확인되지 않으면 게시 후보가 될 수 없다.
- API 키, OAuth token, client secret은 Git에 저장하지 않는다.

## 문서 지도

| 영역 | 문서 |
|---|---|
| 시작점 | [문서 인덱스](docs/INDEX.md) |
| 제품 범위 | [PRD](docs/requirements/PRD.md) |
| 기능·품질 기준 | [기능 요구사항](docs/requirements/FUNCTIONAL_REQUIREMENTS.md), [인수 기준](docs/requirements/ACCEPTANCE_CRITERIA.md) |
| 시스템 설계 | [시스템 개요](docs/architecture/SYSTEM_OVERVIEW.md), [파이프라인](docs/architecture/PIPELINE.md), [데이터 계약](docs/architecture/DATA_CONTRACTS.md) |
| 정책·권리 | [YouTube 및 수익화](docs/policy/YOUTUBE_MONETIZATION.md), [음악 권리와 provenance](docs/policy/AI_MUSIC_RIGHTS.md) |
| 안전 운영 | [Content ID 대응](docs/policy/CONTENT_ID.md), [AI 공개](docs/policy/AI_DISCLOSURE.md), [보안](docs/policy/SECURITY.md) |
| 실행·배포 | [로컬 개발](docs/operations/LOCAL_DEVELOPMENT.md), [운영 런북](docs/operations/RUNBOOK.md), [업로드와 스케줄링](docs/operations/UPLOAD_SCHEDULING.md) |
| 개선 루프 | [Analytics 피드백](docs/operations/ANALYTICS_FEEDBACK.md) |
| 개발 순서 | [Phase 0~9](docs/roadmap/PHASES.md) |

## 명령어 계약

```bash
python main.py doctor
python main.py generate
python main.py generate --seed 42 --duration-minutes 60
python main.py inspect <run_id>
python main.py upload <run_id> --privacy private
python main.py schedule <run_id> --publish-at 2026-10-01T21:00:00+09:00
python main.py analytics sync
python main.py feedback build
```

`doctor`, `generate`, `inspect`가 구현되어 있다. `upload`, `schedule`, `analytics`, `feedback`은 도움말에만 있으며 실행하면 실패 코드 1을 반환한다.

## 비목표

- 검토 없이 대량 공개하는 시스템
- 다른 아티스트, 채널, 캐릭터 또는 브랜드를 모방하는 생성
- 권리 근거가 불명확한 음악·이미지의 사용
- Content ID 자동 이의제기 또는 허위 권리 주장
- 조회수·구독·댓글 조작
- 수익화 승인을 보장하는 기능

## 상태

현재 **Phase 0 기반 + Phase 1 오프라인 구현**을 포함한다. 네트워크 차단 환경에서 60분 인수 테스트를 3회 연속 통과했다.
상세 결과는 [검증 보고서](verification/REPORT.md), 다음 작업은 [다음 작업](docs/roadmap/NEXT_TASK.md)을 확인한다.
Phase 2 준비로 [음악 API 후보 비교](docs/roadmap/MUSIC_PROVIDER_COMPARISON.md)를 작성했다.
첫 기술 평가 후보는 Stable Audio 3.0이며 서비스·예산·권리 승인과 실제 API 연결은 아직이다.
[오프라인 음악 job 계약](docs/architecture/MUSIC_JOBS.md)의 fake adapter와 재시도·비용 한도 테스트도
추가했다. 이 모듈은 기존 generate와 분리되어 있으며 외부 서비스를 호출하지 않는다.

2026-09-28 macOS에서도 1분 생성·inspect·resume와 일반 테스트 48개를 통과했다.
환경과 측정 결과는 [맥북 검증 보고서](verification/MACOS_REPORT.md)를 확인한다.
이어 60분 smoke를 포함한 전체 테스트 49개도 통과했다(205초).
60분 영상 전체 디코딩, A/V 차이 0초, -14 LUFS, 완료 run 재개를 확인했다.

[구현 결정과 한계](docs/architecture/DECISIONS.md)를 먼저 확인한다. 테스트 음원은 상업용 생성물이 아니며 업로드가 차단되어 있다. 실제 음악 API는 아직 연결하지 않았다.



## 지금 실행하기

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
python main.py doctor
python main.py generate
```

macOS에서 FFmpeg가 없다면 `brew install ffmpeg`를 먼저 실행한다.
API 키나 유료 계정은 필요 없다. `.env`는 자동으로 읽으며 동일 환경 변수는 shell 값이 우선한다.
기본값은 seed 42, 60분, 8트랙, 1280×720 정지 테스트 카드(1 fps), stereo 48 kHz다.
`--min-tracks 10` 또는 `MIN_TRACK_COUNT=10`으로 최소 트랙 수를 지정할 수 있다.
음악 provider의 길이 상한에 따라 최대 12개까지 늘리며, 불가능한 구성은 생성 전에 중단한다.
crossfade 기본값은 `CROSSFADE_SECONDS=2`이며 계획·master·chapter에 같은 값을 적용한다.
run당 중간 파일 약 2.2 GB 이상과 완성 MP4가 필요하며 여유 공간 10 GB를 권장한다.

빠른 확인과 실패 재개:

```bash
python main.py generate --duration-minutes 1 --run-id quick-test
python main.py generate --duration-minutes 1 --min-tracks 10 --run-id ten-tracks
python main.py inspect quick-test
python main.py generate --duration-minutes 1 --run-id recovery-test --fail-stage render
# 위 명령은 의도적으로 실패한다.
python main.py generate --run-id recovery-test --resume
```

완료 run에 `--resume`하면 파일 검증만 하고 반환한다. 같은 run ID로 새 생성을 시도하거나
완료 파일이 변조되면 중단한다. `--resume`에는 저장된 seed/길이가 기본 적용된다.
검증 코드가 변경된 경우 새 run을 만든다.

```bash
python -m pytest                         # 빠른 계약·복구 테스트
python -m pytest -m smoke                # 60분 E2E
python -m ruff check .
python scripts/scan_secrets.py
python scripts/scan_secrets.py --staged    # 커밋할 모든 텍스트 검사
# Linux + libseccomp: FFmpeg까지 네트워크 차단, 전체 테스트 실행
python scripts/offline_check.py --basetemp /tmp/bgm-acceptance-new
```

`--basetemp`에는 테스트 전용 새 디렉터리를 사용한다. pytest가 기존 basetemp를 정리할 수 있다.

## 검증 범위

성공 상태는 로컬 테스트 결과에 대한 `ready_for_review`다. `rights.status=blocked`,
`upload_eligible=false`이며 실제 보컬·유사도 검사는 아직 없다. 더미 QC 보고서에 미검사 항목을 표시한다.
스키마 파일은 `src/ai_bgm_factory/schemas/`, migration은 `src/ai_bgm_factory/migrations/`에 있다.
