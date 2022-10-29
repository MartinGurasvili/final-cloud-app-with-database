from django.contrib import admin
# <HINT> Import any new Models here
from .models import Course, Lesson, Instructor, Learner, Choice, Question

# Register QuestionInline and ChoiceInline classes here
class QuestionInLine(admin.StackedInline):
    model = Question
    extra = 1

class ChoiceInLine(admin.StackedInline):
    model = Choice
    extra = 1

class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1

# Register your models here.
class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline]
    list_display = ('name', 'pub_date')
    list_filter = ['pub_date']
    search_fields = ['name', 'description']

class LessonAdmin(admin.ModelAdmin):
    list_display = ['title']

class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInLine]
    list_display = ['course', 'text', 'mark', 'is_partially_correct_accepted']
    list_filter = ['course']
    search_fields = ['text']

class ChoiceAdmin(admin.ModelAdmin):
    list_display = ['question', 'text', 'is_correct']
    list_filter = ['question']
    search_fields = ['text']


# <HINT> Register Question and Choice models here
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)

admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Instructor)
admin.site.register(Learner)
