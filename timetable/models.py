import datetime
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError



def default_working_days():
    return [0, 1, 2, 3, 4]

def validate_working_days(value):
    """Ensures working_days contains a valid list of integer day indices (0-6)."""
    if not isinstance(value, list) or not value:
        raise ValidationError("Working days must be a non-empty list of day numbers.")
    if not all(isinstance(day, int) and 0 <= day <= 6 for day in value):
        raise ValidationError("Working days must only contain integers from 0 (Monday) to 6 (Sunday).")
    if len(value) != len(set(value)):
        raise ValidationError("Working days cannot contain duplicate entries.")


class TimetableSettings(models.Model):
    """
    Stores core timetable rules and constraints for scheduling generation.
    """
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    name = models.CharField(
        max_length=100,
        default="Main Timetable",
        help_text="Name of this timetable configuration."
    )
    start_time = models.TimeField(
        default=datetime.time(7, 30),
        help_text="Time when the first teaching period starts."
    )
    period_duration = models.PositiveIntegerField(
        default=40,
        validators=[MinValueValidator(20), MaxValueValidator(120)],
        help_text="Length of a standard teaching period in minutes."
    )
    periods_per_day = models.PositiveIntegerField(
        default=8,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Maximum number of teaching periods per day."
    )
    working_days = models.JSONField(
        default=default_working_days,
        validators=[validate_working_days],
        help_text="List of teaching days (0=Monday ... 6=Sunday)."
    )
    default_max_teacher_periods_per_day = models.PositiveIntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text="Default max teaching periods for a teacher per day."
    )
    default_max_consecutive_periods = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Default max consecutive periods a teacher can teach."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates if this setting configuration is currently active."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Timetable Setting"
        verbose_name_plural = "Timetable Settings"

    def clean(self):
        super().clean()
        # Enforce logical relations between period limits
        if self.default_max_teacher_periods_per_day > self.periods_per_day:
            raise ValidationError({
                'default_max_teacher_periods_per_day': (
                    "Max teacher periods per day cannot exceed total periods per day."
                )
            })

        if self.default_max_consecutive_periods > self.periods_per_day:
            raise ValidationError({
                'default_max_consecutive_periods': (
                    "Max consecutive periods cannot exceed total periods per day."
                )
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        # Automatically deactivate other settings if this one is activated
        if self.is_active:
            TimetableSettings.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({'Active' if self.is_active else 'Inactive'})"




class TimetableBreak(models.Model):
    """
    Defines non-teaching intervals (e.g., Break, Lunch, Assembly).
    """
    settings = models.ForeignKey(
        TimetableSettings,
        on_delete=models.CASCADE,
        related_name="breaks"
    )
    name = models.CharField(
        max_length=50,
        help_text="e.g., Tea Break, Lunch, Assembly"
    )
    after_period = models.PositiveIntegerField(
        help_text="Period number after which this break occurs (e.g., after period 3)."
    )
    duration = models.PositiveIntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(120)],
        help_text="Duration of break in minutes."
    )

    class Meta:
        ordering = ['after_period']
        unique_together = ('settings', 'after_period')

    def __str__(self):
        return f"{self.name} ({self.duration} mins after Period {self.after_period})"



class TimetableRoom(models.Model):
    """
    Represents physical teaching spaces and specialized facilities.
    """
    class RoomType(models.TextChoices):
        CLASSROOM = "CLASSROOM", "General Classroom"
        LABORATORY = "LABORATORY", "Science Laboratory"
        COMPUTER_LAB = "COMPUTER_LAB", "Computer Lab"
        WORKSHOP = "WORKSHOP", "Technical Workshop"
        HALL = "HALL", "Main Hall / Auditorium"
        SPORTS = "SPORTS", "Sports Field / Gym"
        OTHER = "OTHER", "Other Special Facility"

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Full room name, e.g., 'Science Laboratory 1'."
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short code for timetable grid display, e.g., 'LAB-1'."
    )
    room_type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
        default=RoomType.CLASSROOM,
        db_index=True,
        help_text="Category used for subject room allocation rules."
    )
    building = models.CharField(
        max_length=100,
        blank=True,
        help_text="Building or block location, e.g., 'Science Wing'."
    )
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Maximum student seating capacity."
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Controls room availability for auto-scheduling."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Timetable Room"
        verbose_name_plural = "Timetable Rooms"
        ordering = ["room_type", "name"]

    def clean(self):
        super().clean()
        if self.code:
            self.code = self.code.upper().strip()

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name




from django.db import models
from django.core.validators import MinValueValidator
# from .models import TimetableRoom  # From your timetable app
#

