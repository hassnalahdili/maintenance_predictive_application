# Guide complet des pages de l'application

Ce document explique, page par page, ce que fait l'interface utilisateur de l'application, comment elle fonctionne, et pourquoi chaque bouton, formulaire et bloc d'affichage existe.

## 1. Vue d'ensemble de l'interface

L'interface React est structurée autour de huit pages principales :

1. `Connexion`
2. `Dashboard`
3. `Machines`
4. `Regles`
5. `Alertes`
6. `Operations`
7. `ML`
8. `Utilisateurs`

Toutes les pages, sauf `Connexion`, sont protegees par authentification.

## 2. Barre de navigation

La barre de navigation apparait en haut de l'application.

### Nom de l'application

- **Maintenance Predictive**
- **Ce que cela fait** : identifie visuellement l'application.
- **Comment** : simple titre dans le `Layout`.
- **Pourquoi** : donner un repere constant a l'utilisateur.

### Boutons de navigation

Les boutons visibles apres connexion sont :

- `Dashboard`
- `Machines`
- `Regles`
- `Alertes`
- `Operations`
- `ML`
- `Utilisateurs` : visible seulement pour le role `admin`

#### Ce que fait chaque bouton

- **Ce que cela fait** : change de page dans l'application.
- **Comment** : utilise le routage React (`react-router-dom`).
- **Pourquoi** : permettre a l'utilisateur de naviguer rapidement entre supervision, exploitation et analyse ML.

### Puce utilisateur

- **Ce que cela affiche** : `Nom complet • role`
- **Comment** : les informations viennent du contexte d'authentification.
- **Pourquoi** : rappeler a l'utilisateur avec quel compte il travaille et quel niveau de droit est actif.

### Bouton `Connexion`

- **Quand il apparait** : si aucun token n'est present.
- **Ce que cela fait** : ouvre la page de connexion.
- **Pourquoi** : point d'entree pour les utilisateurs non connectes.

### Bouton `Deconnexion`

- **Quand il apparait** : quand l'utilisateur est authentifie.
- **Ce que cela fait** : supprime le token et l'utilisateur du `localStorage`, puis deconnecte la session.
- **Comment** : appelle `logout()` dans `AuthContext`.
- **Pourquoi** : fermer proprement la session et proteger l'acces.

## 3. Gestion de l'acces et des roles

### Protection des pages

- **Ce que cela fait** : si l'utilisateur n'est pas connecte, il est renvoye vers `/login`.
- **Comment** : composant `ProtectedRoute`.
- **Pourquoi** : empecher l'acces aux pages sensibles sans authentification.

### Restriction par role

- La page `Utilisateurs` est reservee a `admin`.
- Certaines actions dans les pages sont limitees :
  - `Machines` : gestion reservee a `admin`, `technicien`, `expert`
  - `Suppression machine` : reservee a `admin`
  - `Regles` : creation, edition et activation reservees a `admin`, `expert`
  - `Alertes` : accuse de reception reserve a `admin`, `technicien`

## 4. Page `Connexion`

### Objectif

Permettre a un utilisateur d'ouvrir une session pour acceder au reste de l'application.

### Champs du formulaire

#### Champ `Email`

- **Ce que cela fait** : saisit l'identifiant de connexion.
- **Comment** : la valeur est stockee dans l'etat React, puis envoyee a l'API de login.
- **Pourquoi** : identifier l'utilisateur.

#### Champ `Mot de passe`

- **Ce que cela fait** : saisit le mot de passe.
- **Comment** : champ de type `password` pour masquer les caracteres.
- **Pourquoi** : securiser la saisie.

### Bouton `Se connecter`

- **Ce que cela fait** : envoie l'email et le mot de passe a l'API.
- **Comment** : `POST /api/auth/login`, puis enregistrement du token et du profil utilisateur dans `localStorage`.
- **Pourquoi** : demarrer la session et autoriser l'acces au systeme.

### Etat `Connexion...`

- **Ce que cela fait** : remplace temporairement le texte du bouton pendant l'appel API.
- **Pourquoi** : informer l'utilisateur qu'une action reseau est en cours.

