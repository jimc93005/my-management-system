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










]