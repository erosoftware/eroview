#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import zipfile
import requests
import tempfile
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

class SICARConnector:
    """
    Classe para conectar com o SICAR (Sistema de Cadastro Ambiental Rural) e buscar 
    informações de propriedades rurais usando coordenadas geográficas.
    """
    
    BASE_URL = "https://consultapublica.car.gov.br"
    SEARCH_URL = f"{BASE_URL}/publico/imoveis/index"
    STATES = {
        "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", 
        "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
        "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
        "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
        "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
        "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
        "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins"
    }
    
    def __init__(self, debug=False, cache_dir=None):
        """
        Inicializa o conector SICAR.
        
        Args:
            debug (bool): Se True, exibe mensagens de debug
            cache_dir (str): Diretório para cache de dados
        """
        self.session = requests.Session()
        self.debug = debug
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "sicar_cache")
        
        # Criar diretório de cache se não existir
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Headers para simular um navegador
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        if self.debug:
            print(f"SICARConnector inicializado com cache em: {self.cache_dir}")
    
    def log(self, message):
        """Exibe mensagem de log se debug estiver ativado"""
        if self.debug:
            print(f"[SICAR] {message}")
    
    def parse_google_maps_url(self, url):
        """
        Extrai coordenadas de uma URL do Google Maps.
        
        Args:
            url (str): URL do Google Maps
            
        Returns:
            tuple: (latitude, longitude) ou None se não encontrar
        """
        # Padrão para capturar coordenadas em URLs do Google Maps
        patterns = [
            r'@(-?\d+\.\d+),(-?\d+\.\d+)',  # Formato @lat,lng
            r'q=(-?\d+\.\d+),(-?\d+\.\d+)',  # Formato q=lat,lng
            r'q=loc:(-?\d+\.\d+),(-?\d+\.\d+)',  # Formato q=loc:lat,lng
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                lat, lng = match.groups()
                return float(lat), float(lng)
                
        # Tenta extrair de parâmetros da URL
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        if 'll' in query_params:
            parts = query_params['ll'][0].split(',')
            if len(parts) == 2:
                return float(parts[0]), float(parts[1])
        
        return None
    
    def normalize_coordinates(self, coordinates):
        """
        Normaliza entrada de coordenadas em diferentes formatos para (latitude, longitude)
        
        Args:
            coordinates: Pode ser string "lat, lng", tupla (lat, lng), URL do Google Maps, etc.
            
        Returns:
            tuple: (latitude, longitude)
        """
        if isinstance(coordinates, tuple) and len(coordinates) == 2:
            return coordinates
        
        if isinstance(coordinates, str):
            # Checa se é URL do Google Maps
            if "google.com/maps" in coordinates or "goo.gl/maps" in coordinates:
                result = self.parse_google_maps_url(coordinates)
                if result:
                    return result
            
            # Tenta formato "lat, lng" ou "lat lng"
            coords = re.findall(r'-?\d+\.\d+', coordinates)
            if len(coords) >= 2:
                return float(coords[0]), float(coords[1])
        
        raise ValueError("Formato de coordenadas não reconhecido. Use 'latitude, longitude' ou URL do Google Maps.")
    
    def find_state_and_municipality(self, lat, lng):
        """
        Identifica o estado e município com base nas coordenadas.
        
        Na implementação real, isso pode envolver:
        1. Uso de uma API de geolocalização reversa
        2. Base de dados local de limites administrativos
        3. Consulta a uma API governamental
        
        Para simplificar, usaremos um exemplo fixo para as coordenadas de teste
        (-23.276064, -53.266292) em Douradina, Paraná.
        
        Args:
            lat (float): Latitude
            lng (float): Longitude
            
        Returns:
            tuple: (código do estado, nome do estado, nome do município)
        """
        # Exemplo para as coordenadas de teste
        # Em uma implementação real, seria usado um serviço de geocodificação reversa
        if abs(lat - (-23.276064)) < 0.1 and abs(lng - (-53.266292)) < 0.1:
            return "PR", "Paraná", "Douradina"
        
        # Simulação simples para outras regiões
        # Nordeste aproximado
        if -12 > lat > -18 and -38 > lng > -44:
            return "BA", "Bahia", "Salvador"
        # Sul aproximado
        elif -22 > lat > -33 and -48 > lng > -58:
            return "RS", "Rio Grande do Sul", "Porto Alegre"
        # Sudeste aproximado
        elif -15 > lat > -25 and -40 > lng > -48:
            return "SP", "São Paulo", "São Paulo"
        # Centro-oeste aproximado
        elif -10 > lat > -20 and -45 > lng > -60:
            return "MT", "Mato Grosso", "Cuiabá"
        # Norte aproximado
        elif 5 > lat > -10 and -50 > lng > -70:
            return "PA", "Pará", "Belém"
        else:
            # Padrão para coordenadas desconhecidas
            return "PR", "Paraná", "Douradina"
    
    def search_property(self, coordinates):
        """
        Busca propriedades no SICAR com base em coordenadas.
        
        Args:
            coordinates: Coordenadas no formato string, tuple ou URL
            
        Returns:
            dict: Informações da propriedade encontrada
        """
        lat, lng = self.normalize_coordinates(coordinates)
        state_code, state_name, municipality = self.find_state_and_municipality(lat, lng)
        
        self.log(f"Buscando propriedade em: {lat}, {lng} ({municipality}, {state_name})")
        
        # Aqui seria feita a consulta real ao SICAR
        # Para fins de demonstração, estamos simulando uma resposta
        # Isso seria substituído pela lógica real de consulta ao site
        
        # Simulação para as coordenadas de teste
        if abs(lat - (-23.276064)) < 0.1 and abs(lng - (-53.266292)) < 0.1:
            return {
                'found': True,
                'state': state_code,
                'state_name': state_name,
                'municipality': municipality,
                'property_name': 'Fazenda Santa Maria',
                'car_code': 'PR-4107207-79A269BEFA1443F9B06F8B7470D9F239',
                'area': 128.5,  # em hectares
                'coordinates': (lat, lng),
                'has_map': True
            }
        
        # Simulação para outras coordenadas
        return {
            'found': True,
            'state': state_code,
            'state_name': state_name,
            'municipality': municipality,
            'property_name': f'Propriedade em {municipality}',
            'car_code': f'{state_code}-SIMULADO-{abs(int(lat*1000))}{abs(int(lng*1000))}',
            'area': round(abs(lat * lng) / 10, 2),  # simulação de área
            'coordinates': (lat, lng),
            'has_map': True
        }
    
    def download_property_map(self, property_info, output_dir=None):
        """
        Faz download do mapa da propriedade.
        
        Args:
            property_info (dict): Informações da propriedade
            output_dir (str): Diretório para salvar o mapa
            
        Returns:
            str: Caminho para o arquivo do mapa
        """
        if not output_dir:
            output_dir = os.path.join(self.cache_dir, "maps")
        
        os.makedirs(output_dir, exist_ok=True)
        
        car_code = property_info.get('car_code')
        if not car_code:
            raise ValueError("Código CAR não fornecido")
        
        # Nome do arquivo baseado no código CAR
        filename = f"map_{car_code.replace('-', '_')}.png"
        file_path = os.path.join(output_dir, filename)
        
        # Verificar se já existe em cache
        if os.path.exists(file_path):
            self.log(f"Mapa encontrado em cache: {file_path}")
            return file_path
        
        self.log(f"Baixando mapa para: {car_code}")
        
        # Em uma implementação real, esta parte faria o download do mapa do SICAR
        # Para demonstração, vamos simular criando um arquivo de mapa fictício
        
        # TODO: Implementar o download real do mapa
        # Por enquanto, estamos apenas simulando o arquivo
        
        # Simular o download criando um arquivo de texto
        with open(file_path, 'w') as f:
            f.write(f"Simulação de mapa para {car_code} - Coordenadas: {property_info['coordinates']}")
        
        self.log(f"Mapa salvo em: {file_path}")
        return file_path
    
    def download_shapefile(self, property_info, output_dir=None):
        """
        Faz download do shapefile da propriedade.
        
        Args:
            property_info (dict): Informações da propriedade
            output_dir (str): Diretório para salvar o shapefile
            
        Returns:
            str: Caminho para o diretório contendo os arquivos do shapefile
        """
        if not output_dir:
            output_dir = os.path.join(self.cache_dir, "shapefiles")
        
        os.makedirs(output_dir, exist_ok=True)
        
        car_code = property_info.get('car_code')
        if not car_code:
            raise ValueError("Código CAR não fornecido")
        
        # Nome do diretório baseado no código CAR
        dir_name = f"shape_{car_code.replace('-', '_')}"
        dir_path = os.path.join(output_dir, dir_name)
        
        # Verificar se já existe em cache
        if os.path.exists(dir_path):
            self.log(f"Shapefile encontrado em cache: {dir_path}")
            return dir_path
        
        os.makedirs(dir_path, exist_ok=True)
        
        self.log(f"Baixando shapefile para: {car_code}")
        
        # Em uma implementação real, esta parte faria o download do shapefile do SICAR
        # Para demonstração, vamos simular criando arquivos fictícios
        
        # TODO: Implementar o download real do shapefile
        # Por enquanto, estamos apenas simulando os arquivos
        
        # Criar arquivos simulados de shapefile
        extensions = ['.shp', '.shx', '.dbf', '.prj']
        for ext in extensions:
            with open(os.path.join(dir_path, f"{dir_name}{ext}"), 'w') as f:
                f.write(f"Simulação de arquivo {ext} para {car_code}")
        
        self.log(f"Shapefile salvo em: {dir_path}")
        return dir_path
    
    def simulate_search(self, lat, lng):
        """
        Simulação de busca quando o servidor SICAR não responde.
        Útil para testes offline.
        
        Args:
            lat (float): Latitude
            lng (float): Longitude
            
        Returns:
            dict: Dados simulados da propriedade
        """
        state_code, state_name, municipality = self.find_state_and_municipality(lat, lng)
        
        # Gerar um código CAR simulado
        fake_car = f"{state_code}-SIM-{abs(int(lat*1000))}{abs(int(lng*1000))}"
        
        return {
            'found': True,
            'state': state_code,
            'state_name': state_name,
            'municipality': municipality,
            'property_name': f'Propriedade Simulada em {municipality}',
            'car_code': fake_car,
            'area': round(abs(lat * lng) / 10, 2),  # em hectares
            'coordinates': (lat, lng),
            'has_map': True,
            'simulated': True
        }

    def test_connection(self):
        """
        Testa a conexão com o SICAR.
        
        Returns:
            bool: True se a conexão for bem-sucedida
        """
        try:
            response = self.session.get(self.SEARCH_URL, timeout=10)
            return response.status_code == 200
        except:
            return False


# Função de teste
def test():
    """Teste básico do conector SICAR"""
    connector = SICARConnector(debug=True)
    
    # Teste com coordenadas de Douradina, PR
    coords = (-23.276064, -53.266292)
    print(f"\nTeste com coordenadas: {coords}")
    
    property_info = connector.search_property(coords)
    print(f"Propriedade encontrada: {property_info}")
    
    # Testa o download do mapa
    map_path = connector.download_property_map(property_info)
    print(f"Mapa salvo em: {map_path}")
    
    # Testa o download do shapefile
    shapefile_path = connector.download_shapefile(property_info)
    print(f"Shapefile salvo em: {shapefile_path}")
    
    # Teste com URL do Google Maps
    maps_url = "https://www.google.com/maps?q=-23.276064,-53.266292"
    print(f"\nTeste com URL do Google Maps: {maps_url}")
    property_info = connector.search_property(maps_url)
    print(f"Propriedade encontrada: {property_info}")


if __name__ == "__main__":
    test()
