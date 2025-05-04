from django.contrib import admin
from .models import Revenue, AgentWithdrawalHistory

@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ('total_fees', 'last_updated')
    search_fields = ('total_fees',)
    ordering = ('-last_updated',)

@admin.register(AgentWithdrawalHistory)
class AgentWithdrawalHistoryAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'sender_email', 'receiver_email', 'gross_amount', 'commission_earned', 'net_amount', 'status', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('transaction_id', 'sender_email', 'receiver_email', 'agent__agentCode')
    ordering = ('-timestamp',)