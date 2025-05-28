
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [ 
    path('', TemplateView.as_view(template_name='api_documentation.html'), name='api-documentation'), 
    path("admin/", admin.site.urls),
    # path('api-auth/', include('rest_framework.urls')),
    path("api/", include("secmomo.urls")),  # Include the app's URLs
    path(
        "api/password_reset/",
        include("django_rest_passwordreset.urls", namespace="password_reset"),
    ),
    path("api/v1/dpst/", include("deposit.urls")),
    path("api/v1/agent-trsf/", include("agentTransfers.urls")),
    path("api/v1/agent-usr/", include("agents.urls")),
    path("api/v1/wtdr/", include("UserWithdrawsUsingAgent.urls")),
]
