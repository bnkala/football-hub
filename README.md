# Football Hub

## Overview

Football Hub is a personal football data management
platform designed to manage football clubs, players,
managers, stadiums, leagues, competitions, fixtures,
results and tournament standings.

The project currently focuses on building a reliable
and scalable REST API backend before frontend development.

## Technology Stack

- Python
- Django
- Django REST Framework
- PostgreSQL
- Git and GitHub

## Backend Features

### Core Football Management

- Club management
- Player management
- Manager management
- Stadium management
- League management
- REST API CRUD operations

### Competition Management

- Domestic and international competition models
- Competition seasons
- Club registration and participation
- League and group standings
- Fixtures and match results

### Knockout Tournament Management

- Configurable knockout rounds
- Single-leg and two-legged knockout ties
- Aggregate score calculation
- Penalty shootout winner determination
- Automatic tie completion
- Knockout round progression
- Automatic fixture generation
- Configurable fixture scheduling
- Admin-only round progression
- Database integrity constraints
- Transaction rollback protection
- Concurrency protection for tested scenarios

## Backend Architecture

Football Hub uses a modular Django architecture.

| Application | Responsibility |
|-------------|----------------|
| clubs | Football club management |
| players | Player management |
| managers | Manager management |
| stadiums | Stadium management |
| leagues | League management |
| competitions | Competitions, seasons and tournaments |
| fixtures | Match scheduling and results |
| config | Project configuration and API routing |

## Local Development

Create and activate a virtual environment:

    python3 -m venv .venv
    source .venv/bin/activate

Install dependencies:

    pip install -r requirements.txt

Create a local environment configuration:

    cp .env.example .env

Configure the environment variables and PostgreSQL
database before applying migrations.

Apply database migrations:

    python manage.py migrate

Start the development server:

    python manage.py runserver

## Automated Testing

Run the complete backend test suite:

    python manage.py test

Run competition and fixture tests:

    python manage.py test competitions fixtures

Check Django configuration:

    python manage.py check

Check migration consistency:

    python manage.py makemigrations --check --dry-run

### Latest Verified Test Results

Date: 26 November 2026

- Total tests: 87
- Passed: 87
- Failed: 0
- Django system issues: 0
- Pending model migrations: None

## Development Roadmap

| Milestone | Description | Status |
|-----------|-------------|--------|
| 1 | Django and REST API foundations | Completed |
| 2 | Core football models and CRUD | Completed |
| 3A | Competition management | Completed |
| 3B | Seasons and club participation | Completed |
| 3C | Fixtures and match results | Completed |
| 3D | League and group standings | Implemented - review pending |
| 3E | Knockout tournaments | Implementation complete |
| 3F | Automated testing | In progress |
| 4 | Automatic club importing | Started |
| 5 | National teams | Planned |

## Frontend Development

Frontend development will begin after the agreed
backend milestones have been completed.

The frontend technology has not yet been finalised.

## Security

Local environment variables and database credentials
must not be committed to version control.

Use .env.example as the configuration template.

## Project Status

Active development.
