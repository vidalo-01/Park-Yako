# Smart Gate — Modern Parking System

A functional, web-based parking management prototype built for the
"modern parking system" brief: drivers see live slot availability,
vehicles are recorded on arrival, and on exit the system calculates
duration + fee automatically before the barrier opens.

Stack: **Python 3 + Flask** (web layer) + **SQLite** (dynamic database).
Chosen because it needs no external DB server to install for a class
submission, while still being a real relational database with proper
tables, keys and growth — not a flat file.

---

## 1. Use cases identified

| Actor            | Use case                                              |
|-------------------|--------------------------------------------------------|
| Driver             | View available slots before entering                  |
| Gate attendant/system | Record vehicle arrival, assign a slot                |
| Driver / attendant | Request exit, view fee owed                            |
| System              | Calculate fee based on duration                        |
| Driver / attendant | Confirm payment                                          |
| Barrier            | Open on successful payment                              |
| Manager            | View history/log of all sessions                        |

## 2. Modules proposed

1. **Slot Management Module** — tracks every slot's state (available /
   occupied) and drives the visual display.
2. **Vehicle Entry Module** — validates and records an arriving vehicle,
   allocates it a slot.
3. **Fee Calculation Module** — pure function that turns
   (entry_time, exit_time) into a fee using the client's tiers.
4. **Vehicle Exit & Payment Module** — looks up the active session,
   shows the fee, and finalises the session on payment.
5. **Barrier Control Module** — simulated: opens (returns `"OPEN"`)
   only after payment is confirmed. On real hardware this would send a
   signal to a relay/controller instead of returning a string.

All of these live in `algorithms.py` (the algorithms) and `app.py`
(the web routes that expose them), with clear docstrings explaining
each step.

## 3. Algorithms (see `algorithms.py` for full comments)

- **Slot allocation**: pop a free slot number from the front of a
  FIFO queue — O(1) — rather than scanning every slot for the first
  free one (O(n)). Freed slots are pushed to the back of the queue,
  spreading wear evenly.
- **Fee calculation**: tiered decision logic matching the client's
  exact bands (free ≤30 min, Kshs 50 ≤2h, Kshs 100 ≤4h, Kshs 300 ≤6h,
  Kshs 500 beyond) — O(1).
- **Session lookup on exit**: hash map keyed by plate number gives
  O(1) lookup instead of scanning the sessions log.

## 4. Data structures and why

| Structure          | Used for                          | Why this one |
|---------------------|-------------------------------------|----------------|
| `list` (array)       | Ordered slots for the visual grid  | Matches the physical, numbered layout; O(1) indexed access for rendering |
| `collections.deque` (queue) | Available slot numbers      | O(1) allocate (`popleft`) and release (`append`); FIFO fairness across bays |
| `dict` (hash map)     | Active sessions keyed by plate     | O(1) lookup on exit instead of O(n) scan of the sessions log |
| SQLite tables         | Durable state + full history       | Survives restarts; supports reporting/history; relational integrity via foreign key |

## 5. Dynamic database design

```
slots
-----
id            INTEGER PRIMARY KEY
slot_number   TEXT UNIQUE     -- e.g. "S01"
status        TEXT            -- 'available' | 'occupied'

sessions
--------
id            INTEGER PRIMARY KEY
plate_number  TEXT
slot_id       INTEGER  -> FK slots.id
entry_time    TEXT (ISO datetime)
exit_time     TEXT (ISO datetime, NULL while active)
fee           REAL (NULL until paid)
status        TEXT            -- 'active' | 'completed'
```

Why it's "dynamic": `sessions` is append-only and grows with every
car that passes through (this is your history/audit trail for free).
`slots` can be scaled up at any time by changing `TOTAL_SLOTS` in
`database.py` and calling `ensure_slot_count()` — existing data is
never touched, only new rows are added.

## 6. How to run it

