import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from facilities.models import FacilityCategory, Facility, Amenity, FacilityAmenity, FacilityOperatingHour
from reservations.models import Reservation, ClosureBlock, ReservationChange
from events.models import EventRecord
from audit_settings.models import SystemSetting, AuditLog

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds reproducible demonstration dataset for Campus Facility Reservation Management System."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Initializing Campus Facility seed data..."))

        # 1. System Settings
        SystemSetting.objects.update_or_create(
            key=SystemSetting.MAX_DURATION_KEY,
            defaults={'value': '4', 'description': 'Maximum event duration in hours'}
        )
        SystemSetting.objects.update_or_create(
            key=SystemSetting.MAX_ADVANCE_WINDOW_KEY,
            defaults={'value': '30', 'description': 'Maximum advance booking window in days'}
        )

        # 2. Users
        # Admin Account
        admin_user, _ = User.objects.update_or_create(
            username='admin',
            defaults={
                'email': 'admin@campus.edu',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': User.ROLE_ADMIN,
                'department': 'Campus Operations & Facilities',
                'student_or_employee_id': 'EMP-0001',
                'phone_number': '+63 917 100 0001',
                'is_active': True,
                'is_staff': True,
            }
        )
        admin_user.set_password('AdminPass123!')
        admin_user.save()

        # Basic Users (9 accounts)
        basic_user_data = [
            ('juan.delacruz', 'juan@campus.edu', 'Juan', 'Dela Cruz', 'College of Engineering', 'STU-2023-0101', '+63 918 111 2221'),
            ('maria.santos', 'maria@campus.edu', 'Maria', 'Santos', 'College of Computer Studies', 'STU-2023-0202', '+63 918 111 2222'),
            ('clara.reyes', 'clara@campus.edu', 'Clara', 'Reyes', 'School of Business & Economics', 'STU-2022-0303', '+63 918 111 2223'),
            ('pedro.penduko', 'pedro@campus.edu', 'Pedro', 'Penduko', 'College of Arts & Letters', 'STU-2024-0404', '+63 918 111 2224'),
            ('ana.silva', 'ana@campus.edu', 'Ana', 'Silva', 'University Debate Society', 'ORG-2024-0505', '+63 918 111 2225'),
            ('mark.bautista', 'mark@campus.edu', 'Mark', 'Bautista', 'Robotics and AI Club', 'ORG-2023-0606', '+63 918 111 2226'),
            ('elena.torres', 'elena@campus.edu', 'Elena', 'Torres', 'Faculty of Architecture', 'FAC-2021-0707', '+63 918 111 2227'),
            ('gabriel.cruz', 'gabriel@campus.edu', 'Gabriel', 'Cruz', 'Department of Mathematics', 'FAC-2020-0808', '+63 918 111 2228'),
            ('sarah.mendoza', 'sarah@campus.edu', 'Sarah', 'Mendoza', 'Student Council Government', 'ORG-2024-0909', '+63 918 111 2229'),
        ]

        users = {}
        for username, email, fn, ln, dept, sid, phone in basic_user_data:
            u, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': fn,
                    'last_name': ln,
                    'role': User.ROLE_BASIC,
                    'department': dept,
                    'student_or_employee_id': sid,
                    'phone_number': phone,
                    'is_active': True,
                }
            )
            u.set_password('UserPass123!')
            u.save()
            users[username] = u

        # 3. Facility Categories (4 categories)
        cat_data = [
            ('Auditoriums & Theaters', 'Spacious lecture and performance venues with tiered seating and stage equipment.'),
            ('Laboratories & Technical Rooms', 'Computer laboratories, hardware experimentation rooms, and specialized tech spaces.'),
            ('Conference & Meeting Rooms', 'Executive meeting spaces designed for council, thesis defense, and organizational meetings.'),
            ('Multipurpose Halls & Open Spaces', 'Flexible multi-use halls for student fairs, exhibitions, and university gatherings.'),
        ]
        categories = {}
        for cname, cdesc in cat_data:
            cat, _ = FacilityCategory.objects.update_or_create(
                name=cname,
                defaults={'description': cdesc, 'is_active': True}
            )
            categories[cname] = cat

        # 4. Amenities (8 amenities)
        amenity_data = [
            ('HD Laser Projector', 'Ceiling-mounted 4K/HD laser projection unit with HDMI input.', 'bi-projector'),
            ('Wireless Microphones', 'Dual handheld UHF wireless microphone system with sound mixing.', 'bi-mic'),
            ('High-Speed Dedicated Wi-Fi', 'High-throughput enterprise Wi-Fi 6 access point.', 'bi-wifi'),
            ('Video Conferencing Suite', 'Smart auto-tracking camera with beamforming microphone array.', 'bi-camera-video'),
            ('Surround Audio PA System', 'Complete public address amplifier with boundary speakers.', 'bi-speaker'),
            ('Interactive Smart Board', '75-inch touch-enabled collaborative digital whiteboard display.', 'bi-tv'),
            ('Podium & Lectern', 'Wooden presentation podium equipped with reading lamp and microphone goose-neck.', 'bi-easel'),
            ('Modular Workstations', 'Configurable ergonomic movable tables with integrated charging hubs.', 'bi-laptop'),
        ]
        amenities = {}
        for aname, adesc, aicon in amenity_data:
            am, _ = Amenity.objects.update_or_create(
                name=aname,
                defaults={'description': adesc, 'icon': aicon, 'is_active': True}
            )
            amenities[aname] = am

        # 5. Facilities (7 facilities)
        facility_data = [
            ('AUD-101', 'University Main Auditorium', 'Auditoriums & Theaters', 'Building A, 1st Floor', 350,
             'Premier flagship campus venue for university-wide convocations and general assemblies.',
             datetime.time(8, 0), datetime.time(21, 0)),
            ('AUD-201', 'Little Theater Hall', 'Auditoriums & Theaters', 'Building A, 2nd Floor', 120,
             'Acoustically treated amphitheater ideal for cultural presentations and film screenings.',
             datetime.time(8, 0), datetime.time(20, 0)),
            ('LAB-301', 'Advanced Computing Laboratory', 'Laboratories & Technical Rooms', 'Science & Tech Complex, 3rd Floor', 45,
             'High-spec computer workstations running machine learning, CAD, and coding tools.',
             datetime.time(7, 30), datetime.time(19, 30)),
            ('LAB-302', 'Data Science & AI Lab', 'Laboratories & Technical Rooms', 'Science & Tech Complex, 3rd Floor', 40,
             'Research computing lab equipped with dual monitors and GPU clusters.',
             datetime.time(8, 0), datetime.time(20, 0)),
            ('CONF-105', 'Executive Boardroom', 'Conference & Meeting Rooms', 'Administration Building, 2nd Floor', 25,
             'Formal board meeting space with telepresence equipment and climate control.',
             datetime.time(8, 0), datetime.time(18, 0)),
            ('CONF-204', 'Student Council Council Chamber', 'Conference & Meeting Rooms', 'Student Pavilion, 2nd Floor', 30,
             'Collaborative meeting chamber designed for committee deliberations and workshops.',
             datetime.time(8, 0), datetime.time(21, 0)),
            ('HALL-A', 'Grand Campus Activity Hall', 'Multipurpose Halls & Open Spaces', 'Gymnasium Annex, Ground Floor', 200,
             'Open floor venue suitable for hackathons, career fairs, and large exhibitions.',
             datetime.time(8, 0), datetime.time(22, 0)),
        ]
        facilities = {}
        for fcode, fname, fcat, floc, fcap, fdesc, open_t, close_t in facility_data:
            fac, _ = Facility.objects.update_or_create(
                code=fcode,
                defaults={
                    'name': fname,
                    'category': categories[fcat],
                    'location': floc,
                    'capacity': fcap,
                    'description': fdesc,
                    'default_open_time': open_t,
                    'default_close_time': close_t,
                    'is_active': True,
                }
            )
            facilities[fcode] = fac

        # Assign amenities to facilities
        associations = [
            ('AUD-101', ['HD Laser Projector', 'Wireless Microphones', 'Surround Audio PA System', 'Podium & Lectern']),
            ('AUD-201', ['HD Laser Projector', 'Wireless Microphones', 'Surround Audio PA System']),
            ('LAB-301', ['High-Speed Dedicated Wi-Fi', 'Interactive Smart Board', 'Modular Workstations']),
            ('LAB-302', ['High-Speed Dedicated Wi-Fi', 'Interactive Smart Board', 'HD Laser Projector']),
            ('CONF-105', ['Video Conferencing Suite', 'HD Laser Projector', 'High-Speed Dedicated Wi-Fi']),
            ('CONF-204', ['Video Conferencing Suite', 'Interactive Smart Board']),
            ('HALL-A', ['Wireless Microphones', 'Surround Audio PA System', 'Modular Workstations', 'High-Speed Dedicated Wi-Fi']),
        ]
        for fcode, am_list in associations:
            fac = facilities[fcode]
            for am_name in am_list:
                am = amenities[am_name]
                FacilityAmenity.objects.get_or_create(
                    facility=fac,
                    amenity=am,
                    defaults={'quantity': 2, 'notes': 'Installed in primary setup'}
                )

        # 6. Operating Hours per weekday for AUD-101 and LAB-301
        for day in range(5): # Mon-Fri
            FacilityOperatingHour.objects.update_or_create(
                facility=facilities['AUD-101'],
                day_of_week=day,
                defaults={'open_time': datetime.time(8, 0), 'close_time': datetime.time(21, 0), 'is_closed': False}
            )
        FacilityOperatingHour.objects.update_or_create(
            facility=facilities['AUD-101'],
            day_of_week=5, # Saturday
            defaults={'open_time': datetime.time(8, 0), 'close_time': datetime.time(18, 0), 'is_closed': False}
        )
        FacilityOperatingHour.objects.update_or_create(
            facility=facilities['AUD-101'],
            day_of_week=6, # Sunday closed
            defaults={'open_time': datetime.time(8, 0), 'close_time': datetime.time(18, 0), 'is_closed': True}
        )

        # 7. Closure Blocks (5 closure blocks)
        base_now = timezone.now()
        closures_data = [
            (facilities['AUD-101'], base_now + datetime.timedelta(days=12, hours=8), base_now + datetime.timedelta(days=12, hours=12),
             'Annual HVAC and electrical system safety maintenance check.'),
            (facilities['LAB-301'], base_now + datetime.timedelta(days=15, hours=9), base_now + datetime.timedelta(days=15, hours=13),
             'Operating system upgrades and network switch firmware updates.'),
            (facilities['CONF-105'], base_now + datetime.timedelta(days=20, hours=13), base_now + datetime.timedelta(days=20, hours=17),
             'Executive suite interior painting and soundproofing touch-ups.'),
            (facilities['HALL-A'], base_now + datetime.timedelta(days=25, hours=8), base_now + datetime.timedelta(days=25, hours=16),
             'Floor waxing and seismic inspection drill.'),
            (facilities['AUD-201'], base_now - datetime.timedelta(days=10, hours=8), base_now - datetime.timedelta(days=10, hours=14),
             'Past historical closure: Projector lamp replacement and screen realignment.'),
        ]

        for fac, st, et, reason in closures_data:
            ClosureBlock.objects.get_or_create(
                facility=fac,
                start_time=st,
                end_time=et,
                defaults={
                    'reason': reason,
                    'is_active': True,
                    'created_by': admin_user
                }
            )

        # 8. Reservations & Event Records (At least 25 reservations)
        # Reference helper
        ref_counter = 1000

        # Create diverse cases across statuses
        # Historical Completed Events (8 events)
        hist_events = [
            ('juan.delacruz', 'AUD-101', 'Engineering Student Orientation', 'Orientation for freshmen engineering students', 220, -14, 9, 12, 'COMPLETED'),
            ('maria.santos', 'LAB-301', 'Web Development Hackathon 2026', 'Collegiate hackathon competition', 38, -12, 10, 14, 'COMPLETED'),
            ('clara.reyes', 'CONF-105', 'Quarterly Student Council Summit', 'Deliberation of semester organizational budget', 20, -10, 13, 16, 'COMPLETED'),
            ('mark.bautista', 'LAB-302', 'Robotics Hardware Hands-on', 'Workshop on microcontroller programming', 32, -8, 13, 17, 'COMPLETED'),
            ('ana.silva', 'AUD-201', 'Inter-Collegiate Debate Championship', 'Elimination rounds for campus debate cup', 95, -7, 14, 18, 'COMPLETED'),
            ('pedro.penduko', 'CONF-204', 'Campus Literary Society Reading', 'Poetry reading and creative writing open forum', 24, -5, 14, 17, 'COMPLETED'),
            ('elena.torres', 'AUD-101', 'Architecture Design Keynote', 'Guest lecture on sustainable urban structures', 280, -4, 9, 13, 'COMPLETED'),
            ('gabriel.cruz', 'LAB-301', 'Computational Math Symposium', 'Research presentations on applied algebra', 35, -3, 10, 13, 'COMPLETED'),
        ]

        for u_name, f_code, title, purp, pax, day_offset, start_h, end_h, status in hist_events:
            ref_counter += 1
            ref = f"RES-HIST-{ref_counter}"
            s_time = base_now + datetime.timedelta(days=day_offset)
            s_time = s_time.replace(hour=start_h, minute=0, second=0, microsecond=0)
            e_time = s_time.replace(hour=end_h, minute=0, second=0, microsecond=0)

            res, _ = Reservation.objects.update_or_create(
                reference=ref,
                defaults={
                    'user': users[u_name],
                    'facility': facilities[f_code],
                    'title': title,
                    'purpose': purp,
                    'participant_count': pax,
                    'start_time': s_time,
                    'end_time': e_time,
                    'status': status,
                    'decision_by': admin_user,
                    'decision_at': s_time - datetime.timedelta(days=2),
                    'decision_reason': 'Approved by administration based on complete documentation.',
                }
            )

            # Create operational EventRecord
            act_start = s_time + datetime.timedelta(minutes=5)
            act_end = e_time - datetime.timedelta(minutes=5)
            EventRecord.objects.update_or_create(
                reservation=res,
                defaults={
                    'check_in_time': s_time - datetime.timedelta(minutes=15),
                    'checked_in_by': admin_user,
                    'actual_start_time': act_start,
                    'actual_end_time': act_end,
                    'completed_at': act_end,
                    'completed_by': admin_user,
                    'completion_notes': 'Event concluded on schedule. Venue returned clean with all amenities verified.',
                    'incident_notes': '',
                }
            )

        # Historical No-Show Events (2 events)
        no_show_events = [
            ('pedro.penduko', 'CONF-105', 'Campus Editorial Strategy Sync', 'Cancelled attendance without prior notice', 15, -6, 10, 12),
            ('mark.bautista', 'LAB-302', 'Open Hardware Consultation Hour', 'No participants arrived', 10, -2, 15, 17),
        ]
        for u_name, f_code, title, purp, pax, day_offset, start_h, end_h in no_show_events:
            ref_counter += 1
            ref = f"RES-NOSHOW-{ref_counter}"
            s_time = base_now + datetime.timedelta(days=day_offset)
            s_time = s_time.replace(hour=start_h, minute=0, second=0, microsecond=0)
            e_time = s_time.replace(hour=end_h, minute=0, second=0, microsecond=0)

            res, _ = Reservation.objects.update_or_create(
                reference=ref,
                defaults={
                    'user': users[u_name],
                    'facility': facilities[f_code],
                    'title': title,
                    'purpose': purp,
                    'participant_count': pax,
                    'start_time': s_time,
                    'end_time': e_time,
                    'status': Reservation.STATUS_NO_SHOW,
                    'decision_by': admin_user,
                    'decision_at': s_time - datetime.timedelta(days=2),
                    'decision_reason': 'Approved booking.',
                }
            )
            EventRecord.objects.update_or_create(
                reservation=res,
                defaults={
                    'no_show_recorded_at': e_time + datetime.timedelta(minutes=30),
                    'no_show_recorded_by': admin_user,
                    'no_show_notes': 'Organizer failed to appear and check in by scheduled end time.',
                }
            )

        # Rejected Bookings (2 requests)
        ref_counter += 1
        r_rej1, _ = Reservation.objects.update_or_create(
            reference=f"RES-REJ-{ref_counter}",
            defaults={
                'user': users['clara.reyes'],
                'facility': facilities['AUD-101'],
                'title': 'Unauthorized Commercial Merchandise Pop-Up',
                'purpose': 'Selling private merchandise inside university auditorium.',
                'participant_count': 100,
                'start_time': base_now + datetime.timedelta(days=5, hours=9),
                'end_time': base_now + datetime.timedelta(days=5, hours=12),
                'status': Reservation.STATUS_REJECTED,
                'decision_by': admin_user,
                'decision_at': base_now - datetime.timedelta(days=1),
                'decision_reason': 'Commercial sales without university sponsorship violate campus facility policy Section 4.',
            }
        )

        ref_counter += 1
        r_rej2, _ = Reservation.objects.update_or_create(
            reference=f"RES-REJ-{ref_counter}",
            defaults={
                'user': users['pedro.penduko'],
                'facility': facilities['CONF-105'],
                'title': 'Overcrowded Study Group',
                'purpose': 'Open study session for all freshmen.',
                'participant_count': 85,
                'start_time': base_now + datetime.timedelta(days=7, hours=13),
                'end_time': base_now + datetime.timedelta(days=7, hours=16),
                'status': Reservation.STATUS_REJECTED,
                'decision_by': admin_user,
                'decision_at': base_now - datetime.timedelta(days=1),
                'decision_reason': 'Participant count (85) far exceeds room capacity (25). Please book an auditorium.',
            }
        )

        # Cancelled Bookings (2 requests)
        ref_counter += 1
        Reservation.objects.update_or_create(
            reference=f"RES-CAN-{ref_counter}",
            defaults={
                'user': users['ana.silva'],
                'facility': facilities['AUD-201'],
                'title': 'Debate Rehearsal Practice Session',
                'purpose': 'Practice debate before finals.',
                'participant_count': 30,
                'start_time': base_now + datetime.timedelta(days=8, hours=14),
                'end_time': base_now + datetime.timedelta(days=8, hours=17),
                'status': Reservation.STATUS_CANCELLED,
                'decision_reason': 'Cancelled by organizer due to examination schedule overlap.',
            }
        )

        ref_counter += 1
        Reservation.objects.update_or_create(
            reference=f"RES-CAN-{ref_counter}",
            defaults={
                'user': users['sarah.mendoza'],
                'facility': facilities['CONF-204'],
                'title': 'External Speaker Preliminary Briefing',
                'purpose': 'Speaker cancelled flight.',
                'participant_count': 15,
                'start_time': base_now + datetime.timedelta(days=9, hours=10),
                'end_time': base_now + datetime.timedelta(days=9, hours=12),
                'status': Reservation.STATUS_CANCELLED,
                'decision_reason': 'Admin cancellation: External guest flight cancelled.',
            }
        )

        # Approved Upcoming Bookings (including ADJACENT bookings demonstration!)
        # Day +2 on AUD-101:
        # Adjacent Booking 1: 09:00 - 11:00
        # Adjacent Booking 2: 11:00 - 13:00 (Starts exactly when Booking 1 ends — fully permitted by half-open interval [start, end))
        ref_counter += 1
        adj_date = base_now + datetime.timedelta(days=2)
        r_adj1, _ = Reservation.objects.update_or_create(
            reference=f"RES-ADJ-{ref_counter}",
            defaults={
                'user': users['juan.delacruz'],
                'facility': facilities['AUD-101'],
                'title': 'Civil Engineering Career Forum (Morning Session)',
                'purpose': 'Alumni career forum for graduating batch.',
                'participant_count': 180,
                'start_time': adj_date.replace(hour=9, minute=0, second=0, microsecond=0),
                'end_time': adj_date.replace(hour=11, minute=0, second=0, microsecond=0),
                'status': Reservation.STATUS_APPROVED,
                'decision_by': admin_user,
                'decision_at': base_now - datetime.timedelta(days=1),
                'decision_reason': 'Approved morning interval.',
            }
        )
        EventRecord.objects.get_or_create(reservation=r_adj1)

        ref_counter += 1
        r_adj2, _ = Reservation.objects.update_or_create(
            reference=f"RES-ADJ-{ref_counter}",
            defaults={
                'user': users['maria.santos'],
                'facility': facilities['AUD-101'],
                'title': 'Women in Tech Leadership Talk (Midday Session)',
                'purpose': 'Panel discussion on female engineering leadership.',
                'participant_count': 160,
                'start_time': adj_date.replace(hour=11, minute=0, second=0, microsecond=0), # ADJACENT!
                'end_time': adj_date.replace(hour=13, minute=0, second=0, microsecond=0),
                'status': Reservation.STATUS_APPROVED,
                'decision_by': admin_user,
                'decision_at': base_now - datetime.timedelta(days=1),
                'decision_reason': 'Adjacent booking confirmed - no overlap detected.',
            }
        )
        EventRecord.objects.get_or_create(reservation=r_adj2)

        # More Approved Upcoming Bookings
        more_approved = [
            ('clara.reyes', 'HALL-A', 'Annual Campus Startup Expo', 'Exhibition of student business ventures', 150, 4, 10, 14),
            ('mark.bautista', 'LAB-301', 'Autonomous Drone Programming Bootcamp', 'Coding flight paths in simulation', 35, 6, 13, 16),
            ('ana.silva', 'CONF-105', 'University Model UN Delegate Training', 'Training for international simulation', 20, 7, 9, 12),
            ('elena.torres', 'AUD-201', 'Architectural Documentary Screening', 'Screening of heritage preservation film', 80, 8, 14, 17),
        ]
        for u_name, f_code, title, purp, pax, day_offset, start_h, end_h in more_approved:
            ref_counter += 1
            s_time = (base_now + datetime.timedelta(days=day_offset)).replace(hour=start_h, minute=0, second=0, microsecond=0)
            e_time = s_time.replace(hour=end_h, minute=0)
            r_app, _ = Reservation.objects.update_or_create(
                reference=f"RES-APP-{ref_counter}",
                defaults={
                    'user': users[u_name],
                    'facility': facilities[f_code],
                    'title': title,
                    'purpose': purp,
                    'participant_count': pax,
                    'start_time': s_time,
                    'end_time': e_time,
                    'status': Reservation.STATUS_APPROVED,
                    'decision_by': admin_user,
                    'decision_at': base_now,
                    'decision_reason': 'Approved by administration.',
                }
            )
            EventRecord.objects.get_or_create(reservation=r_app)

        # Pending Requests Awaiting Admin Review (5 requests)
        pending_requests = [
            ('sarah.mendoza', 'AUD-101', 'Student Council General Townhall', 'Open forum on campus welfare and student rights', 250, 5, 14, 17),
            ('pedro.penduko', 'AUD-201', 'Campus Acoustic Songwriting Night', 'Student musical performances and acoustic sets', 90, 6, 17, 20),
            ('gabriel.cruz', 'LAB-302', 'Python Data Visualization Workshop', 'Faculty-led student training on Pandas and Matplotlib', 38, 7, 10, 13),
            ('maria.santos', 'CONF-204', 'Google Developer Group Core Meeting', 'Planning campus hackathon timeline and judging criteria', 22, 8, 15, 18),
            ('juan.delacruz', 'HALL-A', 'Inter-Department Chess Olympiad', 'Annual speed chess tournament for campus clubs', 70, 9, 9, 13),
        ]
        for u_name, f_code, title, purp, pax, day_offset, start_h, end_h in pending_requests:
            ref_counter += 1
            s_time = (base_now + datetime.timedelta(days=day_offset)).replace(hour=start_h, minute=0, second=0, microsecond=0)
            e_time = s_time.replace(hour=end_h, minute=0)
            Reservation.objects.update_or_create(
                reference=f"RES-PEND-{ref_counter}",
                defaults={
                    'user': users[u_name],
                    'facility': facilities[f_code],
                    'title': title,
                    'purpose': purp,
                    'participant_count': pax,
                    'start_time': s_time,
                    'end_time': e_time,
                    'status': Reservation.STATUS_PENDING,
                }
            )

        # 9. Audit Logs Initial Seed Entries
        AuditLog.objects.get_or_create(
            action='SETTINGS_UPDATED',
            target_reference='Booking Limits',
            defaults={
                'actor': admin_user,
                'details': 'Configured default limits: Max duration = 4 hrs, Max advance = 30 days',
                'ip_address': '127.0.0.1'
            }
        )
        AuditLog.objects.get_or_create(
            action='FACILITY_CREATED',
            target_reference='AUD-101',
            defaults={
                'actor': admin_user,
                'target_type': 'Facility',
                'details': 'Facility AUD-101 created with capacity 350',
                'ip_address': '127.0.0.1'
            }
        )

        total_cats = FacilityCategory.objects.count()
        total_facs = Facility.objects.count()
        total_amenities = Amenity.objects.count()
        total_users = User.objects.count()
        total_res = Reservation.objects.count()
        total_closures = ClosureBlock.objects.count()
        total_events = EventRecord.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded database:\n"
            f"- {total_cats} Facility Categories\n"
            f"- {total_facs} Facilities\n"
            f"- {total_amenities} Amenities\n"
            f"- {total_users} Users (1 Admin, {total_users - 1} Basic Users)\n"
            f"- {total_res} Reservations (Pending, Approved, Rejected, Cancelled, Completed, No Show, Adjacent)\n"
            f"- {total_closures} Closure Blocks\n"
            f"- {total_events} Event Records"
        ))
