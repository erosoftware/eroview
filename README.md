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
- Navegador web compatível (Chrome recomendado)
- Conexão com internet para acesso ao portal SICAR

## Instalação

1. Clone ou baixe este repositório
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Configure as variáveis de ambiente (opcional):
   - `SICAR_HEADLESS`: Define se o navegador deve rodar em modo headless (sem interface gráfica)
   - `SICAR_DEV_MODE`: Ativa recursos de desenvolvimento
   - `SICAR_BROWSER`: Define qual navegador utilizar (chrome ou firefox)

## Uso

### Coordenadas de teste
Para testes, recomendamos usar as coordenadas: `-23.276064, -53.266292` (localizada em Douradina, Paraná)

### Iniciando o aplicativo
```
python eroview_sicar_app.py
```

### Usando a interface web
1. Acesse o aplicativo através do navegador no endereço indicado (geralmente http://localhost:5000)
2. Na interface "Visualizador de Mapa SICAR", insira as coordenadas geográficas
3. Clique em "Buscar Propriedade"
4. Aguarde o processamento e visualize os resultados

## Solução de problemas comuns

### O navegador não abre dentro do iframe
- Verifique se as opções de segurança do navegador permitem incorporação (embedding)
- Garanta que o parâmetro `embed_browser` esteja definido como True

### O cursor aparece na posição errada
- Certifique-se de que o formato das coordenadas está correto (graus decimais)
- Verifique se as coordenadas estão dentro do território brasileiro

### O estado não é selecionado corretamente
- O sistema usa múltiplos métodos para selecionar o estado. Verifique os logs para entender qual método falhou

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

## Contribuição

Contribuições são bem-vindas! Por favor, siga estas etapas:
1. Faça um fork do repositório
2. Crie uma branch para sua funcionalidade (`git checkout -b feature/nova-funcionalidade`)
3. Faça commit das mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Envie para o repositório (`git push origin feature/nova-funcionalidade`)
5. Crie um Pull Request

## Licença

Este projeto está licenciado sob a Licença Apache 2.0 - veja o arquivo LICENSE para detalhes.

```
Copyright 2023 Ɜrθ Software

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```
