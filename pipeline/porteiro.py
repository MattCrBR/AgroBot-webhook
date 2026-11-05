"""Porteiro de qualidade — pede outra foto antes de gastar inferencia com
uma foto ruim. Mesma logica (e mesmo limiar) de scripts/02_limpar_duplicatas.py:
variancia do Laplaciano pelo MAXIMO entre blocos 4x4, nao pela imagem
inteira, porque macro com profundidade de campo rasa (inseto nitido, fundo
desfocado de proposito) tem variancia baixa na imagem inteira mesmo sendo
uma otima foto."""

import cv2
import numpy as np
from PIL import Image

LADO_MINIMO = 100          # mais tolerante que o dataset (foto de celular real)
LIMIAR_BORRAO = 60.0        # mesmo limiar calibrado no script 02


def _variancia_laplaciano_max_blocos(cinza: np.ndarray) -> float:
    h, w = cinza.shape
    n = 4
    bh, bw = h // n, w // n
    if bh < 8 or bw < 8:
        return float(cv2.Laplacian(cinza, cv2.CV_64F).var())
    melhores = []
    for i in range(n):
        for j in range(n):
            bloco = cinza[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]
            melhores.append(cv2.Laplacian(bloco, cv2.CV_64F).var())
    return float(max(melhores))


def verificar(imagem: Image.Image) -> tuple[bool, str | None]:
    """Devolve (ok, motivo). motivo e' None quando ok=True."""
    w, h = imagem.size
    if min(w, h) < LADO_MINIMO:
        return False, "pequena"

    cinza = np.asarray(imagem.convert("L"))
    if _variancia_laplaciano_max_blocos(cinza) < LIMIAR_BORRAO:
        return False, "borrada"

    return True, None


MENSAGEM_POR_MOTIVO = {
    "pequena": "A foto chegou muito pequena pra eu enxergar direito. "
               "Manda de novo, mais perto da folha ou do bicho? 📷",
    "borrada": "Essa foto saiu meio embaçada, não consigo ter certeza. "
               "Tenta de novo com a mão mais firme, bem em cima do que você quer mostrar? 📷",
}
