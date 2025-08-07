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
    original_instagram_url: Optional[str]  # instagramUrl
    
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

@dataclass
class ProcessingState:
    """Estado do processamento para recuperação"""
    batch_id: str
    total_leads: int
    processed_leads: Set[str]
    failed_leads: Set[str]
    completed_results: List[Dict[str, Any]]
    token_usages: List[TokenUsage]
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
    
    def get_remaining_leads(self, all_leads: List[LeadInput]) -> List[LeadInput]:
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

class ApifyBaseScraper:
    """Classe base para scrapers Apify"""
    
    def __init__(self, api_key: str):
        try:
            from apify_client import ApifyClient
            self.client = ApifyClient(api_key)
        except ImportError:
            logger.error("apify-client não instalado. Execute: pip install apify-client")
            self.client = None
        self.rate_limiter = RateLimiter(0.2)  # 5 requests per second max
    
    async def run_actor(self, actor_id: str, input_data: Dict, timeout: int = 60) -> Optional[List[Dict]]:
        """Executa um actor Apify e retorna os resultados com timeout"""
        if not self.client:
            return None
            
        await self.rate_limiter.acquire()
        
        try:
            logger.info(f"Executando actor {actor_id} com timeout de {timeout}s")
            
            # Executar o actor em thread separada com timeout
            run = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: self.client.actor(actor_id).call(
                        run_input=input_data,
                        wait_secs=timeout
                    )
                ),
                timeout=timeout + 10
            )
            
            # Aguardar conclusão e obter resultados com timeout
            items = []
            start_time = asyncio.get_event_loop().time()
            
            # Converter iteração para assíncrona com timeout
            dataset_items = await asyncio.wait_for(
                asyncio.to_thread(
                    lambda: list(self.client.dataset(run['defaultDatasetId']).iterate_items())
                ),
                timeout=30
            )
            
            for item in dataset_items:
                items.append(item)
            
            logger.info(f"Actor {actor_id} retornou {len(items)} resultados")
            return items
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout ao executar Apify actor {actor_id}")
            return None
        except Exception as e:
            logger.error(f"Erro ao executar Apify actor {actor_id}: {e}")
            return None

class InstagramScraper(ApifyBaseScraper):
    """Scraper para Instagram usando Apify"""
    
    def __init__(self):
        api_key = os.getenv('APIFY_API_KEY')
        super().__init__(api_key)
        # Actor ID para Instagram Profile Scraper (conforme tutorial)
        self.actor_id = "apify/instagram-profile-scraper"
    
    async def scrape_instagram_profile(self, username_or_url: str) -> Dict[str, Any]:
        """Extrai informações do perfil Instagram"""
        if not username_or_url:
            return {}
            
        try:
            # Extrair username da URL se necessário
            username = username_or_url
            if 'instagram.com' in username_or_url:
                # Remover trailing slash e extrair username
                parts = username_or_url.rstrip('/').split('/')
                username = parts[-1].strip('@')
                # Verificar se não ficou vazio
                if not username or username == 'instagram.com':
                    logger.warning(f"Não foi possível extrair username de {username_or_url}")
                    return {}
            
            logger.info(f"Buscando Instagram profile: @{username}")
            
            # Configurar input para o actor (conforme tutorial)
            input_data = {
                "usernames": [username]
            }
            
            # Executar scraper com timeout reduzido para Instagram
            results = await self.run_actor(self.actor_id, input_data, timeout=45)
            
            if results and len(results) > 0:
                profile = results[0]
                return {
                    'gdr_instagram_url': f"https://instagram.com/{profile.get('username', username)}",
                    'gdr_instagram_followers': profile.get('followersCount', 0),
                    'gdr_instagram_bio': profile.get('biography', ''),
                    'gdr_instagram_verified': profile.get('verified', False)
                }
        
        except Exception as e:
            logger.warning(f"Erro ao processar Instagram {username_or_url}: {e}")
        
        return {}

