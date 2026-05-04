import psycopg2
from colorama import Fore, Style
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date, timedelta

def connect_db():
    conn = psycopg2.connect(
        dbname=CONFIG_DB["DB_NAME"],
        user=CONFIG_DB["DB_USER"],
        password=CONFIG_DB["DB_PASSWORD"],
        host=CONFIG_DB["DB_HOST"],
        port=CONFIG_DB["DB_PORT"],
        options=f"-c search_path={CONFIG_DB['DB_SCHEMA']}"
    )
    return conn

# ==============================
# CORE MENU FUNCTIONS
# ==============================
def search_client():
    conn = connect_db()
    cur = conn.cursor()
    name = input("Enter client name or part of it: ")
    cur.execute("""
        SELECT id, name, email, phone 
        FROM client 
        WHERE LOWER(name) LIKE LOWER(%s)
    """, ('%' + name + '%',))
    rows = cur.fetchall()
    if rows:
        print(Fore.CYAN + "\nClients found:" + Style.RESET_ALL)
        for r in rows:
            print(f"ID: {r[0]} | Name: {r[1]} | Email: {r[2]} | Phone: {r[3]}")
    else:
        print(Fore.RED + "No clients found." + Style.RESET_ALL)
    cur.close()
    conn.close()

def list_active_connections():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, type, status 
        FROM connection
        WHERE status = 'Active'
    """)
    rows = cur.fetchall()
    print(Fore.CYAN + "\nActive Connections:" + Style.RESET_ALL)
    for r in rows:
        print(f"Connection ID: {r[0]}, Type: {r[1]}, Status: {r[2]}")
    cur.close()
    conn.close()

def show_service_orders():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, start_date, end_date, notes
        FROM service_order
        ORDER BY start_date DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    print(Fore.CYAN + "\nRecent Service Orders:" + Style.RESET_ALL)
    for r in rows:
        print(f"ID: {r[0]}, Start: {r[1]}, End: {r[2]}, Notes: {r[3]}")
    cur.close()
    conn.close()

def add_rating():
    conn = connect_db()
    cur = conn.cursor()
    service_order_id = input("Enter service order ID (e.g., SO0123): ")
    try:
        rate = int(input("Enter rating (1–5): "))
        if rate < 1 or rate > 5:
            print(Fore.RED + "Invalid rate. Must be between 1 and 5." + Style.RESET_ALL)
            return
    except ValueError:
        print(Fore.RED + "Please enter a valid integer for rate." + Style.RESET_ALL)
        return
    resolved = input("Was the issue resolved? (y/n): ").lower() == "y"
    comment = input("Comment: ")
    cur.execute("""
        INSERT INTO rating (rate, resolved, comment, service_order_id)
        VALUES (%s, %s, %s, %s)
    """, (rate, resolved, comment, service_order_id))
    conn.commit()
    print(Fore.GREEN + "Rating added successfully." + Style.RESET_ALL)
    cur.close()
    conn.close()

def show_statistics():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT ROUND(AVG(rate),2) FROM rating;")
    avg_rate = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM rating WHERE resolved = FALSE;")
    unresolved = cur.fetchone()[0]
    print(Fore.CYAN + "\n=== Service Statistics ===" + Style.RESET_ALL)
    print(f"Average Rating: {avg_rate if avg_rate else 'N/A'}")
    print(f"Unresolved Cases: {unresolved}")
    cur.close()
    conn.close()

def show_power_outages():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT cf.id, c.name, cf.start_time, csf.end_time, cf.cause, csf.status
        FROM service_failure cf
        JOIN city_service_failure csf ON cf.id = csf.service_failure_id
        JOIN city c ON c.id = csf.city_id
        ORDER BY cf.start_time DESC
        LIMIT 10;
    """)
    rows = cur.fetchall()
    print(Fore.CYAN + "\nRecent Power Outages:" + Style.RESET_ALL)
    for r in rows:
        print(f"[{r[1]}] Cause: {r[4]} | Start: {r[2]} | End: {r[3]} | Status: {r[5]}")
    cur.close()
    conn.close()

