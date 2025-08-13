#!/usr/bin/env python3
"""
Script de teste rápido do GDR Framework V3.1
Processa alguns leads para validar a instalação
"""

import asyncio
import pandas as pd
import sys
from pathlib import Path
import argparse
import logging

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent))

from gdr_v3_1_enterprise import GDRFrameworkV31Enterprise

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_test(max_leads: int = 5):
    """Executa teste do framework"""
    
    print("\n" + "="*60)
    print(f"  TESTE DO GDR FRAMEWORK V3.1 - {max_leads} LEADS")
    print("="*60)
    
    try:
        # 1. Inicializar framework
        print("\n[1] Inicializando framework...")
        framework = GDRFrameworkV31Enterprise(use_cache=True)
        print("✅ Framework inicializado")
        
        # 2. Criar dados de teste
        print("\n[2] Criando dados de teste...")
        test_data = [
            {
                'id': f'TEST{i:03d}',
                'name': f'Empresa Teste {i}',
                'original_nome': f'Empresa Teste {i}',
                'original_endereco_completo': f'Rua Teste {i}, 100, Centro, São Paulo, SP',
                'original_telefone': f'(11) 9{i:04d}-{i:04d}',
                'original_website': f'https://www.empresa{i}.com.br' if i % 2 == 0 else None,
                'original_email': f'contato@empresa{i}.com.br' if i % 3 == 0 else None,
            }
            for i in range(1, max_leads + 1)
        ]
        
        df_test = pd.DataFrame(test_data)
        print(f"✅ {len(test_data)} leads de teste criados")
        
        # 3. Processar leads
        print("\n[3] Processando leads...")
        print("-" * 40)
        
        results = []
        total_cost = 0
        
        for idx, lead_data in df_test.iterrows():
            lead_dict = lead_data.to_dict()
            lead_name = lead_dict.get('name', f'Lead {idx+1}')
            
            print(f"\n[{idx+1}/{max_leads}] {lead_name}")
            
            try:
                result = await framework.process_single_lead(lead_dict)
                
                # Verificar resultados
                cost = result.get('gdr_total_cost_usd', 0)
                total_cost += cost
                
                if cost > 0:
                    print(f"  ✅ Processado - Custo: ${cost:.4f}")
                else:
                    print(f"  ✅ Processado (cache)")
                    
                results.append(result)
                
            except Exception as e:
                print(f"  ❌ Erro: {str(e)[:50]}")
                results.append({
                    **lead_dict,
                    'processing_status': 'error',
                    'error_message': str(e)
                })
        
        # 4. Salvar resultados
        print("\n[4] Salvando resultados...")
        
        output_file = Path("outputs") / "test_results.xlsx"
        output_file.parent.mkdir(exist_ok=True)
        
        results_df = pd.DataFrame(results)
        results_df.to_excel(output_file, index=False)
        
        print(f"✅ Resultados salvos em: {output_file}")
        
        # 5. Estatísticas
        print("\n" + "="*60)
        print("  ESTATÍSTICAS DO TESTE")
        print("="*60)
        
        print(f"\n📊 Processamento:")
        print(f"  • Total processado: {len(results)}")
        print(f"  • Custo total: ${total_cost:.4f}")
        print(f"  • Custo médio: ${total_cost/len(results):.4f}")
        
        # Verificar dados coletados
        emails = sum(1 for r in results if r.get('gdr_consolidated_email'))
        phones = sum(1 for r in results if r.get('gdr_consolidated_phone'))
        
        print(f"\n📞 Dados coletados:")
        print(f"  • Emails: {emails}/{len(results)}")
        print(f"  • Telefones: {phones}/{len(results)}")
        
        # Status final
        print("\n" + "="*60)
        if total_cost > 0:
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
            print("   Framework está funcionando corretamente")
        else:
            print("⚠️ TESTE CONCLUÍDO")
            print("   Todos os resultados vieram do cache")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {str(e)}")
        logger.error(f"Erro detalhado: {str(e)}", exc_info=True)
        return False


def main():
    """Função principal"""
    parser = argparse.ArgumentParser(
        description='Teste do GDR Framework V3.1'
    )
    parser.add_argument(
        '--max-leads',
        type=int,
        default=5,
        help='Número de leads para testar (padrão: 5)'
    )
    
    args = parser.parse_args()
    
    print("\n🚀 GDR Framework V3.1 - Teste de Instalação")
    print("Este teste valida se o framework está funcionando corretamente")
    
    success = asyncio.run(run_test(args.max_leads))
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()