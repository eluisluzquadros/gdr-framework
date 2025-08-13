#!/usr/bin/env python3
"""
GDR Framework V3.1 Enterprise
Framework completo com todas as melhorias e funcionalidades avançadas:
- Multi-LLM com 5 providers (OpenAI, Claude, Gemini, DeepSeek, ZhipuAI)
- Estimativa de custos e tokens
- Retry automático inteligente
- Detecção melhorada de Linktree
- Facebook com 7 estratégias
- Revisão de qualidade automática
- Processamento em lotes com checkpointing
- Relatório completo de performance
"""

import asyncio
import pandas as pd
import numpy as np
import json
import os
import sys
import argparse
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import traceback

# Configurar path para imports
sys.path.insert(0, str(Path(__file__).parent))

# Importar módulos do framework
from llm_analyzer_v3 import LLMAnalyzerV3
from token_estimator import TokenEstimator, TokenUsage
from quality_reviewer import QualityReviewer, QualityReport
from scrapers.smart_orchestrator import SmartOrchestrator, ScraperTask, ScraperPriority
from scrapers.linktree_detector import LinktreeDetector
from scrapers.facebook_alternative import FacebookAlternativeScraper
from scrapers.apify_real_scrapers import ApifyRealScrapers, GoogleSearchEngineReal
from scrapers.website_scraper_enhanced import EnhancedWebsiteScraper
from database.lead_cache import LeadCache  # Adicionar cache DuckDB

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gdr_v3_1_enterprise.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GDRFrameworkV31Enterprise:
    """
    GDR Framework V3.1 Enterprise
    Framework completo com todas as funcionalidades avançadas
    """
    
    def __init__(self, use_cache: bool = True):
        """
        Inicializa o framework enterprise completo
        
        Args:
            use_cache: Se True, usa cache DuckDB para evitar reprocessamento
        """
        logger.info("="*80)
        logger.info(" GDR FRAMEWORK V3.1 ENTERPRISE ".center(80))
        logger.info(" SISTEMA COMPLETO DE ENRIQUECIMENTO DE LEADS ".center(80))
        logger.info("="*80)
        
        # Verificar configuração das APIs
        self._check_api_configuration()
        
        # Inicializar componentes principais
        logger.info("Inicializando componentes do framework...")
        
        # 0. Cache DuckDB para persistência e recuperação
        self.use_cache = use_cache
        if self.use_cache:
            self.cache = LeadCache("data/gdr_v31_cache.duckdb")
            logger.info("✓ Cache DuckDB inicializado para persistência")
        else:
            self.cache = None
            logger.info("⚠ Cache desabilitado - reprocessamento completo")
        
        # 1. Analisador Multi-LLM (5 providers)
        self.llm_analyzer = LLMAnalyzerV3()
        logger.info("✓ LLM Analyzer V3 inicializado (OpenAI, Claude, Gemini, DeepSeek, ZhipuAI)")
        
        # 2. Estimador de tokens e custos
        self.token_estimator = TokenEstimator()
        logger.info("✓ Token Estimator inicializado")
        
        # 3. Revisor de qualidade
        self.quality_reviewer = QualityReviewer()
        logger.info("✓ Quality Reviewer inicializado")
        
        # 4. Orquestrador inteligente
        self.smart_orchestrator = SmartOrchestrator(
            max_concurrent=3,
            global_timeout=300.0,
            retry_strategy='exponential'
        )
        logger.info("✓ Smart Orchestrator inicializado")
        
        # 5. Detector de Linktree melhorado
        self.linktree_detector = LinktreeDetector()
        logger.info("✓ Linktree Detector inicializado")
        
        # 6. Scrapers especializados
        self.facebook_scraper = FacebookAlternativeScraper()
        self.apify_scrapers = ApifyRealScrapers()
        self.website_scraper = EnhancedWebsiteScraper()
        self.google_search = GoogleSearchEngineReal()
        logger.info("✓ Scrapers especializados inicializados")
        
        # Estatísticas de processamento
        self.processing_stats = {
            'total_leads': 0,
            'successful_leads': 0,
            'failed_leads': 0,
            'total_time': 0,
            'average_time_per_lead': 0,
            'token_usage': {},
            'cost_breakdown': {},
            'quality_metrics': {},
            'scraper_performance': {},
            'llm_performance': {},
            'errors': []
        }
        
        # Cache de checkpoints
        self.checkpoint_dir = Path("gdr_checkpoints_v31")
        self.checkpoint_dir.mkdir(exist_ok=True)
        
        logger.info("="*80)
        logger.info("Framework V3.1 Enterprise inicializado com sucesso!")
        logger.info(f"✓ {len(self.llm_analyzer.providers)} LLMs disponíveis")
        logger.info("✓ Retry automático ativado")
        logger.info("✓ Estimativa de custos ativa")
        logger.info("✓ Revisão de qualidade ativa")
        logger.info("✓ Detecção Linktree melhorada")
        logger.info("✓ Facebook com 7 estratégias")
        logger.info("="*80)
    
    def _check_api_configuration(self):
        """Verifica configuração das APIs"""
        from dotenv import load_dotenv
        load_dotenv()
        
        required_apis = {
            'OPENAI_API_KEY': 'OpenAI GPT',
            'ANTHROPIC_API_KEY': 'Claude (Anthropic)',
            'GEMINI_API_KEY': 'Google Gemini',
            'DEEPSEEK_API_KEY': 'DeepSeek',
            'ZHIPUAI_API_KEY': 'ZhipuAI (GLM)',
            'APIFY_API_KEY': 'Apify (Instagram, etc)',
            'GOOGLE_CSE_API_KEY': 'Google Custom Search',
            'GOOGLE_CSE_ID': 'Google Search Engine ID'
        }
        
        configured = []
        missing = []
        
        for key, name in required_apis.items():
            if os.getenv(key):
                configured.append(name)
            else:
                missing.append(f"{name} ({key})")
        
        logger.info(f"APIs configuradas: {len(configured)}/{len(required_apis)}")
        for api in configured:
            logger.info(f"  [OK] {api}")
        
        if missing:
            logger.warning("APIs não configuradas (funcionalidade limitada):")
            for api in missing:
                logger.warning(f"  [!] {api}")
    
    async def estimate_batch_cost(self, 
                                 num_leads: int, 
                                 llm_models: List[str] = None,
                                 analyses_per_llm: int = 10) -> Dict[str, Any]:
        """
        Estima custo de processamento de um batch
        
        Args:
            num_leads: Número de leads
            llm_models: Lista de modelos LLM (None = todos disponíveis)
            analyses_per_llm: Número de análises por LLM
            
        Returns:
            Dict com estimativas detalhadas
        """
        if llm_models is None:
            llm_models = list(self.llm_analyzer.providers.keys())
            # Mapear para nomes dos modelos
            model_mapping = {
                'openai': 'gpt-4o-mini',
                'claude': 'claude-3-haiku-20240307',
                'gemini': 'gemini-1.5-flash',
                'deepseek': 'deepseek-chat',
                'zhipuai': 'glm-4-flash'
            }
            llm_models = [model_mapping.get(llm, llm) for llm in llm_models]
        
        estimates = self.token_estimator.estimate_batch_processing(
            num_leads=num_leads,
            llm_models=llm_models,
            analyses_per_llm=analyses_per_llm
        )
        
        # Adicionar custos dos scrapers (estimativa fixa)
        scraper_cost_per_lead = 0.001  # $0.001 por lead para APIs
        estimates['scraper_cost'] = num_leads * scraper_cost_per_lead
        estimates['total_cost'] += estimates['scraper_cost']
        estimates['cost_per_lead'] = estimates['total_cost'] / num_leads if num_leads > 0 else 0
        
        return estimates
    
    def print_cost_estimate(self, estimates: Dict[str, Any]):
        """Imprime estimativa de custos formatada"""
        print("\n" + "="*80)
        print(" ESTIMATIVA DE CUSTOS - GDR V3.1 ENTERPRISE ".center(80))
        print("="*80)
        
        print(f"\n[CONFIG] CONFIGURACAO:")
        print(f"  - Total de leads: {estimates['total_leads']:,}")
        print(f"  - Modelos LLM: {len(estimates['llm_models'])}")
        print(f"  - Analises por LLM: {estimates['analyses_per_llm']}")
        
        print(f"\n[$$] BREAKDOWN DE CUSTOS:")
        
        # LLMs
        total_llm_cost = sum(data['cost'] for data in estimates['by_model'].values())
        print(f"  LLMs: {self.token_estimator.format_cost(total_llm_cost)}")
        for model, data in estimates['by_model'].items():
            print(f"    - {model}: {self.token_estimator.format_cost(data['cost'])}")
        
        # Scrapers
        print(f"  Scrapers: {self.token_estimator.format_cost(estimates['scraper_cost'])}")
        
        print(f"\n[TOTAL] TOTAIS:")
        print(f"  - Tokens estimados: {estimates['total_tokens']:,}")
        print(f"  - Custo total: {self.token_estimator.format_cost(estimates['total_cost'])}")
        print(f"  - Custo por lead: {self.token_estimator.format_cost(estimates['cost_per_lead'])}")
        
        # Warning se custo for alto
        if estimates['total_cost'] > 50:
            print(f"\n[!] ATENCAO: Custo estimado acima de $50")
            print(f"   Considere processar em batches menores")
        
        print("="*80)
    
    async def process_batch(self, 
                           input_file: str,
                           output_file: str = None,
                           batch_size: int = 10,
                           max_leads: int = 75,
                           estimate_only: bool = False) -> Optional[pd.DataFrame]:
        """
        Processa batch de leads com todas as funcionalidades V3.1
        
        Args:
            input_file: Arquivo de entrada
            output_file: Arquivo de saída (None = auto)
            batch_size: Tamanho do batch
            max_leads: Máximo de leads
            estimate_only: Se True, apenas estima custos
            
        Returns:
            DataFrame com resultados ou None se estimate_only
        """
        start_time = time.time()
        
        # Carregar dados
        logger.info(f"Carregando dados de: {input_file}")
        try:
            df = pd.read_excel(input_file)
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo: {e}")
            return None
        
        # Limitar número de leads
        if max_leads and len(df) > max_leads:
            df = df.head(max_leads)
            logger.info(f"Limitando a {max_leads} leads")
        
        total_leads = len(df)
        self.processing_stats['total_leads'] = total_leads
        
        # Estimativa de custos
        logger.info("Calculando estimativa de custos...")
        cost_estimates = await self.estimate_batch_cost(total_leads)
        self.print_cost_estimate(cost_estimates)
        
        if estimate_only:
            logger.info("Modo estimate_only ativado. Finalizando.")
            return None
        
        # Confirmar processamento se custo for alto
        if cost_estimates['total_cost'] > 10:
            print(f"\n[!] Custo estimado: {self.token_estimator.format_cost(cost_estimates['total_cost'])}")
            confirm = input("Deseja continuar? (s/N): ").lower().strip()
            if confirm != 's':
                logger.info("Processamento cancelado pelo usuário")
                return None
        
        # Configurar arquivo de saída
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"outputs/gdr_v31_enterprise_{timestamp}.xlsx"
        
        # Criar diretório de saída
        Path(output_file).parent.mkdir(exist_ok=True, parents=True)
        
        logger.info(f"\nIniciando processamento V3.1 Enterprise")
        logger.info(f"Total de leads: {total_leads}")
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"Saída: {output_file}")
        logger.info("="*80)
        
        # Processar em batches
        results = []
        total_batches = (total_leads + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_leads)
            batch_df = df.iloc[start_idx:end_idx]
            
            logger.info(f"\n{'='*60}")
            logger.info(f"PROCESSANDO BATCH {batch_num + 1}/{total_batches}")
            logger.info(f"Leads {start_idx + 1} a {end_idx} ({len(batch_df)} leads)")
            logger.info(f"{'='*60}")
            
            # Processar batch
            batch_results = await self._process_batch_internal(batch_df, batch_num + 1)
            results.extend(batch_results)
            
            # Salvar checkpoint
            self._save_checkpoint(results, batch_num + 1)
            
            # Log progresso
            processed = len(results)
            progress = (processed / total_leads) * 100
            logger.info(f"\nProgresso geral: {processed}/{total_leads} ({progress:.1f}%)")
            
            # Pausa entre batches se necessário
            if batch_num < total_batches - 1:
                await asyncio.sleep(2)
        
        # Criar DataFrame final
        results_df = pd.DataFrame(results)
        
        # Aplicar ordenação de colunas
        results_df = self._order_columns(results_df)
        
        # Salvar resultados
        logger.info(f"\nSalvando resultados em: {output_file}")
        results_df.to_excel(output_file, index=False)
        
        # Calcular estatísticas finais
        self.processing_stats['total_time'] = time.time() - start_time
        self.processing_stats['average_time_per_lead'] = self.processing_stats['total_time'] / total_leads
        
        # Análise de qualidade do batch
        logger.info("Executando análise de qualidade do batch...")
        batch_quality = self.quality_reviewer.review_batch(results_df)
        self.processing_stats['quality_metrics'] = batch_quality
        
        # Gerar relatório final
        self._generate_final_report(results_df, cost_estimates, batch_quality)
        
        return results_df
    
    async def _process_batch_internal(self, batch_df: pd.DataFrame, batch_num: int) -> List[Dict]:
        """Processa um batch interno de leads"""
        batch_results = []
        
        for idx, row in batch_df.iterrows():
            lead_num = idx + 1
            logger.info(f"\n[BATCH {batch_num}] Processando Lead {lead_num}")
            logger.info("-" * 50)
            
            try:
                # Processar lead individual
                result = await self.process_single_lead(row.to_dict())
                batch_results.append(result)
                
                # Atualizar estatísticas
                if result.get('processing_status') == 'completed':
                    self.processing_stats['successful_leads'] += 1
                else:
                    self.processing_stats['failed_leads'] += 1
                    
            except Exception as e:
                logger.error(f"Erro crítico no Lead {lead_num}: {e}")
                logger.error(traceback.format_exc())
                
                # Criar resultado de erro
                error_result = self._create_error_result(row.to_dict(), str(e))
                batch_results.append(error_result)
                self.processing_stats['failed_leads'] += 1
                self.processing_stats['errors'].append({
                    'lead': lead_num,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return batch_results
    
    async def process_single_lead(self, lead_data: Dict) -> Dict:
        """
        Processa um único lead com todas as funcionalidades V3.1
        Agora com cache DuckDB para evitar reprocessamento
        
        Args:
            lead_data: Dados do lead
            
        Returns:
            Dict com resultado completo
        """
        start_time = time.time()
        
        # VALIDAÇÃO E LIMPEZA DE TIPOS
        lead_data = self._validate_and_clean_lead_data(lead_data)
        
        lead_name = lead_data.get('name', lead_data.get('tradeName', 'Lead'))
        # Garantir que lead_id seja sempre string para consistência no cache
        lead_id = str(lead_data.get('id', lead_data.get('cnpj', lead_name)))
        
        # VERIFICAR CACHE PRIMEIRO
        if self.use_cache and self.cache:
            cached_result = self.cache.get_lead(lead_id)
            if cached_result:
                # Verificar idade do cache (7 dias por padrão)
                cache_age_days = 7
                if self.cache.is_recent(lead_id, days=cache_age_days):
                    logger.info(f"✓ Lead '{lead_name}' encontrado no cache (pulando processamento)")
                    # Adicionar flag indicando que veio do cache
                    cached_result['from_cache'] = True
                    cached_result['cache_hit'] = True
                    return cached_result
                else:
                    logger.info(f"⚠ Cache expirado para '{lead_name}' (>{cache_age_days} dias)")
        
        logger.info(f"Iniciando processamento completo: {lead_name}")
        
        # 1. PRESERVAR DADOS ORIGINAIS (já limpos)
        result = self._preserve_original_data(lead_data)
        result['from_cache'] = False
        result['cache_hit'] = False
        
        # 2. EXECUTAR SCRAPERS COM ORQUESTRAÇÃO INTELIGENTE
        logger.info("Executando scrapers com retry automático...")
        
        # Verificar cache parcial para scrapers
        cached_scrapers = {}
        if self.use_cache and self.cache:
            # Buscar resultados de scrapers no cache
            cached_scrapers = self.cache.get_scraper_results(lead_id)
            if cached_scrapers:
                logger.info(f"✓ Encontrados {len(cached_scrapers)} scrapers no cache")
        
        scraper_tasks = self._create_scraper_tasks(lead_data, cached_scrapers)
        
        # Se temos dados em cache, adicionar ao resultado
        if cached_scrapers:
            # Criar estrutura de resultado com dados cacheados
            scraper_results = {
                'results': cached_scrapers.copy(),
                'stats': {
                    'total_tasks': len(scraper_tasks) + len(cached_scrapers),
                    'successful': len(cached_scrapers),
                    'failed': 0,
                    'retried': 0
                }
            }
            
            # Executar apenas tarefas não cacheadas
            if scraper_tasks:
                new_results = await self.smart_orchestrator.execute_tasks(scraper_tasks)
                # Mesclar resultados novos com cacheados
                scraper_results['results'].update(new_results['results'])
                scraper_results['stats']['successful'] += new_results['stats']['successful']
                scraper_results['stats']['failed'] += new_results['stats']['failed']
                scraper_results['stats']['retried'] += new_results['stats']['retried']
        else:
            # Sem cache, executar todas as tarefas
            scraper_results = await self.smart_orchestrator.execute_tasks(scraper_tasks)
        
        # Consolidar resultados dos scrapers
        for scraper_name, scraper_data in scraper_results['results'].items():
            if isinstance(scraper_data, dict):
                result.update(scraper_data)
        
        # 3. DETECÇÃO MELHORADA DE LINKTREE
        logger.info("Executando detecção melhorada de Linktree...")
        result = self.linktree_detector.enrich_with_detection(result)
        
        # 4. CONSOLIDAÇÃO DE CONTATOS (ETAPA 1)
        logger.info("Consolidando contatos coletados...")
        contact_consolidation = self._consolidate_contacts(result)
        result.update(contact_consolidation)
        
        # 5. ANÁLISE MULTI-LLM COM TODOS OS 5 PROVIDERS
        logger.info("Executando análise Multi-LLM (5 providers)...")
        
        # Executar análise com todos os LLMs disponíveis
        # analyze_all_llms espera (lead_data, scraped_data)
        try:
            llm_results = await self.llm_analyzer.analyze_all_llms(lead_data, result)
            
            if llm_results:
                result.update(llm_results)
                logger.info(f"LLM análise completa: {len(llm_results)} campos adicionados")
                
                # Calcular custo estimado
                num_analyses = len([k for k in llm_results.keys() if 'gdr_llm_' in k])
                estimated_cost = num_analyses * 0.0002  # ~$0.0002 por análise
                result['gdr_total_cost_usd'] = estimated_cost
                result['gdr_providers_used'] = list(self.llm_analyzer.providers.keys())
                logger.info(f"Custo LLM: ${estimated_cost:.4f}")
            else:
                logger.warning("Nenhum resultado LLM retornado")
                result['gdr_total_cost_usd'] = 0.0
                result['gdr_providers_used'] = []
        except Exception as e:
            logger.error(f"Erro na análise LLM: {e}")
            result['gdr_total_cost_usd'] = 0.0
            result['gdr_providers_used'] = []
        
        # Rastrear uso de tokens
        self._track_llm_usage(llm_results)
        
        # 6. CONSENSO MULTI-LLM
        logger.info("Calculando consenso Multi-LLM...")
        consensus = self.llm_analyzer.calculate_consensus(result)
        result.update(consensus)
        
        # 7. REVISÃO DE QUALIDADE AUTOMÁTICA
        logger.info("Executando revisão de qualidade...")
        quality_report = self.quality_reviewer.review_lead(result)
        
        # Adicionar métricas de qualidade
        result['gdr_quality_overall_score'] = quality_report.overall_score
        result['gdr_quality_completeness_score'] = quality_report.completeness_score
        result['gdr_quality_accuracy_score'] = quality_report.accuracy_score
        result['gdr_quality_consistency_score'] = quality_report.consistency_score
        result['gdr_quality_enrichment_score'] = quality_report.enrichment_score
        result['gdr_quality_issues'] = json.dumps(quality_report.issues)
        result['gdr_quality_suggestions'] = json.dumps(quality_report.suggestions)
        
        # 8. METADADOS E ESTATÍSTICAS
        processing_time = time.time() - start_time
        result['processing_time_seconds'] = round(processing_time, 2)
        result['processing_timestamp'] = datetime.now().isoformat()
        result['processing_status'] = 'completed'
        result['framework_version'] = 'v3.1-enterprise'
        result['scrapers_used'] = len(scraper_results['results'])
        result['scrapers_successful'] = scraper_results['stats']['successful']
        result['scrapers_failed'] = scraper_results['stats']['failed']
        result['scrapers_retried'] = scraper_results['stats']['retried']
        
        # Log resumo
        logger.info(f"Lead processado em {processing_time:.1f}s")
        logger.info(f"Qualidade geral: {quality_report.overall_score:.1f}/100")
        logger.info(f"Scrapers: {scraper_results['stats']['successful']}/{scraper_results['stats']['total_tasks']} sucessos")
        
        # SALVAR NO CACHE DUCKDB
        if self.use_cache and self.cache:
            try:
                # Salvar resultado completo
                self.cache.save_lead(lead_id, result)
                
                # Salvar resultados dos scrapers separadamente para cache parcial
                for scraper_name, scraper_data in scraper_results['results'].items():
                    if isinstance(scraper_data, dict) and scraper_data:
                        self.cache.save_scraper_result(lead_id, scraper_name, scraper_data)
                
                logger.info(f"✓ Lead '{lead_name}' salvo no cache DuckDB")
            except Exception as e:
                logger.error(f"Erro ao salvar no cache: {e}")
        
        return result
    
    def _create_scraper_tasks(self, lead_data: Dict, cached_scrapers: Dict = None) -> List[ScraperTask]:
        """Cria lista de tarefas de scraping priorizadas, pulando scrapers em cache"""
        tasks = []
        cached_scrapers = cached_scrapers or {}
        
        # Instagram (prioridade alta se temos URL)
        if not cached_scrapers.get('instagram_scraper') and (lead_data.get('instagramUrl') or lead_data.get('instagram_url')):
            instagram_task = ScraperTask(
                name="instagram_scraper",
                function=self.apify_scrapers.scrape_instagram_profile,
                args=(lead_data.get('instagramUrl', lead_data.get('instagram_url', '')),),
                priority=ScraperPriority.HIGH,
                max_retries=3,
                timeout=45.0,
                required=True
            )
            tasks.append(instagram_task)
        
        # Facebook via Apify (dados reais com curious_coder/facebook-profile-scraper)
        if not cached_scrapers.get('facebook_scraper'):
            facebook_url = lead_data.get('facebookUrl', '')
            if not facebook_url:
                # Tentar construir URL baseado no nome
                company_name = lead_data.get('name', '').lower().replace(' ', '').replace(',', '')
                facebook_url = f"https://www.facebook.com/{company_name}"
            
            facebook_task = ScraperTask(
            name="facebook_scraper",
            function=self.apify_scrapers.scrape_facebook_profile,
            args=(facebook_url,),
            priority=ScraperPriority.MEDIUM,
            max_retries=3,
            timeout=60.0,
            required=False
            )
            tasks.append(facebook_task)
        
        # Website (se temos URL)
        if not cached_scrapers.get('website_scraper') and (lead_data.get('website') or lead_data.get('placesWebsite')):
            website_url = lead_data.get('website', lead_data.get('placesWebsite', ''))
            website_task = ScraperTask(
                name="website_scraper",
                function=self.website_scraper.scrape_website_smart,
                args=(website_url,),
                kwargs={'use_crawl4ai': True},
                priority=ScraperPriority.HIGH,
                max_retries=2,
                timeout=30.0,
                required=False
            )
            tasks.append(website_task)
        
        # Google Search
        if not cached_scrapers.get('google_search'):
            google_task = ScraperTask(
            name="google_search",
            function=self.google_search.search_company_info,
            args=(lead_data.get('name', ''), f"{lead_data.get('city', '')}, {lead_data.get('state', '')}"),
            priority=ScraperPriority.MEDIUM,
            max_retries=2,
            timeout=20.0,
            required=False
        )
        tasks.append(google_task)
        
        return tasks
    
    def _validate_and_clean_lead_data(self, lead_data: Dict) -> Dict:
        """
        Valida e limpa dados do lead, corrigindo tipos incorretos
        Especialmente importante para dados vindos do Excel que podem ter NaN/float
        """
        import pandas as pd
        
        cleaned = {}
        
        for key, value in lead_data.items():
            # Tratar NaN e None
            if pd.isna(value) or value is None:
                cleaned[key] = ''
                continue
            
            # URLs e campos de texto que podem vir como float
            url_fields = ['website', 'placesWebsite', 'instagramUrl', 'facebookUrl', 
                         'linkedinUrl', 'youtubeUrl', 'tiktokUrl']
            text_fields = ['name', 'tradeName', 'city', 'state', 'address', 
                          'neighborhood', 'email', 'phone']
            
            if key in url_fields or key in text_fields:
                # Converter para string e limpar
                try:
                    str_value = str(value).strip()
                    # Verificar se não é "nan" ou valores inválidos
                    if str_value.lower() in ['nan', 'none', 'null']:
                        cleaned[key] = ''
                    else:
                        cleaned[key] = str_value
                except:
                    cleaned[key] = ''
            
            # Campos numéricos
            elif key in ['cnpj', 'zipCode', 'employees', 'revenue']:
                try:
                    # Manter como string mas limpar
                    cleaned[key] = str(value).strip()
                except:
                    cleaned[key] = ''
            
            # Campos booleanos
            elif key in ['active', 'verified', 'claimed']:
                cleaned[key] = bool(value) if value else False
            
            # Outros campos - manter como estão
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _preserve_original_data(self, lead_data: Dict) -> Dict:
        """Preserva dados originais com mapeamento completo"""
        result = {}
        
        # Mapeamento de campos originais
        field_mappings = {
            'original_id': lead_data.get('legalDocument', lead_data.get('id', '')),
            'original_nome': lead_data.get('name', lead_data.get('tradeName', '')),
            'original_endereco_completo': self._build_full_address(lead_data),
            'original_telefone': lead_data.get('phone', ''),
            'original_telefone_place': lead_data.get('placesPhone', ''),
            'original_website': lead_data.get('website', ''),
            'original_avaliacao_google': lead_data.get('placesRating', ''),
            'original_latitude': lead_data.get('placesLat', ''),
            'original_longitude': lead_data.get('placesLng', ''),
            'original_place_users': lead_data.get('placesUserRatingsTotal', ''),
            'original_place_website': lead_data.get('placesWebsite', ''),
            'original_email': lead_data.get('email', ''),
            'original_instagram_url': lead_data.get('instagramUrl', ''),
            'original_facebook_url': lead_data.get('facebookUrl', ''),
            'city': lead_data.get('city', ''),
            'state': lead_data.get('state', ''),
            'country': lead_data.get('country', 'Brasil')
        }
        
        for field, value in field_mappings.items():
            result[field] = str(value) if value and pd.notna(value) else ''
        
        return result
    
    def _build_full_address(self, lead_data: Dict) -> str:
        """Constrói endereço completo"""
        address_parts = []
        address_fields = ['street', 'number', 'complement', 'district', 'city', 'state', 'country', 'postalCode']
        
        for field in address_fields:
            value = lead_data.get(field)
            if value and pd.notna(value):
                address_parts.append(str(value))
        
        return ', '.join(address_parts) if address_parts else ''
    
    def _consolidate_contacts(self, data: Dict) -> Dict:
        """Consolida contatos de todas as fontes com priorização"""
        result = {}
        
        # Emails com priorização
        emails = [
            data.get('original_email'),
            data.get('gdr_website_emails'),  # Do website scraper
            data.get('gdr_google_search_email'),  # Do Google search
            data.get('gdr_facebook_email'),  # Do Facebook
            data.get('gdr_instagram_business_email'),  # Do Instagram
            data.get('gdr_instagram_public_email')  # Do Instagram
        ]
        
        # Processar lista de emails (pode ser string ou lista)
        all_emails = []
        for email_source in emails:
            if email_source:
                if isinstance(email_source, list):
                    all_emails.extend(email_source)
                elif isinstance(email_source, str) and '@' in email_source:
                    all_emails.append(email_source)
        
        # Filtrar emails válidos
        valid_emails = [e for e in all_emails if e and '@' in str(e) and '.' in str(e)]
        result['gdr_consolidated_email'] = valid_emails[0] if valid_emails else ''
        
        # Telefones
        phones = [
            data.get('original_telefone'),
            data.get('original_telefone_place'),
            data.get('gdr_website_phones'),  # Do website scraper
            data.get('gdr_google_search_phone'),  # Do Google search
            data.get('gdr_facebook_phone'),  # Do Facebook
            data.get('gdr_instagram_contact_phone_number'),  # Do Instagram
            data.get('gdr_instagram_business_phone_number')  # Do Instagram
        ]
        
        # Processar lista de telefones
        all_phones = []
        for phone_source in phones:
            if phone_source:
                if isinstance(phone_source, list):
                    all_phones.extend(phone_source)
                elif isinstance(phone_source, str):
                    all_phones.append(phone_source)
        
        # Filtrar telefones válidos
        valid_phones = [p for p in all_phones if p and len(str(p).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')) >= 8]
        result['gdr_consolidated_phone'] = valid_phones[0] if valid_phones else ''
        
        # Websites/URLs
        urls = [
            data.get('original_website'),
            data.get('original_place_website'),
            data.get('gdr_website_url'),  # Do website scraper
            data.get('gdr_google_search_website'),  # Do Google search
            data.get('gdr_facebook_website'),  # Do Facebook
            data.get('gdr_instagram_external_url')  # Do Instagram
        ]
        valid_urls = [u for u in urls if u and ('http' in str(u) or 'www.' in str(u))]
        result['gdr_consolidated_website'] = valid_urls[0] if valid_urls else ''
        
        # WhatsApp
        whatsapps = [
            data.get('gdr_facebook_whatsapp'),
            data.get('gdr_website_whatsapp'),
            data.get('gdr_google_search_whatsapp'),
            data.get('gdr_instagram_whatsapp_number')
        ]
        valid_whatsapps = [w for w in whatsapps if w and ('+' in str(w) or len(str(w).replace(' ', '')) >= 10)]
        result['gdr_consolidated_whatsapp'] = valid_whatsapps[0] if valid_whatsapps else ''
        
        # Se não tem WhatsApp mas tem telefone, converter
        if not result['gdr_consolidated_whatsapp'] and result['gdr_consolidated_phone']:
            phone = result['gdr_consolidated_phone']
            numbers = ''.join(filter(str.isdigit, str(phone)))
            if len(numbers) >= 10:
                if not numbers.startswith('55'):
                    result['gdr_consolidated_whatsapp'] = f"+55{numbers}"
                else:
                    result['gdr_consolidated_whatsapp'] = f"+{numbers}"
        
        # Estatísticas de enriquecimento
        original_fields = [k for k in data.keys() if k.startswith('original_')]
        enriched_fields = [k for k in data.keys() if k.startswith('gdr_') and not k.startswith('gdr_consolidated')]
        
        campos_originais = sum(1 for k in original_fields if data.get(k))
        campos_enriquecidos = sum(1 for k in enriched_fields if data.get(k))
        
        result['gdr_consolidated_original_count'] = campos_originais
        result['gdr_consolidated_enriched_count'] = campos_enriquecidos
        result['gdr_consolidated_enrichment_rate'] = (
            campos_enriquecidos / max(1, campos_originais)
        )
        
        return result
    
    def _prepare_enriched_context(self, data: Dict) -> Dict:
        """Prepara contexto enriquecido para análise LLM"""
        return {
            'name': data.get('original_nome', ''),
            'city': data.get('city', ''),
            'state': data.get('state', ''),
            'address': data.get('original_endereco_completo', ''),
            'website': data.get('gdr_consenso_url', ''),
            'email': data.get('gdr_consenso_email', ''),
            'phone': data.get('gdr_consenso_telefone', ''),
            'whatsapp': data.get('gdr_consenso_whatsapp', ''),
            'instagram_followers': data.get('gdr_instagram_followers', 0),
            'instagram_bio': data.get('gdr_instagram_bio', ''),
            'instagram_verified': data.get('gdr_instagram_is_verified', False),
            'facebook_category': data.get('gdr_facebook_category', ''),
            'facebook_bio': data.get('gdr_facebook_bio', ''),
            'google_rating': data.get('original_avaliacao_google', ''),
            'google_reviews_count': data.get('original_place_users', 0),
            'linktree_detected': data.get('gdr_linktree_detected', False),
            'linktree_url': data.get('gdr_linktree_url', ''),
            'enrichment_rate': data.get('gdr_consenso_taxa_enriquecimento', 0)
        }
    
    def _track_llm_usage(self, llm_results: Dict):
        """Rastreia uso de LLMs para estatísticas"""
        for field_name, result in llm_results.items():
            if 'gdr_llm_' in field_name and result:
                # Extrair provider do nome do campo
                parts = field_name.split('_')
                if len(parts) >= 3:
                    provider = parts[2]  # openai, claude, etc
                    
                    if provider not in self.processing_stats['llm_performance']:
                        self.processing_stats['llm_performance'][provider] = {
                            'successful': 0,
                            'failed': 0,
                            'total_responses': 0
                        }
                    
                    self.processing_stats['llm_performance'][provider]['total_responses'] += 1
                    if result and result != 'Análise em processamento':
                        self.processing_stats['llm_performance'][provider]['successful'] += 1
                    else:
                        self.processing_stats['llm_performance'][provider]['failed'] += 1
    
    def _save_checkpoint(self, results: List[Dict], batch_num: int):
        """Salva checkpoint do processamento"""
        checkpoint_file = self.checkpoint_dir / f"checkpoint_batch_{batch_num}.json"
        
        checkpoint_data = {
            'batch_number': batch_num,
            'total_processed': len(results),
            'timestamp': datetime.now().isoformat(),
            'results': results[-10:] if len(results) > 10 else results,  # Últimos 10 para economizar espaço
            'stats': self.processing_stats
        }
        
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Checkpoint salvo: {checkpoint_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar checkpoint: {e}")
    
    def _create_error_result(self, lead_data: Dict, error_message: str) -> Dict:
        """Cria resultado de erro para um lead que falhou"""
        result = self._preserve_original_data(lead_data)
        result.update({
            'processing_status': 'error',
            'error_message': error_message,
            'processing_timestamp': datetime.now().isoformat(),
            'framework_version': 'v3.1-enterprise',
            'gdr_quality_overall_score': 0,
            'gdr_consenso_email': '',
            'gdr_consenso_telefone': '',
            'gdr_consenso_whatsapp': '',
            'gdr_consenso_url': ''
        })
        return result
    
    def _order_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ordena colunas do DataFrame conforme schema"""
        ordered_columns = []
        
        # 1. Campos originais
        original_fields = [
            'original_id', 'original_nome', 'original_endereco_completo',
            'original_telefone', 'original_telefone_place', 'original_website',
            'original_avaliacao_google', 'original_latitude', 'original_longitude',
            'original_place_users', 'original_place_website', 'original_email',
            'original_instagram_url', 'original_facebook_url', 'city', 'state', 'country'
        ]
        ordered_columns.extend([col for col in original_fields if col in df.columns])
        
        # 2. Scrapers (Instagram, Facebook, Website, etc.)
        scraper_prefixes = ['gdr_instagram_', 'gdr_facebook_', 'gdr_linktree_', 'gdr_cwral4ai_', 'gdr_google_search_']
        for prefix in scraper_prefixes:
            scraper_cols = [col for col in df.columns if col.startswith(prefix)]
            scraper_cols.sort()
            ordered_columns.extend(scraper_cols)
        
        # 3. Consenso
        consenso_cols = [col for col in df.columns if col.startswith('gdr_consenso_')]
        consenso_cols.sort()
        ordered_columns.extend(consenso_cols)
        
        # 4. LLM analyses
        llm_cols = [col for col in df.columns if col.startswith('gdr_llm_')]
        llm_cols.sort()
        ordered_columns.extend(llm_cols)
        
        # 5. Quality metrics
        quality_cols = [col for col in df.columns if col.startswith('gdr_quality_')]
        quality_cols.sort()
        ordered_columns.extend(quality_cols)
        
        # 6. Metadados
        meta_fields = [
            'processing_time_seconds', 'processing_timestamp', 'processing_status',
            'framework_version', 'scrapers_used', 'scrapers_successful', 'scrapers_failed', 'scrapers_retried'
        ]
        ordered_columns.extend([col for col in meta_fields if col in df.columns])
        
        # 7. Campos restantes
        remaining_cols = [col for col in df.columns if col not in ordered_columns]
        ordered_columns.extend(remaining_cols)
        
        return df[ordered_columns]
    
    def _generate_final_report(self, results_df: pd.DataFrame, cost_estimates: Dict, batch_quality: Dict):
        """Gera relatório final completo"""
        print("\n" + "="*100)
        print(" RELATÓRIO FINAL - GDR FRAMEWORK V3.1 ENTERPRISE ".center(100))
        print("="*100)
        
        # Resumo geral
        total_leads = len(results_df)
        successful = (results_df['processing_status'] == 'completed').sum()
        failed = total_leads - successful
        
        print(f"\n[STATS] RESUMO GERAL:")
        print(f"  • Total de leads processados: {total_leads:,}")
        print(f"  • Sucessos: {successful:,} ({(successful/total_leads)*100:.1f}%)")
        print(f"  • Falhas: {failed:,} ({(failed/total_leads)*100:.1f}%)")
        print(f"  • Tempo total: {self.processing_stats['total_time']/60:.1f} minutos")
        print(f"  • Tempo médio por lead: {self.processing_stats['average_time_per_lead']:.1f}s")
        
        # Performance de scrapers
        print(f"\n🔧 PERFORMANCE DOS SCRAPERS:")
        scraper_stats = {}
        for col in results_df.columns:
            if col.startswith('gdr_instagram_') and col.endswith('_id'):
                scraper_stats['Instagram'] = (results_df[col] != '').sum()
            elif col.startswith('gdr_facebook_') and col.endswith('_url'):
                scraper_stats['Facebook'] = (results_df[col] != '').sum()
            elif col.startswith('gdr_cwral4ai_') and col.endswith('_email'):
                scraper_stats['Website'] = (results_df[col] != '').sum()
        
        for scraper, success_count in scraper_stats.items():
            rate = (success_count / total_leads) * 100
            status = "✓" if rate >= 50 else "⚠" if rate >= 25 else "✗"
            print(f"  {status} {scraper}: {success_count}/{total_leads} ({rate:.1f}%)")
        
        # Performance de LLMs
        print(f"\n🤖 PERFORMANCE DOS LLMs:")
        for llm, stats in self.processing_stats.get('llm_performance', {}).items():
            total = stats['total_responses']
            success = stats['successful']
            rate = (success / total) * 100 if total > 0 else 0
            status = "✓" if rate >= 90 else "⚠" if rate >= 70 else "✗"
            print(f"  {status} {llm.upper()}: {success}/{total} ({rate:.1f}%)")
        
        # Qualidade dos dados
        print(f"\n📈 QUALIDADE DOS DADOS:")
        avg_quality = batch_quality.get('average_score', 0)
        distribution = batch_quality.get('distribution', {})
        print(f"  • Score médio de qualidade: {avg_quality:.1f}/100")
        print(f"  • Excelente (≥90): {distribution.get('excellent', 0)} leads")
        print(f"  • Boa (75-89): {distribution.get('good', 0)} leads")
        print(f"  • Regular (60-74): {distribution.get('fair', 0)} leads")
        print(f"  • Ruim (40-59): {distribution.get('poor', 0)} leads")
        print(f"  • Crítica (<40): {distribution.get('critical', 0)} leads")
        
        # Consolidação de contatos
        print(f"\n📞 CONSOLIDAÇÃO DE CONTATOS:")
        if 'gdr_consenso_email' in results_df.columns:
            emails = (results_df['gdr_consenso_email'] != '').sum()
            phones = (results_df['gdr_consenso_telefone'] != '').sum()
            whatsapps = (results_df['gdr_consenso_whatsapp'] != '').sum()
            websites = (results_df['gdr_consenso_url'] != '').sum()
            
            print(f"  • Emails encontrados: {emails}/{total_leads} ({(emails/total_leads)*100:.1f}%)")
            print(f"  • Telefones encontrados: {phones}/{total_leads} ({(phones/total_leads)*100:.1f}%)")
            print(f"  • WhatsApps encontrados: {whatsapps}/{total_leads} ({(whatsapps/total_leads)*100:.1f}%)")
            print(f"  • Websites encontrados: {websites}/{total_leads} ({(websites/total_leads)*100:.1f}%)")
        
        # Custos reais vs estimados
        print(f"\n[$$] ANALISE DE CUSTOS:")
        print(f"  • Custo estimado: {self.token_estimator.format_cost(cost_estimates['total_cost'])}")
        print(f"  • Custo por lead: {self.token_estimator.format_cost(cost_estimates['cost_per_lead'])}")
        
        # Issues mais comuns
        common_issues = batch_quality.get('common_issues', [])[:5]
        if common_issues:
            print(f"\n[!] ISSUES MAIS COMUNS:")
            for i, (issue, count) in enumerate(common_issues, 1):
                print(f"  {i}. {issue} ({count} leads)")
        
        # Sugestões de melhoria
        top_suggestions = batch_quality.get('top_suggestions', [])[:3]
        if top_suggestions:
            print(f"\n💡 PRINCIPAIS SUGESTÕES:")
            for i, (suggestion, count) in enumerate(top_suggestions, 1):
                print(f"  {i}. {suggestion}")
        
        print("\n" + "="*100)
        print(" PROCESSAMENTO CONCLUÍDO COM SUCESSO ".center(100))
        print("="*100)


async def main():
    """Função principal com argumentos de linha de comando"""
    parser = argparse.ArgumentParser(description='GDR Framework V3.1 Enterprise')
    parser.add_argument('--input', type=str, default='data/input/leads.xlsx',
                       help='Arquivo de entrada com leads')
    parser.add_argument('--output', type=str, help='Arquivo de saída (opcional)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Tamanho do batch (padrão: 10)')
    parser.add_argument('--max-leads', type=int, default=75,
                       help='Máximo de leads para processar (padrão: 75)')
    parser.add_argument('--estimate-only', action='store_true',
                       help='Apenas estimar custos sem processar')
    
    args = parser.parse_args()
    
    # Verificar arquivo de entrada
    input_file = args.input
    if not Path(input_file).exists():
        input_file = Path(__file__).parent / args.input
        if not input_file.exists():
            logger.error(f"Arquivo não encontrado: {args.input}")
            return
    
    # Configurar arquivo de saída
    output_file = args.output
    if not output_file and not args.estimate_only:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"outputs/gdr_v31_enterprise_{timestamp}.xlsx"
    
    print("\n" + "="*100)
    print(" GDR FRAMEWORK V3.1 ENTERPRISE ".center(100))
    print(" SISTEMA COMPLETO DE ENRIQUECIMENTO DE LEADS ".center(100))
    print("="*100)
    print(f"\n[FILE] Arquivo de entrada: {input_file}")
    if not args.estimate_only:
        print(f"[FILE] Arquivo de saida: {output_file}")
    print(f"[BATCH] Batch size: {args.batch_size}")
    print(f"[MAX] Maximo de leads: {args.max_leads}")
    print(f"[MODE] Modo: {'Estimativa apenas' if args.estimate_only else 'Processamento completo'}")
    
    print(f"\n[>>] RECURSOS ATIVADOS:")
    print(f"  [OK] Multi-LLM (OpenAI, Claude, Gemini, DeepSeek, ZhipuAI)")
    print(f"  [OK] Estimativa de custos e tokens")
    print(f"  [OK] Retry automatico inteligente")
    print(f"  [OK] Deteccao melhorada de Linktree")
    print(f"  [OK] Facebook com 7 estrategias")
    print(f"  [OK] Revisao de qualidade automatica")
    print(f"  [OK] Processamento em lotes com checkpointing")
    print(f"  [OK] Relatorio completo de performance")
    print("="*100)
    
    try:
        # Inicializar framework
        framework = GDRFrameworkV31Enterprise()
        
        # Executar processamento
        await framework.process_batch(
            input_file=str(input_file),
            output_file=output_file,
            batch_size=args.batch_size,
            max_leads=args.max_leads,
            estimate_only=args.estimate_only
        )
        
        if not args.estimate_only:
            print(f"\n[OK] PROCESSAMENTO CONCLUIDO!")
            print(f"[FILE] Resultados salvos em: {output_file}")
            print(f"[LOG] Logs disponiveis em: gdr_v3_1_enterprise.log")
            print(f"💾 Checkpoints salvos em: gdr_checkpoints_v31/")
    
    except KeyboardInterrupt:
        logger.info("Processamento interrompido pelo usuário")
        print("\n[!] Processamento cancelado pelo usuario")
    
    except Exception as e:
        logger.error(f"Erro crítico: {e}")
        logger.error(traceback.format_exc())
        print(f"\n❌ Erro crítico: {e}")
    
    finally:
        # Fechar sessões
        try:
            if hasattr(framework, 'llm_analyzer'):
                await framework.llm_analyzer.close_session()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())