import os
import csv
import json
import requests
import io
from ixbrlparse import IXBRL

def filter_mortgages_ch_csv(input_file_path):
    OUTPUT_COMPANY_CT = 1
    print(f'Starting CSV file parsing from {input_file_path}...')
    try:
        with open(input_file_path, 'r', newline='', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            
            filter_column_name = 'Mortgages.NumMortOutstanding'
            value_to_match = 0
            header = next(reader)

            try:
                filter_column_index = header.index(filter_column_name)
            except ValueError:
                print(f"Error: Column '{filter_column_name}' not found in the CSV header.")
                return # Exit the function
            
            print(f"Filtering rows where '{filter_column_name}' is '{value_to_match}'...")
            
            rows_written = 0
            filtered_company_list = []
            for row in reader:
                if len(row) > filter_column_index and int(row[filter_column_index]) > value_to_match and row[11] == 'Active':
                    filtered_company_list.append({'companyNumber': row[1].strip(), 
                                                  'companyName': row[0].strip(),
                                                  'companyCategory': row[10].strip(),
                                                  'companyStatus': row[11].strip(),
                                                  'numMortCharges': row[22],
                                                  'numMortOutstanding': row[23],
                                                  'numMortPartSatisfied': row[24],
                                                  'numMortSatisfied': row[25],
                                                  'chUrl':row[32].strip()})
                    rows_written += 1
                if rows_written >= OUTPUT_COMPANY_CT:
                    break
            # print(json.dumps(filtered_company_list, indent=2))
            return filtered_company_list

    except FileNotFoundError:
        print(f"Error: The file '{input_file_path}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def execute_ch_request(method, url, headers = None, query_params = None, API_KEY = '5fdfb592-4c05-4157-98fe-01b6ae111b40'):
    if method == 'get':
        response = requests.get(url, auth=(API_KEY, ''), headers=headers, params=query_params)
        return response
    
def get_ch_filing_history(company_num, company_name):
    url = f'https://api.company-information.service.gov.uk/company/{company_num}/filing-history'
    query_params={"category": "accounts"}
    response = execute_ch_request('get', url, query_params=query_params)
    print(f'Filing History - {json.dumps(response.json(),indent=2)}')
    if response.json()["filing_history_status"] == 'filing-history-available':
        TOT_FINANCIAL_CT = 1
        read_financial_ct = 0
        financials = []
        doc_file_path = os.path.join("output","fin_reports",f'{company_num} - {company_name}')
        if not os.path.exists(doc_file_path):
            print(f"Creating folder - {doc_file_path}")
            os.makedirs(doc_file_path)

        for item in response.json()["items"]:
            if item['category'] == 'accounts' and read_financial_ct < TOT_FINANCIAL_CT:
                # print(f'{company_num} - Item Date - {item['date']} - Item Made Up Date - {item['description_values']['made_up_date']}')
                doc_metadata_response = execute_ch_request('get', item['links']['document_metadata'])
                if 'application/xhtml+xml' in doc_metadata_response.json()['resources'].keys():
                    headers = {"Accept": "application/xhtml+xml"}
                    doc_response = execute_ch_request('get', doc_metadata_response.json()["links"]["document"], headers=headers)
                    doc_file_name = os.path.join(doc_file_path, f'{item['date']} - {item['description']}.html')
                    with open(doc_file_name, 'wb') as doc_outfile:
                        print(f'Streaming file - {item['date']} - {item['description']}.html')
                        for chunk in doc_response.iter_content(chunk_size=128):
                            doc_outfile.write(chunk)
                        print(f'Completed streaming file - {item['date']} - {item['description']}.html')
                        financials.append(doc_file_name)
                read_financial_ct += 1
        
        return financials
                    

if __name__ == '__main__':
    CH_CSV_INPUT = os.path.join('resources', 'small_companies_list.csv')
    company_list = filter_mortgages_ch_csv(CH_CSV_INPUT)

    if company_list is not None and isinstance(company_list, list):
        for company in company_list:
            company['financials'] = get_ch_filing_history(company['companyNumber'], company['companyName'])

    print(json.dumps(company_list, indent=2))