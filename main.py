import time
import threading
import pytesseract
import pydirectinput
from PIL import ImageGrab, Image
import re
import numpy as np
from collections import Counter
import pyautogui

pyautogui.FAILSAFE = True  # move mouse pro canto pra parar
pyautogui.PAUSE = 0.05

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────
# POSIÇÕES (fácil de adaptar pra outra resolução)
# ─────────────────────────────────────────────
POS = {
    # Menu
    "btn_play":        (727, 780),
    "btn_aba1":        (401, 785),
    "btn_aba2":        (401, 785),  # clicado 2x
    "btn_mapa":        (1054, 181),
    "btn_hard":        (987, 325),
    "btn_impopular":   (1000, 602),
    "btn_ok_alert":    (694, 635),

    # Fim de jogo
    "btn_brinde_ok":   (729, 378),
    "btn_proximo":     (711, 755),
    "btn_home":        (515, 705),

    # Torres
    "heroi":           (251, 312),
    "bucaneiro":       (512, 725),
    "usina":           (387, 835),
    "ninja":           (328, 783),
    "vila":            (435, 766),
    "mago":            (338, 669),
    "druida":          (250, 756),
    "macaco_as":       (416, 168),
    "vila2":           (390, 268), 
}

# ─────────────────────────────────────────────
# ATALHOS DE TECLADO
# ─────────────────────────────────────────────
HOTKEY = {
    "heroi":      "u",
    "bucaneiro":  "c",
    "usina":      "j",   # Tack Shooter
    "ninja":      "d",
    "vila":       "k",   # Monkey Village (não listado nos hotkeys = sem atalho padrão, usar loja)
    "mago":       "a",
    "druida":     "g",
    "macaco_as":  "v",
    "up1":        ",",
    "up2":        ".",
    "up3":        "/",
    "play":       "space",
    "habilidade3": "3",
}

# ─────────────────────────────────────────────
# DETECÇÃO DE DINHEIRO
# ─────────────────────────────────────────────
BUSCA_X1, BUSCA_Y1 = 281, 53
BUSCA_X2, BUSCA_Y2 = 393, 80
STREAK_NECESSARIO  = 4
JANELA_MOVEL       = 8
INTERVALO_OCR      = 0.1

dinheiro_atual = 0
dinheiro_leitura = 0  # valor em tempo real (sem streak)
_ocr_lock = threading.Lock()

def _preprocessar(img):
    arr = np.array(img)
    r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    mascara = (r > 225) & (g > 225) & (b > 225)
    colunas = [x for x in range(arr.shape[1]) if mascara[:, x].any()]
    if not colunas:
        return None
    x1 = max(0, colunas[0] - 2)
    x2 = min(arr.shape[1], colunas[-1] + 3)
    recorte = mascara[:, x1:x2]
    if recorte.sum() < 30:
        return None
    resultado = np.where(recorte, 0, 255).astype(np.uint8)
    img_bin = Image.fromarray(resultado)
    w, h = img_bin.size
    return img_bin.resize((w * 3, h * 3), Image.NEAREST)

def _extrair_numero(texto):
    nums = re.sub(r"\D", "", texto.strip())
    if not nums:
        return None

    # mantém como string (IMPORTANTE)
    return nums if len(nums) <= 6 else None

def _leitura_unica():
    img = ImageGrab.grab(bbox=(BUSCA_X1, BUSCA_Y1, BUSCA_X2, BUSCA_Y2))
    img_proc = _preprocessar(img)
    if img_proc is None:
        return None
    texto = pytesseract.image_to_string(
        img_proc,
        config="--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789"
    )
    return _extrair_numero(texto)

def _prefixo_comum(leituras):
    if not leituras:
        return None

    leituras_str = [str(v) for v in leituras]
    max_len = max(len(v) for v in leituras_str)
    limiar = max(2, int(len(leituras_str) * 0.6))

    for tam in range(max_len, 0, -1):
        prefixos = [v[:tam] for v in leituras_str if len(v) >= tam]
        if not prefixos:
            continue

        contagem = Counter(prefixos)
        mais_comum, freq = contagem.most_common(1)[0]

        if freq >= limiar:
            candidatos = [v for v in leituras_str if v.startswith(mais_comum)]
            # 🔥 retorna STRING, não int
            return Counter(candidatos).most_common(1)[0][0]

    return None

