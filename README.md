# Transfer Rate Calculator and Updater

This project provides a tool to calculate and update transfer rates using various APIs and Google Sheets. It integrates with Streamlit for a user-friendly interface, Google Sheets for data storage, and Braze for updating catalogs.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Functions](#functions)
  - [connect_to_google_sheets](#connect_to_google_sheets)
  - [get_transfer_rate](#get_transfer_rate)
  - [update_google_sheet_with_dataframe](#update_google_sheet_with_dataframe)
  - [update_braze_catalog](#update_braze_catalog)
  - [main](#main)
- [Contributing](#contributing)
- [License](#license)

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/thijs-mg/tg-fx-update-gsheets.git
    ```

2. Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

3. Set up your environment secrets for Google Sheets and Braze API by adding them to Streamlit secrets.

## Usage

1. Run the Streamlit app:
    ```sh
    streamlit run app.py
    ```

2. This will open up your browser automatically. Otherwise, open the local Streamlit URL provided in the terminal to access the web interface.

3. Enter the amount and click on "Calculate and Update" to start the process.

## Configuration

Ensure you have the following secrets configured in your Streamlit app:
- `gcp_service_account`
- `spreadsheet_id`
- `braze_api_key`

These secrets should be set in the `.streamlit/secrets.toml` file like this:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "your-private-key"
client_email = "your-client-email"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-client-cert-url"

spreadsheet_id = "your-spreadsheet-id"
braze_api_key = "your-braze-api-key"
