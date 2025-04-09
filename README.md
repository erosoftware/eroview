# Ɜrθ View - Integração SICAR

Aplicativo para integração do Eroview com o Sistema de Cadastro Ambiental Rural (SICAR), permitindo buscar propriedades rurais usando coordenadas geográficas em vez do código CAR.

## Funcionalidades

- Busca de propriedades rurais por coordenadas geográficas (latitude/longitude)
- Suporte para diferentes formatos de entrada (coordenadas diretas, URLs do Google Maps)
- Visualização dos contornos das propriedades com destaque em amarelo
- Download de mapas das propriedades
- Download e extração de shapefiles
- Simulação para testes quando o servidor SICAR não responde

## Requisitos

- Python 3.6 ou superior
- Bibliotecas Python listadas em `requirements.txt`

## Instalação

1. Clone ou baixe este repositório
2. Instale as dependências:

```
pip install -r requirements.txt
```

## Uso

Para iniciar o aplicativo, execute:

```
python eroview_sicar_app.py
```

### Exemplo de uso:

1. Insira coordenadas no formato `-23.276064, -53.266292` (Douradina, PR)
2. Clique em "Buscar Propriedade"
3. Visualize o mapa da propriedade com contornos em amarelo
4. Utilize os botões "Baixar Mapa" e "Baixar Shapefile" conforme necessário

## Estrutura do Projeto

- `eroview_sicar_app.py` - Aplicativo principal com interface gráfica
- `sicar_connector.py` - Módulo para comunicação com o SICAR
- `requirements.txt` - Lista de dependências do projeto

## Próximos passos

- Implementação da geolocalização no Android
- Gerenciamento de shapefiles
- Processamento geoespacial (cálculos de área, perímetro)
- Melhorias na conexão com SICAR
- Testes em campo

## Notas

Os dados utilizados para teste são da coordenada `-23.276064, -53.266292` localizada em Douradina, Paraná.
A exibição dos mapas simula os contornos das propriedades em amarelo conforme especificado nos requisitos.