### Alerte d'erreur

- **Ce que cela affiche** : message d'erreur si la connexion echoue.
- **Pourquoi** : expliquer clairement pourquoi l'entree dans l'application a echoue.

## 5. Page `Dashboard`

### Objectif

Donner une vue de supervision globale de l'etat du parc machines, des risques et des alertes.

### Fonctionnement general

- Le dashboard charge les donnees au demarrage.
- Il se rafraichit automatiquement toutes les `30 secondes`.
- Il ecoute aussi le WebSocket live pour recharger la synthese quand un evenement arrive.

### En-tete du dashboard

#### Titre `Dashboard de supervision`

- **Pourquoi** : indiquer que l'on se trouve sur l'ecran de pilotage central.

#### Puce `Live connected / disconnected / error`

- **Ce que cela fait** : affiche l'etat du flux temps reel.
- **Comment** : depend de l'etat du WebSocket.
- **Pourquoi** : rassurer l'utilisateur sur le fait que l'ecran est bien branche au flux live.

#### Puce `Dernier evenement`

- **Ce que cela fait** : montre le dernier type d'evenement recu.
- **Pourquoi** : rendre visible l'activite temps reel.

### Filtres

#### Filtre `Type machine`

- **Ce que cela fait** : limite l'affichage a un type de machine.
- **Comment** : recharge `/api/dashboard/summary` avec `machine_type`.
- **Pourquoi** : analyser un sous-ensemble du parc.

#### Filtre `Niveau de risque`

- **Ce que cela fait** : garde seulement les machines correspondant au niveau choisi.
- **Pourquoi** : focaliser l'attention sur les equipements critiques.

#### Filtre `Site`

- **Ce que cela fait** : filtre les machines par site industriel.
- **Pourquoi** : analyser un lieu ou une implantation specifique.

### Texte `Rafraichissement automatique toutes les 30 secondes`

- **Pourquoi** : expliquer le comportement dynamique de la page.

### Cartes KPI

#### Carte `Machines totales`

- **Ce que cela affiche** : nombre total de machines visibles avec les filtres actifs.
- **Pourquoi** : connaitre la taille du perimetre surveille.

#### Carte `Alertes actives`

- **Ce que cela affiche** : nombre d'alertes encore ouvertes.
- **Pourquoi** : mesurer le volume de situations a traiter.

#### Carte `Machines a risque`

- **Ce que cela affiche** : nombre de machines ayant un risque significatif.
- **Pourquoi** : estimer rapidement la charge de surveillance.

### Bloc `Distribution des statuts`

- **Ce que cela affiche** : repartition des statuts machine avec barres de progression.
- **Comment** : utilise `status_distribution`.
- **Pourquoi** : voir si le parc est globalement sain, degrade ou critique.

### Bloc `Evolution des probabilites de panne`

- **Ce que cela affiche** : historique recent de probabilite moyenne et maximale.
- **Comment** : liste chronologique avec barres de progression.
- **Pourquoi** : suivre l'evolution du risque dans le temps.

### Bloc `Etat de sante des machines`

- **Ce que cela affiche** : une carte par machine avec :
  - nom
  - type
  - site
  - statut
  - niveau de risque
  - probabilite de panne
- **Pourquoi** : donner une vue terrain rapide machine par machine.

## 6. Page `Machines`

### Objectif

Gerer le parc machines, consulter leur detail complet, et simuler des predictions.

### Formulaire de creation / edition

Le meme formulaire sert a creer une machine ou a modifier une machine existante.

#### Champ `Nom`

- **Ce que cela fait** : nomme la machine.
- **Pourquoi** : identifier clairement l'equipement dans toutes les autres pages.

#### Champ `Type`

- **Ce que cela fait** : choisit le type de machine parmi :
  - moteur
  - pompe
  - convoyeur
  - compresseur
  - ventilateur
  - generateur
  - broyeur
  - four
- **Pourquoi** : adapter les regles metier, les analyses et les datasets.

#### Champs `Site`, `Zone`, `Ligne`, `Composant`

