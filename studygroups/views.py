from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone

from courses.models import Course, Enrollment
from notifications.utils import create_notification
from .models import StudyGroup, Membership, GroupMessage


@login_required
def group_list(request, slug):
    """List study groups for a course."""
    course = get_object_or_404(Course, slug=slug, is_published=True)
    enrollment = Enrollment.objects.filter(
        student=request.user, course=course, is_active=True
    ).first()
    if not enrollment:
        messages.error(request, 'You must be enrolled to view study groups.')
        return redirect('courses:detail', slug=slug)

    groups = StudyGroup.objects.filter(course=course, is_active=True)
    my_groups = Membership.objects.filter(
        student=request.user, group__course=course, is_active=True
    ).values_list('group_id', flat=True)

    context = {
        'course': course,
        'groups': groups,
        'my_groups': list(my_groups),
    }
    return render(request, 'studygroups/group_list.html', context)


@login_required
@require_POST
def create_group(request, slug):
    """Create a new study group."""
    course = get_object_or_404(Course, slug=slug)
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()

    if not name:
        messages.error(request, 'Group name is required.')
        return redirect('studygroups:list', slug=slug)

    group = StudyGroup.objects.create(
        name=name, description=description,
        course=course, created_by=request.user
    )
    Membership.objects.create(
        group=group, student=request.user, role='leader'
    )
    messages.success(request, f'Study group "{name}" created!')
    return redirect('studygroups:chat', slug=slug, group_id=group.pk)


@login_required
@require_POST
def join_group(request, slug, group_id):
    """Join a study group."""
    group = get_object_or_404(StudyGroup, pk=group_id, is_active=True)

    if group.is_full:
        messages.error(request, 'This group is full.')
        return redirect('studygroups:list', slug=slug)

    membership, created = Membership.objects.get_or_create(
        group=group, student=request.user,
        defaults={'role': 'member'}
    )
    if created:
        messages.success(request, f'Joined "{group.name}"!')
        # Notify leader
        leader = group.members.filter(role='leader').first()
        if leader:
            create_notification(
                recipient=leader.student,
                title='New Group Member',
                message=f'{request.user.get_full_name() or request.user.username} joined "{group.name}".',
                notification_type='info',
                link=f'/studygroups/{slug}/chat/{group.pk}/'
            )
    else:
        membership.is_active = True
        membership.save()

    return redirect('studygroups:chat', slug=slug, group_id=group.pk)


@login_required
@require_POST
def leave_group(request, slug, group_id):
    """Leave a study group."""
    membership = Membership.objects.filter(
        group_id=group_id, student=request.user
    ).first()
    if membership:
        membership.is_active = False
        membership.save()
        messages.info(request, 'You left the group.')
    return redirect('studygroups:list', slug=slug)


@login_required
def group_chat(request, slug, group_id):
    """Group chat page."""
    course = get_object_or_404(Course, slug=slug)
    group = get_object_or_404(StudyGroup, pk=group_id, is_active=True)
    membership = Membership.objects.filter(
        group=group, student=request.user, is_active=True
    ).first()

    if not membership:
        messages.error(request, 'Join the group first.')
        return redirect('studygroups:list', slug=slug)

    chat_messages = group.messages.select_related('sender').all()
    members = group.members.filter(is_active=True).select_related('student')

    context = {
        'course': course,
        'group': group,
        'chat_messages': chat_messages,
        'members': members,
        'membership': membership,
    }
    return render(request, 'studygroups/group_chat.html', context)


@login_required
@require_POST
def send_message(request, slug, group_id):
    """Send message to group (AJAX)."""
    group = get_object_or_404(StudyGroup, pk=group_id)
    membership = Membership.objects.filter(
        group=group, student=request.user, is_active=True
    ).first()
    if not membership:
        return JsonResponse({'error': 'Not a member'}, status=403)

    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Empty message'}, status=400)

    msg = GroupMessage.objects.create(
        group=group, sender=request.user, content=content
    )
    return JsonResponse({
        'status': 'ok',
        'message': {
            'id': msg.id,
            'sender': msg.sender.get_full_name() or msg.sender.username,
            'sender_id': msg.sender.id,
            'content': msg.content,
            'time': msg.created_at.strftime('%b %d, %H:%M'),
            'is_mine': True,
        }
    })


@login_required
def poll_messages(request, slug, group_id):
    """Poll for new group messages."""
    group = get_object_or_404(StudyGroup, pk=group_id)
    after = request.GET.get('after', 0)

    msgs = group.messages.filter(pk__gt=int(after)).select_related('sender')
    data = [{
        'id': m.id,
        'sender': m.sender.get_full_name() or m.sender.username,
        'sender_id': m.sender.id,
        'content': m.content,
        'time': m.created_at.strftime('%b %d, %H:%M'),
        'is_mine': m.sender == request.user,
    } for m in msgs]

    return JsonResponse({'messages': data})