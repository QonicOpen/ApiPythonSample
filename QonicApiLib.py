from typing import TypedDict, Any

import requests


class QonicApiError(Exception):
    def __init__(self, response: requests.Response):
        self.response = response
        try:
            self.data = response.json()
        except ValueError:
            self.data = None

        message = f"{response.status_code} {response.reason}"
        if isinstance(self.data, dict):
            details = self.data.get("errorDetails") or self.data.get("detail")
            code = self.data.get("error") or self.data.get("type")
            parts = [message]
            if code:
                parts.append(str(code))
            if details:
                parts.append(str(details))
            message = " - ".join(parts)

        super().__init__(message)


class ModificationInputError:
    def __init__(self, guid: str, field: str, error: str, description: str):
        self.guid = guid
        self.field = field
        self.error = error
        self.description = description

    def __str__(self) -> str:
        return f"{self.guid}: {self.field}: {self.error}: {self.description}"

    __repr__ = __str__

class ProductFilter(TypedDict):
    property: str
    value: Any
    operator: str
