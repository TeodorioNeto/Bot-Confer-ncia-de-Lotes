"""Excecoes que distinguem falha de dado de falha de infraestrutura."""


class ItemValidationError(ValueError):
    """O item nao pode ser processado sem correcao do dado de entrada."""


class InfrastructureError(RuntimeError):
    """Um recurso externo ou de automacao ficou indisponivel."""

