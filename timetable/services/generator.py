from django.db import transaction
from timetable.models import Timetable, TimetableEntry, SubjectConstraint, TeacherUnavailability

from django.db import transaction

from django.db import transaction

from django.db import transaction

from django.db import transaction






from collections import defaultdict
from django.db import transaction



@transaction.atomic
def generate_greedy_timetable(timetable_id):
    timetable = Timetable.objects.get(id=timetable_id)
    settings = timetable.settings

    # 1. Clear existing generated entries
    TimetableEntry.objects.filter(timetable=timetable).delete()

    # 2. Fetch constraints
    constraints = list(SubjectConstraint.objects.select_related(
        'subject', 'subject__teacher_subject', 'subject__target_class'
    ).all())

    # --- STRATEGY 1: Prioritize Busiest Teachers ---
    teacher_loads = defaultdict(int)
    for c in constraints:
        if c.subject.teacher_subject:
            teacher_loads[c.subject.teacher_subject.id] += c.periods_per_week

    # Sort by: Busiest Teacher -> Needs Double -> Total Periods
    constraints.sort(key=lambda c: (
        teacher_loads.get(c.subject.teacher_subject.id if c.subject.teacher_subject else 0, 0),
        c.double_periods_per_week,
        c.periods_per_week
    ), reverse=True)

    working_days = list(settings.working_days)
    periods_per_day = settings.periods_per_day
    break_after_periods = list(settings.breaks.values_list('after_period', flat=True))

    # 3. Pre-load Blocked Slots & Teacher Unavailability
    blocked_matrix = {(bs.day, bs.period_number) for bs in settings.blocked_slots.all()}
    unavail_matrix = set()
    for u in TeacherUnavailability.objects.all():
        period_val = u.period_number if u.period_number is not None else 'ALL'
        unavail_matrix.add((u.teacher_id, u.day, period_val))

    placement_tracker = {c.id: c.periods_per_week for c in constraints}
    doubles_tracker = {c.id: c.double_periods_per_week for c in constraints}
    target_classes = list(set(c.subject.target_class for c in constraints if c.subject.target_class))

    def is_free(day_val, period_val, subj, ignore_entry_id=None):
        if (day_val, period_val) in blocked_matrix: return False
        teacher = subj.teacher_subject
        if teacher:
            if (teacher.id, day_val, 'ALL') in unavail_matrix: return False
            if (teacher.id, day_val, period_val) in unavail_matrix: return False

        class_query = TimetableEntry.objects.filter(timetable=timetable, day=day_val, period_number=period_val,
                                                    subject__target_class=subj.target_class)
        teacher_query = TimetableEntry.objects.filter(timetable=timetable, day=day_val, period_number=period_val,
                                                      subject__teacher_subject=teacher) if teacher else None

        if ignore_entry_id:
            class_query = class_query.exclude(id=ignore_entry_id)
            if teacher_query: teacher_query = teacher_query.exclude(id=ignore_entry_id)

        return not (class_query.exists() or (teacher_query and teacher_query.exists()))

    max_attempts = 4
    attempts = 0

    while any(v > 0 for v in placement_tracker.values()) and attempts < max_attempts:
        attempts += 1

        # --- STRATEGY 2: Relax Double Periods on Later Attempts ---
        relax_doubles = (attempts >= 3)

        for period in range(1, periods_per_day + 1):
            rotated_classes = target_classes[(period % len(target_classes)):] + target_classes[
                :(period % len(target_classes))]

            for day in working_days:
                for target_class in rotated_classes:
                    if TimetableEntry.objects.filter(timetable=timetable, day=day, period_number=period,
                                                     subject__target_class=target_class).exists():
                        continue

                    class_constraints = [c for c in constraints if
                                         c.subject.target_class == target_class and placement_tracker[c.id] > 0]
                    placed_this_slot = False

                    # A. ATTEMPT TO PLACE A DOUBLE PERIOD (Skipped if relaxed)
                    if not relax_doubles:
                        for constraint in class_constraints:
                            subject = constraint.subject
                            if TimetableEntry.objects.filter(timetable=timetable, day=day,
                                                             subject=subject).exists(): continue

                            needs_double = doubles_tracker[constraint.id] > 0 and placement_tracker[constraint.id] >= 2

                            if needs_double and period < periods_per_day and period not in break_after_periods:
                                if is_free(day, period, subject) and is_free(day, period + 1, subject):
                                    TimetableEntry.objects.create(timetable=timetable, subject=subject, day=day,
                                                                  period_number=period)
                                    TimetableEntry.objects.create(timetable=timetable, subject=subject, day=day,
                                                                  period_number=period + 1)
                                    placement_tracker[constraint.id] -= 2
                                    doubles_tracker[constraint.id] -= 1
                                    placed_this_slot = True
                                    break

                    if placed_this_slot: continue

                    # B. FALLBACK TO SINGLE PERIOD
                    for constraint in class_constraints:
                        subject = constraint.subject

                        # Soft day limit: Allow 2 of the same subject per day ONLY on final attempt
                        same_day_count = TimetableEntry.objects.filter(timetable=timetable, day=day,
                                                                       subject=subject).count()
                        if same_day_count >= (2 if attempts == max_attempts else 1):
                            continue

                        # If we aren't relaxing doubles yet, preserve them
                        if not relax_doubles and doubles_tracker[constraint.id] > 0 and placement_tracker[
                            constraint.id] >= 2:
                            continue

                        if is_free(day, period, subject):
                            TimetableEntry.objects.create(timetable=timetable, subject=subject, day=day,
                                                          period_number=period)
                            placement_tracker[constraint.id] -= 1

                            # Deduct from doubles tracker if we were forced to split it
                            if relax_doubles and doubles_tracker[constraint.id] > 0:
                                doubles_tracker[constraint.id] -= 1

                            placed_this_slot = True
                            break

    # 4. Fill remaining odd gaps, then compress everything to the left
    fill_remaining_gaps(timetable, target_classes, placement_tracker, constraints, working_days, periods_per_day,
                        is_free)
    compact_timetable(timetable, target_classes, working_days, periods_per_day, is_free)

    return "Generation Complete"


