# Plan de l'équipe : vérifications, améliorations, soutenance

Code freeze : **jeudi 19 novembre 2026, 23h59** (tag `v1.0`). Soutenance : vendredi 20 novembre (10 min + 5 min de questions, tout le monde parle).

Chaque rôle correspond à une partie de la soutenance.

## Jour 1 (mardi), pour tous, en commun (environ 1 h)

1. Dans le vrai dépôt : poser le tag `v0.0-base` sur le commit actuel, *puis* copier le nouveau code.
2. `uv sync`, `cp .env.example .env` (ajouter `OPENROUTER_API_KEY`), puis `uv run pytest -q`.
3. `uv run python scripts/run_task.py --scenario s004 --reset` : voir l'agent tourner une fois.

Points de vigilance :
- **LangGraph** : le graphe a été testé avec une imitation de la bibliothèque. Si les tests échouent dans `tests/test_graph.py`, la Personne 2 corrige en priorité, et le reste attend.
- **Windows** : `src/agent_demarches/backend.py` utilise `fcntl`, qui n'existe pas sous Windows. Si quelqu'un est sous Windows, la Personne 1 le remplace par un simple verrou.

## Personne 1 : backend et serveurs MCP (Sessions 1 et 2)

Vérifier :
- [ ] Les deux serveurs avec `uv run mcp dev servers/espace_usager_server.py` (l'inspecteur MCP) : schémas typés, annotations, erreurs JSON.
- [ ] La reprise après panne : s011 (timeout après paiement → un seul timbre) et s012 (deux erreurs 429).
- [ ] Que `search_fiches` marche avec et sans l'index Chroma (`scripts/run_ingest.py`).

Améliorer ou rectifier :
- [ ] Les messages d'erreur des outils, s'ils sont mal compris par le modèle (à repérer dans les traces de la Personne 3).
- [ ] La compatibilité Windows (`fcntl`).

À l'oral : le domaine, le backend, les actions dangereuses, et pourquoi 2 serveurs.

## Personne 2 : graphe LangGraph et mémoire (Sessions 3 et 4)

Vérifier :
- [ ] Avec le vrai LangGraph : `__interrupt__`, `aget_state`, la reprise après approbation, `recursion_limit`.
- [ ] Le budget d'étapes (`max_steps`, arrêt `give_up`).
- [ ] La mémoire : `tests/test_memory.py`, puis s013 (avec mémoire) et s018 (sans) avec le vrai modèle.

Améliorer :
- [ ] Le prompt (`src/agent_demarches/prompts.py`), selon les échecs remontés par la Personne 3.
- [ ] Mesurer combien de fois le modèle envoie plusieurs appels d'outils d'un coup (seul le premier est exécuté).

À l'oral : l'architecture (pourquoi ce graphe, pourquoi un seul agent), l'approbation humaine, la mémoire. C'est aussi la Personne 2 qui fait la **démo en direct** avec `scripts/run_task.py`.

## Personne 3 : évaluation et analyse d'erreurs (Session 6)

Vérifier :
- [ ] Relire les 32 scénarios dans `eval/make_scenarios.py` : tâche claire en français ? État attendu juste ? (Après une modification : `uv run python eval/make_scenarios.py`.)
- [ ] Lancer `uv run python eval/run_eval.py --scenarios eval/scenarios.jsonl --out eval/`, idéalement 2 fois (le modèle n'est pas déterministe).

Pour chaque échec :
- [ ] Le lire avec `uv run python scripts/show_trace.py <id>`.
- [ ] Classer la cause : prompt, outil, graphe ou modèle.
- [ ] Faire corriger par la personne concernée, relancer, garder les chiffres avant/après.

Risque connu : dans les cas ambigus, le modèle peut poser sa question en texte au lieu d'utiliser `ask_user`. C'est accepté comme une question (`src/agent_demarches/scoring.py`), mais à vérifier dans les traces.

À l'oral : les résultats par type de scénario et l'analyse d'erreurs, la partie la plus notée selon les conseils du prof.

## Personne 4 : traces, comparaison de modèles, README et soutenance (Session 7 et bonus)

Vérifier :
- [ ] Dans `eval/results.jsonl` : tokens, latence et coût de chaque run. OpenRouter fournit-il bien `usage.cost` ? Sinon, compléter la table `PRICES` dans `src/agent_demarches/config.py`.

Bonus comparaison de modèles :
- [ ] `uv run python eval/run_eval.py --scenarios eval/scenarios.jsonl --out eval/runs/gemini --model google/gemini-2.5-flash`
- [ ] `uv run python eval/summarize.py eval/ eval/runs/gemini --out eval/` → `eval/comparison.md`

README :
- [ ] Remplir les sections 5 (Results) et 6 (Error analysis) avec les données des Personnes 3 et 4, relire le reste.

Soutenance :
- [ ] Préparer les slides.
- [ ] Choisir un run réussi et un run raté, à lire en direct depuis la trace.
- [ ] Chronométrer une répétition à 4.

À l'oral : coûts et latences, comparaison des deux modèles, conclusion et limites.

## Points de synchronisation

| Quand | Quoi |
|---|---|
| Mardi soir | Tests verts et premier run d'éval complet (Personne 3), échecs répartis à chacun |
| Mercredi soir | Corrections faites, deuxième run, comparaison de modèles lancée |
| Jeudi | README final, répétition de la soutenance, tag `v1.0` avant 23h59 |

Règle : toute modification du prompt ou d'un outil se fait **après** un run mesuré. On garde le tableau avant/après dans le README : c'est exactement ce que le jury veut entendre.
