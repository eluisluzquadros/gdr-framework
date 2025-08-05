# PRD - Framework GDR (Generative Development Representative)

## 1. Visão Geral

### 1.1 Objetivo
Desenvolver um agente de IA autônomo que funciona como um representante de desenvolvimento de vendas/negócios (SDR/BDR) generativo, automatizando a coleta, enriquecimento, qualificação e preparação de leads para equipes comerciais através de inteligência artificial multi-LLM.

### 1.2 Escopo
O sistema GDR (Generative Development Representative) atua como um SDR/BDR agentic que processa planilhas de leads básicos e entrega prospects qualificados e enriquecidos, com dados de contato validados, perfis comportamentais e recomendações de abordagem comercial.

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

#### 2.1.5 Módulo de Qualificação e Scoring
- **Agente SDR/BDR Generativo**: Análise de fit comercial e potencial de conversão
- **Scoring Engine**: Pontuação de leads baseada em múltiplos critérios
- **Output**: Leads qualificados com recomendações de abordagem comercial

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

### 3.4 Etapa 4: Análise de Consenso Estatística Kappa
```
Resultados Multi-LLM → Análise Kappa Pairwise → Score de Concordância Geral → Flags de Qualidade
```

**Processo Detalhado de Análise Kappa:**
1. **Matriz de Concordância**: Comparação pairwise entre os 5 LLMs (10 combinações)
2. **Cálculo Kappa por Campo**: Email, telefone, WhatsApp, website individualmente
3. **Kappa Geral**: Score consolidado de todo o dataset
4. **Interpretação Estatística**: 
   - Kappa < 0.20: Poor agreement
   - Kappa 0.21-0.40: Fair agreement  
   - Kappa 0.41-0.60: Moderate agreement
   - Kappa 0.61-0.80: Good agreement
   - Kappa 0.81-1.00: Very good agreement
5. **Flags Automáticos**: Identificação de leads para revisão manual
6. **Ranking de LLMs**: Ordenação por confiabilidade baseada em concordância

### 3.5 Etapa 5: Qualificação e Scoring SDR/BDR
```
Dados Consolidados → Agente SDR/BDR Generativo → Leads Qualificados + Score + Estratégia de Abordagem
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

### 4.3 Variáveis de Consenso e Qualificação SDR/BDR
```
Dados Consolidados:
- gdr_concenso_url, gdr_concenso_email, gdr_concenso_telefone, gdr_concenso_whatsapp
- gdr_concenso_total_campos_originais, gdr_concenso_total_campos_enriquecidos
- gdr_concenso_novos_campos_adicionados

Qualificação SDR/BDR:
- gdr_lead_score (0-100)
- gdr_lead_fit_categoria (Hot/Warm/Cold)
- gdr_lead_priority_rank (1-5)
- gdr_recommended_approach (Email/Phone/Social/Multi-touch)
- gdr_best_contact_time (horário sugerido)
- gdr_lead_stage (Prospect/MQL/SQL)
- gdr_concenso_synergy_score_categoria
- gdr_concenso_synergy_score_justificativa
- gdr_personalization_insights (insights para personalização)
- gdr_pain_points_identified (dores identificadas)
- gdr_next_action_recommended (próxima ação sugerida)
```

### 4.4 Variáveis de Análise Estatística Kappa
```
Métricas de Concordância Geral:
- gdr_kappa_overall_score (0-1, concordância geral entre todos os LLMs)
- gdr_kappa_interpretation (Poor/Fair/Moderate/Good/Very Good/Perfect)
- gdr_kappa_confidence_interval (intervalo de confiança 95%)
- gdr_kappa_p_value (significância estatística)

Concordância por Campo de Contato:
- gdr_kappa_email_score (concordância específica para email)
- gdr_kappa_telefone_score (concordância específica para telefone)
- gdr_kappa_whatsapp_score (concordância específica para WhatsApp)
- gdr_kappa_website_score (concordância específica para website)

Concordância por LLM (Pairwise):
- gdr_kappa_openai_claude_score
- gdr_kappa_openai_gemini_score
- gdr_kappa_openai_deepseek_score
- gdr_kappa_openai_zipouai_score
- gdr_kappa_claude_gemini_score
- gdr_kappa_claude_deepseek_score
- gdr_kappa_claude_zipouai_score
- gdr_kappa_gemini_deepseek_score
- gdr_kappa_gemini_zipouai_score
- gdr_kappa_deepseek_zipouai_score

Métricas de Qualidade do Consenso:
- gdr_kappa_total_agreements (total de concordâncias)
- gdr_kappa_total_disagreements (total de discordâncias)
- gdr_kappa_fields_high_agreement (campos com Kappa > 0.8)
- gdr_kappa_fields_low_agreement (campos com Kappa < 0.4)
- gdr_kappa_most_reliable_llm (LLM com maior concordância média)
- gdr_kappa_least_reliable_llm (LLM com menor concordância média)

Flags de Qualidade:
- gdr_kappa_high_confidence_flag (TRUE se Kappa geral > 0.7)
- gdr_kappa_review_required_flag (TRUE se Kappa geral < 0.4)
- gdr_kappa_partial_consensus_flag (TRUE se concordância parcial)
- gdr_kappa_outlier_detection_flag (TRUE se LLM com resultado muito divergente)

Métricas de Confiabilidade por Fonte:
- gdr_kappa_scraper_reliability_score (confiabilidade dos dados coletados)
- gdr_kappa_cross_validation_score (validação cruzada entre fontes)
- gdr_kappa_data_consistency_score (consistência interna dos dados)
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

