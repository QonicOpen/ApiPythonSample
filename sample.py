from pathlib import Path
from random import randint
import time
import os
import json
from typing import Callable

import requests
from QonicApi import QonicApi
import printMethods
from QonicApiLib import ProductFilter


def wait_for_operation(api: QonicApi, operation_id: str):
    while True:
        operation = api.get_operation(operation_id)
        status = operation["status"]
        print(f"Operation {operation_id} status: {status}")
        if status in ("Ready", "Failed"):
            return operation
        time.sleep(2)


def run_product_modification(api: QonicApi, project_id: str, model_id: str, changes: dict) -> bool:
    print("Starting modification session")
    api.start_session(project_id, model_id)
    try:
        errors = api.modify_products(project_id, model_id, changes)
        if errors:
            print(errors)
            return False
    finally:
        print("Closing modification session")
        api.end_session(project_id, model_id)

    print("Modification is done")
    print()
    return True


def handle_model_queries(api: QonicApi, project_id: str):
    models = api.list_models(project_id)
    print("your models:")
    for model in models:
        print(f"{model['id']} - {model['name']}")
    print()

    model_id = input("Enter a model id: ")
    print()

    available_fields = api.get_available_product_fields(project_id, model_id)
    print("fields: " + ', '.join(available_fields[:10]) + " ...")

    print("Querying the Guid, Class, Name and FireRating fields, filtered on Class Beam...")
    print()

    fields = ["Guid", "Class", "Name", "FireRating"]
    filters: list[ProductFilter] = [{"property": "Class", "value": "Beam", "operator": "Contains"}]
    properties = api.query_products(project_id, model_id, fields=fields, filters=filters)

    print()
    for row in properties:
        print(f"{row}")

    print()
    if not properties:
        print("No beams to add a fire rating to")
        return

    current_fire_rating = properties[0]["FireRating"]
    if current_fire_rating["PropertySet"] is not None or current_fire_rating["Value"] is not None:
        print("Beam already has a fire rating a change modification needed")
        return

    fire_rating = f"F{randint(1, 200)}"
    print(f"Adding FireRating to first row  {fire_rating}")
    add_changes = {
        "add": {
            "FireRating": {
                properties[0]["Guid"]: {
                    "PropertySet": "Pset_BeamCommon",
                    "Value": fire_rating,
                }
            }
        }
    }

    if not run_product_modification(api, project_id, model_id, add_changes):
        return

    print("Querying data again")
    properties = api.query_products(project_id, model_id, fields=fields, filters=filters)

    print("Showing only the first row:")
    print(properties[0])

    print()
    print("Starting modification session to reset value")
    update_changes = {
        "update": {
            "FireRating": {
                properties[0]["Guid"]: None
            }
        }
    }

    if not run_product_modification(api, project_id, model_id, update_changes):
        return

    print("Querying data again")
    properties = api.query_products(project_id, model_id, fields=fields, filters=filters)

    print("Showing only the first row:")
    print(properties[0])

    print()
    print("Starting modification to delete property")
    delete_changes = {
        "delete": {
            "FireRating": {
                properties[0]["Guid"]: None
            }
        }
    }

    if not run_product_modification(api, project_id, model_id, delete_changes):
        return

    print("Querying data again")
    properties = api.query_products(project_id, model_id, fields=fields, filters=filters)

    if properties:
        print("Showing only the first row:")
        print(properties[0])


def handle_codifications(api: QonicApi, project_id: str):
    print("Showing first codification library")
    libraries = api.list_codification_libraries(project_id)
    if not libraries:
        print("No codification libraries found")
        return

    printMethods.printCodificationLibrary(libraries[0])

    print("Adding new TestCodificationLibrary")
    data = {
        "name": "CodificationTestLibrary",
        "description": "codification library for testing",
    }

    new_library = api.create_codification_library(project_id, data)

    library_id = new_library["guid"]

    new_code_to_add = {
        "name": "NewRootCode",
        "identification": "0",
        "description": "NewCodeForTesting",
        "parentId": None,
    }
    print("Adding new root code the library")
    new_code = api.create_classification_code(
        project_id,
        library_id,
        new_code_to_add,
    )

    print("updating the name of the new code from NewRootcode to  updatedName")
    updated_code = {
        "name": "updatedName"
    }
    api.update_classification_code(
        project_id,
        library_id,
        new_code["guid"],
        updated_code,
    )

    print("Show new library")
    newly_added_library = api.get_codification_library(project_id, library_id)
    printMethods.printCodificationLibrary(newly_added_library)

    print("Delete newly added code")
    api.delete_classification_code(
        project_id,
        library_id,
        new_code["guid"],
    )
    print("Delete new library")
    api.delete_codification_library(
        project_id,
        library_id,
    )


