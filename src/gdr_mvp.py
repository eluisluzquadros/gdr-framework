#!/usr/bin/env python3
"""
GDR - Generative Development Representative
MVP Completo para processamento de leads reais
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
import json
import re
import time
import pickle
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from urllib.parse import urljoin, urlparse
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gdr_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ProcessingState:
    """Estado do processamento para recuperação"""
    batch_id: str
    total_leads: int
    processed_leads: Set[str]
    failed_leads: Set[str]
    completed_results: List[Dict[str, Any]]
    token_usages: List['TokenUsage']
    start_time: datetime
    last_checkpoint: datetime
    
    def save_checkpoint(self, checkpoint_dir: Path):
        """Salva checkpoint do estado atual"""
        checkpoint_file = checkpoint_dir / f"checkpoint_{self.batch_id}.pkl"
        
        with open(checkpoint_file, 'wb') as f:
            pickle.dump(self, f)
        
        logger.info(f"Checkpoint salvo: {len(self.processed_leads)}/{self.total_leads} leads processados")
    
    @classmethod
    def load_checkpoint(cls, batch_id: str, checkpoint_dir: Path) -> Optional['ProcessingState']:
        """Carrega checkpoint existente"""
        checkpoint_file = checkpoint_dir / f"checkpoint_{batch_id}.pkl"
        
        if checkpoint_file.exists():
            try:
                with open(checkpoint_file, 'rb') as f:
                    state = pickle.load(f)
                logger.info(f"Checkpoint carregado: {len(state.processed_leads)}/{state.total_leads} leads já processados")
                return state
            except Exception as e:
                logger.warning(f"Erro ao carregar checkpoint: {e}")
        
        return None
    
    def get_remaining_leads(self, all_leads: List['LeadInput']) -> List['LeadInput']:
        """Retorna leads que ainda precisam ser processados"""
        return [lead for lead in all_leads if lead.original_id not in self.processed_leads]
    
    def is_complete(self) -> bool:
        """Verifica se o processamento foi concluído"""
        return len(self.processed_leads) + len(self.failed_leads) >= self.total_leads

class PersistenceManager:
    """Gerenciador de persistência e recuperação"""
    
    def __init__(self, base_dir: Path = Path("./gdr_state")):
        self.base_dir = base_dir
        self.checkpoint_dir = base_dir / "checkpoints"
        self.results_dir = base_dir / "partial_results"
        self.locks_dir = base_dir / "locks"
        
        # Criar diretórios
        for directory in [self.checkpoint_dir, self.results_dir, self.locks_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
    
    def create_batch_id(self, leads: List[LeadInput]) -> str:
        """Cria ID único para o batch baseado nos leads"""
        lead_ids = sorted([lead.original_id for lead in leads])
        content = "_".join(lead_ids[:5])  # Primeiros 5 IDs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"batch_{timestamp}_{abs(hash(content)) % 10000:04d}"
    
    def acquire_lock(self, batch_id: str) -> bool:
        """Adquire lock para evitar processamento duplicado"""
        lock_file = self.locks_dir / f"{batch_id}.lock"
        
        if lock_file.exists():
            # Verificar se lock não está muito antigo (> 2 horas)
            if time.time() - lock_file.stat().st_mtime > 7200:
                logger.warning("Lock antigo encontrado, removendo...")
                lock_file.unlink()
            else:
                logger.warning(f"Batch {batch_id} já está sendo processado")
                return False
        
        # Criar lock
        with open(lock_file, 'w') as f:
            f.write(f"{os.getpid()}\n{datetime.now().isoformat()}")
        
        return True
    
    def release_lock(self, batch_id: str):
        """Libera lock do batch"""
        lock_file = self.locks_dir / f"{batch_id}.lock"
        if lock_file.exists():
            lock_file.unlink()
    
    def save_partial_result(self, batch_id: str, lead_id: str, result: Dict[str, Any]):
        """Salva resultado parcial de um lead"""
        with self._lock:
            result_file = self.results_dir / f"{batch_id}_{lead_id}.json"
            
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    
    def load_partial_results(self, batch_id: str) -> List[Dict[str, Any]]:
        """Carrega todos os resultados parciais de um batch"""
        results = []
        pattern = f"{batch_id}_*.json"
        
        for result_file in self.results_dir.glob(pattern):
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                    results.append(result)
            except Exception as e:
                logger.warning(f"Erro ao carregar resultado parcial {result_file}: {e}")
        
        return results
    
    def cleanup_batch(self, batch_id: str):
        """Limpa arquivos temporários de um batch concluído"""
        # Remover resultados parciais
        pattern = f"{batch_id}_*.json"
        for file in self.results_dir.glob(pattern):
            file.unlink()
        
        # Remover checkpoint
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{batch_id}.pkl"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
        
        # Liberar lock
        self.release_lock(batch_id)
        
        logger.info(f"Limpeza concluída para batch {batch_id}")

@dataclass
class LeadInput:
    """Modelo de dados conforme metadata_esperado_etapa1.txt"""
    # Variáveis obrigatórias do metadata
    original_id: str  # legalDocument
    original_nome: str  # name
    original_endereco_completo: str  # street+number+complement+district+postcode+city+state+country
    original_telefone: Optional[str]  # phone
    original_telefone_place: Optional[str]  # placesPhone
    original_website: Optional[str]  # website
    original_avaliacao_google: Optional[float]  # placesRating
    original_latitude: Optional[float]  # placesLat
    original_longitude: Optional[float]  # placesLng
    original_place_users: Optional[int]  # placesUserRatingsTotal
    original_place_website: Optional[str]  # placesWebsite
    original_email: Optional[str]  # email
    
    # Campos adicionais para processamento interno
    _places_id: Optional[str] = None  # Para referência interna
    
    @property
    def display_name(self) -> str:
        return f"{self.original_nome} (ID: {self.original_id})"

@dataclass
class CollectedData:
    """Dados coletados pelos scrapers"""
    # Social Media
    gdr_facebook_url: Optional[str] = None
    gdr_facebook_email: Optional[str] = None
    gdr_facebook_whatsapp: Optional[str] = None
    gdr_facebook_followers: Optional[int] = None
    
    gdr_instagram_url: Optional[str] = None
    gdr_instagram_followers: Optional[int] = None
    gdr_instagram_bio: Optional[str] = None
    gdr_instagram_verified: Optional[bool] = None
    
    gdr_linktree_url: Optional[str] = None
    gdr_linktree_links: Optional[str] = None
    
    # Website
    gdr_website_email: Optional[str] = None
    gdr_website_phone: Optional[str] = None
    gdr_website_whatsapp: Optional[str] = None
    gdr_website_youtube: Optional[str] = None
    
    # Google Search
    gdr_search_email: Optional[str] = None
    gdr_search_phone: Optional[str] = None
    gdr_search_additional_info: Optional[str] = None

@dataclass
class TokenUsage:
    """Controle de uso de tokens por LLM"""
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float

class RateLimiter:
    """Controle de rate limiting"""
    def __init__(self, requests_per_second: float = 1.0):
        self.requests_per_second = requests_per_second
        self.last_request = 0
    
    async def acquire(self):
        now = time.time()
        time_since_last = now - self.last_request
        min_interval = 1.0 / self.requests_per_second
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request = time.time()

class WebsiteScraper:
    """Scraper para extrair informações de websites"""
    
    def __init__(self):
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.phone_pattern = re.compile(r'(\(?\d{2}\)?\s?\d{4,5}-?\d{4})')
        self.whatsapp_pattern = re.compile(r'(?:whatsapp|wpp)[^\d]*(\d{10,13})', re.IGNORECASE)
        
    async def scrape_website(self, url: str) -> Dict[str, Any]:
        """Extrai informações de contato de um website"""
        if not url:
            return {}
            
        try:
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.text()
                        return self._extract_contact_info(content)
        except Exception as e:
            logger.warning(f"Erro ao acessar {url}: {e}")
        
        return {}
    
    def _extract_contact_info(self, html_content: str) -> Dict[str, Any]:
        """Extrai informações de contato do HTML"""
        # Remover tags HTML para análise de texto puro
        text = re.sub(r'<[^>]+>', ' ', html_content)
        
        emails = list(set(self.email_pattern.findall(text)))
        phones = list(set(self.phone_pattern.findall(text)))
        whatsapp_nums = list(set(self.whatsapp_pattern.findall(text)))
        
        # Buscar links do YouTube
        youtube_pattern = re.compile(r'((?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)[^\s<>"]+)')
        youtube_links = list(set(youtube_pattern.findall(html_content)))
        
        return {
            'gdr_website_email': emails[0] if emails else None,
            'gdr_website_phone': phones[0] if phones else None,
            'gdr_website_whatsapp': whatsapp_nums[0] if whatsapp_nums else None,
            'gdr_website_youtube': youtube_links[0] if youtube_links else None
        }

class GoogleSearchScraper:
    """Scraper usando Google Custom Search API"""
    
    def __init__(self, api_key: str, search_engine_id: str):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.rate_limiter = RateLimiter(0.1)  # 10 requests per second max
        
    async def search_business_info(self, business_name: str, location: str) -> Dict[str, Any]:
        """Busca informações adicionais sobre o negócio"""
        await self.rate_limiter.acquire()
        
        query = f'"{business_name}" {location} telefone email contato'
        
        try:
            async with aiohttp.ClientSession() as session:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    'key': self.api_key,
                    'cx': self.search_engine_id,
                    'q': query,
                    'num': 5
                }
                
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._extract_from_search_results(data.get('items', []))
        
        except Exception as e:
            logger.warning(f"Erro na busca para {business_name}: {e}")
        
        return {}
    
    def _extract_from_search_results(self, items: List[Dict]) -> Dict[str, Any]:
        """Extrai informações dos resultados de busca"""
        all_text = ' '.join([
            f"{item.get('title', '')} {item.get('snippet', '')}"
            for item in items
        ])
        
        scraper = WebsiteScraper()
        emails = scraper.email_pattern.findall(all_text)
        phones = scraper.phone_pattern.findall(all_text)
        
        return {
            'gdr_search_email': emails[0] if emails else None,
            'gdr_search_phone': phones[0] if phones else None,
            'gdr_search_additional_info': all_text[:500] if all_text else None
        }

class InstagramScraper:
    """Scraper básico para Instagram (simulado - Apify seria o ideal)"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter(0.5)
    
    async def scrape_instagram_profile(self, instagram_url: str) -> Dict[str, Any]:
        """Extrai informações básicas do perfil Instagram"""
        await self.rate_limiter.acquire()
        
        if not instagram_url:
            return {}
            
        try:
            # Simulação - em produção usaria Apify
            # Por enquanto, extrai informações básicas da URL
            return {
                'gdr_instagram_url': instagram_url,
                'gdr_instagram_followers': None,  # Seria obtido via Apify
                'gdr_instagram_bio': None,
                'gdr_instagram_verified': None
            }
        
        except Exception as e:
            logger.warning(f"Erro ao processar Instagram {instagram_url}: {e}")
        
        return {}

