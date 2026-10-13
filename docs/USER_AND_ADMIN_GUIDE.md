# User and Administrator Operations Guide

## 1. Roles and Access Credentials

| Role | Default Username | Default Password | Initial Landing URL | Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **ADMIN** | `admin` | `AdminPass123!` | `/manage/` | Full campus operational oversight, approval queue, facility inventory, calendar, check-in, closures, reports, audit trail, limits configuration. |
| **BASIC USER** | `juan.delacruz` | `UserPass123!` | `/portal/` | Browse facility inventory, check slot availability, submit requests, cancel own upcoming bookings, update personal profile. |

---

## 2. Administrator Guide (`/manage/`)

### A. Operational Dashboard (`/manage/`)
- View 4 real-time database KPI cards: Pending Requests, Approved Upcoming, Completed Events, and Active Facilities.
- Review monthly booking volume line chart and facility usage comparison bar chart (rendered via Chart.js from live queries).
- Quick triage of recent pending requests.

### B. User Management (`/manage/users/`)
- View all student and faculty accounts.
- Filter by role (`BASIC_USER`, `ADMIN`) or activation status.
- Inspect detailed user profiles and their complete historical booking records.
- Toggle account activation (deactivation instantly expels active sessions via `ActiveUserEnforcementMiddleware` without deleting historical booking records).

### C. Facility & Amenity Management (`/manage/facilities/`)
- **Facilities**: Add new facilities with unique codes, participant capacities, location descriptions, and default opening/closing hours.
- **Operating Hours**: Configure weekday schedules (Monday through Sunday) or mark facilities as closed on specific days.
- **Amenities**: Manage equipment catalogs (projectors, microphones, smart boards) with line icons and attach them to facilities with quantities and installation notes.
- **Archiving**: Archive inactive spaces or categories without breaking historical booking relationships.

### D. Reservation Review & Concurrency Handling (`/manage/reservations/`)
- Filter pending and historical bookings by status, venue, and date.
- Open the detailed **Review Page** to examine:
  - Event purpose and attendee count vs. facility capacity.
  - Requested time window vs. facility operating hours.
  - Active facility closures on the booking date.
  - Other approved bookings on the same date.
- **Approve**: Atomically checks locks and verifies no overlapping approved bookings exist.
- **Reject**: Requires a mandatory explanation, recorded in the audit log and visible to the applicant.
- **Reschedule**: Select a new time window and provide an administrative reason. The original approved timeslot is archived in `ReservationChange`.

### E. Calendar & Schedule (`/manage/calendar/`)
- Switch between **Day View** and **Week View**.
- Filter by specific facility.
- Navigate dates with previous, next, and today controls.
- Displays color-coded approved reservations and active closure periods.

### F. Event Operations & Pass Generation (`/manage/events/`)
- **Check-In**: Record check-in timestamp and actual start time for approved events.
- **Complete**: Record actual end time (enforced >= actual start time), completion notes, and incident/damage notes.
- **No-Show**: Record no-show status for approved events whose scheduled end time elapsed without check-in.
- **Print Pass / Summary**: Click the print icon to open the dedicated printable reservation slip formatted with `@media print`.

### G. Closure & Maintenance Management (`/manage/closures/`)
- Schedule maintenance blocks, sanitization, or campus activity closures.
- Conflicting approved reservations are detected before saving. The administrator is prompted to resolve conflicts before the closure can be activated.
- Active closures immediately block overlapping reservations from being approved or submitted.

### H. Reports & Analytics (`/manage/reports/`)
- Generate date-filtered reservation volume reports and facility utilization analyses.
- Inspect booked hours and completed events per venue.
- **CSV Export**: Click "Export CSV" to download either the detailed reservation report or the facility utilization report. Exported cells are sanitized against spreadsheet formula injection.

### I. Audit Logs & System Settings (`/manage/audit/` & `/manage/settings/`)
- **Audit Logs**: Immutable log of all administrative approvals, rejections, cancellations, reschedules, check-ins, closures, and setting changes.
- **System Settings**: Dynamically update global limits:
  - Maximum continuous event duration (default: 4 hours).
  - Maximum advance booking window (default: 30 days).

---

## 3. Basic User Portal Guide (`/portal/`)

### A. Discover Facilities (`/portal/facilities/`)
- Search by venue name, location, or facility code.
- Filter by facility category or minimum participant capacity.
- View operating hours, location details, and installed amenities.

### B. Inspect Availability Slots (`/portal/facilities/<id>/`)
- Select any date to inspect calculated hourly timeslots.
- Available slots display green with an "Available" badge.
- Occupied slots display red with "Booked" or "Facility Closed" labels without revealing other users' private event details.

### C. Submit a Reservation Request (`/portal/reservations/create/`)
- Select the facility, enter the event title, provide the expected attendee count, and select start and end datetimes.
- The system validates that the request fits within daily operating hours, does not exceed maximum duration, and respects the advance booking horizon.
- Submissions receive a unique reference (e.g., `RES-202610-A1B2C3`) and enter the **Pending** queue.

### D. Track and Cancel Reservations (`/portal/reservations/`)
- View the status of all submitted bookings.
- Inspect decision details and rejection reasons if applicable.
- Cancel pending or approved reservations before their scheduled start time with one click.
