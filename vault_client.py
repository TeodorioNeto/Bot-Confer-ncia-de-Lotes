"""
vault_client.py - acesso à credencial do "ERP" via Credentials Vault.
A senha nunca aparece em log nem em print daqui pra frente.
"""

import logging
from config import CREDENCIAL_LABEL

logger = logging.getLogger(__name__)


def obter_credencial_erp(maestro):
    """
    Busca usuário e senha da credencial do ERP no Maestro Vault.

    Returns:
        tuple (usuario, senha)
    """
    usuario = maestro.get_credential(label=CREDENCIAL_LABEL, key="usuario")
    senha = maestro.get_credential(label=CREDENCIAL_LABEL, key="senha")

    logger.info("Acessando sistema com o usuário: %s", usuario)
    # a senha NUNCA é logada, de propósito

    return usuario, senha