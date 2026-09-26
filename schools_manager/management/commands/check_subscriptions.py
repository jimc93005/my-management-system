import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django_tenants.utils import schema_context
from schools_manager.models import School
from schools_manager.emails import send_billing_warning_email, send_suspension_email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Checks tenant subscription statuses, suspends expired accounts, and sends billing reminders.'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()

        # Only check active schools, skip the master public schema
        active_schools = School.objects.exclude(schema_name='public').filter(status='Active')

        processed_count = 0
        suspended_count = 0

        for school in active_schools:
            if not school.subscription_end_date:
                continue

            end_date = school.subscription_end_date.date()
            days_left = (end_date - today).days

            try:
                # 7-Day Warning
                if days_left == 7:
                    send_billing_warning_email(school, days_left)
                    self.stdout.write(self.style.NOTICE(f"Sent 7-day warning to {school.name}"))

                # 1-Day Warning
                elif days_left == 1:
                    send_billing_warning_email(school, days_left)
                    self.stdout.write(self.style.WARNING(f"Sent 1-day warning to {school.name}"))

                # Lockout Execution (If end date is in the past)
                elif days_left < 0:
                    with schema_context('public'):
                        school.status = 'Suspended'
                        school.save(update_fields=['status'])

                    send_suspension_email(school)
                    suspended_count += 1
                    self.stdout.write(self.style.ERROR(f"SUSPENDED {school.name} - Expired {abs(days_left)} days ago"))

                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing subscription for {school.name}: {e}")
                self.stdout.write(self.style.ERROR(f"Failed processing {school.name}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"Cron complete. Processed {processed_count} schools. Suspended {suspended_count} schools."))