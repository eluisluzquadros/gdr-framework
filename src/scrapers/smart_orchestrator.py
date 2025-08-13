#!/usr/bin/env python3
"""
Smart Orchestrator - Sistema inteligente de orquestração de scrapers
Implementa retry automático, priorização e fallback strategies
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import random
import sys
import os

# Adicionar src ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from src.utils.safe_print import SafeLogger

# Usar SafeLogger para evitar erros de Unicode
logger = SafeLogger(logging.getLogger(__name__))


class ScraperPriority(Enum):
    """Prioridades dos scrapers"""
    CRITICAL = 1     # Google Places (dados fundamentais)
    HIGH = 2         # Instagram, Website
    MEDIUM = 3       # Facebook, Linktree
    LOW = 4          # Google Search, alternativas
    OPTIONAL = 5     # LinkedIn, YouTube


@dataclass
class ScraperTask:
    """Representa uma tarefa de scraping"""
    name: str
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    priority: ScraperPriority = ScraperPriority.MEDIUM
    max_retries: int = 3
    retry_count: int = 0
    timeout: float = 30.0
    required: bool = False
    dependencies: List[str] = field(default_factory=list)
    
    def __hash__(self):
        return hash(self.name)


class RetryStrategy:
    """Estratégias de retry"""
    
    @staticmethod
    def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        """Backoff exponencial com jitter"""
        delay = min(base_delay * (2 ** attempt), max_delay)
        # Adicionar jitter para evitar thundering herd
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter
    
    @staticmethod
    def linear_backoff(attempt: int, delay: float = 2.0) -> float:
        """Backoff linear"""
        return delay * (attempt + 1)
    
    @staticmethod
    def fibonacci_backoff(attempt: int, base_delay: float = 1.0) -> float:
        """Backoff usando sequência de Fibonacci"""
        if attempt <= 1:
            return base_delay
        
        fib = [1, 1]
        for _ in range(attempt - 1):
            fib.append(fib[-1] + fib[-2])
        
        return base_delay * fib[attempt]


class SmartOrchestrator:
    """
    Orquestrador inteligente de scrapers com retry e priorização
    """
    
    def __init__(self, 
                 max_concurrent: int = 5,
                 global_timeout: float = 300.0,
                 retry_strategy: str = 'exponential'):
        """
        Inicializa o orquestrador
        
        Args:
            max_concurrent: Máximo de scrapers concorrentes
            global_timeout: Timeout global para todo o processamento
            retry_strategy: Estratégia de retry ('exponential', 'linear', 'fibonacci')
        """
        self.max_concurrent = max_concurrent
        self.global_timeout = global_timeout
        self.retry_strategy_name = retry_strategy
        
        # Estatísticas
        self.stats = {
            'total_tasks': 0,
            'successful': 0,
            'failed': 0,
            'retried': 0,
            'timed_out': 0,
            'skipped': 0,
            'by_scraper': {},
            'total_time': 0,
            'retry_details': []
        }
        
        # Resultados
        self.results = {}
        self.errors = {}
        
        # Estratégia de retry
        self.retry_strategies = {
            'exponential': RetryStrategy.exponential_backoff,
            'linear': RetryStrategy.linear_backoff,
            'fibonacci': RetryStrategy.fibonacci_backoff
        }
        self.get_retry_delay = self.retry_strategies.get(
            retry_strategy, 
            RetryStrategy.exponential_backoff
        )
    
    async def execute_tasks(self, tasks: List[ScraperTask]) -> Dict[str, Any]:
        """
        Executa tarefas com priorização e retry automático
        
        Args:
            tasks: Lista de tarefas para executar
            
        Returns:
            Dict com resultados consolidados
        """
        start_time = time.time()
        
        # Ordenar por prioridade
        sorted_tasks = sorted(tasks, key=lambda t: (t.priority.value, -t.max_retries))
        self.stats['total_tasks'] = len(sorted_tasks)
        
        # Separar por dependências
        independent_tasks = [t for t in sorted_tasks if not t.dependencies]
        dependent_tasks = [t for t in sorted_tasks if t.dependencies]
        
        # Executar tarefas independentes primeiro
        logger.info(f"Executando {len(independent_tasks)} tarefas independentes")
        await self._execute_batch(independent_tasks)
        
        # Executar tarefas dependentes
        if dependent_tasks:
            logger.info(f"Executando {len(dependent_tasks)} tarefas dependentes")
            await self._execute_dependent_tasks(dependent_tasks)
        
        # Retry automático para tarefas críticas que falharam
        await self._retry_critical_failures()
        
        # Calcular tempo total
        self.stats['total_time'] = time.time() - start_time
        
        # Log estatísticas
        self._log_statistics()
        
        return {
            'results': self.results,
            'errors': self.errors,
            'stats': self.stats
        }
    
    async def _execute_batch(self, tasks: List[ScraperTask]):
        """Executa um batch de tarefas em paralelo"""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def run_with_semaphore(task):
            async with semaphore:
                await self._execute_single_task(task)
        
        # Executar todas as tarefas
        await asyncio.gather(
            *[run_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
    
    async def _execute_single_task(self, task: ScraperTask) -> Optional[Any]:
        """
        Executa uma única tarefa com retry automático
        """
        scraper_name = task.name
        
        while task.retry_count <= task.max_retries:
            try:
                # Log tentativa
                attempt_msg = f" (tentativa {task.retry_count + 1}/{task.max_retries + 1})" if task.retry_count > 0 else ""
                logger.info(f"Executando {scraper_name}{attempt_msg}")
                
                # Executar com timeout
                result = await asyncio.wait_for(
                    task.function(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
                
                # Validar resultado
                if self._is_valid_result(result):
                    self.results[scraper_name] = result
                    self.stats['successful'] += 1
                    self._update_scraper_stats(scraper_name, 'success')
                    
                    logger.info(f"[OK] {scraper_name} completado com sucesso")
                    return result
                else:
                    raise ValueError(f"Resultado inválido de {scraper_name}")
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout em {scraper_name} após {task.timeout}s")
                self.errors[scraper_name] = f"Timeout após {task.timeout}s"
                self.stats['timed_out'] += 1
                self._update_scraper_stats(scraper_name, 'timeout')
                
            except Exception as e:
                logger.error(f"Erro em {scraper_name}: {e}")
                self.errors[scraper_name] = str(e)
                self._update_scraper_stats(scraper_name, 'error')
            
            # Decidir se deve fazer retry
            if task.retry_count < task.max_retries:
                delay = self.get_retry_delay(task.retry_count)
                logger.info(f"Retry de {scraper_name} em {delay:.1f}s")
                
                # Registrar retry
                self.stats['retried'] += 1
                self.stats['retry_details'].append({
                    'scraper': scraper_name,
                    'attempt': task.retry_count + 1,
                    'delay': delay,
                    'timestamp': datetime.now().isoformat()
                })
                
                await asyncio.sleep(delay)
                task.retry_count += 1
            else:
                # Máximo de retries atingido
                self.stats['failed'] += 1
                logger.error(f"[X] {scraper_name} falhou após {task.max_retries + 1} tentativas")
                break
        
        return None
    
    async def _execute_dependent_tasks(self, tasks: List[ScraperTask]):
        """Executa tarefas com dependências"""
        remaining = tasks.copy()
        max_iterations = len(tasks) * 2  # Evitar loop infinito
        iteration = 0
        
        while remaining and iteration < max_iterations:
            iteration += 1
            executable = []
            
            for task in remaining:
                # Verificar se todas as dependências foram satisfeitas
                if all(dep in self.results for dep in task.dependencies):
                    executable.append(task)
            
            if executable:
                # Executar tarefas cujas dependências foram satisfeitas
                await self._execute_batch(executable)
                
                # Remover tarefas executadas
                for task in executable:
                    remaining.remove(task)
            else:
                # Nenhuma tarefa pode ser executada
                if remaining:
                    logger.warning(f"{len(remaining)} tarefas não puderam ser executadas devido a dependências não satisfeitas")
                    for task in remaining:
                        self.stats['skipped'] += 1
                        self._update_scraper_stats(task.name, 'skipped')
                break
    
    async def _retry_critical_failures(self):
        """Retry automático para scrapers críticos que falharam"""
        critical_scrapers = ['google_places', 'instagram', 'website']
        
        for scraper in critical_scrapers:
            if scraper in self.errors and scraper not in self.results:
                logger.info(f"Retry final para scraper crítico: {scraper}")
                
                # Criar tarefa de retry com estratégia diferente
                retry_task = ScraperTask(
                    name=f"{scraper}_final_retry",
                    function=self._get_fallback_function(scraper),
                    priority=ScraperPriority.CRITICAL,
                    max_retries=1,
                    timeout=60.0
                )
                
                await self._execute_single_task(retry_task)
    
    def _is_valid_result(self, result: Any) -> bool:
        """Valida se o resultado é válido"""
        if result is None:
            return False
        
        if isinstance(result, dict):
            # Verificar se tem pelo menos alguns campos preenchidos
            non_empty = sum(1 for v in result.values() if v and v != '')
            return non_empty >= 1
        
        return True
    
    def _update_scraper_stats(self, scraper_name: str, status: str):
        """Atualiza estatísticas por scraper"""
        if scraper_name not in self.stats['by_scraper']:
            self.stats['by_scraper'][scraper_name] = {
                'success': 0,
                'error': 0,
                'timeout': 0,
                'skipped': 0
            }
        
        if status in self.stats['by_scraper'][scraper_name]:
            self.stats['by_scraper'][scraper_name][status] += 1
    
    def _get_fallback_function(self, scraper_name: str):
        """Retorna função de fallback para scraper"""
        # Implementar lógica de fallback específica
        async def fallback():
            logger.info(f"Executando fallback para {scraper_name}")
            return {}
        
        return fallback
    
    def _log_statistics(self):
        """Log estatísticas detalhadas"""
        logger.info("=" * 50)
        logger.info("ESTATÍSTICAS DE EXECUÇÃO:")
        logger.info(f"  Total de tarefas: {self.stats['total_tasks']}")
        logger.info(f"  Sucesso: {self.stats['successful']}")
        logger.info(f"  Falhas: {self.stats['failed']}")
        logger.info(f"  Retries: {self.stats['retried']}")
        logger.info(f"  Timeouts: {self.stats['timed_out']}")
        logger.info(f"  Ignoradas: {self.stats['skipped']}")
        logger.info(f"  Tempo total: {self.stats['total_time']:.2f}s")
        
        if self.stats['by_scraper']:
            logger.info("\nPOR SCRAPER:")
            for scraper, stats in self.stats['by_scraper'].items():
                logger.info(f"  {scraper}:")
                for status, count in stats.items():
                    if count > 0:
                        logger.info(f"    {status}: {count}")
        
        logger.info("=" * 50)
    
    def prioritize_scrapers(self, lead_data: Dict) -> List[ScraperTask]:
        """
        Cria lista priorizada de scrapers baseado nos dados disponíveis
        
        Args:
            lead_data: Dados do lead
            
        Returns:
            Lista de tarefas priorizadas
        """
        tasks = []
        
        # Análise dos dados disponíveis
        has_instagram = bool(lead_data.get('instagram_url') or lead_data.get('instagramUrl'))
        has_facebook = bool(lead_data.get('facebook_url') or lead_data.get('facebookUrl'))
        has_website = bool(lead_data.get('website') or lead_data.get('original_website'))
        has_place_id = bool(lead_data.get('google_place_id'))
        
        # Definir prioridades baseado no que temos
        if not has_place_id:
            # Google Places é crítico se não temos ID
            priority_gp = ScraperPriority.CRITICAL
        else:
            priority_gp = ScraperPriority.LOW
        
        # Instagram tem alta prioridade se temos URL
        priority_ig = ScraperPriority.HIGH if has_instagram else ScraperPriority.MEDIUM
        
        # Website tem alta prioridade se temos URL
        priority_web = ScraperPriority.HIGH if has_website else ScraperPriority.MEDIUM
        
        # Facebook tem prioridade média
        priority_fb = ScraperPriority.MEDIUM if has_facebook else ScraperPriority.LOW
        
        return tasks