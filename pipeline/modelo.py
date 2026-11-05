"""Carrega o classificador treinado (checkpoints/modelo.onnx, gerado por
scripts/05_treinar_cnn.py) e roda a inferencia. Uma inferencia leva ~2ms
em CPU — nao precisa de fila/worker so por causa disto (ver pipeline/
docstring do diagnostico.py)."""

import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
CAMINHO_MODELO = RAIZ / "checkpoints" / "modelo.onnx"
CAMINHO_CLASSES = RAIZ / "checkpoints" / "classes.json"

MEDIA_IMAGENET = np.array([0.485, 0.456, 0.406], dtype=np.float32)
DESVIO_IMAGENET = np.array([0.229, 0.224, 0.225], dtype=np.float32)

_sessao: ort.InferenceSession | None = None
_classes: list[str] | None = None


def _carregar():
    global _sessao, _classes
    if _sessao is None:
        if not CAMINHO_MODELO.exists():
            raise FileNotFoundError(
                f"{CAMINHO_MODELO} nao existe — rode scripts/05_treinar_cnn.py primeiro"
            )
        _sessao = ort.InferenceSession(str(CAMINHO_MODELO), providers=["CPUExecutionProvider"])
        _classes = json.loads(CAMINHO_CLASSES.read_text(encoding="utf-8"))
    return _sessao, _classes


def _preprocessar(imagem: Image.Image) -> np.ndarray:
    """Mesmo pre-processo do val/teste em scripts/05_treinar_cnn.py:
    resize 256 -> center crop 224 -> normaliza com media/desvio da ImageNet.
    Tem que ser identico ao do treino, senao a acuracia despenca."""
    lado = 256
    w, h = imagem.size
    if w < h:
        nova_w, nova_h = lado, int(h * lado / w)
    else:
        nova_w, nova_h = int(w * lado / h), lado
    imagem = imagem.convert("RGB").resize((nova_w, nova_h), Image.BILINEAR)

    esq = (nova_w - 224) // 2
    topo = (nova_h - 224) // 2
    imagem = imagem.crop((esq, topo, esq + 224, topo + 224))

    x = np.asarray(imagem, dtype=np.float32) / 255.0
    x = (x - MEDIA_IMAGENET) / DESVIO_IMAGENET
    x = x.transpose(2, 0, 1)[None, ...]  # HWC -> NCHW
    return x.astype(np.float32)


def classificar(imagem: Image.Image) -> tuple[str, float]:
    """Devolve (classe_prevista, confianca 0-1)."""
    sessao, classes = _carregar()
    x = _preprocessar(imagem)
    logits = sessao.run(None, {"foto": x})[0][0]
    probs = np.exp(logits - logits.max())
    probs /= probs.sum()
    idx = int(probs.argmax())
    return classes[idx], float(probs[idx])
