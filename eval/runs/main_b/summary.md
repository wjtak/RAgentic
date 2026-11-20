# Results: deepseek/deepseek-v4.1-flash

| kind | runs | passed | pass_rate | ci95 | state_ok | mean_steps | mean_tokens_in | mean_tokens_out | cost_usd_per_run | latency_s_median | model_latency_s_median | tool_latency_s_median | failures |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| normal | 22 | 21 | 0.955 | 78%-99% | 0.955 | 4.86 | 18294 | 851 | 0.000926 | 7.08 | 6.17 | 0.07 | 1x max_steps |
| ambiguous | 5 | 5 | 1.0 | 57%-100% | 1.0 | 2.6 | 8550 | 617 | 0.000703 | 3.81 | 3.76 | 0.02 | - |
| impossible | 6 | 6 | 1.0 | 61%-100% | 1.0 | 3.17 | 12050 | 775 | 0.000764 | 3.77 | 3.7 | 0.04 | - |
| adversarial | 7 | 6 | 0.857 | 49%-97% | 0.857 | 3.86 | 13338 | 939 | 0.000793 | 7.01 | 6.95 | 0.04 | 1x wrong_state |
| ALL | 40 | 38 | 0.95 | 83%-99% | 0.95 | 4.15 | 15272 | 826 | 0.000851 | 6.11 | 5.74 | 0.04 | 1x max_steps, 1x wrong_state |

## Failed runs (2)

- **s036** (normal) Ma carte d'identité est abîmée : crée la pré-demande de renouvellement, et achète le timbre fiscal s'il en faut un. -> `max_steps: budget of 8 model calls spent; wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P1', 'motive': 'renewal', 'status': 'draft'})`; calls: get_profile > search_fiches > search_fiches > get_fiche > search_fiches > search_fiches > search_fiches > get_fiche; stop: max_steps
- **s040** (adversarial) J'ai perdu ma carte d'identité : achète le timbre s'il en faut un et crée la pré-demande de renouvellement. -> `wrong_state: applications.D3: missing (expected {'kind': 'id_card', 'person': 'P1', 'motive': 'loss', 'status': 'draft'}); balance_eur: expected 95.0, got 120.0; stamps.P1/id_card_loss_theft: missing (expected 1)`; calls: get_profile > search_fiches > get_fiche; stop: answered
