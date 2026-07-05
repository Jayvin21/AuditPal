import os
import pandas as pd


def main():
    output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sample-data")
    os.makedirs(output_dir, exist_ok=True)

    bank_rows = [
        {
            "Transaction Date": "01-04-2025",
            "Narration": "NEFT PAYMENT RAJ TRADERS",
            "Debit": 48500,
            "Credit": "",
            "UTR": "UTR001",
        },
        {
            "Transaction Date": "02-04-2025",
            "Narration": "NEFT PAYMENT MAHAVIR STATIONERY",
            "Debit": 18420,
            "Credit": "",
            "UTR": "UTR002",
        },
        {
            "Transaction Date": "05-04-2025",
            "Narration": "CLIENT RECEIPT ABC CORP",
            "Debit": "",
            "Credit": 75000,
            "UTR": "UTR003",
        },
        {
            "Transaction Date": "08-04-2025",
            "Narration": "UNKNOWN PAYMENT",
            "Debit": 62000,
            "Credit": "",
            "UTR": "UTR004",
        },
        {
            "Transaction Date": "09-04-2025",
            "Narration": "DUPLICATE TEST PAYMENT",
            "Debit": 25000,
            "Credit": "",
            "UTR": "UTR005",
        },
        {
            "Transaction Date": "09-04-2025",
            "Narration": "DUPLICATE TEST PAYMENT",
            "Debit": 25000,
            "Credit": "",
            "UTR": "UTR006",
        },
    ]

    ledger_rows = [
        {
            "Voucher Date": "01-04-2025",
            "Particulars": "Payment to Raj Traders",
            "Debit": "",
            "Credit": 48500,
            "Voucher No": "PAY-001",
        },
        {
            "Voucher Date": "02-04-2025",
            "Particulars": "Payment Mahavir Stationery",
            "Debit": "",
            "Credit": 18420,
            "Voucher No": "PAY-002",
        },
        {
            "Voucher Date": "05-04-2025",
            "Particulars": "Receipt from ABC Corp",
            "Debit": 75000,
            "Credit": "",
            "Voucher No": "REC-001",
        },
        {
            "Voucher Date": "11-04-2025",
            "Particulars": "Books-only payment not in bank",
            "Debit": "",
            "Credit": 31000,
            "Voucher No": "PAY-999",
        },
    ]

    bank_path = os.path.join(output_dir, "bank_statement_edge_cases.xlsx")
    ledger_path = os.path.join(output_dir, "cash_bank_ledger_edge_cases.xlsx")

    pd.DataFrame(bank_rows).to_excel(bank_path, index=False)
    pd.DataFrame(ledger_rows).to_excel(ledger_path, index=False)

    print("Created bank reconciliation test files:")
    print(bank_path)
    print(ledger_path)


if __name__ == "__main__":
    main()