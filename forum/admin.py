from django.contrib import admin
from .models import ForumCategory, Thread, Post, PostVote, ThreadBookmark

@admin.register(ForumCategory)
class ForumCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}

class PostInline(admin.TabularInline):
    model = Post
    extra = 0
    readonly_fields = ['author', 'created_at']

@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'author', 'is_pinned', 'is_locked', 'is_solved', 'views_count', 'created_at']
    list_filter = ['category', 'is_pinned', 'is_locked', 'is_solved']
    search_fields = ['title', 'content']
    inlines = [PostInline]

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['author', 'thread', 'is_solution', 'created_at']
    list_filter = ['is_solution']
