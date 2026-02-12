"""Messaging views for student-mentor communication."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Max, Count, OuterRef, Subquery
from django.utils import timezone

from accounts.models import CustomUser
from notifications.utils import create_notification
from .models import Conversation, Message
from .forms import ComposeMessageForm, ReplyMessageForm


@login_required
def inbox(request):
    """List all conversations for the current user."""
    conversations = Conversation.objects.filter(
        participants=request.user,
        is_archived=False
    ).annotate(
        last_msg_time=Max('messages__created_at'),
        unread=Count('messages', filter=Q(
            messages__is_read=False
        ) & ~Q(messages__sender=request.user))
    ).order_by('-last_msg_time')

    # Precompute other participant for template
    conv_list = []
    for conv in conversations:
        conv.other_user = conv.other_participant(request.user)
        conv_list.append(conv)

    total_unread = sum(c.unread for c in conversations)

    context = {
        'conversations': conv_list,
        'total_unread': total_unread,
    }
    return render(request, 'messaging/inbox.html', context)


@login_required
def conversation_detail(request, pk):
    """View and reply to a conversation."""
    conversation = get_object_or_404(
        Conversation.objects.filter(participants=request.user), pk=pk
    )

    # Mark messages as read
    conversation.messages.filter(is_read=False).exclude(
        sender=request.user
    ).update(is_read=True)

    if request.method == 'POST':
        form = ReplyMessageForm(request.POST, request.FILES)
        if form.is_valid():
            msg = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=form.cleaned_data['content'],
                attachment=form.cleaned_data.get('attachment'),
            )
            conversation.updated_at = timezone.now()
            conversation.save()

            # Notify other participant
            other = conversation.other_participant(request.user)
            if other:
                create_notification(
                    recipient=other,
                    title='New Message',
                    message=f'{request.user.get_full_name() or request.user.username}: {msg.content[:80]}',
                    notification_type='info',
                    link=f'/messages/{conversation.pk}/'
                )

            # Return JSON for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'ok',
                    'message': {
                        'id': msg.id,
                        'content': msg.content,
                        'sender': msg.sender.get_full_name() or msg.sender.username,
                        'time': msg.created_at.strftime('%b %d, %H:%M'),
                        'is_mine': True,
                        'attachment_url': msg.attachment.url if msg.attachment else None,
                    }
                })
            return redirect('messaging:detail', pk=pk)
    else:
        form = ReplyMessageForm()

    msgs = conversation.messages.select_related('sender').all()
    other = conversation.other_participant(request.user)

    context = {
        'conversation': conversation,
        'messages_list': msgs,
        'other_user': other,
        'form': form,
    }
    return render(request, 'messaging/conversation.html', context)


@login_required
def compose(request):
    """Start a new conversation."""
    recipient_id = request.GET.get('to')
    initial = {}
    recipient_user = None

    if recipient_id:
        try:
            recipient_user = CustomUser.objects.get(pk=int(recipient_id))
        except (ValueError, CustomUser.DoesNotExist):
            recipient_user = CustomUser.objects.filter(username=recipient_id).first()
        if recipient_user:
            initial['recipient'] = recipient_user.pk

    if request.method == 'POST':
        form = ComposeMessageForm(request.POST, request.FILES)
        if form.is_valid():
            recipient = get_object_or_404(CustomUser, pk=form.cleaned_data['recipient'])

            # Check if conversation exists between these two
            existing = Conversation.objects.filter(
                participants=request.user
            ).filter(participants=recipient)

            if existing.exists():
                conversation = existing.first()
            else:
                conversation = Conversation.objects.create(
                    subject=form.cleaned_data.get('subject', ''),
                )
                conversation.participants.add(request.user, recipient)

            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=form.cleaned_data['content'],
                attachment=form.cleaned_data.get('attachment'),
            )
            conversation.updated_at = timezone.now()
            conversation.save()

            create_notification(
                recipient=recipient,
                title='New Message',
                message=f'{request.user.get_full_name() or request.user.username} sent you a message.',
                notification_type='info',
                link=f'/messages/{conversation.pk}/'
            )

            messages.success(request, 'Message sent!')
            return redirect('messaging:detail', pk=conversation.pk)
    else:
        form = ComposeMessageForm(initial=initial)

    # Get available contacts (mentors for students, students for mentors)
    if request.user.role == 'student':
        # Students can message their course mentors
        from courses.models import Enrollment
        mentor_ids = Enrollment.objects.filter(
            student=request.user
        ).values_list('course__mentor_id', flat=True).distinct()
        contacts = CustomUser.objects.filter(
            Q(pk__in=mentor_ids) | Q(role='admin')
        ).distinct()
    elif request.user.role == 'mentor':
        # Mentors can message their students
        from courses.models import Enrollment
        student_ids = Enrollment.objects.filter(
            course__mentor=request.user
        ).values_list('student_id', flat=True).distinct()
        contacts = CustomUser.objects.filter(pk__in=student_ids)
    else:
        # Admin can message everyone
        contacts = CustomUser.objects.filter(is_active=True).exclude(pk=request.user.pk)

    context = {
        'form': form,
        'contacts': contacts,
        'recipient_user': recipient_user,
    }
    return render(request, 'messaging/compose.html', context)


@login_required
def api_unread_count(request):
    """JSON API for unread message count."""
    count = Message.objects.filter(
        conversation__participants=request.user,
        is_read=False
    ).exclude(sender=request.user).count()
    return JsonResponse({'unread_messages': count})


@login_required
def api_conversation_messages(request, pk):
    """JSON API for polling new messages in a conversation."""
    conversation = get_object_or_404(
        Conversation.objects.filter(participants=request.user), pk=pk
    )
    after = request.GET.get('after')
    msgs = conversation.messages.select_related('sender')
    if after:
        msgs = msgs.filter(pk__gt=int(after))

    # Mark as read
    msgs.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    data = [{
        'id': m.id,
        'sender': m.sender.get_full_name() or m.sender.username,
        'sender_id': m.sender.id,
        'sender_role': m.sender.role,
        'content': m.content,
        'time': m.created_at.strftime('%b %d, %H:%M'),
        'is_mine': m.sender == request.user,
        'attachment_url': m.attachment.url if m.attachment else None,
    } for m in msgs]
    return JsonResponse({'messages': data})
