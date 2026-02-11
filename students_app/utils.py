from django.db.models import Sum, Avg
from .models import Grade, Students


def build_term_reports(student):
    """
    Builds per-year, per-term academic reports for a student.
    Returns:
        term_reports (dict)
        total_students (int)
    """

    all_grades = Grade.objects.filter(student=student)

    term_reports = {}

    # -------------------------------
    # Organize grades
    # -------------------------------
    for grade in all_grades:
        year = grade.academic_year
        term = grade.term

        if not year or not term:
            continue

        if year not in term_reports:
            term_reports[year] = {}

        if term not in term_reports[year]:
            term_reports[year][term] = {
                'grades': [],
                'subject_count': 0,
                'average': 0,
                'position': None,
                'promotion_status': '',
                'head_remark': '',
                'class_comment': '',
            }

        term_reports[year][term]['grades'].append(grade)

    # -------------------------------
    # Calculate averages
    # -------------------------------
    for year in term_reports:
        for term in term_reports[year]:
            term_grades = Grade.objects.filter(
                student=student,
                academic_year=year,
                term=term
            )

            total = term_grades.aggregate(total=Sum('score'))['total'] or 0
            count = term_grades.count()

            average = round(total / count, 2) if count > 0 else 0

            term_reports[year][term]['subject_count'] = count
            term_reports[year][term]['average'] = average

    # -------------------------------
    # Position & remarks
    # -------------------------------
    class_students = Students.objects.filter(
        class_level=student.class_level
    )
    total_students = class_students.count()

    for year in term_reports:
        for term in term_reports[year]:

            term_averages = []

            for s in class_students:
                avg = Grade.objects.filter(
                    student=s,
                    academic_year=year,
                    term=term
                ).aggregate(avg=Avg('score'))['avg'] or 0

                term_averages.append({
                    'student_id': s.id,
                    'average': round(avg, 2)
                })

            term_averages.sort(key=lambda x: x['average'], reverse=True)

            position = 0
            last_avg = None

            for index, record in enumerate(term_averages):
                if record['average'] != last_avg:
                    position = index + 1
                last_avg = record['average']

                if record['student_id'] == student.id:
                    term_reports[year][term]['position'] = position

            avg_score = term_reports[year][term]['average']

            if avg_score >= 75:
                status = "Pass"
                remark = "Excellent performance."
                class_teacher_comment = (
                    "A brilliant student with a great future. "
                    "Keep maintained this high standard."
                )
                head_teacher_comment = (
                    "Outstanding results. An asset to this institution."
                )

            elif avg_score >= 60:
                status = "Pass"
                class_teacher_comment = (
                    "Active in class and performs well. "
                    "There is room to reach the top tier."
                )
                remark = (
                    "Satisfactory progress. Continue working hard "
                    "to achieve excellence."
                )

            elif avg_score >= 50:
                status = "Pass"
                class_teacher_comment = (
                    "Shows potential but is easily distracted. "
                    "Needs to focus more on core subjects."
                )
                remark = (
                    "A narrow pass. Consistent effort is required "
                    "in the next term."
                )

            else:
                status = "Fail"
                class_teacher_comment = (
                    "Performance is quite weak. Should attend "
                    "extra-remedial classes and focus."
                )
                remark = (
                    "Unsatisfactory. Parents are requested to visit "
                    "the school to discuss progress."
                )

            term_reports[year][term]['promotion_status'] = status
            term_reports[year][term]['head_remark'] = remark
            term_reports[year][term]['class_comment'] = class_teacher_comment

    # ==================================================
    # SUBJECT-WISE POSITIONING (NEW CODE – ADDED ONLY)
    # ==================================================
    for year in term_reports:
        for term in term_reports[year]:

            grades_in_term = term_reports[year][term]['grades']

            # Get unique subjects in this term
            subjects = set(g.subject for g in grades_in_term)

            for subject in subjects:

                subject_grades = Grade.objects.filter(
                    subject=subject,
                    academic_year=year,
                    term=term,
                    student__class_level=student.class_level
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

    return term_reports, total_students

