from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST 
from django.contrib import messages
from django.http import JsonResponse 
from django.db.models import Sum, F, Q
from django.db import transaction 
from .forms import TreasurerRegistrationForm, TreasurerLoginForm, TreasurerProfileForm, TransactionForm, FundCreationForm 
from .models import Fund, Transaction, TransactionSplit, Treasurer
from django.urls import reverse
from decimal import Decimal, InvalidOperation 
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.hashers import make_password

# --- CORE VIEWS ---

User = get_user_model()

@user_passes_test(lambda u: u.is_superuser) 
def disable_treasurer_view(request, pk):
    # Retrieve the user, assuming your custom user model (Treasurer) is used here
    treasurer = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        # 1. Check to prevent disabling the currently logged-in admin (safety measure)
        if treasurer == request.user:
            messages.error(request, "You cannot disable your own admin account.")
            return redirect('admin_transactions_dashboard')

        # 2. Disable the user account (standard way to prevent login)
        treasurer.is_active = False
        treasurer.save()
        
        # Optional: Log the action for auditing
        # logger.info(f"Admin {request.user.username} disabled treasurer {treasurer.username}")

        messages.success(request, f"Successfully disabled the account for {treasurer.username}.")
        return redirect('admin_transactions_dashboard') # Redirect back to the dashboard

    return redirect('admin_transactions_dashboard')

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_superuser)
def enable_treasurer(request, pk):
    """Enables a treasurer account by setting is_active=True."""
    if request.method == 'POST':
        # Use get_object_or_404 for robust error handling
        treasurer = get_object_or_404(Treasurer, pk=pk)
        treasurer.is_active = True
        treasurer.save()
        # Optionally add a success message here

    # Redirect back to the admin dashboard
    return redirect('admin_transactions_dashboard')

