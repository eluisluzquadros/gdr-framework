#!/usr/bin/env python3
"""
Sistema de Cache com DuckDB para GDR Framework
Evita reprocessamento de leads e mantém histórico completo
"""

import duckdb
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class LeadCache:
    """
    Cache persistente para leads processados usando DuckDB
    """
    
    def __init__(self, db_path: str = "data/gdr_cache.duckdb"):
        """
        Inicializa o cache com DuckDB
        
        Args:
            db_path: Caminho para o arquivo do banco de dados
        """
        # Criar diretório se não existir
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        
        # Criar tabelas se não existirem
        self._create_tables()
        
        # Estatísticas da sessão
        self.stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0,
            'errors': 0
        }
        
        logger.info(f"Cache inicializado: {db_path}")
    
    def _create_tables(self):
        """Cria as tabelas necessárias no banco"""
        
        # Tabela principal de leads processados
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_leads (
                lead_hash VARCHAR PRIMARY KEY,
                lead_id VARCHAR NOT NULL,
                lead_name VARCHAR NOT NULL,
                cnpj VARCHAR,
                
                -- Dados originais
                original_data JSON,
                
                -- Dados enriquecidos
                enriched_email VARCHAR,
                enriched_phone VARCHAR,
                enriched_website VARCHAR,
                enriched_whatsapp VARCHAR,
                enriched_instagram VARCHAR,
                enriched_facebook VARCHAR,
                enriched_linkedin VARCHAR,
                
                -- Scores e análises
                sdr_score DOUBLE,
                sdr_category VARCHAR,
                sdr_qualified BOOLEAN,
                quality_score DOUBLE,
                kappa_score DOUBLE,
                
                -- LLM consensus
                llm_consensus JSON,
                providers_used JSON,
                
                -- Metadados
                processing_time DOUBLE,
                total_cost_usd DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cache_ttl_hours INTEGER DEFAULT 168,  -- 7 dias padrão
                
                -- Resultado completo em JSON
                full_result JSON
            )
        """)
        
        # Tabela de estatísticas de processamento
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS processing_stats (
                id INTEGER PRIMARY KEY,
                date DATE NOT NULL,
                total_processed INTEGER DEFAULT 0,
                cache_hits INTEGER DEFAULT 0,
                cache_misses INTEGER DEFAULT 0,
                total_cost_usd DOUBLE DEFAULT 0,
                avg_processing_time DOUBLE DEFAULT 0,
                avg_sdr_score DOUBLE DEFAULT 0,
                qualified_leads INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tabela de histórico de buscas
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY,
                search_query VARCHAR,
                search_type VARCHAR,  -- 'cnpj', 'name', 'email', etc
                results_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Criar índices para busca rápida
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lead_id ON processed_leads(lead_id)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_cnpj ON processed_leads(cnpj)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lead_name ON processed_leads(lead_name)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON processed_leads(created_at)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sdr_qualified ON processed_leads(sdr_qualified)
        """)
        
        logger.info("Tabelas e índices criados/verificados")
    
    def get_lead(self, lead_id: str, ttl_hours: int = 168) -> Optional[Dict[str, Any]]:
        """
        Busca lead no cache por ID
        
        Args:
            lead_id: ID do lead (CNPJ ou outro identificador)
            ttl_hours: Tempo de vida do cache em horas
            
        Returns:
            Resultado cached ou None se não encontrado/expirado
        """
        try:
            # Buscar no cache considerando TTL
            result = self.conn.execute(f"""
                SELECT full_result, created_at
                FROM processed_leads
                WHERE lead_id = '{lead_id}'
                AND created_at > CURRENT_TIMESTAMP - INTERVAL {ttl_hours} HOUR
                ORDER BY created_at DESC
                LIMIT 1
            """).fetchone()
            
            if result:
                self.stats['hits'] += 1
                logger.info(f"Cache HIT para lead ID: {lead_id}")
                
                # Retornar resultado deserializado
                return json.loads(result[0]) if result[0] else None
            else:
                self.stats['misses'] += 1
                logger.debug(f"Cache MISS para lead ID: {lead_id}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar lead no cache: {e}")
            self.stats['errors'] += 1
            return None
    
    def is_recent(self, lead_id: str, days: int = 7) -> bool:
        """
        Verifica se o cache de um lead é recente
        
        Args:
            lead_id: ID do lead
            days: Número de dias para considerar recente
            
        Returns:
            True se o cache é recente, False caso contrário
        """
        try:
            result = self.conn.execute(f"""
                SELECT created_at
                FROM processed_leads
                WHERE lead_id = '{lead_id}'
                AND created_at > CURRENT_TIMESTAMP - INTERVAL {days} DAY
                ORDER BY created_at DESC
                LIMIT 1
            """).fetchone()
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Erro ao verificar idade do cache: {e}")
            return False
    
    def save_lead(self, lead_id: str, result: Dict[str, Any], ttl_hours: int = 168):
        """
        Salva resultado de lead no cache
        
        Args:
            lead_id: ID do lead
            result: Resultado do processamento
            ttl_hours: Tempo de vida do cache em horas
        """
        try:
            # Gerar hash baseado no lead_id
            lead_hash = hashlib.sha256(lead_id.encode()).hexdigest()
            
            # Preparar dados para inserção
            data = {
                'lead_hash': lead_hash,
                'lead_id': lead_id,
                'lead_name': result.get('original_nome', result.get('name', '')),
                'cnpj': result.get('original_id', result.get('cnpj', lead_id)),
                'original_data': json.dumps(result.get('original_data', {})),
                
                # Dados enriquecidos
                'enriched_email': result.get('gdr_consolidated_email', ''),
                'enriched_phone': result.get('gdr_consolidated_phone', ''),
                'enriched_website': result.get('gdr_consolidated_website', ''),
                'enriched_whatsapp': result.get('gdr_consolidated_whatsapp', ''),
                'enriched_instagram': result.get('gdr_instagram_url', ''),
                'enriched_facebook': result.get('gdr_facebook_url', ''),
                'enriched_linkedin': result.get('gdr_linkedin_url', ''),
                
                # Scores
                'sdr_score': result.get('gdr_sdr_lead_score', 0),
                'sdr_category': result.get('gdr_sdr_category', ''),
                'sdr_qualified': result.get('gdr_sdr_qualified', False),
                'quality_score': result.get('gdr_quality_overall_score', 0),
                'kappa_score': result.get('gdr_kappa_overall_score', 0),
                
                # LLM info
                'llm_consensus': json.dumps(result.get('gdr_llm_consensus', {})),
                'providers_used': json.dumps(result.get('gdr_providers_used', [])),
                
                # Metadados
                'processing_time': result.get('processing_time_seconds', 0),
                'total_cost_usd': result.get('gdr_total_cost_usd', 0),
                'cache_ttl_hours': ttl_hours,
                
                # Resultado completo
                'full_result': json.dumps(result)
            }
            
            # Preparar valores com escape apropriado
            values = []
            for v in data.values():
                if v is None:
                    values.append("NULL")
                elif isinstance(v, str):
                    # Escapar aspas simples
                    values.append(f"'{v.replace(chr(39), chr(39)+chr(39))}'")
                elif isinstance(v, bool):
                    values.append("TRUE" if v else "FALSE")
                else:
                    values.append(str(v))
            
            # Inserir ou atualizar
            query = f"""
                INSERT OR REPLACE INTO processed_leads
                (lead_hash, lead_id, lead_name, cnpj, original_data,
                 enriched_email, enriched_phone, enriched_website, enriched_whatsapp,
                 enriched_instagram, enriched_facebook, enriched_linkedin,
                 sdr_score, sdr_category, sdr_qualified, quality_score, kappa_score,
                 llm_consensus, providers_used,
                 processing_time, total_cost_usd, cache_ttl_hours,
                 full_result, updated_at)
                VALUES ({', '.join(values)}, CURRENT_TIMESTAMP)
            """
            self.conn.execute(query)
            
            self.stats['saves'] += 1
            logger.info(f"Lead {lead_id} salvo no cache")
            
        except Exception as e:
            logger.error(f"Erro ao salvar lead no cache: {e}")
            self.stats['errors'] += 1
    
    def get_scraper_results(self, lead_id: str, ttl_hours: int = 168) -> Dict[str, Any]:
        """
        Busca resultados de scrapers no cache para um lead
        
        Args:
            lead_id: ID do lead
            ttl_hours: Tempo de vida do cache em horas
            
        Returns:
            Dict com resultados dos scrapers ou {} se não encontrado
        """
        try:
            results = self.conn.execute(f"""
                SELECT scraper_name, result_data
                FROM scraper_results
                WHERE lead_id = '{lead_id}'
                AND created_at > CURRENT_TIMESTAMP - INTERVAL {ttl_hours} HOUR
            """).fetchall()
            
            if results:
                scraper_data = {}
                for name, data in results:
                    scraper_data[name] = json.loads(data) if data else {}
                return scraper_data
            
            return {}
            
        except Exception as e:
            logger.error(f"Erro ao buscar scrapers no cache: {e}")
            return {}
    
    def save_scraper_result(self, lead_id: str, scraper_name: str, result: Dict[str, Any]):
        """
        Salva resultado de um scraper específico
        
        Args:
            lead_id: ID do lead
            scraper_name: Nome do scraper
            result: Resultado do scraper
        """
        try:
            # Criar tabela de scrapers se não existir
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS scraper_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id VARCHAR NOT NULL,
                    scraper_name VARCHAR NOT NULL,
                    result_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(lead_id, scraper_name)
                )
            """)
            
            # Criar índice se não existir
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_scraper_lead_id 
                ON scraper_results(lead_id)
            """)
            
            # Inserir ou atualizar resultado
            result_json = json.dumps(result)
            # Primeiro tentar deletar se existir
            self.conn.execute(f"""
                DELETE FROM scraper_results 
                WHERE lead_id = '{lead_id}' AND scraper_name = '{scraper_name}'
            """)
            # Depois inserir novo
            self.conn.execute(f"""
                INSERT INTO scraper_results
                (lead_id, scraper_name, result_data, created_at)
                VALUES ('{lead_id}', '{scraper_name}', '{result_json.replace(chr(39), chr(39)+chr(39))}', CURRENT_TIMESTAMP)
            """)
            
            logger.debug(f"Scraper {scraper_name} salvo para lead {lead_id}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar scraper no cache: {e}")
    
    def _generate_hash(self, lead_data: Dict[str, Any]) -> str:
        """
        Gera hash único para o lead baseado em campos chave
        
        Args:
            lead_data: Dados do lead
            
        Returns:
            Hash SHA256 do lead
        """
        # Campos que identificam unicamente um lead
        key_fields = [
            lead_data.get('original_id', ''),
            lead_data.get('original_nome', ''),
            lead_data.get('original_endereco_completo', '')
        ]
        
        # Criar string única
        unique_string = '|'.join(str(f) for f in key_fields)
        
        # Gerar hash
        return hashlib.sha256(unique_string.encode()).hexdigest()
    
    def get(self, lead_data: Dict[str, Any], ttl_hours: int = 168) -> Optional[Dict[str, Any]]:
        """
        Busca lead no cache
        
        Args:
            lead_data: Dados do lead para buscar
            ttl_hours: Tempo de vida do cache em horas
            
        Returns:
            Resultado cached ou None se não encontrado/expirado
        """
        try:
            lead_hash = self._generate_hash(lead_data)
            
            # Buscar no cache considerando TTL
            result = self.conn.execute(f"""
                SELECT full_result, created_at, cache_ttl_hours
                FROM processed_leads
                WHERE lead_hash = '{lead_hash}'
                AND created_at > CURRENT_TIMESTAMP - INTERVAL {ttl_hours} HOUR
            """).fetchone()
            
            if result:
                self.stats['hits'] += 1
                logger.info(f"Cache HIT para lead: {lead_data.get('original_nome', 'Unknown')[:30]}")
                
                # Retornar resultado deserializado
                return json.loads(result[0]) if result[0] else None
            else:
                self.stats['misses'] += 1
                logger.debug(f"Cache MISS para lead: {lead_data.get('original_nome', 'Unknown')[:30]}")
                return None
                
        except Exception as e:
            logger.error(f"Erro ao buscar no cache: {e}")
            self.stats['errors'] += 1
            return None
    
    def save(self, lead_data: Dict[str, Any], result: Dict[str, Any], ttl_hours: int = 168):
        """
        Salva resultado no cache
        
        Args:
            lead_data: Dados originais do lead
            result: Resultado do processamento
            ttl_hours: Tempo de vida do cache em horas
        """
        try:
            lead_hash = self._generate_hash(lead_data)
            
            # Preparar dados para inserção
            data = {
                'lead_hash': lead_hash,
                'lead_id': lead_data.get('original_id', ''),
                'lead_name': lead_data.get('original_nome', ''),
                'cnpj': lead_data.get('original_id', ''),
                'original_data': json.dumps(lead_data),
                
                # Dados enriquecidos
                'enriched_email': result.get('gdr_consolidated_email'),
                'enriched_phone': result.get('gdr_consolidated_phone'),
                'enriched_website': result.get('gdr_consolidated_website'),
                'enriched_whatsapp': result.get('gdr_consolidated_whatsapp'),
                'enriched_instagram': result.get('gdr_instagram_url'),
                'enriched_facebook': result.get('gdr_facebook_url'),
                'enriched_linkedin': result.get('gdr_linkedin_url'),
                
                # Scores
                'sdr_score': result.get('gdr_sdr_lead_score'),
                'sdr_category': result.get('gdr_sdr_category'),
                'sdr_qualified': result.get('gdr_sdr_qualified'),
                'quality_score': result.get('gdr_quality_score'),
                'kappa_score': result.get('gdr_kappa_overall_score'),
                
                # LLM info
                'llm_consensus': json.dumps(result.get('gdr_llm_consensus', {})),
                'providers_used': json.dumps(result.get('gdr_providers_used', [])),
                
                # Metadados
                'processing_time': result.get('gdr_processing_time_seconds'),
                'total_cost_usd': result.get('gdr_total_cost_usd'),
                'cache_ttl_hours': ttl_hours,
                
                # Resultado completo
                'full_result': json.dumps(result)
            }
            
            # Preparar valores com escape apropriado
            values = []
            for v in data.values():
                if v is None:
                    values.append("NULL")
                elif isinstance(v, str):
                    # Escapar aspas simples
                    values.append(f"'{v.replace(chr(39), chr(39)+chr(39))}'")
                elif isinstance(v, bool):
                    values.append("TRUE" if v else "FALSE")
                else:
                    values.append(str(v))
            
            # Inserir ou atualizar
            query = f"""
                INSERT OR REPLACE INTO processed_leads
                (lead_hash, lead_id, lead_name, cnpj, original_data,
                 enriched_email, enriched_phone, enriched_website, enriched_whatsapp,
                 enriched_instagram, enriched_facebook, enriched_linkedin,
                 sdr_score, sdr_category, sdr_qualified, quality_score, kappa_score,
                 llm_consensus, providers_used,
                 processing_time, total_cost_usd, cache_ttl_hours,
                 full_result, updated_at)
                VALUES ({', '.join(values)}, CURRENT_TIMESTAMP)
            """
            self.conn.execute(query)
            
            self.stats['saves'] += 1
            logger.info(f"Lead salvo no cache: {lead_data.get('original_nome', 'Unknown')[:30]}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar no cache: {e}")
            self.stats['errors'] += 1
    
    def search_by_cnpj(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """Busca lead por CNPJ"""
        try:
            result = self.conn.execute("""
                SELECT full_result
                FROM processed_leads
                WHERE cnpj = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, [cnpj]).fetchone()
            
            if result:
                return json.loads(result[0]) if result[0] else None
            return None
            
        except Exception as e:
            logger.error(f"Erro ao buscar por CNPJ: {e}")
            return None
    
    def search_by_name(self, name: str, fuzzy: bool = True) -> List[Dict[str, Any]]:
        """
        Busca leads por nome
        
        Args:
            name: Nome para buscar
            fuzzy: Se True, usa busca aproximada
            
        Returns:
            Lista de resultados encontrados
        """
        try:
            if fuzzy:
                # Busca aproximada
                results = self.conn.execute("""
                    SELECT full_result
                    FROM processed_leads
                    WHERE LOWER(lead_name) LIKE LOWER(?)
                    ORDER BY updated_at DESC
                    LIMIT 10
                """, [f'%{name}%']).fetchall()
            else:
                # Busca exata
                results = self.conn.execute("""
                    SELECT full_result
                    FROM processed_leads
                    WHERE lead_name = ?
                    ORDER BY updated_at DESC
                    LIMIT 10
                """, [name]).fetchall()
            
            return [json.loads(r[0]) for r in results if r[0]]
            
        except Exception as e:
            logger.error(f"Erro ao buscar por nome: {e}")
            return []
    
    def get_qualified_leads(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retorna leads qualificados pelo SDR"""
        try:
            results = self.conn.execute("""
                SELECT full_result
                FROM processed_leads
                WHERE sdr_qualified = true
                ORDER BY sdr_score DESC
                LIMIT ?
            """, [limit]).fetchall()
            
            return [json.loads(r[0]) for r in results if r[0]]
            
        except Exception as e:
            logger.error(f"Erro ao buscar leads qualificados: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        try:
            stats = self.conn.execute("""
                SELECT 
                    COUNT(*) as total_leads,
                    COUNT(CASE WHEN sdr_qualified = true THEN 1 END) as qualified_leads,
                    AVG(sdr_score) as avg_sdr_score,
                    AVG(quality_score) as avg_quality_score,
                    AVG(kappa_score) as avg_kappa_score,
                    SUM(total_cost_usd) as total_cost,
                    AVG(processing_time) as avg_processing_time,
                    MIN(created_at) as first_processed,
                    MAX(created_at) as last_processed
                FROM processed_leads
            """).fetchone()
            
            if stats:
                return {
                    'total_leads': stats[0] or 0,
                    'qualified_leads': stats[1] or 0,
                    'avg_sdr_score': stats[2] or 0,
                    'avg_quality_score': stats[3] or 0,
                    'avg_kappa_score': stats[4] or 0,
                    'total_cost_usd': stats[5] or 0,
                    'avg_processing_time': stats[6] or 0,
                    'first_processed': stats[7],
                    'last_processed': stats[8],
                    'cache_hits': self.stats['hits'],
                    'cache_misses': self.stats['misses'],
                    'cache_saves': self.stats['saves'],
                    'cache_errors': self.stats['errors'],
                    'hit_rate': self.stats['hits'] / max(1, self.stats['hits'] + self.stats['misses'])
                }
            return {}
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
    
    def cleanup_expired(self) -> int:
        """
        Remove entradas expiradas do cache
        
        Returns:
            Número de entradas removidas
        """
        try:
            result = self.conn.execute("""
                DELETE FROM processed_leads
                WHERE created_at < CURRENT_TIMESTAMP - INTERVAL cache_ttl_hours HOUR
            """)
            
            deleted = result.rowcount
            logger.info(f"Cache cleanup: {deleted} entradas expiradas removidas")
            return deleted
            
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return 0
    
    def export_to_excel(self, output_path: str, qualified_only: bool = False):
        """
        Exporta cache para Excel
        
        Args:
            output_path: Caminho do arquivo Excel
            qualified_only: Se True, exporta apenas leads qualificados
        """
        import pandas as pd
        
        try:
            if qualified_only:
                query = """
                    SELECT * FROM processed_leads
                    WHERE sdr_qualified = true
                    ORDER BY sdr_score DESC
                """
            else:
                query = """
                    SELECT * FROM processed_leads
                    ORDER BY updated_at DESC
                """
            
            df = self.conn.execute(query).df()
            
            # Remover colunas JSON para Excel
            json_columns = ['original_data', 'llm_consensus', 'providers_used', 'full_result']
            df = df.drop(columns=json_columns, errors='ignore')
            
            # Salvar em Excel
            df.to_excel(output_path, index=False)
            logger.info(f"Cache exportado para: {output_path}")
            
        except Exception as e:
            logger.error(f"Erro ao exportar cache: {e}")
    
    def close(self):
        """Fecha conexão com o banco"""
        if self.conn:
            self.conn.close()
            logger.info("Conexão com cache fechada")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class CachedGDRFramework:
    """
    Wrapper para GDRFramework com cache automático
    """
    
    def __init__(self, framework, cache_path: str = "data/gdr_cache.duckdb", ttl_hours: int = 168):
        """
        Inicializa framework com cache
        
        Args:
            framework: Instância do GDRFramework
            cache_path: Caminho do banco de cache
            ttl_hours: TTL padrão do cache em horas
        """
        self.framework = framework
        self.cache = LeadCache(cache_path)
        self.ttl_hours = ttl_hours
    
    async def process_single_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa lead com cache
        
        Args:
            lead_data: Dados do lead
            
        Returns:
            Resultado do processamento (do cache ou novo)
        """
        # Verificar cache primeiro
        cached_result = self.cache.get(lead_data, self.ttl_hours)
        
        if cached_result:
            logger.info(f"Lead recuperado do cache: {lead_data.get('original_nome', 'Unknown')[:30]}")
            return cached_result
        
        # Processar se não estiver em cache
        logger.info(f"Processando novo lead: {lead_data.get('original_nome', 'Unknown')[:30]}")
        result = await self.framework.process_single_lead(lead_data)
        
        # Salvar no cache
        if result:
            self.cache.save(lead_data, result, self.ttl_hours)
        
        return result
    
    async def process_batch(self, leads: List[Dict[str, Any]], max_concurrent: int = 5) -> List[Dict[str, Any]]:
        """
        Processa batch de leads com cache
        
        Args:
            leads: Lista de leads para processar
            max_concurrent: Número máximo de processamentos simultâneos
            
        Returns:
            Lista de resultados
        """
        results = []
        to_process = []
        
        # Verificar cache para cada lead
        for lead in leads:
            cached = self.cache.get(lead, self.ttl_hours)
            if cached:
                results.append(cached)
            else:
                to_process.append(lead)
        
        logger.info(f"Batch: {len(results)} do cache, {len(to_process)} para processar")
        
        # Processar leads não cacheados
        if to_process:
            if hasattr(self.framework, 'process_leads_batch'):
                new_results, _ = await self.framework.process_leads_batch(to_process, max_concurrent)
            else:
                # Processar individualmente se não tiver batch
                new_results = []
                for lead in to_process:
                    result = await self.framework.process_single_lead(lead)
                    new_results.append(result)
            
            # Salvar novos resultados no cache
            for lead, result in zip(to_process, new_results):
                if result:
                    self.cache.save(lead, result, self.ttl_hours)
                    results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas combinadas do cache e processamento"""
        return self.cache.get_statistics()
    
    def close(self):
        """Fecha recursos"""
        self.cache.close()


if __name__ == "__main__":
    # Teste básico
    cache = LeadCache()
    
    # Exemplo de lead
    test_lead = {
        'original_id': '12345678000190',
        'original_nome': 'Empresa Teste',
        'original_endereco_completo': 'Rua Teste, 123'
    }
    
    # Simular resultado
    test_result = {
        'gdr_consolidated_email': 'teste@empresa.com',
        'gdr_consolidated_phone': '11999999999',
        'gdr_sdr_lead_score': 8.5,
        'gdr_sdr_qualified': True,
        'gdr_total_cost_usd': 0.005
    }
    
    # Testar save e get
    cache.save(test_lead, test_result)
    retrieved = cache.get(test_lead)
    
    print("Cache test:")
    print(f"Saved: {test_result}")
    print(f"Retrieved: {retrieved}")
    print(f"Statistics: {cache.get_statistics()}")
    
    cache.close()