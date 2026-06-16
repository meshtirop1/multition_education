from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from courses.models import Course
from forum.models import Thread


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return ["core:home", "core:about", "courses:list", "forum:home"]

    def location(self, item):
        return reverse(item)


class CourseSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return Course.objects.filter(is_published=True)

    def location(self, obj):
        return f"/courses/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, "updated_at") else None


class ForumThreadSitemap(Sitemap):
    priority = 0.5
    changefreq = "daily"
    protocol = "https"

    def items(self):
        return Thread.objects.filter(is_locked=False).order_by("-created_at")[:200]

    def location(self, obj):
        return f"/forum/thread/{obj.slug}/"

    def lastmod(self, obj):
        return obj.updated_at if hasattr(obj, "updated_at") else obj.created_at
