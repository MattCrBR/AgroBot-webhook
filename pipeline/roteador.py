"""Roteador de confianca — o componente mais importante do sistema (ver
docs/02-arquitetura.md secao 3.3). Os erros aqui nao custam a mesma coisa:
dizer "e' X" quando e' Y faz o produtor gastar dinheiro e ainda perder a
lavoura; dizer "nao sei" so custa uma ida a Casa da Agricultura. Por isso
o sistema e' conservador de proposito.

Limiares vindos do doc de arquitetura — ajustar pela curva de
precisao/revocacao no conjunto de validacao quando tivermos mais dado,
nao no chute."""

ALTA = 0.80
MEDIA = 0.50


def decidir_rota(confianca: float) -> str:
    if confianca >= ALTA:
        return "direto"
    if confianca >= MEDIA:
        return "duvida"
    return "humano"
