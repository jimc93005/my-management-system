from collections import defaultdict
from timetable.models import TimetableEntry, Timetable


def generate_timetable_matrix(timetable, teacher=None, class_level=None, room=None):
    """
    Transforms flat TimetableEntry records into a 2D matrix (Days x Periods)
    for easy rendering in Django templates.
    """
    settings = timetable.settings
    working_days = settings.working_days
    max_periods = settings.periods_per_day

    # 1. Build the base queryset with optimized database joins
    qs = TimetableEntry.objects.filter(
        timetable=timetable,
        is_active=True
    ).select_related(
        'assignment',
        'assignment__subject',
        'assignment__teacher',
        'assignment__class_level',
        'room'
    )

    # 2. Filter down to the specific entity we are viewing
    if teacher:
        qs = qs.filter(assignment__teacher=teacher)
    elif class_level:
        qs = qs.filter(assignment__class_level=class_level)
    elif room:
        qs = qs.filter(room=room)

    # 3. Create a quick lookup dictionary: key = (day, period_number), value = entry
    entry_lookup = {(entry.day, entry.period_number): entry for entry in qs}

    # 4. Map day integers to display names using your model's choices
    day_names = dict(TimetableEntry.DayOfWeek.choices)

    # 5. Build the 2D Grid Structure (Rows = Days, Columns = Periods)
    grid = []
    for day_index in working_days:
        day_row = {
            'day_name': day_names.get(day_index, f"Day {day_index}"),
            'day_index': day_index,
            'periods': []
        }

        # Loop through every possible period slot for the day
        for period_num in range(1, max_periods + 1):
            entry = entry_lookup.get((day_index, period_num))
            day_row['periods'].append({
                'period_number': period_num,
                'entry': entry,
                'is_free': entry is None
            })

        grid.append(day_row)

    return {
        'timetable_name': timetable.name,
        'period_headers': range(1, max_periods + 1),
        'grid': grid
    }


from datetime import datetime as dt, timedelta
from timetable.models import TimetableEntry
from students_app.models import ClassLevel  # Adjust imports as per your project


def generate_master_timetable_matrix(timetable, selected_day):
    settings = timetable.settings
    classes = ClassLevel.objects.all()
    breaks_dict = {b.after_period: b for b in settings.breaks.all()}

    # Initialize time tracking using the school's configured start time
    current_time = dt.combine(dt.today(), settings.start_time)
    period_duration = settings.period_duration

    entries = TimetableEntry.objects.filter(
        timetable=timetable, day=selected_day, is_active=True
    ).select_related('subject', 'room')

    entry_lookup = {
        (e.period_number, e.subject.target_class_id): e
        for e in entries if e.subject and e.subject.target_class_id
    }

    grid = []
    for p in range(1, settings.periods_per_day + 1):
        # Calculate start and end strings for this specific period
        start_str = current_time.strftime("%H:%M")
        end_time = current_time + timedelta(minutes=period_duration)
        end_str = end_time.strftime("%H:%M")

        # Advance the clock past this period
        current_time = end_time

        class_slots = []
        for cls in classes:
            entry = entry_lookup.get((p, cls.id))
            class_slots.append({'class_id': cls.id, 'is_free': entry is None, 'entry': entry})

        grid.append({
            'type': 'period',
            'period_number': p,
            'start_time': start_str,
            'end_time': end_str,
            'class_slots': class_slots
        })

        # Check if a break occurs immediately after this period
        if p in breaks_dict:
            break_obj = breaks_dict[p]
            # Advance the clock by the break duration so the next period starts later
            current_time += timedelta(minutes=break_obj.duration)

            grid.append({
                'type': 'break',
                'name': break_obj.name,
                'duration': break_obj.duration
            })

    return {'working_days': settings.working_days, 'classes': classes, 'grid': grid}


from datetime import datetime as dt, timedelta
from timetable.models import TimetableEntry


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


from datetime import datetime as dt, timedelta
from timetable.models import TimetableEntry


