# PRD - Framework de Enriquecimento de Dados de Leads (GDR)

## 1. Visão Geral

### 1.1 Objetivo
Desenvolver um framework automatizado para coleta, enriquecimento e consolidação de dados de contato de leads empresariais, utilizando múltiplas fontes de dados e inteligência artificial para garantir precisão e completude das informações.

### 1.2 Escopo
O sistema GDR (Gestão de Dados e Relacionamento) processará planilhas de leads básicos e retornará dados enriquecidos com informações de contato validadas e consolidadas através de consenso multi-LLM.

## 2. Arquitetura do Sistema

### 2.1 Componentes Principais

#### 2.1.1 Módulo de Input
- **Entrada**: Planilha Excel (.xlsx) com dados básicos dos leads
- **Formato**: `base-lead_amostra_v2.xlsx`
- **Dados mínimos**: ID, nome, endereço, telefone básico

#### 2.1.2 Módulo de Scrapers
- **Google Places Scraper**: Validação e enriquecimento via Google Places API
- **Apify Social Media Scrapers**: Instagram, Facebook, Linktree
- **Website Scraper (cwral4ai)**: Extração de dados de websites corporativos
- **Google Search Engine Scraper**: Busca complementar via mecanismos de pesquisa

#### 2.1.3 Módulo de Consolidação Multi-LLM
- **LLMs Suportadas**: OpenAI, Claude, Gemini, DeepSeek, ZipouAI
- **Função**: Análise e consolidação de dados coletados

#### 2.1.4 Módulo de Consenso
- **Algoritmo**: Estatística Kappa para análise de concordância
- **Objetivo**: Validação da consistência entre diferentes LLMs

#### 2.1.5 Módulo de Revisão Final
- **Agente AI Especializado**: Revisão e validação dos dados consolidados
- **Output**: Dataset final enriquecido e validado

## 3. Fluxo de Dados

### 3.1 Etapa 1: Processamento Inicial
```
Input Planilha → Verificação Google Places Data → Identificação de Canais Digitais
```

### 3.2 Etapa 2: Coleta Paralela
```
┌─ Google Places Scraper
├─ Apify Instagram Scraper
├─ Apify Facebook Scraper  
├─ Apify Linktree Scraper
├─ Website Scraper (cwral4ai)
└─ Google Search Engine Scraper
```

### 3.3 Etapa 3: Consolidação Multi-LLM
```
Dados Coletados → [OpenAI + Claude + Gemini + DeepSeek + ZipouAI] → Dados Consolidados
```

### 3.4 Etapa 4: Análise de Consenso
```
Resultados Multi-LLM → Estatística Kappa → Score de Concordância
```

### 3.5 Etapa 5: Revisão Final
```
Dados Consolidados → Agente AI Revisor → Dataset Final Validado
```

## 4. Especificações Técnicas

### 4.1 Variáveis de Input (Planilha Original)
```
- original_id (legalDocument)
- original_nome (name)
- original_endereco_completo (endereço completo)
- original_telefone (phone)
- original_telefone_place (placesPhone)
- original_website (website)
- original_avaliacao_google (placesRating)
- original_latitude (placesLat)
- original_longitude (placesLng)
- original_place_users (placesUserRatingsTotal)
- original_place_website (placesWebsite)
- original_email (email)
```

### 4.2 Variáveis Coletadas por Scrapers

#### 4.2.1 Redes Sociais (Apify)
```
Facebook:
- gdr_facebook_url, gdr_facebook_mail, gdr_facebook_whatsapp
- gdr_facebook_id, gdr_facebook_username, gdr_facebook_followers
- gdr_facebook_likes, gdr_facebook_category, gdr_facebook_bio
- gdr_facebook_is_verified

Instagram:
- gdr_instagram_url, gdr_instagram_id, gdr_instagram_username
- gdr_instagram_followers, gdr_instagram_following, gdr_instagram_bio
- gdr_instagram_is_verified, gdr_instagram_is_business

Linktree:
- gdr_linktree_username, gdr_linktree_title, gdr_linktree_description
- gdr_linktree_social_urls, gdr_linktree_links_details

LinkedIn:
- gdr_linkedin_url
```

#### 4.2.2 Website Scraper (cwral4ai)
```
- gdr_cwral4ai_url, gdr_cwral4ai_email, gdr_cwral4ai_telefone
- gdr_cwral4ai_whatsapp, gdr_cwral4ai_youtube_url
```

#### 4.2.3 Google Search Engine
```
- gdr_google_search_engine_url, gdr_google_search_engine_email
- gdr_google_search_engine_telefone, gdr_google_search_engine_whatsapp
- gdr_google_search_engine_youtube_url
```

