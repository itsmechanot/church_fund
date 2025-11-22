from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Treasurer, Fund, Transaction

class TreasurerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = Treasurer  # Use the model from models.py
        fields = ['username', 'email', 'password1', 'password2']

class TreasurerLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

class TreasurerProfileForm(forms.ModelForm):
    class Meta:
        model = Treasurer
        fields = ['first_name', 'last_name', 'age', 'sex', 'phone_number', 'church_branch', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': 18, 'max': 100}),
            'sex': forms.Select(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'church_branch': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class TransactionForm(forms.ModelForm):
    transaction_type = forms.ChoiceField(
        choices=Transaction.TRANSACTION_TYPES,
        required=False,
        widget=forms.Select(attrs={'class': 'funds-form-control'})
    )

    class Meta:
        model = Transaction
        fields = ['fund', 'amount', 'description'] # <-- Remove transaction_type here
        widgets = {
            'fund': forms.Select(attrs={'class': 'funds-form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'funds-form-control', 'min': 0.01, 'step': 0.01}),
            # Removed 'transaction_type' widget
            'description': forms.Textarea(attrs={'class': 'funds-form-control', 'rows': 3}),
        }

class FundCreationForm(forms.ModelForm):
    class Meta:
        model = Fund
        fields = ['name', 'fund_type', 'description', 'current_balance'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'funds-form-control'}),
            'fund_type': forms.TextInput(attrs={'class': 'funds-form-control'}),
            'description': forms.Textarea(attrs={'class': 'funds-form-control', 'rows': 3}),
            'current_balance': forms.NumberInput(attrs={'class': 'funds-form-control', 'min': 0.00, 'step': 0.01}),
        }