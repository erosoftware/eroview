"""
Módulo para processamento geoespacial de dados do SICAR
Realiza cálculos de área, perímetro e outras funções geoespaciais
"""
import os
import json
import math
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional

try:
    import shapefile
    from shapely.geometry import Polygon, MultiPolygon, Point, shape
    from shapely.ops import transform, unary_union
    import pyproj
    from functools import partial
except ImportError:
    print("Bibliotecas geoespaciais não encontradas. Instale-as com:")
    print("pip install pyshp shapely pyproj")

class GeoProcessor:
    """
    Classe para processamento geoespacial de dados do SICAR
    """
    def __init__(self):
        """Inicializa o processador geoespacial"""
        pass
    
    def read_shapefile(self, shp_path: Union[str, Path]) -> Dict:
        """
        Lê um shapefile e retorna os dados como um dicionário
        
        Args:
            shp_path: Caminho para o arquivo .shp
            
        Returns:
            Dict contendo informações do shapefile
        """
        try:
            shp_path = Path(shp_path)
            if not shp_path.exists():
                raise FileNotFoundError(f"Arquivo não encontrado: {shp_path}")
                
            # Lê o shapefile
            sf = shapefile.Reader(str(shp_path))
            
            # Extrai os campos
            fields = [field[0] for field in sf.fields[1:]]
            
            # Extrai os shapes e registros
            shapes = sf.shapes()
            records = sf.records()
            
            # Combina shapes e registros
            features = []
            for i, shape in enumerate(shapes):
                feature = {
                    'geometry': shape.__geo_interface__,
                    'properties': dict(zip(fields, records[i]))
                }
                features.append(feature)
            
            return {
                'type': 'FeatureCollection',
                'features': features
            }
            
        except Exception as e:
            print(f"Erro ao ler shapefile: {e}")
            return {'type': 'FeatureCollection', 'features': []}
    
    def calculate_area(self, geometry: Dict, in_hectares: bool = True) -> float:
        """
        Calcula a área de uma geometria em metros quadrados ou hectares
        
        Args:
            geometry: Geometria no formato GeoJSON
            in_hectares: Se True, retorna a área em hectares; caso contrário, em m²
            
        Returns:
            Área calculada
        """
        try:
            # Converte a geometria GeoJSON para objeto Shapely
            geom = shape(geometry)
            
            # Verifica se é uma geometria válida
            if not geom.is_valid:
                geom = geom.buffer(0)  # Tenta corrigir geometria inválida
                
            # Calcula a área usando projeção UTM apropriada para a localização
            lat, lon = self._get_centroid(geom)
            utm_zone = int(math.floor((lon + 180) / 6) + 1)
            is_northern = lat >= 0
            
            proj_string = f"+proj=utm +zone={utm_zone} {'ellps=GRS80' if is_northern else '+south'} +units=m +no_defs"
            project = partial(
                pyproj.transform,
                pyproj.Proj('+proj=longlat +datum=WGS84 +no_defs'),
                pyproj.Proj(proj_string)
            )
            
            # Transforma para projeção UTM e calcula a área
            utm_geom = transform(project, geom)
            area_m2 = utm_geom.area
            
            # Converte para hectares se necessário
            return area_m2 / 10000 if in_hectares else area_m2
            
        except Exception as e:
            print(f"Erro ao calcular área: {e}")
            return 0.0
    
    def calculate_perimeter(self, geometry: Dict) -> float:
        """
        Calcula o perímetro de uma geometria em metros
        
        Args:
            geometry: Geometria no formato GeoJSON
            
        Returns:
            Perímetro calculado em metros
        """
        try:
            # Converte a geometria GeoJSON para objeto Shapely
            geom = shape(geometry)
            
            # Calcula o perímetro usando projeção UTM apropriada
            lat, lon = self._get_centroid(geom)
            utm_zone = int(math.floor((lon + 180) / 6) + 1)
            is_northern = lat >= 0
            
            proj_string = f"+proj=utm +zone={utm_zone} {'ellps=GRS80' if is_northern else '+south'} +units=m +no_defs"
            project = partial(
                pyproj.transform,
                pyproj.Proj('+proj=longlat +datum=WGS84 +no_defs'),
                pyproj.Proj(proj_string)
            )
            
            # Transforma para projeção UTM e calcula o perímetro
            utm_geom = transform(project, geom)
            return utm_geom.length
            
        except Exception as e:
            print(f"Erro ao calcular perímetro: {e}")
            return 0.0
    
    def _get_centroid(self, geometry) -> Tuple[float, float]:
        """
        Obtém o centroide de uma geometria
        
        Args:
            geometry: Objeto geometria Shapely
            
        Returns:
            Tuple (latitude, longitude)
        """
        centroid = geometry.centroid
        return centroid.y, centroid.x
    
    def point_in_property(self, point: Tuple[float, float], geometry: Dict) -> bool:
        """
        Verifica se um ponto está dentro de uma propriedade
        
        Args:
            point: Tuple (latitude, longitude)
            geometry: Geometria da propriedade no formato GeoJSON
            
        Returns:
            True se o ponto estiver dentro da propriedade, False caso contrário
        """
        try:
            # Cria um objeto Point do Shapely
            lat, lon = point
            point_obj = Point(lon, lat)  # Shapely usa (longitude, latitude)
            
            # Converte a geometria GeoJSON para objeto Shapely
            geom = shape(geometry)
            
            # Verifica se o ponto está dentro da geometria
            return geom.contains(point_obj)
            
        except Exception as e:
            print(f"Erro ao verificar ponto na propriedade: {e}")
            return False
    
    def extract_boundary(self, geometry: Dict) -> List[List[float]]:
        """
        Extrai os pontos do perímetro de uma geometria
        
        Args:
            geometry: Geometria no formato GeoJSON
            
        Returns:
            Lista de pontos [lon, lat] que formam o perímetro
        """
        try:
            # Converte a geometria GeoJSON para objeto Shapely
            geom = shape(geometry)
            
            # Extrai os pontos do perímetro
            if isinstance(geom, Polygon):
                # Retorna apenas o anel externo para polígono simples
                return list(geom.exterior.coords)
            elif isinstance(geom, MultiPolygon):
                # Para multipolígono, retorna o perímetro do maior polígono
                largest = max(geom.geoms, key=lambda g: g.area)
                return list(largest.exterior.coords)
            else:
                return []
                
        except Exception as e:
            print(f"Erro ao extrair perímetro: {e}")
            return []
    
    def simplify_geometry(self, geometry: Dict, tolerance: float = 0.0001) -> Dict:
        """
        Simplifica uma geometria reduzindo o número de pontos
        
        Args:
            geometry: Geometria no formato GeoJSON
            tolerance: Tolerância para simplificação (graus)
            
        Returns:
            Geometria simplificada no formato GeoJSON
        """
        try:
            # Converte a geometria GeoJSON para objeto Shapely
            geom = shape(geometry)
            
            # Simplifica a geometria
            simplified = geom.simplify(tolerance, preserve_topology=True)
            
            # Converte de volta para GeoJSON
            return json.loads(json.dumps(simplified.__geo_interface__))
            
        except Exception as e:
            print(f"Erro ao simplificar geometria: {e}")
            return geometry
    
    def find_properties_by_point(self, 
                                point: Tuple[float, float], 
                                shapefiles_dir: Union[str, Path]) -> List[Dict]:
        """
        Encontra todas as propriedades que contêm um determinado ponto
        
        Args:
            point: Tuple (latitude, longitude)
            shapefiles_dir: Diretório contendo shapefiles
            
        Returns:
            Lista de propriedades que contêm o ponto
        """
        try:
            shapefiles_dir = Path(shapefiles_dir)
            if not shapefiles_dir.exists() or not shapefiles_dir.is_dir():
                raise FileNotFoundError(f"Diretório não encontrado: {shapefiles_dir}")
                
            # Cria um objeto Point do Shapely
            lat, lon = point
            point_obj = Point(lon, lat)  # Shapely usa (longitude, latitude)
            
            matching_properties = []
            
            # Procura em todos os shapefiles no diretório
            for shp_file in shapefiles_dir.glob("**/*.shp"):
                try:
                    sf = shapefile.Reader(str(shp_file))
                    
                    # Extrai os campos
                    fields = [field[0] for field in sf.fields[1:]]
                    
                    # Verifica cada shape
                    for i, shp in enumerate(sf.shapes()):
                        geom = shape(shp.__geo_interface__)
                        
                        if geom.contains(point_obj):
                            properties = dict(zip(fields, sf.record(i)))
                            matching_properties.append({
                                'geometry': shp.__geo_interface__,
                                'properties': properties,
                                'shapefile': str(shp_file)
                            })
                except Exception as e:
                    print(f"Erro ao processar {shp_file}: {e}")
                    continue
                    
            return matching_properties
            
        except Exception as e:
            print(f"Erro ao buscar propriedades por ponto: {e}")
            return []
    
    def convert_to_geojson(self, shp_path: Union[str, Path], 
                          output_path: Optional[Union[str, Path]] = None) -> Dict:
        """
        Converte um shapefile para GeoJSON
        
        Args:
            shp_path: Caminho para o shapefile
            output_path: Caminho para salvar o GeoJSON (opcional)
            
        Returns:
            Dados convertidos no formato GeoJSON
        """
        geojson = self.read_shapefile(shp_path)
        
        if output_path is not None:
            output_path = Path(output_path)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(geojson, f)
                
        return geojson
        
    def calculate_property_statistics(self, geometry: Dict) -> Dict:
        """
        Calcula estatísticas de uma propriedade
        
        Args:
            geometry: Geometria no formato GeoJSON
            
        Returns:
            Dicionário com estatísticas da propriedade
        """
        try:
            area_ha = self.calculate_area(geometry, in_hectares=True)
            perimeter_m = self.calculate_perimeter(geometry)
            centroid = self._get_centroid(shape(geometry))
            
            # Calcula métricas adicionais
            compactness = 4 * math.pi * area_ha / (perimeter_m**2 / 10000)  # Índice de compacidade
            
            return {
                'area_hectares': round(area_ha, 2),
                'area_m2': round(area_ha * 10000, 2),
                'perimeter_m': round(perimeter_m, 2),
                'centroid': {'lat': centroid[0], 'lon': centroid[1]},
                'compactness': round(compactness, 4),
            }
            
        except Exception as e:
            print(f"Erro ao calcular estatísticas: {e}")
            return {
                'area_hectares': 0,
                'area_m2': 0,
                'perimeter_m': 0,
                'centroid': {'lat': 0, 'lon': 0},
                'compactness': 0,
            }
