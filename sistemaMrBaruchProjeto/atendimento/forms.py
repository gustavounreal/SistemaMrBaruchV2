from django import forms
from marketing.models import Lead, OrigemLead
from core.services import ConfiguracaoService
from core.utils import Validadores

class AtendimentoInicialForm(forms.ModelForm):
    """Formulário único e simplificado para atendimento via WhatsApp"""
    
    origem = forms.ModelChoiceField(
        queryset=OrigemLead.objects.filter(ativo=True).order_by('ordem'),
        empty_label="Selecione a origem do lead",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Origem do Lead"
    )

    class Meta:
        model = Lead  # Alterado para usar o modelo Lead do app marketing
        fields = ['nome_completo', 'telefone', 'email', 'cpf_cnpj', 'origem', 'motivo_principal', 'perfil_emocional', 'observacoes']
        widgets = {
            'nome_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome completo do cliente',
                'autofocus': True
            }),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(11) 99999-9999'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'email@exemplo.com (opcional)'
            }),
            'cpf_cnpj': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Digite o CPF ou CNPJ'
            }),
            'origem': forms.Select(attrs={'class': 'form-control'}),
            'motivo_principal': forms.Select(attrs={'class': 'form-control'}),
            'perfil_emocional': forms.Select(attrs={'class': 'form-control'}),
            'observacoes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Observações importantes... (opcional)',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra apenas motivos ativos
        self.fields['motivo_principal'].queryset = self.fields['motivo_principal'].queryset.filter(ativo=True)
        self.fields['perfil_emocional'].queryset = self.fields['perfil_emocional'].queryset.filter(ativo=True)
        
        # ✅ VALOR DA CONSULTA VIA CONFIGURAÇÃO (não mais no form)
        self.valor_consulta = ConfiguracaoService.obter_config('VALOR_CONSULTA_PADRAO', 29.90)

    def clean_cpf_cnpj(self):
        """Valida o CPF ou CNPJ"""
        cpf_cnpj = self.cleaned_data.get('cpf_cnpj', '').strip()
        
        # Remove caracteres não numéricos antes de validar
        import re
        cpf_cnpj_limpo = re.sub(r'\D', '', cpf_cnpj)

        if len(cpf_cnpj_limpo) == 11:  # CPF
            if not Validadores.validar_cpf(cpf_cnpj_limpo):
                raise forms.ValidationError("CPF inválido.")
            return cpf_cnpj_limpo
        elif len(cpf_cnpj_limpo) == 14:  # CNPJ
            if not Validadores.validar_cnpj(cpf_cnpj_limpo):
                raise forms.ValidationError("CNPJ inválido.")
            return cpf_cnpj_limpo
        else:
            raise forms.ValidationError("CPF ou CNPJ inválido.")
        
        return cpf_cnpj_limpo