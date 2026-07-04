# Release 0.4.0 — procédure de merge, tag et publication

Procédure concrète pour couper la 0.4.0 (déclinaison de [`RELEASING.md`](../RELEASING.md)
pour cette release). Contexte : la PR [#25](https://github.com/RomainFl50/EndurancePy/pull/25)
porte le bump de version, le CHANGELOG finalisé et le matériel de vérification ;
la release embarque aussi le jalon plotting 0.3.0, jamais publié séparément —
**il n'y aura donc pas de tag `v0.3.0`**, on passe directement de `v0.2.0` à `v0.4.0`.

## 1. Avant de merger — validation

- [ ] Dérouler le plan de test sur une vraie course :
      [`docs/test_plan_0.4.0.md`](test_plan_0.4.0.md), version exécutable
      [`examples/test_plan_0_4_0.ipynb`](../examples/test_plan_0_4_0.ipynb)
      (tous les ✅ passent, critères de plausibilité jugés OK).
- [ ] CI verte sur la PR #25 (lint + tests 3.10–3.12).
- [ ] Vérifier le contenu qui va partir : `pyproject.toml` en `0.4.0`, section
      `## [0.4.0] - 2026-07-04` en tête du CHANGELOG, liens de comparaison à jour.

## 2. Merger

Merger la PR #25 dans `main` (squash ou merge commit, au choix habituel du dépôt).

## 3. Tagger

Le workflow de publication ne se déclenche que sur les tags `v*` :

```bash
git checkout main
git fetch origin main && git pull origin main   # récupérer le commit de merge
git tag v0.4.0
git push origin v0.4.0
```

⚠️ Tagger **le commit de merge sur `main`** (celui qui contient `version = "0.4.0"`),
pas la branche : le wheel est construit depuis le commit taggé.

## 4. Publication (automatique)

Le push du tag déclenche [`release.yml`](../.github/workflows/release.yml) :

1. build du sdist + wheel (Hatchling) ;
2. `twine check` ;
3. publication sur PyPI via **Trusted Publishing** (OIDC, environnement GitHub
   `pypi`) — aucun token à fournir. Si l'environnement `pypi` est protégé par
   des reviewers requis, approuver le déploiement dans l'onglet Actions.

Suivre le run dans **Actions → release**. En cas d'échec du build seul, le
workflow peut être relancé ; en cas d'erreur dans le contenu, corriger sur
`main` **et re-tagger en `v0.4.1`** (ne jamais déplacer un tag déjà poussé —
PyPI refuse de toute façon de réutiliser une version).

## 5. Vérifier

- [ ] https://pypi.org/project/endurancepy/ affiche la `0.4.0`.
- [ ] Installation propre :

```bash
pip install --upgrade endurancepy
python -c "import endurancepy as ep; print(ep.__version__)"   # -> 0.4.0
python -c "import endurancepy as ep; ep.pit_stops"            # l'API 0.4.0 est là
```

- [ ] (Optionnel) Créer la *GitHub Release* depuis le tag `v0.4.0` en collant la
      section `## [0.4.0]` du CHANGELOG.

## 6. Après la release

- [ ] Ouvrir le cycle suivant : rien à faire dans le CHANGELOG (la section
      `## [Unreleased]` vide est déjà en place) ; mettre à jour
      [`ROADMAP.md`](../ROADMAP.md) si le prochain jalon change.
