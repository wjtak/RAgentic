# Model comparison, same scenarios

| model | kind | runs | pass_rate | ci95 | mean_steps | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median |
|---|---|---|---|---|---|---|---|---|---|
| deepseek/deepseek-v4.1-flash | normal | 19 | 0.947 | 75%-99% | 4.95 | 0.001282 | 6.63 | - | - |
| deepseek/deepseek-v4.1-flash | ambiguous | 5 | 0.8 | 38%-96% | 2.6 | 0.000642 | 4.07 | - | - |
| deepseek/deepseek-v4.1-flash | impossible | 5 | 1.0 | 57%-100% | 3 | 0.000529 | 6.12 | - | - |
| deepseek/deepseek-v4.1-flash | adversarial | 6 | 0.833 | 44%-97% | 4.17 | 0.000763 | 7.34 | - | - |
| deepseek/deepseek-v4.1-flash | ALL | 35 | 0.914 | 78%-97% | 4.2 | 0.000994 | 6.58 | - | - |
| google/gemini-2.5-flash | normal | 19 | 0.947 | 75%-99% | 4.58 | 0.002307 | 3.64 | 3.37 | 0.09 |
| google/gemini-2.5-flash | ambiguous | 5 | 0.6 | 23%-88% | 2.6 | 0.001117 | 1.98 | 1.91 | 0.03 |
| google/gemini-2.5-flash | impossible | 5 | 1.0 | 57%-100% | 2.2 | 0.000964 | 1.62 | 1.57 | 0.02 |
| google/gemini-2.5-flash | adversarial | 6 | 0.833 | 44%-97% | 3.67 | 0.001435 | 3.04 | 2.93 | 0.06 |
| google/gemini-2.5-flash | ALL | 35 | 0.886 | 74%-95% | 3.8 | 0.001796 | 3.22 | 3.12 | 0.05 |
