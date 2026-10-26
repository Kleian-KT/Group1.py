# Campus Facility Reservation and Event Scheduling System (BulSU CARES)
# System Architecture Specification

**Document Version:** 1.0.0  
**Target Environment:** Python 3.14 / Django 5.x/6.x  
**Course & Project:** IT 401W - Web Programming and Frameworks (Final Project B)  
**Evaluator:** Dr. Aaron Paul M. Dela Rosa  
**Primary Focus:** 75% Custom Administrative Console (`/manage/`), 25% Basic User Discovery & Booking Portal (`/portal/`)  

---

## 1. Executive Architectural Overview

The **Campus Facility Reservation and Event Scheduling System (BulSU CARES)** is engineered as an enterprise-grade, multi-tier web application built upon the Python/Django ecosystem. The architecture emphasizes **zero reliance on Django's built-in administrative site (`django.contrib.admin`)**, full separation of operational concerns, strict relational and transactional integrity, atomic concurrency protections against race conditions, and complete audit observability.

### Core Architectural Pillars

1. **Clean Three-Tier Decoupling:** Complete separation of presentation (Client Browser / Responsive HTML5 / Bootstrap 5 / Tailwind CSS), application business logic (Django MTV + Service Layer), and persistent relational storage (SQLite / PostgreSQL).
2. **Domain Service Layer Architecture:** High-order business rules (such as interval mathematics, pessimistic concurrency locks, state transitions, and audit trails) are isolated in a decoupled domain service layer (`reservations/services.py`), keeping Django views and models cohesive and maintainable.
3. **Pessimistic Concurrency & Double-Booking Protection:** Multi-layered defense against double bookings combining thread-level locks (`threading.Lock`), transactional row-level pessimistic database locks (`select_for_update`), and post-lock interval overlap revalidation.
4. **Mathematical Interval Arithmetic:** Time-slot conflict resolution adheres to half-open interval overlap mathematics: $[start, end)$, guaranteeing that consecutive adjacent slots (e.g., 08:00–10:00 and 10:00–12:00) never generate false conflicts.
5. **Role-Based Access Control (RBAC) & Active Session Invalidation:** Strict binary role model (`BASIC_USER` vs `ADMIN`). Custom middleware (`ActiveUserEnforcementMiddleware`) intercepts every inbound HTTP request to instantly evict deactivated users mid-session without server restart.
6. **Immutable Audit Observability:** Append-only transaction logging (`audit_settings_auditlog`) capturing 22 distinct system actions with actor identity, action type, IP address, and before-and-after metadata.

---

## 2. System Architecture Diagrams

### 2.1 Simplified System Architecture Diagram (Executive / Presentation View)

The simplified architecture diagram abstracts low-level component wiring to clearly highlight the **Three-Tier Separation**, the **Dual Subsystems (75% Admin vs 25% User Portal)**, **Zero Built-In Django Admin**, and the **Domain Concurrency Engine**.

```mermaid
flowchart TB
    %% Tier 1: Presentation Layer
    subgraph T1 ["Tier 1: Presentation Layer (Client Devices)"]
        direction LR
        U["👤 Basic User\n(Students & Faculty)"]
        A["🛡️ Administrator\n(PFLMO Operations Staff)"]
    end

    %% Tier 2: Application Layer
    subgraph T2 ["Tier 2: Application & Business Logic Layer (Python / Django)"]
        direction TB

        subgraph IngressLayer ["Security & Ingress Boundary"]
            direction LR
            GATE_U["User Security Gate\n• Session Auth & CSRF\n• ActiveUser Middleware"]
            GATE_A["Admin Security Gate\n• Role Guard (@admin_required)\n• ActiveUser Middleware"]
        end

        subgraph Subsystems ["Dual Subsystems (0% Built-in Django Admin)"]
            direction LR
            UP["🌐 User Discovery Portal (/portal/)\n[25% Project Scope]\n• Facility Catalog & Live Slots\n• Request Booking & Own Tracker"]
            AP["⚙️ Custom Admin Console (/manage/)\n[75% Project Scope]\n• Real-Time KPI Dashboard\n• Approvals & Rescheduling\n• Event Check-in, Slips & Audit"]
        end

        SERVICES["⚡ Central Domain Services & Concurrency Engine (services.py)\n• Half-Open Interval Algebra: [start, end) Overlap Theorem\n• Concurrency Lock: threading.Lock + select_for_update()\n• 7-State Lifecycle State Machine & Immutable Audit Trail"]
    end

    %% Tier 3: Persistence Layer
    subgraph T3 ["Tier 3: Persistence & Data Layer"]
        direction TB
        ORM["Django Object-Relational Mapper (ORM)"]
        DATABASE[("🗄️ Relational Database (SQLite / PostgreSQL)\nACID Transactions & Strict Referential Integrity (models.PROTECT)")]
    end

    %% Parallel Non-Crossing Flows (Zero Intersections / Zero Overlaps)
    U -->|"HTTP Request"| GATE_U
    A -->|"HTTP Request"| GATE_A

    GATE_U -->|"Role: BASIC_USER"| UP
    GATE_A -->|"Role: ADMIN"| AP

    UP -->|"Domain Service Call"| SERVICES
    AP -->|"Domain Service Call"| SERVICES

    SERVICES -->|"ORM Queries / Locks"| ORM
    ORM <-->|"SQL Transactions"| DATABASE
```

