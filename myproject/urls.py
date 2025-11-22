from django.contrib import admin
from django.urls import path
from myapp import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Root and User Paths
    path('', views.index, name='index'), 
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'), 
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('transactions/', views.transactions_list_view, name='transactions_list'),

    # FUNDS & TRANSACTION PATHS (Explicitly matching client-side calls)
    path('funds/quick-split/', views.quick_split_transaction, name='quick_split_transaction'),  
    path('funds/specific-multi/', views.specific_multi_transaction, name='specific_multi_transaction'),
    path('funds/transaction/', views.handle_transaction, name='handle_transaction'),          
    path('funds/create/', views.create_fund, name='create_fund'),
    path('funds/deposit/', views.deposit_to_funds, name='deposit_to_funds'),
    path('funds/save_split/', views.save_default_split, name='save_default_split'),
    path('transactions/delete/<int:pk>/', views.delete_transaction_view, name='delete_transaction'),

    path('super-admin/transactions/', views.admin_transactions_view, name='admin_transactions_dashboard'),
    path('super-admin/approve/<int:pk>/', views.approve_treasurer, name='approve_treasurer'),
    path('super-admin/treasurer/<int:pk>/view/', views.admin_view_treasurer_profile, name='admin_view_treasurer_profile'),
    path('treasurers/<int:pk>/disable/', views.disable_treasurer_view, name='disable_treasurer'),
    path('treasurers/enable/<int:pk>/', views.enable_treasurer, name='enable_treasurer'),
    path('create-admin/', views.create_admin_view, name='create_admin'),
    path('debug-admin/', views.debug_admin_view, name='debug_admin'),
    path('simple-create-admin/', views.simple_create_admin, name='simple_create_admin'),
    path('fund-debug/', views.fund_debug_view, name='fund_debug'),
]