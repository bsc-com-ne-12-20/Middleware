
from django.urls import path
from .views import change_password,agent_deposit, verify_identity, register_agent, agent_login, agent_logout, agent_withdraw, agent_transaction_history

urlpatterns = [
    path('register/', register_agent, name='register'),
    path('login/', agent_login, name='login'),
    path('logout/', agent_logout, name='logout'),
    path("agent_withdraw/", agent_withdraw, name="agent_withdraw"),
    path('agent_transactions_history/', agent_transaction_history, name='agent_transaction_history'),
    path('agent_deposit/', agent_deposit, name='agent_deposit'),
    path('verify_identity/', verify_identity, name='verify_identity'),
    path('change_password/', change_password, name='change_password'),
]