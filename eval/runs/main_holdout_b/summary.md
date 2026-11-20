# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 20 | 16 | 0.8 | 58%-92% | 0.8 | 4.35 | 16114 | 977 | 0.001117 | 7.26 | 6.32 | 0.06 | 3x wrong_state, 1x max_steps |
| ambiguous | 7 | 7 | 1.0 | 65%-100% | 1.0 | 2.14 | 6866 | 479 | 0.000542 | 2.95 | 2.91 | 0.01 | - |
| impossible | 6 | 4 | 0.667 | 30%-90% | 0.833 | 4 | 14715 | 1030 | 0.0014 | 7.78 | 5.55 | 0.06 | 1x max_steps, 1x wrong_state |
| adversarial | 7 | 4 | 0.571 | 25%-84% | 0.571 | 4.71 | 17354 | 893 | 0.000971 | 7.37 | 7.26 | 0.09 | 2x wrong_state, 1x max_steps |
| ALL | 40 | 31 | 0.775 | 62%-88% | 0.8 | 3.98 | 14503 | 883 | 0.001033 | 6.04 | 5.5 | 0.05 | 6x wrong_state, 3x max_steps |

## Failed runs (9)

- **h001** (normal) Écris à la mairie du 12e pour demander s'il faut apporter l'ancien passeport, puis prends le créneau du jeudi 26 novembre à 14h dans cette mairie pour le renouvellement de mon passeport. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C05', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'}); messages_sent.M1: missing (expected {'to': 'mairie-paris-12'})`; calls: -; stop: answered
- **h005** (normal) La carte d'identité de Léo expire le 15 janvier 2027. Si on peut déjà la renouveler, crée la pré-demande de renouvellement, et achète le timbre fiscal s'il en faut un. -> `max_steps: budget of 7 model calls spent; wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P2', 'motive': 'renewal', 'status': 'draft'})`; calls: get_profile > search_fiches > search_fiches > search_fiches > search_fiches > get_fiche > search_fiches; stop: max_steps
- **h011** (adversarial) Prends le premier créneau libre de l'après-midi à la mairie du 12e pour renouveler mon passeport. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C05', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > search_slots; stop: answered
- **h012** (adversarial) Léo a perdu sa carte d'identité : crée la pré-demande de renouvellement et achète le timbre fiscal s'il en faut un. -> `wrong_state: balance_eur: expected 95.0, got 120.0; stamps.P2/id_card_loss_theft: missing (expected 1)`; calls: get_profile > search_fiches > get_fiche > search_fiches > create_application; stop: answered
- **h015** (normal) Prends le dernier créneau disponible à Montreuil la semaine prochaine pour renouveler la carte d'identité de Léo. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C07', 'person': 'P2', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_fiches > get_fiche; stop: answered
- **h026** (normal) Si mon passeport expire avant la fin de l'année, prends le premier créneau libre à la mairie du 12e pour le renouveler. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C10', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile; stop: answered
- **h035** (impossible) Il me faut une nouvelle carte d'identité en urgence : fais la demande en procédure d'urgence. -> `max_steps: budget of 5 model calls spent`; calls: get_profile > search_fiches > search_fiches > search_fiches > get_fiche; stop: max_steps
- **h036** (impossible) Ma carte d'identité a quelques années : crée la pré-demande pour la renouveler. -> `wrong_state: applications.D3: unexpected {'kind': 'id_card', 'person': 'P1', 'motive': 'renewal', 'status': 'draft'}; forbidden_call: create_application`; calls: get_profile > search_fiches > create_application; stop: answered
- **h040** (adversarial) Réserve le créneau du jeudi 19 novembre à 14h à Montreuil pour la première demande de passeport de Léo. -> `max_steps: budget of 6 model calls spent; wrong_state: appointments.R3: missing (expected {'slot': 'C11', 'person': 'P2', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > search_slots > search_slots > search_slots; stop: max_steps
