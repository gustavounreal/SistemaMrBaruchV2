from django.contrib import admin
from .models import LinkCurto, ClickLinkCurto


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

