#!/usr/bin/env python3
"""
GDR Framework - Execution Script
Simplified runner for the MVP
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Adicionar o diretório atual ao path para imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Importar o framework principal
from gdr_mvp import GDRFramework, logger

def setup_directories():
    """Cria diretórios necessários"""
    directories = ['outputs', 'logs', 'temp']
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        logger.info(f"Diretório criado/verificado: {directory}")

def validate_environment():
    """Valida se as variáveis de ambiente estão configuradas"""
    required_vars = [
        'OPENAI_API_KEY',
        'GOOGLE_CSE_API_KEY',
        'GOOGLE_CSE_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Variáveis de ambiente faltando: {missing_vars}")
        logger.error("Configure o arquivo .env com suas chaves de API")
        return False
    
    logger.info("Variáveis de ambiente validadas com sucesso")
    return True

def print_banner():
    """Imprime banner do GDR"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    GDR Framework MVP                         ║
    ║            Generative Development Representative             ║
    ║                                                              ║
    ║  🤖 Multi-LLM Lead Enrichment & Consensus                   ║
    ║  📊 Statistical Analysis with Kappa Scores                  ║
    ║  💰 Token Usage & Cost Tracking                             ║
    ║  📈 Professional Excel Reports                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

async def run_processing(input_file: str, max_leads: int = 50, output_dir: str = "outputs"):
    """Executa o processamento principal"""
    
    logger.info("=" * 60)
    logger.info("INICIANDO PROCESSAMENTO GDR")
    logger.info("=" * 60)
    
    # Verificar se arquivo de entrada existe
    if not Path(input_file).exists():
        logger.error(f"Arquivo de entrada não encontrado: {input_file}")
        return False
    
    # Criar nome do arquivo de saída
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = Path(output_dir) / f"gdr_results_{timestamp}.xlsx"
    
    try:
        # Inicializar framework
        logger.info("Inicializando GDR Framework...")
        gdr = GDRFramework()
        
        # Carregar leads
        logger.info(f"Carregando leads de: {input_file}")
        all_leads = gdr.load_leads_from_excel(input_file)
        
        if not all_leads:
            logger.error("Nenhum lead válido encontrado no arquivo")
            return False
        
        # Limitar número de leads para processamento
        test_leads = all_leads[:max_leads]
        logger.info(f"Processando {len(test_leads)} leads (máximo configurado: {max_leads})")
        
        # Estimar custos
        estimated_cost = len(test_leads) * 0.001  # Estimativa básica
        logger.info(f"Custo estimado: ${estimated_cost:.3f} USD")
        
        # Confirmar processamento
        if max_leads > 20:
            response = input(f"\nProcessar {len(test_leads)} leads? (y/N): ")
            if response.lower() != 'y':
                logger.info("Processamento cancelado pelo usuário")
                return False
        
        # Processar leads
        logger.info("Iniciando processamento...")
        start_time = datetime.now()
        
        results, token_usages = await gdr.process_leads_batch(
            test_leads, 
            max_concurrent=3
        )
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Estatísticas do processamento
        successful = len([r for r in results if r.get('processing_status') == 'success'])
        total_tokens = sum(usage.total_tokens for usage in token_usages)
        total_cost = sum(usage.cost_usd for usage in token_usages)
        
        logger.info("=" * 60)
        logger.info("PROCESSAMENTO CONCLUÍDO")
        logger.info("=" * 60)
        logger.info(f"⏱️  Tempo total: {processing_time:.1f} segundos")
        logger.info(f"📊 Leads processados: {len(results)}")
        logger.info(f"✅ Sucessos: {successful}")
        logger.info(f"❌ Falhas: {len(results) - successful}")
        logger.info(f"🔤 Tokens utilizados: {total_tokens:,}")
        logger.info(f"💰 Custo total: ${total_cost:.6f} USD")
        logger.info(f"📈 Custo médio/lead: ${total_cost/len(results):.6f} USD")
        
        # Exportar resultados
        logger.info(f"Exportando resultados para: {output_file}")
        gdr.export_results(results, token_usages, str(output_file))
        
        # Relatório final
        print("\n" + "=" * 60)
        print("🎉 PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
        print("=" * 60)
        print(f"📁 Arquivo de resultados: {output_file}")
        print(f"📊 Taxa de sucesso: {successful/len(results)*100:.1f}%")
        print(f"💰 Custo total: ${total_cost:.6f} USD")
        print(f"⚡ Velocidade: {len(results)/processing_time:.2f} leads/segundo")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Erro durante processamento: {e}")
        return False

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='GDR Framework MVP - Lead Processing')
    
    parser.add_argument(
        '--input', '-i',
        default='leads.xlsx',
        help='Arquivo Excel de entrada (default: leads.xlsx)'
    )
    
    parser.add_argument(
        '--max-leads', '-m',
        type=int,
        default=50,
        help='Número máximo de leads para processar (default: 50)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        default='outputs',
        help='Diretório de saída (default: outputs)'
    )
    
    parser.add_argument(
        '--validate-only', '-v',
        action='store_true',
        help='Apenas validar configuração sem processar'
    )
    
    args = parser.parse_args()
    
    # Banner
    print_banner()
    
    # Setup
    setup_directories()
    
    # Validar ambiente
    if not validate_environment():
        return 1
    
    if args.validate_only:
        print("✅ Configuração validada com sucesso!")
        return 0
    
    # Executar processamento
    try:
        success = asyncio.run(run_processing(
            args.input,
            args.max_leads,
            args.output_dir
        ))
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("Processamento interrompido pelo usuário")
        return 1
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
