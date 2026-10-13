# Database Schema & Entity-Relationship Model

## 1. Overview
The **Campus Facility Reservation Management System** is built on Django ORM with strict relational integrity, foreign key protections (`models.PROTECT`), unique constraints, and database indexes for high-frequency queries on schedules, references, and statuses.

## 2. Mermaid Entity-Relationship Diagram

```mermaid
erDiagram
    User ||--o{ Reservation : "submits"
    User ||--o{ ClosureBlock : "schedules (admin)"
    User ||--o{ ReservationChange : "reschedules (admin)"
    User ||--o{ AuditLog : "acts"
    FacilityCategory ||--o{ Facility : "categorizes"
    Facility ||--o{ FacilityAmenity : "has"
    Amenity ||--o{ FacilityAmenity : "assigned to"
    Facility ||--o{ FacilityOperatingHour : "configures"
    Facility ||--o{ Reservation : "booked in"
    Facility ||--o{ ClosureBlock : "affected by"
    Reservation ||--|| EventRecord : "operational tracking (1-to-1)"
    Reservation ||--o{ ReservationChange : "reschedule history"

    User {
        int id PK
        string username UK
        string email
        string first_name
        string last_name
        string role "BASIC_USER | ADMIN"
        string phone_number
        string department
        string student_or_employee_id
        boolean is_active
        datetime date_joined
    }

    FacilityCategory {
        int id PK
        string name UK
        text description
        boolean is_active
        datetime created_at
    }

    Facility {
        int id PK
        string code UK
        string name
        int category_id FK
        string location
        int capacity
        time default_open_time
        time default_close_time
        boolean is_active
    }

    Amenity {
        int id PK
        string name UK
        string icon
        boolean is_active
    }

    FacilityAmenity {
        int id PK
        int facility_id FK
        int amenity_id FK
        int quantity
        string notes
    }

    FacilityOperatingHour {
        int id PK
        int facility_id FK
        int day_of_week "0=Mon .. 6=Sun"
        time open_time
        time close_time
        boolean is_closed
    }

    Reservation {
        int id PK
        string reference UK
        int user_id FK
        int facility_id FK
        string title
        text purpose
        int participant_count
        datetime start_time
        datetime end_time
        string status "PENDING|APPROVED|REJECTED|CANCELLED|CHECKED_IN|COMPLETED|NO_SHOW"
        int decision_by_id FK
        datetime decision_at
        text decision_reason
    }

    ClosureBlock {
        int id PK
        int facility_id FK
        datetime start_time
        datetime end_time
        text reason
        boolean is_active
        int created_by_id FK
    }

    ReservationChange {
        int id PK
        int reservation_id FK
        datetime previous_start_time
        datetime previous_end_time
        datetime new_start_time
        datetime new_end_time
        text reason
        int changed_by_id FK
        datetime changed_at
    }

    EventRecord {
        int id PK
        int reservation_id UK_FK
        datetime check_in_time
        int checked_in_by_id FK
        datetime actual_start_time
        datetime actual_end_time
        datetime completed_at
        int completed_by_id FK
        text completion_notes
        datetime no_show_recorded_at
        int no_show_recorded_by_id FK
        text no_show_notes
        text incident_notes
    }

    AuditLog {
        int id PK
        int actor_id FK
        string action
        string target_type
        string target_id
        string target_reference
        text details
        string ip_address
        datetime timestamp
    }

    SystemSetting {
        int id PK
        string key UK
        string value
        string description
    }
```

## 3. Relational Protections & Constraints

1. **Deletion Policies**:
   - `Reservation.facility` and `Reservation.user` use `on_delete=models.PROTECT`. Active and historical bookings can never be cascaded away when an account is deactivated or when a facility is archived.
   - `FacilityAmenity` has unique constraint on `(facility, amenity)` to prevent duplicate attachments.
   - `FacilityOperatingHour` has unique constraint on `(facility, day_of_week)`.

2. **One-to-One Operational Event Constraint**:
   - `EventRecord.reservation` is a `models.OneToOneField`, strictly guaranteeing at most one operational record per reservation.

3. **Database Indexes**:
   - `Reservation.reference`: Unique index for fast O(1) tracking lookups.
   - `Reservation.start_time` and `Reservation.end_time`: B-Tree indexes for fast interval overlap queries (`start_time < end_B AND end_time > start_B`).
   - `Reservation.status`: Indexed for queue filtering (`PENDING`, `APPROVED`, etc.).
   - `AuditLog.timestamp` and `AuditLog.action`: Indexed for administrative audit queries.
