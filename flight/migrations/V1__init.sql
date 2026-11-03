CREATE TYPE flight_status      AS ENUM ('SCHEDULED', 'DEPARTED', 'CANCELLED', 'COMPLETED');
CREATE TYPE reservation_status AS ENUM ('ACTIVE', 'RELEASED', 'EXPIRED');

CREATE TABLE airlines (
    code CHAR(2)      PRIMARY KEY CHECK (code ~ '^[A-Z0-9]{2}$'),
    name VARCHAR(100) NOT NULL CHECK (name <> '')
);

CREATE TABLE flights (
    id              BIGSERIAL PRIMARY KEY,
    airline_code    CHAR(2)        NOT NULL REFERENCES airlines (code),
    flight_number   VARCHAR(4)     NOT NULL CHECK (flight_number ~ '^[0-9]{1,4}$'),
    origin          CHAR(3)        NOT NULL CHECK (origin ~ '^[A-Z]{3}$'),
    destination     CHAR(3)        NOT NULL CHECK (destination ~ '^[A-Z]{3}$'),
    departure_time  TIMESTAMPTZ    NOT NULL,
    arrival_time    TIMESTAMPTZ    NOT NULL,
    total_seats     INTEGER        NOT NULL CHECK (total_seats > 0),
    available_seats INTEGER        NOT NULL,
    price           NUMERIC(12, 2) NOT NULL CHECK (price > 0),
    status          flight_status  NOT NULL DEFAULT 'SCHEDULED',
    CHECK (available_seats BETWEEN 0 AND total_seats),
    CHECK (origin <> destination),
    CHECK (arrival_time > departure_time)
);
CREATE UNIQUE INDEX flights_number_day ON flights (airline_code, flight_number, ((departure_time AT TIME ZONE 'UTC')::date));

CREATE TABLE seat_reservations (
    id         BIGSERIAL PRIMARY KEY,
    flight_id  BIGINT             NOT NULL REFERENCES flights (id),
    booking_id UUID               NOT NULL UNIQUE,
    seat_count INTEGER            NOT NULL CHECK (seat_count > 0),
    status     reservation_status NOT NULL DEFAULT 'ACTIVE'
);
