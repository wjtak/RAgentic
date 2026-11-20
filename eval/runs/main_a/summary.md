# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 22 | 19 | 0.864 | 67%-95% | 0.864 | 4.91 | 18505 | 880 | 0.001136 | 7.62 | 6.82 | 0.08 | 2x wrong_state, 1x max_steps |
| ambiguous | 5 | 5 | 1.0 | 57%-100% | 1.0 | 2.4 | 7855 | 563 | 0.000785 | 3.29 | 3.27 | 0.01 | - |
| impossible | 6 | 6 | 1.0 | 61%-100% | 1.0 | 3 | 10572 | 669 | 0.000734 | 5.34 | 5.3 | 0.02 | - |
| adversarial | 7 | 7 | 1.0 | 65%-100% | 1.0 | 4.43 | 16998 | 905 | 0.001238 | 5.04 | 4.99 | 0.02 | - |
| ALL | 40 | 37 | 0.925 | 80%-97% | 0.925 | 4.22 | 15720 | 813 | 0.00105 | 6.31 | 5.78 | 0.03 | 2x wrong_state, 1x max_steps |

## Failed runs (3)

- **s008** (normal) Envoie un message à la mairie de Montreuil pour prévenir que Léo viendra avec son père au rendez-vous de vendredi. -> `wrong_state: messages_sent.M1: missing (expected {'to': 'mairie-montreuil'})`; calls: get_profile > list_appointments; stop: answered
- **s009** (normal) Pour le renouvellement de mon passeport : achète le timbre, envoie ma pré-demande et prends le premier créneau libre à la mairie du 11e. -> `wrong_state: applications.D1.status: expected submitted, got draft; applications.D3: unexpected {'kind': 'passport', 'person': 'P1', 'motive': 'renewal', 'status': 'submitted'}; forbidden_call: create_application`; calls: get_profile > stamp_price > get_wallet > buy_tax_stamp > create_application > submit_application > search_slots > book_appointment; stop: answered
- **s036** (normal) Ma carte d'identité est abîmée : crée la pré-demande de renouvellement, et achète le timbre fiscal s'il en faut un. -> `max_steps: budget of 8 model calls spent; wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P1', 'motive': 'renewal', 'status': 'draft'})`; calls: get_profile > search_fiches > search_fiches > search_fiches > get_fiche > search_fiches > search_fiches > get_fiche; stop: max_steps
