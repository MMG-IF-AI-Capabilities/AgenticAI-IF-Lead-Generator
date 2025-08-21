import pandas as pd

def update_to_dummy():

    csv1 = pd.read_csv("dummy_phones.csv", dtype={"phone": str})
    csv2 = pd.read_csv("companies.csv", dtype={"phone": str})

    csv1.set_index("id", inplace=True)
    csv2.set_index("id", inplace=True)

    csv2.update(csv1[['phone']])

    csv2.to_csv("companies.csv", index=True)
