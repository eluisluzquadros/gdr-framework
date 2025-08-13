#!/usr/bin/env python3
"""
Scrapers REAIS usando APIs Apify
Implementa coleta de dados reais do Instagram, Facebook e Linktree
"""

import os
import json
import asyncio
import aiohttp
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import time
import re

logger = logging.getLogger(__name__)


class ApifyRealScrapers:
    """Implementação REAL dos scrapers Apify"""
    
    def __init__(self):
        """Inicializa com API keys do Apify"""
        self.api_key = os.getenv('APIFY_API_KEY')  # Para Instagram e Facebook
        self.api_key_linktree = os.getenv('APIFY_API_KEY_LINKTREE')  # Para Linktree
        
        if not self.api_key:
            logger.warning("APIFY_API_KEY não configurada - Instagram/Facebook retornarão dados vazios")
        if not self.api_key_linktree:
            logger.warning("APIFY_API_KEY_LINKTREE não configurada - Linktree retornará dados vazios")
    
    async def scrape_instagram_profile(self, username: str) -> Dict[str, Any]:
        """
        Scraper REAL do Instagram via Apify
        Retorna dados reais conforme schema da API
        """
        if not self.api_key:
            logger.warning(f"Instagram scraper: API key não configurada para {username}")
            return self._empty_instagram_data()
        
        # Actor ID do Instagram Profile Scraper
        actor_id = "apify/instagram-profile-scraper"
        
        # Preparar input
        run_input = {
            "usernames": [username.replace('@', '').strip()]
        }
        
        try:
            # Usar Apify Client Python SDK
            from apify_client import ApifyClient
            client = ApifyClient(self.api_key)
            
            # Executar o actor
            logger.info(f"Instagram: Iniciando scraping REAL de @{username}")
            run = client.actor(actor_id).call(run_input=run_input)
            
            # Obter resultados
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)
            
            if results and len(results) > 0:
                profile = results[0]
                logger.info(f"Instagram: Dados REAIS coletados para @{username}")
                
                # Mapear para nosso schema
                return {
                    'gdr_instagram_url': profile.get('url', f"https://instagram.com/{username}"),
                    'gdr_instagram_id': profile.get('id', ''),
                    'gdr_instagram_username': profile.get('username', username),
                    'gdr_instagram_followers': profile.get('followersCount', 0),
                    'gdr_instagram_following': profile.get('followsCount', 0),
                    'gdr_instagram_bio': profile.get('biography', ''),
                    'gdr_instagram_is_verified': profile.get('verified', False),
                    'gdr_instagram_is_business': profile.get('isBusinessAccount', False),
                    # Campos extras úteis
                    'gdr_instagram_full_name': profile.get('fullName', ''),
                    'gdr_instagram_external_url': profile.get('externalUrl', ''),
                    'gdr_instagram_profile_pic': profile.get('profilePicUrl', ''),
                    'gdr_instagram_business_category': profile.get('businessCategoryName', ''),
                    'gdr_instagram_is_private': profile.get('private', False)
                }
            
            logger.warning(f"Instagram: Nenhum resultado para @{username}")
                
        except Exception as e:
            logger.error(f"Instagram: Erro ao buscar dados de {username}: {e}")
        
        return self._empty_instagram_data()
    
    async def scrape_facebook_profile(self, profile_url: str) -> Dict[str, Any]:
        """
        Scraper REAL do Facebook via Apify
        Retorna dados reais conforme schema da API
        """
        if not self.api_key:
            logger.warning(f"Facebook scraper: API key não configurada para {profile_url}")
            return self._empty_facebook_data()
        
        # Actor ID do Facebook Profile Scraper
        actor_id = "curious_coder/facebook-profile-scraper"
        
        # Preparar input
        run_input = {
            "profileUrls": [profile_url],
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyCountry": "US"
            },
            "minDelay": 1,
            "maxDelay": 5
        }
        
        try:
            # Usar Apify Client Python SDK
            from apify_client import ApifyClient
            client = ApifyClient(self.api_key)
            
            # Executar o actor
            logger.info(f"Facebook: Iniciando scraping REAL de {profile_url}")
            run = client.actor(actor_id).call(run_input=run_input)
            
            # Obter resultados
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)
                
            if results and len(results) > 0:
                profile = results[0]
                logger.info(f"Facebook: Dados REAIS coletados")
                
                # Mapear para nosso schema
                return {
                    'gdr_facebook_url': profile.get('url', profile_url),
                    'gdr_facebook_mail': profile.get('email', ''),
                    'gdr_facebook_whatsapp': self._extract_whatsapp(profile.get('mobile', '')),
                    'gdr_facebook_id': profile.get('id', ''),
                    'gdr_facebook_username': profile.get('username_for_profile', ''),
                    'gdr_facebook_followers': self._parse_followers(profile.get('followers', '0')),
                    'gdr_facebook_likes': self._parse_followers(profile.get('likes', '0')),
                    'gdr_facebook_category': profile.get('category', profile.get('influencer_category', '')),
                    'gdr_facebook_bio': profile.get('bio', ''),
                    'gdr_facebook_is_verified': profile.get('is_verified', False),
                    # Campos extras úteis
                    'gdr_facebook_name': profile.get('name', ''),
                    'gdr_facebook_address': profile.get('address', ''),
                    'gdr_facebook_website': profile.get('website', ''),
                    'gdr_facebook_mobile': profile.get('mobile', ''),
                    'gdr_facebook_ratings': profile.get('ratings', ''),
                    'gdr_facebook_hours': profile.get('hours', ''),
                    'gdr_facebook_price_range': profile.get('price', ''),
                    'gdr_facebook_services': profile.get('services', '')
                }
            
            logger.warning(f"Facebook: Nenhum resultado para {profile_url}")
        
        except Exception as e:
            logger.error(f"Facebook: Erro ao buscar dados de {profile_url}: {e}")
        
        return self._empty_facebook_data()
    
    async def scrape_linktree_profile(self, username_or_url: str) -> Dict[str, Any]:
        """
        Scraper REAL do Linktree via Apify
        Retorna dados reais conforme schema da API
        """
        # Usar API key específica do Linktree
        if not self.api_key_linktree:
            logger.warning(f"Linktree scraper: APIFY_API_KEY_LINKTREE não configurada para {username_or_url}")
            return self._empty_linktree_data()
        
        # Actor ID do Linktree Profile Details Scraper
        actor_id = "ecomscrape/linktree-profile-details-scraper"
        
        # Preparar URL
        if not username_or_url.startswith('http'):
            url = f"https://linktr.ee/{username_or_url}"
        else:
            url = username_or_url
        
        # Preparar input
        run_input = {
            "urls_or_usernames": [url],
            "max_retries_per_url": 2,
            "proxy": {"useApifyProxy": False}
        }
        
        try:
            # Usar Apify Client Python SDK com API key específica do Linktree
            from apify_client import ApifyClient
            client = ApifyClient(self.api_key_linktree)  # Usar API key do Linktree
            
            # Executar o actor
            logger.info(f"Linktree: Iniciando scraping REAL de {url} com API key específica")
            run = client.actor(actor_id).call(run_input=run_input)
            
            # Obter resultados
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                results.append(item)
            
            if results and len(results) > 0:
                profile = results[0]
                logger.info(f"Linktree: Dados REAIS coletados")
                
                # Extrair links e URLs sociais
                links = profile.get('links', [])
                social_urls = profile.get('social_urls', [])
                
                # Procurar LinkedIn nos links
                linkedin_url = ''
                for link in links:
                    if 'linkedin' in link.get('url', '').lower():
                        linkedin_url = link['url']
                        break
                
                # Mapear para nosso schema
                return {
                    'gdr_linktree_username': profile.get('username', ''),
                    'gdr_linktree_title': profile.get('title', ''),
                    'gdr_linktree_description': profile.get('description', ''),
                    'gdr_linktree_social_urls': json.dumps(social_urls),
                    'gdr_linktree_links_details': json.dumps(links),
                    'gdr_linkedin_url': linkedin_url,
                    # Campos extras úteis
                    'gdr_linktree_profile_picture': profile.get('profile_picture', ''),
                    'gdr_linktree_from_url': profile.get('from_url', url),
                    'gdr_linktree_total_links': len(links)
                }
            
            logger.warning(f"Linktree: Nenhum resultado para {username_or_url}")
        
        except Exception as e:
            logger.error(f"Linktree: Erro ao buscar dados de {username_or_url}: {e}")
        
        return self._empty_linktree_data()
    
    def _extract_whatsapp(self, mobile: str) -> str:
        """Extrai WhatsApp do número de telefone"""
        if not mobile:
            return ''
        
        # Remover caracteres não numéricos
        numbers = ''.join(filter(str.isdigit, mobile))
        
        # Formatar para WhatsApp
        if len(numbers) >= 10:
            if not numbers.startswith('55'):
                return f"+55{numbers}"
            else:
                return f"+{numbers}"
        
        return ''
    
    def _parse_followers(self, followers_str: str) -> int:
        """Converte string de followers para número"""
        if not followers_str:
            return 0
        
        # Remover texto e deixar apenas números
        followers_str = followers_str.upper().replace(',', '').replace('.', '')
        
        # Converter K, M para números
        if 'K' in followers_str:
            try:
                num = float(followers_str.replace('K', ''))
                return int(num * 1000)
            except:
                pass
        elif 'M' in followers_str:
            try:
                num = float(followers_str.replace('M', ''))
                return int(num * 1000000)
            except:
                pass
        
        # Tentar converter diretamente
        try:
            return int(''.join(filter(str.isdigit, followers_str)))
        except:
            return 0
    
    def _empty_instagram_data(self) -> Dict[str, Any]:
        """Retorna estrutura vazia para Instagram"""
        return {
            'gdr_instagram_url': '',
            'gdr_instagram_id': '',
            'gdr_instagram_username': '',
            'gdr_instagram_followers': 0,
            'gdr_instagram_following': 0,
            'gdr_instagram_bio': '',
            'gdr_instagram_is_verified': False,
            'gdr_instagram_is_business': False
        }
    
    def _empty_facebook_data(self) -> Dict[str, Any]:
        """Retorna estrutura vazia para Facebook"""
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
            'gdr_facebook_is_verified': False
        }
    
    def _empty_linktree_data(self) -> Dict[str, Any]:
        """Retorna estrutura vazia para Linktree"""
        return {
            'gdr_linktree_username': '',
            'gdr_linktree_title': '',
            'gdr_linktree_description': '',
            'gdr_linktree_social_urls': '[]',
            'gdr_linktree_links_details': '[]',
            'gdr_linkedin_url': ''
        }


