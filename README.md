# PrepLoop API

Django REST API for PrepLoop, a tech interview preparation app. It stores accounts, the question archive, solutions, comments, votes, preparation goals, notifications, taxonomy, and moderation.

The local database is SQLite (`db.sqlite3`). Set `DATABASE_URL` to use PostgreSQL instead. Session cookies authenticate the browser. The React app must call this API from an origin listed in `FRONTEND_URL` or `CORS_ALLOWED_ORIGINS`.

## Requirements

- Python 3.13
- The packages in `requirements.txt`

`psycopg2-binary` is installed so a `DATABASE_URL` for PostgreSQL can be used. With no `DATABASE_URL`, the API keeps using SQLite and PostgreSQL does not need to be running.

## Run locally

From `tech-interview-prep-backend`:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py seed
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

The API is then at `http://127.0.0.1:8000/`.

`seed` is safe to run again. It fills every application table and leaves rows that are already there in place. Run it when you want the sample rows. A later run rewrites the seeded question dates, so leave it out of the deploy command.

## Environment

Local values below are the defaults. A name set in the process environment or in `.env` replaces the default. `.env.example` lists the names. Restart the server after a change.

| Variable | Local default | Production |
| --- | --- | --- |
| `SECRET_KEY` | A local development key | Required when `DEBUG` is false |
| `DEBUG` | `True` | `False` |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Render also adds `RENDER_EXTERNAL_HOSTNAME` |
| `DATABASE_URL` | Empty, so SQLite is used | Render Postgres URL |
| `FRONTEND_URL` | `http://localhost:5173` | The Vercel origin, with no path |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Extra browser origins, comma-separated |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:5173` | Same origins as CORS |
| `DEFAULT_FROM_EMAIL` | `PrepLoop <prep@localhost>` | An address the mail provider allows |

`FRONTEND_URL` is added to the CORS and CSRF lists, so the deployed frontend needs that one origin set. With `DEBUG=False`, session and CSRF cookies are `Secure` and `SameSite=None`, which is what a Vercel page needs in order to send them to an `onrender.com` API.

`GET /auth/csrf/` returns `{ "csrfToken": "..." }` and repeats the current token in the `X-CSRFToken` response header. The client stores that value and sends it back on later requests, which is what a page on another host needs.

On macOS or Linux, create the virtualenv the same way and call `./venv/bin/python` instead of `.\venv\Scripts\python.exe`.

## Seeded accounts

Every seeded account uses the password `PrepLoop-test-1`.

| Username | Role | Status |
| --- | --- | --- |
| preploop | user | active, with goals and progress |
| avery | user | active |
| jordan | user | active |
| moderator | moderator | active |
| admin | admin | active |
| pending | user | email not verified |
| suspended | user | suspended |

## Email

With no mail host configured, verification and password-reset messages are printed in the `runserver` console. The link is on its own line.

To send through an SMTP API such as Resend, Brevo, SendGrid, or Mailgun, set these environment variables and restart the server:

| Variable | Purpose |
| --- | --- |
| `EMAIL_HOST` | SMTP host. Setting this switches off the console backend. |
| `EMAIL_PORT` | Defaults to `587`. |
| `EMAIL_HOST_USER` | SMTP username. |
| `EMAIL_HOST_PASSWORD` | SMTP password or API key. |
| `EMAIL_USE_TLS` | Defaults to true. |
| `EMAIL_USE_SSL` | Defaults to false. |
| `DEFAULT_FROM_EMAIL` | Address the provider allows you to send from. |
| `EMAIL_BACKEND` | Optional override of the backend import path. |
| `FRONTEND_URL` | Origin used inside email links. Defaults to `http://localhost:5173`. |

Registration still creates the account when delivery fails. The response then includes `"email_sent": false`.

Render’s free web service blocks outbound SMTP on ports 25, 465, and 587. Verification mail from that host needs an HTTPS mail API. Until that is connected, leave `EMAIL_HOST` empty and use the console backend locally.

## Deploy