# ==============================
# EXTENDED FEATURES
# ==============================

def add_new_client():
    conn = connect_db()
    cur = conn.cursor()
    name = input("Client name: ")
    email = input("Email: ")
    phone = input("Phone (9 digits): ")
    street = input("Street: ")
    number = input("Number: ")
    
    cur.execute("SELECT id, name FROM city ORDER BY name;")
    cities = cur.fetchall()
    for c in cities:
        print(f"{c[0]} - {c[1]}")
    city_id = input("Choose city ID from list: ")
    
    cur.execute("""
        INSERT INTO address (street, number, postal_code, city_id)
        VALUES (%s, %s, %s, %s) RETURNING id
    """, (street, number, "0000-000", city_id))
    address_id = cur.fetchone()[0]
    
    client_id = input("Assign client ID (e.g., C1000): ")
    cur.execute("""
        INSERT INTO client (id, name, email, phone, address_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (client_id, name, email, phone, address_id))
    conn.commit()
    print(Fore.GREEN + "Client added successfully." + Style.RESET_ALL)
    cur.close()
    conn.close()

def add_new_technician():
    conn = connect_db()
    cur = conn.cursor()

    print("\nEnter new technician details:")

    tech_id = input("Technician ID (e.g., T0001): ").strip()
    name = input("Full name: ").strip()
    email = input("Email: ").strip()
    
    phone_input = input("Phone number (only digits, e.g., 912345678): ").strip()
    if not phone_input.isdigit() or len(phone_input) != 9:
        print(Fore.RED + "Invalid phone number. Must be 9 digits." + Style.RESET_ALL)
        return
    phone = int(phone_input)

    center = input("Center: ").strip()

    cur.execute("SELECT id, name FROM region ORDER BY name;")
    regions = cur.fetchall()
    print("\nAvailable Regions:")
    for r in regions:
        print(f"{r[0]}: {r[1]}")
    try:
        region_id = int(input("Enter Region ID from the list above: "))
        if region_id not in [r[0] for r in regions]:
            print(Fore.RED + "Invalid Region ID." + Style.RESET_ALL)
            return
    except ValueError:
        print(Fore.RED + "Invalid input. Must be a number." + Style.RESET_ALL)
        return

    try:
        cur.execute("""
            INSERT INTO technician (id, name, email, phone, center, region_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (tech_id, name, email, phone, center, region_id))
        conn.commit()
        print(Fore.GREEN + "Technician added successfully!" + Style.RESET_ALL)
    except psycopg2.Error as e:
        print(Fore.RED + f"Error adding technician: {e}" + Style.RESET_ALL)
        conn.rollback()

    cur.close()
    conn.close()

def show_technician_feedback():
    conn = connect_db()
    cur = conn.cursor()
    while True:
        print(Fore.GREEN + "\n--- Technician Feedback Menu ---" + Style.RESET_ALL)
        print("1) Search technician by name")
        print("2) Show top N technicians for a service type")
        print("3) Exit menu")
        choice = input("Choose an option [1-3]: ").strip()

        if choice == '1':
            name = input("Enter technician name (or part of it): ").strip()
            cur.execute("""
                SELECT id, name
                FROM technician
                WHERE LOWER(name) LIKE LOWER(%s)
                ORDER BY name;
            """, ('%' + name + '%',))
            technicians = cur.fetchall()

            if not technicians:
                print(Fore.RED + "No technicians found with that name." + Style.RESET_ALL)
                continue

            for tech in technicians:
                tech_id, full_name = tech

                cur.execute("""
                    SELECT ROUND(AVG(r.rate)::numeric, 2) AS avg_rate,
                           COUNT(r.id) AS ratings_count
                    FROM technician t
                    LEFT JOIN service_order so ON so.technician_id = t.id
                    LEFT JOIN rating r ON r.service_order_id = so.id
                    WHERE t.id = %s
                    GROUP BY t.id;
                """, (tech_id,))
                row = cur.fetchone()
                if row:
                    avg, count = row
                else:
                    avg, count = None, 0

                cur.execute("""
                    SELECT r.comment, r.rate, r.id
                    FROM rating r
                    JOIN service_order so ON r.service_order_id = so.id
                    WHERE so.technician_id = %s AND r.comment IS NOT NULL
                    ORDER BY r.id DESC
                    LIMIT 5;
                """, (tech_id,))
                comments = cur.fetchall()

                print(Fore.CYAN + f"\nTechnician: {full_name} (ID: {tech_id})" + Style.RESET_ALL)
                print(f"Average Rating: {avg if avg is not None else 'N/A'}    Number of ratings: {count}")
                if comments:
                    print("Recent comments:")
                    for c in comments:
                        comment_text, rate, rid = c
                        print(f" - [{rate}] {comment_text}")
                else:
                    print("No comments yet.")

        elif choice == '2':
            cur.execute("SELECT id, name FROM service_type ORDER BY name;")
            service_types = cur.fetchall()
            print("\nAvailable service types:")
            print("0) All service types")
            for st in service_types:
                print(f"{st[0]}) {st[1]}")

            sel = input("Choose service type ID (or 0 for all): ").strip()
            if sel == '':
                sel = '0'
            try:
                sel_id = int(sel)
            except ValueError:
                print(Fore.RED + "Invalid service type selection." + Style.RESET_ALL)
                continue

            try:
                n = int(input("How many top technicians to show? [default 5]: ") or 5)
            except ValueError:
                n = 5
            try:
                min_ratings = int(input("Minimum number of ratings required (0 = no minimum) [default 0]: ") or 0)
            except ValueError:
                min_ratings = 0

            if sel_id == 0:
                cur.execute("""
                    SELECT t.id, t.name,
                           ROUND(AVG(r.rate)::numeric, 2) AS avg_rate,
                           COUNT(r.id) AS ratings_count
                    FROM technician t
                    LEFT JOIN service_order so ON so.technician_id = t.id
                    LEFT JOIN rating r ON r.service_order_id = so.id
                    GROUP BY t.id, t.name
                    HAVING COUNT(r.id) >= %s
                    ORDER BY avg_rate DESC NULLS LAST, ratings_count DESC
                    LIMIT %s;
                """, (min_ratings, n))
            else:
                cur.execute("""
                    SELECT t.id, t.name,
                           ROUND(AVG(r.rate)::numeric, 2) AS avg_rate,
                           COUNT(r.id) AS ratings_count
                    FROM technician t
                    JOIN technician_skill ts ON ts.technician_id = t.id
                    LEFT JOIN service_order so ON so.technician_id = t.id
                    LEFT JOIN rating r ON r.service_order_id = so.id
                    WHERE ts.skill_id = %s
                    GROUP BY t.id, t.name
                    HAVING COUNT(r.id) >= %s
                    ORDER BY avg_rate DESC NULLS LAST, ratings_count DESC
                    LIMIT %s;
                """, (sel_id, min_ratings, n))

            rows = cur.fetchall()

            if rows:
                if sel_id == 0:
                    header = f"Top {n} technicians (all service types, min {min_ratings} ratings)"
                else:
                    cur.execute("SELECT name FROM service_type WHERE id = %s;", (sel_id,))
                    st_row = cur.fetchone()
                    st_name = st_row[0] if st_row else f"id {sel_id}"
                    header = f"Top {n} technicians for service '{st_name}' (min {min_ratings} ratings)"

                print(Fore.CYAN + "\n" + header + ":" + Style.RESET_ALL)
                for i, (tid, tname, avg_rate, ratings_count) in enumerate(rows, start=1):
                    avg_display = avg_rate if avg_rate is not None else 'N/A'
                    print(f"{i}. {tname} (ID: {tid}) — Avg: {avg_display}, Ratings: {ratings_count}")

                see_details = input("See recent comments for any of these technicians? Enter technician ID or press Enter to skip: ").strip()
                if see_details:
                    cur.execute("""
                        SELECT r.comment, r.rate, r.id
                        FROM rating r
                        JOIN service_order so ON r.service_order_id = so.id
                        WHERE so.technician_id = %s
                        ORDER BY r.id DESC
                        LIMIT 10;
                    """, (see_details,))
                    comments = cur.fetchall()
                    if comments:
                        print(Fore.YELLOW + f"\nRecent comments for technician {see_details}:" + Style.RESET_ALL)
                        for c in comments:
                            comment_text, rate, rid = c
                            print(f" - [{rate}] {comment_text}")
                    else:
                        print(Fore.RED + "No comments/ratings found for that technician." + Style.RESET_ALL)
            else:
                print(Fore.RED + "No technicians meet the criteria." + Style.RESET_ALL)

        elif choice == '3':
            print("Exiting technician feedback menu.")
            break
        else:
            print(Fore.RED + "Invalid option. Choose 1, 2 or 3." + Style.RESET_ALL)

    cur.close()
    conn.close()

def most_requested_services():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT st.name, COUNT(*) as total
        FROM service_order so
        JOIN service_type st ON so.service_type_id = st.id
        GROUP BY st.name
        ORDER BY total DESC
        LIMIT 5
    """)
    rows = cur.fetchall()
    print(Fore.CYAN + "\nTop 5 Most Requested Services:" + Style.RESET_ALL)
    for r in rows:
        print(f"{r[0]} - {r[1]} orders")
    cur.close()
    conn.close()

def average_outage_duration():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name,
               AVG(EXTRACT(EPOCH FROM (csf.end_time - cf.start_time))/3600) AS avg_hours
        FROM service_failure cf
        JOIN city_service_failure csf ON cf.id = csf.service_failure_id
        JOIN city c ON c.id = csf.city_id
        WHERE csf.end_time IS NOT NULL
        GROUP BY c.name
        ORDER BY c.name
    """)
    rows = cur.fetchall()
    print(Fore.CYAN + "\nAverage Outage Duration per City (hours):" + Style.RESET_ALL)
    for r in rows:
        print(f"{r[0]}: {round(r[1],2)} h")
    cur.close()
    conn.close()