def handle_materials(api: QonicApi, project_id: str):
    print("Showing first material library")
    materials = api.get_material_overview(project_id)

    if not materials.get("materialProperties"):
        print("No material libraries found")
        return

    printMethods.printMaterials(materials["materialProperties"][0])

    new_library = api.create_material_library(
        project_id,
        {"Name": "TestMaterial"},
    )

    library_id = new_library["guid"]
    new_material = {
        "name": "Concrete",
        "description": "test",
        "color": "#785B3DFF",
    }
    print("Adding new material to the library")
    new_material = api.create_material(
        project_id,
        library_id,
        new_material,
    )

    updated_material = {
        "name": "Concrete",
        "description": "concrete test material",
        "color": "#49C73EFF",
    }
    new_material_id = new_material["guid"]
    api.update_material(
        project_id,
        library_id,
        new_material_id,
        updated_material,
    )
    materials = api.get_material_overview(project_id)

    printMethods.printMaterials(
        [lib for lib in materials["materialProperties"] if lib["guid"] == library_id][0]
    )

    print("Delete material again")
    api.delete_material(
        project_id,
        library_id,
        new_material_id,
    )


def handle_locations(api: QonicApi, project_id: str):
    print("Get all locations")
    locations = api.get_locations(project_id)
    for location in locations:
        printMethods.printLocations(location)
        print("-----------------------------------------")

    print("Add new site location")

    new_site = {
        "name": "NewLocation",
        "type": "Site",
        "parentGuid": None,
    }

    site = api.create_location(
        project_id,
        new_site,
    )

    guid_site = [prop for prop in site["properties"] if prop["name"] == "Guid"][0]["value"]

    print("Add new building")
    new_building = {
        "name": "NewBuilding",
        "type": "Building",
        "parentGuid": guid_site,
    }

    api.create_location(
        project_id,
        new_building,
    )

    print("Update site name to newSite")
    updated_site = {
        "name": "newSite"
    }
    api.update_location(
        project_id,
        guid_site,
        updated_site,
    )

    print("Show added locations")
    locations = api.get_locations(project_id)

    for location in locations:
        if [prop for prop in site["properties"] if prop["name"] == "Guid"][0]["value"] == guid_site:
            printMethods.printLocations(location)

    print("Delete added locations")
    api.delete_location(
        project_id,
        guid_site,
    )


def handle_custom_properties(api: QonicApi, project_id: str):
    print("Showing all custom properties")

    custom_properties = api.get_custom_properties(project_id)
    printMethods.printCustomProperties(custom_properties)

    print("Create new propertyset: TestSet")

    property_set_to_add = {
        "Name": "TestSet",
        "EntityTypes": [{"Value": "IfcWall"}, {"Value": "IfcBeam"}, {"Value": "IfcSlab"}],
    }
    added_set = api.create_property_set(
        project_id,
        property_set_to_add,
    )

    print("Add property to set: TestProperty")

    property_to_add = {
        "Name": "TestProperty",
        "DataType": "String",
    }

    api.add_property_definition(
        project_id,
        added_set["id"],
        property_to_add,
    )

    print("Choose model to add this property to")

    models = api.list_models(project_id)
    print("your models:")
    for model in models:
        print(f"{model['id']} - {model['name']}")
    print()

    model_id = input("Enter a model id: ")
    print()

    print("Querying the Guid, Class, Name fields, filtered on Class Wall...")
    print()

    fields = ["Guid", "Class", "Name"]
    filters: list[ProductFilter] = [{"property": "Class", "value": "Wall", "operator": "Contains"}]
    properties = api.query_products(project_id, model_id, fields=fields, filters=filters)

    print()
    for row in properties:
        print(f"{row}")

    print("Adding test property to first wall")
    print("  Starting modification session")
    if not properties:
        print("No walls found")
        return

    api.start_session(project_id, model_id)
    try:
        changes = {
            "add": {
                "TestProperty": {
                    properties[0]["Guid"]: {
                        "PropertySet": "TestSet",
                        "Value": "testValue",
                    }
                }
            }
        }
        errors = api.modify_products(project_id, model_id, changes)
        if errors:
            print(str(errors))
            return
    finally:
        print("Closing modification session")
        api.end_session(project_id, model_id)


