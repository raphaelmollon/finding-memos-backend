import requests
import json

# Load your data from the JSON file
with open('db_save.json', 'r') as file:
    data = json.load(file)

# Send the POST request
response = requests.post('http://127.0.0.1:5000/import', json=data)

# Check the response
if response.status_code == 201:
    print("Data imported successfully.")

else:
    print(f"Error importing data: {response.status_code}")
    print(response.json())
exit();
