> **산출물 E**: 기업 보강 JSONL -> GCS -> PubSub 자동 트리거
> 

---

## 4-1. 홈페이지/뉴스 크롤링 파이프라인 (2주, W24-25)

> 기업 인텔리전스 기본 데이터 수집 (product, funding, growth_signals)
> 

---

## 4-2. 기업 보강 데이터 JSON 생성

```json
{
  "org_id": "ORG_samsung",
  "product": ["갤럭시", "엑시노스"],
  "funding": null,
  "growth_signals": ["반도체 투자 확대"],
  "source": "homepage_crawl",
  "crawled_at": "2026-06-01T09:00:00Z"
}
```

---

## 산출물 E

W24~25:

[] 기업 보강 JSONL -> GCS gs://kg-artifacts/company_enrichment/batch_{id}.jsonl

[] PubSub kg-artifact-ready 자동 발행 (artifact_type: “company_enrichment”)

## W26-27: 품질 체크

[] schema 준수율 >95% 최종 확인

[] 필드 완성도 >90% 최종 확인

[] PII 누출율 <0.01% 최종 확인

[] 통계적 샘플링 384건 최종 리포트

[] S&F 파이프라인 Runbook 문서