def _loop_ocr():
    global dinheiro_atual, dinheiro_leitura

    streak_val = None
    streak_count = 0
    janela = []
    ultimo_confirmado = 0

    while True:
        val = _leitura_unica()

        print(f"[OCR RAW] {val}")

        if val is None:
            streak_val = None
            streak_count = 0
            time.sleep(INTERVALO_OCR)
            continue

        # 🔥 VALOR EM TEMPO REAL (sempre atualiza)
        with _ocr_lock:
            dinheiro_leitura = int(val)

        val_int = int(val)

        # Sanidade (evita leitura bugada)
        if ultimo_confirmado > 0:
            if val_int < ultimo_confirmado * 0.5 and val_int < ultimo_confirmado - 500:
                time.sleep(INTERVALO_OCR)
                continue

            # evita salto absurdo
            if val_int > ultimo_confirmado + 10000:
                time.sleep(INTERVALO_OCR)
                continue

        # --- STREAK ---
        if val == streak_val:
            streak_count += 1
        else:
            streak_val = val
            streak_count = 1

        if streak_count >= STREAK_NECESSARIO:
            dinheiro_int = int(streak_val)

            with _ocr_lock:
                dinheiro_atual = dinheiro_int

            print(f"[OCR FINAL] {dinheiro_int}")

            if dinheiro_int != ultimo_confirmado:
                print(f"  💰 ${dinheiro_int:,}  [confirmado]")
                ultimo_confirmado = dinheiro_int

            janela.clear()
            time.sleep(INTERVALO_OCR)
            continue

        # ❌ NÃO ATUALIZA dinheiro com estimativa (evita bug)
        janela.append(val)
        if len(janela) > JANELA_MOVEL:
            janela.pop(0)

        time.sleep(INTERVALO_OCR)

def get_dinheiro():
    with _ocr_lock:
        return dinheiro_atual

def get_dinheiro_real():
    with _ocr_lock:
        return dinheiro_leitura

def aguardar_dinheiro(valor, msg=""):
    print(f"\n⏳ Aguardando ${valor:,} {msg}")

    confirmacoes = 0

    while True:
        real = get_dinheiro_real()

        print(f"   💰 Tempo real: {real} | Necessário: {valor}")

        if real >= valor:
            confirmacoes += 1
        else:
            confirmacoes = 0

        # 🔥 PRECISA CONFIRMAR 20x SEGUIDAS
        if confirmacoes >= 20:
            print("   ✅ Valor atingido!\n")
            break

        time.sleep(0.15)

# ─────────────────────────────────────────────
# UTILITÁRIOS DE INPUT
# ─────────────────────────────────────────────
def mover(x, y, duracao=0.4):
    """Move o mouse suavemente (evita teleporte)."""
    pyautogui.moveTo(x, y, duration=duracao)

def clicar(x, y, duracao=0.4):
    mover(x, y, duracao)
    pyautogui.click()
    time.sleep(0.15)

def tecla(key, espera=0.15):
    pyautogui.press(key)
    time.sleep(espera)

def colocar_torre(hotkey, pos_x, pos_y):
    """Pressiona atalho, move o mouse suavemente e clica pra colocar a torre."""
    
    pydirectinput.press(hotkey)
    time.sleep(0.2)
    
    # movimento suave (não teleporta)
    pydirectinput.moveTo(pos_x, pos_y, duration=0.2)
    time.sleep(0.2)
    
    pydirectinput.click()
    time.sleep(0.3)

def upar(caminho, vezes=1, espera_entre=0.3):
    """Caminho: 'up1', 'up2' ou 'up3'."""
    
    tecla_upgrade = HOTKEY[caminho]
    
    for _ in range(vezes):
        # mais confiável que press em jogo
        pydirectinput.keyDown(tecla_upgrade)
        time.sleep(0.05)
        pydirectinput.keyUp(tecla_upgrade)
        
        time.sleep(espera_entre)

def clicar_torre(pos_key):
    fechar_painel()  # 🔥 garante estado limpo

    x, y = POS[pos_key]
    clicar(x, y)
    time.sleep(0.2)

def fechar_painel():
    """Clica em uma área vazia pra garantir que nenhum painel esteja aberto."""
    pyautogui.click(628, 114)  # canto seguro da tela
    time.sleep(0.2)

# ─────────────────────────────────────────────
# HABILIDADE PERIÓDICA (a cada 17s aperta '3')
# ─────────────────────────────────────────────
_habilidade_ativa = False

def _loop_habilidade():
    while _habilidade_ativa:
        # usa pydirectinput (funciona dentro do jogo)
        pydirectinput.keyDown("3")
        time.sleep(0.05)
        pydirectinput.keyUp("3")

        print("  ⚡ Habilidade usina ativada")
        time.sleep(17)

