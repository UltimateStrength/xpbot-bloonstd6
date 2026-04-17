# BTD6 XP Farm Bot

Bot de automação para farm de XP de usuário no Bloons Tower Defense 6, usando OCR para leitura de dinheiro em tempo real e PyAutoGUI/pydirectinput para controle do jogo.

---

## Contexto

O objetivo é acumular XP de usuário de forma automatizada. A estratégia usa o mapa **Sapper** no modo **Hard / Impopular**, que oferece uma boa relação de XP por tempo de jogo — mas exige as power-ups **Fast Track** e **Double Cash** ativos para ser viável.

> ⚠️ Sem Fast Track e Double Cash a run demora muito mais e o farm deixa de ser eficiente.

---

## Pré-requisitos

### Software

- **Python 3.10+**
- **Tesseract OCR** instalado em `C:\Program Files\Tesseract-OCR\tesseract.exe`
  - Download: https://github.com/UB-Mannheim/tesseract/wiki

### Dependências Python

```
pip install -r requirements.txt
```

### No jogo

- Power-ups **Fast Track** e **Double Cash** ativos antes de iniciar
- Estar na tela principal (menu) quando rodar o bot

---

## Estrutura

```
.
├── main.py            # Bot principal — loop completo de jogo
├── moneyAnalysis.py   # Versão standalone do monitor de dinheiro (debug/teste)
├── mouseCoords.py     # Utilitário para capturar coordenadas do mouse
└── debug.png          # Imagem gerada pelo OCR (gerada em tempo de execução)
```

### `main.py`

Arquivo principal. Contém:

- **OCR em thread separada** — lê o dinheiro da tela a cada 100ms via screenshot da região configurada, com sistema de streak (confirmação por N leituras iguais) e sanidade (ignora quedas/saltos absurdos)
- **Controle de input** — `pyautogui` para movimento de mouse e `pydirectinput` para teclas (necessário pois o jogo ignora inputs simulados do pyautogui)
- **Fases do loop** — `fase_menu → fase_colocar_torres → fase_iniciar_jogo → fase_build_principal → fase_fim_jogo`, executadas em loop contínuo
- **Habilidade periódica** — thread secundária que pressiona `3` a cada 17s para ativar a habilidade da Usina de Espinhos
- **Failsafe** — mover o mouse pro canto superior esquerdo encerra o bot imediatamente

### `moneyAnalysis.py`

Versão isolada do sistema de OCR, sem automação. Útil para testar se a leitura de dinheiro está funcionando corretamente antes de rodar o bot completo.

### `mouseCoords.py`

Aguarda 5 segundos e imprime as coordenadas atuais do mouse. Usado para mapear posições de torres, botões e outros elementos na tela.

---

## Configuração

### Resolução

O bot foi desenvolvido para resolução **1440x900**. Em outras resoluções todas as coordenadas precisam ser ajustadas.

### Ajustando posições

1. Rode `mouseCoords.py`
2. Posicione o mouse sobre o elemento que quer mapear
3. Aguarde os 5 segundos e anote as coordenadas
4. Atualize o dicionário `POS` no `main.py`

### Ajustando a região do dinheiro

A leitura de OCR captura uma região fixa da tela onde o contador de dinheiro aparece. Se o valor não estiver sendo lido corretamente:

1. Use `mouseCoords.py` para identificar os limites do contador
2. Atualize as constantes no `main.py`:

```python
BUSCA_X1, BUSCA_Y1 = 281, 53   # canto superior esquerdo da região
BUSCA_X2, BUSCA_Y2 = 393, 80   # canto inferior direito da região
```

Também é possível usar `moneyAnalysis.py` para validar a leitura isoladamente antes de rodar o bot completo. O arquivo `debug.png` é gerado a cada leitura e mostra exatamente o que o OCR está processando.

---

## Como usar

```bash
python main.py
```

O bot começa com um delay de 2 segundos. Deixe o jogo na tela principal antes de executar.

Para encerrar: mova o mouse rapidamente para o **canto superior esquerdo** da tela (failsafe do pyautogui).
