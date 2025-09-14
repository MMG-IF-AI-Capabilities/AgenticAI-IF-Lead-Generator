import requests
import csv
import os

APOLLO_API_URL = "https://api.apollo.io/api/v1/organizations/search"
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

HUNTER_API_URL = "https://api.hunter.io/v2/domain-search"
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")

HEADERS = {
    "accept": "application/json",
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "x-api-key": APOLLO_API_KEY
}

def fetch_company_details(company_name):
    """Fetch company details from Apollo API"""
    try:
        payload = {"q_organization_name": company_name}
        response = requests.post(APOLLO_API_URL, headers=HEADERS, json=payload)
        if response.status_code != 200:
            return None
        orgs = response.json().get("organizations", [])
        if not orgs:
            return None

        org = orgs[0]
        return {
            "company": org.get("name"),
            "phone": org.get("phone") or org.get("primary_phone", {}).get("number"),
            "domain": org.get("primary_domain")
        }
    except:
        return None

def fetch_emails_from_hunter(domain):
    """Fetch emails from Hunter.io using domain"""
    if not domain:
        return []
    params = {"domain": domain, "api_key": HUNTER_API_KEY}
    response = requests.get(HUNTER_API_URL, params=params)
    if response.status_code != 200:
        return []
    emails = response.json().get("data", {}).get("emails", [])
    for e in emails:
        if e.get("value"):
            return e.get("value")   
    return None


def enrich_companies(file_path="qualified_company_list.csv"):
    """Enrich CSV with Apollo + Hunter data"""
    updated_rows = []
    with open(file_path, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        if "domain" not in fieldnames:
            fieldnames += ["domain", "phone", "emails", "response"]

        for row in reader:
            company_name = row.get("companyName") or row.get("name") or list(row.values())[0]
            details = fetch_company_details(company_name)
            if details:
                row["domain"] = details.get("domain")
                row["phone"] = details.get("phone")
                row["emails"] = fetch_emails_from_hunter(details["domain"])
            else:
                row["domain"], row["phone"], row["emails"] = None, None, None
            updated_rows.append(row)

    with open(file_path, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)