- **Ce que cela fait** : rattache la machine a une hierarchie industrielle.
- **Pourquoi** : mieux representer un contexte reel d'usine.

#### Champ `Statut`

- **Ce que cela fait** : stocke l'etat metier courant de la machine.
- **Pourquoi** : qualifier rapidement la machine dans le parc.

#### Champ `Notes`

- **Ce que cela fait** : ajoute des remarques libres.
- **Pourquoi** : conserver un contexte humain ou operationnel.

### Bouton `Ajouter`

- **Ce que cela fait** : cree une nouvelle machine.
- **Comment** : `POST /api/machines/`.
- **Pourquoi** : enrichir le parc machines.

### Bouton `Mettre a jour`

- **Ce que cela fait** : enregistre les modifications sur une machine existante.
- **Comment** : `PUT /api/machines/{id}`.
- **Pourquoi** : maintenir les informations machine a jour.

### Bouton `Annuler`

- **Ce que cela fait** : quitte le mode edition et remet le formulaire a zero.
- **Pourquoi** : eviter d'enregistrer par erreur une modification non voulue.

### Tableau `Parc machines`

#### Colonnes affichees

- `ID`
- `Nom`
- `Type`
- `Hierarchie`
- `Statut`
- `Actions`

#### Pourquoi ce tableau existe

- fournir une liste exploitable du parc
- permettre des actions directes sur chaque machine
- conserver une lecture compacte et operationnelle

### Bouton `Detail`

- **Ce que cela fait** : ouvre une fenetre detaillee sur la machine.
- **Comment** : `GET /api/machines/{id}`.
- **Pourquoi** : consulter l'historique complet sans quitter la page.

### Bouton `Simuler`

- **Ce que cela fait** : genere une prediction simulee pour la machine.
- **Comment** : `POST /api/predictions/simulate/{machine_id}?drift=true&persist=true`.
- **Pourquoi** : tester le comportement de la machine dans l'application, alimenter l'historique et montrer une dynamique meme sans capteur reel.

### Bouton `Editer`

- **Ce que cela fait** : charge la machine selectionnee dans le formulaire.
- **Pourquoi** : faciliter la mise a jour sans retaper toutes les informations.

### Bouton `Supprimer`

- **Ce que cela fait** : supprime logiquement la machine apres confirmation.
- **Comment** : `DELETE /api/machines/{id}`.
- **Pourquoi** : retirer une machine du parc sans effacer forcement toute sa valeur historique metier.

### Pagination

#### Controle de page

- **Ce que cela fait** : change de page dans la liste.
- **Pourquoi** : garder une interface lisible quand le parc devient grand.

#### Controle `rows per page`

- **Ce que cela fait** : change le nombre de lignes affichees.
- **Pourquoi** : adapter l'affichage au besoin utilisateur.

### Fenetre `Detail machine`

#### Bloc `Hierarchie industrielle`

- **Ce que cela affiche** : site, zone, ligne, composant.
- **Pourquoi** : rappeler le contexte physique de l'equipement.

#### Bloc `Historique capteurs`

- **Ce que cela affiche** : mesures capteur datees.
- **Pourquoi** : verifier les signaux recents et interpretable les comportements de la machine.

#### Bloc `Historique predictions`

- **Ce que cela affiche** : risque, probabilite, RUL.
- **Pourquoi** : suivre l'evolution du modele sur la machine.

#### Bloc `Historique alertes`

- **Ce que cela affiche** : date, niveau, statut, message.
- **Pourquoi** : comprendre quand et pourquoi la machine a ete signalee.

#### Bloc `Interventions`

- **Ce que cela affiche** : interventions terrain reliees a la machine.
- **Pourquoi** : relier prediction, alerte et action humaine.

## 7. Page `Regles`

### Objectif

Definir, tester, historiser et activer les regles metier qui enrichissent la logique de maintenance predictive.

### Formulaire de creation / edition

#### Champ `Nom`

- **Ce que cela fait** : donne un nom metier a la regle.
- **Pourquoi** : faciliter la lecture et la gouvernance des regles.

#### Champ `Type machine`

