from django.db.models import Sum, Avg
from .models import Grade, Students

from django.db.models import Sum, Avg


def build_term_reports(student, level_filter=None):
    all_grades = Grade.objects.filter(student=student)

    # If the user clicked a specific class level, filter the grades!
    if level_filter:
        all_grades = all_grades.filter(class_level_snapshot__icontains=level_filter)

    # all_grades = Grade.objects.filter(student=student)
    term_reports = {}

    # 1. Organize grades (This part remains mostly the same)
    for grade in all_grades:
        year = grade.academic_year
        term = grade.term

        if not year or not term: continue

        if year not in term_reports: term_reports[year] = {}
        if term not in term_reports[year]:
            term_reports[year][term] = {
                'grades': [], 'subject_count': 0, 'average': 0,
                'position': None, 'promotion_status': '',
                'head_remark': '', 'class_comment': '',
                # Let's also store the historical class for this term
                'historical_class': grade.class_level_snapshot or student.class_level.class_level
            }

        term_reports[year][term]['grades'].append(grade)

    # 2. Calculate Averages, Positions, and Remarks
    for year in term_reports:
        for term in term_reports[year]:
            historical_class = term_reports[year][term]['historical_class']
            term_grades = Grade.objects.filter(student=student, academic_year=year, term=term)

            total = term_grades.aggregate(total=Sum('score'))['total'] or 0
            count = term_grades.count()
            average = round(total / count, 2) if count > 0 else 0

            term_reports[year][term]['subject_count'] = count
            term_reports[year][term]['average'] = average

            # --- HISTORICAL POSITION CALCULATION ---
            # Find all students who took exams in THIS year, THIS term, and THIS historical class
            cohort_grades = Grade.objects.filter(
                academic_year=year,
                term=term,
                class_level_snapshot=historical_class
            )

            # Get unique student IDs in this cohort
            cohort_student_ids = cohort_grades.values_list('student_id', flat=True).distinct()
            total_students_in_term = cohort_student_ids.count()

            term_averages = []
            for s_id in cohort_student_ids:
                avg = Grade.objects.filter(
                    student_id=s_id, academic_year=year, term=term
                ).aggregate(avg=Avg('score'))['avg'] or 0
                term_averages.append({'student_id': s_id, 'average': round(avg, 2)})

            term_averages.sort(key=lambda x: x['average'], reverse=True)

            position = 0
            last_avg = None
            for index, record in enumerate(term_averages):
                if record['average'] != last_avg:
                    position = index + 1
                last_avg = record['average']

                if record['student_id'] == student.id:
                    term_reports[year][term]['position'] = position

            # --- Remarks (Remains the same as your logic) ---
            avg_score = average
            if avg_score >= 75:
                status, remark, class_teacher_comment = "Pass", "Excellent performance.", "A brilliant student..."
            elif avg_score >= 60:
                status, remark, class_teacher_comment = "Pass", "Satisfactory progress...", "Active in class..."
            elif avg_score >= 50:
                status, remark, class_teacher_comment = "Pass", "A narrow pass...", "Shows potential..."
            else:
                status, remark, class_teacher_comment = "Fail", "Unsatisfactory...", "Performance is quite weak..."

            term_reports[year][term]['promotion_status'] = status
            term_reports[year][term]['head_remark'] = remark
            term_reports[year][term]['class_comment'] = class_teacher_comment

            # --- HISTORICAL SUBJECT-WISE POSITIONING ---
            grades_in_term = term_reports[year][term]['grades']
            subjects = set(g.subject for g in grades_in_term)

            for subject in subjects:
                # Compare against the historical class, not the current one
                subject_grades = Grade.objects.filter(
                    subject=subject,
                    academic_year=year,
                    term=term,
                    class_level_snapshot=historical_class
                ).order_by('-score')

                total_subject_students = subject_grades.count()
                subject_position = 0
                last_score = None

                for index, g in enumerate(subject_grades):
                    if g.score != last_score:
                        subject_position = index + 1
                    last_score = g.score

                    if g.student.id == student.id:
                        for student_grade in grades_in_term:
                            if student_grade.subject == subject:
                                student_grade.subject_position = subject_position
                                student_grade.subject_total = total_subject_students

    # Return total_students based on their current class just for the profile header,
    # but the reports are all completely historical now.
    current_total_students = Students.objects.filter(class_level=student.class_level).count()
    return term_reports, current_total_students