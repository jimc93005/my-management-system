from django.db.models import Sum, Avg, Q
from .models import Grade, Students, ClassLevel, GradeBoundary


def build_term_reports(student, level_filter=None):
    all_grades = Grade.objects.filter(student=student)

    if level_filter:
        all_grades = all_grades.filter(class_level_snapshot__icontains=level_filter)

    term_reports = {}

    # 1. Organize grades (UPDATED WITH CLASS-LOCK)
    for grade in all_grades:
        year = grade.academic_year
        term = grade.term

        # Grab the snapshot for this specific grade
        current_snapshot = grade.class_level_snapshot or getattr(student.class_level, 'class_level', '')

        if not year or not term: continue

        if year not in term_reports: term_reports[year] = {}
        if term not in term_reports[year]:
            # Lock this term's bucket to the FIRST class level we find
            term_reports[year][term] = {
                'grades': [], 'subject_count': 0, 'average': 0,
                'position': None, 'promotion_status': '',
                'head_remark': '', 'class_comment': '',
                'historical_class': current_snapshot
            }

        # STRICT FILTER: Only append the grade if it matches this term's locked class!
        if current_snapshot == term_reports[year][term]['historical_class']:
            term_reports[year][term]['grades'].append(grade)

    # 2. Calculate Averages, Positions, and Remarks
    for year in term_reports:
        for term in term_reports[year]:
            historical_class = term_reports[year][term]['historical_class']

            # STRICT FILTER: Only query grades matching the locked class!
            term_grades = Grade.objects.filter(
                student=student,
                academic_year=year,
                term=term,
                class_level_snapshot=historical_class
            )

            total = term_grades.aggregate(total=Sum('score'))['total'] or 0
            count = term_grades.count()
            average = round(total / count, 2) if count > 0 else 0

            term_reports[year][term]['subject_count'] = count
            term_reports[year][term]['average'] = average

            # --- HISTORICAL POSITION CALCULATION (Updated with Strict Filter) ---
            cohort_grades = Grade.objects.filter(
                academic_year=year, term=term, class_level_snapshot=historical_class
            )
            cohort_student_ids = cohort_grades.values_list('student_id', flat=True).distinct()
            total_students_in_term = cohort_student_ids.count()

            term_averages = []
            for s_id in cohort_student_ids:
                # Calculate ranking average only using the locked class subjects
                avg = Grade.objects.filter(
                    student_id=s_id,
                    academic_year=year,
                    term=term,
                    class_level_snapshot=historical_class
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

            # =========================================================
            # 👇 FULLY DYNAMIC OVERALL REMARKS ENGINE 👇
            # =========================================================

            # Find the grading system for this specific class
            grading_system = None
            try:
                hist_class_obj = ClassLevel.objects.get(class_level=historical_class)
                grading_system = hist_class_obj.grading_system
            except ClassLevel.DoesNotExist:
                pass

            status = "Pass"
            remark = "Progressing well."
            class_teacher_comment = "Satisfactory performance."

            if grading_system:
                # Ask the database what the student's OVERALL AVERAGE means on this scale!
                boundary = GradeBoundary.objects.filter(
                    grading_system=grading_system,
                    min_score__lte=average,
                    max_score__gte=average
                ).first()

                if boundary:
                    remark = boundary.remark
                    # List of typical failing grade indicators
                    fail_indicators = ['F', '9', '8', '7', 'Fail', 'U']

                    if boundary.grade_name in fail_indicators:
                        status = "Fail"
                        class_teacher_comment = f"Average score maps to {boundary.grade_name}. Must work harder."
                    else:
                        status = "Pass"
                        class_teacher_comment = f"Overall performance is {boundary.grade_name}. {boundary.remark}"
            else:
                # FALLBACK: If the school hasn't assigned a dynamic grading system yet, use the old hardcoded logic
                if average >= 75:
                    status, remark, class_teacher_comment = "Pass", "Excellent performance.", "A brilliant student..."
                elif average >= 60:
                    status, remark, class_teacher_comment = "Pass", "Satisfactory progress...", "Active in class..."
                elif average >= 50:
                    status, remark, class_teacher_comment = "Pass", "A narrow pass...", "Shows potential..."
                else:
                    status, remark, class_teacher_comment = "Fail", "Unsatisfactory...", "Performance is quite weak..."

            # =========================================================
            # 👇 UPDATED: ENGLISH OVERRIDE & WEAK SUBJECTS LOGIC 👇
            # =========================================================
            english_failed = False
            fail_indicators = ['F', '9', '8', '7', 'Fail', 'U']
            weak_subjects = []

            for g in term_grades:
                # 1. Check if the subject is English
                if 'english' in str(g.subject.name).lower():
                    if g.grade_letter_snapshot in fail_indicators or g.get_remark() in fail_indicators:
                        english_failed = True

                # 2. Check if the score is below 55 to flag for the comment
                if g.score < 55:
                    weak_subjects.append(str(g.subject.name))

            # Apply the English override if necessary
            if status == "Pass" and english_failed:
                status = "Fail"
                remark = "Failed: Did not pass English."
                class_teacher_comment = "Overall average is passing, but failed English. English is a strict requirement for promotion."

            # 3. Stitch the weak subjects together and append to the comment!
            if weak_subjects:
                if len(weak_subjects) == 1:
                    subjects_str = weak_subjects[0]
                else:
                    subjects_str = ", ".join(weak_subjects[:-1]) + f" and {weak_subjects[-1]}"

                # Add a space before appending to ensure clean formatting
                class_teacher_comment += f", However, {student.first_name.capitalize()} must work hard in {subjects_str}."

            # Save to report dictionary
            term_reports[year][term]['promotion_status'] = status
            term_reports[year][term]['head_remark'] = remark
            term_reports[year][term]['class_comment'] = class_teacher_comment

            # --- HISTORICAL SUBJECT-WISE POSITIONING (Unchanged) ---
            grades_in_term = term_reports[year][term]['grades']
            subjects = set(g.subject for g in grades_in_term)

            for subject in subjects:
                subject_grades = Grade.objects.filter(
                    subject=subject, academic_year=year, term=term, class_level_snapshot=historical_class
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

    # Get the dynamic class total
    current_total_students = 0
    if student.class_level:
        current_total_students = Students.objects.filter(class_level=student.class_level).count()

    return term_reports, current_total_students