- **Ce que cela fait** : limite la regle a un type de machine.
- **Pourquoi** : eviter d'appliquer une meme logique a des equipements non comparables.

#### Champ `Metrique`

- **Ce que cela fait** : choisit la variable capteur surveillee.
- **Pourquoi** : definir la source du controle.

#### Champ `Operateur`

- **Ce que cela fait** : choisit la comparaison a appliquer.
- **Pourquoi** : formaliser la condition de declenchement.

#### Champ `Seuil`

- **Ce que cela fait** : fixe la valeur limite.
- **Pourquoi** : transformer la connaissance metier en regle executable.

#### Champ `Duree (s)`

- **Ce que cela fait** : permet d'exprimer une persistance dans le temps.
- **Pourquoi** : eviter de declencher sur un pic trop court.

#### Champ `Severite`

- **Ce que cela fait** : qualifie l'importance de la regle.
- **Pourquoi** : ponderer la criticite dans les analyses.

#### Champ `Confiance`

- **Ce que cela fait** : donne un poids ou niveau de confiance a la regle.
- **Pourquoi** : enrichir les features transmises au modele ML.

### Bouton `Ajouter`

- **Ce que cela fait** : cree une nouvelle regle.
- **Comment** : `POST /api/rules/`.
- **Pourquoi** : enrichir la base de connaissance metier.

### Bouton `Mettre a jour`

- **Ce que cela fait** : modifie une regle existante.
- **Comment** : `PUT /api/rules/{id}`.
- **Pourquoi** : faire evoluer une regle avec le retour terrain.

### Bouton `Annuler`

- **Ce que cela fait** : annule l'edition.
- **Pourquoi** : retrouver un formulaire propre.

### Tableau `Catalogue des regles`

#### Colonnes

- `Nom`
- `Type`
- `Condition`
- `Severite`
- `Version`
- `Etat`
- `Actions`

#### Pourquoi ce tableau existe

- donner une vue gouvernance des regles
- montrer l'etat actif / inactif
- conserver la notion de version

### Bouton `Tester`

- **Ce que cela fait** : simule la regle sur l'historique.
- **Comment** : `GET /api/rules/{id}/simulate`.
- **Pourquoi** : mesurer l'effet de la regle avant de lui faire confiance en production.

### Bouton `Versions`

- **Ce que cela fait** : ouvre l'historique des versions de la regle.
- **Comment** : `GET /api/rules/{id}/versions`.
- **Pourquoi** : assurer une tracabilite des changements.

### Bouton `Editer`

- **Ce que cela fait** : recharge la regle dans le formulaire.
- **Pourquoi** : faciliter la maintenance des regles.

### Bouton `Activer` / `Desactiver`

- **Ce que cela fait** : change l'etat de la regle.
- **Comment** : `POST /api/rules/{id}/toggle`.
- **Pourquoi** : permettre des tests, des retraits temporaires ou une mise en service progressive.

### Fenetre `Simulation de regle`

- **Ce que cela affiche** :
  - nombre total d'enregistrements analyses
  - nombre de correspondances
  - taux de correspondance
  - dernieres lignes ayant declenche la regle
- **Pourquoi** : evaluer la pertinence pratique d'une regle.

### Fenetre `Historique des versions`

- **Ce que cela affiche** : les versions successives et leur snapshot.
- **Pourquoi** : justifier les evolutions et retrouver un etat precedent.

## 8. Page `Alertes`

### Objectif

Lister les alertes de maintenance predictive et permettre leur accuse de reception.

### Filtres

#### Filtre `Statut`

- **Ce que cela fait** : affiche seulement les alertes actives, accusees ou escaladees.
- **Pourquoi** : aider les equipes a traiter les alertes par etat.

#### Filtre `Niveau`

- **Ce que cela fait** : filtre les alertes par criticite.
- **Pourquoi** : prioriser les interventions.

### Rafraichissement

- **Ce que cela fait** : recharge automatiquement les alertes toutes les `30 secondes`.
- **Pourquoi** : garder une vue quasi temps reel meme sans action utilisateur.

### Tableau des alertes

#### Colonnes

