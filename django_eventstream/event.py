from dataclasses import dataclass, field
from typing import Optional, Dict
import re
import six
import warnings


@dataclass
class Event:
    channel: str = ""
    type: str = "message"
    data: Dict = field(default_factory=dict)
    id: Optional[int] = None
    retry: Optional[int] = None

    # Regex pattern for parsing SSE lines
    sse_line_pattern: re.Pattern = field(
        init=False, default=re.compile(r"(?P<name>[^:]*):?( ?(?P<value>.*))?")
    )

    def __str__(self):
        return f"Event(channel={self.channel}, type={self.type}, data={self.data}, id={self.id}, retry={self.retry})"

    @classmethod
    def parse(cls, raw: str) -> "Event":
        """
        Given a possibly-multiline string representing an SSE message, parse it
        and return an Event object.
        """
        msg = cls()
        for line in raw.splitlines():
            m = cls.sse_line_pattern.match(line)
            if m is None:
                # Malformed line. Discard but warn.
                warnings.warn(f'Invalid SSE line: "{line}"', SyntaxWarning)
                continue

            name = m.group("name")
            if name == "":
                # line began with a ":", so is a comment. Ignore
                continue
            value = m.group("value")

            if name == "data":
                # If we already have some data, then join to it with a newline.
                # Else this is it.
                if "data" in msg.data:
                    msg.data["data"] += f"\n{value}"
                else:
                    msg.data["data"] = value
            elif name == "event":
                msg.type = value
            elif name == "id":
                msg.id = value
            elif name == "retry":
                msg.retry = int(value)

        return msg

    def dump(self) -> str:
        """
        Convert the Event object back to a string format suitable for SSE transmission.
        """
        lines = []
        if self.id is not None:
            lines.append(f"id: {self.id}")

        if self.type != "message":
            lines.append(f"event: {self.type}")

        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        lines.extend(f"data: {line}" for line in self.data["data"].splitlines())
        return "\n".join(lines) + "\n\n"
