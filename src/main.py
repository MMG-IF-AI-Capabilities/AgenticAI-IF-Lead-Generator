import os
import csv
import json
import requests
import io
import openai
from ixbrlparse import IXBRL
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

def filter_mortgages_ch_csv(input_file_path):
    OUTPUT_COMPANY_CT = 35
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
                                                  'companyName': row[0].strip().replace("\"",""),
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
    print(f"Getting filing history for {company_name}")
    response = execute_ch_request('get', url, query_params=query_params)
    # print(f'Filing History - {json.dumps(response.json(),indent=2)}')
    if response.json()["filing_history_status"] == 'filing-history-available':
        TOT_FINANCIAL_CT = 3
        read_financial_ct = 0
        financials = []
        doc_file_path = os.path.join("output","fin_reports",f'{company_num} - {company_name}')
        if not os.path.exists(doc_file_path):
            print(f"Creating folder - {doc_file_path}")
            os.makedirs(doc_file_path)

        for item in response.json()["items"]:
            if read_financial_ct >= TOT_FINANCIAL_CT:
                break
            # print(f"Item Category - {item['category']}")

            print(f"Document link - {item['links']['document_metadata']}")        
            doc_metadata_response = execute_ch_request('get', item['links']['document_metadata'])
            print(f'Metadata Response types - {doc_metadata_response.json()['resources'].keys()}')
            if 'application/xhtml+xml' in doc_metadata_response.json()['resources'].keys():
                headers = {"Accept": "application/xhtml+xml"}
                doc_response = execute_ch_request('get', doc_metadata_response.json()["links"]["document"], headers=headers)
                doc_file_name = os.path.join(doc_file_path, f'{item['date']} - {item['description']}.html')
                with open(doc_file_name, 'wb') as doc_outfile:
                    print(f'Streaming file - {item['date']} - {item['description']}.html')
                    for chunk in doc_response.iter_content(chunk_size=128):
                        doc_outfile.write(chunk)
                    print(f'Completed streaming file - {item['date']} - {item['description']}.html')
                    try:
                        financials.extend(parse_iXBRL(doc_file_name))
                    except KeyError as e:
                        print(f"Error while parsing {doc_file_name} for {company_name}. Skipping parsing. Error {e}")
                    else:
                        print(f"File - {doc_file_name} parsed successfully.")
            else:
                print(f"iXBRL file not found")
            read_financial_ct += 1
            # if read_financial_ct < TOT_FINANCIAL_CT:      #gather more items if read ct is less than required limit
            #     pass
        return financials
    else: 
        print(f"Filing history not available for {company_name}")

def parse_iXBRL(path):
    with open(path, 'r', encoding='utf-8') as fin_report:
        report = IXBRL(fin_report)
        fin_obj = []
        for fact in report.numeric:
            fact_obj = fact.to_json()
            # print(json.dumps(fact_obj, indent=2))
            fact = {"fact_name": fact_obj['name'], "fact_value": fact_obj['value'], "instant_date": fact_obj['context']['instant']} if isinstance(fact_obj['context'], dict) and fact_obj['context']['instant'] is not None else {"fact_name": fact_obj['name'], "fact_value": fact_obj['value'], "start_date": fact_obj['context']['startdate'], "end_date": fact_obj['context']['enddate']} if isinstance(fact_obj['context'], dict) else {"fact_name": fact_obj['name'], "fact_value": fact_obj['value']}
            fin_obj.append(fact)
    return fin_obj
            
