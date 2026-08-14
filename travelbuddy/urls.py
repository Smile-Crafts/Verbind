from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

from trips.views import VerbindLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Our own styled login page, listed before the auth defaults so it wins.
    path('accounts/login/', VerbindLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('trips.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
