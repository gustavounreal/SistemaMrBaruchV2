from django import forms
from .models import ConfiguracaoSistema

class ConfiguracaoSistemaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoSistema
        fields = ['valor']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tipo = getattr(self.instance, 'tipo', 'TEXTO')
        if tipo == 'NUMERO':
            self.fields['valor'] = forms.FloatField(label='Valor', initial=self.instance.valor)
        elif tipo == 'BOOLEANO':
            self.fields['valor'] = forms.ChoiceField(
                choices=[('true', 'Sim'), ('false', 'Não')],
                label='Valor',
                initial=self.instance.valor
            )
        else:
            self.fields['valor'] = forms.CharField(label='Valor', initial=self.instance.valor)