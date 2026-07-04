# Plan de test manuel — 0.4.0 (race-craft & stratégie)

Objectif : vérifier sur des **données réelles** (portail Al Kamel) tout ce qui a
été ajouté par la 0.4.0, la suite offline étant déjà verte. Périmètre :

- Parser : `PitTime` conservé sur les in-laps ; `Hour` (heure du jour) rempli.
- `endurancepy.pit_stops(source, settle=)` — 1 ligne par arrêt, avec
  `PosBefore`/`PosAfter`/`PlacesGained` (signal undercut/overcut).
- `endurancepy.stint_summary(source)` — pace + pente de dégradation (s/tour).
- `endurancepy.driver_summary(source)` — tours, temps en voiture, régularité.
- `endurancepy.lead_changes(source, in_class=)` — périodes de leadership.
- `endurancepy.battles(source, within=, min_laps=, in_class=)` — batailles en piste.
- `endurancepy.time_lost(source, threshold=)` — temps perdu vs son propre rythme.
- `endurancepy.fuel_corrected(source, rate=)` — correction carburant.
- `plotting.plot_pit_stops(source)` et `plotting.add_day_night(fig, source)`.

## 0. Pré-requis

```bash
pip install -e ".[dev,interactive,plot]"
python -m pytest -q          # attendu : tout passe (3 skips réseau si hors-ligne)
```

La suite offline valide déjà la logique sur la fixture synthétique ; les étapes
suivantes valident le comportement sur une vraie course.

> **Version exécutable** : le notebook
> [`examples/test_plan_0_4_0.ipynb`](../examples/test_plan_0_4_0.ipynb) déroule
> ce plan cellule par cellule, avec les contrôles automatisables imprimés en
> ✅/❌ ; ne restent à juger à l'œil que les critères de plausibilité ci-dessous.

## 1. Charger une course riche (24h du Mans recommandé)

Une course de 24h coche toutes les cases : beaucoup d'arrêts, relais complets,
nuit (pour `add_day_night`), batailles, changements de leader.

```python
import endurancepy as ep
from endurancepy import plotting

ep.set_log_level("INFO")
ep.Cache.enable_cache("./endurancepy-cache")

print(ep.list_seasons("WEC"))                    # repérer l'id de saison voulu
session = ep.get_session(2023, "WEC", "Le Mans", "Race")
session.load(season="<id de saison>")            # ex. format "NN_YYYY"
laps = session.laps
```

✅ Critères : chargement sans erreur ; plusieurs centaines de tours pour les
voitures de tête ; `laps["PitTime"]` non-NaT sur les in-laps uniquement ;
`laps["Hour"]` rempli et couvrant ~0–24 h (course de 24h).

## 2. `pit_stops`

```python
stops = ep.pit_stops(session)
print(stops.groupby("CarNumber").size().describe())
print(stops[["CarNumber", "Lap", "PitTime", "PosBefore", "PosAfter", "PlacesGained"]].head(20))
```

✅ Critères :
- Nombre d'arrêts par voiture plausible (ordre de grandeur : ~25–35 sur 24h
  pour une voiture qui finit ; comparer 2–3 voitures avec le live/rapport de course).
- `PitTime` majoritairement rempli et réaliste (≈ 1–2 min au Mans, ravitaillement inclus).
- `PosBefore`/`PosAfter` remplis pour la plupart des arrêts (NaN acceptable en
  début/fin de course) ; `PlacesGained` distribué autour de 0.
- Essayer `settle=1` et `settle=3` : les valeurs bougent mais restent cohérentes.

## 3. `stint_summary`

```python
stints = ep.stint_summary(session)
car = stints[stints["CarNumber"] == "<voiture de tête>"]
print(car.to_string())
```

✅ Critères :
- Longueur de relais cohérente avec la fenêtre carburant de la catégorie
  (Hypercar au Mans : ~10–14 tours).
- `StartLap`/`EndLap` contigus d'un relais au suivant, un pilote par relais.
- `Degradation` : petites valeurs, majoritairement positives sur les relais
  longs et propres (quelques négatives normales : évolution de piste, trafic).
- `BestLap`/`MedianLap` cohérents avec les temps réels de la course.

## 4. `driver_summary`

```python
drivers = ep.driver_summary(session)
print(drivers.to_string())
print(drivers.groupby("CarNumber")["TimeInCar"].sum().head())  # ≈ durée de course
```

✅ Critères : 2–3 pilotes par voiture ; la somme des `TimeInCar` d'un équipage
approche la durée de course (moins le temps aux stands) ; `Consistency` de
l'ordre de quelques dixièmes à quelques secondes ; `BestLap` par pilote cohérent.

## 5. `lead_changes`

