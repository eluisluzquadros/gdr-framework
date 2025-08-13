#!/usr/bin/env python3
"""
Pipeline completo do GDR Framework V3.1
Processa uma planilha real de leads com todas as funcionalidades
"""

import asyncio
import pandas as pd
import sys
from pathlib import Path
import argparse
import logging
from datetime import datetime
import json

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

from gdr_v3_1_enterprise import GDRFrameworkV31Enterprise

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_pipeline(
    input_file: str,
    max_leads: int = None,
    output_dir: str = "outputs"
):
    """
    Executa pipeline completo de processamento
    
    Args:
        input_file: Caminho para arquivo Excel de entrada
        max_leads: Número máximo de leads para processar
        output_dir: Diretório de saída
    """
    
    print("\n" + "="*80)
    print("                     GDR FRAMEWORK V3.1 - PIPELINE COMPLETO")
    print("="*80)
    
    start_time = datetime.now()
    
    try:
        # 1. Validar entrada
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {input_file}")
        
        print(f"\n📁 Arquivo de entrada: {input_path}")
        
        # 2. Carregar dados
        print("\n[1] Carregando dados...")
        df = pd.read_excel(input_path)
        total_leads = len(df)
        
        if max_leads:
            df = df.head(max_leads)
            print(f"✅ {len(df)} de {total_leads} leads carregados (limite: {max_leads})")
        else:
            print(f"✅ {total_leads} leads carregados")
        
        # 3. Inicializar framework
        print("\n[2] Inicializando framework...")
        framework = GDRFrameworkV31Enterprise(use_cache=True)
        print("✅ Framework inicializado com cache DuckDB")
        
        # 4. Processar leads
        print("\n[3] Processando leads...")
        print("-" * 60)
        
        results = []
        stats = {
            'total': len(df),
            'processed': 0,
            'errors': 0,
            'from_cache': 0,
            'total_cost': 0,
            'total_time': 0
        }
        
        for idx, row in df.iterrows():
            lead_data = row.to_dict()
            lead_name = lead_data.get('name', lead_data.get('original_nome', f'Lead {idx+1}'))
            
            print(f"\n[{idx+1}/{len(df)}] Processando: {lead_name[:50]}")
            
            try:
                lead_start = datetime.now()
                result = await framework.process_single_lead(lead_data)
                lead_time = (datetime.now() - lead_start).total_seconds()
                
                # Coletar estatísticas
                stats['processed'] += 1
                stats['total_time'] += lead_time
                
                if result.get('from_cache'):
                    stats['from_cache'] += 1
                    print(f"  ⚡ Cache hit! ({lead_time:.2f}s)")
                else:
                    cost = result.get('gdr_total_cost_usd', 0)
                    stats['total_cost'] += cost
                    print(f"  ✅ Processado em {lead_time:.2f}s - Custo: ${cost:.4f}")
                
                results.append(result)
                
            except Exception as e:
                stats['errors'] += 1
                print(f"  ❌ Erro: {str(e)[:100]}")
                logger.error(f"Erro processando {lead_name}: {str(e)}", exc_info=True)
                
                results.append({
                    **lead_data,
                    'processing_status': 'error',
                    'error_message': str(e)
                })
        
        # 5. Salvar resultados
        print("\n[4] Salvando resultados...")
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_file = output_path / f"gdr_results_{timestamp}.xlsx"
        json_file = output_path / f"gdr_stats_{timestamp}.json"
        
        # Salvar Excel
        results_df = pd.DataFrame(results)
        results_df.to_excel(excel_file, index=False)
        print(f"✅ Resultados salvos em: {excel_file}")
        
        # Salvar estatísticas
        stats['execution_time'] = (datetime.now() - start_time).total_seconds()
        stats['average_time'] = stats['total_time'] / stats['processed'] if stats['processed'] > 0 else 0
        stats['average_cost'] = stats['total_cost'] / stats['processed'] if stats['processed'] > 0 else 0
        stats['cache_hit_rate'] = stats['from_cache'] / stats['processed'] if stats['processed'] > 0 else 0
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"✅ Estatísticas salvas em: {json_file}")
        
        # 6. Análise dos resultados
        print("\n" + "="*80)
        print("                           ANÁLISE DOS RESULTADOS")
        print("="*80)
        
        print(f"\n📊 Estatísticas de Processamento:")
        print(f"  • Total processado: {stats['processed']}/{stats['total']}")
        print(f"  • Erros: {stats['errors']}")
        print(f"  • Cache hits: {stats['from_cache']} ({stats['cache_hit_rate']*100:.1f}%)")
        print(f"  • Tempo total: {stats['execution_time']:.1f}s")
        print(f"  • Tempo médio: {stats['average_time']:.1f}s/lead")
        
        print(f"\n💰 Custos:")
        print(f"  • Custo total: ${stats['total_cost']:.4f}")
        print(f"  • Custo médio: ${stats['average_cost']:.4f}/lead")
        print(f"  • Economia com cache: ${stats['from_cache'] * stats['average_cost']:.4f}")
        
        # Análise de dados coletados
        if stats['processed'] > 0:
            print(f"\n📞 Dados Coletados:")
            
            fields_to_check = [
                ('gdr_consolidated_email', 'Emails'),
                ('gdr_consolidated_phone', 'Telefones'),
                ('gdr_consolidated_website', 'Websites'),
                ('gdr_instagram_url', 'Instagram'),
                ('gdr_facebook_url', 'Facebook')
            ]
            
            for field, label in fields_to_check:
                if field in results_df.columns:
                    count = results_df[field].notna().sum()
                    pct = (count / stats['processed']) * 100
                    print(f"  • {label}: {count}/{stats['processed']} ({pct:.1f}%)")
            
            # Qualidade média
            if 'gdr_quality_score' in results_df.columns:
                avg_quality = results_df['gdr_quality_score'].mean()
                print(f"\n⭐ Qualidade Média: {avg_quality:.1f}/100")
            
            # Leads qualificados
            if 'gdr_sdr_qualified' in results_df.columns:
                qualified = results_df['gdr_sdr_qualified'].sum()
                print(f"✅ Leads Qualificados: {qualified}/{stats['processed']}")
        
        # 7. Status final
        print("\n" + "="*80)
        if stats['errors'] == 0 and stats['processed'] == stats['total']:
            print("🎉 PIPELINE CONCLUÍDO COM SUCESSO!")
            print(f"   Todos os {stats['total']} leads foram processados")
        elif stats['processed'] > 0:
            print("⚠️ PIPELINE CONCLUÍDO COM AVISOS")
            print(f"   {stats['processed']}/{stats['total']} leads processados")
            if stats['errors'] > 0:
                print(f"   {stats['errors']} erros encontrados")
        else:
            print("❌ PIPELINE FALHOU")
            print("   Nenhum lead foi processado com sucesso")
        print("="*80)
        
        return stats['errors'] == 0
        
    except Exception as e:
        print(f"\n❌ ERRO FATAL: {str(e)}")
        logger.error(f"Erro no pipeline: {str(e)}", exc_info=True)
        return False


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Pipeline completo do GDR Framework V3.1'
    )
    parser.add_argument(
        '--input',
        '-i',
        required=True,
        help='Arquivo Excel de entrada com leads'
    )
    parser.add_argument(
        '--max-leads',
        '-m',
        type=int,
        help='Número máximo de leads para processar'
    )
    parser.add_argument(
        '--output-dir',
        '-o',
        default='outputs',
        help='Diretório de saída (padrão: outputs)'
    )
    
    args = parser.parse_args()
    
    print("\n🚀 GDR Framework V3.1 Enterprise - Pipeline Completo")
    print("Sistema de enriquecimento e qualificação automatizada de leads")
    
    success = asyncio.run(run_pipeline(
        input_file=args.input,
        max_leads=args.max_leads,
        output_dir=args.output_dir
    ))
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()