### 4.3 Variáveis de Consenso Final
```
- gdr_concenso_url
- gdr_concenso_email
- gdr_concenso_telefone
- gdr_concenso_whatsapp
- gdr_concenso_total_campos_originais
- gdr_concenso_total_campos_enriquecidos
- gdr_concenso_novos_campos_adicionados
- gdr_concenso_synergy_score_categoria
- gdr_concenso_synergy_score_justificativa
```

## 5. Requisitos Funcionais

### 5.1 RF01 - Processamento de Planilhas
- O sistema deve aceitar planilhas Excel (.xlsx) como input
- Deve validar a estrutura e campos obrigatórios
- Deve processar múltiplos leads em lote

### 5.2 RF02 - Coleta de Dados Multi-Fonte
- Deve executar scrapers em paralelo para otimizar tempo
- Deve implementar retry logic para falhas temporárias
- Deve respeitar rate limits das APIs/sites

### 5.3 RF03 - Consolidação Multi-LLM
- Deve distribuir dados para 5 LLMs diferentes
- Deve coletar e comparar respostas
- Deve implementar fallback para LLMs indisponíveis

### 5.4 RF04 - Análise de Consenso
- Deve calcular estatística Kappa entre LLMs
- Deve identificar discrepâncias significativas
- Deve priorizar dados com maior concordância

### 5.5 RF05 - Revisão Final
- Deve implementar agente AI para revisão
- Deve aplicar regras de validação de dados
- Deve gerar relatório de qualidade dos dados

## 6. Requisitos Não-Funcionais

### 6.1 Performance
- Processar até 1000 leads por hora
- Tempo máximo de 30 segundos por lead
- Paralelização de até 10 scrapers simultâneos

### 6.2 Confiabilidade
- Disponibilidade de 99.5%
- Taxa de erro inferior a 2%
- Backup automático de dados processados

### 6.3 Escalabilidade
- Suporte a crescimento horizontal
- Queue system para processamento em lote
- Load balancing entre scrapers

### 6.4 Segurança
- Proteção de dados pessoais (LGPD/GDPR)
- Logs de auditoria completos
- Criptografia de dados sensíveis

## 7. APIs e Integrações

### 7.1 APIs Externas
- Google Places API
- Apify Platform APIs
- OpenAI API
- Claude API (Anthropic)
- Google Gemini API
- DeepSeek API
- ZipouAI API

### 7.2 Formatos de Saída
- Excel (.xlsx) enriquecido
- JSON estruturado
- CSV para integração
- API REST para consulta

## 8. Monitoramento e Métricas

### 8.1 KPIs Operacionais
- Taxa de sucesso por scraper
- Tempo médio de processamento
- Taxa de consenso entre LLMs
- Qualidade dos dados enriquecidos

### 8.2 Métricas de Qualidade
- Synergy Score por categoria
- Campos novos adicionados por lead
- Taxa de validação de contatos
- Precisão dos dados coletados

## 9. Roadmap e Fases

### 9.1 Fase 1 - MVP (2 meses)
- Scrapers básicos funcionais
- Consolidação com 3 LLMs
- Interface de upload/download

### 9.2 Fase 2 - Otimização (1 mês)
- Implementação de todas as 5 LLMs
- Análise de consenso avançada
- Dashboard de monitoramento

### 9.3 Fase 3 - Escala (1 mês)
- API REST completa
- Processamento em tempo real
- Integração com CRMs

## 10. Riscos e Mitigações

### 10.1 Riscos Técnicos
- **Bloqueio de scrapers**: Implementar rotação de IPs e user agents
- **Falha de LLMs**: Sistema de fallback e cache de respostas
- **Rate limiting**: Queue inteligente com throttling

### 10.2 Riscos de Negócio
- **Qualidade dos dados**: Validação múltipla e scoring de confiança
- **Compliance**: Auditoria regular e políticas de retenção
- **Custos de API**: Otimização de chamadas e caching

## 11. Critérios de Aceite

### 11.1 Funcionais
- ✅ Processar planilha de input com 100% dos campos mapeados
- ✅ Coletar dados de todas as fontes configuradas
- ✅ Consolidar com consenso > 70% entre LLMs
- ✅ Gerar output com synergy score > 0.8

### 11.2 Qualidade
- ✅ Taxa de erro < 2%
- ✅ Tempo de processamento < 30s por lead
- ✅ Cobertura de dados > 85%
- ✅ Validação de contatos > 90%

---

**Versão**: 1.0  
**Data**: Agosto 2025  
**Responsável**: Equipe GDR