#!/usr/bin/env python3
"""
Facebook Alternative Scraper
Usa múltiplas estratégias para coletar dados do Facebook sem necessidade de cookies
"""

import os
import re
import json
import asyncio
import aiohttp
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import quote, urlparse

logger = logging.getLogger(__name__)


class FacebookAlternativeScraper:
    """
    Scraper alternativo para Facebook usando múltiplas estratégias
    """
    
    def __init__(self):
        """Inicializa o scraper alternativo"""
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def scrape_facebook_alternative(self, company_name: str, location: str = '', existing_url: str = '') -> Dict[str, Any]:
        """
        Tenta múltiplas estratégias para obter dados do Facebook
        """
        result = self._empty_facebook_data()
        
        # Estratégia 0: Usar URL existente se fornecida
        if existing_url and 'facebook.com' in existing_url:
            result['gdr_facebook_url'] = existing_url
            result['gdr_facebook_username'] = self._extract_username_from_url(existing_url)
        
        # Estratégia 1: Buscar via Google
        if not result['gdr_facebook_url']:
            google_result = await self._search_via_google(company_name, location)
            if google_result.get('url'):
                result['gdr_facebook_url'] = google_result['url']
                result['gdr_facebook_username'] = self._extract_username_from_url(google_result['url'])
        
        # Estratégia 2: Buscar via Bing (nova estratégia)
        if not result['gdr_facebook_url']:
            bing_result = await self._search_via_bing(company_name, location)
            if bing_result.get('url'):
                result['gdr_facebook_url'] = bing_result['url']
                result['gdr_facebook_username'] = self._extract_username_from_url(bing_result['url'])
        
        # Estratégia 3: Construir URLs prováveis e testar múltiplas variações
        if not result['gdr_facebook_url']:
            probable_urls = self._build_probable_urls(company_name)  # Agora retorna lista
            for url in probable_urls:
                if await self._verify_url_exists(url):
                    result['gdr_facebook_url'] = url
                    result['gdr_facebook_username'] = self._extract_username_from_url(url)
                    break
        
        # Estratégia 4: Buscar via DuckDuckGo (sem API key)
        if not result['gdr_facebook_url']:
            ddg_result = await self._search_via_duckduckgo(company_name, location)
            if ddg_result.get('url'):
                result['gdr_facebook_url'] = ddg_result['url']
                result['gdr_facebook_username'] = self._extract_username_from_url(ddg_result['url'])
        
        # Estratégia 5: Buscar via API Graph pública (limitada)
        if result['gdr_facebook_url']:
            public_data = await self._get_public_graph_data(result['gdr_facebook_username'])
            result.update(public_data)
        
        # Estratégia 6: Extrair dados do HTML público (sem cookies)
        if result['gdr_facebook_url']:
            html_data = await self._extract_from_public_html(result['gdr_facebook_url'])
            result.update(html_data)
        
        # Estratégia 7: Tentar extrair dados de Open Graph meta tags
        if result['gdr_facebook_url']:
            og_data = await self._extract_open_graph_data(result['gdr_facebook_url'])
            result.update(og_data)
        
        return result
    
    async def _search_via_google(self, company_name: str, location: str) -> Dict[str, Any]:
        """
        Busca página do Facebook via Google
        """
        try:
            google_api_key = os.getenv('GOOGLE_CSE_API_KEY')
            google_cse_id = os.getenv('GOOGLE_CSE_ID')
            
            if not google_api_key or not google_cse_id:
                return {}
            
            query = f'site:facebook.com "{company_name}" {location}'
            url = f"https://www.googleapis.com/customsearch/v1"
            params = {
                'key': google_api_key,
                'cx': google_cse_id,
                'q': query,
                'num': 3
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        
                        for item in items:
                            link = item.get('link', '')
                            if 'facebook.com' in link and any(x in link for x in ['/pages/', '/people/', '/']):
                                logger.info(f"Facebook encontrado via Google: {link}")
                                return {'url': link}
            
        except Exception as e:
            logger.error(f"Erro ao buscar Facebook via Google: {e}")
        
        return {}
    
    async def _search_via_bing(self, company_name: str, location: str) -> Dict[str, Any]:
        """
        Busca página do Facebook via Bing Web Search (não requer API key)
        """
        try:
            query = f'site:facebook.com "{company_name}" {location}'
            url = f"https://www.bing.com/search?q={quote(query)}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        # Extrair links do Facebook do HTML
                        import re
                        pattern = r'href="(https?://(?:www\.)?facebook\.com/[^"]+)"'
                        matches = re.findall(pattern, html)
                        
                        if matches:
                            # Filtrar e retornar o primeiro link válido
                            for link in matches:
                                if '/pages/' in link or '/people/' in link or link.count('/') == 3:
                                    logger.info(f"Facebook encontrado via Bing: {link}")
                                    return {'url': link}
        
        except Exception as e:
            logger.debug(f"Erro ao buscar via Bing: {e}")
        
        return {}
    
    async def _search_via_duckduckgo(self, company_name: str, location: str) -> Dict[str, Any]:
        """
        Busca página do Facebook via DuckDuckGo (não requer API key)
        """
        try:
            query = f'site:facebook.com "{company_name}" {location}'
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            
            headers = {
                **self.headers,
                'Referer': 'https://duckduckgo.com/'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        # Extrair links do Facebook
                        import re
                        pattern = r'href=".*?(https?://(?:www\.)?facebook\.com/[^"&]+)'
                        matches = re.findall(pattern, html)
                        
                        if matches:
                            for link in matches:
                                if '/pages/' in link or '/people/' in link or link.count('/') == 3:
                                    logger.info(f"Facebook encontrado via DuckDuckGo: {link}")
                                    return {'url': link}
        
        except Exception as e:
            logger.debug(f"Erro ao buscar via DuckDuckGo: {e}")
        
        return {}
    
    async def _extract_open_graph_data(self, url: str) -> Dict[str, Any]:
        """
        Extrai dados de Open Graph meta tags
        """
        result = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Extrair Open Graph tags
                        og_patterns = {
                            'title': r'<meta property="og:title" content="([^"]+)"',
                            'description': r'<meta property="og:description" content="([^"]+)"',
                            'image': r'<meta property="og:image" content="([^"]+)"',
                            'type': r'<meta property="og:type" content="([^"]+)"',
                            'site_name': r'<meta property="og:site_name" content="([^"]+)"'
                        }
                        
                        for key, pattern in og_patterns.items():
                            match = re.search(pattern, html, re.IGNORECASE)
                            if match:
                                value = match.group(1)
                                if key == 'description' and not result.get('gdr_facebook_bio'):
                                    result['gdr_facebook_bio'] = value[:500]
                                elif key == 'type' and not result.get('gdr_facebook_category'):
                                    result['gdr_facebook_category'] = value
                        
                        logger.debug(f"Open Graph data extraído para {url}")
        
        except Exception as e:
            logger.debug(f"Erro ao extrair Open Graph de {url}: {e}")
        
        return result
    
    def _build_probable_urls(self, company_name: str) -> List[str]:
        """
        Constrói múltiplas URLs prováveis do Facebook baseado no nome
        """
        # Limpar e formatar nome
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', company_name)
        # Variações do nome
        formatted = ''.join(word.capitalize() for word in clean_name.split())
        lowercase = clean_name.lower().replace(' ', '')
        with_dots = clean_name.lower().replace(' ', '.')
        with_dash = clean_name.lower().replace(' ', '-')
        with_underscore = clean_name.lower().replace(' ', '_')
        
        # Tentar múltiplas variações
        variations = [
            f"https://www.facebook.com/{formatted}",
            f"https://www.facebook.com/{formatted.lower()}",
            f"https://www.facebook.com/{lowercase}",
            f"https://www.facebook.com/{with_dots}",
            f"https://www.facebook.com/{with_dash}",
            f"https://www.facebook.com/{with_underscore}",
            f"https://www.facebook.com/pages/{formatted}",
            f"https://www.facebook.com/people/{formatted}",
        ]
        
        return variations
    
    async def _verify_url_exists(self, url: str) -> bool:
        """
        Verifica se URL do Facebook existe (sem necessitar login)
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, headers=self.headers, allow_redirects=True) as response:
                    # Facebook retorna 200 mesmo para páginas que não existem
                    # mas redireciona para /login se a página não existe
                    final_url = str(response.url)
                    
                    if response.status == 200 and '/login' not in final_url:
                        return True
                        
        except Exception as e:
            logger.debug(f"Erro ao verificar URL {url}: {e}")
        
        return False
    
    async def _get_public_graph_data(self, username: str) -> Dict[str, Any]:
        """
        Tenta obter dados públicos via Graph API (muito limitado sem token)
        """
        result = {}
        
        try:
            # Tentar endpoint público (geralmente bloqueado, mas vale tentar)
            url = f"https://graph.facebook.com/{username}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result['gdr_facebook_id'] = data.get('id', '')
                        result['gdr_facebook_username'] = data.get('username', username)
                        result['gdr_facebook_category'] = data.get('category', '')
                        
                        logger.info(f"Dados públicos obtidos do Graph API para {username}")
        
        except Exception as e:
            logger.debug(f"Graph API não disponível para {username}: {e}")
        
        return result
    
    async def _extract_from_public_html(self, url: str) -> Dict[str, Any]:
        """
        Extrai dados do HTML público (limitado mas funcional)
        """
        result = {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Extrair dados usando regex no HTML
                        # Nome da página
                        name_match = re.search(r'<title>([^<]+)</title>', html)
                        if name_match:
                            name = name_match.group(1).replace(' | Facebook', '').strip()
                            
                        # Tentar extrair categoria
                        category_match = re.search(r'"category":"([^"]+)"', html)
                        if category_match:
                            result['gdr_facebook_category'] = category_match.group(1)
                        
                        # Tentar extrair descrição/bio
                        bio_match = re.search(r'"description":"([^"]+)"', html)
                        if bio_match:
                            result['gdr_facebook_bio'] = bio_match.group(1)[:500]
                        
                        # Tentar extrair telefone
                        phone_patterns = [
                            r'tel:([+\d\s()-]+)',
                            r'"phone":"([^"]+)"',
                            r'WhatsApp[:\s]*([+\d\s()-]+)'
                        ]
                        
                        for pattern in phone_patterns:
                            phone_match = re.search(pattern, html, re.IGNORECASE)
                            if phone_match:
                                phone = phone_match.group(1)
                                result['gdr_facebook_mobile'] = phone
                                
                                # Se for WhatsApp, adicionar também
                                if 'whatsapp' in pattern.lower():
                                    result['gdr_facebook_whatsapp'] = self._format_whatsapp(phone)
                                break
                        
                        # Tentar extrair email
                        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', html)
                        if email_match:
                            result['gdr_facebook_mail'] = email_match.group(1)
                        
                        # Tentar extrair website
                        website_patterns = [
                            r'"website":"([^"]+)"',
                            r'href="(https?://(?!.*facebook)[^"]+)"'
                        ]
                        
                        for pattern in website_patterns:
                            website_match = re.search(pattern, html)
                            if website_match:
                                website = website_match.group(1)
                                if 'facebook.com' not in website:
                                    result['gdr_facebook_website'] = website
                                    break
                        
                        # Indicadores de verificação
                        if '"is_verified":true' in html or '"verified":true' in html:
                            result['gdr_facebook_is_verified'] = True
                        
                        logger.info(f"Dados extraídos do HTML público para {url}")
        
        except Exception as e:
            logger.error(f"Erro ao extrair HTML de {url}: {e}")
        
        return result
    
    def _extract_username_from_url(self, url: str) -> str:
        """
        Extrai username da URL do Facebook
        """
        # Padrões comuns de URL do Facebook
        patterns = [
            r'facebook\.com/([^/?]+)',
            r'fb\.com/([^/?]+)',
            r'facebook\.com/pages/[^/]+/(\d+)',
            r'facebook\.com/people/[^/]+/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return ''
    
    def _format_whatsapp(self, phone: str) -> str:
        """
        Formata número para WhatsApp
        """
        # Remover caracteres não numéricos
        numbers = ''.join(filter(str.isdigit, phone))
        
        if len(numbers) >= 10:
            if not numbers.startswith('55'):
                return f"+55{numbers}"
            else:
                return f"+{numbers}"
        
        return ''
    
    def _empty_facebook_data(self) -> Dict[str, Any]:
        """
        Retorna estrutura vazia para Facebook
        """
        return {
            'gdr_facebook_url': '',
            'gdr_facebook_mail': '',
            'gdr_facebook_whatsapp': '',
            'gdr_facebook_id': '',
            'gdr_facebook_username': '',
            'gdr_facebook_followers': 0,
            'gdr_facebook_likes': 0,
            'gdr_facebook_category': '',
            'gdr_facebook_bio': '',
            'gdr_facebook_is_verified': False,
            # Campos extras que podemos tentar pegar
            'gdr_facebook_website': '',
            'gdr_facebook_mobile': ''
        }


# Função helper para integração
async def scrape_facebook_smart(company_name: str, location: str = '', url: str = '') -> Dict[str, Any]:
    """
    Função principal para scraping inteligente do Facebook
    """
    scraper = FacebookAlternativeScraper()
    
    # Se já temos URL, extrair username e tentar coletar mais dados
    if url:
        username = scraper._extract_username_from_url(url)
        result = await scraper._extract_from_public_html(url)
        result['gdr_facebook_url'] = url
        result['gdr_facebook_username'] = username
        return result
    
    # Caso contrário, buscar do zero
    return await scraper.scrape_facebook_alternative(company_name, location)