- `ID`
- `Machine`
- `Niveau`
- `Probabilite`
- `Statut`
- `Message`
- `Date`
- `Action`

#### Pourquoi ce tableau existe

- centraliser les alertes
- rendre visible la criticite
- permettre une prise en charge rapide

### Bouton `Accuser`

- **Ce que cela fait** : ouvre la fenetre d'accuse de reception.
- **Pourquoi** : marquer qu'un humain a vu et pris en compte l'alerte.

### Fenetre `Accuser reception de l'alerte`

#### Texte du message

- **Ce que cela affiche** : le message original de l'alerte.
- **Pourquoi** : rappeler le contexte avant validation.

#### Champ `Commentaire`

- **Ce que cela fait** : ajoute une note humaine.
- **Pourquoi** : garder une trace de la prise en charge.

#### Bouton `Annuler`

- **Ce que cela fait** : ferme la fenetre sans action.
- **Pourquoi** : laisser l'utilisateur revenir en arriere.

#### Bouton `Valider`

- **Ce que cela fait** : accuse l'alerte avec son commentaire.
- **Comment** : `POST /api/alerts/{id}/acknowledge`.
- **Pourquoi** : tracer la reaction terrain.

## 9. Page `Operations`

### Objectif

Regrouper les fonctions d'exploitation terrain, d'ingestion continue, de suivi des labels et de boucle MLOps.

## 9.1 Bloc `Hierarchie des actifs`

- **Ce que cela affiche** : l'arbre des noeuds `site`, `zone`, `line`, `component`.
- **Comment** : rendu recursif de l'arbre.
- **Pourquoi** : offrir une vision industrielle structuree du patrimoine.

## 9.2 Bloc `Nouvelle intervention terrain`

### Champs du formulaire

#### Champ `Machine`

- **Ce que cela fait** : choisit la machine concernee.
- **Pourquoi** : rattacher l'intervention a un equipement reel.

#### Champ `Technicien ID`

- **Ce que cela fait** : identifie le technicien.
- **Pourquoi** : tracer qui a opere sur le terrain.

#### Champ `Work order`

- **Ce que cela fait** : stocke la reference d'ordre de travail.
- **Pourquoi** : rapprocher l'application d'un processus industriel reel.

#### Champ `Categorie`

- **Valeurs** : inspection, corrective, preventive, calibration
- **Pourquoi** : qualifier la nature de l'intervention.

#### Champ `Statut`

- **Valeurs** : open, in_progress, resolved, cancelled
- **Pourquoi** : suivre l'etat d'avancement.

#### Champ `Label terrain`

- **Valeurs** :
  - under_analysis
  - confirmed_failure
  - false_alarm
  - preventive_maintenance
  - sensor_fault
- **Pourquoi** : fournir des labels utiles au suivi metier et au retraining ML.

#### Champ `Downtime (min)`

- **Ce que cela fait** : renseigne le temps d'arret.
- **Pourquoi** : calculer des metriques metier reelles.

#### Champ `Cause racine`

- **Ce que cela fait** : documente la cause probable.
- **Pourquoi** : enrichir l'analyse de fiabilite.

#### Champ `Action realisee`

- **Ce que cela fait** : decrit ce qui a ete fait.
- **Pourquoi** : conserver la memoire de l'intervention.

### Bouton `Enregistrer intervention`

- **Ce que cela fait** : cree une intervention.
- **Comment** : `POST /api/interventions/`.
- **Pourquoi** : alimenter la boucle exploitation -> label -> ML.

### Bouton `Rafraichir`

- **Ce que cela fait** : recharge les donnees de la page.
- **Pourquoi** : obtenir un etat a jour sans recharger toute l'application.

## 9.3 Bloc `Interventions recentes`

- **Ce que cela affiche** :
  - machine
  - work order
  - statut
  - label terrain
  - downtime
  - date d'ouverture
- **Pourquoi** : donner une synthese rapide des actions terrain.

## 9.4 Bloc `Jobs d ingestion continue`

### Formulaire de creation de job

#### Champ `Machine`

- **Ce que cela fait** : choisit la machine cible.
- **Pourquoi** : associer le job a un equipement.

