# Security Architecture & Concurrency Strategy

## 1. Security Defenses

### A. Strict Two-Role Authorization
- Exactly two application roles exist: `BASIC_USER` and `ADMIN`.
- Server-side role enforcement is implemented via custom decorators (`@admin_required`, `@active_user_required`) and context processors.
- User registration strictly sets `role = 'BASIC_USER'` on the server. Tampered role fields in POST payloads are disregarded.

### B. Active-User Session Enforcement
- `accounts.middleware.ActiveUserEnforcementMiddleware` inspects every incoming authenticated request.
- If an account is deactivated by an administrator, the middleware flushes the user's session, logs them out, injects an alert message, and redirects to `/login/`.
- Deactivated accounts cannot sign in or perform any transactions, even if their browser session had not expired.

### C. IDOR & Object Reference Protection
- All basic-user lookups, cancellation queries, and detail endpoints are scoped to `user=request.user` using `get_object_or_404(Reservation, id=reservation_id, user=request.user)`.
- A basic user cannot view, cancel, or infer details of another user's reservation by substituting IDs in query parameters or URL paths.
- Administrative endpoints reject unauthorized users with `403 PermissionDenied`.

### D. CSRF & State-Changing Operation Protection
- All state-changing operations (approvals, rejections, cancellations, rescheduling, check-ins, completions, status toggles, setting updates) require `POST` requests protected by Django CSRF tokens.
- No state changes are permitted via `GET` requests.

### E. Spreadsheet Formula Injection Defense
- Exported CSV cells in `/manage/reports/export/` are sanitized via `sanitize_csv_cell()`.
- Values beginning with formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) are automatically escaped with a leading single quote (`'`), preventing formula execution in Excel or Google Sheets.

### F. Privacy Preservation in Availability Displays
- When basic users inspect facility timeslots on `/portal/facilities/<id>/`, occupied intervals display generic labels (`Booked` or `Facility Closed`).
- Personal applicant details, event titles, purposes, attendee counts, and administrative notes of other users are never exposed.

---

## 2. Concurrency Strategy & Race Condition Prevention

### A. Half-Open Interval Definition
- All reservation time intervals are treated as half-open: `[start, end)`.
- Two bookings overlap if and only if:
  $$\text{start}_A < \text{end}_B \quad\text{and}\quad \text{end}_A > \text{start}_B$$
- Adjacent bookings (e.g., `09:00 - 10:00` and `10:00 - 11:00`) are explicitly permitted and non-conflicting.

### B. Atomic Transaction & Lock Strategy
- The approval workflow in `reservations.services.approve_reservation()` executes inside `with transaction.atomic():`.
- The service acquires row-level locks on the reservation and the facility using `select_for_update()`.
- Inside the atomic block, the service performs fresh database queries for:
  1. Reservation status (must still be `PENDING`).
  2. Active facility status (must not be archived).
  3. Operating hours compliance.
  4. Active facility closures during the requested window.
  5. Existing `APPROVED` or `CHECKED_IN` bookings during the interval.
- If any conflict is detected, the transaction rolls back cleanly, raising `ReservationConflictError`.
- No partial state changes, duplicate event records, or orphaned audit entries are persisted.

### C. Backend-Specific Concurrency Limitations
- **SQLite (Local Demonstration)**:
  - SQLite uses file-level database locking during write transactions.
  - When two threads concurrently execute `select_for_update()`, SQLite serializes writes or raises `OperationalError: database is locked`.
  - `approve_reservation` catches `(OperationalError, DatabaseError)` and converts it to a clean `ReservationConflictError("Concurrency conflict: The database locked this facility...")`.
  - This ensures SQLite never crashes the application, rolls back cleanly, and preserves the losing reservation in `PENDING` status.
- **PostgreSQL / MySQL (Production Recommendation)**:
  - On PostgreSQL/MySQL, `select_for_update()` achieves true row-level locks on the `Facility` and `Reservation` records without locking unrelated tables or facilities.
  - Competing approvals for the same facility serialize cleanly, allowing one to complete and immediately triggering the conflict detection check on the second transaction.
