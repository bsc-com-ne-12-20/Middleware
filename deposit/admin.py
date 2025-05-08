from django.contrib import admin
from .models import AgentDepositHistory

@admin.register(AgentDepositHistory)
class AgentDepositHistoryAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'agent', 'sender_email', 'receiver_email', 'amount', 'commission_earned', 'status', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('transaction_id', 'sender_email', 'receiver_email', 'agent__agentCode')
    ordering = ('-timestamp',)