def get_working_capital_eligibilty(company_data):
    os.environ["GOOGLE_API_KEY"] = "AIzaSyAVe_KrmZLN6UI3C_k1l6mDiOwbsgO14cE"
    llm = ChatGoogleGenerativeAI(model = "gemini-1.5-flash", temperature=0)

    analysis_prompt = PromptTemplate(
        input_variables=["json_content"],
        template="""
                *ROLE AND GOAL:*
                You are an expert UK-based credit analyst specializing in SME working capital. Your goal is to analyze the provided financial statements to determine if the company is a strong candidate for an invoice discounting facility. You must identify signs of cash flow pressure caused by growth, long payment terms, or operational inefficiencies.

                *CONTEXT:*
                Invoice discounting helps businesses by advancing cash against their unpaid B2B invoices, immediately improving their working capital. Ideal candidates are B2B companies that are growing, but whose cash is tied up in accounts receivable (debtors). Key indicators of need include high or increasing debtor days, revenue growth outstripping cash reserves, and pressure on the current ratio.

                *FINANCIAL DATA:*
                {json_content}

                *CRITICAL ANALYSIS & INSTRUCTIONS:*
                1.  *Analyze Key Ratios & Trends:* Do not just state the ratios. Analyze the trends over the available periods for:
                    *   *Revenue Growth:* Is the company growing? Calculate the year-over-year percentage.
                    *   *Accounts Receivable (Debtors):* Are debtors growing, and are they growing faster than revenue? This is a critical signal.
                    *   *Debtor Days:* Calculate and analyze the trend in debtor days. An increase is a strong signal of cash flow pressure.
                    *   *Current Ratio (Current Assets / Current Liabilities):* Is it healthy for their industry? Is it declining over time?
                    *   *Working Capital:* Is the net working capital positive and sufficient for its sales volume? Is it deteriorating?
                2.  *Synthesize a Qualitative Narrative:* Based on your analysis, provide a concise (2-3 sentences) summary of the company's working capital situation. This MUST be a human-readable narrative that can be used in an email. Reference specific data points to add credibility.
                3.  *Generate a Qualification Score:* Provide a "Cash Flow Pressure Score" (CFPS) from 1 (no pressure) to 10 (extreme pressure). A score above 6 indicates a strong candidate.
                4.  *Determine Final Qualification:* Based on the score and narrative, provide a final binary decision: QUALIFIED or NOT_QUALIFIED.

                *OUTPUT FORMAT:*
                You MUST return your response as a valid JSON object. Do not include any other text or explanations outside of the JSON structure.

              {{
                "cfps_score": <integer>,
                "qualitative_narrative": "<string>",
                "final_qualification": "<'QUALIFIED' or 'ASSISTED' or 'NOT_QUALIFIED'>"
              }}

                """,
                # template_format="jinja2",
    )

    prompt = analysis_prompt.format(json_content=json.dumps(company_data, indent=2))

    try:
        response_text = llm.invoke(prompt).content.strip().replace('`','')[4:]
        # print(f"LLM Response: {response_text}")
        result = json.loads(response_text)
        for key in result.keys():
            company_data[key] = result[key]
    except Exception as e:
        print(e)
    else:
        print("Got result from Gemini!")


if __name__ == '__main__':
    CH_CSV_INPUT = os.path.join('resources', 'small_companies_list.csv')
    company_list = filter_mortgages_ch_csv(CH_CSV_INPUT)

    qualified_company_list = []
    non_qualified_company_list = []

    if company_list is not None and isinstance(company_list, list):
        for company in company_list:
            company['financials'] = get_ch_filing_history(company['companyNumber'], company['companyName'])
            if company['financials'] != []:
                get_working_capital_eligibilty(company)
                qualified_company_list.append(company) if company["final_qualification"] == "QUALIFIED" else non_qualified_company_list.append(company)
                
                COMPANY_OUTPUT_JSON_FILEPATH = os.path.join('output', 'fin_json')
                COMPANY_OUTPUT_JS0N_FILENAME = os.path.join(COMPANY_OUTPUT_JSON_FILEPATH, f'{company["companyNumber"]} - {company["companyName"]}.json')
                if not os.path.exists(COMPANY_OUTPUT_JSON_FILEPATH):
                    os.makedirs(COMPANY_OUTPUT_JSON_FILEPATH)
                with open(COMPANY_OUTPUT_JS0N_FILENAME, 'w', encoding='utf-8') as outfile:
                    json.dump(company, outfile, indent=2)
                
            else:
                print(f"No financial data for {company["companyName"]}")
    
    with open("qualified_company_list.csv", 'w', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["companyNumber","companyName","chUrl","cfps_score","qualitative_narrative","final_qualification"])
        for company in qualified_company_list:
            writer.writerow([company["companyNumber"],company["companyName"],company["chUrl"],company["cfps_score"],company["qualitative_narrative"],company["final_qualification"]])

    with open("non_qualified_company_list.csv", 'w', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["companyNumber","companyName","chUrl","cfps_score","qualitative_narrative","final_qualification"])
        for company in non_qualified_company_list:
            writer.writerow([company["companyNumber"],company["companyName"],company["chUrl"],company["cfps_score"],company["qualitative_narrative"],company["final_qualification"]])