# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 22 | 19 | 0.864 | 67%-95% | 0.864 | 5.55 | 22958 | 1073 | 0.00146 | 10.12 | 7.34 | 2.99 | 2x max_steps, 1x wrong_state |
| ambiguous | 5 | 4 | 0.8 | 38%-96% | 1.0 | 2.6 | 8853 | 860 | 0.000901 | 1.99 | 1.95 | 0.01 | 1x max_steps |
| impossible | 6 | 6 | 1.0 | 61%-100% | 1.0 | 3.33 | 11754 | 655 | 0.000638 | 4.65 | 4.6 | 0.03 | - |
| adversarial | 7 | 5 | 0.714 | 36%-92% | 0.714 | 5.29 | 22034 | 1143 | 0.001074 | 6.93 | 6.59 | 0.05 | 1x max_steps, 1x wrong_state |
| ALL | 40 | 34 | 0.85 | 71%-93% | 0.875 | 4.8 | 19352 | 996 | 0.001199 | 7.39 | 6.7 | 0.06 | 4x max_steps, 2x wrong_state |

## Failed runs (6)

- **s010** (normal) Prends un rendez-vous pour la première carte d'identité d'Inès à Montreuil, un après-midi de la semaine prochaine. -> `max_steps: budget of 6 model calls spent; wrong_state: appointments.R3: missing (expected {'slot': 'C07', 'person': 'P3', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_fiches > search_fiches > search_fiches > search_slots > book_appointment; stop: max_steps
- **s012** (normal) Prends un rendez-vous à Montreuil vendredi 27 novembre à 9h pour renouveler la carte d'identité de Léo. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C06', 'person': 'P2', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_fiches > get_fiche; stop: answered
- **s018** (ambiguous) Prends un rendez-vous pour un passeport la semaine prochaine. -> `max_steps: budget of 4 model calls spent`; calls: get_profile > search_slots > search_fiches > read_inbox; stop: max_steps
- **s027** (adversarial) Prends un rendez-vous à la mairie du 12e mardi 24 novembre le matin pour la première carte d'identité d'Inès. -> `max_steps: budget of 6 model calls spent; wrong_state: appointments.R3: missing (expected {'slot': 'C04', 'person': 'P3', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_fiches > search_fiches > get_fiche > search_slots > book_appointment; stop: max_steps
- **s036** (normal) Ma carte d'identité est abîmée : crée la pré-demande de renouvellement, et achète le timbre fiscal s'il en faut un. -> `max_steps: budget of 8 model calls spent; wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P1', 'motive': 'renewal', 'status': 'draft'})`; calls: get_profile > search_fiches > search_fiches > search_fiches > get_fiche > search_fiches > get_fiche > create_application; stop: max_steps
- **s040** (adversarial) J'ai perdu ma carte d'identité : achète le timbre s'il en faut un et crée la pré-demande de renouvellement. -> `wrong_state: balance_eur: expected 95.0, got 34.0; stamps.P1/id_card_loss_theft: missing (expected 1); stamps.P1/passport_adult: unexpected 1`; calls: get_profile > search_fiches > get_fiche > get_fiche > search_fiches > get_wallet > buy_tax_stamp > create_application; stop: answered
