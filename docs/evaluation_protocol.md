# Evaluation Protocol

## Task Families

1. Long-context retrieval
   - Find a value or date in a long announcement bundle.
   - Measure exact match and evidence recall.

2. Table reasoning
   - Filter, compare, aggregate, and rank rows from public housing price or sale-history tables.
   - Measure exact numeric accuracy and execution-validity.

3. Cross-document reasoning
   - Combine an announcement, housing rule, and public-data table.
   - Measure answer accuracy, evidence completeness, and faithfulness.

4. Answerability detection
   - Ask questions whose required source is absent.
   - Measure abstention accuracy and false-answer rate.

5. RAG vs full-context
   - Compare the same questions under full-context, retrieval, and hybrid pipelines.
   - Measure accuracy, cost, latency, and evidence quality.

## Suggested Context Tiers

- 32K tokens
- 64K tokens
- 128K tokens
- 256K tokens
- 512K tokens

Use licensed public distractor documents to scale context length. Keep the answer evidence position controlled: early, middle, late, and multi-position.

## Systems to Compare

- Full-context prompting
- BM25 RAG
- Dense-vector RAG
- Hybrid RAG
- Hierarchical RAG
- Table/tool pipeline
- Full-context plus retrieved evidence

## Metrics

- Exact Match for short factual answers
- Numeric exact match with tolerance for calculated values
- Macro accuracy by task family
- Evidence recall
- Answerability F1
- Cost per correct answer
- Latency per correct answer

## Required Ablations

- Context length scaling
- Evidence position sensitivity
- With and without table tools
- With and without retrieved evidence
- Answerable vs unanswerable split
- Korean-only vs translated prompt instructions

## Reporting Standard

A paper should report:

- Source-license table
- Annotation pipeline
- Inter-annotator or deterministic-verifier agreement
- Main model results
- RAG vs full-context comparison
- Cost/latency analysis
- Failure taxonomy

