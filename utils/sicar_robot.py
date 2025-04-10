#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo para interação automatizada com o SICAR (Sistema de Cadastro Ambiental Rural)
Usando Selenium para navegação e extração de mapas de propriedades rurais
"""

import logging
import os
import time
import json
import uuid
import re
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from unidecode import unidecode
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

class SICARRobot:
    """
    Classe para automação de busca e extração no site do SICAR
    
    Atributos:
        base_dir (str): Diretório base da aplicação
        browser (str): Navegador a ser utilizado (chrome ou firefox)
        headless (bool): Se True, executa em modo headless (sem interface gráfica)
        dev_mode (bool): Se True, ativa recursos de desenvolvimento
        driver: Instância do webdriver do Selenium
        log: Instância do logger
    """
    
    def __init__(self, base_dir, browser="chrome", headless=True, dev_mode=False, embed_browser=True):
        """
        Inicializa o robô SICAR
        
        Args:
            base_dir (str): Diretório base da aplicação
            browser (str): Navegador a ser utilizado (chrome ou firefox)
            headless (bool): Se True, executa em modo headless (sem interface gráfica)
            dev_mode (bool): Se True, ativa recursos de desenvolvimento
            embed_browser (bool): Se True, configura o navegador para ser exibido em um iframe
        """
        self.base_dir = base_dir
        self.browser = browser
        self.headless = headless
        self.dev_mode = dev_mode
        self.embed_browser = embed_browser
        self.driver = None
        self.log_callback = None
        self.diagnostics = []
        self.progresso = 0  # Progresso da automação (0-100)
        # Inicializa o logger
        self.log = logging.getLogger('sicar_robot')
        
        # Cria diretório para mapas
        self.maps_dir = os.path.join(base_dir, "static", "maps")
        os.makedirs(self.maps_dir, exist_ok=True)
        
        # URL do portal SICAR
        self.sicar_url = "https://consultapublica.car.gov.br/publico/imoveis/index"
    
    def set_log_callback(self, callback):
        """Define função de callback para logs"""
        self.log_callback = callback
    
    def add_diagnostic(self, operation: str, success: bool, error_message: str = None):
        """
        Adiciona um diagnóstico à lista de diagnósticos
        
        Args:
            operation (str): Nome da operação
            success (bool): Se a operação foi bem-sucedida
            error_message (str, optional): Mensagem de erro, se houver
        """
        diagnostic = {
            "operation": operation,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "error": error_message if not success and error_message else None
        }
        
        self.diagnostics.append(diagnostic)
        
        # Registra no log
        if success:
            self.log.info(f"[{operation}] Sucesso")
        else:
            self.log.error(f"[{operation}] Falha: {error_message}")
        
        # Chama o callback se existir
        if self.log_callback:
            level = "success" if success else "error"
            message = f"[{operation}] " + (f"Sucesso" if success else f"Falha: {error_message}")
            self.log_callback(message, level)
    
    def _setup_webdriver(self):
        """
        Configura o webdriver para automação
        
        Returns:
            bool: True se configurou com sucesso, False caso contrário
        """
        try:
            self.add_diagnostic("setup_webdriver", True, "Iniciando configuração do webdriver")
            
            if self.browser.lower() == "chrome":
                # Configuração do Chrome
                options = webdriver.ChromeOptions()
                
                if self.headless:
                    options.add_argument('--headless=new')
                    options.add_argument('--disable-gpu')
                
                # Opções adicionais para melhorar a estabilidade
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-popup-blocking')
                options.add_argument('--blink-settings=imagesEnabled=true')
                options.add_argument('--disable-infobars')
                options.add_argument('--window-size=1366,768')
                
                # Evita detecção de automação
                options.add_experimental_option('excludeSwitches', ['enable-automation'])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Diretório de download
                download_dir = os.path.join(self.base_dir, 'downloads')
                os.makedirs(download_dir, exist_ok=True)
                
                prefs = {
                    'download.default_directory': download_dir,
                    'download.prompt_for_download': False,
                    'download.directory_upgrade': True,
                    'safebrowsing.enabled': False
                }
                options.add_experimental_option('prefs', prefs)
                
                if self.embed_browser:
                    options.add_argument("--window-position=0,0")
                    options.add_argument("--window-size=800,600")
                
                self.driver = webdriver.Chrome(options=options)
                self.add_diagnostic("setup_webdriver", True, "Chrome WebDriver inicializado com sucesso")
                
            elif self.browser.lower() == "opera":
                # Configuração do Opera
                options = webdriver.ChromeOptions()
                options.add_experimental_option('w3c', True)
                options.binary_location = self._find_opera_binary()
                
                if self.headless:
                    options.add_argument('--headless')
                
                # Opções adicionais para melhorar a estabilidade
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-popup-blocking')
                options.add_argument('--window-size=1366,768')
                
                self.driver = webdriver.Chrome(options=options)
                self.add_diagnostic("setup_webdriver", True, "Opera WebDriver inicializado com sucesso")
                
            else:
                self.add_diagnostic("setup_webdriver", False, f"Navegador não suportado: {self.browser}")
                return False
            
            # Configurações gerais do webdriver
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            # Maximize a janela para garantir que elementos sejam visíveis
            if not self.headless:
                self.driver.maximize_window()
                
            return True
            
        except Exception as e:
            error_message = f"Erro na configuração do WebDriver: {str(e)}"
            self.add_diagnostic("setup_webdriver", False, error_message)
            logger.error(error_message)
            return False
    
    def _find_opera_binary(self):
        """
        Localiza o binário do Opera no sistema
        
        Returns:
            str: Caminho para o binário do Opera ou None se não encontrado
        """
        # Caminhos comuns do Opera em diferentes sistemas operacionais
        possible_paths = [
            # Windows
            r"C:\Program Files\Opera\opera.exe",
            r"C:\Program Files (x86)\Opera\opera.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Opera\launcher.exe"),
            # Linux
            "/usr/bin/opera",
            "/usr/local/bin/opera",
            # macOS
            "/Applications/Opera.app/Contents/MacOS/Opera"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Se não encontrou, retorna None
        return None
    
    def wait_for_page_load(self, timeout=30):
        """
        Aguarda o carregamento completo da página
        
        Args:
            timeout (int): Tempo máximo de espera em segundos
            
        Returns:
            bool: True se a página carregou, False caso contrário
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            return True
        except:
            return False
    
    def wait_for_element(self, by, value, timeout=10, visible=True):
        """
        Aguarda um elemento ficar disponível/visível na página
        
        Args:
            by: Método de localização (By.ID, By.CSS_SELECTOR, etc)
            value: Valor para localização
            timeout: Tempo máximo de espera em segundos
            visible: Se True, espera o elemento ficar visível
            
        Returns:
            WebElement: Elemento encontrado ou None se não encontrado
        """
        try:
            if visible:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.visibility_of_element_located((by, value))
                )
            else:
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
            return element
        except Exception as e:
            logger.warning(f"Elemento não encontrado: {by}={value} - {str(e)}")
            return None
    
    def acessar_sicar(self, max_attempts=5):
        """
        Acessa o portal do SICAR
        
        Args:
            max_attempts (int): Número máximo de tentativas
            
        Returns:
            bool: True se acessou com sucesso, False caso contrário
        """
        url = self.sicar_url
        
        for attempt in range(max_attempts):
            try:
                self.add_diagnostic("access_site", True, f"Tentativa {attempt+1} de {max_attempts}")
                
                # Acessa a URL
                self.driver.get(url)
                
                # Espera a página carregar
                self.wait_for_page_load(timeout=30)
                
                # Verifica se está na página correta - CORRIGIDO: aceita mais variações dos títulos
                current_title = self.driver.title.upper()
                current_url = self.driver.current_url.lower()
                
                # Verifica por diferentes padrões que indicam que estamos na página correta
                sicar_indicators = [
                    "CONSULTA PÚBLICA" in current_title,
                    "SICAR" in current_title,
                    "CAR" in current_title and "RURAL" in current_title,
                    "consultapublica.car.gov.br" in current_url,
                    "car.gov.br" in current_url
                ]
                
                # Se qualquer um dos indicadores for positivo, consideramos que estamos na página do SICAR
                if any(sicar_indicators):
                    self.add_diagnostic("access_site", True, f"Portal SICAR acessado com sucesso: {current_title}")
                    
                    # Verifica se já estamos na tela de consulta de imóveis
                    if "IMÓVEIS" in current_title or "/imoveis/" in current_url:
                        self.add_diagnostic("access_site", True, "Já na tela de consulta de imóveis")
                        return True
                        
                    # Tenta localizar e clicar no botão ou link de "Consulta Pública" se não estiver na página correta
                    try:
                        # Busca por vários elementos que podem levar à página de consulta
                        consulta_elements = self.driver.find_elements(By.XPATH, 
                            "//a[contains(text(), 'Consulta') or contains(@href, 'consulta')] | " +
                            "//button[contains(text(), 'Consulta')] | " + 
                            "//div[contains(text(), 'Consulta')]")
                        
                        if consulta_elements:
                            # Clica no primeiro elemento encontrado
                            consulta_elements[0].click()
                            self.wait_for_page_load(timeout=10)
                    except Exception as nav_e:
                        self.add_diagnostic("access_site", True, f"Aviso ao navegar: {str(nav_e)}")
                        # Continuamos mesmo se houver erro, pois já podemos estar na página correta
                    
                    return True
                else:
                    self.add_diagnostic("access_site", False, f"Página incorreta: {current_title}")
                    
                    # Tenta seguir links para a página correta
                    try:
                        # Busca por links que possam levar ao SICAR
                        sicar_links = self.driver.find_elements(By.XPATH, 
                            "//a[contains(text(), 'SICAR') or contains(text(), 'CAR') or contains(@href, 'car.gov.br')]")
                        
                        if sicar_links:
                            sicar_links[0].click()
                            time.sleep(3)
                            self.wait_for_page_load(timeout=10)
                            
                            # Verifica novamente
                            if "consultapublica.car.gov.br" in self.driver.current_url.lower():
                                self.add_diagnostic("access_site", True, "Portal SICAR acessado após redirecionamento")
                                return True
                    except Exception as e:
                        pass
            
            except Exception as e:
                self.add_diagnostic("access_site", False, f"Erro: {str(e)}")
            
            # Espera antes de tentar novamente
            time.sleep(2)
        
        # Se chegou aqui, todas as tentativas falharam
        self.add_diagnostic("access_site", False, "Falha em todas as tentativas de acessar o SICAR")
        return False

    def identificar_estado(self, lat, lon):
        """
        Identifica o estado brasileiro com base nas coordenadas usando uma API de geocodificação
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            
        Returns:
            str: Nome do estado ou None se não for possível identificar
        """
        try:
            self.add_diagnostic("identificar_estado", True, f"Buscando estado para coordenadas {lat}, {lon}")
            
            # Usa a API Nominatim do OpenStreetMap (gratuita e sem necessidade de chave API)
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&accept-language=pt-BR"
            
            headers = {
                'User-Agent': 'EroView/1.0 (contato@erosoftware.com.br)'  # Importante para não ser bloqueado
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extrai o estado (pode estar em diferentes chaves dependendo da localização)
                estado = None
                address = data.get('address', {})
                
                # Tenta obter o estado em diferentes formatos
                if 'state' in address:
                    estado = address['state'].upper()
                elif 'province' in address:
                    estado = address['province'].upper()
                elif 'county' in address and 'country' in address and address['country'] == 'Brasil':
                    # Para alguns casos onde o estado não é retornado diretamente
                    county = address['county'].upper()
                    # Aqui poderíamos mapear o condado para o estado, mas isso requer uma tabela de mapeamento
                
                if estado:
                    self.add_diagnostic("identificar_estado", True, f"Estado identificado: {estado}")
                    return estado
                else:
                    self.add_diagnostic("identificar_estado", False, "Estado não encontrado nos dados retornados")
            else:
                self.add_diagnostic("identificar_estado", False, f"Erro na API: {response.status_code}")
        
        except Exception as e:
            self.add_diagnostic("identificar_estado", False, f"Erro: {str(e)}")
        
        return None

    def identificar_municipio(self, lat, lon):
        """
        Identifica o município com base nas coordenadas usando uma API de geocodificação
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            
        Returns:
            str: Nome do município ou None se não for possível identificar
        """
        try:
            self.add_diagnostic("identificar_municipio", True, f"Buscando município para coordenadas {lat}, {lon}")
            
            # Usa a API Nominatim do OpenStreetMap (gratuita e sem necessidade de chave API)
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&accept-language=pt-BR"
            
            headers = {
                'User-Agent': 'EroView/1.0 (contato@erosoftware.com.br)'  # Importante para não ser bloqueado
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extrai o município
                municipio = None
                address = data.get('address', {})
                
                # Tenta obter o município em diferentes formatos
                if 'city' in address:
                    municipio = address['city'].upper()
                elif 'town' in address:
                    municipio = address['town'].upper()
                elif 'village' in address:
                    municipio = address['village'].upper()
                elif 'municipality' in address:
                    municipio = address['municipality'].upper()
                
                if municipio:
                    self.add_diagnostic("identificar_municipio", True, f"Município identificado: {municipio}")
                    return municipio
                else:
                    self.add_diagnostic("identificar_municipio", False, "Município não encontrado nos dados retornados")
            else:
                self.add_diagnostic("identificar_municipio", False, f"Erro na API: {response.status_code}")
        
        except Exception as e:
            self.add_diagnostic("identificar_municipio", False, f"Erro: {str(e)}")
        
        return None

    def buscar_propriedade(self, lat, lon):
        """
        Busca uma propriedade com base nas coordenadas
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
            
        Returns:
            dict: Informações da propriedade ou None se não encontrada
        """
        try:
            self.add_diagnostic("find_property", True, f"Buscando propriedade em {lat}, {lon}")
            
            # Verifica se a página do SICAR foi carregada corretamente
            try:
                WebDriverWait(self.driver, 20).until(
                    lambda d: "consultapublica.car.gov.br" in d.current_url.lower()
                )
            except TimeoutException:
                self.add_diagnostic("find_property", False, "Não foi possível acessar o portal do SICAR")
                return None
            
            # Verifica se há algum formulário de pesquisa de coordenadas
            try:
                # Verifica se existe um campo para inserir coordenadas diretamente
                input_coord = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'coord') or contains(@id, 'latit') or contains(@id, 'longit')]")
                
                if input_coord:
                    # Modo 1: Inserir coordenadas diretamente
                    self.add_diagnostic("find_property", True, "Inserindo coordenadas no formulário")
                    
                    # Busca por campos de latitude e longitude
                    lat_input = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'lat')]")
                    lon_input = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'lon')]")
                    
                    if lat_input and lon_input:
                        # Limpa os campos
                        lat_input[0].clear()
                        lon_input[0].clear()
                        
                        # Insere as coordenadas
                        lat_input[0].send_keys(str(lat))
                        lon_input[0].send_keys(str(lon))
                        
                        # Busca pelo botão de busca
                        buscar_btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'btn-primary') or contains(text(), 'Busc')]")
                        buscar_btn.click()
                        
                        # Aguarda o resultado
                        time.sleep(3)
                else:
                    # Modo 2: Usar o mapa para selecionar
                    self.add_diagnostic("find_property", True, "Usando mapa para localizar coordenadas")
                    
                    # Verifica se o mapa está visível
                    map_element = WebDriverWait(self.driver, 10).until(
                        EC.visibility_of_element_located((By.ID, "mapContainer"))
                    )
                    
                    # Clica no botão de ir para coordenadas, se existir
                    try:
                        goto_coord_btn = self.driver.find_element(By.XPATH, "//button[contains(@title, 'coordenada') or contains(@title, 'local')]")
                        goto_coord_btn.click()
                        time.sleep(1)
                        
                        # Verifica se apareceu um popup para inserir coordenadas
                        coord_popup = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'popup') or contains(@class, 'modal')]")
                        
                        if coord_popup:
                            # Busca os campos de entrada
                            inputs = coord_popup[0].find_elements(By.TAG_NAME, "input")
                            
                            if len(inputs) >= 2:
                                # Limpa e preenche
                                inputs[0].clear()
                                inputs[0].send_keys(str(lat))
                                inputs[1].clear()
                                inputs[1].send_keys(str(lon))
                                
                                # Busca botão de confirmar
                                confirm_btn = coord_popup[0].find_element(By.XPATH, ".//button[contains(@class, 'btn-primary') or contains(text(), 'Confirm') or contains(text(), 'OK')]")
                                confirm_btn.click()
                                time.sleep(2)
                    except:
                        # Tenta usar JavaScript para centralizar o mapa na coordenada
                        self.driver.execute_script("""
                            // Verifica se existe a função de mapa do Leaflet
                            if (typeof L !== 'undefined' && map) {
                                // Centraliza o mapa nas coordenadas
                                map.setView([{lat}, {lon}], 15);
                                
                                // Adiciona um marcador
                                L.marker([{lat}, {lon}]).addTo(map);
                            }
                        """, lat, lon)
                        time.sleep(2)
            
            except Exception as e:
                self.add_diagnostic("find_property", False, f"Erro ao inserir coordenadas: {str(e)}")
            
            # Verifica se a lista de imóveis foi carregada
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-imovel, div.leaflet-overlay-pane"))
                )
            except TimeoutException:
                self.add_diagnostic("find_property", False, "Lista de imóveis não encontrada")
                return None
            
            # Busca propriedades na lista ou no mapa
            propriedades = self.driver.find_elements(By.CSS_SELECTOR, "table.table-imovel tbody tr")
            
            if propriedades:
                # Há uma lista de propriedades, seleciona a primeira
                self.add_diagnostic("find_property", True, f"Encontradas {len(propriedades)} propriedades")
                
                # Clica na primeira propriedade
                propriedades[0].click()
                time.sleep(3)
                
                # Extrai informações
                try:
                    nome = propriedades[0].find_element(By.CSS_SELECTOR, "td:nth-child(1)").text
                    car = propriedades[0].find_element(By.CSS_SELECTOR, "td:nth-child(2)").text
                    area = propriedades[0].find_element(By.CSS_SELECTOR, "td:nth-child(3)").text
                    
                    resultado = {
                        'nome': nome,
                        'car': car,
                        'area': area
                    }
                    
                    self.add_diagnostic("find_property", True, f"Propriedade selecionada: {nome}")
                    return resultado
                except:
                    # Se não conseguir extrair os detalhes da tabela, retorna informações genéricas
                    self.add_diagnostic("find_property", True, "Propriedade encontrada, mas sem detalhes")
                    return {'nome': 'Propriedade encontrada', 'car': 'N/A', 'area': 'N/A'}
            else:
                # Sem lista de propriedades, verifica se há elementos no mapa
                overlay_elements = self.driver.find_elements(By.CSS_SELECTOR, "path.leaflet-interactive")
                
                if overlay_elements:
                    # Há elementos no mapa, clica no primeiro
                    self.add_diagnostic("find_property", True, f"Encontradas {len(overlay_elements)} propriedades no mapa")
                    
                    try:
                        # Tenta clicar no elemento do mapa mais próximo das coordenadas
                        self.driver.execute_script("""
                            // Verifica se existe a função de mapa do Leaflet
                            if (typeof L !== 'undefined' && map) {
                                // Simula um clique no local das coordenadas
                                map.fire('click', {
                                    latlng: L.latLng(arguments[0], arguments[1]),
                                    originalEvent: { preventDefault: function() {} }
                                });
                            }
                        """, lat, lon)
                        time.sleep(3)
                        
                        # Busca informações após o clique
                        info_elements = self.driver.find_elements(By.CSS_SELECTOR, ".leaflet-popup-content, .info-panel")
                        
                        if info_elements:
                            # Extrai informações do popup ou painel
                            info_text = info_elements[0].text
                            
                            # Busca padrões comuns de informação
                            nome_match = re.search(r"Nome:?\s*([^\n]+)", info_text)
                            car_match = re.search(r"CAR:?\s*([^\n]+)", info_text)
                            area_match = re.search(r"Área:?\s*([^\n]+)", info_text)
                            
                            nome = nome_match.group(1) if nome_match else "Propriedade sem nome"
                            car = car_match.group(1) if car_match else "CAR não disponível"
                            area = area_match.group(1) if area_match else "Área não disponível"
                            
                            resultado = {
                                'nome': nome,
                                'car': car,
                                'area': area
                            }
                            
                            self.add_diagnostic("find_property", True, f"Propriedade selecionada: {nome}")
                            return resultado
                    except Exception as e:
                        self.add_diagnostic("find_property", False, f"Erro ao interagir com o mapa: {str(e)}")
                
                # Se chegou aqui, não encontrou propriedades
                self.add_diagnostic("find_property", False, "Nenhuma propriedade encontrada")
                return None
            
        except Exception as e:
            self.add_diagnostic("find_property", False, f"Erro: {str(e)}")
            return None

    def extrair_mapa(self, propriedade):
        """
        Extrai o mapa da propriedade selecionada e prepara visualização interativa
        
        Args:
            propriedade (dict): Informações da propriedade
            
        Returns:
            str: URL para visualização do mapa interativo ou None se falhar
        """
        try:
            self._update_status("Extraindo mapa da propriedade...", 80)
            self.add_diagnostic("extract_map", True, "Extraindo mapa da propriedade")
            
            # Aguarda o carregamento do mapa
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#mapContainer canvas, .leaflet-container"))
                )
            except TimeoutException:
                self._update_status("Erro: Mapa não encontrado", 80)
                self.add_diagnostic("extract_map", False, "Mapa não encontrado")
                return None
            
            # Aguarda mais um pouco para o mapa renderizar completamente
            time.sleep(3)
            
            # Verificar se estamos em uma visualização do tipo Leaflet (mapa interativo)
            is_leaflet = self.driver.execute_script("""
                return typeof L !== 'undefined' && document.querySelector('.leaflet-container') !== null;
            """)
            
            if is_leaflet:
                # Para mapas Leaflet, vamos melhorar a experiência e preservar a interatividade
                self.log.info("Mapa interativo (Leaflet) encontrado")
                self._update_status("Preparando mapa interativo...", 85)
                
                # Melhorar a aparência do mapa
                self.driver.execute_script("""
                    // Melhorar aparência sem remover funcionalidade
                    document.querySelectorAll('.leaflet-control').forEach(el => {
                        // Manter controles mas reduzir opacidade quando não em uso
                        el.style.opacity = '0.6';
                        el.addEventListener('mouseover', function() { this.style.opacity = '1'; });
                        el.addEventListener('mouseout', function() { this.style.opacity = '0.6'; });
                    });
                    
                    // Destacar os contornos das propriedades
                    document.querySelectorAll('path.leaflet-interactive').forEach(el => {
                        el.setAttribute('stroke', '#FFCC00');
                        el.setAttribute('stroke-width', '3');
                        el.setAttribute('fill-opacity', '0.2');
                    });
                    
                    // Adicionar camada do Google Satellite se disponível
                    if (typeof L !== 'undefined' && typeof L.gridLayer !== 'undefined') {
                        try {
                            var googleSat = L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
                                maxZoom: 20,
                                subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
                                attribution: ' Google'
                            });
                            
                            // Se tivermos acesso ao objeto map, adicionar a camada
                            if (typeof map !== 'undefined') {
                                googleSat.addTo(map);
                                
                                // Criar um controle de camadas se não existir
                                if (!document.querySelector('.leaflet-control-layers')) {
                                    var baseMaps = {
                                        "Padrão": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'),
                                        "Satélite": googleSat
                                    };
                                    L.control.layers(baseMaps).addTo(map);
                                }
                            }
                        } catch(e) {
                            console.error("Erro ao adicionar camada Google:", e);
                        }
                    }
                    
                    // Adicionar botão de fullscreen
                    if (typeof L !== 'undefined' && !document.querySelector('.leaflet-control-fullscreen')) {
                        try {
                            var fullscreenButton = document.createElement('a');
                            fullscreenButton.className = 'leaflet-control-fullscreen';
                            fullscreenButton.innerHTML = '';
                            fullscreenButton.style.fontSize = '18px';
                            fullscreenButton.style.backgroundColor = 'white';
                            fullscreenButton.style.padding = '5px 8px';
                            fullscreenButton.style.border = '2px solid rgba(0,0,0,0.2)';
                            fullscreenButton.style.borderRadius = '4px';
                            fullscreenButton.style.cursor = 'pointer';
                            
                            fullscreenButton.onclick = function() {
                                var mapEl = document.querySelector('.leaflet-container');
                                if (mapEl) {
                                    if (!document.fullscreenElement) {
                                        if (mapEl.requestFullscreen) {
                                            mapEl.requestFullscreen();
                                        } else if (mapEl.mozRequestFullScreen) {
                                            mapEl.mozRequestFullScreen();
                                        } else if (mapEl.webkitRequestFullscreen) {
                                            mapEl.webkitRequestFullscreen();
                                        } else if (mapEl.msRequestFullscreen) {
                                            mapEl.msRequestFullscreen();
                                        }
                                    } else {
                                        if (document.exitFullscreen) {
                                            document.exitFullscreen();
                                        } else if (document.mozCancelFullScreen) {
                                            document.mozCancelFullScreen();
                                        } else if (document.webkitExitFullscreen) {
                                            document.webkitExitFullscreen();
                                        } else if (document.msExitFullscreen) {
                                            document.msExitFullscreen();
                                        }
                                    }
                                }
                            };
                            
                            var controlContainer = document.querySelector('.leaflet-top.leaflet-right');
                            if (controlContainer) {
                                var controlDiv = document.createElement('div');
                                controlDiv.className = 'leaflet-control-fullscreen leaflet-bar leaflet-control';
                                controlDiv.appendChild(fullscreenButton);
                                controlContainer.appendChild(controlDiv);
                            }
                        } catch(e) {
                            console.error("Erro ao adicionar botão de fullscreen:", e);
                        }
                    }
                """)
                
                # Capturar a URL atual do mapa para acesso futuro
                mapa_url = self.driver.current_url
                self._update_status("Mapa interativo pronto!", 90)
                
                # Em vez de retornar apenas uma imagem, retornaremos a URL para o iframe
                self.log.info(f"Mapa interativo disponível em: {mapa_url}")
                self.add_diagnostic("extract_map", True, f"Mapa interativo: {mapa_url}")
                return mapa_url
                
            else:
                # Para mapas não-interativos, continuar com a abordagem anterior
                self.log.info("Mapa estático encontrado, capturando screenshot")
                self._update_status("Capturando imagem do mapa...", 85)
                
                # Melhora a visualização do mapa (remove controles, destaca limites)
                self.driver.execute_script("""
                    // Remove controles desnecessários
                    document.querySelectorAll('.leaflet-control-container, .leaflet-top, .leaflet-bottom').forEach(el => {
                        el.style.display = 'none';
                    });
                    
                    // Destaca os contornos das propriedades
                    document.querySelectorAll('path.leaflet-interactive').forEach(el => {
                        el.setAttribute('stroke', '#FFCC00');
                        el.setAttribute('stroke-width', '3');
                        el.setAttribute('fill-opacity', '0.2');
                    });
                """)
                
                # Captura a tela
                mapa_filename = f"sicar_map_{int(time.time())}.png"
                mapa_path = os.path.join(self.maps_dir, mapa_filename)
                
                # Encontra o elemento do mapa
                mapa_element = None
                try:
                    mapa_element = self.driver.find_element(By.ID, "mapContainer")
                except:
                    try:
                        mapa_element = self.driver.find_element(By.CSS_SELECTOR, ".leaflet-container")
                    except:
                        self.log.warning("Elemento específico do mapa não encontrado, usando captura de tela inteira")
                
                if mapa_element:
                    # Tira screenshot do elemento
                    mapa_element.screenshot(mapa_path)
                else:
                    # Tira screenshot da tela inteira
                    self.driver.save_screenshot(mapa_path)
                
                # Verifica se o arquivo foi criado
                if not os.path.exists(mapa_path):
                    self._update_status("Erro ao salvar mapa", 85)
                    self.add_diagnostic("extract_map", False, "Falha ao salvar mapa")
                    return None
                
                # Tenta melhorar a imagem
                try:
                    from PIL import Image, ImageEnhance
                    
                    # Abre a imagem
                    img = Image.open(mapa_path)
                    
                    # Melhora o contraste
                    enhancer = ImageEnhance.Contrast(img)
                    img = enhancer.enhance(1.2)
                    
                    # Melhora a saturação
                    enhancer = ImageEnhance.Color(img)
                    img = enhancer.enhance(1.3)
                    
                    # Salva a imagem melhorada
                    img.save(mapa_path)
                except:
                    # Falha ao processar a imagem, mas não é crítico
                    pass
                
                self._update_status("Mapa extraído com sucesso", 90)
                self.add_diagnostic("extract_map", True, f"Mapa salvo em: {mapa_path}")
                return os.path.basename(mapa_path)
                
        except Exception as e:
            self._update_status(f"Erro ao extrair mapa: {str(e)}", 80)
            self.add_diagnostic("extract_map", False, f"Erro: {str(e)}")
            return None
    
    def abrir_sicar(self):
        """
        Abre a página principal do SICAR
        
        Returns:
            bool: True se conseguiu abrir a página, False caso contrário
        """
        try:
            # Atualiza status
            self._update_status("Abrindo página do SICAR...", 10)
            
            # URL do SICAR
            url = "https://consultapublica.car.gov.br/publico/imoveis/index"
            
            # Abre a URL
            self.driver.get(url)
            
            # Espera a página carregar
            self.log.info(f"Aguardando carregamento da página principal do SICAR: {url}")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Verifica se carregou corretamente
            if "Sistema Nacional de Cadastro Ambiental Rural" in self.driver.page_source:
                self.log.info("Página do SICAR carregada com sucesso")
                self._update_status("Página do SICAR carregada", 20)
                self.add_diagnostic("open_sicar", True, "Página do SICAR carregada com sucesso")
                return True
            else:
                self.log.warning("Página do SICAR carregada, mas conteúdo não parece correto")
                self._update_status("Erro ao verificar página do SICAR", 20)
                self.add_diagnostic("open_sicar", False, "Conteúdo da página não parece ser do SICAR")
                return False
                
        except Exception as e:
            self.log.error(f"Erro ao abrir página do SICAR: {str(e)}")
            self._update_status("Erro ao abrir página do SICAR", 10)
            self.add_diagnostic("open_sicar", False, f"Erro: {str(e)}")
            return False

    def close(self):
        """
        Fecha o navegador e libera recursos
        """
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.info("Navegador fechado")
        except Exception as e:
            logger.error(f"Erro ao fechar navegador: {str(e)}")
            
    def save_screenshot(self, filename="screenshot.png"):
        """
        Salva um screenshot da tela atual
        
        Args:
            filename (str): Nome do arquivo para salvar o screenshot
        
        Returns:
            str: Caminho do arquivo salvo ou None se falhar
        """
        try:
            if not self.driver:
                return None
                
            filepath = os.path.join(self.maps_dir, filename)
            self.driver.save_screenshot(filepath)
            return filepath
        except Exception as e:
            logger.error(f"Erro ao salvar screenshot: {str(e)}")
            return None

    def selecionar_elemento_com_texto(self, texto, tipo_elemento="option", timeout=10):
        """
        Seleciona um elemento baseado no texto contido nele
        
        Args:
            texto (str): Texto para buscar
            tipo_elemento (str): Tipo de elemento HTML (default: option)
            timeout (int): Tempo máximo de espera em segundos
            
        Returns:
            bool: True se clicou com sucesso, False caso contrário
        """
        try:
            # Normaliza o texto de busca (remove acentos e converte para maiúsculas)
            texto_normalizado = unidecode(texto.upper()).strip()
            
            # Espera elementos do tipo especificado
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, tipo_elemento))
            )
            
            # Encontra todos os elementos do tipo
            elementos = self.driver.find_elements(By.TAG_NAME, tipo_elemento)
            
            # Itera pelos elementos buscando o texto
            for elemento in elementos:
                texto_elemento = elemento.text.strip()
                texto_elemento_normalizado = unidecode(texto_elemento.upper()).strip()
                
                # Verifica se o texto está contido (não precisa ser exatamente igual)
                if texto_normalizado in texto_elemento_normalizado:
                    # Rola até o elemento para garantir que ele esteja visível
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                    time.sleep(0.5)  # Pequena pausa para garantir que o scroll terminou
                    
                    # Tenta clicar no elemento
                    elemento.click()
                    time.sleep(1)  # Espera para processar o clique
                    return True
            
            # Se não encontrou com o método anterior, tenta um método mais flexível com JavaScript
            self.driver.execute_script("""
                // Busca elementos do tipo especificado
                var elementos = document.getElementsByTagName(arguments[0]);
                var texto = arguments[1].toUpperCase();
                
                // Função para normalizar texto (remover acentos)
                function normalizar(texto) {
                    return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase().trim();
                }
                
                // Busca elementos que contêm o texto
                for (var i = 0; i < elementos.length; i++) {
                    var el = elementos[i];
                    var textoEl = el.textContent || el.innerText;
                    if (normalizar(textoEl).includes(texto)) {
                        // Rola até o elemento e clica
                        el.scrollIntoView();
                        el.click();
                        return true;
                    }
                }
                return false;
            """, tipo_elemento, texto_normalizado)
            
            # Pequena pausa para processar a ação
            time.sleep(1)
            
            return False
        
        except Exception as e:
            logger.error(f"Erro ao selecionar elemento com texto '{texto}': {str(e)}")
            return False
    
    def mover_cursor_para(self, elemento):
        """
        Move o cursor para um elemento
        
        Args:
            elemento: Elemento web para mover o cursor
            
        Returns:
            bool: True se moveu com sucesso, False caso contrário
        """
        try:
            # Verifica se o elemento está visível
            if not elemento.is_displayed():
                # Rola até o elemento para garantir que seja visível
                self.driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                time.sleep(0.5)
            
            # Cria ação para mover o mouse
            acao = ActionChains(self.driver)
            acao.move_to_element(elemento)
            acao.perform()
            return True
        except Exception as e:
            logger.error(f"Erro ao mover cursor: {str(e)}")
            
            # Tenta mover usando JavaScript como fallback
            try:
                # Simula hover via JavaScript
                self.driver.execute_script("""
                    var element = arguments[0];
                    var mouseoverEvent = new MouseEvent('mouseover', {
                        'view': window,
                        'bubbles': true,
                        'cancelable': true
                    });
                    element.dispatchEvent(mouseoverEvent);
                """, elemento)
                return True
            except:
                return False
    
    def selecionar_estado(self, estado):
        """
        Seleciona um estado no mapa do SICAR.
        Implementação que passa o cursor sobre o estado e clica quando aparecer o balão.
        
        Args:
            estado (str): Nome do estado
            
        Returns:
            bool: True se o estado foi selecionado com sucesso, False caso contrário
        """
        try:
            # Normaliza o nome do estado para evitar problemas com acentos
            estado_normalizado = unidecode(estado.upper())
            estado_sigla = self._mapear_estado_para_sigla(estado)
            
            self.log.info(f"Tentando selecionar estado: {estado} (sigla: {estado_sigla})")
            self._update_status(f"Selecionando estado: {estado}", 30)
            self.save_screenshot("pre_selecao_estado.png")

            # Localizações aproximadas do cursor para estados populares
            # Valores em porcentagem da tela
            coordenadas_estados = {
                "PR": {"x": 0.52, "y": 0.70},    # Paraná
                "SP": {"x": 0.55, "y": 0.63},    # São Paulo
                "SC": {"x": 0.51, "y": 0.75},    # Santa Catarina
                "RS": {"x": 0.50, "y": 0.85},    # Rio Grande do Sul
                "MG": {"x": 0.60, "y": 0.55},    # Minas Gerais
                # Adicionar mais estados conforme necessário
            }
            
            # Se não temos coordenadas específicas para o estado, usar abordagem genérica
            if estado_sigla not in coordenadas_estados:
                self.log.warning(f"Coordenadas para {estado_sigla} não definidas, usando método alternativo")
                self._update_status(f"Estado {estado} não mapeado, tentando alternativa", 30)
                return self._selecionar_estado_generico(estado, estado_sigla)
            
            # Obter as coordenadas para o estado alvo
            coords = coordenadas_estados[estado_sigla]
            
            # Obter dimensões da janela do navegador
            viewport_size = self.driver.execute_script("""
                return {
                    width: window.innerWidth,
                    height: window.innerHeight
                };
            """)
            
            # Calcular coordenadas absolutas
            x_abs = int(coords["x"] * viewport_size["width"])
            y_abs = int(coords["y"] * viewport_size["height"])
            
            self.log.info(f"Movendo cursor para coordenadas: x={x_abs}, y={y_abs}")
            self._update_status(f"Movendo cursor sobre o estado {estado}", 35)
            
            # Remover qualquer marcador anterior (caso tenha)
            self.driver.execute_script("""
                var oldMarkers = document.querySelectorAll('.cursor-marker');
                oldMarkers.forEach(function(marker) {
                    marker.remove();
                });
            """)
            
            # Criar marcador visual para debug
            self.driver.execute_script(f"""
                var marker = document.createElement('div');
                marker.className = 'cursor-marker';
                marker.style.position = 'absolute';
                marker.style.left = '{x_abs}px';
                marker.style.top = '{y_abs}px';
                marker.style.width = '10px';
                marker.style.height = '10px';
                marker.style.backgroundColor = 'red';
                marker.style.borderRadius = '50%';
                marker.style.zIndex = '9999';
                marker.style.pointerEvents = 'none'; // Para não interferir nos cliques
                document.body.appendChild(marker);
            """)
            
            time.sleep(1)
            self.save_screenshot("marcador_posicao.png")
            
            # Resetar posição do mouse (importante para garantir posição relativa correta)
            actions = ActionChains(self.driver)
            actions.move_to_element(self.driver.find_element(By.TAG_NAME, "body"))
            actions.perform()
            
            # Encontrar o mapa SVG ou elemento de mapa principal
            mapa_element = None
            try:
                # Tentar diferentes seletores para o mapa
                seletores = [
                    "svg", 
                    ".leaflet-container", 
                    "#mapContainer", 
                    "map",
                    "img[usemap]"
                ]
                
                for seletor in seletores:
                    try:
                        mapa_element = self.driver.find_element(By.CSS_SELECTOR, seletor)
                        if mapa_element and mapa_element.is_displayed():
                            self.log.info(f"Elemento de mapa encontrado: {seletor}")
                            break
                    except:
                        pass
            except:
                self.log.warning("Não foi possível encontrar o elemento do mapa, usando body")
                mapa_element = self.driver.find_element(By.TAG_NAME, "body")
            
            # Obter posição do mapa
            if mapa_element:
                mapa_rect = self.driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return {
                        left: rect.left,
                        top: rect.top,
                        width: rect.width,
                        height: rect.height
                    };
                """, mapa_element)
                
                # Ajustar coordenadas relativas ao mapa, não à janela inteira
                x_rel = int(coords["x"] * mapa_rect["width"]) + mapa_rect["left"]
                y_rel = int(coords["y"] * mapa_rect["height"]) + mapa_rect["top"]
                
                self.log.info(f"Coordenadas ajustadas ao mapa: x={x_rel}, y={y_rel}")
                
                # Atualizar o marcador para posição correta
                self.driver.execute_script(f"""
                    var markers = document.querySelectorAll('.cursor-marker');
                    if (markers.length > 0) {{
                        markers[0].style.left = '{x_rel}px';
                        markers[0].style.top = '{y_rel}px';
                    }}
                """)
                
                # Usar moveTo em vez de moveByOffset para maior precisão
                actions = ActionChains(self.driver)
                actions.move_to_element_with_offset(mapa_element, 
                                                   int(coords["x"] * mapa_rect["width"]), 
                                                   int(coords["y"] * mapa_rect["height"]))
                actions.perform()
            else:
                # Usar moveByOffset como fallback
                actions = ActionChains(self.driver)
                actions.move_by_offset(x_abs, y_abs).perform()
            
            # Aguardar o balão aparecer
            self.log.info("Aguardando balão aparecer...")
            self._update_status("Aguardando o balão de seleção aparecer...", 40)
            time.sleep(3)
            self.save_screenshot("hover_estado.png")
            
            # Verificar se há tooltip/balão visível
            tooltip_visible = self.driver.execute_script("""
                var tooltips = document.querySelectorAll('.tooltip, [role="tooltip"], [data-tooltip], .leaflet-tooltip, .ui-tooltip, .tippy-box');
                var visibleTooltip = false;
                
                for (var i = 0; i < tooltips.length; i++) {
                    var tooltip = tooltips[i];
                    if (tooltip.offsetParent !== null) { // Elemento visível
                        visibleTooltip = true;
                        // Destacar o tooltip
                        tooltip.style.border = '2px solid red';
                        break;
                    }
                }
                
                // Se não encontrou tooltips específicos, procurar qualquer elemento que apareceu após o hover
                if (!visibleTooltip) {
                    var allElements = document.querySelectorAll('*');
                    for (var i = 0; i < allElements.length; i++) {
                        var el = allElements[i];
                        var styles = window.getComputedStyle(el);
                        
                        // Elementos que podem ser tooltips geralmente têm estas características
                        if (el.offsetParent !== null && // Visível
                            (styles.position === 'absolute' || styles.position === 'fixed') && // Posicionado
                            styles.zIndex && parseInt(styles.zIndex) > 1) { // Com z-index alto
                            
                            // Verificar se contém o nome do estado
                            if (el.textContent && (el.textContent.includes('Paraná') || 
                                                  el.textContent.includes('Parana') || 
                                                  el.textContent.includes('PARANÁ') || 
                                                  el.textContent.includes('PR'))) {
                                visibleTooltip = true;
                                el.style.border = '2px solid red';
                                break;
                            }
                        }
                    }
                }
                
                return visibleTooltip;
            """)
            
            if tooltip_visible:
                self.log.info("Balão detectado, clicando...")
                self._update_status("Balão detectado, clicando no estado", 45)
                # 2. Clicar na posição atual (onde está o balão)
                actions.click().perform()
                time.sleep(3)
                self.save_screenshot("apos_clique_balao.png")
                
                # Verificar se houve navegação para página do estado
                url_alterada = self.driver.execute_script("""
                    return window.location.href.includes('estado=PR') || 
                           window.location.href.includes('uf=PR') || 
                           window.location.href.toLowerCase().includes('parana');
                """)
                
                # Verificar se apareceu alguma indicação de seleção de município
                selecao_municipio = self.driver.execute_script("""
                    return document.body.innerHTML.includes('município') || 
                           document.body.innerHTML.includes('municipio') || 
                           document.body.innerHTML.includes('Douradina');
                """)
                
                if url_alterada or selecao_municipio:
                    self.log.info("Estado selecionado com sucesso!")
                    self._update_status("Estado selecionado com sucesso", 50)
                    return True
                else:
                    self.log.warning("Clique realizado, mas sem indicação clara de sucesso")
                    self._update_status("Verificando resultado da seleção", 45)
                    
                    # Verificar mudanças visuais que possam indicar seleção bem-sucedida
                    mudanca_visual = self._verificar_mudanca_visual()
                    if mudanca_visual:
                        self.log.info("Mudança visual detectada, considerando seleção bem-sucedida")
                        self._update_status("Estado selecionado com sucesso", 50)
                        return True
                    
                    # Tentar expandir a área de busca e tentar novamente
                    self.log.info("Tentando clicar em pontos próximos...")
                    self._update_status("Tentando clicar em pontos próximos", 40)
                    
                    # Matriz de pontos ao redor da coordenada original para tentar novos cliques
                    offsets = [
                        {"dx": -10, "dy": -10},
                        {"dx": 0, "dy": -10},
                        {"dx": 10, "dy": -10},
                        {"dx": -10, "dy": 0},
                        {"dx": 10, "dy": 0},
                        {"dx": -10, "dy": 10},
                        {"dx": 0, "dy": 10},
                        {"dx": 10, "dy": 10}
                    ]
                    
                    for i, offset in enumerate(offsets):
                        try:
                            # Calcular nova posição
                            new_x = x_abs + offset["dx"]
                            new_y = y_abs + offset["dy"]
                            
                            # Mover para a nova posição
                            actions = ActionChains(self.driver)
                            actions.move_by_offset(new_x - x_abs, new_y - y_abs).perform()
                            time.sleep(2)
                            
                            # Clicar
                            actions.click().perform()
                            time.sleep(3)
                            self.save_screenshot(f"tentativa_clique_{i+1}.png")
                            
                            # Verificar se houve sucesso
                            if self._verificar_mudanca_visual():
                                self.log.info(f"Seleção de estado realizada na tentativa {i+1}")
                                self._update_status("Estado selecionado com sucesso", 50)
                                return True
                        except Exception as e:
                            self.log.warning(f"Erro na tentativa {i+1}: {str(e)}")
            else:
                self.log.warning("Balão não detectado após hover")
                self._update_status("Balão não detectado, tentando clique direto", 40)
                
                # Tentar clique direto mesmo sem balão
                actions.click().perform()
                time.sleep(3)
                self.save_screenshot("clique_sem_balao.png")
                
                # Verificar se houve sucesso
                if self._verificar_mudanca_visual():
                    self.log.info("Estado possivelmente selecionado após clique direto")
                    self._update_status("Estado selecionado com sucesso", 50)
                    return True
            
            # Se chegamos aqui, fazer uma última tentativa direta
            self._update_status("Tentando método alternativo para selecionar estado", 35)
            return self._selecionar_estado_generico(estado, estado_sigla)
            
        except Exception as e:
            self.log.error(f"Erro ao tentar selecionar estado: {str(e)}")
            self._update_status(f"Erro ao selecionar estado: {str(e)}", 30)
            self.save_screenshot("erro_selecao_estado.png")
            return False
                
    def _selecionar_estado_generico(self, estado, estado_sigla):
        """
        Método alternativo para selecionar estados quando a abordagem principal falha
        
        Args:
            estado (str): Nome do estado
            estado_sigla (str): Sigla do estado
            
        Returns:
            bool: True se o estado foi selecionado com sucesso, False caso contrário
        """
        try:
            self.log.info("Tentando método alternativo para selecionar estado")
            
            # 1. Procurar por elementos que contenham o texto do estado
            elementos = self.driver.find_elements(By.XPATH, 
                f"//*[contains(text(),'{estado}') or contains(text(),'{estado_sigla}')]")
            
            for elem in elementos:
                if elem.is_displayed():
                    self.log.info(f"Elemento com texto do estado encontrado: {elem.text}")
                    
                    # Destacar visualmente
                    self.driver.execute_script("""
                        arguments[0].style.border = '3px solid red';
                        arguments[0].scrollIntoView({block: 'center'});
                    """, elem)
                    
                    time.sleep(1)
                    self.save_screenshot("elemento_estado_encontrado.png")
                    
                    # Tentar clicar
                    try:
                        elem.click()
                        time.sleep(3)
                        self.save_screenshot("apos_clique_elemento.png")
                        
                        if self._verificar_mudanca_visual():
                            self.log.info("Estado selecionado via texto")
                            self._update_status("Estado selecionado com sucesso", 50)
                            return True
                    except Exception as e:
                        self.log.warning(f"Erro ao clicar no elemento: {str(e)}")
                        
                        # Tentar via JavaScript
                        try:
                            self.driver.execute_script("arguments[0].click();", elem)
                            time.sleep(3)
                            self.save_screenshot("apos_clique_js.png")
                            
                            if self._verificar_mudanca_visual():
                                self.log.info("Estado selecionado via clique JS")
                                self._update_status("Estado selecionado com sucesso", 50)
                                return True
                        except:
                            pass
            
            # 2. Última alternativa: manipular variáveis JavaScript
            js_resultado = self.driver.execute_script(f"""
                try {{
                    if (typeof window.estado !== 'undefined') {{
                        window.estado = '{estado}';
                        return true;
                    }}
                    if (typeof window.uf !== 'undefined') {{
                        window.uf = '{estado_sigla}';
                        return true;
                    }}
                    return false;
                }} catch(e) {{
                    return false;
                }}
            """)
            
            if js_resultado:
                self.log.info("Variáveis JS manipuladas com sucesso")
                time.sleep(2)
                self._update_status("Estado selecionado com sucesso", 50)
                return True
            
            self.log.error("Todas as tentativas de selecionar estado falharam")
            return False
            
        except Exception as e:
            self.log.error(f"Erro no método genérico: {str(e)}")
            return False

    def selecionar_municipio(self, municipio):
        """
        Seleciona um município no dropdown do SICAR
        
        Args:
            municipio (str): Nome do município
            
        Returns:
            bool: True se o município foi selecionado com sucesso, False caso contrário
        """
        try:
            self.add_diagnostic("select_municipality", True, f"Tentando selecionar município: {municipio}")
            
            # Aguarda carregamento da página e do javascript que pode preencher dinamicamente o select
            time.sleep(3)
            
            # Primeiro tenta encontrar o elemento select de municípios usando vários seletores possíveis
            selectors = [
                (By.ID, "selectMunicipio"),
                (By.NAME, "municipio"),
                (By.CSS_SELECTOR, "select[id*='munic' i], select[name*='munic' i]"),
                (By.XPATH, "//select[contains(@id, 'munic') or contains(@name, 'munic') or contains(@class, 'munic')]"),
                (By.XPATH, "//label[contains(text(), 'Município')]/following::select[1]"),
                (By.XPATH, "//label[contains(text(), 'Cidade')]/following::select[1]")
            ]
            
            municipio_select = None
            for selector_type, selector_value in selectors:
                try:
                    elementos = self.driver.find_elements(selector_type, selector_value)
                    if elementos and len(elementos) > 0:
                        municipio_select = elementos[0]
                        self.add_diagnostic("select_municipality", True, f"Seletor de municípios encontrado: {selector_type}={selector_value}")
                        break
                except:
                    continue
            
            # Se não encontrou o seletor de municípios, tenta abordagem mais agressiva
            if not municipio_select:
                self.add_diagnostic("select_municipality", True, "Tentando encontrar qualquer elemento select na página")
                try:
                    # Pega todos os selects da página
                    selects = self.driver.find_elements(By.TAG_NAME, "select")
                    
                    # Se já encontramos anteriormente um select para estados, tenta encontrar outro select
                    if selects and len(selects) > 1:
                        # Filtra selects que não são o de estados (que já deve ter sido selecionado)
                        for select in selects:
                            try:
                                # Verifica o texto das opções
                                options = select.find_elements(By.TAG_NAME, "option")
                                textos_opcoes = [opt.text.upper() for opt in options if opt.text.strip()]
                                
                                # Se tem mais de 10 opções (provável lista de municípios) e não contém nomes típicos de estados
                                estados_br = ["ACRE", "BAHIA", "PARANÁ", "SÃO PAULO", "RIO DE JANEIRO", "MINAS GERAIS"]
                                
                                # Se pelo menos 3 estados conhecidos estiverem nas opções, considera que esse é o select de estados
                                estados_encontrados = sum(1 for e in estados_br if any(e in opt_text for opt_text in textos_opcoes))
                                if len(textos_opcoes) > 10 and estados_encontrados < 3:
                                    municipio_select = select
                                    self.add_diagnostic("select_municipality", True, "Seletor de municípios identificado por exclusão")
                                    break
                            except:
                                continue
                except Exception as e:
                    self.add_diagnostic("select_municipality", False, f"Erro ao procurar selects: {str(e)}")
            
            # Se ainda não encontrou, tenta via JavaScript
            if not municipio_select:
                try:
                    script = """
                        // Tenta encontrar o dropdown de municípios por diferentes meios
                        var municipioSelect = document.querySelector('#selectMunicipio, select[name*="munic" i], select[id*="munic" i]');
                        
                        // Se não encontrou diretamente, procura o segundo select da página
                        if (!municipioSelect) {
                            var selects = document.querySelectorAll('select');
                            if (selects.length > 1) {
                                // Assume que o segundo select é o de municípios
                                municipioSelect = selects[1];
                            }
                        }
                        
                        return municipioSelect ? true : false;
                    """
                    
                    result = self.driver.execute_script(script)
                    if result:
                        # Se encontrou via JavaScript, tenta novamente com Selenium
                        try:
                            municipio_select = self.driver.find_element(By.CSS_SELECTOR, '#selectMunicipio, select[name*="munic" i], select[id*="munic" i]')
                        except:
                            try:
                                selects = self.driver.find_elements(By.TAG_NAME, 'select')
                                if len(selects) > 1:
                                    municipio_select = selects[1]
                            except:
                                pass
                except:
                    pass
            
            # Verifica se o seletor está habilitado
            if not municipio_select.is_enabled():
                self.add_diagnostic("select_municipality", True, "Seletor de municípios desabilitado, aguardando...")
                
                # Aguarda mais tempo, pode ser que o JavaScript da página ainda esteja carregando as opções
                time.sleep(5)
                
                # Verifica novamente
                if not municipio_select.is_enabled():
                    # Tenta habilitar via JavaScript
                    try:
                        self.driver.execute_script("""
                            arguments[0].disabled = false;
                            arguments[0].style.opacity = '1';
                        """, municipio_select)
                        
                        if not municipio_select.is_enabled():
                            self.add_diagnostic("select_municipality", False, "Seletor de municípios permanece desabilitado")
                            return False
                    except:
                        self.add_diagnostic("select_municipality", False, "Seletor de municípios desabilitado")
                        return False
            
            # Rola até o elemento para garantir que ele esteja visível
            self.driver.execute_script("arguments[0].scrollIntoView(true);", municipio_select)
            time.sleep(0.5)
            
            # Clica para abrir o dropdown
            try:
                municipio_select.click()
                time.sleep(1)
            except Exception as click_error:
                self.add_diagnostic("select_municipality", True, f"Aviso ao clicar no seletor: {str(click_error)}")
                # Continua mesmo com erro, pois algumas implementações não precisam do clique
            
            # Procura a opção com o texto do município
            municipio_normalizado = unidecode(municipio.upper())
            
            # Primeiro tenta método direto do Selenium
            try:
                select_obj = Select(municipio_select)
                
                # Tenta diferentes métodos para encontrar a opção correta
                # 1. Texto exato
                try:
                    select_obj.select_by_visible_text(municipio)
                    time.sleep(1)
                    self.add_diagnostic("select_municipality", True, f"Município {municipio} selecionado por texto exato")
                    time.sleep(2)
                except:
                    # 2. Texto aproximado (qualquer opção que contenha o nome do município)
                    encontrou = False
                    for option in select_obj.options:
                        option_text = option.text
                        option_norm = unidecode(option_text.upper())
                        
                        if municipio_normalizado in option_norm:
                            select_obj.select_by_visible_text(option_text)
                            self.add_diagnostic("select_municipality", True, f"Município {municipio} selecionado por texto aproximado: {option_text}")
                            time.sleep(2)
                            encontrou = True
                            break
                    
                    if not encontrou:
                        # 3. Texto parcial (se o município for composto, tenta apenas a primeira parte)
                        partes_municipio = municipio_normalizado.split()
                        if len(partes_municipio) > 1:
                            primeira_parte = partes_municipio[0]
                            for option in select_obj.options:
                                option_text = option.text
                                option_norm = unidecode(option_text.upper())
                                
                                if primeira_parte in option_norm:
                                    select_obj.select_by_visible_text(option_text)
                                    self.add_diagnostic("select_municipality", True, f"Município {municipio} selecionado por primeira parte do nome: {option_text}")
                                    time.sleep(2)
                                    encontrou = True
                                    break
                            
                        if not encontrou:
                            self.add_diagnostic("select_municipality", False, f"Município {municipio} não encontrado na lista")
                            return False
            
            except Exception as select_error:
                self.add_diagnostic("select_municipality", True, f"Erro ao usar Select: {str(select_error)}")
                
                # Se falhou o método direto, tenta abordagem via JavaScript
                try:
                    script = """
                        var select = arguments[0];
                        var municipioTexto = arguments[1].toUpperCase();
                        
                        function removerAcentos(texto) {
                            return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toUpperCase();
                        }
                        
                        // Tenta encontrar uma opção que contenha o texto do município
                        for (var i = 0; i < select.options.length; i++) {
                            var opt = select.options[i];
                            var optTexto = removerAcentos(opt.text.toUpperCase());
                            
                            if (optTexto.includes(removerAcentos(municipioTexto))) {
                                select.selectedIndex = i;
                                select.dispatchEvent(new Event('change', { bubbles: true }));
                                return true;
                            }
                        }
                        
                        // Se não encontrou com o texto completo, tenta apenas a primeira palavra
                        var primeiraParte = removerAcentos(municipioTexto).split(' ')[0];
                        for (var i = 0; i < select.options.length; i++) {
                            var opt = select.options[i];
                            var optTexto = removerAcentos(opt.text.toUpperCase());
                            
                            if (optTexto.includes(primeiraParte)) {
                                select.selectedIndex = i;
                                select.dispatchEvent(new Event('change', { bubbles: true }));
                                return true;
                            }
                        }
                        
                        return false;
                    """
                    
                    result = self.driver.execute_script(script, municipio_select, municipio)
                    if result:
                        self.add_diagnostic("select_municipality", True, f"Município {municipio} selecionado via JavaScript")
                        time.sleep(2)
                    else:
                        self.add_diagnostic("select_municipality", False, f"Município {municipio} não encontrado via JavaScript")
                        return False
                except Exception as js_error:
                    self.add_diagnostic("select_municipality", False, f"Erro JavaScript: {str(js_error)}")
                    return False
            
            # Após selecionar o município, tenta localizar e clicar no botão de busca
            try:
                # Procura botões que possam ser de busca/pesquisa
                botoes_busca = self.driver.find_elements(By.XPATH, 
                    "//button[contains(text(), 'Buscar') or contains(text(), 'Pesquisar') or contains(text(), 'Consultar') or contains(@class, 'btn-primary')]")
                
                if botoes_busca:
                    botoes_busca[0].click()
                    time.sleep(2)
                    self.add_diagnostic("select_municipality", True, "Botão de busca clicado")
                else:
                    # Tenta via JavaScript
                    try:
                        self.driver.execute_script("""
                            var botoes = document.querySelectorAll('button');
                            var botaoBusca = null;
                            
                            for (var i = 0; i < botoes.length; i++) {
                                var texto = botoes[i].textContent.toLowerCase();
                                if (texto.includes('buscar') || texto.includes('pesquisar') || texto.includes('consultar') || 
                                    botoes[i].classList.contains('btn-primary') || botoes[i].type === 'submit') {
                                    botoes[i].click();
                                    return true;
                                }
                            }
                            return false;
                        """)
                    except:
                        pass
            except Exception as btn_error:
                self.add_diagnostic("select_municipality", True, f"Aviso ao clicar no botão de busca: {str(btn_error)}")
                # Continua mesmo com erro, pois algumas implementações não precisam clicar em botão
            
            return True
                
        except Exception as e:
            self.add_diagnostic("select_municipality", False, f"Erro: {str(e)}")
            return False

    def _update_status(self, message, progress=None):
        """
        Atualiza o status da automação e envia para o callback, se disponível
        
        Args:
            message (str): Mensagem de status
            progress (int): Progresso (0-100)
        """
        if progress is not None:
            self.progresso = progress
        
        # Registrar no log
        self.log.info(f"Status: {message} ({self.progresso}%)")
        
        # Adiciona ao diagnóstico
        self.add_diagnostic("status_update", True, {
            "message": message,
            "progress": self.progresso
        })
        
        # Se temos uma função de callback, envia o status para ela
        if self.log_callback:
            try:
                self.log_callback({
                    "type": "status",
                    "message": message,
                    "progress": self.progresso,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                self.log.error(f"Erro ao enviar status via callback: {str(e)}")

    def _mapear_estado_para_sigla(self, estado):
        """
        Mapeia o nome do estado para sua sigla de duas letras
        
        Args:
            estado (str): Nome do estado
            
        Returns:
            str: Sigla do estado (UF)
        """
        # Normalizar o nome do estado (remover acentos e caixa alta)
        estado_norm = unidecode(estado.upper())
        
        mapa_estados = {
            'ACRE': 'AC',
            'ALAGOAS': 'AL',
            'AMAPA': 'AP',
            'AMAZONAS': 'AM',
            'BAHIA': 'BA',
            'CEARA': 'CE',
            'DISTRITO FEDERAL': 'DF',
            'ESPIRITO SANTO': 'ES',
            'GOIAS': 'GO',
            'MARANHAO': 'MA',
            'MATO GROSSO': 'MT',
            'MATO GROSSO DO SUL': 'MS',
            'MINAS GERAIS': 'MG',
            'PARA': 'PA',
            'PARAIBA': 'PB',
            'PARANA': 'PR',
            'PERNAMBUCO': 'PE',
            'PIAUI': 'PI',
            'RIO DE JANEIRO': 'RJ',
            'RIO GRANDE DO NORTE': 'RN',
            'RIO GRANDE DO SUL': 'RS',
            'RONDONIA': 'RO',
            'RORAIMA': 'RR',
            'SANTA CATARINA': 'SC',
            'SAO PAULO': 'SP',
            'SERGIPE': 'SE',
            'TOCANTINS': 'TO'
        }
        
        # Procurar pelo estado no mapa
        for nome, sigla in mapa_estados.items():
            if estado_norm == nome or estado_norm == sigla:
                return sigla
            elif estado_norm in nome:
                return sigla
        
        # Fallback para o valor original se não encontrou correspondência
        if len(estado_norm) == 2:
            return estado_norm  # Já é uma sigla UF
        
        self.log.warning(f"Não foi possível mapear o estado '{estado}' para uma sigla UF")
        return estado_norm[:2]  # Retorna as duas primeiras letras como última tentativa

    def _verificar_mudanca_visual(self):
        """
        Verifica se houve alguma mudança visual na página que indique interação bem-sucedida
        
        Returns:
            bool: True se houve mudança visual, False caso contrário
        """
        try:
            # Capturar elementos destacados
            elementos_destacados = self.driver.execute_script("""
                var destacados = [];
                
                // Verificar elementos com estilos que indiquem seleção
                document.querySelectorAll('*').forEach(function(el) {
                    var computedStyle = window.getComputedStyle(el);
                    
                    // Verificar propriedades que indicam destaque
                    if ((computedStyle.backgroundColor && 
                         computedStyle.backgroundColor !== 'rgba(0, 0, 0, 0)' && 
                         computedStyle.backgroundColor !== 'rgb(255, 255, 255)') ||
                        (computedStyle.borderColor && 
                         computedStyle.borderWidth && 
                         parseInt(computedStyle.borderWidth) >= 2)) {
                        
                        destacados.push({
                            tag: el.tagName,
                            text: el.innerText ? el.innerText.substring(0, 50) : '',
                            id: el.id,
                            class: el.className
                        });
                    }
                });
                
                return {
                    encontrados: destacados.length > 0,
                    quantidade: destacados.length,
                    elementos: destacados.slice(0, 5)  // Retornar apenas os 5 primeiros para não sobrecarregar
                };
            """)
            
            if elementos_destacados.get('encontrados', False):
                self.log.info(f"Encontrados {elementos_destacados.get('quantidade')} elementos destacados")
                self.log.info(f"Primeiros elementos: {elementos_destacados.get('elementos')}")
                return True
                
            # Verificar se surgiram novos elementos na página
            novos_elementos = self.driver.execute_script("""
                var conteudo = document.body.innerHTML;
                
                // Verificar palavras-chave que indicariam a próxima etapa
                var palavrasChave = ['município', 'municipio', 'Selecione o município', 'propriedade', 'imóvel'];
                
                var encontradas = palavrasChave.filter(function(palavra) {
                    return conteudo.includes(palavra);
                });
                
                return {
                    encontrados: encontradas.length > 0,
                    palavras: encontradas
                };
            """)
            
            if novos_elementos.get('encontrados', False):
                self.log.info(f"Encontradas palavras-chave que indicam próxima etapa: {novos_elementos.get('palavras')}")
                return True
                
            return False
        except Exception as e:
            self.log.warning(f"Erro ao verificar mudança visual: {str(e)}")
            return False

# Exemplo de uso se executado diretamente
if __name__ == "__main__":
    # Coordenadas de exemplo para teste
    lat, lon = -23.276064, -53.266292
    
    print(f"Testando com coordenadas: {lat}, {lon}")
    
    # Configura logging
    logging.basicConfig(level=logging.INFO)
    
    # Inicializa o robô
    base_dir = os.path.dirname(os.path.abspath(__file__))
    robot = SICARRobot(base_dir=base_dir, headless=False, embed_browser=True)
    
    # Executa o teste
    try:
        if robot._setup_webdriver():
            print("Navegador iniciado com sucesso")
            
            # Acessa o portal do SICAR
            if robot.acessar_sicar():
                print("Portal SICAR acessado com sucesso")
                
                # Identifica o estado
                estado = robot.identificar_estado(lat, lon)
                if estado:
                    print(f"Estado identificado: {estado}")
                    
                    # Seleciona o estado
                    if robot.selecionar_estado(estado):
                        print(f"Estado selecionado: {estado}")
                        
                        # Identifica o município
                        municipio = robot.identificar_municipio(lat, lon)
                        if municipio:
                            print(f"Município identificado: {municipio}")
                            
                            # Seleciona o município
                            if robot.selecionar_municipio(municipio):
                                print(f"Município selecionado: {municipio}")
                                
                                # Busca propriedade
                                propriedade = robot.buscar_propriedade(lat, lon)
                                if propriedade:
                                    print(f"Propriedade encontrada: {propriedade}")
                                    
                                    # Extrai mapa
                                    mapa = robot.extrair_mapa(propriedade)
                                    if mapa:
                                        print(f"Mapa salvo em: {mapa}")
                                    else:
                                        print("Erro ao extrair mapa")
                                else:
                                    print("Propriedade não encontrada")
                            else:
                                print("Erro ao selecionar município")
                        else:
                            print("Município não identificado")
                    else:
                        print("Erro ao selecionar estado")
                else:
                    print("Estado não identificado")
            else:
                print("Erro ao acessar portal SICAR")
    finally:
        # Fecha o navegador
        if robot and robot.driver:
            robot.driver.quit()
            print("Navegador fechado")
