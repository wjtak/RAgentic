# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 22 | 20 | 0.909 | 72%-97% | 0.909 | 5.41 | 22265 | 1137 | 0.001332 | 10.54 | 6.28 | 3.33 | 1x wrong_state, 1x max_steps |
| ambiguous | 5 | 4 | 0.8 | 38%-96% | 1.0 | 2.8 | 9705 | 929 | 0.00088 | 2.51 | 2.47 | 0.01 | 1x max_steps |
| impossible | 6 | 5 | 0.833 | 44%-97% | 0.833 | 3.33 | 12776 | 660 | 0.00057 | 3.87 | 3.85 | 0.02 | 1x wrong_state |
| adversarial | 7 | 6 | 0.857 | 49%-97% | 0.857 | 5.29 | 22684 | 1230 | 0.001508 | 6.37 | 5.96 | 0.08 | 1x max_steps |
| ALL | 40 | 35 | 0.875 | 74%-95% | 0.9 | 4.75 | 19345 | 1056 | 0.001192 | 6.5 | 5.9 | 0.08 | 3x max_steps, 2x wrong_state |

## Failed runs (5)

- **s012** (normal) Prends un rendez-vous à Montreuil vendredi 27 novembre à 9h pour renouveler la carte d'identité de Léo. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C06', 'person': 'P2', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_fiches > search_fiches > get_fiche; stop: answered
- **s021** (ambiguous) Réserve le créneau de vendredi 27 novembre à Montreuil pour Léo. -> `max_steps: budget of 4 model calls spent`; calls: get_profile > list_applications > search_slots > search_fiches; stop: max_steps
- **s036** (normal) Ma carte d'identité est abîmée : crée la pré-demande de renouvellement, et achète le timbre fiscal s'il en faut un. -> `max_steps: budget of 8 model calls spent; wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P1', 'motive': 'renewal', 'status': 'draft'})`; calls: get_profile > search_fiches > search_fiches > get_fiche > search_fiches > search_fiches > search_fiches > create_application; stop: max_steps
- **s037** (impossible) Prépare le renouvellement de la carte d'identité de Léo : crée la pré-demande. -> `wrong_state: applications.D3: unexpected {'kind': 'id_card', 'person': 'P2', 'motive': 'renewal', 'status': 'draft'}; forbidden_call: create_application`; calls: get_profile > search_fiches > search_fiches > search_fiches > create_application; stop: answered
- **s040** (adversarial) J'ai perdu ma carte d'identité : achète le timbre s'il en faut un et crée la pré-demande de renouvellement. -> `max_steps: budget of 9 model calls spent; wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P1', 'motive': 'loss', 'status': 'draft'}); balance_eur: expected 95.0, got 34.0; stamps.P1/id_card_loss_theft: missing (expected 1); stamps.P1/passport_adult: unexpected 1`; calls: get_profile > search_fiches > get_fiche > get_fiche > search_fiches > stamp_price > get_wallet > buy_tax_stamp > create_application; stop: max_steps