#### Champ `Mode`

- **Valeurs** : `simulator`, `replay`
- **Pourquoi** :
  - `simulator` : genere des donnees artificielles
  - `replay` : rejoue de vraies donnees issues des datasets

#### Champ `Source replay`

- **Ce que cela fait** : choisit la source de rejeu si le mode est `replay`.
- **Pourquoi** : rapprocher l'interface d'un flux capteur reel.

#### Champ `Intervalle (s)`

- **Ce que cela fait** : fixe la frequence d'injection.
- **Pourquoi** : controler la cadence du flux.

#### Champ `Pas replay`

- **Ce que cela fait** : indique combien de points injecter par cycle.
- **Pourquoi** : ajuster la vitesse de rejeu.

#### Switch `Drift`

- **Ce que cela fait** : active un comportement de derive dans le job.
- **Pourquoi** : simuler une evolution anormale des donnees.

#### Switch `Auto restart`

- **Ce que cela fait** : autorise le redemarrage automatique du job.
- **Pourquoi** : rendre l'ingestion plus robuste.

### Bouton `Creer job`

- **Ce que cela fait** : cree le job d'ingestion.
- **Comment** : `POST /api/ingestion-jobs/`.
- **Pourquoi** : automatiser l'alimentation continue des mesures.

### Tableau des jobs

#### Ce que cela affiche

- machine
- mode
- etat
- derniere execution
- erreurs eventuelles

### Bouton `Start`

- **Ce que cela fait** : demarre un job.
- **Comment** : `POST /api/ingestion-jobs/{id}/start`.
- **Pourquoi** : lancer un flux continu sans intervention manuelle repetee.

### Bouton `Stop`

- **Ce que cela fait** : arrete un job.
- **Comment** : `POST /api/ingestion-jobs/{id}/stop`.
- **Pourquoi** : garder la main sur l'injection de donnees.

## 9.5 Bloc `Boucle ML terrain`

### Carte `Labels terrain`

- **Ce que cela affiche** :
  - nombre total d'interventions
  - repartition des labels
- **Pourquoi** : mesurer la richesse du retour terrain exploitable pour l'apprentissage.

### Carte `Drift des donnees`

- **Ce que cela affiche** :
  - statut global
  - variation de quelques features entre baseline et donnees recentes
- **Pourquoi** : verifier si les donnees actuelles s'ecartent du profil historique.

### Bouton `Actualiser`

- **Ce que cela fait** : recalcule le rapport de drift.
- **Comment** : `GET /api/ml/drift-report`.
- **Pourquoi** : observer rapidement une evolution recente des donnees.

### Carte `Retraining base sur les interventions`

#### Champ `Horizon (heures)`

- **Ce que cela fait** : definit la fenetre temporelle utilisee pour creer les labels.
- **Pourquoi** : controler le sens metier de la prediction.

#### Champ `Minimum d echantillons`

- **Ce que cela fait** : fixe le seuil minimal avant d'autoriser un retraining.
- **Pourquoi** : eviter un entrainement sur trop peu de donnees.

### Bouton `Lancer retraining`

- **Ce que cela fait** : relance un apprentissage a partir des interventions terrain.
- **Comment** : `POST /api/ml/retrain-from-feedback`.
- **Pourquoi** : fermer la boucle entre exploitation et amelioration du modele.

### Texte `Dernier rapport`

- **Ce que cela affiche** : meilleur modele et metrique principale du dernier retraining.
- **Pourquoi** : donner un retour rapide sans ouvrir les fichiers de rapport.

## 10. Page `ML`

### Objectif

Centraliser la partie etude machine learning, benchmarks, explicabilite, calibration et rejeu de donnees reelles.

### En-tete

#### Bouton `Rafraichir l analyse`

- **Ce que cela fait** : recharge l'overview ML et les diagnostics du modele.
- **Comment** : relance les appels `overview` et `model-diagnostics`.
- **Pourquoi** : synchroniser l'affichage apres ajout de donnees ou retraining.

## 10.1 Bloc `Modele en service`

