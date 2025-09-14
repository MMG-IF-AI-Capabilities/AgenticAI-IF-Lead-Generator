import pandas as pd

def update_to_dummy():
    csv1 = pd.read_csv("dummy_phones.csv", dtype={"companyNumber": str})
    csv2 = pd.read_csv("qualified_company_list.csv", dtype={"companyNumber": str})

    csv1.set_index("companyNumber", inplace=True)
    csv2.set_index("companyNumber", inplace=True)

    csv2.update(csv1[['phone', 'emails']])

    csv2.to_csv("qualified_company_list.csv", index=True)

