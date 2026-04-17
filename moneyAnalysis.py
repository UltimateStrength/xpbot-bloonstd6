import time
import pytesseract
from PIL import ImageGrab, Image
import re
import numpy as np
from collections import Counter

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

BUSCA_X1 = 281
BUSCA_X2 = 393
BUSCA_Y1 = 53
BUSCA_Y2 = 80

STREAK_NECESSARIO = 4   # leituras consecutivas iguais pra confirmar valor exato
JANELA_MOVEL = 8        # leituras recentes pra analisar prefixo em movimento
INTERVALO = 0.1

def preprocessar(img):
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
    img_bin = img_bin.resize((w * 3, h * 3), Image.NEAREST)
    img_bin.save("debug.png")
    return img_bin

def extrair_numero(texto):
    nums = re.sub(r"\D", "", texto.strip())
    if not nums:
        return None
    val = int(nums)
    return str(val) if val <= 999999 else None

def leitura_unica():
    img = ImageGrab.grab(bbox=(BUSCA_X1, BUSCA_Y1, BUSCA_X2, BUSCA_Y2))
    img_proc = preprocessar(img)
    if img_proc is None:
        return None
    texto = pytesseract.image_to_string(
        img_proc,
        config="--psm 7 --oem 1 -c tessedit_char_whitelist=0123456789"
    )
    return extrair_numero(texto)

def prefixo_comum(leituras):
    """
    Acha o prefixo mais longo que aparece em pelo menos 60% das leituras válidas.
    Ex: ['16434', '16875', '16', '1600'] -> '16' aparece em todas -> retorna '16xxx'
    """
    if not leituras:
        return None

    # Tenta prefixos do maior pro menor
    max_len = max(len(v) for v in leituras)
    limiar = max(2, int(len(leituras) * 0.6))

    for tam in range(max_len, 0, -1):
        prefixos = [v[:tam] for v in leituras if len(v) >= tam]
        if not prefixos:
            continue
        contagem = Counter(prefixos)
        mais_comum, freq = contagem.most_common(1)[0]
        if freq >= limiar:
            # Retorna o valor completo mais frequente que começa com esse prefixo
            candidatos = [v for v in leituras if v.startswith(mais_comum)]
            return Counter(candidatos).most_common(1)[0][0]

    return None

def monitorar():
    ultimo_confirmado = None
    streak_val = None
    streak_count = 0
    janela = []  # leituras recentes pra análise de prefixo

    print("Monitorando dinheiro BTD6... (Ctrl+C pra parar)\n")

    while True:
        val = leitura_unica()

        if val is None:
            streak_val = None
            streak_count = 0
            time.sleep(INTERVALO)
            continue

        # Sanidade: ignora quedas bruscas
        if ultimo_confirmado is not None:
            ultimo_int = int(ultimo_confirmado)
            val_int = int(val)
            if ultimo_int > 0 and val_int < ultimo_int * 0.5 and val_int < ultimo_int - 500:
                time.sleep(INTERVALO)
                continue

        # --- STREAK: número parado ---
        if val == streak_val:
            streak_count += 1
        else:
            streak_val = val
            streak_count = 1

        if streak_count >= STREAK_NECESSARIO:
            if streak_val != ultimo_confirmado:
                print(f"Dinheiro: ${streak_val}  [confirmado]")
                ultimo_confirmado = streak_val
                janela.clear()

                # ACAO CONDICIONAL
                # if int(streak_val) >= 5000:
                #     pyautogui.click(x, y)

            time.sleep(0.5)
            continue

        # --- PREFIXO: número em movimento ---
        janela.append(val)
        if len(janela) > JANELA_MOVEL:
            janela.pop(0)

        if len(janela) >= 4:
            estimativa = prefixo_comum(janela)
            if estimativa and estimativa != ultimo_confirmado:
                print(f"Dinheiro: ~${estimativa}  [estimativa]")
                ultimo_confirmado = estimativa

        time.sleep(INTERVALO)

monitorar()