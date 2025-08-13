#!/usr/bin/env python3
"""
Token Estimator - Sistema de estimativa e gestão de tokens para LLMs
Calcula custos e uso de tokens para múltiplos providers
"""

import tiktoken
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Representa uso de tokens"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""
    provider: str = ""
    cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'model': self.model,
            'provider': self.provider,
            'cost': self.cost,
            'timestamp': self.timestamp.isoformat()
        }


class TokenEstimator:
    """
    Estima uso de tokens e custos para múltiplos LLMs
    """
    
    def __init__(self):
        """Inicializa o estimador com modelos e preços"""
        
        # Configuração de preços por 1000 tokens (em USD)
        self.pricing = {
            # OpenAI
            'gpt-4o': {'input': 0.005, 'output': 0.015},
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
            'gpt-3.5-turbo-16k': {'input': 0.003, 'output': 0.004},
            
            # Claude (Anthropic)
            'claude-3-opus': {'input': 0.015, 'output': 0.075},
            'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
            'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},
            'claude-3-haiku-20240307': {'input': 0.00025, 'output': 0.00125},
            'claude-2.1': {'input': 0.008, 'output': 0.024},
            'claude-2': {'input': 0.008, 'output': 0.024},
            'claude-instant': {'input': 0.0008, 'output': 0.0024},
            
            # Google Gemini
            'gemini-pro': {'input': 0.00025, 'output': 0.0005},
            'gemini-1.5-pro': {'input': 0.0035, 'output': 0.0105},
            'gemini-1.5-flash': {'input': 0.00035, 'output': 0.00105},
            'gemini-ultra': {'input': 0.007, 'output': 0.021},
            
            # DeepSeek
            'deepseek-chat': {'input': 0.00014, 'output': 0.00028},
            'deepseek-coder': {'input': 0.00014, 'output': 0.00028},
            
            # ZhipuAI (GLM)
            'glm-4': {'input': 0.0001, 'output': 0.0001},
            'glm-4-flash': {'input': 0.00001, 'output': 0.00001},
            'glm-4-plus': {'input': 0.0005, 'output': 0.0005},
            'glm-3-turbo': {'input': 0.00005, 'output': 0.00005},
        }
        
        # Mapeamento de modelos para encoding
        self.model_encodings = {
            'gpt-4': 'cl100k_base',
            'gpt-4o': 'cl100k_base',
            'gpt-4o-mini': 'cl100k_base',
            'gpt-3.5-turbo': 'cl100k_base',
            'claude': 'cl100k_base',  # Aproximação
            'gemini': 'cl100k_base',  # Aproximação
            'deepseek': 'cl100k_base',  # Aproximação
            'glm': 'cl100k_base',  # Aproximação
        }
        
        # Cache de encodings
        self.encodings = {}
        
        # Estatísticas acumuladas
        self.total_usage = {
            'by_provider': {},
            'by_model': {},
            'total_tokens': 0,
            'total_cost': 0.0,
            'requests': 0,
            'history': []
        }
    
    def get_encoding(self, model: str) -> Any:
        """Obtém encoding para um modelo"""
        # Determinar encoding baseado no modelo
        encoding_name = 'cl100k_base'  # Default
        
        for key, enc in self.model_encodings.items():
            if key in model.lower():
                encoding_name = enc
                break
        
        # Cache encoding
        if encoding_name not in self.encodings:
            try:
                self.encodings[encoding_name] = tiktoken.get_encoding(encoding_name)
            except:
                # Fallback para gpt-3.5-turbo
                self.encodings[encoding_name] = tiktoken.encoding_for_model("gpt-3.5-turbo")
        
        return self.encodings[encoding_name]
    
    def count_tokens(self, text: str, model: str = 'gpt-3.5-turbo') -> int:
        """
        Conta tokens em um texto
        
        Args:
            text: Texto para contar
            model: Modelo para usar na contagem
            
        Returns:
            Número de tokens
        """
        try:
            encoding = self.get_encoding(model)
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.warning(f"Erro ao contar tokens: {e}. Usando estimativa.")
            # Estimativa aproximada: 1 token ≈ 4 caracteres
            return len(text) // 4
    
    def estimate_prompt_tokens(self, prompt: str, model: str = 'gpt-3.5-turbo') -> int:
        """Estima tokens do prompt"""
        # Adicionar overhead do formato de mensagem
        overhead = 10  # Tokens para estrutura da mensagem
        return self.count_tokens(prompt, model) + overhead
    
    def estimate_completion_tokens(self, expected_length: int = 500) -> int:
        """Estima tokens da resposta"""
        # Estimativa baseada no comprimento esperado
        return expected_length
    
    def calculate_cost(self, 
                       prompt_tokens: int, 
                       completion_tokens: int, 
                       model: str) -> float:
        """
        Calcula custo baseado no uso de tokens
        
        Args:
            prompt_tokens: Tokens do prompt
            completion_tokens: Tokens da resposta
            model: Modelo usado
            
        Returns:
            Custo em USD
        """
        if model not in self.pricing:
            # Procurar modelo similar
            for key in self.pricing:
                if key in model or model in key:
                    model = key
                    break
            else:
                logger.warning(f"Modelo {model} não encontrado na tabela de preços. Usando preço padrão.")
                model = 'gpt-3.5-turbo'
        
        prices = self.pricing[model]
        
        # Calcular custo
        input_cost = (prompt_tokens / 1000) * prices['input']
        output_cost = (completion_tokens / 1000) * prices['output']
        
        return input_cost + output_cost
    
    def estimate_llm_call(self, 
                         prompt: str, 
                         model: str,
                         expected_response_length: int = 500) -> TokenUsage:
        """
        Estima uso completo de uma chamada LLM
        
        Args:
            prompt: Prompt a ser enviado
            model: Modelo a ser usado
            expected_response_length: Tamanho esperado da resposta
            
        Returns:
            TokenUsage com estimativas
        """
        # Contar tokens
        prompt_tokens = self.estimate_prompt_tokens(prompt, model)
        completion_tokens = self.estimate_completion_tokens(expected_response_length)
        total_tokens = prompt_tokens + completion_tokens
        
        # Calcular custo
        cost = self.calculate_cost(prompt_tokens, completion_tokens, model)
        
        # Determinar provider
        provider = self._get_provider(model)
        
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            provider=provider,
            cost=cost
        )
    
    def estimate_batch_processing(self, 
                                 num_leads: int,
                                 llm_models: List[str],
                                 analyses_per_llm: int = 10) -> Dict[str, Any]:
        """
        Estima custos para processamento em lote
        
        Args:
            num_leads: Número de leads
            llm_models: Lista de modelos LLM a usar
            analyses_per_llm: Número de análises por LLM
            
        Returns:
            Dict com estimativas detalhadas
        """
        estimates = {
            'total_leads': num_leads,
            'llm_models': llm_models,
            'analyses_per_llm': analyses_per_llm,
            'by_model': {},
            'by_provider': {},
            'total_tokens': 0,
            'total_cost': 0.0,
            'cost_per_lead': 0.0
        }
        
        # Tamanho médio de prompt e resposta
        avg_prompt_size = 800  # caracteres
        avg_response_tokens = 300  # tokens
        
        for model in llm_models:
            # Estimar para um lead
            prompt_tokens = self.count_tokens("x" * avg_prompt_size, model)
            completion_tokens = avg_response_tokens * analyses_per_llm
            
            # Multiplicar pelo número de leads
            total_prompt_tokens = prompt_tokens * analyses_per_llm * num_leads
            total_completion_tokens = completion_tokens * num_leads
            
            # Calcular custo
            cost = self.calculate_cost(total_prompt_tokens, total_completion_tokens, model)
            
            # Adicionar às estimativas
            provider = self._get_provider(model)
            
            estimates['by_model'][model] = {
                'prompt_tokens': total_prompt_tokens,
                'completion_tokens': total_completion_tokens,
                'total_tokens': total_prompt_tokens + total_completion_tokens,
                'cost': cost,
                'cost_per_lead': cost / num_leads if num_leads > 0 else 0
            }
            
            # Agregar por provider
            if provider not in estimates['by_provider']:
                estimates['by_provider'][provider] = {
                    'tokens': 0,
                    'cost': 0.0
                }
            
            estimates['by_provider'][provider]['tokens'] += total_prompt_tokens + total_completion_tokens
            estimates['by_provider'][provider]['cost'] += cost
            
            # Totais
            estimates['total_tokens'] += total_prompt_tokens + total_completion_tokens
            estimates['total_cost'] += cost
        
        estimates['cost_per_lead'] = estimates['total_cost'] / num_leads if num_leads > 0 else 0
        
        return estimates
    
    def track_usage(self, usage: TokenUsage):
        """
        Registra uso de tokens
        
        Args:
            usage: Uso de tokens para registrar
        """
        # Atualizar totais
        self.total_usage['total_tokens'] += usage.total_tokens
        self.total_usage['total_cost'] += usage.cost
        self.total_usage['requests'] += 1
        
        # Por provider
        if usage.provider not in self.total_usage['by_provider']:
            self.total_usage['by_provider'][usage.provider] = {
                'tokens': 0,
                'cost': 0.0,
                'requests': 0
            }
        
        self.total_usage['by_provider'][usage.provider]['tokens'] += usage.total_tokens
        self.total_usage['by_provider'][usage.provider]['cost'] += usage.cost
        self.total_usage['by_provider'][usage.provider]['requests'] += 1
        
        # Por modelo
        if usage.model not in self.total_usage['by_model']:
            self.total_usage['by_model'][usage.model] = {
                'tokens': 0,
                'cost': 0.0,
                'requests': 0
            }
        
        self.total_usage['by_model'][usage.model]['tokens'] += usage.total_tokens
        self.total_usage['by_model'][usage.model]['cost'] += usage.cost
        self.total_usage['by_model'][usage.model]['requests'] += 1
        
        # Histórico
        self.total_usage['history'].append(usage.to_dict())
        
        # Limitar histórico a últimas 1000 entradas
        if len(self.total_usage['history']) > 1000:
            self.total_usage['history'] = self.total_usage['history'][-1000:]
    
    def get_usage_report(self) -> Dict[str, Any]:
        """
        Gera relatório de uso
        
        Returns:
            Dict com estatísticas de uso
        """
        report = {
            'summary': {
                'total_tokens': self.total_usage['total_tokens'],
                'total_cost': round(self.total_usage['total_cost'], 4),
                'total_requests': self.total_usage['requests'],
                'avg_tokens_per_request': (
                    self.total_usage['total_tokens'] / self.total_usage['requests']
                    if self.total_usage['requests'] > 0 else 0
                ),
                'avg_cost_per_request': (
                    self.total_usage['total_cost'] / self.total_usage['requests']
                    if self.total_usage['requests'] > 0 else 0
                )
            },
            'by_provider': {},
            'by_model': {}
        }
        
        # Por provider
        for provider, data in self.total_usage['by_provider'].items():
            report['by_provider'][provider] = {
                'tokens': data['tokens'],
                'cost': round(data['cost'], 4),
                'requests': data['requests'],
                'percentage_of_cost': (
                    (data['cost'] / self.total_usage['total_cost'] * 100)
                    if self.total_usage['total_cost'] > 0 else 0
                )
            }
        
        # Por modelo
        for model, data in self.total_usage['by_model'].items():
            report['by_model'][model] = {
                'tokens': data['tokens'],
                'cost': round(data['cost'], 4),
                'requests': data['requests']
            }
        
        return report
    
    def _get_provider(self, model: str) -> str:
        """Determina provider baseado no modelo"""
        model_lower = model.lower()
        
        if 'gpt' in model_lower or 'openai' in model_lower:
            return 'openai'
        elif 'claude' in model_lower:
            return 'anthropic'
        elif 'gemini' in model_lower:
            return 'google'
        elif 'deepseek' in model_lower:
            return 'deepseek'
        elif 'glm' in model_lower or 'zhipu' in model_lower:
            return 'zhipuai'
        else:
            return 'unknown'
    
    def format_cost(self, cost: float) -> str:
        """Formata custo para exibição"""
        if cost < 0.01:
            return f"${cost:.6f}"
        elif cost < 1:
            return f"${cost:.4f}"
        else:
            return f"${cost:.2f}"
    
    def print_estimate(self, estimates: Dict[str, Any]):
        """Imprime estimativas formatadas"""
        print("\n" + "=" * 60)
        print("ESTIMATIVA DE CUSTOS DE PROCESSAMENTO")
        print("=" * 60)
        
        print(f"\n📊 CONFIGURAÇÃO:")
        print(f"  • Total de leads: {estimates['total_leads']}")
        print(f"  • Modelos LLM: {', '.join(estimates['llm_models'])}")
        print(f"  • Análises por LLM: {estimates['analyses_per_llm']}")
        
        print(f"\n💰 CUSTOS POR MODELO:")
        for model, data in estimates['by_model'].items():
            print(f"  {model}:")
            print(f"    • Tokens: {data['total_tokens']:,}")
            print(f"    • Custo total: {self.format_cost(data['cost'])}")
            print(f"    • Custo por lead: {self.format_cost(data['cost_per_lead'])}")
        
        print(f"\n🏢 CUSTOS POR PROVIDER:")
        for provider, data in estimates['by_provider'].items():
            print(f"  {provider}:")
            print(f"    • Tokens: {data['tokens']:,}")
            print(f"    • Custo: {self.format_cost(data['cost'])}")
        
        print(f"\n📈 TOTAIS:")
        print(f"  • Total de tokens: {estimates['total_tokens']:,}")
        print(f"  • Custo total estimado: {self.format_cost(estimates['total_cost'])}")
        print(f"  • Custo médio por lead: {self.format_cost(estimates['cost_per_lead'])}")
        
        print("\n" + "=" * 60)