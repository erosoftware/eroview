#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EroMaps - Interface de Desenvolvedor do SICAR
=============================================

Este script implementa uma interface web para visualizar o processo de extração
de mapas do SICAR em tempo real, facilitando o desenvolvimento e depuração.

Autor: Cascade
Data: Maio 2023
"""

# Imports do sistema
import os
import sys
import time
import uuid
import json
import logging
import threading
import traceback
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from pathlib import Path

from flask import Flask, render_template, request, jsonify, send_from_directory, send_file, redirect, url_for
import matplotlib.pyplot as plt
from PIL import Image

# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('dev_sicar_debug.log', mode='w')
    ]
)

# Silencia logs muito verbosos
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('selenium').setLevel(logging.WARNING)

logger = logging.getLogger('dev_sicar')

# Define o diretório base
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'
MAPS_DIR = BASE_DIR / 'maps'

# Cria os diretórios necessários
STATIC_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
MAPS_DIR.mkdir(exist_ok=True)

# Adiciona o diretório base ao caminho de importação
sys.path.append(os.path.abspath('.'))

# Importa a classe SICAR Robot
from utils.sicar_robot import SICARRobot

# Configuração da aplicação Flask
app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR)
)

# Inicialização da aplicação e estado
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Configuração de logs
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dev_sicar')

# Estado global da aplicação
app_state = {
    'status': 'idle',
    'message': 'Pronto para iniciar',
    'started_at': None,
    'finished_at': None,
    'progress': 0,
    'robot': None,
    'result': None,
    'error': None,
    'logs': [],
    'steps': [],
    # Importante: Flag para evitar buscas automáticas não solicitadas
    'auto_search_disabled': True
}

# Cria objeto para os logs do navegador
app.browser_logs = []

# Configurações
def get_config():
    """Retorna as configurações da aplicação."""
    return {
        'dev_mode': os.environ.get('SICAR_DEV_MODE', 'true').lower() == 'true',
        'force_visual': os.environ.get('SICAR_FORCE_VISUAL', 'false').lower() == 'true',
        'force_headless': os.environ.get('SICAR_FORCE_HEADLESS', 'false').lower() == 'true',
    }

# Modos de operação
DEV_MODE = "developer"
USER_MODE = "user"

# Rotas da aplicação
@app.route('/')
def index():
    # Configuração do ambiente - valores padrão
    dev_mode = os.environ.get('SICAR_DEV_MODE', 'True').lower() in ('true', '1', 't')
    force_visual = os.environ.get('SICAR_FORCE_VISUAL', 'False').lower() in ('true', '1', 't')
    force_headless = os.environ.get('SICAR_FORCE_HEADLESS', 'False').lower() in ('true', '1', 't')
    
    # Define o modelo de visualização
    headless = force_headless or (not dev_mode and not force_visual)
    
    # Coordenadas padrão para testes no modo desenvolvedor
    # Estas são apenas coordenadas de teste e não têm tratamento especial
    default_lat = "-23.276064"
    default_lon = "-53.266292"
    
    # Define o modo de operação
    operation_mode = DEV_MODE if dev_mode else USER_MODE
    
    # IMPORTANTE: Resetar o estado da aplicação para garantir que não existam buscas anteriores ativas
    reset_state()
    
    # Desativar a busca automática
    app_state['status'] = 'idle'
    app_state['message'] = 'Pronto para iniciar'
    app_state['auto_search_disabled'] = True
    
    return render_template('dev_sicar.html', 
                          headless=headless, 
                          default_lat=default_lat,
                          default_lon=default_lon,
                          operation_mode=operation_mode)

@app.route('/sicar_view')
def sicar_view():
    """Exibe a página de consulta em um iframe."""
    return render_template(
        'sicar_iframe.html',
        sicar_url="https://consultapublica.car.gov.br/publico/imoveis/index"
    )

@app.route('/config', methods=['GET'])
def get_current_config():
    """Retorna as configurações atuais."""
    return jsonify(get_config())

@app.route('/status', methods=['GET'])
def get_status():
    """
    Retorna o status atual do processo
    """
    global app_state
    
    # Formata o progresso para o frontend
    progress = 0
    if app_state['steps']:
        total_steps = len(app_state['steps'])
        completed_steps = sum(1 for step in app_state['steps'] if step['status'] in ['success', 'error'])
        running_steps = sum(1 for step in app_state['steps'] if step['status'] == 'running')
        
        if total_steps > 0:
            # Conta etapas completas como 100%, em andamento como 50%
            progress = int((completed_steps * 100 + running_steps * 50) / total_steps)
    
    return jsonify({
        'status': app_state['status'],
        'message': app_state['message'],
        'progress': progress,
        'logs': app_state['logs'],
        'steps': app_state['steps'],
        'result': app_state['result'],
        'error': app_state['error'],
        'started_at': app_state['started_at'],
        'finished_at': app_state['finished_at']
    })

@app.route('/iniciar', methods=['POST'])
def iniciar_busca():
    """
    Inicia uma busca no SICAR com base em coordenadas
    
    Returns:
        dict: Status da operação
    """
    # Log de entrada na função
    logger.debug("Recebida requisição em /iniciar")
    logger.debug(f"Método: {request.method}")
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Dados brutos: {request.data}")
    
    try:
        # Verifica e registra detalhes da requisição
        if request.is_json:
            logger.debug(f"JSON Content-Type detectado: {request.content_type}")
            try:
                data = request.get_json(force=True)
                logger.debug(f"Dados JSON recebidos: {data}")
            except Exception as json_error:
                logger.error(f"Erro ao processar JSON: {str(json_error)}")
                logger.error(traceback.format_exc())
                return jsonify({
                    'status': 'error',
                    'message': f'Erro no formato JSON: {str(json_error)}'
                }), 400
        else:
            logger.debug(f"Content-Type não é JSON: {request.content_type}")
            logger.debug(f"Form data: {request.form}")
            data = request.form
        
        # Tenta extrair coordenadas de diferentes fontes
        lat = None
        lon = None
        
        sources = ['data.get("lat")', 'data.get("latitude")', 
                  'request.args.get("lat")', 'request.args.get("latitude")',
                  'request.form.get("lat")', 'request.form.get("latitude")']
        
        for source in sources:
            try:
                lat_val = eval(source)
                if lat_val:
                    lat = lat_val
                    logger.debug(f"Latitude obtida de {source}: {lat}")
                    break
            except Exception as e:
                logger.debug(f"Erro ao obter latitude de {source}: {str(e)}")
        
        sources = ['data.get("lon")', 'data.get("longitude")', 
                  'request.args.get("lon")', 'request.args.get("longitude")',
                  'request.form.get("lon")', 'request.form.get("longitude")']
        
        for source in sources:
            try:
                lon_val = eval(source)
                if lon_val:
                    lon = lon_val
                    logger.debug(f"Longitude obtida de {source}: {lon}")
                    break
            except Exception as e:
                logger.debug(f"Erro ao obter longitude de {source}: {str(e)}")
        
        # Se ainda não temos coordenadas, extrai do corpo JSON ou data
        if not lat or not lon:
            try:
                if isinstance(data, dict):
                    lat = data.get('lat')
                    lon = data.get('lon')
                    logger.debug(f"Tentativa final: lat={lat}, lon={lon} do dicionário de dados")
            except Exception as e:
                logger.error(f"Erro ao extrair coordenadas do dicionário: {str(e)}")
        
        if not lat or not lon:
            logger.error("Coordenadas não fornecidas em nenhuma fonte disponível")
            logger.error(f"Dados disponíveis: form={request.form}, args={request.args}, json={request.get_json(silent=True)}")
            return jsonify({
                'status': 'error',
                'message': 'Coordenadas não fornecidas'
            }), 400
        
        # Tenta converter para float
        try:
            lat = float(lat)
            lon = float(lon)
            logger.info(f"Coordenadas convertidas para float: lat={lat}, lon={lon}")
        except (ValueError, TypeError) as e:
            logger.error(f"Erro ao converter coordenadas para float: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': f'Coordenadas inválidas, devem ser numéricas: {str(e)}'
            }), 400
        
        # Reset do estado da aplicação
        reset_state()
        
        # Inicia thread de busca
        logger.info(f"Iniciando thread de busca para lat={lat}, lon={lon}")
        thread = threading.Thread(target=buscar_sicar, args=(lat, lon))
        thread.daemon = True
        thread.start()
        logger.debug("Thread de busca iniciada")
        
        # Registra o início da busca
        app_state['status'] = 'running'
        app_state['started_at'] = datetime.now().isoformat()
        app_state['steps'] = [
            {'id': 'init', 'name': 'Inicialização', 'status': 'success'},
            {'id': 'browser', 'name': 'Inicializar navegador', 'status': 'running'},
            {'id': 'access_site', 'name': 'Acessar site', 'status': 'pending'},
            {'id': 'select_state', 'name': 'Selecionar estado', 'status': 'pending'},
            {'id': 'select_city', 'name': 'Selecionar município', 'status': 'pending'},
            {'id': 'select_property', 'name': 'Selecionar propriedade', 'status': 'pending'},
            {'id': 'extract', 'name': 'Extrair informações', 'status': 'pending'},
            {'id': 'finish', 'name': 'Finalização', 'status': 'pending'}
        ]
        
        # Adiciona logs iniciais
        add_log(f"Iniciando busca para coordenadas {lat}, {lon}", "info")
        add_log(f"Thread ID: {thread.ident}", "debug")
        
        # Responde ao cliente
        logger.info("Enviando resposta de sucesso para o cliente")
        return jsonify({
            'status': 'success',
            'message': f'Busca iniciada para coordenadas {lat}, {lon}',
            'progress': 5
        })
        
    except Exception as e:
        # Captura qualquer exceção e registra detalhes
        logger.error(f"Erro não tratado em iniciar_busca: {str(e)}")
        logger.error(traceback.format_exc())
        add_log(f"Erro ao iniciar busca: {str(e)}", "error")
        
        return jsonify({
            'status': 'error',
            'message': f'Erro interno: {str(e)}',
            'traceback': traceback.format_exc()
        }), 500

@app.route('/cancelar', methods=['POST'])
def cancelar_busca():
    """Cancela a busca em andamento."""
    global app_state
    
    # Verifica se há um processo em execução
    if app_state['status'] != 'running':
        return jsonify({
            'success': False,
            'message': 'Não há processo em execução para cancelar'
        }), 400
    
    # Cancela o processo
    if app_state['robot']:
        try:
            app_state['robot'].close()
        except Exception as e:
            logger.error(f"Erro ao fechar o robô: {e}")
    
    # Atualiza o estado
    app_state['status'] = 'idle'
    app_state['message'] = 'Processo cancelado pelo usuário'
    app_state['progress'] = 0
    for step in app_state['steps']:
        if step['status'] == 'running':
            step['status'] = 'canceled'
    app_state['finished_at'] = datetime.now().isoformat()
    
    add_log('Busca cancelada pelo usuário', 'warning')
    
    return jsonify({
        'success': True,
        'message': 'Busca cancelada com sucesso'
    })

@app.route('/maps/<filename>')
def serve_map(filename):
    """Serve os mapas gerados."""
    return send_from_directory(str(MAPS_DIR), filename)

@app.route('/resultado', methods=['GET'])
def get_resultado():
    """Retorna o resultado do último processo."""
    global app_state
    
    if app_state['result'] is None:
        return jsonify({
            'success': False,
            'message': 'Nenhum resultado disponível'
        }), 404
    
    return jsonify({
        'success': True,
        'result': app_state['result']
    })

@app.route('/log_callback', methods=['POST'])
def log_callback():
    """Endpoint para receber logs do robô Selenium."""
    data = request.json
    if data and 'message' in data and 'level' in data:
        add_log(data['level'], data['message'])
        
        # Se tiver informação de etapa, atualiza o progresso
        if 'step' in data:
            update_progress(data['step'], 'running', data['message'])
    
    return jsonify({'success': True})

@app.route('/update_step', methods=['POST'])
def update_step():
    """Endpoint para atualizar o status de uma etapa."""
    data = request.json
    if data and 'step' in data and 'status' in data:
        update_progress(data['step'], data['status'], data.get('message', ''))
    
    return jsonify({'success': True})

@app.route('/sicar-iframe')
def sicar_iframe():
    """
    Exibe a página do SICAR em um iframe com visualização do código
    """
    return render_template('sicar_iframe.html', sicar_url="https://consultapublica.car.gov.br/publico/imoveis/index")

@app.route('/show_map/<car_code>')
def show_map(car_code):
    """
    Exibe o mapa de uma propriedade específica
    """
    # Verifica se temos resultado
    if not app_state.get('result'):
        return "Nenhum resultado disponível", 404
        
    # Obtem o mapa_path do resultado
    map_path = app_state['result'].get('map_path')
    
    if not map_path or map_path == "None":
        # Gera um mapa simulado se não tiver um real
        return render_template(
            'property_map.html', 
            car_code=car_code,
            coordinates=app_state['result'].get('coordinates', '-23.276064, -53.266292'),
            name=app_state['result'].get('name', 'Fazenda Simulada'),
            area=app_state['result'].get('area', '245.32 ha'),
            municipality=app_state['result'].get('municipality', 'Douradina'),
            state=app_state['result'].get('state', 'PR'),
            simulated=True
        )
    
    # Retorna o arquivo de mapa
    if os.path.exists(map_path):
        return send_file(map_path)
    
    # Se não encontrou o arquivo, retorna o simulado
    return render_template(
        'property_map.html', 
        car_code=car_code,
        coordinates=app_state['result'].get('coordinates', '-23.276064, -53.266292'),
        name=app_state['result'].get('name', 'Fazenda Simulada'),
        area=app_state['result'].get('area', '245.32 ha'),
        municipality=app_state['result'].get('municipality', 'Douradina'),
        state=app_state['result'].get('state', 'PR'),
        simulated=True
    )

@app.route('/property_map')
def property_map():
    """
    Exibe o mapa de uma propriedade com base nas coordenadas ou URL do SICAR
    """
    lat = request.args.get('lat', '')
    lon = request.args.get('lon', '')
    sicar_map_url = request.args.get('sicar_map_url', '')
    
    # Se não tiver URL do SICAR e tiver coordenadas, redireciona para a busca
    if not sicar_map_url and (lat and lon):
        return redirect(f"/search?lat={lat}&lon={lon}")
        
    # Prepara os dados do modelo
    data = {
        'coordinates': f"{lat}, {lon}",
        'sicar_map_url': sicar_map_url
    }
    
    # Retorna erro se não tiver URL do mapa SICAR
    if not sicar_map_url:
        return render_template('error.html', message="URL do mapa SICAR não fornecida")
    
    return render_template('property_map.html', **data)

@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    Endpoint para iniciar a busca de propriedades
    Se GET: exibe a página de busca
    Se POST: inicia a busca com as coordenadas informadas
    """
    # Reset do estado da aplicação
    reset_state()
    
    if request.method == 'POST':
        # Adiciona log para ajudar na depuração
        app.logger.info("POST request received on /search")
        print("POST request received on /search")
        
        try:
            # Verifica o conteúdo da requisição
            print(f"Content-Type: {request.content_type}")
            print(f"Form data: {request.form}")
            print(f"JSON data: {request.get_json(silent=True)}")
            print(f"Args: {request.args}")
            
            # Modo de busca - recebe coordenadas e inicia busca
            lat = request.form.get('lat')
            lon = request.form.get('lon')
            
            if not lat or not lon:
                # Verifica se os parâmetros estão no corpo JSON
                if request.is_json:
                    data = request.get_json()
                    print(f"JSON data: {data}")
                    if data:
                        lat = data.get('lat')
                        lon = data.get('lon')
                
                # Verifica se os parâmetros estão nos argumentos da URL
                if not lat or not lon:
                    lat = request.args.get('lat')
                    lon = request.args.get('lon')
            
            # Verifica se as coordenadas foram fornecidas
            if not lat or not lon:
                print("Latitude and longitude not provided")
                return jsonify({
                    "success": False, 
                    "error": "Latitude e longitude são obrigatórios"
                }), 400
                
            try:
                lat = float(lat)
                lon = float(lon)
            except ValueError as e:
                print(f"Invalid coordinates: lat={lat}, lon={lon}, error={str(e)}")
                return jsonify({
                    "success": False,
                    "error": f"Coordenadas inválidas. Devem ser números. Erro: {str(e)}"
                }), 400
                
            # Inicia a busca em uma thread separada para não bloquear
            print(f"Starting search thread with coordinates: {lat}, {lon}")
            thread = threading.Thread(target=buscar_sicar, args=(float(lat), float(lon)))
            thread.daemon = True
            thread.start()
            
            app_state['status'] = 'running'
            app_state['message'] = f'Iniciando busca para coordenadas {lat}, {lon}'
            
            # Retorna imediatamente, enquanto a busca continua em background
            return jsonify({
                "success": True,
                "message": "Busca iniciada com sucesso"
            })
        except Exception as e:
            print(f"Error in search endpoint: {str(e)}")
            print(traceback.format_exc())
            return jsonify({
                "success": False,
                "error": f"Erro ao processar requisição: {str(e)}"
            }), 500
    else:
        # Modo de exibição - renderiza a página de busca
        return render_template('dev_sicar.html')

