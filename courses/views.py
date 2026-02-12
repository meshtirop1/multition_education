from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count

from .models import Course, Module, Exercise, Enrollment, ExerciseSubmission, ModuleContentView
from .forms import ExerciseSubmissionForm
from notifications.utils import create_notification


def course_list(request):
    """Browse all published courses."""
    courses = Course.objects.filter(is_published=True)

    # Filters
    category = request.GET.get('category')
    level = request.GET.get('level')
    search = request.GET.get('search')

    if category:
        courses = courses.filter(category=category)
    if level:
        courses = courses.filter(level=level)
    if search:
        courses = courses.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    context = {
        'courses': courses,
        'categories': Course.CATEGORY_CHOICES,
        'levels': Course.LEVEL_CHOICES,
        'current_category': category,
        'current_level': level,
        'search_query': search or '',
    }
    return render(request, 'courses/course_list.html', context)


def course_detail(request, slug):
    """Course detail page."""
    course = get_object_or_404(Course, slug=slug, is_published=True)
    modules = list(course.modules.all().prefetch_related('exercises'))
    enrollment = None
    progress = 0

    if request.user.is_authenticated:
        enrollment = Enrollment.objects.filter(
            student=request.user, course=course
        ).first()
        if enrollment:
            progress = enrollment.progress_percentage
            # Attach lock/pass status to modules
            for m in modules:
                m.is_unlocked = enrollment.is_module_unlocked(m)
                m.is_passed = enrollment.is_module_passed(m)

    context = {
        'course': course,
        'modules': modules,
        'enrollment': enrollment,
        'progress': progress,
    }
    return render(request, 'courses/course_detail.html', context)


@login_required
def enroll_course(request, slug):
    """Enroll in a course."""
    course = get_object_or_404(Course, slug=slug, is_published=True)

    if not request.user.is_approved:
        messages.warning(request, 'Your account must be approved before enrolling in courses.')
        return redirect('courses:detail', slug=slug)

    if request.user.role != 'student':
        messages.error(request, 'Only students can enroll in courses.')
        return redirect('courses:detail', slug=slug)

    # Check if paid course requires payment
    if not course.is_free:
        from payments.models import Payment
        if not Payment.has_paid(request.user, course):
            return redirect('payments:checkout', slug=slug)

    enrollment, created = Enrollment.objects.get_or_create(
        student=request.user, course=course,
        defaults={'status': 'enrolled'}
    )

    if created:
        # If paid course and no payment, redirect to checkout
        if not course.is_free and course.price > 0:
            from billing.models import Payment
            has_paid = Payment.objects.filter(
                student=request.user, course=course, status='completed'
            ).exists()
            if not has_paid:
                # Remove the enrollment we just created
                enrollment.delete()
                return redirect('billing:checkout', slug=slug)

        messages.success(request, f'Successfully enrolled in {course.title}!')
        # Notify mentor
        if course.mentor:
            create_notification(
                recipient=course.mentor,
                title='New Student Enrolled',
                message=f'{request.user.get_full_name() or request.user.username} enrolled in {course.title}.',
                notification_type='info',
                link=f'/dashboard/mentor/course/{course.slug}/'
            )
    else:
        messages.info(request, 'You are already enrolled in this course.')

    return redirect('courses:detail', slug=slug)


