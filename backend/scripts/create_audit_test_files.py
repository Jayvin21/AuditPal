import os
import pandas as pd


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sample-data")
    os.makedirs(output_dir, exist_ok=True)

    purchase_rows = [
        {
            "Bill No": "INV-1001",
            "Bill Date": "01-04-2025",
            "Party Name": "Raj Traders",
            "Gross Amount": 48500,
            "GSTIN": "27ABCDE1234F1Z5",
            "Narration": "Office material purchase",
        },
        {
            "Bill No": "INV-1002",
            "Bill Date": "02-04-2025",
            "Party Name": "Mahavir Stationery",
            "Gross Amount": 18420,
            "GSTIN": "27PQRSX5678K1Z2",
            "Narration": "Stationery purchase",
        },
        {
            "Bill No": "INV-1002",
            "Bill Date": "02-04-2025",
            "Party Name": "Mahavir Stationery",
            "Gross Amount": 18420,
            "GSTIN": "27PQRSX5678K1Z2",
            "Narration": "Duplicate entry test case",
        },
        {
            "Bill No": "",
            "Bill Date": "04-04-2025",
            "Party Name": "Bright Computers",
            "Gross Amount": 65000,
            "GSTIN": "27LMNOP4321Q1Z9",
            "Narration": "Laptop purchase without invoice number",
        },
        {
            "Bill No": "INV-1005",
            "Bill Date": "31-03-2026",
            "Party Name": "Year End Suppliers",
            "Gross Amount": 100000,
            "GSTIN": "INVALIDGST123",
            "Narration": "Year-end high value purchase",
        },
        {
            "Bill No": "INV-1006",
            "Bill Date": "12-05-2025",
            "Party Name": "",
            "Gross Amount": 12000,
            "GSTIN": "",
            "Narration": "Missing party and GSTIN",
        },
        {
            "Bill No": "INV-1007",
            "Bill Date": "20-06-2025",
            "Party Name": "Cash Vendor",
            "Gross Amount": 0,
            "GSTIN": "27ABCDE1234F1Z5",
            "Narration": "Zero amount edge case",
        },
    ]

    messy_rows = [
        ["ABC Traders Pvt Ltd"],
        ["Purchase Register FY 2025-26"],
        [""],
        ["Voucher Number", "Posting Date", "Ledger Name", "Total", "GST No", "Details"],
        ["VR-01", "05-04-2025", "Alpha Suppliers", "25000", "27ABCDE1234F1Z5", "Regular purchase"],
        ["VR-02", "05-04-2025", "Alpha Suppliers", "25000", "27ABCDE1234F1Z5", "Repeated same vendor amount date"],
        ["VR-03", "30-03-2026", "March Supplier", "75000", "27PQRSX5678K1Z2", "Near year-end purchase"],
    ]

    standard_df = pd.DataFrame(purchase_rows)
    messy_df = pd.DataFrame(messy_rows)

    standard_path = os.path.join(output_dir, "purchase_register_edge_cases.xlsx")
    messy_path = os.path.join(output_dir, "messy_tally_purchase_export.xlsx")
    csv_path = os.path.join(output_dir, "purchase_register_edge_cases.csv")

    standard_df.to_excel(standard_path, index=False)
    standard_df.to_csv(csv_path, index=False)

    with pd.ExcelWriter(messy_path, engine="openpyxl") as writer:
        messy_df.to_excel(writer, index=False, header=False, sheet_name="Tally Export")

    print("Created test files:")
    print(standard_path)
    print(messy_path)
    print(csv_path)


if __name__ == "__main__":
    main()