def handle_delete_product(api: QonicApi, project_id: str):
    models = api.list_models(project_id)
    print("your models:")
    for model in models:
        print(f"{model['id']} - {model['name']}")
    print()

    model_id = input("Enter a model id: ")
    print()

    available_fields = api.get_available_product_fields(project_id, model_id)
    print("fields: " + ', '.join(available_fields[:10]) + " ...")
    print()

    print("Querying the Guid, Class, Name and FireRating fields, filtered on Class Beam...")
    print()

    fields = ["Guid", "Class", "Name"]
    filters: list[ProductFilter] = [{"property": "Class", "value": "Wall", "operator": "Contains"}]
    properties = api.query_products(project_id, model_id, fields=fields, filters=filters)

    initial_amount_of_walls = len(properties)
    print(f"Found {initial_amount_of_walls} walls")

    print("Deleting the first wall")

    if not properties:
        print("No walls found")
        return

    guid = properties[0]["Guid"]
    api.start_session(project_id, model_id)

    try:
        api.delete_product(project_id, model_id, guid)
    finally:
        print("Closing modification session")
        api.end_session(project_id, model_id)
    print("Modification is done")
    print()
    print("Querying data again")

    properties_after = api.query_products(project_id, model_id, fields=fields, filters=filters)
    amount_after_delete = len(properties_after)
    print(f"Found {amount_after_delete} walls")


def handle_create_model(api: QonicApi, project_id: str):
    print("Requesting upload URL")
    upload_url = api.get_upload_url()
    print("Upload URL received")
    local_path = input("Enter the path to the local model file to upload: ").strip()
    while not local_path or not os.path.isfile(local_path):
        if not local_path:
            print("No file path provided")
        if not os.path.isfile(local_path):
            print("File does not exist")

        local_path = input("Enter the path to the local model file to upload: ").strip()

    upload_file_name = os.path.basename(local_path)
    print(f"Uploading {upload_file_name} to storage")
    with open(local_path, "rb") as f:
        resp = requests.put(upload_url, data=f)
        resp.raise_for_status()
    print("Upload finished")

    model_name = upload_file_name if "." not in upload_file_name else upload_file_name.split(".")[0]
    result = api.create_model(
        project_id,
        model_name=model_name,
        upload_url=upload_url,
        upload_file_name=upload_file_name,
        discipline="Other",
    )

    print(f"Created model with id {result['modelId']}")
    print(f"Import operation id {result['id']} with status {result['status']}")
    operation = wait_for_operation(api, result["id"])
    print(f"Final import status: {operation['status']}")


def _resolve_output_path(user_input: str, model_id: str) -> Path:
    p = Path(user_input).expanduser()

    as_str = str(user_input)
    if as_str.endswith(("/", "\\")) or (p.exists() and p.is_dir()):
        p = p / f"{model_id}.ifc"

    if p.suffix == "":
        p = p / f"{model_id}.ifc"

    return p


