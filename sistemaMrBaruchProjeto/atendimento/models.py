    
from django.db import models
from django.conf import settings

class Atendimento(models.Model):
    TIPO_SERVICO_CHOICES = [
        ('LIMPA_NOME', 'Limpa Nome'),
        ('RETIRADA_TRAVAS', 'Retirada de Travas'),
        ('RECUPERACAO_SCORE', 'Recuperação de Score'),
        ('LIMPA_NOME_RETIRADA_TRAVAS', 'Limpa Nome + Retirada de Travas'),
        ('RECUPERACAO_SCORE_LIMPA_NOME', 'Recuperação Score + Limpa Nome'),
        ('RECUPERACAO_SCORE_RETIRADA_TRAVAS', 'Recuperação Score + Retirada Travas'),
        ('COMPLETO', 'Completo'),
    ]
    
        
    lead = models.ForeignKey('marketing.Lead', on_delete=models.CASCADE, related_name='atendimentos')
    atendente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE) 
    data_atendimento = models.DateTimeField(auto_now_add=True)
    
    #tabelas dinâmicas do marketing
    motivo_principal = models.ForeignKey('marketing.MotivoContato', on_delete=models.PROTECT,
                                        limit_choices_to={'tipo': 'MOTIVO'},
                                        related_name='motivo_atendimentos')
    perfil_emocional = models.ForeignKey('marketing.MotivoContato', on_delete=models.PROTECT,
                                        limit_choices_to={'tipo': 'PERFIL'},
                                        related_name='perfil_atendimentos')
    
    tipo_servico_interesse = models.CharField(max_length=50, choices=TIPO_SERVICO_CHOICES)
    observacoes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Atendimento {self.lead.nome_completo} - {self.data_atendimento}"

class HistoricoAtendimento(models.Model):
    atendimento = models.ForeignKey(Atendimento, on_delete=models.CASCADE)
    descricao = models.TextField()
    data_registro = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Histórico {self.atendimento} - {self.data_registro}"