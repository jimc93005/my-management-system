from collections import defaultdict
from django.db import transaction
from timetable.models import Timetable, TimetableEntry, SubjectConstraint, TeacherUnavailability

MORNING = SubjectConstraint.TimePreference.MORNING
AFTERNOON = SubjectConstraint.TimePreference.AFTERNOON
ANYTIME = SubjectConstraint.TimePreference.ANYTIME


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------
def get_zone_boundary(break_after_periods, periods_per_day):
    """
    Last period that counts as 'morning'.
    Two or more breaks -> the second break. One break -> that break.
    No breaks -> split the day in half.
    """
    breaks = sorted(break_after_periods)
    if len(breaks) >= 2:
        return breaks[1]
    if len(breaks) == 1:
        return breaks[0]
    return (periods_per_day + 1) // 2


def zone_penalty(preference, period, boundary):
    """0 = matches the preferred zone, 1 = no preference, 2 = against the preference."""
    if preference == ANYTIME:
        return 1
    is_morning = period <= boundary
    if preference == MORNING:
        return 0 if is_morning else 2
    return 0 if not is_morning else 2  # AFTERNOON


def spread_penalty(constraint, day, used_days, day_pos):
    """
    0 = placing a lesson on `day` keeps the subject well spaced across the week.
    Higher = closer to a day the subject already uses.
    """
    n_days = len(day_pos)
    # A double period occupies one day, so it counts once
    days_needed = max(1, constraint.periods_per_week - constraint.double_periods_per_week)

    if not used_days or days_needed >= n_days:
        return 0  # nothing to space, or the subject needs every day anyway

    ideal_gap = -(-n_days // days_needed)  # ceil(n_days / days_needed)
    nearest = min(abs(day_pos[day] - day_pos[d]) for d in used_days)
    return max(0, ideal_gap - nearest)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
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

    # --- Prioritize busiest teachers (used as the final tie-breaker) ---
    teacher_loads = defaultdict(int)
    for c in constraints:
        if c.subject.teacher_subject:
            teacher_loads[c.subject.teacher_subject.id] += c.periods_per_week

    constraints.sort(key=lambda c: (
        teacher_loads.get(c.subject.teacher_subject.id if c.subject.teacher_subject else 0, 0),
        c.double_periods_per_week,
        c.periods_per_week
    ), reverse=True)
    order_index = {c.id: i for i, c in enumerate(constraints)}

    working_days = list(settings.working_days)
    day_pos = {d: i for i, d in enumerate(working_days)}
    periods_per_day = settings.periods_per_day
    break_after_periods = list(settings.breaks.values_list('after_period', flat=True))
    zone_boundary = get_zone_boundary(break_after_periods, periods_per_day)

    # 3. Pre-load Blocked Slots & Teacher Unavailability
    blocked_matrix = {(bs.day, bs.period_number) for bs in settings.blocked_slots.all()}
    unavail_matrix = set()
    for u in TeacherUnavailability.objects.all():
        period_val = u.period_number if u.period_number is not None else 'ALL'
        unavail_matrix.add((u.teacher_id, u.day, period_val))

    placement_tracker = {c.id: c.periods_per_week for c in constraints}
    doubles_tracker = {c.id: c.double_periods_per_week for c in constraints}
    target_classes = list(set(c.subject.target_class for c in constraints if c.subject.target_class))

    if not target_classes:
        raise ValueError("No subjects are linked to a class, so there is nothing to schedule.")

    # In-memory record of where each subject already sits (used for spreading)
    lessons_on_day = defaultdict(int)   # (subject_id, day) -> lessons
    days_used = defaultdict(set)        # subject_id -> {days}

    def place(constraint, day, periods):
        subject = constraint.subject
        for p in periods:
            TimetableEntry.objects.create(
                timetable=timetable, subject=subject, day=day, period_number=p
            )
        placement_tracker[constraint.id] -= len(periods)
        lessons_on_day[(subject.id, day)] += len(periods)
        days_used[subject.id].add(day)

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

        relax_doubles = (attempts >= 3)   # split doubles on later attempts
        strict_zones = (attempts <= 2)    # honour Morning/Afternoon on early attempts

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

                    # A. DOUBLE PERIOD (skipped once doubles are relaxed)
                    if not relax_doubles and period < periods_per_day and period not in break_after_periods:
                        double_candidates = []
                        for constraint in class_constraints:
                            subject = constraint.subject
                            if lessons_on_day[(subject.id, day)] > 0:
                                continue
                            if not (doubles_tracker[constraint.id] > 0 and placement_tracker[constraint.id] >= 2):
                                continue

                            zone = max(
                                zone_penalty(constraint.time_preference, period, zone_boundary),
                                zone_penalty(constraint.time_preference, period + 1, zone_boundary),
                            )
                            if strict_zones and zone == 2:
                                continue

                            spread = spread_penalty(constraint, day, days_used[subject.id], day_pos)
                            if attempts == 1 and spread > 0:
                                continue  # first pass: doubles only on well-spaced days

                            double_candidates.append(((spread, zone, order_index[constraint.id]), constraint))

                        double_candidates.sort(key=lambda item: item[0])
                        for _, constraint in double_candidates:
                            subject = constraint.subject
                            if is_free(day, period, subject) and is_free(day, period + 1, subject):
                                place(constraint, day, [period, period + 1])
                                doubles_tracker[constraint.id] -= 1
                                placed_this_slot = True
                                break

                    if placed_this_slot:
                        continue

                    # B. SINGLE PERIOD
                    single_candidates = []
                    for constraint in class_constraints:
                        subject = constraint.subject

                        zone = zone_penalty(constraint.time_preference, period, zone_boundary)
                        if strict_zones and zone == 2:
                            continue

                        # Soft day limit: allow 2 of the same subject per day ONLY on the final attempt
                        if lessons_on_day[(subject.id, day)] >= (2 if attempts == max_attempts else 1):
                            continue

                        # While doubles are still protected, don't burn them as singles
                        if not relax_doubles and doubles_tracker[constraint.id] > 0 and placement_tracker[
                            constraint.id] >= 2:
                            continue

                        spread = spread_penalty(constraint, day, days_used[subject.id], day_pos)
                        single_candidates.append(((spread, zone, order_index[constraint.id]), constraint))

                    single_candidates.sort(key=lambda item: item[0])
                    for _, constraint in single_candidates:
                        if is_free(day, period, constraint.subject):
                            place(constraint, day, [period])

                            # Deduct from doubles tracker if we were forced to split it
                            if relax_doubles and doubles_tracker[constraint.id] > 0:
                                doubles_tracker[constraint.id] -= 1
                            break

    # 4. Fill remaining odd gaps, then compress everything to the left
    # 4. Fill remaining odd gaps, then compress everything toward the morning
    # 4. Fill remaining odd gaps, then compress everything toward the morning
    preferences = {c.subject_id: c.time_preference for c in constraints}

    fill_remaining_gaps(timetable, target_classes, placement_tracker, constraints, working_days,
                        periods_per_day, is_free, place, lessons_on_day, days_used, day_pos, zone_boundary)
    compact_timetable(timetable, target_classes, working_days, periods_per_day, is_free,
                      preferences, zone_boundary)

    # 5. Summarise the result
    unplaced = []
    for c in constraints:
        remaining = placement_tracker[c.id]
        if remaining > 0:
            unplaced.append({
                'subject': str(c.subject.name),
                'class_name': str(c.subject.target_class) if c.subject.target_class else 'No class assigned',
                'missing': remaining,
            })

    preference_misses = sum(
        1 for subject_id, period in
        TimetableEntry.objects.filter(timetable=timetable).values_list('subject_id', 'period_number')
        if zone_penalty(preferences.get(subject_id, ANYTIME), period, zone_boundary) == 2
    )

    return {
        'requested': sum(c.periods_per_week for c in constraints),
        'placed': TimetableEntry.objects.filter(timetable=timetable).count(),
        'unplaced': unplaced,
        'preference_misses': preference_misses,
    }
def compact_timetable(timetable, target_classes, working_days, periods_per_day, is_free,
                      preferences, zone_boundary):
    """
    'Gravity': pull lessons earlier in the day to close gaps, but
      - never into a worse zone for the subject's Morning/Afternoon preference
      - never by splitting a double period
    """

    def zone_ok(subject_id, from_period, to_period):
        pref = preferences.get(subject_id, ANYTIME)
        return (zone_penalty(pref, to_period, zone_boundary)
                <= zone_penalty(pref, from_period, zone_boundary))

    def is_part_of_double(entry):
        return TimetableEntry.objects.filter(
            timetable=timetable, day=entry.day, subject=entry.subject,
            period_number__in=[entry.period_number - 1, entry.period_number + 1],
        ).exists()

    compaction_made = True
    passes = 0

    # Loop until no more movements can be made (max 3 passes for safety)
    while compaction_made and passes < 3:
        compaction_made = False
        passes += 1

        for day in working_days:
            for target_class in target_classes:

                for empty_period in range(1, periods_per_day):

                    is_empty = not TimetableEntry.objects.filter(
                        timetable=timetable, day=day, period_number=empty_period,
                        subject__target_class=target_class
                    ).exists()
                    if not is_empty:
                        continue

                    # Find the first later lesson that can legally move into the hole
                    for later_period in range(empty_period + 1, periods_per_day + 1):
                        entry_to_move = TimetableEntry.objects.filter(
                            timetable=timetable, day=day, period_number=later_period,
                            subject__target_class=target_class
                        ).select_related('subject').first()

                        if not entry_to_move:
                            continue
                        if is_part_of_double(entry_to_move):
                            continue
                        if not zone_ok(entry_to_move.subject_id, later_period, empty_period):
                            continue

                        if is_free(day, empty_period, entry_to_move.subject, ignore_entry_id=entry_to_move.id):
                            entry_to_move.period_number = empty_period
                            entry_to_move.save()
                            compaction_made = True
                            break  # hole filled, move on to the next empty period


def fill_remaining_gaps(timetable, target_classes, placement_tracker, constraints, working_days,
                        periods_per_day, is_free, place, lessons_on_day, days_used, day_pos, zone_boundary):
    """
    Last resort for lessons that are still unplaced. Zones are only a preference here,
    but the best-spaced, best-fitting subject is still tried first.
    """
    filled_count = 0

    # Loop periods FIRST so morning gaps are patched before afternoon ones
    for period in range(1, periods_per_day + 1):
        for day in working_days:
            for target_class in target_classes:

                already_filled = TimetableEntry.objects.filter(
                    timetable=timetable, day=day, period_number=period,
                    subject__target_class=target_class
                ).exists()
                if already_filled:
                    continue

                candidates = []
                for constraint in constraints:
                    subject = constraint.subject
                    if subject.target_class != target_class or placement_tracker[constraint.id] <= 0:
                        continue
                    # Allow a second single period on the same day as a last resort
                    if lessons_on_day[(subject.id, day)] >= 2:
                        continue

                    spread = spread_penalty(constraint, day, days_used[subject.id], day_pos)
                    zone = zone_penalty(constraint.time_preference, period, zone_boundary)
                    candidates.append(((spread, zone), constraint))

                candidates.sort(key=lambda item: item[0])
                for _, constraint in candidates:
                    if is_free(day, period, constraint.subject):
                        place(constraint, day, [period])
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