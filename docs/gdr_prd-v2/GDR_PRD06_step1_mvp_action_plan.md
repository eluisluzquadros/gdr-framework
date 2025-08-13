# Plano de Ação MVP - GDR Etapa 1
**Implementation Roadmap**

---

## 🎯 Objetivo do MVP

Desenvolver e entregar a **Etapa 1** do framework GDR em **8 semanas**, focando em:
- Coleta automatizada de dados multi-fonte
- Consenso multi-LLM com análise estatística
- Export de resultados estruturados
- Base sólida para expansão futura

---

## 📅 Timeline Geral

| Sprint | Duração | Foco Principal | Entrega |
|--------|---------|----------------|---------|
| **Sprint 0** | Semana 1 | Setup + Infraestrutura | Ambiente configurado |
| **Sprint 1** | Semanas 2-3 | Core Framework + Scrapers | Coleta básica funcionando |
| **Sprint 2** | Semanas 4-5 | Multi-LLM + Consenso | Análise estatística |
| **Sprint 3** | Semanas 6-7 | Integration + Export | MVP completo |
| **Sprint 4** | Semana 8 | Testing + Refinement | Produto pronto |

---

## 🏗️ Sprint 0: Setup e Infraestrutura (Semana 1)

### Objetivos
- Configurar ambiente de desenvolvimento
- Estruturar arquitetura do projeto
- Configurar APIs e dependências
- Criar base de testes

### 📋 Tarefas Detalhadas

#### Dia 1-2: Project Setup
```bash
# Estrutura inicial do projeto
mkdir gdr-framework
cd gdr-framework

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Estrutura de diretórios
mkdir -p src/{core,collectors,llm,utils,models}
mkdir -p tests data/{input,output} docs
touch requirements.txt .env.example .gitignore
```

**Arquivos a criar:**

**requirements.txt**
```txt
# Core
pandas>=1.5.0
numpy>=1.24.0
python-dotenv>=1.0.0
pydantic>=2.0.0

# HTTP & Scraping
aiohttp>=3.8.0
requests>=2.28.0
beautifulsoup4>=4.11.0
lxml>=4.9.0

# LLM APIs
openai>=1.0.0
anthropic>=0.7.0
google-generativeai>=0.3.0

# Statistics
scikit-learn>=1.3.0
scipy>=1.10.0

# Export
openpyxl>=3.1.0
xlsxwriter>=3.0.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-asyncio>=0.21.0

# Development
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
```

**.env.example** (usando as APIs fornecidas)
```bash
# Google APIs
GOOGLE_MAPS_API_KEY=AIzaSyBMkdOiWIPVy0jPP4YeW3FLZBD4IsoIJ54
GOOGLE_CSE_API_KEY=AIzaSyBMkdOiWIPVy0jPP4YeW3FLZBD4IsoIJ54
GOOGLE_CSE_ID=f45b646b4f8fd4705

# LLM APIs
OPENAI_API_KEY=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
ANTHROPIC_API_KEY=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
GEMINI_API_KEY=AIzaSyC_QyLUF9LjDzc5zuSRoV-WGl4o3M9jhnY
DEEPSEEK_API_KEY=sk-75e2959de5424400970050c18842f650
ZHIPUAI_API_KEY=99e0d72dacc94db18ab1bb56d5b1b2aa.AGKfhwZQVe7Ki8IO

# Scraping APIs
APIFY_API_KEY=apify_api_TMGFkWu9zZ1tBsp0zKcSj4CfdhPxY52RVcK5
APIFY_API_KEY_LINKTREE=apify_api_20MX13sMQQK7hdHJPxXrmL32zuvhCt24Hepx

# Config
INPUT_DIR=./data/input
OUTPUT_DIR=./data/output
LOG_LEVEL=INFO
```

#### Dia 3-4: Core Models e Config

**src/models/lead_model.py**
```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator

@dataclass
class LeadInput:
    original_id: str  # legalDocument
    original_nome: str  # name
    original_endereco_completo: str
    original_telefone: Optional[str] = None
    original_website: Optional[str] = None
    original_email: Optional[str] = None
    
    @validator('original_id')
    def validate_cnpj(cls, v):
        # Implementar validação de CNPJ
        return v

class CollectedData(BaseModel):
    # Facebook
    gdr_facebook_url: Optional[str] = None
    gdr_facebook_mail: Optional[str] = None
    gdr_facebook_whatsapp: Optional[str] = None
    # ... outros campos conforme PRD

class ConsensusData(BaseModel):
    gdr_concenso_url: Optional[str] = None
    gdr_concenso_email: Optional[str] = None
    gdr_concenso_telefone: Optional[str] = None
    gdr_concenso_whatsapp: Optional[str] = None
    # ... análise Kappa
```

