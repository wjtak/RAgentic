# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 22 | 21 | 0.955 | 78%-99% | 0.955 | 4.95 | 18662 | 859 | 0.001034 | 7.44 | 5.75 | 0.08 | 1x wrong_state |
| ambiguous | 5 | 5 | 1.0 | 57%-100% | 1.0 | 2.4 | 7913 | 591 | 0.000459 | 2.44 | 2.41 | 0.01 | - |
| impossible | 6 | 6 | 1.0 | 61%-100% | 1.0 | 3.33 | 11876 | 723 | 0.000698 | 5.78 | 5.73 | 0.02 | - |
| adversarial | 7 | 7 | 1.0 | 65%-100% | 1.0 | 4.43 | 17086 | 831 | 0.000744 | 5.36 | 5.3 | 0.03 | - |
| ALL | 40 | 39 | 0.975 | 87%-100% | 0.975 | 4.3 | 16025 | 800 | 0.000861 | 6.16 | 5.26 | 0.03 | 1x wrong_state |

## Failed runs (1)

- **s009** (normal) Pour le renouvellement de mon passeport : achète le timbre, envoie ma pré-demande et prends le premier créneau libre à la mairie du 11e. -> `wrong_state: applications.D1.status: expected submitted, got draft; applications.D3: unexpected {'kind': 'passport', 'person': 'P1', 'motive': 'renewal', 'status': 'submitted'}; forbidden_call: create_application`; calls: get_profile > stamp_price > get_wallet > buy_tax_stamp > create_application > submit_application > search_slots > book_appointment; stop: answered
