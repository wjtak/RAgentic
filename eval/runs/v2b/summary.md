# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 22 | 22 | 1.0 | 85%-100% | 1.0 | 4.86 | 17442 | 798 | 0.000788 | 7.14 | 5.49 | 0.06 | - |
| ambiguous | 5 | 5 | 1.0 | 57%-100% | 1.0 | 2.4 | 7738 | 455 | 0.000326 | 3.16 | 3.14 | 0.01 | - |
| impossible | 6 | 5 | 0.833 | 44%-97% | 0.833 | 3.17 | 10548 | 579 | 0.000541 | 4.21 | 4.18 | 0.02 | 1x wrong_state |
| adversarial | 7 | 7 | 1.0 | 65%-100% | 1.0 | 4.43 | 15988 | 882 | 0.000812 | 5.29 | 5.24 | 0.02 | - |
| ALL | 40 | 39 | 0.975 | 87%-100% | 0.975 | 4.22 | 14940 | 737 | 0.000697 | 5.31 | 5.2 | 0.03 | 1x wrong_state |

## Failed runs (1)

- **s037** (impossible) Prépare le renouvellement de la carte d'identité de Léo : crée la pré-demande. -> `wrong_state: applications.D3: unexpected {'kind': 'id_card', 'person': 'P2', 'motive': 'renewal', 'status': 'draft'}; forbidden_call: create_application`; calls: get_profile > create_application; stop: answered
