from random import randint
import requests
import re
from oauth import login


apiUrl = "https://api.qonic.com/v1/"

tokenResponse = login(
    issuer="https://release-qonic.eu.auth0.com",
    client_id="yBoHANGQWFoMcM3uxk1CUI4G4vURmFn9",
    redirect_uri="http://localhost:34362",
    scope="openid profile email",
    audience="https://api.qonic.com")

def handleErrorResponse(availableDataResponse: requests.Response):
    try:
        print(availableDataResponse.json())
    except Exception as err:
        print(f"Error occurred while processing error response: {err}")
    exit()

def sendGetRequest(path, params=None):
    try:
        response = requests.get(f"{apiUrl}{path}", params=params,  headers={"Authorization": f"Bearer {tokenResponse.access_token}"})
        response.raise_for_status()
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        handleErrorResponse(response)
    except Exception as err:
        print(f"Other error occurred: {err}")
        exit()
    return response.json()

def sendPostRequest(path, data=None, json=None, params=None):
    try:
        response = requests.post(f"{apiUrl}{path}", data=data, json=json, params=params,  headers={"Authorization": f"Bearer {tokenResponse.access_token}"})
        response.raise_for_status()
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        handleErrorResponse(response)
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
    
modelsJson = sendGetRequest(f"projects/{projectId}/models")
print("your models:")
for model in modelsJson["models"]:
    print(f"{model['id']} - {model['name']}")

print()
modelId = input("Enter a model id: ")
print()

availableDataJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/external-query-available-data")
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
propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/external-query", params)

print()
for row in propertiesJson["result"]:
    print(f"{row}")

print()


print("Starting modification session")
sendPostRequest(f"projects/{projectId}/models/{modelId}/start-external-modification-session")
try:
    fireRating = f"F{randint(1, 200)}"
    print(f"Modifying FireRating of first row to {fireRating}")
    changes = {
        "values": {
            "FireRating": {
                propertiesJson["result"][0]["Guid"]: fireRating 
            }
        }
    }
    sendPostRequest(f"projects/{projectId}/models/{modelId}/external-data-modification", json=changes)
finally:
    print("Closing modification session")
    sendPostRequest(f"projects/{projectId}/models/{modelId}/end-external-modification-session")
print("Modification is done")
print()
print("Quering data again")

propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/external-query", params)

print("Showing only the first row:")
print(propertiesJson["result"][0])

print()
print("Starting modification session to reset value")
sendPostRequest(f"projects/{projectId}/models/{modelId}/start-external-modification-session")
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
    sendPostRequest(f"projects/{projectId}/models/{modelId}/external-data-modification", json=changes)
finally:
    print("Closing modification session")
    sendPostRequest(f"projects/{projectId}/models/{modelId}/end-external-modification-session")
print("Modification is done")
print()
print("Quering data again")

propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/external-query", params)

print("Showing only the first row:")
print(propertiesJson["result"][0])