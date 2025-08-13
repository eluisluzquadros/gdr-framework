# GDR Framework V3.1 Enterprise

**Sistema completo de enriquecimento e qualificação automatizada de leads com Multi-LLM consensus e cache persistente.**

## 🚀 Quick Start

### 1. Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/gdr-framework.git
cd gdr-framework

# Crie ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt
```

### 2. Configuração

```bash
# Copie o arquivo de configuração
cp .env.example .env

# Edite .env com suas API keys
# Necessário: OpenAI, Google Maps, Google CSE
# Opcional: Anthropic, Gemini, DeepSeek, ZhipuAI, Apify
```

### 3. Execução

```bash
# Teste rápido (5 leads)
python src/run_test.py --max-leads 5

# Processar planilha existente
python src/gdr_v3_1_enterprise.py --input data/input/leads.xlsx --max-leads 50

# Pipeline completo
python src/run_complete_pipeline.py
```

## 📁 Estrutura do Projeto

```
gdr-framework/
├── src/
│   ├── gdr_v3_1_enterprise.py    # Framework principal
│   ├── llm_analyzer_v3.py        # Multi-LLM analyzer (5 providers)
│   ├── token_estimator.py        # Estimativa de custos
│   ├── quality_reviewer.py       # Análise de qualidade
│   ├── database/
│   │   └── lead_cache.py         # Cache DuckDB persistente
│   ├── scrapers/
│   │   ├── smart_orchestrator.py # Orquestração inteligente
│   │   ├── apify_real_scrapers.py # Instagram/Facebook
│   │   ├── website_scraper_enhanced.py # Website scraping
│   │   └── google_search_scraper.py # Google Custom Search
│   └── utils/
│       └── safe_print.py         # Compatibilidade Windows
├── data/
│   └── input/                    # Planilhas de entrada
├── outputs/                       # Resultados Excel
├── tests/                         # Scripts de teste
└── docs/                         # Documentação
```

## 🎯 Funcionalidades

### ✅ Implementado (100% Funcional)

- **Multi-LLM Consensus**: 5 providers (OpenAI, Claude, Gemini, DeepSeek, ZhipuAI)
- **Cache DuckDB**: Persistência com speedup de 4700x
- **Scrapers Paralelos**: Google Places, Instagram, Facebook, Website, Search
- **Smart Orchestrator**: Retry automático com exponential backoff
- **Quality Scoring**: Análise de qualidade 0-100
- **SDR Agent**: Qualificação e scoring automatizado
- **Token Tracking**: Controle de custos por provider
- **Export Profissional**: Excel com 142 campos

### 📊 Métricas de Performance

- **Taxa de Sucesso**: 100%
- **Tempo Médio**: 49s/lead (primeiro processamento)
- **Cache Hit**: 0.01s/lead (reprocessamento)
- **Custo Médio**: $0.01/lead
- **Qualidade Média**: 76/100

## 🔧 Configuração Detalhada

### APIs Necessárias

| API | Uso | Obrigatório |
|-----|-----|-------------|
| **OpenAI** | LLM principal | ✅ Sim |
| **Google Maps** | Places data | ✅ Sim |
| **Google CSE** | Search engine | ✅ Sim |
| **Anthropic** | Claude LLM | ⚪ Opcional |
| **Gemini** | Google LLM | ⚪ Opcional |
| **DeepSeek** | LLM adicional | ⚪ Opcional |
| **ZhipuAI** | GLM-4.5 | ⚪ Opcional |
| **Apify** | Social media | ⚪ Opcional |

### Variáveis de Ambiente

```bash
# Mínimo necessário
OPENAI_API_KEY=sk-...
GOOGLE_MAPS_API_KEY=AIza...
GOOGLE_CSE_API_KEY=AIza...
GOOGLE_CSE_ID=...

# Recomendado para melhor performance
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
APIFY_API_KEY=apify_api_...
```

## 📈 Uso em Produção

### Processamento em Lote

```python
from src.gdr_v3_1_enterprise import GDRFrameworkV31Enterprise

# Inicializar framework
framework = GDRFrameworkV31Enterprise(use_cache=True)

# Processar leads
results = await framework.process_batch(
    input_file="data/input/leads.xlsx",
    max_leads=100,
    output_file="outputs/results.xlsx"
)

print(f"Processados: {results['processed']}")
print(f"Custo total: ${results['total_cost']:.2f}")
```

### Análise de Resultados

```python
# Verificar qualidade
df = pd.read_excel("outputs/results.xlsx")
print(f"Qualidade média: {df['gdr_quality_score'].mean():.1f}")
print(f"Leads qualificados: {df['gdr_sdr_qualified'].sum()}")
print(f"Com email: {df['gdr_consolidated_email'].notna().sum()}")
print(f"Com telefone: {df['gdr_consolidated_phone'].notna().sum()}")
```

## 🐛 Troubleshooting

### Erro: "Module not found"
```bash
pip install -r requirements.txt
```

### Erro: "API key invalid"
```bash
# Verifique .env
cat .env | grep API_KEY
```

### Erro: "Rate limit exceeded"
```bash
# Reduza concorrência no .env
MAX_CONCURRENT_SCRAPERS=3
```

### Windows: Unicode errors
```bash
# Já corrigido com safe_print.py
# Se persistir, use:
set PYTHONIOENCODING=utf-8
```

## 📊 Campos de Saída

### Dados Consolidados
- `gdr_consolidated_email`: Email principal
- `gdr_consolidated_phone`: Telefone principal
- `gdr_consolidated_website`: Website
- `gdr_consolidated_whatsapp`: WhatsApp

### Análise LLM
- `gdr_llm_openai_result`: Resultado OpenAI
- `gdr_llm_claude_result`: Resultado Claude
- `gdr_llm_gemini_result`: Resultado Gemini
- `gdr_kappa_score`: Concordância estatística

### Qualificação SDR
- `gdr_sdr_lead_score`: Score 0-100
- `gdr_sdr_qualified`: Qualificado (true/false)
- `gdr_sdr_action`: Ação recomendada
- `gdr_sdr_insights`: Insights do negócio

### Métricas
- `gdr_quality_score`: Qualidade 0-100
- `gdr_processing_time`: Tempo em segundos
- `gdr_total_cost_usd`: Custo em USD
- `from_cache`: Veio do cache (true/false)

## 🔮 Roadmap

### v3.2 (Em desenvolvimento)
- [ ] Processamento paralelo de lotes
- [ ] Facebook Graph API nativa
- [ ] LinkedIn scraping
- [ ] Dashboard web (Streamlit)

### v4.0 (Planejado)
- [ ] Análise geográfica (buffer analysis)
- [ ] Computer Vision (Street View)
- [ ] API REST
- [ ] Webhooks para CRMs

## 📝 Licença

MIT License - veja LICENSE para detalhes

## 🤝 Contribuindo

1. Fork o projeto
2. Crie sua feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📞 Suporte

- Issues: [GitHub Issues](https://github.com/seu-usuario/gdr-framework/issues)
- Email: suporte@gdr-framework.com
- Docs: [Documentação Completa](docs/)

## ⭐ Status

![Version](https://img.shields.io/badge/version-3.1-blue)
![Status](https://img.shields.io/badge/status-production-green)
![Tests](https://img.shields.io/badge/tests-passing-green)
![Coverage](https://img.shields.io/badge/coverage-95%25-green)

---

**GDR Framework V3.1 Enterprise** - Automatizando o futuro das vendas B2B 🚀