#### Simplified Diagram Code for Draw.io / PlantUML (Orthogonal Routing - Zero Overlaps)
*To use in Draw.io or Lucidchart: Click `Arrange` &rarr; `Insert` &rarr; `Advanced` &rarr; `PlantUML`, paste the block below, and insert:*

```plantuml
@startuml
skinparam backgroundColor #FFFFFF
skinparam defaultFontName Arial
skinparam roundcorner 8
skinparam shadowing false
skinparam linetype ortho

package "Tier 1: Presentation Layer (Clients)" {
    actor "Basic User\n(Student / Faculty)" as User
    actor "Administrator\n(PFLMO Staff)" as Admin
}

package "Tier 2: Application Layer (Python / Django)" {
    package "Security & Ingress Boundary" {
        component "User Security Gate\n(Session Auth, CSRF, ActiveUser)" as GateUser
        component "Admin Security Gate\n(@admin_required, CSRF, ActiveUser)" as GateAdmin
    }
    
    package "Dual Subsystems (0% Built-in Django Admin)" {
        component "User Discovery Portal (/portal/)\n[25% Scope]\n- Facility Catalog & Slot Preview\n- Booking Form & Tracker" as UserPortal
        component "Custom Admin Console (/manage/)\n[75% Scope]\n- Real-Time KPI Dashboard\n- Approvals & Rescheduling\n- Event Operations & Audit" as AdminConsole
    }
    
    component "Central Domain Services & Concurrency Engine (services.py)\n- Half-Open Interval Algebra: [start, end) Overlap Theorem\n- Concurrency Lock: threading.Lock + select_for_update()\n- 7-State Lifecycle State Machine & Immutable Audit Trail" as DomainServices
}

package "Tier 3: Persistence Layer (Data Store)" {
    component "Django ORM" as ORM
    database "Relational Database\n(SQLite / PostgreSQL)\n- ACID Transactions\n- Referential Integrity (models.PROTECT)" as DB
}

' Parallel Left Track (Zero Overlap)
User -down-> GateUser : HTTP
GateUser -down-> UserPortal : Role: BASIC_USER
UserPortal -down-> DomainServices : Service Calls

' Parallel Right Track (Zero Overlap)
Admin -down-> GateAdmin : HTTP
GateAdmin -down-> AdminConsole : Role: ADMIN
AdminConsole -down-> DomainServices : Service Calls

' Shared Database Track (Zero Overlap)
DomainServices -down-> ORM : ORM Operations
ORM <->down- DB : SQL / Transactions
@enduml
```

---

### 2.2 Comprehensive Multi-Tier System Architecture Diagram (Detailed Engineering View)

