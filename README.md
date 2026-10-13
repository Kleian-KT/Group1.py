# Campus Facility Reservation Management System

A production-grade, secure, and fully functional **Campus Facility Reservation Management System** built with Python, Django, Bootstrap 5, and Chart.js. Designed for academic engineering standards with strict relational integrity, atomic concurrency protections, role-based authorization, and an end-to-end custom administrative operations console.

---

## 1. Project Purpose & User Roles

This system facilitates discovery, availability verification, booking submission, administrative review, operational execution, and reporting for campus facilities.

The system enforces **exactly two application-level roles**:

| Role | Permitted Actions |
| :--- | :--- |
| **BASIC USER** | Browse active facilities, inspect calculated time-slot availability, submit reservation requests, track own bookings, cancel own pending/approved bookings before event start time, update personal profile. Cannot access any administrative views or modify account activation status. |
| **ADMIN** | Full operational console access (`/manage/`): review and approve/reject bookings, manage facility inventory and operating hours, maintain amenities, schedule facility closures, monitor live events, perform check-in/completion/no-show recording, print slips, generate reports, export CSVs, inspect audit trails, and configure global booking limits. |

> **Note**: Django's built-in `admin.site.urls` is explicitly excluded. The entire administrative interface is built with custom Django views, forms, models, and templates.

---

## 2. Main Features & Workflows

1. **Custom Admin Operations Console (`/manage/`)**:
   - 4 Live Database KPI Cards: Pending Requests, Approved Upcoming, Completed Events, Active Facilities.
   - Live Chart.js visualizations for monthly booking volume and facility usage breakdown.
   - Queue management for Pending submissions with atomic approval and mandatory rejection reasons.
2. **Facility & Amenity Management (`/manage/facilities/`)**:
   - Categorized venues with capacities, location details, and configurable weekday operating hours (Monday–Sunday).
   - Amenity catalog with line icons attached to rooms with specific quantities.
   - Archiving support that preserves historical booking references.
3. **Master Calendar & Scheduling (`/manage/calendar/`)**:
   - Interactive Day View and Week View with date navigation and facility filtering.
   - Visual display of confirmed reservations and active facility closures.
4. **Rescheduling (`/manage/reservations/<id>/reschedule/`)**:
   - Dedicated rescheduling form with conflict revalidation.
   - Original schedules archived in `ReservationChange` with reason and responsible admin metadata.
5. **Event Operations & Printable Slips (`/manage/events/`)**:
   - Check-in, actual start/end recording, event completion notes, incident notes, and no-show recording.
   - Printable official reservation slip and completion summary with dedicated print CSS (`@media print`).
6. **Facility Closure & Conflict Workflow (`/manage/closures/`)**:
   - Schedules maintenance blocks and detects overlapping approved bookings before creation.
   - Unresolved conflicts must be explicitly rescheduled or cancelled prior to closure activation.
7. **Reports, Analytics & CSV Export (`/manage/reports/`)**:
   - Date-filtered reservation logs and facility utilization metrics (booked hours and completed count).
   - Server-side CSV exports protected against spreadsheet formula injection.
8. **Audit Trail & System Settings (`/manage/audit/` & `/manage/settings/`)**:
   - Immutable audit trail recording actor, action, timestamp, target reference, and IP address.
   - Configurable limits: maximum event duration (default: 4h) and advance booking window (default: 30d).
9. **Basic User Discovery Portal (`/portal/`)**:
   - Searchable venue directory with category and capacity filtering.
   - Dynamic hourly availability slot calculator with privacy protections (organizer details hidden).
   - User booking tracker with cancellation protection before event start.

---

## 3. Application Architecture & Django MTV Design

The codebase adheres strictly to Django's Model-Template-View (MTV) pattern across modular applications:

- **`accounts`**: Custom `User` model, registration, login/logout, profile views, active user enforcement middleware (`ActiveUserEnforcementMiddleware`), role permissions (`@admin_required`), and admin user management.
- **`facilities`**: Models and views for `FacilityCategory`, `Facility`, `FacilityOperatingHour`, `Amenity`, and `FacilityAmenity`.
- **`reservations`**: Models (`Reservation`, `ClosureBlock`, `ReservationChange`), centralized business logic (`services.py`), review queues, calendar, and user submission flows.
- **`events`**: `EventRecord` model, on-site check-in, completion, no-show recording, and printable slip views.
- **`reporting`**: Aggregate metrics, facility utilization calculations, and formula-safe CSV exports.
- **`audit_settings`**: `AuditLog`, `SystemSetting`, and administrative configuration views.

---

## 4. Database Entities & Relationships

Detailed schema specifications, ER diagrams, and constraints are documented in [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md).

- **`User`**: Custom user subclassing `AbstractUser` with `role` (`BASIC_USER`, `ADMIN`), department, student/employee ID, and active status.
- **`FacilityCategory`** & **`Facility`**: Foreign-key protected (`on_delete=models.PROTECT`) with unique codes and operating schedules.
- **`FacilityAmenity`**: Many-to-many relationship with unique constraint on `(facility, amenity)`.
- **`Reservation`**: References facility and user with unique tracking reference, start/end timestamps, status, and decision metadata.
- **`ReservationChange`**: Captures previous schedule, new schedule, reason, and admin actor for rescheduled bookings.
- **`EventRecord`**: One-to-one operational tracking record (`models.OneToOneField`) tied to each reservation.
- **`ClosureBlock`**: Maintenance and blackout windows blocking facility availability.
- **`AuditLog`**: Append-only audit record capturing state-changing transactions.
- **`SystemSetting`**: Key-value table storing configurable booking constraints.

---

## 5. Supported Environment & Tested Dependencies

