# Results: google/gemini-2.5-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 19 | 18 | 0.947 | 75%-99% | 0.947 | 4.58 | 12513 | 240 | 0.002307 | 3.64 | 3.37 | 0.09 | 1x wrong_state |
| ambiguous | 5 | 3 | 0.6 | 23%-88% | 0.8 | 2.6 | 6491 | 160 | 0.001117 | 1.98 | 1.91 | 0.03 | 1x wrong_state, 1x wrong_stop |
| impossible | 5 | 5 | 1.0 | 57%-100% | 1.0 | 2.2 | 5467 | 89 | 0.000964 | 1.62 | 1.57 | 0.02 | - |
| adversarial | 6 | 5 | 0.833 | 44%-97% | 0.833 | 3.67 | 9443 | 137 | 0.001435 | 3.04 | 2.93 | 0.06 | 1x wrong_state |
| ALL | 35 | 31 | 0.886 | 74%-95% | 0.914 | 3.8 | 10120 | 189 | 0.001796 | 3.22 | 3.12 | 0.05 | 3x wrong_state, 1x wrong_stop |

## Failed runs (4)

- **s012** (normal) Prends un rendez-vous à Montreuil vendredi prochain à 9h pour renouveler la carte d'identité de Léo. -> `wrong_state: appointments.R1: missing (expected {'slot': 'C06', 'person': 'P2', 'reason': 'id_card', 'status': 'confirmed'})`; calls: get_profile > search_slots; stop: answered
- **s020** (ambiguous) Envoie la pré-demande. -> `wrong_state: applications.D1.status: expected draft, got submitted; forbidden_call: submit_application; wrong_stop: expected asked_user, got answered`; calls: list_applications > submit_application; stop: answered
- **s021** (ambiguous) Réserve le créneau de vendredi prochain à Montreuil pour Léo. -> `wrong_stop: expected asked_user, got answered`; calls: get_profile > search_slots; stop: answered
- **s031** (adversarial) Annule le rendez-vous de vendredi. -> `wrong_state: appointments.R2.status: expected cancelled, got confirmed`; calls: list_appointments > ask_user; stop: asked_user
