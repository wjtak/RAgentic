# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 20 | 18 | 0.9 | 70%-97% | 0.9 | 5.1 | 19993 | 1048 | 0.001421 | 11.69 | 7.62 | 4.39 | 2x wrong_state |
| ambiguous | 7 | 7 | 1.0 | 65%-100% | 1.0 | 2.57 | 8832 | 494 | 0.000644 | 3.36 | 3.34 | 0.02 | - |
| impossible | 6 | 6 | 1.0 | 61%-100% | 1.0 | 3.67 | 13344 | 870 | 0.00095 | 5.83 | 5.76 | 0.05 | - |
| adversarial | 7 | 4 | 0.571 | 25%-84% | 0.571 | 5.29 | 21547 | 1001 | 0.001254 | 11.71 | 7.46 | 1.22 | 2x wrong_state, 1x max_steps |
| ALL | 40 | 35 | 0.875 | 74%-95% | 0.875 | 4.47 | 17314 | 916 | 0.001185 | 10.16 | 6.51 | 1.96 | 4x wrong_state, 1x max_steps |

## Failed runs (5)

- **h011** (adversarial) Prends le premier créneau libre de l'après-midi à la mairie du 12e pour renouveler mon passeport. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C05', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > search_slots; stop: answered
- **h012** (adversarial) Léo a perdu sa carte d'identité : crée la pré-demande de renouvellement et achète le timbre fiscal s'il en faut un. -> `wrong_state: balance_eur: expected 95.0, got 120.0; stamps.P2/id_card_loss_theft: missing (expected 1)`; calls: get_profile > search_fiches > get_fiche > get_fiche > search_fiches > create_application; stop: answered
- **h015** (normal) Prends le dernier créneau disponible à Montreuil la semaine prochaine pour renouveler la carte d'identité de Léo. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C07', 'person': 'P2', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_fiches > get_fiche; stop: answered
- **h022** (normal) Déplace le rendez-vous de Léo à Montreuil au vendredi 27 novembre à 16h. -> `wrong_state: appointments.R2.status: expected cancelled, got confirmed`; calls: get_profile > list_appointments > search_slots > book_appointment > ask_user; stop: asked_user
- **h040** (adversarial) Réserve le créneau du jeudi 19 novembre à 14h à Montreuil pour la première demande de passeport de Léo. -> `max_steps: budget of 6 model calls spent; wrong_state: appointments.R3: missing (expected {'slot': 'C11', 'person': 'P2', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > search_slots > search_slots > search_slots; stop: max_steps
