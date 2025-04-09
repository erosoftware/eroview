"""
Módulo para gerenciar diferentes tipos de entrada de localização
"""
import re
import requests
from typing import Tuple, Optional
from urllib.parse import urlparse, parse_qs

class LocationManager:
    def __init__(self):
        """Inicializa o gerenciador de localização"""
        # Regex para coordenadas em diferentes formatos
        self.coord_patterns = [
            # Formato decimal: -23.276064, -53.266292
            r'^(-?\d+\.?\d*),\s*(-?\d+\.?\d*)$',
            # Formato graus: 23°16'33.8"S 53°15'58.7"W
            r'^(\d+)°(\d+)\'(\d+\.?\d*)\"([NS])\s*(\d+)°(\d+)\'(\d+\.?\d*)\"([EW])$'
        ]
    
    def parse_coordinates(self, input_str: str) -> Optional[Tuple[float, float]]:
        """
        Converte uma string de coordenadas em latitude e longitude
        
        Args:
            input_str: String com as coordenadas em vários formatos possíveis
        
        Returns:
            Tuple (latitude, longitude) ou None se inválido
        """
        input_str = input_str.strip()
        
        # Tenta cada padrão de coordenadas
        for pattern in self.coord_patterns:
            match = re.match(pattern, input_str)
            if match:
                if len(match.groups()) == 2:
                    # Formato decimal
                    return float(match.group(1)), float(match.group(2))
                else:
                    # Formato graus
                    lat = float(match.group(1)) + float(match.group(2))/60 + float(match.group(3))/3600
                    if match.group(4) == 'S':
                        lat = -lat
                    
                    lon = float(match.group(5)) + float(match.group(6))/60 + float(match.group(7))/3600
                    if match.group(8) == 'W':
                        lon = -lon
                    
                    return lat, lon
        
        return None
    
    def extract_from_maps_url(self, url: str) -> Optional[Tuple[float, float]]:
        """
        Extrai coordenadas de uma URL do Google Maps
        
        Args:
            url: URL do Google Maps
        
        Returns:
            Tuple (latitude, longitude) ou None se inválido
        """
        try:
            print(f"Processando URL do Google Maps: {url}")
            
            # Primeiro, tenta extrair diretamente via regex o padrão mais comum
            # Padrão: "/-23.276064,-53.266292/" ou "@-23.276064,-53.266292"
            direct_pattern = r'[/@](-?\d+\.\d+),(-?\d+\.\d+)'
            match = re.search(direct_pattern, url)
            if match:
                print(f"Extraído diretamente: {match.group(1)}, {match.group(2)}")
                return float(match.group(1)), float(match.group(2))
            
            # Verifica se é uma URL curta do Google Maps
            if 'goo.gl' in url or 'maps.app.goo.gl' in url:
                try:
                    print("Expandindo URL curta do Google...")
                    session = requests.Session()
                    session.verify = False  # Desativa verificação SSL
                    response = session.head(url, allow_redirects=True, timeout=10)
                    url = response.url
                    print(f"URL expandida: {url}")
                    
                    # Tenta novamente com a URL expandida
                    match = re.search(direct_pattern, url)
                    if match:
                        print(f"Extraído da URL expandida: {match.group(1)}, {match.group(2)}")
                        return float(match.group(1)), float(match.group(2))
                except Exception as e:
                    print(f"Erro ao expandir URL curta: {e}")
            
            # Parse da URL
            parsed = urlparse(url)
            print(f"Parsed URL: {parsed}")
            
            # Extrair do caminho da URL (mais comum)
            path_coords = re.search(r'[/@](-?\d+\.\d+),(-?\d+\.\d+)', parsed.path)
            if path_coords:
                print(f"Coordenadas encontradas no path: {path_coords.group(1)}, {path_coords.group(2)}")
                return float(path_coords.group(1)), float(path_coords.group(2))
            
            # Extrair do fragmento
            if parsed.fragment:
                frag_coords = re.search(r'[/@](-?\d+\.\d+),(-?\d+\.\d+)', parsed.fragment)
                if frag_coords:
                    print(f"Coordenadas encontradas no fragmento: {frag_coords.group(1)}, {frag_coords.group(2)}")
                    return float(frag_coords.group(1)), float(frag_coords.group(2))
                
            # Se for maps.google.com ou qualquer domínio do Google Maps
            if any(domain in parsed.netloc for domain in ['google.com', 'maps.google', 'goo.gl']):
                # Tentar extrair de parâmetros específicos
                params = parse_qs(parsed.query)
                print(f"Parâmetros da URL: {params}")
                
                # Procurar em qualquer parâmetro
                for param_name, param_values in params.items():
                    for value in param_values:
                        coords_match = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', value)
                        if coords_match:
                            print(f"Coordenadas encontradas em parâmetro {param_name}: {coords_match.group(1)}, {coords_match.group(2)}")
                            return float(coords_match.group(1)), float(coords_match.group(2))
                
                # Parâmetros mais específicos
                specific_params = ['ll', 'sll', 'center', 'q', 'daddr', 'saddr']
                for param in specific_params:
                    if param in params:
                        value = params[param][0]
                        coords_match = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', value)
                        if coords_match:
                            print(f"Coordenadas encontradas em {param}: {coords_match.group(1)}, {coords_match.group(2)}")
                            return float(coords_match.group(1)), float(coords_match.group(2))
                
                # Verificar em data=
                data_param = re.search(r'data=.*!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', url)
                if data_param:
                    print(f"Coordenadas encontradas em data parameter: {data_param.group(1)}, {data_param.group(2)}")
                    return float(data_param.group(1)), float(data_param.group(2))
                
                # Extração por padrões de URL do Maps
                if '/place/' in url:
                    place_match = re.search(r'/place/[^/]*/@?(-?\d+\.\d+),(-?\d+\.\d+)', url)
                    if place_match:
                        print(f"Coordenadas encontradas em /place/: {place_match.group(1)}, {place_match.group(2)}")
                        return float(place_match.group(1)), float(place_match.group(2))
            
            # Tenta encontrar qualquer par de coordenadas na URL completa
            any_coords = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', url)
            if any_coords:
                print(f"Coordenadas encontradas na URL: {any_coords.group(1)}, {any_coords.group(2)}")
                return float(any_coords.group(1)), float(any_coords.group(2))
            
            print(f"Nenhum formato de coordenadas reconhecido na URL: {url}")
            return None
        except Exception as e:
            print(f"Erro ao processar URL do Maps: {e}")
            return None
    
    def get_current_location(self) -> Optional[Tuple[float, float]]:
        """
        Obtém a localização atual do dispositivo (deve ser implementado na plataforma)
        
        Returns:
            Tuple (latitude, longitude) ou None se não disponível
        """
        # TODO: Implementar usando a API de geolocalização do Android
        return None
    
    def get_coordinates(self, location_input: str) -> Optional[Tuple[float, float]]:
        """
        Processa diferentes tipos de entrada de localização
        
        Args:
            location_input: String com coordenadas, URL do Maps ou 'current'
        
        Returns:
            Tuple (latitude, longitude) ou None se inválido
        """
        print(f"Processando entrada de localização: {location_input}")
        
        # Verifica se é pedido de localização atual
        if location_input.lower() == 'current':
            return self.get_current_location()
        
        # Tenta parse direto das coordenadas primeiro (mais comum e confiável)
        coords = self.parse_coordinates(location_input)
        if coords:
            print(f"Coordenadas processadas diretamente: {coords}")
            return coords
        
        # Se não for coordenadas diretas, verifica se é URL do Google Maps
        if any(domain in location_input.lower() for domain in [
            'maps.google', 'google.com/maps', 'goo.gl', 'maps.app'
        ]) or 'maps' in location_input.lower():
            coords = self.extract_from_maps_url(location_input)
            if coords:
                print(f"Coordenadas extraídas de URL: {coords}")
                return coords
        
        print(f"Não foi possível processar as coordenadas: {location_input}")
        return None

# Exemplo de uso
if __name__ == "__main__":
    location_manager = LocationManager()
    
    # Testa diferentes formatos
    test_inputs = [
        "-23.276064, -53.266292",  # Formato decimal
        "23°16'33.8\"S 53°15'58.7\"W",  # Formato graus
        "https://maps.app.goo.gl/oT95tobPKX7Pp9dx8",  # URL do Maps
        "current"  # Localização atual
    ]
    
    print("Testando diferentes formatos de entrada:")
    for input_str in test_inputs:
        coords = location_manager.get_coordinates(input_str)
        print(f"\nEntrada: {input_str}")
        print(f"Coordenadas: {coords if coords else 'Inválido/Não disponível'}")