# Rotas para a API da busca SICAR
@app.route('/sicar/search', methods=['POST'])
def sicar_search():
    """
    Inicia uma busca no SICAR com base em coordenadas
    """
    reset_state()
    
    try:
        # Obtém as coordenadas do formulário
        lat = request.form.get('latitude')
        lon = request.form.get('longitude')
        
        if not lat or not lon:
            return jsonify({
                "success": False,
                "error": "Latitude e longitude são obrigatórios"
            }), 400
        
        # Gera um ID único para a busca
        search_id = str(uuid.uuid4())
        app_state['search_id'] = search_id
        app_state['status'] = 'running'
        app_state['message'] = 'Iniciando busca...'
        app_state['started_at'] = datetime.now().isoformat()
        
        # Inicia a busca em uma thread separada
        thread = threading.Thread(target=buscar_sicar, args=(float(lat), float(lon)))
        thread.daemon = True
        thread.start()
        
        # Retorna o ID da busca para o cliente consultar o status
        return jsonify({
            "success": True,
            "search_id": search_id,
            "message": "Busca iniciada com sucesso"
        })
    
    except Exception as e:
        app.logger.error(f"Erro ao iniciar busca: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Erro ao iniciar busca: {str(e)}"
        }), 500

@app.route('/sicar/status/<search_id>', methods=['GET'])
def sicar_status(search_id):
    """
    Retorna o status atual de uma busca
    """
    if app_state.get('search_id') != search_id:
        return jsonify({
            "success": False,
            "error": "Busca não encontrada"
        }), 404
    
    return jsonify({
        "success": True,
        "status": app_state['status'],
        "progress": app_state['progress'],
        "message": app_state['message'],
        "result": app_state.get('result'),
        "error": app_state.get('error'),
        "steps": app_state['steps']
    })

