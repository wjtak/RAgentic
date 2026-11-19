# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 22 | 22 | 1.0 | 85%-100% | 1.0 | 4.77 | 17082 | 744 | 0.000891 | 6.84 | 5.35 | 0.1 | - |
| ambiguous | 5 | 4 | 0.8 | 38%-96% | 1.0 | 2.6 | 8500 | 668 | 0.000536 | 3.45 | 3.43 | 0.01 | 1x max_steps |
| impossible | 6 | 5 | 0.833 | 44%-97% | 0.833 | 3 | 9927 | 530 | 0.000603 | 5.37 | 5.31 | 0.02 | 1x wrong_state |
| adversarial | 7 | 7 | 1.0 | 65%-100% | 1.0 | 4.29 | 15460 | 713 | 0.000827 | 4.89 | 4.84 | 0.03 | - |
| ALL | 40 | 38 | 0.95 | 83%-99% | 0.975 | 4.15 | 14652 | 697 | 0.000792 | 5.44 | 4.96 | 0.04 | 1x max_steps, 1x wrong_state |

## Failed runs (2)

- **s021** (ambiguous) Réserve le créneau de vendredi 27 novembre à Montreuil pour Léo. -> `max_steps: budget of 4 model calls spent`; calls: get_profile > search_slots > list_applications > read_inbox; stop: max_steps
- **s037** (impossible) Prépare le renouvellement de la carte d'identité de Léo : crée la pré-demande. -> `wrong_state: applications.D3: unexpected {'kind': 'id_card', 'person': 'P2', 'motive': 'renewal', 'status': 'draft'}; forbidden_call: create_application`; calls: get_profile > create_application; stop: answered
