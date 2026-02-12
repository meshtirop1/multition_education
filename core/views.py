from django.shortcuts import render
from courses.models import Course


def home(request):
    """Landing page."""
    featured_courses = Course.objects.filter(is_published=True, is_featured=True)[:6]
    all_courses = Course.objects.filter(is_published=True)[:8]
    total_courses = Course.objects.filter(is_published=True).count()

    context = {
        'featured_courses': featured_courses,
        'courses': all_courses,
        'total_courses': total_courses,
    }
    return render(request, 'core/home.html', context)


def about(request):
    return render(request, 'core/about.html')


def privacy_policy(request):
    """Privacy policy page."""
    return render(request, 'core/privacy.html')


def terms_of_service(request):
    """Terms of service page."""
    return render(request, 'core/terms.html')
