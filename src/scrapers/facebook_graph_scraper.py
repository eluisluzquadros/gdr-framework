#!/usr/bin/env python3
"""
Facebook Graph API Scraper
Alternativa ao scraper com cookies usando a API oficial do Facebook
Requer Facebook Access Token
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


class FacebookGraphScraper:
    """
    Scraper usando Facebook Graph API para dados públicos
    Não requer cookies mas tem limitações de dados disponíveis
    """
    
    def __init__(self):
        """Inicializa o scraper com Graph API"""
        self.access_token = os.getenv('FACEBOOK_ACCESS_TOKEN', '')
        self.app_id = os.getenv('FACEBOOK_APP_ID', '')
        self.app_secret = os.getenv('FACEBOOK_APP_SECRET', '')
        self.base_url = "https://graph.facebook.com/v18.0"
        
        # Se não tem access token mas tem app credentials, gerar token
        if not self.access_token and self.app_id and self.app_secret:
            self.access_token = f"{self.app_id}|{self.app_secret}"
        
        if not self.access_token:
            logger.warning("Facebook Graph API: Sem access token configurado")
    
    async def scrape_facebook_page(self, page_url_or_id: str) -> Dict[str, Any]:
        """
        Obtém informações públicas de uma página do Facebook
        
        Args:
            page_url_or_id: URL da página ou ID/username
            
        Returns:
            Dict com dados da página
        """
        if not self.access_token:
            logger.error("Facebook Graph API: Access token não configurado")
            return self._empty_facebook_data()
        
        # Extrair ID ou username da URL
        page_id = self._extract_page_id(page_url_or_id)
        if not page_id:
            logger.warning(f"Facebook Graph API: Não foi possível extrair ID de {page_url_or_id}")
            return self._empty_facebook_data()
        
        # Campos que queremos buscar
        fields = [
            'id',
            'name',
            'about',
            'category',
            'category_list',
            'description',
            'emails',
            'phone',
            'website',
            'link',
            'username',
            'fan_count',
            'followers_count',
            'location',
            'hours',
            'price_range',
            'rating_count',
            'overall_star_rating',
            'is_verified',
            'verification_status',
            'whatsapp_number',
            'single_line_address',
            'cover'
        ]
        
        # Montar URL da API
        url = f"{self.base_url}/{page_id}"
        params = {
            'fields': ','.join(fields),
            'access_token': self.access_token
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Facebook Graph API: Dados obtidos para {page_id}")
                        return self._parse_graph_response(data, page_url_or_id)
                    else:
                        error_data = await response.json()
                        error_message = error_data.get('error', {}).get('message', 'Unknown error')
                        
                        # Se é erro de permissão, tentar com campos básicos
                        if response.status == 403 or 'permission' in error_message.lower():
                            return await self._scrape_basic_info(page_id, page_url_or_id)
                        
                        logger.error(f"Facebook Graph API: Erro {response.status} - {error_message}")
                        return self._empty_facebook_data()
        
        except asyncio.TimeoutError:
            logger.error(f"Facebook Graph API: Timeout ao buscar {page_id}")
        except Exception as e:
            logger.error(f"Facebook Graph API: Erro ao buscar {page_id}: {e}")
        
        return self._empty_facebook_data()
    
    async def _scrape_basic_info(self, page_id: str, original_url: str) -> Dict[str, Any]:
        """
        Busca apenas informações básicas (menos campos, mais chance de funcionar)
        """
        basic_fields = ['id', 'name', 'category', 'link', 'fan_count', 'is_verified']
        
        url = f"{self.base_url}/{page_id}"
        params = {
            'fields': ','.join(basic_fields),
            'access_token': self.access_token
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Facebook Graph API: Dados básicos obtidos para {page_id}")
                        return self._parse_graph_response(data, original_url)
        except Exception as e:
            logger.error(f"Facebook Graph API: Erro ao buscar dados básicos de {page_id}: {e}")
        
        return self._empty_facebook_data()
    
    def _extract_page_id(self, url_or_id: str) -> Optional[str]:
        """
        Extrai o ID ou username de uma URL do Facebook
        """
        # Se já é um ID ou username simples
        if not url_or_id.startswith('http'):
            return url_or_id.strip('/')
        
        # Patterns para extrair de URLs
        patterns = [
            r'facebook\.com/([^/?#]+)',
            r'fb\.com/([^/?#]+)',
            r'facebook\.com/pages/[^/]+/(\d+)',
            r'facebook\.com/profile\.php\?id=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                page_id = match.group(1)
                # Remover parâmetros extras
                page_id = page_id.split('?')[0].split('#')[0]
                return page_id
        
        return None
    
    def _parse_graph_response(self, data: Dict, original_url: str) -> Dict[str, Any]:
        """
        Converte resposta da Graph API para nosso formato
        """
        # Extrair email (pode estar em emails array ou como string)
        email = ''
        if 'emails' in data and isinstance(data['emails'], list) and data['emails']:
            email = data['emails'][0]
        elif 'email' in data:
            email = data['email']
        
        # Extrair endereço
        address = ''
        if 'single_line_address' in data:
            address = data['single_line_address']
        elif 'location' in data:
            location = data['location']
            if isinstance(location, dict):
                parts = []
                if 'street' in location:
                    parts.append(location['street'])
                if 'city' in location:
                    parts.append(location['city'])
                if 'state' in location:
                    parts.append(location['state'])
                if 'country' in location:
                    parts.append(location['country'])
                address = ', '.join(filter(None, parts))
        
        # Extrair WhatsApp
        whatsapp = data.get('whatsapp_number', '')
        if not whatsapp and 'phone' in data:
            # Tentar converter phone para WhatsApp
            phone = re.sub(r'\D', '', data['phone'])
            if len(phone) >= 10:
                whatsapp = f"https://wa.me/{phone}"
        
        # Montar resposta
        return {
            'gdr_facebook_url': data.get('link', original_url),
            'gdr_facebook_mail': email,
            'gdr_facebook_whatsapp': whatsapp,
            'gdr_facebook_id': data.get('id', ''),
            'gdr_facebook_username': data.get('username', ''),
            'gdr_facebook_followers': data.get('followers_count', data.get('fan_count', 0)),
            'gdr_facebook_likes': data.get('fan_count', 0),
            'gdr_facebook_category': data.get('category', ''),
            'gdr_facebook_bio': data.get('about', data.get('description', '')),
            'gdr_facebook_is_verified': data.get('is_verified', False),
            # Campos extras úteis
            'gdr_facebook_name': data.get('name', ''),
            'gdr_facebook_address': address,
            'gdr_facebook_website': data.get('website', ''),
            'gdr_facebook_phone': data.get('phone', ''),
            'gdr_facebook_rating': data.get('overall_star_rating', 0),
            'gdr_facebook_rating_count': data.get('rating_count', 0),
            'gdr_facebook_price_range': data.get('price_range', ''),
            'gdr_facebook_hours': json.dumps(data.get('hours', {})) if 'hours' in data else ''
        }
    
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
            'gdr_facebook_name': '',
            'gdr_facebook_address': '',
            'gdr_facebook_website': '',
            'gdr_facebook_phone': '',
            'gdr_facebook_rating': 0,
            'gdr_facebook_rating_count': 0,
            'gdr_facebook_price_range': '',
            'gdr_facebook_hours': ''
        }
    
    async def search_facebook_page(self, company_name: str, location: str = '') -> Optional[str]:
        """
        Busca uma página no Facebook pelo nome
        Retorna a URL da página se encontrada
        """
        if not self.access_token:
            return None
        
        # Montar query de busca
        query = company_name
        if location:
            query += f" {location}"
        
        url = f"{self.base_url}/pages/search"
        params = {
            'q': query,
            'fields': 'id,name,link,category,location',
            'access_token': self.access_token,
            'limit': 5
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if 'data' in data and data['data']:
                            # Retornar o primeiro resultado
                            first_result = data['data'][0]
                            return first_result.get('link', f"https://facebook.com/{first_result['id']}")
        except Exception as e:
            logger.error(f"Facebook Graph API: Erro ao buscar página '{query}': {e}")
        
        return None


# Teste standalone
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test():
        scraper = FacebookGraphScraper()
        
        # Testar com diferentes URLs
        test_urls = [
            "https://www.facebook.com/assistencia.casanova/",
            "https://www.facebook.com/CellCompany01",
            "assistencia.casanova",  # Só o username
            "123456789"  # ID numérico
        ]
        
        for url in test_urls:
            print(f"\nTestando: {url}")
            result = await scraper.scrape_facebook_page(url)
            
            if result['gdr_facebook_name']:
                print(f"  Nome: {result['gdr_facebook_name']}")
                print(f"  Categoria: {result['gdr_facebook_category']}")
                print(f"  Seguidores: {result['gdr_facebook_followers']}")
                print(f"  Verificado: {result['gdr_facebook_is_verified']}")
                print(f"  Website: {result['gdr_facebook_website']}")
                print(f"  Email: {result['gdr_facebook_mail']}")
            else:
                print("  [Sem dados]")
        
        # Testar busca
        print("\n\nTestando busca:")
        url = await scraper.search_facebook_page("Bred Capas", "Bagé RS")
        print(f"  Resultado da busca: {url}")
    
    asyncio.run(test())