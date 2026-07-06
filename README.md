# Python example for the Qonic API

A python example for accessing the Qonic API

## Setup

Follow these steps to configure and run the Python example for the Qonic API.

### 1. Prerequisites

- Python 3.10+

By default, this sample uses Qonic's pre-registered public OAuth client. To test your own app registration, set `QONIC_CLIENT_ID` to your application's client id and make sure `QONIC_REDIRECT_URI` is whitelisted.

### 2.  Copy the environment template
```bash
cp .env.example .env
```

### 3. Configure .env
```bash
# Must exactly match a whitelisted redirect URI
QONIC_REDIRECT_URI=http://localhost:8765/callback

# Optional: local callback server port (should match the redirect URI)
QONIC_LOCAL_PORT=8765

# Space-separated scopes required for the sample
QONIC_SCOPES=projects:read models:read

# Optional: override Qonic's default sample client
QONIC_CLIENT_ID=YOUR_CLIENT_ID
```

**Notes**
- QONIC_REDIRECT_URI must match a whitelisted Redirect URI exactly (scheme, host, port, path). 
- The sample spins up a tiny local HTTP server on QONIC_LOCAL_PORT to receive the authorization code. 
- PKCE is used out of the box; no client secret is required or sent.


### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the example
```bash
python sample.py
```

Your default browser will open, prompting you to log in and authorize the application. After authorization, the script will receive an access token that can be used to make requests against the api.

## Project structure

The main example is in [sample.py](./sample.py). This file includes all the configuration for authentication and example requests.

All authentication-related code is in [oauth.py](./oauth.py). This file uses the OAuth authorization code flow to obtain an access token. A local web server is started to receive the authorization code and token response from the authentication server.
