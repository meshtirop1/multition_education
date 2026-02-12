"""Community forum views."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.decorators.http import require_POST

from notifications.utils import create_notification
from .models import ForumCategory, Thread, Post, PostVote, ThreadBookmark
from .forms import ThreadForm, PostForm


def forum_home(request):
    """Forum landing — list categories with stats."""
    categories = ForumCategory.objects.filter(is_active=True).annotate(
        num_threads=Count('threads'),
        num_posts=Count('threads__posts'),
    )
    recent_threads = Thread.objects.select_related(
        'author', 'category'
    ).annotate(
        num_replies=Count('posts')
    ).order_by('-created_at')[:5]

    popular_threads = Thread.objects.select_related(
        'author', 'category'
    ).annotate(
        num_replies=Count('posts')
    ).order_by('-views_count')[:5]

    # Stats
    total_threads = Thread.objects.count()
    total_posts = Post.objects.count()

    context = {
        'categories': categories,
        'recent_threads': recent_threads,
        'popular_threads': popular_threads,
        'total_threads': total_threads,
        'total_posts': total_posts,
    }
    return render(request, 'forum/home.html', context)


def category_detail(request, slug):
    """List threads in a category."""
    category = get_object_or_404(ForumCategory, slug=slug, is_active=True)

    sort = request.GET.get('sort', 'latest')
    threads = category.threads.select_related('author').annotate(
        num_replies=Count('posts'),
        vote_score=Sum('posts__votes__value'),
    )

    if sort == 'popular':
        threads = threads.order_by('-is_pinned', '-views_count')
    elif sort == 'unanswered':
        threads = threads.filter(posts__isnull=True).order_by('-is_pinned', '-created_at')
    elif sort == 'solved':
        threads = threads.filter(is_solved=True).order_by('-is_pinned', '-last_activity')
    else:
        threads = threads.order_by('-is_pinned', '-last_activity')

    context = {
        'category': category,
        'threads': threads,
        'current_sort': sort,
    }
    return render(request, 'forum/category.html', context)


def thread_detail(request, slug):
    """View a thread with all posts/replies."""
    thread = get_object_or_404(
        Thread.objects.select_related('author', 'category'), slug=slug
    )

    # Increment views
    thread.views_count += 1
    thread.save(update_fields=['views_count'])

    posts = thread.posts.select_related('author', 'parent', 'parent__author').annotate(
        upvotes=Count('votes', filter=Q(votes__value=1)),
        downvotes=Count('votes', filter=Q(votes__value=-1)),
    ).order_by('created_at')

    # Check user votes and bookmark status
    user_votes = {}
    is_bookmarked = False
    if request.user.is_authenticated:
        user_votes = dict(
            PostVote.objects.filter(
                user=request.user,
                post__thread=thread
            ).values_list('post_id', 'value')
        )
        is_bookmarked = ThreadBookmark.objects.filter(
            thread=thread, user=request.user
        ).exists()

    # Reply form
    if request.method == 'POST' and request.user.is_authenticated and not thread.is_locked:
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.thread = thread
            post.author = request.user

            parent_id = request.POST.get('parent_id')
            if parent_id:
                post.parent = Post.objects.filter(pk=parent_id, thread=thread).first()

            post.save()

            thread.last_activity = timezone.now()
            thread.save(update_fields=['last_activity'])

            # Notify thread author
            if thread.author != request.user:
                create_notification(
                    recipient=thread.author,
                    title='New Reply',
                    message=f'{request.user.get_full_name() or request.user.username} replied to "{thread.title[:60]}"',
                    notification_type='info',
                    link=f'/forum/thread/{thread.slug}/'
                )

            # Notify parent post author if replying
            if post.parent and post.parent.author != request.user:
                create_notification(
                    recipient=post.parent.author,
                    title='Reply to Your Post',
                    message=f'{request.user.get_full_name() or request.user.username} replied to your post.',
                    notification_type='info',
                    link=f'/forum/thread/{thread.slug}/'
                )

            messages.success(request, 'Reply posted!')
            return redirect('forum:thread', slug=thread.slug)
    else:
        form = PostForm()

    context = {
        'thread': thread,
        'posts': posts,
        'form': form,
        'user_votes': user_votes,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'forum/thread.html', context)


@login_required
def create_thread(request):
    """Create a new discussion thread."""
    category_slug = request.GET.get('category')
    initial = {}
    if category_slug:
        cat = ForumCategory.objects.filter(slug=category_slug).first()
        if cat:
            initial['category'] = cat.pk

    if request.method == 'POST':
        form = ThreadForm(request.POST)
        if form.is_valid():
            thread = form.save(commit=False)
            thread.author = request.user
            thread.save()
            messages.success(request, 'Thread created!')
            return redirect('forum:thread', slug=thread.slug)
    else:
        form = ThreadForm(initial=initial)

    context = {'form': form}
    return render(request, 'forum/create_thread.html', context)


@login_required
@require_POST
def vote_post(request, post_id):
    """Upvote or downvote a post."""
    post = get_object_or_404(Post, pk=post_id)
    value = int(request.POST.get('value', 1))
    if value not in (1, -1):
        return JsonResponse({'error': 'Invalid vote'}, status=400)

    vote, created = PostVote.objects.get_or_create(
        post=post, user=request.user,
        defaults={'value': value}
    )
    if not created:
        if vote.value == value:
            # Remove vote (toggle off)
            vote.delete()
            current_vote = 0
        else:
            vote.value = value
            vote.save()
            current_vote = value
    else:
        current_vote = value

    # Get updated scores
    upvotes = post.votes.filter(value=1).count()
    downvotes = post.votes.filter(value=-1).count()

    return JsonResponse({
        'upvotes': upvotes,
        'downvotes': downvotes,
        'score': upvotes - downvotes,
        'user_vote': current_vote,
    })


@login_required
@require_POST
def toggle_bookmark(request, thread_id):
    """Bookmark/unbookmark a thread."""
    thread = get_object_or_404(Thread, pk=thread_id)
    bookmark, created = ThreadBookmark.objects.get_or_create(
        thread=thread, user=request.user
    )
    if not created:
        bookmark.delete()
        return JsonResponse({'bookmarked': False})
    return JsonResponse({'bookmarked': True})


@login_required
@require_POST
def mark_solution(request, post_id):
    """Mark a post as the solution (thread author or mentor/admin only)."""
    post = get_object_or_404(Post.objects.select_related('thread'), pk=post_id)
    thread = post.thread

    if request.user != thread.author and request.user.role not in ('mentor', 'admin') and not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    # Toggle solution
    if post.is_solution:
        post.is_solution = False
        thread.is_solved = False
    else:
        # Remove any existing solution
        thread.posts.filter(is_solution=True).update(is_solution=False)
        post.is_solution = True
        thread.is_solved = True

        if post.author != request.user:
            create_notification(
                recipient=post.author,
                title='Your Answer Accepted!',
                message=f'Your reply in "{thread.title[:50]}" was marked as the solution.',
                notification_type='success',
                link=f'/forum/thread/{thread.slug}/'
            )

    post.save()
    thread.save()
    return JsonResponse({'is_solution': post.is_solution, 'thread_solved': thread.is_solved})


@login_required
@require_POST
def toggle_pin(request, thread_id):
    """Pin/unpin a thread (mentor/admin only)."""
    if request.user.role not in ('mentor', 'admin') and not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    thread = get_object_or_404(Thread, pk=thread_id)
    thread.is_pinned = not thread.is_pinned
    thread.save(update_fields=['is_pinned'])
    return JsonResponse({'is_pinned': thread.is_pinned})


@login_required
@require_POST
def toggle_lock(request, thread_id):
    """Lock/unlock a thread (mentor/admin only)."""
    if request.user.role not in ('mentor', 'admin') and not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    thread = get_object_or_404(Thread, pk=thread_id)
    thread.is_locked = not thread.is_locked
    thread.save(update_fields=['is_locked'])
    return JsonResponse({'is_locked': thread.is_locked})


def search_threads(request):
    """Search forum threads."""
    query = request.GET.get('q', '')
    threads = Thread.objects.none()

    if query:
        threads = Thread.objects.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query)
        ).select_related('author', 'category').annotate(
            num_replies=Count('posts')
        ).order_by('-last_activity')[:50]

    context = {
        'threads': threads,
        'query': query,
    }
    return render(request, 'forum/search.html', context)


@login_required
def my_threads(request):
    """User's threads and bookmarks."""
    user_threads = Thread.objects.filter(author=request.user).annotate(
        num_replies=Count('posts')
    ).order_by('-created_at')

    bookmarked = Thread.objects.filter(
        bookmarks__user=request.user
    ).annotate(
        num_replies=Count('posts')
    ).order_by('-last_activity')

    context = {
        'user_threads': user_threads,
        'bookmarked_threads': bookmarked,
    }
    return render(request, 'forum/my_threads.html', context)
