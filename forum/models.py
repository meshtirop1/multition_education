"""Community forum for students and mentors."""
from django.db import models
from django.conf import settings
from django.utils.text import slugify
import uuid


class ForumCategory(models.Model):
    """Forum categories (e.g., Machine Learning, General Discussion)."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-comments')
    color = models.CharField(max_length=20, default='#3b82f6')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Forum categories'

    def __str__(self):
        return self.name

    @property
    def thread_count(self):
        return self.threads.count()

    @property
    def post_count(self):
        return Post.objects.filter(thread__category=self).count()

    @property
    def latest_thread(self):
        return self.threads.order_by('-last_activity').first()


class Thread(models.Model):
    """A forum discussion thread."""
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=260, unique=True)
    category = models.ForeignKey(
        ForumCategory, on_delete=models.CASCADE, related_name='threads'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_threads'
    )
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_solved = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now_add=True)

    # Tags (simple comma-separated)
    tags = models.CharField(max_length=300, blank=True, default='')

    class Meta:
        ordering = ['-is_pinned', '-last_activity']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:250]
            self.slug = f"{base}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)

    @property
    def reply_count(self):
        return self.posts.count()

    @property
    def tag_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []

    @property
    def last_post(self):
        return self.posts.order_by('-created_at').first()


class Post(models.Model):
    """A reply/post within a thread."""
    thread = models.ForeignKey(
        Thread, on_delete=models.CASCADE, related_name='posts'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_posts'
    )
    content = models.TextField()
    is_solution = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Reply to specific post
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='replies'
    )

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author.username} on {self.thread.title}"


class PostVote(models.Model):
    """Upvote/downvote on posts."""
    VOTE_CHOICES = ((1, 'Upvote'), (-1, 'Downvote'))

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='forum_votes'
    )
    value = models.SmallIntegerField(choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['post', 'user']

    def __str__(self):
        return f"{self.user.username} {'up' if self.value > 0 else 'down'}voted"


class ThreadBookmark(models.Model):
    """User bookmarks on threads."""
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='bookmarks')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='bookmarked_threads'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['thread', 'user']
