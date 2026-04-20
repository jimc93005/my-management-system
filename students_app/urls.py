from django.urls import path
from . import views

app_name = 'students_app'
urlpatterns = [
    path('', views.index, name='index'),
    path('students/', views.student_list, name='students_list'),
    path('students/add/', views.add_student, name='add_student'),
    path('students/<int:student_id>/delete', views.delete_student, name='delete_student'),
    path('students/<int:student_id>/edit', views.edit_student, name='edit_student'),
    path('students/class/', views.class_list, name='class_list'),
    path('students/<str:class_level>/', views.students_by_class, name='students_by_class'),
    path('student/<int:student_id>/', views.student_profile, name='student_profile'),

    # SUBJECT URLS
    path('subjects/', views.subjects_list, name='subjects_list'),
    path('subjects/add', views.add_subject, name='add_subject'),
    path('subjects/<int:subject_id>/edit', views.edit_subject, name='edit_subject'),
    path('subjects/<int:subject_id>/delete', views.delete_subject, name='delete_subject'),
    path('subjects/<int:subject_id>/delete', views.delete_subject, name='delete_subject'),

    # GRADES URLS
    path('grade/<int:student_id>/add', views.add_grade, name='add_grade'),
    path("grade/<int:grade_id>/edit/", views.edit_grade, name="edit_grade"),



    # DELETING AND UNDO DELATES TEMPLATES
    path("grade/<int:grade_id>/delete/", views.delete_grade, name="delete_grade"),
    path("<int:student_id>/<str:year>/<str:term>/delete-term/", views.delete_term_grades, name="delete_term_grades"),

    path("<int:student_id>/<str:year>/delete-year/", views.delete_year_grades, name="delete_year_grades"),
    path("school/", views.edit_school_profile, name="edit_school_profile"),

    # SCHOOL REPORT URLS
    path('<int:student_id>/report/<str:academic_year>/<str:term>/',views.school_report,name='school_report'),


    # PDF URLS
    path('<int:student_id>/report/<str:academic_year>/<str:term>/pdf/',views.school_report_pdf,name='school_report_pdf'),

    # DEPARTMENTS URLS
    path('departments/', views.department_list, name='department_list'),
    path('departments/add/', views.add_department, name='add_department'),
    path('departments/<int:department_id>/edit/', views.edit_department, name='edit_department'),
    path('departments/<int:department_id>/delete/',views.department_delete, name='department_delete'),
    path('departments/<int:department_id>/sub-departments/', views.subdepartment_list,name='subdepartment_list'),
    path('departments/<int:department_id>/sub-departments/add/',views.subdepartment_create, name='subdepartment_create'),
    path('sub-departments/<int:subdepartment_id>/roles/', views.subdepartment_roles, name='subdepartment_roles'),
    path('sub-departments/<int:subdepartment_id>/roles/add/',views.subdepartment_role_create, name='subdepartment_role_create'),

    # TEACHERS LIST URLS
    path('teachers/', views.teachers_list, name='teachers_list'),
    path('teachers/add/', views.add_teachers, name='add_teachers'),
    path('teachers/<int:teachers_id>/edit/', views.edit_teachers, name='edit_teachers'),
    path('teachers/<int:teachers_id>/delete/', views.delete_teachers, name='delete_teachers'),
    path('teachers/<int:teachers_id>/teacher_subject_list/', views.teacher_subject_list, name='teacher_subject_list'),

    # CHANGE CLASS LEVELS URLS

    path('student/<int:student_id>/change-class/', views.change_class_level, name='change_class_level'),


    # DASHBOARD URLS
    path('dashboard/', views.dashboard, name='dashboard'),
    # URL for viewing a specific subject's details
    path('subject/<int:subject_id>/', views.subject_detail, name='subject_detail'),
    path('add-staff/', views.add_staff, name='add_staff'),
    # SCHOLASTIC PDF
    path('scholastic-pdf/<str:class_level>/<str:academic_year>/<str:term>/',
         views.scholastic_report_pdf, name='scholastic_report_pdf'),
    path('scholastic-selector/', views.scholastic_selector, name='scholastic_selector'),

    # ARCHIVE VIEWS
    path('alumni/', views.alumni_list, name='alumni_list'),


    # ATTENDANCE REGISTER URLS
    path('attendance/', views.attendance_selector, name='attendance_selector'),
    path('attendance/<str:class_id>/<str:date_str>/', views.take_attendance, name='take_attendance'),

    # STATISTICS URLS
    path('statistics/', views.academic_statistics, name='academic_statistics'),

    # CALENDER URLS
    path('calendar/', views.calendar_of_events, name='calendar'),
    # BULK PROMOTIONS
    path('bulk-promote/', views.promote_students, name='promote_students'),
    # GETTING EXISTING GRADES URLS
    path('get-existing-grades/<int:student_id>/', views.get_existing_grades, name='get_existing_grades'),
    # RESSETTING PASSWORD URLS
    path('setup-password/', views.change_temp_password, name='change_temp_password'),

    # STAFF MANAGEMENT URLS
    path('staff/<int:user_id>/edit/', views.edit_staff_profile, name='edit_staff_profile'),
    path('staff/<int:user_id>/roles/', views.manage_staff_roles, name='manage_staff_roles'),
    path('staff/<int:user_id>/delete/', views.delete_staff, name='delete_staff'),

    # settings urls
    path('classes/add/', views.add_class_level, name='add_class'),
    path('setup/add-subject/', views.add_master_subject, name='add_master_subject'),

    # SUBDEPATMENT EVENTS
    path('sub-department/<int:subdept_id>/events/', views.department_events, name='department_events'),
    path('sub-department/<int:subdept_id>/events/add/', views.add_department_event, name='add_department_event'),
    path('sub-department/<int:subdept_id>/events/print/', views.print_department_events, name='print_department_events'),
    # NOTIFICATIONS URLS
    path('messages/broadcast/', views.broadcast_message, name='broadcast_message'),
    path('messages/read/<int:notification_id>/', views.read_notification, name='read_notification'),
    path('messages/inbox/', views.notification_list, name='notification_list'),










]