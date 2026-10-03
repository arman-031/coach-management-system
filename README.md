> 🚧 This project is currently under active development. Core backend features are being implemented incrementally.

# Coach Management System

## Overview

Coach Management System is a Persian-first coaching management backend built with Django REST Framework and PostgreSQL. It is designed to support coach and student workflows, with account, student, and exercise APIs implemented so far.

## Project Status

This repository is an active work in progress, not a finished product. Account authentication, student management, and the exercise bank are implemented. Program, payment, and notification workflows, dashboards, automated test coverage, and production deployment are not complete.

## Key Features

- Custom phone-number-based user model with coach and student roles.
- Registration, JWT login and refresh, and authenticated current-user endpoints.
- Student profile management and coach-facing student list, detail, update, activate, and deactivate APIs.
- Exercise and muscle-group models with authenticated coach-facing list and management APIs.
- A JSON exercise seed dataset containing 100 entries and an import management command.
- Exercise media records with image, video, and GIF categories, optional thumbnails, and ordering.

## Architecture

The backend uses Django's app structure. `config` owns project settings and URL routing; `accounts`, `students`, and `exercises` separate identity, student profiles, and exercise-bank behavior. Django REST Framework serializers and views define the API, while Django models persist application data in PostgreSQL.

## Tech Stack

- Python 3.11
- Django 5.2
- Django REST Framework
- PostgreSQL with Psycopg 3
- JWT authentication with SimpleJWT
- Git and GitHub

## Project Structure

```text
morabi/
├── accounts/                 # Custom user, registration, permissions, and authentication APIs
├── config/                   # Django settings and root URL configuration
├── exercises/
│   ├── data/                 # Bundled exercise JSON seed data
│   ├── management/commands/  # Exercise import command
│   ├── media_seed/           # Seed media used by the import command
│   ├── migrations/
│   └── models, serializers, views, and URLs
├── students/                 # Student profiles and coach-facing APIs
├── manage.py
├── requirements.txt
└── .env.example
```

Planned modules that do not exist yet include programs, payments, and notifications.

## Authentication

JWT authentication is configured through SimpleJWT. The current account routes are:

- `POST /api/accounts/register/`
- `POST /api/accounts/login/`
- `POST /api/accounts/token/refresh/`
- `GET` or `PATCH /api/accounts/me/`

Authenticated endpoints use JWT bearer tokens. Coach and student permissions are used to restrict role-specific API areas.

## Exercise Bank

The exercise domain currently includes `MuscleGroup`, `Exercise`, and `ExerciseMedia` models. Exercises can reference primary and secondary muscle groups, difficulty, equipment, and common mistakes. The bundled `exercises/data/exercises.json` contains 100 exercise entries, and `python manage.py import_exercises` imports or updates those records and processes available seed media.

## Media Handling

Exercise media records support image, video, and GIF categories, with an optional image thumbnail and display ordering. The upload field can store files such as WebM videos; the seed data includes a small example video and thumbnail. Uploaded files live under the local `media/` directory, which is ignored by Git. Production media storage and delivery are not configured yet.

## Business Rules

The following product rules are planned and are not implemented in the current models or API:

- Programs run for 45 days.
- Students retain access to previous programs in an archive.
- Program types include bodybuilding, nutrition, and corrective programs.

## Installation

1. Clone the repository after the GitHub repository has been created:

   ```bash
   git clone https://github.com/arman-031/coach-management-system.git
   cd coach-management-system
   ```

2. Create and activate a Python 3.11 virtual environment. In PowerShell:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install the project dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env`, then replace its placeholders with local configuration values. Never commit `.env`.

5. Create a PostgreSQL database and user, then configure the database variables described below.

6. Apply migrations and start Django:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

To load the bundled exercise dataset after migrations, run `python manage.py import_exercises`.

## Environment Variables

Configure these values in the local `.env` file. The example file contains placeholders only.

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django signing key; use a private, randomly generated value outside local development. |
| `DEBUG` | Django debug mode; enable only for local development. |
| `ALLOWED_HOSTS` | Comma-separated hostnames accepted by Django. |
| `DB_NAME` | PostgreSQL database name. |
| `DB_USER` | PostgreSQL username. |
| `DB_PASSWORD` | PostgreSQL password. |
| `DB_HOST` | PostgreSQL host, usually `localhost` for local development. |
| `DB_PORT` | PostgreSQL port, usually `5432`. |

## Database Setup

The project uses PostgreSQL through Psycopg 3. Create a local database and a database user with permission to connect and run migrations, then enter those local values in `.env`. No database credentials are stored in the repository. `db.sqlite3` and database dump files are excluded by `.gitignore`.

## Running the Project

```bash
python manage.py check
python manage.py migrate
python manage.py runserver
```

The development API is available under `/api/`; Django admin is available under `/admin/`.

## API Development Status

Implemented API areas include account registration and JWT authentication, current-user profile access, student profile and coach-facing student management, and coach-facing exercise and muscle-group management. Program, payment, and notification APIs are planned. There is no frontend dashboard in this repository.

## Roadmap

- [x] Django project setup
- [x] PostgreSQL configuration through environment variables
- [x] Django REST Framework setup
- [x] JWT authentication
- [x] Exercise bank models and API
- [x] Exercise import command and 100-entry JSON dataset
- [x] Student management API
- [ ] Program management, including 45-day periods and archived programs
- [ ] Payment management
- [ ] Notifications
- [ ] Coach dashboard
- [ ] Student dashboard
- [ ] Automated tests
- [ ] Production deployment and media storage

## Security Notes

- `.env` and other `.env.*` files are excluded from Git; `.env.example` contains placeholders only.
- No static signing key is committed. If `SECRET_KEY` is absent, Django generates a development key at startup; set a private, stable `SECRET_KEY` through the environment before deployment.
- Keep database credentials, development credentials, private uploads, and local database files out of commits.
- `DEBUG` defaults to `False` when it is not explicitly enabled in the environment.