import csv
from datetime import datetime
import re
from typing import Dict, List, Optional, Tuple
import psycopg2

# Database configuration
CONFIG_DB = {
    "DB_NAME": "fced06",
    "DB_USER": "fced06",
    "DB_PASSWORD": "db062025",
    "DB_HOST": "dbm.fe.up.pt",
    "DB_PORT": "5433",
    "DB_SCHEMA": "electrogrid",
}

# Delete order (children -> parents)
TABLES_ORDER = [
    "rating",
    "city_service_failure",
    "service_failure",
    "bill",
    "service_order",
    "technician_skill",
    "connection",
    "client",
    "technician",
    "service_type",
    "address",
    "city",
    "region",
]

# CSV file paths
CSV_PATHS = {
    "CLIENTS": "data/clients_raw.csv",
    "BILLS": "data/bills_raw.csv",
    "CONNECTIONS": "data/connections_raw.csv",
    "SERVICES": "data/service_orders_raw.csv",
    "TECHNICIANS": "data/technicians_raw.csv",
    "CITY": "data/city.csv",
    "REGION": "data/region.csv",
    "SERVICE_FAILURE": "data/service_failure.csv",
    "RATING": "data/rating.csv",
}


def connect_db():
    """Create a PostgreSQL connection using CONFIG_DB settings."""
    return psycopg2.connect(
        dbname=CONFIG_DB["DB_NAME"],
        user=CONFIG_DB["DB_USER"],
        password=CONFIG_DB["DB_PASSWORD"],
        host=CONFIG_DB["DB_HOST"],
        port=CONFIG_DB["DB_PORT"],
        options=f"-c search_path={CONFIG_DB['DB_SCHEMA']}",
    )


# ---------------------------------
# Clear data with DELETE
# ---------------------------------
def clear_data_delete():
    """Delete all data from tables in TABLES_ORDER (children -> parents)."""
    conn = connect_db()
    cur = conn.cursor()
    schema = CONFIG_DB["DB_SCHEMA"]
    tables = [f'"{schema}"."{t}"' for t in TABLES_ORDER]

    print("Deleting data from all tables with DELETE...")
    try:
        for table in tables:
            sql = f"DELETE FROM {table};"
            print(f"  -> {sql}")
            cur.execute(sql)
        conn.commit()
        print("DELETE completed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] DELETE failed: {e}")
    finally:
        cur.close()
        conn.close()