@login_required
def module_detail(request, slug, module_id):
    """View module content and exercises."""
    course = get_object_or_404(Course, slug=slug)
    module = get_object_or_404(Module, pk=module_id, course=course)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)

    # Check if module is unlocked
    is_unlocked = enrollment.is_module_unlocked(module)
    if not is_unlocked:
        # Find the first incomplete module
        for m in course.modules.all():
            if not enrollment.is_module_passed(m):
                messages.warning(
                    request,
                    f'You must pass all exercises in "{m.title}" before accessing this module.'
                )
                return redirect('courses:module_detail', slug=slug, module_id=m.pk)
        messages.warning(request, 'This module is locked. Complete previous modules first.')
        return redirect('courses:detail', slug=slug)

    # Track content view (for "must review before retry" logic)
    content_view, created = ModuleContentView.objects.get_or_create(
        student=request.user, module=module
    )
    if not created:
        content_view.view_count += 1
        content_view.save()

    exercises = module.exercises.all()

    # Build submission info per exercise with attempt tracking
    for ex in exercises:
        best = ExerciseSubmission.get_best_submission(request.user, ex)
        attempts_used = ExerciseSubmission.get_attempt_count(request.user, ex)
        has_passed = ExerciseSubmission.has_passed(request.user, ex)
        max_att = ex.max_attempts if ex.max_attempts > 0 else None

        # Check if must review content before retrying
        needs_review = False
        if attempts_used > 0 and not has_passed and best and not best.is_correct:
            last_failed = ExerciseSubmission.objects.filter(
                student=request.user, exercise=ex, is_correct=False
            ).order_by('-submitted_at').first()
            if last_failed:
                needs_review = content_view.last_viewed_at <= last_failed.submitted_at

        can_retry = (
            not has_passed
            and (max_att is None or attempts_used < max_att)
            and not needs_review
        )
        out_of_attempts = (max_att is not None and attempts_used >= max_att and not has_passed)

        # Attach to exercise object for template access
        ex.best_submission = best
        ex.attempts_used = attempts_used
        ex.max_att = max_att
        ex.attempts_remaining = (max_att - attempts_used) if max_att else None
        ex.has_passed = has_passed
        ex.can_retry = can_retry
        ex.needs_review = needs_review
        ex.out_of_attempts = out_of_attempts

    # Update current module
    enrollment.current_module = module
    if enrollment.status == 'enrolled':
        enrollment.status = 'in_progress'
    enrollment.save()

    # Check module lock status for sidebar
    all_modules = list(course.modules.all())
    for m in all_modules:
        m.is_unlocked = enrollment.is_module_unlocked(m)
        m.is_passed = enrollment.is_module_passed(m)

    context = {
        'course': course,
        'module': module,
        'exercises': exercises,
        'enrollment': enrollment,
        'modules': all_modules,
    }
    return render(request, 'courses/module_detail.html', context)