### 5.4 RF04 - Análise de Consenso Estatística Kappa
- Deve calcular estatística Kappa entre todos os pares de LLMs
- Deve gerar score de concordância geral (overall Kappa)
- Deve identificar campos com alta/baixa concordância
- Deve calcular intervalos de confiança e significância estatística
- Deve flaggar leads que necessitam revisão manual (Kappa < 0.4)
- Deve ranquear LLMs por confiabilidade
- Deve detectar outliers e resultados divergentes
- Deve gerar métricas de validação cruzada entre fontes de dados

### 5.5 RF05 - Qualificação e Scoring SDR/BDR
- Deve implementar agente SDR/BDR generativo para qualificação
- Deve aplicar scoring baseado em múltiplos critérios comerciais
- Deve gerar insights de personalização e estratégias de abordagem
- Deve identificar pain points e oportunidades de negócio
- Deve recomendar próximas ações e timing de contato

### 5.6 RF06 - Integração com CRM e Sales Tools
- Deve exportar leads qualificados para CRMs populares
- Deve gerar templates de outreach personalizados
- Deve criar sequências de follow-up automatizadas
- Deve integrar com ferramentas de sales engagement

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

### 7.2 Formatos de Saída para Equipes de Vendas
- Excel (.xlsx) com leads qualificados e scores
- CRM-ready CSV com campos mapeados
- JSON para integrações automáticas
- Templates de outreach personalizados
- Relatórios de insights por lead/batch
- API REST para consulta e integração com sales tools

## 8. Monitoramento e Métricas SDR/BDR

### 8.1 KPIs Operacionais
- Taxa de sucesso por scraper
- Tempo médio de processamento por lead
- Taxa de consenso entre LLMs
- Qualidade dos dados enriquecidos

### 8.2 KPIs de Performance SDR/BDR
- Lead Score médio por batch
- Taxa de qualificação (MQL/SQL)
- Precisão do scoring (conversion rate)
- Tempo médio para first contact
- Taxa de resposta de outreach personalizado

### 8.3 Métricas de Análise Estatística Kappa
- **Kappa Score Médio**: Concordância média entre LLMs por batch
- **Taxa de Alto Consenso**: % de leads com Kappa > 0.7
- **Taxa de Baixo Consenso**: % de leads com Kappa < 0.4 (necessitam revisão)
- **Confiabilidade por LLM**: Ranking de performance individual
- **Consistência Cross-Source**: Validação entre diferentes scrapers
- **Tempo de Convergência**: Rapidez para alcançar consenso estatístico

### 8.4 Métricas de Qualidade Comercial
- Synergy Score por categoria de negócio
- Campos novos adicionados por lead
- Taxa de validação de contatos
- Precisão dos insights de personalização
- Efetividade das recomendações de abordagem

## 9. Roadmap e Fases

### 9.1 Fase 1 - MVP (2 meses)
- Scrapers básicos funcionais
- Consolidação com 3 LLMs
- Interface de upload/download

### 9.2 Fase 2 - Otimização (1 mês)
- Implementação de todas as 5 LLMs
- **Análise de consenso Kappa completa** com todas as variáveis estatísticas
- **Sistema de flags automáticos** baseado em scores Kappa
- **Ranking dinâmico de LLMs** por confiabilidade
- Dashboard de monitoramento com métricas Kappa

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

### 10.3 Riscos de Análise Estatística
- **Baixa concordância Kappa**: Implementar revisão manual automática para Kappa < 0.4
- **Viés de LLM específico**: Rotação e balanceamento de pesos entre modelos
- **Falsos consensos**: Validação cruzada com dados externos
- **Outliers não detectados**: Algoritmos de detecção de anomalias complementares

## 11. Critérios de Aceite SDR/BDR

### 11.1 Funcionais
- ✅ Processar planilha de input com 100% dos campos mapeados
- ✅ Coletar dados de todas as fontes configuradas
- ✅ Consolidar com consenso > 70% entre LLMs
- ✅ Gerar lead scores para 100% dos prospects
- ✅ Produzir insights de personalização para > 80% dos leads

### 11.2 Qualidade SDR/BDR
- ✅ Taxa de erro < 2%
- ✅ Tempo de processamento < 30s por lead
- ✅ Cobertura de dados > 85%
- ✅ Validação de contatos > 90%
- ✅ Precisão do scoring > 75% (baseado em conversions)
- ✅ Taxa de resposta de outreach personalizado > 15%

### 11.3 Qualidade Estatística Kappa
- ✅ Kappa Score médio > 0.6 (Good agreement)
- ✅ Taxa de alto consenso (Kappa > 0.7) > 80%
- ✅ Taxa de baixo consenso (Kappa < 0.4) < 10%
- ✅ Intervalos de confiança com 95% de significância
- ✅ Detecção automática de outliers em 100% dos casos
- ✅ Confiabilidade cross-source > 0.7

### 11.4 Performance Comercial
- ✅ Lead Score médio > 60/100
- ✅ Taxa de qualificação MQL > 25%
- ✅ Redução de 50% no tempo de pesquisa manual
- ✅ Aumento de 30% na taxa de resposta vs. métodos tradicionais

---

**Versão**: 1.0  
**Data**: Agosto 2025  
**Responsável**: Equipe GDR (Generative Development Representative)  
**Stakeholders**: Sales Development, Business Development, Revenue Operations