def show_last_two_bills():
    conn = connect_db()
    cur = conn.cursor()
    prop_id = input("Enter property (address) ID: ")

    cur.execute("""
        SELECT c.name AS client_name,
               cn.id AS connection_id,
               b.period_start,
               b.period_end,
               b.consumption,
               b.amount,
               b.payment_date
        FROM (
            SELECT b.*,
                   ROW_NUMBER() OVER (PARTITION BY b.connection_id ORDER BY b.issue_date DESC, b.period_end DESC) AS rn
            FROM bill b
            JOIN connection cn2 ON b.connection_id = cn2.id
            WHERE cn2.property_id = %s
        ) b
        JOIN connection cn ON b.connection_id = cn.id
        JOIN client c ON cn.client_id = c.id
        WHERE b.rn <= 2
        ORDER BY cn.id, b.period_end DESC;
    """, (prop_id,))

    rows = cur.fetchall()

    if rows:
        print(Fore.CYAN + f"\nLast 2 invoices per connection for property{prop_id}:" + Style.RESET_ALL)
        current_conn = None
        for r in rows:
            client_name, connection_id, period_start, period_end, consumption, amount, payment_date = r
            if connection_id != current_conn:
                print(Fore.YELLOW + f"\nConnection {connection_id} (Client: {client_name})" + Style.RESET_ALL)
                current_conn = connection_id
            print(f"  Period: {period_start} to {period_end}, Consumption: {consumption} kWh, "
                  f"Value: €{amount}, Payment: {payment_date}")
    else:
        print(Fore.RED + "No invoices found for this property." + Style.RESET_ALL)

    cur.close()
    conn.close()