@app.route('/sicar/cancel/<search_id>', methods=['POST'])
def sicar_cancel(search_id):
    """
    Cancela uma busca em andamento
    """
    if app_state.get('search_id') != search_id:
        return jsonify({
            "success": False,
            "error": "Busca não encontrada"
        }), 404
    
    if app_state['status'] == 'running':
        app_state['status'] = 'canceled'
        app_state['message'] = 'Busca cancelada pelo usuário'
        add_log('Busca cancelada pelo usuário', 'warning')
    
    return jsonify({
        "success": True,
        "message": "Busca cancelada com sucesso"
    })

@app.route('/sicar/map/<filename>')
def sicar_map(filename):
    """
    Serve o mapa gerado pelo SICAR
    """
    return send_from_directory(os.path.join(app.root_path, 'maps'), filename)

# Rota para testar coordenadas específicas
@app.route('/teste_coordenadas', methods=['GET'])
def teste_coordenadas():
    """
    Rota para testar se conseguimos buscar coordenadas específicas
    """
    # Coordenadas de teste para Douradina, Paraná
    lat = -23.276064
    lon = -53.266292
    
    # Inicia thread de busca
    thread = threading.Thread(target=buscar_sicar, args=(lat, lon))
    thread.daemon = True
    thread.start()
    
    # Registra o início da busca
    app_state['status'] = 'running'
    app_state['message'] = 'Iniciando busca para coordenadas de teste de Douradina'
    app_state['started_at'] = datetime.now().isoformat()
    app_state['steps'] = [
        {'id': 'init', 'name': 'Inicialização', 'status': 'success'},
        {'id': 'browser', 'name': 'Inicializar navegador', 'status': 'running'},
        {'id': 'access_site', 'name': 'Acessar site', 'status': 'pending'},
        {'id': 'select_state', 'name': 'Selecionar estado', 'status': 'pending'},
        {'id': 'select_city', 'name': 'Selecionar município', 'status': 'pending'},
        {'id': 'select_property', 'name': 'Selecionar propriedade', 'status': 'pending'},
        {'id': 'extract', 'name': 'Extrair informações', 'status': 'pending'},
        {'id': 'finish', 'name': 'Finalização', 'status': 'pending'}
    ]
    
    # Retorna com redirecionamento para a página principal
    return redirect(url_for('index'))