**src/core/config.py**
```python
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class GDRConfig:
    # API Keys
    google_maps_api_key: str = os.getenv('GOOGLE_MAPS_API_KEY')
    openai_api_key: str = os.getenv('OPENAI_API_KEY')
    anthropic_api_key: str = os.getenv('ANTHROPIC_API_KEY')
    # ... outras APIs
    
    # Processing
    max_concurrent_scrapers: int = 5
    llm_timeout: int = 60
    retry_attempts: int = 3
    
    # Paths
    input_dir: str = os.getenv('INPUT_DIR', './data/input')
    output_dir: str = os.getenv('OUTPUT_DIR', './data/output')
```

#### Dia 5: Base Classes e Interfaces

**src/collectors/base.py**
```python
from abc import ABC, abstractmethod
from typing import Any, Dict
import asyncio
import logging

class BaseScraper(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def scrape(self, lead_input: 'LeadInput') -> Dict[str, Any]:
        pass
    
    async def scrape_with_retry(self, lead_input: 'LeadInput', max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                return await self.scrape(lead_input)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)
```

**src/llm/base.py**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseLLM(ABC):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    @abstractmethod
    async def analyze_lead(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
```

#### Entregáveis Sprint 0
- ✅ Projeto estruturado e configurado
- ✅ Dependências instaladas
- ✅ APIs testadas (conectividade básica)
- ✅ Base classes implementadas
- ✅ Modelos de dados definidos

---

## 🔧 Sprint 1: Core Framework + Scrapers (Semanas 2-3)

### Objetivos
- Implementar sistema de coleta multi-fonte
- Integrar Google Places API
- Desenvolver scrapers de redes sociais
- Criar orchestrador de coleta

### 📋 Tarefas Detalhadas

#### Semana 2: Google Places + Website Scraper

**Dia 1-2: Google Places Scraper**

**src/collectors/google_places.py**
```python
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from .base import BaseScraper

class GooglePlacesScraper(BaseScraper):
    BASE_URL = "https://maps.googleapis.com/maps/api/place"
    
    async def scrape(self, lead_input: 'LeadInput') -> Dict[str, Any]:
        # Text search para encontrar place
        place_id = await self._search_place(lead_input)
        if not place_id:
            return {}
        
        # Details API para informações completas
        details = await self._get_place_details(place_id)
        return self._format_output(details)
    
    async def _search_place(self, lead_input: 'LeadInput') -> Optional[str]:
        query = f"{lead_input.original_nome} {lead_input.original_endereco_completo}"
        
        params = {
            'query': query,
            'key': self.config['api_key'],
            'fields': 'place_id,name,formatted_address'
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/textsearch/json"
            async with session.get(url, params=params) as response:
                data = await response.json()
                
                if data['status'] == 'OK' and data['results']:
                    return data['results'][0]['place_id']
                return None
    
    async def _get_place_details(self, place_id: str) -> Dict[str, Any]:
        fields = [
            'name', 'formatted_address', 'formatted_phone_number',
            'website', 'rating', 'user_ratings_total', 'geometry',
            'reviews', 'photos'
        ]
        
        params = {
            'place_id': place_id,
            'fields': ','.join(fields),
            'key': self.config['api_key']
        }
        
        async with aiohttp.ClientSession() as session:
            url = f"{self.BASE_URL}/details/json"
            async with session.get(url, params=params) as response:
                data = await response.json()
                return data.get('result', {})
```

**Dia 3-4: Website Scraper**

**src/collectors/website_scraper.py**
```python
import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from .base import BaseScraper

class WebsiteScraper(BaseScraper):
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'(\(?\d{2}\)?\s?\d{4,5}-?\d{4})')
    WHATSAPP_PATTERN = re.compile(r'whatsapp[^0-9]*(\d{10,13})')
    
    async def scrape(self, lead_input: 'LeadInput') -> Dict[str, Any]:
        if not lead_input.original_website:
            return {}
        
        try:
            content = await self._fetch_website_content(lead_input.original_website)
            return self._extract_contact_info(content)
        except Exception as e:
            self.logger.error(f"Error scraping {lead_input.original_website}: {e}")
            return {}
    
    async def _fetch_website_content(self, url: str) -> str:
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                return await response.text()
    
    def _extract_contact_info(self, html_content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        # Extrair informações
        emails = list(set(self.EMAIL_PATTERN.findall(text)))
        phones = list(set(self.PHONE_PATTERN.findall(text)))
        whatsapp = list(set(self.WHATSAPP_PATTERN.findall(text)))
        
        # Procurar links YouTube
        youtube_links = []
        for link in soup.find_all('a', href=True):
            if 'youtube.com' in link['href'] or 'youtu.be' in link['href']:
                youtube_links.append(link['href'])
        
        return {
            'gdr_cwral4ai_email': emails[0] if emails else None,
            'gdr_cwral4ai_telefone': phones[0] if phones else None,
            'gdr_cwral4ai_whatsapp': whatsapp[0] if whatsapp else None,
            'gdr_cwral4ai_youtube_url': youtube_links[0] if youtube_links else None,
            'gdr_cwral4ai_url': lead_input.original_website
        }
```

#### Semana 3: Social Media + Search Engine

**Dia 1-2: Social Media Scraper (Apify)**

**src/collectors/social_media.py**
```python
import asyncio
import aiohttp
from typing import Dict, Any, List
from .base import BaseScraper

class SocialMediaScraper(BaseScraper):
    APIFY_API_BASE = "https://api.apify.com/v2"
    
    async def scrape(self, lead_input: 'LeadInput') -> Dict[str, Any]:
        results = {}
        
        # Buscar perfis nas redes sociais
        social_profiles = await self._search_social_profiles(lead_input)
        
        if social_profiles.get('instagram'):
            instagram_data = await self._scrape_instagram(social_profiles['instagram'])
            results.update(instagram_data)
        
        if social_profiles.get('facebook'):
            facebook_data = await self._scrape_facebook(social_profiles['facebook'])
            results.update(facebook_data)
        
        return results
    
    async def _search_social_profiles(self, lead_input: 'LeadInput') -> Dict[str, str]:
        # Lógica para encontrar perfis sociais
        # Pode usar Google Search ou heurísticas
        return {
            'instagram': f"@{lead_input.original_nome.lower().replace(' ', '')}",
            'facebook': f"{lead_input.original_nome}"
        }
    
    async def _scrape_instagram(self, username: str) -> Dict[str, Any]:
        # Usar Apify Instagram scraper
        actor_input = {
            "usernames": [username],
            "resultsLimit": 1
        }
        
        result = await self._run_apify_actor("apify/instagram-scraper", actor_input)
        
        if result and len(result) > 0:
            profile = result[0]
            return {
                'gdr_instagram_url': profile.get('url'),
                'gdr_instagram_username': profile.get('username'),
                'gdr_instagram_followers': profile.get('followersCount'),
                'gdr_instagram_bio': profile.get('biography'),
                'gdr_instagram_is_verified': profile.get('isVerified'),
                'gdr_instagram_is_business': profile.get('isBusinessAccount')
            }
        return {}
    
    async def _run_apify_actor(self, actor_id: str, input_data: Dict) -> List[Dict]:
        headers = {'Authorization': f'Bearer {self.config["apify_api_key"]}'}
        
        async with aiohttp.ClientSession() as session:
            # Start actor run
            url = f"{self.APIFY_API_BASE}/acts/{actor_id}/runs"
            async with session.post(url, json=input_data, headers=headers) as response:
                run_data = await response.json()
                run_id = run_data['data']['id']
            
            # Wait for completion and get results
            await self._wait_for_run_completion(session, run_id, headers)
            return await self._get_run_results(session, run_id, headers)
```

**Dia 3-4: Search Engine Scraper**

**src/collectors/search_engine.py**
```python
import asyncio
import aiohttp
from .base import BaseScraper

class SearchEngineScraper(BaseScraper):
    CUSTOM_SEARCH_URL = "https://www.googleapis.com/customsearch/v1"
    
    async def scrape(self, lead_input: 'LeadInput') -> Dict[str, Any]:
        query = f'"{lead_input.original_nome}" contato telefone email'
        
        search_results = await self._perform_search(query)
        return self._extract_contact_info_from_snippets(search_results)
    
    async def _perform_search(self, query: str) -> List[Dict]:
        params = {
            'key': self.config['api_key'],
            'cx': self.config['search_engine_id'],
            'q': query,
            'num': 10
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.CUSTOM_SEARCH_URL, params=params) as response:
                data = await response.json()
                return data.get('items', [])
    
    def _extract_contact_info_from_snippets(self, results: List[Dict]) -> Dict[str, Any]:
        # Usar regex para extrair contatos dos snippets
        all_text = ' '.join([item.get('snippet', '') for item in results])
        
        emails = self.EMAIL_PATTERN.findall(all_text)
        phones = self.PHONE_PATTERN.findall(all_text)
        
        return {
            'gdr_google_search_engine_email': emails[0] if emails else None,
            'gdr_google_search_engine_telefone': phones[0] if phones else None,
            'gdr_google_search_engine_url': results[0]['link'] if results else None
        }
```

#### Entregáveis Sprint 1
- ✅ Google Places Scraper funcional
- ✅ Website Scraper implementado
- ✅ Social Media Scraper (Apify integration)
- ✅ Search Engine Scraper
- ✅ Testes unitários básicos
- ✅ Orchestrador de coleta funcionando

---

## 🧠 Sprint 2: Multi-LLM + Consenso (Semanas 4-5)

### Objetivos
- Implementar integração com 5 LLMs
- Desenvolver sistema de consenso
- Calcular análise estatística Kappa
- Criar scoring engine

### 📋 Tarefas Detalhadas

#### Semana 4: LLM Integrations

**Dia 1-2: LLM Providers**

**src/llm/providers/openai_provider.py**
```python
import openai
from typing import Dict, Any
from ..base import BaseLLM

class OpenAIProvider(BaseLLM):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = openai.OpenAI(api_key=api_key)
    
    async def analyze_lead(self, collected_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_analysis_prompt(collected_data)
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        return self._parse_response(response.choices[0].message.content)
    
    def _get_system_prompt(self) -> str:
        return """
        Você é um especialista em análise de dados de leads B2B.
        Consolide as informações de contato coletadas de múltiplas fontes.
        Retorne sempre um JSON válido com os campos consolidados.
        """
    
    def _build_analysis_prompt(self, data: Dict[str, Any]) -> str:
        return f"""
        Analise os dados coletados abaixo e consolide as informações de contato:
        
        Dados coletados:
        {data}
        
        Retorne um JSON com:
        - url: melhor website encontrado
        - email: email mais confiável
        - telefone: telefone principal
        - whatsapp: número WhatsApp
        - synergy_score_categoria: High/Medium/Low
        - synergy_score_justificativa: explicação do score
        """
```

**src/llm/providers/claude_provider.py** (similar structure)
**src/llm/providers/gemini_provider.py** (similar structure)
**src/llm/providers/deepseek_provider.py** (similar structure)
**src/llm/providers/zhipuai_provider.py** (similar structure)

**Dia 3-4: Multi-LLM Manager**

**src/llm/llm_manager.py**
```python
import asyncio
from typing import Dict, Any, List, Optional
from .providers import (
    OpenAIProvider, ClaudeProvider, GeminiProvider,
    DeepSeekProvider, ZhipuAIProvider
)

class MultiLLMManager:
    def __init__(self, config: Dict[str, str]):
        self.providers = {
            'openai': OpenAIProvider(config['openai_api_key']),
            'claude': ClaudeProvider(config['anthropic_api_key']),
            'gemini': GeminiProvider(config['gemini_api_key']),
            'deepseek': DeepSeekProvider(config['deepseek_api_key']),
            'zhipuai': ZhipuAIProvider(config['zhipuai_api_key'])
        }
    
    async def analyze_with_all_llms(self, collected_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        tasks = []
        for name, provider in self.providers.items():
            task = asyncio.create_task(
                self._analyze_with_timeout(provider, collected_data, name)
            )
            tasks.append((name, task))
        
        results = {}
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
            except Exception as e:
                logger.error(f"Error with {name}: {e}")
                results[name] = None
        
        return results
    
    async def _analyze_with_timeout(self, provider: BaseLLM, data: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
        try:
            return await asyncio.wait_for(
                provider.analyze_lead(data),
                timeout=60
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout for {name} provider")
            return None
```

#### Semana 5: Consensus Analysis

**Dia 1-3: Kappa Statistics**

**src/llm/kappa_analysis.py**
```python
import numpy as np
from sklearn.metrics import cohen_kappa_score
from scipy.stats import chi2
from typing import Dict, List, Tuple, Any
from itertools import combinations

class KappaAnalyzer:
    def __init__(self):
        self.interpretation_map = {
            (0.0, 0.20): "Poor",
            (0.21, 0.40): "Fair", 
            (0.41, 0.60): "Moderate",
            (0.61, 0.80): "Good",
            (0.81, 1.00): "Very Good"
        }
    
    def calculate_comprehensive_kappa(self, llm_responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        # Preparar dados para análise
        valid_responses = {k: v for k, v in llm_responses.items() if v is not None}
        
        if len(valid_responses) < 2:
            return self._create_insufficient_data_result()
        
        # Análise por campo
        field_kappa_scores = self._calculate_field_kappa_scores(valid_responses)
        
        # Análise pairwise entre LLMs
        pairwise_scores = self._calculate_pairwise_kappa(valid_responses)
        
        # Score geral
        overall_kappa = self._calculate_overall_kappa(valid_responses)
        
        # Ranking de confiabilidade
        reliability_ranking = self._calculate_llm_reliability(pairwise_scores)
        
        return {
            'gdr_kappa_overall_score': overall_kappa['score'],
            'gdr_kappa_interpretation': overall_kappa['interpretation'],
            'gdr_kappa_confidence_interval': overall_kappa['confidence_interval'],
            'gdr_kappa_p_value': overall_kappa['p_value'],
            
            # Por campo
            'gdr_kappa_email_score': field_kappa_scores.get('email', 0.0),
            'gdr_kappa_telefone_score': field_kappa_scores.get('telefone', 0.0),
            'gdr_kappa_whatsapp_score': field_kappa_scores.get('whatsapp', 0.0),
            'gdr_kappa_website_score': field_kappa_scores.get('url', 0.0),
            
            # Pairwise scores
            **pairwise_scores,
            
            # Flags
            'gdr_kappa_high_confidence_flag': overall_kappa['score'] > 0.7,
            'gdr_kappa_review_required_flag': overall_kappa['score'] < 0.4,
            'gdr_kappa_partial_consensus_flag': 0.4 <= overall_kappa['score'] <= 0.7,
            
            # Confiabilidade
            'gdr_kappa_most_reliable_llm': reliability_ranking['most_reliable'],
            'gdr_kappa_least_reliable_llm': reliability_ranking['least_reliable']
        }
    
    def _calculate_field_kappa_scores(self, responses: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        fields = ['email', 'telefone', 'whatsapp', 'url']
        field_scores = {}
        
        for field in fields:
            # Extrair valores do campo de cada LLM
            values = []
            for llm_name, response in responses.items():
                value = response.get(field, None)
                # Normalizar valores (None, empty string, etc.)
                normalized_value = self._normalize_field_value(value)
                values.append(normalized_value)
            
            # Calcular Kappa para este campo
            if len(set(values)) > 1:  # Há variação nos dados
                field_scores[field] = self._calculate_inter_rater_agreement(values)
            else:
                field_scores[field] = 1.0  # Concordância perfeita
        
        return field_scores
    
    def _calculate_pairwise_kappa(self, responses: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        llm_names = list(responses.keys())
        pairwise_scores = {}
        
        for llm1, llm2 in combinations(llm_names, 2):
            # Comparar responses dos dois LLMs
            kappa_score = self._calculate_llm_pair_kappa(
                responses[llm1], responses[llm2]
            )
            
            key = f"gdr_kappa_{llm1}_{llm2}_score"
            pairwise_scores[key] = kappa_score
        
        return pairwise_scores
    
    def _calculate_overall_kappa(self, responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        # Implementar Fleiss' Kappa para múltiplos avaliadores
        all_ratings = self._prepare_ratings_matrix(responses)
        
        kappa_score = self._fleiss_kappa(all_ratings)
        interpretation = self._interpret_kappa(kappa_score)
        confidence_interval = self._calculate_confidence_interval(kappa_score, len(responses))
        p_value = self._calculate_significance(kappa_score, len(responses))
        
        return {
            'score': kappa_score,
            'interpretation': interpretation,
            'confidence_interval': confidence_interval,
            'p_value': p_value
        }
```

**Dia 4-5: Consensus Engine**

**src/llm/consensus.py**
```python
from typing import Dict, Any, List, Optional
from .kappa_analysis import KappaAnalyzer

class ConsensusEngine:
    def __init__(self):
        self.kappa_analyzer = KappaAnalyzer()
        self.field_weights = {
            'email': 0.3,
            'telefone': 0.3,
            'whatsapp': 0.2,
            'url': 0.2
        }
    
    def generate_consensus(self, llm_responses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        # Análise Kappa
        kappa_analysis = self.kappa_analyzer.calculate_comprehensive_kappa(llm_responses)
        
        # Consolidação de dados por campo
        consolidated_data = self._consolidate_fields(llm_responses, kappa_analysis)
        
        # Scoring final
        synergy_score = self._calculate_synergy_score(consolidated_data, kappa_analysis)
        
        # Combinar resultados
        final_result = {
            **consolidated_data,
            **kappa_analysis,
            **synergy_score,
            'gdr_concenso_total_campos_originais': self._count_original_fields(llm_responses),
            'gdr_concenso_total_campos_enriquecidos': self._count_enriched_fields(consolidated_data),
            'gdr_concenso_novos_campos_adicionados': self._count_new_fields(consolidated_data)
        }
        
        return final_result
    
    def _consolidate_fields(self, responses: Dict[str, Dict[str, Any]], kappa_data: Dict[str, Any]) -> Dict[str, Any]:
        consolidated = {}
        
        # Para cada campo, escolher valor baseado em consenso e confiabilidade
        for field in ['email', 'telefone', 'whatsapp', 'url']:
            field_values = []
            for llm_name, response in responses.items():
                if response and response.get(field):
                    field_values.append((llm_name, response[field]))
            
            # Escolher melhor valor baseado em:
            # 1. Consenso (valores mais frequentes)
            # 2. Confiabilidade do LLM
            # 3. Qualidade do dado
            best_value = self._select_best_field_value(field_values, kappa_data)
            consolidated[f'gdr_concenso_{field}'] = best_value
        
        return consolidated
    
    def _calculate_synergy_score(self, consolidated_data: Dict[str, Any], kappa_data: Dict[str, Any]) -> Dict[str, Any]:
        # Calcular score baseado em:
        # - Quantidade de dados consolidados
        # - Qualidade do consenso (Kappa)
        # - Completude das informações
        
        data_completeness = sum(1 for v in consolidated_data.values() if v is not None) / len(consolidated_data)
        consensus_quality = kappa_data['gdr_kappa_overall_score']
        
        final_score = (data_completeness * 0.6) + (consensus_quality * 0.4)
        
        if final_score >= 0.8:
            categoria = "High"
        elif final_score >= 0.5:
            categoria = "Medium"
        else:
            categoria = "Low"
        
        justificativa = f"Score {final_score:.2f} baseado em completude ({data_completeness:.2f}) e consenso Kappa ({consensus_quality:.2f})"
        
        return {
            'gdr_concenso_synergy_score_categoria': categoria,
            'gdr_concenso_synergy_score_justificativa': justificativa
        }
```

#### Entregáveis Sprint 2
- ✅ Integração com 5 LLMs funcionando
- ✅ Sistema de consenso implementado
- ✅ Análise estatística Kappa completa
- ✅ Scoring engine funcional
- ✅ Testes de integração

---

## 🚀 Sprint 3: Integration + Export (Semanas 6-7)

### Objetivos
- Integrar todos os componentes
- Implementar sistema de export
- Criar framework principal
- Desenvolver sistema de logs e monitoramento

### 📋 Tarefas Detalhadas

#### Semana 6: Main Framework

**src/core/gdr_main.py**
```python
import asyncio
import logging
from typing import List, Dict, Any
import pandas as pd

from ..models.lead_model import LeadInput
from ..collectors import ScrapingOrchestrator
from ..llm import MultiLLMManager, ConsensusEngine
from ..utils import ExportManager, DataValidator

class GDRFramework:
    def __init__(self, config: GDRConfig):
        self.config = config
        self.scraping_orchestrator = ScrapingOrchestrator(config)
        self.llm_manager = MultiLLMManager(config)
        self.consensus_engine = ConsensusEngine()
        self.export_manager = ExportManager(config)
        self.data_validator = DataValidator()
        
        # Setup logging
        self._setup_logging()
    
    async def process_leads_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Processa arquivo de leads completo"""
        self.logger.info(f"Processando arquivo: {file_path}")
        
        # Carregar e validar dados
        leads = await self._load_and_validate_leads(file_path)
        self.logger.info(f"Carregados {len(leads)} leads válidos")
        
        # Processar em lotes
        results = []
        batch_size = 10  # Processar 10 por vez
        
        for i in range(0, len(leads), batch_size):
            batch = leads[i:i+batch_size]
            batch_results = await self._process_batch(batch)
            results.extend(batch_results)
            
            self.logger.info(f"Processado lote {i//batch_size + 1}/{(len(leads)-1)//batch_size + 1}")
        
        return results
    
    async def _process_batch(self, leads: List[LeadInput]) -> List[Dict[str, Any]]:
        """Processa um lote de leads"""
        tasks = []
        for lead in leads:
            task = asyncio.create_task(self._process_single_lead(lead))
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _process_single_lead(self, lead: LeadInput) -> Dict[str, Any]:
        """Processa um lead individual"""
        try:
            # Etapa 1: Coleta de dados
            collected_data = await self.scraping_orchestrator.collect_lead_data(lead)
            
            # Etapa 2: Análise multi-LLM
            llm_responses = await self.llm_manager.analyze_with_all_llms(collected_data)
            
            # Etapa 3: Consenso e consolidação
            consensus_result = self.consensus_engine.generate_consensus(llm_responses)
            
            # Combinar dados originais + coletados + consenso
            final_result = {
                **lead.__dict__,  # Dados originais
                **collected_data,  # Dados coletados
                **consensus_result,  # Dados consolidados
                'processing_status': 'success',
                'processing_timestamp': datetime.now().isoformat()
            }
            
            return final_result
            
        except Exception as e:
            self.logger.error(f"Erro processando lead {lead.original_id}: {e}")
            return {
                **lead.__dict__,
                'processing_status': 'error',
                'processing_error': str(e),
                'processing_timestamp': datetime.now().isoformat()
            }
```

#### Semana 7: Export System

**src/utils/export_manager.py**
```python
import pandas as pd
import json
from typing import List, Dict, Any
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

class ExportManager:
    def __init__(self, config):
        self.config = config
    
    def export_results(self, results: List[Dict[str, Any]], output_path: str, format: str = 'excel'):
        """Exporta resultados em formato especificado"""
        
        if format == 'excel':
            self._export_to_excel(results, output_path)
        elif format == 'csv':
            self._export_to_csv(results, output_path)
        elif format == 'json':
            self._export_to_json(results, output_path)
        else:
            raise ValueError(f"Formato {format} não suportado")
    
    def _export_to_excel(self, results: List[Dict[str, Any]], output_path: str):
        """Exporta para Excel com múltiplas abas"""
        wb = Workbook()
        
        # Aba principal: Dados consolidados
        ws_main = wb.active
        ws_main.title = "Dados Consolidados"
        
        # Preparar dados principais
        main_columns = [
            'original_id', 'original_nome', 'original_endereco_completo',
            'gdr_concenso_email', 'gdr_concenso_telefone', 'gdr_concenso_whatsapp',
            'gdr_concenso_url', 'gdr_concenso_synergy_score_categoria',
            'gdr_kappa_overall_score', 'gdr_kappa_interpretation',
            'processing_status'
        ]
        
        # Headers
        for col, header in enumerate(main_columns, 1):
            cell = ws_main.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
        
        # Dados
        for row, result in enumerate(results, 2):
            for col, column in enumerate(main_columns, 1):
                ws_main.cell(row=row, column=col, value=result.get(column, ''))
        
        # Aba: Métricas Kappa
        ws_kappa = wb.create_sheet("Análise Kappa")
        self._create_kappa_analysis_sheet(ws_kappa, results)
        
        # Aba: Dados Brutos Coletados
        ws_raw = wb.create_sheet("Dados Coletados")
        self._create_raw_data_sheet(ws_raw, results)
        
        # Aba: Estatísticas
        ws_stats = wb.create_sheet("Estatísticas")
        self._create_statistics_sheet(ws_stats, results)
        
        wb.save(output_path)
    
    def _create_kappa_analysis_sheet(self, worksheet, results):
        """Cria aba com análise detalhada do Kappa"""
        kappa_columns = [
            'original_id', 'original_nome',
            'gdr_kappa_overall_score', 'gdr_kappa_interpretation',
            'gdr_kappa_email_score', 'gdr_kappa_telefone_score',
            'gdr_kappa_high_confidence_flag', 'gdr_kappa_review_required_flag'
        ]
        
        # Headers
        for col, header in enumerate(kappa_columns, 1):
            worksheet.cell(row=1, column=col, value=header)
        
        # Dados
        for row, result in enumerate(results, 2):
            for col, column in enumerate(kappa_columns, 1):
                worksheet.cell(row=row, column=col, value=result.get(column, ''))
    
    def generate_processing_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Gera relatório de processamento"""
        total_leads = len(results)
        successful = len([r for r in results if r.get('processing_status') == 'success'])
        failed = total_leads - successful
        
        # Métricas de qualidade
        high_confidence = len([r for r in results if r.get('gdr_kappa_high_confidence_flag')])
        review_required = len([r for r in results if r.get('gdr_kappa_review_required_flag')])
        
        # Cobertura de dados
        with_email = len([r for r in results if r.get('gdr_concenso_email')])
        with_phone = len([r for r in results if r.get('gdr_concenso_telefone')])
        with_whatsapp = len([r for r in results if r.get('gdr_concenso_whatsapp')])
        
        return {
            'total_leads_processed': total_leads,
            'successful_processing': successful,
            'failed_processing': failed,
            'success_rate': successful / total_leads if total_leads > 0 else 0,
            
            'high_confidence_leads': high_confidence,
            'review_required_leads': review_required,
            'high_confidence_rate': high_confidence / total_leads if total_leads > 0 else 0,
            
            'email_coverage': with_email / total_leads if total_leads > 0 else 0,
            'phone_coverage': with_phone / total_leads if total_leads > 0 else 0,
            'whatsapp_coverage': with_whatsapp / total_leads if total_leads > 0 else 0,
            
            'average_kappa_score': sum(r.get('gdr_kappa_overall_score', 0) for r in results) / total_leads if total_leads > 0 else 0
        }
```

#### Entregáveis Sprint 3
- ✅ Framework principal completo e funcionando
- ✅ Sistema de export Excel/CSV/JSON
- ✅ Relatórios de métricas e qualidade
- ✅ Logs estruturados e monitoramento
- ✅ Sistema de configuração flexível

---

## 🧪 Sprint 4: Testing + Refinement (Semana 8)

### Objetivos
- Testes completos do sistema
- Refinamento baseado em testes
- Documentação técnica
- Preparação para produção

### 📋 Tarefas Detalhadas

#### Dia 1-2: Testes Automatizados

**tests/test_integration.py**
```python
import pytest
import asyncio
from src.core.gdr_main import GDRFramework
from src.core.config import GDRConfig

@pytest.mark.asyncio
async def test_end_to_end_processing():
    """Teste end-to-end com dados reais"""
    config = GDRConfig()
    gdr = GDRFramework(config)
    
    # Dados de teste
    test_file = "tests/data/sample_leads.xlsx"
    
    # Processar
    results = await gdr.process_leads_file(test_file)
    
    # Validações
    assert len(results) > 0
    assert all('processing_status' in result for result in results)
    assert any(result['processing_status'] == 'success' for result in results)

@pytest.mark.asyncio
async def test_google_places_integration():
    """Teste integração Google Places"""
    # Implementar teste específico

@pytest.mark.asyncio  
async def test_multi_llm_consensus():
    """Teste consenso multi-LLM"""
    # Implementar teste específico

def test_kappa_calculation():
    """Teste cálculo estatística Kappa"""
    # Implementar teste específico
```

#### Dia 3-4: Performance Testing

```python
# tests/test_performance.py
import time
import asyncio
import pytest
from src.core.gdr_main import GDRFramework

@pytest.mark.performance
async def test_processing_speed():
    """Teste velocidade de processamento"""
    config = GDRConfig()
    gdr = GDRFramework(config)
    
    # 100 leads de teste
    start_time = time.time()
    results = await gdr.process_leads_file("tests/data/100_leads.xlsx")
    end_time = time.time()
    
    processing_time = end_time - start_time
    leads_per_second = len(results) / processing_time
    
    # Validações de performance
    assert processing_time < 3000  # Menos de 50 minutos para 100 leads
    assert leads_per_second > 0.033  # Pelo menos 1 lead a cada 30 segundos
```

#### Dia 5: Documentation & Final Polish

**Criar documentação técnica completa:**
- API Reference
- Configuration Guide  
- Troubleshooting Guide
- Performance Tuning

#### Entregáveis Sprint 4
- ✅ Suite completa de testes (unitários + integração)
- ✅ Testes de performance validados
- ✅ Documentação técnica completa
- ✅ Sistema otimizado e pronto para produção
- ✅ Exemplos de uso documentados

---

## 📊 Critérios de Aceite do MVP

### ✅ Funcionalidades Core
- [ ] Processar planilha Excel com 100+ leads
- [ ] Integrar 4+ scrapers (Google Places, Social Media, Website, Search)
- [ ] Executar consenso com 5 LLMs (OpenAI, Claude, Gemini, DeepSeek, ZhipuAI)
- [ ] Calcular análise estatística Kappa completa
- [ ] Exportar resultados Excel/CSV/JSON

### ✅ Performance Targets
- [ ] Processar 100 leads em < 50 minutos
- [ ] Taxa de sucesso > 85%
- [ ] Cobertura de enriquecimento > 70%
- [ ] Kappa médio > 0.5 (Moderate agreement)

### ✅ Qualidade
- [ ] Suite de testes com > 80% coverage
- [ ] Logs estruturados completos
- [ ] Tratamento de erros robusto
- [ ] Documentação técnica completa

---

## 🎯 Próximos Passos (Pós-MVP)

### Etapa 2: Análise Geográfica
- Computer Vision para Street View
- Análise de buffer geográfico (concorrentes, tráfego)
- Insights qualitativos avançados

### Etapa 3: Platform Features
- Dashboard web interativo
- API REST para integrações
- Sistema de notificações
- Multi-tenancy

---

**MVP Ready Date: 8 semanas a partir do início**  
**Next Review: Final da Semana 4**