```mermaid
flowchart TB
    %% Tier 1: Presentation Layer
    subgraph Tier1 ["Tier 1: Presentation & Client Layer"]
        direction LR
        UserClient["Basic User Client Browser\n(Students / Faculty / Org Leaders)\nDesktop & Mobile HTML5"]
        AdminClient["Administrator Operations Client\n(PFLMO / Facility Staff)\nConsole & Print Engine"]
    end

    %% Tier 2: Application & Business Logic Layer
    subgraph Tier2 ["Tier 2: Application & Business Logic Layer (Python / Django)"]
        direction TB

        subgraph IngressGateway ["Security & Ingress Boundary"]
            HTTPRouter["HTTP / HTTPS Listener (Port 8000 / 443)"]
            CSRFShield["CSRF Protection Token Validator"]
            SessionGuard["Session Authentication & Verification"]
            ActiveMiddleware["ActiveUserEnforcementMiddleware\n(Live User Deactivation Eviction)"]
            RBACFilter["RBAC Decorators (@admin_required, @active_user_required)"]
        end

        subgraph Subsystems ["Presentation & Controller Subsystems"]
            direction LR
            PortalSubsystem["User Discovery Portal (/portal/)\n- Facility Catalog & Details (U2)\n- Dynamic Availability Grid (U2)\n- Booking Request Submission (U3)\n- Own Booking Tracker & Cancel (U4)\n- Personal Profile Management (U1)"]
            AdminSubsystem["Custom Admin Console (/manage/)\n- Real-Time KPI Dashboard (A7)\n- User Account Controls (A1)\n- Facility & Amenity Engine (A2)\n- Review & Approval Queue (A3)\n- Master Calendar & Reschedule (A4)\n- Live Event Operations & Slips (A5)\n- Facility Closure Management (A6)\n- Reports & Analytics Exporter (A7)\n- Audit Trail & Global Settings (A8)"]
        end

        subgraph ServiceLayer ["Domain Service Layer (reservations/services.py)"]
            IntervalEngine["Interval Conflict Engine\n[start, end) Half-Open Interval Algebra"]
            ConcurrencyMgr["Concurrency & Locking Manager\nthreading.Lock + select_for_update()"]
            StateMachine["Reservation State Machine\n7-State Lifecycle Validator & Enforcer"]
            EventTracker["Event Operations Engine\nCheck-in / Completion / No-Show Logs"]
            AuditService["Audit Trail Engine (log_audit)\n22 Immutable Operational Events"]
            ExportService["Report & CSV Streaming Engine\nAggregations + Formula Injection Filter"]
        end
    end

    %% Tier 3: Persistence Layer
    subgraph Tier3 ["Tier 3: Persistence & Relational Data Layer"]
        direction TB
        ORM["Django Object-Relational Mapper (ORM)"]
        
        subgraph RelationalDB ["Relational Database (SQLite / PostgreSQL)"]
            UserTable[("accounts_user")]
            FacilityTable[("facilities_facility & related")]
            ReservationTable[("reservations_reservation & changes")]
            EventTable[("events_eventrecord")]
            AuditTable[("audit_settings_auditlog")]
            SettingsTable[("audit_settings_systemsetting")]
        end
    end

    %% Inter-Tier Connections
    UserClient -->|"HTTP Requests (GET/POST)"| HTTPRouter
    AdminClient -->|"HTTP Requests (GET/POST)"| HTTPRouter

    HTTPRouter --> CSRFShield
    CSRFShield --> SessionGuard
    SessionGuard --> ActiveMiddleware
    ActiveMiddleware --> RBACFilter

    RBACFilter -->|"Role: BASIC_USER"| PortalSubsystem
    RBACFilter -->|"Role: ADMIN"| AdminSubsystem

    PortalSubsystem --> IntervalEngine
    PortalSubsystem --> StateMachine

    AdminSubsystem --> ConcurrencyMgr
    AdminSubsystem --> IntervalEngine
    AdminSubsystem --> StateMachine
    AdminSubsystem --> EventTracker
    AdminSubsystem --> AuditService
    AdminSubsystem --> ExportService

    ConcurrencyMgr --> ORM
    IntervalEngine --> ORM
    StateMachine --> ORM
    EventTracker --> ORM
    AuditService --> ORM
    ExportService --> ORM

    ORM <--> UserTable
    ORM <--> FacilityTable
    ORM <--> ReservationTable
    ORM <--> EventTable
    ORM <--> AuditTable
    ORM <--> SettingsTable
```

---

## 3. Django MTV & Service-Layer Architecture

BulSU CARES implements an extended **Model-Template-View-Service (MTVS)** design pattern. While traditional Django couples business workflows directly inside views or model methods, BulSU CARES decouples mission-critical transaction coordination into an explicit service layer.

```mermaid
flowchart LR
    ClientBrowser(["Client Browser"]) -->|"1. HTTP Request"| DjangoMiddleware["Django Middleware\n(CSRF, Auth, ActiveUser)"]
    DjangoMiddleware -->|"2. Dispatched Route"| URLResolver["URL Dispatcher\n(config/urls.py)"]
    URLResolver -->|"3. Executed View"| ViewLayer["View Controller Layer\n(views.py)"]
    ViewLayer -->|"4. Form Clean & Bind"| FormLayer["Form Layer\n(forms.py)"]
    ViewLayer -->|"5. Coordinate Transaction"| ServiceLayer["Domain Service Layer\n(services.py)"]
    ServiceLayer -->|"6. Atomic Locking & ORM Calls"| ModelLayer["Model / ORM Layer\n(models.py)"]
    ModelLayer <-->|"7. SQL Queries / Locks"| Database[("Database Engine")]
    ServiceLayer -->|"8. Result / State"| ViewLayer
    ViewLayer -->|"9. Render Context"| TemplateLayer["Template Presentation\n(DTL + Tailwind CSS)"]
    TemplateLayer -->|"10. HTTP Response (HTML5)"| ClientBrowser
```

### Component Responsibility Breakdown

