#!/usr/bin/env python3
"""
LLM Analyzer V3 - Sistema Multi-LLM Atualizado
Inclui: OpenAI, Claude (Anthropic), Gemini, DeepSeek, ZhipuAI (GLM-4.5)
"""

import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMAnalyzerV3:
    """Sistema Multi-LLM com 5 providers"""
    
    def __init__(self):
        self.providers = self._init_providers()
        self.session = None
        self.analises_esperadas = [
            'resumo_qualitativo_reviews_google_place',
            'analise_localização_google_place',
            'analise_fluxo_pessoas_comercio',
            'concorrentes_buffer_500m',
            'vetores_geradores_trafego_buffer_500m',
            'potencial_geomarkenting_categoria',
            'potencial_geomarketing_justificativa',
            'abordagem_sugerida_pitch',
            'synergy_score_categoria',
            'synergy_score_justificativa'
        ]
        
    def _init_providers(self) -> Dict:
        """Inicializa todos os providers de LLM disponíveis"""
        providers = {}
        
        # OpenAI
        if os.getenv('OPENAI_API_KEY'):
            providers['openai'] = {
                'api_key': os.getenv('OPENAI_API_KEY'),
                'model': 'gpt-4o-mini',  # Modelo mais recente e econômico
                'endpoint': 'https://api.openai.com/v1/chat/completions',
                'type': 'openai'
            }
            logger.info("✓ OpenAI configurado (GPT-4o-mini)")
        
        # Claude (Anthropic)
        if os.getenv('ANTHROPIC_API_KEY'):
            providers['claude'] = {
                'api_key': os.getenv('ANTHROPIC_API_KEY'),
                'model': 'claude-3-haiku-20240307',  # Modelo econômico e rápido
                'endpoint': 'https://api.anthropic.com/v1/messages',
                'type': 'claude',
                'version': '2023-06-01'
            }
            logger.info("✓ Claude configurado (Claude 3 Haiku)")
        
        # Gemini
        if os.getenv('GEMINI_API_KEY'):
            providers['gemini'] = {
                'api_key': os.getenv('GEMINI_API_KEY'),
                'model': 'gemini-1.5-flash',
                'endpoint': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent',
                'type': 'gemini'
            }
            logger.info("✓ Gemini configurado (1.5 Flash)")
        
        # DeepSeek
        if os.getenv('DEEPSEEK_API_KEY'):
            providers['deepseek'] = {
                'api_key': os.getenv('DEEPSEEK_API_KEY'),
                'model': 'deepseek-chat',
                'endpoint': 'https://api.deepseek.com/v1/chat/completions',
                'type': 'openai'  # DeepSeek usa formato OpenAI
            }
            logger.info("✓ DeepSeek configurado")
        
        # ZhipuAI (GLM-4.5)
        if os.getenv('ZHIPUAI_API_KEY'):
            providers['zhipuai'] = {
                'api_key': os.getenv('ZHIPUAI_API_KEY'),
                'model': 'glm-4-flash',  # GLM-4.5 Flash (mais rápido)
                'endpoint': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
                'type': 'zhipuai'
            }
            logger.info("✓ ZhipuAI configurado (GLM-4.5 Flash)")
        
        logger.info(f"Total de LLMs disponíveis: {len(providers)}")
        return providers
    
    async def init_session(self):
        """Inicializa sessão HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Fecha sessão HTTP"""
        if self.session:
            await self.session.close()
    
    async def analyze_with_llm(self, lead_data: Dict, scraped_data: Dict, llm_name: str) -> Dict:
        """Realiza análises com um LLM específico"""
        if llm_name not in self.providers:
            logger.warning(f"LLM {llm_name} não configurado")
            return self._generate_fallback_analysis_all(lead_data)
        
        await self.init_session()
        result = {}
        
        # Executar todas as análises em paralelo
        tasks = []
        for analise in self.analises_esperadas:
            task = self._analyze_single(analise, lead_data, scraped_data, llm_name)
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Processar respostas
        for analise, response in zip(self.analises_esperadas, responses):
            field_name = f'gdr_llm_{llm_name}_{analise}'
            if isinstance(response, Exception):
                logger.error(f"Erro em {llm_name}/{analise}: {response}")
                result[field_name] = self._generate_fallback_analysis(analise, lead_data)
            else:
                result[field_name] = response
        
        logger.info(f"LLM {llm_name}: Geradas {len(result)} análises")
        return result
    
    async def _analyze_single(self, analise: str, lead_data: Dict, scraped_data: Dict, llm_name: str) -> str:
        """Executa uma análise única"""
        prompt = self._create_specific_prompt(analise, lead_data, scraped_data)
        return await self._call_llm(prompt, llm_name)
    
    async def _call_llm(self, prompt: str, llm_name: str) -> str:
        """Chama LLM específico"""
        provider = self.providers[llm_name]
        
        try:
            if provider['type'] == 'openai':
                return await self._call_openai_compatible(prompt, provider)
            elif provider['type'] == 'claude':
                return await self._call_claude(prompt, provider)
            elif provider['type'] == 'gemini':
                return await self._call_gemini(prompt, provider)
            elif provider['type'] == 'zhipuai':
                return await self._call_zhipuai(prompt, provider)
            else:
                return "Tipo de LLM não suportado"
        except Exception as e:
            logger.error(f"Erro ao chamar {llm_name}: {e}")
            raise
    
    async def _call_openai_compatible(self, prompt: str, provider: Dict) -> str:
        """Chama APIs compatíveis com OpenAI (OpenAI, DeepSeek)"""
        headers = {
            'Authorization': f"Bearer {provider['api_key']}",
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': provider['model'],
            'messages': [
                {'role': 'system', 'content': 'Você é um analista de negócios especializado em análise de dados empresariais.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 500
        }
        
        async with self.session.post(provider['endpoint'], headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                error = await response.text()
                raise Exception(f"Erro API {provider['model']}: {error}")
    
    async def _call_claude(self, prompt: str, provider: Dict) -> str:
        """Chama API do Claude (Anthropic)"""
        headers = {
            'x-api-key': provider['api_key'],
            'anthropic-version': provider['version'],
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': provider['model'],
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 500,
            'temperature': 0.7
        }
        
        async with self.session.post(provider['endpoint'], headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result['content'][0]['text'].strip()
            else:
                error = await response.text()
                raise Exception(f"Erro Claude API: {error}")
    
    async def _call_gemini(self, prompt: str, provider: Dict) -> str:
        """Chama API do Gemini"""
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            'contents': [{
                'parts': [{
                    'text': prompt
                }]
            }],
            'generationConfig': {
                'temperature': 0.7,
                'maxOutputTokens': 500
            }
        }
        
        url = f"{provider['endpoint']}?key={provider['api_key']}"
        
        async with self.session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result['candidates'][0]['content']['parts'][0]['text'].strip()
            else:
                error = await response.text()
                raise Exception(f"Erro Gemini API: {error}")
    
    async def _call_zhipuai(self, prompt: str, provider: Dict) -> str:
        """Chama API do ZhipuAI (GLM-4.5)"""
        headers = {
            'Authorization': f"Bearer {provider['api_key']}",
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': provider['model'],
            'messages': [
                {'role': 'system', 'content': 'Você é um analista de negócios especializado em análise de dados empresariais.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 500,
            'stream': False
        }
        
        async with self.session.post(provider['endpoint'], headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                error = await response.text()
                raise Exception(f"Erro ZhipuAI API: {error}")
    
    def _create_specific_prompt(self, analise_type: str, lead_data: Dict, scraped_data: Dict) -> str:
        """Cria prompt específico para cada tipo de análise"""
        company_name = lead_data.get('name', 'Empresa')
        location = f"{lead_data.get('city', '')}, {lead_data.get('state', '')}"
        
        prompts = {
            'resumo_qualitativo_reviews_google_place': f"""
                Analise os reviews e avaliações para {company_name}.
                Com base nos dados disponíveis: {scraped_data.get('gdr_google_places_rating', 'N/A')} estrelas,
                {scraped_data.get('gdr_google_places_user_ratings_total', 0)} avaliações.
                Crie um resumo qualitativo identificando pontos fortes e fracos.
                Responda em 2-3 linhas.
            """,
            
            'analise_localização_google_place': f"""
                Analise a localização de {company_name} em {location}.
                Endereço: {lead_data.get('address', 'N/A')}
                Avalie o potencial da localização para o negócio.
                Responda em 2 linhas sobre a qualidade da localização.
            """,
            
            'analise_fluxo_pessoas_comercio': f"""
                Estime o fluxo de pessoas na região de {company_name} em {location}.
                Tipo de negócio: {scraped_data.get('gdr_google_places_types', 'comercial')}
                Forneça estimativa com justificativa em 2 linhas.
            """,
            
            'concorrentes_buffer_500m': f"""
                Liste 3-5 possíveis concorrentes de {company_name} num raio de 500m.
                Segmento: {scraped_data.get('gdr_facebook_category', lead_data.get('category', 'N/A'))}
                Retorne APENAS uma lista JSON de nomes.
                Exemplo: ["Loja A", "Empresa B", "Negócio C"]
            """,
            
            'vetores_geradores_trafego_buffer_500m': f"""
                Identifique 3-5 âncoras que geram tráfego próximo a {company_name} em {location}.
                Retorne APENAS uma lista JSON.
                Exemplo: ["Shopping X", "Estação Y", "Hospital Z"]
            """,
            
            'potencial_geomarkenting_categoria': f"""
                Classifique o potencial de geomarketing para {company_name}.
                Localização: {location}
                Retorne APENAS: ALTO, MÉDIO ou BAIXO
            """,
            
            'potencial_geomarketing_justificativa': f"""
                Justifique a classificação de potencial de geomarketing para {company_name}.
                Responda em 1-2 linhas máximo.
            """,
            
            'abordagem_sugerida_pitch': f"""
                Crie um pitch de vendas para abordar {company_name}.
                Segmento: {scraped_data.get('gdr_facebook_category', 'N/A')}
                Responda em 2-3 linhas com abordagem personalizada.
            """,
            
            'synergy_score_categoria': f"""
                Calcule score de sinergia para {company_name} como potencial cliente.
                Considere: localização, segmento, tamanho.
                Retorne APENAS um número entre 0-100.
            """,
            
            'synergy_score_justificativa': f"""
                Justifique o score de sinergia para {company_name}.
                Responda em 1-2 linhas máximo.
            """
        }
        
        return prompts.get(analise_type, f"Analise {analise_type} para {company_name}")
    
    def _generate_fallback_analysis(self, analise: str, lead_data: Dict) -> str:
        """Gera análise fallback quando LLM falha"""
        fallbacks = {
            'resumo_qualitativo_reviews_google_place': "Análise em processamento. Dados insuficientes para avaliação completa.",
            'analise_localização_google_place': f"Localização em {lead_data.get('city', 'cidade')} com potencial a ser avaliado.",
            'analise_fluxo_pessoas_comercio': "Fluxo médio estimado - análise detalhada pendente.",
            'concorrentes_buffer_500m': '["Concorrente A", "Concorrente B", "Concorrente C"]',
            'vetores_geradores_trafego_buffer_500m': '["Ponto de ônibus", "Área comercial", "Escola"]',
            'potencial_geomarkenting_categoria': "MÉDIO",
            'potencial_geomarketing_justificativa': "Potencial médio baseado em localização padrão.",
            'abordagem_sugerida_pitch': f"Olá {lead_data.get('name', '')}! Temos soluções que podem ajudar seu negócio a crescer.",
            'synergy_score_categoria': "50",
            'synergy_score_justificativa': "Score médio - análise completa pendente."
        }
        return fallbacks.get(analise, "Análise pendente")
    
    def _generate_fallback_analysis_all(self, lead_data: Dict) -> Dict:
        """Gera todas as análises fallback"""
        result = {}
        for analise in self.analises_esperadas:
            field_name = f'gdr_llm_fallback_{analise}'
            result[field_name] = self._generate_fallback_analysis(analise, lead_data)
        return result
    
    async def analyze_all_llms(self, lead_data: Dict, scraped_data: Dict) -> Dict:
        """Executa análise com todos os LLMs disponíveis"""
        result = {}
        
        # Analisar com cada LLM disponível
        tasks = []
        llm_names = []
        
        for llm_name in self.providers.keys():
            tasks.append(self.analyze_with_llm(lead_data, scraped_data, llm_name))
            llm_names.append(llm_name)
        
        if tasks:
            logger.info(f"Executando análise com {len(tasks)} LLMs: {llm_names}")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for llm_name, llm_result in zip(llm_names, results):
                if isinstance(llm_result, Exception):
                    logger.error(f"Erro em {llm_name}: {llm_result}")
                    result.update(self._generate_fallback_analysis_all(lead_data))
                else:
                    result.update(llm_result)
        else:
            logger.warning("Nenhum LLM configurado - usando fallback")
            result = self._generate_fallback_analysis_all(lead_data)
        
        return result
    
    def calculate_consensus(self, all_llm_results: Dict) -> Dict:
        """Calcula consenso entre múltiplos LLMs"""
        consensus = {}
        
        # Agrupar resultados por tipo de análise
        for analise in self.analises_esperadas:
            values = []
            for llm_name in self.providers.keys():
                field_name = f'gdr_llm_{llm_name}_{analise}'
                if field_name in all_llm_results:
                    values.append(all_llm_results[field_name])
            
            # Calcular consenso baseado no tipo de análise
            if 'score' in analise and values:
                # Para scores, calcular média
                try:
                    scores = [float(v) for v in values if v.isdigit()]
                    consensus[f'gdr_concenso_{analise}'] = str(int(sum(scores) / len(scores))) if scores else "50"
                except:
                    consensus[f'gdr_concenso_{analise}'] = "50"
            elif values:
                # Para textos, escolher o mais comum ou o primeiro
                from collections import Counter
                most_common = Counter(values).most_common(1)
                consensus[f'gdr_concenso_{analise}'] = most_common[0][0] if most_common else values[0]
            else:
                consensus[f'gdr_concenso_{analise}'] = "Dados insuficientes"
        
        return consensus