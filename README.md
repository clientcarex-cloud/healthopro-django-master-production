# HealthO

HealthO is an Unified Healthcare Platform for Patients and Healthcare Providers.

## Installation

To set up the project, follow these steps:

1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies with `pip install -r requirements.txt`.

## Usage

Here's how to run the development server:

```bash
python manage.py runserver
```

For Models Chart to generate
```commandline
python manage.py graph_models -a -o healtho_models.png
```

For Data Fixtures to Load Data
```commandline
python load_all_fixtures.py
```
## Development Note
"HealthO" is for Patients and "HealthO Pro" is for Healthcare Providers

There are two app into this project i.e. HealthO and HealthO Pro,
each app with its module contains README.md, so developers must read it before starting
and leaving a note after completion of Task or Work.

## Developer Note Pattern
1.  .## Developer Note by Your Name
2. Started From to End (Date: DD-MM-YYYY)
3. Task: Task Name
4. Status: Completed/Processing
5. Contributors Names: Your Colleague names
6. Libraries installed: Nil
7. Dependant Modules: Global/user/healtho_pro
8. Message: Details explanation what you have done in this task