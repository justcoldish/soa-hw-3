import logging
import os
import threading
import time
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import grpc
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.protobuf.json_format import MessageToDict
from psycopg import Connection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, Field

import flight_pb2 as pb
from flight_client import RETRYABLE, flight

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger()
db = ConnectionPool(os.environ["DATABASE_URL"], connection_class=Connection[DictRow], kwargs={"row_factory": dict_row}, open=True)
app = FastAPI(title="Booking Service")
HTTP_CODES = {grpc.StatusCode.INVALID_ARGUMENT: 400, grpc.StatusCode.NOT_FOUND: 404,
              grpc.StatusCode.FAILED_PRECONDITION: 409, grpc.StatusCode.RESOURCE_EXHAUSTED: 409,
              grpc.StatusCode.UNAVAILABLE: 503, grpc.StatusCode.DEADLINE_EXCEEDED: 503}


class Flight(BaseModel):
    id: int
    flight_number: str
    airline: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    total_seats: int
    available_seats: int
    price: Decimal
    status: str


class BookingIn(BaseModel):
    user_id: int = Field(gt=0)
    flight_id: int = Field(gt=0)
    passenger_name: str = Field(min_length=1)
    passenger_email: str = Field(pattern=".@.")
    seat_count: int = Field(gt=0)


class Booking(BookingIn):
    id: UUID
    total_price: Decimal
    status: str


@app.exception_handler(grpc.RpcError)
async def grpc_error(_, e):
    return JSONResponse({"detail": e.details()}, HTTP_CODES.get(e.code(), 500))


def to_dict(message):
    return MessageToDict(message, preserving_proto_field_name=True, always_print_fields_with_no_presence=True)


@app.get("/flights", response_model=list[Flight])
def search_flights(origin: str, destination: str, date: date | None = None):
    req = pb.SearchFlightsRequest(origin=origin, destination=destination)
    if date:
        req.date.FromDatetime(datetime.combine(date, datetime.min.time()))
    return to_dict(flight.SearchFlights(req))["flights"]


@app.get("/flights/{flight_id}", response_model=Flight)
def get_flight(flight_id: int):
    return to_dict(flight.GetFlight(pb.GetFlightRequest(id=flight_id)))


@app.post("/bookings", status_code=201, response_model=Booking)
def create_booking(b: BookingIn):
    f = flight.GetFlight(pb.GetFlightRequest(id=b.flight_id))
    booking_id = str(uuid4())
    # резерв мог пройти даже при ошибке вызова: если бронь не запишется, места вернет reconcile
    with db.connection() as conn:
        conn.execute("INSERT INTO pending_releases (booking_id) VALUES (%s)", [booking_id])
    try:
        flight.ReserveSeats(pb.ReserveSeatsRequest(flight_id=b.flight_id, seat_count=b.seat_count, booking_id=booking_id))
    except grpc.RpcError as e:
        # точный отказ flight: резерва нет, возвращать нечего
        if e.code() not in RETRYABLE:
            with db.connection() as conn:
                conn.execute("DELETE FROM pending_releases WHERE booking_id = %s", [booking_id])
        raise
    try:
        with db.connection() as conn:
            if not conn.execute("DELETE FROM pending_releases WHERE booking_id = %s", [booking_id]).rowcount:
                raise HTTPException(409, "reservation already released")
            return conn.execute("""INSERT INTO bookings
                (id, user_id, flight_id, passenger_name, passenger_email, seat_count, total_price)
                VALUES (%(id)s, %(user_id)s, %(flight_id)s, %(passenger_name)s, %(passenger_email)s, %(seat_count)s,
                %(total_price)s) RETURNING *""",
                                b.model_dump() | {"id": booking_id, "total_price": b.seat_count * Decimal(f.price)}).fetchone()
    except Exception:
        release(booking_id)
        raise


@app.get("/bookings/{booking_id}", response_model=Booking)
def get_booking(booking_id: UUID):
    with db.connection() as conn:
        if b := conn.execute("SELECT * FROM bookings WHERE id = %s", [booking_id]).fetchone():
            return b
    raise HTTPException(404, "booking not found")


@app.get("/bookings", response_model=list[Booking])
def list_bookings(user_id: int):
    with db.connection() as conn:
        return conn.execute("SELECT * FROM bookings WHERE user_id = %s", [user_id]).fetchall()


@app.post("/bookings/{booking_id}/cancel", response_model=Booking)
def cancel_booking(booking_id: UUID):
    with db.connection() as conn:
        b = conn.execute("SELECT * FROM bookings WHERE id = %s FOR UPDATE", [booking_id]).fetchone()
        if b is None:
            raise HTTPException(404, "booking not found")
        if b["status"] != "CONFIRMED":
            raise HTTPException(409, f"booking is already {b['status']}")
        b = conn.execute("UPDATE bookings SET status = 'CANCELLED' WHERE id = %s RETURNING *", [booking_id]).fetchone()
        conn.execute("INSERT INTO pending_releases (booking_id) VALUES (%s)", [booking_id])
    release(booking_id)
    return b


# строка pending_releases заблокирована до конца вызова, поэтому бронь не запишется, пока ее места возвращаются
def release(booking_id):
    with db.connection() as conn:
        if not conn.execute("DELETE FROM pending_releases WHERE booking_id = %s", [booking_id]).rowcount:
            return
        try:
            flight.ReleaseReservation(pb.ReleaseReservationRequest(booking_id=str(booking_id)))
            code = grpc.StatusCode.OK
        except grpc.RpcError as e:
            code = e.code()
        log.info("release seats of booking %s: %s", booking_id, code.name)
        # NOT_FOUND: резерва нет или он уже снят
        if code not in (grpc.StatusCode.OK, grpc.StatusCode.NOT_FOUND):
            conn.rollback()


def reconcile():
    while True:
        time.sleep(10)
        # записи старше минуты: бронь, которая их ждала, уже закончилась
        with db.connection() as conn:
            rows = conn.execute("SELECT booking_id FROM pending_releases WHERE created_at < now() - interval '1 minute'").fetchall()
        for row in rows:
            release(row["booking_id"])


threading.Thread(target=reconcile, daemon=True).start()
uvicorn.run(app, host="0.0.0.0", port=8000)
