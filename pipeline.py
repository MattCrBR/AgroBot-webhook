import os
import logging

# Limiares do roteador de confiança
LIMIAR_ALTO = 0.80
LIMIAR_MEDIO = 0.50

CLASSES = ["lagarta-do-cartucho", "lagarta-da-espiga", "vaquinha", "milho-saudavel"]

logger = logging.getLogger(__name__)

# Rodapé fixo: anexado pelo sistema, sem depender do LLM
AVISO = "⚠️ Orientação geral, não substitui a receita de um engenheiro agrônomo."
PERGUNTA_FEEDBACK = "Acertei? Responda com 👍 ou 👎"


def _com_rodape(texto: str) -> str:
    return f"{texto}\n\n{AVISO}\n{PERGUNTA_FEEDBACK}"


# ---------------------------------------------------------------
# MOCKS: cada função será trocada pela versão real
# O contrato (o que recebe e o que devolve) é o que importa manter.
# ---------------------------------------------------------------

def checar_qualidade(imagem_base64: str) -> bool:
    """Retorna True se a foto está nítida e grande o bastante."""
    return os.getenv("MOCK_FOTO_OK", "true").lower() == "true"


def classificar(imagem_base64: str) -> dict:
    """Retorna {"praga": str, "confianca": float entre 0 e 1}."""
    return {
        "praga": os.getenv("MOCK_PRAGA", "lagarta-do-cartucho"),
        "confianca": float(os.getenv("MOCK_CONFIANCA", "0.85")),
    }


FICHAS = {
    c: f"[MOCK] Ficha técnica de {c}: como reconhecer o dano e o manejo, do mais barato ao mais caro."
    for c in CLASSES
}


def buscar_ficha(praga: str) -> str:
    """Retorna o texto técnico da praga na base de conhecimento."""
    return FICHAS.get(praga, "[MOCK] Ficha não encontrada.")


def reescrever(praga: str, ficha: str) -> str:
    """O LLM reescreve a ficha em linguagem simples."""
    return f"[MOCK] {ficha}"


# ---------------------------------------------------------------
# Orquestração e roteador de confiança
# ---------------------------------------------------------------

def analisar_foto(imagem_base64: str) -> dict:
    """Devolve {"texto": str, "diagnostico": {"praga", "confianca"} ou None}."""
    if not checar_qualidade(imagem_base64):
        return {
            "texto": "A foto ficou difícil de analisar (borrada ou muito pequena). Pode tirar outra, mais de perto e com boa luz?",
            "diagnostico": None,
        }

    resultado = classificar(imagem_base64)
    praga = resultado["praga"]
    confianca = resultado["confianca"]
    logger.info("Classificação: %s (%.0%%)", praga, confianca * 100)

    # Confiança baixa: não arrisca diagnóstico
    if confianca < LIMIAR_MEDIO:
        return {
            "texto": "Não consegui identificar com segurança o que está na foto. Procure a Casa da Agricultura mais próxima para uma avaliação.",
            "diagnostico": None,
        }

    ficha = buscar_ficha(praga)
    texto = reescrever(praga, ficha)

    # Confiança média: diagnóstico com ressalva, pede outra foto
    if confianca < LIMIAR_ALTO:
        texto = f"Pode ser {praga}, mas não tenho certeza. {texto}\n\nSe puder, mande outra foto para eu confirmar."

    # Confiança média ou alta: anexa o rodapé e devolve o diagnóstico (para o feedback)
    return {
        "texto": _com_rodape(texto),
        "diagnostico": {"praga": praga, "confianca": confianca},
    }