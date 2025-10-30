from django.db import models
from django.conf import settings
from django.utils import timezone
import string
import random


class LinkCurto(models.Model):
    """
    Model para armazenar links curtos de indicação dos captadores.
    Permite rastreamento de cliques e analytics.
    """
    captador = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='link_curto',
        verbose_name='Captador'
    )
    codigo = models.CharField(
        max_length=8,
        unique=True,
        db_index=True,
        verbose_name='Código Curto'
    )
    url_completa = models.URLField(
        max_length=500,
        verbose_name='URL Completa'
    )
    total_cliques = models.IntegerField(
        default=0,
        verbose_name='Total de Cliques'
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Criado em'
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name='Atualizado em'
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name='Ativo'
    )

    class Meta:
        verbose_name = 'Link Curto'
        verbose_name_plural = 'Links Curtos'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.captador.get_full_name()} - {self.codigo} ({self.total_cliques} cliques)"

    @staticmethod
    def gerar_codigo_unico(tamanho=6):
        """
        Gera um código único de caracteres alfanuméricos.
        """
        caracteres = string.ascii_lowercase + string.digits
        while True:
            codigo = ''.join(random.choices(caracteres, k=tamanho))
            if not LinkCurto.objects.filter(codigo=codigo).exists():
                return codigo

    def incrementar_clique(self):
        """
        Incrementa o contador de cliques.
        """
        self.total_cliques += 1
        self.save(update_fields=['total_cliques', 'atualizado_em'])

    def get_url_curta(self, request=None):
        """
        Retorna a URL curta completa.
        """
        if request:
            return request.build_absolute_uri(f'/c/{self.codigo}')
        return f'/c/{self.codigo}'


class ClickLinkCurto(models.Model):
    """
    Model para registrar cada clique no link curto (analytics detalhado).
    """
    link_curto = models.ForeignKey(
        LinkCurto,
        on_delete=models.CASCADE,
        related_name='cliques',
        verbose_name='Link Curto'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='Endereço IP'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )
    referer = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Referência'
    )
    clicado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Clicado em'
    )

    class Meta:
        verbose_name = 'Clique em Link Curto'
        verbose_name_plural = 'Cliques em Links Curtos'
        ordering = ['-clicado_em']

    def __str__(self):
        return f"Clique em {self.link_curto.codigo} - {self.clicado_em.strftime('%d/%m/%Y %H:%M')}"

