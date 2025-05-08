from django.contrib import admin
from .models import Transfer

@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('trans_id', 'sender_email', 'receiver_email', 'amount', 'commission_earned', 'status', 'time_stamp')
    list_filter = ('status', 'time_stamp')
    search_fields = ('trans_id', 'sender_email', 'receiver_email', 'sender__agentCode', 'receiver__agentCode')
    ordering = ('-time_stamp',)