```python
overall = ep.lead_changes(session)
print(overall.to_string())
print(ep.lead_changes(session, in_class=True).query("Class == 'LMGT3'"))
```

✅ Critères :
- La succession des leaders correspond au récit connu de la course (à vérifier
  contre un rapport de course / le replay du timing).
- La somme des `Laps` ≈ le nombre de tours du vainqueur.
- Le dernier `Leader` (overall et par classe) = le vainqueur au classement
  (`session.results`).

## 6. `battles`

```python
fights = ep.battles(session)                       # défaut : within="1s", min_laps=3, in_class=True
print(fights.sort_values("Laps", ascending=False).head(10))
print(len(ep.battles(session, within="3s")))       # seuil plus large -> plus de batailles
```

✅ Critères :
- Les plus longues batailles correspondent à des duels réellement observés
  (ex. la lutte pour la victoire dans la dernière partie de course).
- `MinGap <= MeanGap <= within` sur chaque ligne ; `ToLap - FromLap + 1 == Laps`.
- Élargir `within` augmente (ou égale) le nombre de lignes, jamais l'inverse.
- `in_class=False` : des batailles inter-classes apparaissent (trafic).

## 7. `time_lost`

```python
lost = ep.time_lost(session)
print(lost.sort_values("TimeLost", ascending=False).head(10))
```

✅ Critères : `TimeLost >= 0` partout ; les voitures de pointe perdent en
général moins que le milieu de peloton ; avec `threshold="2s"` les valeurs
baissent (on ne compte que les gros écarts). NB : une course à forte proportion
de neutralisations gonfle le signal — c'est attendu (proxy, pas une mesure).

## 8. `fuel_corrected`

```python
raw = laps["LapTime"].dt.total_seconds()
corrected = ep.fuel_corrected(session, rate=0.03).dt.total_seconds()  # ~0.03 s/tour de carburant
one = laps[(laps["CarNumber"] == "<voiture>") & (laps["Stint"] == 3)]
print(raw[one.index] - corrected[one.index])   # 0 au 1er tour du relais, croît ensuite
```

✅ Critères : correction nulle au premier tour de chaque relais puis strictement
croissante ; sur un relais propre, la tendance des temps corrigés est plus
plate (la dégradation pneus reste, l'effet carburant disparaît) ; `rate=0`
rend exactement `LapTime`.

## 9. Graphiques : `plot_pit_stops` et `add_day_night`

```python
fig = plotting.plot_pit_stops(session)
fig.show()   # bulle par arrêt : x = tour, y = voiture, taille = temps aux stands, couleur = classe

fig2 = plotting.plot_lap_evolution(laps.pick_classes("HYPERCAR"))
plotting.add_day_night(fig2, session)
plotting.add_track_status(fig2, session)   # combo 0.3.0 + 0.4.0
fig2.show()
```

✅ Critères :
- `plot_pit_stops` : lisible, gros arrêts visiblement plus gros (réparations),
  hover correct, une couleur par classe.
- `add_day_night` : bande(s) nocturnes ≈ 22h–6h locale au Mans ; les bandes ne
  masquent pas les courbes ; cohabite avec `add_track_status`.
- Sur une course diurne (ex. 6h de Spa) : `add_day_night` = no-op (aucune bande).

## 10. Non-régression & cas limites

```python
# a) Les tables acceptent indifféremment Session, Laps, ou un sous-ensemble filtré
ep.pit_stops(laps.pick_classes("LMGT3"))

# b) Ancienne saison (CSV sans colonne flag) : toujours parsable, tables non vides
old = ep.get_session(2019, "WEC", "Spa", "Race"); old.load(season="08_2018-2019")
ep.stint_summary(old); ep.time_lost(old)

# c) Session sans course (qualif/essais) : tables vides ou réduites, pas d'exception
quali = ep.get_session(2023, "WEC", "Le Mans", "Qualifying"); quali.load(season="<id>")
ep.pit_stops(quali); ep.lead_changes(quali); ep.battles(quali)

# d) Cache : recharger la même session -> quasi instantané, résultats identiques
```

✅ Critères : aucun crash ; DataFrames vides bien typés quand il n'y a rien à
dire ; les charts 0.3.0 (`plot_strategy`, `plot_gap`, …) fonctionnent toujours.

## 11. Reste à faire côté release

`pyproject.toml` est passé en `0.4.0` et le CHANGELOG a ses sections `## [0.4.0]`
et `## [0.3.0]` (le jalon plotting garde sa section datée de son merge, mais n'a
jamais été tagué ni publié — il part avec la v0.4.0 ; les tags `v0.1.0`/`v0.2.0`
existent déjà). Une fois ce plan validé et la branche mergée sur `main`, il ne
reste que le tag :

```bash
git tag v0.4.0
git push origin v0.4.0   # déclenche release.yml -> build + publication PyPI
```