class SubjectRoomRequirement(models.Model):
    """
    Defines room rules for a Subject or specific TeachingAssignment.
    Cross-app reference to your existing models.
    """
    # Link to existing Subject in schools_manager app
    subject = models.OneToOneField(
        'students_app.Subject',
        on_delete=models.CASCADE,
        related_name='room_requirement',
        help_text="The subject that requires a specific room type."
    )
    required_room_type = models.CharField(
        max_length=20,
        choices=TimetableRoom.RoomType.choices,
        default=TimetableRoom.RoomType.CLASSROOM,
        help_text="Minimum room type needed for this subject."
    )
    specific_room = models.ForeignKey(
        TimetableRoom,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Optional override to force a specific room."
    )

    def __str__(self):
        return f"{self.subject.name} -> {self.specific_room or self.required_room_type}"


from django.db import models
from django.core.validators import MinValueValidator

class SubjectConstraint(models.Model):
    """
    Stores scheduling rules per Subject (e.g., 5 periods/week, max 2 double periods).
    """
    # Changed from 'assignment' to 'subject'
    subject = models.OneToOneField(
        'students_app.Subject',  # Pointing directly to your Subject model
        on_delete=models.CASCADE,
        related_name='timetable_constraint'
    )
    periods_per_week = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Total teaching periods allocated per week for this subject."
    )
    double_periods_per_week = models.PositiveIntegerField(
        default=0,
        help_text="How many double periods should this subject have per week? (e.g., 2 for Mathematics)"
    )
    allow_double_periods = models.BooleanField(
        default=True,
        help_text="Whether consecutive periods (double periods) are allowed."
    )

    def __str__(self):
        return f"{self.subject} ({self.periods_per_week} periods/week)"



from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q


class Timetable(models.Model):
    """
    Represents one complete timetable version for the school.
    """

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    name = models.CharField(
        max_length=100,
        help_text="Name of this timetable, e.g., '2026 Term 1 Main'."
    )
    academic_year = models.PositiveIntegerField(
        help_text="Academic year this timetable belongs to (e.g., 2026)."
    )
    term = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="Term number: 1, 2, or 3."
    )
    settings = models.ForeignKey(
        'TimetableSettings',
        on_delete=models.PROTECT,
        related_name="timetables",
        help_text="Timetable rules and periods used to generate this version."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Draft (editing), Published (visible), or Archived (historical)."
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Designates if this is the currently running timetable for the school."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Timetable"
        verbose_name_plural = "Timetables"
        ordering = ["-academic_year", "-term", "-created_at"]
        constraints = [
            # Prevent duplicate names in the same term/year
            models.UniqueConstraint(
                fields=['name', 'academic_year', 'term'],
                name='unique_timetable_version'
            ),
            # Enforce that only ONE timetable can be active at a time
            models.UniqueConstraint(
                fields=['is_active'],
                condition=Q(is_active=True),
                name='unique_active_timetable'
            )
        ]

    def clean(self):
        super().clean()
        # Ensure a Draft or Archived timetable cannot be made active
        if self.is_active and self.status != self.Status.PUBLISHED:
            raise ValidationError({
                'is_active': "Only a 'Published' timetable can be marked as active."
            })

    def save(self, *args, **kwargs):
        self.full_clean()

        # If this one is being activated, deactivate all others
        if self.is_active:
            Timetable.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)

        super().save(*args, **kwargs)

    def __str__(self):
        status_flag = " (ACTIVE)" if self.is_active else f" ({self.get_status_display()})"
        return f"{self.name} - {self.academic_year} T{self.term}{status_flag}"



from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q


