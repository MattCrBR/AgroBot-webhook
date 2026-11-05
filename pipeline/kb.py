"""Busca estruturada na base de conhecimento (kb/fichas-pragas-milho.md).

Ver docs/02-arquitetura.md secao 4: "o RAG nao escolhe a praga — a CNN ja
escolheu. Entao a recuperacao e' primeiro um filtro estruturado por
praga_id... com corpus desse tamanho, o filtro faz 90% do trabalho".
Por isso isto e' so um parser de markdown, sem embeddings nem Postgres —
a busca vetorial (pra pergunta livre do produtor, tipo "posso usar sabao?")
fica pra quando o LLM entrar."""

import re
from pathlib import Path

CAMINHO_KB = Path(__file__).resolve().parent.parent / "kb" / "fichas-pragas-milho.md"

# classe do classificador -> nome da secao "# N. NOME" na KB
PRAGA_ID_PARA_SECAO = {
    "lagarta_cartucho": "LAGARTA-DO-CARTUCHO",
    "lagarta_espiga": "LAGARTA-DA-ESPIGA",
    "vaquinha": "VAQUINHA / LARVA-ALFINETE",
    "lagarta_elasmo": "LAGARTA-ELASMO / BROCA-DO-COLO",
}

_cache: dict[str, dict[str, str]] | None = None


def _carregar_secoes(texto: str) -> dict[str, dict[str, str]]:
    secoes = {}
    for parte in re.split(r"^# \d+\.\s*", texto, flags=re.MULTILINE)[1:]:
        nome, _, resto = parte.partition("\n")
        campos = {}
        for bloco in re.split(r"^## ", resto, flags=re.MULTILINE)[1:]:
            campo, _, conteudo = bloco.partition("\n")
            campos[campo.strip()] = conteudo.strip()
        secoes[nome.strip()] = campos
    return secoes


def buscar_ficha(praga_id: str) -> dict[str, str] | None:
    """Devolve os campos da ficha (nome_popular, como_reconhecer_o_dano,
    manejo_ordenado_por_custo, quando_encaminhar_para_tecnico, ...) ou
    None se a classe nao tem ficha (ex.: milho_sadio, que nao e' praga)."""
    global _cache
    if _cache is None:
        _cache = _carregar_secoes(CAMINHO_KB.read_text(encoding="utf-8"))
    nome_secao = PRAGA_ID_PARA_SECAO.get(praga_id)
    if not nome_secao:
        return None
    return _cache.get(nome_secao)
