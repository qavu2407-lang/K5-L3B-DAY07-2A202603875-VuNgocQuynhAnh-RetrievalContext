# Agent comparison — test

| | A0 | I3 |
|---|---|---|
| retriever | dense | hybrid |
| budget | 3200 | 9600 |
| distinct_queries | False | True |
| repeated_queries | 4 | 0 |
| chunks_added_by_later_searches | 3 | 15 |
| agent_CER | 4/5 | 5/5 |
| missing_gold_in_context | ['t04'] | [] |
| searches | {'1': 4, '3': 3} | {'1': 4, '2': 1, '3': 2} |
| model_calls | 22 | 23 |
| repairs | 2 | 4 |
| cost_usd | 0.008371 | 0.009662 |
| cost_per_q | 0.0012 | 0.00138 |
| median_s | 5.32 | 4.36 |
| errors | 0 | 0 |
| grounded_0/1/2 | 0/2/3 | 0/1/4 |
| grounded_mean | 1.6 | 1.8 |
| citation_valid | 8/8 | 7/7 |
| abstention | 2/2 | 2/2 |
| false_abstention | 0/5 | 0/5 |