class WebScraperReal:
    """Scraper real de websites usando BeautifulSoup/requests"""
    
    def __init__(self):
        self.session = None
        self.timeout = 30
    
    async def scrape_website(self, url: str) -> Dict[str, Any]:
        """
        Scraper real de website para extrair contatos
        """
        if not url or not url.startswith('http'):
            return self._empty_website_data()
        
        try:
            import aiohttp
            from bs4 import BeautifulSoup
            import re
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.timeout) as response:
                    if response.status != 200:
                        logger.warning(f"Website scraper: Status {response.status} para {url}")
                        return self._empty_website_data()
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extrair texto da página
                    text = soup.get_text()
                    
                    # Buscar emails
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    emails = re.findall(email_pattern, text)
                    email = emails[0] if emails else ''
                    
                    # Buscar telefones brasileiros
                    phone_patterns = [
                        r'\(\d{2}\)\s*\d{4,5}[-.\s]?\d{4}',  # (11) 98765-4321
                        r'\d{2}\s*\d{4,5}[-.\s]?\d{4}',       # 11 98765-4321
                        r'\+55\s*\d{2}\s*\d{4,5}[-.\s]?\d{4}' # +55 11 98765-4321
                    ]
                    
                    phones = []
                    for pattern in phone_patterns:
                        phones.extend(re.findall(pattern, text))
                    
                    phone = phones[0] if phones else ''
                    
                    # Buscar WhatsApp
                    whatsapp = ''
                    whatsapp_patterns = [
                        r'whatsapp[:\s]*([+\d\s()-]+)',
                        r'wa\.me/(\d+)',
                        r'api\.whatsapp\.com/send\?phone=(\d+)'
                    ]
                    
                    for pattern in whatsapp_patterns:
                        matches = re.findall(pattern, text.lower())
                        if matches:
                            whatsapp = matches[0]
                            break
                    
                    # Buscar YouTube
                    youtube_pattern = r'(youtube\.com/[@\w-]+|youtu\.be/[\w-]+)'
                    youtube_matches = re.findall(youtube_pattern, text)
                    youtube = f"https://{youtube_matches[0]}" if youtube_matches else ''
                    
                    logger.info(f"Website: Extraídos {1 if email else 0} email, {1 if phone else 0} telefone")
                    
                    return {
                        'gdr_cwral4ai_url': url,
                        'gdr_cwral4ai_email': email,
                        'gdr_cwral4ai_telefone': phone,
                        'gdr_cwral4ai_whatsapp': self._format_whatsapp(whatsapp or phone),
                        'gdr_cwral4ai_youtube_url': youtube
                    }
        
        except Exception as e:
            logger.error(f"Website scraper: Erro ao processar {url}: {e}")
        
        return self._empty_website_data()
    
    def _format_whatsapp(self, phone: str) -> str:
        """Formata número para WhatsApp"""
        if not phone:
            return ''
        
        numbers = ''.join(filter(str.isdigit, phone))
        if len(numbers) >= 10:
            if not numbers.startswith('55'):
                return f"+55{numbers}"
            else:
                return f"+{numbers}"
        return ''
    
    def _empty_website_data(self) -> Dict[str, Any]:
        """Retorna estrutura vazia para website"""
        return {
            'gdr_cwral4ai_url': '',
            'gdr_cwral4ai_email': '',
            'gdr_cwral4ai_telefone': '',
            'gdr_cwral4ai_whatsapp': '',
            'gdr_cwral4ai_youtube_url': ''
        }


