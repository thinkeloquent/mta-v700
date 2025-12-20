from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

@dataclass
class VaultHeader:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VaultHeader':
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            version=data.get("version", "1.0"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
        )

@dataclass
class VaultMetadata:
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"data": self.data}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VaultMetadata':
        return cls(data=data.get("data", {}))

@dataclass
class VaultPayload:
    content: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {"content": self.content}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VaultPayload':
        return cls(content=data.get("content"))

@dataclass
class LoadResult:
    files_loaded: list[str] = field(default_factory=list)
    errors: list[Dict[str, Any]] = field(default_factory=list)
    total_vars_loaded: int = 0