def calculate_monthly_net_growth(month_start, month_end):
    """Calculates net income (Income - Expense) for a specific month range."""
    
    monthly_transactions = Transaction.objects.filter(
        transaction_date__gte=month_start,
        transaction_date__lt=month_end 
    )
    
    monthly_income = monthly_transactions.filter(
        transaction_type__in=['OFFERING']
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    monthly_expense = monthly_transactions.filter(
        transaction_type__in=['WITHDRAWAL']
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    return monthly_income - monthly_expense


def calculate_net_growth(start_date, end_date):
    """Calculates net income (Income - Expense) for a specific date range across ALL funds."""
    
    # Calculate total income (OFFERINGs) within the date range
    income_data = Transaction.objects.filter(
        transaction_date__range=(start_date, end_date),
        transaction_type='OFFERING'
    ).aggregate(total_income=Sum('amount'))
    total_income = income_data['total_income'] or Decimal('0.00')

    # Calculate total expense (WITHDRAWALs) within the date range
    expense_data = Transaction.objects.filter(
        transaction_date__range=(start_date, end_date),
        transaction_type='WITHDRAWAL'
    ).aggregate(total_expense=Sum('amount'))
    total_expense = expense_data['total_expense'] or Decimal('0.00')

    # Net growth = Income - Expense
    net_growth = total_income - total_expense
    
    return net_growth

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

@user_passes_test(is_superuser)
def admin_transactions_view(request):
    current_admin = request.user

    all_transactions = Transaction.objects.all().select_related('fund', 'created_by').prefetch_related('splits').order_by('-transaction_date')

    # Add fund display logic for each transaction
    for transaction in all_transactions:
        if transaction.splits.exists():
            # This is a split transaction
            split_count = transaction.splits.count()
            transaction.fund_display = f"Split to {split_count} funds"
        elif transaction.fund:
            # This is a single fund transaction
            transaction.fund_display = transaction.fund.name
        else:
            # Fallback for any edge cases
            transaction.fund_display = "Unknown"

    pending_treasurers = Treasurer.objects.filter(is_approved=False, is_superuser=False).order_by('date_created')

    approved_treasurers = User.objects.filter(
        is_approved=True, 
        is_active=True
    ).exclude(
        pk=current_admin.pk  
    ).order_by('username')

    disabled_treasurers = User.objects.filter(
        is_approved=True, 
        is_active=False 
    ).order_by('username')
    
    context = {
        'transactions': all_transactions,
        'total_transactions': all_transactions.count(),
        'pending_treasurers': pending_treasurers,
        'approved_treasurers': approved_treasurers,
        'disabled_treasurers': disabled_treasurers
    }
    
    return render(request, 'admin_transactions_dashboard.html', context)

@user_passes_test(is_superuser) 
@require_POST # Ensure this view only accepts POST requests (for security)
def approve_treasurer(request, pk):
    # Get the treasurer or return a 404 if not found
    treasurer = get_object_or_404(Treasurer, pk=pk)
    
    if not treasurer.is_approved:
        treasurer.is_approved = True
        treasurer.save()
        messages.success(request, f"Treasurer {treasurer.username} has been approved and can now log in.")
    else:
        messages.warning(request, f"Treasurer {treasurer.username} was already approved.")
        
    # Redirect back to the dashboard after action
    return redirect('admin_transactions_dashboard')


def index(request):
    funds = Fund.objects.all().order_by('id') 
    total_data = funds.aggregate(total_balance=Sum('current_balance'))
    total_balance = total_data.get('total_balance') or Decimal('0.00')
    
    now = timezone.now()
    
    # 1. Calculate This Month's Net Growth
    start_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    this_month_growth = calculate_monthly_net_growth(start_of_current_month, now)
    
    # 2. Calculate Average Monthly Growth
    all_growth_values = []
    
    start_date = start_of_current_month - relativedelta(months=12)
    
    # Loop through the 12 full historical months
    for i in range(12):
        month_start = start_date + relativedelta(months=i)
        month_end = start_date + relativedelta(months=i + 1)
        
        net_growth = calculate_monthly_net_growth(month_start, month_end)
        all_growth_values.append(net_growth)

    # Calculate the average
    if all_growth_values:
        total_growth_sum = sum(all_growth_values)
        num_months = len(all_growth_values)
        avg_monthly_growth = total_growth_sum / num_months
    else:
        avg_monthly_growth = Decimal('0.00')
        
    recent_transactions = Transaction.objects.all().select_related('fund').order_by('-transaction_date')[:5]
    
    context = {
        'funds': funds,
        'total_balance': total_balance,
        'this_month_growth': this_month_growth, 
        'avg_monthly_growth': avg_monthly_growth,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'index.html', context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Debug: Check if user exists
        try:
            user_exists = Treasurer.objects.get(username=username)
            print(f"DEBUG: User {username} exists. Active: {user_exists.is_active}, Approved: {user_exists.is_approved}, Superuser: {user_exists.is_superuser}")
        except Treasurer.DoesNotExist:
            print(f"DEBUG: User {username} does not exist")
            messages.error(request, f'User {username} not found.')
            return render(request, 'login.html')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            print(f"DEBUG: Authentication successful for {username}")
            # 1. Check for Approval
            if user.is_approved:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # 2. Check for Superuser Role and Redirect
                if user.is_superuser:
                    return redirect('admin_transactions_dashboard')
                else:
                    return redirect('profile')
            else:
                # User is authenticated but NOT approved
                messages.error(request, 'Your account is pending administrator approval.')
                
        else:
            # User is NOT authenticated (invalid credentials)
            print(f"DEBUG: Authentication failed for {username}")
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

def register_view(request):
    if request.method == 'POST':
        form = TreasurerRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! Please wait for admin approval.')
            return redirect('login')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TreasurerRegistrationForm()
    
    return render(request, 'register.html', {'form': form})

@login_required
def profile_view(request):
    treasurer = request.user
    
    # --- STATISTICS CALCULATION ---
    now = timezone.now()

    total_managed_data = Fund.objects.all().aggregate(total=Sum('current_balance'))
    total_managed_funds = total_managed_data.get('total') or Decimal('0.00')

    start_of_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    current_month_transaction_count = Transaction.objects.filter(
        created_by=treasurer,
        transaction_date__gte=start_of_current_month
    ).count()

    recent_transactions = Transaction.objects.filter(
        created_by=treasurer
    ).select_related('fund').order_by('-transaction_date')[:10]

    days_ago_30 = now - timedelta(days=30)

    net_growth_30_days = calculate_net_growth(days_ago_30, now)

    balance_30_days_ago = total_managed_funds - net_growth_30_days
    growth_percentage = Decimal('0.00')
    if balance_30_days_ago > Decimal('0.00'):
        growth_percentage = (net_growth_30_days / balance_30_days_ago) * 100
    
    # --- END STATISTICS CALCULATION ---
    
    if request.method == 'POST':
        form = TreasurerProfileForm(request.POST, instance=treasurer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = TreasurerProfileForm(instance=treasurer)
    
    context = {
        'form': form,
        'treasurer': treasurer,
        'total_managed_funds': total_managed_funds,
        'current_month_transaction_count': current_month_transaction_count,
        'recent_transactions': recent_transactions,
        'growth_percentage': growth_percentage, 
    }
    
    return render(request, 'profile.html', context)

def admin_view_treasurer_profile(request, pk):
    # 1. Fetch the Treasurer object or return a 404 error
    treasurer = get_object_or_404(Treasurer, pk=pk)

    # 2. Calculate Statistics
    
    total_managed_funds = Transaction.objects.filter(
        created_by=treasurer
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    
    # Transactions Created (Current Month)
    today = date.today()
    start_of_month = today.replace(day=1)
    current_month_transaction_count = Transaction.objects.filter(
        created_by=treasurer,
        transaction_date__gte=start_of_month
    ).count()

    # --- 3. PAGINATION LOGIC ---
    
    # Get ALL transactions, ordered descending
    all_transactions = Transaction.objects.filter(created_by=treasurer).order_by('-transaction_date')
    
    # Set up Paginator: 5 items per page
    paginator = Paginator(all_transactions, 5) 
    
    # Get the requested page number from the URL (defaults to 1)
    page_number = request.GET.get('page')
    
    # Get the Page object for the requested page number
    recent_transactions_page = paginator.get_page(page_number)
    
    # --- END PAGINATION LOGIC ---

    # For a read-only view, we don't need a form, but we pass the data.
    context = {
        'treasurer': treasurer,
        'total_managed_funds': total_managed_funds,
        'current_month_transaction_count': current_month_transaction_count,
        
        # CHANGED: Pass the Paginator Page object instead of the sliced queryset
        'recent_transactions_page': recent_transactions_page, 
        
        # Placeholder data for the chart script
        'chart_labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'chart_data': [12000, 19000, 15000, 25000, 22000, 30000], 
    }
    
    return render(request, 'admin_view_treasurer_profile.html', context)

@login_required
def transactions_list_view(request):
    # Set the desired items per page
    ITEMS_PER_PAGE = 10 

    # 1. Base Query: Prefetch related data to prevent N+1 queries in the template
    transactions_queryset = Transaction.objects.all() \
        .order_by('-transaction_date', '-id') \
        .select_related('fund', 'created_by') \
        .prefetch_related('splits__fund') 

    all_funds = Fund.objects.all().order_by('name')

    # Get current filter/search values for context and pagination links
    current_type = request.GET.get('type')
    current_fund = request.GET.get('fund')
    current_q = request.GET.get('q')

    # --- 2. Filtering Logic ---
    
    # Filter by Transaction Type (OFFERING or WITHDRAWAL)
    if current_type in ['OFFERING', 'WITHDRAWAL']:
        transactions_queryset = transactions_queryset.filter(transaction_type=current_type)
        
    # Filter by Fund (for single-fund transactions OR transactions with splits allocated to this fund)
    if current_fund:
        try:
            # Q object allows OR logic: Match single-fund transactions OR parent split transactions
            transactions_queryset = transactions_queryset.filter(
                Q(fund_id=current_fund) | Q(splits__fund_id=current_fund)
            ).distinct() 
        except ValueError:
            pass
            
    # Search Query (Search across multiple fields)
    if current_q:
        transactions_queryset = transactions_queryset.filter(
            Q(description__icontains=current_q) |
            Q(fund__name__icontains=current_q) |
            Q(created_by__first_name__icontains=current_q) |
            Q(created_by__last_name__icontains=current_q)
        ).distinct()
        
    # --- 3. Total Balance Calculation (Organizational Balance) ---
    
    # Sum the current balance of all funds (Correct way)
    total_balance_agg = Fund.objects.aggregate(
        total_current_balance=Sum('current_balance')
    )['total_current_balance']

    total_balance = total_balance_agg or Decimal('0.00')

    # --- 4. Pagination ---
    paginator = Paginator(transactions_queryset, ITEMS_PER_PAGE)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    for transaction in page_obj.object_list:
        if transaction.splits.exists():
            for split in transaction.splits.all():
                # Calculate the percentage
                try:
                    percentage = (split.amount_allocated / transaction.amount) * 100
                    # Attach the new attribute to the split object
                    split.percentage = round(percentage, 0)
                except (ZeroDivisionError, TypeError):
                    split.percentage = 0
    
    # --- 5. Prepare Context ---
    context = {
        'page_obj': page_obj, # Contains the paginated transactions
        'transactions': page_obj.object_list, # The actual list of 10 transactions
        'funds': all_funds, # All funds for the filter dropdown
        'total_balance': total_balance, 
        
        # Maintain filter state
        'current_type': current_type,
        'current_fund': current_fund,
        'current_q': current_q,
    }
    
    return render(request, 'transaction.html', context)

@require_http_methods(["POST", "DELETE"])
def delete_transaction_view(request, pk):
    # Ensure only POST or DELETE requests are accepted
    
    transaction = get_object_or_404(Transaction, pk=pk)
    
    # Optional: Add permission checks here (e.g., if request.user is not admin)
    
    try:
        transaction.delete()
        messages.success(request, f"Transaction #{pk} successfully deleted.")
    except Exception as e:
        messages.error(request, f"Error deleting transaction: {e}")
        
    # Redirect back to the transaction list page
    return redirect('transactions_list')

# --- FUND MANAGEMENT VIEWS ---

@login_required
@require_POST
def create_fund(request):
    form = FundCreationForm(request.POST)
    
    if form.is_valid():
        fund = form.save(commit=False)
        
        if request.user.is_authenticated:
            fund.created_by = request.user
        else:
            messages.error(request, "Authentication failed for fund creation.")
            return redirect('index') 

        fund.save()
        messages.success(request, f'New Fund "{fund.name}" created successfully!')
        return redirect(reverse('index') + '#funds-page')
        
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"Error creating fund - {field}: {error}")
        return redirect(reverse('index') + '#funds-page')
    
@login_required
@require_http_methods(["POST"])
@transaction.atomic
def quick_split_transaction(request):
    # --- ADDED DEFENSIVE CHECK HERE ---
    # Check if this request is actually for the specific multi-fund form
    for key in request.POST.keys():
        if key.startswith('fund_') and key.endswith('_amount'):
            # If we find multi-fund fields, this request is misrouted!
            # Tell the user to try the correct method.
            messages.error(request, "Error: This transaction was submitted using the wrong form. Please try the 'Specific Fund' button instead.")
            return redirect(reverse('index') + '#funds-page')
    # Set the rounding precision
    TWO_PLACES = Decimal('0.01')
    
    try:
        # --- 1. Validation and Setup ---
        raw_total_amount = request.POST.get('total_offering_amount', '0.00')
        total_amount = Decimal(raw_total_amount).quantize(TWO_PLACES) # Ensure total is rounded to 2 places

        if total_amount <= Decimal('0.00'):
            messages.error(request, "Total offering must be a positive amount.")
            return redirect(reverse('index') + '#funds-page')

        # Identify a designated fund for handling rounding differences (e.g., 'General Fund')
        try:
            # ASSUMPTION: Replace 'General Fund' with the actual name of your catch-all fund
            general_fund = Fund.objects.get(name='General Fund') 
        except Fund.DoesNotExist:
            messages.error(request, "Setup error: 'General Fund' not found to handle allocation differences.")
            return redirect(reverse('index') + '#funds-page')
            
        # Get all funds *except* the general fund to calculate splits first
        split_funds = Fund.objects.filter(default_percentage__gt=0).exclude(pk=general_fund.pk)
        
        # If no split funds exist, just allocate the full amount to the general fund
        if not split_funds.exists() and general_fund.default_percentage == 0:
            messages.warning(request, "Cannot perform quick split: Only the General Fund exists, but it has a 0% split. Please update percentages.")
            return redirect(reverse('index') + '#funds-page')

        # --- 2. Create Single Parent Transaction ---
        parent_transaction = Transaction.objects.create(
            transaction_type='OFFERING', 
            amount=total_amount,
            fund=None, 
            description=f"Quick Split Offering (Total: ₱{total_amount:,.2f})",
            created_by=request.user,
        )

        total_allocated = Decimal('0.00')
        
        # --- 3. Process Splits for Non-General Funds ---
        for fund in split_funds:
            percentage = fund.default_percentage / Decimal('100.0')
            
            # CRITICAL: Round the allocated amount to ensure accuracy
            allocated_amount = (total_amount * percentage).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            
            if allocated_amount > Decimal('0.00'):
                # Update Fund Balance
                fund.current_balance = F('current_balance') + allocated_amount
                fund.save(update_fields=['current_balance'])
                
                # Create the CHILD TransactionSplit Record
                TransactionSplit.objects.create(
                    parent_transaction=parent_transaction,
                    fund=fund,
                    amount_allocated=allocated_amount
                )
                total_allocated += allocated_amount

        # --- 4. Allocate Remaining Amount to General Fund (The "Remainder") ---
        # The remainder covers both the General Fund's intended percentage *and* any rounding difference
        
        # Calculate the General Fund's intended percentage amount
        general_fund_percentage = general_fund.default_percentage / Decimal('100.0')
        general_fund_intended_amount = (total_amount * general_fund_percentage).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        
        # Calculate the actual remainder: Total amount minus all amounts allocated so far
        remainder_amount = total_amount - total_allocated
        
        if remainder_amount > Decimal('0.00'):
            # Update General Fund Balance (Atomically)
            general_fund.current_balance = F('current_balance') + remainder_amount
            general_fund.save(update_fields=['current_balance'])
            
            # Create the CHILD TransactionSplit Record for the remainder
            TransactionSplit.objects.create(
                parent_transaction=parent_transaction,
                fund=general_fund,
                amount_allocated=remainder_amount
            )

        # --- 5. Final Message and Redirect ---
        messages.success(request, f"Quick Split successful. Total ₱{total_amount:,.2f} recorded and split across {split_funds.count() + 1} funds.")
        return redirect(reverse('index') + '#funds-page')

    except Exception as e:
        messages.error(request, f'A critical error occurred during the split: {e}')
        return redirect(reverse('index') + '#funds-page')

@login_required
@require_POST
@transaction.atomic 
def deposit_to_funds(request):
    successful_deposits = 0
    
    for key, value in request.POST.items():
        if key.startswith('fund-'):
            try:
                fund_pk = int(key.split('-')[1])
                amount_to_add = Decimal(value or '0.00') 
                
                if amount_to_add <= Decimal('0.00'):
                    continue
                    
                fund_obj = Fund.objects.get(pk=fund_pk)
                
                Transaction.objects.create(
                    fund=fund_obj,
                    transaction_type='OFFERING',
                    amount=amount_to_add,
                    description=f"Specific deposit to {fund_obj.name} fund via admin panel.",
                    created_by=request.user
                )
                
                Fund.objects.filter(pk=fund_pk).update(
                    current_balance=F('current_balance') + amount_to_add
                )
                
                successful_deposits += 1

            except Fund.DoesNotExist:
                messages.error(request, f"Error: Fund ID {fund_pk} not found.")
                continue
            except (ValueError, IndexError, InvalidOperation):
                continue
            
    if successful_deposits > 0:
        messages.success(request, f"Successfully deposited money into {successful_deposits} fund(s).")
    else:
        messages.info(request, "No positive amounts were entered for deposit.")

    return redirect(reverse('index') + '#funds-page')

# --- TRANSACTION & SPLIT VIEWS ---

@login_required
@require_POST
@transaction.atomic
def handle_transaction(request):
    post_data = request.POST.copy()
    js_transaction_type = post_data.get('transaction_type')
    
    # 1. Reject non-Expense types immediately
    if js_transaction_type != 'Expense':
        return JsonResponse({
            'success': False, 
            'message': 'This endpoint is reserved for Withdrawals (Expense) only.'
        }, status=400)
    
    # Map to model field value
    post_data['transaction_type'] = 'WITHDRAWAL'
    form = TransactionForm(post_data) 
    
    if form.is_valid():
        fund = form.cleaned_data['fund']
        amount = form.cleaned_data['amount']
        
        try:
            # 2. Check for Insufficient funds
            if fund.current_balance < amount:
                return JsonResponse({'success': False, 'message': 'Insufficient funds for withdrawal.'}, status=400)
            
            # 3. Process Withdrawal
            fund.current_balance -= amount
            fund.save(update_fields=['current_balance'])
            
            transaction_record = form.save(commit=False)
            transaction_record.created_by = request.user
            transaction_record.transaction_type = 'WITHDRAWAL'
            transaction_record.transaction_date = timezone.now()
            transaction_record.save()
            
            # 4. Success return
            return JsonResponse({
                'success': True, 
                'message': f'₱{amount:,.2f} withdrawn from {fund.name}.', 
                'new_balance': float(fund.current_balance)
            })

        except Exception as e:
            # 5. Critical Error return (Server 500)
            print(f"Transaction Error: {e}") 
            return JsonResponse({'success': False, 'message': f'A critical server error occurred: {e}'}, status=500)

    # 6. Form Validation Error return (Client 400)
    errors = dict(form.errors.items())
    if form.non_field_errors():
        errors['non_field_errors'] = [str(e) for e in form.non_field_errors()]
    
    return JsonResponse({'success': False, 'message': 'Invalid transaction data sent to server.', 'errors': errors}, status=400)


@login_required
@require_POST
@transaction.atomic
def save_default_split(request):
    """Receives dynamic percentage assignments and saves them to Fund models."""
    updates = {}
    total_percentage = 0.0
    TOLERANCE = 0.01 

    for key, value in request.POST.items():
        if key.startswith('split-'):
            try:
                fund_id = int(key.split('-')[1])
                percentage = float(value)
                
                if not 0 <= percentage <= 100:
                    return JsonResponse({'success': False, 'message': f'Percentage for Fund ID {fund_id} is outside the 0-100 range.'}, status=400)
                
                updates[fund_id] = percentage
                total_percentage += percentage

            except (ValueError, IndexError):
                continue

    if not (100.0 - TOLERANCE < total_percentage < 100.0 + TOLERANCE):
        return JsonResponse({
            'success': False, 
            'message': f'Total percentage must be 100%. Current total is {total_percentage:.2f}%.',
            'total': total_percentage
        }, status=400)

    try:
        for fund_id, percentage in updates.items():
            fund = get_object_or_404(Fund, pk=fund_id)
            fund.default_percentage = percentage
            fund.save(update_fields=['default_percentage'])

        return JsonResponse({'success': True, 'message': 'Default offering split saved successfully.'})

    except Exception:
        return JsonResponse({'success': False, 'message': 'An unexpected error occurred while saving the split configuration.'}, status=500)
    
@require_http_methods(["POST"])
@transaction.atomic
def debug_admin_view(request):
    import os
    
    users = Treasurer.objects.all()
    context = {
        'users': users,
        'total_users': users.count(),
        'admin_username': os.environ.get('ADMIN_USERNAME', 'Not set'),
        'admin_password_set': bool(os.environ.get('ADMIN_PASSWORD')),
    }
    return render(request, 'simple_debug.html', context)

def fund_debug_view(request):
    if request.method == 'POST' and 'create_general' in request.POST:
        try:
            if not Fund.objects.filter(name='General Fund').exists():
                Fund.objects.create(
                    name='General Fund',
                    description='Main church fund for general expenses',
                    current_balance=Decimal('0.00'),
                    default_percentage=50.0,
                    created_by=request.user if request.user.is_authenticated else None
                )
                message = 'General Fund created successfully!'
            else:
                message = 'General Fund already exists!'
        except Exception as e:
            message = f'Error: {e}'
    else:
        message = None
    
    funds = Fund.objects.all()
    context = {
        'funds': funds,
        'total_funds': funds.count(),
        'message': message
    }
    return render(request, 'fund_debug.html', context)

def simple_create_admin(request):
    if request.method == 'POST':
        try:
            if not Treasurer.objects.filter(username='admin').exists():
                admin = Treasurer.objects.create(
                    username='admin',
                    email='admin@test.com',
                    first_name='Admin',
                    last_name='User',
                    is_staff=True,
                    is_superuser=True,
                    is_approved=True,
                    is_active=True
                )
                admin.set_password('admin123')
                admin.save()
                return render(request, 'create_admin_simple.html', {'message': 'Admin created! Username: admin, Password: admin123'})
            else:
                return render(request, 'create_admin_simple.html', {'message': 'Admin already exists!'})
        except Exception as e:
            return render(request, 'create_admin_simple.html', {'message': f'Error: {e}'})
    return render(request, 'create_admin_simple.html')

def create_admin_view(request):
    # Check if admin already exists
    if Treasurer.objects.filter(is_superuser=True).exists():
        messages.error(request, 'Admin already exists. Please login instead.')
        return redirect('login')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        # Validation
        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return render(request, 'create_admin.html')
            
        if Treasurer.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
            return render(request, 'create_admin.html')
        
        try:
            admin = Treasurer.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_staff=True,
                is_superuser=True,
                is_approved=True,
                is_active=True
            )
            admin.set_password(password)  # Use set_password for proper hashing
            admin.save()
            
            # Create General Fund if it doesn't exist
            if not Fund.objects.filter(name='General Fund').exists():
                Fund.objects.create(
                    name='General Fund',
                    description='Main church fund for general expenses',
                    current_balance=Decimal('0.00'),
                    default_percentage=Decimal('100.0'),
                    created_by=admin
                )
            
            messages.success(request, f'Admin {username} created successfully! You can now login.')
            return render(request, 'setup_complete.html')
        except Exception as e:
            messages.error(request, f'Error creating admin: {e}')
    
    return render(request, 'create_admin.html')

@login_required
@require_POST
@transaction.atomic
def undo_transaction(request, transaction_id):
    """Undo a transaction by creating reversal transactions"""
    try:
        trans = get_object_or_404(Transaction, pk=transaction_id)
        
        # Check if transaction was created within last 5 minutes (safety measure)
        time_limit = timezone.now() - timedelta(minutes=5)
        if trans.transaction_date < time_limit:
            messages.error(request, "Cannot undo transactions older than 5 minutes for security reasons.")
            return redirect(reverse('index') + '#funds-page')
        
        # Handle split transactions
        if trans.splits.exists():
            for split in trans.splits.all():
                # Reverse the fund balance changes
                split.fund.current_balance = F('current_balance') - split.amount_allocated
                split.fund.save(update_fields=['current_balance'])
        
        # Handle single fund transactions
        elif trans.fund:
            if trans.transaction_type == 'OFFERING':
                # Reverse offering by subtracting amount
                trans.fund.current_balance = F('current_balance') - trans.amount
            else:  # WITHDRAWAL
                # Reverse withdrawal by adding amount back
                trans.fund.current_balance = F('current_balance') + trans.amount
            trans.fund.save(update_fields=['current_balance'])
        
        # Delete the transaction
        trans.delete()
        
        messages.success(request, f"Transaction of ₱{trans.amount:,.2f} has been successfully undone.")
        
    except Exception as e:
        messages.error(request, f"Error undoing transaction: {e}")
    
    return redirect(reverse('index') + '#funds-page')

def specific_multi_transaction(request):
    # This dictionary will store Fund ID -> Amount pairs
    fund_allocations = {}
    total_offering = Decimal('0.00')
    
    # 1. Parse all fund inputs from the POST request
    for key, value in request.POST.items():
        if key.startswith('fund_') and key.endswith('_amount') and value:
            try:
                fund_id = key.split('_')[1]
                # Ensure the value is treated as a Decimal and strip commas/spaces
                amount = Decimal(value.replace(',', '').strip()) 
                if amount > Decimal('0.00'):
                    fund_allocations[fund_id] = amount
                    total_offering += amount
            except Exception:
                messages.error(request, "Invalid amount provided for one of the funds.")
                return redirect(reverse('index') + '#funds-page')

    num_funds = len(fund_allocations)

    if total_offering <= Decimal('0.00'):
        messages.error(request, "Total offering must be a positive amount.")
        return redirect(reverse('index') + '#funds-page')

    # --- HANDLE SINGLE FUND CASE (num_funds == 1) ---
    if num_funds == 1:
        # Get the single fund ID and amount
        fund_id = list(fund_allocations.keys())[0]
        amount = fund_allocations[fund_id]
        
        # Look up the fund object
        fund_obj = Fund.objects.get(pk=fund_id)
        
        # 1. Create a standard single transaction (no split necessary)
        Transaction.objects.create(
            transaction_type='OFFERING', 
            fund=fund_obj,
            amount=amount,
            description=f"Specific Offering to {fund_obj.name}",
            created_by=request.user,
        )
        
        # 2. Update Fund Balance (Atomically)
        fund_obj.current_balance = F('current_balance') + amount
        fund_obj.save(update_fields=['current_balance'])
        
        messages.success(request, f"Specific offering of ₱{total_offering:,.2f} recorded for {fund_obj.name}.")
        return redirect(reverse('index') + '#funds-page')

    # --- HANDLE MULTIPLE FUNDS CASE (num_funds >= 2) ---
    
    # 1. Retrieve the names of the funds involved for a better description
    fund_names = []
    # Fetching names outside the loop to prepare the description
    for fund_id in fund_allocations.keys():
        fund_names.append(Fund.objects.get(pk=fund_id).name)
    
    # Create a concise list string for the description
    if num_funds == 2:
        fund_list_str = f"{fund_names[0]} and {fund_names[1]}"
    else:
        # e.g., "Fund A, Fund B, and 3 others"
        fund_list_str = f"{fund_names[0]}, {fund_names[1]}, and {num_funds - 2} other(s)"

    # 2. Create the SINGLE PARENT Transaction record (Total Offering)
    parent_transaction = Transaction.objects.create(
        transaction_type='OFFERING', 
        amount=total_offering,
        fund=None, # Assuming fund is nullable or set to a default fund object
        # --- MODIFIED DESCRIPTION HERE ---
        description=f"Specific Multi-Fund Offering (Allocated to {fund_list_str}) (Total: ₱{total_offering:,.2f})",
        # ---------------------------------
        created_by=request.user,
    )
    
    # The individual saving is more robust than bulk_update when using F expressions
    
    # 3. Process Splits, Update Fund Balances, and Create TransactionSplit records
    for fund_id, amount_allocated in fund_allocations.items():
        fund_obj = Fund.objects.get(pk=fund_id)
        
        # A. Update Fund Balance (Atomically)
        fund_obj.current_balance = F('current_balance') + amount_allocated
        fund_obj.save(update_fields=['current_balance'])
        
        # B. Create the CHILD TransactionSplit Record
        TransactionSplit.objects.create(
            parent_transaction=parent_transaction,
            fund=fund_obj,
            amount_allocated=amount_allocated
        )
        
    messages.success(request, f"Specific offering of ₱{total_offering:,.2f} successfully split across {num_funds} funds.")
    return redirect(reverse('index') + '#funds-page')