habilidade_thread = None

def iniciar_habilidade():
    global _habilidade_ativa, habilidade_thread
    _habilidade_ativa = True
    habilidade_thread = threading.Thread(target=_loop_habilidade, daemon=True)
    habilidade_thread.start()

def parar_habilidade():
    global _habilidade_ativa
    _habilidade_ativa = False

# ─────────────────────────────────────────────
# FASES DA BUILD5
# ─────────────────────────────────────────────
def fase_menu():
    print("\n🎮 Abrindo mapa...")
    clicar(*POS["btn_play"])
    time.sleep(1)
    # Clica 2x na aba pra chegar na certa
    clicar(*POS["btn_aba1"])
    time.sleep(0.3)
    clicar(*POS["btn_aba2"])
    time.sleep(0.5)
    clicar(*POS["btn_mapa"])
    time.sleep(0.5)  # espera carregar
    clicar(*POS["btn_hard"])
    time.sleep(0.5)
    clicar(*POS["btn_impopular"])
    time.sleep(10)
    clicar(*POS["btn_ok_alert"])
    time.sleep(1)
    print("✅ Mapa selecionado")

def fase_colocar_torres():
    print("\n🐒 Colocando torres...")

    # Herói
    colocar_torre(HOTKEY["heroi"], *POS["heroi"])
    print("  Herói colocado")

    clicar(45, 824)

    # Bucaneiro
    colocar_torre(HOTKEY["bucaneiro"], *POS["bucaneiro"])
    print("  Bucaneiro colocado")

    # Usina de espinhos
    colocar_torre(HOTKEY["usina"], *POS["usina"])
    print("  Usina colocada")

    # Upar usina: 2x cima, 3x meio
    clicar_torre("usina")
    upar("up1", 2)
    upar("up2", 3)
    print("  Usina upada (2 cima, 3 meio)")

    # Upar bucaneiro: 3x meio, 2x cima
    clicar_torre("bucaneiro")
    upar("up2", 3)
    upar("up1", 2)
    print("  Bucaneiro upado (3 meio, 2 cima)")

def fase_iniciar_jogo():
    print("\n▶️  Iniciando jogo...")
    
    # start
    pydirectinput.keyDown("space")
    time.sleep(0.05)
    pydirectinput.keyUp("space")
    
    time.sleep(1.5)
    
    # acelera
    pydirectinput.keyDown("space")
    time.sleep(0.05)
    pydirectinput.keyUp("space")
    
    time.sleep(0.5)

