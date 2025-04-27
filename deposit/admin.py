# deposit/admin.py
from django.contrib import admin
from .models import Deposit, AgentDepositHistory

@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ['agent', 'amount', 'timestamp', 'status', 'transaction_id']
    search_fields = ['agent__username', 'transaction_id']

@admin.register(AgentDepositHistory)
class AgentDepositHistoryAdmin(admin.ModelAdmin):
    list_display = ['agent', 'user_email', 'amount', 'transaction_id', 'timestamp']
    search_fields = ['agent__username', 'user_email', 'transaction_id']
