/**
 * Script para formatação de valores monetários no padrão brasileiro
 * Formata valores com separador de milhares (.) e decimais (,)
 * 
 * Uso: Incluir este script em qualquer template que exiba valores monetários
 */

document.addEventListener('DOMContentLoaded', function() {
    // Função para formatar valores monetários no padrão brasileiro
    function formatarMoeda(valor) {
        // Remove "R$" e espaços
        let numero = valor.replace('R$', '').trim();
        
        // Converte para número
        numero = parseFloat(numero);
        
        // Se não for um número válido, retorna o valor original
        if (isNaN(numero)) {
            return valor;
        }
        
        // Formata no padrão brasileiro (1.234.567,89)
        return 'R$ ' + numero.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
    
    // Seletores comuns para valores monetários
    const seletores = [
        '.rank-stat-value',
        '.detail-value',
        '.resumo-valor',
        '.valor-monetario',
        '.card-value',
        '.metric-value',
        '.comissao-valor',
        '.total-valor',
        '[data-format="currency"]'
    ];
    
    // Seleciona todos os elementos com valores monetários
    seletores.forEach(function(seletor) {
        const elementos = document.querySelectorAll(seletor);
        
        elementos.forEach(function(elemento) {
            const texto = elemento.textContent;
            
            // Verifica se o texto contém "R$"
            if (texto.includes('R$')) {
                elemento.textContent = formatarMoeda(texto);
            }
        });
    });
    
    // Observer para elementos adicionados dinamicamente
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === 1) { // Element node
                    seletores.forEach(function(seletor) {
                        if (node.matches && node.matches(seletor)) {
                            const texto = node.textContent;
                            if (texto.includes('R$')) {
                                node.textContent = formatarMoeda(texto);
                            }
                        }
                        
                        // Também verifica elementos filhos
                        const filhos = node.querySelectorAll(seletor);
                        filhos.forEach(function(filho) {
                            const texto = filho.textContent;
                            if (texto.includes('R$')) {
                                filho.textContent = formatarMoeda(texto);
                            }
                        });
                    });
                }
            });
        });
    });
    
    // Inicia observação
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Exporta função para uso global
window.formatarMoeda = function(valor) {
    if (typeof valor === 'number') {
        return 'R$ ' + valor.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
    
    let numero = String(valor).replace('R$', '').trim();
    numero = parseFloat(numero);
    
    if (isNaN(numero)) {
        return valor;
    }
    
    return 'R$ ' + numero.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
};
