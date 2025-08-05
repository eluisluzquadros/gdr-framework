#!/usr/bin/env python3
"""
GDR Google Places Collector
Coleta leads diretamente do Google Places API baseado em segmento + localização
"""

import asyncio
import aiohttp
import pandas as pd
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import os
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PlacesSearchConfig:
    """Configuração para busca no Google Places"""
    query: str  # Ex: "assistência técnica celular"
    location: str  # Ex: "Santa Cruz do Sul, RS"
    radius: int = 10000  # Raio em metros
    business_types: List[str] = None  # Ex: ["electronics_store", "phone_repair"]
    min_rating: float = 0.0
    max_results: int = 60  # Máximo por busca

class GooglePlacesCollector:
    """Coletor de leads usando Google Places API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_businesses(self, config: PlacesSearchConfig) -> List[Dict[str, Any]]:
        """Busca negócios baseado na configuração"""
        
        logger.info(f"Buscando: '{config.query}' em {config.location}")
        
        # Primeiro, buscar pela query geral
        places = []
        
        # Text Search
        text_places = await self._text_search(config.query, config.location)
        places.extend(text_places)
        
        # Nearby Search (se temos coordenadas)
        if config.business_types:
            coords = await self._geocode_location(config.location)
            if coords:
                for business_type in config.business_types:
                    nearby_places = await self._nearby_search(
                        coords['lat'], coords['lng'], 
                        config.radius, business_type
                    )
                    places.extend(nearby_places)
        
        # Remover duplicatas
        unique_places = self._deduplicate_places(places)
        
        # Filtrar por rating
        if config.min_rating > 0:
            unique_places = [p for p in unique_places if p.get('rating', 0) >= config.min_rating]
        
        # Limitar resultados
        if len(unique_places) > config.max_results:
            unique_places = unique_places[:config.max_results]
        
        logger.info(f"Encontrados {len(unique_places)} negócios únicos")
        
        # Buscar detalhes para cada lugar
        detailed_places = []
        for i, place in enumerate(unique_places):
            logger.info(f"Coletando detalhes {i+1}/{len(unique_places)}: {place.get('name', 'Unknown')}")
            
            details = await self._get_place_details(place['place_id'])
            if details:
                # Combinar dados básicos + detalhes
                combined = {**place, **details}
                detailed_places.append(combined)
            
            # Rate limiting
            await asyncio.sleep(0.1)
        
        return detailed_places
    
    async def _text_search(self, query: str, location: str) -> List[Dict[str, Any]]:
        """Busca por texto"""
        
        search_query = f"{query} {location}"
        
        params = {
            'query': search_query,
            'key': self.api_key,
            'language': 'pt-BR',
            'region': 'br'
        }
        
        url = f"{self.base_url}/textsearch/json"
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data['status'] == 'OK':
                    return data.get('results', [])
                else:
                    logger.warning(f"Text search error: {data['status']}")
                    return []
                    
        except Exception as e:
            logger.error(f"Erro na busca por texto: {e}")
            return []
    
    async def _nearby_search(self, lat: float, lng: float, radius: int, place_type: str) -> List[Dict[str, Any]]:
        """Busca negócios próximos por tipo"""
        
        params = {
            'location': f"{lat},{lng}",
            'radius': radius,
            'type': place_type,
            'key': self.api_key,
            'language': 'pt-BR'
        }
        
        url = f"{self.base_url}/nearbysearch/json"
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data['status'] == 'OK':
                    return data.get('results', [])
                else:
                    logger.warning(f"Nearby search error: {data['status']}")
                    return []
                    
        except Exception as e:
            logger.error(f"Erro na busca nearby: {e}")
            return []
    
    async def _geocode_location(self, location: str) -> Optional[Dict[str, float]]:
        """Converte endereço em coordenadas"""
        
        params = {
            'address': location,
            'key': self.api_key,
            'language': 'pt-BR',
            'region': 'br'
        }
        
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data['status'] == 'OK' and data['results']:
                    coords = data['results'][0]['geometry']['location']
                    return {'lat': coords['lat'], 'lng': coords['lng']}
                    
        except Exception as e:
            logger.error(f"Erro no geocoding: {e}")
            
        return None
    
    async def _get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Busca detalhes completos de um lugar"""
        
        fields = [
            'name', 'formatted_address', 'formatted_phone_number',
            'international_phone_number', 'website', 'url',
            'rating', 'user_ratings_total', 'reviews',
            'opening_hours', 'geometry', 'types',
            'price_level', 'photos', 'business_status'
        ]
        
        params = {
            'place_id': place_id,
            'fields': ','.join(fields),
            'key': self.api_key,
            'language': 'pt-BR'
        }
        
        url = f"{self.base_url}/details/json"
        
        try:
            async with self.session.get(url, params=params) as response:
                data = await response.json()
                
                if data['status'] == 'OK':
                    return data.get('result', {})
                else:
                    logger.warning(f"Details error for {place_id}: {data['status']}")
                    return None
                    
        except Exception as e:
            logger.error(f"Erro nos detalhes para {place_id}: {e}")
            return None
    
    def _deduplicate_places(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove lugares duplicados"""
        
        seen_place_ids = set()
        unique_places = []
        
        for place in places:
            place_id = place.get('place_id')
            if place_id and place_id not in seen_place_ids:
                seen_place_ids.add(place_id)
                unique_places.append(place)
        
        return unique_places
    
    def format_leads_for_gdr(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Formata dados do Places para o formato esperado pelo GDR"""
        
        formatted_leads = []
        
        for i, place in enumerate(places):
            # Extrair componentes do endereço
            address_components = self._parse_address(place.get('formatted_address', ''))
            
            # Extrair reviews resumidos
            reviews_summary = self._summarize_reviews(place.get('reviews', []))
            
            formatted_lead = {
                'id': i + 1,
                'name': place.get('name', ''),
                'tradeName': place.get('name', ''),
                'personType': 'J',  # Jurídica
                'email': None,  # Será coletado pelos scrapers
                'phone': self._clean_phone(place.get('formatted_phone_number')),
                'mobilePhone': None,
                'status': 'NEW',
                'statusDate': datetime.now().isoformat(),
                'website': place.get('website'),
                'observations': reviews_summary,
                'legalDocument': place.get('place_id'),  # Usar Place ID como identificador
                'street': address_components.get('street', ''),
                'number': address_components.get('number', ''),
                'complement': None,
                'district': address_components.get('district', ''),
                'postalCode': address_components.get('postal_code', ''),
                'city': address_components.get('city', ''),
                'state': address_components.get('state', ''),
                'country': address_components.get('country', 'BR'),
                'addressObservations': None,
                'placesId': place.get('place_id'),
                'placesRating': place.get('rating'),
                'placesMaps': place.get('url'),
                'placesLat': place.get('geometry', {}).get('location', {}).get('lat'),
                'placesLng': place.get('geometry', {}).get('location', {}).get('lng'),
                'placesUserRatingsTotal': place.get('user_ratings_total'),
                'placesPhone': self._clean_phone(place.get('formatted_phone_number')),
                'placesWebsite': place.get('website'),
                'placesThumb': self._get_photo_url(place.get('photos', [])),
                'instagramUrl': None,  # Será detectado pelos scrapers
                'classificationInfo': ', '.join(place.get('types', [])),
                
                # Campos de qualificação baseados nos dados do Places
                'Qualify → LeadId': i + 1,
                'Qualify → Evaluable': 'LEAD',
                'Qualify → StarRating': int(place.get('rating', 0)),
                'Qualify → BusinessTarget': self._classify_business_type(place.get('types', [])),
                'Qualify → StoreLocation': self._classify_location_type(place.get('types', [])),
                'Qualify → StoreType': 'A definir',
                'Qualify → MediaAndDisplays': 'A verificar',
                'Qualify → Products': 'A identificar',
                'Qualify → StoreArea': 'A medir',
                'Qualify → AccessoriesArea': 'A avaliar'
            }
            
            formatted_leads.append(formatted_lead)
        
        return formatted_leads
    
    def _parse_address(self, formatted_address: str) -> Dict[str, str]:
        """Extrai componentes do endereço formatado"""
        
        components = {
            'street': '',
            'number': '',
            'district': '',
            'city': '',
            'state': '',
            'postal_code': '',
            'country': 'BR'
        }
        
        if not formatted_address:
            return components
        
        # Exemplo: "Rua Marechal Floriano, 545 - Centro, Santa Cruz do Sul - RS, 96810-052, Brasil"
        parts = [part.strip() for part in formatted_address.split(',')]
        
        if len(parts) >= 1:
            # Primeira parte: Rua + número
            street_part = parts[0]
            street_parts = street_part.rsplit(' ', 1)
            if len(street_parts) == 2 and street_parts[1].isdigit():
                components['street'] = street_parts[0]
                components['number'] = street_parts[1]
            else:
                components['street'] = street_part
        
        if len(parts) >= 2:
            # Segunda parte: Bairro
            district_part = parts[1].split(' - ')[0].strip()
            components['district'] = district_part
        
        if len(parts) >= 3:
            # Terceira parte: Cidade - Estado
            city_state = parts[2]
            if ' - ' in city_state:
                city, state = city_state.split(' - ', 1)
                components['city'] = city.strip()
                components['state'] = state.strip()
            else:
                components['city'] = city_state.strip()
        
        # CEP (última parte que contém números)
        for part in reversed(parts):
            if any(char.isdigit() for char in part):
                # Extrair CEP
                import re
                cep_match = re.search(r'\d{5}-?\d{3}', part)
                if cep_match:
                    components['postal_code'] = cep_match.group()
                break
        
        return components
    
    def _clean_phone(self, phone: Optional[str]) -> Optional[str]:
        """Limpa e padroniza telefone"""
        if not phone:
            return None
        
        # Remover caracteres não numéricos exceto + no início
        import re
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Se começa com +55, remover para padronizar
        if cleaned.startswith('+55'):
            cleaned = cleaned[3:]
        
        return cleaned if len(cleaned) >= 10 else None
    
    def _summarize_reviews(self, reviews: List[Dict]) -> str:
        """Cria resumo dos reviews"""
        if not reviews:
            return ""
        
        # Pegar os 3 primeiros reviews
        summaries = []
        for review in reviews[:3]:
            text = review.get('text', '')
            if text:
                # Pegar primeira frase
                first_sentence = text.split('.')[0][:100] + "..."
                summaries.append(first_sentence)
        
        return " | ".join(summaries)
    
    def _get_photo_url(self, photos: List[Dict]) -> Optional[str]:
        """Extrai URL da primeira foto"""
        if not photos:
            return None
        
        # Construir URL da foto
        photo_reference = photos[0].get('photo_reference')
        if photo_reference:
            return f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo_reference}&key={self.api_key}"
        
        return None
    
    def _classify_business_type(self, types: List[str]) -> str:
        """Classifica tipo de negócio baseado nos types do Google"""
        
        type_mapping = {
            'electronics_store': 'Especialista Loja',
            'store': 'Loja Varejo',
            'establishment': 'Estabelecimento',
            'point_of_interest': 'Ponto de Interesse',
            'phone_repair': 'Assistencia Tecnica',
            'shopping_mall': 'Shopping Center'
        }
        
        for google_type in types:
            if google_type in type_mapping:
                return type_mapping[google_type]
        
        return 'A classificar'
    
    def _classify_location_type(self, types: List[str]) -> str:
        """Classifica tipo de localização"""
        
        if 'shopping_mall' in types:
            return 'Shopping center'
        elif any(t in types for t in ['store', 'establishment', 'electronics_store']):
            return 'Centro comercial (rua)'
        else:
            return 'A definir'

