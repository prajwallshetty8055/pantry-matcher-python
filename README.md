# Pantry to Recipe Matcher

**Language:** Python (FastAPI) &nbsp;|&nbsp; **Needs:** Postgres + Redis

This is a **starter**. The application already works. Your job is everything
that gets it building, tested and running in CI.

---

## You do not need Python installed

You will build this into a container, and the container brings its own
Python 3.12. You are not being asked to extend the app — you are being asked
to ship it.

---

## 1. What this app needs

| | |
|---|---|
| **Runtime** | Python 3.12 |
| **Install dependencies** | `pip install -r requirements.txt` |
| **Start the app** | `uvicorn app.main:app --host 0.0.0.0 --port 8080` |
| **Listens on** | port 8080, bound to `0.0.0.0` |
| **Environment variables** | `DATABASE_URL`, `REDIS_URL` |
| **Needs running first** | Postgres, Redis, and the migrations applied |

### What it does

Tell it what is in your kitchen. It shows what you can cook now, what you could cook with one more item, and builds a shopping list for a recipe you pick.

### Endpoints

```
GET  /health
GET  /recipes                     every recipe with its ingredients
GET  /pantry/{user}               what they have
PUT  /pantry/{user}               {"items":[{"name":"flour","grams":500}]}
GET  /pantry/{user}/cookable      can cook now / need one more
GET  /recipes/{id}/shopping/{user} what is missing, with quantities
```

`/health` reports Postgres and Redis **separately**. If it says
`postgres: false` the app started fine and your compose wiring is wrong —
do not go looking in the application code.

### Migrations

`migrations/` holds `.sql` files applied **in filename order** before the app
starts. They create the tables and insert sample data. A container running
`psql` over them in order is enough; you do not need a migration tool.

---

## 2. What you must write

| File | What it has to do |
|---|---|
| `Dockerfile` | Install dependencies **before** copying source, pin the base image, do not run as root. |
| `docker-compose.yml` | App + Postgres + Redis + a migration step, one `docker compose up`. |
| `.circleci/config.yml` | lint → unit tests → integration tests → secret scan → image build |
| Unit tests | For `app/matching.py`. No database, no network. |
| Integration tests | Against a real Postgres and Redis as CircleCI service containers. |

Then push your image to **your own Docker Hub account**, tagged `:1.0`.

### When it works

```bash
docker compose up --build
curl localhost:8080/health
```

```json
{"status":"ok","postgres":true,"redis":true}
```

---

## Where the marks are

`app/matching.py` is **pure logic** — plain functions over plain data, no
database and no HTTP. Start your tests there. Use pytest:
`pytest --cov=app --cov-report=term-missing`. Minimum 70%.



## Why Redis is here

Redis sets, used for exactly what they were designed for: intersect a pantry with each recipe's ingredients instead of doing it in SQL.

## The hard part

Units. 2 cups of flour and 250g of flour are the same ingredient, and students will treat them as two. Normalise to one base unit per ingredient type and test the conversions.

Write your answer in your README. It is worth more marks than the feature.

---

## Getting unstuck

| Symptom | Almost always |
|---|---|
| `/health` says `postgres: false` | Wrong hostname. In compose the host is the **service name**, not `localhost`. |
| Page will not load, logs fine | No `ports:` mapping, or bound to `127.0.0.1` not `0.0.0.0`. |
| `relation "..." does not exist` | Migrations did not run, or the app started before they finished. |
| Build takes minutes each time | `COPY . .` is above your dependency install. |
| CI cannot reach the database | In CircleCI service containers the host **is** `localhost` — opposite of compose. |
## Units

Recipes and pantries use different units (2 cups vs 250 g), so everything is
converted to one base unit before comparing: grams for solids, millilitres
for liquids (`to_base` in `app/matching.py`). Conversion tables are in
`TO_GRAMS` and `TO_ML`.

**The cup trap:** a cup is not one number. A cup of flour is ~120 g, but a cup
of liquid is 240 ml, so `to_base(..., liquid=True)` selects the liquid table.
Unit tests cover this explicitly.

Other decisions:
- Unknown units, negative or non-numeric quantities raise `UnitError`
  instead of silently becoming 0.
- Ingredient names are normalised (trimmed, lowercased, plural "s" removed)
  so "Oats" and "oat" match.
- Substitutes (butter/oil/ghee, milk/curd/yoghurt) are pooled: 50 g butter
  plus 60 g oil satisfies a 100 g butter requirement.
- The shortfall is rounded to 2 decimals.

**Known limitations:** cup = 120 g is a flour approximation (sugar is ~200 g,
so per-ingredient densities would be the next step), "piece" is a flat 50 g,
and `normalise` strips every trailing "s", so "molasses" becomes "molasse".

## CI

CircleCI runs on `main`: gitleaks secret scan, ruff lint, unit tests,
integration tests (real Postgres and Redis service containers, host
`localhost`), then builds and pushes `:qa`. `staging` and `prod` only build and
push `:stage` and `:prod`. Every build also pushes an immutable
`<branch>-<short-sha>` tag. In Docker Compose the database host is the
service name `db`; in CircleCI service containers it is `localhost`.