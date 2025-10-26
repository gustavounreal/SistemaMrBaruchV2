import logging
from django.utils import timezone
from django.conf import settings
from .models import ConfiguracaoSistema, LogSistema, Notificacao

logger = logging.getLogger(__name__)

class LogService:
    """Serviço centralizado de logging"""
    
    @staticmethod
    def registrar(usuario=None, nivel='INFO', mensagem='', modulo='', acao='', ip=None):
        """Registra log no banco de dados"""
        try:
            # Respeita configuração de logs
            ativo = ConfiguracaoService.obter_config('LOG_ATIVO', True)
            nivel_min = str(ConfiguracaoService.obter_config('LOG_NIVEL_MINIMO', 'INFO') or 'INFO').upper()
            niveis_ordem = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40}
            if not ativo or niveis_ordem.get(str(nivel).upper(), 20) < niveis_ordem.get(nivel_min, 20):
                # Ainda assim loga em console para dev (nível WARNING/ERROR)
                log_message = f"[{modulo}.{acao}] {mensagem}"
                if nivel == 'ERROR':
                    logger.error(log_message)
                elif nivel == 'WARNING':
                    logger.warning(log_message)
                else:
                    logger.info(log_message)
                return
            LogSistema.objects.create(
                usuario=usuario,
                nivel=nivel,
                mensagem=mensagem,
                modulo=modulo,
                acao=acao,
                ip_address=ip
            )
            
            # Também loga no console para desenvolvimento
            log_message = f"[{modulo}.{acao}] {mensagem}"
            if nivel == 'ERROR':
                logger.error(log_message)
            elif nivel == 'WARNING':
                logger.warning(log_message)
            else:
                logger.info(log_message)
                
        except Exception as e:
            logger.error(f"Erro ao registrar log: {e}")

class NotificacaoService:
    """Serviço de notificações"""
    
    @staticmethod
    def criar_notificacao(usuario, titulo, mensagem, tipo='INFO', link=''):
        """Cria uma notificação para o usuário"""
        try:
            return Notificacao.objects.create(
                usuario=usuario,
                titulo=titulo,
                mensagem=mensagem,
                tipo=tipo,
                link=link
            )
        except Exception as e:
            logger.error(f"Erro ao criar notificação: {e}")
            return None
    
    @staticmethod
    def marcar_como_lida(notificacao_id, usuario):
        """Marca uma notificação como lida"""
        try:
            notificacao = Notificacao.objects.get(id=notificacao_id, usuario=usuario)
            notificacao.lida = True
            notificacao.data_leitura = timezone.now()
            notificacao.save()
            return True
        except Notificacao.DoesNotExist:
            return False

