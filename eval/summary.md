# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 19 | 18 | 0.947 | 75%-99% | 0.947 | 4.95 | 17049 | 930 | 0.001282 | 6.63 | 1x wrong_state |
| ambiguous | 5 | 4 | 0.8 | 38%-96% | 1.0 | 2.6 | 8208 | 557 | 0.000642 | 4.07 | 1x max_steps |
| impossible | 5 | 5 | 1.0 | 57%-100% | 1.0 | 3 | 9733 | 584 | 0.000529 | 6.12 | - |
| adversarial | 6 | 5 | 0.833 | 44%-97% | 0.833 | 4.17 | 13686 | 883 | 0.000763 | 7.34 | 1x wrong_state |
| ALL | 35 | 32 | 0.914 | 78%-97% | 0.943 | 4.2 | 14164 | 819 | 0.000994 | 6.58 | 2x wrong_state, 1x max_steps |

## Failed runs (3)

- **s021** (ambiguous) Réserve le créneau de vendredi prochain à Montreuil pour Léo. -> `max_steps: budget of 4 model calls spent`; calls: get_profile > search_slots > search_slots > ask_user; stop: max_steps
- **s027** (adversarial) Prends un rendez-vous à la mairie du 12e mardi prochain le matin pour la première carte d'identité d'Inès. -> `wrong_state: appointments.R3: missing (expected {'slot': 'C04', 'person': 'P3', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_slots > search_slots > ask_user; stop: asked_user
- **s035** (normal) La carte d'identité de Léo a été volée : fais le nécessaire (timbre et pré-demande). -> `wrong_state: applications.D3.status: expected draft, got submitted; forbidden_call: submit_application`; calls: get_profile > search_fiches > get_wallet > create_application > buy_tax_stamp > submit_application; stop: answered
