# Retrieval comparison — test

| Metric | dense | hybrid |
|---|---|---|
| hit@1 | 4/5 (80.0%) | 4/5 (80.0%) |
| evidence_hit@3 | 4/5 (80.0%) | 5/5 (100.0%) |
| context_evidence_rate | 4/5 (80.0%) | 5/5 (100.0%) |
| context_evidence_rate_if_budget_800 | 2/5 (40.0%) | 3/5 (60.0%) |
| mrr@10 | 0.85 | 0.9 |
| avg_context_chars | 2025 | 2159 |
| median_ms | 486.9 | 457.9 |
| total_s | 3.66 | 3.4 |
| embedding_tokens | 123 | 123 |
| cost_usd | 2e-06 | 2e-06 |

First rank (≤10) at which a chunk containing the gold evidence appears; `-` = not in top 10; **bold** = within top 3. Unanswerable rows show the top-1 chunk and score.

| Q | filter | dense | hybrid |
|---|---|---|---|
| t01 |  | **1** | **1** |
| t02 |  | **1** | **1** |
| t03 |  | **1** | **1** |
| t04 |  | 4 | **2** |
| t05 | {'chapter': 2} | **1** | **1** |
| t06 |  | top1 p76 (0.497) | top1 p76 (0.032) |
| t07 |  | top1 p140 (0.607) | top1 p140 (0.033) |
