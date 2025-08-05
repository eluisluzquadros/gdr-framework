#!/usr/bin/env python3
"""
GDR Complete Pipeline Demo
Demonstra pipeline completo: Coleta Google Places → Processamento GDR → Relatórios
"""

import asyncio
import argparse
import os
import time
from datetime import datetime
from pathlib import Path
import pandas as pd

# Imports dos módulos do GDR
from google_places_collector import collect_leads_from_google_places, SECTOR_CONFIGS
from gdr_mvp import GDRFramework
from run_gdr import print_banner, setup_directories, validate_environment

class CompletePipelineDemo:
    """Demo do pipeline completo GDR"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = Path(f"pipeline_demo_{self.timestamp}")
        self.output_dir.mkdir(exist_ok=True)
    
    async def run_complete_demo(self, sector: str, locations: list, max_leads: int = 30):
        """Executa demo completo do pipeline"""
        
        print("🚀 GDR COMPLETE PIPELINE DEMO")
        print("=" * 60)
        print(f"📍 Setor: {SECTOR_CONFIGS[sector]['description']}")
        print(f"🌍 Localizações: {', '.join(locations)}")
        print(f"📊 Max leads para processar: {max_leads}")
        print(f"📁 Diretório de saída: {self.output_dir}")
        print("=" * 60)
        
        total_start_time = time.time()
        
        # ETAPA 1: Coleta Google Places
        print("\n🔍 ETAPA 1: COLETA GOOGLE PLACES")
        print("-" * 40)
        
        places_file = self.output_dir / f"leads_collected_{sector}.xlsx"
        
        collect_start_time = time.time()
        
        config = SECTOR_CONFIGS[sector]
        collected_file = await collect_leads_from_google_places(
            queries=config['queries'],
            locations=locations,
            business_types=config['business_types'],
            output_file=str(places_file)
        )
        
        collect_end_time = time.time()
        collect_time = collect_end_time - collect_start_time
        
        # Analisar dados coletados
        df_collected = pd.read_excel(collected_file)
        
        print(f"✅ Coleta concluída em {collect_time:.1f}s")
        print(f"📊 Total de leads coletados: {len(df_collected)}")
        print(f"🏪 Negócios únicos: {df_collected['name'].nunique()}")
        print(f"⭐ Rating médio: {df_collected['placesRating'].mean():.2f}")
        print(f"📞 Com telefone: {df_collected['placesPhone'].notna().sum()}")
        print(f"🌐 Com website: {df_collected['placesWebsite'].notna().sum()}")
        
        # ETAPA 2: Processamento GDR
        print(f"\n🧠 ETAPA 2: PROCESSAMENTO GDR")
        print("-" * 40)
        
        # Limitar leads para processamento
        leads_to_process = min(max_leads, len(df_collected))
        print(f"📝 Processando {leads_to_process} leads...")
        
        # Criar subset da planilha
        df_subset = df_collected.head(leads_to_process)
        subset_file = self.output_dir / f"leads_subset_{leads_to_process}.xlsx"
        df_subset.to_excel(subset_file, index=False)
        
        # Processar com GDR
        gdr_start_time = time.time()
        
        gdr = GDRFramework()
        leads = gdr.load_leads_from_excel(str(subset_file))
        
        results, token_usages = await gdr.process_leads_batch(
            leads[:leads_to_process], 
            max_concurrent=3
        )
        
        gdr_end_time = time.time()
        gdr_time = gdr_end_time - gdr_start_time
        
        # Salvar resultados processados
        processed_file = self.output_dir / f"leads_processed_{sector}.xlsx"
        gdr.export_results(results, token_usages, str(processed_file))
        
        # ETAPA 3: Análise de Resultados
        print(f"\n📊 ETAPA 3: ANÁLISE DE RESULTADOS")
        print("-" * 40)
        
        successful = len([r for r in results if r.get('processing_status') == 'success'])
        total_tokens = sum(usage.total_tokens for usage in token_usages)
        total_cost = sum(usage.cost_usd for usage in token_usages)
        
        # Análise de enriquecimento
        enrichment_stats = self._analyze_enrichment(results)
        
        print(f"✅ GDR processamento concluído em {gdr_time:.1f}s")
        print(f"📈 Taxa de sucesso: {successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
        print(f"🔤 Tokens utilizados: {total_tokens:,}")
        print(f"💰 Custo total: ${total_cost:.6f}")
        print(f"📧 Emails encontrados: {enrichment_stats['emails_found']}")
        print(f"📞 Telefones consolidados: {enrichment_stats['phones_found']}")
        print(f"📱 WhatsApp encontrados: {enrichment_stats['whatsapp_found']}")
        print(f"⭐ Score médio qualidade: {enrichment_stats['avg_quality']:.3f}")
        
        # ETAPA 4: Relatório Executivo
        print(f"\n📋 ETAPA 4: RELATÓRIO EXECUTIVO")
        print("-" * 40)
        
        executive_report = self._generate_executive_report(
            sector, locations, df_collected, results, token_usages,
            collect_time, gdr_time
        )
        
        report_file = self.output_dir / f"executive_report_{sector}.xlsx"
        self._save_executive_report(executive_report, str(report_file))
        
        # RESUMO FINAL
        total_end_time = time.time()
        total_time = total_end_time - total_start_time
        
        print(f"\n🎉 PIPELINE COMPLETO CONCLUÍDO!")
        print("=" * 60)
        print(f"⏱️ Tempo total: {total_time:.1f} segundos")
        print(f"   └─ Coleta Google Places: {collect_time:.1f}s")
        print(f"   └─ Processamento GDR: {gdr_time:.1f}s")
        print(f"📁 Arquivos gerados:")
        print(f"   └─ 🔍 Leads coletados: {places_file.name}")
        print(f"   └─ 🧠 Leads processados: {processed_file.name}")
        print(f"   └─ 📊 Relatório executivo: {report_file.name}")
        print(f"💰 ROI estimado:")
        print(f"   └─ Custo de coleta: $0.00 (Google Places gratuito)")
        print(f"   └─ Custo de processamento: ${total_cost:.6f}")
        print(f"   └─ Custo por lead qualificado: ${total_cost/successful:.6f}")
        print(f"📈 Valor gerado:")
        print(f"   └─ Leads originais: {len(df_collected)}")
        print(f"   └─ Leads enriquecidos: {successful}")
        print(f"   └─ Taxa de enriquecimento: {successful/len(df_collected)*100:.1f}%")
        print("=" * 60)
        
        return {
            'output_dir': self.output_dir,
            'leads_collected': len(df_collected),
            'leads_processed': len(results),
            'leads_successful': successful,
            'total_cost': total_cost,
            'total_time': total_time,
            'files_generated': [places_file, processed_file, report_file]
        }
    
    def _analyze_enrichment(self, results: list) -> dict:
        """Analisa estatísticas de enriquecimento"""
        
        successful_results = [r for r in results if r.get('processing_status') == 'success']
        
        emails_found = len([r for r in successful_results if r.get('gdr_consolidated_email')])
        phones_found = len([r for r in successful_results if r.get('gdr_consolidated_phone')])
        whatsapp_found = len([r for r in successful_results if r.get('gdr_consolidated_whatsapp')])
        
        quality_scores = [r.get('gdr_quality_score', 0) for r in successful_results if r.get('gdr_quality_score')]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        return {
            'emails_found': emails_found,
            'phones_found': phones_found,
            'whatsapp_found': whatsapp_found,
            'avg_quality': avg_quality
        }
    
    def _generate_executive_report(self, sector: str, locations: list, df_collected: pd.DataFrame, 
                                 results: list, token_usages: list, collect_time: float, gdr_time: float) -> dict:
        """Gera relatório executivo completo"""
        
        successful_results = [r for r in results if r.get('processing_status') == 'success']
        total_cost = sum(usage.cost_usd for usage in token_usages)
        
        # Análise por localização
        location_analysis = {}
        for location in locations:
            location_leads = df_collected[df_collected['search_location'] == location]
            location_analysis[location] = {
                'leads_found': len(location_leads),
                'avg_rating': location_leads['placesRating'].mean(),
                'with_phone': location_leads['placesPhone'].notna().sum(),
                'with_website': location_leads['placesWebsite'].notna().sum()
            }
        
        # Análise por query
        query_analysis = {}
        for query in SECTOR_CONFIGS[sector]['queries']:
            query_leads = df_collected[df_collected['search_query'] == query]
            if len(query_leads) > 0:
                query_analysis[query] = {
                    'leads_found': len(query_leads),
                    'avg_rating': query_leads['placesRating'].mean(),
                    'top_cities': query_leads['city'].value_counts().head(3).to_dict()
                }
        
        # Análise de qualidade
        quality_distribution = {}
        for result in successful_results:
            score = result.get('gdr_quality_score', 0)
            if score >= 0.8:
                category = 'Alto (0.8+)'
            elif score >= 0.6:
                category = 'Médio (0.6-0.8)'
            elif score >= 0.4:
                category = 'Baixo (0.4-0.6)'
            else:
                category = 'Muito Baixo (<0.4)'
            
            quality_distribution[category] = quality_distribution.get(category, 0) + 1
        
        return {
            'pipeline_summary': {
                'sector': SECTOR_CONFIGS[sector]['description'],
                'locations_searched': locations,
                'execution_date': datetime.now().isoformat(),
                'total_execution_time': collect_time + gdr_time,
                'collection_time': collect_time,
                'processing_time': gdr_time
            },
            'collection_metrics': {
                'total_leads_collected': len(df_collected),
                'unique_businesses': df_collected['name'].nunique(),
                'avg_rating': df_collected['placesRating'].mean(),
                'leads_with_phone': df_collected['placesPhone'].notna().sum(),
                'leads_with_website': df_collected['placesWebsite'].notna().sum(),
                'by_location': location_analysis,
                'by_query': query_analysis
            },
            'processing_metrics': {
                'leads_processed': len(results),
                'successful_processing': len(successful_results),
                'success_rate': len(successful_results) / len(results) if results else 0,
                'total_tokens_used': sum(usage.total_tokens for usage in token_usages),
                'total_cost_usd': total_cost,
                'cost_per_lead': total_cost / len(results) if results else 0
            },
            'enrichment_results': {
                'emails_found': len([r for r in successful_results if r.get('gdr_consolidated_email')]),
                'phones_consolidated': len([r for r in successful_results if r.get('gdr_consolidated_phone')]),
                'whatsapp_found': len([r for r in successful_results if r.get('gdr_consolidated_whatsapp')]),
                'websites_confirmed': len([r for r in successful_results if r.get('gdr_consolidated_website')]),
                'quality_distribution': quality_distribution
            },
            'roi_analysis': {
                'collection_cost': 0.0,  # Google Places é gratuito até certo limite
                'processing_cost': total_cost,
                'total_investment': total_cost,
                'leads_qualified': len(successful_results),
                'cost_per_qualified_lead': total_cost / len(successful_results) if successful_results else 0,
                'potential_value_per_lead': 50.0,  # Estimativa
                'estimated_roi': (50.0 * len(successful_results) - total_cost) / total_cost if total_cost > 0 else 0
            }
        }
    
    def _save_executive_report(self, report: dict, output_file: str):
        """Salva relatório executivo em Excel"""
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            
            # Aba 1: Resumo Executivo
            summary_data = []
            summary_data.append(['Pipeline Execution Summary', ''])
            summary_data.append(['Setor', report['pipeline_summary']['sector']])
            summary_data.append(['Data de Execução', report['pipeline_summary']['execution_date']])
            summary_data.append(['Tempo Total (segundos)', report['pipeline_summary']['total_execution_time']])
            summary_data.append(['', ''])
            summary_data.append(['Métricas de Coleta', ''])
            summary_data.append(['Leads Coletados', report['collection_metrics']['total_leads_collected']])
            summary_data.append(['Negócios Únicos', report['collection_metrics']['unique_businesses']])
            summary_data.append(['Rating Médio', f"{report['collection_metrics']['avg_rating']:.2f}"])
            summary_data.append(['', ''])
            summary_data.append(['Métricas de Processamento', ''])
            summary_data.append(['Leads Processados', report['processing_metrics']['leads_processed']])
            summary_data.append(['Taxa de Sucesso', f"{report['processing_metrics']['success_rate']*100:.1f}%"])
            summary_data.append(['Custo Total (USD)', f"${report['processing_metrics']['total_cost_usd']:.6f}"])
            summary_data.append(['Custo por Lead', f"${report['processing_metrics']['cost_per_lead']:.6f}"])
            summary_data.append(['', ''])
            summary_data.append(['ROI Estimado', f"{report['roi_analysis']['estimated_roi']*100:.1f}%"])
            
            pd.DataFrame(summary_data, columns=['Métrica', 'Valor']).to_excel(
                writer, sheet_name='Resumo Executivo', index=False
            )
            
            # Aba 2: Análise por Localização
            location_data = []
            for location, metrics in report['collection_metrics']['by_location'].items():
                location_data.append([
                    location,
                    metrics['leads_found'],
                    f"{metrics['avg_rating']:.2f}",
                    metrics['with_phone'],
                    metrics['with_website']
                ])
            
            pd.DataFrame(location_data, columns=[
                'Localização', 'Leads Encontrados', 'Rating Médio', 
                'Com Telefone', 'Com Website'
            ]).to_excel(writer, sheet_name='Análise por Localização', index=False)
            
            # Aba 3: Distribuição de Qualidade
            quality_data = []
            for category, count in report['enrichment_results']['quality_distribution'].items():
                quality_data.append([category, count])
            
            pd.DataFrame(quality_data, columns=[
                'Categoria de Qualidade', 'Quantidade'
            ]).to_excel(writer, sheet_name='Distribuição de Qualidade', index=False)
        
        print(f"📊 Relatório executivo salvo: {output_file}")

async def main():
    """Função principal para demo"""
    
    parser = argparse.ArgumentParser(description='GDR Complete Pipeline Demo')
    
    parser.add_argument(
        '--sector', '-s',
        choices=list(SECTOR_CONFIGS.keys()),
        default='celulares_acessorios',
        help='Setor para busca'
    )
    
    parser.add_argument(
        '--locations', '-l',
        nargs='+',
        default=['Santa Cruz do Sul, RS', 'Venâncio Aires, RS'],
        help='Lista de localizações para busca'
    )
    
    parser.add_argument(
        '--max-leads', '-m',
        type=int,
        default=20,
        help='Máximo de leads para processar com GDR'
    )
    
    args = parser.parse_args()
    
    # Validações
    print_banner()
    setup_directories()
    
    if not validate_environment():
        print("❌ Erro na validação do ambiente")
        return 1
    
    # Executar demo completo
    demo = CompletePipelineDemo()
    
    try:
        results = await demo.run_complete_demo(
            sector=args.sector,
            locations=args.locations,
            max_leads=args.max_leads
        )
        
        print(f"\n🎯 DEMO CONCLUÍDA COM SUCESSO!")
        print(f"📁 Todos os arquivos estão em: {results['output_dir']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro durante execução: {e}")
        return 1

if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
