# Plan d'implémentation — EndurancePy (phase 2)

> Document de cadrage technique pour la phase d'implémentation. Il s'appuie sur
> l'analyse fonctionnelle de [`analyse_fastf1.md`](analyse_fastf1.md) (inventaire
> FastF1 + transposition Al Kamel vérifiée). Objectif : un package Python qui
> **reproduit l'API et le contenu de FastF1** pour l'endurance, dans la limite
> des données publiques (timing Al Kamel, **pas de télémétrie**).
>
> ⚠️ Aucun code n'est écrit ici : c'est le plan qui précède le code.

---

## Table des matières

1. [Objectifs et principes de conception](#1-objectifs-et-principes-de-conception)
2. [Pile technique et dépendances](#2-pile-technique-et-dépendances)
3. [Arborescence du package](#3-arborescence-du-package)
4. [Schémas de données (colonnes cibles)](#4-schémas-de-données-colonnes-cibles)
5. [Pipeline de traitement](#5-pipeline-de-traitement)
6. [Points techniques délicats (parsing)](#6-points-techniques-délicats-parsing)
7. [Algorithmes de dérivation](#7-algorithmes-de-dérivation)
8. [Conception du cache](#8-conception-du-cache)
9. [API publique cible (signatures)](#9-api-publique-cible-signatures)
10. [Stratégie de test et fixtures](#10-stratégie-de-test-et-fixtures)
11. [Jalons et découpage en lots](#11-jalons-et-découpage-en-lots)
12. [Compatibilité FastF1 et divergences](#12-compatibilité-fastf1-et-divergences)
13. [Risques et questions ouvertes](#13-risques-et-questions-ouvertes)

---

## 1. Objectifs et principes de conception

| Principe | Mise en œuvre |
|---|---|
| **Miroir de l'API FastF1** | Mêmes noms (`get_session`, `Session.load`, `Session.laps`, `pick_*`, `Cache`) → un utilisateur FastF1 est immédiatement productif. |
| **Objets pandas enrichis** | `Laps`/`Lap`, `SessionResults`/`CarResult`, `EventSchedule`/`Event` sous-classent `DataFrame`/`Series`. |
| **Chargement paresseux** | `get_session()` construit l'objet ; `Session.load()` télécharge + parse. |
| **Cache transparent 2 étages** | HTTP brut + données parsées (indispensable : un 24 h = dizaines de milliers de tours). |
| **Parseur tolérant** | Un seul parseur Al Kamel pour toutes les séries ; robuste aux dérives d'en-tête entre saisons. |
| **Schéma de colonnes stable et typé** | Colonnes toujours présentes, dtypes fixés (cf. FastF1). |
| **Multi-séries / multi-classes natif** | Axe `series` + colonnes `Class`/`Manufacturer`/`PositionInClass`. |
| **Légalité** | Parsing pour usage perso ; **jamais** de redistribution des archives brutes (cf. analyse §14.8). |

---

## 2. Pile technique et dépendances

- **Python** : 3.10+ (typage moderne, `match`, `|` dans les annotations).
- **Cœur** : `pandas`, `numpy`.
- **Réseau / cache** : `requests` + `requests-cache` (étage 1, comme FastF1).
- **Fuzzy matching** des noms d'événements : `rapidfuzz` (recherche `gp`/event).
- **Plotting** (extra optionnel) : `matplotlib`.
- **PDF** (phase ultérieure, extra) : `pdfplumber` (classification/entry list PDF).
- **Live** (phase ultérieure, extra) : `python-socketio[client]` (feed « LT2 »).
- **Qualité** : `pytest`, `pytest-cov`, `ruff` (lint+format), `mypy`.
- **Packaging** : `pyproject.toml` (PEP 621), backend `hatchling` ou
  `setuptools`. Distribution PyPI : `endurancepy` ; import : `endurancepy`.
- **Extras** : `endurancepy[plot]`, `endurancepy[pdf]`, `endurancepy[live]`,
  `endurancepy[dev]`.

---

## 3. Arborescence du package

Miroir de la structure FastF1 (`fastf1.core`, `fastf1.events`, `fastf1.req`,
`fastf1.api`, `fastf1.plotting`, `fastf1.ergast`).

```
EndurancePy/
├── pyproject.toml
├── README.md
├── LICENSE
├── docs/
│   ├── analyse_fastf1.md
│   └── plan_implementation.md
├── src/
│   └── endurancepy/
│       ├── __init__.py          # API top-level : get_session, get_event,
│       │                        #   get_event_schedule, Cache, set_log_level
│       ├── core.py              # Session, Laps, Lap, SessionResults, CarResult
│       ├── events.py            # Event, EventSchedule, Series (enum)
│       ├── cache.py             # Cache (2 étages)
│       ├── exceptions.py        # DataNotLoadedError, SessionNotAvailableError…
│       ├── logger.py            # set_log_level + logger configuré
│       ├── plotting.py          # couleurs/styles par classe/écurie/constructeur
│       ├── standings.py         # (ultérieur) classements championnat recalculés
│       ├── _types.py            # dtypes/colonnes de référence (schémas)
│       └── alkamel/
│           ├── __init__.py
│           ├── client.py        # registre d'hôtes, construction d'URL, download
│           ├── discovery.py     # liste saisons/événements/sessions (index HTML)
│           ├── headers.py       # mappeur d'en-têtes tolérant (BOM, espaces, drift)
│           ├── timeparse.py     # parsing des temps Al Kamel (M:SS.mmm, rollover)
│           ├── analysis.py      # CSV 23_Analysis  -> Laps
│           ├── classification.py# CSV 03_          -> SessionResults
│           ├── timecards.py     # CSV 23_TimeCards -> mapping pilote<->tours
│           └── weather.py       # CSV 26_Weather   -> weather_data
└── tests/
    ├── fixtures/                # mini-CSV synthétiques/réduits (cf. §10)
    └── ...
```

> Choix `src/` layout (recommandé) pour éviter les imports accidentels et
> fiabiliser les tests d'installation.

---

## 4. Schémas de données (colonnes cibles)

### 4.1 `Laps` (compatibles FastF1 + ajouts endurance)

Colonnes **reprises de FastF1** (mêmes noms/dtypes — cf. analyse §5) :
`Time`, `Driver`, `DriverNumber`, `LapTime`, `LapNumber`, `Stint`, `PitOutTime`,
`PitInTime`, `Sector1Time`, `Sector2Time`, `Sector3Time`,
`Sector1SessionTime`…`Sector3SessionTime`, `SpeedST` (← `TOP_SPEED`),
`IsPersonalBest`, `Team`, `LapStartTime`, `LapStartDate`, `TrackStatus`,
`Position`, `IsAccurate`, `Generated` (≈ `FastF1Generated`).

Colonnes **endurance ajoutées** :

| Colonne | dtype | Source / dérivation |
|---|---|---|
| `CarNumber` | `str` | `NUMBER` (zéros conservés) |
| `Class` | `str` | `CLASS` |
| `Manufacturer` | `str` | `MANUFACTURER` |
| `PositionInClass` | `float64` | dérivée (cf. §7) |
| `GapToLeader` | `timedelta64[ns]` | dérivée |
| `GapToLeaderInClass` | `timedelta64[ns]` | dérivée |
| `LapAvgSpeed` | `float64` | `KPH` (km/h) — **moyenne du tour**, ≠ `SpeedST` |
| `Hour` | `float64` | n° d'heure (course) — déduit du dossier/`ELAPSED` |
| `DriverChange` | `bool` | changement de pilote vs tour précédent de la voiture |

Colonnes FastF1 **non applicables** (présentes mais vides, pour compat) :
`Compound`, `TyreLife`, `FreshTyre`, `SpeedI1`, `SpeedI2`, `SpeedFL`,
`Deleted`, `DeletedReason`.

### 4.2 `SessionResults` / `CarResult`

Repris de FastF1 : `Position`, `ClassifiedPosition`, `GridPosition`, `Time`,
`Status`, `Points`, `Laps`, `TeamName`, `FullName`/`FirstName`/`LastName`,
`Abbreviation`, `DriverNumber`. Ajouts endurance : `CarNumber`, `Class`,
`PositionInClass`, `ClassifiedPositionInClass`, `Manufacturer`, `Crew`
(liste des pilotes de la voiture). Unité = **voiture/équipage**.

### 4.3 `weather_data`

`Time`, `AirTemp`, `TrackTemp`, `Humidity`, `Pressure`, `Rainfall`,
`WindSpeed`, `WindDirection` (mêmes noms que FastF1, depuis le CSV `26_`).

### 4.4 `track_status`

`Time`, `Status` (enum : `GreenFlag`, `FCY`, `SafetyCar`, `Code60`,
`SlowZone`, `RedFlag`, `Chequered`), `Message`. Reconstruit depuis la
chronologie des `FLAG_AT_FL`.

---

## 5. Pipeline de traitement

```
get_session(year, series, event, session)
        │  (résolution : Series -> hôte ; fuzzy match event ; n° session)
        ▼
Session.load()
        │
        ├─ client.build_url(...)          # §3 alkamel/client
        ├─ cache.get_or_download(url)      # §8
        ├─ headers.normalize(raw)          # BOM, espaces, drift  (§6)
        ├─ timeparse.*                     # temps -> Timedelta    (§6)
        ├─ analysis.to_laps(df)            # 23_  -> Laps brut
        ├─ derive(): Stint, PitIn/Out,     # §7
        │            LapStartTime, Position,
        │            PositionInClass, Gaps,
        │            TrackStatus, IsAccurate
        ├─ classification.to_results(df)   # 03_  -> SessionResults
        ├─ timecards.map_drivers(...)      # 23_TimeCards -> Driver par tour
        └─ weather.to_weather(df)          # 26_  -> weather_data
        ▼
Session.laps / .results / .weather_data / .track_status disponibles
```

---

## 6. Points techniques délicats (parsing)

À encapsuler dans `alkamel/headers.py` et `alkamel/timeparse.py` :

| Sujet | Détail | Traitement |
|---|---|---|
| **BOM** | `﻿` devant `NUMBER` | `encoding='utf-8-sig'`. |
| **Espaces d'en-tête** | `; DRIVER_NUMBER` (espace de tête sur ~15 col.) | `str.strip()` sur chaque nom + table de synonymes. |
| **Séparateur** | `;` | `pd.read_csv(sep=';')`. |
| **Dérive d'en-tête** | 2018-19 sans `Sn_SECONDS`/`FLAG_AT_FL` ; variante IMSA `…WithSections` avec `IMx`/`INT-n` | mappeur tolérant par nom ; colonnes manquantes → `NA`. |
| **N° de voiture** | `03`, `021` | **toujours `str`** (jamais `int`). |
| **Temps au tour/secteur** | `SS.mmm`, `M:SS.mmm`, `H:MM:SS.mmm` | parseur unique → `Timedelta`. Préférer `Sn_SECONDS` (float) quand présent. |
| **`ELAPSED`** | cumul ; **rollover `24:`** (24 h) | parseur gérant heures ≥ 24. |
| **`HOUR`** | heure du jour `HH:MM:SS.mmm` | → reconstruction `LapStartDate`. |
| **`CROSSING_FINISH_LINE_IN_PIT`** | vide ou `B` | `B` ⇒ tour d'entrée stand. |
| **`LAP_IMPROVEMENT`/`Sn_IMPROVEMENT`** | `0`/`1`/`2` | none / personal best / session best. |
| **`KPH` vs `TOP_SPEED`** | moyenne vs pointe | colonnes distinctes (`LapAvgSpeed`, `SpeedST`). |
| **`FLAG_AT_FL`** | `GF`/`FCY`/`SC`/`SF`/`FF`/`Code60` | mapping enum + `TrackStatus`. |
| **`PIT_TIME`** | `H:MM:SS.mmm`, vide si pas d'arrêt | → durée de l'arrêt. |

---

## 7. Algorithmes de dérivation

Le CSV Analysis ne donne pas tout : plusieurs colonnes FastF1 se **recalculent**.
Traiter **par voiture** (`groupby('CarNumber')`, trié par `LapNumber`).

- **`Stint`** : incrémenté à chaque tour suivant un tour avec `PIT_TIME` non vide
  ou `CROSSING_FINISH_LINE_IN_PIT == 'B'`. (Relais = segment entre deux arrêts.)
- **`PitInTime`** : `ELAPSED` du tour si `B`/`PIT_TIME` présent (entrée stand).
- **`PitOutTime`** : `LapStartTime` du **premier tour du relais suivant**.
- **`LapStartTime`** : `ELAPSED(tour) − LapTime(tour)` (= `ELAPSED` du tour
  précédent, à valider).
- **`LapStartDate`** : à partir de `t0` (heure de départ) + `LapStartTime`, ou
  reconstruit depuis `HOUR`.
- **`Position`** (overall) : à chaque tour, classer les voitures par `ELAPSED`
  croissant (qui a parcouru le plus de distance le plus tôt). Méthode robuste :
  trier l'ensemble des passages par `ELAPSED`, attribuer le rang par
  `(LapNumber décroissant, ELAPSED croissant)` à instant donné.
- **`PositionInClass`** : idem restreint à `Class`.
- **`GapToLeader` / `…InClass`** : différence d'`ELAPSED` au leader à tour égal
  (ou différence de tours).
- **`IsPersonalBest`** : depuis `LAP_IMPROVEMENT`, ou recalcul (meilleur temps
  cumulé du pilote/voiture).
- **`IsAccurate`** : contrôles de cohérence (somme S1+S2+S3 ≈ LapTime à ε près ;
  pas de tour pit ; `FLAG_AT_FL == 'GF'` ; valeurs non nulles). Réplique l'esprit
  de la validation FastF1.
- **`Driver`** : via Time Cards (relie `DRIVER_NUMBER`/relais → nom) ; fallback
  sur `DRIVER_NAME` du CSV Analysis.
- **`total_laps`** : max `LapNumber` du vainqueur, ou métadonnée session.

---

## 8. Conception du cache

Réplique du modèle FastF1 (cf. analyse §9) :

- **Étage 1 (HTTP)** : `requests-cache` (SQLite), expiration configurable, sert
  aussi de garde-fou anti-surcharge des serveurs Al Kamel.
- **Étage 2 (parsé)** : sérialisation des objets parsés (`Laps`, `SessionResults`)
  en pickle/parquet (`*.epkl`), versionné par un `PARSER_VERSION` (invalidation
  au changement de schéma).
- **Résolution du dossier** : argument de `enable_cache` → variable
  d'environnement `ENDURANCEPY_CACHE` → défaut OS (`~/.cache/endurancepy`).
- **API** (miroir FastF1) : `Cache.enable_cache(dir, …)`, `clear_cache(...)`,
  `get_cache_info()`, `disabled()` (context manager), `set_disabled()`/
  `set_enabled()`, `offline_mode(bool)`.
- **Légal** : le cache reste **local** ; ne pas versionner ni publier son contenu
  (déjà couvert par `.gitignore`).

---

## 9. API publique cible (signatures)

```python
# endurancepy/__init__.py
def get_session(year: int, series: str | Series, event: str | int,
                session: str | int) -> core.Session: ...
def get_event(year: int, series: str | Series, event: str | int) -> events.Event: ...
def get_event_schedule(year: int, series: str | Series) -> events.EventSchedule: ...
def set_log_level(level) -> None: ...
Cache = cache.Cache

# events.py
class Series(enum.Enum):
    WEC = "fiawec.alkamelsystems.com"
    ELMS = "elms.alkamelsystems.com"
    ASLMS = "alms.alkamelsystems.com"
    LMC = "lemanscup.alkamelsystems.com"
    IMSA = "imsa.results.alkamelcloud.com"

# core.Session (sélection)
class Session:
    def load(self, *, laps=True, weather=True, messages=True) -> None: ...
    @property
    def laps(self) -> Laps: ...
    @property
    def results(self) -> SessionResults: ...
    @property
    def weather_data(self) -> pandas.DataFrame: ...
    @property
    def track_status(self) -> pandas.DataFrame: ...
    @property
    def cars(self) -> list[str]: ...            # équiv. de Session.drivers
    def get_car(self, number: str) -> CarResult: ...

# core.Laps (sélection) — pick_* FastF1 + ajouts endurance
class Laps(pandas.DataFrame):
    def pick_drivers(self, ids) -> "Laps": ...
    def pick_teams(self, names) -> "Laps": ...
    def pick_cars(self, numbers) -> "Laps": ...          # ajout
    def pick_classes(self, classes) -> "Laps": ...       # ajout
    def pick_manufacturers(self, names) -> "Laps": ...   # ajout
    def pick_laps(self, numbers) -> "Laps": ...
    def pick_fastest(self, only_by_time=False) -> "Lap | None": ...
    def pick_quicklaps(self, threshold=None) -> "Laps": ...
    def pick_track_status(self, status, how="equals") -> "Laps": ...
    def pick_wo_box(self) -> "Laps": ...
    def pick_box_laps(self, which="both") -> "Laps": ...
    def pick_accurate(self) -> "Laps": ...
    def pick_stints(self, numbers) -> "Laps": ...        # ajout
```

> **Pas** de `get_telemetry`/`Telemetry` : aucune source publique (analyse §6/§13).

---

## 10. Stratégie de test et fixtures

- **Tests unitaires ciblés** sur les briques risquées : `headers` (BOM, espaces,
  drift, variante WithSections), `timeparse` (formats + rollover `24:`),
  dérivations `Stint`/`Position`/`IsAccurate`.
- **Fixtures** : **mini-CSV synthétiques** reproduisant le format (quelques
  voitures, 2 classes, quelques tours, un arrêt, une FCY) — **on ne versionne
  pas d'archives Al Kamel réelles** (cf. légal §14.8 de l'analyse). Pour les
  tests d'intégration locaux, pointer vers des jeux de données publics tiers
  (dataset HuggingFace `tobil/imsa`, repos hackathon Toyota) **hors dépôt**.
- **Tests réseau** : marqués `@pytest.mark.network`, désactivés par défaut /
  en CI ; le reste tourne hors-ligne via le cache.
- **Couverture** : viser le parsing + dérivations (cœur de la valeur).
- **CI** : `ruff` + `mypy` + `pytest` (matrice Python 3.10–3.12).

---

## 11. Jalons et découpage en lots

> Chaque lot est livrable et testable indépendamment.

- [ ] **2.0 — Échafaudage** : `pyproject.toml`, layout `src/`, `endurancepy/`
      vide importable, `exceptions.py`, `logger.py`, CI (ruff/mypy/pytest).
- [ ] **2.1 — Cache + client Al Kamel** : `Cache` (2 étages),
      `alkamel/client.py` (registre d'hôtes, `build_url`, download),
      `discovery.py` (lister saisons/événements/sessions depuis l'index).
- [ ] **2.2 — Parseur Analysis → `Laps`** : `headers.py`, `timeparse.py`,
      `analysis.py`, dérivations (`Stint`, pit, `LapStartTime`, `Position`,
      `PositionInClass`, `IsAccurate`), méthodes `pick_*`. **(cœur du projet)**
- [ ] **2.3 — Résultats & pilotes** : `classification.py` → `SessionResults`
      (par voiture + par classe) ; `timecards.py` → mapping pilote↔tours.
- [ ] **2.4 — Météo & statut piste** : `weather.py` → `weather_data` ;
      `track_status` depuis `FLAG_AT_FL`.
- [ ] **2.5 — Événements** : `Event`/`EventSchedule`, `Series`, recherche fuzzy
      d'événement, calendriers par saison.
- [ ] **2.6 — Plotting** : couleurs/styles par classe/écurie/constructeur,
      `setup_mpl`, helpers `get_*`.
- [ ] **2.7 — Standings** (optionnel) : recalcul des classements championnat.
- [ ] **2.8 — Finalisation** : docs (Sphinx/mkdocs), exemples, packaging, release
      PyPI, badge couverture.

**Chemin critique** : 2.0 → 2.1 → 2.2 (les autres lots en dépendent).

---

## 12. Compatibilité FastF1 et divergences

| Aspect | Décision |
|---|---|
| Noms d'API | Identiques à FastF1 quand cela a un sens (`get_session`, `load`, `laps`, `results`, `pick_*`, `Cache`). |
| Axe `series` | **Ajout** obligatoire (plusieurs championnats). |
| Unité de résultat | **Voiture/équipage** (`CarResult`) au lieu de pilote ; `Session.cars` ≈ `Session.drivers`. |
| Télémétrie | **Absente** (pas de `Telemetry`, ni `car_data`/`pos_data`). |
| Colonnes `Laps` | Sur-ensemble de FastF1 (colonnes pneus/télémétrie présentes mais vides pour compat). |
| Ergast | Remplacé par `standings` (recalcul), phase ultérieure. |
| Cache | Même comportement/API. |

---

## 13. Risques et questions ouvertes

| Sujet | Risque | Mitigation |
|---|---|---|
| Dérive des formats Al Kamel | en-têtes/variantes par saison/série | mappeur tolérant + fixtures multi-saisons + `PARSER_VERSION`. |
| Stabilité des URL / index HTML | structure du portail peut changer | `discovery.py` isolé, tests réseau marqués, dégradation gracieuse. |
| Exactitude des positions/gaps | reconstruction non triviale (multi-classes, tours en retard) | valider contre la Classification officielle (`03_`). |
| Codes `FLAG_AT_FL` partiels | `SF`/`FF`/`Code60` inférés | confirmer sur données réelles ; enum extensible. |
| Légalité (redistribution) | données « propriété Al Kamel » | parsing local only ; aucun jeu réel versionné ; respect CGU/`robots.txt`/débit. |
| Live timing (Socket.IO) | schéma non documenté | hors phase 1 ; lire le connecteur `timing71` le moment venu. |

**À trancher avant 2.0** : nom de distribution PyPI (`endurancepy` proposé),
backend de build (`hatchling` proposé), gestion `src/` (recommandé), choix
parquet vs pickle pour l'étage 2 du cache.

---

*Plan vivant — à amender au fil des lots. Le code démarre au lot 2.0.*
