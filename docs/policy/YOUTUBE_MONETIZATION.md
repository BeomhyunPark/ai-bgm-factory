# YouTube 게시 및 수익화 정책

- 상태: Policy / Operational
- 최종 검토일: 2026-09-27
- 주의: 플랫폼 정책은 변경될 수 있다. 아래 공식 링크를 배포 전 재확인한다.

## 결론

AI로 만들었다는 사실만으로 수익화가 자동 금지되거나 허용되는 것은 아니다. YouTube는 원본성, 진정성, 시청자 가치, 반복·대량생산 여부, 권리 보유 등을 본다. 이 프로젝트는 “서로 바꿔 끼워도 구분되지 않는 영상”을 빠르게 양산하지 않고, 각 영상에 구체적인 creative direction과 실질적 차이를 만드는 방식으로 운영한다.

YouTube는 2025년 `repetitious content` 명칭을 `inauthentic content`로 명확화했고, 반복적이거나 대량생산된 콘텐츠가 수익화 대상이 아니라는 취지를 공식 정책에 설명한다. 자동화 도구나 템플릿을 사용하더라도 최종 콘텐츠에는 창작적 비전과 실질적 가치가 드러나야 한다. [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392)

## 주요 위험

### 1. 영상 간 실질적 차이가 없음

배경색, 제목, track 순서만 바뀌고 음악·구조·경험이 사실상 같다면 `inauthentic content` 위험이 높다. 한 장의 유사 이미지와 반복 음원을 수십 편 생성하는 운영은 피한다.

### 2. 권리는 있어도 수익화는 별개

provider가 commercial use를 허용해도 YouTube가 채널을 original/authentic하다고 판단한다는 보장은 없다. 반대로 Content ID claim이 없다고 수익화 적합성이 증명되는 것도 아니다. YouTube는 상업적으로 사용할 모든 audio/visual element의 필요한 권리를 확보해야 한다고 설명한다. [What kind of content can I monetize?](https://support.google.com/youtube/answer/2490020)

### 3. Metadata가 실제 내용보다 앞섬

과장 title, 관련 없는 인기 keyword, 오해를 부르는 thumbnail은 사용하지 않는다. “집중력 10배”, “ADHD 치료”, “공식 사운드트랙”처럼 검증되지 않거나 혼동시키는 표현을 금지한다.

## 채널 고유성 설계

각 영상에는 다음 항목 중 최소 4개의 의미 있는 차이가 있어야 하며, 단순 랜덤값 변경은 차이로 보지 않는다.

- 구체적인 사용 상황과 청취자 문제
- 조성·화성·tempo curve·instrument palette
- track narrative와 energy progression
- sound texture/field ambience
- visual location, time, lighting, composition
- thumbnail information hierarchy
- track naming theme와 설명 문맥
- 실험 가설(예: BPM band와 early retention의 관계)

시리즈 정체성은 유지할 수 있지만, series template가 각 편의 substance를 대체하면 안 된다.

## 생성 전/후 originality gate

### 생성 전

- 최근 30개 영상의 concept fingerprint와 비교한다.
- 동일 use case + mood + genre + visual motif 조합의 반복 빈도를 제한한다.
- 특정 아티스트, 채널, 앨범, 캐릭터를 모방하는 문구를 거부한다.

### 생성 후

- audio embedding/fingerprint similarity
- image perceptual hash/embedding similarity
- title/description semantic similarity
- track structure와 duration pattern
- 사람이 확인하는 “이 영상만의 이유” 한 문장

자동 점수는 참고 신호이며 정책 판정의 대체물이 아니다.

## 게시 단계

1. `generate` 완료
2. 내부 quality/rights/originality gate
3. YouTube `private` upload
4. processing, platform copyright checks, metadata, disclosure 확인
5. human approval
6. future schedule 또는 수동 공개

YouTube Data API 문서에 따르면 unverified API project의 upload는 private로 제한될 수 있다. 이 프로젝트는 그 제약과 별개로 자체적으로도 private를 기본값으로 강제한다. [YouTube video resource](https://developers.google.com/youtube/v3/docs/videos)

## 운영 한도

- 초기 pilot: 주 1~2편, 최소 10편 private 검토
- production 초기: 공개 최대 주 2편
- upload/생성 수는 `.env`의 daily cap으로 제한
- 품질 또는 claim 비율이 악화되면 자동 scaling을 중단

일일 한도는 정책 준수를 보장하지 않는다. 콘텐츠의 substance가 우선이다.

## 기록할 정책 결정

- `creative_distinctiveness` 설명과 score
- 유사 비교 대상 run IDs
- 사용 권리 상태
- AI disclosure 결정과 이유
- made-for-kids 설정의 고정 근거
- human reviewer와 승인 시각
- YouTube processing/claim 상태
- 공개 시각과 metadata hash

## 금지 운영

- 여러 채널에 같은 파일 또는 미세 변형 파일 재업로드
- 조회수·댓글·좋아요 구매 또는 self-view automation
- 권리 불명 asset을 “일단 올리고 claim을 보자”는 방식
- 수익화 재신청을 위한 외형적 metadata 변경만 반복
- reviewer가 구분할 수 없는 template series의 대량 예약
- private 검사 결과를 기다리지 않은 즉시 공개

## 공식 참고 자료

- [YouTube channel monetization policies](https://support.google.com/youtube/answer/1311392)
- [What kind of content can I monetize?](https://support.google.com/youtube/answer/2490020)
- [YouTube Data API video resource](https://developers.google.com/youtube/v3/docs/videos)
- [Quota and compliance audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits)