# Funções auxiliares
def reset_state():
    """
    Reinicia o estado da aplicação para o estado inicial.
    """
    global app_state
    
    # Define as etapas do processo
    steps = [
        {'id': 'init', 'name': 'Inicialização', 'status': 'pending'},
        {'id': 'browser', 'name': 'Inicializar navegador', 'status': 'pending'},
        {'id': 'access_site', 'name': 'Acessar site', 'status': 'pending'},
        {'id': 'select_state', 'name': 'Selecionar estado', 'status': 'pending'},
        {'id': 'select_city', 'name': 'Selecionar município', 'status': 'pending'},
        {'id': 'select_property', 'name': 'Selecionar propriedade', 'status': 'pending'},
        {'id': 'extract', 'name': 'Extrair informações', 'status': 'pending'},
        {'id': 'finish', 'name': 'Finalização', 'status': 'pending'}
    ]
    
    app_state = {
        'status': 'idle',
        'message': 'Pronto para iniciar',
        'progress': 0,
        'logs': [],
        'steps': steps,
        'current_step': 'idle',
        'result': None,
        'error': None,
        'robot': None,
        'started_at': None,
        'finished_at': None,
        'auto_search_disabled': True
    }
    return app_state

def init_sicar_robot():
    """
    Inicializa e configura o robô SICAR
    
    Returns:
        SICARRobot: Instância configurada do robô
    """
    # Configuração do ambiente - valores padrão
    dev_mode = os.environ.get('SICAR_DEV_MODE', 'true').lower() in ('true', '1', 't')
    force_visual = os.environ.get('SICAR_FORCE_VISUAL', 'false').lower() in ('true', '1', 't')
    force_headless = os.environ.get('SICAR_FORCE_HEADLESS', 'false').lower() in ('true', '1', 't')
    
    # Define o modelo de visualização
    headless = force_headless or (not dev_mode and not force_visual)
    
    # Cria e configura o robô
    robot = SICARRobot(
        base_dir=str(BASE_DIR),
        browser="chrome",
        headless=headless,
        dev_mode=dev_mode
    )
    
    def log_callback(message, level):
        """Callback para receber logs do robô"""
        add_log(message, level)
    
    robot.set_log_callback(log_callback)
    
    # Inicia o navegador
    if not robot._setup_webdriver():
        error_message = "Falha ao inicializar o navegador"
        add_log(error_message, 'error')
        raise Exception(error_message)
    
    # Ajusta o tamanho da janela para garantir que todos os elementos sejam visíveis
    if not headless:
        robot.driver.set_window_size(1366, 768)
    
    return robot

