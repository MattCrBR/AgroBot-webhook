import os

# Limiares do roteador de confiança
LIMIAR_ALTO = 0.80
LIMIAR_MEDIO = 0.50

CLASSES = ["lagarta-do-cartucho", "lagarta-da-espiga", "vaquinha", "milho-saudavel"]

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


FICHAS = {c: f"[MOCK] Ficha técnica de {c}: como reconhecer o dano e o manejo, do mais barato ao mais caro." for c in CLASSES}


def buscar_ficha(praga: str) -> str:
    """Retorna o texto técnico da praga na base de conhecimento."""
    return FICHAS.get(praga, "[MOCK] Ficha não encontrada.")


def reescrever(praga: str, ficha: str) -> str:
    """O LLM reescreve a ficha em linguagem simples."""
    return f"[MOCK] {ficha}"


# ---------------------------------------------------------------
# Orquestração e roteador de confiança
# ---------------------------------------------------------------

def analisar_foto(imagem_base64: str) -> str:
    """Recebe a foto e devolve o texto final que será enviado ao produtor."""
    if not checar_qualidade(imagem_base64):
        return "A foto ficou difícil de analisar (borrada ou muito pequena). Pode tirar outra, mais de perto e com boa luz?"

    resultado = classificar(imagem_base64)
    praga = resultado["praga"]
    confianca = resultado["confianca"]
    print(f"Classificação: {praga} ({confianca:.0%})")

    # Confiança baixa: não arrisca diagnóstico
    if confianca < LIMIAR_MEDIO:
        return "Não consegui identificar com segurança o que está na foto. Procure a Casa da Agricultura mais próxima para uma avaliação."

    ficha = buscar_ficha(praga)
    texto = reescrever(praga, ficha)

    # Confiança média: diagnóstico com ressalva, pede outra foto
    if confianca < LIMIAR_ALTO:
        return f"Pode ser {praga}, mas não tenho certeza. {texto}\n\nSe puder, mande outra foto para eu confirmar."

    # Confiança alta
    return texto