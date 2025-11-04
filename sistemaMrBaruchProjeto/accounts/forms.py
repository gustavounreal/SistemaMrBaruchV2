from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
from .models import User, DadosUsuario

User = get_user_model()

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="E-mail ou Usuário",
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'seu@email.com ou usuário',
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
        self.fields['username'].label = "E-mail ou Usuário"
        
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                raise ValidationError(
                    "E-mail/usuário ou senha incorretos.",
                    code='invalid_login',
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

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
        # Converte username para maiúsculas
        user.username = self.cleaned_data['email'].split('@')[0].upper()
        if commit:
            user.save()
            # Adiciona o usuário ao grupo 'captador' por padrão
            from django.contrib.auth.models import Group
            grupo_captador, created = Group.objects.get_or_create(name='captador')
            user.groups.add(grupo_captador)
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