def add_log(message: str, level: str = 'info', step: str = None):
    """
    Adiciona um log ao estado da aplicação
    
    Args:
        message: Mensagem a ser logada
        level: Nível de log (info, error, warning, success)
        step: Etapa do processo (opcional)
    """
    global app_state
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'level': level,
        'message': message
    }
    
    if step:
        log_entry['step'] = step
        
    app_state['logs'].append(log_entry)
    
    # Também envia para o console
    log_method = getattr(logger, level if level != 'success' else 'info')
    log_method(message)
    
    # Adiciona ao browser_log se disponível
    if hasattr(app, 'browser_logs'):
        app.browser_logs.append({
            'message': message,
            'level': level,
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'step': step
        })

def update_progress(step_id: str, status: str, message: Optional[str] = None):
    """Atualiza o progresso de uma etapa."""
    global app_state
    
    # Verifica se já existe o estado da aplicação
    if not app_state:
        app_state = {}
    
    if 'steps' not in app_state:
        app_state['steps'] = []
    
    # Atualiza o passo específico
    found = False
    for step in app_state['steps']:
        if step['id'] == step_id:
            step['status'] = status
            if message:
                step['message'] = message
            found = True
            break
    
    # Se não existir, cria o passo
    if not found and status != 'skipped':
        app_state['steps'].append({
            'id': step_id,
            'status': status,
            'message': message or ''
        })
    
    if status != 'skipped':
        app_state['current_step'] = step_id
        level = 'info' if status == 'running' else 'success' if status == 'success' else 'error'
        add_log(f"[{step_id}] {message or ''}", level, step_id)

