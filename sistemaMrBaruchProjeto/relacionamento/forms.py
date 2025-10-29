from django import forms
from .models import InteracaoCliente, CanalComunicacao, Cliente

class NovaInteracaoForm(forms.ModelForm):
    class Meta:
        model = InteracaoCliente
        fields = [
            'cliente', 'tipo', 'canal', 'status', 'data_agendada', 'data_realizada',
            'assunto', 'mensagem', 'observacoes', 'venda'
        ]
        widgets = {
            'data_agendada': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'data_realizada': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'assunto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Digite o assunto da interação'}),
            'mensagem': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Digite a mensagem ou descrição da interação'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observações internas (opcional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = Cliente.objects.select_related('lead').all().order_by('lead__nome_completo')
        self.fields['canal'].queryset = CanalComunicacao.objects.filter(ativo=True)
        self.fields['tipo'].widget.attrs.update({'class': 'form-select'})
        self.fields['status'].widget.attrs.update({'class': 'form-select'})
        self.fields['canal'].widget.attrs.update({'class': 'form-select'})
        self.fields['cliente'].widget.attrs.update({'class': 'form-select', 'id': 'id_cliente'})
        self.fields['venda'].required = False
        self.fields['venda'].widget.attrs.update({'class': 'form-select'})
