# Python example for the Qonic API

A python example for accessing the Qonic API

# Example Usage
To run the example, follow these steps:

Ensure you have installed the dependencies:

```bash
pip install -r requirements.txt
```

Run the sample script:
```
python sample.py
```

Your default browser will open, prompting you to log in and authorize the application. After authorization, the script will receive an access token that can be used to make requests against the api.

## Project structure

The main example is in [sample.py](./sample.py). This file includes all the configuration for authentication and example requests.

All authentication-related code is in [oauth.py](./oauth.py). This file uses the OAuth authorization code flow to obtain an access token. A local web server is started to receive the authorization code and token response from the authentication server.
