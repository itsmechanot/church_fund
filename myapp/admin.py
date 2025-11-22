from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Treasurer, Fund, Transaction

# --- Treasurer Admin ---
@admin.register(Treasurer)
class TreasurerAdmin(UserAdmin):
    # Keep list_display and list_filter as is
    list_display = (
        'username', 
        'email', 
        'first_name', 
        'last_name', 
        'church_branch', 
        'is_approved',
        'is_active', 
        'date_created'
    )
    list_filter = (
        'sex', 
        'church_branch', 
        'is_approved', 
        'is_staff', 
        'is_active', 
        'date_created'
    )
    search_fields = ('username', 'email', 'first_name', 'last_name', 'church_branch')
    ordering = ('-date_created',)
    readonly_fields = ('date_created',)

    # --- Re-defining the FIELDSETS for editing existing users ---
    fieldsets = (
        (None, {'fields': ('username', 'password')}), # Default UserAdmin fields
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'age', 'sex', 'phone_number')}),
        # Custom section combining Treasurer info and the approval status
        ('Church/Treasurer Status', {'fields': ('church_branch', 'position', 'is_approved', 'date_created')}),
        # Default Permissions and Groups fieldsets must be retained
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

    # --- Re-defining ADD_FIELDSETS for creating new users ---
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password', 'first_name', 'last_name', 'age', 'sex', 'phone_number', 'church_branch', 'position', 'is_approved'),
        }),
    )


# --- Fund Admin ---
@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ('name', 'fund_type', 'current_balance', 'created_by', 'date_created')
    list_filter = ('fund_type', 'created_by')
    search_fields = ('name', 'description')
    readonly_fields = ('current_balance', 'date_created') 
    ordering = ('fund_type', 'name')


# --- Transaction Admin ---
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_type', 'fund', 'amount', 'created_by', 'transaction_date')
    list_filter = ('transaction_type', 'fund', 'created_by')
    search_fields = ('description', 'fund__name')
    date_hierarchy = 'transaction_date' 
    readonly_fields = ('transaction_date',)
    raw_id_fields = ('created_by',)
    ordering = ('-transaction_date',)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - ₱{self.amount}"