# 데이터 계약

- 상태: Phase 1 구현 스키마 + 향후 production 예시
- 형식: JSON, UTF-8, ISO 8601 timestamp, SHA-256

모든 JSON에는 `schema_version`을 둔다. 아래 예시는 최소 계약이며 구현 시 JSON Schema 파일로 분리한다.

Phase 2 준비용 성공 job receipt는 별도 `music_job.schema.json` 1.0.0을 사용한다.
전용 SQLite ledger는 user_version 2이며 [음악 job 계약](MUSIC_JOBS.md)을 따른다.
HTTP 응답의 allowlist evidence는 `music_http_evidence.schema.json` 1.0.0을 사용한다.
기존 Phase 1 산출물의 schema version은 유지한다.

길이 계획은 `track_plan.schema.json` **1.0.0**으로 검증한다. 정수 프레임으로 target,
crossfade, source 길이와 시작 위치를 기록한다. config snapshot은 **1.1.0**으로 갱신하여
`track_count`를 `min_track_count`로 교체하고 `crossfade_seconds`를 추가했다.
pipeline snapshot에는 providers와 track_plan도 포함한다. manifest 외형 및 metadata/provenance/QC는
1.0.0을 유지한다. 이전 구현의 완료 파일은 그대로 보존하고 새 코드는 implementation hash가
다른 run의 재개를 거부한다. 기존 파일을 자동 변환하거나 덮어쓰지 않는다.

## `manifest.json`

```json
{
  "schema_version": "1.0.0",
  "run_id": "01J...",
  "status": "ready_for_review",
  "created_at": "2026-09-27T12:00:00+09:00",
  "updated_at": "2026-09-27T13:20:00+09:00",
  "seed": 42,
  "config_hash": "sha256:...",
  "stages": [
    {
      "name": "render",
      "status": "succeeded",
      "attempt": 1,
      "started_at": "...",
      "finished_at": "...",
      "input_hash": "sha256:..."
    }
  ],
  "artifacts": [
    {
      "role": "final_video",
      "path": "final.mp4",
      "sha256": "...",
      "bytes": 123456
    }
  ],
  "publication": {
    "privacy_status": "private",
    "approval_required": true
  }
}
```

## `metadata.json`

```json
{
  "schema_version": "1.0.0",
  "title": "Rainy Deploy Night — Minimal Electronic for Deep Work",
  "description": "...",
  "tags": ["deep work", "instrumental"],
  "category_id": "10",
  "default_language": "ko",
  "privacy_status": "private",
  "contains_synthetic_media": true,
  "made_for_kids": false,
  "chapters": [
    {"start_seconds": 0, "timestamp": "00:00", "title": "Cold Start"}
  ],
  "disclosure_note": "Music and visuals were created with generative AI and curated through an automated quality pipeline.",
  "creative_distinctiveness": {
    "concept_id": "...",
    "novelty_anchors": ["..."],
    "similarity_score": 0.31
  }
}
```

`made_for_kids`는 모델 추정에 맡기지 않는다. 채널 정책의 명시적 설정으로 관리한다.

## `provenance.json`

```json
{
  "schema_version": "1.0.0",
  "run_id": "01J...",
  "created_at": "...",
  "code": {
    "git_commit": "...",
    "dirty": false,
    "pipeline_version": "0.1.0"
  },
  "inputs": {
    "concept_hash": "sha256:...",
    "prompt_template_versions": {"music": "1.0.0", "visual": "1.0.0"}
  },
  "assets": [
    {
      "asset_id": "track-01-attempt-01",
      "kind": "audio",
      "provider": "provider_name",
      "model": "model_name",
      "model_version": "provider-reported-or-unknown",
      "request_id": "provider-request-id",
      "prompt": "instrumental only ...",
      "negative_prompt": "vocals, spoken words ...",
      "seed": 42,
      "generated_at": "...",
      "source_sha256": "...",
      "raw_response_path": "raw/provider/...json",
      "qc_report_path": "qc/track-01.json"
    }
  ],
  "rights": {
    "status": "verified_for_intended_use",
    "intended_use": ["youtube_upload", "commercial_monetization"],
    "account_tier": "...",
    "terms_url": "https://...",
    "terms_reviewed_at": "...",
    "terms_snapshot_sha256": "...",
    "evidence_paths": ["evidence/..."],
    "restrictions": ["no_content_id_registration"]
  },
  "transforms": [
    {
      "tool": "ffmpeg",
      "version": "...",
      "operation": "loudness_normalization",
      "input_sha256": ["..."],
      "output_sha256": "...",
      "parameters": {"target_lufs": -14.0, "max_true_peak_dbtp": -1.0}
    }
  ],
  "final_artifacts": [
    {"path": "final.mp4", "sha256": "..."}
  ]
}
```

`rights.status` 허용값:

- `unverified`: 아직 검토하지 않음
- `verified_for_intended_use`: 계획된 사용 범위에 대한 근거 존재
- `restricted`: 일부 사용 금지
- `expired`: 생성 당시 또는 현재 근거 만료/불명
- `blocked`: 사용 불가

## `qc/<track>.json`

```json
{
  "schema_version": "1.0.0",
  "asset_id": "track-01-attempt-01",
  "status": "passed",
  "measurements": {
    "duration_seconds": 312.4,
    "integrated_lufs": -16.3,
    "true_peak_dbtp": -1.8,
    "max_silence_seconds": 1.2,
    "vocal_probability": 0.04,
    "max_similarity": 0.41
  },
  "thresholds_version": "2026-09-27",
  "failures": []
}
```

## Approval record

```json
{
  "approval_id": "...",
  "run_id": "...",
  "artifact_hash": "sha256:...",
  "decision": "approved_for_schedule",
  "approved_by": "local-operator-id",
  "approved_at": "...",
  "checks": {
    "rights": true,
    "qc": true,
    "metadata": true,
    "disclosure": true,
    "platform_claims": true
  },
  "note": ""
}
```

승인 후 artifact나 metadata가 변경되면 승인 hash가 불일치하므로 재승인이 필요하다.



## Phase 1 실제 계약

위 production 예시는 미래 상태를 설명하는 참고 예시다. 현재 실행의 엄격한 JSON Schema는
`src/ai_bgm_factory/schemas/`의 4개 파일이다. 생성/검증 코드가 같은 파일을 읽는다.
Phase 1의 manifest에는 config, implementation_sha256, review_scope와 publication.upload_eligible이
추가된다. rights는 blocked/test-only, metadata.similarity_score와 QC의 미검사 확률은 null이다.
시각·텍스트도 source asset으로 기록되며 모든 응답 파일과 실제 소스의 해시를 보존한다.
provider 약관 URL이 존재하지 않는 로컬 dummy는 terms_url=null이다. 실재 URL을 꾸며내지 않는다.
`final_artifacts`는 final.mp4/thumbnail/metadata를 가리킨다. provenance 자신의 해시는 manifest에
기록하며 manifest의 자기참조 해시는 만들지 않는다. 로그와 manifest는 변경되는 실행 기록이다.