class ConfiguracaoService:
    """Serviço de configurações do sistema"""
    
    @staticmethod
    def obter_config(chave, valor_padrao=None):
        """Obtém valor de configuração"""
        try:
            config = ConfiguracaoSistema.objects.get(chave=chave)
            # Converte o valor baseado no tipo
            if config.tipo == 'NUMERO':
                return float(config.valor) if '.' in config.valor else int(config.valor)
            elif config.tipo == 'BOOLEANO':
                return config.valor.lower() in ('true', '1', 'yes')
            elif config.tipo == 'JSON':
                import json
                return json.loads(config.valor)
            else:
                return config.valor
        except ConfiguracaoSistema.DoesNotExist:
            return valor_padrao
        except Exception as e:
            logger.error(f"Erro ao obter configuração {chave}: {e}")
            return valor_padrao
    
    @staticmethod
    def definir_config(chave, valor, descricao='', tipo='TEXTO'):
        """Define ou atualiza configuração"""
        try:
            config, created = ConfiguracaoSistema.objects.get_or_create(
                chave=chave,
                defaults={'valor': str(valor), 'descricao': descricao, 'tipo': tipo}
            )
            if not created:
                config.valor = str(valor)
                if descricao:
                    config.descricao = descricao
                config.tipo = tipo
                config.save()
            return True
        except Exception as e:
            logger.error(f"Erro ao definir configuração {chave}: {e}")
            return False
    
    @staticmethod   
    def inicializar_configs():
        """Inicializa todas as configurações padrão do sistema"""
        configs = [
            # Configurações gerais
            {
                'chave': 'VALOR_CONSULTA_PADRAO', 
                'valor': '29.90', 
                'tipo': 'NUMERO',
                'descricao': 'Valor padrão para consultas iniciais'
            },
            {
                'chave': 'ASAAS_API_URL', 
                'valor': 'https://sandbox.asaas.com/api/v3', 
                'tipo': 'TEXTO',
                'descricao': 'URL da API do ASAAS'
            },
            
            # Comissões - Atendente (PIX Levantamento)
            {
                'chave': 'COMISSAO_ATENDENTE_VALOR_FIXO', 
                'valor': '0.50', 
                'tipo': 'NUMERO',
                'descricao': 'Valor fixo (R$) por levantamento PIX confirmado'
            },
            
            # Comissões - Captador (Vendas - Fixo)
            {
                'chave': 'COMISSAO_CAPTADOR_PERCENTUAL', 
                'valor': '3.00', 
                'tipo': 'NUMERO',
                'descricao': 'Percentual fixo sobre valor recebido (entrada + boletos)'
            },
            
            # Comissões - Consultor (Vendas - Escala Progressiva)
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_1_MIN', 
                'valor': '20000.00', 
                'tipo': 'NUMERO',
                'descricao': 'Faturamento mínimo Faixa 1 (R$ 20k = 2%)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_1_PERCENT', 
                'valor': '2.00', 
                'tipo': 'NUMERO',
                'descricao': 'Percentual Faixa 1 (>= R$ 20k)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_2_MIN', 
                'valor': '30000.00', 
                'tipo': 'NUMERO',
                'descricao': 'Faturamento mínimo Faixa 2 (R$ 30k = 3%)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_2_PERCENT', 
                'valor': '3.00', 
                'tipo': 'NUMERO',
                'descricao': 'Percentual Faixa 2 (>= R$ 30k)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_3_MIN', 
                'valor': '40000.00', 
                'tipo': 'NUMERO',
                'descricao': 'Faturamento mínimo Faixa 3 (R$ 40k = 4%)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_3_PERCENT', 
                'valor': '4.00', 
                'tipo': 'NUMERO',
                'descricao': 'Percentual Faixa 3 (>= R$ 40k)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_4_MIN', 
                'valor': '50000.00', 
                'tipo': 'NUMERO',
                'descricao': 'Faturamento mínimo Faixa 4 (R$ 50k = 5%)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_4_PERCENT', 
                'valor': '5.00', 
                'tipo': 'NUMERO',
                'descricao': 'Percentual Faixa 4 (>= R$ 50k)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_5_MIN', 
                'valor': '60000.00', 
                'tipo': 'NUMERO',
                'descricao': 'Faturamento mínimo Faixa 5 (R$ 60k = 6%)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_5_PERCENT', 
                'valor': '6.00', 
                'tipo': 'NUMERO',
                'descricao': 'Percentual Faixa 5 (>= R$ 60k)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_6_MIN', 
                'valor': '80000.00', 
                'tipo': 'NUMERO',
                'descricao': 'Faturamento mínimo Faixa 6 (R$ 80k = 10%)'
            },
            {
                'chave': 'COMISSAO_CONSULTOR_FAIXA_6_PERCENT', 
                'valor': '10.00', 
                'tipo': 'NUMERO',
                'descricao': 'Percentual Faixa 6 (>= R$ 80k)'
            },
            
            # Prazos
            {
                'chave': 'PRAZO_LIMINAR_DIAS', 
                'valor': '10', 
                'tipo': 'NUMERO',
                'descricao': 'Prazo em dias para obtenção de liminar'
            },
            {
                'chave': 'PRAZO_CONCLUSAO_SERVICO', 
                'valor': '90', 
                'tipo': 'NUMERO',
                'descricao': 'Prazo em dias para conclusão do serviço'
            },
            
            # Valores financeiros
            {
                'chave': 'VALOR_MINIMO_ENTRADA', 
                'valor': '400.0', 
                'tipo': 'NUMERO',
                'descricao': 'Valor mínimo de entrada para serviços'
            },
            
            # Configurações de sistema
            {
                'chave': 'NOTIFICACAO_EMAIL_ATIVO', 
                'valor': 'true', 
                'tipo': 'BOOLEANO',
                'descricao': 'Ativa/desativa envio de notificações por email'
            },
            {
                'chave': 'NOTIFICACAO_SMS_ATIVO', 
                'valor': 'false', 
                'tipo': 'BOOLEANO',
                'descricao': 'Ativa/desativa envio de notificações por SMS'
            },
            {
                'chave': 'NOTIFICACAO_WHATSAPP_ATIVO', 
                'valor': 'true', 
                'tipo': 'BOOLEANO',
                'descricao': 'Ativa/desativa envio de notificações por WhatsApp'
            },
            
            # Configurações de mensagens
            {
                'chave': 'MENSAGEM_BOAS_VINDAS', 
                'valor': 'Bem-vindo ao Sistema Mr. Baruch! Estamos felizes em tê-lo conosco.', 
                'tipo': 'TEXTO',
                'descricao': 'Mensagem de boas-vindas para novos clientes'
            },
            {
                'chave': 'MENSAGEM_PIX_ENVIADO', 
                'valor': 'Seu PIX foi gerado com sucesso! Por favor efetue o pagamento para prosseguirmos com seu atendimento.', 
                'tipo': 'TEXTO',
                'descricao': 'Mensagem enviada quando um PIX é gerado'
            }
        ]
        
        count = 0
        for config_data in configs:
            if ConfiguracaoService.definir_config(
                chave=config_data['chave'],
                valor=config_data['valor'],
                tipo=config_data['tipo'],
                descricao=config_data['descricao']
            ):
                count += 1
                
        return f"Inicializadas {count} configurações"


