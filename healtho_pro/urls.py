from django.contrib import admin
from django.urls import path, include
from healtho_pro.views import home
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('api', home, name='home'),
    path('api/admin/', admin.site.urls),
    path('api/user/', include('healtho_pro_user.urls')),
    path('api/pro_u_data/', include('pro_universal_data.urls')),
    path('api/lab/', include('pro_laboratory.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/inter/', include('interoperability.urls')),
    path('api/mobile_app/', include('mobile_app.urls')),
    path('api/pro_hospital/', include('pro_hospital.urls')),
    path('api/pro_pharmacy/', include('pro_pharmacy.urls')),
    path('api/messaging/', include('cloud_messaging.urls')),
    path('api/super_admin/', include('super_admin.urls'))
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

