import json
import anthropic
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.conf import settings
from django.views.decorators.http import require_POST
from django.utils.html import strip_tags

from courses.models import Course, Enrollment
from .models import ChatSession, ChatMessage


def get_course_context(course):
    """Build course content context for the AI."""
    context_parts = [
        f"You are an AI study assistant for the course: {course.title}",
        f"Course Level: {course.get_level_display()}",
        f"Course Description: {course.description}",
        "\n--- COURSE CONTENT ---\n",
    ]

    for module in course.modules.all().order_by('order'):
        context_parts.append(f"\n## Module {module.order}: {module.title}")
        if module.description:
            context_parts.append(f"Description: {module.description}")
        # Strip HTML tags from content
        clean_content = strip_tags(module.content)
        context_parts.append(clean_content)

        if module.resources:
            context_parts.append(f"\nResources: {module.resources}")

        for exercise in module.exercises.all().order_by('order'):
            context_parts.append(f"\n  Exercise: {exercise.title}")
            context_parts.append(f"  Type: {exercise.get_exercise_type_display()}")
            context_parts.append(f"  Description: {strip_tags(exercise.description)}")

    return "\n".join(context_parts)


def build_system_prompt(course):
    """Build the system prompt with course context."""
    course_context = get_course_context(course)

    return f"""You are a helpful, friendly AI study assistant for the MultiTion Education platform.

COURSE CONTEXT:
{course_context}

YOUR ROLE:
- Help students understand the course material
- Answer questions about the topics covered in this course
- Explain concepts in simple, clear language
- Give examples to illustrate difficult concepts
- Help students prepare for exercises and quizzes
- Encourage students and keep them motivated

RULES:
- Stay focused on the course topic. If asked about unrelated topics, gently redirect.
- NEVER give direct answers to quiz questions or exercises. Instead, guide the student to find the answer themselves.
- If a student is struggling, break the concept down into smaller parts.
- Use markdown formatting for code blocks, lists, and emphasis.
- Be concise but thorough. Aim for clear explanations.
- If you don't know something, say so honestly.
- Reference specific module content when relevant (e.g., "As covered in Module 2...")
"""


@login_required
def chat_home(request, slug):
    """Main chat page for a course — shows sessions list + active chat."""
    course = get_object_or_404(Course, slug=slug, is_published=True)

    # Verify enrollment
    enrollment = Enrollment.objects.filter(
        student=request.user, course=course, is_active=True
    ).first()
    if not enrollment:
        from django.contrib import messages as msg
        msg.error(request, 'You must be enrolled in this course to use the study assistant.')
        return redirect('courses:detail', slug=slug)

    sessions = ChatSession.objects.filter(
        student=request.user, course=course, is_active=True
    )

    context = {
        'course': course,
        'sessions': sessions,
        'enrollment': enrollment,
    }
    return render(request, 'studybot/chat_home.html', context)


@login_required
def chat_session(request, slug, session_id):
    """View a specific chat session."""
    course = get_object_or_404(Course, slug=slug, is_published=True)
    session = get_object_or_404(
        ChatSession, pk=session_id, student=request.user, course=course
    )
    messages_list = session.messages.all()

    sessions = ChatSession.objects.filter(
        student=request.user, course=course, is_active=True
    )

    context = {
        'course': course,
        'session': session,
        'messages_list': messages_list,
        'sessions': sessions,
    }
    return render(request, 'studybot/chat_home.html', context)


@login_required
@require_POST
def new_session(request, slug):
    """Create a new chat session."""
    course = get_object_or_404(Course, slug=slug, is_published=True)
    session = ChatSession.objects.create(
        student=request.user,
        course=course,
        title='New Chat',
    )
    return redirect('studybot:session', slug=slug, session_id=session.pk)


@login_required
@require_POST
def delete_session(request, slug, session_id):
    """Delete (deactivate) a chat session."""
    session = get_object_or_404(
        ChatSession, pk=session_id, student=request.user
    )
    session.is_active = False
    session.save()
    return redirect('studybot:home', slug=slug)


@login_required
@require_POST
def send_message(request, slug, session_id):
    """Send a message and get AI response."""
    course = get_object_or_404(Course, slug=slug)
    session = get_object_or_404(
        ChatSession, pk=session_id, student=request.user, course=course
    )

    user_message = request.POST.get('message', '').strip()
    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Save user message
    ChatMessage.objects.create(
        session=session, role='user', content=user_message
    )

    # Build conversation history
    history = []
    for msg in session.messages.all().order_by('created_at'):
        history.append({
            'role': msg.role,
            'content': msg.content,
        })

    # Auto-title on first message
    if session.title == 'New Chat' and len(history) == 1:
        session.title = user_message[:50] + ('...' if len(user_message) > 50 else '')
        session.save()

    # Call Claude API
    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        system_prompt = build_system_prompt(course)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=history,
        )

        assistant_content = response.content[0].text

        # Save assistant message
        ChatMessage.objects.create(
            session=session, role='assistant', content=assistant_content
        )

        session.save()  # Update updated_at

        return JsonResponse({
            'status': 'ok',
            'response': assistant_content,
        })

    except anthropic.AuthenticationError:
        return JsonResponse({
            'status': 'error',
            'response': 'AI service is not configured. Please contact the administrator to set up the API key.',
        }, status=500)
    except anthropic.RateLimitError:
        return JsonResponse({
            'status': 'error',
            'response': 'The AI is currently busy. Please try again in a moment.',
        }, status=429)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'response': f'Something went wrong. Please try again.',
        }, status=500)
