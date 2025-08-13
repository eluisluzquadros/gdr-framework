#!/usr/bin/env python3
"""
Linktree Detector - Detecção melhorada de perfis Linktree
Detecta Linktree em bios do Instagram, websites e outras fontes
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class LinktreeDetector:
    """Detecta e extrai informações de Linktree de várias fontes"""
    
    def __init__(self):
        """Inicializa o detector com padrões de detecção"""
        
        # Padrões de URL do Linktree
        self.linktree_patterns = [
            # Padrão completo
            r'(?:https?://)?(?:www\.)?linktr\.ee/([a-zA-Z0-9_.-]+)',
            r'(?:https?://)?(?:www\.)?linktree\.com/([a-zA-Z0-9_.-]+)',
            
            # Padrão curto (comum em bios)
            r'linktr\.ee/([a-zA-Z0-9_.-]+)',
            r'linktree\.com/([a-zA-Z0-9_.-]+)',
            
            # Com emojis ou caracteres especiais ao redor
            r'🔗\s*linktr\.ee/([a-zA-Z0-9_.-]+)',
            r'Link:\s*linktr\.ee/([a-zA-Z0-9_.-]+)',
            r'👉\s*linktr\.ee/([a-zA-Z0-9_.-]+)',
            
            # Em contexto de frase
            r'(?:link|links|bio|clique|acesse|visite)[:\s]+linktr\.ee/([a-zA-Z0-9_.-]+)',
            
            # Variações com espaços
            r'link\s+tree[:\s]+([a-zA-Z0-9_.-]+)',
            r'linktree[:\s]+([a-zA-Z0-9_.-]+)',
        ]
        
        # Padrões alternativos (outros agregadores de links)
        self.alternative_patterns = {
            'beacons': r'(?:https?://)?(?:www\.)?beacons\.ai/([a-zA-Z0-9_.-]+)',
            'biolink': r'(?:https?://)?(?:www\.)?bio\.link/([a-zA-Z0-9_.-]+)',
            'lnk.bio': r'(?:https?://)?(?:www\.)?lnk\.bio/([a-zA-Z0-9_.-]+)',
            'taplink': r'(?:https?://)?(?:www\.)?taplink\.cc/([a-zA-Z0-9_.-]+)',
            'milkshake': r'(?:https?://)?(?:www\.)?msha\.ke/([a-zA-Z0-9_.-]+)',
            'campsite': r'(?:https?://)?(?:www\.)?campsite\.bio/([a-zA-Z0-9_.-]+)',
            'solo.to': r'(?:https?://)?(?:www\.)?solo\.to/([a-zA-Z0-9_.-]+)',
        }
    
    def detect_linktree(self, text: str) -> Dict[str, any]:
        """
        Detecta Linktree ou alternativas em um texto
        
        Args:
            text: Texto para analisar (bio, descrição, etc)
            
        Returns:
            Dict com informações detectadas
        """
        result = {
            'found': False,
            'platform': None,
            'username': None,
            'url': None,
            'alternatives': []
        }
        
        if not text:
            return result
        
        # Normalizar texto
        text = str(text)
        
        # Procurar Linktree
        for pattern in self.linktree_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                username = matches[0]
                # Limpar username
                username = username.strip().rstrip('.,!?;:')
                
                result['found'] = True
                result['platform'] = 'linktree'
                result['username'] = username
                result['url'] = f"https://linktr.ee/{username}"
                
                logger.info(f"Linktree detectado: {username}")
                break
        
        # Se não encontrou Linktree, procurar alternativas
        if not result['found']:
            for platform, pattern in self.alternative_patterns.items():
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    username = matches[0]
                    username = username.strip().rstrip('.,!?;:')
                    
                    alt_info = {
                        'platform': platform,
                        'username': username,
                        'url': self._build_alternative_url(platform, username)
                    }
                    result['alternatives'].append(alt_info)
                    
                    # Se ainda não tem resultado principal, usar a primeira alternativa
                    if not result['found']:
                        result['found'] = True
                        result['platform'] = platform
                        result['username'] = username
                        result['url'] = alt_info['url']
                        
                        logger.info(f"Agregador alternativo detectado: {platform}/{username}")
        
        return result
    
    def detect_from_instagram_data(self, instagram_data: Dict) -> Dict[str, any]:
        """
        Detecta Linktree de dados do Instagram
        
        Args:
            instagram_data: Dados coletados do Instagram
            
        Returns:
            Dict com informações detectadas
        """
        # Lugares onde procurar
        search_fields = [
            'gdr_instagram_bio',
            'gdr_instagram_external_url',
            'biography',
            'bio',
            'external_url',
            'website',
            'contact_phone_number',  # Às vezes colocam links aqui
            'business_contact_method',
            'category_name',  # Às vezes tem "Link in bio"
        ]
        
        combined_text = []
        
        for field in search_fields:
            value = instagram_data.get(field, '')
            if value:
                combined_text.append(str(value))
        
        # Procurar em todo o texto combinado
        full_text = ' '.join(combined_text)
        result = self.detect_linktree(full_text)
        
        # Se não encontrou na bio, verificar se o external_url é um Linktree
        if not result['found'] and instagram_data.get('gdr_instagram_external_url'):
            url = instagram_data['gdr_instagram_external_url']
            if self._is_linktree_url(url):
                username = self._extract_username_from_url(url)
                if username:
                    result['found'] = True
                    result['platform'] = self._detect_platform_from_url(url)
                    result['username'] = username
                    result['url'] = url
        
        return result
    
    def detect_from_multiple_sources(self, data: Dict) -> Dict[str, any]:
        """
        Detecta Linktree de múltiplas fontes de dados
        
        Args:
            data: Dados combinados de várias fontes
            
        Returns:
            Dict com informações detectadas
        """
        results = []
        
        # Instagram
        if any(k.startswith('gdr_instagram') for k in data.keys()):
            instagram_result = self.detect_from_instagram_data(data)
            if instagram_result['found']:
                results.append(instagram_result)
        
        # Facebook bio
        if data.get('gdr_facebook_bio'):
            fb_result = self.detect_linktree(data['gdr_facebook_bio'])
            if fb_result['found']:
                results.append(fb_result)
        
        # Website scraped data
        if data.get('gdr_cwral4ai_social_urls'):
            try:
                import json
                social_urls = json.loads(data['gdr_cwral4ai_social_urls'])
                for url in social_urls.values():
                    if self._is_linktree_url(url):
                        username = self._extract_username_from_url(url)
                        if username:
                            results.append({
                                'found': True,
                                'platform': self._detect_platform_from_url(url),
                                'username': username,
                                'url': url
                            })
            except:
                pass
        
        # Google Search results
        if data.get('gdr_google_search_engine_url'):
            url = data['gdr_google_search_engine_url']
            if self._is_linktree_url(url):
                username = self._extract_username_from_url(url)
                if username:
                    results.append({
                        'found': True,
                        'platform': self._detect_platform_from_url(url),
                        'username': username,
                        'url': url
                    })
        
        # Consolidar resultados
        if results:
            # Priorizar Linktree sobre alternativas
            for r in results:
                if r['platform'] == 'linktree':
                    return r
            # Se não tem Linktree, retornar primeiro resultado
            return results[0]
        
        return {
            'found': False,
            'platform': None,
            'username': None,
            'url': None,
            'alternatives': []
        }
    
    def _is_linktree_url(self, url: str) -> bool:
        """Verifica se uma URL é do Linktree ou alternativas"""
        if not url:
            return False
        
        url_lower = url.lower()
        linktree_domains = [
            'linktr.ee',
            'linktree.com',
            'beacons.ai',
            'bio.link',
            'lnk.bio',
            'taplink.cc',
            'msha.ke',
            'campsite.bio',
            'solo.to'
        ]
        
        return any(domain in url_lower for domain in linktree_domains)
    
    def _extract_username_from_url(self, url: str) -> Optional[str]:
        """Extrai username de uma URL do Linktree"""
        try:
            # Remover parâmetros de query
            url = url.split('?')[0]
            # Remover trailing slash
            url = url.rstrip('/')
            # Pegar última parte
            parts = url.split('/')
            if len(parts) > 0:
                username = parts[-1]
                # Limpar username
                username = username.strip().rstrip('.,!?;:')
                if username and not username.startswith('http'):
                    return username
        except:
            pass
        return None
    
    def _detect_platform_from_url(self, url: str) -> str:
        """Detecta a plataforma baseado na URL"""
        url_lower = url.lower()
        
        platforms = {
            'linktr.ee': 'linktree',
            'linktree.com': 'linktree',
            'beacons.ai': 'beacons',
            'bio.link': 'biolink',
            'lnk.bio': 'lnk.bio',
            'taplink.cc': 'taplink',
            'msha.ke': 'milkshake',
            'campsite.bio': 'campsite',
            'solo.to': 'solo.to'
        }
        
        for domain, platform in platforms.items():
            if domain in url_lower:
                return platform
        
        return 'unknown'
    
    def _build_alternative_url(self, platform: str, username: str) -> str:
        """Constrói URL para plataformas alternativas"""
        urls = {
            'beacons': f"https://beacons.ai/{username}",
            'biolink': f"https://bio.link/{username}",
            'lnk.bio': f"https://lnk.bio/{username}",
            'taplink': f"https://taplink.cc/{username}",
            'milkshake': f"https://msha.ke/{username}",
            'campsite': f"https://campsite.bio/{username}",
            'solo.to': f"https://solo.to/{username}",
        }
        
        return urls.get(platform, f"https://{platform}/{username}")
    
    def enrich_with_detection(self, data: Dict) -> Dict:
        """
        Enriquece dados com detecção de Linktree
        
        Args:
            data: Dados para enriquecer
            
        Returns:
            Dados enriquecidos com informações de Linktree
        """
        detection = self.detect_from_multiple_sources(data)
        
        if detection['found']:
            # Adicionar campos de Linktree
            data['gdr_linktree_detected'] = True
            data['gdr_linktree_platform'] = detection['platform']
            data['gdr_linktree_username'] = detection['username']
            data['gdr_linktree_url'] = detection['url']
            
            # Se tem alternativas, adicionar também
            if detection.get('alternatives'):
                import json
                data['gdr_linktree_alternatives'] = json.dumps(detection['alternatives'])
            
            logger.info(f"Dados enriquecidos com Linktree: {detection['platform']}/{detection['username']}")
        else:
            data['gdr_linktree_detected'] = False
        
        return data


# Função helper para uso direto
def detect_and_enrich_linktree(data: Dict) -> Dict:
    """
    Função helper para detectar e enriquecer dados com Linktree
    
    Args:
        data: Dados para processar
        
    Returns:
        Dados enriquecidos
    """
    detector = LinktreeDetector()
    return detector.enrich_with_detection(data)