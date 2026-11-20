# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 20 | 19 | 0.95 | 76%-99% | 0.95 | 4.35 | 15500 | 770 | 0.00087 | 7.14 | 6.16 | 0.05 | 1x wrong_state |
| ambiguous | 7 | 7 | 1.0 | 65%-100% | 1.0 | 2.43 | 7933 | 446 | 0.000407 | 3.77 | 3.71 | 0.02 | - |
| impossible | 6 | 6 | 1.0 | 61%-100% | 1.0 | 3.67 | 13236 | 1081 | 0.001193 | 6.28 | 6.22 | 0.03 | - |
| adversarial | 7 | 6 | 0.857 | 49%-97% | 0.857 | 4 | 14066 | 750 | 0.000756 | 6.01 | 5.93 | 0.05 | 1x wrong_state |
| ALL | 40 | 38 | 0.95 | 83%-99% | 0.95 | 3.85 | 13585 | 756 | 0.000818 | 5.91 | 5.62 | 0.03 | 2x wrong_state |

## Failed runs (2)

- **h001** (normal) Écris à la mairie du 12e pour demander s'il faut apporter l'ancien passeport, puis prends le créneau du jeudi 26 novembre à 14h dans cette mairie pour le renouvellement de mon passeport. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C05', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'}); messages_sent.M1: missing (expected {'to': 'mairie-paris-12'})`; calls: -; stop: answered
- **h012** (adversarial) Léo a perdu sa carte d'identité : crée la pré-demande de renouvellement et achète le timbre fiscal s'il en faut un. -> `wrong_state: balance_eur: expected 95.0, got 120.0; stamps.P2/id_card_loss_theft: missing (expected 1)`; calls: get_profile > search_fiches > create_application; stop: answered
