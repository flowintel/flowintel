# Flowintel - Vue d'Ensemble du Projet

## 1. Présentation

Flowintel est une plateforme open-source de gestion de cas pour analystes de sécurité. Elle combine gestion de cas, intégration threat intelligence (MISP), automatisation de workflow et alertes en une seule plateforme.

**Fonctionnalités clés :**
- Gestion de cas et tâches pour analystes sécurité
- Documentation riche avec Markdown et diagrammes Mermaid
- Intégration taxonomies et galaxies MISP
- Système de calendrier et notifications
- Système de templating pour playbooks et processus
- API REST pour accès programmatique
- Gestion utilisateurs et workflows avec audit logging
- Export vers MISP, AIL et autres plateformes

## 2. Stack Technique

### Backend
| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3 |
| Framework | Flask |
| Base de données | PostgreSQL 17 |
| Session Store | Valkey (Redis fork) |
| ORM | SQLAlchemy |

**Bibliothèques Python clés :**
- Extensions Flask : `flask-sqlalchemy`, `flask-session`, `Flask-WTF`, `Flask-Migrate`, `Flask-Login`, `flask-restx`
- Intégration MISP : `pymisp`, `pymispgalaxies`, `misp-modules`
- Notifications : `matrix-nio` (Matrix bot)
- Sécurité : `python-gnupg`
- Autres : `pytest`, `gunicorn`, `email_validator`, `WTForms`

### Frontend
| Composant | Technologie |
|-----------|-------------|
| Build Tool | Vite |
| Package Manager | npm |
| UI Framework | Bootstrap 5 |
| JavaScript | jQuery, Chart.js, FullCalendar, CodeMirror, Mermaid, Select2, SortableJS |

### Infrastructure
- **Containerisation** : Docker & Docker Compose
- **Port par défaut** : 7006

## 3. Structure des Répertoires

```
/flowintel/
├── app/                          # Application Flask principale
│   ├── __init__.py               # Factory Flask
│   ├── api.py                    # Blueprint API REST
│   ├── decorators.py             # Decorators personnalisés (auth, permissions)
│   ├── account/                  # Authentification & profils utilisateurs
│   ├── admin/                    # Panneau d'administration
│   ├── analyzer/                 # Intégration modules MISP
│   ├── assets/                   # Build frontend (Vite, npm)
│   │   ├── package.json          # Dépendances npm
│   │   ├── vite.config.mjs       # Configuration Vite
│   │   └── src/                  # Fichiers JS/CSS source
│   ├── calendar/                 # Vues calendrier & API
│   ├── case/                     # Gestion cas (core, API, forms)
│   ├── connectors/              # Connecteurs externes (MISP, AIL)
│   ├── custom_tags/              # Système de tagging personnalisé
│   ├── db_class/
│   │   └── db.py                 # Modèles SQLAlchemy (1400+ lignes)
│   ├── main/
│   │   └── home.py               # Controlleur home/dashboard
│   ├── modules/                  # Modules additionnels
│   ├── my_assignment/           # Affectations de tâches utilisateur
│   ├── notification/             # Système de notifications
│   ├── static/                   # Fichiers statiques (images, etc.)
│   ├── templating/               # Système de templates
│   ├── tools/                     # Outils import/export
│   ├── utils/                    # Utilitaires (scripts init, helpers)
│   └── templates/                # Templates Jinja2 HTML
│
├── conf/                         # Configuration
│   ├── config.py                 # Configuration principale
│   └── config_module.py          # Configuration des modules
│
├── modules/                     # Threat intelligence externe
│   ├── misp-taxonomies/          # Taxonomies MISP
│   ├── misp-galaxy/              # Clusters galaxy MISP
│   ├── misp-objects/             # Objets MISP
│   ├── custom_taxonomies/        # Taxonomies utilisateur
│   └── custom_galaxies/         # Galaxies utilisateur
│
├── app.py                        # Point d'entrée principal & CLI
├── launch.sh                    # Script de lancement
├── requirements.txt             # Dépendances Python
├── docker-compose.yml            # Orchestration Docker
├── Dockerfile                   # Build container
├── version                      # Fichier version (3.1.0)
└── template.env                 # Template environnement
```

## 4. Fichiers de Configuration Clés

### `conf/config.py` (Configuration Principale)
- **SECRET_KEY** : Chiffrement sessions et protection CSRF
- **FLASK_URL/FLASK_PORT** : Binding serveur (défaut 127.0.0.1:7006)
- **Database** : Paramètres connexion PostgreSQL
- **Session** : Configuration Valkey (Redis)
- **File uploads** : Taille max (défaut 5MB)
- **MISP settings** : Module server, options export, defaults événements
- **Authentication** : Microsoft Entra ID (Azure AD) SSO
- **Roles** : Rôles système, enforcement privilèges
- **GDPR** : Configuration notice vie privée
- **GPG signing** : Capacités signature rapports

### `template.env`
Variables d'environnement pour déploiement Docker :
- Identifiants PostgreSQL
- Configuration Valkey
- Port/IP application
- Settings SSO Entra ID optionnels

