member_ledger_transaction_type =          fields.Selection([('registration',"Registration Fee"),('membership',"Membership Fees"),('penalties',"Penalties"),('fines',"Fines"),('insurance',"Insurance"),('savings',"Savings"),('deposits',"Share Contribution"),('loan_fees',"Loan Processing Fees"),('loan',"Loan"),('interest',"Interest")])
table_lines_transaction_type =            fields.Selection([('registration',"Registration Fee"),('membership',"Membership Fees"),('penalties',"Penalties"),('fines',"Fines"),('insurance',"Insurance"),('savings',"Savings"),('deposits',"Share Contribution"),('loan_fees',"Loan Processing Fees"),('loan',"Loan"),('loan_repayment',"Loan Repayment"),('interest',"Interest on Loan"),('membership',"Membership Fees"),('bank_in',"Banking In"),('bank_out',"Banking Out")])
receipt_line_transaction_type =           fields.Selection([('registration',"Registration Fee"),('membership',"Membership Fees"),('penalties',"Penalties"),('fines',"Fines"),('insurance',"Insurance"),('savings',"Savings"),('deposits',"Share Contribution"),('repayment',"Loan Repayment")])
membership_checklist_transaction_type =   fields.Selection([('registration',"Registration Fee"),('membership',"Membership Fees"),('insurance',"Insurance")])
loan_fees_transaction_type =              fields.Selection([('loan_fees',"Loan Processing Fees")])


'penalties'
'savings'
'deposits'
'loan'
'interest'