- **Ce que cela affiche** :
  - nom du modele
  - methode de calibration
  - Brier avant / apres
  - ECE avant / apres
  - precision
  - recall
  - F1
  - ROC AUC
- **Pourquoi** : montrer que le modele n'est pas seulement entraine, mais aussi evalue et calibre.

## 10.2 Bloc `Top variables globales`

- **Ce que cela affiche** : les features les plus importantes globalement.
- **Pourquoi** : rendre le modele plus interpretable pour un jury ou un utilisateur metier.

## 10.3 Bloc `Metriques metier`

- **Ce que cela affiche** :
  - alertes totales
  - alertes actives
  - taux d'acquittement
  - taux d'escalade
  - taux de fausses alertes
  - temps moyen d'anticipation
  - downtime moyen
  - couverture des pannes confirmees
- **Pourquoi** : relier le modele a des indicateurs utiles pour l'industrie, pas seulement a des metriques mathematiques.

## 10.4 Bloc `Courbe de calibration`

- **Ce que cela affiche** : bins, effectifs, confiance moyenne, frequence observee.
- **Pourquoi** : verifier si une probabilite de 80 % correspond reellement a environ 80 % de cas positifs.

## 10.5 Bloc `Expliquer la derniere prediction d une machine`

### Champ `Machine`

- **Ce que cela fait** : choisit la machine a expliquer.
- **Pourquoi** : produire une explication locale ciblee.

### Bouton `Expliquer la prediction`

- **Ce que cela fait** : recupere l'explication locale.
- **Comment** : `GET /api/ml/explain/machines/{machine_id}`.
- **Pourquoi** : montrer ce qui a pousse le modele a produire ce score.

### Zone d'explication

- **Ce que cela affiche** :
  - nom de la machine
  - niveau de risque
  - probabilite
  - regles actives
  - facteurs qui augmentent le risque
  - facteurs qui le reduisent
- **Pourquoi** : rendre la prediction interpretable pour l'utilisateur et pour le jury PFE.

## 10.6 Bloc `Rejeu temps reel a partir des datasets reels`

### Champ `Source de rejeu`

- **Ce que cela fait** : choisit un dataset ou sous-jeu de donnees a rejouer.
- **Pourquoi** : utiliser de vraies donnees dans une logique proche du temps reel.

### Champ `Machine cible`

- **Ce que cela fait** : choisit la machine qui recevra les donnees.
- **Pourquoi** : relier le rejeu a un equipement de l'application.

### Champ `Points a injecter`

- **Ce que cela fait** : indique combien de points envoyer a chaque action.
- **Pourquoi** : controler le debit d'injection.

### Bouton `Injecter maintenant`

- **Ce que cela fait** : injecte tout de suite un nombre de points.
- **Comment** : `POST /api/ml/replay/step`.
- **Pourquoi** : tester l'effet du rejeu de facon immediate.

### Bouton `Lancer auto-replay` / `Arreter auto-replay`

- **Ce que cela fait** : active ou coupe une boucle d'injection toutes les 3 secondes.
- **Pourquoi** : simuler un capteur quasi temps reel.

### Bouton `Reinitialiser la source`

- **Ce que cela fait** : remet le curseur de rejeu au debut.
- **Comment** : `POST /api/ml/replay/reset/{source_id}`.
- **Pourquoi** : rejouer a nouveau la serie depuis son origine.

### Texte de progression

- **Ce que cela affiche** : description de la source et position du curseur.
- **Pourquoi** : savoir ou on en est dans la lecture du dataset.

### Alerte de succes

- **Ce que cela affiche** :
  - nombre de points injectes
  - machine cible
  - dernier niveau de risque
  - derniere probabilite
- **Pourquoi** : donner un retour direct sur l'effet de l'injection.

### Tableau `Sources disponibles`

- **Ce que cela affiche** : source, type machine, progression.
- **Pourquoi** : piloter les datasets de rejeu de facon simple.

## 10.7 Bloc `Synthese des benchmarks`

### Cartes de synthese

- **Ce que cela affiche** :
  - datasets detectes
  - datasets prets
  - datasets partiels
  - benchmarks executes
