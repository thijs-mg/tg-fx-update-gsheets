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

    try:
        rates = [payment_option['quote']['rate'] 
                 for delivery_option in response_data['deliveryOptions'].values() 
                 for payment_option in delivery_option['paymentOptions'].values()]
        highest_rate = max(rates)
        unique_highest_rates = list(set([rate for rate in rates if rate == highest_rate]))

        return round(unique_highest_rates[0], 2)
    except KeyError as e:
        st.error(f"Key error: {e}")
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
            sheet = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range='Base!A2:F').execute()
            rows = sheet.get('values', [])

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
                    row_id = f"{country_of_residence}-{blended_hub}"

                    rate = get_transfer_rate(calculation_base, amount, country_of_residence, to_country_code, from_currency_code, to_currency_code)
                    data.append([row_id, country_of_residence, blended_hub, to_country_code, from_currency_code, to_currency_code, rate])
                
                progress_bar.progress((i + 1) / len(rows))

            df = pd.DataFrame(data, columns=['id', 'country_of_residence', 'blended_hub', 'to_country_code', 'from_currency_code', 'to_currency_code', 'transfer_rate'])
            
            # Update Google Sheet with the DataFrame
            update_google_sheet_with_dataframe(service, spreadsheet_id, df, 'results')

        st.success("Process completed successfully!")
        st.dataframe(df)

if __name__ == "__main__":
    main()