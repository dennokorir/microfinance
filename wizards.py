from openerp import models, fields, api
from datetime import datetime

class microfinance_loan_posting(models.TransientModel):
    _name = 'microfinance.loan.post'

    loan = fields.Many2one('microfinance.loan')
    paying_bank = fields.Many2one('res.bank')
    paying_account_no = fields.Char()
    amount = fields.Float()
    net_amount = fields.Float()

    @api.one
    def action_post(self):
        self.loan.action_post(self.paying_bank.id)
        '''
        if not self.loan.posted:
            #date
            today = datetime.now().strftime("%Y/%m/%d")
            setup = self.env['microfinance.setup'].search([('id','=',1)])
            #create journal header
            journal = self.env['account.journal'].search([('id','=',setup.loans_journal.id)]) #get journal id
            #period
            period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
            period_id = period.id

            journal_header = self.env['account.move']#reference to journal entry


            move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.loan.name,
                'date':today})

            move_id = move.id

            #create journal lines

            journal_lines = self.env['account.move.line']

            #loans = self.env['sacco.loan'].search([('batch_no','=',self.id)])

            member_ledger = self.env['microfinance.member.ledger.entry']
            #get last entry no
            ledgers = self.env['microfinance.member.ledger.entry'].search([])
            entries = [ledger.entry_no for ledger in ledgers]
            try:
                entry_no = max(entries)
            except:
                entry_no = 0

            #get required accounts for the transaction

            #setup = self.env['sacco.setup'].search([('id','=',1)])
            loan_acc = setup.loans_account.id
            bank = self.env['res.partner.bank'].search([('bank','=',self.paying_bank.id)])
            bank_acc = bank.journal_id.default_credit_account_id.id
            loan_interest_acc = setup.loan_interest_acc.id
            loan_interest_receivable_acc = setup.loan_interest_receivable_acc.id
            loan_processing_fee_acc = setup.loan_processing_fee_acc.id
            processing_rate = setup.processing_rate

            #this section allows for any charges applicable to your loan to be made
            processing_fee = 0.0
            processing_fee = (processing_rate*0.01)*self.amount
            amount_to_disburse = 0.0
            amount_to_disburse = self.amount - processing_fee
            #post loan journal
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.loan.name +'::'+self.loan.member_name,'account_id':loan_acc,'move_id':move_id,'debit':self.amount})#loan debtor
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.loan.name +'::'+self.loan.member_name,'account_id':bank_acc,'move_id':move_id,'credit':amount_to_disburse})#bank account
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.loan.name +'::'+self.loan.member_name+'::Processing Fees','account_id':loan_processing_fee_acc,'move_id':move_id,'credit':processing_fee})#processing fees
            self.loan.posted = True
            #post member ledger entry

            entry_no += 1
            member_ledger.create({'member_no':self.loan.member_no.id,'member_name':self.loan.member_name,'date':today,'transaction_no':self.loan.name,'transaction_name':'Loan Application','amount':self.amount,
            'transaction_type':'loan','entryno':entry_no})
        '''

class microfinance_member_application_wizard(models.TransientModel):
    _name = 'microfinance.member.application.wizard'

    member_application = fields.Many2one('microfinance.member.application')
    paying_bank = fields.Many2one('res.bank')
    amount = fields.Float()
    checklist_items = fields.One2many('microfinance.membership.checklist')



