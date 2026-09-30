# Student Management API — Concepts & Code Walkthrough

A beginner-oriented guide covering what an API is, what FastAPI is, what a REST
API is, the HTTP methods a REST API exposes, and a line-by-line explanation of
`student_mgmt.py`.

---

## Table of contents

1. [What is an API?](#1-what-is-an-api)
2. [What is FastAPI?](#2-what-is-fastapi)
3. [What is a REST API?](#3-what-is-a-rest-api)
4. [FastAPI vs REST API — the key distinction](#4-fastapi-vs-rest-api--the-key-distinction)
5. [HTTP methods in a REST API](#5-http-methods-in-a-rest-api)
6. [Status codes you will meet in this project](#6-status-codes-you-will-meet-in-this-project)
7. [Walkthrough of `student_mgmt.py`](#7-walkthrough-of-student_mgmtpy)
8. [Running the project](#8-running-the-project)
9. [Summary](#summary)

---

## 1. What is an API?

**API** stands for **Application Programming Interface**. It is a set of rules
that lets one software program talk to another program, without needing to know
how the other one is built internally.

Think of it as a contract between two parties:

- **The client** (a mobile app, a website, another server, a Python script)
- **The server** (the program that owns the data)

The client agrees to send a request in a known format. The server agrees to
return a response in a known format. Neither side needs to understand the
other's internals — only the agreed contract.

### The student records analogy

Imagine a college keeps its student records in a locked filing room. Staff
cannot walk in and read the files directly — the records contain personal data,
and the room holds the only copy.

So the college puts a clerk at the door with a counter. Staff write a request on
a slip, hand it to the clerk, and receive back what the clerk brings out. The
clerk is the API.

| College records concept | API concept |
| --- | --- |
| The request slip | Your HTTP request |
| The clerk at the counter | The API endpoint you call |
| "Pull the file for roll number 2" | A request naming a resource, like `GET /students/2` |
| The locked filing room | Your database |
| The file the clerk hands back | The response, usually JSON |
| Roll number | A resource identifier such as `/students/2` |
| The rulebook of what can be asked for | The API documentation |

The point is the separation. Staff never enter the filing room and never learn
how the files are stored — whether they sit in cupboards, a database, or
spreadsheets. They only need to know the rulebook: what can be asked, what must
be supplied, and what comes back.

This is exactly what `student_mgmt.py` does. The `students` table is the filing
room. `get_student_by_id` is the clerk. And `HTTPException(status_code=404,
detail="Student not found")` is the clerk answering "there is no roll number 2"
— a clear, agreed answer that the caller can act on, instead of an empty file.

### A concrete request/response cycle

```http
GET /students/2 HTTP/1.1
Host: localhost:8000
```

```json
{"id": 2, "name": "Kumar", "age": 38, "city": "Singapore",
 "email": "kumar@example.com", "course": "Data Science"}
```

- **Request line** — the *method* (`GET`), the *path* (`/students/2`), the protocol.
- **Path** — identifies the *resource* (the student with id 2).
- **Response body** — JSON, because JSON is the standard interchange format for
  web APIs.

### Why bother with an API?

- **Separation of concerns** — the database layer can change without breaking clients.
- **Reuse** — a web frontend, a mobile app, and a reporting script can all use the same API.
- **Language independence** — a Python server can serve a JavaScript client.
- **Security** — clients never get direct database credentials; they only see the endpoints you expose.

---

## 2. What is FastAPI?

**FastAPI** is a Python **web framework** for building APIs. It is a tool, not
a standard. It is *how* you build; REST is *what* you build.

It gives you four main things:

### a) Automatic interactive documentation

Add routes, and FastAPI generates browsable docs at `/docs` (Swagger UI) and
`/redoc`. The docstrings and `Field(...)` constraints you write in the code are
read and turned into documentation automatically. This project gets that for
free — run the app and open `/docs`.

### b) Data validation with Pydantic

You declare the shape of the request body as a Python class:

```python
class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    age: int = Field(ge=0, le=100)
    city: str = Field(min_length=2, max_length=50)
    email: EmailStr
    course: str = Field(min_length=2, max_length=50)
```

Before your function body ever runs, FastAPI validates the incoming JSON
against this class. If a client sends `{"name": "A", "age": 999}`, validation
fails and the client gets **HTTP 422** with a precise list of what was wrong —
your function is never called. This is a large amount of manual code you do not
have to write.

Two of those five fields are worth calling out:

- `email: EmailStr` is not `str`. `EmailStr` is a Pydantic type that checks the
  address is shaped like an email, so `"not-an-email"` is rejected with 422
  before your handler runs.
- `course` carries a `@field_validator`, which runs **after** the field's own
  constraints and can rewrite the value. Here it collapses internal whitespace,
  so `"Data  Science"` is stored as `"Data Science"` and differently spaced
  spellings of one course stay one value.

### c) Type hints drive everything

The annotation in `def get_student_by_id(student_id: int)` is not decoration.
FastAPI uses it to:

- validate the path parameter (a non-integer gives 422),
- and, if you set a `response_model`, filter and coerce the response.

### d) Async support and speed

FastAPI is built on Starlette and ASGI, so it handles thousands of concurrent
requests with `async def`. It also benchmarks at or near the top of Python
frameworks. Neither feature is used in this project, but it is the main reason
people choose FastAPI over Flask or Django REST Framework.

### Other pieces used in this project

| Package | Role |
| --- | --- |
| `uvicorn` | The ASGI server that actually runs the app |
| `pydantic` | Data validation and settings |
| `sqlalchemy` | Talks to the database (engine, sessions, raw SQL) |
| `python-dotenv` | Loads `DATABASE_URL` from the `.env` file |
| `psycopg2-binary` | The PostgreSQL driver SQLAlchemy uses |

---

## 3. What is a REST API?

**REST** stands for **REpresentational State Transfer**. It is an
*architectural style* — a set of conventions for designing networked
applications.

The central idea: a REST API models the system as a collection of **resources**
(a student, an order, a user), each with a stable URL, and lets the client
manipulate those resources using a small fixed set of HTTP methods.

### The six REST constraints

1. **Client–server** — the client and server are independent. The server does
   not need to know how the client renders things.
2. **Stateless** — every request carries all the information the server needs.
   The server stores no session between requests. Each request is
   self-contained; this is what lets you scale the app horizontally.
3. **Cacheable** — a response can declare itself cacheable, so the client or a
   proxy can reuse it instead of re-requesting.
4. **Uniform interface** — every resource has the same shape of URL and the
   same small set of verbs. `GET /students/2` means the same thing no matter
   which client asks.
5. **Layered system** — the client does not know whether it is talking to one
   server or a load balancer in front of ten.
6. **Code on demand (optional)** — the server may ship JavaScript to the client
   to do work locally. This one is rarely used in practice.

### Resources and URLs

A resource is a noun, plural, addressed by a stable identifier:

```
/students          -> the collection
/students/2        -> one member of the collection
```

Resources are nouns, not verbs. `GET /getStudent?id=2` violates the uniform
interface; `GET /students/2` is correct, because the **method** already says
"get" and the **path** says *what* to get.

### REST is a style, not a protocol

There is no "REST protocol" to install. REST is a set of conventions layered
on top of HTTP. You can build a completely RESTful API in Flask, in FastAPI, in
Django, or in a raw socket library — or you can build a non-RESTful API in
FastAPI. The framework does not decide.

---

## 4. FastAPI vs REST API — the key distinction

This is the single most common confusion for beginners, so here it is plainly:

> **REST is a set of rules. FastAPI is a tool. They are not competitors — you
> use FastAPI to build a REST API.**

| | REST API | FastAPI |
| --- | --- | --- |
| **What it is** | An architectural style / convention | A Python web framework (library) |
| **Answers the question** | *How should my API be designed?* | *What do I write the code with?* |
| **Language** | Language-agnostic concept | Python only |
| **Standard/protocol?** | No — a style, not a spec you can validate against | Yes — software you install |
| **Who enforces it?** | Nobody; the team decides to follow it | FastAPI's decorators, validation, and docs |
| **Status codes** | You choose them (200, 201, 404, 409 …) | FastAPI supplies defaults but you set them explicitly |
| **Documentation** | Not provided | Generated automatically at `/docs` |
| **Validation** | Not provided | Automatic, via Pydantic |
| **Can one have the other?** | A FastAPI app may or may not follow REST | A REST API can be built with Flask, Django, Spring, Express, … |

### You can use FastAPI and *not* build a REST API

```python
# This is FastAPI, but it is NOT RESTful.
@app.get("/getStudentById")
def get_student(id: int):
    ...
```

It uses the verb `get` in the path, returns 200 for a missing student, and
returns bare status messages. FastAPI is perfectly happy. It is simply not REST.

```python
# This is a REST API, built in FastAPI.
@app.get("/students/{student_id}", response_model=StudentRead)
def get_student(student_id: int):
    ...
```

Noun-based path, a correct status code, a proper representation back.

### The everyday phrasing

- "**FastAPI**" = the tool in your hand.
- "**REST API**" = the shape your endpoints should have.
- "**a REST API built with FastAPI**" = what `student_mgmt.py` is trying to be.

---

## 5. HTTP methods in a REST API

These are the verbs. Their meaning comes from the HTTP specification, and each
one carries a distinct, standardized semantic.

| Method | Purpose | Safe | Idempotent | Has a body | Success code | Used in this project |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | Retrieve a resource | Yes | Yes | No | 200 | Yes |
| `POST` | Create a subordinate resource | No | No | Yes | 201 | Yes |
| `PUT` | Replace a resource entirely | No | Yes | Yes | 200 / 204 | Yes |
| `PATCH` | Partially modify a resource | No | Not guaranteed | Yes | 200 / 204 | Yes |
| `DELETE` | Remove a resource | No | Yes | Optional | 204 | Yes |
| `HEAD` | Same as GET but headers only | Yes | Yes | No | 200 | Automatic |
| `OPTIONS` | Ask which methods are allowed | Yes | Yes | No | 204 | Automatic |

Two words that cause endless confusion, so let's be precise:

- **Safe** = the method does not *change server state*. GET is safe. `GET
  /students/2` five times leaves the database identical.
- **Idempotent** = repeating the request has the *same effect as doing it once*.
  This is not the same as safe. `DELETE /students/2` repeated ten times still
  leaves the student deleted, so DELETE is idempotent even though it certainly
  changes state.

### 5.1 `GET` — read a resource

**Significance.** Retrieve a representation of a resource. Safe and idempotent:
it must never modify anything. Because it is safe, browsers and proxies are
allowed to cache GET responses and even prefetch them.

**Use cases.** Load a profile page, search a catalogue, fetch a report, poll
for status, populate a dropdown.

**Example from this project.**

```python
@app.get("/students")
def get_students_data():
    with SessionLocal() as session:
        result = session.execute(text("SELECT * from students order by id"))
        students = [dict(row) for row in result.mappings()]
        return students
```

**Response**

```json
[
  {"id": 1, "name": "Kumar", "age": 38, "city": "Singapore",
   "email": "kumar@example.com", "course": "Data Science"},
  {"id": 2, "name": "Venkat", "age": 34, "city": "India",
   "email": "venkat@example.com", "course": "Machine Learning"}
]
```

**Gotcha.** A GET that changes data breaks the safe guarantee and can be
triggered by crawlers and prefetchers. If a "GET" deletes something, it is
really a DELETE.

---

### 5.2 `POST` — create a subordinate resource

**Significance.** Ask the server to create a new resource as a child of
whatever the parent URL identifies. Not safe, and **not idempotent**: posting
the same body twice creates two students, because "create a new one" is a
fresh action every time.

**Use cases.** Sign-up, placing an order, uploading a file, submitting a form,
sending a message.

**Example from this project.**

```python
@app.post("/students", status_code=201)
def create_student(student: StudentCreate):
    with SessionLocal() as session:
        session.execute(
            text(
                "INSERT INTO students (name, age, city, email, course) "
                "VALUES (:name, :age, :city, :email, :course)"
            ),
            {
                "name": student.name,
                "age": student.age,
                "city": student.city,
                "email": str(student.email),
                "course": student.course,
            },
        )
        session.commit()
    return {"message": "Student created successfully"}
```

**Request**

```json
{"name": "Sravan", "age": 21, "city": "Hyderabad",
 "email": "sravan@example.com", "course": "Data Science"}
```

Note the two details that make this RESTful: the path is `POST /students` with
**no id** (the id is the database's to assign, not the client's), and the
decorator declares `status_code=201` so a successful create answers **201
Created** rather than the 200 default.

`str(student.email)` looks redundant but is not: `EmailStr` is a Pydantic
subclass of `str`, and casting it to a plain `str` is what makes it a value the
database driver accepts.

---

### 5.3 `PUT` — replace a resource

**Significance.** Replace the current representation of a resource with a new
one. The client sends the *complete* new state. The server replaces the whole
resource with what was sent.

- **Not safe** — it changes data.
- **Idempotent** — sending the same PUT ten times leaves the same end state.
  Unlike POST, there is no "two copies" problem.

The two rules people get wrong:

1. The id in the URL identifies *which* resource; the id in the body (if any)
   must match it.
2. Fields you omit are **set to empty/null** — not left alone. That is what
   makes it a *replace*. If you want to change one field and keep the rest,
   that is PATCH.

**Use cases.** Replacing a whole profile/settings blob, setting a resource to a
known complete state, idempotent bulk operations.

**Example from this project.**

```python
@app.put("/students/{student_id}")
def update_student(student_id: int, student: StudentCreate):
    try:
        with SessionLocal() as session:
            try:
                result = session.execute(
                    text(
                        "UPDATE students SET name = :name, age = :age, city = :city, "
                        "email = :email, course = :course WHERE id = :id"
                    ),
                    {
                        "name": student.name,
                        "age": student.age,
                        "city": student.city,
                        "email": str(student.email),
                        "course": student.course,
                        "id": student_id,
                    },
                )
                updated = result.rowcount
                if updated:
                    session.commit()
            except IntegrityError:
                session.rollback()
                raise HTTPException(status_code=409, detail=DUPLICATE_EMAIL_DETAIL)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating student: {e}")

    if not updated:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"message": "Student updated successfully"}
```

All five fields are always written, so this is a true full replace.

The `updated = result.rowcount` line is the one that makes 404 work: `UPDATE` on
an id that does not exist matches **zero** rows without raising anything, so
without the check the handler would report success for a student it never
touched. Two further details are load-bearing and easy to drop: the commit is
inside `if updated`, and the 404 is raised **after** the `try` block so the
broad `except Exception` cannot convert it to a 500.

---

### 5.4 `PATCH` — partially modify a resource

**Significance.** Apply a *partial* modification. The client sends only the
fields it wants to change; everything not mentioned stays as it was.

- **Not safe.**
- **Idempotency is not guaranteed** by the spec, and in practice it depends on
  the operation. `{"age": 22}` applied twice gives the same result (idempotent);
  `{"city": "next city"}` applied twice does not. Do not rely on it.

**Use cases.** Toggling a single field, editing one property in a UI, changing
a password, marking something as read.

**Example from this project.**

```python
class studentpatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=50)
    age: int | None = Field(default=None, ge=0, le=100)
    city: str | None = Field(default=None, min_length=2, max_length=50)
    email: EmailStr | None = None
    course: str | None = Field(default=None, min_length=2, max_length=50)

@app.patch("/students/{student_id}")
def patch_student(student_id: int, student: studentpatch):
    update_data = {k: v for k, v in student.dict().items() if v is not None}
    if "email" in update_data:
        update_data["email"] = str(update_data["email"])
    if update_data:
        set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
        update_data["id"] = student_id
        session.execute(
            text(f"UPDATE students SET {set_clause} WHERE id = :id"),
            update_data
        )
        session.commit()
```

**Request** — only `city` is sent

```json
{"city": "Bengaluru"}
```

**What happens, step by step:**

1. `name`, `age`, `email` and `course` are `None`, so the dict comprehension
   drops them.
2. `update_data == {"city": "Bengaluru"}`.
3. `set_clause == "city = :city"`.
4. The SQL becomes `UPDATE students SET city = :city WHERE id = :id`.
5. The other four columns in the database are untouched.

Note that the SQL string is built by interpolating **column names** from the
model's own keys, while the **values** stay as bound parameters. That split is
why this is still safe: the keys come from the Pydantic model, never from the
request body, so a client cannot invent a column to write to.

This is why the code has a **separate PATCH endpoint** and a **separate
`studentpatch` model** instead of reusing `StudentCreate`: PUT's model requires
all fields, PATCH's makes them all optional.

---

### 5.5 `DELETE` — remove a resource

**Significance.** Ask the server to delete the resource. Not safe, but
**idempotent** — deleting an already-deleted resource leaves the same state.

**Use cases.** Removing an account, cancelling an order, deleting a file.

**Example from this project.**

```python
@app.delete("/students/{student_id}", status_code=204)
def delete_student(student_id: int):
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
```

Two conventions are in play here:

- `status_code=204` on the decorator makes a successful delete answer **204 No
  Content**, which by definition carries **no body**. That is why the handler
  returns nothing at all — returning a `{"message": ...}` dict would contradict
  the status code it just declared.
- Deleting an id that does not exist is a **404**, decided by `rowcount`, for
  the same reason as PUT: a `DELETE` matching zero rows raises nothing on its
  own.

The `except Exception` wrapper is not shown here, but note where the 404 is
raised — **after** the `try` block. That placement is what stops the broad
handler from catching its own deliberate 404 and re-reporting it as a 500. See
[7.11](#711-error-handling).

---

### 5.6 `HEAD` — headers only

Identical to GET but the server sends **no body**. Used to check whether a
resource exists, or to read its size and caching metadata, without paying for
the payload. FastAPI registers it for you on every GET route.

### 5.7 `OPTIONS` — what can I do here?

Asks which methods the server allows on a resource. FastAPI answers it
automatically, and it is what makes CORS preflight requests work. In the
OpenAPI docs you will see `OPTIONS` listed for every path.

---

### Quick comparison table

| Question | GET | POST | PUT | PATCH | DELETE |
| --- | --- | --- | --- | --- | --- |
| Creates a new resource? | No | **Yes** | No | No | No |
| Modifies existing? | No | Sometimes | **Yes** | **Yes** | No |
| Deletes? | No | No | No | No | **Yes** |
| Safe (no state change)? | **Yes** | No | No | No | No |
| Idempotent? | **Yes** | No | **Yes** | No* | **Yes** |
| Sends a request body? | Rarely | **Yes** | **Yes** | **Yes** | Optional |
| Correct success code | 200 | **201** | 200/204 | 200/204 | 204 |
| Typical URL | `/students` | `/students` | `/students/2` | `/students/2` | `/students/2` |

\* Not guaranteed; depends on the operation.

---

## 6. Status codes you will meet in this project

| Code | Meaning | When to use |
| --- | --- | --- |
| **200 OK** | Request succeeded | GET, and successful PUT/PATCH |
| **201 Created** | Resource created | POST — return this, not 200 |
| **204 No Content** | Succeeded, empty body | DELETE, or a write with nothing to say |
| **400 Bad Request** | Malformed request | Only when the request is syntactically broken |
| **404 Not Found** | No such resource | Student id does not exist |
| **409 Conflict** | Conflicts with current state | Duplicate email, version mismatch |
| **422 Unprocessable Entity** | Validation failed | Pydantic rejected the body — FastAPI's default for bad input |
| **500 Internal Server Error** | Server bug | An unhandled exception |

`422` is FastAPI's own choice and is worth internalising: a Pydantic
`HTTPException`-free validation failure returns 422 *before* your code runs.

### What this project actually returns

| Request | Status |
| --- | --- |
| `GET /students` — ok / query fails | 200 / 500 |
| `GET /students/{id}` — exists / missing | 200 / 404 |
| `POST /students` — valid / bad body / duplicate email | 201 / 422 / 409 |
| `PUT /students/{id}` — exists / missing / duplicate email | 200 / 404 / 409 |
| `PATCH /students/{id}` — valid / bad body / duplicate email | 200 / 422 / 409 |
| `DELETE /students/{id}` — exists / missing | 204 / 404 |

One gap worth naming: `PATCH` is the only write route here that does not check
whether the student exists, so patching an unknown id still returns 200. It is
listed correctly in the table above as what the code does, not as what it should
do.

---

## 7. Walkthrough of `student_mgmt.py`

### 7.1 The module docstring (lines 1–23)

Documents what the module is, the full route table, the storage, and how to run
it. This is the first thing a new teammate reads.

### 7.2 Setup and configuration (lines 34–46)

```python
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
DUPLICATE_EMAIL_DETAIL = "Email already registered"
```

- `load_dotenv()` reads the `.env` file and puts the variables into the
  environment. This is how the database password stays out of the source code.
- `create_engine(DATABASE_URL)` creates the **engine** — the object that knows
  how to talk to PostgreSQL and manages a connection pool.
- `sessionmaker(...)` creates `SessionLocal`, a **factory**. Calling
  `SessionLocal()` gives a session. One session is a unit of work: a few queries
  plus one commit, then close it.
- `autocommit=False` is the important one. Changes are staged and only written
  when you call `session.commit()`. This is how you get transactions.
- `Base = declarative_base()` defines where ORM models would be registered.
  **No model is mapped to it in this file** — the routes use raw SQL.
- `DUPLICATE_EMAIL_DETAIL` is a fixed message returned for any unique-constraint
  violation. The driver's own text names the index and the failing SQL, which is
  noise for a client, so the detail stays constant instead of interpolating the
  original error.

### 7.3 The connection check (lines 49–71)

```python
def check_database_connection():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Database connection successful")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
    return True

check_database_connection()
```

`SELECT 1` is the cheapest possible query — it proves the credentials and the
network path work. Crucially, this is called **at import time**, not inside a
request. If the database is unreachable, you find out when the server starts,
rather than when a user gets a 500.

### 7.4 Creating the app (line 73)

```python
app = FastAPI(title="API Marketplace", description="Market place for API", version="1.0.0")
```

`title`, `description` and `version` are metadata that FastAPI shows on the
generated `/docs` page. The `app` object is the registry that every decorator
below attaches a route to.

### 7.5 The route decorators — how routing works

```python
@app.get("/students/{student_id}")
def get_student_by_id(student_id: int):
```

Read this as three parts:

1. `@app.get(...)` — **register** a GET handler for this path. It returns the
   original function unchanged, so you can still call it directly in Python.
2. `"/students/{student_id}"` — the **path template**. The literal text
   `/students/` followed by a parameter captured into the variable
   `student_id`.
3. `student_id: int` — because it is annotated `int`, FastAPI coerces and
   validates the value from the URL before calling the function.

Because the literal part comes first, FastAPI can reliably distinguish
`/Test API` from `/students/2`. Route order still matters if two templates
could both match.

You can also declare the success status directly on the decorator, which two
routes do:

```python
@app.post("/students", status_code=201)
@app.delete("/students/{student_id}", status_code=204)
```

`status_code` sets the status FastAPI sends on **success**. It does not affect
error responses — raising `HTTPException(404)` still returns 404 even on the
route declared as 204, because the exception handler builds that response
separately.

### 7.6 The session lifecycle

Every handler that touches the database uses this same shape:

```python
with SessionLocal() as session:
    result = session.execute(text("SELECT ..."), {"id": student_id})
    ...
    session.commit()
```

- `SessionLocal()` opens a session (a connection is checked out of the pool).
- `with` guarantees the session is **closed and the connection returned to the
  pool** even if the code raises — that is why a burst of requests does not
  exhaust the pool.
- `session.execute(text("..."), {...})` runs raw SQL. The values go in as a
  separate dict and SQLAlchemy sends them as **bound parameters**, so the
  database never sees them as part of the SQL string. This is what makes the
  query safe from SQL injection:
  ```python
  text("SELECT * FROM students WHERE id = :id"), {"id": student_id}
  ```
  `:id` is a placeholder, not string formatting.
- `session.commit()` writes the transaction. Without it, closing the session
  rolls the changes back and nothing is saved.

### 7.7 Reading rows into JSON

```python
result = session.execute(text("SELECT * from students order by id"))
students = [dict(row) for row in result.mappings()]
```

- `execute()` returns a `Result` object, **not** a list of rows. You must ask
  for what you want.
- `.mappings()` wraps each row so you can read it by column name (`row["name"]`).
- `dict(row)` converts each to a plain Python dict.
- FastAPI serialises a list of dicts straight to a JSON array.

`order by id` is not cosmetic: **SQL has no guaranteed row order** without it,
and without a stable order, pagination is unreliable.

### 7.8 Finding exactly one row

```python
student = result.mappings().first()
if not student:
    raise HTTPException(status_code=404, detail="Student not found")
```

`.first()` returns the first row **or `None`**. The `if not student` guard turns
"no result" into a proper 404. This is the standard FastAPI idiom for a
not-found response.

**Where that guard sits is the whole trick.** It has to be *after* the `try` /
`except` pair, not inside the `try`:

```python
try:
    with SessionLocal() as session:
        student = session.execute(...).mappings().first()
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error fetching student data: {e}")

if not student:                                     # outside the try
    raise HTTPException(status_code=404, detail="Student not found")
```

Inside the `try`, the `except Exception` catches the 404 the guard just raised
and re-reports it as a 500 — the client gets
`500 "Error fetching student data: 404: Student not found"` for a student that
simply does not exist. See [7.11](#711-error-handling).

### 7.9 Input validation (lines 160–193)

```python
class StudentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    age: int = Field(ge=0, le=100)
    city: str = Field(min_length=2, max_length=50)
    email: EmailStr
    course: str = Field(min_length=2, max_length=50)

    @field_validator("course")
    @classmethod
    def normalise_course(cls, v: str) -> str:
        return " ".join(v.split())
```

```python
@app.post("/students", status_code=201)
def create_student(student: StudentCreate):
```

Because the parameter is annotated with a Pydantic model, FastAPI:

1. parses the request body as JSON,
2. validates it against `StudentCreate`,
3. rejects it with **422** if anything is wrong, without calling your function,
4. otherwise passes a `StudentCreate` instance, so you use `student.name`
   rather than digging through a raw dict.

The `Field` constraints are the rules: `ge=0, le=100` means "greater than or
equal to 0, less than or equal to 100" — exactly the kind of rule that would
otherwise be a hand-written `if` in every handler.

### 7.10 The PUT vs PATCH decision, again in the code

`update_student` (line 244) takes `StudentCreate` — every field required, all
five always written. `patch_student` (line 324) takes `studentpatch` — every
field `Optional` with `default=None`, and it filters out the `None` values
before building SQL. That single difference in the model type is the entire
difference between the two HTTP verbs in this program.

### 7.11 Error handling

```python
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error updating student: {e}")
```

`HTTPException` is how you tell FastAPI "return this status code with this
message". It is the correct tool for a 404 or a 409.

However, `except Exception` is a **very** broad net — and `HTTPException` is an
`Exception`, so the handler catches the 404 you raised on purpose and reports it
as a 500. Two ways out, both used in this file:

1. **Raise deliberate status codes outside the `try`.** The 404 in
   `get_student_by_id`, `update_student` and `delete_student` all sit after the
   `except`, so the broad net never sees them.
2. **Re-raise `HTTPException` untouched.** Where the check has to happen inside
   the `try` — the 409s — the handler catches it separately and passes it on:

   ```python
   try:
       with SessionLocal() as session:
           try:
               session.execute(...)
               session.commit()
           except IntegrityError:
               session.rollback()
               raise HTTPException(status_code=409, detail=DUPLICATE_EMAIL_DETAIL)
   except HTTPException:
       raise                       # let the 409 through unchanged
   except Exception as e:
       raise HTTPException(status_code=500, detail=f"Error creating student: {e}")
   ```

   The outer `except HTTPException: raise` is the part that matters. Without it
   the outer `except Exception` would still turn that careful 409 into a 500.

Two habits make this reliable: keep `except` clauses **narrowest first** (the
specific `IntegrityError` or `HTTPException` before the general `Exception`),
and **always `session.rollback()`** before raising, so the failed transaction
does not stay open.

---

## 8. Running the project

```bash
# 1. install dependencies
pip install -r requirements.txt

# 2. make sure .env contains DATABASE_URL, e.g.
#    DATABASE_URL=postgresql://user:password@host:5432/dbname

# 3. make sure the students table has the columns the code writes
#    (see "The students table" below)

# 4. start the server
uvicorn student_mgmt:app --reload
```

### The students table

The code writes six columns, so the table needs all six:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | `integer` | Primary key, serial |
| `name` | `varchar` | |
| `age` | `integer` | |
| `city` | `varchar` | |
| `email` | `varchar(255)` | **Unique**, nullable |
| `course` | `varchar(100)` | Nullable |

If you are starting from a table that only has the first four, add the rest:

```sql
ALTER TABLE students ADD COLUMN email VARCHAR(255);
ALTER TABLE students ADD COLUMN course VARCHAR(100);
CREATE UNIQUE INDEX students_email_key ON students (email) WHERE email IS NOT NULL;
```

Both columns are nullable, so existing rows survive and read back with `null`
for the two new fields. The index is **partial** (`WHERE email IS NOT NULL`)
because in SQL a `UNIQUE` constraint treats every `NULL` as distinct, so the
existing null rows would not collide anyway — the partial form just states the
intent instead of relying on that.

You do not need to run this by hand if the table is already set up; it is
documented here so the schema the code assumes is written down somewhere.

### Then open the docs

- **<http://127.0.0.1:8000/docs>** — interactive Swagger UI, generated from the
  docstrings and `Field` constraints in the code
- <http://127.0.0.1:8000/redoc> — ReDoc rendering
- <http://127.0.0.1:8000/Test%20API> — a static greeting, useful as a
  smoke test that the server is up at all

### Try it with curl

```bash
# list all students
curl http://127.0.0.1:8000/students

# fetch one  -> 200, or 404 if no such id
curl http://127.0.0.1:8000/students/2

# create  -> 201, or 422 on a bad body, 409 if the email is taken
curl -X POST http://127.0.0.1:8000/students \
     -H "Content-Type: application/json" \
     -d '{"name": "Sravan", "age": 21, "city": "Hyderabad",
          "email": "sravan@example.com", "course": "Data Science"}'

# partial update — only city changes
curl -X PATCH http://127.0.0.1:8000/students/2 \
     -H "Content-Type: application/json" \
     -d '{"city": "Bengaluru"}'

# full replace — all five fields required
curl -X PUT http://127.0.0.1:8000/students/2 \
     -H "Content-Type: application/json" \
     -d '{"name": "Kumar", "age": 39, "city": "Singapore",
          "email": "kumar@example.com", "course": "Machine Learning"}'

# delete  -> 204 with no body, or 404 if already gone
curl -X DELETE http://127.0.0.1:8000/students/2
```

### Project layout

```
student_management_api/
├── student_mgmt.py    # the whole application
├── requirements.txt   # dependencies
├── .env               # DATABASE_URL (keep this out of version control)
└── README.md          # this file
```

---
## Summary

- An **API** is a contract between two programs; a **REST API** is a specific,
  opinionated style for designing that contract around resources.
- **REST** tells you *how to design* (nouns for URLs, fixed verbs, correct status
  codes, statelessness). **FastAPI** is the *tool* that builds it, adding
  validation, dependency injection, and free interactive documentation.
- The **methods** differ in what they promise: `GET` is safe and idempotent,
  `POST` creates and is not idempotent, `PUT` replaces, `PATCH` modifies part,
  `DELETE` removes. Choosing the wrong one breaks caching, retry logic, or
  correctness.
- `student_mgmt.py` follows that structure — `GET` to read, `POST` to create,
  `PUT` to replace, `PATCH` to modify in place, `DELETE` to remove — and relies
  on Pydantic to validate input and on SQLAlchemy sessions to talk to
  PostgreSQL safely with parameterised SQL.
- **Status codes are part of the contract, not decoration.** `201` on create,
  `204` on delete, `404` for a student that does not exist, `409` for a
  duplicate email, `422` for a bad body. Most of that comes from two details
  that are easy to miss: a write that matched zero rows has to check `rowcount`
  to notice, and a deliberate `HTTPException` has to be raised outside the broad
  `except Exception` that would otherwise turn it into a 500.

Happy learning. The fastest way to internalise all of this is to keep the app
running, hit every endpoint in `/docs`, and change one thing at a time.
