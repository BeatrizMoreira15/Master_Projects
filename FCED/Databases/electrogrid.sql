DROP TABLE IF EXISTS rating;
DROP TABLE IF EXISTS city_service_failure;
DROP TABLE IF EXISTS service_failure;
DROP TABLE IF EXISTS bill;
DROP TABLE IF EXISTS service_order;
DROP TABLE IF EXISTS technician_skill;
DROP TABLE IF EXISTS connection;
DROP TABLE IF EXISTS client;
DROP TABLE IF EXISTS technician;
DROP TABLE IF EXISTS service_type;
DROP TABLE IF EXISTS address;
DROP TABLE IF EXISTS city;
DROP TABLE IF EXISTS region;


-- Region(id, name[NN, UK]) 
CREATE TABLE region (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);


-- City(id, name[NN, UK], #region->Region) 
CREATE TABLE city (
    id SERIAL PRIMARY KEY,
    name TEXT,
    region_id INT REFERENCES region(id) NOT NULL,
    UNIQUE(name, region_id)
);


-- Address(id, street[NN], number, postal_code, city)
CREATE TABLE address (
    id SERIAL PRIMARY KEY,
    street TEXT NOT NULL,
    number INT,
    postal_code VARCHAR(8),
    city_id INT REFERENCES city(id)
);


-- Client(id, name[NN], email[UK], phone[NN], #address->Address)
CREATE TABLE client (
    id VARCHAR(5) PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone NUMERIC(9,0),
    address_id INT REFERENCES address(id)
);


-- Technician(id, name[NN], email, phone, center[NN], region[NN])
CREATE TABLE technician (
    id VARCHAR(5) PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone NUMERIC(9,0),
    center TEXT NOT NULL,
    region_id INT REFERENCES region(id) NOT NULL
);


-- Service_type(id, name[NN,UK])
CREATE TABLE service_type (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);


-- Technician_skill(#technician->Technician, #service_type->Service_type)
CREATE TABLE technician_skill (
    technician_id VARCHAR(5) NOT NULL REFERENCES technician(id) ON DELETE CASCADE,
    skill_id INT NOT NULL REFERENCES service_type(id) ON DELETE CASCADE,
    PRIMARY KEY (technician_id, skill_id)
);


-- Connection(id, type[NN], install_date[NN], meter_serial[NN], status[NN], #installer->Technician[NN], #client->Client[NN], #property->Address[NN])
CREATE TABLE connection (
    id VARCHAR(7) PRIMARY KEY,
    type TEXT NOT NULL,
    install_date DATE NOT NULL,
    meter_serial TEXT NOT NULL,
    status TEXT NOT NULL,
    installer_id VARCHAR(5) NOT NULL REFERENCES technician(id) ON DELETE RESTRICT,
    client_id VARCHAR(5) NOT NULL REFERENCES client(id) ON DELETE RESTRICT,
    property_id INT NOT NULL REFERENCES address(id) ON DELETE RESTRICT
);


-- Service_order(id, start_date[NN], end_date, notes, #technician->Technician[NN], #connection->Connection[NN], #service_type->Service_type[NN], #client->Client)
CREATE TABLE service_order (
    id VARCHAR(7) PRIMARY KEY,
    start_date DATE NOT NULL,
    end_date DATE,
    notes TEXT,
    technician_id VARCHAR(5) NOT NULL REFERENCES technician(id) ON DELETE RESTRICT,
    connection_id VARCHAR(7) NOT NULL REFERENCES connection(id) ON DELETE CASCADE,               
    service_type_id INT NOT NULL REFERENCES service_type(id) ON DELETE RESTRICT,
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);


-- Bill(id, billing period[NN], consumption[NN], amount[NN], issue_date[NN], payment_date, #connection->Connection[NN])
CREATE TABLE bill (
    id VARCHAR(6) PRIMARY KEY,
    period_start date NOT NULL,
    period_end date NOT NULL,
    consumption NUMERIC(12,3) NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    issue_date DATE NOT NULL,
    payment_date DATE, 
    connection_id VARCHAR(7) NOT NULL REFERENCES connection(id) ON DELETE CASCADE,
    CHECK (payment_date IS NULL OR payment_date >= issue_date)
);


-- Service_failure(id, start, cause)
CREATE TABLE service_failure (
    id SERIAL PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    cause TEXT
);


-- City_service_failure(#city->City, #service_failure->Service_failure, end, duration, status)
CREATE TABLE city_service_failure (
    city_id INT REFERENCES city(id) ON DELETE CASCADE,
    service_failure_id INT REFERENCES service_failure(id) ON DELETE CASCADE,
    end_time TIMESTAMP,
    status TEXT NOT NULL,
    PRIMARY KEY (city_id, service_failure_id)
);


-- Rating(id, rate, resolved, comment, #service_order->Service_order)
CREATE TABLE rating (
    id SERIAL PRIMARY KEY,
    rate INT NOT NULL,
    resolved BOOLEAN NOT NULL,
    comment TEXT,
    service_order_id VARCHAR(7) NOT NULL REFERENCES service_order(id),
    CHECK (rate >= 1 AND rate <= 5)
); 



-------------------------
-- TRIGGERS
-------------------------

-- A criar (os que existiam estavam relacionados com person)






-------------------------
-- ÍNDICES (NAO SE DEVEMOS POR)
-------------------------

-- Índice na tabela connection (client_id)
DROP INDEX IF EXISTS idx_connection_client;
CREATE INDEX idx_connection_client ON connection (client_id);

DROP INDEX IF EXISTS idx_service_order_connection;
CREATE INDEX idx_service_order_connection ON service_order (connection_id);

DROP INDEX IF EXISTS idx_service_order_technician;
CREATE INDEX idx_service_order_technician ON service_order (technician_id);

-- Índices na tabela bill
DROP INDEX IF EXISTS idx_bill_connection;
CREATE INDEX idx_bill_connection ON bill (connection_id);