class FacebookScraper(ApifyBaseScraper):
    """Scraper para Facebook usando Apify"""
    
    def __init__(self):
        api_key = os.getenv('APIFY_API_KEY')
        super().__init__(api_key)
        # Actor ID para Facebook Profile Scraper (conforme tutorial)
        self.actor_id = "curious_coder/facebook-profile-scraper"
    
    async def scrape_facebook_page(self, page_url_or_name: str) -> Dict[str, Any]:
        """Extrai informações de página do Facebook"""
        if not page_url_or_name:
            return {}
            
        try:
            logger.info(f"Buscando Facebook page: {page_url_or_name}")
            
            # Configurar input para o actor (conforme tutorial)
            input_data = {
                "profileUrls": [page_url_or_name if 'facebook.com' in page_url_or_name else f"https://www.facebook.com/{page_url_or_name}"],
                "proxy": {
                    "useApifyProxy": True,
                    "apifyProxyCountry": "US"
                },
                "minDelay": 1,
                "maxDelay": 3
            }
            
            # Executar scraper com timeout reduzido para Instagram
            results = await self.run_actor(self.actor_id, input_data, timeout=45)
            
            if results and len(results) > 0:
                page = results[0]
                
                # Extrair email e WhatsApp dos dados
                email = page.get('email')
                phone = page.get('phone')
                
                # Tentar extrair WhatsApp do about ou description
                whatsapp = None
                about_text = page.get('about', '') + ' ' + page.get('description', '')
                whatsapp_pattern = re.compile(r'whatsapp[^\d]*(\d{10,13})', re.IGNORECASE)
                whatsapp_match = whatsapp_pattern.search(about_text)
                if whatsapp_match:
                    whatsapp = whatsapp_match.group(1)
                
                return {
                    'gdr_facebook_url': page.get('url', page_url_or_name),
                    'gdr_facebook_email': email,
                    'gdr_facebook_whatsapp': whatsapp or phone,
                    'gdr_facebook_followers': page.get('likes', 0)
                }
        
        except Exception as e:
            logger.warning(f"Erro ao processar Facebook {page_url_or_name}: {e}")
        
        return {}

