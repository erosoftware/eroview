#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import threading
import webbrowser
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import json
import tempfile
from datetime import datetime

# Importar o conector SICAR
from sicar_connector import SICARConnector

class EroViewSICARApp:
    """
    Aplicativo para buscar e visualizar propriedades rurais do SICAR
    usando coordenadas geográficas.
    """
    
    def __init__(self, root):
        """
        Inicializa a interface do aplicativo.
        
        Args:
            root: Janela principal do Tkinter
        """
        self.root = root
        self.root.title("Ɜrθ View - Integração SICAR")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Definir ícone do aplicativo (será implementado posteriormente)
        # self.root.iconbitmap("path/to/icon.ico")
        
        # Inicializar o conector SICAR
        self.data_dir = os.path.join(Path.home(), ".eroview-sicar")
        os.makedirs(self.data_dir, exist_ok=True)
        self.sicar = SICARConnector(debug=True, cache_dir=os.path.join(self.data_dir, "cache"))
        
        # Variáveis de estado
        self.current_property = None
        self.map_image_path = None
        self.shapefile_path = None
        
        # Criar a interface
        self.create_widgets()
        
        # Preencher valores de teste
        self.coordinates_entry.insert(0, "-23.276064, -53.266292")  # Coordenadas de teste (Douradina, PR)
        
        # Verificar conexão com SICAR
        self.check_sicar_connection()
    
    def create_widgets(self):
        """Cria todos os widgets da interface"""
        # Frame principal com 2 colunas
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Coluna da esquerda - Entrada de dados e controles
        left_frame = ttk.LabelFrame(main_frame, text="Consulta ao SICAR", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # Entrada de coordenadas
        ttk.Label(left_frame, text="Coordenadas:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        coords_frame = ttk.Frame(left_frame)
        coords_frame.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5)
        
        self.coordinates_entry = ttk.Entry(coords_frame, width=30)
        self.coordinates_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(coords_frame, text="?", width=2, 
                  command=self.show_coordinate_help).pack(side=tk.LEFT, padx=2)
        
        # Botões de busca
        buttons_frame = ttk.Frame(left_frame)
        buttons_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(buttons_frame, text="Buscar Propriedade", 
                  command=self.search_property).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(buttons_frame, text="Limpar", 
                  command=self.clear_results).pack(side=tk.LEFT, padx=5)
        
        # Frame para resultados detalhados
        results_frame = ttk.LabelFrame(left_frame, text="Informações da Propriedade", padding=10)
        results_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, pady=10)
        
        # Informações da propriedade
        info_grid = ttk.Frame(results_frame)
        info_grid.pack(fill=tk.X, expand=True)
        
        # Estado
        ttk.Label(info_grid, text="Estado:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.state_var = tk.StringVar()
        ttk.Label(info_grid, textvariable=self.state_var).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        # Município
        ttk.Label(info_grid, text="Município:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.municipality_var = tk.StringVar()
        ttk.Label(info_grid, textvariable=self.municipality_var).grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Nome da propriedade
        ttk.Label(info_grid, text="Propriedade:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.property_name_var = tk.StringVar()
        ttk.Label(info_grid, textvariable=self.property_name_var).grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Código CAR
        ttk.Label(info_grid, text="Código CAR:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.car_code_var = tk.StringVar()
        ttk.Label(info_grid, textvariable=self.car_code_var).grid(row=3, column=1, sticky=tk.W, pady=2)
        
        # Área
        ttk.Label(info_grid, text="Área (ha):").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.area_var = tk.StringVar()
        ttk.Label(info_grid, textvariable=self.area_var).grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # Botões de ação para propriedades
        action_frame = ttk.Frame(results_frame)
        action_frame.pack(fill=tk.X, expand=True, pady=10)
        
        self.download_map_btn = ttk.Button(action_frame, text="Baixar Mapa", 
                                         command=self.download_map, state=tk.DISABLED)
        self.download_map_btn.pack(side=tk.LEFT, padx=5)
        
        self.download_shape_btn = ttk.Button(action_frame, text="Baixar Shapefile", 
                                           command=self.download_shapefile, state=tk.DISABLED)
        self.download_shape_btn.pack(side=tk.LEFT, padx=5)
        
        # Status da conexão SICAR
        status_frame = ttk.Frame(left_frame)
        status_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(status_frame, text="Status SICAR:").pack(side=tk.LEFT, padx=(0, 5))
        self.status_var = tk.StringVar(value="Verificando...")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                    foreground="orange")
        self.status_label.pack(side=tk.LEFT)
        
        ttk.Button(status_frame, text="Verificar", width=8, 
                  command=self.check_sicar_connection).pack(side=tk.RIGHT)
        
        # Log de eventos
        log_frame = ttk.LabelFrame(left_frame, text="Log de Eventos", padding=5)
        log_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, pady=10)
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_text = ScrolledText(log_frame, height=6, width=40, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        
        # Coluna da direita - Visualização de mapas
        right_frame = ttk.LabelFrame(main_frame, text="Visualização de Mapa", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Frame para o mapa
        self.map_frame = ttk.Frame(right_frame)
        self.map_frame.pack(fill=tk.BOTH, expand=True)
        
        # Inicializa a figura de matplotlib
        self.init_map()
        
        # Ajustes de layout
        left_frame.configure(width=350)
        right_frame.configure(width=550)
    
    def init_map(self):
        """Inicializa o mapa vazio"""
        self.fig, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        self.ax.set_facecolor('#F0F0F0')
        self.ax.set_title("Mapa da Propriedade")
        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # Criar mensagem de instrução no centro
        self.ax.text(0.5, 0.5, "Busque uma propriedade\npara visualizar o mapa",
                   horizontalalignment='center',
                   verticalalignment='center',
                   transform=self.ax.transAxes,
                   fontsize=12)
        
        # Adicionar a figura ao frame
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.map_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def update_map(self, simulate=True):
        """
        Atualiza o mapa com a propriedade atual
        
        Args:
            simulate (bool): Se True, simula o mapa quando não há dados reais
        """
        if not self.current_property:
            return
        
        # Limpar o mapa atual
        self.ax.clear()
        self.ax.set_facecolor('#F0F0F0')
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        lat, lng = self.current_property['coordinates']
        property_name = self.current_property['property_name']
        
        # Título com nome da propriedade
        self.ax.set_title(f"{property_name}")
        
        # Em uma implementação real, aqui seria carregado o shapefile ou imagem do mapa
        # Para demonstração, vamos simular um polígono em torno das coordenadas
        
        if simulate:
            # Simular um polígono da propriedade (retângulo irregular)
            # Offset aleatório mas consistente para a mesma propriedade
            offset_factor = abs(hash(self.current_property['car_code'])) % 100 / 5000.0
            
            # Cria um polígono em formato de propriedade rural
            points = [
                (lng - 0.003 - offset_factor, lat - 0.002 - offset_factor*0.8),
                (lng + 0.004 + offset_factor*1.2, lat - 0.001 - offset_factor*0.5),
                (lng + 0.005 + offset_factor*0.8, lat + 0.003 + offset_factor*1.1),
                (lng - 0.002 - offset_factor*0.7, lat + 0.002 + offset_factor),
            ]
            
            # Criar o polígono com contorno amarelo
            polygon = patches.Polygon(points, closed=True, 
                                     edgecolor='gold', facecolor='none', 
                                     linewidth=2, alpha=0.8)
            self.ax.add_patch(polygon)
            
            # Adicionar um marcador para o ponto exato
            self.ax.plot(lng, lat, 'ro', markersize=8)
            
            # Ajustar os limites do mapa para mostrar a propriedade
            min_x = min(p[0] for p in points) - 0.001
            max_x = max(p[0] for p in points) + 0.001
            min_y = min(p[1] for p in points) - 0.001
            max_y = max(p[1] for p in points) + 0.001
            
            self.ax.set_xlim(min_x, max_x)
            self.ax.set_ylim(min_y, max_y)
        else:
            # Se não estivermos simulando, mostrar apenas o ponto
            self.ax.plot(lng, lat, 'ro', markersize=8)
            self.ax.set_xlim(lng - 0.01, lng + 0.01)
            self.ax.set_ylim(lat - 0.01, lat + 0.01)
        
        # Adicionar texto com coordenadas
        self.ax.text(0.02, 0.02, f"Lat: {lat}, Lng: {lng}",
                   transform=self.ax.transAxes,
                   fontsize=8, verticalalignment='bottom',
                   bbox=dict(facecolor='white', alpha=0.6))
        
        # Adicionar informação sobre simulação se necessário
        if 'simulated' in self.current_property and self.current_property['simulated']:
            self.ax.text(0.5, 0.02, "SIMULAÇÃO - Dados não reais",
                       transform=self.ax.transAxes,
                       fontsize=10, color='red', 
                       horizontalalignment='center',
                       bbox=dict(facecolor='white', alpha=0.7))
        
        # Atualizar o canvas
        self.canvas.draw()
        
    def log(self, message):
        """
        Adiciona uma mensagem ao log com timestamp
        
        Args:
            message (str): Mensagem a ser adicionada
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Rolar para mostrar a última entrada
    
    def check_sicar_connection(self):
        """Verifica a conexão com o SICAR"""
        self.status_var.set("Verificando...")
        self.status_label.configure(foreground="orange")
        self.root.update_idletasks()
        
        def check():
            try:
                connected = self.sicar.test_connection()
                if connected:
                    self.status_var.set("Conectado")
                    self.status_label.configure(foreground="green")
                    self.log("Conexão com SICAR estabelecida")
                else:
                    self.status_var.set("Desconectado")
                    self.status_label.configure(foreground="red")
                    self.log("Não foi possível conectar ao SICAR. Usando modo offline.")
            except Exception as e:
                self.status_var.set("Erro")
                self.status_label.configure(foreground="red")
                self.log(f"Erro ao verificar conexão: {str(e)}")
        
        # Executar em uma thread para não travar a interface
        threading.Thread(target=check, daemon=True).start()
    
    def search_property(self):
        """Busca propriedade com base nas coordenadas fornecidas"""
        coordinates = self.coordinates_entry.get().strip()
        if not coordinates:
            messagebox.showwarning("Dados Incompletos", "Por favor, informe as coordenadas")
            return
        
        self.log(f"Buscando propriedade com coordenadas: {coordinates}")
        
        # Desabilitar a interface durante a busca
        self.root.config(cursor="wait")
        self.coordinates_entry.config(state=tk.DISABLED)
        self.root.update_idletasks()
        
        def search_task():
            try:
                property_info = self.sicar.search_property(coordinates)
                
                if property_info and property_info.get('found'):
                    self.current_property = property_info
                    
                    # Atualizar interface com os resultados
                    self.state_var.set(property_info.get('state_name', ''))
                    self.municipality_var.set(property_info.get('municipality', ''))
                    self.property_name_var.set(property_info.get('property_name', ''))
                    self.car_code_var.set(property_info.get('car_code', ''))
                    self.area_var.set(str(property_info.get('area', '')) + " ha")
                    
                    # Habilitar botões de download
                    self.download_map_btn.config(state=tk.NORMAL)
                    self.download_shape_btn.config(state=tk.NORMAL)
                    
                    # Atualizar o mapa
                    self.update_map(simulate=True)
                    
                    self.log(f"Propriedade encontrada: {property_info['property_name']}")
                else:
                    messagebox.showinfo("Sem Resultados", 
                                      "Nenhuma propriedade encontrada nas coordenadas informadas")
                    self.log("Nenhuma propriedade encontrada")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao buscar propriedade: {str(e)}")
                self.log(f"Erro: {str(e)}")
            finally:
                # Restaurar a interface
                self.root.config(cursor="")
                self.coordinates_entry.config(state=tk.NORMAL)
        
        # Executar em uma thread para não travar a interface
        threading.Thread(target=search_task, daemon=True).start()
    
    def download_map(self):
        """Download do mapa da propriedade atual"""
        if not self.current_property:
            return
        
        try:
            self.log(f"Baixando mapa para {self.current_property['car_code']}")
            
            # Iniciar download em thread separada
            def download_task():
                try:
                    map_path = self.sicar.download_property_map(self.current_property)
                    self.map_image_path = map_path
                    
                    # Perguntar ao usuário onde salvar
                    target_path = filedialog.asksaveasfilename(
                        defaultextension=".png",
                        filetypes=[("Imagem PNG", "*.png"), ("Todos os arquivos", "*.*")],
                        initialdir=os.path.expanduser("~"),
                        initialfile=f"mapa_{self.current_property['car_code'].replace('-', '_')}.png",
                        title="Salvar Mapa Como"
                    )
                    
                    if target_path:
                        # Copiar o arquivo para o destino selecionado
                        # (Na implementação real seria realmente uma imagem)
                        with open(map_path, 'r') as src, open(target_path, 'w') as dst:
                            dst.write(src.read())
                        
                        self.log(f"Mapa salvo em: {target_path}")
                        
                        # Perguntar se deseja abrir o arquivo
                        if messagebox.askyesno("Download Concluído", 
                                             "Mapa salvo com sucesso. Deseja abrir o arquivo?"):
                            webbrowser.open(target_path)
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao baixar mapa: {str(e)}")
                    self.log(f"Erro ao baixar mapa: {str(e)}")
            
            threading.Thread(target=download_task, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar download: {str(e)}")
            self.log(f"Erro: {str(e)}")
    
    def download_shapefile(self):
        """Download do shapefile da propriedade atual"""
        if not self.current_property:
            return
        
        try:
            self.log(f"Baixando shapefile para {self.current_property['car_code']}")
            
            # Iniciar download em thread separada
            def download_task():
                try:
                    shapefile_dir = self.sicar.download_shapefile(self.current_property)
                    self.shapefile_path = shapefile_dir
                    
                    # Perguntar ao usuário onde salvar
                    target_dir = filedialog.askdirectory(
                        initialdir=os.path.expanduser("~"),
                        title="Selecionar Pasta para Salvar Shapefile"
                    )
                    
                    if target_dir:
                        # Nome do diretório baseado no código CAR
                        dir_name = f"shape_{self.current_property['car_code'].replace('-', '_')}"
                        target_path = os.path.join(target_dir, dir_name)
                        
                        # Criar diretório de destino
                        os.makedirs(target_path, exist_ok=True)
                        
                        # Copiar os arquivos para o destino selecionado
                        for file in os.listdir(shapefile_dir):
                            src_file = os.path.join(shapefile_dir, file)
                            dst_file = os.path.join(target_path, file)
                            
                            with open(src_file, 'r') as src, open(dst_file, 'w') as dst:
                                dst.write(src.read())
                        
                        self.log(f"Shapefile salvo em: {target_path}")
                        
                        # Perguntar se deseja abrir o diretório
                        if messagebox.askyesno("Download Concluído", 
                                             "Shapefile salvo com sucesso. Deseja abrir a pasta?"):
                            # Abrir o diretório no explorador de arquivos
                            os.startfile(target_path)
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao baixar shapefile: {str(e)}")
                    self.log(f"Erro ao baixar shapefile: {str(e)}")
            
            threading.Thread(target=download_task, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao iniciar download: {str(e)}")
            self.log(f"Erro: {str(e)}")
    
    def clear_results(self):
        """Limpa os resultados e formulários"""
        # Limpar os campos de texto
        self.coordinates_entry.delete(0, tk.END)
        
        # Limpar as variáveis
        self.state_var.set("")
        self.municipality_var.set("")
        self.property_name_var.set("")
        self.car_code_var.set("")
        self.area_var.set("")
        
        # Desabilitar botões
        self.download_map_btn.config(state=tk.DISABLED)
        self.download_shape_btn.config(state=tk.DISABLED)
        
        # Limpar propriedade atual
        self.current_property = None
        self.map_image_path = None
        self.shapefile_path = None
        
        # Reinicializar o mapa
        self.init_map()
        
        self.log("Formulário limpo")
    
    def show_coordinate_help(self):
        """Mostra ajuda sobre formatos de coordenadas aceitos"""
        help_text = """
Formatos de coordenadas aceitos:

1. Decimal direto:  -23.276064, -53.266292
2. URL do Google Maps: https://www.google.com/maps?q=-23.276064,-53.266292
3. Formato com direção: 23.276064 S, 53.266292 W

Dica: Para o teste principal, use -23.276064, -53.266292 (Douradina, PR)
        """
        messagebox.showinfo("Ajuda - Coordenadas", help_text)


def main():
    """Função principal para iniciar o aplicativo"""
    root = tk.Tk()
    app = EroViewSICARApp(root)
    
    # Centralizar a janela na tela
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'+{x}+{y}')
    
    root.mainloop()


if __name__ == "__main__":
    main()
