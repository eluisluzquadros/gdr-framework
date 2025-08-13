"""
Validadores e sanitizadores de dados para o GDR Framework
"""

from typing import Any, Optional, Union, List
import pandas as pd
import numpy as np
import re

class DataSanitizer:
    """Sanitiza e valida dados de entrada"""
    
    @staticmethod
    def safe_string(value: Any) -> str:
        """Converte qualquer valor para string segura"""
        if value is None or pd.isna(value):
            return ""
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (int, float)):
            if pd.isna(value) or np.isinf(value):
                return ""
            return str(value)
        return str(value).strip()
    
    @staticmethod
    def safe_float(value: Any) -> Optional[float]:
        """Converte para float seguro"""
        if value is None or pd.isna(value):
            return None
        try:
            result = float(value)
            if np.isinf(result) or np.isnan(result):
                return None
            return result
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def safe_int(value: Any) -> Optional[int]:
        """Converte para int seguro"""
        if value is None or pd.isna(value):
            return None
        try:
            # Primeiro converte para float, depois para int
            result = float(value)
            if np.isinf(result) or np.isnan(result):
                return None
            return int(result)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def safe_url(value: Any) -> str:
        """Processa URLs e handles do Instagram"""
        url = DataSanitizer.safe_string(value)
        if not url:
            return ""
        
        # Remover @ do início se for handle
        if url.startswith('@'):
            url = url[1:]
        
        # Adicionar https:// se necessário
        if url and not url.startswith(('http://', 'https://')):
            # Se for um handle do Instagram (sem / ou .)
            if '/' not in url and '.' not in url:
                return f"https://www.instagram.com/{url}/"
            # Se parecer um domínio
            elif '.' in url:
                return f"https://{url}"
        
        return url
    
    @staticmethod
    def extract_instagram_username(value: Any) -> str:
        """Extrai username do Instagram de URL ou handle"""
        url = DataSanitizer.safe_string(value)
        if not url:
            return ""
        
        # Remover @ do início
        if url.startswith('@'):
            url = url[1:]
        
        # Se for URL completa, extrair username
        if 'instagram.com' in url:
            # Regex para extrair username
            match = re.search(r'instagram\.com/([^/?#]+)', url)
            if match:
                return match.group(1)
        
        # Se não tiver / ou ., provavelmente é um username
        if '/' not in url and '.' not in url:
            return url
        
        return ""
    
    @staticmethod
    def safe_phone(value: Any) -> str:
        """Limpa e formata número de telefone"""
        phone = DataSanitizer.safe_string(value)
        if not phone:
            return ""
        
        # Remove caracteres não numéricos
        phone = re.sub(r'\D', '', phone)
        
        # Remove zeros à esquerda desnecessários
        phone = phone.lstrip('0')
        
        # Se tiver menos de 8 dígitos, provavelmente não é válido
        if len(phone) < 8:
            return ""
        
        return phone
    
    @staticmethod
    def safe_email(value: Any) -> str:
        """Valida e limpa endereço de email"""
        email = DataSanitizer.safe_string(value).lower()
        if not email:
            return ""
        
        # Regex básico para validar email
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return email
        
        return ""
    
    @staticmethod
    def safe_list(value: Any) -> List:
        """Converte valor para lista segura"""
        if value is None or pd.isna(value):
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Tentar parsear como lista se for string
            if value.startswith('[') and value.endswith(']'):
                try:
                    import json
                    return json.loads(value)
                except:
                    pass
        return []