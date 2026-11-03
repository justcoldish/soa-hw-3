CREATE TYPE booking_status AS ENUM ('CONFIRMED', 'CANCELLED');

CREATE TABLE bookings (
    id              UUID           PRIMARY KEY,
    user_id         BIGINT         NOT NULL,
    flight_id       BIGINT         NOT NULL,
    passenger_name  VARCHAR(255)   NOT NULL CHECK (passenger_name <> ''),
    passenger_email VARCHAR(255)   NOT NULL CHECK (passenger_email LIKE '%_@_%'),
    seat_count      INTEGER        NOT NULL CHECK (seat_count > 0),
    total_price     NUMERIC(12, 2) NOT NULL CHECK (total_price > 0),
    status          booking_status NOT NULL DEFAULT 'CONFIRMED'
);

CREATE TABLE pending_releases (
    booking_id UUID        PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
