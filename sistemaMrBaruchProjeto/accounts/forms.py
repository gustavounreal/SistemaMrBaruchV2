from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
from .models import User, DadosUsuario

User = get_user_model()

class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'seu@email.com',
            'id': 'email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Sua senha',
            'id': 'password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'remember_me'
        }),
        label="Lembrar de mim"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "E-mail"
        
    def clean_username(self):
        email = self.cleaned_data.get('username')
        if email:
            try:
                user = User.objects.get(email=email)
                return user.username  # Retorna username para compatibilidade
            except User.DoesNotExist:
                raise ValidationError("E-mail não encontrado.")
        return email

class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'seu@email.com'
        })
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Seu nome'
        })
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Seu sobrenome'
        })
    )
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Crie uma senha forte'
        })
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirme sua senha'
        })
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este e-mail já está cadastrado.")
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email'].split('@')[0]
        if commit:
            user.save()
        return user

class AtendenteForm(forms.ModelForm):
    class Meta:
        model = DadosUsuario
        fields = [
            'bio',
            'whatsapp_pessoal',
            'contato_recado',
            'id_consultor',
            'total_vendas',
            'total_comissao_recebida',
            'quantidade_clientes'
        ]

class PerfilAtendenteForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'nome_completo',
            'email',
            'telefone',
            'endereco_completo',
            'chave_pix',
            'conta_bancaria'
        ]