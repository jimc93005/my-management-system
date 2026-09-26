from django.shortcuts import render

# timetable/views.py
from django.shortcuts import render, get_object_or_404
from timetable.models import Timetable
from timetable.services.grid import generate_timetable_matrix
from students_app.models import ClassLevel  # Adjust import to your actual app
from django.contrib.auth.decorators import login_required
from .decorators import role_required

@login_required
def class_timetable_view(request, timetable_id, class_id):
    # Get the active timetable and the requested class
    timetable = get_object_or_404(Timetable, id=timetable_id)
    class_level = get_object_or_404(ClassLevel, id=class_id)

    # Generate the 2D matrix
    matrix_data = generate_timetable_matrix(timetable=timetable, class_level=class_level)

    context = {
        'class_level': class_level,
        'matrix_data': matrix_data
    }
    return render(request, 'timetable/class_grid.html', context)


from django.shortcuts import render, get_object_or_404
from .models import Timetable, TimetableEntry
from .services.grid import generate_master_timetable_matrix

@login_required
def master_timetable_view(request, timetable_id):
    timetable = get_object_or_404(Timetable, id=timetable_id)
    selected_day = int(request.GET.get('day', 0))  # Default to 0 (Monday)
    classes = ClassLevel.objects.all().order_by('level_order')

    matrix_data = generate_master_timetable_matrix(timetable, selected_day=selected_day)
    day_choices = TimetableEntry.DayOfWeek.choices

    context = {
        'timetable': timetable,
        'matrix_data': matrix_data,
        'selected_day': selected_day,
        'day_choices': day_choices,
        'classes': classes,
    }
    return render(request, 'timetable/master_grid_view.html', context)


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .services.generator import generate_greedy_timetable
from .models import Timetable

@login_required
@role_required(allowed_roles=['Admin', 'HOD'])
def generate_timetable_view(request, timetable_id):
    # Security check: Ensure it's a POST request so it isn't triggered accidentally by a crawler
    if request.method == "POST":
        try:
            # Run the engine!
            generate_greedy_timetable(timetable_id)
            messages.success(request, "Timetable generated successfully!")
        except Exception as e:
            messages.error(request, f"Generation failed: {str(e)}")

    # Redirect back to the master view to see the results
    return redirect('timetable:master_timetable', timetable_id=timetable_id)
    # Make sure 'master_timetable' matches the name=... in your urls.py for the grid view


@login_required
def export_timetable_pdf_view(request, timetable_id):
    timetable = Timetable.objects.get(id=timetable_id)
    selected_day = request.GET.get('day', 'Monday')

    school_profile = SchoolProfile.objects.first()

    # --- NEW HELPER FUNCTION ---
    def get_image_uri(image_field):
        """Safely fetches the absolute local file path for WeasyPrint"""
        if image_field and hasattr(image_field, 'path'):
            try:
                # Bypass the network and use the direct local disk path (e.g., file:///...)
                return pathlib.Path(image_field.path).as_uri()
            except NotImplementedError:
                # Fallback just in case you use Amazon S3/Cloud storage in the future
                return image_field.url
        return None

    # Fetch the URIs using the helper
    school_logo_uri = get_image_uri(school_profile.logo if school_profile else None)
    head_sig_uri = get_image_uri(school_profile.headteacher_signature if school_profile else None)

    matrix_data = generate_master_timetable_matrix(timetable, selected_day)

    context = {
        'timetable': timetable,
        'selected_day': selected_day,
        'matrix_data': matrix_data,
        'school_profile': school_profile,
        'school_logo_uri': school_logo_uri,
        'head_sig_uri': head_sig_uri,
    }

    template = get_template('timetable/timetable_pdf.html')
    html_string = template.render(context)

    # Generate PDF
    pdf_file = HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{timetable.name}_{selected_day}_schedule.pdf"'

    return response


import pathlib
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML
from .models import Timetable
from students_app.models import SchoolProfile, ClassLevel
from .services.grid import generate_master_timetable_matrix, generate_class_timetable_matrix


def get_image_uri(image_field):
    """Safely fetches the absolute local file path for WeasyPrint"""
    if image_field and hasattr(image_field, 'path'):
        try:
            return pathlib.Path(image_field.path).as_uri()
        except NotImplementedError:
            return image_field.url
    return None


from .services.grid import generate_compact_master_matrix

@login_required
def export_full_school_pdf_view(request, timetable_id):
    """Generates a compact, single-page matrix for the entire school."""
    timetable = Timetable.objects.get(id=timetable_id)
    school_profile = SchoolProfile.objects.first()

    matrix_data = generate_compact_master_matrix(timetable)

    context = {
        'timetable': timetable,
        'matrix_data': matrix_data,
        'school_profile': school_profile,
        'school_logo_uri': get_image_uri(school_profile.logo if school_profile else None),
        'head_sig_uri': get_image_uri(school_profile.headteacher_signature if school_profile else None),
    }

    html_string = get_template('timetable/full_school_pdf.html').render(context)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{timetable.name}_Compact_Schedule.pdf"'
    return response