def compact_timetable(timetable, target_classes, working_days, periods_per_day, is_free):
    """
    Applies 'gravity' to the timetable, pulling lessons as early in the day as
    possible to eliminate isolated mid-morning gaps.
    """
    compaction_made = True
    passes = 0

    # Loop until no more movements can be made (max 3 passes for safety)
    while compaction_made and passes < 3:
        compaction_made = False
        passes += 1

        for day in working_days:
            for target_class in target_classes:

                # Scan periods from left (morning) to right (afternoon)
                for empty_period in range(1, periods_per_day):

                    is_empty = not TimetableEntry.objects.filter(
                        timetable=timetable, day=day, period_number=empty_period, subject__target_class=target_class
                    ).exists()

                    if is_empty:
                        # Find the first lesson later in the day to pull forward
                        for later_period in range(empty_period + 1, periods_per_day + 1):
                            entry_to_move = TimetableEntry.objects.filter(
                                timetable=timetable, day=day, period_number=later_period,
                                subject__target_class=target_class
                            ).first()

                            if entry_to_move:
                                # Ensure moving this lesson doesn't create a teacher clash at the new time
                                if is_free(day, empty_period, entry_to_move.subject, ignore_entry_id=entry_to_move.id):
                                    # Shift the lesson
                                    entry_to_move.period_number = empty_period
                                    entry_to_move.save()
                                    compaction_made = True
                                    break  # Gap filled, move to the next empty_period slot




def fill_remaining_gaps(timetable, target_classes, placement_tracker, constraints, working_days, periods_per_day, is_free):
    filled_count = 0

    # --- FIX: Loop Periods FIRST to patch morning gaps ---
    for period in range(1, periods_per_day + 1):
        for day in working_days:
            for target_class in target_classes:

                already_filled = TimetableEntry.objects.filter(
                    timetable=timetable, day=day, period_number=period,
                    subject__target_class=target_class
                ).exists()
                if already_filled:
                    continue

                candidates = [
                    c for c in constraints
                    if c.subject.target_class == target_class and placement_tracker[c.id] > 0
                ]

                for constraint in candidates:
                    subject = constraint.subject

                    # Allow a second single period on the same day as a last resort
                    same_day_count = TimetableEntry.objects.filter(
                        timetable=timetable, day=day, subject=subject
                    ).count()
                    if same_day_count >= 2:
                        continue

                    if is_free(day, period, subject):
                        TimetableEntry.objects.create(
                            timetable=timetable, subject=subject, day=day,
                            period_number=period, room=None
                        )
                        placement_tracker[constraint.id] -= 1
                        filled_count += 1
                        break

    return filled_count





from datetime import datetime as dt, timedelta
from timetable.models import TimetableEntry
from students_app.models import SchoolProfile, ClassLevel

def generate_class_timetable_matrix(timetable, class_level):
    settings = timetable.settings
    working_days = list(settings.working_days)
    breaks_dict = {b.after_period: b for b in settings.breaks.all()}

    # Initialize time tracking
    current_time = dt.combine(dt.today(), settings.start_time)
    period_duration = settings.period_duration

    # Get only the entries for this specific class
    entries = TimetableEntry.objects.filter(
        timetable=timetable,
        subject__target_class=class_level,
        is_active=True
    ).select_related('subject', 'room', 'subject__teacher_subject')

    # Lookup key is now (period, day) instead of (period, class)
    entry_lookup = {(e.period_number, e.day): e for e in entries}

    grid = []
    for p in range(1, settings.periods_per_day + 1):
        start_str = current_time.strftime("%H:%M")
        end_time = current_time + timedelta(minutes=period_duration)
        end_str = end_time.strftime("%H:%M")

        current_time = end_time

        day_slots = []
        for day in working_days:
            entry = entry_lookup.get((p, day))
            day_slots.append({'day': day, 'is_free': entry is None, 'entry': entry})

        grid.append({
            'type': 'period',
            'period_number': p,
            'start_time': start_str,
            'end_time': end_str,
            'day_slots': day_slots
        })

        if p in breaks_dict:
            break_obj = breaks_dict[p]
            current_time += timedelta(minutes=break_obj.duration)
            grid.append({
                'type': 'break',
                'name': break_obj.name,
                'duration': break_obj.duration
            })

    return {'working_days': working_days, 'class_level': class_level, 'grid': grid}