from django import forms
from accounts.models import User, DadosUsuario


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['nome_completo', 'email', 'telefone', 'chave_pix', 'endereco_completo', 'conta_bancaria']
        widgets = {
            'nome_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control phone-mask'}),
            'chave_pix': forms.TextInput(attrs={'class': 'form-control'}),
            'endereco_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'conta_bancaria': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ConsultorForm(forms.ModelForm):
    class Meta:
        model = DadosUsuario
        fields = ['whatsapp_pessoal', 'contato_recado', 'id_consultor']
        widgets = {
            'whatsapp_pessoal': forms.TextInput(attrs={'class': 'form-control phone-mask'}),
            'contato_recado': forms.TextInput(attrs={'class': 'form-control phone-mask'}),
            'id_consultor': forms.TextInput(attrs={'class': 'form-control', 'readonly': True}),
        }