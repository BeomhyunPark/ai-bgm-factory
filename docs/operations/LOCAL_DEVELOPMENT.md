# 로컬 개발 가이드

- 상태: Operational / Phase 1 구현

## 사전 요구사항

- Python 3.12+
- FFmpeg와 ffprobe
- Git
- 충분한 disk space: 60분 중간 WAV와 MP4를 위해 run당 최소 10 GB 여유 권장

## 초기 설정

macOS에서는 `brew install python@3.12 ffmpeg`로 실행 도구를 설치한다.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e '.[dev]'
cp .env.example .env
python main.py doctor
```

1분 확인은 `python main.py generate --duration-minutes 1 --run-id quick-test`로 실행한다.
이미 완료된 ID는 새 생성에 재사용하지 않는다. 검증만 하려면
`python main.py generate --run-id quick-test --resume`를 실행한다.
FFmpeg 9의 loudnorm JSON 뒤 통계 로그도 지원한다.

doctor/generate/inspect는 구현되어 있다. 나머지 기능은 Phase별로 구현한다.

## 기본 개발 실행

```bash
pytest
python main.py generate --seed 42 --duration-minutes 60
python main.py inspect <run_id>
```

기본 설정에서 external provider와 YouTube 호출은 비활성화되어야 한다.

## 권장 repository layout

```text
.
├── README.md
├── AGENTS.md
├── CONTRIBUTING.md
├── .env.example
├── docs/
├── src/
├── tests/
├── prompts/
├── src/ai_bgm_factory/schemas/
├── src/ai_bgm_factory/migrations/
└── data/                 # ignored runtime data
```

## 테스트 media

- 저작권 불명 sample을 fixture로 넣지 않는다.
- test tone/noise/algorithmic pattern을 코드로 생성한다.
- fixture는 짧고 결정적이어야 한다.
- 60분 E2E는 별도 smoke marker로 분리한다.

```bash
pytest -m 'not smoke'
pytest -m smoke
```

## FFmpeg 확인

```bash
ffmpeg -version
ffprobe -version
```

container/codec 검증은 파일명 확장자만 보지 않고 ffprobe JSON을 사용한다.

## 데이터 디렉터리

```text
data/
├── app.db
├── runs/<run_id>/
├── cache/
├── analytics/
└── quarantine/
```

`quarantine/`은 rights/QC/policy 실패 asset을 게시 흐름에서 분리하기 위한 위치다. 실패 파일을 자동 삭제하지 않아 원인 분석을 가능하게 하되 retention policy를 적용한다.

## 실제 API를 켜기 전

- adapter contract test 통과
- sandbox 비용 상한 설정
- Terms/License evidence 검토
- raw response redaction test
- `.env`와 secret directory permission 확인
- upload flag는 계속 `false`

음악/이미지 API부터 단계적으로 켜고, YouTube upload는 Phase 7에서 별도 활성화한다.