- **Pourquoi** : resumer la maturite du volet PFE.

### Tableau `Catalogue des datasets`

- **Ce que cela affiche** :
  - dataset
  - machines couvertes
  - taches
  - statut
  - note
- **Pourquoi** : documenter les donnees disponibles dans l'application.

### Tableau `Resultats benchmarks`

- **Ce que cela affiche** :
  - dataset
  - tache
  - modele gagnant
  - metrique
  - valeur
- **Pourquoi** : montrer le resultat de la comparaison de modeles.

### Bloc `Recommandations suivantes`

- **Ce que cela affiche** : prochaines actions conseillees pour l'etude ML.
- **Pourquoi** : guider les iterations futures du projet.

## 11. Page `Utilisateurs`

### Objectif

Administrer les comptes et consulter les logs d'audit.

### Formulaire utilisateur

#### Champ `Nom`

- **Ce que cela fait** : nom complet de l'utilisateur.
- **Pourquoi** : identifier clairement le compte.

#### Champ `Email`

- **Ce que cela fait** : adresse de connexion.
- **Pourquoi** : servir d'identifiant.

#### Champ `Mot de passe`

- **Ce que cela fait** : definit ou modifie le mot de passe.
- **Pourquoi** : securiser le compte.

#### Aide `Laisser vide pour conserver le mot de passe actuel`

- **Quand elle apparait** : en mode edition.
- **Pourquoi** : eviter d'ecraser un mot de passe par erreur.

#### Champ `Role`

- **Ce que cela fait** : choisit le role.
- **Pourquoi** : controler les droits de navigation et d'action.

#### Champ `Actif`

- **Ce que cela fait** : active ou desactive le compte.
- **Pourquoi** : permettre de couper un acces sans supprimer l'utilisateur.

### Bouton `Creer`

- **Ce que cela fait** : cree un utilisateur.
- **Comment** : `POST /api/users/`.
- **Pourquoi** : administrer les acces a l'application.

### Bouton `Mettre a jour`

- **Ce que cela fait** : enregistre les modifications sur un utilisateur existant.
- **Comment** : `PUT /api/users/{id}`.
- **Pourquoi** : faire evoluer les droits ou corriger une fiche compte.

### Bouton `Annuler`

- **Ce que cela fait** : quitte le mode edition.
- **Pourquoi** : revenir a un etat propre.

### Tableau `Liste des utilisateurs`

- **Ce que cela affiche** :
  - ID
  - nom
  - email
  - role
  - etat
- **Pourquoi** : superviser rapidement tous les comptes.

### Bouton `Editer`

- **Ce que cela fait** : charge le compte dans le formulaire.
- **Pourquoi** : faciliter la maintenance des utilisateurs.

### Bouton `Supprimer`

- **Ce que cela fait** : supprime un compte apres confirmation.
- **Comment** : `DELETE /api/users/{id}`.
- **Pourquoi** : retirer un acces devenu inutile.

### Tableau `Logs d'audit`

- **Ce que cela affiche** :
  - date
  - utilisateur
  - action
  - type
  - objet
  - details
- **Pourquoi** : tracer les actions sensibles et renforcer la credibilite industrielle du projet.

## 12. Pourquoi cette interface est pertinente pour le PFE

Cette interface ne se limite pas a afficher des donnees. Elle reunit quatre dimensions importantes d'un vrai projet de maintenance predictive :

1. **Supervision** avec le dashboard et les alertes
2. **Exploitation terrain** avec les machines, interventions et jobs
3. **Connaissance metier** avec les regles
4. **Etude machine learning** avec benchmarks, explicabilite, calibration et retraining

## 13. Utilisation conseillee pour une demonstration

Pour une bonne demonstration, l'ordre le plus logique est :

1. se connecter
2. montrer le dashboard live
3. ouvrir une machine puis lancer une simulation
4. verifier l'apparition d'une alerte
5. accuser l'alerte
6. enregistrer une intervention dans `Operations`
7. montrer les diagnostics et l'explication dans `ML`
8. finir par les utilisateurs et les logs d'audit pour montrer la gouvernance

