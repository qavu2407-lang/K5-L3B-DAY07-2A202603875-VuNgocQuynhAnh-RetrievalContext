# Agent comparison — dev

| | A0 | A1 | I1 | I2 | I3 |
|---|---|---|---|---|---|
| retriever | dense | hybrid | hybrid | hybrid | hybrid |
| budget | 3200 | 3200 | 3200 | 9600 | 9600 |
| distinct_queries | False | False | True | True | True |
| repeated_queries | 15 | 9 | 0 | 0 | 0 |
| chunks_added_by_later_searches | 1 | 2 | 3 | 5 | 30 |
| agent_CER | 11/15 | 14/15 | 14/15 | 14/15 | 15/15 |
| missing_gold_in_context | ['d01', 'd07', 'd10', 'd14'] | ['d07'] | ['d07'] | ['d07'] | [] |
| searches | {'1': 8, '3': 9} | {'1': 9, '2': 1, '3': 7} | {'1': 11, '2': 3, '3': 3} | {'1': 11, '2': 2, '3': 4} | {'1': 11, '2': 2, '3': 4} |
| model_calls | 52 | 49 | 50 | 51 | 50 |
| repairs | 0 | 0 | 7 | 7 | 6 |
| cost_usd | 0.019051 | 0.017714 | 0.018522 | 0.019258 | 0.021565 |
| cost_per_q | 0.00112 | 0.00104 | 0.00109 | 0.00113 | 0.00127 |
| median_s | 5.05 | 3.69 | 4.0 | 3.92 | 3.92 |
| errors | 0 | 0 | 0 | 0 | 0 |
| grounded_0/1/2 | 2/3/10 | 0/1/14 | 0/1/14 | 0/1/14 | 0/1/14 |
| grounded_mean | 1.53 | 1.93 | 1.93 | 1.93 | 1.93 |
| citation_valid | 22/24 | 24/24 | 21/22 | 24/24 | 26/26 |
| abstention | 2/2 | 2/2 | 2/2 | 2/2 | 2/2 |
| false_abstention | 1/15 | 0/15 | 0/15 | 0/15 | 0/15 |