| Layer | Files / Locations | Primary Responsibilities |
| :--- | :--- | :--- |
| **URL Dispatcher** | `config/urls.py`, `accounts/urls.py`, `reservations/user_urls.py`, `reservations/admin_urls.py` | Routes incoming requests based on prefix (`/`, `/portal/`, `/manage/`). Contains zero default `admin/` references. |
| **Middleware** | `accounts/middleware.py` (`ActiveUserEnforcementMiddleware`) | Intercepts all requests pre-view. Checks `request.user.is_active` against database. Discards sessions for deactivated users. |
| **View Controllers** | `accounts/views.py`, `facilities/views.py`, `reservations/views.py`, `events/views.py`, `reporting/views.py`, `audit_settings/views.py` | Accepts HTTP requests, checks authorization decorators, coordinates form validation, calls domain services, prepares UI view context. |
| **Form Layer** | `accounts/forms.py`, `facilities/forms.py`, `reservations/forms.py`, `events/forms.py`, `audit_settings/forms.py` | Validates input formats, cleans POST data, enforces field-level rules (e.g. non-negative participants, date ordering). |
| **Domain Service Layer** | `reservations/services.py`, `audit_settings/utils.py` | Encapsulates non-trivial business logic: pessimistic row locking, conflict overlap detection, state machine validation, audit recording. |
| **Model / ORM Layer** | `*/models.py` | Represents relational entities, declares field types, enforces database-level integrity (`models.PROTECT`, composite indexes, unique constraints). |
| **Presentation Templates** | `templates/base.html`, `templates/portal/*`, `templates/manage/*` | Server-rendered HTML5 using Django Template Language (DTL), styled with Tailwind CSS tokens and Chart.js dashboards. |

---

## 4. Subsystem & Modular Application Architecture

The system is partitioned into six cohesive Django applications, each addressing a dedicated domain:

```mermaid
graph TD
    subgraph CoreApplication ["BulSU CARES Core System Modules"]
        accounts["accounts\n- User Authentication\n- Binary Roles (BASIC / ADMIN)\n- Profile & Session Enforcement\n- User Directory Management"]
        facilities["facilities\n- Facility Catalog & Profiles\n- Categories & Soft Archival\n- Amenity Inventory (M:N)\n- Weekday Operating Schedule Matrix"]
        reservations["reservations\n- Booking Submissions\n- 7-State Lifecycle Engine\n- Double-Booking Prevention\n- Master Calendar & Rescheduling\n- Facility Closure Blocks"]
        events["events\n- On-Site Check-in Logging\n- Actual Run Time Tracking\n- Completion & Incident Notes\n- No-Show Penalties\n- Official Printable Slips"]
        reporting["reporting\n- 8 Real-time KPI Aggregations\n- Monthly Volume Trends (Chart.js)\n- Facility Utilization Metrics\n- Formula-Safe CSV Streaming"]
        audit_settings["audit_settings\n- Append-Only Audit Trail (22 Actions)\n- Actor & IP Address Auditing\n- Dynamic Booking Limits Config\n- System Operational Flags"]
    end

    accounts --> facilities
    accounts --> reservations
    accounts --> audit_settings
    facilities --> reservations
    reservations --> events
    reservations --> reporting
    reservations --> audit_settings
    events --> audit_settings
```

### Module Responsibilities & Capabilities

#### 1. `accounts` (Identity & Access Management)
- **Custom User Model (`User`)**: Inherits from `AbstractUser`; extends with `role` (`BASIC_USER`, `ADMIN`), `department`, `contact_number`, and `student_employee_id`.
- **Enforcement Middleware (`ActiveUserEnforcementMiddleware`)**: Evicts users immediately upon deactivation without waiting for session expiry.
- **Role Decorators**: `@admin_required` guarantees only administrators can access `/manage/` routes. `@active_user_required` blocks suspended accounts.
- **Admin User Management**: Custom CRUD for administrators to activate, deactivate, or reassign user privileges.

#### 2. `facilities` (Physical Asset & Schedule Catalog)
- **Facility Management**: Stores facility profiles with physical capacities, locations, and status flags. Soft archiving via `is_active=False` guarantees historical booking records are never orphaned.
- **Operating Hours Matrix (`FacilityOperatingHour`)**: Configurable operating hours per weekday (Monday–Sunday) with fallback to facility default hours and explicit `is_closed` override flags.
- **Amenity Catalog (`Amenity` & `FacilityAmenity`)**: Reusable campus equipment catalog mapped to facilities with quantified allocations.

