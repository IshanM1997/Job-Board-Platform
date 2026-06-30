# Job Board Platform

A Django learning project that models a small job board: companies post listings, candidates apply with an uploaded resume, and recruiters move applications through a hiring pipeline. The project exists to teach three things in depth:

1. **File uploads** — accepting, validating (file type and size), and storing candidate resumes, then serving them back safely to the people who are allowed to see them.
2. **Role-based authentication** — a single custom `User` model with a `role` field (`candidate` or `employer`) that gates entire views and individual records, rather than bolting permissions on after the fact.
3. **Email notifications via Django signals** — decoupling "something happened" (a new application arrived, a recruiter changed a status) from "send an email about it," using `post_save`/`pre_save` receivers instead of scattering `send_mail()` calls through every view that might cause a notification.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Folder Structure](#folder-structure)
- [Architecture Overview](#architecture-overview)
- [Data Model](#data-model)
- [Role-Based Authentication](#role-based-authentication)
- [File Uploads (Resumes)](#file-uploads-resumes)
- [Email Notifications via Signals](#email-notifications-via-signals)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [URL Reference](#url-reference)
- [Running Tests](#running-tests)
- [Possible Extensions](#possible-extensions)

---

## Features

- **Two account types, one User model** — candidates and employers share `accounts.User`, distinguished by a `role` field, with separate signup flows for each.
- **Company profiles** — an employer creates a company profile (with logo upload) before posting jobs; job listings always belong to a company.
- **Job listings** — full CRUD for employers, public browsing and keyword/location/type search for everyone.
- **Resume-backed applications** — a candidate applies to a job by uploading a resume (PDF/DOC/DOCX, size-limited) with an optional cover letter; the system enforces one application per candidate per job.
- **Recruiter pipeline** — employers see applications to their listings grouped into stages (Applied → Reviewing → Interview → Offer → Hired, or Rejected) and move candidates between stages.
- **Email notifications, signal-driven** — a new application emails the employer; a status change emails the candidate. Both fire from Django signals on the `Application` model, not from view code.
- **Ownership enforcement everywhere** — an employer can only edit their own company and listings, and only manage applications submitted to their own listings; a candidate can only see their own applications.
- **Console email backend by default** — the whole project runs and sends "real" notification emails (visible in your terminal) with zero external email service configuration.

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Django 5.x |
| Database | SQLite (default, zero setup) |
| Auth | Django's built-in auth system, swapped to a custom `User` model |
| File storage | Django's default `FileField`/`ImageField` (local filesystem under `media/`) |
| Email | Django's `send_mail`, console backend by default, swappable to real SMTP |
| Forms | Django forms + `django-widget-tweaks` for clean template styling |
| Testing | Django's test framework (`unittest` underneath) |

## Folder Structure

```
job-board-platform/
├── manage.py                       # Django's command-line entry point
├── requirements.txt                # Django, Pillow (for ImageField), python-decouple, widget-tweaks
├── .env.example                     # template for required environment variables
├── .gitignore
│
├── config/                          # project-level settings, not an "app"
│   ├── __init__.py
│   ├── settings.py                  # reads config from environment; SQLite + console email by default
│   ├── urls.py                      # root URLconf, includes each app's urls.py by namespace
│   ├── wsgi.py
│   └── asgi.py
│
├── accounts/                        # custom User model + role-based auth
│   ├── models.py                     # User(AbstractUser) with role='candidate'|'employer'
│   ├── forms.py                      # CandidateSignUpForm, EmployerSignUpForm
│   ├── decorators.py                 # role_required() and RoleRequiredMixin (see below)
│   ├── views.py                      # signup flows, login, role-aware dashboard
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
│       └── 0001_initial.py
│
├── companies/                        # employer-owned company profiles
│   ├── models.py                      # Company(owner=FK to User, logo=ImageField, ...)
│   ├── forms.py
│   ├── views.py                       # create/edit restricted to the owning employer
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
│       └── 0001_initial.py
│
├── jobs/                              # job listings
│   ├── models.py                       # JobListing(company=FK, employment_type, salary range, ...)
│   ├── forms.py                         # JobListingForm + JobSearchForm
│   ├── views.py                         # public browse/search, employer-only create/edit
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
│       └── 0001_initial.py
│
├── applications/                       # the core of the project
│   ├── models.py                        # Application(job, candidate, resume=FileField, status, ...)
│   ├── validators.py                     # resume file type/size validation
│   ├── signals.py                        # post_save/pre_save -> email notifications
│   ├── apps.py                           # wires signals.py up via AppConfig.ready()
│   ├── forms.py                          # ApplicationForm (apply), ApplicationStatusForm (recruiter)
│   ├── views.py                          # apply, view application, update status, pipeline board
│   ├── urls.py
│   ├── admin.py
│   ├── templatetags/
│   │   └── application_extras.py         # `get_item` filter used by the pipeline board template
│   └── migrations/
│       └── 0001_initial.py
│
├── templates/
│   ├── base.html                          # shared layout, nav, messages
│   ├── 403.html, 404.html                 # custom error pages (rendered when DEBUG=False)
│   ├── registration/                       # signup landing, candidate/employer signup, login
│   ├── accounts/                           # role-specific dashboards
│   ├── companies/                          # company detail + create/edit form
│   ├── jobs/                               # job list (with search), detail, create/edit form
│   ├── applications/                       # apply form, application detail, recruiter pipeline board
│   └── emails/
│       ├── new_application_employer.txt     # sent to the employer on a new application
│       └── status_update_candidate.txt      # sent to the candidate on a status change
│
├── static/
│   └── css/
│       └── styles.css                      # small dependency-free stylesheet
│
├── media/
│   └── resumes/                            # uploaded resumes land here, namespaced by candidate id
│
└── tests/
    ├── test_access_control.py               # role + ownership checks across every protected view
    ├── test_resume_upload.py                # file validator + one-application-per-job constraint
    └── test_signals.py                      # email notifications fire (or don't) on the right events
```

## Architecture Overview

Each app is intentionally narrow and owns exactly one concept:

```
accounts      -> who can log in, and what role they have
companies     -> employer-owned organizations
jobs          -> listings, owned by a company
applications  -> a candidate's submission to a listing, plus the email signals
```

Dependency direction flows downward — `applications` depends on `jobs` and `accounts`, `jobs` depends on `companies` and `accounts`, but `accounts` depends on nothing else in the project. This is why `accounts/models.py` has zero imports from any other local app: the custom `User` model has to be defined before Django processes `AUTH_USER_MODEL`, and keeping it dependency-free avoids any import-order headaches.

Views in every app follow the same shape: a public read path (no decorator), and a restricted write path wrapped in `@role_required(...)` from `accounts/decorators.py`, with an additional in-view ownership check (`if company.owner_id != request.user.id`) wherever the action touches one specific record. Role checks answer "what *kind* of user is this," ownership checks answer "does this *particular* user own this *particular* record" — both are necessary, and conflating them is a common source of bugs in real apps (e.g. forgetting the ownership check and letting any employer edit any company).

## Data Model

```
accounts.User (AbstractUser + role)
 ├─ role: 'candidate' | 'employer'
 └─ phone_number

companies.Company
 ├─ owner -> accounts.User (must be an employer)
 └─ name, slug, website, description, logo, location

jobs.JobListing
 ├─ company -> companies.Company
 ├─ posted_by -> accounts.User (the employer who created it)
 ├─ title, description, responsibilities, requirements
 ├─ location, is_remote, employment_type, experience_level
 └─ salary_min, salary_max, is_active

applications.Application
 ├─ job -> jobs.JobListing
 ├─ candidate -> accounts.User (must be a candidate)
 ├─ resume (FileField, validated), cover_letter
 ├─ status: applied -> reviewing -> interview -> offer -> hired | rejected
 ├─ recruiter_notes (internal only, never shown to the candidate)
 └─ unique constraint: one row per (job, candidate) pair
```

## Role-Based Authentication

Rather than a separate `Profile` model bolted onto Django's default `User`, this project swaps in a custom user model (`AUTH_USER_MODEL = 'accounts.User'`) with the role baked directly in. That means `request.user.role`, `request.user.is_candidate`, and `request.user.is_employer` are available everywhere in the project — views, templates, querysets — with no extra join or lookup.

Two enforcement layers exist, and both matter:

1. **`@role_required('employer')`** (in `accounts/decorators.py`) — wraps `login_required` and then checks `request.user.role`. An anonymous user is redirected to log in; a logged-in candidate hitting an employer-only view gets a 403, not a redirect, since they *are* authenticated, just not authorized.
2. **In-view ownership checks** — e.g. in `jobs/views.py`, `job_edit` additionally checks `job.company.owner_id != request.user.id` before allowing an edit. Being *an* employer is necessary but not sufficient — you must be *that listing's* employer.

A `RoleRequiredMixin` is also included for class-based views (unused by the current views, which are all function-based, but provided as a drop-in extension point if you add `ListView`/`CreateView`-style views later).

## File Uploads (Resumes)

Resumes are a standard Django `FileField` on `Application`, with two custom pieces:

- **`resume_upload_path`** (in `applications/models.py`) — builds the storage path as `resumes/<candidate_id>/<filename>`, so uploads are namespaced per candidate and never collide.
- **`validate_resume_file`** (in `applications/validators.py`) — checks the file extension against `ALLOWED_RESUME_EXTENSIONS` (`.pdf`, `.doc`, `.docx` by default) and the file size against `MAX_RESUME_UPLOAD_SIZE_MB` (5 MB by default, both configurable via `.env`). This runs automatically as part of Django's form/model validation — `ApplicationForm` doesn't need any extra code to enforce it, since the validator is attached directly to the model field.

Uploaded files are served back through Django's standard `MEDIA_URL`/`MEDIA_ROOT` machinery in development; a production deployment would put `media/` behind a real web server or object storage (S3, etc.) rather than Django itself.

## Email Notifications via Signals

This is the part of the project most worth reading slowly: `applications/signals.py`.

Two notification-worthy events both happen via the same model method — `Application.save()` — which is exactly why signals are the right tool here instead of putting `send_mail()` calls inside view functions:

- **New application → notify the employer.** A `post_save` receiver checks Django's `created` flag; if `True`, it emails the company owner.
- **Status change → notify the candidate.** Knowing the status *changed* requires knowing what it changed *from*, but by the time `post_save` fires, the database already has the *new* value — the old value is gone. The fix is a `pre_save` receiver that runs just before the save, looks up the row's current status in the database, and stashes it as a private attribute (`instance._old_status`) on the in-memory object. The `post_save` receiver then compares that stashed value against `instance.status` to decide whether anything notification-worthy actually happened (so re-saving recruiter notes without touching `status` correctly sends nothing).

Both receivers are connected in `applications/apps.py`'s `ready()` method — importing `signals.py` there (rather than at the top of `models.py`) is the documented Django pattern, since it guarantees the whole app registry is loaded before receivers are wired up.

Because this is implemented at the model layer, it doesn't matter whether a status change comes from the recruiter's "update status" form, the Django admin, a future bulk-import script, or a test — the email always fires. This is the main argument for using signals over scattering notification calls through every place that *might* change a status: there's exactly one place to look, and exactly one place to test.

Email templates live in `templates/emails/` as plain-text `.txt` files rendered with `render_to_string`, kept deliberately simple (no HTML/CSS email layout) since the teaching focus is the signal wiring, not email design.

## Getting Started

```bash
# 1. Create and activate a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# The defaults work out of the box: SQLite database, console email backend.

# 4. Apply migrations
python manage.py migrate

# 5. Create an admin account (optional, for /admin/)
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` to browse listings, `/accounts/signup/` to create a candidate or employer account, and `/admin/` for the Django admin.

Because `EMAIL_BACKEND` defaults to Django's console backend, every notification email (new application, status change) prints directly to the terminal running `runserver` — there's nothing else to configure to see the signal-driven notifications working.

## Environment Variables

See `.env.example` for the full list with comments. The important ones:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django's cryptographic signing key — change this for any real deployment. |
| `DEBUG` | When `True` (the default), Django's own error pages are shown instead of `403.html`/`404.html`. |
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` by default — prints emails to the terminal. Swap to `django.core.mail.backends.smtp.EmailBackend` plus the `EMAIL_HOST*` variables for real delivery. |
| `MAX_RESUME_UPLOAD_SIZE_MB` | Maximum resume upload size, enforced by `applications/validators.py`. |

## URL Reference

**Accounts**
- `GET /accounts/signup/` — choose candidate or employer signup
- `GET,POST /accounts/signup/candidate/`
- `GET,POST /accounts/signup/employer/`
- `GET,POST /accounts/login/`
- `POST /accounts/logout/`
- `GET /accounts/dashboard/` — role-aware: candidates see their applications, employers see their companies/listings

**Companies**
- `GET,POST /companies/new/` — employer only
- `GET /companies/<slug>/`
- `GET,POST /companies/<slug>/edit/` — owning employer only

**Jobs**
- `GET /` — browse/search all active listings
- `GET,POST /jobs/new/` — employer only (requires a company first)
- `GET /jobs/<id>/`
- `GET,POST /jobs/<id>/edit/` — owning employer only

**Applications**
- `GET,POST /applications/apply/<job_id>/` — candidate only, one per job
- `GET /applications/<id>/` — owning candidate or owning employer only
- `POST /applications/<id>/status/` — owning employer only; triggers the candidate notification email
- `GET /applications/pipeline/<job_id>/` — owning employer only; applications grouped by status

## Running Tests

```bash
python manage.py test tests
```

This covers three things specifically called out as the project's learning goals:

- **`test_access_control.py`** — every role-gated and ownership-gated view: anonymous users redirected, wrong-role users get a 403, owners succeed, non-owners get a 403.
- **`test_resume_upload.py`** — the resume validator accepts good files and rejects bad extensions/oversized files; the database-level uniqueness constraint prevents a candidate from applying twice to the same job.
- **`test_signals.py`** — creating an application emails the employer exactly once; changing status emails the candidate exactly once; saving an application *without* changing status sends no email; multiple status changes each send their own email.

Tests use Django's `locmem` email backend (via `@override_settings`) to inspect `django.core.mail.outbox` directly, and a temporary `MEDIA_ROOT` so test resume uploads never touch the project's real `media/` folder.

## Possible Extensions

- HTML email templates (the current `.txt` templates are deliberately plain to keep the signal-wiring the focus).
- A "saved jobs" / favorites list for candidates.
- Email notification preferences (let a candidate opt out of status-change emails).
- Resume parsing (extract name/skills from the uploaded file automatically).
- Multi-company employer support in the UI (the data model already allows one employer to own multiple companies; the dashboard currently just lists all of them).
- Async email sending via Celery instead of the synchronous `send_mail()` call inside the signal receiver, so a slow SMTP server can't add latency to an application submission.
