# macOS 설치·1분 생성 검증

- 검증일: 2026-09-28 (Asia/Seoul)
- 환경: macOS 27.0 arm64, Python 3.12.14, FFmpeg/ffprobe 9.0.2
- 설치: Homebrew Python/FFmpeg, 프로젝트 `.venv`, `pip install -e '.[dev]'`
- 주요 의존성: NumPy 2.5.3, Pillow 12.3.0, jsonschema 4.26.0,
  pytest 9.1.1, Ruff 0.16.9. `pip check` 통과.
- API 키 없이 기본 dummy 설정 사용. `.env` 권한은 600이며 Git에서 제외.

## 결과

| 검증 | 결과 | 증거 |
|---|---|---|
| doctor | 필수 항목 통과 | [JSON](macos-doctor.json) |
| 일반 테스트 | 48 passed, 60분 smoke 1개 제외 | [로그](macos-tests.log) |
| Ruff | 통과 | [로그](macos-lint.log) |
| 1분 생성 | 10단계 성공, ready_for_review | [로그](macos-generate.log) |
| inspect | 모든 등록 파일의 크기·해시 검증 통과 | [JSON](macos-inspect.json) |
| 완료 run resume | 성공 | [JSON](macos-resume.json) |

실행 명령:

```bash
source .venv/bin/activate
python main.py doctor
python -m pytest
python -m ruff check .
python main.py generate --duration-minutes 1 --run-id macbook-verified-20260928
python main.py inspect macbook-verified-20260928
python main.py generate --run-id macbook-verified-20260928 --resume
python scripts/scan_secrets.py
python scripts/scan_secrets.py --staged
```

영상·오디오 측정과 필수 5개 산출물의 SHA-256은
[macos-measurements.json](macos-measurements.json)에 기록했다.
영상은 `data/runs/macbook-verified-20260928/final.mp4`에 로컬 보관한다.

## 호환성 수정

첫 실행은 audio_master에서 실패했다. FFmpeg 9가 loudnorm JSON 뒤에
통계 로그를 출력해 `json.loads`가 Extra data 오류를 냈다.
JSON 객체만 파싱하고 필수 측정값이 유한한 숫자인지 확인하도록 수정했다.
후행 로그와 잘못된 JSON/측정값에 대한 회귀 테스트 4개를 추가했다.
기존 loudness/true-peak 기준은 유지했다. 실패 run은 로컬에 보존하고
수정된 코드로 새 run ID를 생성했다.

## 공개 범위와 한계

소스·문서·테스트·텍스트 검증 증거를 공개한다. 커밋 전에 소스와 스테이징된
모든 파일을 비밀정보 패턴으로 검사한다. 패턴 검사는 모든 형태의 비밀정보 탐지를
보장하지 않는다. `.env`, 인증 파일, 음원·영상, sample/, data/, 캐시와 가상환경은 제외한다.

이 검증은 1분 실행이다. macOS에서 60분 인수 테스트 3회를 재실행하거나
Linux libseccomp 네트워크 차단을 재현한 것은 아니다. 기존 Linux 보고서의
commit ID는 전달받은 원본 검증 이력을 가리키며 이 새 저장소의 commit ID와 다르다.
현재 구현은 Phase 0·1이며 rights_status=blocked, upload_eligible=false다.
실제 provider, 보컬·유사도 검사, YouTube 업로드는 구현되지 않았다.
데이터 계약 변경이 없어 schema version 1.0.0과 `.env.example`은 유지한다.