def cities_without_service():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT c.id, c.name
        FROM city c
        JOIN city_service_failure csf ON c.id = csf.city_id
        WHERE csf.status != 'resolved'
        ORDER BY c.name
    """)
    rows = cur.fetchall()
    print(Fore.CYAN + "\nCities currently without service:" + Style.RESET_ALL)
    if rows:
        for r in rows:
            print(f"  ID: {r[0]} — {r[1]}")
    else:
        print(Fore.YELLOW + "All cities currently have service available." + Style.RESET_ALL)
    cur.close()
    conn.close()

def technicians_for_service_failures():
    conn = connect_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT DISTINCT c.id, c.name
            FROM city c
            JOIN city_service_failure csf ON c.id = csf.city_id
            WHERE csf.status != 'resolved'
            ORDER BY c.name;
        """)
        cities = cur.fetchall()

        if not cities:
            print(Fore.RED + "No cities currently have active service failures." + Style.RESET_ALL)
            return

        print(Fore.CYAN + "\n=== Cities with Active Service Failures ===" + Style.RESET_ALL)
        for c in cities:
            print(f"  {c[0]} - {c[1]}")

        try:
            selected_city_id = int(input("\nEnter the ID of the city to view details: ").strip())
        except ValueError:
            print(Fore.RED + "Invalid input. Please enter a valid number." + Style.RESET_ALL)
            return

        city_ids = [c[0] for c in cities]
        if selected_city_id not in city_ids:
            print(Fore.RED + "City not found or not affected by any active failure." + Style.RESET_ALL)
            return

        cur.execute("""
            SELECT c.name AS city_name,
                   c.region_id AS region_id,
                   sf.id AS failure_id,
                   sf.cause,
                   csf.status
            FROM city c
            JOIN city_service_failure csf ON c.id = csf.city_id
            JOIN service_failure sf ON sf.id = csf.service_failure_id
            WHERE c.id = %s AND csf.status != 'resolved';
        """, (selected_city_id,))
        failures = cur.fetchall()

        if not failures:
            print(Fore.YELLOW + "No active service failures found for this city." + Style.RESET_ALL)
            return

        print(Fore.MAGENTA + "\n--- Urgency Levels ---" + Style.RESET_ALL)
        print("  Low    → up to 5 addresses affected")
        print("  Medium → 6 to 15 addresses affected")
        print("  High   → more than 15 addresses affected")

        for city_name, region_id, sf_id, cause, status in failures:
            cur.execute("""
                SELECT COUNT(a.id)
                FROM address a
                LEFT JOIN connection cn ON cn.property_id = a.id
                WHERE a.city_id = %s;
            """, (selected_city_id,))
            affected = cur.fetchone()[0]

            if affected <= 5:
                urgency = "Low"
            elif affected <= 15:
                urgency = "Medium"
            else:
                urgency = "High"

            cur.execute("""
                SELECT COUNT(*) 
                FROM technician
                WHERE region_id = %s;
            """, (region_id,))
            tech_count = cur.fetchone()[0]

            print(Fore.CYAN + f"\nCity: {city_name} (ID: {selected_city_id})" + Style.RESET_ALL)
            print(f"  Service Failure ID: {sf_id} | Status: {status}")
            print(f"  Affected addresses: {affected} | Urgency: {urgency}")
            print(f"  Available technicians in same region: {tech_count}")

    except Exception as e:
        import traceback
        print(Fore.RED + "Unexpected error in technicians_for_service_failures:" + Style.RESET_ALL)
        print(Fore.RED + str(e) + Style.RESET_ALL)
        print(Fore.YELLOW + "Traceback (most recent call last):" + Style.RESET_ALL)
        traceback.print_exc()
    finally:
        cur.close()
        conn.close()


