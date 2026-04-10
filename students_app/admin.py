from django.contrib import admin

from .models import Students
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

# users/admin.py
