"""
Command para popular estratégias de repescagem padrão
"""
from django.core.management.base import BaseCommand
from vendas.models import MotivoRecusa, EstrategiaRepescagem


class Command(BaseCommand):
    help = 'Popula estratégias de repescagem padrão para cada motivo'

    def handle(self, *args, **options):
        estrategias_padrao = {
            'Valor (Achou caro)': [
                {
                    'titulo': 'Oferecer campanha promocional exclusiva',
                    'descricao': 'Apresentar uma promoção especial com desconto limitado por tempo. Criar senso de urgência.',
                    'ordem': 1
                },
                {
                    'titulo': 'Propor plano com benefícios adicionais',
                    'descricao': 'Incluir serviços extras sem custo adicional para agregar mais valor à proposta.',
                    'ordem': 2
                },
                {
                    'titulo': 'Apresentar diferentes faixas de valor',
                    'descricao': 'Mostrar opções de pacotes com diferentes níveis de serviço e preços.',
                    'ordem': 3
                },
                {
                    'titulo': 'Destacar ROI e vantagens competitivas',
                    'descricao': 'Demonstrar o retorno sobre investimento e como o serviço se paga ao longo do tempo.',
                    'ordem': 4
                }
            ],
            'Parcela alta': [
                {
                    'titulo': 'Reestruturar parcelamento',
                    'descricao': 'Aumentar o número de parcelas para reduzir o valor mensal. Priorizar a entrada do cliente.',
                    'ordem': 1
                },
                {
                    'titulo': 'Oferecer carência inicial',
                    'descricao': 'Propor início do pagamento das parcelas após 30-60 dias, dando fôlego ao cliente.',
                    'ordem': 2
                },
                {
                    'titulo': 'Propor entrada redistribuída',
                    'descricao': 'Parcelar também o valor da entrada em 2-3x para facilitar o início.',
                    'ordem': 3
                },
                {
                    'titulo': 'Flexibilizar datas de vencimento',
                    'descricao': 'Ajustar as datas de vencimento conforme o fluxo de caixa do cliente.',
                    'ordem': 4
                }
            ],
            'Sem entrada': [
                {
                    'titulo': 'Oferecer entrada flexível',
                    'descricao': 'Propor entrada simbólica (10-20% do valor) parcelada em 2-3x.',
                    'ordem': 1
                },
                {
                    'titulo': 'Propor entrada simbólica',
                    'descricao': 'Reduzir drasticamente o valor da entrada, focando em fechar o negócio.',
                    'ordem': 2
                },
                {
                    'titulo': 'Entrada em 2x sem juros',
                    'descricao': 'Dividir o valor da entrada em duas parcelas sem acréscimo.',
                    'ordem': 3
                },
                {
                    'titulo': 'Entrada com boleto futuro',
                    'descricao': 'Permitir que a entrada seja paga em data futura (30-45 dias).',
                    'ordem': 4
                }
            ],
            'Prazo': [
                {
                    'titulo': 'Revisão do prazo total do serviço',
                    'descricao': 'Ajustar o cronograma de execução conforme necessidade do cliente.',
                    'ordem': 1
                },
                {
                    'titulo': 'Flexibilização de datas',
                    'descricao': 'Permitir que o cliente escolha quando deseja iniciar o serviço.',
                    'ordem': 2
                },
                {
                    'titulo': 'Fases de entrega escalonadas',
                    'descricao': 'Dividir o serviço em etapas com entregas parciais.',
                    'ordem': 3
                },
                {
                    'titulo': 'Período de teste gratuito',
                    'descricao': 'Oferecer primeiros 15-30 dias como teste antes do compromisso total.',
                    'ordem': 4
                }
            ],
            'Desconfiança': [
                {
                    'titulo': 'Apresentar cases de sucesso',
                    'descricao': 'Mostrar resultados reais de outros clientes (com autorização).',
                    'ordem': 1
                },
                {
                    'titulo': 'Oferecer garantia estendida',
                    'descricao': 'Dar garantia de satisfação ou devolução do dinheiro se não cumprir o prometido.',
                    'ordem': 2
                },
                {
                    'titulo': 'Disponibilizar referências',
                    'descricao': 'Conectar o lead com clientes satisfeitos para que conversem diretamente.',
                    'ordem': 3
                },
                {
                    'titulo': 'Propor contrato trial',
                    'descricao': 'Oferecer período experimental com possibilidade de cancelamento.',
                    'ordem': 4
                }
            ],
            'Mau Atendimento': [
                {
                    'titulo': 'Pedido formal de desculpas',
                    'descricao': 'Reconhecer o erro, pedir desculpas sinceras e mostrar comprometimento com melhoria.',
                    'ordem': 1
                },
                {
                    'titulo': 'Oferecer reassistência imediata',
                    'descricao': 'Designar um consultor sênior para refazer todo o atendimento com excelência.',
                    'ordem': 2
                },
                {
                    'titulo': 'Propor benefício compensatório',
                    'descricao': 'Oferecer desconto especial ou serviço adicional como compensação.',
                    'ordem': 3
                },
                {
                    'titulo': 'Garantir atendimento prioritário',
                    'descricao': 'Assegurar que terá suporte VIP durante todo o processo.',
                    'ordem': 4
                }
            ],
            'Outros': [
                {
                    'titulo': 'Análise personalizada da objeção',
                    'descricao': 'Investigar a fundo qual é a real objeção e trabalhar especificamente nela.',
                    'ordem': 1
                },
                {
                    'titulo': 'Proposta customizada',
                    'descricao': 'Montar uma proposta única considerando todas as particularidades do caso.',
                    'ordem': 2
                },
                {
                    'titulo': 'Negociação flexível',
                    'descricao': 'Demonstrar abertura total para adaptar qualquer aspecto da proposta.',
                    'ordem': 3
                },
                {
                    'titulo': 'Solução sob medida',
                    'descricao': 'Criar um pacote específico que atenda exatamente às necessidades do lead.',
                    'ordem': 4
                }
            ],
            'Sem resposta': [
                {
                    'titulo': 'Reabordagem por canal alternativo',
                    'descricao': 'Se tentou por WhatsApp, tentar ligação. Se foi e-mail, tentar SMS.',
                    'ordem': 1
                },
                {
                    'titulo': 'Mensagem personalizada',
                    'descricao': 'Enviar mensagem curta e direta perguntando se ainda tem interesse.',
                    'ordem': 2
                },
                {
                    'titulo': 'Oferecer novo horário',
                    'descricao': 'Perguntar qual melhor horário e dia para conversar.',
                    'ordem': 3
                },
                {
                    'titulo': 'Proposta de recontato',
                    'descricao': 'Enviar proposta por escrito e agendar retorno específico.',
                    'ordem': 4
                }
            ]
        }

        total_criadas = 0
        total_existentes = 0

        for motivo_nome, estrategias in estrategias_padrao.items():
            try:
                motivo = MotivoRecusa.objects.get(nome__iexact=motivo_nome)
                
                for est_data in estrategias:
                    estrategia, created = EstrategiaRepescagem.objects.get_or_create(
                        motivo_recusa=motivo,
                        titulo=est_data['titulo'],
                        defaults={
                            'descricao': est_data['descricao'],
                            'ordem': est_data['ordem'],
                            'ativo': True
                        }
                    )
                    
                    if created:
                        total_criadas += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Estratégia criada: {motivo_nome} - {est_data["titulo"]}'
                            )
                        )
                    else:
                        total_existentes += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f'→ Estratégia já existe: {motivo_nome} - {est_data["titulo"]}'
                            )
                        )
            
            except MotivoRecusa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Motivo de recusa não encontrado: {motivo_nome}'
                    )
                )
                continue

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'📊 Resumo:'))
        self.stdout.write(self.style.SUCCESS(f'   • {total_criadas} estratégias criadas'))
        self.stdout.write(self.style.WARNING(f'   • {total_existentes} estratégias já existiam'))
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                '✅ Processo concluído! As estratégias estão disponíveis para o Comercial 2.'
            )
        )
