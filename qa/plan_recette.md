# Plan de tests et de recette

## Objectif

Ce plan permet de mesurer la conformite restante de `predictive_maintenance_app`
par rapport au cahier des charges `cahier_des_charges _r.pdf`, point par point.

Le livrable est compose de :

- une matrice de traceabilite entre exigences et cas de test
- un runner de recette automatise : [run_recette.py](C:/Users/HASSNA/Master/stage/predictive_maintenance_app/predictive_maintenance_app/qa/run_recette.py)
- une checklist manuelle pour les exigences non automatisables proprement

## Prerequis

- Python du projet disponible : `pfe\Scripts\python.exe`
- dependances backend installees dans l'environnement `pfe`
- PostgreSQL accessible sur `localhost:5432`
- ou bien Docker disponible pour lancer la base avec `--start-db`
- port `8010` libre pour l'instance temporaire du backend

## Execution automatique

Depuis la racine du projet :

```powershell
.\pfe\Scripts\python.exe .\qa\run_recette.py --start-db --output .\qa\reports\recette_report.json
```

Le runner :

- demarre le service `db` si necessaire
- lance temporairement le backend sur `http://127.0.0.1:8010`
- execute les cas de recette automatisables
- produit un rapport JSON avec statuts `PASS`, `FAIL`, `SKIP`, `MANUAL`

Le code de retour est :

- `0` si aucun cas automatise ne tombe en echec
- `1` si au moins un cas automatise echoue

## Matrice de traceabilite

| Cas | Source cahier | Exigence verifiee | Mode |
| --- | --- | --- | --- |
| `CA-05` | CA-05 / 6.2 | Authentification JWT fonctionnelle | Auto |
| `CA-01` | OF-02 / CA-01 / 3.2.1 | Dashboard, KPIs, filtres, donnees de supervision | Auto |
| `OF-01A` | 2.3.1 / 6.1 | Creation utilisateur avec role | Auto |
| `OF-01B` | 6.1 / 6.2 | Connexion technicien et normalisation du role | Auto |
| `CA-02` | OF-01 / CA-02 / 3.2.2 | CRUD machines, detail, historique, suppression logique | Auto |
| `CA-06` | OF-05 / CA-06 / 3.2.4 | Creation, simulation, activation, versioning des regles | Auto |
| `CA-03` | OF-03 / CA-03 / 3.2.3 | Generation d'alertes et accusé de reception | Auto |
| `CA-07` | CA-07 / 4.2.2 | Prediction disponible et historisee pour chaque machine | Auto |
| `OF-05` | 6.1 / 6.2 | Logs d'audit et traçabilite securite | Auto |
| `OF-01C` | 2.3.1 / 6.1 | Suppression utilisateur | Auto |
| `CP-02` | OT-01 / CP-02 / 7.1 | Temps de reponse prediction < 200 ms | Auto |
| `CP-01` | CP-01 / 7.1 | Temps de chargement du dashboard < 2 s | Manuel |
| `CP-03` | CP-03 / 7.1 | Concurrence 50 utilisateurs | Manuel |
| `OT-03` | OT-03 / 5.4.1 / CP-04 | Recall du modele >= 80 % | Manuel |
| `OT-04` | OT-04 / CP-05 | Anticipation moyenne >= 7 jours | Manuel |
| `UI-RESP` | 2.3.1 / 3.2.1 | Interface responsive | Manuel |
| `NAV-BROWSERS` | 7.4 | Compatibilite navigateurs | Manuel |

## Ce que mesure le runner automatiquement

### Authentification et roles

- connexion admin
- creation d'un utilisateur `technicien`
- connexion technicien
- verification implicite des droits en creation machine et accuse d'alerte

### Machines

- creation par technicien
- modification par admin
- detail machine avec historiques capteurs, predictions et alertes
- suppression logique

### Regles metier

- creation d'une regle
- simulation sur historique capteurs
- activation/desactivation
- verification du versioning

### Alertes

- ingestion d'une mesure critique
- creation d'une alerte
- accuse de reception avec commentaire

### Predictions

- simulation de prediction persistante
- verification de l'historisation
- mesure de temps moyen de reponse

### Audit

- lecture des logs
- verification de quelques actions structurantes

## Checklist de recette manuelle

### `CP-01` Temps de chargement dashboard

1. Se connecter avec `admin@example.com`
2. Ouvrir `/`
3. Mesurer le chargement initial avec l'onglet Network du navigateur
4. Verifier que le chargement complet reste sous `2 s`

### `UI-RESP` Interface responsive

1. Ouvrir les pages `Dashboard`, `Machines`, `Regles`, `Alertes`
2. Verifier largeur mobile `390 px`
3. Verifier largeur tablette `768 px`
4. Verifier largeur desktop `1440 px`
5. Confirmer absence de debordement horizontal et lisibilite des actions

### `NAV-BROWSERS` Compatibilite navigateurs

1. Chrome
2. Firefox
3. Edge
4. Safari

Pour chacun :

- connexion
- dashboard
- creation machine
- creation regle
- generation et accuse d'alerte

### `CP-03` Charge

1. Lancer le backend en mode normal
2. Utiliser un outil de charge externe
3. Cibler au minimum :
   - `GET /api/dashboard/summary`
   - `GET /api/machines/`
   - `POST /api/predictions/simulate/{machine_id}`
4. Verifier que 50 utilisateurs simultanes ne degradent pas fortement les temps de reponse

### `OT-03` et `OT-04` Qualite IA

1. Preparer un jeu de verite terrain avec dates reelles de panne
2. Evaluer les predictions du modele
3. Calculer :
   - recall
   - precision
   - F1-score
   - AUC-ROC
   - anticipation moyenne en jours
4. Comparer aux seuils du cahier

## Interpretation du rapport JSON

Chaque entree contient :

- `case_id` : identifiant du cas
- `requirement` : exigence verifiee
- `status` : `PASS`, `FAIL`, `SKIP` ou `MANUAL`
- `duration_ms` : duree du test
- `details` : resultat exploitable ou raison d'echec

## Recommandation d'usage

- executer le runner apres chaque lot de corrections backend
- executer la checklist manuelle avant chaque jalon de recette
- conserver les rapports JSON dans `qa/reports/` pour suivre l'evolution de conformite