`Procfile` starts Gunicorn. `render.yaml` describes a free Render web service and a free Postgres database. The free plan has no pre-deploy command, so the build installs dependencies, collects static files, and runs `migrate`. Set `FRONTEND_URL` to the Vercel origin in the Render dashboard before relying on login from that site.

The free service disk is wiped on sleep and redeploy, so production uses `DATABASE_URL`. Run `seed` once from this machine with `DATABASE_URL` set to the external Postgres URL. The free database expires 30 days after it is created.

## Authentication

The API uses Django sessions. Call `GET /auth/csrf/` first so the browser stores `csrftoken`, then send that value as `X-CSRFToken` on later requests. Requests from the frontend must include credentials.

The local frontend origin is `http://localhost:5173`. Opening the frontend at `http://127.0.0.1:5173` is rejected unless that origin is added to `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

Verified study actions require `account_status` of `active`. Moderators and admins can open the moderation queue.

## Apps

| App | Responsibility |
| --- | --- |
| accounts | Registration, session login, profile, email verification, password reset |
| taxonomy | Companies, job roles, and topics |
| questions | Questions and per-user solved status |
| discussions | Solutions, comments, and reports |
| voting | One vote per user on a question |
| progress | Goals and statistics |
| notifications | Replies, solutions, moderation, and goal progress |
| moderation | Pending questions and report actions |

## API

### Accounts

| Method | Path |
| --- | --- |
| POST | `/auth/register/` |
| POST | `/auth/login/` |
| POST | `/auth/logout/` |
| GET | `/auth/csrf/` |
| GET | `/auth/current-user/` |
| PATCH | `/auth/edit-profile/` |
| PATCH | `/profile/manage/` |
| POST | `/auth/resend-verification/` |
| GET | `/auth/verify-email/<token>/` |
| POST | `/auth/recover-password/` |
| POST | `/auth/reset-password/<token>/` |
| POST | `/auth/change-password/` |
| DELETE | `/auth/delete-account/` |

`POST /auth/recover-password/` expects `username` and `email`. `POST /auth/reset-password/<token>/` expects `password`.

### Questions and progress

| Method | Path |
| --- | --- |
| GET, POST | `/questions/` |
| GET | `/questions/mine/` |
| GET | `/questions/statuses/` |
| GET | `/questions/company/<company_id>/` |
| GET, PATCH, DELETE | `/questions/<id>/` |
| GET | `/questions/progress/` |
| GET, POST, PATCH, DELETE | `/questions/<id>/status/` |
| GET, POST | `/questions/<id>/vote/` |
| GET | `/questions/<id>/votes/` |

### Discussion

| Method | Path |
| --- | --- |
| GET, POST | `/questions/<id>/solutions/` |
| GET, PATCH, DELETE | `/solutions/<id>/` |
| GET | `/questions/<id>/comments/` |
| GET | `/solutions/<id>/comments/` |
| POST | `/comments/` |
| PATCH, DELETE | `/comments/<id>/` |
| GET, POST | `/reports/` |
| GET, PATCH, DELETE | `/reports/<id>/` |

### Taxonomy, goals, notifications, moderation

| Method | Path |
| --- | --- |
| GET, POST | `/taxonomy/companies/`, `/taxonomy/job-roles/`, `/taxonomy/tags/` |
| PATCH, DELETE | `/taxonomy/companies/<id>/`, `/taxonomy/job-roles/<id>/`, `/taxonomy/tags/<id>/` |
| GET, POST | `/progress/goals/` |
| GET, PATCH, DELETE | `/progress/goals/<id>/` |
| GET | `/progress/statistics/` |
| GET | `/notifications/` |
| POST | `/notifications/read-all/` |
| PATCH | `/notifications/<id>/` |
| GET | `/moderation/reports/` |
| GET, PATCH | `/moderation/reports/<id>/` |
| GET | `/moderation/questions/` |
| PATCH | `/moderation/questions/<id>/` |

Taxonomy delete marks the row inactive. A name posted again reuses the existing row, including one that was inactive.

Creating a company, role, or topic from the question form uses the same taxonomy endpoints. The name match is case-insensitive.
