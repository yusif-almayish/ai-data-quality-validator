import sqlite3
import random
import os
from datetime import date, timedelta

random.seed(42)

# ── Configuration ────────────────────────────────────────────────
DB_PATH = "loan_portfolio.db"
N_RECORDS = 200
BATCH_START = "2026-06-01"
BATCH_END   = "2026-06-30"

# ── Reference data ───────────────────────────────────────────────
STATES_GOOD  = ["VA","MD","TX","FL","CA","NY","PA","OH","GA","NC","IL","AZ","CO","WA","NJ"]
STATES_BAD   = ["va","Md","TXX","FLOR","cal","new york"]   # intentional DQ issues
SERVICERS    = ["ABC Servicing","First National","Heritage Mortgage","Summit Loan Co","Blue Ridge Servicers","Capitol MSR"]
STATUSES_OK  = ["Current","Delinquent","Paid Off","Foreclosure","Forbearance"]
STATUSES_BAD = ["CURR","active","delinquant","N/A"]          # intentional DQ issues
FIRST_NAMES  = ["James","Maria","Robert","Patricia","Michael","Linda","William","Barbara","David","Susan",
                 "Richard","Jessica","Joseph","Sarah","Thomas","Karen","Charles","Lisa","Daniel","Nancy"]
LAST_NAMES   = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Wilson","Moore",
                 "Taylor","Anderson","Thomas","Jackson","White","Harris","Martin","Thompson","Young","Lee"]

def rand_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"

def rand_date(start_year=2015, end_year=2023):
    d = date(start_year, 1, 1) + timedelta(days=random.randint(0, (date(end_year,12,31)-date(start_year,1,1)).days))
    return d.strftime("%m/%d/%Y")

def rand_next_payment():
    d = date(2026, 7, 1) + timedelta(days=random.randint(0, 365))
    return d.strftime("%Y-%m-%d")

def rand_balance():
    return f"{random.uniform(50_000, 850_000):,.2f}"

def rand_rate():
    return f"{random.uniform(3.0, 9.5):.3f}%"

def rand_ingestion_date():
    start = date(2026, 6, 1)
    return (start + timedelta(days=random.randint(0, 29))).isoformat()

# ── Build records ────────────────────────────────────────────────
records = []
loan_ids_used = []

for i in range(N_RECORDS):
    loan_id = f"10{random.randint(1000000, 9999999)}"
    loan_ids_used.append(loan_id)

    rec = {
        "loanNumber":       loan_id,
        "borrowerName":     rand_name(),
        "principalBalance": rand_balance(),
        "interestRate":     rand_rate(),
        "loanStatus":       random.choice(STATUSES_OK),
        "origDate":         rand_date(),
        "nextPaymentDue":   rand_next_payment(),
        "propertyState":    random.choice(STATES_GOOD),
        "servicerName":     random.choice(SERVICERS),
        "ficoScore":        random.randint(580, 820),
        "ingestion_date":   rand_ingestion_date(),
    }
    records.append(rec)

# ── Inject data quality issues ───────────────────────────────────
# 1) 5 exact duplicate LOAN_IDs (copy existing records)
dup_indices = random.sample(range(N_RECORDS), 5)
for idx in dup_indices:
    dup = dict(records[idx])
    dup["ingestion_date"] = rand_ingestion_date()
    records.append(dup)

# 2) 8 missing required fields (None out critical columns)
for idx in random.sample(range(N_RECORDS), 8):
    field = random.choice(["borrowerName","principalBalance","ficoScore","origDate"])
    records[idx][field] = None

# 3) 6 out-of-range credit scores
for idx in random.sample(range(N_RECORDS), 6):
    records[idx]["ficoScore"] = random.choice([150, 260, 900, 950, 1050, -5])

# 4) 5 malformed interest rates (missing %, negative, or text)
bad_rates = ["6.25", "-1.50%", "N/A", "12.00", "0.0%"]
for i, idx in enumerate(random.sample(range(N_RECORDS), 5)):
    records[idx]["interestRate"] = bad_rates[i % len(bad_rates)]

# 5) 4 invalid origination dates
bad_dates = ["13/45/2021", "00/00/0000", "Feb 30 2020", "2099-99-99"]
for i, idx in enumerate(random.sample(range(N_RECORDS), 4)):
    records[idx]["origDate"] = bad_dates[i % len(bad_dates)]

# 6) 5 inconsistent state codes
for i, idx in enumerate(random.sample(range(N_RECORDS), 5)):
    records[idx]["propertyState"] = STATES_BAD[i % len(STATES_BAD)]

# 7) 4 malformed balance strings
bad_bals = ["31O,442.87", "ABC", "$$50000", ""]
for i, idx in enumerate(random.sample(range(N_RECORDS), 4)):
    records[idx]["principalBalance"] = bad_bals[i % len(bad_bals)]

# 8) 3 invalid loan statuses
for i, idx in enumerate(random.sample(range(N_RECORDS), 3)):
    records[idx]["loanStatus"] = STATUSES_BAD[i % len(STATUSES_BAD)]

# ── Write to SQLite ───────────────────────────────────────────────
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

cur.execute("""
    CREATE TABLE vendor_loan_data (
        loanNumber       TEXT,
        borrowerName     TEXT,
        principalBalance TEXT,
        interestRate     TEXT,
        loanStatus       TEXT,
        origDate         TEXT,
        nextPaymentDue   TEXT,
        propertyState    TEXT,
        servicerName     TEXT,
        ficoScore        TEXT,
        ingestion_date   TEXT
    )
""")

cur.executemany("""
    INSERT INTO vendor_loan_data VALUES (
        :loanNumber,:borrowerName,:principalBalance,:interestRate,:loanStatus,
        :origDate,:nextPaymentDue,:propertyState,:servicerName,:ficoScore,:ingestion_date
    )
""", records)

conn.commit()
conn.close()

# ── Export ───────────────────────────────────────────────────────
db_path = DB_PATH
ingestion_date_range = (BATCH_START, BATCH_END)
total_seeded = len(records)

print("=" * 60)
print("  LOAN PORTFOLIO DATABASE — SEEDED")
print("=" * 60)
print(f"  File            : {DB_PATH}")
print(f"  Total records   : {total_seeded}  ({N_RECORDS} base + {total_seeded - N_RECORDS} duplicates)")
print(f"  Batch window    : {BATCH_START}  →  {BATCH_END}")
print()
print("  Injected DQ Issues:")
print(f"    Duplicate loan IDs            : 5")
print(f"    Missing required fields       : 8 records")
print(f"    Out-of-range credit scores    : 6 records")
print(f"    Malformed interest rates      : 5 records")
print(f"    Invalid origination dates     : 4 records")
print(f"    Inconsistent state codes      : 5 records")
print(f"    Malformed balance strings     : 4 records")
print(f"    Invalid loan statuses         : 3 records")
print("=" * 60)
