from random import randint
import requests
import re
import uuid
from oauth import login
import printMethods

apiUrl = "https://develop-api.qonic.com/v1/"

tokenResponse = login(
    issuer="https://develop-qonic.eu.auth0.com",
    client_id="dHXtN1ta43D9KKoOFGKXYWdBobBvACvW",
    redirect_uri="http://localhost:34362",
    scope="openid profile email",
    audience="https://develop-api.qonic.com")

class ModificationInputError:
    def __init__(self, guid, field, error, description):
        self.guid = guid
        self.field = field
        self.error = error
        self.description = description
    def __str__(self):
        return f"{self.guid}: {self.field}: {self.error}: {self.description}"
    def __repr__(self):
        return f"{self.guid}: {self.field}: {self.error}: {self.description}"

class ApiError:
    def __init__(self, Error, ErrorDetails):
        self.error = Error
        self.details = ErrorDetails
    def __str__(self):
        return f"{self.error}: {self.details}"
    def __repr__(self):
        return f"{self.error}: {self.details}"

def handleErrorResponse(response: requests.Response):
    try:
        apiError = ApiError(**response.json())
        print(apiError)
    except Exception as err:
        print(f"Error occurred while processing error response: {err}")

def sendGetRequest(path, params=None):
    try:
        response = requests.get(f"{apiUrl}{path}", params=params,  headers={"Authorization": f"Bearer {tokenResponse.access_token}"})
        response.raise_for_status()
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        handleErrorResponse(response)
        exit()
    except Exception as err:
        print(f"Other error occurred: {err}")
        exit()
    return response.json()

def sendPostRequest(path, data=None, json=None, params=None, sessionId=str):
    try:
        response = requests.post(f"{apiUrl}{path}", data=data, json=json, params=params,  headers={"Authorization": f"Bearer {tokenResponse.access_token}", "X-Client-Session-Id": sessionId})
        response.raise_for_status()
        return response
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        handleErrorResponse(response)
        exit()
    except Exception as err:
        print(f"Other error occurred: {err}")
        exit()

def sendDeleteRequest(path, data=None, json=None, params=None, sessionId=str):
    try:
        response = requests.delete(f"{apiUrl}{path}", data=data, json=json, params=params,  headers={"Authorization": f"Bearer {tokenResponse.access_token}", "X-Client-Session-Id": sessionId})
        response.raise_for_status()
        return response
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        handleErrorResponse(response)
        exit()
    except Exception as err:
        print(f"Other error occurred: {err}")
        exit()

def sendPutRequest(path, data=None, json=None, params=None, sessionId=str):
    try:
        response = requests.put(f"{apiUrl}{path}", data=data, json=json, params=params,  headers={"Authorization": f"Bearer {tokenResponse.access_token}", "X-Client-Session-Id": sessionId})
        response.raise_for_status()
        return response
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        handleErrorResponse(response)
        exit()
    except Exception as err:
        print(f"Other error occurred: {err}")
        exit()





projectsJson = sendGetRequest("projects")
print("your projects:")
for project in projectsJson["projects"]:
    print(f"{project['id']} - {project['name']}")

print()
projectId = input("Enter a project id: ")
print()
    


print("Choose what to do next:")
print("1: Model Queries")
print("2: Codifcations")
print("3: Materials")
print("4: Locations")
print("5: CustomProperties")
choose = input()

