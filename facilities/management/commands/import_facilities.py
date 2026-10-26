import csv
import datetime
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from facilities.models import Facility, FacilityCategory, Amenity, FacilityAmenity, FacilityOperatingHour


class Command(BaseCommand):
    help = "Import facilities from a CSV file into the BulSU CARES database."

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            nargs='?',
            default='facilities_template.csv',
            help='Path to the facilities CSV file (defaults to facilities_template.csv in project root)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Deactivate existing facilities before importing new ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate the CSV without saving changes to the database'
        )

    def parse_time(self, time_str, default_time):
        if not time_str or not time_str.strip():
            return default_time
        time_str = time_str.strip()
        for fmt in ('%H:%M', '%H:%M:%S', '%I:%M %p', '%I:%M%p'):
            try:
                return datetime.datetime.strptime(time_str, fmt).time()
            except ValueError:
                pass
        return default_time

    def parse_bool(self, val_str, default=True):
        if val_str is None or val_str.strip() == '':
            return default
        return str(val_str).strip().lower() in ('true', '1', 'yes', 'y', 'active')

    def handle(self, *args, **options):
        csv_path = options['csv_file']
        dry_run = options['dry_run']
        clear_existing = options['clear']

        if not os.path.exists(csv_path):
            raise CommandError(f"CSV file not found at: {csv_path}")

        self.stdout.write(self.style.NOTICE(f"{'[DRY RUN] ' if dry_run else ''}Reading facilities from: {csv_path}"))

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = [fn.strip().lower() for fn in (reader.fieldnames or [])]

            required_fields = ['code', 'name', 'category']
            missing = [req for req in required_fields if req not in fieldnames]
            if missing:
                raise CommandError(f"Missing required columns in CSV: {', '.join(missing)}")

            rows = list(reader)

        if not rows:
            self.stdout.write(self.style.WARNING("The CSV file is empty. No facilities were imported."))
            return

        with transaction.atomic():
            if clear_existing and not dry_run:
                updated_count = Facility.objects.filter(is_active=True).update(is_active=False)
                self.stdout.write(self.style.WARNING(f"Archived {updated_count} existing active facilities."))

            created_count = 0
            updated_count = 0

            # Default icon lookup for common amenity names
            icon_map = {
                'projector': 'bi-projector',
                'microphone': 'bi-mic',
                'mic': 'bi-mic',
                'wi-fi': 'bi-wifi',
                'wifi': 'bi-wifi',
                'video': 'bi-camera-video',
                'camera': 'bi-camera-video',
                'audio': 'bi-speaker',
                'sound': 'bi-speaker',
                'speaker': 'bi-speaker',
                'pa': 'bi-speaker',
                'board': 'bi-tv',
                'screen': 'bi-tv',
                'smart': 'bi-tv',
                'podium': 'bi-easel',
                'lectern': 'bi-easel',
                'workstation': 'bi-laptop',
                'computer': 'bi-laptop',
                'laptop': 'bi-laptop',
                'ac': 'bi-snow',
                'air': 'bi-snow',
            }

            for idx, raw_row in enumerate(rows, start=1):
                # Clean keys and values
                row = {k.strip().lower(): (v.strip() if v else '') for k, v in raw_row.items() if k}

                code = row.get('code', '').upper()
                name = row.get('name', '')
                cat_name = row.get('category', 'General Facilities')
                location = row.get('location', 'BulSU Campus')
                
                try:
                    capacity = int(row.get('capacity', 50))
                except ValueError:
                    capacity = 50

                description = row.get('description', '')
                image_url = row.get('image_url') or row.get('custom_image_url') or ''
                open_time = self.parse_time(row.get('default_open_time'), datetime.time(8, 0))
                close_time = self.parse_time(row.get('default_close_time'), datetime.time(21, 0))
                is_active = self.parse_bool(row.get('is_active', 'TRUE'))
                amenities_str = row.get('amenities', '')

                if not code or not name:
                    self.stdout.write(self.style.WARNING(f"Row {idx}: Skipping row due to missing code or name."))
                    continue

                if dry_run:
                    self.stdout.write(f"  [VALID] {code} - {name} ({cat_name}) | Cap: {capacity} | {open_time.strftime('%H:%M')}-{close_time.strftime('%H:%M')}")
                    continue

                # Get or create category
                category, _ = FacilityCategory.objects.get_or_create(
                    name=cat_name,
                    defaults={
                        'description': f"University venues categorized under {cat_name}.",
                        'is_active': True,
                    }
                )

                facility, created = Facility.objects.update_or_create(
                    code=code,
                    defaults={
                        'name': name,
                        'category': category,
                        'location': location,
                        'capacity': capacity,
                        'description': description,
                        'default_open_time': open_time,
                        'default_close_time': close_time,
                        'custom_image_url': image_url,
                        'is_active': is_active,
                    }
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                # Configure Operating Hours: Monday to Saturday open, Sunday closed by default
                for weekday in range(6):  # 0 = Monday, 5 = Saturday
                    FacilityOperatingHour.objects.update_or_create(
                        facility=facility,
                        day_of_week=weekday,
                        defaults={
                            'open_time': open_time,
                            'close_time': close_time,
                            'is_closed': False,
                        }
                    )
                # Sunday
                FacilityOperatingHour.objects.update_or_create(
                    facility=facility,
                    day_of_week=6,
                    defaults={
                        'open_time': open_time,
                        'close_time': close_time,
                        'is_closed': True,
                    }
                )

                # Process amenities if provided
                if amenities_str:
                    # Support both semicolon and comma separation
                    separator = ';' if ';' in amenities_str else ','
                    amenity_names = [a.strip() for a in amenities_str.split(separator) if a.strip()]

                    for am_name in amenity_names:
                        # Determine icon from keywords
                        icon = 'bi-check-circle'
                        lower_name = am_name.lower()
                        for key, ic in icon_map.items():
                            if key in lower_name:
                                icon = ic
                                break

                        amenity, _ = Amenity.objects.get_or_create(
                            name=am_name,
                            defaults={
                                'description': f"Available amenity: {am_name}",
                                'icon': icon,
                                'is_active': True,
                            }
                        )

                        FacilityAmenity.objects.get_or_create(
                            facility=facility,
                            amenity=amenity,
                            defaults={'quantity': 1, 'notes': 'Installed in primary setup'}
                        )

            if dry_run:
                self.stdout.write(self.style.SUCCESS(f"Validation complete: {len(rows)} facilities are valid and ready to import."))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully imported facilities! Created: {created_count}, Updated: {updated_count}."
                ))
