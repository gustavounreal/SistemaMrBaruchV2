from django.core.management.base import BaseCommand
from financeiro.models import PixEntrada
from core.asaas_service import AsaasService


class Command(BaseCommand):
    help = 'Sincroniza PIX Copia e Cola de entradas que estão sem código no banco'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Iniciando sincronização de PIX com ASAAS...'))
        
        # Busca PIX sem código
        pix_vazios = PixEntrada.objects.filter(pix_code='').order_by('-data_criacao')
        total = pix_vazios.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✅ Nenhum PIX sem código encontrado!'))
            return
        
        self.stdout.write(f'Encontrados {total} PIX sem código. Sincronizando...')
        
        asaas = AsaasService()
        atualizados = 0
        erros = 0
        
        for pix in pix_vazios:
            try:
                self.stdout.write(f'\n🔄 Processando PIX #{pix.id} - Venda #{pix.venda.id}')
                self.stdout.write(f'   ASAAS Payment ID: {pix.asaas_payment_id}')
                
                # Busca QR Code no ASAAS
                qr_data = asaas.obter_qr_code_pix(pix.asaas_payment_id)
                
                if qr_data and 'payload' in qr_data:
                    pix.pix_code = qr_data['payload']
                    pix.pix_qr_code_url = qr_data.get('encodedImage', '')
                    pix.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'   ✅ Atualizado! PIX Code: {len(pix.pix_code)} caracteres'
                    ))
                    atualizados += 1
                else:
                    self.stdout.write(self.style.ERROR(
                        f'   ❌ Não foi possível obter dados do ASAAS'
                    ))
                    erros += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'   ❌ Erro: {str(e)}'))
                erros += 1
        
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS(f'✅ Sincronização concluída!'))
        self.stdout.write(f'   Total processados: {total}')
        self.stdout.write(f'   Atualizados: {atualizados}')
        self.stdout.write(f'   Erros: {erros}')
        self.stdout.write('='*80)