### `app/assets/package.json`
Dépendances frontend : Bootstrap, Chart.js, FullCalendar, CodeMirror, Mermaid, Vite

## 5. Points d'Entrée

### `app.py` (Application Principale)`
Point d'entrée principal. Il :
1. Crée l'application Flask avec le pattern factory
2. Configure le logging vers `logs/record.log`
3. Enregistre les error handlers (404, CSRF)
4. Gère les arguments CLI :
   - `-i/--init_db` : Initialiser la base de données
   - `-r/--recreate_db` : Recréer la base de données
   - `-tg/--taxo_galaxies` : Ajouter taxonomies/galaxies
   - `-mm/--misp_modules` : Ajouter modules MISP
   - `-td/--test_data` : Créer des cas de test
   - Par défaut : Lancer le serveur développement Flask

### `launch.sh` (Script de Démarrage)`
Script自动化 qui :
1. Vérifie/crée les fichiers de configuration
2. Tue les sessions screen existantes
3. Démarre Valkey (session store) dans un screen
4. Démarre le bot de notifications dans un screen
5. Lance l'application Flask

## 6. Architecture et Connexion des Composants

### Architecture applicative

```
┌─────────────────────────────────────────────────────────────┐
│                      Flask App (app.py)                     │
│                   http://localhost:7006                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   PostgreSQL  │   │    Valkey     │   │ MISP Modules  │
│   (Database)  │   │   (Sessions)  │   │  (Enrichment) │
└───────────────┘   └──────────���────┘   └───────────────┘
```

### Enregistrement des Blueprints

Le factory Flask (`app/__init__.py`) inicialise et enregistre ces blueprints :

| Blueprint | Préfixe URL | Fonctionnalité |
|-----------|------------|---------------|
| `home_blueprint` | `/` | Dashboard |
| `account_blueprint` | `/account` | Login, profil, SSO |
| `case_blueprint` | `/case` | Gestion cas |
| `admin_blueprint` | `/admin` | Administration |
| `calendar_blueprint` | `/calendar` | Vue calendrier |
| `notification_blueprint` | `/notification` | Notifications |
| `tools_blueprint` | `/tools` | Import/export |
| `my_assignment_blueprint` | `/my_assignment` | Affectations tâches |
| `connector_blueprint` | `/connectors` | Connecteurs MISP, AIL |
| `analyzer_blueprint` | `/analyzer` | Modules MISP |
| `custom_tags_blueprint` | `/custom_tags` | Tagging |
| `templating_blueprint` | `/templating` | Templates |
| `api_blueprint` | `/api` | API REST |

### Modèles de Base de Données (`app/db_class/db.py`)`

Modèles principaux :
- **User** : Authentification, rôles, organisation
- **Case** : Gestion cas avec status, tags, fichiers
- **Task** : Affectation tâches dans cas
- **Organization** : Support multi-tenant
- **Role** : Gestion permissions
- **Taxonomy/Galaxy** : Tagging threat intelligence
- **AuditLog** : Piste d'audit complète

### API REST (`app/api.py`)`

Utilise flask-restx pour documentation Swagger avec authentification API key. Espaces de noms :
- `/api/case` - Opérations cas
- `/api/task` - Opérations tâches
- `/api/admin` - Fonctions admin
- `/api/analyzer` - Exécution modules MISP
- `/apiconnectors` - Intégrations externes
- `/api/calendar` - Événements calendrier

### Pipeline Build Frontend

1. **Source** : `app/assets/src/js/` et `app/assets/src/css/`
2. **Build** : Vite (`npm run build:static` depuis `app/assets/`)
3. **Output** : Fichiers statiques servis par Flask
4. **Templates** : Templates Jinja2 dans `app/templates/` rendent HTML avec données Python embarquées

### Système de Notifications

- Bot Matrix (`startNotif.py`) tourne dans une session screen séparée
- Communique avec Flask via Valkey/Redis pub/sub
- Envoie alertes pour affectations tâches, mises à jour cas, etc.

### Déploiement Docker

```
docker-compose.yml définit :
├── postgresql    # Base de données (port 5432)
├── valkey        # Session store (port 6379)
└── flowintel     # Application (port 7006)
```

## 7. Commandes Utiles

### Installation et configuration

```bash
# Installer les dépendances
pip install -r requirements.txt

# Initialiser la base de données
python app.py --init_db

# Ajouter taxonomies et galaxies
python app.py --taxo_galaxies

# Ajouter modules MISP
python app.py --misp_modules

# Créer des données de test
python app.py --test_data

# Lancer l'application
python app.py

# Ou utiliser le script de lancement
./launch.sh
```

### Docker

```bash
# Construire et lancer avec Docker Compose
docker-compose up --build

# Lancer en arrière-plan
docker-compose up -d
```

### Tests

```bash
# Lancer les tests
pytest

# Avec coverage
pytest --cov=app --cov-report=html
```

## 8. Contribution

Pour contribuer au projet :
1. Forker le dépôt
2. Créer une branche feature (`git checkout -b feature/ma-feature`)
3. Commit avec messages descriptifs
4. Pousser vers votre fork
5. Créer une Pull Request

Veiller à respecter les standards de code et inclure les tests.