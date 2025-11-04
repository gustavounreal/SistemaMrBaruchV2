from django.db import models
from django.conf import settings
from django.utils import timezone
import string
import random
import os


def material_upload_path(instance, filename):
    """
    Define o caminho de upload dos materiais.
    Formato: materiais_divulgacao/YYYY/MM/filename
    """
    return f'materiais_divulgacao/{timezone.now().year}/{timezone.now().month:02d}/{filename}'


class MaterialDivulgacao(models.Model):
    """
    Model para armazenar materiais de divulgação (imagens, vídeos, PDFs).
    Administradores podem fazer upload/excluir, captadores apenas visualizam/baixam.
    """
    TIPO_CHOICES = [
        ('IMAGEM', 'Imagem'),
        ('VIDEO', 'Vídeo'),
        ('PDF', 'PDF'),
        ('OUTRO', 'Outro'),
    ]
    
    nome = models.CharField(
        max_length=255,
        verbose_name='Nome do Material'
    )
    descricao = models.TextField(
        blank=True,
        verbose_name='Descrição'
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='IMAGEM',
        verbose_name='Tipo de Material'
    )
    arquivo = models.FileField(
        upload_to=material_upload_path,
        verbose_name='Arquivo'
    )
    thumbnail = models.ImageField(
        upload_to='materiais_divulgacao/thumbnails/',
        blank=True,
        null=True,
        verbose_name='Miniatura'
    )
    tamanho = models.IntegerField(
        default=0,
        help_text='Tamanho do arquivo em bytes',
        verbose_name='Tamanho'
    )
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='materiais_criados',
        verbose_name='Criado por'
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
    ordem = models.IntegerField(
        default=0,
        verbose_name='Ordem de Exibição',
        help_text='Materiais com menor número aparecem primeiro'
    )

    class Meta:
        verbose_name = 'Material de Divulgação'
        verbose_name_plural = 'Materiais de Divulgação'
        ordering = ['ordem', '-criado_em']

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"

    def save(self, *args, **kwargs):
        """
        Salva o tamanho do arquivo e detecta tipo automaticamente.
        """
        if self.arquivo:
            self.tamanho = self.arquivo.size
            
            # Detectar tipo pelo arquivo se não foi definido
            extensao = os.path.splitext(self.arquivo.name)[1].lower()
            if extensao in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                self.tipo = 'IMAGEM'
            elif extensao in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']:
                self.tipo = 'VIDEO'
            elif extensao == '.pdf':
                self.tipo = 'PDF'
            else:
                self.tipo = 'OUTRO'
        
        super().save(*args, **kwargs)

    def get_tamanho_formatado(self):
        """
        Retorna o tamanho do arquivo formatado (KB, MB, GB).
        """
        if self.tamanho < 1024:
            return f"{self.tamanho} bytes"
        elif self.tamanho < 1024 * 1024:
            return f"{self.tamanho / 1024:.2f} KB"
        elif self.tamanho < 1024 * 1024 * 1024:
            return f"{self.tamanho / (1024 * 1024):.2f} MB"
        else:
            return f"{self.tamanho / (1024 * 1024 * 1024):.2f} GB"

    def delete(self, *args, **kwargs):
        """
        Deleta o arquivo físico ao deletar o registro.
        """
        if self.arquivo:
            if os.path.isfile(self.arquivo.path):
                os.remove(self.arquivo.path)
        if self.thumbnail:
            if os.path.isfile(self.thumbnail.path):
                os.remove(self.thumbnail.path)
        super().delete(*args, **kwargs)


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

