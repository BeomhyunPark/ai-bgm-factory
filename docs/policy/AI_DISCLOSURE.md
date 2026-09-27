# AI 생성 콘텐츠 공개(disclosure) 정책

- 상태: Policy / Operational
- 최종 검토일: 2026-09-27

## 내부 기본값

이 채널은 음악과 이미지에 생성 AI를 사용했다는 사실을 description에 명확하고 짧게 알린다. YouTube의 공식 altered/synthetic disclosure가 요구되는 경우 API/Studio 설정도 함께 사용한다.

YouTube는 사실적인 altered/synthetic content에 대한 공개 수단을 제공하며, Data API의 `status.containsSyntheticMedia`로 realistic altered or synthetic content 포함 여부를 표시할 수 있다. [YouTube video resource](https://developers.google.com/youtube/v3/docs/videos) [How this content was made disclosures](https://support.google.com/youtube/answer/15447836)

## 두 층의 disclosure

### 1. 플랫폼 필드

- `metadata.contains_synthetic_media`를 explicit boolean으로 저장한다.
- 사실적인 장소·사건·인물을 생성 또는 의미 있게 변경했다면 `true`를 원칙으로 한다.
- 모델이 독단으로 `false`를 선택하지 못한다.
- 업로드 시 지원되는 YouTube API field와 Studio 표시가 일치하는지 private 상태에서 확인한다.

### 2. 설명란 투명성

모든 영상 description에 다음 사실을 자연스럽게 공개한다.

```text
이 영상의 음악과 비주얼은 생성형 AI 도구로 제작하고, 자동 품질 검사와 사람의 공개 검토를 거쳤습니다.
```

영문 metadata를 쓸 때:

```text
Music and visuals were created with generative AI tools, then passed automated quality checks and human publishing review.
```

provider명을 공개해야 하는 라이선스라면 attribution 요구사항을 정확히 따른다.

## 판단표

| 콘텐츠 | description 고지 | `containsSyntheticMedia` 기본 |
|---|---:|---:|
| 비현실적 일러스트 + AI 음악 | 예 | 정책 검토 후 명시 값 |
| 실제처럼 보이는 존재하지 않는 도시/사건 | 예 | `true` |
| 실존 인물의 얼굴/목소리 합성 | 이 프로젝트에서 금지 | 해당 없음 |
| 단순 color correction/resize | 제작 전체가 AI면 예 | 일반적으로 해당 변경만으로는 별도 판단 |

플랫폼 기준은 변할 수 있으므로 ambiguous하면 숨기는 쪽이 아니라 공개하는 쪽으로 검토하되, 공식 필드의 정확한 의미를 왜곡하지 않는다.

## Provenance와 C2PA

provider가 C2PA/Content Credentials를 제공하면 변환 과정에서 가능한 한 유지하고 검증 결과를 provenance에 기록한다. YouTube가 valid Content Credentials의 생성 정보 표시를 이어받을 수 있으므로 로컬 metadata와 description이 모순되지 않아야 한다. [How this content was made disclosures](https://support.google.com/youtube/answer/15447836)

## 금지

- AI 사용을 숨기기 위해 metadata를 제거하는 변환
- `AI-free`, `human composed`, `live recorded` 같은 허위 표기
- 실제 사건·장소처럼 보이는 합성을 “ambience”라는 이유로 미공개 처리
- disclosure가 추천/수익화에 불리할 것이라는 추정만으로 필드를 끄는 행위
