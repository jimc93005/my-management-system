from django.urls import path
from . import views

app_name = 'timetable'

urlpatterns = [
    path('class/<int:timetable_id>/<int:class_id>/', views.class_timetable_view, name='class_timetable'),
    # You can add teacher and room routes here later using the same pattern
    path('master/<int:timetable_id>/', views.master_timetable_view, name='master_timetable'),
    path('master/<int:timetable_id>/generate/', views.generate_timetable_view, name='generate_timetable'),
    path('master/<int:timetable_id>/pdf/', views.export_timetable_pdf_view, name='export_timetable_pdf'),
    path('master/<int:timetable_id>/full-pdf/', views.export_full_school_pdf_view, name='export_full_school_pdf'),
    path('master/<int:timetable_id>/class-pdf/<int:class_id>/', views.export_class_timetable_pdf_view, name='export_class_timetable_pdf'),

    # TIMETABLE UI URLS
    path('setup/settings/', views.setup_settings_view, name='setup_settings'),
    path('setup/rooms/', views.setup_rooms_view, name='setup_rooms'),
    path('setup/constraints/', views.setup_constraints_view, name='setup_constraints'),
    path('setup/generate/', views.setup_generate_view, name='setup_generate'),
    path('setup/teachers/', views.setup_teachers_view, name='setup_teachers'),
]