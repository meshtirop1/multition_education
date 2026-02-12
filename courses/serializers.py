from rest_framework import serializers
from .models import Course, Module, Exercise, Enrollment, ExerciseSubmission


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ['id', 'title', 'description', 'exercise_type', 'points', 'order',
                  'option_a', 'option_b', 'option_c', 'option_d']


class ModuleSerializer(serializers.ModelSerializer):
    exercises = ExerciseSerializer(many=True, read_only=True)
    total_exercises = serializers.ReadOnlyField()

    class Meta:
        model = Module
        fields = ['id', 'title', 'description', 'content', 'order', 'video_url',
                  'resources', 'exercises', 'total_exercises']


class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    total_modules = serializers.ReadOnlyField()
    total_exercises = serializers.ReadOnlyField()
    enrolled_count = serializers.ReadOnlyField()
    mentor_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'description', 'short_description', 'category',
                  'level', 'thumbnail', 'duration_hours', 'is_published', 'is_featured',
                  'max_students', 'modules', 'total_modules', 'total_exercises',
                  'enrolled_count', 'mentor_name', 'created_at']

    def get_mentor_name(self, obj):
        if obj.mentor:
            return obj.mentor.get_full_name() or obj.mentor.username
        return None


class CourseListSerializer(serializers.ModelSerializer):
    total_modules = serializers.ReadOnlyField()
    enrolled_count = serializers.ReadOnlyField()
    mentor_name = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'short_description', 'category', 'level',
                  'thumbnail', 'duration_hours', 'total_modules', 'enrolled_count',
                  'mentor_name', 'is_featured']

    def get_mentor_name(self, obj):
        if obj.mentor:
            return obj.mentor.get_full_name() or obj.mentor.username
        return None


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    progress = serializers.ReadOnlyField(source='progress_percentage')
    all_completed = serializers.ReadOnlyField(source='all_exercises_completed')

    class Meta:
        model = Enrollment
        fields = ['id', 'course', 'course_title', 'status', 'enrolled_at',
                  'completed_at', 'progress', 'all_completed', 'mentor_approved']