def buscar_sicar(lat, lon):
    """
    Realiza busca de propriedade no SICAR com base em coordenadas
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
    """
    global app_state
    
    # Reinicia o estado
    reset_state()
    app_state['started_at'] = datetime.now().isoformat()
    app_state['status'] = 'running'
    
    # Adiciona log
    add_log("Inicializando robô SICAR...", "info")
    add_log(f"Iniciando busca para coordenadas {lat}, {lon}", "info")
    add_log(f"Thread ID: {threading.get_ident()}", "debug")
    
    # Atualiza status
    update_step('init', 'running')
    app_state['message'] = "Inicializando..."
    
    try:
        # Inicializa o robô SICAR
        robot = init_sicar_robot()
        app_state['robot'] = robot
        
        # Adiciona log de sucesso
        add_log("Robot Chrome inicializado com sucesso", "success")
        
        # Atualiza status
        update_step('init', 'success')
        update_step('browser', 'success')
        update_step('access_site', 'running')
        
        # Adiciona log
        add_log("Configurando navegador...", "info")
        app_state['message'] = "Configurando navegador..."
        
        # Acessa o site do SICAR
        add_log("Acessando portal do SICAR...", "info")
        app_state['message'] = "Acessando portal do SICAR..."
        
        try:
            if not robot.acessar_sicar():
                raise Exception("Falha ao acessar o portal do SICAR")
            
            # Atualiza status
            update_step('access_site', 'success')
            update_step('select_state', 'running')
            
            # Adiciona log
            add_log("Portal do SICAR acessado com sucesso", "success")
            app_state['message'] = "Buscando estado..."
            
            # Identifica o estado
            add_log("Identificando estado...", "info")
            estado = robot.identificar_estado(lat, lon)
            
            if not estado:
                raise Exception("Não foi possível identificar o estado para estas coordenadas")
            
            add_log(f"Estado identificado: {estado}", "success")
            
            # Seleciona o estado
            add_log(f"Selecionando estado: {estado}", "info")
            app_state['message'] = f"Selecionando estado: {estado}..."
            
            if not robot.selecionar_estado(estado):
                raise Exception(f"Não foi possível selecionar o estado: {estado}")
            
            # Atualiza status
            update_step('select_state', 'success')
            update_step('select_city', 'running')
            
            # Adiciona log
            add_log(f"Estado selecionado: {estado}", "success")
            app_state['message'] = "Buscando município..."
            
            # Identifica o município
            add_log("Identificando município...", "info")
            municipio = robot.identificar_municipio(lat, lon)
            
            if not municipio:
                raise Exception("Não foi possível identificar o município para estas coordenadas")
            
            add_log(f"Município identificado: {municipio}", "success")
            
            # Seleciona o município
            add_log(f"Selecionando município: {municipio}", "info")
            app_state['message'] = f"Selecionando município: {municipio}..."
            
            if not robot.selecionar_municipio(municipio):
                raise Exception(f"Não foi possível selecionar o município: {municipio}")
            
            # Atualiza status
            update_step('select_city', 'success')
            update_step('select_property', 'running')
            
            # Adiciona log
            add_log(f"Município selecionado: {municipio}", "success")
            app_state['message'] = "Buscando propriedade..."
            
            # Busca propriedade
            add_log("Buscando propriedade por coordenadas...", "info")
            propriedade = robot.buscar_propriedade(lat, lon)
            
            if not propriedade:
                raise Exception("Nenhuma propriedade encontrada para estas coordenadas")
            
            # Atualiza status
            update_step('select_property', 'success')
            update_step('extract', 'running')
            
            # Adiciona log
            add_log(f"Propriedade encontrada: {propriedade['nome']}", "success")
            app_state['message'] = f"Extraindo informações da propriedade: {propriedade['nome']}..."
            
            # Extrai informações da propriedade
            add_log("Extraindo informações e mapa da propriedade...", "info")
            mapa = robot.extrair_mapa(propriedade)
            
            if not mapa:
                raise Exception("Não foi possível extrair o mapa da propriedade")
            
            # Atualiza status
            update_step('extract', 'success')
            update_step('finish', 'running')
            
            # Adiciona log
            add_log("Mapa extraído com sucesso", "success")
            app_state['message'] = "Finalizando..."
            
            # Define o resultado
            app_state['result'] = {
                'estado': estado,
                'municipio': municipio,
                'propriedade': propriedade,
                'mapa': mapa
            }
            
            # Atualiza status
            update_step('finish', 'success')
            
            # Adiciona log
            add_log("Processo concluído com sucesso", "success")
            app_state['message'] = "Busca concluída com sucesso"
            app_state['status'] = 'success'
            
        except Exception as e:
            error_message = f"Erro na busca: {str(e)}"
            add_log(error_message, "error")
            app_state['error'] = {
                'message': str(e),
                'traceback': traceback.format_exc()
            }
            app_state['status'] = 'error'
            app_state['message'] = f"Erro: {str(e)}"
            
        finally:
            # Fecha o navegador
            try:
                if robot and robot.driver:
                    robot.driver.quit()
                    add_log("Navegador fechado", "info")
            except:
                add_log("Erro ao fechar navegador", "warning")
            
            # Marca como finalizado
            app_state['finished_at'] = datetime.now().isoformat()
            
    except Exception as e:
        app_state['status'] = 'error'
        app_state['message'] = f"Erro: {str(e)}"
        app_state['error'] = {
            'message': str(e),
            'traceback': traceback.format_exc()
        }
        add_log(f"Erro crítico: {str(e)}", "error")
        app_state['finished_at'] = datetime.now().isoformat()
    
    return app_state

