from django.contrib import admin
from django.utils.html import format_html
from .models import LinkCurto, ClickLinkCurto, MaterialDivulgacao


@admin.register(MaterialDivulgacao)
class MaterialDivulgacaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'preview_miniatura', 'tamanho_formatado', 'ativo', 'ordem', 'criado_em']
    list_filter = ['tipo', 'ativo', 'criado_em']
    search_fields = ['nome', 'descricao']
    readonly_fields = ['tamanho', 'criado_por', 'criado_em', 'atualizado_em', 'preview_arquivo']
    list_editable = ['ordem', 'ativo']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'tipo', 'ordem', 'ativo')
        }),
        ('Arquivo', {
            'fields': ('arquivo', 'thumbnail', 'preview_arquivo', 'tamanho')
        }),
        ('Metadados', {
            'fields': ('criado_por', 'criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Salva quem criou o material"""
        if not change:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)
    
    def preview_miniatura(self, obj):
        """Mostra preview da miniatura ou do arquivo"""
        if obj.thumbnail:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 80px; border-radius: 5px;" />', obj.thumbnail.url)
        elif obj.tipo == 'IMAGEM' and obj.arquivo:
            return format_html('<img src="{}" style="max-height: 50px; max-width: 80px; border-radius: 5px;" />', obj.arquivo.url)
        return '-'
    preview_miniatura.short_description = 'Preview'
    
    def preview_arquivo(self, obj):
        """Preview maior do arquivo"""
        if obj.tipo == 'IMAGEM' and obj.arquivo:
            return format_html('<img src="{}" style="max-width: 400px; border-radius: 8px;" />', obj.arquivo.url)
        elif obj.tipo == 'VIDEO' and obj.arquivo:
            return format_html('<video controls style="max-width: 400px;"><source src="{}" type="video/mp4"></video>', obj.arquivo.url)
        elif obj.tipo == 'PDF' and obj.arquivo:
            return format_html('<a href="{}" target="_blank" class="button">📄 Visualizar PDF</a>', obj.arquivo.url)
        return '-'
    preview_arquivo.short_description = 'Preview do Arquivo'
    
    def tamanho_formatado(self, obj):
        """Mostra o tamanho formatado"""
        return obj.get_tamanho_formatado()
    tamanho_formatado.short_description = 'Tamanho'


@admin.register(LinkCurto)
class LinkCurtoAdmin(admin.ModelAdmin):
    list_display = ['captador', 'codigo', 'total_cliques', 'ativo', 'criado_em']
    list_filter = ['ativo', 'criado_em']
    search_fields = ['captador__username', 'captador__email', 'codigo']
    readonly_fields = ['codigo', 'total_cliques', 'criado_em', 'atualizado_em']
    
    fieldsets = (
        ('Informações do Link', {
            'fields': ('captador', 'codigo', 'url_completa', 'ativo')
        }),
        ('Estatísticas', {
            'fields': ('total_cliques', 'criado_em', 'atualizado_em')
        }),
    )


@admin.register(ClickLinkCurto)
class ClickLinkCurtoAdmin(admin.ModelAdmin):
    list_display = ['link_curto', 'ip_address', 'clicado_em']
    list_filter = ['clicado_em']
    search_fields = ['link_curto__codigo', 'ip_address']
    readonly_fields = ['link_curto', 'ip_address', 'user_agent', 'referer', 'clicado_em']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