class GoogleSearchEngineReal:
    """Scraper real usando Google Custom Search API"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_CSE_API_KEY')
        self.cse_id = os.getenv('GOOGLE_CSE_ID')
        
        if not self.api_key or not self.cse_id:
            logger.warning("Google Search: API key ou CSE ID não configurados")
    
    async def search_company_info(self, company_name: str, location: str = '') -> Dict[str, Any]:
        """
        Busca informações da empresa no Google
        IMPORTANTE: Usa nome + endereço completo para melhor precisão
        """
        if not self.api_key or not self.cse_id:
            return self._empty_search_data()
        
        try:
            # Montar query inteligente - nome + localização
            # Não usar termos muito restritivos que podem eliminar resultados
            query = f'{company_name}'
            if location:
                # Adicionar localização para melhor precisão
                query += f' {location}'
            
            # URL da API
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': self.api_key,
                'cx': self.cse_id,
                'q': query,
                'num': 10  # Número de resultados
            }
            
            logger.info(f"Google Search: Buscando '{query}'")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Google Search: Status {response.status}")
                        return self._empty_search_data()
                    
                    data = await response.json()
                    
                    # Processar resultados
                    email = ''
                    phone = ''
                    website = ''
                    whatsapp = ''
                    youtube = ''
                    
                    items_found = len(data.get('items', []))
                    total_results = data.get('searchInformation', {}).get('totalResults', 0)
                    logger.info(f"Google Search: {items_found} de {total_results} resultados")
                    
                    for item in data.get('items', []):
                        snippet = item.get('snippet', '')
                        link = item.get('link', '')
                        title = item.get('title', '')
                        
                        # Combinar title + snippet para melhor extração
                        full_text = f"{title} {snippet}"
                        
                        # Buscar email no texto completo
                        if not email:
                            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text)
                            if email_match:
                                email = email_match.group()
                        
                        # Buscar telefone no texto completo
                        if not phone:
                            phone_patterns = [
                                r'\(\d{2}\)\s*\d{4,5}[-.\s]?\d{4}',
                                r'\d{2}\s*\d{4,5}[-.\s]?\d{4}',
                                r'\+55\s*\d{2}\s*\d{4,5}[-.\s]?\d{4}'
                            ]
                            for pattern in phone_patterns:
                                phone_match = re.search(pattern, full_text)
                                if phone_match:
                                    phone = phone_match.group()
                                    break
                        
                        # Buscar website principal
                        # Priorizar Instagram/Facebook da empresa
                        if not website:
                            company_name_clean = re.sub(r'[^a-z0-9]', '', company_name.lower())
                            link_clean = link.lower()
                            
                            # Verificar se é página da empresa
                            if any([
                                company_name_clean in link_clean,
                                'instagram.com' in link_clean and company_name_clean[:10] in link_clean,
                                'facebook.com' in link_clean and company_name_clean[:10] in link_clean
                            ]):
                                website = link
                        
                        # Buscar YouTube
                        if not youtube and 'youtube.com' in link:
                            youtube = link
                    
                    # Se não encontrou website, usar o primeiro resultado
                    if not website and data.get('items'):
                        website = data['items'][0].get('link', '')
                    
                    return {
                        'gdr_google_search_engine_url': website,
                        'gdr_google_search_engine_email': email,
                        'gdr_google_search_engine_telefone': phone,
                        'gdr_google_search_engine_whatsapp': self._format_whatsapp(whatsapp or phone),
                        'gdr_google_search_engine_youtube_url': youtube
                    }
        
        except Exception as e:
            logger.error(f"Google Search: Erro ao buscar {company_name}: {e}")
        
        return self._empty_search_data()
    
    def _format_whatsapp(self, phone: str) -> str:
        """Formata número para WhatsApp"""
        if not phone:
            return ''
        
        numbers = ''.join(filter(str.isdigit, phone))
        if len(numbers) >= 10:
            if not numbers.startswith('55'):
                return f"+55{numbers}"
            else:
                return f"+{numbers}"
        return ''
    
    def _empty_search_data(self) -> Dict[str, Any]:
        """Retorna estrutura vazia para search"""
        return {
            'gdr_google_search_engine_url': '',
            'gdr_google_search_engine_email': '',
            'gdr_google_search_engine_telefone': '',
            'gdr_google_search_engine_whatsapp': '',
            'gdr_google_search_engine_youtube_url': ''
        }