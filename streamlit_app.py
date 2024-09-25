import requests
import pandas as pd
import time
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Define the scope for Google Sheets API
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

@st.cache_resource
def connect_to_google_sheets():
    # Create credentials from environment secrets
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=credentials)

def parse_api_response(response_data):
    parsed_response = {
        "deliveryOptions": {},
        "paymentOptions": {},
        "rates": []
    }
    
    for delivery_key, delivery_value in response_data.get('deliveryOptions', {}).items():
        parsed_response["deliveryOptions"][delivery_key] = delivery_value.get('name', 'Unknown')
        
        for payment_key, payment_value in delivery_value.get('paymentOptions', {}).items():
            parsed_response["paymentOptions"][payment_key] = payment_value.get('name', 'Unknown')
            
            quote = payment_value.get('quote', {})
            if 'rate' in quote:
                parsed_response["rates"].append(quote['rate'])
    
    return parsed_response

def get_transfer_rate(calculation_base, amount, country_of_residence, to_country_code, from_currency_code, to_currency_code):
    url = "https://my.transfergo.com/api/transfers/quote"
    params = {
        "calculationBase": calculation_base,
        "amount": amount,
        "fromCountryCode": country_of_residence,
        "toCountryCode": to_country_code,
        "fromCurrencyCode": from_currency_code,
        "toCurrencyCode": to_currency_code
    }

    time.sleep(1 / 7)  # Sleep to ensure not more than 7 calls per second

    response = requests.get(url, params=params)
    response_data = response.json()
    
    parsed_response = parse_api_response(response_data)
    
    st.session_state.latest_api_call = {
        "parameters": params,
        "parsed_response": parsed_response
    }

    try:
        highest_rate = max(parsed_response["rates"])
        return round(highest_rate, 2)
    except ValueError:
        st.error("No valid rates found in the API response.")
        return None

def update_google_sheet_with_dataframe(service, spreadsheet_id, dataframe, sheet_name):
    sheets_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_titles = [sheet['properties']['title'] for sheet in sheets_metadata['sheets']]
    
    if sheet_name in sheet_titles:
        sheet_id = next(sheet['properties']['sheetId'] for sheet in sheets_metadata['sheets'] if sheet['properties']['title'] == sheet_name)
        body = {'requests': [{'deleteSheet': {'sheetId': sheet_id}}]}
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    body = {'requests': [{'addSheet': {'properties': {'title': sheet_name}}}]}
    service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    values = [dataframe.columns.values.tolist()] + dataframe.values.tolist()
    body = {'values': values}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!A1',
        valueInputOption="RAW",
        body=body
    ).execute()
    st.write(f"Updated Google Sheet '{sheet_name}' with {len(dataframe)} rows")

def main():
    st.title("Transfer Rate Calculator and Updater")

    # Configuration
    spreadsheet_id = st.secrets["spreadsheet_id"]
    calculation_base = "sendAmount"
    amount = st.number_input("Enter amount", min_value=1.0, value=101.0, step=1.0)
    braze_api_key = st.secrets["braze_api_key"]
    catalog_name = 'transfer_rates'

    if st.button("Calculate and Update"):
        with st.spinner("Processing..."):
            # Connect to Google Sheets
            service = connect_to_google_sheets()

            # Read rows from the Google Sheet
            sheet = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range='Base!A2:G').execute()
            rows = sheet.get('values', [])
            st.write(f"Read {len(rows)} rows from Google Sheet")

            # Prepare DataFrame
            data = []
            progress_bar = st.progress(0)
            for i, row in enumerate(rows):
                if len(row) >= 7:
                    country_of_residence = row[1]
                    blended_hub = row[2]
                    to_country_code = row[3]
                    from_currency_code = row[4]
                    to_currency_code = row[5]
                    nationality = row[6]
                    row_id = f"{country_of_residence}-{blended_hub}"

                    rate = get_transfer_rate(calculation_base, amount, country_of_residence, to_country_code, from_currency_code, to_currency_code)
                    data.append([row_id, country_of_residence, blended_hub, to_country_code, from_currency_code, to_currency_code, nationality, rate])
                
                progress_bar.progress((i + 1) / len(rows))

            df = pd.DataFrame(data, columns=['id', 'country_of_residence', 'blended_hub', 'to_country_code', 'from_currency_code', 'to_currency_code', 'nationality', 'transfer_rate'])
            
            # Update Google Sheet with the DataFrame
            update_google_sheet_with_dataframe(service, spreadsheet_id, df, 'results')

        st.success("Process completed successfully!")
        st.dataframe(df)

        # Display the latest API call details
        if hasattr(st.session_state, 'latest_api_call'):
            st.subheader("Latest API Call Details")
            st.json(st.session_state.latest_api_call)

if __name__ == "__main__":
    main()