def update_step(step_id, status):
    """
    Atualiza o status de uma etapa do processo
    
    Args:
        step_id: ID da etapa
        status: Novo status (pending, running, success, error)
    """
    global app_state
    
    for step in app_state['steps']:
        if step['id'] == step_id:
            step['status'] = status
            break

@app.route('/sicar/run', methods=['POST'])
def sicar_run():
    """
    Rota API para executar buscas no SICAR (sistema nacional CAR)
    """
    if not request.json:
        return jsonify({'success': False, 'msg': 'Parâmetros ausentes'})
        
    try:
        lat = float(request.json.get('lat', '0'))
        lon = float(request.json.get('lon', '0'))
        
        # Valida coordenadas
        if abs(lat) > 90 or abs(lon) > 180:
            return jsonify({'success': False, 'msg': 'Coordenadas inválidas'})
            
        if lat == 0 and lon == 0:
            return jsonify({'success': False, 'msg': 'Coordenadas zeradas'})
    except:
        return jsonify({'success': False, 'msg': 'Formato de coordenadas inválido'})
    
    # Define o modo de execução (visual ou headless)
    force_visual = os.environ.get('SICAR_FORCE_VISUAL', 'false').lower() == 'true'
    force_headless = os.environ.get('SICAR_FORCE_HEADLESS', 'false').lower() == 'true'
    
    if force_visual:
        headless = False
    elif force_headless:
        headless = True
    else:
        # Se estiver em modo de desenvolvimento, usa visual por padrão
        headless = not (os.environ.get('SICAR_DEV_MODE', 'false').lower() == 'true')
    
    # Cria o robô
    robot = SICARRobot(base_dir=os.path.dirname(os.path.abspath(__file__)), headless=headless)
    
    try:
        # Inicia o webdriver
        if not robot._setup_webdriver():
            return jsonify({
                'success': False, 
                'msg': 'Falha ao iniciar navegador', 
                'diagnostics': robot.diagnostics
            })
            
        # 1. Acessa o portal do SICAR
        success_site = robot.acessar_sicar(max_attempts=5)  # Aumentado para 5 tentativas
        if not success_site:
            robot.save_screenshot("erro_acesso_site.png")
            return jsonify({
                'success': False, 
                'msg': 'Falha ao acessar site do SICAR', 
                'diagnostics': robot.diagnostics
            })
            
        # Aguarda um pouco para garantir que a página carregou completamente
        time.sleep(3)
        
        # 2. Identifica o estado com base nas coordenadas
        estado = robot.identificar_estado(lat, lon)
        if not estado:
            robot.save_screenshot("erro_identificar_estado.png")
            return jsonify({
                'success': False, 
                'msg': 'Falha ao identificar estado das coordenadas', 
                'diagnostics': robot.diagnostics
            })
            
        # 3. Seleciona o estado
        success_estado = robot.selecionar_estado(estado)
        if not success_estado:
            robot.save_screenshot("erro_selecionar_estado.png")
            return jsonify({
                'success': False, 
                'msg': f'Falha ao selecionar estado: {estado}', 
                'diagnostics': robot.diagnostics
            })
            
        # 4. Identifica o município
        municipio = robot.identificar_municipio(lat, lon)
        if not municipio:
            robot.save_screenshot("erro_identificar_municipio.png")
            return jsonify({
                'success': False, 
                'msg': 'Falha ao identificar município das coordenadas', 
                'diagnostics': robot.diagnostics
            })
            
        # 5. Seleciona o município
        success_municipio = robot.selecionar_municipio(municipio)
        if not success_municipio:
            robot.save_screenshot("erro_selecionar_municipio.png")
            return jsonify({
                'success': False, 
                'msg': f'Falha ao selecionar município: {municipio}', 
                'diagnostics': robot.diagnostics
            })
            
        # 6. Busca propriedade
        propriedade = robot.buscar_propriedade(lat, lon)
        if not propriedade:
            robot.save_screenshot("erro_buscar_propriedade.png")
            return jsonify({
                'success': False, 
                'msg': 'Falha ao encontrar propriedade nas coordenadas especificadas', 
                'diagnostics': robot.diagnostics
            })
            
        # 7. Extrai o mapa
        mapa = robot.extrair_mapa(propriedade)
        if not mapa:
            robot.save_screenshot("erro_extrair_mapa.png")
            return jsonify({
                'success': False, 
                'msg': 'Falha ao extrair mapa da propriedade',
                'diagnostics': robot.diagnostics
            })
            
        # Resultado bem-sucedido
        resultado = {
            'success': True,
            'msg': 'Propriedade encontrada e mapa extraído com sucesso',
            'coordinates': {
                'lat': lat,
                'lon': lon
            },
            'location': {
                'estado': estado,
                'municipio': municipio
            },
            'property': propriedade,
            'map': mapa,
            'diagnostics': robot.diagnostics
        }
        
        # Fecha o navegador
        robot.close()
        
        return jsonify(resultado)
        
    except Exception as e:
        # Salva screenshot do erro
        try:
            robot.save_screenshot("erro_excecao.png")
        except:
            pass
            
        # Fecha o navegador
        try:
            robot.close()
        except:
            pass
            
        app.logger.error(f"Erro ao buscar propriedade: {str(e)}")
        return jsonify({
            'success': False, 
            'msg': f'Erro durante a execução: {str(e)}',
            'diagnostics': robot.diagnostics if robot else []
        })