class TimetableEntry(models.Model):
    """
    Represents an allocated slot (class, teacher, room, day, period)
    for a specific timetable version, directly linked to a Subject.
    """
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    timetable = models.ForeignKey(
        'timetable.Timetable',
        on_delete=models.CASCADE,
        related_name='entries',
        help_text="The specific timetable version this slot belongs to."
    )

    # Directly linked to Subject (adjust 'students.Subject' app name if different)
    subject = models.ForeignKey(
        'students_app.Subject',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='timetable_entries',
        help_text="The subject instance containing the teacher and target class."
    )

    room = models.ForeignKey(
        'timetable.TimetableRoom',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timetable_entries',
        help_text="The physical room or laboratory assigned for this period slot."
    )

    day = models.IntegerField(
        choices=DayOfWeek.choices,
        db_index=True,
        help_text="Day of the week."
    )

    period_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        db_index=True,
        help_text="Period index (1 for Period 1, 2 for Period 2, etc.)."
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Controls entry activation state."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Timetable Entry"
        verbose_name_plural = "Timetable Entries"
        ordering = ['timetable', 'day', 'period_number']
        constraints = [
            # Database-level constraint: Prevent room double-booking within the same timetable
            models.UniqueConstraint(
                fields=['timetable', 'room', 'day', 'period_number'],
                condition=Q(room__isnull=False),
                name='unique_room_slot_per_timetable'
            ),
        ]

    def clean(self):
        super().clean()

        # Guard clause: Ensure parent relationships exist before validating
        if not hasattr(self, 'timetable') or not hasattr(self, 'subject'):
            return

        settings = self.timetable.settings

        # 1. Configuration Validation: Check max periods
        if settings and self.period_number > settings.periods_per_day:
            raise ValidationError({
                'period_number': f"Period {self.period_number} exceeds maximum allowed periods ({settings.periods_per_day}) in timetable settings."
            })

        # 2. Configuration Validation: Check valid working days
        if settings and settings.working_days and self.day not in settings.working_days:
            raise ValidationError({
                'day': f"{self.get_day_display()} is not set as a working day in active timetable settings."
            })

        # --- NEW: Check Blocked Slots ---
        if settings:
            blocked = settings.blocked_slots.filter(day=self.day, period_number=self.period_number).first()
            if blocked:
                raise ValidationError(
                    f"{self.get_day_display()} Period {self.period_number} is globally blocked for: {blocked.label}"
                )

        # Base queryset scoped strictly to the current timetable version and time slot.
        sibling_entries = self.__class__.objects.filter(
            timetable=self.timetable,
            day=self.day,
            period_number=self.period_number
        ).exclude(pk=self.pk)

        # 3. Teacher Checks
        if self.subject and self.subject.teacher_subject:
            teacher = self.subject.teacher_subject

            # --- NEW: Check Teacher Unavailability (Whole Day) ---
            from .models import TeacherUnavailability  # Import locally to avoid circular issues
            if TeacherUnavailability.objects.filter(teacher=teacher, day=self.day, period_number__isnull=True).exists():
                raise ValidationError(
                    f"Teacher '{teacher}' is marked as unavailable for the entire day on {self.get_day_display()}."
                )

            # --- NEW: Check Teacher Unavailability (Specific Period) ---
            if TeacherUnavailability.objects.filter(teacher=teacher, day=self.day,
                                                    period_number=self.period_number).exists():
                raise ValidationError(
                    f"Teacher '{teacher}' is marked as unavailable on {self.get_day_display()}, Period {self.period_number}."
                )

            # Clash Validation: Teacher double-booking
            if sibling_entries.filter(subject__teacher_subject=teacher).exists():
                raise ValidationError(
                    f"Teacher '{teacher}' is already assigned to another class on {self.get_day_display()}, Period {self.period_number}."
                )

        # 4. Clash Validation: Class Level double-booking (Cohort scheduling)
        if self.subject and self.subject.target_class:
            target_class = self.subject.target_class
            if sibling_entries.filter(subject__target_class=target_class).exists():
                raise ValidationError(
                    f"Class '{target_class}' already has a lesson scheduled on {self.get_day_display()}, Period {self.period_number}."
                )

        # 5. Clash Validation: Room double-booking
        if self.room_id:
            if sibling_entries.filter(room=self.room).exists():
                raise ValidationError({
                    'room': f"Room '{self.room}' is already occupied during {self.get_day_display()}, Period {self.period_number}."
                })



from django.conf import settings # Add this at the top if not already there

class BlockedSlot(models.Model):
    """
    Defines specific periods in the week where NO teaching should be scheduled
    (e.g., Friday Period 8 for general cleaning or clubs).
    """
    settings = models.ForeignKey(
        'TimetableSettings',
        on_delete=models.CASCADE,
        related_name="blocked_slots"
    )
    day = models.IntegerField(
        choices=TimetableSettings.DayOfWeek.choices,
        help_text="Day of the week."
    )
    period_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Period index to block (e.g., 8 for Period 8)."
    )
    label = models.CharField(
        max_length=50,
        help_text="Reason for blocking, e.g., 'Clubs', 'Assembly'"
    )

    class Meta:
        ordering = ['day', 'period_number']
        unique_together = ('settings', 'day', 'period_number')

    def __str__(self):
        return f"{self.get_day_display()} P{self.period_number} Blocked: {self.label}"


class TeacherUnavailability(models.Model):
    """
    Defines when a specific teacher cannot be scheduled.
    If period_number is null, it means they are unavailable for the entire day.
    """
    # Adjust 'settings.AUTH_USER_MODEL' if your teacher is a different specific model (like 'users.Teacher')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='unavailabilities',
        help_text="The teacher who is unavailable."
    )
    day = models.IntegerField(
        choices=TimetableSettings.DayOfWeek.choices,
        help_text="Day of the week."
    )
    period_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Leave blank to mark the whole day as unavailable. Otherwise, specify the period number."
    )
    reason = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g., 'Part-time off', 'Admin duties'"
    )

    class Meta:
        verbose_name_plural = "Teacher Unavailabilities"
        # Prevent duplicating the exact same constraint
        unique_together = ('teacher', 'day', 'period_number')

    def __str__(self):
        period_str = f"Period {self.period_number}" if self.period_number else "All Day"
        return f"{self.teacher} unavailable on {self.get_day_display()} ({period_str})"