#### 3. `reservations` (Core Booking & Concurrency Engine)
- **Booking Submission**: Public submission flow validating participant capacities, lead times, and single-day bounds.
- **7-State Lifecycle State Machine**: Enforces valid transitions across `PENDING`, `APPROVED`, `CHECKED_IN`, `COMPLETED`, `REJECTED`, `CANCELLED`, and `NO_SHOW`.
- **Rescheduling Engine (`ReservationChange`)**: Preserves complete historical audit trail when a confirmed reservation's date, time, or venue is modified.
- **Closure Management (`ClosureBlock`)**: Blackout blocks for maintenance or campus holidays. Enforces explicit pre-closure resolution of conflicting approved bookings.

#### 4. `events` (Operational Execution & Day-of-Event Operations)
- **Event Tracking (`EventRecord`)**: One-to-one record tied to each reservation. Captures actual arrival time, actual completion time, incident reports, and staff notes.
- **No-Show Tracking**: Marks abandoned bookings and prevents re-check-in.
- **Printable Slips**: Dedicated printable booking permits and completion certificates formatted with `@media print` stylesheets.

#### 5. `reporting` (Business Intelligence & Data Export)
- **KPI Metrics**: Real-time database aggregations (Total Requests, Approval Rate, Hours Booked, Most Utilized Facility).
- **Chart.js Integration**: Feeds interactive JSON payloads for monthly booking trends and facility usage distribution.
- **CSV Data Streaming**: Server-side CSV generation with **formula injection defense** (prefixes dangerous characters `=`, `+`, `-`, `@`, `\t`, `\r` with single quotes).

#### 6. `audit_settings` (Governance & Configuration)
- **Immutable Audit Trail (`AuditLog`)**: Logs 22 distinct system actions with user reference, IP address, timestamp, and target entity references.
- **Dynamic Configuration (`SystemSetting`)**: Runtime-configurable limits without server restart (e.g., `MAX_ADVANCE_DAYS`, `MAX_EVENT_HOURS`).

---

## 5. Security & Access Control Architecture

BulSU CARES enforces defense-in-depth across the network, application, and database tiers.

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Browser
    participant Gate as Ingress Security & Middleware
    participant Route as URL Router & Permissions
    participant View as Custom View Controller
    participant Service as Domain Service Layer
    participant DB as Database (ACID)

    Client->>Gate: HTTP POST /manage/reservations/12/approve/
    Note over Gate: Validate CSRF Token
    Gate->>Gate: ActiveUserEnforcementMiddleware: Check user.is_active
    alt User is Inactive
        Gate-->>Client: Flush Session & Redirect to Login with Alert
    else User is Active
        Gate->>Route: Pass Request to Route Dispatcher
    end

    Route->>Route: Check @admin_required Decorator
    alt Role != ADMIN
        Route-->>Client: 403 Forbidden / Redirect to User Portal
    else Role == ADMIN
        Route->>View: Invoke admin_reservation_approve(request, 12)
    end

    View->>Service: approve_reservation(12, admin_user, request)
    Note over Service: Acquire Thread Concurrency Lock
    Service->>DB: BEGIN TRANSACTION (atomic)
    Service->>DB: SELECT ... FOR UPDATE (Lock Reservation & Facility rows)
    Service->>Service: Revalidate State (Must be PENDING)
    Service->>Service: Revalidate Half-Open Overlaps [start, end)
    
    alt Overlap Conflict Detected
        Service->>DB: ROLLBACK TRANSACTION
        Service-->>View: Raise ReservationConflictError
        View-->>Client: Error Banner: "Slot already booked by #REF"
    else No Conflict
        Service->>DB: UPDATE reservations_reservation SET status='APPROVED'
        Service->>DB: INSERT INTO audit_settings_auditlog
        Service->>DB: COMMIT TRANSACTION
        Service-->>View: Success Confirmation
        View-->>Client: Redirect to Reservation Detail with Success Alert
    end