@app.route('/dev_sicar/progress', methods=['GET'])
def sicar_progress():
    """
    Rota para verificar o progresso do robô
    """
    # Verifica se há um robô em execução
    if not hasattr(g, 'robot_sicar') or not g.robot_sicar:
        return jsonify({
            'success': False,
            'status': 'not_running',
            'progress': 0,
            'message': 'Robô não está em execução'
        })
        
    # Obtém diagnósticos do robô
    diagnostics = g.robot_sicar.diagnostics if hasattr(g.robot_sicar, 'diagnostics') else []
    
    # Define o estado baseado nos diagnósticos
    status = 'running'
    message = 'Em execução'
    progress = 0
    steps_completed = 0
    total_steps = 7  # Total de passos (acessar_sicar até extrair_mapa)
    
    # Verifica quais passos foram concluídos com sucesso - CORRIGIDO: nomes de keys atualizados
    if any(d['key'] == 'access_site' and d['success'] for d in diagnostics):
        steps_completed += 1
        message = 'Site do SICAR acessado'
        
    if any(d['key'] == 'identify_state' and d['success'] for d in diagnostics):
        steps_completed += 1
        message = 'Estado identificado'
        
    if any(d['key'] == 'select_state' and d['success'] for d in diagnostics):
        steps_completed += 1
        message = 'Estado selecionado'
        
    if any(d['key'] == 'identify_municipality' and d['success'] for d in diagnostics):
        steps_completed += 1
        message = 'Município identificado'
        
    if any(d['key'] == 'select_municipality' and d['success'] for d in diagnostics):
        steps_completed += 1
        message = 'Município selecionado'
        
    if any(d['key'] == 'find_property' and d['success'] for d in diagnostics):
        steps_completed += 1
        message = 'Propriedade encontrada'
        
    if any(d['key'] == 'extract_map' and d['success'] for d in diagnostics):
        steps_completed += 1
        message = 'Mapa extraído'
        status = 'completed'
        
    # Verifica se houve falha em algum passo
    for step in ['access_site', 'identify_state', 'select_state', 'identify_municipality', 
                'select_municipality', 'find_property', 'extract_map']:
        if any(d['key'] == step and not d['success'] for d in diagnostics):
            status = 'error'
            message = next((d['message'] for d in diagnostics if d['key'] == step and not d['success']), 'Erro desconhecido')
            break
            
    # Calcula o progresso em percentual
    progress = int((steps_completed / total_steps) * 100) if total_steps > 0 else 0
    
    # Se chegou ao final com sucesso
    if status == 'completed':
        progress = 100
        
    # Obtém o resultado, se disponível
    resultado = g.get('robot_sicar_result', None)
    
    return jsonify({
        'success': True,
        'status': status,
        'progress': progress,
        'message': message,
        'diagnostics': diagnostics,
        'result': resultado
    })

# Executa a aplicação
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    print(f" * EroMaps Dev SICAR iniciado em http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
