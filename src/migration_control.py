"""Coexistencia segura entre o fluxo legado e o pipeline novo."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


VALID_MODES = {"legado", "shadow", "novo"}


@dataclass(frozen=True)
class ExecutionClaim:
    allowed: bool
    official: bool
    mode: str
    business_key: str
    reason: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class DesktopSessionBusyError(RuntimeError):
    """Outra automacao ja possui a sessao grafica dedicada."""


class MigrationController:
    def __init__(self, state_dir, mode: str):
        self.state_dir = Path(state_dir)
        self.mode = str(mode).strip().lower()
        if self.mode not in VALID_MODES:
            raise ValueError(
                "ORCHESTRATOR_MODE deve ser 'legado', 'shadow' ou 'novo'"
            )

    def claim_execution(self, business_key: str, pipeline_id: str) -> ExecutionClaim:
        """Reserva uma execucao oficial; shadow nao disputa a saida oficial."""
        business_key = str(business_key).strip()
        if not business_key:
            raise ValueError("business_key e obrigatoria")
        if self.mode == "legado":
            return ExecutionClaim(
                allowed=False,
                official=False,
                mode=self.mode,
                business_key=business_key,
                reason="pipeline_novo_inativo",
            )
        if self.mode == "shadow":
            return ExecutionClaim(
                allowed=True,
                official=False,
                mode=self.mode,
                business_key=business_key,
            )

        self.state_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(business_key.encode("utf-8")).hexdigest()[:24]
        marker = self.state_dir / f"official_{digest}.json"
        payload = {
            "business_key": business_key,
            "pipeline_id": pipeline_id,
            "mode": self.mode,
            "claimed_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return ExecutionClaim(
                allowed=False,
                official=True,
                mode=self.mode,
                business_key=business_key,
                reason="execucao_oficial_duplicada",
            )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
        return ExecutionClaim(
            allowed=True,
            official=True,
            mode=self.mode,
            business_key=business_key,
        )

    @contextmanager
    def desktop_session(self, pipeline_id: str):
        """Implementa mutex de arquivo para a sessao grafica do Runner."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        lock_path = self.state_dir / "desktop_session.lock"
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            raise DesktopSessionBusyError(
                "Sessao desktop ocupada por outra automacao"
            ) from error

        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(
                        {
                            "pipeline_id": pipeline_id,
                            "locked_at": datetime.now(timezone.utc).isoformat(),
                        },
                        ensure_ascii=False,
                    )
                )
            yield lock_path
        finally:
            lock_path.unlink(missing_ok=True)

