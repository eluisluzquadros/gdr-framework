#!/usr/bin/env python3
"""
Enhanced Website Scraper
Suporta sites estáticos (BeautifulSoup) e dinâmicos (Selenium como fallback)
Integra crawl4ai para sites da coluna original_website
"""

import os
import re
import json
import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional, Union
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Tentar importar Selenium (opcional)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium não disponível - apenas sites estáticos serão processados")

# Tentar importar crawl4ai
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("Crawl4AI não disponível - usando scraper alternativo")


class EnhancedWebsiteScraper:
    """
    Scraper melhorado que suporta sites estáticos e dinâmicos
    """
    
    def __init__(self):
        """Inicializa o scraper"""
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Padrões de extração
        self.email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]
        
        self.phone_patterns = [
            r'\(?\d{2}\)?\s*\d{4,5}[-.\s]?\d{4}',  # Brasileiro
            r'\+55\s*\d{2}\s*\d{4,5}[-.\s]?\d{4}',  # +55
            r'tel:([+\d\s()-]+)',
            r'phone:([+\d\s()-]+)'
        ]
        
        self.whatsapp_patterns = [
            r'wa\.me/(\d+)',
            r'api\.whatsapp\.com/send\?phone=(\d+)',
            r'whatsapp://send\?phone=(\d+)',
            r'whatsapp[:\s]*([+\d\s()-]+)'
        ]
        
        self.social_patterns = {
            'instagram': r'(?:instagram\.com|instagr\.am)/([^/?#\s]+)',
            'facebook': r'(?:facebook\.com|fb\.com)/([^/?#\s]+)',
            'linkedin': r'linkedin\.com/(?:company|in)/([^/?#\s]+)',
            'youtube': r'(?:youtube\.com|youtu\.be)/(?:c/|channel/|user/)?([^/?#\s]+)',
            'twitter': r'(?:twitter\.com|x\.com)/([^/?#\s]+)',
            'tiktok': r'tiktok\.com/@([^/?#\s]+)'
        }
    
    async def scrape_website_smart(self, url: Any, use_crawl4ai: bool = False) -> Dict[str, Any]:
        """
        Scraping inteligente que escolhe a melhor estratégia
        Corrigido para lidar com URLs como float/NaN do Excel
        """
        # Validação de tipo - trata float, NaN, None
        if url is None or (isinstance(url, float) and str(url).lower() == 'nan'):
            return self._empty_website_data()
        
        # Converter para string e validar
        try:
            url = str(url).strip()
        except:
            return self._empty_website_data()
        
        # Verificar se é válido
        if not url or url.lower() in ['nan', 'none', '']:
            return self._empty_website_data()
        
        # Adicionar protocolo se necessário
        if not url.startswith(('http://', 'https://')):
            url = f'https://{url}'
        
        result = {}
        
        # Estratégia 1: Tentar crawl4ai se disponível e solicitado
        if use_crawl4ai and CRAWL4AI_AVAILABLE:
            logger.info(f"Usando Crawl4AI para {url}")
            result = await self._scrape_with_crawl4ai(url)
            if self._has_valid_data(result):
                return result
        
        # Estratégia 2: Tentar scraping estático (rápido)
        logger.info(f"Tentando scraping estático para {url}")
        result = await self._scrape_static(url)
        
        # Se é um site dinâmico conhecido e não obtivemos dados
        if self._is_dynamic_site(url) and not self._has_valid_data(result):
            # Estratégia 3: Usar Selenium se disponível
            if SELENIUM_AVAILABLE:
                logger.info(f"Site dinâmico detectado, usando Selenium para {url}")
                result = await self._scrape_dynamic(url)
        
        return result if result else self._empty_website_data()
    
    async def _scrape_with_crawl4ai(self, url: str) -> Dict[str, Any]:
        """
        Usa Crawl4AI para scraping avançado
        """
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                
                if result.success:
                    # Extrair dados do resultado
                    text = result.text
                    html = result.html
                    
                    return self._extract_data_from_content(text, html, url)
        
        except Exception as e:
            logger.error(f"Erro com Crawl4AI em {url}: {e}")
        
        return {}
    
    async def _scrape_static(self, url: str) -> Dict[str, Any]:
        """
        Scraping tradicional com BeautifulSoup
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status != 200:
                        logger.warning(f"Status {response.status} para {url}")
                        return {}
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    text = soup.get_text()
                    
                    # Extrair dados
                    result = self._extract_data_from_content(text, str(soup), url)
                    
                    # Buscar links de contato
                    contact_links = self._find_contact_pages(soup, url)
                    if contact_links and not self._has_valid_data(result):
                        # Tentar página de contato
                        for contact_url in contact_links[:2]:  # Máximo 2 tentativas
                            contact_data = await self._scrape_static(contact_url)
                            result.update(contact_data)
                            if self._has_valid_data(result):
                                break
                    
                    return result
        
        except Exception as e:
            logger.error(f"Erro no scraping estático de {url}: {e}")
        
        return {}
    
    async def _scrape_dynamic(self, url: str) -> Dict[str, Any]:
        """
        Scraping com Selenium para sites dinâmicos
        """
        if not SELENIUM_AVAILABLE:
            return {}
        
        driver = None
        try:
            # Configurar Chrome options
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            # Criar driver
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            
            # Aguardar carregamento
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Aguardar um pouco para JavaScript carregar
            await asyncio.sleep(2)
            
            # Pegar HTML renderizado
            html = driver.page_source
            text = driver.find_element(By.TAG_NAME, "body").text
            
            # Extrair dados
            result = self._extract_data_from_content(text, html, url)
            
            # Tentar clicar em botões de "mostrar mais" para emails/telefones
            try:
                show_more_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'contato') or contains(text(), 'email') or contains(text(), 'telefone')]")
                for button in show_more_buttons[:3]:
                    try:
                        button.click()
                        await asyncio.sleep(0.5)
                    except:
                        pass
                
                # Re-extrair após cliques
                html = driver.page_source
                text = driver.find_element(By.TAG_NAME, "body").text
                new_data = self._extract_data_from_content(text, html, url)
                result.update(new_data)
            
            except:
                pass
            
            return result
        
        except Exception as e:
            logger.error(f"Erro no scraping dinâmico de {url}: {e}")
        
        finally:
            if driver:
                driver.quit()
        
        return {}
    
    def _extract_data_from_content(self, text: str, html: str, url: str) -> Dict[str, Any]:
        """
        Extrai dados do conteúdo (texto e HTML)
        """
        result = {'gdr_cwral4ai_url': url}
        
        # Combinar texto e HTML para busca
        combined = f"{text}\n{html}"
        
        # Extrair emails
        emails = []
        for pattern in self.email_patterns:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            emails.extend(matches)
        
        # Filtrar emails válidos e únicos
        valid_emails = []
        for email in emails:
            if isinstance(email, tuple):
                email = email[0]
            email = email.lower().strip()
            if '@' in email and '.' in email and email not in valid_emails:
                # Filtrar emails genéricos
                if not any(generic in email for generic in ['example.com', 'email.com', 'domain.com', 'sentry.io']):
                    valid_emails.append(email)
        
        if valid_emails:
            result['gdr_cwral4ai_email'] = valid_emails[0]
        
        # Extrair telefones
        phones = []
        for pattern in self.phone_patterns:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            phones.extend(matches)
        
        # Limpar e validar telefones
        valid_phones = []
        for phone in phones:
            if isinstance(phone, tuple):
                phone = phone[0]
            # Limpar número
            clean_phone = ''.join(filter(lambda x: x.isdigit() or x in '+- ()', str(phone)))
            if len(re.sub(r'\D', '', clean_phone)) >= 10:
                if clean_phone not in valid_phones:
                    valid_phones.append(clean_phone)
        
        if valid_phones:
            result['gdr_cwral4ai_telefone'] = valid_phones[0]
        
        # Extrair WhatsApp
        for pattern in self.whatsapp_patterns:
            matches = re.findall(pattern, combined, re.IGNORECASE)
            if matches:
                whatsapp = matches[0] if isinstance(matches[0], str) else matches[0][0]
                result['gdr_cwral4ai_whatsapp'] = self._format_whatsapp(whatsapp)
                break
        
        # Se não encontrou WhatsApp mas tem telefone, assumir que pode ser WhatsApp
        if not result.get('gdr_cwral4ai_whatsapp') and result.get('gdr_cwral4ai_telefone'):
            result['gdr_cwral4ai_whatsapp'] = self._format_whatsapp(result['gdr_cwral4ai_telefone'])
        
        # Extrair redes sociais
        social_urls = {}
        for platform, pattern in self.social_patterns.items():
            matches = re.findall(pattern, combined, re.IGNORECASE)
            if matches:
                username = matches[0] if isinstance(matches[0], str) else matches[0][0]
                if platform == 'youtube':
                    social_urls[platform] = f"https://youtube.com/{username}"
                else:
                    social_urls[platform] = username
        
        # Adicionar YouTube se encontrado
        if 'youtube' in social_urls:
            result['gdr_cwral4ai_youtube_url'] = social_urls['youtube']
        
        # Guardar outras redes sociais encontradas
        result['gdr_cwral4ai_social_urls'] = json.dumps(social_urls)
        
        logger.info(f"Extraídos de {url}: {1 if result.get('gdr_cwral4ai_email') else 0} email, "
                   f"{1 if result.get('gdr_cwral4ai_telefone') else 0} telefone, "
                   f"{len(social_urls)} redes sociais")
        
        return result
    
    def _find_contact_pages(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Encontra links para páginas de contato
        """
        contact_urls = []
        
        # Palavras-chave para páginas de contato
        keywords = ['contato', 'contact', 'fale-conosco', 'atendimento', 'telefone', 'email']
        
        # Buscar links
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            # Verificar se é link de contato
            if any(keyword in text or keyword in href.lower() for keyword in keywords):
                # Construir URL completa
                full_url = urljoin(base_url, href)
                if full_url not in contact_urls and full_url != base_url:
                    contact_urls.append(full_url)
        
        return contact_urls[:3]  # Máximo 3 páginas de contato
    
    def _is_dynamic_site(self, url: str) -> bool:
        """
        Verifica se é um site dinâmico conhecido
        """
        dynamic_sites = [
            'instagram.com',
            'facebook.com',
            'twitter.com',
            'x.com',
            'linkedin.com',
            'tiktok.com',
            'youtube.com'
        ]
        
        domain = urlparse(url).netloc.lower()
        return any(site in domain for site in dynamic_sites)
    
    def _has_valid_data(self, data: Dict) -> bool:
        """
        Verifica se os dados extraídos são válidos
        """
        return bool(
            data.get('gdr_cwral4ai_email') or 
            data.get('gdr_cwral4ai_telefone') or 
            data.get('gdr_cwral4ai_whatsapp')
        )
    
    def _format_whatsapp(self, phone: str) -> str:
        """
        Formata número para WhatsApp
        """
        if not phone:
            return ''
        
        # Remover caracteres não numéricos
        numbers = ''.join(filter(str.isdigit, str(phone)))
        
        if len(numbers) >= 10:
            if not numbers.startswith('55'):
                return f"+55{numbers}"
            else:
                return f"+{numbers}"
        
        return ''
    
    def _empty_website_data(self) -> Dict[str, Any]:
        """
        Retorna estrutura vazia
        """
        return {
            'gdr_cwral4ai_url': '',
            'gdr_cwral4ai_email': '',
            'gdr_cwral4ai_telefone': '',
            'gdr_cwral4ai_whatsapp': '',
            'gdr_cwral4ai_youtube_url': ''
        }