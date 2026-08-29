<p align="center">
  <img src="static/images/cocon-logo.png" alt="Cocon pixel-art butterfly and cocoon logo" width="80">
</p>

<h1 align="center">Cocon</h1>

<p align="center">
  A calm, low-stimulation study workspace built to conquer sensory overload, eliminate decision fatigue, and transform scattered focus into structured, measurable progress.
</p>

![Cocon dashboard with focus analytics, Pomodoro timer, and study navigation](docs/images/cocon-dashboard.png)

<img width="1920" height="873" alt="dark_mode" src="https://github.com/user-attachments/assets/e7db34b0-b80c-4f02-8a45-4f76e93f5983" />

Cocon helps organize learning materials, plan the next step, and understand
where focused time actually goes.
Instead of keeping notes, flashcards, timers, and plans across many tabs, Cocon
connects them to one learning hierarchy:

`Topic → Section → Subject → Notes / Flashcards`

## Why Cocon Exists

*Cocon* was created out of a personal necessity to survive learning with sensory hyper-sensitivity and executive function challenges.

Many standard tools demand constant setup, feature overwhelming interfaces full of distracting visual noise, and push users into passive tracking where you check boxes without knowing if you actually focused. Moreover, keeping dozens of tabs, PDFs, and links open across browsers triggers immediate sensory overload, draining mental energy before studying even begins.

*Cocon* solves this by offering a sanctuary of quiet structure:

**Zero Noise, Full Calm:** A low-stimulation interface designed to protect mental energy, eliminating flashing widgets, bright clutter, and endless tabs.

**The End of Tab Hoarding:** Instead of scattering PDFs, tutorials, and materials across separate spaces, everything lives inside a strict, intuitive hierarchy: Topic → Section → Subject → Notes / Flashcards.

**Active Focus Accountability:** Built-in timers and smart tracking ensure that every recorded minute represents real, active concentration rather than passive presence.


## The Architecture of Learning

*Cocon* connects every piece of your education into a single, cohesive workflow so you never have to waste time wondering what to do next or where you put your materials:

- Topics & Sections: High-level domains (like IMAT, Programming, Languages, or Musical Instruments) broken down into targeted sub-domains (e.g., Biology, Python, Dombra).

- Subjects & Practical Execution: Step-by-step topics, syllabi, and mini-projects where you check off milestones as you build real skills.

- Bulk Flashcard Creation (Build Card): Paste entire blocks of text or prompts to generate review decks instantly, bypassing the tedious single-card entry that kills learning momentum.

- Plans & Deadlines: Clear priority management (Low, Normal, Important) with timezone-aware tracking for projects, goals, and exams.

- Unified Journal: Automatic logging of completed tasks, Pomodoro sessions, and manual study entries, tied directly to a calendar view so you can see your daily evolution.

## Analytics That Guide, Not Overwhelm
Tracking time shouldn't feel like micromanagement. Cocon splits analytics into purpose-driven views:

- **Focus by Area:** Aggregates all-time accumulated time across your topics, giving you a bird’s-eye view of your life balance. If creativity starts overshadowing core priorities, you spot the imbalance immediately and adjust.

- **Flexible Timeframes:** Seamlessly switch between 7-day, 30-day, and 12-month breakdowns with interactive tooltips and hierarchy drilling (Topic → Subject → Notes).

- **Manual Time Logging (Manage Time):** For moments when you are deep in a flow state without a running timer (or practicing an instrument offline), you can log or adjust time manually to keep your statistics honest.

## Flashcard Spaced Repetition
Studying languages or complex theory requires reliable memory loops:

- **Again** returns cards instantly to the current queue without wait timers.

- Overdue review dates display clearly as Review due, and mastered items clean up automatically.

- Active rating badges (e.g., **Learning · Easy**) show directly on cards so you always know your retention state.

## Tech stack

- Python 3.12
- Django 6
- SQLite for local development
- Vanilla JavaScript, HTML, and CSS
- Pillow and django-cleanup for uploaded media

## Run locally

1. Clone the repository and enter the project directory.
2. Create and activate a virtual environment.
3. Install dependencies and prepare the database:

```bash
python -m venv .venv
python -m pip install -r requirements.txt
python manage.py migrate
```

4. Start the development server:

```bash
python manage.py runserver
```

5. Open `http://127.0.0.1:8000/` and create an account.

The repository does not include a database or uploaded media. Django creates a
fresh local `db.sqlite3` automatically when migrations run.

## Configuration

Local development works with safe development defaults. For deployment, set
the variables listed in `.env.example` through the hosting platform. At a
minimum, production needs:

```text
DJANGO_SECRET_KEY=<a new long random value>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.example
DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.example
```

The checked-in `.env.example` is documentation only; `.env` files and secrets
are intentionally ignored by Git.

## Tests

Run the complete test suite and project checks with:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

GitHub Actions runs the same checks for every push and pull request.

## Project structure

```text
config/      Django configuration and root URLs
topics/      Topic, section, subject, dashboard, and search flows
notes/       Contextual notes, attachments, pins, and quick notes
flashcards/  Decks, review scheduling, and mastery state
study/       Focus-session tracking and Pomodoro endpoints
planner/     To-do tasks and deadlines
users/       Registration and study preferences
templates/   Shared and page templates
static/      CSS and browser-side JavaScript
```

## Privacy and repository data

`db.sqlite3`, uploaded files in `media/`, local logs, environment files, and
Python caches are excluded from Git. This keeps personal study data and
copyrighted learning materials out of the public repository.

## License

Released under the [MIT License](LICENSE).