# ==============================
# Plots
# ==============================


def plot_monthly_consumption_by_region(months=12, top_n=5, conn=None, save_path="consumption_by_region.png"):
    conn = connect_db()  
    end_date = date.today().replace(day=1)  
    sql_months_interval = f"{months} months"

    query = f"""
        SELECT
            r.name AS region,
            date_trunc('month', b.period_end)::date AS month,
            SUM(b.consumption) AS total_consumption
        FROM bill b
        JOIN connection cn ON b.connection_id = cn.id
        JOIN address a ON cn.property_id = a.id
        JOIN city c ON a.city_id = c.id
        JOIN region r ON c.region_id = r.id
        WHERE b.period_end >= (date_trunc('month', current_date) - INTERVAL %s)
        GROUP BY r.name, month
        ORDER BY month;
    """

    try:
        df = pd.read_sql_query(query, conn, params=(sql_months_interval,))
    finally:
            conn.close()


    df_pivot = df.pivot_table(index='month', columns='region', values='total_consumption', aggfunc='sum').fillna(0)

    region_totals = df_pivot.sum(axis=0).sort_values(ascending=False)
    top_regions = region_totals.head(top_n).index.tolist()

    df_top = df_pivot[top_regions]

    plt.figure(figsize=(12, 6))
    for col in df_top.columns:
        plt.plot(df_top.index, df_top[col], marker='o', label=col)

    plt.title(f"Monthly Energy Consumption by Region — Last {months} Months (Top {top_n} Regions)")
    plt.xlabel("Month")
    plt.ylabel("Consumption (unit as in 'bill' table, e.g., kWh)")
    plt.grid(True)
    plt.legend(title="Region", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()


    plt.savefig(save_path)
    plt.show()

    return df_top



# ==============================
# MAIN MENU
# ==============================
def menu():
    while True:
        print(Fore.CYAN + "\n=== ElectroGrid Menu ===" + Style.RESET_ALL)
        print("[1] Search for a client")
        print("[2] List active connections")
        print("[3] Show recent service orders")
        print("[4] Add a new service rating")
        print("[5] Show service statistics")
        print("[6] Show power outage log")
        print("[7] Add a new client")
        print("[8] Show technician feedback")
        print("[9] Most requested services")
        print("[10] Average outage duration per city")
        print("[11] Show last two bills for a property")
        print("[12] Add a new technician")
        print("[13] Cities without service")
        print("[14] Technicians for service failures")
        print("[15] Plots")
        print("[0] Exit")
        choice = input("\nChoose an option: ")

        if choice == "1":
            search_client()
        elif choice == "2":
            list_active_connections()
        elif choice == "3":
            show_service_orders()
        elif choice == "4":
            add_rating()
        elif choice == "5":
            show_statistics()
        elif choice == "6":
            show_power_outages()
        elif choice == "7":
            add_new_client()
        elif choice == "8":
            show_technician_feedback()
        elif choice == "9":
            most_requested_services()
        elif choice == "10":
            average_outage_duration()
        elif choice == "11":
            show_last_two_bills()
        elif choice == "12":
            add_new_technician()
        elif choice == "13":
            cities_without_service()
        elif choice == "14":
            technicians_for_service_failures()
        elif choice == "15":
            plot_monthly_consumption_by_region(months=12, top_n=6) 
        elif choice == "0":
            print(Fore.GREEN + "Exiting program..." + Style.RESET_ALL)
            break
        else:
            print(Fore.RED + "Invalid option. Try again." + Style.RESET_ALL)


# ==============================
# RUN PROGRAM
# ==============================
if __name__ == "__main__":
    print(Fore.YELLOW + "Connecting to ElectroGrid System..." + Style.RESET_ALL)
    menu()