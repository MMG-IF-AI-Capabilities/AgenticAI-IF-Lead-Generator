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

def execute_ch_request(method, url, headers = None, API_KEY = '5fdfb592-4c05-4157-98fe-01b6ae111b40'):
    if method == 'get':
        response = requests.get(url, auth=(API_KEY, ''), headers=headers)
        return response
    
def get_ch_filing_history(company_num):
    url = f'https://api.company-information.service.gov.uk/company/{company_num}/filing-history'
    response = execute_ch_request('get', url)
    if response.json()["filing_history_status"] == 'filing-history-available':
        TOT_FINANCIAL_CT = 3
        read_financial_ct = 0
        financials = []
        for item in response.json()["items"]:
            if item['category'] == 'accounts' and read_financial_ct < TOT_FINANCIAL_CT:
                # print(f'{company_num} - Item Date - {item['date']} - Item Made Up Date - {item['description_values']['made_up_date']}')
                doc_metadata_response = execute_ch_request('get', item['links']['document_metadata'])
                if 'application/xhtml+xml' in doc_metadata_response.json()['resources'].keys():
                    headers = {"Accept": "application/xhtml+xml"}
                    doc_response = execute_ch_request('get', doc_metadata_response.json()["links"]["document"], headers=headers)
                    if doc_response.status_code == 200:
                        financial_doc = IXBRL(io.StringIO(doc_response.text))
                        # for ctx in financial_doc.contexts.items():
                            # print(ctx[1].to_json())
                        # print(json.dumps(financial_doc.to_json(), indent=2))
                        # with open(os.path.join('output',f'Sample-iXBRL.json'), 'w') as outfile:
                        #     json.dump(financial_doc.to_json(), outfile)
                        

                        # 2. DEFINE TAG MAPPING
                        TAG_MAP = {
                            "revenue": ["Revenue", "Turnover"],
                            "net_profit": ["ProfitLoss"],
                            "fixed_assets": ["FixedAssets"],
                            "current_assets": ["CurrentAssets"],
                            "current_liabilities": ["Creditors"],
                            "total_liabilities": ["Liabilities"],
                            "shareholder_funds": ["Equity", "NetAssetsLiabilities"],
                        }

                        # 3. IDENTIFY REPORTING DATES
                        # Find the two most recent 'instant' dates to identify current and prior year contexts
                        dates = {}
                        for ctx in financial_doc.contexts.values():
                            if ctx.instant:
                                dates[ctx.id] = ctx.instant
                        
                        if len(dates) < 2:
                            raise ValueError("Could not find at least two distinct reporting dates in the file.")

                        sorted_contexts = sorted(dates.items(), key=lambda item: item[1], reverse=True)
                        current_year_date_str = sorted_contexts[0][1].strftime('%Y-%m-%d')
                        prior_year_date_str = sorted_contexts[1][1].strftime('%Y-%m-%d')

                        print(f"Current Year End: {current_year_date_str}")
                        print(f"Prior Year End: {prior_year_date_str}\n")
                        
                        # 4. INITIALIZE RESULTS DICTIONARY
                        results = {
                            current_year_date_str: {},
                            prior_year_date_str: {}
                        }

                        # 5. ITERATE AND EXTRACT NUMERIC FACTS
                        for fact in financial_doc.numeric:
                            # Determine which data point this fact represents
                            metric_name = None
                            for name, tags in TAG_MAP.items():
                                if fact.name in tags:
                                    metric_name = name
                                    break
                            
                            if not metric_name:
                                continue

                            # Determine the date for the fact from its context
                            fact_date = fact.context.instant
                            if not fact_date:
                                # Skip duration-based facts for this simple example
                                continue

                            fact_date_str = fact_date.strftime('%Y-%m-%d')
                            
                            # Special handling for current liabilities (check context segments)
                            if metric_name == "current_liabilities":
                                is_current = any(
                                    'WithinOneYear' in (seg.value or '') for seg in fact.context.segments
                                )
                                if not is_current:
                                    continue # This is not a current liability

                            # Store the value in the correct year
                            if fact_date_str in results:
                                results[fact_date_str][metric_name] = fact.value
                        
                        # 6. CALCULATE DERIVED METRICS
                        for year, data in results.items():
                            if "fixed_assets" in data and "current_assets" in data:
                                data["total_assets"] = data["fixed_assets"] + data["current_assets"]
                            # Note: 'total_liabilities' might be tagged directly or may need calculation.
                            # This script assumes it might be tagged directly.

                        # 7. DISPLAY RESULTS
                        print("--- Financial Data Extracted ---")
                        header = f"{'Metric':<25} | {'Value for ' + current_year_date_str:<20} | {'Value for ' + prior_year_date_str:<20}"
                        print(header)
                        print("-" * len(header))

                        display_order = [
                            "revenue", "net_profit", "fixed_assets", "current_assets", 
                            "total_assets", "current_liabilities", "total_liabilities", "shareholder_funds"
                        ]

                        for metric in display_order:
                            current_val = results.get(current_year_date_str, {}).get(metric, 'N/A')
                            prior_val = results.get(prior_year_date_str, {}).get(metric, 'N/A')
                            
                            # Format for display
                            current_disp = f"£{current_val:19,.2f}" if isinstance(current_val, (int, float)) else 'Not Found'
                            prior_disp = f"£{prior_val:19,.2f}" if isinstance(prior_val, (int, float)) else 'Not Found'

                            print(f"{metric.replace('_', ' ').title():<25} | {current_disp:<20} | {prior_disp:<20}")




                        # financials.append(financial_doc)
                read_financial_ct += 1
        
        return financials
                    

if __name__ == '__main__':
    CH_CSV_INPUT = os.path.join('resources', 'small_companies_list.csv')
    company_list = filter_mortgages_ch_csv(CH_CSV_INPUT)

    if company_list is not None and isinstance(company_list, list):
        for company in company_list:
            company['financials'] = get_ch_filing_history(company['companyNumber'])

    print(json.dumps(company_list, indent=2))