```

### Security Measures & Implementation Reference

| Threat Vector | Mitigation Strategy | Architectural Mechanism | Implementation File |
| :--- | :--- | :--- | :--- |
| **Privilege Escalation** | Strict server-side role assignment | `UserRegistrationForm.save()` hardcodes `role = 'BASIC_USER'`. Django Admin (`admin.site.urls`) completely disabled. | `accounts/forms.py`, `config/urls.py` |
| **Unauthorized Admin Access** | Role-based route decorators | `@admin_required` intercepts unauthorized requests, displays flash notice, and redirects to basic portal. | `accounts/permissions.py` |
| **Deactivated User Exploitation** | Live mid-session expulsion | `ActiveUserEnforcementMiddleware` verifies database `is_active` state on every request, flushes session immediately if deactivated. | `accounts/middleware.py` |
| **Insecure Direct Object Reference (IDOR)** | Owner-scoped query filtering | Basic user views filter querysets with `filter(user=request.user)`. Users cannot view or cancel other users' bookings. | `reservations/views.py` |
| **Double-Booking Race Conditions** | Pessimistic locking + overlap revalidation | `threading.Lock` + `select_for_update()` inside `transaction.atomic()` serializes concurrent approvals. | `reservations/services.py` |
| **Cross-Site Request Forgery (CSRF)** | Synchronizer Token Pattern | All POST forms require `{% csrf_token %}`. Cookie secured with `CSRF_COOKIE_HTTPONLY`. | `config/settings.py` |
| **Spreadsheet Formula Injection** | CSV export character sanitization | Server prefixes spreadsheet trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with single quotes before CSV output. | `reporting/views.py` |
| **SQL Injection** | Parameterized queries | 100% of database interactions leverage Django ORM parameterization; zero raw SQL concatenation. | Global codebase |

---

## 6. Concurrency Control & Double-Booking Prevention

### The Concurrency Problem

When two administrators simultaneously attempt to approve two pending reservations for the same facility at identical or overlapping time windows, standard database read-then-write logic permits a **Time-of-Check to Time-of-Use (TOCTOU)** race condition, resulting in illegal double bookings.

```
Admin A: Read Slot (Vacant) ------> Approve (Writes Approved) ----> [Double Booking!]
Admin B: Read Slot (Vacant) --------------------------------------> [Double Booking!]
```

### BulSU CARES Two-Tier Concurrency Architecture

To guarantee absolute transactional isolation, BulSU CARES deploys a **Two-Tier Synchronization Lock**:

1. **Process-Level Thread Lock (`_approval_concurrency_lock = threading.Lock()`):** Serializes approval execution across concurrent server threads, preventing simultaneous evaluation within the same application process.
2. **Database-Level Pessimistic Row Lock (`select_for_update()`):** Enforces exclusive row-level locking on the `Facility` and `Reservation` records within an atomic transaction (`with transaction.atomic()`).
3. **Post-Lock Conflict Revalidation:** Inside the acquired lock, the service queries for any existing `APPROVED` or `CHECKED_IN` reservations overlapping the requested interval:
   $$\text{Overlap} \iff (S_1 < E_2) \land (E_1 > S_2)$$
   If any overlap exists, the transaction rolls back immediately and raises a `ReservationConflictError`.

```mermaid
flowchart TD
    StartApproval["Admin clicks 'Approve Reservation'"] --> ThreadLock["Acquire Process-Level Thread Lock\n(_approval_concurrency_lock)"]
    ThreadLock --> BeginTx["Begin Atomic Database Transaction\n(transaction.atomic())"]
    BeginTx --> RowLock["Acquire Row-Level Pessimistic Lock\nReservation.objects.select_for_update().get(id)\nFacility.objects.select_for_update().get(id)"]
    RowLock --> VerifyStatus{"Is Reservation Status\nstill PENDING?"}
    VerifyStatus -- No --> AbortState["Raise ReservationWorkflowError\n(Rollback Transaction)"]
    VerifyStatus -- Yes --> VerifyActive{"Is Facility\nActive & Operational?"}
    VerifyActive -- No --> AbortFacility["Raise ReservationWorkflowError\n(Rollback Transaction)"]
    VerifyActive -- Yes --> VerifyRules{"Validate Rules:\nCapacity & Single-Day Bounds"}
    VerifyRules -- Failed --> AbortRules["Raise ReservationWorkflowError\n(Rollback Transaction)"]
    VerifyRules -- Passed --> CheckClosures{"Overlaps Active\nFacility Closure?"}
    CheckClosures -- Yes --> AbortClosure["Raise ReservationConflictError\n(Rollback Transaction)"]
    CheckClosures -- No --> CheckApproved{"Overlaps Approved or\nChecked-In Reservation?\n(start1 < end2 AND end1 > start2)"}
    CheckApproved -- Yes --> AbortOverlap["Raise ReservationConflictError\n(Rollback Transaction)"]
    CheckApproved -- No --> CommitApproval["1. Set status = APPROVED\n2. Set decision_by & decision_at\n3. Create/Init EventRecord\n4. Write AuditLog Record\n5. COMMIT Transaction"]
    CommitApproval --> ReleaseLock["Release Thread Lock"]
    AbortState --> ReleaseLock
    AbortFacility --> ReleaseLock
    AbortRules --> ReleaseLock
    AbortClosure --> ReleaseLock
    AbortOverlap --> ReleaseLock
    ReleaseLock --> ResultNotice["Return Result & Render Alert to Admin"]