print()
if choose.startswith("1"):
    modelsJson = sendGetRequest(f"projects/{projectId}/models")
    print("your models:")
    for model in modelsJson["models"]:
        print(f"{model['id']} - {model['name']}")
    print()

    modelId = input("Enter a model id: ")
    print()

    availableDataJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/products/available-data")
    print("fields:")
    for field in availableDataJson["fields"]:
        print(f"{field}")
    print()


    print("Quering the Guid, Class, Name and FireRating fields, filtered on Class Beam...")
    print()
    # Query the Guid, Class, Name and FireRating fields
    fieldsStr = "Guid Class Name FireRating"
    params = list(map(lambda field: ("fields", field), re.split(r'[;,\s]+', fieldsStr)))
    # Filter on class Beam
    params.append(("filters[Class]", "Beam"))
    propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/products", params)

    print()
    for row in propertiesJson["result"]:
        print(f"{row}")

    print()

    print("Starting modification session")
    sessionId = str(uuid.uuid4())
    sendPostRequest(f"projects/{projectId}/models/{modelId}/start-session", sessionId=sessionId)
    try:
        fireRating = f"F{randint(1, 200)}"
        print(f"Modifying FireRating of first row to {fireRating}")
        changes = {
            "values": {
                "FireRating": {
                    propertiesJson["result"][0]["Guid"]: {
                        "PropertySet": "Pset_BeamCommon",
                        "Value": fireRating
                    }
                }
            }
        }
        response = sendPostRequest(f"projects/{projectId}/models/{modelId}/products", json=changes, sessionId=sessionId)
        errors =  list(map(lambda json: ModificationInputError(**json), response.json()["errors"]))
        if len(errors) > 0:
            print(str(errors))
            exit()
    finally:
        print("Closing modification session")
        sendPostRequest(f"projects/{projectId}/models/{modelId}/end-session", sessionId=sessionId)
    print("Modification is done")
    print()
    print("Quering data again")

    propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/products", params)

    print("Showing only the first row:")
    print(propertiesJson["result"][0])

    print()
    print("Starting modification session to reset value")
    sessionId = str(uuid.uuid4())
    sendPostRequest(f"projects/{projectId}/models/{modelId}/start-session", sessionId=sessionId)
    try:
        fireRating = f"F{randint(1, 200)}"
        print(f"Clearing FireRating of first row")
        changes = {
            "values": {
                "FireRating": {
                    propertiesJson["result"][0]["Guid"]: None
                }
            }
        }
        response = sendPostRequest(f"projects/{projectId}/models/{modelId}/products", json=changes, sessionId=sessionId)
        errors =  list(map(lambda json: ModificationInputError(**json), response.json()["errors"]))
        if len(errors) > 0:
            print(errors)
            exit()
    finally:
        print("Closing modification session")
        sendPostRequest(f"projects/{projectId}/models/{modelId}/end-session", sessionId=sessionId)
    print("Modification is done")
    print()
    print("Quering data again")

    propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/products", params)

    print("Showing only the first row:")
    print(propertiesJson["result"][0])

elif choose.startswith("2"):
    print("Showing first codification library")
    codes = sendGetRequest(f"projects/{projectId}/Codifications")

    printMethods.printCodificationLibrary(codes["codificationLibraries"][0])

    #Add new codification library
    print("Adding new TestCodificationLibrary")
    data = {
        "name" : "CodificationTestLibrary",
        "description": "codification library for testing"
    }
    
    sessionId = str(uuid.uuid4())
    newLibrary = (sendPostRequest(f"projects/{projectId}/Codifications", json= data, sessionId=sessionId)).json()

    libraryId = newLibrary["libraryGuid"]

    #Add Codification to library

    newCodeToAdd = {
        "name" : "NewRootCode",
        "identification" : "0",
        "description" :"NewCodeForTesting",
        "parentId": None
    }
    print("Adding new root code the library")
    newCode = (sendPostRequest(f"projects/{projectId}/codifications/{libraryId}/codification", json = newCodeToAdd, sessionId=sessionId)).json()

    code = [item for item in newCode["properties"] if item["name"] == "Guid"]

    #Update Codification
    print("updating the name of the new code from NewRootcode to  updatedName")
    updatedCode = {
    "name": "updatedName"
    }
    sendPutRequest(f"projects/{projectId}/codifications/{libraryId}/codification/{code[0]["value"]}", json = updatedCode, sessionId=sessionId)
    #View specific library
    print("Show new library")
    newlyAddedLibrary = sendGetRequest(f"projects/{projectId}/codifications/{libraryId}")
    printMethods.printCodificationLibrary(newlyAddedLibrary)
    #Delete Codification
    print("Delete newly added code")
    sendDeleteRequest(f"projects/{projectId}/codifications/{libraryId}/codification/{code[0]["value"]}", json = updatedCode, sessionId=sessionId)
    #Delete new CodificationLibrary
    print("Delete new library")
    sendDeleteRequest(f"projects/{projectId}/codifications/{libraryId}", sessionId=sessionId)

elif choose.startswith("3"):
    print("Showing first material library")
    materials = sendGetRequest(f"projects/{projectId}/material-libraries")

    printMethods.printMaterials(materials["materialProperties"][0])

    sessionId = str(uuid.uuid4())
    #Create new material library

    newLibrary = sendPostRequest(f"projects/{projectId}/material-libraries",json = {"Name" :"TestMaterial"}, sessionId=sessionId).json()

    libraryId = newLibrary["guid"]
    #Add material
    newMaterial = {
        "name" : "Concrete",
        "description": "test",
        "color": "#785B3DFF"

    }
    print("Adding new material to the library")
    newMaterial = (sendPostRequest(f"projects/{projectId}/material-libraries/{libraryId}/materials", json = newMaterial, sessionId=sessionId)).json()

    #Update material
    updatedMaterial =  {
        "name": "Concrete",
        "description": "concrete test material",
        "color": "#49C73EFF"
    }
    newMaterialId = newMaterial["guid"]
    sendPutRequest(f"projects/{projectId}/material-libraries/{libraryId}/materials/{newMaterialId}", json=updatedMaterial, sessionId= sessionId)
    materials = sendGetRequest(f"projects/{projectId}/material-libraries")

    printMethods.printMaterials( [lib for lib in materials["materialProperties"] if lib["guid"] == libraryId][0])
    #Delete material
    print("Delete material again")
    sendDeleteRequest(f"projects/{projectId}/material-libraries/{libraryId}/materials/{newMaterialId}", sessionId=sessionId)

