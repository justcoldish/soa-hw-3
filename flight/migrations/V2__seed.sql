INSERT INTO airlines (code, name) VALUES ('SU', 'Aeroflot'), ('DP', 'Pobeda');

INSERT INTO flights (airline_code, flight_number, origin, destination, departure_time, arrival_time, total_seats, available_seats, price, status) VALUES
    ('SU', '1234', 'SVO', 'LED', '2026-12-01 08:00+03', '2026-12-01 09:30+03', 150, 150, 4500.00, 'SCHEDULED'),
    ('SU', '1236', 'SVO', 'LED', '2026-12-01 18:00+03', '2026-12-01 19:30+03', 150, 150, 5200.00, 'SCHEDULED'),
    ('SU', '1234', 'SVO', 'LED', '2026-12-02 08:00+03', '2026-12-02 09:30+03', 150, 150, 4500.00, 'SCHEDULED'),
    ('SU', '1238', 'SVO', 'LED', '2026-12-01 12:00+03', '2026-12-01 13:30+03', 150, 150, 4800.00, 'CANCELLED'),
    ('DP', '401',  'VKO', 'LED', '2026-12-01 10:00+03', '2026-12-01 11:30+03', 180,   1, 2999.00, 'SCHEDULED');
