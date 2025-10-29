from django.contrib import admin
from .models import (
    CanalComunicacao, InteracaoCliente, PesquisaSatisfacao,
    Indicacao, ProgramaFidelidade, MovimentacaoPontos
)


@admin.register(CanalComunicacao)
class CanalComunicacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'ativo']
    list_filter = ['tipo', 'ativo']
    search_fields = ['nome', 'descricao']


@admin.register(InteracaoCliente)
class InteracaoClienteAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'tipo', 'canal', 'status', 'data_agendada', 'responsavel']
    list_filter = ['tipo', 'status', 'canal', 'data_agendada']
    search_fields = ['cliente__nome', 'assunto', 'mensagem']
    date_hierarchy = 'data_agendada'
    raw_id_fields = ['cliente', 'venda', 'responsavel', 'criado_por']


@admin.register(PesquisaSatisfacao)
class PesquisaSatisfacaoAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'nota_geral', 'recomendaria', 'enviada_em', 'respondida']
    list_filter = ['recomendaria', 'enviada_em', 'respondida_em']
    search_fields = ['cliente__nome', 'comentarios']
    date_hierarchy = 'enviada_em'
    raw_id_fields = ['cliente', 'venda', 'interacao']
    
    def respondida(self, obj):
        return obj.respondida
    respondida.boolean = True


@admin.register(Indicacao)
class IndicacaoAdmin(admin.ModelAdmin):
    list_display = ['nome_indicado', 'cliente_indicador', 'status', 'telefone_indicado', 'criado_em']
    list_filter = ['status', 'criado_em']
    search_fields = ['nome_indicado', 'telefone_indicado', 'email_indicado', 'cliente_indicador__nome']
    date_hierarchy = 'criado_em'
    raw_id_fields = ['cliente_indicador', 'venda_indicador', 'venda_gerada']


@admin.register(ProgramaFidelidade)
class ProgramaFidelidadeAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'nivel', 'pontos_disponiveis', 'total_indicacoes', 'ativo']
    list_filter = ['nivel', 'ativo']
    search_fields = ['cliente__nome']
    raw_id_fields = ['cliente']


@admin.register(MovimentacaoPontos)
class MovimentacaoPontosAdmin(admin.ModelAdmin):
    list_display = ['fidelidade', 'tipo', 'pontos', 'descricao', 'criado_em']
    list_filter = ['tipo', 'criado_em']
    search_fields = ['fidelidade__cliente__nome', 'descricao']
    date_hierarchy = 'criado_em'
    raw_id_fields = ['fidelidade']