# ---------------------------
# Parsing helpers
# ---------------------------
def parse_address(raw: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Return (street, number, postal_code, city_name) parsed from a raw address string.
    """
    if not raw:
        return (None, None, None, None)
    s = raw.strip()
    parts = [p.strip() for p in s.split(",") if p.strip()]

    street = number = postal = city = None

    if len(parts) == 1:
        street = parts[0]
    elif len(parts) == 2:
        street = parts[0]
        second = parts[1]
        m = re.search(r"(\d{4}-\d{3})", second)
        if m:
            postal = m.group(1)
            city = second.replace(postal, "").strip() or None
        else:
            number = second
    else:
        street = parts[0]
        number = parts[1]
        rest = ",".join(parts[2:]).strip()
        m = re.search(r"(\d{4}-\d{3})", rest)
        if m:
            postal = m.group(1)
            city = rest.replace(postal, "").strip() or None
        else:
            city = rest or None

    return (street or None, number or None, postal or None, city or None)


def clean_email(raw: str) -> Optional[str]:
    """Normalize an email string (strip and lower), or return None."""
    if not raw:
        return None
    v = raw.strip().lower()
    return v or None


def parse_date(raw: str) -> Optional[str]:
    """Parse a date string and return it as 'YYYY-MM-DD', or None if invalid."""
    if not raw or raw.strip() == "":
        return None
    raw = raw.strip()

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%Y-%m-%dT%H:%M:%S",
    ):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.date().isoformat()
        except Exception:
            pass

    m = re.search(r"(\d{4}-\d{2}-\d2)", raw)
    if m:
        return m.group(1)
    return None


def parse_timestamp(raw: str) -> Optional[str]:
    """
    Parse a date/time string and return a timestamp in 'YYYY-MM-DD HH:MM:SS' format,
    or None if invalid.
    """
    if not raw or raw.strip() == "":
        return None
    raw = raw.strip()

    fmts = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in fmts:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

    d = parse_date(raw)
    if d:
        return d + " 00:00:00"
    return None


def normalize_phone_to_int(raw: Optional[str]) -> Optional[int]:
    """Extract digits from a phone number and normalize to 9-digit int, or None."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if len(digits) > 9:
        digits = digits[-9:]
    if len(digits) == 9:
        try:
            return int(digits)
        except ValueError:
            return None
    return None


def to_bool(raw: Optional[str]) -> Optional[bool]:
    """Convert common string values to boolean, or None if unknown."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if s in {"true", "t", "1", "yes", "y", "sim"}:
        return True
    if s in {"false", "f", "0", "no", "n", "nao", "não"}:
        return False
    return None


# ---------------------------
# Load for region and city
# ---------------------------
def load_region(conn, path: str) -> Dict[str, int]:
    """
    Load regions from CSV and ensure they exist in the database.
    Returns a map: region_name_lower -> region_id.
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    name_to_id: Dict[str, int] = {}

    with conn.cursor() as cur, open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        reader.fieldnames = [fn.strip() for fn in reader.fieldnames]

        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            key = name.lower()

            cur.execute(f'SELECT id FROM "{schema}"."region" WHERE name = %s;', (name,))
            r = cur.fetchone()
            if r:
                name_to_id[key] = r[0]
                continue

            cur.execute(
                f'INSERT INTO "{schema}"."region" (name) VALUES (%s) RETURNING id;',
                (name,),
            )
            new_id = cur.fetchone()[0]
            name_to_id[key] = new_id

    conn.commit()
    print(f"[INFO] {len(name_to_id)} regions loaded.")
    return name_to_id


def load_city(conn, path: str, region_name_map: Dict[str, int]) -> Dict[str, int]:
    """
    Load cities from CSV and ensure they exist in the database.
    Supports same city name in different regions.
    Returns a map: city_name_lower -> one city_id (first occurrence).
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    name_to_id: Dict[str, int] = {}

    with conn.cursor() as cur, open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        # Normalize header names (remove spaces and BOM)
        cleaned = []
        for fn in reader.fieldnames:
            if fn is None:
                cleaned.append(fn)
                continue
            cleaned.append(fn.strip().lstrip("\ufeff"))
        reader.fieldnames = cleaned

        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                continue

            region_name = (row.get("region_name") or "").strip()
            if not region_name:
                raise RuntimeError(f"City without region_name in CSV: {row}")

            reg_key = region_name.lower()
            region_id = region_name_map.get(reg_key)
            if region_id is None:
                raise RuntimeError(
                    f"City '{name}' references unknown region '{region_name}' "
                    f"(not in region.csv / region table)."
                )

            key = name.lower()

            cur.execute(
                f'''
                SELECT id FROM "{schema}"."city"
                WHERE name = %s AND region_id = %s;
                ''',
                (name, region_id),
            )
            r = cur.fetchone()
            if r:
                city_id = r[0]
            else:
                cur.execute(
                    f'''
                    INSERT INTO "{schema}"."city" (name, region_id)
                    VALUES (%s, %s)
                    RETURNING id;
                    ''',
                    (name, region_id),
                )
                city_id = cur.fetchone()[0]

            if key not in name_to_id:
                name_to_id[key] = city_id

    conn.commit()
    print(f"[INFO] {len(name_to_id)} cities loaded.")
    return name_to_id


def ensure_city(conn, city_name: str, city_name_map: Dict[str, int]) -> Optional[int]:
    """
    Ensure a city exists in the database.
    If it does not exist, create it using a default region (first existing or 'Unknown Region').
    Returns city_id or None if city_name is empty.
    """
    if not city_name:
        return None
    key = city_name.strip().lower()
    if key in city_name_map:
        return city_name_map[key]

    schema = CONFIG_DB["DB_SCHEMA"]
    with conn.cursor() as cur:
        # Try to find city by name (any region)
        cur.execute(
            f'SELECT id FROM "{schema}"."city" WHERE LOWER(name) = %s;',
            (key,),
        )
        r = cur.fetchone()
        if r:
            city_id = r[0]
            city_name_map[key] = city_id
            return city_id

        # Get default region or create 'Unknown Region'
        cur.execute(f'SELECT id FROM "{schema}"."region" LIMIT 1;')
        rr = cur.fetchone()
        if rr:
            region_id = rr[0]
        else:
            cur.execute(
                f'INSERT INTO "{schema}"."region" (name) VALUES (%s) RETURNING id;',
                ("Unknown Region",),
            )
            region_id = cur.fetchone()[0]

        # Create new city with default region
        cur.execute(
            f'INSERT INTO "{schema}"."city" (name, region_id) VALUES (%s, %s) RETURNING id;',
            (city_name.strip(), region_id),
        )
        new_id = cur.fetchone()[0]
        city_name_map[key] = new_id
        conn.commit()
        return new_id


# ---------------------------
# Load address / service_type
# ---------------------------
def load_address(
    conn,
    addresses: Dict[str, Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]],
    city_name_map: Dict[str, int],
) -> Dict[str, int]:
    """
    Insert addresses (street, number, postal_code, city_id).
    Returns a map: addr_key -> address.id.
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    addr_db_map: Dict[str, int] = {}

    with conn.cursor() as cur:
        for addr_key, (street, number, postal, city_name) in addresses.items():
            if not street:
                street = "UNKNOWN"

            # Normalize number to int (or None)
            num_val = None
            if isinstance(number, str):
                n = number.strip().lower()
                if n in (
                    "s/n",
                    "sn",
                    "sem numero",
                    "sem número",
                    "sem-número",
                    "sem_numero",
                    "n/a",
                    "-",
                    "",
                ):
                    num_val = None
                else:
                    digits = re.sub(r"\D", "", n)
                    num_val = int(digits) if digits else None
            elif isinstance(number, int):
                num_val = number

            city_id = None
            if city_name:
                city_id = ensure_city(conn, city_name, city_name_map)

            cur.execute(
                f"""
                SELECT id FROM "{schema}"."address"
                WHERE street = %s
                  AND number IS NOT DISTINCT FROM %s
                  AND postal_code IS NOT DISTINCT FROM %s
                  AND city_id IS NOT DISTINCT FROM %s
                """,
                (street, num_val, postal, city_id),
            )
            row = cur.fetchone()
            if row:
                addr_db_map[addr_key] = row[0]
                continue

            cur.execute(
                f"""
                INSERT INTO "{schema}"."address" (street, number, postal_code, city_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (street, num_val, postal, city_id),
            )
            new_id = cur.fetchone()[0]
            addr_db_map[addr_key] = new_id

    conn.commit()
    print(f"[INFO] {len(addr_db_map)} addresses loaded.")
    return addr_db_map


def load_service_type(conn, service_types: List[str]) -> Dict[str, int]:
    """
    Load service types and ensure they exist in the database.
    Returns a map: service_type_name -> id.
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    st_map: Dict[str, int] = {}

    with conn.cursor() as cur:
        for raw_name in service_types:
            name = (raw_name or "").strip()
            if not name:
                continue

            cur.execute(
                f'SELECT id FROM "{schema}"."service_type" WHERE name = %s;',
                (name,),
            )
            row = cur.fetchone()
            if row:
                st_map[name] = row[0]
                continue

            cur.execute(
                f'INSERT INTO "{schema}"."service_type" (name) VALUES (%s) RETURNING id;',
                (name,),
            )
            new_id = cur.fetchone()[0]
            st_map[name] = new_id

    conn.commit()
    print(f"[INFO] {len(st_map)} service types loaded.")
    return st_map


# ---------------------------
# Load technicians / clients
# ---------------------------
def load_technician(conn, technicians: Dict[str, Dict], region_name_map: Dict[str, int]):
    """
    Insert technicians with their region.
    """
    schema = CONFIG_DB["DB_SCHEMA"]

    with conn.cursor() as cur:
        sql = f"""
        INSERT INTO "{schema}"."technician" (id, name, email, phone, center, region_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        data = []

        for tid, info in technicians.items():
            name = info.get("name")
            email = info.get("email")
            phone = normalize_phone_to_int(info.get("phone"))
            center = info.get("center") or "UNKNOWN"
            region_name = info.get("region")

            if not name:
                if email and "@" in email:
                    name = email.split("@")[0].replace(".", " ").title()
                else:
                    name = f"Technician {tid}"

            if phone is None:
                phone = 999_999_999

            region_id = None
            if region_name:
                key = region_name.strip().lower()
                region_id = region_name_map.get(key)

            if region_id is None:
                cur.execute(f'SELECT id FROM "{schema}"."region" LIMIT 1;')
                r = cur.fetchone()
                if r:
                    region_id = r[0]
                else:
                    cur.execute(
                        f'INSERT INTO "{schema}"."region" (name) VALUES (%s) RETURNING id;',
                        ("Unknown Region",),
                    )
                    region_id = cur.fetchone()[0]
                    region_name_map["unknown region"] = region_id

            data.append((tid, name, email, phone, center, region_id))

        if data:
            cur.executemany(sql, data)

    conn.commit()
    print(f"[INFO] {len(technicians)} technicians inserted.")


def load_client(conn, clients: Dict[str, Dict]):
    """
    Insert clients with their main address.
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    with conn.cursor() as cur:
        sql = f"""
        INSERT INTO "{schema}"."client" (id, name, email, phone, address_id)
        VALUES (%s, %s, %s, %s, %s)
        """
        data = []

        for cid, info in clients.items():
            name = info.get("name") or f"Client {cid}"
            email = info.get("email")
            phone = normalize_phone_to_int(info.get("phone"))
            address_id = info.get("address_id")

            if phone is None:
                phone = 999_999_999

            if not address_id:
                raise RuntimeError(f"Client {cid} without address_id (NOT NULL).")

            data.append((cid, name.strip(), email, phone, address_id))

        if data:
            cur.executemany(sql, data)

    conn.commit()
    print(f"[INFO] {len(clients)} clients inserted.")


# ---------------------------
# Load connection / bill / orders / skills
# ---------------------------
def load_connections(conn, connections: Dict[str, Dict]):
    """
    Insert connections.
    Also inserts missing clients that appear only in the connections CSV.
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    with conn.cursor() as cur:
        # Load existing client IDs
        cur.execute(f'SELECT id FROM "{schema}"."client";')
        existing_client_ids = {row[0] for row in cur.fetchall()}

        # Find missing clients referenced by connections
        new_clients = []  # list of (id, name)

        for conn_id, info in connections.items():
            client_id = info.get("client_id")
            if not client_id:
                raise RuntimeError(f"Connection {conn_id} without client_id.")

            if client_id not in existing_client_ids:
                existing_client_ids.add(client_id)
                client_name = info.get("client_name") or f"Client {client_id}"
                new_clients.append((client_id, client_name.strip()))

        # Insert missing clients (if any)
        if new_clients:
            sql_client = f'INSERT INTO "{schema}"."client" (id, name) VALUES (%s, %s);'
            cur.executemany(sql_client, new_clients)
            print(f"[INFO] {len(new_clients)} extra clients inserted from connections.")

        # Insert connections
        sql_conn = f"""
        INSERT INTO "{schema}"."connection"
        (id, type, install_date, meter_serial, status, installer_id, client_id, property_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        data = []

        for conn_id, info in connections.items():
            if not info.get("install_date"):
                raise RuntimeError(f"Connection {conn_id} without install_date.")
            if not info.get("property_address_id"):
                raise RuntimeError(f"Connection {conn_id} without property_address_id.")
            if not info.get("client_id"):
                raise RuntimeError(f"Connection {conn_id} without client_id.")
            if not info.get("installer_id"):
                raise RuntimeError(f"Connection {conn_id} without installer_id.")

            data.append(
                (
                    conn_id,
                    info.get("type"),
                    info.get("install_date"),
                    info.get("meter_serial"),
                    info.get("status"),
                    info.get("installer_id"),
                    info.get("client_id"),
                    info.get("property_address_id"),
                )
            )

        if data:
            cur.executemany(sql_conn, data)

    conn.commit()
    print(f"[INFO] {len(connections)} connections inserted.")


def load_bill(conn, bills: Dict[str, Dict]):
    """
    Insert bills.
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    with conn.cursor() as cur:
        sql = f"""
        INSERT INTO "{schema}"."bill"
        (id, period_start, period_end, consumption, amount, issue_date, payment_date, connection_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        data = []

        for bid, info in bills.items():
            if not info.get("period_start") or not info.get("period_end"):
                raise RuntimeError(f"Bill {bid} without period_start/period_end.")
            if not info.get("kwh_used") or not info.get("amount"):
                raise RuntimeError(f"Bill {bid} without consumption/amount.")
            if not info.get("issue_date"):
                raise RuntimeError(f"Bill {bid} without issue_date.")
            if not info.get("connection_id"):
                raise RuntimeError(f"Bill {bid} without connection_id.")

            data.append(
                (
                    bid,
                    info.get("period_start"),
                    info.get("period_end"),
                    info.get("kwh_used"),
                    info.get("amount"),
                    info.get("issue_date"),
                    info.get("payment_date"),
                    info.get("connection_id"),
                )
            )

        if data:
            cur.executemany(sql, data)

    conn.commit()
    print(f"[INFO] {len(bills)} bills inserted.")


def load_service_order(conn, service_orders: Dict[str, Dict], service_type_map: Dict[str, int]):
    """
    Insert service orders (if they pass basic validation checks).
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    with conn.cursor() as cur:
        # Load valid technician IDs
        cur.execute(f'SELECT id FROM "{schema}"."technician";')
        existing_tech_ids = {row[0] for row in cur.fetchall()}

        # Load valid connection IDs
        cur.execute(f'SELECT id FROM "{schema}"."connection";')
        existing_conn_ids = {row[0] for row in cur.fetchall()}

        sql = f"""
        INSERT INTO "{schema}"."service_order"
        (id, start_date, end_date, notes, technician_id, connection_id, service_type_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        data = []
        skipped_no_start = 0
        skipped_bad_tech = 0
        skipped_bad_conn = 0
        skipped_bad_st = 0

        for soid, info in service_orders.items():
            st_name = info.get("service_type")
            st_id = service_type_map.get(st_name) if st_name else None

            start_date = info.get("start_date")
            end_date = info.get("end_date")
            notes = info.get("notes")
            tech_id = info.get("technician_id")
            conn_id = info.get("connection_id")

            # start_date is NOT NULL
            if not start_date:
                print(f"[WARN] Service order {soid} without start_date. Skipped.")
                skipped_no_start += 1
                continue

            # technician_id must exist
            if not tech_id or tech_id not in existing_tech_ids:
                print(f"[WARN] Service order {soid} with invalid technician_id ({tech_id}). Skipped.")
                skipped_bad_tech += 1
                continue

            # connection_id must exist
            if not conn_id or conn_id not in existing_conn_ids:
                print(f"[WARN] Service order {soid} with invalid connection_id ({conn_id}). Skipped.")
                skipped_bad_conn += 1
                continue

            # service_type_id must exist
            if not st_id:
                print(f"[WARN] Service order {soid} with unknown service_type: {st_name}. Skipped.")
                skipped_bad_st += 1
                continue

            data.append(
                (
                    soid,
                    start_date,
                    end_date,
                    notes,
                    tech_id,
                    conn_id,
                    st_id,
                )
            )

        if data:
            cur.executemany(sql, data)

    conn.commit()
    print(f"[INFO] {len(data)} service orders inserted.")


def load_technician_skill(conn, tech_skill_pairs: List[Tuple[str, str]], service_type_map: Dict[str, int]):
    """
    Insert technician skills (technician_id, skill_id).
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    with conn.cursor() as cur:
        sql = f"""
        INSERT INTO "{schema}"."technician_skill" (technician_id, skill_id)
        VALUES (%s, %s)
        """
        data = []

        for tech_id, st_name in tech_skill_pairs:
            st_id = service_type_map.get(st_name)
            if st_id:
                data.append((tech_id, st_id))

        if data:
            cur.executemany(sql, data)

    conn.commit()
    print(f"[INFO] {len(data)} technician_skill entries inserted.")


# ---------------------------
# Load service_failure / city_service_failure / rating
# ---------------------------
def load_service_failure(conn, path: str, city_name_map: Dict[str, int]):
    """
    Load service failures and city-service-failure relations from CSV.

    The CSV is expected to contain:
      - id
      - start_time
      - cause
      - city_name
      - end_date / end_time
      - status

    For each distinct failure id:
      - one row in service_failure
    For each row (id, city_name, ...):
      - one row in city_service_failure
    """
    schema = CONFIG_DB["DB_SCHEMA"]

    # 1) Read all rows from CSV
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        rows = []
        for row in reader:
            sid_raw = (row.get("id") or "").strip()
            # typo-safe: start_time / start_time / start
            start = parse_timestamp(
                row.get("start_time")
                or row.get("start_time")
                or row.get("start")
                or ""
            )
            cause = (row.get("cause") or "").strip() or None
            city_name = (row.get("city_name") or "").strip()
            end_time = parse_timestamp(row.get("end_date") or row.get("end_time") or "")
            status = (row.get("status") or "").strip()

            if not sid_raw:
                raise RuntimeError(f"Row in service_failure.csv without id: {row}")
            if not start:
                raise RuntimeError(f"Service_failure {sid_raw} without valid start_time: {row}")
            if not city_name or not status:
                raise RuntimeError(f"Invalid row in service_failure.csv (city_name/status): {row}")

            rows.append((sid_raw, start, cause, city_name, end_time, status))

    # 2) Aggregate by failure id (one row per failure in service_failure)
    failures_by_sid: Dict[str, Tuple[str, Optional[str]]] = {}
    for sid_raw, start, cause, _, _, _ in rows:
        if sid_raw not in failures_by_sid:
            failures_by_sid[sid_raw] = (start, cause)
        else:
            # Optional: could check consistency of start/cause here
            pass

    # 3) Insert into service_failure and build map original_id -> db_id
    sid_to_dbid: Dict[str, int] = {}
    with conn.cursor() as cur:
        for sid_raw, (start, cause) in failures_by_sid.items():
            cur.execute(
                f'INSERT INTO "{schema}"."service_failure" (start_time, cause) '
                f'VALUES (%s, %s) RETURNING id;',
                (start, cause),
            )
            db_id = cur.fetchone()[0]
            sid_to_dbid[sid_raw] = db_id

        # 4) Insert into city_service_failure (one row per city + failure)
        sql_city = f"""
            INSERT INTO "{schema}"."city_service_failure"
            (city_id, service_failure_id, end_time, status)
            VALUES (%s, %s, %s, %s)
        """
        data_city = []

        for sid_raw, start, cause, city_name, end_time, status in rows:
            city_id = ensure_city(conn, city_name, city_name_map)
            sf_db_id = sid_to_dbid[sid_raw]
            data_city.append((city_id, sf_db_id, end_time, status))

        if data_city:
            cur.executemany(sql_city, data_city)

    conn.commit()
    print(f"[INFO] {len(failures_by_sid)} service_failure rows loaded.")
    print(f"[INFO] {len(rows)} city_service_failure rows loaded.")


def load_rating(conn, path: str):
    """
    Load ratings from CSV and insert into rating table.
    """
    schema = CONFIG_DB["DB_SCHEMA"]
    with conn.cursor() as cur, open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sql = f"""
        INSERT INTO "{schema}"."rating"
        (rate, resolved, comment, service_order_id)
        VALUES (%s, %s, %s, %s)
        """
        data = []

        for row in reader:
            rate = int(row.get("rate")) if row.get("rate") else None
            resolved = to_bool(row.get("resolved"))
            comment = row.get("comment")
            soid = row.get("service_order_id")

            if rate is None or resolved is None or not soid:
                raise RuntimeError(f"Invalid row in rating.csv: {row}")

            data.append((rate, resolved, comment, soid))

        if data:
            cur.executemany(sql, data)

    conn.commit()
    print(f"[INFO] {len(data)} ratings loaded.")


# ---------------------------
# Load base CSVs into memory
# ---------------------------
def load_clients_csv(path: str):
    """
    Read clients CSV and return:
      - clients dict
      - address_map dict (address_key -> parsed address tuple)
    """
    clients = {}
    address_map = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = (row.get("client_id") or row.get("id") or "").strip()
            name = (row.get("client_name") or row.get("client") or "").strip()
            email = clean_email(row.get("email", ""))
            phone = row.get("phone", "")
            addr_raw = (row.get("address", "") or "").strip()
            prop_raw = (row.get("property_address", "") or "").strip()

            st, num, postal, city = parse_address(addr_raw)
            prop_st, prop_num, prop_postal, prop_city = parse_address(prop_raw)

            addr_key = None
            prop_key = None

            if any([st, num, postal, city]):
                addr_key = f"addr_{(st or '')}_{(num or '')}_{(postal or '')}_{(city or '')}"
                addr_key = re.sub(r"\s+", "_", addr_key.strip())
                address_map[addr_key] = (st, num, postal, city)
            elif cid:
                addr_key = f"addr_client_{cid}_UNKNOWN"
                address_map[addr_key] = ("UNKNOWN", None, None, None)

            if any([prop_st, prop_num, prop_postal, prop_city]):
                prop_key = f"addr_{(prop_st or '')}_{(prop_num or '')}_{(prop_postal or '')}_{(prop_city or '')}"
                prop_key = re.sub(r"\s+", "_", prop_key.strip())
                address_map[prop_key] = (prop_st, prop_num, prop_postal, prop_city)

            clients[cid] = {
                "name": name or None,
                "email": email,
                "phone": phone,
                "address_raw": addr_raw,
                "address_id": addr_key,
                "property_address_raw": prop_raw,
                "property_address_id": prop_key,
            }

    return clients, address_map


def load_technicians_csv(path: str):
    """
    Read technicians CSV and return:
      - technicians dict
      - set of service_type names
      - list of (technician_id, skill_name) pairs
    """
    techs = {}
    service_type_set = set()
    tech_skill_pairs = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = (row.get("technician_id") or row.get("id") or "").strip()
            name = (row.get("technician_name") or row.get("technician") or "").strip()
            email = clean_email(row.get("email", ""))
            phone = row.get("phone", "")
            center = (row.get("center", None) or "").strip() or None
            region = (row.get("region", None) or "").strip() or None
            skills_raw = (row.get("skills", "") or "")
            skills = [s.strip() for s in re.split(r",|;", skills_raw) if s.strip()]

            for s in skills:
                service_type_set.add(s)
                tech_skill_pairs.append((tid, s))

            techs[tid] = {
                "name": name or None,
                "email": email,
                "phone": phone,
                "center": center,
                "region": region,
                "skills": skills,
            }

    return techs, service_type_set, tech_skill_pairs


def load_connections_csv(path: str):
    """
    Read connections CSV and return:
      - connections dict
      - address_map dict for property addresses
    """
    conns = {}
    address_map = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = (row.get("connection_id") or row.get("id") or "").strip()
            client_id = (row.get("client_id") or "").strip()
            client_name = (row.get("client_name") or row.get("client") or "").strip()
            prop_raw = (row.get("property_address") or "").strip()

            st, num, postal, city = parse_address(prop_raw)
            prop_key = None

            if any([st, num, postal, city]):
                prop_key = f"addr_{(st or '')}_{(num or '')}_{(postal or '')}_{(city or '')}"
                prop_key = re.sub(r"\s+", "_", prop_key.strip())
                address_map[prop_key] = (st, num, postal, city)
            else:
                prop_key = f"addr_connection_{cid}_UNKNOWN"
                address_map[prop_key] = ("UNKNOWN", None, None, None)

            connection_type = (row.get("connection_type") or row.get("type") or "").strip() or None
            install_date = parse_date(row.get("install_date") or "")
            meter_serial = (row.get("meter_serial") or None)
            status = (row.get("status") or None)
            technician_id = (row.get("technician_id") or None)

            conns[cid] = {
                "type": connection_type,
                "install_date": install_date,
                "meter_serial": meter_serial.strip() if isinstance(meter_serial, str) else meter_serial,
                "status": status.strip() if isinstance(status, str) else status,
                "installer_id": technician_id.strip() if isinstance(technician_id, str) else technician_id,
                "client_id": client_id if client_id else None,
                "client_name": client_name or None,
                "property_address_id": prop_key,
            }

    return conns, address_map


def load_service_orders_csv(path: str):
    """
    Read service orders CSV and return:
      - service_orders dict
      - set of service_type names
    """
    sos = {}
    service_type_set = set()

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            soid = (row.get("service_order_id") or row.get("id") or "").strip()
            connection_id = (row.get("connection_id") or None)
            client_id = (row.get("client_id") or None)
            technician_id = (row.get("technician_id") or None)
            service_type = (row.get("service_type") or None)
            start_date = parse_date(row.get("start_date") or "")
            end_date = parse_date(row.get("end_date") or "")
            notes = (row.get("notes") or None)

            if service_type:
                service_type_set.add(service_type.strip())

            sos[soid] = {
                "connection_id": connection_id.strip() if isinstance(connection_id, str) else connection_id,
                "client_id": client_id.strip() if isinstance(client_id, str) else client_id,
                "technician_id": technician_id.strip() if isinstance(technician_id, str) else technician_id,
                "service_type": service_type.strip() if isinstance(service_type, str) else service_type,
                "start_date": start_date,
                "end_date": end_date,
                "notes": notes.strip() if isinstance(notes, str) else notes,
            }

    return sos, service_type_set


def load_bills_csv(path: str):
    """
    Read bills CSV and return a bills dict.
    """
    bills = {}

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            bid = (row.get("bill_id") or row.get("id") or "").strip()
            connection_id = (row.get("connection_id") or "").strip()
            period_start = parse_date(row.get("period_start") or "")
            period_end = parse_date(row.get("period_end") or "")
            kwh = (row.get("kwh_used") or row.get("kwh") or "").strip()
            amount = (row.get("amount") or "").strip()
            issue = parse_date(row.get("issue_date") or "")
            payment = parse_date(row.get("payment_date") or "")

            bills[bid] = {
                "connection_id": connection_id or None,
                "period_start": period_start,
                "period_end": period_end,
                "kwh_used": kwh or None,
                "amount": amount or None,
                "issue_date": issue,
                "payment_date": payment,
            }

    return bills


# ---------------------------
# Main orchestrator
# ---------------------------
def load_all(
    clients_csv,
    connections_csv,
    technicians_csv,
    service_orders_csv,
    bills_csv,
    city_csv,
    region_csv,
    service_failure_csv,
    rating_csv,
):
    """
    High-level function:
      - read all CSVs
      - load dimension tables (region, city, address, service_type, technician, client)
      - load fact tables (connection, bill, service_order, technician_skill, service_failure, rating)
    """
    # Read base CSVs
    clients, addr_map_from_clients = load_clients_csv(clients_csv)
    conns, addr_map_from_conns = load_connections_csv(connections_csv)
    techs, types_from_techs, tech_skill_pairs = load_technicians_csv(technicians_csv)
    sos, types_from_sos = load_service_orders_csv(service_orders_csv)
    bills = load_bills_csv(bills_csv)

    # Merge address maps from clients and connections
    address_map = {}
    address_map.update(addr_map_from_clients)
    address_map.update(addr_map_from_conns)

    # Collect all service types
    service_types = set()
    service_types.update(types_from_techs)
    service_types.update(types_from_sos)

    conn = connect_db()
    try:
        # 1) region and city from CSVs
        print("Inserting regions...")
        region_name_map = load_region(conn, region_csv)

        print("Inserting cities...")
        city_name_map = load_city(conn, city_csv, region_name_map)

        # 2) addresses
        print("Inserting addresses...")
        address_db_map = load_address(conn, address_map, city_name_map)

        # Update clients and connections with real address_id
        for cid, info in clients.items():
            old = info.get("address_id")
            clients[cid]["address_id"] = address_db_map.get(old) if (old and old in address_db_map) else None

        for conid, info in conns.items():
            old = info.get("property_address_id")
            conns[conid]["property_address_id"] = address_db_map.get(old) if (old and old in address_db_map) else None

        # 3) service_type
        print("Inserting service types...")
        st_map = load_service_type(conn, list(service_types))

        # 4) technicians
        print("Inserting technicians...")
        load_technician(conn, techs, region_name_map)

        # 5) clients
        print("Inserting clients...")
        load_client(conn, clients)

        # 6) connections
        print("Inserting connections...")
        load_connections(conn, conns)

        # 7) bills
        print("Inserting bills...")
        load_bill(conn, bills)

        # 8) service_orders
        print("Inserting service_orders...")
        load_service_order(conn, sos, st_map)

        # 9) technician_skill
        print("Inserting technician_skill entries...")
        load_technician_skill(conn, tech_skill_pairs, st_map)

        # 10) service_failure / city_service_failure / rating
        print("Inserting service_failure + city_service_failure...")
        load_service_failure(conn, service_failure_csv, city_name_map)

        print("Inserting ratings...")
        load_rating(conn, rating_csv)

        print("Load completed successfully.")
    finally:
        conn.close()


if __name__ == "__main__":
    print("Clearing data with DELETE ...")
    clear_data_delete()

    print("\n-----------------------------------------------\n")
    print("Loading all data from CSVs...")
    load_all(
        clients_csv=CSV_PATHS["CLIENTS"],
        connections_csv=CSV_PATHS["CONNECTIONS"],
        technicians_csv=CSV_PATHS["TECHNICIANS"],
        service_orders_csv=CSV_PATHS["SERVICES"],
        bills_csv=CSV_PATHS["BILLS"],
        city_csv=CSV_PATHS["CITY"],
        region_csv=CSV_PATHS["REGION"],
        service_failure_csv=CSV_PATHS["SERVICE_FAILURE"],
        rating_csv=CSV_PATHS["RATING"],
    )

    print("Done.")