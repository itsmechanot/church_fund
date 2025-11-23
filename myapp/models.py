from django.contrib.auth.models import AbstractUser
from django.db import models

class Treasurer(AbstractUser):
    first_name = models.CharField(max_length=30, blank=True, null=True)
    last_name = models.CharField(max_length=30, blank=True, null=True)
    age = models.PositiveIntegerField(blank=True, null=True)
    SEX_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    sex = models.CharField(max_length=1, choices=SEX_CHOICES, blank=True, null=True)
    
    email = models.EmailField(unique=True)

    is_approved = models.BooleanField(default=False, help_text="Designates whether the user is an approved treasurer.")
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    church_branch = models.CharField(max_length=100, blank=True, null=True)
    position = models.CharField(max_length=100, default='Treasurer')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='treasurer_set',
        related_query_name='treasurer'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='treasurer_set',
        related_query_name='treasurer'
    )

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def __str__(self):
        return f"{self.username} - {self.church_branch or 'No Branch'}"

class Fund(models.Model):
    name = models.CharField(max_length=100)
    fund_type = models.CharField(max_length=50, unique=True)
    current_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey('Treasurer', on_delete=models.CASCADE) 
    date_created = models.DateTimeField(auto_now_add=True)
    
    default_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.00,
        help_text="Default percentage of offerings to be allocated to this fund."
    )
    
    def __str__(self):
        return f"{self.name} - ₱{self.current_balance}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('OFFERING', 'Offering'),
        ('WITHDRAWAL', 'Withdrawal'),
    ]
    
    fund = models.ForeignKey(
        'Fund', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField()
    created_by = models.ForeignKey(Treasurer, on_delete=models.CASCADE)
    transaction_date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.transaction_type} - ₱{self.amount}"
    
class TransactionSplit(models.Model):
    """
    Records how a single parent Transaction (like an Offering) was distributed 
    across different funds.
    """
    # Links back to the single parent Transaction (e.g., "Sunday Offering")
    parent_transaction = models.ForeignKey(
        'Transaction', 
        on_delete=models.CASCADE, 
        related_name='splits'
    )
    
    # The specific fund this portion went to
    fund = models.ForeignKey(
        'Fund', 
        on_delete=models.PROTECT # Prevent deleting a fund if it has splits
    )
    
    # The amount that went into this specific fund
    amount_allocated = models.DecimalField(
        max_digits=10, 
        decimal_places=2
    )
    
    def __str__(self):
        return f"{self.fund.name}: ₱{self.amount_allocated}"