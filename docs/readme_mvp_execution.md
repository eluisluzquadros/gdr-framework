# GDR MVP - Execução Completa

## 🚀 Quick Start

### 1. Setup do Ambiente

```bash
# Criar diretório do projeto
mkdir gdr-mvp
cd gdr-mvp

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configuração das APIs

Copie o arquivo `.env` e suas chaves de API estão prontas:

```bash
# As chaves já estão configuradas no .env
# Google APIs, OpenAI, Anthropic, etc.
```

### 3. Execução Simples

```bash
# Processar os primeiros 10 leads (teste rápido)
python run_gdr.py -m 10

# Processar 50 leads (recomendado para demo)
python run_gdr.py -m 50

# Processar arquivo específico
python run_gdr.py -i minha_planilha.xlsx -m 25
```

### 4. Resultados

O sistema gerará:
- `outputs/gdr_results_YYYYMMDD_HHMMSS.xlsx` com 4 abas:
  - **Dados Consolidados**: Resultados principais
  - **Dados Completos**: Todos os dados coletados
  - **Estatísticas**: Métricas de performance
  - **Custos de Tokens**: Detalhamento de custos por LLM

## 📊 Estrutura da Planilha de Entrada

Sua planilha `leads.xlsx` tem **1000 leads** do setor de celulares/acessórios com:

| Campo | Descrição | Exemplo |
|-------|-----------|---------|
| `id` | ID único | 721 |
| `name` | Nome do negócio | "My Case Store" |
| `email` | Email (se disponível) | null ou email@domain.com |
| `phone` | Telefone | null ou (51)99655-3221 |
| `website` | Website | "https://instagram.com/mycasest" |
| `placesId` | Google Places ID | "ChIJCwvP4kCjHJURrFIVdxXwjTc" |
| `placesRating` | Avaliação Google | 4.1 |
| `city` | Cidade | "Santa Cruz do Sul" |
| `state` | Estado | "RS" |
| `businessTarget` | Tipo de negócio | "Especialista Loja" |

## 🔄 Processamento Completo

### O que o GDR faz com cada lead:

1. **📥 Input Processing**
   - Carrega dados da planilha
   - Valida campos obrigatórios
   - Normaliza formatos

2. **🕷️ Data Collection** (Multi-Source)
   - **Website Scraping**: Extrai emails, telefones, WhatsApp
   - **Google Search**: Busca informações adicionais
   - **Instagram**: Processa perfis sociais (simulado)
   - **Rate Limiting**: Respeita limites das APIs

3. **🧠 Multi-LLM Analysis** 
   - **OpenAI GPT-4**: Consolidação inteligente
   - **Token Tracking**: Monitora uso e custos
   - **Error Handling**: Fallback robusto

4. **📊 Consensus & Statistics**
   - **Data Consolidation**: Melhor email, telefone, etc.
   - **Quality Scoring**: Score 0-1 de qualidade
   - **Kappa Analysis**: Estatísticas de concordância
   - **Business Insights**: Análise do negócio

5. **📈 Export & Reporting**
   - **Excel Profissional**: Múltiplas abas
   - **Cost Analysis**: Detalhamento de custos
   - **Statistics Dashboard**: Métricas de performance

## 💰 Controle de Custos

### Estimativas por Lead:
- **OpenAI GPT-4**: ~$0.001-0.003 por lead
- **Google Search**: Gratuito (100 queries/dia)
- **Website Scraping**: Gratuito
- **Processamento**: ~30-60 segundos por lead

### Custos Totais Esperados:
```
10 leads  = ~$0.01-0.03 USD
50 leads  = ~$0.05-0.15 USD  
100 leads = ~$0.10-0.30 USD
```

## 📋 Comandos Úteis

### Validação Sem Processamento
```bash
python run_gdr.py --validate-only
```

### Processamento Customizado
```bash
# Arquivo específico + diretório de saída
python run_gdr.py -i leads.xlsx -o resultados -m 30

# Processar apenas 5 leads para teste
python run_gdr.py -m 5
```

### Logs Detalhados
```bash
# Os logs são salvos em:
# - gdr_processing.log (arquivo)
# - Console (tempo real)
```

## 📊 Exemplo de Resultados

### Dados Consolidados (Principais):
| id | name | business_target | gdr_consolidated_email | gdr_consolidated_phone | gdr_quality_score |
|----|------|----------------|----------------------|----------------------|------------------|
| 721 | My Case Store | Especialista Loja | contato@mycasestore.com | (51)99655-3221 | 0.85 |
| 723 | SOS Celulares | Assistencia Tecnica | sos@celulares.com.br | (51)3056-3003 | 0.92 |

### Estatísticas de Performance:
- **Taxa de Sucesso**: 95%+
- **Cobertura Email**: 70%+  
- **Cobertura Telefone**: 85%+
- **Score Médio Qualidade**: 0.75+

### Custos por Batch:
- **Total Tokens**: 150,000
- **Custo Total**: $0.12 USD
- **Custo/Lead**: $0.002 USD

## 🎯 Casos de Uso

### 1. Validação de Dados
- Conferir telefones e emails existentes
- Identificar dados faltantes
- Priorizar leads por qualidade

### 2. Enriquecimento
- Encontrar contatos adicionais
- Mapear presença digital
- Extrair insights de negócio

### 3. Qualificação
- Scoring automático de leads
- Identificar leads premium
- Análise de potencial comercial

### 4. Relatórios Executivos
- Dashboards de performance
- Análise de ROI por região
- Benchmarking de qualidade

## ⚠️ Limitações do MVP

### APIs Simuladas:
- **Apify Social Media**: Simulado (usar Apify real em produção)
- **Multiple LLMs**: Apenas OpenAI (expandir para Claude, Gemini, etc.)
- **Street View**: Não implementado (Etapa 2)

### Rate Limits:
- **Google Search**: 100 queries/dia (grátis)
- **OpenAI**: Conforme seu plano
- **Websites**: 1 request/segundo

## 🚀 Próximos Passos

### Etapa 2 - Análise Geográfica:
- Computer Vision (Street View)
- Buffer analysis (concorrentes 500m)
- Análise de tráfego local
- Insights qualitativos avançados

### Etapa 3 - Platform Features:
- Dashboard web interativo
- API REST para integrações
- Multi-tenancy
- Automação de outreach

## 📞 Suporte

### Problemas Comuns:

**1. "API Key inválida"**
```bash
# Verificar arquivo .env
# Testar conectividade:
python run_gdr.py --validate-only
```

**2. "Arquivo não encontrado"**
```bash
# Certificar que leads.xlsx está no diretório
ls -la leads.xlsx
```

**3. "Rate limit exceeded"**
```bash
# Reduzir concorrência ou aguardar
python run_gdr.py -m 10  # Processar menos leads
```

### Logs de Debug:
```bash
# Verificar logs detalhados
tail -f gdr_processing.log
```

---

**🎉 MVP Pronto para Demonstração!**

Este MVP processa dados reais da sua planilha de 1000 leads, demonstrando o valor completo do framework GDR em ação.