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