from django.urls import path
from .views import (
    auto_approve_agent, change_password, get_agent_username, get_balance,  register_agent, agent_login, agent_logout, agent_profile
)

urlpatterns = [
    path('register/', register_agent, name='register-agent'),
    path('login/', agent_login, name='agent-login'),
    path('logout/', agent_logout, name='agent-logout'),
    path('change-password/', change_password, name='change-password'),
    path('profile/', agent_profile, name='agent-profile'),
    path('get-username/', get_agent_username, name='get_agent_username'),
    path('agent-balance/', get_balance, name='get-balance'),
    path('applications/auto-approve/', auto_approve_agent, name='auto-approve-agent'),

]