@login_required
def submit_exercise(request, slug, module_id, exercise_id):
    """Submit an exercise answer with attempt tracking."""
    course = get_object_or_404(Course, slug=slug)
    module = get_object_or_404(Module, pk=module_id, course=course)
    exercise = get_object_or_404(Exercise, pk=exercise_id, module=module)
    enrollment = get_object_or_404(Enrollment, student=request.user, course=course)

    # Check module is unlocked
    if not enrollment.is_module_unlocked(module):
        messages.error(request, 'This module is locked. Complete previous modules first.')
        return redirect('courses:detail', slug=slug)

    # Check if already passed
    if ExerciseSubmission.has_passed(request.user, exercise):
        messages.info(request, 'You have already passed this exercise.')
        return redirect('courses:module_detail', slug=slug, module_id=module_id)

    # Check attempt limits
    attempts_used = ExerciseSubmission.get_attempt_count(request.user, exercise)
    max_attempts = exercise.max_attempts if exercise.max_attempts > 0 else None

    if max_attempts and attempts_used >= max_attempts:
        messages.error(request, f'You have used all {max_attempts} attempts for this exercise. Contact your mentor for help.')
        return redirect('courses:module_detail', slug=slug, module_id=module_id)

    # Check must-review-content-before-retry
    if attempts_used > 0:
        content_view = ModuleContentView.objects.filter(
            student=request.user, module=module
        ).first()
        last_failed = ExerciseSubmission.objects.filter(
            student=request.user, exercise=exercise, is_correct=False
        ).order_by('-submitted_at').first()

        if last_failed and content_view:
            if content_view.last_viewed_at <= last_failed.submitted_at:
                messages.warning(
                    request,
                    'You must review the module content before retrying. Please read through the lesson material above, then try again.'
                )
                return redirect('courses:module_detail', slug=slug, module_id=module_id)

    existing_best = ExerciseSubmission.get_best_submission(request.user, exercise)

    if request.method == 'POST':
        form = ExerciseSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            new_attempt = attempts_used + 1

            submission = ExerciseSubmission(
                student=request.user,
                exercise=exercise,
                attempt_number=new_attempt,
                answer=form.cleaned_data.get('answer', ''),
                file_upload=form.cleaned_data.get('file_upload'),
            )

            # Auto-grade quiz type
            if exercise.exercise_type == 'quiz':
                selected = request.POST.get('selected_option', '').upper()
                submission.answer = selected
                if selected == exercise.correct_answer.upper():
                    submission.is_correct = True
                    submission.is_completed = True
                    submission.score = exercise.points
                    submission.graded_at = timezone.now()
                    messages.success(request, f'Correct! Exercise completed. ({new_attempt}/{max_attempts or "∞"} attempts used)')
                else:
                    submission.is_correct = False
                    submission.is_completed = True
                    submission.score = 0
                    submission.graded_at = timezone.now()

                    remaining = (max_attempts - new_attempt) if max_attempts else None

                    if remaining is not None and remaining == 0:
                        messages.error(
                            request,
                            f'Incorrect. The correct answer was {exercise.correct_answer}. '
                            f'You have used all {max_attempts} attempts. Your mentor has been notified.'
                        )
                        # Notify mentor — out of attempts
                        if course.mentor:
                            create_notification(
                                recipient=course.mentor,
                                title='⚠️ Student Out of Attempts',
                                message=f'{request.user.get_full_name() or request.user.username} has exhausted all {max_attempts} attempts on "{exercise.title}" in {course.title} without passing. They may need additional support.',
                                notification_type='warning',
                                link=f'/dashboard/mentor/course/{course.slug}/students/'
                            )
                    elif remaining is not None:
                        messages.warning(
                            request,
                            f'Incorrect. You have {remaining} attempt(s) remaining. '
                            f'Review the module content before trying again.'
                        )
                    else:
                        messages.warning(
                            request,
                            f'Incorrect. Review the module content before trying again.'
                        )

                    # Auto-notify mentor after 2+ failures
                    if new_attempt >= 2 and course.mentor:
                        create_notification(
                            recipient=course.mentor,
                            title='🔔 Student Struggling',
                            message=f'{request.user.get_full_name() or request.user.username} has failed "{exercise.title}" {new_attempt} time(s) in {course.title}. Consider reaching out to offer support.',
                            notification_type='warning',
                            link=f'/messages/compose/?to={request.user.username}'
                        )

                submission.save()
            else:
                # Text/code/file — mentor graded
                submission.save()
                messages.success(request, f'Answer submitted (Attempt {new_attempt}). Waiting for mentor review.')
                if course.mentor:
                    create_notification(
                        recipient=course.mentor,
                        title='New Exercise Submission',
                        message=f'{request.user.username} submitted "{exercise.title}" (Attempt {new_attempt}) in {course.title}.',
                        notification_type='info',
                        link=f'/dashboard/mentor/course/{course.slug}/'
                    )

            # Check if all exercises completed (passed)
            if enrollment.all_exercises_completed:
                enrollment.status = 'completed'
                enrollment.completed_at = timezone.now()
                enrollment.save()

                create_notification(
                    recipient=request.user,
                    title='Course Completed!',
                    message=f'Congratulations! You passed all exercises in {course.title}. Awaiting mentor approval for certificate.',
                    notification_type='success',
                    link=f'/dashboard/'
                )
                if course.mentor:
                    create_notification(
                        recipient=course.mentor,
                        title='Student Completed Course',
                        message=f'{request.user.username} completed all exercises in {course.title}. Please review and approve.',
                        notification_type='info',
                        link=f'/dashboard/mentor/course/{course.slug}/'
                    )

            return redirect('courses:module_detail', slug=slug, module_id=module_id)
    else:
        form = ExerciseSubmissionForm()

    context = {
        'course': course,
        'module': module,
        'exercise': exercise,
        'form': form,
        'existing': existing_best,
        'attempts_used': attempts_used,
        'max_attempts': max_attempts,
        'attempts_remaining': (max_attempts - attempts_used) if max_attempts else None,
    }
    return render(request, 'courses/submit_exercise.html', context)


@login_required
def submission_result(request, slug, module_id, exercise_id):
    """View submission result and feedback."""
    course = get_object_or_404(Course, slug=slug)
    module = get_object_or_404(Module, pk=module_id, course=course)
    exercise = get_object_or_404(Exercise, pk=exercise_id, module=module)

    # Get best submission
    submission = ExerciseSubmission.get_best_submission(request.user, exercise)
    if not submission:
        messages.info(request, 'No submission found for this exercise.')
        return redirect('courses:module_detail', slug=slug, module_id=module_id)

    # Get all attempts for this exercise
    all_attempts = ExerciseSubmission.objects.filter(
        student=request.user, exercise=exercise
    ).order_by('attempt_number')

    context = {
        'course': course,
        'module': module,
        'exercise': exercise,
        'submission': submission,
        'all_attempts': all_attempts,
        'total_attempts': all_attempts.count(),
    }
    return render(request, 'courses/submission_result.html', context)
