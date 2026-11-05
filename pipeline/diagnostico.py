"""Orquestra o pipeline de diagnostico (ver docs/02-arquitetura.md secao 2):
porteiro de qualidade -> CNN -> roteador de confianca -> resposta.

Roda SINCRONO dentro do proprio request da API por enquanto — sem LLM na
jogada, a inferencia inteira leva poucos milissegundos (medido: ~2ms),
bem abaixo do limite de 1s que preocupa o webhook. Quando entrar o LLM
(chamada de rede externa, 3-15s), isto precisa virar job de fila
(Redis/RQ) pra nao travar o webhook — nao antes disso."""

from PIL import Image

from pipeline import porteiro
from pipeline.modelo import classificar
from pipeline.resposta import montar_resposta


def diagnosticar(imagem: Image.Image) -> str:
    ok, motivo = porteiro.verificar(imagem)
    if not ok:
        return porteiro.MENSAGEM_POR_MOTIVO[motivo]

    classe, confianca = classificar(imagem)
    return montar_resposta(classe, confianca)
