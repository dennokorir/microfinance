from openerp import models, fields, api
from datetime import datetime
from openerp.exceptions import ValidationError


class microfinance_loan_posting(models.TransientModel):
    _name = 'microfinance.loan.post'

    loan = fields.Many2one('microfinance.loan')
    paying_bank = fields.Many2one('res.bank')
    paying_account_no = fields.Char()
    amount = fields.Float()
    net_amount = fields.Float()
    loan_category = fields.Selection([('agri',"Agri-Booster Loan"),('table',"Table Banking Loan")])
    agribooster_fees = fields.One2many('microfinance.loan.fees.wizard','header_id')
    table_banking_fees = fields.One2many('microfinance.loan.fees.wizard','header_id2')
    fees = fields.Float(compute = 'calculate_fees')
    amount_received = fields.Float()

    @api.one
    def action_post(self):
        if self.amount_received != self.fees:
            raise ValidationError('Loan Cannot be disbursed without payment of applicable fees!')
        else:
            fees = []
            if self.loan_category == 'table':
                for line in self.table_banking_fees:
                    fees.append({'name':line.name, 'amount':line.amount, 'account':line.account.id, 'transaction_type':line.transaction_type})
            elif self.loan_category == 'agri':
                for line in self.agribooster_fees:
                    fees.append({'name':line.name, 'amount':line.amount, 'account':line.account.id, 'transaction_type':line.transaction_type})
            #raise ValidationError(fees)
            self.loan.action_post(self.paying_bank.id,fees)

    @api.onchange('loan_category')
    def get_fees(self):
        if self.loan_category == 'table':
            self.table_banking_fees.unlink()
            lines = []
            loan_type = self.env['microfinance.loan.types'].search([('id','=',self.loan.loan_type.id)])
            for line in loan_type.fees2:
                if line.based_on == 'fixed':
                    val = {'name':line.name,'amount':line.amount, 'account':line.account.id, 'transaction_type':line.transaction_type}
                    lines += [val]
                elif line.based_on == 'percentage':
                    amount = self.amount * line.percentage * 0.01
                    val = {'name':line.name,'amount':amount, 'account':line.account.id, 'transaction_type':line.transaction_type}
                    lines += [val]
            self.update({'table_banking_fees':lines})
        elif self.loan_category == 'agri':
            self.agribooster_fees.unlink()
            lines = []
            loan_product = self.env['microfinance.loan.products'].search([('id','=',self.loan.loan_product.id)])
            for line in loan_product.fees:
                if line.based_on == 'fixed':
                    val = {'name':line.name,'amount':line.amount, 'account':line.account.id, 'transaction_type':line.transaction_type}
                    lines += [val]
                elif line.based_on == 'percentage':
                    amount = self.amount * line.percentage * 0.01
                    val = {'name':line.name,'amount':amount, 'account':line.account.id, 'transaction_type':line.transaction_type}
                    lines += [val]
            self.update({'agribooster_fees':lines})

    @api.one
    @api.depends('loan_category','agribooster_fees','table_banking_fees')
    def calculate_fees(self):
        if self.loan_category == 'table':
            self.fees = sum(line.amount for line in self.table_banking_fees)
        elif self.loan_category == 'agri':
            self.fees = sum(line.amount for line in self.agribooster_fees)

class microfinance_loan_fees_wizard(models.TransientModel):
    _name = 'microfinance.loan.fees.wizard'
    header_id = fields.Many2one('microfinance.loan.post')
    header_id2 = fields.Many2one('microfinance.loan.post')
    name = fields.Char()
    account = fields.Many2one('account.account')
    transaction_type = fields.Selection([('loan_fees',"Loan Processing Fees")])
    amount = fields.Float()


class microfinance_member_application_wizard(models.TransientModel):
    _name = 'microfinance.member.application.wizard'

    application_no = fields.Char(string = 'Appliation No.')
    member_application = fields.Many2one('microfinance.member.application', string = 'Applicant')
    receiving_bank = fields.Many2one('res.bank', required = True)
    amount = fields.Float()
    #checklist_items = fields.One2many('microfinance.membership.checklist')

    @api.one
    def action_post(self):
        self.member_application.action_post(self.receiving_bank.id)

class microfinance_table_fines_wizard(models.TransientModel):
    _name = 'microfinance.table.fines'

    session = fields.Many2one('microfinance.table')
    group = fields.Many2one('microfinance.group')
    member = fields.Many2one('microfinance.member')
    fine = fields.Many2one('microfinance.charges.setup')
    bank = fields.Many2one('account.journal',domain = [('type','=','bank')])
    amount = fields.Float()

    @api.onchange('fine')
    def get_amount(self):
        self.amount = self.fine.amount

    @api.one
    def charge(self):
        #date
        if self.session.date:
            today = self.session.date
        else:
            today = datetime.now().strftime("%m/%d/%Y")
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        #create journal header
        journal = self.env['account.journal'].search([('id','=',setup.miscellaneous_journal.id)]) #get journal id
        #period
        period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
        period_id = period.id

        journal_header = self.env['account.move']#reference to journal entry

        move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.session.name+'::'+self.fine.charge_type+'::'+self.member.name,
            'date':today})
        move_id = move.id
        #create journal lines
        journal_lines = self.env['account.move.line']
        #get required accounts for the transaction
        #debit account
        bank = self.env['account.journal'].search([('id','=',self.session.bank.id)])
        bank_acc = bank.default_debit_account_id.id
        #credit account
        cr = self.fine.account.id

        member_ledger = self.env['microfinance.member.ledger.entry']
        ledgers = self.env['microfinance.member.ledger.entry'].search([])
        entries = [ledger.entryno for ledger in ledgers]
        try:
            entryno = max(entries)
        except:
            entryno = 0
        #post journal
        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.fine.description + '::' + self.member.name,'account_id':cr,'move_id':move_id,'credit':self.amount})
        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.fine.description + '::' + self.member.name,'account_id':bank_acc,'move_id':move_id,'debit':self.amount})
        #post member ledger entry
        entryno += 1
        member = self.env['microfinance.member'].search([('id','=',self.member.id)])
        member_name = member.name
        member_ledger.create({'member_no':self.member.id,'member_name':member_name,'date':today,'transaction_no':self.session.name,'transaction_name':self.fine.name + '::' + self.member.name,'amount':self.amount,'transaction_type':self.fine.charge_type,'entryno':entryno,'group_no':self.member.group_id.id, 'group_name':self.member.group_id.name})

        #post table session data
        #create_transaction(self,header_id, transaction_type, group, member, amount, direction)
        self.session.create_transaction(self.session.id,self.fine.charge_type,self.member.group_id.id, self.member.id, self.amount,'inward')

        move.post()




