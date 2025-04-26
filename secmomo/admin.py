from django.contrib import admin
from .models import AgentApplication, Agents
from django.contrib.auth.admin import UserAdmin

@admin.register(AgentApplication)
class AgentApplicationAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone_number', 'status', 'application_date')
    list_filter = ('status', 'applicant_type')
    search_fields = ('email', 'phone_number', 'business_name')
    readonly_fields = ('application_date',)

@admin.register(Agents)
class AgentAdmin(UserAdmin):
    # Display fields in list view
    list_display = ('username', 'email', 'phone_number', 'agent_code', 'status', 'date_joined')
    
    # Filter options
    list_filter = ('status', 'is_active', 'is_staff')
    
    # Searchable fields
    search_fields = ('username', 'email', 'phone_number', 'agent_code', 'first_name', 'last_name')
    
    # Readonly fields
    readonly_fields = ('date_joined', 'last_login', 'agent_code')
    
    # Fieldsets for edit view
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Agent Info', {'fields': ('agent_code', 'current_balance', 'status', 'mobile_money_user_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Add user form fields
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone_number', 'password1', 'password2'),
        }),
    )
    
    # Ordering
    ordering = ('-date_joined',)