- **Python**: `3.14.x` (or `>= 3.10`)
- **Django**: `6.1.2` (or `>= 5.1`)
- **python-dotenv**: `1.2.4`
- **tzdata**: `2026.5`
- **sqlparse**: `0.6.0`
- **asgiref**: `3.12.1`
- **Frontend Assets**: Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Chart.js 4.4.7 (bundled locally in `static/`).
- **Database**: SQLite (default local demonstration) / PostgreSQL / MySQL.
- **Timezone**: `Asia/Manila`.

---

## 6. Virtual Environment Setup

### Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Linux / macOS:
```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 7. Dependency Installation

Install all required packages from `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## 8. Environment-Variable Configuration

1. Copy the example configuration template:
   ```bash
   cp .env.example .env
   ```
2. Update the `.env` file with appropriate environment values:
   ```env
   DEBUG=True
   SECRET_KEY=django-insecure-campus-facility-management-system-secret-key-2026-grp1
   ALLOWED_HOSTS=127.0.0.1,localhost,testserver
   TIME_ZONE=Asia/Manila
   ```

---

## 9. Database Migration

Run initial migrations to establish database tables and constraints:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 10. Admin Account Creation

An administrator account can be created using Django's interactive command:
```bash
python manage.py createsuperuser
```
Or simply use the repeatable seed data command below to automatically provision demo accounts.

---

## 11. Demo-Data Initialization

Execute the idempotent database seeder to populate realistic fictional campus data:
```bash
python manage.py seed_data
```

This provisions:
- **4 Facility Categories**: Auditoriums, Laboratories, Meeting Rooms, Multipurpose Halls.
- **7 Campus Facilities**: AUD-101, AUD-201, LAB-301, LAB-302, CONF-105, CONF-204, HALL-A.
- **8 Amenity Types**: 4K Projectors, Wireless Mics, Wi-Fi 6, Video Conferencing, PA Systems, Smart Boards, etc.
- **10 User Accounts**:
  - Administrator: `admin` (Password: `AdminPass123!`)
  - Basic Users: `juan.delacruz`, `maria.santos`, `clara.reyes`, `pedro.penduko`, `ana.silva`, `mark.bautista`, `elena.torres`, `gabriel.cruz`, `sarah.mendoza` (Password for all: `UserPass123!`)
- **25 Reservations**: Pending queue, Approved bookings, Rejected requests, Cancelled requests, Completed events, No-show events, and Adjacent booking demonstrations (`[09:00-11:00)` and `[11:00-13:00)`).
- **5 Facility Closure Blocks**.
- **16 Operational Event Records**.

---

## 12. Running the Development Server

Start the local server:
```bash
python manage.py runserver 127.0.0.1:8000
```
Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.
- Unauthenticated users will be directed to `/login/`.
- Signing in as `admin` automatically routes to the Admin Console at `/manage/`.
- Signing in as a basic user (e.g., `juan.delacruz`) automatically routes to the User Portal at `/portal/`.

---

## 13. Running Automated Tests

Run the full automated test suite covering permissions, validation, workflows, reports, and concurrency:
```bash
python manage.py test
```

### Test Coverage Highlights:
- **Authentication & Roles**: Verifies registration cannot create admin accounts, validates role-based redirects, enforces active-account session expulsion upon deactivation.
- **Reservation Rules**: Enforces capacity limits, operating hours, advance booking horizon, maximum duration, half-open interval overlap arithmetic, and adjacent timeslot validation.
- **Workflows**: Confirms rejection reasons are mandatory, checks rescheduling audit retention, validates check-in, completion, and no-show requirements.
- **IDOR & Security**: Confirms User B cannot view or cancel User A's reservations.
- **CSV & Formula Injection**: Confirms formula escape character handling and admin authorization for exports.
- **Concurrency & Locking**: Tests competing approvals for the same venue and overlapping time window under atomic database transactions.

---

## 14. CSV Report Exports & Important Features

1. **CSV Export (`/manage/reports/export/`)**:
   - `report_type=reservations`: Exports reference, status, venue, applicant, schedule, attendee count, decision metadata, and submission date.
   - `report_type=utilization`: Exports venue code, name, capacity, active bookings, total booked hours, and completed events.
   - Formula Injection Defense: Cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are prefixed with `'` to prevent malicious command execution when opened in Microsoft Excel or Google Sheets.
2. **Printable Reservation Slip (`/manage/events/<id>/print/`)**:
   - Accessible from the event operations table.
   - Uses `@media print` styling to remove navigation elements and print cleanly for venue staff and campus security.

---

## 15. Known Limitations & Concurrency Considerations

- **Concurrency Under SQLite**:
  - SQLite applies file-level locking during write transactions. When two threads concurrently execute `select_for_update()` inside `transaction.atomic()`, SQLite may raise `OperationalError: database is locked`.
  - The application catches database locking errors and converts them to user-friendly `ReservationConflictError` messages, cleanly rolling back without partial state corruption.
- **Production Concurrency (PostgreSQL / MySQL)**:
  - When deployed on PostgreSQL or MySQL with row-level locking, `select_for_update()` locks only the target `Facility` and `Reservation` rows, allowing non-conflicting bookings across other facilities to proceed concurrently without database-wide lock contention.

---

## 16. Submission Packaging Checklist

To produce the submission ZIP package:
- Target Archive Name: `IT401W_ProjectB_Section_Group.zip`
- Included: Source code (`accounts/`, `facilities/`, `reservations/`, `events/`, `reporting/`, `audit_settings/`, `config/`), templates, static assets, migrations, `docs/`, `requirements.txt`, `.env.example`, `.gitignore`, `README.md`.
- Excluded: `venv/`, `__pycache__/`, `db.sqlite3`, `.env`, temporary IDE artifacts.