# Import the new function at the top
from .services.grid import generate_compact_class_matrix
@login_required
def export_class_timetable_pdf_view(request, timetable_id, class_id):
    """Generates a compact landscape PDF schedule for a specific class."""
    timetable = Timetable.objects.get(id=timetable_id)
    class_level = ClassLevel.objects.get(id=class_id)
    school_profile = SchoolProfile.objects.first()

    # USE THE NEW FUNCTION HERE
    matrix_data = generate_compact_class_matrix(timetable, class_level)

    context = {
        'timetable': timetable,
        'class_level': class_level,
        'matrix_data': matrix_data,
        'school_profile': school_profile,
        'school_logo_uri': get_image_uri(school_profile.logo if school_profile else None),
        'head_sig_uri': get_image_uri(school_profile.headteacher_signature if school_profile else None),
    }

    html_string = get_template('timetable/class_timetable_pdf.html').render(context)
    pdf_file = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    # Make sure we use the correct field for the file name: class_level.class_level
    response['Content-Disposition'] = f'inline; filename="{class_level.class_level}_Weekly_Schedule.pdf"'
    return response




# TIMETABLE UI VIEWS



from django.contrib.auth.decorators import login_required
from .decorators import role_required


from .forms import TimetableSettingsForm, TimetableBreakFormSet, BlockedSlotFormSet


@login_required
@role_required(allowed_roles=['Admin', 'Principal', 'Headteacher', 'Deputy'])
def setup_settings_view(request):
    settings = TimetableSettings.objects.filter(is_active=True).first()
    if not settings:
        settings = TimetableSettings.objects.last()

    if request.method == 'POST':
        form = TimetableSettingsForm(request.POST, instance=settings)
        break_formset = TimetableBreakFormSet(request.POST, instance=settings, prefix='breaks')
        blocked_formset = BlockedSlotFormSet(request.POST, instance=settings, prefix='blocked')

        if form.is_valid() and break_formset.is_valid() and blocked_formset.is_valid():
            saved_settings = form.save()
            break_formset.instance = saved_settings
            break_formset.save()
            blocked_formset.instance = saved_settings
            blocked_formset.save()
            messages.success(request, "Timetable configuration, breaks, and blocked slots updated successfully!")
            return redirect('timetable:setup_settings')
        else:
            messages.error(request, "Please fix the validation errors below.")
    else:
        initial_days = settings.working_days if settings else [0, 1, 2, 3, 4]
        form = TimetableSettingsForm(instance=settings, initial={'working_days': initial_days})
        break_formset = TimetableBreakFormSet(instance=settings, prefix='breaks')
        blocked_formset = BlockedSlotFormSet(instance=settings, prefix='blocked')

    return render(request, 'timetable/settings.html', {
        'active_tab': 'settings',
        'form': form,
        'break_formset': break_formset,
        'blocked_formset': blocked_formset,
        'settings': settings,
    })

from .models import TimetableRoom
from .forms import TimetableRoomForm
from django.shortcuts import render, redirect
from django.contrib import messages


@login_required
@role_required(allowed_roles=['Admin', 'Principal', 'Headteacher', 'Deputy'])
def setup_rooms_view(request):
    rooms = TimetableRoom.objects.all().order_by('room_type', 'name')
    form = TimetableRoomForm()

    if request.method == 'POST':
        # Handle Deletion
        if 'delete_room' in request.POST:
            room_id = request.POST.get('room_id')
            TimetableRoom.objects.filter(id=room_id).delete()
            messages.success(request, "Room deleted successfully.")
            return redirect('timetable:setup_rooms')

        # Handle Addition / Update
        if 'save_room' in request.POST:
            form = TimetableRoomForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Room added successfully.")
                return redirect('timetable:setup_rooms')
            else:
                messages.error(request, "Failed to add room. Please check the errors.")

    return render(request, 'timetable/rooms.html', {
        'active_tab': 'rooms',
        'rooms': rooms,
        'form': form,
    })


from students_app.models import Subject, ClassLevel
from .models import SubjectConstraint, SubjectRoomRequirement, TimetableRoom
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


