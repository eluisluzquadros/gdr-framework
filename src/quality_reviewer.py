#!/usr/bin/env python3
"""
Quality Reviewer Agent - Sistema de revisão e análise de qualidade
Analisa dados coletados, identifica problemas e sugere melhorias
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class QualityMetric:
    """Métrica de qualidade"""
    name: str
    score: float  # 0-100
    weight: float = 1.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class QualityReport:
    """Relatório de qualidade"""
    overall_score: float
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    enrichment_score: float
    metrics: List[QualityMetric]
    issues: List[str]
    suggestions: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'overall_score': self.overall_score,
            'completeness_score': self.completeness_score,
            'accuracy_score': self.accuracy_score,
            'consistency_score': self.consistency_score,
            'enrichment_score': self.enrichment_score,
            'metrics': [
                {
                    'name': m.name,
                    'score': m.score,
                    'weight': m.weight,
                    'issues': m.issues,
                    'suggestions': m.suggestions
                }
                for m in self.metrics
            ],
            'issues': self.issues,
            'suggestions': self.suggestions,
            'timestamp': self.timestamp.isoformat()
        }


class QualityReviewer:
    """
    Agente de revisão de qualidade para dados coletados
    """
    
    def __init__(self):
        """Inicializa o revisor"""
        
        # Campos críticos (peso maior)
        self.critical_fields = {
            'gdr_concenso_email': 3.0,
            'gdr_concenso_telefone': 3.0,
            'gdr_concenso_whatsapp': 2.5,
            'gdr_concenso_url': 2.0,
            'gdr_instagram_username': 2.0,
            'gdr_facebook_url': 1.5,
            'original_nome': 3.0,
            'original_cnpj': 2.0
        }
        
        # Campos importantes
        self.important_fields = {
            'gdr_instagram_followers': 1.0,
            'gdr_instagram_bio': 1.0,
            'gdr_facebook_category': 1.0,
            'gdr_google_places_rating': 1.0,
            'gdr_google_places_user_ratings_total': 1.0,
            'gdr_linktree_url': 0.8,
            'gdr_linkedin_url': 0.8
        }
        
        # Campos opcionais
        self.optional_fields = {
            'gdr_cwral4ai_youtube_url': 0.5,
            'gdr_facebook_likes': 0.5,
            'gdr_instagram_is_verified': 0.3
        }
        
        # Padrões de validação
        self.validation_patterns = {
            'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'phone': r'^\+?[\d\s\-\(\)]+$',
            'url': r'^https?://[^\s]+$',
            'cnpj': r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$|^\d{14}$',
            'instagram': r'^[a-zA-Z0-9._]+$',
            'number': r'^\d+$'
        }
        
        # Thresholds de qualidade
        self.thresholds = {
            'excellent': 90,
            'good': 75,
            'fair': 60,
            'poor': 40,
            'critical': 20
        }
    
    def review_lead(self, lead_data: Dict) -> QualityReport:
        """
        Revisa qualidade de um lead
        
        Args:
            lead_data: Dados do lead para revisar
            
        Returns:
            QualityReport com análise completa
        """
        metrics = []
        all_issues = []
        all_suggestions = []
        
        # 1. Completude
        completeness = self._assess_completeness(lead_data)
        metrics.append(completeness)
        all_issues.extend(completeness.issues)
        all_suggestions.extend(completeness.suggestions)
        
        # 2. Acurácia
        accuracy = self._assess_accuracy(lead_data)
        metrics.append(accuracy)
        all_issues.extend(accuracy.issues)
        all_suggestions.extend(accuracy.suggestions)
        
        # 3. Consistência
        consistency = self._assess_consistency(lead_data)
        metrics.append(consistency)
        all_issues.extend(consistency.issues)
        all_suggestions.extend(consistency.suggestions)
        
        # 4. Enriquecimento
        enrichment = self._assess_enrichment(lead_data)
        metrics.append(enrichment)
        all_issues.extend(enrichment.issues)
        all_suggestions.extend(enrichment.suggestions)
        
        # 5. Scrapers
        scrapers = self._assess_scrapers(lead_data)
        metrics.append(scrapers)
        all_issues.extend(scrapers.issues)
        all_suggestions.extend(scrapers.suggestions)
        
        # 6. Análise LLM
        llm_analysis = self._assess_llm_analysis(lead_data)
        metrics.append(llm_analysis)
        all_issues.extend(llm_analysis.issues)
        all_suggestions.extend(llm_analysis.suggestions)
        
        # Calcular score geral
        total_weighted_score = sum(m.score * m.weight for m in metrics)
        total_weight = sum(m.weight for m in metrics)
        overall_score = total_weighted_score / total_weight if total_weight > 0 else 0
        
        # Criar relatório
        report = QualityReport(
            overall_score=round(overall_score, 2),
            completeness_score=completeness.score,
            accuracy_score=accuracy.score,
            consistency_score=consistency.score,
            enrichment_score=enrichment.score,
            metrics=metrics,
            issues=list(set(all_issues)),  # Remover duplicatas
            suggestions=list(set(all_suggestions))
        )
        
        # Adicionar sugestões baseadas no score geral
        report.suggestions.extend(self._generate_improvement_suggestions(report))
        
        return report
    
    def _assess_completeness(self, data: Dict) -> QualityMetric:
        """Avalia completude dos dados"""
        issues = []
        suggestions = []
        
        # Contar campos preenchidos
        total_fields = len(self.critical_fields) + len(self.important_fields) + len(self.optional_fields)
        filled_critical = 0
        filled_important = 0
        filled_optional = 0
        
        # Verificar campos críticos
        for field, weight in self.critical_fields.items():
            if field in data and data[field] and str(data[field]).strip():
                filled_critical += 1
            else:
                issues.append(f"Campo crítico ausente: {field}")
                if 'email' in field:
                    suggestions.append("Executar scraping de website para encontrar email")
                elif 'telefone' in field or 'whatsapp' in field:
                    suggestions.append("Verificar Google Places ou Instagram para contato")
        
        # Verificar campos importantes
        for field in self.important_fields:
            if field in data and data[field] and str(data[field]).strip():
                filled_important += 1
        
        # Verificar campos opcionais
        for field in self.optional_fields:
            if field in data and data[field] and str(data[field]).strip():
                filled_optional += 1
        
        # Calcular score ponderado
        critical_score = (filled_critical / len(self.critical_fields)) * 100 if self.critical_fields else 100
        important_score = (filled_important / len(self.important_fields)) * 100 if self.important_fields else 100
        optional_score = (filled_optional / len(self.optional_fields)) * 100 if self.optional_fields else 100
        
        # Score final com pesos
        score = (critical_score * 0.5) + (important_score * 0.3) + (optional_score * 0.2)
        
        # Adicionar sugestões baseadas no score
        if score < 60:
            suggestions.append("Considerar re-executar scrapers com retry automático")
            suggestions.append("Verificar se APIs estão configuradas corretamente")
        
        return QualityMetric(
            name="Completeness",
            score=round(score, 2),
            weight=2.0,
            issues=issues,
            suggestions=suggestions
        )
    
    def _assess_accuracy(self, data: Dict) -> QualityMetric:
        """Avalia acurácia dos dados"""
        issues = []
        suggestions = []
        score = 100.0
        
        # Validar email
        if data.get('gdr_concenso_email'):
            import re
            if not re.match(self.validation_patterns['email'], str(data['gdr_concenso_email'])):
                issues.append(f"Email inválido: {data['gdr_concenso_email']}")
                suggestions.append("Verificar formato do email coletado")
                score -= 10
        
        # Validar CNPJ
        if data.get('original_cnpj'):
            import re
            cnpj = str(data['original_cnpj']).strip()
            if not re.match(self.validation_patterns['cnpj'], cnpj):
                issues.append(f"CNPJ em formato incorreto: {cnpj}")
                suggestions.append("Formatar CNPJ para padrão XX.XXX.XXX/XXXX-XX")
                score -= 5
        
        # Validar URLs
        url_fields = ['gdr_concenso_url', 'gdr_instagram_url', 'gdr_facebook_url']
        for field in url_fields:
            if data.get(field):
                url = str(data[field])
                if url and not url.startswith('http'):
                    issues.append(f"URL sem protocolo: {field}")
                    suggestions.append(f"Adicionar https:// ao {field}")
                    score -= 3
        
        # Validar números
        if data.get('gdr_instagram_followers'):
            try:
                followers = int(data['gdr_instagram_followers'])
                if followers < 0:
                    issues.append("Número de seguidores negativo")
                    score -= 5
            except:
                issues.append("Número de seguidores não é numérico")
                score -= 5
        
        return QualityMetric(
            name="Accuracy",
            score=max(0, round(score, 2)),
            weight=1.5,
            issues=issues,
            suggestions=suggestions
        )
    
    def _assess_consistency(self, data: Dict) -> QualityMetric:
        """Avalia consistência dos dados"""
        issues = []
        suggestions = []
        score = 100.0
        
        # Verificar consistência entre fontes
        
        # Instagram username consistente
        ig_fields = ['gdr_instagram_username', 'gdr_instagram_id']
        ig_values = [data.get(f) for f in ig_fields if data.get(f)]
        if len(set(ig_values)) > 1:
            issues.append("Inconsistência nos dados do Instagram")
            score -= 10
        
        # Telefone/WhatsApp consistente
        if data.get('gdr_concenso_telefone') and data.get('gdr_concenso_whatsapp'):
            phone = ''.join(filter(str.isdigit, str(data['gdr_concenso_telefone'])))
            whats = ''.join(filter(str.isdigit, str(data['gdr_concenso_whatsapp'])))
            if phone and whats and phone != whats:
                if not whats.endswith(phone) and not phone.endswith(whats):
                    issues.append("Telefone e WhatsApp não correspondem")
                    suggestions.append("Verificar se telefone e WhatsApp são do mesmo número")
                    score -= 5
        
        # Nome consistente
        name_fields = ['original_nome', 'gdr_google_places_name']
        names = [data.get(f) for f in name_fields if data.get(f)]
        if len(names) > 1:
            # Verificar similaridade básica
            name1 = names[0].lower().replace(' ', '')
            name2 = names[1].lower().replace(' ', '')
            if name1[:5] != name2[:5]:  # Primeiros 5 caracteres diferentes
                issues.append("Nome inconsistente entre fontes")
                score -= 8
        
        return QualityMetric(
            name="Consistency",
            score=max(0, round(score, 2)),
            weight=1.0,
            issues=issues,
            suggestions=suggestions
        )
    
    def _assess_enrichment(self, data: Dict) -> QualityMetric:
        """Avalia nível de enriquecimento"""
        issues = []
        suggestions = []
        
        # Contar campos enriquecidos (não originais)
        enriched_fields = [k for k in data.keys() if k.startswith('gdr_')]
        original_fields = [k for k in data.keys() if k.startswith('original_')]
        
        enrichment_ratio = len(enriched_fields) / (len(original_fields) + 1)
        
        # Score baseado no ratio
        score = min(100, enrichment_ratio * 20)
        
        # Verificar enriquecimentos específicos
        if not data.get('gdr_instagram_username'):
            issues.append("Instagram não encontrado")
            suggestions.append("Buscar Instagram via Google Search")
            
        if not data.get('gdr_facebook_url'):
            issues.append("Facebook não encontrado")
            suggestions.append("Usar estratégias alternativas de busca do Facebook")
        
        if not data.get('gdr_linktree_detected'):
            if data.get('gdr_instagram_bio'):
                suggestions.append("Verificar bio do Instagram para Linktree")
        
        # Bonus por dados valiosos
        valuable_fields = [
            'gdr_concenso_email',
            'gdr_concenso_whatsapp',
            'gdr_instagram_followers',
            'gdr_google_places_rating'
        ]
        
        for field in valuable_fields:
            if data.get(field):
                score += 5
        
        return QualityMetric(
            name="Enrichment",
            score=min(100, round(score, 2)),
            weight=1.5,
            issues=issues,
            suggestions=suggestions
        )
    
    def _assess_scrapers(self, data: Dict) -> QualityMetric:
        """Avalia performance dos scrapers"""
        issues = []
        suggestions = []
        
        # Verificar quais scrapers retornaram dados
        scrapers_status = {
            'Instagram': bool(data.get('gdr_instagram_id')),
            'Facebook': bool(data.get('gdr_facebook_url')),
            'Website': bool(data.get('gdr_cwral4ai_email') or data.get('gdr_cwral4ai_telefone')),
            'Google Search': bool(data.get('gdr_google_search_engine_url')),
            'Google Places': bool(data.get('gdr_google_places_place_id')),
            'Linktree': bool(data.get('gdr_linktree_username'))
        }
        
        successful = sum(scrapers_status.values())
        total = len(scrapers_status)
        score = (successful / total) * 100
        
        # Identificar scrapers que falharam
        for scraper, success in scrapers_status.items():
            if not success:
                issues.append(f"{scraper} scraper não retornou dados")
                
                if scraper == 'Instagram':
                    suggestions.append("Verificar se Instagram URL está correto ou usar busca")
                elif scraper == 'Facebook':
                    suggestions.append("Ativar estratégias alternativas do Facebook scraper")
                elif scraper == 'Website':
                    suggestions.append("Verificar se website está acessível e tem dados de contato")
        
        return QualityMetric(
            name="Scrapers Performance",
            score=round(score, 2),
            weight=1.0,
            issues=issues,
            suggestions=suggestions
        )
    
    def _assess_llm_analysis(self, data: Dict) -> QualityMetric:
        """Avalia análises dos LLMs"""
        issues = []
        suggestions = []
        score = 100.0
        
        # Verificar se análises foram geradas
        llm_providers = ['openai', 'gemini', 'deepseek', 'claude', 'zhipuai']
        llm_fields_found = {}
        
        for provider in llm_providers:
            provider_fields = [k for k in data.keys() if f'llm_{provider}' in k]
            llm_fields_found[provider] = len(provider_fields)
            
            if provider_fields:
                # Verificar se tem conteúdo válido
                empty_fields = sum(1 for f in provider_fields if not data.get(f) or data[f] == 'Análise em processamento')
                if empty_fields > 5:
                    issues.append(f"LLM {provider} tem {empty_fields} análises vazias")
                    score -= 10
            else:
                issues.append(f"LLM {provider} não executou análises")
                suggestions.append(f"Verificar configuração da API key do {provider}")
                score -= 15
        
        # Verificar consenso
        if not data.get('gdr_concenso_synergy_score_categoria'):
            issues.append("Consenso entre LLMs não foi calculado")
            suggestions.append("Executar análise de consenso multi-LLM")
            score -= 20
        
        return QualityMetric(
            name="LLM Analysis",
            score=max(0, round(score, 2)),
            weight=0.8,
            issues=issues,
            suggestions=suggestions
        )
    
    def _generate_improvement_suggestions(self, report: QualityReport) -> List[str]:
        """Gera sugestões de melhoria baseadas no score geral"""
        suggestions = []
        
        if report.overall_score < self.thresholds['critical']:
            suggestions.append("⚠️ CRÍTICO: Re-executar processamento completo com todas as APIs")
            suggestions.append("Verificar conectividade e configuração de APIs")
            
        elif report.overall_score < self.thresholds['poor']:
            suggestions.append("Ativar retry automático para scrapers que falharam")
            suggestions.append("Considerar usar scrapers alternativos")
            
        elif report.overall_score < self.thresholds['fair']:
            suggestions.append("Executar scrapers de enriquecimento adicionais")
            suggestions.append("Verificar quality de dados de entrada")
            
        elif report.overall_score < self.thresholds['good']:
            suggestions.append("Otimizar configuração de scrapers")
            suggestions.append("Adicionar validação de dados")
            
        else:
            suggestions.append("✅ Qualidade excelente - manter configuração atual")
        
        return suggestions
    
    def review_batch(self, leads_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Revisa um batch de leads
        
        Args:
            leads_df: DataFrame com leads
            
        Returns:
            Dict com análise agregada
        """
        reports = []
        
        for idx, row in leads_df.iterrows():
            lead_data = row.to_dict()
            report = self.review_lead(lead_data)
            reports.append(report)
        
        # Agregar estatísticas
        scores = [r.overall_score for r in reports]
        
        aggregated = {
            'total_leads': len(reports),
            'average_score': np.mean(scores),
            'median_score': np.median(scores),
            'min_score': np.min(scores),
            'max_score': np.max(scores),
            'std_dev': np.std(scores),
            'distribution': {
                'excellent': sum(1 for s in scores if s >= self.thresholds['excellent']),
                'good': sum(1 for s in scores if self.thresholds['good'] <= s < self.thresholds['excellent']),
                'fair': sum(1 for s in scores if self.thresholds['fair'] <= s < self.thresholds['good']),
                'poor': sum(1 for s in scores if self.thresholds['poor'] <= s < self.thresholds['fair']),
                'critical': sum(1 for s in scores if s < self.thresholds['poor'])
            },
            'common_issues': self._aggregate_issues(reports),
            'top_suggestions': self._aggregate_suggestions(reports),
            'individual_reports': [r.to_dict() for r in reports]
        }
        
        return aggregated
    
    def _aggregate_issues(self, reports: List[QualityReport]) -> List[Tuple[str, int]]:
        """Agrega issues mais comuns"""
        from collections import Counter
        
        all_issues = []
        for report in reports:
            all_issues.extend(report.issues)
        
        counter = Counter(all_issues)
        return counter.most_common(10)
    
    def _aggregate_suggestions(self, reports: List[QualityReport]) -> List[Tuple[str, int]]:
        """Agrega sugestões mais comuns"""
        from collections import Counter
        
        all_suggestions = []
        for report in reports:
            all_suggestions.extend(report.suggestions)
        
        counter = Counter(all_suggestions)
        return counter.most_common(10)
    
    def generate_action_plan(self, batch_review: Dict[str, Any]) -> List[str]:
        """
        Gera plano de ação baseado na revisão
        
        Args:
            batch_review: Resultado da revisão em batch
            
        Returns:
            Lista de ações recomendadas
        """
        actions = []
        
        avg_score = batch_review['average_score']
        distribution = batch_review['distribution']
        
        # Ações baseadas no score médio
        if avg_score < 60:
            actions.append("1. URGENTE: Revisar configuração de todas as APIs")
            actions.append("2. Implementar sistema de retry automático mais agressivo")
            actions.append("3. Adicionar scrapers alternativos de backup")
        
        # Ações baseadas na distribuição
        if distribution['critical'] > len(batch_review['individual_reports']) * 0.2:
            actions.append("4. Revisar qualidade dos dados de entrada")
            actions.append("5. Implementar validação pré-processamento")
        
        if distribution['excellent'] < len(batch_review['individual_reports']) * 0.3:
            actions.append("6. Otimizar estratégias de enriquecimento")
            actions.append("7. Adicionar mais fontes de dados")
        
        # Ações baseadas em issues comuns
        top_issues = batch_review['common_issues'][:3]
        for i, (issue, count) in enumerate(top_issues, 8):
            actions.append(f"{i}. Resolver: {issue} (afeta {count} leads)")
        
        return actions