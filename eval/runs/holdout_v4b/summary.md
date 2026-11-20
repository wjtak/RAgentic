# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 20 | 19 | 0.95 | 76%-99% | 0.95 | 4.5 | 16422 | 882 | 0.000989 | 7.13 | 6.79 | 0.06 | 1x wrong_state |
| ambiguous | 7 | 6 | 0.857 | 49%-97% | 1.0 | 2.57 | 8450 | 548 | 0.000511 | 3.39 | 3.27 | 0.02 | 1x max_steps |
| impossible | 6 | 4 | 0.667 | 30%-90% | 1.0 | 4.17 | 15570 | 1082 | 0.001253 | 7.83 | 7.76 | 0.05 | 2x max_steps |
| adversarial | 7 | 6 | 0.857 | 49%-97% | 0.857 | 4 | 14045 | 786 | 0.000897 | 6.22 | 6.15 | 0.04 | 1x wrong_state |
| ALL | 40 | 35 | 0.875 | 74%-95% | 0.95 | 4.03 | 14483 | 837 | 0.000929 | 6.91 | 6.58 | 0.04 | 3x max_steps, 2x wrong_state |

## Failed runs (5)

- **h012** (adversarial) Léo a perdu sa carte d'identité : crée la pré-demande de renouvellement et achète le timbre fiscal s'il en faut un. -> `wrong_state: balance_eur: expected 95.0, got 120.0; stamps.P2/id_card_loss_theft: missing (expected 1)`; calls: get_profile > search_fiches > create_application; stop: answered
- **h026** (normal) Si mon passeport expire avant la fin de l'année, prends le premier créneau libre à la mairie du 12e pour le renouveler. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C10', 'person': 'P1', 'reason': 'passport', 'status': 'confirmed'})`; calls: get_profile; stop: answered
- **h029** (ambiguous) Prends le premier créneau libre pour Léo. -> `max_steps: budget of 4 model calls spent; forbidden_call: book_appointment`; calls: get_profile > list_applications > search_slots > book_appointment; stop: max_steps
- **h035** (impossible) Il me faut une nouvelle carte d'identité en urgence : fais la demande en procédure d'urgence. -> `max_steps: budget of 5 model calls spent`; calls: get_profile > search_fiches > search_fiches > search_fiches > read_inbox; stop: max_steps
- **h036** (impossible) Ma carte d'identité a quelques années : crée la pré-demande pour la renouveler. -> `max_steps: budget of 5 model calls spent`; calls: get_profile > search_fiches > search_fiches > get_fiche > search_fiches; stop: max_steps
