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

        # 2. Users (Exactly 1 Admin, 11 Basic Users)
        # Admin Account (Strictly 1 Admin - No others added)
        admin_user, _ = User.objects.update_or_create(
            username='glenardsteevenrmayor',
            defaults={
                'email': 'glenardsteevenrmayor@gmail.com',
                'first_name': 'Glenard Steeven',
                'last_name': 'Mayor',
                'role': User.ROLE_ADMIN,
                'department': 'Physical Facilities and Logistics Management Office (PFLMO)',
                'student_or_employee_id': 'EMP-2022-0001',
                'phone_number': '+63 919 555 6677',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        admin_user.set_password('Password123!')
        admin_user.save()

        # Basic Users: Primary demo accounts + fictional student accounts (Part 4 requires >= 8 basic users)
        basic_user_data = [
            ('glenardmayor', 'glenardmayor@gmail.com', 'Glenard', 'Mayor', 'College of Information and Communications Technology (CICT)', '2024-101001', '+63 917 111 2233'),
            ('steevenrural', 'steevenrural@gmail.com', 'Steeven', 'Rural', 'College of Engineering (COE)', '2024-102002', '+63 918 333 4455'),
            ('juan.delacruz', 'juan.delacruz@bulsu.edu.ph', 'Juan', 'Dela Cruz', 'College of Engineering (COE)', '2024-100001', '+63 917 111 2201'),
            ('maria.santos', 'maria.santos@bulsu.edu.ph', 'Maria', 'Santos', 'College of Information and Communications Technology (CICT)', '2024-100002', '+63 917 111 2202'),
            ('clara.reyes', 'clara.reyes@bulsu.edu.ph', 'Clara', 'Reyes', 'College of Industrial Technology (CIT)', '2024-100003', '+63 917 111 2203'),
            ('pedro.penduko', 'pedro.penduko@bulsu.edu.ph', 'Pedro', 'Penduko', 'College of Education (COED)', '2024-100004', '+63 917 111 2204'),
            ('ana.silva', 'ana.silva@bulsu.edu.ph', 'Ana', 'Silva', 'College of Science (CS)', '2024-100005', '+63 917 111 2205'),
            ('mark.bautista', 'mark.bautista@bulsu.edu.ph', 'Mark', 'Bautista', 'College of Architecture and Fine Arts (CAFA)', '2024-100006', '+63 917 111 2206'),
            ('elena.torres', 'elena.torres@bulsu.edu.ph', 'Elena', 'Torres', 'College of Arts and Letters (CAL)', '2024-100007', '+63 917 111 2207'),
            ('gabriel.cruz', 'gabriel.cruz@bulsu.edu.ph', 'Gabriel', 'Cruz', 'College of Business Administration (CBA)', '2024-100008', '+63 917 111 2208'),
            ('sarah.mendoza', 'sarah.mendoza@bulsu.edu.ph', 'Sarah', 'Mendoza', 'College of Nursing (CON)', '2024-100009', '+63 917 111 2209'),
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
                    'is_staff': False,
                    'is_superuser': False,
                }
            )
            u.set_password('Password123!')
            u.save()
            users[username] = u

        users['admin'] = admin_user

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

        # 5. Facilities (10 authentic BulSU facilities)
        facility_data = [
            ('VAL-GYM', 'Valencia Hall (University Gymnasium)', 'Multipurpose Halls & Open Spaces', 'BulSU Main Campus - Gate 1 Athletic Grounds', 2500,
             'Premier indoor sports stadium and university assembly arena for commencements, UAAP/SCUAA athletic meets, major convocations, concerts, and general assemblies.',
             datetime.time(7, 0), datetime.time(21, 0),
             '/static/img/facilities/val-gym.jpg'),
            ('FED-AVR', 'Federizo Hall Audio-Visual Theater', 'Auditoriums & Theaters', 'Federizo Hall - 2nd Floor', 180,
             'Historic tiered academic theater equipped with acoustic paneling, theatrical lighting, and multimedia projection for collegiate symposiums, cultural presentations, and film screenings.',
             datetime.time(8, 0), datetime.time(19, 0),
             '/static/img/facilities/fed-avr.jpg'),
            ('ELIB-CONF', 'BulSU E-Library Multimedia Conference Center', 'Conference & Meeting Rooms', 'University E-Library Building - 4th Floor', 120,
             'State-of-the-art multimedia conference hall inside the university premier learning resource center, featuring interactive whiteboards, video teleconferencing, and acoustic zoning for research colloquiums.',
             datetime.time(8, 0), datetime.time(18, 0),
             '/static/img/facilities/elib-conf.jpg'),
            ('CICT-LAB1', 'CICT Advanced Computer & Software Lab 1', 'Laboratories & Technical Rooms', 'College of Information and Communications Technology - 3rd Floor', 50,
             'High-specification computing laboratory equipped with dual-display development workstations, Gigabit LAN networking, Cisco switching racks, and modern development software suites.',
             datetime.time(8, 0), datetime.time(18, 0),
             '/static/img/facilities/cict-lab1.jpg'),
            ('NAT-AMP', 'Natividad Hall Engineering Amphitheater', 'Auditoriums & Theaters', 'Natividad Hall - College of Engineering 3rd Floor', 220,
             'Tiered collegiate amphitheater designed for technical engineering symposiums, capstone project exhibits, robotics demonstrations, and inter-collegiate academic competitions.',
             datetime.time(8, 0), datetime.time(19, 0),
             '/static/img/facilities/nat-amp.jpg'),
            ('ALV-HALL', 'Alvarado Hall Multi-Purpose Function Hall', 'Multipurpose Halls & Open Spaces', 'Alvarado Hall - College of Industrial Technology 1st Floor', 300,
             'Expansive multi-purpose hall accommodating industrial technology expos, vocational trade exhibitions, student seminars, skills demonstrations, and departmental assemblies.',
             datetime.time(8, 0), datetime.time(20, 0),
             '/static/img/facilities/alv-hall.jpg'),
            ('ROX-AVR', 'Roxas Hall Audio-Visual Presentation Hall', 'Auditoriums & Theaters', 'Roxas Hall - College of Education 2nd Floor', 140,
             'Specialized presentation theater tailored for teacher education demonstrations, demonstration-teaching evaluations, academic workshops, and pedagogical colloquiums.',
             datetime.time(8, 0), datetime.time(18, 0),
             '/static/img/facilities/rox-avr.jpg'),
            ('SAC-HALL', 'Student Activity Center (SAC) Grand Hall', 'Multipurpose Halls & Open Spaces', 'Student Activity Center Building - 2nd Floor', 350,
             'Central vibrant hub for accredited student organizations, Supreme Student Council (SSC) summits, leadership training, socio-cultural rehearsals, and student welfare activities.',
             datetime.time(8, 0), datetime.time(20, 0),
             '/static/img/facilities/sac-hall.jpg'),
            ('HOST-FUNC', 'BulSU University Hostel Grand Ballroom', 'Conference & Meeting Rooms', 'BulSU University Hostel & Training Center - 2nd Floor', 160,
             'Elegant banquet and conference ballroom managed under hospitality training standards, ideal for institutional banquets, dignitary receptions, accreditation dinners, and executive conferences.',
             datetime.time(8, 0), datetime.time(22, 0),
             '/static/img/facilities/host-func.jpg'),
            ('FLR-CONF', 'Flores Hall Executive Boardroom', 'Conference & Meeting Rooms', 'Flores Hall (Administration Building) - 4th Floor Executive Wing', 40,
             'Premier executive council chamber featuring ergonomic leather seating, integrated table-top microphone arrays, dual telepresence monitors, and secure board-meeting accommodations.',
             datetime.time(8, 0), datetime.time(18, 0),
             '/static/img/facilities/flr-conf.jpg'),
        ]
        facilities = {}
        for fcode, fname, fcat, floc, fcap, fdesc, open_t, close_t, img_url in facility_data:
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
                    'custom_image_url': img_url,
                    'is_active': True,
                }
            )
            facilities[fcode] = fac

        # Backward compatibility aliases for historical seed fixtures
        facilities['AUD-101'] = facilities['VAL-GYM']
        facilities['AUD-201'] = facilities['FED-AVR']
        facilities['LAB-301'] = facilities['CICT-LAB1']
        facilities['LAB-302'] = facilities['NAT-AMP']
        facilities['CONF-105'] = facilities['FLR-CONF']
        facilities['CONF-204'] = facilities['ELIB-CONF']
        facilities['HALL-A'] = facilities['ALV-HALL']

        # Assign amenities to facilities
        associations = [
            ('VAL-GYM', ['Surround Audio PA System', 'Wireless Microphones', 'High-Speed Dedicated Wi-Fi', 'Podium & Lectern']),
            ('FED-AVR', ['HD Laser Projector', 'Surround Audio PA System', 'Wireless Microphones', 'Podium & Lectern']),
            ('ELIB-CONF', ['Video Conferencing Suite', 'Interactive Smart Board', 'High-Speed Dedicated Wi-Fi', 'HD Laser Projector']),
            ('CICT-LAB1', ['Modular Workstations', 'High-Speed Dedicated Wi-Fi', 'Interactive Smart Board', 'HD Laser Projector']),
            ('NAT-AMP', ['HD Laser Projector', 'Wireless Microphones', 'Interactive Smart Board', 'Podium & Lectern']),
            ('ALV-HALL', ['HD Laser Projector', 'Wireless Microphones', 'Surround Audio PA System', 'Modular Workstations']),
            ('ROX-AVR', ['HD Laser Projector', 'Wireless Microphones', 'Surround Audio PA System', 'Podium & Lectern']),
            ('SAC-HALL', ['Surround Audio PA System', 'Wireless Microphones', 'High-Speed Dedicated Wi-Fi', 'Modular Workstations']),
            ('HOST-FUNC', ['HD Laser Projector', 'Video Conferencing Suite', 'Wireless Microphones', 'Surround Audio PA System']),
            ('FLR-CONF', ['Video Conferencing Suite', 'Interactive Smart Board', 'High-Speed Dedicated Wi-Fi', 'Podium & Lectern']),
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

        # 6. Operating Hours per weekday for all facilities
        for fac in facilities.values():
            for day in range(6): # Mon-Sat
                FacilityOperatingHour.objects.update_or_create(
                    facility=fac,
                    day_of_week=day,
                    defaults={'open_time': fac.default_open_time, 'close_time': fac.default_close_time, 'is_closed': False}
                )
            FacilityOperatingHour.objects.update_or_create(
                facility=fac,
                day_of_week=6, # Sunday closed
                defaults={'open_time': fac.default_open_time, 'close_time': fac.default_close_time, 'is_closed': True}
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
            ('glenardmayor', 'VAL-GYM', 'CICT Collegiate Assembly & Tech Summit', 'Annual gathering of CICT students and computing faculty', 350, 3, 13, 17),
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

        # Pending Requests Awaiting Admin Review (6 requests)
        pending_requests = [
            ('steevenrural', 'NAT-AMP', 'COE Engineering Robotics Colloquium', 'Presentation of robotic designs and capstone projects', 120, 4, 9, 13),
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
