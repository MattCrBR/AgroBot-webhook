"""Monta a resposta final.

docs/02-arquitetura.md secao 5: um LLM so REDIGE, a partir do trecho
recuperado, num template fixo de ~90 palavras — nunca decide a praga,
nunca inventa produto. Ver pipeline/llm.py pro prompt e as regras.

O LLM (Claude Haiku 4.5) so entra nos casos com conteudo tecnico de
verdade pra resumir — rota "direto" e "duvida" com praga identificada.
Os casos triviais (porteiro reprovou, rota "humano", milho_sadio) ficam
com resposta fixa aqui mesmo, sem custo de API nem risco de alucinacao
onde nao precisa. Se a chamada ao LLM falhar (rede, chave invalida), cai
pra uma versao mecanica extraida direto da ficha — o produtor sempre
recebe alguma resposta."""

import logging
import re

from pipeline import kb, llm
from pipeline.roteador import decidir_rota

logger = logging.getLogger(__name__)


def _primeiro_item_numerado(texto: str) -> str:
    """Pega o texto do item '1.' de uma lista numerada em markdown e
    limpa negrito/quebra de linha — usado pra extrair 'o primeiro sinal'
    e 'a primeira medida' sem precisar resumir com LLM."""
    m = re.search(r"1\.\s+(.+?)(?:\n\d+\.|\Z)", texto, re.DOTALL)
    trecho = m.group(1) if m else texto
    trecho = re.sub(r"\*\*(.+?)\*\*", r"\1", trecho)
    trecho = re.sub(r"\s+", " ", trecho).strip()
    return trecho


def _nome_curto(ficha: dict) -> str:
    """A ficha as vezes junta dois nomes na mesma frase (ex.: 'Vaquinha
    (o besouro adulto), larva-alfinete (a larva no solo)') — pega so o
    primeiro, sem negrito nem parenteses."""
    nome = ficha.get("nome_popular", "").split("\n")[0]
    nome = re.sub(r"\*\*(.+?)\*\*", r"\1", nome)
    primeira_frase = nome.split(".")[0]
    primeiro_nome = primeira_frase.split(",")[0]
    primeiro_nome = re.sub(r"\(.+?\)", "", primeiro_nome)
    return primeiro_nome.strip()


def montar_resposta(classe: str, confianca: float) -> str:
    rota = decidir_rota(confianca)
    pct = int(round(confianca * 100))

    if rota == "humano":
        return (
            "😕 Não consegui identificar essa foto com segurança.\n\n"
            "Melhor levar uma folha ou uma foto bem nítida na Casa da "
            "Agricultura / CATI mais perto de você."
        )

    if classe == "milho_sadio":
        if rota == "direto":
            return (
                f"🌽 Não vi sinal de praga nessa planta ({pct}% de confiança). "
                "Parece saudável!\n\n"
                "Se notar folha raspada, furada ou planta murchando, manda outra foto."
            )
        return (
            f"🌽 Parece que está saudável ({pct}% de confiança), mas não tenho certeza.\n\n"
            "Consegue tirar outra foto mais de perto da folha?"
        )

    ficha = kb.buscar_ficha(classe)
    if ficha is None:
        return (
            "Identifiquei algo na foto, mas não achei a ficha de manejo "
            "dessa praga na nossa base. Avisa o time do projeto."
        )

    nome = _nome_curto(ficha)

    try:
        return llm.redigir(
            classe_nome=nome,
            confianca_pct=pct,
            rota=rota,
            como_reconhecer_o_dano=ficha.get("como_reconhecer_o_dano", ""),
            manejo_ordenado_por_custo=ficha.get("manejo_ordenado_por_custo", ""),
        )
    except Exception:
        logger.exception("Falha ao chamar o LLM — caindo pra resposta mecanica")
        return _resposta_mecanica(nome, pct, rota, ficha)


def _resposta_mecanica(nome: str, pct: int, rota: str, ficha: dict) -> str:
    """Fallback sem LLM — usado so se a chamada ao Claude falhar (rede,
    chave invalida, limite de taxa). Garante que o produtor sempre recebe
    alguma resposta, mesmo com a API fora do ar."""
    dano = _primeiro_item_numerado(ficha.get("como_reconhecer_o_dano", ""))
    manejo = _primeiro_item_numerado(ficha.get("manejo_ordenado_por_custo", ""))

    if rota == "direto":
        return (
            f"🐛 Parece {nome.upper()} no milho ({pct}% de confiança).\n\n"
            f"O que ela faz: {dano}\n\n"
            "O que fazer, começando pelo mais barato:\n"
            f"1. {manejo}\n"
            "2. Se estiver tomando conta, leve uma folha na Casa da Agricultura."
            + llm.RODAPE_FIXO
        )

    # rota == "duvida"
    return (
        f"🤔 Pode ser {nome.upper()} ({pct}% de confiança), mas não tenho certeza.\n\n"
        f"Sinal pra confirmar: {dano}\n\n"
        "Consegue tirar outra foto bem em cima da folha ou do bicho, com boa luz?"
    )