```

---

## 7. Reservation Lifecycle & State Machine Architecture

A reservation traverses a deterministic, finite state machine with **7 discrete states**. Direct modification of terminal states is structurally prevented by validation guards in the service layer.

```mermaid
stateDiagram-v2
    [*] --> PENDING: User Submits Request (/portal/reservations/create/)
    
    PENDING --> APPROVED: Admin Approves (/manage/reservations/approve/)
    PENDING --> REJECTED: Admin Rejects with Reason (/manage/reservations/reject/)
    PENDING --> CANCELLED: User Cancels Own Request (/portal/reservations/cancel/)
    
    APPROVED --> CHECKED_IN: Admin Records On-Site Arrival (/manage/events/check-in/)
    APPROVED --> CANCELLED: Admin or User Cancels Before Start
    APPROVED --> APPROVED: Admin Reschedules with Conflict Check (/manage/reservations/reschedule/)
    APPROVED --> NO_SHOW: Admin Records Abandonment (/manage/events/no-show/)
    
    CHECKED_IN --> COMPLETED: Admin Records Checkout & Notes (/manage/events/complete/)
    
    REJECTED --> [*]: Terminal State (Read-Only)
    CANCELLED --> [*]: Terminal State (Read-Only)
    COMPLETED --> [*]: Terminal State (Read-Only)
    NO_SHOW --> [*]: Terminal State (Read-Only)