**Easiest way (no code editor needed):** double-click `run.bat` (Windows)
or `run.sh` (Mac/Linux) inside the unzipped `parking_system` folder. It
sets everything up and opens your browser automatically. Requires
Python 3 to already be installed on your machine (python.org).

**Manual way, from a terminal:**

```bash
cd parking_system
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

Then open **http://localhost:5000** in your browser.

- The dashboard shows the live slot grid (green = available, red =
  occupied) and a form to record an arrival.
- "Exit / Pay" looks up a plate, shows the fee owed, and on
  "Confirm Payment" opens the barrier and shows a receipt.
- "History" lists the last 100 sessions from the database.

The database file `parking.db` is created automatically on first run
in the project folder — nothing else to configure.

## 7. M-Pesa / Daraja setup

This project uses Safaricom's **Daraja 3.0 M-Pesa Express (STK Push)** API.
Safaricom documents the STK endpoint as an asynchronous request: the API
accepts the request, prompts the customer's phone, and sends the transaction
result to the callback URL.

1. Create a Daraja account and a **sandbox app** to obtain a Consumer Key and
   Consumer Secret. Safaricom's developer portal provides the sandbox and app
   setup.
2. Copy `.env.example` to `.env`. The app loads this file automatically (or you can set the same variables in your operating system environment).
3. Fill in:
   - `MPESA_CONSUMER_KEY`
   - `MPESA_CONSUMER_SECRET`
   - `MPESA_SHORTCODE`
   - `MPESA_PASSKEY`
   - `MPESA_CALLBACK_URL`
4. The callback URL must be reachable from the internet. Safaricom notes that
   sandbox callbacks may use HTTP, while production callbacks must use HTTPS;
   production URLs should be publicly accessible.
5. Run the application and use **Exit / Pay**. Enter a Kenyan number such as
   `0712345678`; the app normalizes it to the `2547XXXXXXXX` format expected
   by Daraja and sends the prompt.
6. Do not treat Daraja's initial "request accepted" response as proof of
   payment. The app waits for the callback's successful result before
   completing the parking session and opening the simulated barrier.

For production, switch `MPESA_ENV=production`, use the production credentials
and live shortcode/passkey supplied through Daraja, and use an HTTPS callback.

### Important security notes

- Do **not** put Consumer Secrets or passkeys directly in Python source code.
- Do **not** commit a real `.env` file to Git.
- The included callback endpoint is `/payments/callback`; it deliberately does
  not expose credentials or payment secrets in the URL.
- Safaricom also provides a Transaction Status API for checking transactions
  when a callback cannot be delivered.

## 8. Pushing to GitHub

```bash
git init
git add .
git commit -m "Modern Parking System prototype"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

(`.gitignore` already excludes `parking.db`, `venv/` and `__pycache__/`.)

## 9. What to extend next

- **Authentication** for attendants/managers before they can view history.
- **Number-plate recognition (ANPR)** camera integration instead of
  manual plate entry, feeding straight into `park_vehicle()`.
- **Reserved/VIP slots**: add a `slot_type` column and a second queue
  so reserved bays aren't handed out by the general FIFO.
- **Real barrier hardware**: replace the `"barrier": "OPEN"` string in
  `checkout_vehicle()` with a GPIO/serial signal to an actual relay.
- **M-Pesa/online payment** integration in the checkout confirm step,
  instead of the current "assume paid on confirm" flow.
- **Multi-level/multi-branch support**: add a `level` or `branch_id`
  column to `slots` and partition the queue per level.


## Park Yako staff login
The dashboard is protected by a staff login. Configure these values in `.env`:

```text
STAFF_USERNAME=staff
STAFF_PASSWORD=ParkYako@123
FLASK_SECRET_KEY=change-this-to-a-random-secret
```

Change the default password and secret key before using the system beyond local testing.

Open `/login` to sign in. After login, staff can access the dashboard, vehicle entry, Exit / Pay, history, payment status, and receipts. The M-Pesa callback remains public so Daraja can deliver payment confirmations.
