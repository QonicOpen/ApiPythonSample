def printCodificationLibrary(data):
    # Print Library
    print(f"Library: {data['libraryGuid']}")
    
    # Print Codes
    print("Codes:")
    
    # Loop through classifications and properties
    for classification in data["codes"]["classifications"]:
        for property in classification["properties"]:
            # Print each set, name, and value
            print(f" {property['name']} {property['value']}")
        print("-----------------------------------------")

def printMaterials(data):
    print(f"Name: {data['name']}")
    print(f"Guid: {data['guid']}")
    for material in data["properties"]:
        for property in material:
            print(f" {property['name']} {property['value']}")
        print("-----------------------------------------")



def printLocations(data, level = 0):
    extraspaces = level*2 * ' '
    print(f"{extraspaces}Name: {data['name']}")
    print("Properties:")
    for property in data["properties"]:
    # Print each set, name, and value
        print(f" {extraspaces}{property['name']} {property['value']}")
    print(extraspaces +"SubLevels:")
    for child in data["children"]:
        print()
        printLocations(child, level +1)

def printCustomProperties(data):
    print(data["libraryId"])
    for set in data["sets"]:
        print(f"  Id:{set['id']}")
        print(f"  Name:{set['name']}")
        print("  Properties:")
        for propdef in set["propertyDefinitions"]:
            print(f"    Id:{propdef['id']} Guid:{propdef['guid']} Name:{propdef['name']} DataType:{propdef['dataType']} MeasureType:{propdef['measureType']} Unit:{propdef['unitName']}")

    
    