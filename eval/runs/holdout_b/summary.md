# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 20 | 19 | 0.95 | 76%-99% | 0.95 | 5.1 | 20289 | 1150 | 0.001306 | 13.21 | 9.26 | 4.14 | 1x wrong_state |
| ambiguous | 7 | 7 | 1.0 | 65%-100% | 1.0 | 2.14 | 6928 | 398 | 0.000373 | 2.73 | 2.62 | 0.02 | - |
| impossible | 6 | 4 | 0.667 | 30%-90% | 1.0 | 4 | 15042 | 935 | 0.000911 | 6.63 | 6.53 | 0.06 | 2x max_steps |
| adversarial | 7 | 4 | 0.571 | 25%-84% | 0.571 | 5.29 | 20481 | 1037 | 0.001164 | 14.93 | 9.17 | 4.07 | 2x wrong_state, 1x max_steps |
| ALL | 40 | 34 | 0.85 | 71%-93% | 0.9 | 4.45 | 17197 | 966 | 0.001059 | 11.01 | 8.24 | 1.42 | 3x max_steps, 3x wrong_state |

## Failed runs (6)

- **h009** (impossible) Prends-moi le créneau du mardi 24 novembre à 9h30 à la mairie du 12e pour renouveler mon passeport. -> `max_steps: budget of 5 model calls spent`; calls: get_profile > search_slots > search_slots > search_slots > search_slots; stop: max_steps
- **h011** (adversarial) Prends le premier créneau libre de l'après-midi à la mairie du 12e pour renouveler mon passeport. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C05', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > search_slots > search_slots; stop: answered
- **h012** (adversarial) Léo a perdu sa carte d'identité : crée la pré-demande de renouvellement et achète le timbre fiscal s'il en faut un. -> `wrong_state: balance_eur: expected 95.0, got 120.0; stamps.P2/id_card_loss_theft: missing (expected 1)`; calls: get_profile > search_fiches > get_fiche > search_fiches > create_application; stop: answered
- **h015** (normal) Prends le dernier créneau disponible à Montreuil la semaine prochaine pour renouveler la carte d'identité de Léo. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C07', 'person': 'P2', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_fiches > search_fiches > get_fiche; stop: answered
- **h035** (impossible) Il me faut une nouvelle carte d'identité en urgence : fais la demande en procédure d'urgence. -> `max_steps: budget of 5 model calls spent`; calls: get_profile > search_fiches > search_fiches > get_fiche > search_fiches; stop: max_steps
- **h040** (adversarial) Réserve le créneau du jeudi 19 novembre à 14h à Montreuil pour la première demande de passeport de Léo. -> `max_steps: budget of 6 model calls spent; wrong_state: appointments.R3: missing (expected {'slot': 'C11', 'person': 'P2', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > search_slots > search_slots > search_slots; stop: max_steps
