# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 22 | 21 | 0.955 | 78%-99% | 0.955 | 4.91 | 18413 | 843 | 0.00149 | 5.49 | 4.78 | 0.09 | 1x max_steps |
| ambiguous | 5 | 4 | 0.8 | 38%-96% | 1.0 | 2.4 | 7907 | 706 | 0.000925 | 2.4 | 2.33 | 0.02 | 1x wrong_stop |
| impossible | 6 | 6 | 1.0 | 61%-100% | 1.0 | 3.17 | 11287 | 947 | 0.000863 | 4.37 | 4.33 | 0.04 | - |
| adversarial | 7 | 7 | 1.0 | 65%-100% | 1.0 | 4.29 | 15466 | 925 | 0.001041 | 5.83 | 5.75 | 0.04 | - |
| ALL | 40 | 38 | 0.95 | 83%-99% | 0.975 | 4.22 | 15515 | 856 | 0.001247 | 5.04 | 4.69 | 0.05 | 1x wrong_stop, 1x max_steps |

## Failed runs (2)

- **s018** (ambiguous) Prends un rendez-vous pour un passeport la semaine prochaine. -> `wrong_stop: expected asked_user, got answered`; calls: get_profile > search_slots; stop: answered
- **s036** (normal) Ma carte d'identité est abîmée : crée la pré-demande de renouvellement, et achète le timbre fiscal s'il en faut un. -> `max_steps: budget of 8 model calls spent; wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P1', 'motive': 'renewal', 'status': 'draft'})`; calls: get_profile > search_fiches > search_fiches > search_fiches > get_fiche > search_fiches > get_fiche > create_application; stop: max_steps