def generate_compact_master_matrix(timetable):
    """Generates a matrix with Times as columns and Days/Forms as rows."""
    settings = timetable.settings
    working_days = list(settings.working_days)

    # FIX 1: Sort by 'level_order' instead of 'name'
    classes = list(ClassLevel.objects.all().order_by('level_order'))

    breaks_dict = {b.after_period: b for b in settings.breaks.all()}

    # 1. Build the Timeline (Columns)
    timeline = []
    current_time = dt.combine(dt.today(), settings.start_time)
    period_duration = settings.period_duration

    for p in range(1, settings.periods_per_day + 1):
        start_str = current_time.strftime("%H:%M")
        end_time = current_time + timedelta(minutes=period_duration)
        end_str = end_time.strftime("%H:%M")

        timeline.append({
            'type': 'period',
            'period_number': p,
            'label': f"{start_str}\n{end_str}"
        })
        current_time = end_time

        # Add Break column if it occurs after this period
        if p in breaks_dict:
            break_obj = breaks_dict[p]
            break_end = current_time + timedelta(minutes=break_obj.duration)
            timeline.append({
                'type': 'break',
                'name': break_obj.name.upper(),
                'label': f"{current_time.strftime('%H:%M')}\n{break_end.strftime('%H:%M')}"
            })
            current_time = break_end

    # 2. Fetch Entries
    entries = TimetableEntry.objects.filter(
        timetable=timetable, is_active=True
    ).select_related('subject', 'room', 'subject__target_class')

    # Lookup key: (Day, Class ID, Period Number)
    entry_lookup = {(e.day, e.subject.target_class_id, e.period_number): e for e in entries}
    day_mapping = {'0': 'MON', '1': 'TUE', '2': 'WED', '3': 'THU', '4': 'FRI', '5': 'SAT', '6': 'SUN'}

    # 3. Build the Grid Rows
    grid = []
    for day in working_days:
        day_str = str(day)
        day_name = day_mapping.get(day_str, day_str.upper())

        day_rows = []
        for cls_idx, cls in enumerate(classes):
            row_cells = []
            for col in timeline:
                if col['type'] == 'break':
                    # Only inject the break cell on the FIRST form's row so it can rowspan down
                    if cls_idx == 0:
                        row_cells.append({'type': 'break', 'name': col['name'], 'rowspan': len(classes)})
                    else:
                        row_cells.append({'type': 'skip'})  # Tell the template to ignore this cell
                else:
                    entry = entry_lookup.get((day, cls.id, col['period_number']))
                    row_cells.append({
                        'type': 'period',
                        'is_free': entry is None,
                        'entry': entry
                    })

            day_rows.append({
                # FIX 2: Use str(cls) or cls.class_level instead of cls.name
                'class_name': str(cls),
                'cells': row_cells,
                'is_first': cls_idx == 0
            })

        grid.append({
            'day_name': day_name,
            'rowspan': len(classes),
            'rows': day_rows
        })

    return {
        'timeline': timeline,
        'grid': grid,
        'classes': classes
    }


def generate_compact_class_matrix(timetable, class_level):
    """Generates a landscape matrix for a single class (Days as rows, Times as columns)."""
    settings = timetable.settings
    working_days = list(settings.working_days)
    breaks_dict = {b.after_period: b for b in settings.breaks.all()}

    # 1. Build the Timeline (Columns)
    timeline = []
    current_time = dt.combine(dt.today(), settings.start_time)
    period_duration = settings.period_duration

    for p in range(1, settings.periods_per_day + 1):
        start_str = current_time.strftime("%H:%M")
        end_time = current_time + timedelta(minutes=period_duration)
        end_str = end_time.strftime("%H:%M")

        timeline.append({
            'type': 'period',
            'period_number': p,
            'label': f"{start_str}\n{end_str}"
        })
        current_time = end_time

        if p in breaks_dict:
            break_obj = breaks_dict[p]
            break_end = current_time + timedelta(minutes=break_obj.duration)
            timeline.append({
                'type': 'break',
                'name': break_obj.name.upper(),
                'label': f"{current_time.strftime('%H:%M')}\n{break_end.strftime('%H:%M')}"
            })
            current_time = break_end

    # 2. Fetch Entries for THIS specific class only
    entries = TimetableEntry.objects.filter(
        timetable=timetable,
        is_active=True,
        subject__target_class=class_level
    ).select_related('subject', 'room')

    entry_lookup = {(e.day, e.period_number): e for e in entries}
    day_mapping = {'0': 'MON', '1': 'TUE', '2': 'WED', '3': 'THU', '4': 'FRI', '5': 'SAT', '6': 'SUN'}

    # 3. Build the Grid Rows (1 row per day)
    grid = []
    for day in working_days:
        day_str = str(day)
        day_name = day_mapping.get(day_str, day_str.upper())

        row_cells = []
        for col in timeline:
            if col['type'] == 'break':
                row_cells.append({'type': 'break', 'name': col['name']})
            else:
                entry = entry_lookup.get((day, col['period_number']))
                row_cells.append({
                    'type': 'period',
                    'is_free': entry is None,
                    'entry': entry
                })

        grid.append({
            'day_name': day_name,
            'cells': row_cells
        })

    return {
        'timeline': timeline,
        'grid': grid
    }