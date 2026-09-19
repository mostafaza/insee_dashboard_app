# Dashboard INSEE

Dashboard Streamlit pour explorer des jeux de données XML publiés par l'Insee, filtrer les données, visualiser des graphiques et exporter les résultats en CSV.

## Prérequis

- Git
- Python 3.12
- Un terminal PowerShell ou CMD (Windows)

## Cloner le projet

```bash
git clone <url-du-repo>
cd insee_dashboard_app
```

## Créer un environnement virtuel

Sous Windows PowerShell :

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si tu utilises un autre terminal, adapte la commande d'activation selon ton OS.

## Installer les dépendances

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Les dépendances principales sont :

- streamlit
- pandas
- pytest

## Lancer le dashboard

Depuis le dossier du projet :

```bash
python dashboard.py
```

Le lanceur démarre Streamlit et affiche l'URL locale :

```text
http://localhost:8501
```

Ouvre cette URL dans ton navigateur.

## Exécuter les tests

```bash
python -m pytest -q
```

## Arrêter le serveur

Dans le terminal qui exécute le dashboard, appuie sur :

```text
Ctrl+C
```

Cela arrête proprement le serveur Streamlit.

## Structure du projet

- `insee_dashboard.py` : application Streamlit principale
- `dashboard.py` : lanceur de l'application
- `test_dashboard.py` : tests de régression
- `requirements.txt` : dépendances Python du projet
- `README.md` : documentation du projet

## Dépannage courant

### Erreur : `No module named streamlit`

Cela signifie que le bon environnement virtuel n'est pas activé ou que les dépendances ne sont pas installées.

Vérifie :

```bash
python -m pip show streamlit
```

Si besoin, réinstalle les dépendances :

```bash
python -m pip install -r requirements.txt
```

### Erreur : port 8501 déjà utilisé

Un ancien serveur Streamlit peut encore tourner. Tu peux le tuer puis relancer :

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'streamlit' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Ensuite relance :

```bash
python dashboard.py
```

### Le dashboard ne se charge pas correctement

- Vérifie que l'URL INSEE utilisée est bien une URL XML de l'API
- Vérifie que le projet est bien lancé depuis la racine du dossier
- Vérifie que l'environnement virtuel est activé

## Exemple de lancement rapide

```powershell
cd C:\chemin\vers\insee_dashboard_app
.\.venv\Scripts\Activate.ps1
python dashboard.py
```

Puis ouvrir :

```text
http://localhost:8501
```

## Remarque

Le projet est conçu pour fonctionner avec des jeux de données XML de l'Insee et pour gérer les erreurs de saisie de données non conforme. La sélection des axes graphiques est laissée à l'utilisateur pour garantir la compatibilité avec plusieurs jeux de données.
