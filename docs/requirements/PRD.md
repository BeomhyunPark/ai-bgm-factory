# 제품 요구사항 문서(PRD)

- 상태: Normative
- 대상 릴리스: Phase 1 MVP → Phase 9 운영 자동화
- 문서 언어: 설명은 한국어, code/command/identifier는 영어

## 1. 제품 비전

`AI BGM Factory`는 고유한 상황·정서·청취 목적을 가진 60분 무보컬 BGM 영상을 반복 가능하게 제작한다. 사람은 채널 전략, 정책, 공개 승인에 집중하고, 시스템은 생성·검수·기록·렌더링·비공개 업로드·데이터 수집을 담당한다.

## 2. 해결하려는 문제

- 여러 AI/미디어 도구 사이의 수작업 전달이 느리고 오류가 많다.
- 음악과 이미지의 상업 이용 근거가 실행 후 흩어진다.
- 보컬, clipping, 긴 silence, 음량 편차 같은 오류를 수동 청취만으로 찾기 어렵다.
- 자동화가 강해질수록 영상이 서로 비슷해져 YouTube의 반복·대량생산형 콘텐츠 위험이 커진다.
- Content ID claim 발생 시 어떤 모델과 라이선스로 만든 파일인지 즉시 입증하기 어렵다.
- 제목/썸네일 최적화가 실제 영상 내용과 분리되어 과장되기 쉽다.

## 3. 목표 사용자

- 1차: AI만으로 개발·운영하되 최종 공개 책임을 직접 지는 1인 채널 운영자
- 2차: 생성 provider나 채널 콘셉트를 교체해 같은 파이프라인을 운영하는 소규모 팀

## 4. 사용자 가치

- 한 명령으로 배포 전 완성 패키지를 얻는다.
- 각 산출물의 생성 근거와 변환 이력을 감사할 수 있다.
- 위험한 결과를 게시 전에 자동 차단한다.
- Analytics를 조회수 최대화가 아니라 만족도·유지율·재방문 개선 신호로 활용한다.

## 5. 제품 범위

### 포함

1. 콘셉트 및 creative brief 생성
2. instrumental track 8~12개 생성
3. 오디오 QC와 normalize/crossfade
4. prompt, model, seed, license, response, hash provenance
5. 배경 이미지와 썸네일 생성
6. 미세 motion을 포함한 60분 FFmpeg render
7. 제목, 설명, chapter/tracklist, tag 생성 및 검증
8. YouTube `private` upload
9. 승인된 영상의 예약 공개
10. YouTube Analytics 수집과 다음 기획 입력 생성
11. SQLite 기반 실행·asset·policy decision 이력

### 제외

- 사람 승인 없는 자동 공개
- 권리 판단의 법적 보증
- Content ID 자동 등록/자동 이의제기
- 음원 유통사 배포
- 보컬·음성 복제
- 실존 인물의 사실적 합성
- 조회수 또는 engagement 조작

## 6. 핵심 시나리오

### S1. 로컬 생성

운영자가 `python main.py generate`를 실행한다. 시스템은 새 `run_id`를 만들고, 60분 영상과 썸네일·메타데이터·provenance를 생성한다. 모든 gate가 통과되어야 상태가 `ready_for_review`가 된다.

### S2. 비공개 업로드

운영자가 검토 완료 후 `python main.py upload <run_id> --privacy private`를 실행한다. 시스템은 정확한 파일 hash를 확인하고 private로 업로드한 뒤 YouTube video ID를 기록한다.

### S3. 예약 공개

운영자가 YouTube private 처리 결과, 저작권 검사, metadata, disclosure, thumbnail을 확인하고 승인한다. 그 후에만 미래 `publishAt`을 설정할 수 있다.

### S4. 피드백

시스템은 승인된 channel scope로 Analytics를 동기화하고, 최소 샘플과 관찰 기간을 충족한 데이터만 다음 experiment backlog에 반영한다.

## 7. 성공 기준

### Phase 1 기술 성공

- clean environment에서 dummy E2E가 한 명령으로 성공한다.
- `final.mp4` duration은 3600초 ± 1초다.
- 필수 5개 산출물이 schema validation을 통과한다.
- 같은 seed/config는 동일한 metadata와 provenance 입력을 재현한다.
- 외부 API나 YouTube 계정 없이 테스트할 수 있다.

### 운영 성공

- 생성 run의 95% 이상이 수동 파일 복구 없이 종료된다.
- 공개 영상 100%에 검증 가능한 rights/provenance record가 있다.
- 공개 영상 100%가 private staging과 사람 승인 단계를 거친다.
- Content ID claim 대응 자료를 15분 이내에 모을 수 있다.
- 동일 템플릿 반복 위험을 측정하고 임계치 초과 후보를 차단한다.

### 콘텐츠 성공

단일 vanity metric을 최적화하지 않는다. 아래를 cohort/콘셉트별로 함께 본다.

- `averageViewDuration`
- `estimatedMinutesWatched`
- 초반 및 구간별 retention
- returning viewer에 대응 가능한 가용 지표
- subscriber gain/loss
- impressions CTR(가용한 표면에서)
- comments/likes보다 먼저 claim, 정책 경고, negative feedback

## 8. 제품 원칙

- **Private first**: 공개는 생성의 부수 효과가 아니다.
- **Evidence first**: “AI가 만들었다”가 아니라 “어떤 권리로 사용 가능한가”를 기록한다.
- **Quality gates**: 실패한 asset은 자동으로 다음 단계에 흐르지 않는다.
- **Originality by design**: 영상마다 creative brief와 구조적 차이를 만든다.
- **Provider portability**: provider 변경이 domain logic 변경이 되지 않게 한다.
- **Human accountability**: 자동화가 최종 게시 책임을 대체하지 않는다.
- **Reproducibility**: 동일 실행을 설명하고 감사할 수 있어야 한다.

## 9. 출시 조건

Phase 7 전에는 실제 YouTube upload를 활성화하지 않는다. Phase 8 전에는 예약 공개를 활성화하지 않는다. 공개 허용 전 최소 10개의 private pilot을 만들어 품질, 권리, 중복도, Content ID 결과를 수동 검토한다.