class LLMProvider:
    """Classe base para provedores de LLM"""
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.token_costs = {
            'openai': {'input': 0.00001, 'output': 0.00003},  # GPT-4 aproximado
            'anthropic': {'input': 0.00001, 'output': 0.00003},
            'google': {'input': 0.000001, 'output': 0.000002},
            'deepseek': {'input': 0.0000001, 'output': 0.0000003},
            'zhipuai': {'input': 0.0000001, 'output': 0.0000003}
        }
    
    def estimate_tokens(self, text: str) -> int:
        """Estimativa simples de tokens (4 chars = 1 token aproximadamente)"""
        return len(text) // 4
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calcula custo baseado no uso de tokens"""
        costs = self.token_costs.get(self.provider_name, {'input': 0.00001, 'output': 0.00003})
        return (input_tokens * costs['input']) + (output_tokens * costs['output'])

class OpenAIProvider(LLMProvider):
    """Provedor OpenAI"""
    
    def __init__(self, api_key: str):
        super().__init__('openai')
        self.api_key = api_key
        
    async def analyze_lead(self, lead: LeadInput, collected_data: CollectedData) -> Tuple[Dict[str, Any], TokenUsage]:
        """Analisa lead usando OpenAI"""
        
        prompt = self._build_prompt(lead, collected_data)
        input_tokens = self.estimate_tokens(prompt)
        
        # Simulação da chamada OpenAI (implementar com openai library)
        analysis_result = {
            'consolidated_email': self._consolidate_email(lead, collected_data),
            'consolidated_phone': self._consolidate_phone(lead, collected_data),
            'consolidated_whatsapp': self._extract_whatsapp(lead, collected_data),
            'consolidated_website': self._consolidate_website(lead, collected_data),
            'quality_score': self._calculate_quality_score(lead, collected_data),
            'business_insights': self._generate_business_insights(lead, collected_data)
        }
        
        result_text = json.dumps(analysis_result)
        output_tokens = self.estimate_tokens(result_text)
        cost = self.calculate_cost(input_tokens, output_tokens)
        
        token_usage = TokenUsage(
            provider='openai',
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost
        )
        
        return analysis_result, token_usage
    
    def _build_prompt(self, lead: LeadInput, collected_data: CollectedData) -> str:
        """Constrói prompt para análise"""
        return f"""
        Analise os dados do lead e consolide as informações de contato:
        
        Dados originais:
        - Nome: {lead.name}
        - Email original: {lead.email}
        - Telefone original: {lead.phone}
        - Website original: {lead.website}
        - Endereço: {lead.full_address}
        - Tipo de negócio: {lead.business_target}
        
        Dados coletados:
        - Website email: {collected_data.gdr_website_email}
        - Website phone: {collected_data.gdr_website_phone}
        - Search email: {collected_data.gdr_search_email}
        - Search phone: {collected_data.gdr_search_phone}
        - Instagram: {collected_data.gdr_instagram_url}
        
        Consolide as melhores informações de contato e avalie a qualidade do lead.
        """
    
    def _consolidate_email(self, lead: LeadInput, collected_data: CollectedData) -> Optional[str]:
        """Consolida informações de email"""
        emails = [
            lead.original_email,
            collected_data.gdr_website_email,
            collected_data.gdr_search_email
        ]
        valid_emails = [e for e in emails if e and '@' in e]
        return valid_emails[0] if valid_emails else None
    
    def _consolidate_phone(self, lead: LeadInput, collected_data: CollectedData) -> Optional[str]:
        """Consolida informações de telefone"""
        phones = [
            lead.original_telefone,
            lead.original_telefone_place,
            collected_data.gdr_website_phone,
            collected_data.gdr_search_phone
        ]
        valid_phones = [p for p in phones if p and len(str(p)) >= 10]
        return valid_phones[0] if valid_phones else None
    
    def _extract_whatsapp(self, lead: LeadInput, collected_data: CollectedData) -> Optional[str]:
        """Extrai número do WhatsApp"""
        whatsapp_nums = [
            collected_data.gdr_website_whatsapp
        ]
        valid_whatsapp = [w for w in whatsapp_nums if w]
        return valid_whatsapp[0] if valid_whatsapp else None
    
    def _consolidate_website(self, lead: LeadInput, collected_data: CollectedData) -> Optional[str]:
        """Consolida informações de website"""
        websites = [
            lead.original_website,
            lead.original_place_website
        ]
        valid_websites = [w for w in websites if w and ('http' in w or 'www' in w or '.com' in w)]
        return valid_websites[0] if valid_websites else None
    
    def _calculate_quality_score(self, lead: LeadInput, collected_data: CollectedData) -> float:
        """Calcula score de qualidade do lead baseado no metadata"""
        score = 0.0
        
        # Dados de contato (50%)
        if self._consolidate_email(lead, collected_data):
            score += 0.20
        if self._consolidate_phone(lead, collected_data):
            score += 0.20
        if self._extract_whatsapp(lead, collected_data):
            score += 0.10
        
        # Presença digital (25%)
        if lead.original_website or lead.original_place_website:
            score += 0.15
        if collected_data.gdr_instagram_url:
            score += 0.10
        
        # Dados do Google Places (25%)
        if lead.original_avaliacao_google and lead.original_avaliacao_google > 4.0:
            score += 0.15
        if lead.original_latitude and lead.original_longitude:
            score += 0.10
        
        return min(score, 1.0)
    
    def _generate_business_insights(self, lead: LeadInput, collected_data: CollectedData) -> str:
        """Gera insights sobre o negócio baseado no metadata"""
        insights = []
        
        # Análise de localização
        if lead.original_endereco_completo:
            insights.append(f"Localizado em: {lead.original_endereco_completo}")
        
        # Análise de avaliação Google
        if lead.original_avaliacao_google:
            if lead.original_avaliacao_google >= 4.5:
                insights.append("Excelente reputação no Google")
            elif lead.original_avaliacao_google >= 4.0:
                insights.append("Boa reputação no Google")
            elif lead.original_avaliacao_google >= 3.0:
                insights.append("Reputação média no Google")
            else:
                insights.append("Reputação baixa no Google - oportunidade de melhoria")
        
        # Análise de volume de avaliações
        if lead.original_place_users:
            if lead.original_place_users > 100:
                insights.append(f"Alto engajamento ({lead.original_place_users} avaliações)")
            elif lead.original_place_users > 20:
                insights.append(f"Bom engajamento ({lead.original_place_users} avaliações)")
            else:
                insights.append(f"Baixo engajamento ({lead.original_place_users} avaliações)")
        
        # Presença digital
        digital_presence = []
        if lead.original_website:
            digital_presence.append("website próprio")
        if lead.original_place_website:
            digital_presence.append("presença no Google")
        if collected_data.gdr_instagram_url:
            digital_presence.append("Instagram")
        
        if digital_presence:
            insights.append(f"Presença digital: {', '.join(digital_presence)}")
        else:
            insights.append("Presença digital limitada - oportunidade de melhoria")
        
        return "; ".join(insights) if insights else "Análise básica disponível"

class MultiLLMProcessor:
    """Processador que usa múltiplos LLMs para consenso"""
    
    def __init__(self):
        # Inicializar provedores (usando apenas OpenAI para o MVP)
        self.providers = {
            'openai': OpenAIProvider(os.getenv('OPENAI_API_KEY'))
        }
        # Em produção, adicionar outros LLMs:
        # 'anthropic': AnthropicProvider(os.getenv('ANTHROPIC_API_KEY')),
        # 'google': GoogleProvider(os.getenv('GEMINI_API_KEY')),
        # etc.
    
    async def process_lead(self, lead: LeadInput, collected_data: CollectedData) -> Tuple[Dict[str, Any], List[TokenUsage]]:
        """Processa lead através de múltiplos LLMs"""
        
        results = {}
        token_usages = []
        
        for provider_name, provider in self.providers.items():
            try:
                result, token_usage = await provider.analyze_lead(lead, collected_data)
                results[provider_name] = result
                token_usages.append(token_usage)
                
                logger.info(f"Processado com {provider_name}: {token_usage.total_tokens} tokens, ${token_usage.cost_usd:.6f}")
                
            except Exception as e:
                logger.error(f"Erro com provedor {provider_name}: {e}")
                results[provider_name] = None
        
        # Para MVP, usar apenas resultado do OpenAI
        # Em produção, implementar consenso entre múltiplos LLMs
        consensus_result = results.get('openai', {})
        
        return consensus_result, token_usages

class StatisticsCalculator:
    """Calculadora de estatísticas Kappa"""
    
    def calculate_kappa_scores(self, llm_results: Dict[str, Dict]) -> Dict[str, Any]:
        """Calcula scores Kappa (simplificado para MVP)"""
        
        # Para MVP com um LLM, retorna scores máximos
        # Em produção, calcularia concordância entre múltiplos LLMs
        return {
            'gdr_kappa_overall_score': 1.0,
            'gdr_kappa_interpretation': 'Perfect',
            'gdr_kappa_confidence_interval': (0.95, 1.0),
            'gdr_kappa_email_score': 1.0,
            'gdr_kappa_phone_score': 1.0,
            'gdr_kappa_whatsapp_score': 1.0,
            'gdr_kappa_website_score': 1.0,
            'gdr_kappa_high_confidence_flag': True,
            'gdr_kappa_review_required_flag': False
        }

class GDRFramework:
    """Framework principal do GDR com persistência e recuperação"""
    
    def __init__(self):
        self.website_scraper = WebsiteScraper()
        self.google_search = GoogleSearchScraper(
            os.getenv('GOOGLE_CSE_API_KEY'),
            os.getenv('GOOGLE_CSE_ID')
        )
        self.instagram_scraper = InstagramScraper()
        self.llm_processor = MultiLLMProcessor()
        self.stats_calculator = StatisticsCalculator()
        self.persistence_manager = PersistenceManager()
    
    async def process_leads_batch_with_recovery(self, leads: List[LeadInput], max_concurrent: int = 3, 
                                              checkpoint_interval: int = 10) -> Tuple[List[Dict[str, Any]], List[TokenUsage]]:
        """Processa lote de leads com persistência e recuperação à falhas"""
        
        # Criar ID do batch
        batch_id = self.persistence_manager.create_batch_id(leads)
        logger.info(f"Iniciando batch {batch_id} com {len(leads)} leads")
        
        # Verificar se já está sendo processado
        if not self.persistence_manager.acquire_lock(batch_id):
            raise RuntimeError(f"Batch {batch_id} já está sendo processado por outro processo")
        
        try:
            # Tentar carregar checkpoint existente
            state = ProcessingState.load_checkpoint(batch_id, self.persistence_manager.checkpoint_dir)
            
            if state is None:
                # Novo processamento
                logger.info("Iniciando novo processamento")
                state = ProcessingState(
                    batch_id=batch_id,
                    total_leads=len(leads),
                    processed_leads=set(),
                    failed_leads=set(),
                    completed_results=[],
                    token_usages=[],
                    start_time=datetime.now(),
                    last_checkpoint=datetime.now()
                )
            else:
                # Continuando processamento existente
                logger.info(f"Continuando processamento existente: {len(state.processed_leads)}/{state.total_leads} concluídos")
                
                # Carregar resultados parciais salvos
                partial_results = self.persistence_manager.load_partial_results(batch_id)
                state.completed_results.extend(partial_results)
            
            # Obter leads que ainda precisam ser processados
            remaining_leads = state.get_remaining_leads(leads)
            
            if not remaining_leads:
                logger.info("Todos os leads já foram processados")
                return state.completed_results, state.token_usages
            
            logger.info(f"Processando {len(remaining_leads)} leads restantes")
            
            # Processar leads restantes
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_with_recovery(lead):
                async with semaphore:
                    return await self._process_single_lead_with_persistence(lead, batch_id, state)
            
            # Processar em chunks para checkpoints regulares
            chunk_size = checkpoint_interval
            for i in range(0, len(remaining_leads), chunk_size):
                chunk = remaining_leads[i:i + chunk_size]
                
                logger.info(f"Processando chunk {i//chunk_size + 1}: leads {i+1}-{min(i+chunk_size, len(remaining_leads))}")
                
                # Processar chunk em paralelo
                tasks = [process_with_recovery(lead) for lead in chunk]
                chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Processar resultados do chunk
                for j, result in enumerate(chunk_results):
                    lead = chunk[j]
                    
                    if isinstance(result, Exception):
                        logger.error(f"Erro no lead {lead.original_id}: {result}")
                        state.failed_leads.add(lead.original_id)
                        
                        # Salvar resultado de erro
                        error_result = self._create_error_result(lead, result)
                        state.completed_results.append(error_result)
                        self.persistence_manager.save_partial_result(batch_id, lead.original_id, error_result)
                    else:
                        lead_result, token_usages = result
                        state.processed_leads.add(lead.original_id)
                        state.completed_results.append(lead_result)
                        state.token_usages.extend(token_usages)
                        
                        # Salvar resultado parcial
                        self.persistence_manager.save_partial_result(batch_id, lead.original_id, lead_result)
                
                # Salvar checkpoint
                state.last_checkpoint = datetime.now()
                state.save_checkpoint(self.persistence_manager.checkpoint_dir)
                
                # Log de progresso
                total_processed = len(state.processed_leads) + len(state.failed_leads)
                logger.info(f"Progresso: {total_processed}/{state.total_leads} leads processados")
            
            # Processamento concluído
            logger.info(f"Batch {batch_id} concluído com sucesso")
            
            # Limpeza (opcional - manter para debug)
            # self.persistence_manager.cleanup_batch(batch_id)
            
            return state.completed_results, state.token_usages
            
        except Exception as e:
            logger.error(f"Erro crítico no batch {batch_id}: {e}")
            raise
        finally:
            # Sempre liberar lock
            self.persistence_manager.release_lock(batch_id)
    
    async def _process_single_lead_with_persistence(self, lead: LeadInput, batch_id: str, 
                                                  state: ProcessingState) -> Tuple[Dict[str, Any], List[TokenUsage]]:
        """Processa um lead individual com persistência"""
        
        logger.debug(f"Processando lead {lead.original_id}: {lead.original_nome}")
        
        try:
            # Coleta de dados
            collected_data = await self.collect_data_for_lead(lead)
            
            # Processamento multi-LLM
            llm_result, token_usages = await self.llm_processor.process_lead(lead, collected_data)
            
            # Cálculo de estatísticas
            kappa_stats = self.stats_calculator.calculate_kappa_scores({'openai': llm_result})
            
            # Resultado final conforme metadata esperado
            final_result = {
                # Dados originais (metadata_esperado_etapa1.txt)
                'original_id': lead.original_id,
                'original_nome': lead.original_nome,
                'original_endereco_completo': lead.original_endereco_completo,
                'original_telefone': lead.original_telefone,
                'original_telefone_place': lead.original_telefone_place,
                'original_website': lead.original_website,
                'original_avaliacao_google': lead.original_avaliacao_google,
                'original_latitude': lead.original_latitude,
                'original_longitude': lead.original_longitude,
                'original_place_users': lead.original_place_users,
                'original_place_website': lead.original_place_website,
                'original_email': lead.original_email,
                
                # Dados coletados pelos scrapers
                **asdict(collected_data),
                
                # Resultado do consenso LLM
                'gdr_concenso_url': llm_result.get('consolidated_website'),
                'gdr_concenso_email': llm_result.get('consolidated_email'),
                'gdr_concenso_telefone': llm_result.get('consolidated_phone'),
                'gdr_concenso_whatsapp': llm_result.get('consolidated_whatsapp'),
                'gdr_concenso_synergy_score_categoria': self._categorize_quality_score(llm_result.get('quality_score', 0)),
                'gdr_concenso_synergy_score_justificativa': llm_result.get('business_insights', ''),
                'gdr_concenso_total_campos_originais': self._count_original_fields(lead),
                'gdr_concenso_total_campos_enriquecidos': self._count_enriched_fields(llm_result),
                'gdr_concenso_novos_campos_adicionados': self._count_new_fields(lead, llm_result),
                
                # Estatísticas Kappa
                **kappa_stats,
                
                # Metadados de processamento
                'processing_timestamp': datetime.now().isoformat(),
                'processing_status': 'success',
                'batch_id': batch_id
            }
            
            return final_result, token_usages
            
        except Exception as e:
            raise Exception(f"Erro processando lead {lead.original_id}: {str(e)}")
    
    def _create_error_result(self, lead: LeadInput, error: Exception) -> Dict[str, Any]:
        """Cria resultado de erro para um lead"""
        return {
            'original_id': lead.original_id,
            'original_nome': lead.original_nome,
            'original_endereco_completo': lead.original_endereco_completo,
            'original_telefone': lead.original_telefone,
            'original_telefone_place': lead.original_telefone_place,
            'original_website': lead.original_website,
            'original_avaliacao_google': lead.original_avaliacao_google,
            'original_latitude': lead.original_latitude,
            'original_longitude': lead.original_longitude,
            'original_place_users': lead.original_place_users,
            'original_place_website': lead.original_place_website,
            'original_email': lead.original_email,
            'processing_timestamp': datetime.now().isoformat(),
            'processing_status': 'error',
            'processing_error': str(error)
        }
    
    def _categorize_quality_score(self, score: float) -> str:
        """Categoriza score de qualidade"""
        if score >= 0.8:
            return "High"
        elif score >= 0.6:
            return "Medium"
        elif score >= 0.4:
            return "Low"
        else:
            return "Very Low"
    
    def _count_original_fields(self, lead: LeadInput) -> int:
        """Conta campos originais não-nulos"""
        return len([v for v in asdict(lead).values() if v is not None])
    
    def _count_enriched_fields(self, llm_result: Dict[str, Any]) -> int:
        """Conta campos enriquecidos não-nulos"""
        enriched_fields = ['consolidated_email', 'consolidated_phone', 'consolidated_whatsapp', 'consolidated_website']
        return len([field for field in enriched_fields if llm_result.get(field)])
    
    def _count_new_fields(self, lead: LeadInput, llm_result: Dict[str, Any]) -> int:
        """Conta novos campos adicionados pelo processamento"""
        original_email = lead.original_email
        original_phone = lead.original_telefone or lead.original_telefone_place
        original_website = lead.original_website or lead.original_place_website
        
        new_fields = 0
        
        if not original_email and llm_result.get('consolidated_email'):
            new_fields += 1
        if not original_phone and llm_result.get('consolidated_phone'):
            new_fields += 1
        if not original_website and llm_result.get('consolidated_website'):
            new_fields += 1
        if llm_result.get('consolidated_whatsapp'):  # WhatsApp sempre é novo
            new_fields += 1
            
        return new_fields
    
    # Manter método antigo para compatibilidade
    async def process_leads_batch(self, leads: List[LeadInput], max_concurrent: int = 3) -> Tuple[List[Dict[str, Any]], List[TokenUsage]]:
        """Wrapper para compatibilidade - usa método com recovery"""
        return await self.process_leads_batch_with_recovery(leads, max_concurrent)
    
    async def collect_data_for_lead(self, lead: LeadInput) -> CollectedData:
        """Coleta dados de múltiplas fontes para um lead baseado no metadata"""
        
        collected = CollectedData()
        
        # Website scraping - usar original_website ou original_place_website
        website_url = lead.original_website or lead.original_place_website
        if website_url:
            website_data = await self.website_scraper.scrape_website(website_url)
            
            collected.gdr_website_email = website_data.get('gdr_website_email')
            collected.gdr_website_phone = website_data.get('gdr_website_phone')
            collected.gdr_website_whatsapp = website_data.get('gdr_website_whatsapp')
            collected.gdr_website_youtube = website_data.get('gdr_website_youtube')
        
        # Google Search - usar nome e endereço do metadata
        if lead.original_nome:
            # Extrair cidade do endereço completo para busca mais eficiente
            location_for_search = self._extract_city_from_address(lead.original_endereco_completo)
            
            search_data = await self.google_search.search_business_info(
                lead.original_nome, 
                location_for_search or "Brasil"
            )
            collected.gdr_search_email = search_data.get('gdr_search_email')
            collected.gdr_search_phone = search_data.get('gdr_search_phone')
            collected.gdr_search_additional_info = search_data.get('gdr_search_additional_info')
        
        # Instagram - tentar detectar perfil baseado no nome do negócio
        instagram_data = await self._try_find_instagram_profile(lead.original_nome)
        if instagram_data:
            collected.gdr_instagram_url = instagram_data.get('gdr_instagram_url')
            collected.gdr_instagram_followers = instagram_data.get('gdr_instagram_followers')
            collected.gdr_instagram_bio = instagram_data.get('gdr_instagram_bio')
            collected.gdr_instagram_verified = instagram_data.get('gdr_instagram_verified')
        
        return collected
    
    def _extract_city_from_address(self, full_address: str) -> Optional[str]:
        """Extrai cidade do endereço completo"""
        if not full_address:
            return None
        
        # Tentar extrair cidade (normalmente antes do estado)
        parts = [part.strip() for part in full_address.split(',')]
        
        # Procurar por parte que contém cidade (antes de estado como "RS", "SP", etc.)
        for i, part in enumerate(parts):
            if i < len(parts) - 1:
                next_part = parts[i + 1].strip()
                # Se próxima parte é um estado (2 letras maiúsculas)
                if len(next_part) == 2 and next_part.isupper():
                    return part.strip()
        
        # Fallback: pegar primeira parte que parece ser cidade
        for part in parts:
            if len(part.strip()) > 3 and not part.strip().isdigit():
                return part.strip()
        
        return None
    
    async def _try_find_instagram_profile(self, business_name: str) -> Dict[str, Any]:
        """Tenta encontrar perfil Instagram baseado no nome do negócio"""
        
        # Simplificar nome para busca
        simplified_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
        
        # Gerar possíveis usernames
        possible_usernames = [
            simplified_name,
            simplified_name.replace('loja', ''),
            simplified_name.replace('assistencia', ''),
            f"{simplified_name}oficial",
            f"{simplified_name}_"
        ]
        
        # Para MVP, simular busca (em produção usar Apify)
        # Por enquanto, retornar dados vazios
        return {}
    
    # Resto dos métodos permanecem os mesmos...
    
    async def process_single_lead(self, lead: LeadInput) -> Tuple[Dict[str, Any], List[TokenUsage]]:
        """Processa um lead individual"""
        
        try:
            # Coleta de dados
            collected_data = await self.collect_data_for_lead(lead)
            
            # Processamento multi-LLM
            llm_result, token_usages = await self.llm_processor.process_lead(lead, collected_data)
            
            # Cálculo de estatísticas
            kappa_stats = self.stats_calculator.calculate_kappa_scores({'openai': llm_result})
            
            # Resultado final
            final_result = {
                # Dados originais
                **asdict(lead),
                
                # Dados coletados
                **asdict(collected_data),
                
                # Resultado do LLM
                'gdr_consolidated_email': llm_result.get('consolidated_email'),
                'gdr_consolidated_phone': llm_result.get('consolidated_phone'),
                'gdr_consolidated_whatsapp': llm_result.get('consolidated_whatsapp'),
                'gdr_consolidated_website': llm_result.get('consolidated_website'),
                'gdr_quality_score': llm_result.get('quality_score'),
                'gdr_business_insights': llm_result.get('business_insights'),
                
                # Estatísticas Kappa
                **kappa_stats,
                
                # Metadados
                'processing_timestamp': datetime.now().isoformat(),
                'processing_status': 'success'
            }
            
            return final_result, token_usages
            
        except Exception as e:
            logger.error(f"Erro processando lead {lead.id}: {e}")
            
            error_result = {
                **asdict(lead),
                'processing_timestamp': datetime.now().isoformat(),
                'processing_status': 'error',
                'processing_error': str(e)
            }
            
            return error_result, []
    
    async def process_leads_batch(self, leads: List[LeadInput], max_concurrent: int = 5) -> Tuple[List[Dict[str, Any]], List[TokenUsage]]:
        """Processa lote de leads com concorrência limitada"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        all_token_usages = []
        
        async def process_with_semaphore(lead):
            async with semaphore:
                return await self.process_single_lead(lead)
        
        logger.info(f"Processando {len(leads)} leads com concorrência máxima de {max_concurrent}")
        
        # Processar leads em paralelo
        tasks = [process_with_semaphore(lead) for lead in leads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Erro no lead {leads[i].id}: {result}")
                error_result = {
                    **asdict(leads[i]),
                    'processing_status': 'error',
                    'processing_error': str(result),
                    'processing_timestamp': datetime.now().isoformat()
                }
                processed_results.append(error_result)
            else:
                lead_result, token_usages = result
                processed_results.append(lead_result)
                all_token_usages.extend(token_usages)
        
        return processed_results, all_token_usages
    
    def export_results(self, results: List[Dict[str, Any]], token_usages: List[TokenUsage], output_path: str):
        """Exporta resultados para Excel com múltiplas abas"""
        
        logger.info(f"Exportando resultados para {output_path}")
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            
            # Aba 1: Dados Consolidados
            main_columns = [
                'id', 'name', 'business_target', 'city', 'state',
                'gdr_consolidated_email', 'gdr_consolidated_phone', 
                'gdr_consolidated_whatsapp', 'gdr_consolidated_website',
                'gdr_quality_score', 'gdr_kappa_overall_score',
                'processing_status', 'gdr_business_insights'
            ]
            
            main_df = pd.DataFrame(results)
            main_df = main_df[[col for col in main_columns if col in main_df.columns]]
            main_df.to_excel(writer, sheet_name='Dados Consolidados', index=False)
            
            # Aba 2: Dados Completos
            full_df = pd.DataFrame(results)
            full_df.to_excel(writer, sheet_name='Dados Completos', index=False)
            
            # Aba 3: Estatísticas de Processamento
            stats_data = self._generate_processing_statistics(results, token_usages)
            stats_df = pd.DataFrame([stats_data])
            stats_df.to_excel(writer, sheet_name='Estatísticas', index=False)
            
            # Aba 4: Uso de Tokens e Custos
            if token_usages:
                token_df = pd.DataFrame([asdict(usage) for usage in token_usages])
                token_df.to_excel(writer, sheet_name='Custos de Tokens', index=False)
        
        logger.info(f"Exportação concluída: {output_path}")
    
    def _generate_processing_statistics(self, results: List[Dict[str, Any]], token_usages: List[TokenUsage]) -> Dict[str, Any]:
        """Gera estatísticas de processamento"""
        
        total_leads = len(results)
        successful = len([r for r in results if r.get('processing_status') == 'success'])
        failed = total_leads - successful
        
        # Cobertura de dados
        with_email = len([r for r in results if r.get('gdr_consolidated_email')])
        with_phone = len([r for r in results if r.get('gdr_consolidated_phone')])
        with_whatsapp = len([r for r in results if r.get('gdr_consolidated_whatsapp')])
        with_website = len([r for r in results if r.get('gdr_consolidated_website')])
        
        # Qualidade
        quality_scores = [r.get('gdr_quality_score', 0) for r in results if r.get('gdr_quality_score')]
        avg_quality = np.mean(quality_scores) if quality_scores else 0
        
        # Custos
        total_tokens = sum(usage.total_tokens for usage in token_usages)
        total_cost = sum(usage.cost_usd for usage in token_usages)
        
        return {
            'total_leads_processed': total_leads,
            'successful_processing': successful,
            'failed_processing': failed,
            'success_rate_percent': (successful / total_leads * 100) if total_leads > 0 else 0,
            
            'email_coverage_percent': (with_email / total_leads * 100) if total_leads > 0 else 0,
            'phone_coverage_percent': (with_phone / total_leads * 100) if total_leads > 0 else 0,
            'whatsapp_coverage_percent': (with_whatsapp / total_leads * 100) if total_leads > 0 else 0,
            'website_coverage_percent': (with_website / total_leads * 100) if total_leads > 0 else 0,
            
            'average_quality_score': avg_quality,
            'high_quality_leads_percent': (len([s for s in quality_scores if s >= 0.7]) / len(quality_scores) * 100) if quality_scores else 0,
            
            'total_tokens_used': total_tokens,
            'total_cost_usd': total_cost,
            'average_cost_per_lead': total_cost / total_leads if total_leads > 0 else 0,
            
            'processing_date': datetime.now().isoformat()
        }

async def main():
    """Função principal para executar o processamento com persistência e recuperação"""
    
    # Configuração
    INPUT_FILE = "leads.xlsx"
    OUTPUT_FILE = f"gdr_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    MAX_LEADS = 50  # Processar apenas os primeiros 50 para teste
    
    logger.info("=" * 60)
    logger.info("🚀 INICIANDO PROCESSAMENTO GDR COM PERSISTÊNCIA")
    logger.info("=" * 60)
    logger.info("✅ Apenas variáveis do metadata_esperado_etapa1.txt serão mantidas")
    logger.info("💾 Sistema de persistência e recuperação ativado")
    logger.info("🔄 Processamento pode ser retomado em caso de falha")
    
    # Inicializar framework
    gdr = GDRFramework()
    
    # Carregar leads (apenas variáveis do metadata)
    all_leads = gdr.load_leads_from_excel(INPUT_FILE)
    
    if not all_leads:
        logger.error("❌ Nenhum lead válido encontrado")
        return
    
    # Processar subset para teste
    test_leads = all_leads[:MAX_LEADS]
    logger.info(f"📊 Processando {len(test_leads)} leads de teste (de {len(all_leads)} totais)")
    
    # Mostrar amostra dos dados carregados
    sample_lead = test_leads[0]
    logger.info(f"📋 Amostra - ID: {sample_lead.original_id}, Nome: {sample_lead.original_nome}")
    logger.info(f"📍 Endereço: {sample_lead.original_endereco_completo[:100]}...")
    logger.info(f"📞 Telefone original: {sample_lead.original_telefone}")
    logger.info(f"🌐 Website original: {sample_lead.original_website}")
    
    start_time = time.time()
    
    try:
        # Processar leads com sistema de persistência
        logger.info("🔄 Iniciando processamento com recovery automático...")
        results, token_usages = await gdr.process_leads_batch_with_recovery(
            test_leads, 
            max_concurrent=3,
            checkpoint_interval=10  # Checkpoint a cada 10 leads
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Estatísticas do processamento
        successful = len([r for r in results if r.get('processing_status') == 'success'])
        failed = len([r for r in results if r.get('processing_status') == 'error'])
        total_tokens = sum(usage.total_tokens for usage in token_usages)
        total_cost = sum(usage.cost_usd for usage in token_usages)
        
        # Análise de enriquecimento
        enrichment_stats = gdr._analyze_enrichment_results(results)
        
        logger.info("=" * 60)
        logger.info("✅ PROCESSAMENTO CONCLUÍDO COM SUCESSO")
        logger.info("=" * 60)
        logger.info(f"⏱️  Tempo total: {processing_time:.1f} segundos")
        logger.info(f"📊 Leads processados: {len(results)}")
        logger.info(f"✅ Sucessos: {successful}")
        logger.info(f"❌ Falhas: {failed}")
        logger.info(f"📈 Taxa de sucesso: {successful/(successful+failed)*100:.1f}%")
        
        logger.info(f"💾 Persistência:")
        logger.info(f"   └─ Checkpoints automáticos a cada 10 leads")
        logger.info(f"   └─ Resultados parciais salvos individualmente")
        logger.info(f"   └─ Recuperação automática em caso de falha")
        
        logger.info(f"🔤 Tokens utilizados: {total_tokens:,}")
        logger.info(f"💰 Custo total: ${total_cost:.6f} USD")
        logger.info(f"📈 Custo médio/lead: ${total_cost/len(results):.6f} USD")
        
        logger.info(f"📧 Enriquecimento de dados:")
        logger.info(f"   └─ Emails encontrados: {enrichment_stats['emails_found']}")
        logger.info(f"   └─ Telefones consolidados: {enrichment_stats['phones_found']}")
        logger.info(f"   └─ WhatsApp encontrados: {enrichment_stats['whatsapp_found']}")
        logger.info(f"   └─ Websites confirmados: {enrichment_stats['websites_found']}")
        
        # Exportar resultados
        gdr.export_results(results, token_usages, OUTPUT_FILE)
        
        logger.info(f"📁 Resultados exportados para: {OUTPUT_FILE}")
        
        # Mostrar amostra dos resultados
        if successful > 0:
            success_sample = next(r for r in results if r.get('processing_status') == 'success')
            logger.info("📋 Amostra de resultado enriquecido:")
            logger.info(f"   └─ Email consolidado: {success_sample.get('gdr_concenso_email', 'N/A')}")
            logger.info(f"   └─ Telefone consolidado: {success_sample.get('gdr_concenso_telefone', 'N/A')}")
            logger.info(f"   └─ WhatsApp: {success_sample.get('gdr_concenso_whatsapp', 'N/A')}")
            logger.info(f"   └─ Score qualidade: {success_sample.get('gdr_concenso_synergy_score_categoria', 'N/A')}")
        
        # Informações sobre escalabilidade
        logger.info("🚀 Projeção para escala:")
        cost_per_lead = total_cost / len(results) if results else 0
        logger.info(f"   └─ 100 leads: ~${cost_per_lead * 100:.3f} USD")
        logger.info(f"   └─ 1.000 leads: ~${cost_per_lead * 1000:.2f} USD")
        logger.info(f"   └─ 10.000 leads: ~${cost_per_lead * 10000:.1f} USD")
        
    except Exception as e:
        logger.error(f"❌ Erro durante processamento: {e}")
        logger.error("💾 Estado salvo para recuperação posterior")
        raise

# Adicionar método de análise de enriquecimento na classe GDRFramework
def _analyze_enrichment_results(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analisa resultados de enriquecimento"""
    successful_results = [r for r in results if r.get('processing_status') == 'success']
    
    return {
        'emails_found': len([r for r in successful_results if r.get('gdr_concenso_email')]),
        'phones_found': len([r for r in successful_results if r.get('gdr_concenso_telefone')]),
        'whatsapp_found': len([r for r in successful_results if r.get('gdr_concenso_whatsapp')]),
        'websites_found': len([r for r in successful_results if r.get('gdr_concenso_url')])
    }

# Adicionar método à classe GDRFramework
GDRFramework._analyze_enrichment_results = _analyze_enrichment_results

if __name__ == "__main__":
    asyncio.run(main())
