# Fonctionnalites ajoutees

Cette mise a jour ajoute les neuf axes qui manquaient a l'application pour une demonstration PFE plus complete.

## 1. Navigation

- Ajout des entrees `Regles` et `ML` dans la barre de navigation principale.

## 2. Exports

- Export CSV des machines.
- Export CSV des alertes.
- Export CSV des interventions.
- Rapport PDF simple pour une machine.
- Rapport PDF simple pour une alerte.

## 3. Graphiques

- Ajout d'une carte thermique des risques sur le dashboard.
- Ajout de barres visuelles pour l'importance des variables ML.
- Ajout d'une visualisation de calibration.
- Ajout de cartes de comparaison des meilleurs benchmarks.

## 4. Notifications

- Ajout d'une table `notifications`.
- Creation de notifications lors de la generation, de l'escalade et de la prise en charge d'une alerte.
- Affichage des notifications dans la barre superieure.
- Support des notifications navigateur si l'utilisateur les autorise.

## 5. Interventions

- Ajout de la priorite.
- Ajout de la date prevue.
- Ajout des pieces utilisees.
- Ajout du cout estime.
- Selection d'un technicien actif au lieu d'un simple champ ID.

## 6. Jobs d'ingestion

- Ajout d'une table de logs des jobs.
- Journalisation des creations, demarrages, arrets, executions, erreurs et fins de jobs.
- Consultation des logs depuis la page `Operations`.

## 7. ML avance

- Ajout d'un endpoint de registre modele.
- Affichage visuel des importances globales.
- Cartes de synthese des benchmarks gagnants.
- Visualisation des bins de calibration.

## 8. Securite

- Blocage des comptes inactifs a la connexion.
- Endpoint de politique de mot de passe.
- Changement de mot de passe par l'utilisateur connecte.
- Reinitialisation du mot de passe par l'administrateur.
- Indicateur `password_reset_required`.

## 9. Tests

- Ajout d'un test de politique de mot de passe.
- Ajout d'un test du generateur PDF minimal.
