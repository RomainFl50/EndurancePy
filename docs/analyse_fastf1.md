# Analyse du contenu de FastF1 — base de référence pour EndurancePy

> Document de travail interne. Objectif : **inventorier exhaustivement ce que
> fournit FastF1** (API, objets, colonnes de données, méthodes) afin de pouvoir
> reproduire « à l'identique » le même contenu pour l'endurance (WEC, IMSA,
> ELMS, Asian Le Mans Series, Le Mans Cup…), dans la mesure où les données
> sources (archives Al Kamel principalement) le permettent.
>
> Le premier objectif d'EndurancePy est d'offrir **le même contenu que FastF1
> lorsque la donnée existe**. Ce document sert donc de cahier des charges
> fonctionnel : pour chaque brique de FastF1, on note (1) ce qu'elle contient,
> (2) sa disponibilité côté endurance, (3) l'équivalent EndurancePy envisagé.
>
> Source : FastF1 **v3.8.3** (code installé, identique à ce qui génère
> `docs.fastf1.dev`). Documentation : <https://docs.fastf1.dev/>,
> dépôt : <https://github.com/theOehrly/Fast-F1>.

---

## Table des matières

1. [Philosophie et architecture de FastF1](#1-philosophie-et-architecture-de-fastf1)
2. [API de premier niveau (fonctions `fastf1.*`)](#2-api-de-premier-niveau-fonctions-fastf1)
3. [Système d'événements : `Event` et `EventSchedule`](#3-système-dévénements--event-et-eventschedule)
4. [La `Session` (objet central)](#4-la-session-objet-central)
5. [`Laps` et `Lap` (données de tours)](#5-laps-et-lap-données-de-tours)
6. [`Telemetry` (télémétrie voiture et position)](#6-telemetry-télémétrie-voiture-et-position)
7. [`SessionResults` et `DriverResult` (classement)](#7-sessionresults-et-driverresult-classement)
8. [Données annexes (météo, drapeaux, statuts, messages, circuit)](#8-données-annexes-météo-drapeaux-statuts-messages-circuit)
9. [Le cache (`fastf1.Cache`)](#9-le-cache-fastf1cache)
10. [Module `plotting`](#10-module-plotting)
11. [Module `ergast`](#11-module-ergast)
12. [Sources de données de FastF1](#12-sources-de-données-de-fastf1)
13. [Synthèse : inventaire du « contenu » FastF1](#13-synthèse--inventaire-du-contenu-fastf1)
14. [Transposition à l'endurance (Al Kamel)](#14-transposition-à-lendurance-al-kamel)
15. [Cartographie de l'API cible EndurancePy](#15-cartographie-de-lapi-cible-endurancepy)

---

## 1. Philosophie et architecture de FastF1

FastF1 expose les données de Formule 1 (timing, télémétrie, météo, classements,
messages de direction de course) à travers une API Python centrée sur **pandas**.
Les objets de données principaux (`Laps`, `Telemetry`, `SessionResults`) sont des
**sous-classes de `pandas.DataFrame`**, ce qui permet à l'utilisateur de garder
toute la puissance de pandas tout en bénéficiant de méthodes métier (sélection de
tours, accès à la télémétrie, etc.).

Chaîne de valeur typique :

```python
import fastf1

session = fastf1.get_session(2023, 'Monza', 'Q')   # crée l'objet (ne charge rien)
session.load()                                      # télécharge + parse + met en cache
laps = session.laps                                 # Laps (DataFrame enrichi)
fastest = laps.pick_fastest()                       # Lap
tel = fastest.get_telemetry()                       # Telemetry (vitesse, RPM, X/Y…)
```

Principes structurants à reproduire dans EndurancePy :

| Principe FastF1 | Détail | À reproduire ? |
|---|---|---|
| Objets = `DataFrame`/`Series` enrichis | `Laps`/`Lap`, `Telemetry`, `SessionResults`/`DriverResult`, `Event`/`EventSchedule` | **Oui** |
| Chargement paresseux | `get_session()` crée l'objet, `load()` télécharge | **Oui** |
| Cache transparent sur disque | requêtes HTTP + données parsées | **Oui** (indispensable vu le volume endurance) |
| Colonnes toujours présentes | les colonnes existent même si non pertinentes pour la session | **Oui** |
| Méthodes `pick_*` de filtrage | filtrage métier sur les `Laps` | **Oui** (à étendre : classes, voitures, relais) |
| Schéma de colonnes typé | dtypes fixés (`timedelta64[ns]`, `str`, `float64`, `bool`…) | **Oui** |

---

## 2. API de premier niveau (fonctions `fastf1.*`)

Tout est importable directement sous `fastf1.<nom>`. Les fonctions vivent dans
`fastf1.events` ; s'y ajoutent `fastf1.Cache` (depuis `fastf1.req`) et
`fastf1.set_log_level` (depuis `fastf1.logger`).

| Fonction | Signature (simplifiée) | Retour | Rôle |
|---|---|---|---|
| `get_session` | `(year, gp, identifier=None, *, backend=None)` | `core.Session` | Crée une session (ne charge pas les données). `gp` = nom (fuzzy) ou n° de manche ; `identifier` = n°/abréviation/nom de session. |
| `get_event` | `(year, gp, *, backend=None, exact_match=False)` | `events.Event` | Crée un événement (week-end). |
| `get_event_schedule` | `(year, *, include_testing=True, backend=None)` | `events.EventSchedule` | Calendrier complet d'une saison. |
| `get_events_remaining` | `(dt=None, *, include_testing=True, backend=None)` | `events.EventSchedule` | Événements restants après `dt` (par défaut : maintenant, UTC). |
| `get_testing_event` | `(year, test_number, *, backend=None)` | `events.Event` | Événement d'essais (manche 0). |
| `get_testing_session` | `(year, test_number, session_number, *, backend=None)` | `core.Session` | Session d'essais. |
| `set_log_level` | `(level)` | — | Niveau de log global. |

> `backend` (keyword-only) ∈ `'fastf1' | 'f1timing' | 'ergast' | None`. Avec
> `None`, l'ordre par défaut est `'fastf1'` puis repli ; avant 2018, c'est
> toujours `'ergast'`. Le paramètre `force_ergast` est déprécié partout.

**Transposition endurance** : équivalents directs envisagés —
`endurancepy.get_session(year, series, event, session)`,
`get_event(...)`, `get_event_schedule(year, series)`. La grande différence est
l'ajout d'un axe **série** (`'WEC' | 'ELMS' | 'IMSA' | 'ALMS' | 'LMC'`), car
plusieurs championnats coexistent (voir §14-15).

---

## 3. Système d'événements : `Event` et `EventSchedule`

### `EventSchedule` (sous-classe de `DataFrame`)

Calendrier d'une saison ; une ligne = un événement. Découper une ligne renvoie un
`Event`. Colonnes (`_COLUMNS`) :

| Colonne | dtype | Sens |
|---|---|---|
| `RoundNumber` | `int` | N° de manche (0 = essais). |
| `Country` | `str` | Pays. |
| `Location` | `str` | Lieu / localité du circuit. |
| `OfficialEventName` | `str` | Nom officiel (avec sponsors). |
| `EventDate` | `datetime64[ns]` | Date de l'événement (jour de la course). |
| `EventName` | `str` | Nom court. |
| `EventFormat` | `str` | `conventional` / `sprint` / `sprint_shootout` / `sprint_qualifying` / `testing`. |
| `Session1`…`Session5` | `str` | Nom de chaque session (5 créneaux). |
| `Session1Date`…`Session5Date` | `object` | Datetime **local** (tz-aware) de chaque session. |
| `Session1DateUtc`…`Session5DateUtc` | `datetime64[ns]` | Datetime **UTC** (tz-naïf) de chaque session. |
| `F1ApiSupport` | `bool` | Données timing API disponibles (≈ année ≥ 2018). |

Méthodes : `is_testing()` (Series booléenne), `get_event_by_round(round)`,
`get_event_by_name(name, *, exact_match=False)`.

### `Event` (sous-classe de `Series`)

Une ligne du calendrier ; mêmes champs que ci-dessus + attribut `year`.
Méthodes : `is_testing()`, `get_session_name(id)`, `get_session_date(id, utc=False)`,
`get_session(id)`, `get_race()`, `get_qualifying()`, `get_sprint()`,
`get_sprint_shootout()`, `get_sprint_qualifying()`, `get_practice(n)`.

**Formats de week-end F1** (à mémoriser car la logique des « 5 créneaux » est
réutilisable côté endurance, mais avec un contenu différent) :

| `EventFormat` | S1 | S2 | S3 | S4 | S5 |
|---|---|---|---|---|---|
| `conventional` | Practice 1 | Practice 2 | Practice 3 | Qualifying | Race |
| `sprint` (21-22) | Practice 1 | Qualifying | Practice 2 | Sprint | Race |
| `sprint_shootout` (23) | Practice 1 | Qualifying | Sprint Shootout | Sprint | Race |
| `sprint_qualifying` (24+) | Practice 1 | Sprint Qualifying | Sprint | Qualifying | Race |

Abréviations de session : `R`=Race, `Q`=Qualifying, `S`=Sprint,
`SQ`=Sprint Qualifying, `SS`=Sprint Shootout, `FP1/FP2/FP3`=Practice 1/2/3.

**Transposition endurance** : le modèle « événement → N sessions » se transpose
bien. Un week-end WEC type = `Free Practice 1/2/3`, `Qualifying` (souvent
*Hyperpole* en plus), `Race` (6 h, 8 h, 24 h…). Il faudra élargir le jeu
d'abréviations (`FP`, `QP`/`HP` hyperpole, `WU` warm-up, `R`) et autoriser plus
de 5 créneaux (les 24 h du Mans ont de nombreuses sessions). Voir §15.

---

## 4. La `Session` (objet central)

`fastf1.core.Session` est le point d'entrée. La plupart des données ne sont
disponibles **qu'après `load()`**.

### Attributs / propriétés

| Nom | Type | Disponible après | Sens |
|---|---|---|---|
| `event` | `Event` | toujours | Événement associé. |
| `name` | `str` | toujours | Nom de session. |
| `f1_api_support` | `bool` | toujours | Timing/télémétrie disponibles. |
| `date` | `Timestamp` | toujours | Date de la session (UTC). |
| `api_path` | `str` | toujours | Chemin API de base. |
| `session_info` | `dict` | `load` | Infos meeting/session/circuit + identifiants API. |
| `drivers` | `list[str]` | `load` | N° de pilotes ayant participé. |
| `results` | `SessionResults` | `load` | Classement + infos pilotes. |
| `laps` | `Laps` | `load(laps=True)` | Tous les tours, tous pilotes. |
| `total_laps` | `int \| None` | `load(laps=True)` | Nombre de tours prévu (courses). |
| `weather_data` | `DataFrame` | `load(weather=True)` | Données météo (voir §8). |
| `car_data` | `dict[str, Telemetry]` | `load(telemetry=True)` | Télémétrie voiture par n°. |
| `pos_data` | `dict[str, Telemetry]` | `load(telemetry=True)` | Position (X/Y/Z) par n°. |
| `session_status` | `DataFrame` | `load(laps=True)` | Statut de session (voir §8). |
| `track_status` | `DataFrame` | `load(laps=True)` | Statut de piste / drapeaux (voir §8). |
| `race_control_messages` | `DataFrame` | `load(messages=True)` | Messages direction de course (voir §8). |
| `session_start_time` | `Timedelta \| None` | `load(laps=True)` | Heure (temps de session) du départ. |
| `t0_date` | `Timestamp \| None` | `load(telemetry=True)` | Date à `SessionTime = 0`. |

### Méthodes

| Méthode | Signature | Rôle |
|---|---|---|
| `load` | `(*, laps=True, telemetry=True, weather=True, messages=True, livedata=None)` | Télécharge et assemble les données depuis les API supportées. |
| `get_driver` | `(identifier)` | Renvoie un `DriverResult` (par abréviation ou n°). |
| `get_circuit_info` | `()` | `CircuitInfo` (virages, postes de commissaires, rotation de la carte). |

> `load()` mélange volontairement plusieurs sources pour corriger/compléter les
> données. L'erreur temporelle absolue peut atteindre ~10 m lorsqu'on superpose
> la télémétrie de tours différents.

**Transposition endurance** : `Session.load()` est l'équivalent central à
recréer. Côté endurance, `load()` téléchargera et fusionnera les fichiers Al
Kamel (CSV d'analyse, classement, météo, etc.). `car_data`/`pos_data` (télémétrie)
**n'auront pas d'équivalent public** (voir §6 et §14). En revanche `laps`,
`results`, `weather_data`, `track_status` (drapeaux/FCY/SC) et un équivalent
`race_control_messages` sont reproductibles.

---

## 5. `Laps` et `Lap` (données de tours)

### `Laps` (sous-classe de `DataFrame`)

Tableau de tours (multi-pilotes). Attribut de classe
`QUICKLAP_THRESHOLD = 1.07` (règle des 107 %). Découper une ligne donne un `Lap`.

**Colonnes (`_COLUMNS`) — c'est le cœur de l'inventaire à répliquer :**

| Colonne | dtype | Sens | Dispo endurance |
|---|---|---|---|
| `Time` | `timedelta64[ns]` | Temps de session au passage ligne. | ✅ (`ELAPSED`/`HOUR`) |
| `Driver` | `str` | Abréviation pilote. | ⚠️ pilote *du relais* |
| `DriverNumber` | `str` | N° pilote. | ⚠️ → **n° voiture** |
| `LapTime` | `timedelta64[ns]` | Temps au tour. | ✅ (`LAP_TIME`) |
| `LapNumber` | `float64` | N° du tour. | ✅ (`LAP_NUMBER`) |
| `Stint` | `float64` | N° de relais (segment entre arrêts). | ✅ (déductible) |
| `PitOutTime` | `timedelta64[ns]` | Heure de sortie des stands. | ✅ (déductible) |
| `PitInTime` | `timedelta64[ns]` | Heure d'entrée aux stands. | ✅ (`CROSSING_FINISH_LINE_IN_PIT`, `PIT_TIME`) |
| `Sector1Time` | `timedelta64[ns]` | Temps S1. | ✅ (`S1`) |
| `Sector2Time` | `timedelta64[ns]` | Temps S2. | ✅ (`S2`) |
| `Sector3Time` | `timedelta64[ns]` | Temps S3. | ✅ (`S3`) |
| `Sector1SessionTime` | `timedelta64[ns]` | Temps de session au passage du repère S1. | ⚠️ recalculable |
| `Sector2SessionTime` | `timedelta64[ns]` | idem S2. | ⚠️ recalculable |
| `Sector3SessionTime` | `timedelta64[ns]` | idem S3. | ⚠️ recalculable |
| `SpeedI1` | `float64` | Vitesse au point intermédiaire 1 (km/h). | ❌ rarement public |
| `SpeedI2` | `float64` | Vitesse au point intermédiaire 2. | ❌ rarement public |
| `SpeedFL` | `float64` | Vitesse ligne d'arrivée. | ⚠️ partiel |
| `SpeedST` | `float64` | Vitesse au speed-trap. | ✅ (`TOP_SPEED`) |
| `IsPersonalBest` | `bool` | Meilleur tour perso. | ⚠️ recalculable |
| `Compound` | `str` | Gomme (`SOFT`/`MEDIUM`/`HARD`/`INTERMEDIATE`/`WET`…). | ❌ non public |
| `TyreLife` | `float64` | Nombre de tours sur le train. | ❌ non public |
| `FreshTyre` | `bool` | Train neuf. | ❌ non public |
| `Team` | `str` | Écurie. | ✅ (`TEAM`) |
| `LapStartTime` | `timedelta64[ns]` | Temps de session au début du tour. | ✅ recalculable |
| `LapStartDate` | `datetime64[ns]` | Date/heure de début du tour. | ✅ recalculable |
| `TrackStatus` | `str` | Statut de piste pendant le tour (codes concaténés). | ✅ (`FLAG_AT_FL` + drapeaux) |
| `Position` | `float64` | Position pendant le tour. | ✅ (recalculable, **overall + classe**) |
| `Deleted` | `bool \| None` | Tour supprimé. | ⚠️ partiel |
| `DeletedReason` | `str` | Raison de suppression. | ⚠️ partiel |
| `FastF1Generated` | `bool` | Ligne générée/complétée par FastF1. | ✅ (renommer `Generated`) |
| `IsAccurate` | `bool` | Tour jugé fiable (contrôles de cohérence). | ✅ (à réimplémenter) |

> **Champs à AJOUTER pour l'endurance** (non présents dans FastF1 car
> spécifiques) : `CarNumber`, `Class` (Hypercar/LMP2/LMGT3, GTP/GTD…),
> `Manufacturer`, `PositionInClass`, `GapToLeader`, `GapInClass`, `DriverChange`
> (changement de pilote au stand). Voir §14.

**Méthodes d'accès aux données** :

| Méthode | Rôle |
|---|---|
| `telemetry` (cached property) | = `get_telemetry()` (un seul pilote). |
| `get_telemetry(*, frequency=None)` | Fusion car+pos data + canaux calculés. |
| `get_car_data(**kw)` | Tranche de `Session.car_data` pour ces tours. |
| `get_pos_data(**kw)` | Tranche de `Session.pos_data`. |
| `get_weather_data()` | 1 point météo par tour. |

**Méthodes de filtrage (`pick_*`)** — *à reproduire et étendre* :

| Méthode | Rôle |
|---|---|
| `pick_drivers(ids)` | Tours d'un/plusieurs pilotes (abréviation et/ou n°). |
| `pick_teams(names)` | Tours d'une/plusieurs écuries. |
| `pick_laps(numbers)` | Par n° de tour. |
| `pick_fastest(only_by_time=False)` | Tour le plus rapide (par défaut, marqué *personal best*). |
| `pick_quicklaps(threshold=None)` | Tours sous le seuil (107 % par défaut). |
| `pick_compounds(compounds)` | Par gomme. |
| `pick_track_status(status, how='equals')` | Par statut de piste (`equals`/`contains`/`excludes`/`any`/`none`). |
| `pick_wo_box()` | Tours hors entrée/sortie stands. |
| `pick_box_laps(which='both')` | In-laps / out-laps. |
| `pick_not_deleted()` | Tours non supprimés. |
| `pick_accurate()` | Tours fiables (`IsAccurate`). |

> Méthodes dépréciées (singulier → pluriel) : `pick_driver`→`pick_drivers`,
> `pick_team`→`pick_teams`, `pick_lap`→`pick_laps`, `pick_tyre`→`pick_compounds`.

**Méthodes diverses** : `split_qualifying_sessions()` (Q1/Q2/Q3),
`iterlaps(require=None)`, `join`/`merge` (propagent la métadonnée `session`).

> **`pick_*` à AJOUTER pour l'endurance** : `pick_cars(numbers)`,
> `pick_classes(['HYPERCAR', 'LMP2', 'LMGT3'])`, `pick_manufacturers(...)`,
> `pick_stints(...)`, `pick_track_status('FCY'/'SC'/'CODE60')`.

### `Lap` (sous-classe de `Series`)

Un tour unique. Méthodes : `telemetry` (cached), `get_telemetry()`,
`get_car_data()`, `get_pos_data()`, `get_weather_data()` (renvoie une `Series`).

---

## 6. `Telemetry` (télémétrie voiture et position)

`fastf1.core.Telemetry` (sous-classe de `DataFrame`) porte les **canaux haute
fréquence**. Deux origines : *car data* et *position data*, fusionnables.

**Canaux *car data*** (API « Car_Data ») :

| Canal | dtype | Sens |
|---|---|---|
| `Date` | `datetime64` | Horodatage absolu. |
| `Time` | `timedelta64` | Temps depuis le 1er échantillon de la tranche. |
| `SessionTime` | `timedelta64` | Temps de session. |
| `RPM` | `int` | Régime moteur. |
| `Speed` | `int` | Vitesse (km/h). |
| `nGear` | `int` | Rapport engagé (0–8). |
| `Throttle` | `int` | Accélérateur (0–100 %). |
| `Brake` | `bool` | Frein appuyé. |
| `DRS` | `int` | Code d'état DRS. |
| `Source` | `str` | `'car'`. |

**Canaux *position data*** (API « Position ») :

| Canal | dtype | Sens |
|---|---|---|
| `Date`, `Time`, `SessionTime` | — | Horodatages. |
| `Status` | `str` | `'OnTrack'` / `'OffTrack'`. |
| `X`, `Y`, `Z` | `int` | Position (1/10 de mètre). |
| `Source` | `str` | `'pos'`. |

**Canaux calculés** (ajoutés par les méthodes) : `Distance`,
`RelativeDistance` (0–1), `DifferentialDistance`, `DriverAhead`,
`DistanceToDriverAhead`.

**Méthodes** : `slice_by_lap()`, `slice_by_time()`, `slice_by_mask()`,
`merge_channels()`, `resample_channels()`, `fill_missing()`,
`add_distance()`, `add_relative_distance()`, `add_differential_distance()`,
`add_driver_ahead()`, `calculate_driver_ahead()`, `get_car_data()`,
`get_pos_data()`.

> ⛔ **Point critique pour EndurancePy** : **il n'existe pas de télémétrie
> publique en endurance** (ni vitesse instantanée, ni RPM, ni rapport, ni
> accélérateur/frein, ni position GPS X/Y/Z). Les archives Al Kamel ne fournissent
> que de la donnée de **timing** (temps au tour, temps de secteurs, vitesse de
> pointe au speed-trap, heures de passage). La classe `Telemetry` de FastF1 n'a
> donc **pas d'équivalent direct**. EndurancePy proposera au mieux une
> télémétrie « dérivée du timing » (profil de temps par secteur, vitesses de
> pointe). C'est la principale limite assumée du projet (voir §14).

---

## 7. `SessionResults` et `DriverResult` (classement)

### `SessionResults` (sous-classe de `DataFrame`)

Indexé par n° de pilote, trié par position. **Toutes les colonnes existent
toujours**, même si non pertinentes.

| Colonne | dtype | Sens | Dispo endurance |
|---|---|---|---|
| `DriverNumber` | `str` | N° pilote. | ⚠️ → **n° voiture** |
| `BroadcastName` | `str` | Nom TV (« P GASLY »). | ✅ |
| `Abbreviation` | `str` | Abréviation 3 lettres. | ⚠️ à générer |
| `DriverId` | `str` | Identifiant Ergast. | ➕ id interne |
| `TeamName` | `str` | Écurie (nom court). | ✅ |
| `TeamColor` | `str` | Couleur écurie (hex). | ⚠️ à constituer |
| `TeamId` | `str` | Identifiant constructeur Ergast. | ➕ id interne |
| `FirstName` / `LastName` / `FullName` | `str` | Identité pilote. | ✅ |
| `HeadshotUrl` | `str` | Portrait. | ❌ rarement public |
| `CountryCode` | `str` | Code pays pilote. | ⚠️ partiel |
| `Position` | `float64` | Position finale (overall). | ✅ |
| `ClassifiedPosition` | `str` | Classement officiel (`R`/`D`/`E`/`W`/`F`/`N` ou n°). | ✅ |
| `GridPosition` | `float64` | Position sur la grille. | ✅ |
| `Q1` / `Q2` / `Q3` | `timedelta64[ns]` | Temps de qualif. | ⚠️ adapter (Hyperpole) |
| `Time` | `timedelta64[ns]` | Temps total de course (si < 1 tour du leader). | ✅ |
| `Status` | `str` | État final (`Finished`, `+ 1 Lap`, `Crash`…). | ✅ |
| `Points` | `float64` | Points marqués. | ✅ |
| `Laps` | `float64` | Nombre de tours parcourus. | ✅ |

> **Colonnes à AJOUTER pour l'endurance** : `Class`, `PositionInClass`,
> `ClassifiedPositionInClass`, `Manufacturer`, `CarNumber`, et une notion
> d'**équipage** (liste des pilotes par voiture, car le « résultat » porte sur la
> voiture, pas sur un pilote unique). Voir §14.

### `DriverResult` (sous-classe de `Series`)

Une ligne de `SessionResults`. Propriété `dnf` (booléen : `True` si abandon).

> Côté endurance, l'unité de classement est la **voiture/équipage**, pas le
> pilote. EndurancePy aura probablement un `CarResult` (et un mapping
> voiture→pilotes), tout en gardant la compatibilité de nommage avec FastF1.

---

## 8. Données annexes (météo, drapeaux, statuts, messages, circuit)

### `weather_data` (`fastf1.api.weather_data`)

| Colonne | Unité | Sens |
|---|---|---|
| `Time` | timedelta | Temps de session. |
| `AirTemp` | °C | Température air. |
| `Humidity` | % | Humidité. |
| `Pressure` | mbar | Pression. |
| `Rainfall` | bool | Pluie. |
| `TrackTemp` | °C | Température piste. |
| `WindDirection` | ° (0–359) | Direction du vent. |
| `WindSpeed` | m/s | Vitesse du vent. |

→ **Reproductible** : Al Kamel publie des rapports météo (souvent PDF, parfois
exploitables) avec les mêmes grandeurs.

### `track_status` (`fastf1.api.track_status_data`)

Codes : `1` AllClear (vert), `2` Yellow, `4` SafetyCar, `5` Red, `6` VSC
deployed, `7` VSC ending (+ message). → **Reproductible et même enrichi** :
l'endurance a Green Flag, Full Course Yellow (FCY), Safety Car, **Code 60**,
*slow zones*, Red Flag, Checkered.

### `session_status` (`fastf1.api.session_status_data`)

`Started` / `Finished` / `Finalised` / `Ends` / `Aborted` / `Inactive`. →
**Reproductible**.

### `race_control_messages` (`fastf1.api.race_control_messages`)

Colonnes : `Time`, `Category` (`Flag`/`SafetyCar`/`Drs`/`CarEvent`/`Other`),
`Message`, `Status`, `Flag`, `Scope` (`Track`/`Sector`/`Driver`), `Sector`,
`RacingNumber`, `Lap`. → **Partiellement reproductible** : la WEC publie des
décisions de commissaires / messages de course, mais le format est moins
structuré qu'en F1 (souvent PDF). À traiter en *best-effort*.

### `CircuitInfo` (`fastf1.mvapi.CircuitInfo`)

`corners`, `marshal_lights`, `marshal_sectors` (DataFrames X/Y/numéro…),
`rotation` (angle de la carte). Sert à annoter les tracés. → **Optionnel /
phase ultérieure** (données à constituer manuellement, comme chez FastF1).

---

## 9. Le cache (`fastf1.Cache`)

Cache à deux étages, **activé par défaut** :
1. Cache HTTP brut (SQLite, `fastf1_http_cache.sqlite`, expiration ~12 h).
2. Cache des données parsées (fichiers pickle `.ff1pkl`).

Répertoire : appel à `enable_cache`, sinon `FASTF1_CACHE`, sinon défaut OS
(`~/.cache/fastf1` sous Linux).

Méthodes de classe : `enable_cache(cache_dir, ignore_version=False, force_renew=False, use_requests_cache=True)`,
`clear_cache(cache_dir=None, deep=False)`, `get_cache_info()`,
`disabled()` (context manager), `set_disabled()`, `set_enabled()`,
`offline_mode(enabled)`, `ci_mode(enabled)`.

→ **À reproduire intégralement.** Le cache est encore plus important en
endurance : un fichier d'analyse de 24 h contient des dizaines de milliers de
tours ; le re-téléchargement/re-parsing doit être évité.

---

## 10. Module `plotting`

Aides à la visualisation matplotlib. Principales fonctions : `setup_mpl()`,
`get_driver_color()`, `get_driver_style()`, `get_team_color()`,
`get_compound_color()`, `get_driver_name()`, `get_driver_abbreviation()`,
`get_team_name()`, `list_team_names()`, `list_driver_abbreviations()`,
`list_compounds()`, `add_sorted_driver_legend()`, et la table
`COMPOUND_COLORS`.

→ **À reproduire et adapter** : couleurs par **constructeur/écurie** et par
**classe** (Hypercar/LMP2/LMGT3…), plutôt que par pilote. Pas de couleurs de
gommes (non publiques en endurance).

---

## 11. Module `ergast`

`fastf1.ergast.Ergast` est un client de l'API Ergast/Jolpica (base de données
historique F1). Méthodes typiques : `get_seasons`, `get_race_schedule`,
`get_driver_standings`, `get_constructor_standings`, `get_race_results`,
`get_qualifying_results`, `get_sprint_results`, `get_lap_times`, `get_pit_stops`,
`get_driver_info`, `get_constructor_info`, `get_circuits`, `get_finishing_status`.
Retourne des réponses paginées (`ErgastSimpleResponse` / `ErgastMultiResponse`).

→ **Pas d'équivalent unique en endurance** : il n'existe pas d'« Ergast de
l'endurance ». Les **classements de championnat** (pilotes, équipes,
constructeurs) devront être soit scrappés des sites officiels, soit recalculés à
partir des résultats. Candidat pour une phase ultérieure : un module
`endurancepy.standings`.

---

## 12. Sources de données de FastF1

| Source | Contenu | Backend |
|---|---|---|
| **F1 Live Timing API** (`livetiming.formula1.com`, SignalR) | Timing, télémétrie, position, météo, messages. | `fastf1` / `f1timing` |
| **Ergast / Jolpica** | Historique : calendriers, résultats, classements, temps au tour, arrêts. | `ergast` |

→ Côté endurance, la source primaire sera les **archives Al Kamel** (fichiers de
résultats CSV/PDF par session) et, en complément, les portails officiels
(fiawec.com, elms… , imsa.com). Détail en §14.

---

## 13. Synthèse : inventaire du « contenu » FastF1

Vue d'ensemble du « contenu » à viser, avec verdict de faisabilité endurance :

| Brique FastF1 | Contenu | Faisable endurance ? |
|---|---|---|
| Calendrier (`EventSchedule`/`Event`) | Manches, sessions, dates. | ✅ Oui |
| Session (`Session.load`) | Orchestration du chargement. | ✅ Oui |
| Classement (`SessionResults`) | Positions, temps, points, grille, statut. | ✅ Oui (+ classe/équipage) |
| Tours (`Laps`/`Lap`) | Temps au tour, secteurs, relais, pit, statut piste. | ✅ Oui (cœur de la donnée Al Kamel) |
| Filtrage `pick_*` | Sélection métier des tours. | ✅ Oui (+ classes/voitures) |
| Météo (`weather_data`) | Temp/hum/pression/pluie/vent. | ✅ Oui (best-effort) |
| Statut piste / drapeaux | Vert/jaune/SC/VSC/rouge. | ✅ Oui (+ FCY/Code 60) |
| Messages course | Direction de course. | ⚠️ Partiel (PDF) |
| Cache | 2 étages, transparent. | ✅ Oui (indispensable) |
| Plotting | Couleurs/styles. | ✅ Oui (par classe/écurie) |
| **Télémétrie (`Telemetry`)** | **Vitesse/RPM/gear/throttle/brake/GPS.** | ❌ **Non public** |
| **Ergast (historique)** | **Standings, archives normalisées.** | ⚠️ À reconstruire |

**Conclusion** : ~80 % du « contenu » FastF1 est reproductible pour l'endurance.
Les deux manques structurels sont (1) la **télémétrie voiture/position** (aucune
source publique) et (2) une base **historique normalisée** type Ergast (à
reconstruire à partir des archives). Tout le reste — calendriers, sessions,
classements, tours/secteurs/relais/pit, météo, drapeaux, cache, plotting — est à
portée à partir des archives Al Kamel.

---

## 14. Transposition à l'endurance (Al Kamel)

> ⏳ *Section en cours de consolidation : les en-têtes exacts du CSV d'analyse Al
> Kamel et les URL des portails sont en cours de vérification par une recherche
> dédiée ; elle sera affinée à son retour. Le contenu ci-dessous reflète l'état
> actuel des connaissances et sera corrigé si besoin.*

### 14.1 Spécificités de l'endurance vs F1 (impact sur le modèle de données)

| Aspect | F1 | Endurance | Conséquence modèle |
|---|---|---|---|
| Unité classée | Pilote | **Voiture / équipage** | Ajouter `CarNumber`, `Crew` (2–4 pilotes), classement par voiture. |
| Catégories | Mono-classe | **Multi-classes** (WEC : Hypercar/LMP2/LMGT3 ; IMSA : GTP/LMP2/GTD Pro/GTD ; ELMS : LMP2/LMP3/LMGT3) | Ajouter `Class`, `PositionInClass`, `GapInClass`. |
| Pilotes/voiture | 1 | **Plusieurs** | `Driver` = pilote *du tour/relais* ; gérer les changements de pilote. |
| Durée | ~90 min | **6 h / 8 h / 10 h / 24 h** | Classement **par heure** ; volumes de tours énormes (cache crucial). |
| Neutralisations | SC / VSC | **SC, FCY, Code 60, slow zones** | Étendre les statuts de piste. |
| Performance | — | **Balance of Performance (BoP)** | Métadonnée optionnelle par voiture. |
| Constructeur | Écurie | **Manufacturer** distinct de l'équipe | Ajouter `Manufacturer`. |

### 14.2 Source de données : archives Al Kamel

Al Kamel Systems assure le chronométrage de la WEC, l'ELMS, l'Asian Le Mans
Series et la Le Mans Cup (IMSA utilise un dispositif distinct — à confirmer).
Pour chaque session, un portail de résultats publie des fichiers téléchargeables.
Le plus précieux est le **CSV d'analyse** (« Analysis »), une ligne par tour et
par voiture, qui contient l'essentiel de ce dont EndurancePy a besoin.

*En-têtes pressentis du CSV d'analyse (à confirmer)* : `NUMBER`,
`DRIVER_NUMBER`, `LAP_NUMBER`, `LAP_TIME`, `LAP_IMPROVEMENT`,
`CROSSING_FINISH_LINE_IN_PIT`, `S1/S2/S3` (+ `_IMPROVEMENT`), `KPH`, `ELAPSED`,
`HOUR`, `TOP_SPEED`, `DRIVER_NAME`, `PIT_TIME`, `CLASS`, `GROUP`, `TEAM`,
`MANUFACTURER`, `FLAG_AT_FL`. → mapping vers les colonnes `Laps` du §5.

### 14.3 Tableau de correspondance (cible)

| Concept FastF1 | Équivalent EndurancePy | Source endurance |
|---|---|---|
| `get_session(year, gp, id)` | `get_session(year, series, event, session)` | Portail Al Kamel |
| `EventSchedule` | `EventSchedule` (+ `Series`) | Calendriers officiels |
| `Session.results` | `SessionResults` (+ classe/équipage) | Classement (CSV/PDF) |
| `Session.laps` | `Laps` (+ classe/voiture/manufacturer) | **CSV d'analyse** |
| `Lap.get_telemetry()` | — (indisponible) | ❌ pas de source |
| `weather_data` | `weather_data` | Rapport météo |
| `track_status` | `track_status` (+ FCY/Code 60) | Drapeaux / `FLAG_AT_FL` |
| `Cache` | `Cache` | local |
| `plotting` | `plotting` (couleurs par classe/écurie) | table interne |
| `ergast` | `standings` (recalcul) | recalcul/scraping |

---

## 15. Cartographie de l'API cible EndurancePy

Esquisse d'API (phase 2 — **non implémentée**, ce document précède le code) :

```python
import endurancepy as ep

# Calendrier d'une saison pour une série
sched = ep.get_event_schedule(2024, series='WEC')

# Une session précise
session = ep.get_session(2024, series='WEC', event='Le Mans', session='Race')
session.load()                         # télécharge + parse les fichiers Al Kamel

# Classement (par voiture / par classe)
session.results                        # SessionResults
session.results.pick_classes('HYPERCAR')

# Tours
laps = session.laps                    # Laps
laps.pick_cars(['7', '8'])             # par n° de voiture
laps.pick_classes('LMGT3')             # par catégorie
laps.pick_drivers('HARTLEY')           # par pilote (relais)
fastest = laps.pick_fastest()          # meilleur tour

# Données annexes
session.weather_data
session.track_status                   # vert / FCY / SC / code 60 / rouge
```

**Modules cibles** (miroir de FastF1) :

| Module FastF1 | Module EndurancePy | Statut |
|---|---|---|
| `fastf1` (API top-level) | `endurancepy` | À créer |
| `fastf1.core` (`Session`/`Laps`/`Lap`) | `endurancepy.core` | À créer |
| `fastf1.events` (`Event`/`EventSchedule`) | `endurancepy.events` | À créer |
| `fastf1.req` (`Cache`) | `endurancepy.cache` | À créer |
| `fastf1.api` (parseurs) | `endurancepy.alkamel` (+ parseurs) | À créer |
| `fastf1.plotting` | `endurancepy.plotting` | À créer |
| `fastf1.ergast` | `endurancepy.standings` | Ultérieur |
| `fastf1.core.Telemetry` | — | Sans objet (pas de source) |

---

*Document de référence — à mettre à jour au fil de l'avancement. La phase 2
(implémentation) commencera une fois cette base validée.*