def handle_export_model(api: "QonicApi", project_id: str) -> None:
    models = api.list_models(project_id)
    if not models:
        print("No models found")
        return

    print("your models:")
    for model in models:
        print(f"{model['id']} - {model['name']}")
    print()

    model_id = input("Enter a model id: ").strip()
    if not model_id:
        print("No model id provided")
        return

    output_raw = input(
        "Enter a directory or path to save the IFC file (e.g. ./exports/ or ./exports/export.ifc): "
    ).strip()
    if not output_raw:
        print("No output path provided")
        return

    output_path = _resolve_output_path(output_raw, model_id)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Could not create directory {output_path.parent}: {e}")
        return

    if output_path.exists():
        print(f"Output file {output_path} already exists, please remove it first")
        return

    print("Starting IFC export")
    operation = api.start_export_ifc(project_id, model_id)
    operation_id = operation["id"]
    print(f"Export operation id {operation_id}")

    final_operation = wait_for_operation(api, operation_id)
    if final_operation.get("status") != "Ready":
        print("Export operation did not complete successfully")
        return

    result_url = api.get_export_ifc_result_url(project_id, model_id, operation_id)

    print(f"Downloading IFC file to {output_path}")
    resp = requests.get(result_url, stream=True)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"IFC file saved to {output_path}")


def handle_calculate_quantities(api: QonicApi, project_id: str):
    models = api.list_models(project_id)
    if not models:
        print("No models found")
        return

    print("your models:")
    for model in models:
        print(f"{model['id']} - {model['name']}")
    print()

    model_id = input("Enter a model id: ")
    print()

    print("Starting quantity calculation of 'Length' and 'GrossArea' for all products with class 'Wall'")
    filters: list[ProductFilter] = [{"property": "Class", "value": "Wall", "operator": "Contains"}]
    operation = api.calculate_quantities(
        project_id,
        model_id,
        calculators=["Length", "GrossArea"],
        filters=filters
    )
    operation_id = operation["id"]
    print(f"Quantities operation id {operation_id}")

    final_operation = wait_for_operation(api, operation_id)
    if final_operation["status"] != "Ready":
        print("Quantities operation did not complete successfully")
        return

    result_url = api.get_quantities_result_url(project_id, model_id, operation_id)
    print("Downloading quantities result")
    resp = requests.get(result_url)
    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError:
        print("Result is not valid JSON, raw response below:")
        print(resp.text)
        return

    print("Quantities result:")
    print(json.dumps(data, indent=2))

def _choose_project(projects: list[dict]) -> str | None:
    if not projects:
        print("No projects found.")
        return None

    print("your projects:")
    for p in projects:
        print(f"{p['id']} - {p['name']}")
    print()

    valid_ids = {str(p["id"]) for p in projects}

    while True:
        pid = input("Enter a project id (or blank to exit): ").strip()
        if not pid:
            return None
        if pid in valid_ids:
            return pid
        print("Invalid project id. Please pick one from the list.\n")

def _choose_action(actions: dict[str, tuple[str, Callable[[], None]]]) -> str:
    print("Choose what to do next:")
    for key, (label, _) in actions.items():
        print(f"{key}: {label}")

    return input(f"Enter choice ({', '.join(actions.keys())}): ").strip()

def main() -> None:
    api = QonicApi()
    api.authorize()

    project_id = _choose_project(api.list_projects())
    if not project_id:
        return

    actions: dict[str, tuple[str, Callable[[], None]]] = {
        "1": ("Model Queries", lambda: handle_model_queries(api, project_id)),
        "2": ("Codifications", lambda: handle_codifications(api, project_id)),
        "3": ("Materials", lambda: handle_materials(api, project_id)),
        "4": ("Locations", lambda: handle_locations(api, project_id)),
        "5": ("CustomProperties", lambda: handle_custom_properties(api, project_id)),
        "6": ("Delete Product", lambda: handle_delete_product(api, project_id)),
        "7": ("Create model", lambda: handle_create_model(api, project_id)),
        "8": ("Export model", lambda: handle_export_model(api, project_id)),
        "9": ("Calculate quantities", lambda: handle_calculate_quantities(api, project_id)),
        "10": ("Exit", lambda: exit()),
    }

    try:
        while True:
            print()
            choice = _choose_action(actions)
            if choice not in actions:
                print("Please choose a valid option.\n")
                continue

            _, action = actions[choice]
            action()

    except (KeyboardInterrupt, EOFError):
        print("\nExiting...")


if __name__ == "__main__":
    main()
