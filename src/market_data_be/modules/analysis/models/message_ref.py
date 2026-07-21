"""Stdlib MessageRef value object for analysis narrative facts."""

from dataclasses import dataclass

MessageParamValue = str | int | float | bool


@dataclass(frozen=True, slots=True)
class MessageRef:
    code: str
    params: tuple[tuple[str, MessageParamValue], ...] = ()
    severity: str | None = None
    channel: str | None = None

    @classmethod
    def of(
        cls,
        code: str,
        *,
        severity: str | None = None,
        channel: str | None = None,
        **params: MessageParamValue,
    ) -> "MessageRef":
        return cls(
            code=code,
            params=tuple(params.items()),
            severity=severity,
            channel=channel,
        )
