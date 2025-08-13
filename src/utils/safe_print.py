#!/usr/bin/env python3
"""
Safe Print Utilities
Remove caracteres Unicode problemáticos para evitar erros no Windows
"""

import sys
import logging
from typing import Any

# Mapeamento de caracteres Unicode para ASCII
UNICODE_REPLACEMENTS = {
    # Checkmarks e X
    '✓': '[OK]',
    '✗': '[X]',
    '✅': '[DONE]',
    '❌': '[FAIL]',
    '☑': '[v]',
    '☒': '[x]',
    '✔': '[v]',
    '✖': '[x]',
    
    # Avisos e status
    '⚠️': '[WARN]',
    '⚠': '[!]',
    '⏳': '[WAIT]',
    '⏰': '[TIME]',
    '🚀': '[START]',
    '🔄': '[SYNC]',
    '♻️': '[RETRY]',
    
    # Símbolos técnicos
    '🔧': '[CONFIG]',
    '🛠️': '[TOOLS]',
    '⚙️': '[SETUP]',
    '🔨': '[BUILD]',
    
    # Financeiro
    '💰': '[$]',
    '💵': '[USD]',
    '💸': '[COST]',
    
    # Estatísticas
    '📊': '[STATS]',
    '📈': '[UP]',
    '📉': '[DOWN]',
    '📋': '[LIST]',
    
    # Informação
    '📌': '[PIN]',
    '📍': '[LOC]',
    '🔍': '[SEARCH]',
    '💡': '[IDEA]',
    
    # Matemática
    '≥': '>=',
    '≤': '<=',
    '≠': '!=',
    '≈': '~=',
    '∞': 'INF',
    
    # Setas
    '→': '->',
    '←': '<-',
    '↑': '^',
    '↓': 'v',
    '↔': '<->',
    
    # Outros
    '•': '*',
    '◦': 'o',
    '▪': '-',
    '▫': '-',
    '■': '[#]',
    '□': '[ ]',
    '▢': '[ ]',
    '▣': '[#]'
}


def safe_string(text: Any) -> str:
    """
    Converte qualquer entrada para string segura sem Unicode problemático
    
    Args:
        text: Qualquer tipo de entrada
        
    Returns:
        String segura para impressão no Windows
    """
    # Converter para string
    if text is None:
        return ''
    
    if not isinstance(text, str):
        text = str(text)
    
    # Substituir caracteres problemáticos
    for unicode_char, ascii_char in UNICODE_REPLACEMENTS.items():
        text = text.replace(unicode_char, ascii_char)
    
    # Remover outros caracteres não-ASCII se necessário
    if sys.platform == 'win32':
        # No Windows, remover caracteres que não podem ser codificados em cp1252
        try:
            text.encode('cp1252')
        except UnicodeEncodeError:
            # Remover caracteres problemáticos
            text = ''.join(char if ord(char) < 128 else '?' for char in text)
    
    return text


def safe_print(*args, **kwargs):
    """
    Print seguro que remove caracteres Unicode problemáticos
    
    Uso:
        safe_print("✓ Sucesso!")  # Imprime: [OK] Sucesso!
    """
    # Converter todos os argumentos para strings seguras
    safe_args = [safe_string(arg) for arg in args]
    
    # Imprimir com argumentos seguros
    print(*safe_args, **kwargs)


def safe_log(logger: logging.Logger, level: int, message: str, *args, **kwargs):
    """
    Logging seguro que remove caracteres Unicode problemáticos
    
    Args:
        logger: Logger instance
        level: Nível de log (logging.INFO, logging.ERROR, etc)
        message: Mensagem a logar
        *args: Argumentos adicionais
        **kwargs: Argumentos nomeados
    """
    safe_message = safe_string(message)
    
    # Se há argumentos, torná-los seguros também
    if args:
        safe_args = tuple(safe_string(arg) for arg in args)
        logger.log(level, safe_message, *safe_args, **kwargs)
    else:
        logger.log(level, safe_message, **kwargs)


class SafeLogger:
    """
    Wrapper para logger que automaticamente remove Unicode problemático
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def debug(self, message: str, *args, **kwargs):
        safe_log(self.logger, logging.DEBUG, message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        safe_log(self.logger, logging.INFO, message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        safe_log(self.logger, logging.WARNING, message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        safe_log(self.logger, logging.ERROR, message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        safe_log(self.logger, logging.CRITICAL, message, *args, **kwargs)


# Função helper para configurar logging seguro globalmente
def setup_safe_logging():
    """
    Configura o sistema de logging para usar strings seguras
    """
    import logging
    
    # Criar formatter personalizado
    class SafeFormatter(logging.Formatter):
        def format(self, record):
            # Formatar normalmente
            result = super().format(record)
            # Tornar seguro
            return safe_string(result)
    
    # Aplicar a todos os handlers existentes
    for handler in logging.root.handlers:
        handler.setFormatter(SafeFormatter(handler.formatter._fmt))
    
    # Configurar para novos loggers
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Aplicar formatter seguro ao handler padrão
    if logging.root.handlers:
        for handler in logging.root.handlers:
            original_format = handler.formatter._fmt if handler.formatter else '%(message)s'
            handler.setFormatter(SafeFormatter(original_format))


# Testes
if __name__ == "__main__":
    # Testar conversões
    test_strings = [
        "✓ Teste aprovado",
        "✗ Teste falhou",
        "⚠️ Aviso importante",
        "💰 Custo: $10.00",
        "📊 Estatísticas: ≥ 90%",
        "🔧 Configuração → Completa",
        None,
        123,
        ["✅", "Lista", "com", "unicode"]
    ]
    
    print("=== TESTES DE CONVERSÃO ===")
    for test in test_strings:
        original = str(test) if test is not None else "None"
        safe = safe_string(test)
        print(f"Original: {original[:30]:<30} -> Seguro: {safe}")
    
    print("\n=== TESTE DE PRINT SEGURO ===")
    safe_print("✅ Sucesso!", "⚠️ Aviso", "❌ Erro")
    
    print("\n=== TESTE DE LOGGING SEGURO ===")
    setup_safe_logging()
    logger = logging.getLogger(__name__)
    safe_logger = SafeLogger(logger)
    
    safe_logger.info("✓ Informação com unicode")
    safe_logger.warning("⚠️ Aviso com emoji")
    safe_logger.error("✗ Erro com símbolo")