async def collect_leads_from_google_places(
    queries: List[str],
    locations: List[str],
    business_types: List[str] = None,
    output_file: str = "google_places_leads.xlsx"
) -> str:
    """
    Coleta leads do Google Places baseado em queries e localizações
    
    Args:
        queries: Lista de termos de busca (ex: ["assistência técnica celular", "loja celular"])
        locations: Lista de cidades (ex: ["Santa Cruz do Sul, RS", "Porto Alegre, RS"])
        business_types: Tipos de negócio (ex: ["electronics_store", "phone_repair"])
        output_file: Arquivo de saída
    
    Returns:
        Caminho do arquivo gerado
    """
    
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY não configurada")
    
    all_leads = []
    
    async with GooglePlacesCollector(api_key) as collector:
        
        for location in locations:
            for query in queries:
                
                config = PlacesSearchConfig(
                    query=query,
                    location=location,
                    business_types=business_types,
                    radius=15000,  # 15km
                    min_rating=0.0,
                    max_results=60
                )
                
                logger.info(f"Buscando '{query}' em '{location}'")
                
                places = await collector.search_businesses(config)
                formatted_leads = collector.format_leads_for_gdr(places)
                
                # Adicionar informações de busca
                for lead in formatted_leads:
                    lead['search_query'] = query
                    lead['search_location'] = location
                
                all_leads.extend(formatted_leads)
                
                logger.info(f"Coletados {len(formatted_leads)} leads para '{query}' em '{location}'")
                
                # Rate limiting entre buscas
                await asyncio.sleep(1)
    
    # Remover duplicatas baseado em place_id
    unique_leads = []
    seen_place_ids = set()
    
    for lead in all_leads:
        place_id = lead.get('placesId')
        if place_id not in seen_place_ids:
            seen_place_ids.add(place_id)
            unique_leads.append(lead)
    
    logger.info(f"Total de leads únicos coletados: {len(unique_leads)}")
    
    # Salvar em Excel
    df = pd.DataFrame(unique_leads)
    df.to_excel(output_file, index=False)
    
    logger.info(f"Leads salvos em: {output_file}")
    
    return output_file

