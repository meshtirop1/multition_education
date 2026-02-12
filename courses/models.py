from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Course(models.Model):
    """AI Course model."""
    LEVEL_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    CATEGORY_CHOICES = (
        ('ml', 'Machine Learning'),
        ('dl', 'Deep Learning'),
        ('nlp', 'Natural Language Processing'),
        ('cv', 'Computer Vision'),
        ('rl', 'Reinforcement Learning'),
        ('genai', 'Generative AI'),
        ('data', 'Data Science & AI'),
        ('ethics', 'AI Ethics'),
        ('robotics', 'AI in Robotics'),
        ('other', 'Other AI Topics'),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='ml')
    level = models.CharField(max_length=15, choices=LEVEL_CHOICES, default='beginner')
    thumbnail = models.ImageField(upload_to='course_images/', blank=True, null=True)
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='mentored_courses',
        limit_choices_to={'role': 'mentor'}
    )
    duration_hours = models.PositiveIntegerField(default=0, help_text='Estimated hours to complete')
    is_published = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    max_students = models.PositiveIntegerField(default=100)
    is_free = models.BooleanField(default=True, help_text='Free courses require no payment')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Price in USD (0 for free)')
    price_kes = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Price in KES for M-Pesa (0 = auto-convert from USD)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_courses'
    )

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure unique slug
            counter = 1
            original_slug = self.slug
            while Course.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def total_modules(self):
        return self.modules.count()

    @property
    def total_exercises(self):
        return Exercise.objects.filter(module__course=self).count()

    @property
    def enrolled_count(self):
        return self.enrollments.filter(is_active=True).count()


class Module(models.Model):
    """Course module/chapter."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content = models.TextField(help_text='Module content (supports HTML)')
    order = models.PositiveIntegerField(default=0)
    video_url = models.URLField(blank=True, help_text='YouTube or video URL')
    resources = models.TextField(blank=True, help_text='Additional resources/links')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        unique_together = ['course', 'order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def total_exercises(self):
        return self.exercises.count()


class Exercise(models.Model):
    """Module exercise/assignment."""
    EXERCISE_TYPES = (
        ('quiz', 'Multiple Choice Quiz'),
        ('text', 'Text Answer'),
        ('code', 'Code Exercise'),
        ('file', 'File Upload'),
    )

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='exercises')
    title = models.CharField(max_length=200)
    description = models.TextField()
    exercise_type = models.CharField(max_length=10, choices=EXERCISE_TYPES, default='text')
    points = models.PositiveIntegerField(default=10)
    order = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3, help_text='Maximum attempts allowed (0 = unlimited)')

    # For quiz type
    option_a = models.CharField(max_length=300, blank=True)
    option_b = models.CharField(max_length=300, blank=True)
    option_c = models.CharField(max_length=300, blank=True)
    option_d = models.CharField(max_length=300, blank=True)
    correct_answer = models.CharField(max_length=1, blank=True, help_text='A, B, C, or D')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.module.title} - {self.title}"


class Enrollment(models.Model):
    """Student course enrollment."""
    STATUS_CHOICES = (
        ('enrolled', 'Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='enrolled')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    mentor_approved = models.BooleanField(default=False)
    current_module = models.ForeignKey(
        Module, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='current_students'
    )

    class Meta:
        unique_together = ['student', 'course']
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

    @property
    def progress_percentage(self):
        total_exercises = self.course.total_exercises
        if total_exercises == 0:
            return 0
        completed = ExerciseSubmission.objects.filter(
            student=self.student,
            exercise__module__course=self.course,
            is_completed=True,
            is_correct=True
        ).values('exercise').distinct().count()
        return int((completed / total_exercises) * 100)

    @property
    def all_exercises_completed(self):
        total = self.course.total_exercises
        if total == 0:
            return False
        completed = ExerciseSubmission.objects.filter(
            student=self.student,
            exercise__module__course=self.course,
            is_completed=True,
            is_correct=True
        ).values('exercise').distinct().count()
        return completed >= total

    def is_module_unlocked(self, module):
        """Check if a module is unlocked (all previous modules passed)."""
        if module.order == 1:
            return True
        previous_modules = self.course.modules.filter(order__lt=module.order)
        for prev_module in previous_modules:
            if not self.is_module_passed(prev_module):
                return False
        return True

    def is_module_passed(self, module):
        """Check if all exercises in a module are passed."""
        total = module.exercises.count()
        if total == 0:
            return True
        passed = ExerciseSubmission.objects.filter(
            student=self.student,
            exercise__module=module,
            is_completed=True,
            is_correct=True
        ).values('exercise').distinct().count()
        return passed >= total


class ExerciseSubmission(models.Model):
    """Student exercise submission (supports multiple attempts)."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='submissions'
    )
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='submissions')
    attempt_number = models.PositiveIntegerField(default=1)
    answer = models.TextField(blank=True)
    file_upload = models.FileField(upload_to='submissions/', blank=True, null=True)
    is_completed = models.BooleanField(default=False)
    is_correct = models.BooleanField(default=False)
    score = models.PositiveIntegerField(default=0)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='graded_submissions'
    )

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['student', 'exercise', 'attempt_number']

    def __str__(self):
        return f"{self.student.username} - {self.exercise.title} (Attempt {self.attempt_number})"

    @classmethod
    def get_best_submission(cls, student, exercise):
        """Get the best (highest score) submission for a student-exercise pair."""
        return cls.objects.filter(
            student=student, exercise=exercise
        ).order_by('-score', '-submitted_at').first()

    @classmethod
    def get_attempt_count(cls, student, exercise):
        """Get total attempts for a student-exercise pair."""
        return cls.objects.filter(student=student, exercise=exercise).count()

    @classmethod
    def has_passed(cls, student, exercise):
        """Check if student has a correct submission."""
        return cls.objects.filter(
            student=student, exercise=exercise, is_correct=True
        ).exists()


class ModuleContentView(models.Model):
    """Track when students view/review module content."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='module_views'
    )
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='content_views')
    last_viewed_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ['student', 'module']

    def __str__(self):
        return f"{self.student.username} viewed {self.module.title}"
