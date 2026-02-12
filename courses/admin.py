from django.contrib import admin
from .models import Course, Module, Exercise, Enrollment, ExerciseSubmission


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 1
    fields = ['title', 'exercise_type', 'points', 'order', 'correct_answer']


class ModuleInline(admin.StackedInline):
    model = Module
    extra = 1
    fields = ['title', 'description', 'content', 'order', 'video_url']
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'level', 'mentor', 'is_published', 'is_featured',
                    'enrolled_count', 'total_modules', 'created_at']
    list_filter = ['category', 'level', 'is_published', 'is_featured']
    search_fields = ['title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline]
    list_editable = ['is_published', 'is_featured']

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ['title', 'course', 'order', 'total_exercises']
    list_filter = ['course']
    search_fields = ['title', 'course__title']
    inlines = [ExerciseInline]


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ['title', 'module', 'exercise_type', 'points', 'order']
    list_filter = ['exercise_type', 'module__course']
    search_fields = ['title']


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'course', 'status', 'enrolled_at', 'mentor_approved', 'progress_percentage']
    list_filter = ['status', 'mentor_approved', 'course']
    search_fields = ['student__username', 'course__title']
    list_editable = ['status', 'mentor_approved']


@admin.register(ExerciseSubmission)
class ExerciseSubmissionAdmin(admin.ModelAdmin):
    list_display = ['student', 'exercise', 'is_completed', 'is_correct', 'score', 'submitted_at']
    list_filter = ['is_completed', 'is_correct']
    search_fields = ['student__username', 'exercise__title']
