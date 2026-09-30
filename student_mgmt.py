"""Student management API served by FastAPI and backed by PostgreSQL.

This module is a self-contained application: it builds the SQLAlchemy engine
and session factory, verifies connectivity at import time, and then registers
the student routes directly on the ``app`` instance.

Routes exposed by this module:

    GET    /Test API          - static greeting, for smoke-testing the app.
    GET    /students          - list every row of the ``students`` table.
    GET    /students/{id}     - fetch one student by primary key.
    POST   /students          - insert a student.
    PUT    /students/{id}     - replace a student's details by primary key.
    PATCH  /students/{id}     - update only the supplied fields.
    DELETE /students/{id}     - delete a student by primary key.

Storage is the pre-existing ``students`` table (id, name, age, city) in the
database named by ``DATABASE_URL`` in the .env file. Queries are written as
raw parameterised SQL via ``text()`` rather than through the ORM.

Run with: uvicorn student_mgmt:app --reload
"""

import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Reads DATABASE_URL (and any other keys) from the .env file next to this module.
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declared for future use: the routes below query with raw SQL, so no ORM model
# is currently mapped onto it.
Base = declarative_base()


def check_database_connection():
    """Check that the configured database is reachable.

    Executes a trivial ``SELECT 1`` against the engine so connection problems
    surface at startup instead of on the first request.

    Returns:
        bool: True if the database responded, False if the attempt raised.
    """

    try:
        # Open a pooled connection just long enough to prove the credentials
        # and network path work; the connection is returned to the pool after.
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    return True


check_database_connection()

app = FastAPI(title="API Marketplace", description="Market place for API", version="1.0.0")


@app.get("/Test API")
def test_api():
    """Return a static greeting.

    Intended as a trivial endpoint for confirming the server is up.
    """

    return "Welcome to API Market"


@app.get("/students")
def get_students_data():
    """Return every row of the ``students`` table.

    ``.mappings()`` turns each row into a plain dict keyed by column name, which
    FastAPI serialises directly to JSON. Row order is not guaranteed by the
    query, so callers must not depend on it.

    Returns:
        list[dict]: One dict per student, each holding id, name, age and city.

    Note:
        The ``except`` below catches query failures as well as connection
        failures, so its "Database connection failed" message is misleading for
        a malformed or missing table. It also returns None in that case, which
        FastAPI serialises as a null body.
    """

    try:
        with SessionLocal() as session:
            result = session.execute(text("SELECT * from students order by id"))
            students = [dict(row) for row in result.mappings()]
            return students
    except Exception as e:
        print(f"Database connection failed: {e}")


# Warm the query path at import time so a broken table is noticed on startup.
# The result is discarded.
get_students_data()


@app.get("/students/{student_id}")
def get_student_by_id(student_id: int):
    """Fetch a single student by primary key.

    Args:
        student_id: Primary key of the student to look up.

    Returns:
        dict: The matching row as a dict of column names to values.

    Raises:
        HTTPException: 404 if no student has that id, or 500 if the lookup fails.
    """

    try:
        with SessionLocal() as session:
            result = session.execute(
                text("SELECT * FROM students WHERE id = :id"), {"id": student_id}
            )
            student = result.mappings().first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching student data: {e}")

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# --- Request payloads ---------------------------------------------------------
# Imported here rather than at the top of the file to keep the original layout.

from pydantic import (  # noqa: E402
    BaseModel,
    EmailStr,
    Field,
    HttpUrl,
    field_validator,
)


class StudentCreate(BaseModel):
    """Payload for creating or fully replacing a student.

    Attributes:
        name: Student name, 2-50 characters.
        age: Student age, 0-100 inclusive.
        city: City of residence, 2-50 characters.

    Note:
        ``EmailStr``, ``HttpUrl`` and ``field_validator`` are imported for
        validation helpers that are not used by this model yet.
    """

    name: str = Field(min_length=2, max_length=50)
    age: int = Field(ge=0, le=100)
    city: str = Field(min_length=2, max_length=50)


@app.post("/students", status_code=201)
def create_student(student: StudentCreate):
    """Insert a new student.

    The ``id`` column is left to its sequence default, so rows are numbered by
    the database. The route is POST on /students, so there is no id in the path.

    Args:
        student: Validated name, age and city of the student to add.

    Returns:
        dict: A success message, sent with status 201 Created as declared on
            the route decorator. The generated id is absent from the response,
            so a client cannot learn which row it just created without a
            follow-up GET.

    Raises:
        HTTPException: 500 if the insert fails, e.g. on a constraint violation.
    """

    try:
        with SessionLocal() as session:
            session.execute(
                text("INSERT INTO students (name, age, city) VALUES (:name, :age, :city)"),
                {"name": student.name, "age": student.age, "city": student.city},
            )
            session.commit()
        return {"message": "Student created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating student: {e}")


@app.put("/students/{student_id}")
def update_student(student_id: int, student: StudentCreate):
    """Replace all supplied fields of a student.

    Args:
        student_id: Primary key of the student to update.
        student: The new name, age and city. All three are always written, so
            this is a full replace rather than a partial update.

    Returns:
        dict: A success message, sent with status 200 as declared on the route
            decorator. Only returned when a row was actually updated.

    Raises:
        HTTPException: 404 if no student has that id, or 500 if the update
            fails.
    """

    try:
        with SessionLocal() as session:
            result = session.execute(
                text("UPDATE students SET name = :name, age = :age, city = :city WHERE id = :id"),
                {"name": student.name, "age": student.age, "city": student.city, "id": student_id},
            )
            updated = result.rowcount
            if updated:
                session.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating student: {e}")

    if not updated:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student updated successfully"}


class studentpatch(BaseModel):
    """Payload for a partial update: every field is optional.

    Attributes:
        name: New name, or None to leave the stored value untouched.
        age: New age, or None to leave the stored value untouched.
        city: New city, or None to leave the stored value untouched.
    """

    name: str | None = Field(default=None, min_length=2, max_length=50)
    age: int | None = Field(default=None, ge=0, le=100)
    city: str | None = Field(default=None, min_length=2, max_length=50)


@app.patch("/students/{student_id}")
def patch_student(student_id: int, student: studentpatch):
    """Update only the fields that were actually supplied.

    Fields left as None are filtered out, and the SQL SET clause is built from
    the remaining keys, so omitted fields keep their stored values. When every
    field is None the update is skipped entirely and the stored row is left
    untouched.

    Args:
        student_id: Primary key of the student to update.
        student: Any subset of name, age and city.

    Returns:
        dict: A success message. The updated row is not read back, so the
            response does not show the new values.

    Raises:
        HTTPException: 500 if the update fails.
    """

    try:
        with SessionLocal() as session:
            update_data = {k: v for k, v in student.dict().items() if v is not None}
            if update_data:
                set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
                update_data["id"] = student_id
                session.execute(
                    text(f"UPDATE students SET {set_clause} WHERE id = :id"),
                    update_data
                )
                session.commit()
        return {"message": "Student patched successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error patching student: {e}")


@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int):
    """Delete a student by primary key.

    Args:
        student_id: Primary key of the student to remove.

    Returns:
        None: A 204 No Content response, which carries no body, so there is no
            message to report. Returned only when a row was actually deleted.

    Raises:
        HTTPException: 404 if no student has that id, or 500 if the delete
            fails.
    """

    try:
        with SessionLocal() as session:
            result = session.execute(
                text("DELETE FROM students WHERE id = :id"),
                {"id": student_id},
            )
            deleted = result.rowcount
            if deleted:
                session.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting student: {e}")

    if not deleted:
        raise HTTPException(status_code=404, detail="Student not found")