class GrupoService:
    """Serviço para gerenciamento de grupos de usuários"""
    
    # Definição dos grupos do sistema com descrições
    GRUPOS_SISTEMA = {
        'admin': {
            'nome': 'Administrador',
            'descricao': 'Administradores do sistema com acesso total',
            'icone': 'bi-shield-lock-fill',
            'cor': 'danger'
        },
        'atendente': {
            'nome': 'Atendente',
            'descricao': 'Atendentes de leads e suporte',
            'icone': 'bi-headset',
            'cor': 'info'
        },
        'captador': {
            'nome': 'Captador',
            'descricao': 'Responsáveis pela captação de leads',
            'icone': 'bi-magnet',
            'cor': 'warning'
        },
        'compliance': {
            'nome': 'Compliance',
            'descricao': 'Equipe de análise de compliance',
            'icone': 'bi-clipboard-check',
            'cor': 'primary'
        },
        'comercial1': {
            'nome': 'Comercial 1',
            'descricao': 'Consultores comerciais nível 1',
            'icone': 'bi-briefcase',
            'cor': 'success'
        },
        'comercial2': {
            'nome': 'Comercial 2',
            'descricao': 'Consultores comerciais nível 2',
            'icone': 'bi-briefcase-fill',
            'cor': 'success'
        },
        'cliente': {
            'nome': 'Cliente',
            'descricao': 'Clientes do sistema',
            'icone': 'bi-person-circle',
            'cor': 'secondary'
        },
        'financeiro': {
            'nome': 'Financeiro',
            'descricao': 'Equipe financeira',
            'icone': 'bi-cash-stack',
            'cor': 'warning'
        },
        'administrativo': {
            'nome': 'Administrativo',
            'descricao': 'Equipe administrativa',
            'icone': 'bi-file-earmark-text',
            'cor': 'info'
        },
        'retencao': {
            'nome': 'Retenção',
            'descricao': 'Equipe de retenção de clientes',
            'icone': 'bi-arrow-repeat',
            'cor': 'primary'
        },
        'relacionamento': {
            'nome': 'Relacionamento',
            'descricao': 'Equipe de relacionamento com clientes',
            'icone': 'bi-chat-heart',
            'cor': 'danger'
        },
    }
    
    @staticmethod
    def listar_grupos_sistema():
        """
        Retorna todos os grupos do sistema com metadados.
        
        Returns:
            list: Lista de dicionários com informações dos grupos
        """
        from django.contrib.auth.models import Group
        
        grupos_info = []
        for nome_grupo, info in GrupoService.GRUPOS_SISTEMA.items():
            try:
                grupo = Group.objects.get(name=nome_grupo)
                grupos_info.append({
                    'id': grupo.id,
                    'name': nome_grupo,
                    'display_name': info['nome'],
                    'descricao': info['descricao'],
                    'icone': info['icone'],
                    'cor': info['cor'],
                    'total_usuarios': grupo.user_set.count()
                })
            except Group.DoesNotExist:
                # Grupo não existe, mas está na definição
                grupos_info.append({
                    'id': None,
                    'name': nome_grupo,
                    'display_name': info['nome'],
                    'descricao': info['descricao'],
                    'icone': info['icone'],
                    'cor': info['cor'],
                    'total_usuarios': 0,
                    'nao_existe': True
                })
        
        return sorted(grupos_info, key=lambda x: x['display_name'])
    
    @staticmethod
    def adicionar_usuario_grupo(usuario, grupo_name):
        """
        Adiciona um usuário a um grupo.
        
        Args:
            usuario: Instância do User
            grupo_name: Nome do grupo (string)
            
        Returns:
            tuple: (sucesso: bool, mensagem: str)
        """
        from django.contrib.auth.models import Group
        
        try:
            grupo = Group.objects.get(name=grupo_name)
            
            # Verifica se o usuário já está no grupo
            if usuario.groups.filter(name=grupo_name).exists():
                return False, f'Usuário já pertence ao grupo {grupo_name}'
            
            grupo.user_set.add(usuario)
            
            # Registra log
            LogService.registrar(
                usuario=usuario,
                nivel='INFO',
                mensagem=f'Adicionado ao grupo {grupo_name}',
                modulo='core',
                acao='adicionar_grupo'
            )
            
            return True, f'Usuário adicionado ao grupo {grupo_name} com sucesso'
            
        except Group.DoesNotExist:
            return False, f'Grupo {grupo_name} não encontrado'
        except Exception as e:
            logger.error(f"Erro ao adicionar usuário ao grupo: {e}")
            return False, f'Erro ao adicionar usuário ao grupo: {str(e)}'
    
    @staticmethod
    def remover_usuario_grupo(usuario, grupo_name):
        """
        Remove um usuário de um grupo.
        
        Args:
            usuario: Instância do User
            grupo_name: Nome do grupo (string)
            
        Returns:
            tuple: (sucesso: bool, mensagem: str)
        """
        from django.contrib.auth.models import Group
        
        try:
            grupo = Group.objects.get(name=grupo_name)
            
            # Verifica se o usuário está no grupo
            if not usuario.groups.filter(name=grupo_name).exists():
                return False, f'Usuário não pertence ao grupo {grupo_name}'
            
            grupo.user_set.remove(usuario)
            
            # Registra log
            LogService.registrar(
                usuario=usuario,
                nivel='INFO',
                mensagem=f'Removido do grupo {grupo_name}',
                modulo='core',
                acao='remover_grupo'
            )
            
            return True, f'Usuário removido do grupo {grupo_name} com sucesso'
            
        except Group.DoesNotExist:
            return False, f'Grupo {grupo_name} não encontrado'
        except Exception as e:
            logger.error(f"Erro ao remover usuário do grupo: {e}")
            return False, f'Erro ao remover usuário do grupo: {str(e)}'
    
    @staticmethod
    def obter_grupos_usuario(usuario):
        """
        Retorna lista de grupos do usuário com metadados.
        
        Args:
            usuario: Instância do User
            
        Returns:
            list: Lista de dicionários com informações dos grupos do usuário
        """
        grupos_usuario = []
        for grupo in usuario.groups.all():
            info = GrupoService.GRUPOS_SISTEMA.get(grupo.name, {
                'nome': grupo.name.title(),
                'descricao': '',
                'icone': 'bi-people',
                'cor': 'secondary'
            })
            grupos_usuario.append({
                'id': grupo.id,
                'name': grupo.name,
                'display_name': info['nome'],
                'descricao': info['descricao'],
                'icone': info['icone'],
                'cor': info['cor']
            })
        
        return grupos_usuario