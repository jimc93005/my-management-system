from django.contrib import admin

from .models import Students, AttendanceWarning
from .models import Subject
from .models import Grade
from .models import SchoolProfile
from .models import Department
from .models import SubDepartment
from .models import SubDepartmentRole
from .models import Teacher
from .models import DepartmentEvent
from .models import ClassLevel
from .models import TeachingAssignment
from .models import SubjectDepartment
from .models import Attendance
from .models import AttendanceWarning
from .models import GradeBoundary
from .models import GradingSystem
from .models import CalendarEvent



admin.site.register(Students)
admin.site.register(Subject)
admin.site.register(Grade)
admin.site.register(SchoolProfile)
admin.site.register(Department)
admin.site.register(SubDepartment)
admin.site.register(SubDepartmentRole)
admin.site.register(Teacher)
admin.site.register(DepartmentEvent)
admin.site.register(ClassLevel)
admin.site.register(TeachingAssignment)
admin.site.register(SubjectDepartment)
admin.site.register(Attendance)
admin.site.register(AttendanceWarning)
admin.site.register(GradeBoundary)
admin.site.register(GradingSystem)
admin.site.register(CalendarEvent)

# users/admin.py


from django.contrib import admin
from .models import Folder, Document

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'folder', 'uploaded_at')
    list_filter = ('folder',)
    search_fields = ('title',)



from django.contrib import admin
from .models import Announcement, NewsArticle, LeadershipProfile

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date_posted', 'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('title', 'content')

@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ('headline', 'publish_date', 'is_active')
    list_filter = ('is_active', 'publish_date')
    search_fields = ('headline', 'summary')

@admin.register(LeadershipProfile)
class LeadershipProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active') # Allows them to re-order directly from the list view!
    ordering = ('display_order',)