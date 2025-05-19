from datetime import datetime
from typing import List, Dict, Optional, Any, Union

Part = Union[str, Dict[str, Any], bytes]

TASK_STATUS = ["queued", "in-progress", "completed", "failed", "input-required"]

class Message:
    def __init__(self, role: str, content: Part, created_at: Optional[str] = None):
        self.role = role
        self.content = content
        self.created_at = created_at or datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            role=data["role"],
            content=data["content"],
            created_at=data.get("created_at")
        )

class Task:
    def __init__(
            self,
            id: str,
            input: Optional[Dict[str, Any]] = None,
            output: Optional[Dict[str, Any]] = None,
            status: str = "queued",
            messages: Optional[List[Message]] = None,
            error: Optional[Dict[str, str]] = None,
            created_at: Optional[str] = None,
            modified_at: Optional[str] = None,
            requires_input: Optional[bool] = False,
            metadata: Optional[Dict[str, Any]] = None,
    ):
        if status not in TASK_STATUS:
            raise ValueError(f"Invalid task status: {status}")
        self.id = id
        self.input = input
        self.output = output
        self.status = status
        self.messages = messages or []
        self.error = error
        self.requires_input = requires_input
        self.metadata = metadata or {}
        now = datetime.now().isoformat()
        self.created_at = created_at or now
        self.modified_at = modified_at or now

    def to_dict(self):
        return {
            "id": self.id,
            "input": self.input,
            "output": self.output,
            "status": self.status,
            "messages": [m.to_dict() for m in self.messages],
            "error": self.error,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "requires_input": self.requires_input,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(
            id=data["id"],
            input=data.get("input"),
            output=data.get("output"),
            status=data.get("status", "queued"),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            error=data.get("error"),
            created_at=data.get("created_at"),
            modified_at=data.get("modified_at"),
            requires_input=data.get("requires_input", False),
            metadata=data.get("metadata", {})
        )

    def complete(self, output: Dict[str, Any]):
        self.output = output
        self.status = "completed"
        self.modified_at = datetime.now().isoformat()

    def fail(self, error_message: str, code: str = "ERROR"):
        self.status = "failed"
        self.error = {
            "message": error_message,
            "code": code
        }
        self.modified_at = datetime.now().isoformat()