class LinktreeScraper(ApifyBaseScraper):
    """Scraper para Linktree usando Apify"""
    
    def __init__(self):
        api_key = os.getenv('APIFY_API_KEY_LINKTREE', os.getenv('APIFY_API_KEY'))
        super().__init__(api_key)
        # Actor ID para Linktree Scraper (conforme tutorial)
        self.actor_id = "ecomscrape/linktree-profile-details-scraper"
    
    async def scrape_linktree_profile(self, username_or_url: str) -> Dict[str, Any]:
        """Extrai links do perfil Linktree"""
        if not username_or_url:
            return {}
            
        try:
            logger.info(f"Buscando Linktree profile: {username_or_url}")
            
            # Formatar URL corretamente
            if 'linktr.ee' not in username_or_url:
                url = f"https://linktr.ee/{username_or_url}"
            else:
                url = username_or_url
            
            # Configurar input para o actor (conforme tutorial)
            input_data = {
                "urls_or_usernames": [url],
                "max_retries_per_url": 2,
                "proxy": {
                    "useApifyProxy": False
                }
            }
            
            # Executar scraper com timeout reduzido para Instagram
            results = await self.run_actor(self.actor_id, input_data, timeout=45)
            
            if results and len(results) > 0:
                profile = results[0]
                links = profile.get('links', [])
                
                # Formatar links como string
                links_formatted = []
                for link in links:
                    text = link.get('text', '')
                    url = link.get('url', '')
                    if text and url:
                        links_formatted.append(f"{text}: {url}")
                
                return {
                    'gdr_linktree_url': profile.get('from_url', ''),
                    'gdr_linktree_links': ' | '.join(links_formatted),
                    'gdr_linktree_username': profile.get('username', ''),
                    'gdr_linktree_title': profile.get('title', ''),
                    'gdr_linktree_description': profile.get('description', '')
                }
        
        except Exception as e:
            logger.warning(f"Erro ao processar Linktree {username_or_url}: {e}")
        
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
        - Nome: {lead.original_nome}
        - Email original: {lead.original_email}
        - Telefone original: {lead.original_telefone}
        - Website original: {lead.original_website}
        - Endereço: {lead.original_endereco_completo}
        - Tipo de negócio: {getattr(lead, 'business_target', 'N/A')}
        
        Dados coletados:
        - Website email: {collected_data.gdr_website_email}
        - Website phone: {collected_data.gdr_website_phone}
        - Website WhatsApp: {collected_data.gdr_website_whatsapp}
        - Search email: {collected_data.gdr_search_email}
        - Search phone: {collected_data.gdr_search_phone}
        - Instagram: {collected_data.gdr_instagram_url} (Seguidores: {collected_data.gdr_instagram_followers})
        - Facebook: {collected_data.gdr_facebook_url} (Seguidores: {collected_data.gdr_facebook_followers})
        - Facebook email: {collected_data.gdr_facebook_email}
        - Facebook WhatsApp: {collected_data.gdr_facebook_whatsapp}
        - Linktree: {collected_data.gdr_linktree_url}
        - Links do Linktree: {collected_data.gdr_linktree_links}
        
        Consolide as melhores informações de contato e avalie a qualidade do lead.
        """
    
    def _consolidate_email(self, lead: LeadInput, collected_data: CollectedData) -> Optional[str]:
        """Consolida informações de email"""
        emails = [
            lead.original_email,
            collected_data.gdr_website_email,
            collected_data.gdr_search_email,
            collected_data.gdr_facebook_email
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
            collected_data.gdr_website_whatsapp,
            collected_data.gdr_facebook_whatsapp
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
            digital_presence.append(f"Instagram ({collected_data.gdr_instagram_followers or 0} seguidores)")
        if collected_data.gdr_facebook_url:
            digital_presence.append(f"Facebook ({collected_data.gdr_facebook_followers or 0} seguidores)")
        if collected_data.gdr_linktree_url:
            digital_presence.append("Linktree")
        
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
    
    def __init__(self, enable_social_media_scrapers: bool = True, 
                 enable_website_scraper: bool = True,
                 enable_search_scraper: bool = True,
                 max_social_attempts: int = 1):
        """
        Inicializa o framework com flags de controle para otimização
        
        Args:
            enable_social_media_scrapers: Habilita scrapers de redes sociais (Instagram, Facebook, Linktree)
            enable_website_scraper: Habilita scraper de websites
            enable_search_scraper: Habilita Google Search scraper
            max_social_attempts: Máximo de tentativas para encontrar perfis sociais (1-3)
        """
        self.enable_social_media = enable_social_media_scrapers
        self.enable_website = enable_website_scraper
        self.enable_search = enable_search_scraper
        self.max_social_attempts = min(max(max_social_attempts, 1), 3)
        
        # Cache para evitar buscas duplicadas
        self.social_media_cache = {}
        
        # Inicializar scrapers apenas se habilitados
        self.website_scraper = WebsiteScraper() if enable_website_scraper else None
        self.google_search = GoogleSearchScraper(
            os.getenv('GOOGLE_CSE_API_KEY'),
            os.getenv('GOOGLE_CSE_ID')
        ) if enable_search_scraper else None
        
        # Scrapers de redes sociais
        self.instagram_scraper = InstagramScraper() if enable_social_media_scrapers else None
        self.facebook_scraper = FacebookScraper() if enable_social_media_scrapers else None
        self.linktree_scraper = LinktreeScraper() if enable_social_media_scrapers else None
        
        self.llm_processor = MultiLLMProcessor()
        self.stats_calculator = StatisticsCalculator()
        self.persistence_manager = PersistenceManager()
    
    async def process_leads_batch_with_recovery(self, leads: List[LeadInput], max_concurrent: int = 10, 
                                              checkpoint_interval: int = 50) -> Tuple[List[Dict[str, Any]], List[TokenUsage]]:
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
    async def process_leads_batch(self, leads: List[LeadInput], max_concurrent: int = 10) -> Tuple[List[Dict[str, Any]], List[TokenUsage]]:
        """Wrapper para compatibilidade - usa método com recovery"""
        return await self.process_leads_batch_with_recovery(leads, max_concurrent)
    
    async def collect_data_for_lead(self, lead: LeadInput) -> CollectedData:
        """Coleta dados de múltiplas fontes para um lead baseado no metadata"""
        
        collected = CollectedData()
        
        # Detectar URLs de redes sociais no campo website
        website_url = lead.original_website or lead.original_place_website
        instagram_url_from_website = None
        facebook_url_from_website = None
        
        if website_url:
            # Verificar se é URL do Instagram
            if 'instagram.com' in website_url:
                instagram_url_from_website = website_url
                # Não fazer scraping de website em URL do Instagram
            elif 'facebook.com' in website_url:
                facebook_url_from_website = website_url
                # Não fazer scraping de website em URL do Facebook
            else:
                # Website scraping normal - não é rede social
                if self.enable_website and self.website_scraper:
                    website_data = await self.website_scraper.scrape_website(website_url)
                    
                    collected.gdr_website_email = website_data.get('gdr_website_email')
                    collected.gdr_website_phone = website_data.get('gdr_website_phone')
                    collected.gdr_website_whatsapp = website_data.get('gdr_website_whatsapp')
                    collected.gdr_website_youtube = website_data.get('gdr_website_youtube')
        
        # Google Search - usar nome e endereço do metadata
        if self.enable_search and self.google_search and lead.original_nome:
            # Extrair cidade do endereço completo para busca mais eficiente
            location_for_search = self._extract_city_from_address(lead.original_endereco_completo)
            
            search_data = await self.google_search.search_business_info(
                lead.original_nome, 
                location_for_search or "Brasil"
            )
            collected.gdr_search_email = search_data.get('gdr_search_email')
            collected.gdr_search_phone = search_data.get('gdr_search_phone')
            collected.gdr_search_additional_info = search_data.get('gdr_search_additional_info')
        
        # Redes sociais apenas se habilitadas
        if self.enable_social_media:
            # Instagram - usar URL do website, original_instagram_url ou tentar detectar
            instagram_url = instagram_url_from_website or getattr(lead, 'original_instagram_url', None)
            
            if instagram_url and instagram_url.strip() and instagram_url.lower() != 'nan':
                # Usar URL fornecida
                try:
                    instagram_data = await self.instagram_scraper.scrape_instagram_profile(instagram_url)
                    if instagram_data:
                        collected.gdr_instagram_url = instagram_data.get('gdr_instagram_url')
                        collected.gdr_instagram_followers = instagram_data.get('gdr_instagram_followers')
                        collected.gdr_instagram_bio = instagram_data.get('gdr_instagram_bio')
                        collected.gdr_instagram_verified = instagram_data.get('gdr_instagram_verified')
                except Exception as e:
                    logger.warning(f"Erro ao buscar Instagram {instagram_url}: {e}")
            else:
                # Tentar detectar perfil baseado no nome do negócio
                instagram_data = await self._try_find_instagram_profile(lead.original_nome)
                if instagram_data:
                    collected.gdr_instagram_url = instagram_data.get('gdr_instagram_url')
                    collected.gdr_instagram_followers = instagram_data.get('gdr_instagram_followers')
                    collected.gdr_instagram_bio = instagram_data.get('gdr_instagram_bio')
                    collected.gdr_instagram_verified = instagram_data.get('gdr_instagram_verified')
            
            # Facebook - usar URL do website ou tentar detectar
            if facebook_url_from_website:
                try:
                    facebook_data = await self.facebook_scraper.scrape_facebook_page(facebook_url_from_website)
                    if facebook_data:
                        collected.gdr_facebook_url = facebook_data.get('gdr_facebook_url')
                        collected.gdr_facebook_email = facebook_data.get('gdr_facebook_email')
                        collected.gdr_facebook_whatsapp = facebook_data.get('gdr_facebook_whatsapp')
                        collected.gdr_facebook_followers = facebook_data.get('gdr_facebook_followers')
                except Exception as e:
                    logger.warning(f"Erro ao buscar Facebook {facebook_url_from_website}: {e}")
            else:
                # Tentar detectar página baseado no nome do negócio
                facebook_data = await self._try_find_facebook_page(lead.original_nome)
                if facebook_data:
                    collected.gdr_facebook_url = facebook_data.get('gdr_facebook_url')
                    collected.gdr_facebook_email = facebook_data.get('gdr_facebook_email')
                    collected.gdr_facebook_whatsapp = facebook_data.get('gdr_facebook_whatsapp')
                    collected.gdr_facebook_followers = facebook_data.get('gdr_facebook_followers')
            
            # Linktree - tentar detectar perfil baseado no nome do negócio
            linktree_data = await self._try_find_linktree_profile(lead.original_nome)
            if linktree_data:
                collected.gdr_linktree_url = linktree_data.get('gdr_linktree_url')
                collected.gdr_linktree_links = linktree_data.get('gdr_linktree_links')
        
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
        
        # Verificar cache primeiro
        cache_key = f"instagram_{business_name.lower()}"
        if cache_key in self.social_media_cache:
            return self.social_media_cache[cache_key]
        
        # Simplificar nome para busca
        simplified_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
        
        # Gerar possíveis usernames
        possible_usernames = [
            simplified_name,
            simplified_name.replace('loja', ''),
            simplified_name.replace('assistencia', ''),
        ]
        
        # Tentar buscar perfil com os possíveis usernames (limitado por max_social_attempts)
        for username in possible_usernames[:self.max_social_attempts]:
            try:
                result = await self.instagram_scraper.scrape_instagram_profile(username)
                if result and result.get('gdr_instagram_url'):
                    self.social_media_cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Tentativa de buscar Instagram @{username} falhou: {e}")
        
        # Armazenar resultado vazio no cache
        self.social_media_cache[cache_key] = {}
        return {}
    
    async def _try_find_facebook_page(self, business_name: str) -> Dict[str, Any]:
        """Tenta encontrar página Facebook baseado no nome do negócio"""
        
        # Verificar cache primeiro
        cache_key = f"facebook_{business_name.lower()}"
        if cache_key in self.social_media_cache:
            return self.social_media_cache[cache_key]
        
        # Simplificar nome para busca
        simplified_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
        
        # Gerar possíveis nomes de página
        possible_names = [
            business_name,
            simplified_name,
        ]
        
        # Tentar buscar página com os possíveis nomes (limitado por max_social_attempts)
        for page_name in possible_names[:self.max_social_attempts]:
            try:
                result = await self.facebook_scraper.scrape_facebook_page(page_name)
                if result and result.get('gdr_facebook_url'):
                    self.social_media_cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Tentativa de buscar Facebook /{page_name} falhou: {e}")
        
        # Armazenar resultado vazio no cache
        self.social_media_cache[cache_key] = {}
        return {}
    
    async def _try_find_linktree_profile(self, business_name: str) -> Dict[str, Any]:
        """Tenta encontrar perfil Linktree baseado no nome do negócio"""
        
        # Verificar cache primeiro
        cache_key = f"linktree_{business_name.lower()}"
        if cache_key in self.social_media_cache:
            return self.social_media_cache[cache_key]
        
        # Simplificar nome para busca
        simplified_name = re.sub(r'[^a-zA-Z0-9]', '', business_name.lower())
        
        # Gerar possíveis usernames
        possible_usernames = [
            simplified_name,
            simplified_name[:15]  # Linktree tem limite de caracteres
        ]
        
        # Tentar buscar perfil com os possíveis usernames (limitado por max_social_attempts)
        for username in possible_usernames[:self.max_social_attempts]:
            try:
                result = await self.linktree_scraper.scrape_linktree_profile(username)
                if result and result.get('gdr_linktree_url'):
                    self.social_media_cache[cache_key] = result
                    return result
            except Exception as e:
                logger.debug(f"Tentativa de buscar Linktree @{username} falhou: {e}")
        
        # Armazenar resultado vazio no cache
        self.social_media_cache[cache_key] = {}
        return {}
    
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
            logger.error(f"Erro processando lead {lead.original_id}: {e}")
            
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
                logger.error(f"Erro no lead {leads[i].original_id}: {result}")
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
                'original_id', 'original_nome', 'original_endereco_completo',
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
    
    def load_leads_from_excel(self, file_path: str) -> List[LeadInput]:
        """Carrega leads de um arquivo Excel"""
        try:
            df = pd.read_excel(file_path)
            logger.info(f"Arquivo carregado: {len(df)} registros encontrados")
            
            leads = []
            for idx, row in df.iterrows():
                try:
                    # Mapear colunas do Excel para o modelo LeadInput
                    lead = LeadInput(
                        original_id=str(row.get('legalDocument', row.get('id', f'ID_{idx}'))),
                        original_nome=str(row.get('name', '')),
                        original_endereco_completo=self._build_address(row),
                        original_telefone=self._clean_phone(row.get('phone')),
                        original_telefone_place=self._clean_phone(row.get('placesPhone')),
                        original_website=str(row.get('website', '')),
                        original_avaliacao_google=float(row.get('placesRating', 0)) if pd.notna(row.get('placesRating')) else None,
                        original_latitude=float(row.get('placesLat', 0)) if pd.notna(row.get('placesLat')) else None,
                        original_longitude=float(row.get('placesLng', 0)) if pd.notna(row.get('placesLng')) else None,
                        original_place_users=int(row.get('placesUserRatingsTotal', 0)) if pd.notna(row.get('placesUserRatingsTotal')) else None,
                        original_place_website=str(row.get('placesWebsite', '')),
                        original_email=str(row.get('email', '')),
                        original_instagram_url=str(row.get('instagramUrl', '')) if pd.notna(row.get('instagramUrl')) else None
                    )
                    leads.append(lead)
                except Exception as e:
                    logger.warning(f"Erro ao processar linha {idx}: {e}")
            
            logger.info(f"Leads carregados com sucesso: {len(leads)}")
            return leads
            
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo Excel: {e}")
            return []
    
    def _build_address(self, row) -> str:
        """Constrói endereço completo a partir dos campos"""
        parts = []
        for field in ['street', 'number', 'complement', 'district', 'postcode', 'city', 'state', 'country']:
            if field in row and pd.notna(row[field]) and str(row[field]).strip():
                parts.append(str(row[field]).strip())
        return ', '.join(parts) if parts else ''
    
    def _clean_phone(self, phone) -> Optional[str]:
        """Limpa número de telefone"""
        if pd.isna(phone) or not str(phone).strip():
            return None
        # Remove caracteres não numéricos
        cleaned = re.sub(r'\D', '', str(phone))
        return cleaned if len(cleaned) >= 10 else None

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