def fase_build_principal():
    print("\n🔧 Build principal em andamento...\n")

    # ── $5000: upar bucaneiro meio 1x
    aguardar_dinheiro(5000, "bucaneiro up2")
    clicar_torre("bucaneiro")
    upar("up2", 1)
    print("  ✔ Bucaneiro +1 meio")

    # ── $9000: upar usina meio 1x
    aguardar_dinheiro(9000, "usina up2")
    clicar_torre("usina")
    upar("up2", 1)
    print("  ✔ Usina +1 meio")

    # Inicia habilidade periódica da usina
    iniciar_habilidade()

    # ── Ninja ($500 de margem sobre custo base)
    aguardar_dinheiro(500 + 50, "ninja")
    colocar_torre(HOTKEY["ninja"], *POS["ninja"])
    print("  ✔ Ninja colocado")

    # ── Ninja: 3x baixo (acima de 3600)
    aguardar_dinheiro(3600, "ninja up3 x3")
    clicar_torre("ninja")
    upar("up3", 3)
    print("  ✔ Ninja +3 baixo")

    # ── Ninja: 2x cima (acima de 900)
    aguardar_dinheiro(900, "ninja up1 x2")
    clicar_torre("ninja")
    upar("up1", 2)
    print("  ✔ Ninja +2 cima")

    # ── Ninja: mais 1 baixo (acima de 6000)
    aguardar_dinheiro(6000, "ninja up3")
    clicar_torre("ninja")
    upar("up3", 1)
    print("  ✔ Ninja +1 baixo")

    # ── Vila macaco ($1500 margem)
    aguardar_dinheiro(1500, "vila macaco")
    colocar_torre(HOTKEY["vila"], *POS["vila"])
    print("  ✔ Vila colocada")

    # Vila: ups sequenciais (arredondados pra cima)
    for custo, path, vezes, label in [
        (500,  "up1", 1, "vila +1 cima"),
        (1800, "up1", 1, "vila +1 cima"),
        (300,  "up2", 1, "vila +1 meio"),
        (2400, "up2", 1, "vila +1 meio"),
    ]:
        aguardar_dinheiro(custo, label)
        clicar_torre("vila")
        upar(path, vezes)
        print(f"  ✔ {label}")

    # ── Mago ($350 margem)
    aguardar_dinheiro(350, "mago")
    colocar_torre(HOTKEY["mago"], *POS["mago"])
    print("  ✔ Mago colocado")

    # Mago ups
    aguardar_dinheiro(15450, "mago +1 cima")
    clicar_torre("mago")
    upar("up1", 4)
    upar("up3", 2)
    print("mago +1 cima")

    # ── Druida ($530 margem)
    aguardar_dinheiro(500, "druida")
    colocar_torre(HOTKEY["druida"], *POS["druida"])
    print("  ✔ Druida colocado")

    # ── Druida: 4x meio (acima de 8000)
    aguardar_dinheiro(8000, "druida up2 x4")
    clicar_torre("druida")
    upar("up2", 4)
    print("  ✔ Druida +4 meio")

    # ── Druida: 2x cima (acima de 1500)
    aguardar_dinheiro(1500, "druida up1 x2")
    clicar_torre("druida")
    upar("up1", 2)
    print("  ✔ Druida +2 cima")

    # ── $50000: usina up meio
    aguardar_dinheiro(50000, "usina up2")
    clicar_torre("usina")
    upar("up2", 1)
    print("  ✔ Usina +1 meio")

    # ── $40000: mago up cima
    aguardar_dinheiro(40000, "mago up1")
    clicar_torre("mago")
    upar("up1", 1)
    print("  ✔ Mago +1 cima")

    # ── Macaco as + Vila 2
    aguardar_dinheiro(5500, "macaco as + vila2")
    colocar_torre(HOTKEY["macaco_as"], *POS["macaco_as"])
    print("  ✔ Macaco as colocado")
    colocar_torre(HOTKEY["vila"], *POS["vila2"])
    print("  ✔ Vila 2 colocada")

    # Vila2: 2x cima, 2x meio (~$5000 total)
    for path, vezes, label in [
        ("up1", 2, "vila2 +2 cima"),
        ("up2", 2, "vila2 +2 meio"),
    ]:
        clicar_torre("vila2")
        upar(path, vezes)
        print(f"  ✔ {label}")

        aguardar_dinheiro(34000, "macaco_as +2 cima")
        clicar_torre("macaco_as")
        upar("up1", 2)
        upar("up3", 4)
        print("macaco_as +2 cima")

    # ── $33000: bucaneiro up meio
    aguardar_dinheiro(33000, "bucaneiro up2")
    clicar_torre("bucaneiro")
    upar("up2", 1)
    print("  ✔ Bucaneiro +1 meio")

    # ── $50000: ninja up baixo
    aguardar_dinheiro(50000, "ninja up3")
    clicar_torre("ninja")
    upar("up3", 1)
    print("  ✔ Ninja +1 baixo")

    # ── $43000: druida up meio
    aguardar_dinheiro(43000, "druida up2")
    clicar_torre("druida")
    upar("up2", 1)
    print("  ✔ Druida +1 meio")

    print("\n🏆 Build completa! Aguardando fim de jogo...")
    time.sleep(100)

def fase_fim_jogo():
    parar_habilidade()
    print("\n🎉 Fim de jogo detectado — coletando brinde...")
    time.sleep(3)  # espera tela de vitória aparecer
    clicar(*POS["btn_brinde_ok"])
    time.sleep(1)
    clicar(*POS["btn_proximo"])
    time.sleep(1)
    clicar(*POS["btn_home"])
    time.sleep(2)
    print("✅ Voltando ao menu — reiniciando loop\n")

# ─────────────────────────────────────────────
# LOOP PRINCIPAL
# ─────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  BTD6 BOT — iniciando")
    print("  Mova o mouse pro canto superior esquerdo pra parar (failsafe)")
    print("=" * 50)

    # Inicia thread de OCR em background
    ocr_thread = threading.Thread(target=_loop_ocr, daemon=True)
    ocr_thread.start()

    time.sleep(2)  # pequena margem antes de começar

    while True:
        try:
            fase_menu()
            fase_colocar_torres()
            fase_iniciar_jogo()
            fase_build_principal()
            fase_fim_jogo()
        except pyautogui.FailSafeException:
            print("\n🛑 Failsafe ativado — bot encerrado")
            parar_habilidade()
            break
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            parar_habilidade()
            time.sleep(5)
            print("🔄 Reiniciando loop...")

if __name__ == "__main__":
    main()