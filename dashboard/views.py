from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from accounts.models import CustomUser
from accounts.forms import MentorCreationForm
from courses.models import Course, Module, Exercise, Enrollment, ExerciseSubmission
from courses.forms import CourseForm, ModuleForm, ExerciseForm, GradeSubmissionForm
from certificates.models import Certificate
from certificates.generator import generate_certificate_pdf
from notifications.utils import create_notification


def admin_or_mentor_required(view_func):
    """Decorator for admin/mentor only views."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role not in ('admin', 'mentor') and not request.user.is_superuser:
            messages.error(request, 'Access denied.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_required(view_func):
    """Decorator for admin only views."""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role != 'admin' and not request.user.is_superuser:
            messages.error(request, 'Admin access required.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
def dashboard_home(request):
    """Route to appropriate dashboard based on role."""
    user = request.user
    if user.is_superuser or user.role == 'admin':
        return redirect('dashboard:admin_dashboard')
    elif user.role == 'mentor':
        return redirect('dashboard:mentor_dashboard')
    else:
        return redirect('dashboard:student_dashboard')


# ==================== STUDENT DASHBOARD ====================

@login_required
def student_dashboard(request):
    """Student main dashboard."""
    user = request.user
    enrollments = Enrollment.objects.filter(student=user, is_active=True).select_related('course', 'course__mentor')

    # Stats
    total_enrolled = enrollments.count()
    in_progress = enrollments.filter(status='in_progress').count()
    completed = enrollments.filter(status='completed').count()
    certificates = Certificate.objects.filter(student=user)

    # Recent activity
    recent_submissions = ExerciseSubmission.objects.filter(
        student=user
    ).select_related('exercise', 'exercise__module__course').order_by('-submitted_at')[:5]

    context = {
        'enrollments': enrollments,
        'total_enrolled': total_enrolled,
        'in_progress': in_progress,
        'completed': completed,
        'certificates': certificates,
        'recent_submissions': recent_submissions,
    }
    return render(request, 'dashboard/student_dashboard.html', context)


# ==================== MENTOR DASHBOARD ====================

@login_required
def mentor_dashboard(request):
    """Mentor main dashboard."""
    user = request.user
    if user.role != 'mentor' and not user.is_superuser:
        return redirect('dashboard:home')

    courses = Course.objects.filter(mentor=user)
    pending_submissions = ExerciseSubmission.objects.filter(
        exercise__module__course__mentor=user,
        is_completed=False,
    ).exclude(
        exercise__exercise_type='quiz'
    ).select_related('student', 'exercise', 'exercise__module__course')

    # Students awaiting completion approval
    pending_approvals = Enrollment.objects.filter(
        course__mentor=user,
        status='completed',
        mentor_approved=False,
    ).select_related('student', 'course')

    total_students = Enrollment.objects.filter(
        course__mentor=user, is_active=True
    ).values('student').distinct().count()

    context = {
        'courses': courses,
        'pending_submissions': pending_submissions,
        'pending_approvals': pending_approvals,
        'total_students': total_students,
    }
    return render(request, 'dashboard/mentor_dashboard.html', context)


@login_required
def mentor_course_detail(request, slug):
    """Mentor view of a specific course."""
    course = get_object_or_404(Course, slug=slug, mentor=request.user)
    enrollments = Enrollment.objects.filter(course=course, is_active=True).select_related('student')
    modules = course.modules.all().prefetch_related('exercises')

    submissions = ExerciseSubmission.objects.filter(
        exercise__module__course=course,
        is_completed=False,
    ).exclude(exercise__exercise_type='quiz').select_related('student', 'exercise')

    context = {
        'course': course,
        'enrollments': enrollments,
        'modules': modules,
        'submissions': submissions,
    }
    return render(request, 'dashboard/mentor_course_detail.html', context)


@login_required
def grade_submission(request, submission_id):
    """Mentor grades a submission."""
    submission = get_object_or_404(ExerciseSubmission, pk=submission_id)
    course = submission.exercise.module.course

    if course.mentor != request.user and not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard:mentor_dashboard')

    if request.method == 'POST':
        form = GradeSubmissionForm(request.POST)
        if form.is_valid():
            submission.score = form.cleaned_data['score']
            submission.feedback = form.cleaned_data['feedback']
            submission.is_completed = form.cleaned_data.get('is_completed', False)
            if submission.is_completed:
                submission.is_correct = True
            submission.graded_by = request.user
            submission.graded_at = timezone.now()
            submission.save()

            create_notification(
                recipient=submission.student,
                title='Exercise Graded',
                message=f'Your submission for "{submission.exercise.title}" has been graded. Score: {submission.score}/{submission.exercise.points}',
                notification_type='info',
                link=f'/courses/{course.slug}/module/{submission.exercise.module.id}/'
            )

            # Check if student completed all exercises
            enrollment = Enrollment.objects.filter(
                student=submission.student, course=course
            ).first()
            if enrollment and enrollment.all_exercises_completed:
                enrollment.status = 'completed'
                enrollment.completed_at = timezone.now()
                enrollment.save()

            messages.success(request, 'Submission graded successfully!')
            return redirect('dashboard:mentor_course_detail', slug=course.slug)
    else:
        form = GradeSubmissionForm(initial={
            'score': submission.exercise.points,
            'is_completed': True,
        })

    context = {
        'submission': submission,
        'form': form,
        'course': course,
    }
    return render(request, 'dashboard/grade_submission.html', context)


@login_required
@require_POST
def approve_completion(request, enrollment_id):
    """Mentor approves student completion and triggers certificate."""
    enrollment = get_object_or_404(Enrollment, pk=enrollment_id)
    course = enrollment.course

    if course.mentor != request.user and not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('dashboard:mentor_dashboard')

    if not enrollment.all_exercises_completed:
        messages.error(request, 'Student has not completed all exercises.')
        return redirect('dashboard:mentor_course_detail', slug=course.slug)

    enrollment.mentor_approved = True
    enrollment.save()

    # Generate certificate
    cert, created = Certificate.objects.get_or_create(
        student=enrollment.student,
        course=course,
        defaults={
            'enrollment': enrollment,
            'approved_by': request.user,
        }
    )
    if created:
        generate_certificate_pdf(cert)

    create_notification(
        recipient=enrollment.student,
        title='Certificate Issued!',
        message=f'Congratulations! Your completion of "{course.title}" has been approved. Your certificate is ready for download!',
        notification_type='success',
        link='/certificates/'
    )

    messages.success(request, f'Approved! Certificate generated for {enrollment.student.username}.')
    return redirect('dashboard:mentor_course_detail', slug=course.slug)


# ==================== ADMIN DASHBOARD ====================

@admin_required
def admin_dashboard(request):
    """Admin main dashboard."""
    total_students = CustomUser.objects.filter(role='student').count()
    pending_students = CustomUser.objects.filter(role='student', status='pending').count()
    total_mentors = CustomUser.objects.filter(role='mentor').count()
    total_courses = Course.objects.count()
    published_courses = Course.objects.filter(is_published=True).count()
    total_enrollments = Enrollment.objects.filter(is_active=True).count()
    total_certificates = Certificate.objects.count()

    recent_students = CustomUser.objects.filter(role='student').order_by('-date_joined')[:10]

    context = {
        'total_students': total_students,
        'pending_students': pending_students,
        'total_mentors': total_mentors,
        'total_courses': total_courses,
        'published_courses': published_courses,
        'total_enrollments': total_enrollments,
        'total_certificates': total_certificates,
        'recent_students': recent_students,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


@admin_required
def admin_students(request):
    """Admin student management."""
    status_filter = request.GET.get('status', '')
    students = CustomUser.objects.filter(role='student')
    if status_filter:
        students = students.filter(status=status_filter)
    students = students.order_by('-date_joined')

    context = {
        'students': students,
        'current_status': status_filter,
    }
    return render(request, 'dashboard/admin_students.html', context)


@admin_required
@require_POST
def admin_approve_student(request, pk):
    """Approve a student."""
    student = get_object_or_404(CustomUser, pk=pk, role='student')
    student.status = 'approved'
    student.save()

    create_notification(
        recipient=student,
        title='Account Approved!',
        message='Your account has been approved. You can now browse and enroll in courses!',
        notification_type='success',
        link='/courses/'
    )
    messages.success(request, f'{student.username} approved.')
    return redirect('dashboard:admin_students')


@admin_required
@require_POST
def admin_reject_student(request, pk):
    """Reject a student."""
    student = get_object_or_404(CustomUser, pk=pk, role='student')
    student.status = 'rejected'
    student.save()

    create_notification(
        recipient=student,
        title='Account Not Approved',
        message='Unfortunately, your registration was not approved at this time.',
        notification_type='warning'
    )
    messages.info(request, f'{student.username} rejected.')
    return redirect('dashboard:admin_students')


@admin_required
def admin_mentors(request):
    """Admin mentor management."""
    mentors = CustomUser.objects.filter(role='mentor').order_by('-date_joined')
    context = {'mentors': mentors}
    return render(request, 'dashboard/admin_mentors.html', context)


@admin_required
def admin_create_mentor(request):
    """Admin creates a new mentor."""
    if request.method == 'POST':
        form = MentorCreationForm(request.POST)
        if form.is_valid():
            mentor = form.save()
            create_notification(
                recipient=mentor,
                title='Welcome, Mentor!',
                message='Your mentor account has been created on MultiTion Education.',
                notification_type='success',
                link='/dashboard/'
            )
            messages.success(request, f'Mentor {mentor.username} created successfully!')
            return redirect('dashboard:admin_mentors')
    else:
        form = MentorCreationForm()

    return render(request, 'dashboard/admin_create_mentor.html', {'form': form})


@admin_required
def admin_courses(request):
    """Admin course management."""
    courses = Course.objects.all().select_related('mentor', 'created_by')
    context = {'courses': courses}
    return render(request, 'dashboard/admin_courses.html', context)


@admin_required
def admin_create_course(request):
    """Admin creates a new course."""
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            course.save()
            messages.success(request, f'Course "{course.title}" created!')
            return redirect('dashboard:admin_edit_course', slug=course.slug)
    else:
        form = CourseForm()

    context = {'form': form, 'action': 'Create'}
    return render(request, 'dashboard/admin_course_form.html', context)


@admin_required
def admin_edit_course(request, slug):
    """Admin edits a course with modules and exercises."""
    course = get_object_or_404(Course, slug=slug)
    modules = course.modules.all().prefetch_related('exercises')

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated!')
            return redirect('dashboard:admin_edit_course', slug=course.slug)
    else:
        form = CourseForm(instance=course)

    context = {
        'form': form,
        'course': course,
        'modules': modules,
        'action': 'Edit',
    }
    return render(request, 'dashboard/admin_course_form.html', context)


@admin_required
def admin_add_module(request, slug):
    """Add a module to a course."""
    course = get_object_or_404(Course, slug=slug)

    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            messages.success(request, f'Module "{module.title}" added!')
            return redirect('dashboard:admin_edit_course', slug=course.slug)
    else:
        next_order = course.modules.count() + 1
        form = ModuleForm(initial={'order': next_order})

    context = {'form': form, 'course': course, 'action': 'Add Module'}
    return render(request, 'dashboard/admin_module_form.html', context)


@admin_required
def admin_edit_module(request, slug, module_id):
    """Edit a module."""
    course = get_object_or_404(Course, slug=slug)
    module = get_object_or_404(Module, pk=module_id, course=course)

    if request.method == 'POST':
        form = ModuleForm(request.POST, instance=module)
        if form.is_valid():
            form.save()
            messages.success(request, 'Module updated!')
            return redirect('dashboard:admin_edit_course', slug=course.slug)
    else:
        form = ModuleForm(instance=module)

    context = {
        'form': form,
        'course': course,
        'module': module,
        'action': 'Edit Module',
        'exercises': module.exercises.all(),
    }
    return render(request, 'dashboard/admin_module_form.html', context)


@admin_required
def admin_add_exercise(request, slug, module_id):
    """Add an exercise to a module."""
    course = get_object_or_404(Course, slug=slug)
    module = get_object_or_404(Module, pk=module_id, course=course)

    if request.method == 'POST':
        form = ExerciseForm(request.POST)
        if form.is_valid():
            exercise = form.save(commit=False)
            exercise.module = module
            exercise.save()
            messages.success(request, f'Exercise "{exercise.title}" added!')
            return redirect('dashboard:admin_edit_module', slug=course.slug, module_id=module.id)
    else:
        next_order = module.exercises.count() + 1
        form = ExerciseForm(initial={'order': next_order})

    context = {'form': form, 'course': course, 'module': module, 'action': 'Add Exercise'}
    return render(request, 'dashboard/admin_exercise_form.html', context)


@admin_required
def admin_edit_exercise(request, slug, module_id, exercise_id):
    """Edit an exercise."""
    course = get_object_or_404(Course, slug=slug)
    module = get_object_or_404(Module, pk=module_id, course=course)
    exercise = get_object_or_404(Exercise, pk=exercise_id, module=module)

    if request.method == 'POST':
        form = ExerciseForm(request.POST, instance=exercise)
        if form.is_valid():
            form.save()
            messages.success(request, 'Exercise updated!')
            return redirect('dashboard:admin_edit_module', slug=course.slug, module_id=module.id)
    else:
        form = ExerciseForm(instance=exercise)

    context = {'form': form, 'course': course, 'module': module, 'exercise': exercise, 'action': 'Edit Exercise'}
    return render(request, 'dashboard/admin_exercise_form.html', context)


# ==================== ENHANCED MENTOR FEATURES ====================

@login_required
def mentor_students(request, slug):
    """Detailed student analytics for a course."""
    course = get_object_or_404(Course, slug=slug, mentor=request.user)
    enrollments = Enrollment.objects.filter(course=course).select_related('student')

    # Compute analytics
    students_data = []
    for e in enrollments:
        submissions = ExerciseSubmission.objects.filter(
            student=e.student, exercise__module__course=course
        )
        total_subs = submissions.count()
        completed_subs = submissions.filter(is_completed=True).count()
        avg_score = submissions.filter(score__isnull=False).values_list('score', flat=True)
        avg = sum(avg_score) / len(avg_score) if avg_score else 0

        students_data.append({
            'enrollment': e,
            'student': e.student,
            'total_submissions': total_subs,
            'completed_submissions': completed_subs,
            'average_score': round(avg, 1),
            'progress': e.progress_percentage,
        })

    context = {
        'course': course,
        'students_data': students_data,
        'total_enrolled': enrollments.count(),
    }
    return render(request, 'dashboard/mentor_students.html', context)


@login_required
def mentor_announcements(request, slug):
    """Send announcement to all students in a course."""
    course = get_object_or_404(Course, slug=slug, mentor=request.user)

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message_text = request.POST.get('message', '').strip()

        if title and message_text:
            # Notify all enrolled students
            enrollments = Enrollment.objects.filter(course=course, is_active=True)
            count = 0
            for e in enrollments:
                create_notification(
                    recipient=e.student,
                    title=f'📢 {title}',
                    message=f'[{course.title}] {message_text}',
                    notification_type='info',
                    link=f'/courses/{course.slug}/'
                )
                count += 1
            messages.success(request, f'Announcement sent to {count} students!')
            return redirect('dashboard:mentor_course_detail', slug=slug)

    context = {'course': course}
    return render(request, 'dashboard/mentor_announcements.html', context)


@login_required
def mentor_bulk_grade(request, slug):
    """Bulk grade pending submissions for a course."""
    course = get_object_or_404(Course, slug=slug, mentor=request.user)
    # Get latest ungraded non-quiz submissions
    pending = ExerciseSubmission.objects.filter(
        exercise__module__course=course,
        is_completed=False,
    ).exclude(exercise__exercise_type='quiz').select_related(
        'student', 'exercise', 'exercise__module'
    ).order_by('student__username', 'exercise__module__order', 'exercise__order', '-attempt_number')

    if request.method == 'POST':
        graded_count = 0
        for sub in pending:
            score_key = f'score_{sub.id}'
            feedback_key = f'feedback_{sub.id}'
            complete_key = f'complete_{sub.id}'

            if score_key in request.POST:
                score = request.POST.get(score_key)
                if score:
                    sub.score = int(score)
                    sub.feedback = request.POST.get(feedback_key, '')
                    sub.is_completed = complete_key in request.POST
                    # Mark as correct (passed) if score >= 50% of points
                    if sub.is_completed and sub.score >= (sub.exercise.points * 0.5):
                        sub.is_correct = True
                    sub.graded_by = request.user
                    sub.graded_at = timezone.now()
                    sub.save()

                    status = 'passed' if sub.is_correct else 'needs improvement'
                    create_notification(
                        recipient=sub.student,
                        title='Exercise Graded',
                        message=f'"{sub.exercise.title}" graded: {sub.score}/{sub.exercise.points} ({status})',
                        notification_type='success' if sub.is_correct else 'warning',
                    )
                    graded_count += 1

        messages.success(request, f'{graded_count} submissions graded!')
        return redirect('dashboard:mentor_course_detail', slug=slug)

    context = {'course': course, 'pending': pending}
    return render(request, 'dashboard/mentor_bulk_grade.html', context)


@login_required
def mentor_course_analytics(request, slug):
    """Course analytics and statistics for mentor."""
    course = get_object_or_404(Course, slug=slug, mentor=request.user)
    enrollments = Enrollment.objects.filter(course=course)
    submissions = ExerciseSubmission.objects.filter(exercise__module__course=course)

    total_enrolled = enrollments.count()
    active = enrollments.filter(status='in_progress').count()
    completed = enrollments.filter(status='completed').count()
    total_submissions = submissions.count()
    graded = submissions.filter(is_completed=True).count()
    pending = submissions.filter(is_completed=False).exclude(exercise__exercise_type='quiz').count()

    # Average progress
    progress_list = [e.progress_percentage for e in enrollments]
    avg_progress = round(sum(progress_list) / len(progress_list), 1) if progress_list else 0

    # Per-module stats
    module_stats = []
    for module in course.modules.all():
        exercises = module.exercises.all()
        total_ex = exercises.count()
        subs = ExerciseSubmission.objects.filter(exercise__module=module)
        module_stats.append({
            'module': module,
            'total_exercises': total_ex,
            'total_submissions': subs.count(),
            'completed': subs.filter(is_completed=True).count(),
        })

    context = {
        'course': course,
        'total_enrolled': total_enrolled,
        'active': active,
        'completed': completed,
        'total_submissions': total_submissions,
        'graded': graded,
        'pending': pending,
        'avg_progress': avg_progress,
        'module_stats': module_stats,
    }
    return render(request, 'dashboard/mentor_analytics.html', context)
@admin_required
def admin_payments(request):
    """Admin payment tracking dashboard."""
    from billing.models import Payment
    from django.db.models import Sum, Count

    status_filter = request.GET.get('status', '')
    provider_filter = request.GET.get('provider', '')

    payments = Payment.objects.all().select_related('student', 'course')

    if status_filter:
        payments = payments.filter(status=status_filter)
    if provider_filter:
        payments = payments.filter(provider=provider_filter)

    # Stats
    total_revenue = Payment.objects.filter(status='completed', currency='USD').aggregate(
        total=Sum('amount'))['total'] or 0
    total_revenue_kes = Payment.objects.filter(status='completed', currency='KES').aggregate(
        total=Sum('amount'))['total'] or 0
    total_transactions = Payment.objects.filter(status='completed').count()
    pending_count = Payment.objects.filter(status='pending').count()
    failed_count = Payment.objects.filter(status='failed').count()

    # Per-provider breakdown
    paystack_revenue = Payment.objects.filter(status='completed', provider='paystack').aggregate(
        total=Sum('amount'))['total'] or 0
    mpesa_revenue = Payment.objects.filter(status='completed', provider='mpesa').aggregate(
        total=Sum('amount'))['total'] or 0

    context = {
        'payments': payments.order_by('-created_at'),
        'total_revenue': total_revenue,
        'total_revenue_kes': total_revenue_kes,
        'total_transactions': total_transactions,
        'pending_count': pending_count,
        'failed_count': failed_count,
        'paystack_revenue': paystack_revenue,
        'mpesa_revenue': mpesa_revenue,
        'current_status': status_filter,
        'current_provider': provider_filter,
    }
    return render(request, 'dashboard/admin_payments.html', context)