@login_required
@role_required(allowed_roles=['Admin', 'Principal', 'Headteacher', 'Deputy'])
def setup_constraints_view(request):
    class_levels = ClassLevel.objects.all().order_by('class_level')

    # Default to the first class if none specified in query string
    selected_class_id = request.GET.get('class_id')
    if selected_class_id:
        selected_class = get_object_or_404(ClassLevel, id=selected_class_id)
    else:
        selected_class = class_levels.first()

    subjects = Subject.objects.filter(target_class=selected_class).select_related(
        'teacher_subject', 'timetable_constraint', 'room_requirement'
    ) if selected_class else []

    # Ensure constraint and room requirement records exist for every subject
    subject_rows = []
    if selected_class:
        for sub in subjects:
            constraint, _ = SubjectConstraint.objects.get_or_create(subject=sub)
            room_req, _ = SubjectRoomRequirement.objects.get_or_create(subject=sub)
            subject_rows.append({
                'subject': sub,
                'constraint': constraint,
                'room_req': room_req,
            })

    # Save updates for all subjects in the selected class
    if request.method == 'POST' and selected_class:
        for row in subject_rows:
            sub_id = row['subject'].id
            constraint = row['constraint']
            room_req = row['room_req']

            # Extract fields from POST data
            periods = request.POST.get(f'periods_{sub_id}', 5)
            allow_double = request.POST.get(f'allow_double_{sub_id}') == 'on'
            double_periods = request.POST.get(f'double_periods_{sub_id}', 0)
            req_room_type = request.POST.get(f'room_type_{sub_id}', TimetableRoom.RoomType.CLASSROOM)
            spec_room_id = request.POST.get(f'specific_room_{sub_id}')

            # Update SubjectConstraint
            constraint.periods_per_week = int(periods) if periods else 5
            constraint.allow_double_periods = allow_double
            constraint.double_periods_per_week = int(double_periods) if double_periods else 0
            constraint.save()

            # Update SubjectRoomRequirement
            room_req.required_room_type = req_room_type
            if spec_room_id:
                room_req.specific_room = TimetableRoom.objects.filter(id=spec_room_id).first()
            else:
                room_req.specific_room = None
            room_req.save()

        messages.success(request, f"Rules for {selected_class} updated successfully!")
        return redirect(f"{request.path}?class_id={selected_class.id}")

    rooms = TimetableRoom.objects.filter(is_active=True).order_by('name')
    room_types = TimetableRoom.RoomType.choices

    return render(request, 'timetable/constraints.html', {
        'active_tab': 'constraints',
        'class_levels': class_levels,
        'selected_class': selected_class,
        'subject_rows': subject_rows,
        'rooms': rooms,
        'room_types': room_types,
    })


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .decorators import role_required
from .models import TimetableSettings, TimetableRoom, SubjectConstraint
from students_app.models import Subject


@login_required
@role_required(allowed_roles=['Admin', 'Principal', 'Headteacher', 'Deputy'])
def setup_generate_view(request):
    settings = TimetableSettings.objects.filter(is_active=True).first()
    rooms_count = TimetableRoom.objects.filter(is_active=True).count()
    subjects_count = Subject.objects.count()

    # Pre-flight readiness checks
    readiness_errors = []

    if not settings:
        readiness_errors.append("No active timetable configuration found. Please save settings.")
    if rooms_count == 0:
        readiness_errors.append("No active rooms exist. Please add at least one room.")
    if subjects_count == 0:
        readiness_errors.append("No subjects exist in the database.")

    is_ready = len(readiness_errors) == 0

    if request.method == 'POST':
        if not is_ready:
            messages.error(request, "Cannot generate timetable. Please resolve the errors below.")
        else:
            # Placeholder for the actual scheduling algorithm call
            # e.g., generate_timetable_task(settings.id)
            messages.success(request, "Timetable generation algorithm triggered successfully!")
            return redirect('timetable:setup_generate')

    return render(request, 'timetable/generate.html', {
        'active_tab': 'generate',
        'settings': settings,
        'rooms_count': rooms_count,
        'subjects_count': subjects_count,
        'is_ready': is_ready,
        'readiness_errors': readiness_errors,
    })


from .models import TeacherUnavailability
from .forms import TeacherUnavailabilityForm


@login_required
@role_required(allowed_roles=['Admin', 'Principal', 'Headteacher', 'Deputy'])
def setup_teachers_view(request):
    unavailabilities = TeacherUnavailability.objects.all().select_related('teacher').order_by('day', 'teacher')
    form = TeacherUnavailabilityForm()

    if request.method == 'POST':
        # Handle Deletion
        if 'delete_unavailability' in request.POST:
            u_id = request.POST.get('unavailability_id')
            TeacherUnavailability.objects.filter(id=u_id).delete()
            messages.success(request, "Teacher availability rule removed successfully.")
            return redirect('timetable:setup_teachers')

        # Handle Addition
        if 'save_unavailability' in request.POST:
            form = TeacherUnavailabilityForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Teacher unavailability rule added successfully.")
                return redirect('timetable:setup_teachers')
            else:
                messages.error(request, "Failed to add rule. Ensure this exact rule doesn't already exist.")

    return render(request, 'timetable/teachers.html', {
        'active_tab': 'teachers',
        'unavailabilities': unavailabilities,
        'form': form,
    })