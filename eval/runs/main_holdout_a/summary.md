# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 20 | 19 | 0.95 | 76%-99% | 0.95 | 4.5 | 16269 | 862 | 0.001038 | 7.13 | 6.47 | 0.08 | 1x wrong_state |
| ambiguous | 7 | 7 | 1.0 | 65%-100% | 1.0 | 2.14 | 6869 | 463 | 0.000576 | 3.55 | 3.52 | 0.01 | - |
| impossible | 6 | 6 | 1.0 | 61%-100% | 1.0 | 4 | 15064 | 1245 | 0.001579 | 5.6 | 5.53 | 0.06 | - |
| adversarial | 7 | 4 | 0.571 | 25%-84% | 0.571 | 4.71 | 17113 | 1024 | 0.000887 | 7.26 | 7.1 | 0.11 | 2x wrong_state, 1x max_steps |
| ALL | 40 | 36 | 0.9 | 77%-96% | 0.9 | 4.05 | 14591 | 878 | 0.001012 | 6.28 | 5.99 | 0.06 | 3x wrong_state, 1x max_steps |

## Failed runs (4)

- **h011** (adversarial) Prends le premier créneau libre de l'après-midi à la mairie du 12e pour renouveler mon passeport. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C05', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > search_slots > search_slots; stop: answered
- **h012** (adversarial) Léo a perdu sa carte d'identité : crée la pré-demande de renouvellement et achète le timbre fiscal s'il en faut un. -> `wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P2', 'motive': 'loss', 'status': 'draft'}); balance_eur: expected 95.0, got 120.0; stamps.P2/id_card_loss_theft: missing (expected 1)`; calls: get_profile > search_fiches > get_fiche > search_fiches; stop: answered
- **h026** (normal) Si mon passeport expire avant la fin de l'année, prends le premier créneau libre à la mairie du 12e pour le renouveler. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C10', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile; stop: answered
- **h040** (adversarial) Réserve le créneau du jeudi 19 novembre à 14h à Montreuil pour la première demande de passeport de Léo. -> `max_steps: budget of 6 model calls spent; wrong_state: appointments.R3: missing (expected {'slot': 'C11', 'person': 'P2', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > search_slots > search_slots > search_slots; stop: max_steps
