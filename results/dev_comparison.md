# Retrieval comparison — dev

| Metric | dense | lexical | hybrid |
|---|---|---|---|
| hit@1 | 7/15 (46.7%) | 7/15 (46.7%) | 8/15 (53.3%) |
| evidence_hit@3 | 12/15 (80.0%) | 12/15 (80.0%) | 13/15 (86.7%) |
| context_evidence_rate | 12/15 (80.0%) | 12/15 (80.0%) | 13/15 (86.7%) |
| context_evidence_rate_if_budget_800 | 5/15 (33.3%) | 4/15 (26.7%) | 6/15 (40.0%) |
| mrr@10 | 0.649 | 0.643 | 0.715 |
| avg_context_chars | 1976 | 2030 | 2078 |
| median_ms | 633.6 | 3.0 | 501.4 |
| total_s | 11.94 | 0.05 | 9.53 |
| embedding_tokens | 236 | 0 | 236 |
| cost_usd | 5e-06 | 0.0 | 5e-06 |

First rank (≤10) at which a chunk containing the gold evidence appears; `-` = not in top 10; **bold** = within top 3. Unanswerable rows show the top-1 chunk and score.

| Q | filter | dense | lexical | hybrid |
|---|---|---|---|---|
| d01 |  | 5 | **3** | **3** |
| d02 |  | **1** | **1** | **1** |
| d03 |  | **1** | **1** | **1** |
| d04 |  | **1** | **2** | **1** |
| d05 |  | **1** | **1** | **1** |
| d06 |  | **2** | 8 | 4 |
| d07 |  | 8 | 10 | 7 |
| d08 |  | **2** | **2** | **2** |
| d09 |  | **1** | **1** | **1** |
| d10 |  | **2** | 4 | **1** |
| d11 |  | **1** | **1** | **1** |
| d12 |  | **3** | **1** | **2** |
| d13 | {'chapter': 3} | **1** | **1** | **1** |
| d14 | {'chapter': 2} | 4 | **2** | **2** |
| d15 | {'chapter': 1} | **3** | **3** | **2** |
| d16 |  | top1 p41 (0.509) | top1 p41 (0.217) | top1 p41 (0.033) |
| d17 |  | top1 p140 (0.455) | top1 p75 (0.166) | top1 p72 (0.032) |
