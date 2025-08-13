#!/usr/bin/env python3
"""
Snowball Collection Manager
Gerencia coleta em múltiplos níveis com cache e detecção de loops
"""

import asyncio
import json
import hashlib
import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Tipos de fontes de dados"""
    GOOGLE_PLACES = "google_places"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKTREE = "linktree"
    WEBSITE = "website"
    GOOGLE_SEARCH = "google_search"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"


@dataclass
class ScrapeTask:
    """Representa uma tarefa de scraping"""
    url: str
    source: DataSource
    depth: int
    parent_url: Optional[str] = None
    priority: int = 0
    metadata: Dict = field(default_factory=dict)
    
    def __hash__(self):
        return hash(f"{self.url}_{self.source.value}")


class SnowballCollectionManager:
    """
    Gerencia coleta snowball com cache e anti-loop
    """
    
    def __init__(self, max_depth: int = 3, max_seeds_per_level: int = 10):
        """
        Inicializa o gerenciador
        
        Args:
            max_depth: Profundidade máxima de coleta
            max_seeds_per_level: Máximo de seeds por nível
        """
        self.max_depth = max_depth
        self.max_seeds_per_level = max_seeds_per_level
        
        # Cache de URLs/IDs visitados
        self.visited_urls: Set[str] = set()
        self.visited_ids: Set[str] = set()
        
        # Cache de resultados
        self.cache: Dict[str, Tuple[Dict, datetime]] = {}
        self.cache_ttl = timedelta(hours=24)
        
        # Detecção de ciclos
        self.scraping_chain: List[str] = []
        
        # Estatísticas
        self.stats = {
            'total_scraped': 0,
            'cache_hits': 0,
            'loops_detected': 0,
            'errors': 0,
            'by_level': {0: 0, 1: 0, 2: 0, 3: 0},
            'by_source': {source.value: 0 for source in DataSource}
        }
    
    def get_cache_key(self, url: str, source: DataSource) -> str:
        """
        Gera chave única para cache
        """
        return hashlib.md5(f"{url}_{source.value}".encode()).hexdigest()
    
    def is_cached(self, url: str, source: DataSource) -> bool:
        """
        Verifica se resultado está em cache válido
        """
        key = self.get_cache_key(url, source)
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.cache_ttl:
                self.stats['cache_hits'] += 1
                logger.debug(f"Cache hit para {url} ({source.value})")
                return True
        
        return False
    
    def get_cached(self, url: str, source: DataSource) -> Optional[Dict]:
        """
        Retorna dados do cache se disponível
        """
        key = self.get_cache_key(url, source)
        
        if self.is_cached(url, source):
            data, _ = self.cache[key]
            return data
        
        return None
    
    def add_to_cache(self, url: str, source: DataSource, data: Dict):
        """
        Adiciona resultado ao cache
        """
        key = self.get_cache_key(url, source)
        self.cache[key] = (data, datetime.now())
        logger.debug(f"Adicionado ao cache: {url} ({source.value})")
    
    def should_scrape(self, url: str, source: DataSource, depth: int) -> bool:
        """
        Determina se deve fazer scraping
        """
        # Verificar profundidade
        if depth > self.max_depth:
            logger.debug(f"Profundidade máxima atingida para {url}")
            return False
        
        # Verificar se já foi visitado
        url_id = f"{url}_{source.value}"
        if url_id in self.visited_urls:
            logger.debug(f"URL já visitada: {url}")
            return False
        
        # Verificar cache
        if self.is_cached(url, source):
            logger.debug(f"Usando cache para {url}")
            return False
        
        # Detectar ciclos
        if self.detect_cycle(url):
            logger.warning(f"Ciclo detectado para {url}")
            self.stats['loops_detected'] += 1
            return False
        
        return True
    
    def detect_cycle(self, url: str) -> bool:
        """
        Detecta ciclos na cadeia de scraping
        """
        # Normalizar URL
        normalized = self.normalize_url(url)
        
        # Verificar se está na cadeia atual
        return normalized in self.scraping_chain
    
    def normalize_url(self, url: str) -> str:
        """
        Normaliza URL para comparação
        """
        # Remover protocolo
        url = url.replace('https://', '').replace('http://', '')
        # Remover www
        url = url.replace('www.', '')
        # Remover trailing slash
        url = url.rstrip('/')
        # Lowercase
        return url.lower()
    
    def mark_visited(self, url: str, source: DataSource):
        """
        Marca URL como visitada
        """
        url_id = f"{url}_{source.value}"
        self.visited_urls.add(url_id)
        
        # Adicionar à cadeia para detecção de ciclos
        normalized = self.normalize_url(url)
        if normalized not in self.scraping_chain:
            self.scraping_chain.append(normalized)
    
    def extract_seeds(self, data: Dict, current_depth: int) -> List[ScrapeTask]:
        """
        Extrai seeds (URLs/usernames) dos dados coletados
        """
        seeds = []
        next_depth = current_depth + 1
        
        if next_depth > self.max_depth:
            return seeds
        
        # Extrair Instagram username
        if data.get('gdr_instagram_username'):
            username = data['gdr_instagram_username']
            seeds.append(ScrapeTask(
                url=f"@{username}",
                source=DataSource.INSTAGRAM,
                depth=next_depth,
                priority=8
            ))
        
        # Extrair Facebook URL
        if data.get('gdr_facebook_url'):
            seeds.append(ScrapeTask(
                url=data['gdr_facebook_url'],
                source=DataSource.FACEBOOK,
                depth=next_depth,
                priority=7
            ))
        
        # Extrair website
        if data.get('gdr_cwral4ai_url'):
            seeds.append(ScrapeTask(
                url=data['gdr_cwral4ai_url'],
                source=DataSource.WEBSITE,
                depth=next_depth,
                priority=9
            ))
        
        # Extrair Linktree
        if data.get('gdr_instagram_bio'):
            bio = data['gdr_instagram_bio']
            # Procurar linktree na bio
            import re
            linktree_match = re.search(r'linktr\.ee/(\w+)', bio, re.IGNORECASE)
            if linktree_match:
                username = linktree_match.group(1)
                seeds.append(ScrapeTask(
                    url=username,
                    source=DataSource.LINKTREE,
                    depth=next_depth,
                    priority=6
                ))
        
        # Extrair LinkedIn do Linktree
        if data.get('gdr_linkedin_url'):
            seeds.append(ScrapeTask(
                url=data['gdr_linkedin_url'],
                source=DataSource.LINKEDIN,
                depth=next_depth,
                priority=5
            ))
        
        # Extrair YouTube
        if data.get('gdr_cwral4ai_youtube_url'):
            seeds.append(ScrapeTask(
                url=data['gdr_cwral4ai_youtube_url'],
                source=DataSource.YOUTUBE,
                depth=next_depth,
                priority=4
            ))
        
        # Extrair URLs do Google Search
        if data.get('gdr_google_search_engine_url'):
            url = data['gdr_google_search_engine_url']
            # Determinar tipo de URL
            if 'instagram.com' in url:
                seeds.append(ScrapeTask(
                    url=url,
                    source=DataSource.INSTAGRAM,
                    depth=next_depth,
                    priority=8
                ))
            elif 'facebook.com' in url:
                seeds.append(ScrapeTask(
                    url=url,
                    source=DataSource.FACEBOOK,
                    depth=next_depth,
                    priority=7
                ))
            else:
                seeds.append(ScrapeTask(
                    url=url,
                    source=DataSource.WEBSITE,
                    depth=next_depth,
                    priority=6
                ))
        
        # Filtrar seeds duplicadas e já visitadas
        unique_seeds = []
        seen = set()
        
        for seed in seeds:
            seed_id = f"{seed.url}_{seed.source.value}"
            if seed_id not in seen and seed_id not in self.visited_urls:
                seen.add(seed_id)
                unique_seeds.append(seed)
        
        # Ordenar por prioridade e limitar quantidade
        unique_seeds.sort(key=lambda x: x.priority, reverse=True)
        
        return unique_seeds[:self.max_seeds_per_level]
    
    def prioritize_sources(self, lead_data: Dict) -> List[DataSource]:
        """
        Prioriza fontes baseado nos dados disponíveis
        """
        sources = []
        
        # Sempre começar com Google Places se não tiver ID
        if not lead_data.get('google_place_id'):
            sources.append(DataSource.GOOGLE_PLACES)
        
        # Priorizar baseado no que já temos
        if lead_data.get('instagram_url') or lead_data.get('instagramUrl'):
            sources.append(DataSource.INSTAGRAM)
        
        if lead_data.get('facebook_url') or lead_data.get('facebookUrl'):
            sources.append(DataSource.FACEBOOK)
        
        if lead_data.get('website') or lead_data.get('original_website'):
            sources.append(DataSource.WEBSITE)
        
        # Sempre incluir Google Search
        sources.append(DataSource.GOOGLE_SEARCH)
        
        # Adicionar Linktree se tivermos Instagram
        if DataSource.INSTAGRAM in sources:
            sources.append(DataSource.LINKTREE)
        
        return sources
    
    def get_statistics(self) -> Dict:
        """
        Retorna estatísticas da coleta
        """
        return {
            **self.stats,
            'cache_size': len(self.cache),
            'visited_urls': len(self.visited_urls),
            'chain_length': len(self.scraping_chain),
            'cache_hit_rate': (
                self.stats['cache_hits'] / self.stats['total_scraped'] * 100
                if self.stats['total_scraped'] > 0 else 0
            )
        }
    
    def reset_chain(self):
        """
        Reseta a cadeia de scraping (usar entre leads)
        """
        self.scraping_chain = []
    
    def cleanup_cache(self):
        """
        Remove entradas expiradas do cache
        """
        now = datetime.now()
        expired_keys = []
        
        for key, (_, timestamp) in self.cache.items():
            if now - timestamp > self.cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Removidas {len(expired_keys)} entradas expiradas do cache")


class SnowballOrchestrator:
    """
    Orquestra a coleta snowball usando o manager
    """
    
    def __init__(self, scrapers: Dict[DataSource, Any], max_depth: int = 3):
        """
        Inicializa o orquestrador
        
        Args:
            scrapers: Dicionário com instâncias dos scrapers
            max_depth: Profundidade máxima
        """
        self.scrapers = scrapers
        self.manager = SnowballCollectionManager(max_depth=max_depth)
    
    async def collect_snowball(self, lead_data: Dict) -> Dict:
        """
        Executa coleta snowball completa
        """
        result = lead_data.copy()
        
        # Resetar cadeia para novo lead
        self.manager.reset_chain()
        
        # Nível 0: Dados iniciais
        logger.info(f"Iniciando coleta snowball para {lead_data.get('name', 'Lead')}")
        
        # Determinar fontes prioritárias
        priority_sources = self.manager.prioritize_sources(lead_data)
        
        # Criar tarefas iniciais (Nível 1)
        level_1_tasks = []
        for source in priority_sources:
            task = ScrapeTask(
                url=self._get_url_for_source(lead_data, source),
                source=source,
                depth=1
            )
            if task.url and self.manager.should_scrape(task.url, task.source, task.depth):
                level_1_tasks.append(task)
        
        # Executar Nível 1
        level_1_results = await self._execute_level(level_1_tasks, result)
        
        # Extrair seeds do Nível 1
        all_seeds = []
        for data in level_1_results:
            result.update(data)
            seeds = self.manager.extract_seeds(data, 1)
            all_seeds.extend(seeds)
        
        # Executar Nível 2
        if all_seeds:
            level_2_results = await self._execute_level(all_seeds, result)
            
            # Extrair seeds do Nível 2
            level_3_seeds = []
            for data in level_2_results:
                result.update(data)
                seeds = self.manager.extract_seeds(data, 2)
                level_3_seeds.extend(seeds)
            
            # Executar Nível 3
            if level_3_seeds:
                level_3_results = await self._execute_level(level_3_seeds, result)
                for data in level_3_results:
                    result.update(data)
        
        # Adicionar estatísticas
        result['snowball_stats'] = self.manager.get_statistics()
        
        logger.info(f"Coleta snowball concluída: {self.manager.stats['total_scraped']} scrapers executados")
        
        return result
    
    async def _execute_level(self, tasks: List[ScrapeTask], current_result: Dict) -> List[Dict]:
        """
        Executa tarefas de um nível em paralelo
        """
        if not tasks:
            return []
        
        logger.info(f"Executando {len(tasks)} tarefas no nível {tasks[0].depth}")
        
        # Criar coroutines
        coroutines = []
        for task in tasks:
            # Verificar cache primeiro
            cached = self.manager.get_cached(task.url, task.source)
            if cached:
                coroutines.append(self._return_cached(cached))
            else:
                coroutines.append(self._execute_scraper(task, current_result))
        
        # Executar em paralelo
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # Filtrar erros
        valid_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Erro em scraper: {result}")
                self.manager.stats['errors'] += 1
            elif result:
                valid_results.append(result)
        
        return valid_results
    
    async def _return_cached(self, data: Dict) -> Dict:
        """
        Retorna dados do cache (async para compatibilidade)
        """
        return data
    
    async def _execute_scraper(self, task: ScrapeTask, current_data: Dict) -> Dict:
        """
        Executa um scraper específico
        """
        try:
            # Marcar como visitado
            self.manager.mark_visited(task.url, task.source)
            
            # Incrementar estatísticas
            self.manager.stats['total_scraped'] += 1
            self.manager.stats['by_level'][task.depth] += 1
            self.manager.stats['by_source'][task.source.value] += 1
            
            # Executar scraper apropriado
            scraper = self.scrapers.get(task.source)
            if not scraper:
                logger.warning(f"Scraper não disponível para {task.source.value}")
                return {}
            
            # Chamar método apropriado do scraper
            result = {}
            
            if task.source == DataSource.INSTAGRAM:
                result = await scraper.scrape_instagram_profile(task.url)
            elif task.source == DataSource.FACEBOOK:
                result = await scraper.scrape_facebook_alternative(
                    current_data.get('name', ''),
                    current_data.get('location', ''),
                    task.url
                )
            elif task.source == DataSource.LINKTREE:
                result = await scraper.scrape_linktree_profile(task.url)
            elif task.source == DataSource.WEBSITE:
                result = await scraper.scrape_website_smart(
                    task.url,
                    use_crawl4ai=True if task.depth == 1 else False
                )
            elif task.source == DataSource.GOOGLE_SEARCH:
                result = await scraper.search_company_info(
                    current_data.get('name', ''),
                    current_data.get('location', '')
                )
            
            # Adicionar ao cache
            if result:
                self.manager.add_to_cache(task.url, task.source, result)
            
            return result
        
        except Exception as e:
            logger.error(f"Erro ao executar scraper {task.source.value} para {task.url}: {e}")
            self.manager.stats['errors'] += 1
            return {}
    
    def _get_url_for_source(self, lead_data: Dict, source: DataSource) -> str:
        """
        Obtém URL apropriada para cada fonte
        """
        if source == DataSource.INSTAGRAM:
            return lead_data.get('instagram_url', lead_data.get('instagramUrl', ''))
        elif source == DataSource.FACEBOOK:
            return lead_data.get('facebook_url', lead_data.get('facebookUrl', ''))
        elif source == DataSource.WEBSITE:
            return lead_data.get('website', lead_data.get('original_website', ''))
        elif source == DataSource.GOOGLE_SEARCH:
            return lead_data.get('name', '')  # Usar nome como "URL" para busca
        elif source == DataSource.GOOGLE_PLACES:
            return lead_data.get('name', '')
        
        return ''