```

### State Transition Rules & Invariants

| From State | To State | Initiator | Preconditions & Invariants |
| :--- | :--- | :--- | :--- |
| **`[None]`** | `PENDING` | Basic User | Participant count $\le$ capacity; date within max advance window; single-day boundary. |
| `PENDING` | `APPROVED` | Admin | Atomic row lock; no overlapping closures; no overlapping approved reservations. |
| `PENDING` | `REJECTED` | Admin | Mandatory rejection reason entered; audit log entry recorded. |
| `PENDING` | `CANCELLED` | User / Admin | Can be cancelled any time while pending. |
| `APPROVED` | `CHECKED_IN` | Admin | Event date must match current date; actual check-in timestamp captured. |
| `APPROVED` | `CANCELLED` | User / Admin | Permitted only **prior** to event start time (`start_time > timezone.now()`). |
| `APPROVED` | `APPROVED` (Rescheduled) | Admin | New time must not conflict; original schedule preserved in `ReservationChange`. |
| `APPROVED` | `NO_SHOW` | Admin | Permitted after scheduled start time when organizer fails to arrive. |
| `CHECKED_IN` | `COMPLETED` | Admin | Actual end time, incident notes, and equipment return notes recorded in `EventRecord`. |

---

## 8. Relational Data Architecture & Referential Integrity

```mermaid
erDiagram
    User ||--o{ Reservation : "submits"
    User ||--o{ ReservationChange : "rescheduled_by"
    User ||--o{ ClosureBlock : "scheduled_by"
    User ||--o{ AuditLog : "performed_by"
    
    FacilityCategory ||--o{ Facility : "categorizes"
    Facility ||--o{ FacilityOperatingHour : "defines_schedule"
    Facility ||--o{ FacilityAmenity : "equips"
    Amenity ||--o{ FacilityAmenity : "assigned_to"
    
    Facility ||--o{ Reservation : "hosts"
    Facility ||--o{ ClosureBlock : "undergoes"
    
    Reservation ||--|| EventRecord : "tracks_operations"
    Reservation ||--o{ ReservationChange : "records_rescheduling"

    User {
        int id PK
        string username UK
        string email
        string role "BASIC_USER | ADMIN"
        string department
        string student_employee_id
        boolean is_active
    }

    FacilityCategory {
        int id PK
        string name UK
        string description
        boolean is_active
    }

    Facility {
        int id PK
        string code UK
        string name
        int category_id FK "PROTECT"
        int capacity
        string location
        time default_opening_time
        time default_closing_time
        boolean is_active
    }

    FacilityOperatingHour {
        int id PK
        int facility_id FK "CASCADE"
        int day_of_week "0=Mon..6=Sun"
        time opening_time
        time closing_time
        boolean is_closed
    }

    Amenity {
        int id PK
        string name UK
        string icon_class
        boolean is_active
    }

    FacilityAmenity {
        int id PK
        int facility_id FK "CASCADE"
        int amenity_id FK "CASCADE"
        int quantity
    }

    Reservation {
        int id PK
        string reference UK "e.g. RES-20261025-XXXX"
        int user_id FK "PROTECT"
        int facility_id FK "PROTECT"
        string title
        text purpose
        int participant_count
        datetime start_time
        datetime end_time
        string status "PENDING..COMPLETED"
        int decision_by_id FK "SET_NULL"
        datetime decision_at
        text rejection_reason
    }

    ReservationChange {
        int id PK
        int reservation_id FK "CASCADE"
        datetime previous_start_time
        datetime previous_end_time
        datetime new_start_time
        datetime new_end_time
        text reason
        int changed_by_id FK "PROTECT"
        datetime created_at
    }

    EventRecord {
        int id PK
        int reservation_id FK "CASCADE" "UNIQUE"
        datetime actual_start_time
        datetime actual_end_time
        text completion_notes
        text incident_notes
        boolean is_no_show
    }

    ClosureBlock {
        int id PK
        int facility_id FK "PROTECT"
        datetime start_time
        datetime end_time
        string reason
        int created_by_id FK "PROTECT"
        boolean is_active
    }

    AuditLog {
        int id PK
        int user_id FK "SET_NULL"
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
        datetime updated_at
    }
```

### Referential Integrity Strategies

1. **`on_delete=models.PROTECT` on Mission-Critical Relations:**
   - Deleting a `FacilityCategory` with active `Facility` records is prevented by the database.
   - Deleting a `Facility` or `User` with existing `Reservation` records is prohibited, ensuring that booking histories, financial logs, and audit trails remain permanently uncorrupted.
2. **`on_delete=models.CASCADE` for Dependent Child Records:**
   - `FacilityOperatingHour` and `FacilityAmenity` records are tied directly to their parent facility.
   - `EventRecord` and `ReservationChange` records cascade with their parent `Reservation`.
3. **`on_delete=models.SET_NULL` for Decoupled Audit Logs:**
   - If an administrative account is ever removed from the system, historical `AuditLog` entries retain all textual log details with `user_id` set to `NULL`, maintaining complete forensic records.
4. **Composite Unique Constraints:**
   - `(facility, day_of_week)` in `FacilityOperatingHour` prevents duplicate daily schedule rows.
   - `(facility, amenity)` in `FacilityAmenity` prevents redundant amenity links.

---

## 9. Deployment & Runtime Infrastructure Architecture

For production readiness, the system can be deployed across a containerized or virtualized topology:

```mermaid
flowchart TD
    PublicInternet(["Public Internet / Campus Network"]) --> WAF["Reverse Proxy & SSL Termination\n(Nginx 1.26+)\n- HTTPS Termination\n- Rate Limiting & DDoS Shield\n- Static Asset Caching (/static/)"]
    
    WAF -->|"Proxy Pass (Unix Socket / HTTP Port 8000)"| AppServer["WSGI Application Server\n(Gunicorn 23.x / Uvicorn)\n- 4-8 Worker Processes\n- Python 3.14 Execution\n- Django Application Thread Pool"]
    
    AppServer -->|"Internal Private Network"| DatabaseServer[("Relational Database\n(PostgreSQL 16+ / SQLite Dev)\n- ACID Transactions\n- Automated Snapshots\n- Connection Pooling (pgbouncer)")]
    
    AppServer -->|"Static Files Volume"| StaticVolume[("Static Asset Storage\n- Bootstrap 5 Assets\n- Chart.js 4.4.7 Bundles\n- Font & Icon Libraries")]
    
    AppServer -->|"Environment Config"| EnvConfig[(".env Secrets\n- SECRET_KEY\n- DEBUG=False\n- ALLOWED_HOSTS\n- DATABASE_URL")]
```

### Key Deployment Characteristics

- **Timezone Awareness:** Configured to `TIME_ZONE = 'Asia/Manila'` with `USE_TZ = True`. All database timestamps are persisted as UTC internally and converted aware for Philippine Standard Time presentation.
- **Static Assets:** Zero external CDN runtime dependencies required. Bootstrap 5, Bootstrap Icons, and Chart.js are vendor-bundled within the `static/` directory for air-gapped campus network reliability.
- **Formula Injection Defense:** CSV exports streamed with `Content-Type: text/csv` and sanitize leading formula triggers.

---

## 10. Summary Verification & Architectural Compliance

| Architectural Standard | Compliance Status | Implementation Reference |
| :--- | :--- | :--- |
| **Zero Django Admin Usage** | **100% Compliant** | `django.contrib.admin` excluded from `INSTALLED_APPS`; `admin.site.urls` omitted. |
| **75% / 25% Effort Distribution** | **100% Compliant** | Dedicated `/manage/` operations portal with 8 distinct administrative management modules. |
| **Atomic Concurrency Protection** | **100% Compliant** | `_approval_concurrency_lock` + `select_for_update()` in `reservations/services.py`. |
| **Interval Mathematics** | **100% Compliant** | Strict half-open $[start, end)$ overlap validation across all booking & closure engines. |
| **Session Eviction on Deactivation** | **100% Compliant** | `ActiveUserEnforcementMiddleware` flushes session immediately upon deactivation. |
| **Automated Test Coverage** | **100% Pass Rate** | 37 automated tests passing with zero failures and zero errors. |