elif choose.startswith("4"):
    print("Get all locations")
    locations = sendGetRequest(f"projects/{projectId}/locations")
    for location in locations["locationViews"]:
        printMethods.printLocations(location)
        print("-----------------------------------------")

    print("Add new site location")

    newSite = {
        "name" : "NewLocation",
        "type" : "Site",
        "parentGuid" : None
    }

    sessionId = str(uuid.uuid4())
    site = (sendPostRequest(f"projects/{projectId}/locations", json=newSite, sessionId= sessionId)).json()

    guidSite = [prop for prop in  site["properties"] if prop["name"] == "Guid"][0]["value"]
    
    print("Add new building")
    newBuilding = {
        "name" :"NewBuilding",
        "type" : "Building",
        "parentGuid" : guidSite

    }

    building = sendPostRequest(f"projects/{projectId}/locations", json= newBuilding, sessionId= sessionId)

    print("Update site name to newSite")
    updatedSite ={
        "name":"newSite"
    }
    sendPutRequest(f"projects/{projectId}/locations/{guidSite}", json =updatedSite , sessionId=sessionId)

    print("Show added locations")
    locations = sendGetRequest(f"projects/{projectId}/locations")

    for location in locations["locationViews"]:
        if [prop for prop in  site["properties"] if prop["name"] == "Guid"][0]["value"] == guidSite:
            printMethods.printLocations(location)

    print("Delete added locations")
    sendDeleteRequest(f"projects/{projectId}/locations/{guidSite}", sessionId=sessionId)

elif choose.startswith("5"):
    print("Showing all custom properties")
    
    customProperties = sendGetRequest(f"projects/{projectId}/customProperties")
    printMethods.printCustomProperties(customProperties)

    print("Create new propertyset: TestSet")

    propertySetToAdd = {
        "Name": "TestSet",
        "EntityTypes" : [  {"Value": "IfcWall"}, {"Value": "IfcBeam"}, {"Value": "IfcSlab"}]
    }
    sessionId = str(uuid.uuid4())
    addedSet =  (sendPostRequest(f"projects/{projectId}/customProperties/property-sets", json= propertySetToAdd, sessionId=sessionId)).json()

    print("Add property to set: TestProperty")

    propertyToAdd = {
        "Name": "TestProperty",
        "DataType": "String"
    }

    addedProperty = sendPostRequest(f"projects/{projectId}/customProperties/property-sets/{addedSet["id"]}/property",json=propertyToAdd, sessionId=sessionId)

    print("Choose model to add this property to")

    modelsJson = sendGetRequest(f"projects/{projectId}/models")
    print("your models:")
    for model in modelsJson["models"]:
        print(f"{model['id']} - {model['name']}")
    print()

    modelId = input("Enter a model id: ")
    print()


    print("Quering the Guid, Class, Name fields, filtered on Class Wall...")
    print()
    # Query the Guid, Class, Name  fields
    fieldsStr = "Guid Class Name"
    params = list(map(lambda field: ("fields", field), re.split(r'[;,\s]+', fieldsStr)))
    # Filter on class wall
    params.append(("filters[Class]", "Wall"))
    propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/products", params)

    print()
    for row in propertiesJson["result"]:
        print(f"{row}")

    print("Adding test property to first wall")
    print("  Starting modification session")
    sessionId = str(uuid.uuid4())
    sendPostRequest(f"projects/{projectId}/models/{modelId}/start-session", sessionId=sessionId)
    try:
        changes = {
            "values": {
                "TestProperty": {
                    propertiesJson["result"][0]["Guid"]: {
                        "PropertySet": "TestSet",
                        "Value": "testValue"
                    }
                }
            }
        }
        response = sendPostRequest(f"projects/{projectId}/models/{modelId}/products", json=changes, sessionId=sessionId)
        errors =  list(map(lambda json: ModificationInputError(**json), response.json()["errors"]))
        if len(errors) > 0:
            print(str(errors))
            exit()


    finally:
        print("Closing modification session")
        sendPostRequest(f"projects/{projectId}/models/{modelId}/end-session", sessionId=sessionId)

   
  


    


    




    
