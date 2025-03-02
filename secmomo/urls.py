
from django.urls import path
from .views import change_password, register_agent, agent_login, agent_logout

urlpatterns = [
    path('register/', register_agent, name='register'),
    path('login/', agent_login, name='login'),
    path('logout/', agent_logout, name='logout'),
    path('change_password/', change_password, name='change_password'),
]