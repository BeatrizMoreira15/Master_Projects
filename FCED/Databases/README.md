# ElectroGrid Database Project

This project implements a relational database and command-line application for the ElectroGrid electricity distribution company. It is based on synthetic operational data (clients, connections, technicians, service orders and bills) and is intended for educational use in data modeling, SQL, and ETL with Python. 

## How to change the connection properties

The database connection settings used by the project are defined in the Python scripts that connect to PostgreSQL (`load_electrogrid.py` and `electrogrid.py`).

At the top of each script there is a small configuration block where you can change the connection parameters:

```python
CONFIG_DB = {
    "DB_NAME": "fced06",               # database name
    "DB_USER": "fced06",               # PostgreSQL user
    "DB_PASSWORD": "db062025",         # password for that user
    "DB_HOST": "dbm.fe.up.pt",         # database server address
    "DB_PORT": "5433",                 # PostgreSQL port (default is 5432)
    "DB_SCHEMA": "electrogrid",        # schema where the ElectroGrid tables are created
}
```

To use a different PostgreSQL server or user, update these values, save the file and run the scipt again, making sure these new parameters match your database configuration.



## Overall structure of the project

The project is organized as follows:

```text
electrogrid_project/
├─ README.md
├─ uml.png
├─ relational.txt
├─ electrogrid.sql
├─ load_electrogrid.py
├─ electrogrid.py
└─ data/
   ├─ city.csv
   ├─ rating.csv
   ├─ region.csv
   └─ service_failure.csv
```

**Note:** 

According to the assignment instructions, the original raw CSV files provided (`clients_raw.csv`, `connections_raw.csv`, `technicians_raw.csv`, `service_orders_raw.csv`, `bills_raw.csv`) are **not** included in the submitted `electrogrid_project.zip`. The `data` folder in this project already contains additional CSV files used by the model extension (`city.csv`, `rating.csv`, `region.csv`, `service_failure.csv`).

To fully run the project, you must manually copy the five raw CSV files provided in `electrogrid_raw_data_v2.zip` into the **existing** `data/` folder, keeping exactly the same filenames as above.



## Main Design Decisions

- **Generalisation of people into `Person`**  
  In the raw files (`clients_raw.csv` and `technicians_raw.csv`) the columns `client_name` / `technician_name`, `email` and `phone` are common.  
  At the conceptual (UML) level we introduced a superclass **Person** with these common attributes and modeled **Client** and **Technician** as specialisations. This captures the idea that both clients and technicians are people and avoids duplicating attributes in the conceptual model.

  However, when converting to the relational model we decided **not** to keep a separate `Person` table.  
  Instead, we created two tables, `Client` and `Technician`, each with its own `name`, `email` and `phone` columns. This introduces a small amount of redundancy, but it simplifies the schema and the queries (we do not need extra joins through a `Person` table) and there were no other subtypes that would benefit from sharing that table.

- **Regions and technicians**  
  The column `region` in `technicians_raw.csv` was turned into a separate **Region** entity.  
  Each technician now *works in* exactly one region, which allows region-level analysis (like number of service orders per region) and avoids repeating the same region name in every technician row.

- **Addresses, cities and regions**  
  The raw datasets contain free-text addresses (`address` and `property_address` in `clients_raw.csv` and `connections_raw.csv`).  
  We normalised this by creating an **Address** entity with `street`, `number` and `postal_code` and by extracting the city name into a separate **City** entity (using the `city` column from `connections_raw.csv` and parsing the address strings).  
  Each address is located in exactly one city and each city is located in exactly one region. This avoids storing long address strings repeatedly and makes geographic queries simpler.

- **Service types and technician skills**  
  We noticed that the `service_type` column in `service_orders_raw.csv` matches the values in the `skills` column of `technicians_raw.csv`.  
  We therefore created a **ServiceType** entity and:  
  - Linked `ServiceOrder` to exactly one `ServiceType`;  
  - Introduced a many-to-many relationship between `Technician` and `ServiceType` (“has skill”).  
  This makes it possible to check, for example, whether a technician has the required skills for a given service order.

- **Client–connection as the central relationship**  
  In the raw files, the client information is repeated in several places: `client_id` and `client_name` appear in `clients_raw.csv`, `connections_raw.csv`, `service_orders_raw.csv` and `bills_raw.csv`.  
  In the conceptual model, **Client** is the owner of one or more **Connections**, and **ServiceOrder** and **Bill** are always associated with a connection.  
  We decided that a client can only request service orders and receive bills for connections they own, so we removed the direct links from `Client` to `ServiceOrder` and `Bill`; the relationship through **Connection** is enough.

- **Precedence of `connections_raw` over `clients_raw`**  
  When there were inconsistencies between the client information in `clients_raw.csv` and the ownership stored in `connections_raw.csv`, we treated `connections_raw.csv` as the authoritative source for the `Client`–`Connection` relationship.  
  New clients that appeared only in `connections_raw.csv` were inserted into the **Client** table even if they were missing from `clients_raw.csv`.

- **Handling incomplete client and technician data**  
  Because some entries only have an `id` and a name (but no email, phone or address), we kept only the `name` attribute as `NOT NULL` in **Client** and **Technician**.  
  This allows us to preserve as many rows as possible (especially those needed to satisfy foreign keys from `Connection`), while still enforcing that every person has at least a name.

- **Service failures (model extension)**  
  As an extension to the original model, we introduced **ServiceFailure** to represent outages in the electricity distribution network.  
  Each failure has a start time and a cause and is associated with a city; it *affects* one or more cities. For each affected city we keep the end time and status.  
  Conceptually we assume that distribution is organised at city level (each city has an associated distribution centre), so a failure impacts at least one entire city.

- **Service ratings (model extension)**  
  We also added a **Rating** entity to store customer feedback about completed service orders.  
  A rating is linked to a single `ServiceOrder` and contains a numeric `rate` (1–5), a `resolved` flag and an optional textual `comment`.  
  This allows us to compute statistics such as average rating per technician or per service type and to analyse unresolved issues.




## Contributions

This project was developed by group **DB-06**:
- Beatriz Sonnemberg, *up202206098*
- Luana Lima, *up202206845*
- Maria Beatriz Moreira, *up202208293*
- Marta Costa, *up202207879*

----

All group members contributed to the main parts of the work, including:

- Understanding the raw datasets  
- Designing the conceptual (UML) and relational models  
- Implementing the PostgreSQL schema (`electrogrid.sql`)  
- Developing and testing the data loading script (`load_electrogrid.py`)  
- Implementing the command-line application (`electrogrid.py`)  
- Designing and integrating the model extension and example data  

While some tasks were occasionally led by one member or another, the overall development was shared and carried out jointly by the whole group.

----

> *Master in Data Science and Engineering - FEUP*
> 
> *FCED Database - 03/11/2025*