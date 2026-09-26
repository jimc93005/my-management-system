from django.contrib import admin

from .models import  Timetable, TimetableRoom, TimetableSettings, TimetableBreak
from . models import TimetableEntry, SubjectRoomRequirement, SubjectConstraint

admin.site.register(SubjectRoomRequirement)
admin.site.register(SubjectConstraint)
admin.site.register(Timetable)
admin.site.register(TimetableRoom)
admin.site.register(TimetableEntry)
admin.site.register(TimetableSettings)
admin.site.register(TimetableBreak)
