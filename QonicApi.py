import os
import uuid
from typing import Dict, List, Optional, Any, Iterable
import requests
from oauth import login


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


class QonicApi:
    def __init__(self):
        self.base_url = os.getenv("QONIC_API_URL", "https://api.qonic.com/v1/").rstrip("/") + "/"
        self.session = requests.Session()
        self.session_id = self.new_session_id()
        self.access_token = None

    def _url(self, path: str) -> str:
        path = path.lstrip("/")
        return self.base_url + path

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "X-Client-Session-Id": self.session_id
        }

    def _request(
            self,
            method: str,
            path: str,
            *,
            params: Dict[str, Any] | None = None,
            json: Any = None,
            data: Any = None,
            allow_redirects: bool = True,
    ) -> requests.Response:
        url = self._url(path)
        resp = self.session.request(
            method,
            url,
            params=params,
            json=json,
            data=data,
            headers=self._headers(),
            allow_redirects=allow_redirects,
        )
        if not resp.ok:
            raise QonicApiError(resp)
        return resp

    def get(self, path: str, **kwargs) -> Any:
        resp = self._request("GET", path, **kwargs)
        return resp.json()

    def _post(self, path: str, **kwargs) -> Any:
        resp = self._request("POST", path, **kwargs)
        if resp.content:
            try:
                return resp.json()
            except ValueError:
                return resp.text
        return None

    def _delete(self, path: str, **kwargs) -> Any:
        resp = self._request("DELETE", path, **kwargs)
        if resp.content:
            try:
                return resp.json()
            except ValueError:
                return resp.text
        return None

    def _put(self, path: str, **kwargs) -> Any:
        resp = self._request("PUT", path, **kwargs)
        if resp.content:
            try:
                return resp.json()
            except ValueError:
                return resp.text
        return None

    def authorize(self):
        self.access_token = login()["access_token"]

    def list_projects(self) -> List[Any]:
        return self.get("projects").get("projects", [])

    def list_models(self, project_id: str) -> List[Any]:
        return self.get(f"projects/{project_id}/models").get("models", [])

    def get_available_product_fields(self, project_id: str, model_id: str) -> List[str]:
        return self.get(f"projects/{project_id}/models/{model_id}/products/available-data").get("fields", [])

    def query_products(
            self,
            project_id: str,
            model_id: str,
            fields: Iterable[str],
            filters: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        body = {
            "fields": list(fields),
            "filters": filters or {},
        }
        return self._post(f"projects/{project_id}/models/{model_id}/products/query", json=body).get("result", {})

    def calculate_quantities(self, project_id: str, model_id: str, calculators: Iterable[str],
                             filters: Dict[str, Any] | None = None) -> Dict[str, Any]:
        body = {
            "calculators": list(calculators),
            "filters": filters or {},
        }
        return self._post(f"projects/{project_id}/models/{model_id}/quantities", json=body)

    def get_quantities_result_url(self, project_id: str, model_id: str, operation_id: str) -> str:
        resp = self._request(
            "GET",
            f"projects/{project_id}/models/{model_id}/quantities/{operation_id}/result",
            allow_redirects=False,
        )
        location = resp.headers.get("Location")
        if not location:
            raise QonicApiError(resp)
        return location

    def get_operation(self, operation_id: str) -> Dict[str, Any]:
        return self.get(f"operations/{operation_id}")

    @staticmethod
    def new_session_id() -> str:
        return str(uuid.uuid4())

    def start_session(self, project_id: str, model_id: str) -> None:
        self.session_id = self.new_session_id()
        self._post(f"projects/{project_id}/models/{model_id}/start-session")

    def end_session(self, project_id: str, model_id: str) -> None:
        self._post(f"projects/{project_id}/models/{model_id}/end-session")

    def modify_products(self, project_id: str, model_id: str, changes: Dict[str, Any]) -> List[ModificationInputError]:
        result = self._post(
            f"projects/{project_id}/models/{model_id}/products",
            json=changes,

        )
        errors_json = result.get("errors", []) if isinstance(result, dict) else []
        return [ModificationInputError(**e) for e in errors_json]

    def delete_product(self, project_id: str, model_id: str, guid: str) -> None:
        self._delete(f"projects/{project_id}/models/{model_id}/products/{guid}")

    def publish_changes(self, project_id: str, title: Optional[str] = None, description: Optional[str] = None) -> None:
        body = {
            "title": title,
            "description": description,
        }
        self._post(f"projects/{project_id}//publish", json=body)

    def discard_changes(self, project_id: str) -> None:
        self._post(f"projects/{project_id}/discard")

    def get_upload_url(self) -> str:
        data = self.get("upload-url")
        return data["uploadUrl"]

    def create_model(
            self,
            project_id: str,
            *,
            model_name: str,
            upload_url: str,
            upload_file_name: str,
            discipline: str,
            default_role: Optional[str] = None,
    ) -> Dict[str, Any]:
        body = {
            "modelName": model_name,
            "uploadUrl": upload_url,
            "uploadFileName": upload_file_name,
            "discipline": discipline,
        }
        if default_role is not None:
            body["defaultRole"] = default_role

        return self._post(f"projects/{project_id}/models", json=body)

    def start_export_ifc(self, project_id: str, model_id: str) -> Dict[str, Any]:
        return self._post(f"projects/{project_id}/models/{model_id}/export-ifc")

    def get_export_ifc_result_url(self, project_id: str, model_id: str, operation_id: str) -> str:
        resp = self._request(
            "GET",
            f"projects/{project_id}/models/{model_id}/export-ifc/{operation_id}/result",
            allow_redirects=False,
        )
        location = resp.headers.get("Location")
        if not location:
            raise QonicApiError(resp)
        return location

    def list_codification_libraries(self, project_id: str) -> List[Dict[str, Any]]:
        data = self.get(f"projects/{project_id}/codifications")
        return data.get("codificationLibraries", []) if isinstance(data, dict) else []

    def create_codification_library(self, project_id: str, library_properties: Dict[str, Any]) -> Dict[str, Any]:
        result = self._post(f"projects/{project_id}/codifications", json=library_properties)
        return result if isinstance(result, dict) else {}

    def get_codification_library(self, project_id: str, library_guid: str) -> Dict[str, Any]:
        data = self.get(f"projects/{project_id}/codifications/{library_guid}")
        return data if isinstance(data, dict) else {}

    def delete_codification_library(self, project_id: str, library_guid: str) -> None:
        self._delete(f"projects/{project_id}/codifications/{library_guid}")

    def create_classification_code(self, project_id: str, library_guid: str, code: Dict[str, Any]) -> Dict[str, Any]:
        result = self._post(f"projects/{project_id}/codifications/{library_guid}/codification", json=code)
        return result if isinstance(result, dict) else {}

    def update_classification_code(self, project_id: str, library_guid: str, codification_guid: str,
                                   changes: Dict[str, Any]) -> None:
        self._put(f"projects/{project_id}/codifications/{library_guid}/codification/{codification_guid}",
                  json=changes, )

    def delete_classification_code(self, project_id: str, library_guid: str, codification_guid: str) -> None:
        self._delete(f"projects/{project_id}/codifications/{library_guid}/codification/{codification_guid}")

    def get_custom_properties(self, project_id: str) -> Dict[str, Any]:
        data = self.get(f"projects/{project_id}/customProperties")
        return data if isinstance(data, dict) else {}

    def create_property_set(self, project_id: str, property_set: Dict[str, Any]) -> Dict[str, Any]:
        result = self._post(f"projects/{project_id}/customProperties/property-sets", json=property_set)
        return result if isinstance(result, dict) else {}

    def update_property_set(self, project_id: str, property_set_id: int | str, changes: Dict[str, Any]) -> None:
        self._put(f"projects/{project_id}/customProperties/property-sets/{property_set_id}", json=changes)

    def delete_property_set(self, project_id: str, property_set_id: int | str) -> None:
        self._delete(f"projects/{project_id}/customProperties/property-sets/{property_set_id}")

    def add_property_definition(self, project_id: str, property_set_id: int | str, definition: Dict[str, Any]) -> Dict[str, Any]:
        result = self._post(f"projects/{project_id}/customProperties/property-sets/{property_set_id}/property",
                            json=definition)
        return result if isinstance(result, dict) else {}

    def update_property_definition(self, project_id: str, property_set_id: int | str, property_definition_id: int | str,
                                   changes: Dict[str, Any]) -> Dict[str, Any]:
        result = self._put(
            f"projects/{project_id}/customProperties/property-sets/{property_set_id}/property/{property_definition_id}",
            json=changes)
        return result if isinstance(result, dict) else {}

    def delete_property_definition(self, project_id: str, property_set_id: int | str,
                                   property_definition_id: int | str) -> None:
        self._delete(
            f"projects/{project_id}/customProperties/property-sets/{property_set_id}/property/{property_definition_id}")

    def get_material_overview(self, project_id: str) -> Dict[str, Any]:
        data = self.get(f"projects/{project_id}/material-libraries")
        return data if isinstance(data, dict) else {}

    def get_material_library(self, project_id: str, library_guid: str) -> Dict[str, Any]:
        data = self.get(f"projects/{project_id}/material-libraries/{library_guid}")
        return data if isinstance(data, dict) else {}

    def create_material(self, project_id: str, library_guid: str, material: Dict[str, Any], ) -> Dict[str, Any]:
        result = self._post(f"projects/{project_id}/material-libraries/{library_guid}/materials", json=material)
        return result if isinstance(result, dict) else {}

    def update_material(self, project_id: str, material_guid: str, material: Dict[str, Any], ) -> None:
        self._put(f"projects/{project_id}/material-libraries/{material_guid}/materials/{material_guid}", json=material)

    def delete_material(self, project_id: str, library_guid: str, material_guid: str) -> None:
        self._delete(f"projects/{project_id}/material-libraries/{library_guid}/materials/{material_guid}")

    def create_material_library(self, project_id: str, library_properties: Dict[str, Any]) -> Dict[str, Any]:
        result = self._post(f"projects/{project_id}/material-libraries", json=library_properties)
        return result if isinstance(result, dict) else {}

    def delete_material_library(self, project_id: str, library_guid: str) -> None:
        self._delete(f"projects/{project_id}/material-libraries/{library_guid}")

    def get_locations(self, project_id: str) -> List[Dict[str, Any]]:
        data = self.get(f"projects/{project_id}/locations")
        if isinstance(data, dict):
            return data.get("locationViews", [])
        return []

    def create_location(self, project_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        result = self._post(f"projects/{project_id}/locations", json=properties)
        return result if isinstance(result, dict) else {}

    def update_location(self, project_id: str, location_guid: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        result = self._put(f"projects/{project_id}/locations/{location_guid}", json=properties)
        return result if isinstance(result, dict) else {}

    def delete_location(self, project_id: str, location_guid: str) -> None:
        self._delete(f"projects/{project_id}/locations/{location_guid}")

    def get_types(self, project_id: str) -> Dict[str, Any]:
        data = self.get(f"projects/{project_id}/types")
        return data if isinstance(data, dict) else {}

    def create_type(self, project_id: str, library_guid: str, type_item: Dict[str, Any]) -> Dict[str, Any]:
        result = self._post(f"projects/{project_id}/types/{library_guid}", json=type_item)
        return result if isinstance(result, dict) else {}

    def update_type(self, project_id: str, library_guid: str, type_guid: str, changes: Dict[str, Any]) -> None:
        self._put(f"projects/{project_id}/types/{library_guid}/types/{type_guid}", json=changes)

    def delete_type(self, project_id: str, library_guid: str, type_guid: str) -> None:
        self._delete(f"projects/{project_id}/types/{library_guid}/types/{type_guid}")