# Configurações pré-definidas para diferentes setores
SECTOR_CONFIGS = {
    'celulares_acessorios': {
        'queries': [
            'assistência técnica celular',
            'loja celular',
            'acessórios celular',
            'capinhas celular',
            'películas celular',
            'conserto celular'
        ],
        'business_types': ['electronics_store', 'phone_repair'],
        'description': 'Lojas e assistências técnicas de celulares e acessórios'
    },
    
    'farmacia_drogaria': {
        'queries': [
            'farmácia',
            'drogaria',
            'medicamentos'
        ],
        'business_types': ['pharmacy', 'drugstore'],
        'description': 'Farmácias e drogarias'
    },
    
    'pet_shop': {
        'queries': [
            'pet shop',
            'loja animais',
            'ração animal',
            'veterinária'
        ],
        'business_types': ['pet_store', 'veterinary_care'],
        'description': 'Pet shops e clínicas veterinárias'
    },
    
    'alimentacao': {
        'queries': [
            'restaurante',
            'lanchonete',
            'pizzaria',
            'padaria'
        ],
        'business_types': ['restaurant', 'meal_takeaway', 'bakery'],
        'description': 'Estabelecimentos de alimentação'
    }
}

async def main():
    """Exemplo de uso"""
    
    print("🚀 GDR Google Places Collector")
    print("=" * 50)
    
    # Exemplo: Coletar leads do setor de celulares em algumas cidades do RS
    sector = 'celulares_acessorios'
    config = SECTOR_CONFIGS[sector]
    
    locations = [
        "Santa Cruz do Sul, RS",
        "Venâncio Aires, RS", 
        "Lajeado, RS",
        "Estrela, RS"
    ]
    
    print(f"Setor: {config['description']}")
    print(f"Queries: {config['queries']}")
    print(f"Localizações: {locations}")
    print("=" * 50)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"leads_google_places_{sector}_{timestamp}.xlsx"
    
    start_time = time.time()
    
    try:
        result_file = await collect_leads_from_google_places(
            queries=config['queries'],
            locations=locations,
            business_types=config['business_types'],
            output_file=output_file
        )
        
        end_time = time.time()
        
        print("=" * 50)
        print("✅ COLETA CONCLUÍDA!")
        print(f"📁 Arquivo gerado: {result_file}")
        print(f"⏱️ Tempo total: {end_time - start_time:.1f} segundos")
        print("=" * 50)
        print("\n🔄 Próximo passo:")
        print(f"python run_gdr.py -i {result_file} -m 50")
        
    except Exception as e:
        logger.error(f"Erro na coleta: {e}")

if __name__ == "__main__":
    asyncio.run(main())
