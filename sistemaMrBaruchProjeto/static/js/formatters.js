// Funções utilitárias para formatar valores em pt-BR
(function(window){
  'use strict';

  function parseNumber(value){
    if(value === null || value === undefined) return NaN;
    var s = String(value).trim();
    // remove non-digit except comma and dot
    s = s.replace(/[^0-9.,-]/g, '');
    // if contains comma and dot, assume comma is decimal separator
    if(s.indexOf(',') !== -1 && s.indexOf('.') !== -1){
      s = s.replace(/\./g, ''); // remove thousand dots
      s = s.replace(/,/g, '.'); // comma to decimal
    } else if(s.indexOf(',') !== -1){
      s = s.replace(/,/g, '.');
    }
    var n = parseFloat(s);
    return isNaN(n) ? NaN : n;
  }

  function formatToBRL(value){
    var n = parseNumber(value);
    if(isNaN(n)) return value;
    return n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function formatAllBRL(){
    document.querySelectorAll('.format-brl').forEach(function(el){
      el.textContent = formatToBRL(el.textContent || el.innerText || el.value || '');
    });
  }

  // Expose
  window.Formatters = {
    formatToBRL: formatToBRL,
    formatAllBRL: formatAllBRL
  };

  // Auto init on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', function(){
    try{
      formatAllBRL();
    }catch(e){
      console.warn('Formatters: erro ao formatar (DOMContentLoaded)', e);
    }
  });

  // Fallback: também aplicar no window.load para elementos que carreguem tardiamente
  window.addEventListener('load', function(){
    try{
      formatAllBRL();
    }catch(e){
      console.warn('Formatters: erro ao formatar (load)', e);
    }
  });

})(window);
