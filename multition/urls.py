"""MultiTion Education URL Configuration."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from core.sitemaps import StaticViewSitemap, CourseSitemap, ForumThreadSitemap

sitemaps = {
    "static": StaticViewSitemap,
    "courses": CourseSitemap,
    "forum": ForumThreadSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('courses/', include('courses.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('certificates/', include('certificates.urls')),
    path('notifications/', include('notifications.urls')),
    path('messages/', include('messaging.urls')),
    path('forum/', include('forum.urls')),
    path('api/', include('accounts.api_urls')),
    path('api/', include('courses.api_urls')),
    path('api/', include('notifications.api_urls')),
    path('social/', include('allauth.urls')),
    path('studybot/', include('studybot.urls')),
    path('billing/', include('billing.urls')),
    path('studygroups/', include('studygroups.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
