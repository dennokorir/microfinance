# -*- coding: utf-8 -*-

from openerp import models, fields, api
from datetime import datetime
from openerp.exceptions import ValidationError
from openerp.tools import amount_to_text_en
from openerp.tools.amount_to_text_en import amount_to_text


def next_date(startdate_param):
        """
        This next function calculates the next month with same date. If that date is larger than available dates for the
        following month, it gets the maximum date for that month:::>>>Author:dennokorir
        """
        #we create a dictionary for months against their max days
        months_structure = {1:31,2:28,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
        #start calculation
        start_date = datetime.strptime(str(startdate_param),'%Y-%m-%d').date()#start_date
        current_month = start_date.month
        current_year = start_date.year
        next_month = 0
        next_year = current_year
        if current_month == 12:
            next_month = 1
            next_year += 1
        else:
            next_month = current_month + 1

        #routine to ensure we do not exceed the number of days in the next month
        end_day = start_date
        current_day = start_date.day
        if current_day < months_structure[next_month]:
            end_day = start_date.replace(month = next_month, year = next_year)
        else:
            end_day = start_date.replace(day=months_structure[next_month],month=next_month, year = next_year)#months_structure[next_month] returns max days of next month
            #end_day = start_date.replace(month=next_month)
        return end_day

def calc_interest(amount,installments,interest,repayment_method):
        #this function calculates and returns interest and principal and risk for all calculation methods
        principal = 0.0
        interest_calculated = 0.0
        schedule = []
        if repayment_method == 'straight':
            loan_balance = 0.0
            principal = round((amount/installments),2)#each month
            monthly_principal = [principal for x in range(1,installments + 1 )]#creates a list of straigt line principals
            loan_balance += principal#poor way of making it start from the actual loan balance. Find a better way later
            monthly_balances = []
            for item in monthly_principal:
                loan_balance -= principal
            interest_calculated = round((principal*interest*0.01),2)
            monthly_interest = [interest_calculated for x in range(1,installments + 1 )]#creates a list of straigt line principals
            schedule = [monthly_principal,monthly_interest]
        elif repayment_method == 'reducing':
            loan_balance = amount
            principal = round((amount/installments),2)#monthly installments
            monthly_principal = [principal for x in range(1,installments + 1 )]
            loan_balance += principal#poor way of making it start from the actual loan balance. Find a better way later
            monthly_balances = []
            for item in monthly_principal:
                loan_balance -= principal
                monthly_balances.append(loan_balance)
            monthly_interest = [round((x*interest/1200),2) for x in monthly_balances]
            schedule = [monthly_principal,monthly_interest]
        elif repayment_method == 'amortized':
            loan_balance = amount
            monthly_principal = []
            monthly_interest = []
            monthly_rate = interest/1200
            monthly_repayment_amount = (monthly_rate/(1-(1+monthly_rate)**-installments))*amount
            for item in range(1,installments + 1):
                principal = monthly_repayment_amount - (loan_balance*interest/1200)
                monthly_principal.append(round(principal,2))
                monthly_interest.append(round((loan_balance*interest/1200),2))
                loan_balance -= principal
            schedule = [monthly_principal,monthly_interest]

        return schedule

class microfinance_member_application(models.Model):
    _name = 'microfinance.member.application'

    no = fields.Char()
    name = fields.Char()
    group_id = fields.Many2one('microfinance.group', string = "Group")
    application_date = fields.Date(default=fields.date.today())
    employer_code = fields.Many2one('microfinance.employers')
    id_no = fields.Char()
    pin = fields.Char()
    gender = fields.Selection([('male',"Male"),('female',"Female")])
    occupation = fields.Char()
    mobile = fields.Char()
    email = fields.Char()
    created = fields.Boolean()
    table_session_id = fields.Many2one('microfinance.table')
    user_id = fields.Many2one('res.users', string = 'Field Officer')
    membership_checklist = fields.One2many('microfinance.membership.checklist','application_id')
    membership_fees_paid = fields.Boolean()
    membership_fees = fields.Float(compute = 'compute_total_on_checklist')
    state = fields.Selection([('draft',"Draft"),('ready',"Ready"),('complete',"Complete")], default = 'draft')
    member = fields.Many2one('microfinance.member')
    user_id = fields.Many2one('res.users', default = lambda self: self.env.user, string = 'Field Officer')

    @api.onchange('table_session_id')
    def get_group(self):
        self.group_id = self.table_session_id.group.id


    @api.one
    @api.onchange('no')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.member_application_nos.id)])
        self.no = sequence.next_by_id(sequence.id, context = None)

        #get membership_checklist
        self.membership_checklist.unlink()
        lines = []
        for line in setup.membership_checklist:
            val = {'name':line.name,'account':line.account.id,'amount':line.amount}
            lines += [val]
        self.update({'membership_checklist':lines})

    @api.one
    def create_member(self):
        #if self.state == 'complete'
        member = self.env['microfinance.member'].create({'name':self.name,'group_id':self.group_id.id, 'id_no':self.id_no,
            'pin':self.pin, 'gender':self.gender, 'occupation':self.occupation, 'mobile':self.mobile, 'email':self.email,'state':'draft'})
        member.get_sequence()
        self.member = member.id

    @api.one
    @api.depends('membership_checklist')
    def compute_total_on_checklist(self):
        self.membership_fees = sum(line.amount for line in self.membership_checklist)

    @api.one
    def validate_membership(self):
        #create session transactions and accounting entries.
        #collect required accounts again in case of an error or additional setup
        checklist_items = self.env['microfinance.membership.checklist.setup'].search([])
        for line in checklist_items:
            checklist_item = self.env['microfinance.membership.checklist'].search([('application_id','=',self.id),('name','=',line.name)])
            if len(checklist_item) > 0:
                checklist_item.transaction_type = line.transaction_type
                checklist_item.amount = line.amount
                checklist_item.account = line.account.id
            else:
                new_checklist_item = {'application_id':self.id,'name':line.name,'transaction_type':line.transaction_type,'account':line.account.id,'amount':line.amount}
                self.env['microfinance.membership.checklist'].create(new_checklist_item)

        self.state = 'ready'
        self.create_member()#create account at this point but leave it as being inactive

    @api.one
    def action_post(self, receiving_bank):
        #start processing available lines
        #ensure all amounts are as per setup and all accounts are avaible as well as transaction types
        for line in self.membership_checklist:
            if not (line.transaction_type and line.account and line.amount):
                raise ValidationError('One or more items is not correctly setup in the Membership Checklist!')
            if line.amount != line.paid:
                raise ValidationError('Checklist item amount and paid must be equal!')

        if not self.membership_fees_paid:
            #date
            if self.application_date:
                today = self.application_date
            else:
                today = datetime.now().strftime("%Y/%m/%d")
            setup = self.env['microfinance.setup'].search([('id','=',1)])
            #create journal header
            journal = self.env['account.journal'].search([('id','=',setup.loans_journal.id)]) #get journal id
            #period
            period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
            period_id = period.id

            journal_header = self.env['account.move']#reference to journal entry


            move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.name,
                'date':today})

            move_id = move.id

            #create journal lines
            journal_lines = self.env['account.move.line']
            member_ledger = self.env['microfinance.member.ledger.entry']
            #get last entry no
            ledgers = self.env['microfinance.member.ledger.entry'].search([])
            entries = [ledger.entryno for ledger in ledgers]
            try:
                entryno = max(entries)
            except:
                entryno = 0

            #dr
            bank = self.env['res.partner.bank'].search([('bank','=',receiving_bank)])
            bank_acc = bank.journal_id.default_credit_account_id.id
            for line in self.membership_checklist:
                #cr
                cr = line.account.id
                journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member.name,'account_id':bank_acc,'move_id':move_id,'debit':line.amount})
                journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member.name,'account_id':cr,'move_id':move_id,'credit':line.amount})
                #post member ledger entry
                entryno += 1
                member_ledger.create({'member_no':self.member.id,'member_name':self.member.name,'date':today,'transaction_no':self.name,'transaction_name':line.name,'amount':line.amount,
                'transaction_type':line.transaction_type,'entryno':entryno,'group_no':self.group_id.id, 'group_name':self.group_id.name,'date':today})
                #post table session data
                #create_transaction(self,header_id, transaction_type, group, member, amount, direction)
                self.table_session_id.create_transaction(self.table_session_id.id,line.transaction_type,self.member.group_id.id, self.member.id, line.amount,'inward')

            self.state = 'complete'
            self.member.state = 'open'#activate account and make it visible in member list
            membership_fees_paid = True


class microfinance_member_registration_checklist_setup(models.Model):
    _name = 'microfinance.membership.checklist.setup'

    name = fields.Char()
    transaction_type =   fields.Selection([('registration',"Registration Fee"),('insurance',"Insurance"),('membership',"Membership Fees")])
    account = fields.Many2one('account.account')
    amount = fields.Float()
    setup_id = fields.Many2one('microfinance.setup')

class microfinance_member_registration_checklist(models.Model):
    _name = 'microfinance.membership.checklist'
    _inherit = 'microfinance.membership.checklist.setup'

    paid = fields.Float()
    balance = fields.Float()
    application_id = fields.Many2one('microfinance.member.application')

class microfinance_group_application(models.Model):
    _name = 'microfinance.group.application'

    no = fields.Char(string = 'No.')
    name = fields.Char(string='Name')
    application_date = fields.Date()
    group_members = fields.One2many('microfinance.group.member','application_id')
    reg_no = fields.Char()
    date_of_registration = fields.Date()
    constituency = fields.Char()
    district = fields.Char()
    location = fields.Char()
    bank_name = fields.Char()
    bank_branch = fields.Char()
    account_no = fields.Char()
    signatories = fields.Char()
    created = fields.Boolean()
    state = fields.Selection([('draft',"Draft"),('ready',"Ready"),('complete',"Complete")], default = 'draft')

    @api.one
    @api.onchange('no')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.group_application_nos.id)])
        self.no = sequence.next_by_id(sequence.id, context = None)

    @api.one
    def create_group(self):
        group = self.env['microfinance.group'].create({'name':self.name,'reg_no':self.reg_no,'date_of_registration':self.date_of_registration,'constituency':self.constituency,'district':self.district,'location':self.location,
            'bank_name':self.bank_name,'bank_branch':self.bank_branch,'account_no':self.account_no})
        group.get_sequence()
        for item in self.group_members:
            member = self.env['microfinance.member'].create({'name':item.name,'gender':item.gender,'dob':item.dob,'id_no':item.id_no,'mobile':item.mobile_no,'email':item.email,'group_id':group.id})
            member.get_sequence()


class microfinance_member(models.Model):
    _name = 'microfinance.member'

    no = fields.Char(string = 'No.')
    name = fields.Char()
    registration_date = fields.Date()
    employer_code = fields.Many2one('microfinance.employers')
    staff_no = fields.Char()
    id_no = fields.Char()
    pin = fields.Char()
    dob = fields.Date()
    gender = fields.Selection([('male',"Male"),('female',"Female")])
    occupation = fields.Char()
    mobile = fields.Char()
    email = fields.Char()
    loan_ids = fields.One2many('microfinance.loan','member_no')
    loans = fields.Float(compute = 'compute_loan_stats')
    group_id = fields.Many2one('microfinance.group', string = "Group")
    state = fields.Selection([('draft',"Innactive"),('open',"Active"),('closed',"Closed")], default = 'draft')


    @api.one
    @api.onchange('no')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.member_nos.id)])
        self.no = sequence.next_by_id(sequence.id, context = None)

    @api.one
    @api.depends('loan_ids')
    def compute_loan_stats(self):
        self.loans = sum(loan.balance for loan in self.loan_ids)

class microfinance_group(models.Model):
    _name = 'microfinance.group'

    no = fields.Char(string = 'No.')
    name = fields.Char(string='Name')
    group_members = fields.One2many('microfinance.member','group_id')
    reg_no = fields.Char()
    date_of_registration = fields.Date()
    constituency = fields.Char()
    district = fields.Char()
    location = fields.Char()
    bank_name = fields.Char()
    bank_branch = fields.Char()
    account_no = fields.Char()
    signatories = fields.Char()
    loan_ids = fields.One2many('microfinance.loan','group_no')
    loans = fields.Float()
    state = fields.Selection([('draft',"Draft"),('ready',"Ready"),('complete',"Complete")], default = 'draft')

    @api.one
    @api.onchange('no')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.group_nos.id)])
        self.no = sequence.next_by_id(sequence.id, context = None)

class microfinance_group_members(models.Model):
    _name = 'microfinance.group.member'

    application_id = fields.Many2one('microfinance.member.application')
    group_id = fields.Many2one('microfinance.group')
    name = fields.Char()
    dob = fields.Date(string = 'Date of Birth')
    id_no = fields.Char()
    mobile_no = fields.Char()
    designation = fields.Char()
    signature = fields.Binary()
    email = fields.Char()
    gender = fields.Selection([('male',"Male"),('female',"Female")])

class microfinance_loan(models.Model):
    _name = 'microfinance.loan'

    name = fields.Char(string = 'No.')
    application_date = fields.Date()
    user_id = fields.Many2one('res.users', default = lambda self: self.env.user)
    group = fields.Many2one('microfinance.group')
    member_no = fields.Many2one('microfinance.member')
    member_name = fields.Char(string = 'Member Name')
    group_no = fields.Many2one('microfinance.group')
    group_name = fields.Char(string = 'Group Name')
    employer_code = fields.Many2one('microfinance.employers')
    staff_no = fields.Char()
    loan_batch = fields.Many2one('microfinance.loan.batch')
    requested_amount = fields.Float()
    approved_amount = fields.Float()
    balance = fields.Float(compute = 'compute_loan_stats', string = 'Principal Balance')
    interest_balance = fields.Float(compute = 'compute_loan_stats')
    balance_due = fields.Float()
    interest_due = fields.Float()
    loan_purpose = fields.Text()
    posted = fields.Boolean()
    loan_category = fields.Selection([('table',"Table Banking Loans"),('agri',"Agri-Booster Loans")], default = 'table')
    loan_type = fields.Many2one('microfinance.loan.types')#for table banking
    loan_product = fields.Many2one('microfinance.loan.products')#for agribooster
    installments = fields.Integer()
    scale = fields.Many2one('microfinance.scales')
    interest = fields.Float(string = 'Expected Income')
    interest_rate = fields.Float()
    posting = fields.Selection([('individual',"Individual"),('batch',"Batch")], default = 'individual')
    matrix = fields.Many2one('microfinance.product.scale.matrix')
    schedule_ids = fields.One2many('microfinance.loan.repayment.schedule', 'loan_id')
    table_session_id = fields.Many2one('microfinance.table', string = 'Table Session')

    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.loan_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

    @api.onchange('member_no')
    def populate_member(self):
        if self.member_no:
            self.member_name = self.member_no.name
            #self.employer_code = self.member_no.employer_code.id
            #self.staff_no = self.member_no.staff_no

    @api.onchange('table_session_id')
    def get_group(self):
        self.group = self.table_session_id.group.id

    @api.onchange('loan_product','scale')
    def get_loan_product_amount(self):
        if self.loan_product and self.scale:
            matrix = self.env['microfinance.product.scale.matrix'].search([('product.id','=',self.loan_product.id),('scale.id','=',self.scale.id)])
            if len(matrix)>0:
                #self.matrix.id = matrix.id
                self.approved_amount = matrix.total_input
                self.interest = matrix.margin
                self.installments = self.loan_product.installments
            else:
                raise ValidationError('Matrix with Product::' + self.loan_product.name +' and scale::' + self.scale.name +' does not exist. Please create one')

    @api.onchange('loan_type')
    def get_loan_types_details(self):
        self.interest_rate = self.loan_type.interest_rate
        self.installments = self.loan_type.installments

    @api.one
    @api.depends('posted')
    def compute_loan_stats(self):
        if self.posted:
            ledgers = self.env['microfinance.member.ledger.entry'].search([('transaction_no','=',self.name)])
            self.balance = sum(ledger.amount for ledger in ledgers if ledger.transaction_type == 'loan')
            self.interest_balance = sum(ledger.amount for ledger in ledgers if ledger.transaction_type == 'interest')

    @api.one
    def action_post(self, paying_bank,fees):
        if not self.posted:
            #date
            if self.application_date:
                today = self.application_date
            else:
                today = datetime.now().strftime("%Y/%m/%d")
            setup = self.env['microfinance.setup'].search([('id','=',1)])
            #create journal header
            journal = self.env['account.journal'].search([('id','=',setup.loans_journal.id)]) #get journal id
            #period
            period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
            period_id = period.id

            journal_header = self.env['account.move']#reference to journal entry


            move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.name,
                'date':today})

            move_id = move.id

            #create journal lines

            journal_lines = self.env['account.move.line']

            member_ledger = self.env['microfinance.member.ledger.entry']
            #get last entry no
            ledgers = self.env['microfinance.member.ledger.entry'].search([])
            entries = [ledger.entryno for ledger in ledgers]
            try:
                entryno = max(entries)
            except:
                entryno = 0

            #get required accounts for the transaction
            loan_acc = setup.loans_account.id
            bank = self.env['res.partner.bank'].search([('bank','=',paying_bank)])
            bank_acc = bank.journal_id.default_credit_account_id.id
            loan_interest_acc = setup.loan_interest_acc.id
            loan_interest_receivable_acc = setup.loan_interest_receivable_acc.id

            #receipt processing fees and create table transactions
            for line in fees:
                #post fees journal
                #raise ValidationError(fees)
                journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+ line['name'] +'::'+ self.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':line['amount']})
                journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+ line['name'] +'::'+ self.member_no.name,'account_id':line['account'],'move_id':move_id,'credit':line['amount']})

                #create member ledger transaction
                entryno += 1
                #fees
                member_ledger.create({'member_no':self.member_no.id,'member_name':self.member_no.name,'date':today,'transaction_no':self.name,'transaction_name':self.name + '::' + line['name'],'amount':line['amount'],
                'transaction_type':line['transaction_type'],'entryno':entryno,'group_no':self.group.id, 'group_name':self.group.name,'date':today})

                #create table transaction
                #create_transaction(self,header_id, transaction_type, group, member, amount, direction)
                self.table_session_id.create_transaction(self.table_session_id.id,line['transaction_type'],self.member_no.group_id.id, self.member_no.id, line['amount'],'inward')

            #post loan disbursement
            amount_to_disburse = 0.0
            interest = 0.0
            interest = self.interest#approved_amount*self.loan_type.interest_rate*0.01
            #post loan journal
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_no.name,'account_id':loan_acc,'move_id':move_id,'debit':self.approved_amount})#loan debtor
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_no.name,'account_id':bank_acc,'move_id':move_id,'credit':self.approved_amount})#bank account
            #journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_name+'::Processing Fees','account_id':loan_processing_fee_acc,'move_id':move_id,'credit':processing_fee})#processing fees
            #post interest receivable
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_no.name+'::Loan interest','account_id':loan_interest_receivable_acc,'move_id':move_id,'debit':interest})
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_no.name+'::Loan interest','account_id':loan_interest_acc,'move_id':move_id,'credit':interest})
            self.posted = True
            #post member ledger entry

            entryno += 1
            #loan
            member_ledger.create({'member_no':self.member_no.id,'member_name':self.member_no.name,'date':today,'transaction_no':self.name,'transaction_name':'Loan Application','amount':self.approved_amount,
            'transaction_type':'loan','entryno':entryno,'group_no':self.group.id, 'group_name':self.group.name,'date':today})
            #interest
            entryno += 1
            member_ledger.create({'member_no':self.member_no.id,'member_name':self.member_no.name,'date':today,'transaction_no':self.name,'transaction_name':'Loan Interest Due','amount':interest,
            'transaction_type':'interest','entryno':entryno,'group_no':self.group.id, 'group_name':self.group.name,'date':today})

            #post table session data
            #create_transaction(self,header_id, transaction_type, group, member, amount, direction)
            self.table_session_id.create_transaction(self.table_session_id.id,'loan',self.member_no.group_id.id, self.member_no.id, self.approved_amount,'outward')

    @api.one
    def generate_schedule(self):
        #delete first then generate schedule
        if self.application_date:
            self.env['microfinance.loan.repayment.schedule'].search([('loan_id','=',self.id)]).unlink()
            repayment_schedule = self.env['microfinance.loan.repayment.schedule']
            if self.loan_category == 'agri':
                loan_product = self.env['microfinance.loan.products'].search([('id','=',self.loan_product.id)])
            else:
                loan_product = self.env['microfinance.loan.types'].search([('id','=',self.loan_type.id)])
            loan_schedule = calc_interest(self.approved_amount,self.installments,self.interest_rate,loan_product.repayment_method)
            principal = loan_schedule[0]
            interest = loan_schedule[1]
            self.interest = sum(loan_schedule[1])
            start_date = self.application_date
            installment = 0
            balance = self.approved_amount
            for item in principal:
                installment += 1
                schedule_period_paid = next_date(start_date)
                start_date = next_date(start_date)#increment for next loop
                repayment_schedule.create({'loan_id':self.id,'installment':installment,'period_paid':schedule_period_paid,'loan_balance':balance,'principal':item,'interest':interest[installment-1]})
                balance -= item
        else:
            raise exceptions.ValidationError("Application date must have a value before generating schedule")

class microfinance_loan_batch(models.Model):
    _name = 'microfinance.loan.batch'

    name = fields.Char()
    date = fields.Date()
    paying_bank = fields.Many2one('res.bank')
    amount = fields.Float()
    posted = fields.Boolean()
    line_ids = fields.One2many('microfinance.loan','loan_batch')

    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.loan_batch_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

    @api.one
    def action_post(self):
        for line in self.line_ids:
            if not line.posted:
                line.action_post(self.paying_bank.id)

class microfinance_loan_advice(models.Model):
    _name = 'microfinance.loan.advice'

    name = fields.Char(string = 'No.')
    date = fields.Date()
    amount = fields.Float()
    line_ids = fields.One2many('microfinance.loan.advice.lines','header_id')

    @api.one
    def generate_advice(self):
        self.line_ids.unlink()
        loans = self.env['microfinance.loan'].search([('posted','=',True),('balance','>',0)])
        for loan in loans:
            total = 0.0
            interest_ledger = self.env['microfinance.member.ledger.entry'].search([('transaction_no','=',loan.name),('transaction_type','=','interest')])
            interest = 0.0
            interest = sum(interest_ledger.amount for ledger in interest_ledger)
            loan_amount = 0.0
            loan_ledger = self.env['microfinance.member.ledger.entry'].search([('transaction_no','=',loan.name),('transaction_type','=','loan')])
            loan_amount = sum(loan_ledger.amount for ledger in loan_ledger)
            total = loan_amount + interest
            self.env['microfinance.loan.advice.lines'].create({'header_id':self.id,'loan_no':loan.id,'employer':loan.employer_code.id,
                'member_no':loan.member_no.id,'member_name':loan.member_name,'loan':loan_amount,'interest':interest,'amount':total})

class microfinance_loan_advice_lines(models.Model):
    _name = 'microfinance.loan.advice.lines'

    header_id = fields.Many2one('microfinance.loan.advice')
    loan_no = fields.Many2one('microfinance.loan')
    employer = fields.Many2one('microfinance.employers')
    member_no = fields.Many2one('microfinance.member')
    member_name = fields.Char()
    loan = fields.Float()
    interest = fields.Float()
    amount = fields.Float(string = 'Total')

class microfinance_checkoff(models.Model):
    _name = 'microfinance.checkoff.header'

    name = fields.Char()
    date = fields.Date()
    amount = fields.Float()
    line_ids = fields.One2many('microfinance.checkoff.lines','header_id')

    @api.one
    def validate_checkoff(self):
        pass

    def action_post(self):
        pass

class microfinance_checkoff_lines(models.Model):
    _name = 'microfinance.checkoff.lines'

    header_id = fields.Many2one('microfinance.checkoff.header')
    loan_no = fields.Many2one('microfinance.loan')
    member_no = fields.Many2one('microfinance.member')
    member_name = fields.Char()
    loan_amount = fields.Float()
    amount = fields.Float()

class microfinance_loan_products(models.Model):
    #reserve this for agri-booster loans
    _name = 'microfinance.loan.products'

    name = fields.Char()
    description = fields.Char()
    interest_rate = fields.Float()
    installments = fields.Integer()
    loan_product_input_ids = fields.One2many('microfinance.loan.product.inputs', 'loan_product')
    repayment_method = fields.Selection([('straight',"Straight")], default = 'straight')
    fees = fields.One2many('microfinance.loan.fees','header_id')#for agribooster loans


class microfinance_loan_types(models.Model):
    #reserve for normal table banking loans
    _inherit = 'microfinance.loan.products'
    _name = 'microfinance.loan.types'

    field = fields.Char()
    fees2 = fields.One2many('microfinance.loan.fees','header_id2')#for table banking loans

class microfinance_loan_fees(models.Model):
    _name = 'microfinance.loan.fees'

    header_id = fields.Many2one('microfinance.loan.products')#for agribooster loans
    header_id2 = fields.Many2one('microfinance.loan.types')#for table banking loans
    name = fields.Char()
    transaction_type = fields.Selection([('loan_fees',"Loan Processing Fees")], default = 'loan_fees')
    account = fields.Many2one('account.account')
    based_on = fields.Selection([('percentage',"Percentage"),('fixed',"Fixed")], default = 'fixed', requred = True)
    percentage = fields.Float()
    amount = fields.Float()


class microfinance_loan_product_inputs(models.Model):
    _name = 'microfinance.loan.product.inputs'

    loan_product = fields.Many2one('microfinance.loan.product')
    name = fields.Many2one('microfinance.farm.input')

class microfinance_loan_product_output(models.Model):
    _name = 'microfinance.loan.product.output'

    name = fields.Char()
    #matrix_id = fields.Many2one('microfinance.product.scale.matrix')

class microfinance_farm_input(models.Model):
    _name = 'microfinance.farm.input'

    name = fields.Char()
    description = fields.Text()
    #matrix_id = fields.Many2one('microfinance.product.scale.matrix')

class microfinance_product_scale_matrix(models.Model):
    _name = 'microfinance.product.scale.matrix'

    product = fields.Many2one('microfinance.loan.products')
    scale = fields.Many2one('microfinance.scales')
    farm_inputs = fields.One2many('microfinance.product.scale.matrix.input', 'matrix_id')
    farm_output = fields.One2many('microfinance.product.scale.matrix.output', 'matrix_id')
    total_input = fields.Float(compute='compute_totals')
    total_output = fields.Float(compute='compute_totals')
    margin = fields.Float(compute='compute_totals')
    percentage_margin = fields.Float()

    @api.onchange('product')
    def get_product_inputs(self):
        self.farm_inputs.unlink()
        lines = []
        farm_output = [self.product.id]
        #val = {}
        for line in self.product.loan_product_input_ids:
            val = {'farm_input':line.name.id}
            lines += [val]
        self.update({'farm_inputs':lines})
        #self.update({'farm_output':farm_output})

    @api.onchange('total_input','total_output')
    def compute_percentage_margin(self):
        if self.total_input > 0 and self.margin:
            self.percentage_margin = (self.margin/self.total_input)*100

    @api.one
    @api.depends('farm_inputs','farm_output')
    def compute_totals(self):
        self.total_input = sum(line.total for line in self.farm_inputs)
        self.total_output = sum(line.total for line in self.farm_output)
        self.margin = self.total_output - self.total_input

class microfinance_product_scale_matrix_input(models.Model):
    _name = 'microfinance.product.scale.matrix.input'

    name = fields.Char()
    matrix_id = fields.Many2one('microfinance.product.scale.matrix')
    farm_input = fields.Many2one('microfinance.farm.input')
    quantity = fields.Float()
    cost = fields.Float()
    uom = fields.Char()
    total = fields.Float()

    @api.onchange('quantity','cost')
    def compute_total(self):
        if self.quantity and self.cost:
            self.total = self.quantity * self.cost

class microfinance_product_scale_matrix_output(models.Model):
    _name = 'microfinance.product.scale.matrix.output'

    name = fields.Char()
    matrix_id = fields.Many2one('microfinance.product.scale.matrix')
    farm_output = fields.Many2one('microfinance.loan.products')
    quantity = fields.Float()
    price = fields.Float()
    uom = fields.Char()
    total = fields.Float()

    @api.onchange('quantity','price')
    def compute_total(self):
        if self.quantity and self.price:
            self.total = self.quantity * self.price

class microfinance_scales(models.Model):
    _name = 'microfinance.scales'

    name = fields.Char()

class microfinance_setup(models.Model):
    _name = 'microfinance.setup'

    name = fields.Char()
    member_application_nos = fields.Many2one('ir.sequence')
    group_application_nos = fields.Many2one('ir.sequence')
    member_nos = fields.Many2one('ir.sequence')
    group_nos = fields.Many2one('ir.sequence')
    loan_nos = fields.Many2one('ir.sequence')
    loan_batch_nos = fields.Many2one('ir.sequence')
    loan_advice_nos = fields.Many2one('ir.sequence')
    checkoff_nos = fields.Many2one('ir.sequence')
    receipt_nos = fields.Many2one('ir.sequence')
    payment_nos = fields.Many2one('ir.sequence')
    table_session_nos = fields.Many2one('ir.sequence')
    miscellaneous_journal = fields.Many2one('account.journal')
    loans_journal = fields.Many2one('account.journal')
    loans_account = fields.Many2one('account.account')
    loan_interest_acc = fields.Many2one('account.account')
    loan_interest_receivable_acc = fields.Many2one('account.account')
    loan_processing_fee_acc = fields.Many2one('account.account')
    processing_rate = fields.Float()
    registration_fee_acc = fields.Many2one('account.account')
    deposits_account = fields.Many2one('account.account')
    shares_account = fields.Many2one('account.account')
    savings_account = fields.Many2one('account.account')
    penalties_account = fields.Many2one('account.account')
    insurance_account = fields.Many2one('account.account')
    membership_checklist = fields.One2many('microfinance.membership.checklist.setup','setup_id')

class microfinance_employer(models.Model):
    _name = 'microfinance.employers'

    name = fields.Char()
    address1 = fields.Char()
    address2 = fields.Char()
    phone = fields.Char()
    mobile = fields.Char()
    email = fields.Char()
    no_of_employees = fields.Integer()
    employees = fields.One2many('microfinance.member','employer_code')
    loans = fields.One2many('microfinance.loan','employer_code')

class microfinance_member_ledger(models.Model):
    _name = 'microfinance.member.ledger.entry'

    entryno = fields.Integer()
    date = fields.Date()
    member_no = fields.Many2one('microfinance.member')
    member_name = fields.Char()
    group_no = fields.Many2one('microfinance.group')
    group_name = fields.Char()
    transaction_type = fields.Selection([('registration',"Registration Fee"),('membership',"Membership Fees"),('penalties',"Penalties"),('fines',"Fines"),('insurance',"Insurance"),('savings',"Savings"),('deposits',"Share Contribution"),('loan_fees',"Loan Processing Fees"),('loan',"loan"),('interest',"Interest")])
    transaction_no = fields.Char()
    amount = fields.Float()
    dr = fields.Float()
    cr = fields.Float()

class repayment_schedule(models.Model):
    _name = 'microfinance.loan.repayment.schedule'

    loan_id = fields.Many2one('microfinance.loan')
    installment = fields.Integer()
    period_paid = fields.Char()
    loan_balance = fields.Float()
    principal = fields.Float()
    interest = fields.Float()
    total = fields.Float(compute = 'sum_total')#
    principal_paid = fields.Boolean()#compute = 'check'
    interest_paid = fields.Boolean()#compute = 'check'

    @api.one
    @api.depends('principal','interest')
    def sum_total(self):
        self.total = self.principal + self.interest

class receipt_header(models.Model):
    _name = 'microfinance.receipt.header'

    name = fields.Char()
    date = fields.Date(default=fields.date.today())
    table_session_id = fields.Many2one('microfinance.table')
    group = fields.Many2one('microfinance.group')
    member = fields.Many2one('microfinance.member')
    bank_code = fields.Many2one('account.journal',domain = [('type','=','bank')])
    bank_name = fields.Char()
    amount_received = fields.Float(compute = 'compute_total')#
    received_from = fields.Char()
    cashier = fields.Many2one('res.users', default=lambda self: self.env.user, readonly = True)
    posted = fields.Boolean()
    amount_words = fields.Char(compute = 'compute_total')
    line_ids = fields.One2many('microfinance.receipt.line','no')

    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.receipt_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

    @api.onchange('table_session_id')
    def get_group(self):
        self.group = self.table_session_id.group.id

    @api.one
    @api.onchange('bank_code')
    def get_bank(self):
        #get bank name
        bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
        self.bank_name = bank.name


    @api.onchange('member')
    def correct_lines(self):
        lines = self.env['microfinance.receipt.line'].search([('no','=',self.id)])
        lines.write({'member':self.member.id})


    @api.one
    def action_post(self):
        if not self.posted:
            #date
            if self.date:
                today = self.date
            else:
                today = datetime.now().strftime("%m/%d/%Y")
            setup = self.env['microfinance.setup'].search([('id','=',1)])
            #create journal header
            journal = self.env['account.journal'].search([('id','=',setup.miscellaneous_journal.id)]) #get journal id
            #period
            period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
            period_id = period.id

            journal_header = self.env['account.move']#reference to journal entry


            move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.name,
                'date':today})

            move_id = move.id

            #create journal lines
            journal_lines = self.env['account.move.line']

            #get required accounts for the transaction
            #debit account
            bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
            bank_acc = bank.default_debit_account_id.id

            member_ledger = self.env['microfinance.member.ledger.entry']

            ledgers = self.env['microfinance.member.ledger.entry'].search([])
            entries = [ledger.entryno for ledger in ledgers]
            try:
                entryno = max(entries)
            except:
                entryno = 0
            #post journal

            for line in self.line_ids:
                #credit account
                credit_acc = 0
                entry_type = ''
                transaction_name = ''
                create_ledger = False
                factor = 1 #we'll use this to choose whether the entry made on the member ledger is positive or negative
                if line.transaction_type == 'registration':
                    #registration fee account
                    create_ledger = False
                    credit_acc = setup.registration_fee_acc.id
                    transaction_no = self.name
                    transaction_name = 'Member Registration'
                elif line.transaction_type == 'deposits':
                    #liability account
                    credit_acc = setup.deposits_account.id
                    entry_type = 'deposits'
                    transaction_name = 'Member Deposits'
                    create_ledger = True
                    transaction_no = self.name
                elif line.transaction_type == 'unallocated':
                    #liability account
                    credit_acc = setup.unallocated_funds.id
                    entry_type = 'unallocated'
                    transaction_name = 'Online Receipts'
                    create_ledger = True
                    transaction_no = self.name
                elif line.transaction_type == 'shares':
                    #shares account
                    credit_acc = setup.shares_account.id
                    entry_type = 'shares'
                    transaction_name = 'Member Shares'
                    create_ledger = True
                    transaction_no = self.name
                elif line.transaction_type == 'savings':
                    #savings account
                    credit_acc = setup.savings_account.id
                    entry_type = 'savings'
                    transaction_name = 'Member Savings'
                    create_ledger = True
                    transaction_no = self.name
                elif line.transaction_type == 'penalties':
                    #penalties account
                    credit_acc = setup.penalties_account.id
                    entry_type = 'penalties'
                    transaction_name = 'Member Penalties'
                    create_ledger = True
                    transaction_no = self.name
                elif line.transaction_type == 'insurance':
                    #insurance account
                    credit_acc = setup.insurance_account.id
                    entry_type = 'insurance'
                    transaction_name = 'Insurance'
                    create_ledger = True
                    transaction_no = self.name
                elif line.transaction_type == 'repayment':
                    #debtor account
                    loan = self.env['microfinance.loan'].search([('id','=',line.loan_no.id)])
                    credit_acc = setup.loans_account.id
                    entry_type = 'loan'
                    transaction_name = 'Loan Repayment'
                    create_ledger = True
                    transaction_no = loan.name
                    factor = -1
                else:
                    credit_acc = 0


                #quick bad solution
                if line.transaction_type != 'repayment':
                    journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':credit_acc,'move_id':move_id,'credit':line.amount})
                    journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(line.amount)})
                    #post member ledger entry
                    if create_ledger:
                        entryno += 1
                        member = self.env['microfinance.member'].search([('id','=',line['member_no'].id)])
                        member_name = member.name
                        member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':factor*line.amount,'transaction_type':entry_type,'entryno':entryno,'group_no':line.group.id, 'group_name':line.group.name})

                        #post table session data
                        #create_transaction(self,header_id, transaction_type, group, member, amount, direction)
                        self.table_session_id.create_transaction(self.table_session_id.id,entry_type,line.member_no.group_id.id, line.member_no.id, line.amount,'inward')

                else:
                    #recover interest then principal
                    member = self.env['microfinance.member'].search([('id','=',line['member_no'].id)])
                    member_name = member.name
                    runBal = line.amount
                    interest = 0.0
                    principal = 0.0
                    #unallocated = 0.0
                    loan = self.env['microfinance.loan'].search([('id','=',line.loan_no.id)])
                    #recover interest
                    if runBal >loan.interest_balance:
                        interest = loan.interest_balance
                        runBal -= interest
                    else:
                        interest = runBal
                        runBal = 0
                    #recover principal
                    if runBal > 0:
                        principal = runBal


                    if interest > 0:
                        entryno += 1
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':setup.loan_interest_acc.id,'move_id':move_id,'credit':abs(interest)})
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(interest)})
                        member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':interest,'transaction_type':'interest','entryno':entryno,'group_no':line.group.id, 'group_name':line.group.name})

                    if principal > 0:
                        entryno += 1
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':credit_acc,'move_id':move_id,'credit':abs(principal)})
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(principal)})
                        member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':factor*principal,'transaction_type':entry_type,'entryno':entryno,'group_no':line.group.id, 'group_name':line.group.name})

                    #post table session data
                    #create_transaction(self,header_id, transaction_type, group, member, amount, direction)
                    self.table_session_id.create_transaction(self.table_session_id.id,entry_type,line.member_no.group_id.id, line.member_no.id, line.amount,'inward')

            move.post()
            self.posted = True


    @api.one
    @api.depends('line_ids')
    def compute_total(self):
        amount = 0
        for line in self.line_ids:
            amount += line.amount
        self.amount_received = amount
        self.amount_words = amount_to_text_en.amount_to_text(float(amount), "Shilling")

class receipt_line(models.Model):
    _name = 'microfinance.receipt.line'

    no = fields.Many2one('microfinance.receipt.header')
    transaction_type = fields.Selection([('registration',"Registration Fee"),('membership',"Membership Fees"),('penalties',"Penalties"),('fines',"Fines"),('insurance',"Insurance"),('savings',"Savings"),('deposits',"Share Contribution"),('repayment',"Loan Repayment")])
    group = fields.Many2one('microfinance.group')
    member_no = fields.Many2one('microfinance.member')
    loan_no = fields.Many2one('microfinance.loan', domain = [('posted','=',True)])
    description = fields.Char()
    amount = fields.Float()

    @api.onchange('transaction_type')
    def get_group(self):
        self.group = self.no.group.id
        self.member_no = self.no.member.id

class payment_header(models.Model):
    _name = 'microfinance.payment.header'

    name = fields.Char()
    date = fields.Date(default=fields.date.today())
    bank_code = fields.Many2one('account.journal',domain = [('type','=','bank')])
    bank_name = fields.Char()
    amount = fields.Float(compute = 'compute_total')#compute = 'compute_total'
    amount_words = fields.Char(compute = 'compute_total')
    payment_to = fields.Char()
    payment_narration = fields.Text()
    cashier = fields.Many2one('res.users', default=lambda self: self.env.user, readonly = True, string = 'Field Officer')
    pay_mode = fields.Selection([('cash',"Cash"),('cheque',"Cheque")])
    cheque_no = fields.Char()
    status = fields.Selection([('open',"Open"),('pending',"Pending Approval"),('approved',"Approved"),('rejected',"Rejected")], default = 'open')
    posted = fields.Boolean()
    line_ids = fields.One2many('microfinance.payment.line','no')
    table_session_id = fields.Many2one('microfinance.table')
    group = fields.Many2one('microfinance.group')

    @api.one
    def action_post(self):
        if not self.posted:
            if self.date:
                today = self.date
            else:
                today = datetime.now().strftime("%m/%d/%Y")
            setup = self.env['microfinance.setup'].search([('id','=',1)])
            member_ledger = self.env['microfinance.member.ledger.entry']

            ledgers = self.env['microfinance.member.ledger.entry'].search([])
            entries = [ledger.entryno for ledger in ledgers]
            try:
                entryno = max(entries)
            except:
                entryno = 0

            #initialize journals
            #create journal header
            journal = self.env['account.journal'].search([('id','=',setup.miscellaneous_journal.id)]) #get journal id
            #period
            period = self.env['account.period'].search([('state','=','draft'),('date_start','<=',today),('date_stop','>=',today)])
            period_id = period.id

            journal_header = self.env['account.move']#reference to journal entry


            move = journal_header.create({'journal_id':journal.id,'period_id':period_id,'state':'draft','name':self.name,
                'date':today})

            move_id = move.id

            #create journal lines

            journal_lines = self.env['account.move.line']

            #credit account
            bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
            bank_acc = bank.default_debit_account_id.id

            #debit account
            debit_acc = 0
            for line in self.line_ids:

                if line.transaction_type == 'withdrawal':
                    debit_acc = setup.deposits_account.id

                elif line.transaction_type == 'dividend':
                    pass #find out accounting for dividends

                #check if balance is enough
                member = self.env['microfinance.member'].search([('id','=',line['member_no'].id)])
                if member.current_deposits < line.amount:
                    raise ValidationError('Amount requested exceeds current deposits.')

                #start posting entries
                journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + self.name,'account_id':debit_acc,'move_id':move_id,'debit':self.amount})
                journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + self.name,'account_id':bank_acc,'move_id':move_id,'credit':self.amount})

                #post member ledger
                entryno += 1
                member_name = member.name
                member_ledger.create({'entryno':entryno,'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':self.name,'transaction_name':line.transaction_type + '::' + self.name,'amount':line.amount,'transaction_type':line.transaction_type})
            move.post()
            self.posted = True

        else:
            raise ValidationError("This payment has already been posted!")


    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.payment_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

    @api.one
    @api.onchange('bank_code')
    def get_bank(self):
        #get bank name
        bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
        self.bank_name = bank.name

    @api.one
    @api.depends('line_ids')
    def compute_total(self):
        self.amount = sum(line.amount for line in self.line_ids)
        self.amount_words = amount_to_text_en.amount_to_text(float(self.amount), "Shilling")

class payment_line(models.Model):
    _name = 'microfinance.payment.line'

    no = fields.Many2one('microfinance.payment.header')
    transaction_type = fields.Selection([('withdrawal',"Deposit Withdrawal"),('dividend',"Dividend")])
    group = fields.Many2one('microfinance.group')
    member_no = fields.Many2one('microfinance.member')
    description = fields.Char()
    amount = fields.Float()

class microfinance_table(models.Model):
    _name = 'microfinance.table'

    name = fields.Char()
    date = fields.Date(default = fields.Date.today())
    start_date = fields.Datetime(string = 'Starting')
    end_date = fields.Datetime(string = 'Ending')
    location = fields.Char()
    bank = fields.Many2one('account.journal',domain = [('type','=','bank')])
    group = fields.Many2one('microfinance.group')
    field_officer = fields.Many2one('res.users', default=lambda self: self.env.user)
    line_ids = fields.One2many('microfinance.table.lines','header_id', readonly = True)
    state = fields.Selection([('open',"Draft"),('ready',"Ready"),('closed',"Closed")], default = 'open')
    charges = fields.One2many('microfinance.charges','table_session_id')
    total_charges = fields.Float(compute='calculate_charges')
    group_opening_balance = fields.Float(string = 'Banking In')#, compute = 'calculate_revolving_fund'
    transactions = fields.Float()#compute = 'calculate_revolving_fund'
    group_closing_balance = fields.Float(string = 'Banking Out')#, compute = 'calculate_revolving_fund'
    total_revolving_fund = fields.Float(string = 'Total Revolving Fund')#, compute = 'calculate_revolving_fund'
    posted = fields.Boolean()
    attendee_ids = fields.One2many('microfinance.table.attendance','header_id')
    entries = fields.Integer(compute = 'sum_entries')

    @api.one
    def sum_entries(self):
        self.entries = len(self.line_ids)


    @api.one
    def calculate_revolving_fund(self):
        ledgers = self.env['microfinance.member.ledger.entry'].search([('group_no','=',self.group.id),('transaction_type','=','loan')])
        self.total_revolving_fund = sum(ledger.amount for ledger in ledgers)
        group_ledger = self.env['microfinance.group.ledger.entry'].search([('group_no','=',self.group.id)])
        self.group_opening_balance = sum(ledger.amount for ledger in group_ledger)
        transactions = 0
        for line in self.line_ids:
            if line.direction == 'inward':
                transactions+=line.amount
            elif line.direction == 'outward':
                transactions -= line.amount
        self.transactions = transactions
        self.group_closing_balance = self.group_opening_balance + self.transactions

    @api.one
    @api.depends('charges')
    def calculate_charges(self):
        self.total_charges = sum(charge.amount for charge in self.charges)

    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.table_session_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

    @api.one
    def close_session(self):
        #closing will create a banking out transaction in group ledger
        #get last entry no
        ledgers = self.env['microfinance.group.ledger.entry'].search([])
        entries = [ledger.entryno for ledger in ledgers]
        try:
            entryno = max(entries)
        except:
            entryno = 0
        entryno += 1
        self.env['microfinance.group.ledger.entry'].create({'entryno':entryno,'table_session_id':self.id, 'group_no':self.group.id,'transaction_type':'outward','transaction_no':self.name,'amount':self.group_closing_balance})
        self.state = 'closed'
        #compute charges
        self.charges.unlink()
        charges_setup = self.env['microfinance.charges.setup'].search([])
        for member in self.attendee_ids:
            for charges in charges_setup:
                charge = charges.compute_charges(member.name.id, self.id)
                #raise ValidationError(str(charge))
                if len(charge)>0:
                    #raise ValidationError('Err Here')
                    charge = charge[0]
                    for item in charge:
                        #raise ValidationError(type(item))
                        #key, value = item.items()
                        for key in item:
                            self.env['microfinance.charges'].create({'table_session_id':self.id, 'charge_type':key,'amount':item[key],'member':member.name.id,'group':member.name.group_id.id, 'account':charges.account.id})


    @api.one
    def confirm(self):
        #confirming will create a banking in transaction in group ledger
        group_ledgers = self.env['microfinance.group.ledger.entry'].search([])
        entries = [ledger.entryno for ledger in group_ledgers]
        try:
            entryno = max(entries)
        except:
            entryno = 0

        ledgers = self.env['microfinance.group.ledger.entry'].search([('group_no','=',self.group.id)])
        total = sum(ledger.amount for ledger in ledgers)
        entryno += 1
        self.env['microfinance.group.ledger.entry'].create({'entryno':entryno,'table_session_id':self.id, 'group_no':self.group.id,'transaction_type':'inward','transaction_no':self.name,'amount':total*-1})
        self.state = 'ready'
        self.calculate_revolving_fund()

    @api.one
    def reset(self):
        #reseting will delete all group ledger transactions that have been created
        self.env['microfinance.group.ledger.entry'].search([('transaction_no','=',self.name)]).unlink()
        self.state = 'open'
        self.calculate_revolving_fund()

    @api.one
    def create_transaction(self,header_id, transaction_type, group, member, amount, direction):
        if not header_id and transaction_type and group and member and amount and header_id and direction:
            raise ValidationError("One or more required fields is not provided!")

        res = {'header_id':header_id, 'transaction_type':transaction_type, 'group':group, 'member':member,
        'amount':amount, 'direction':direction}
        self.env['microfinance.table.lines'].create(res)
        #raise ValidationError('Am here!!!!!!!')

    @api.onchange('group')
    def get_attendees(self):
        self.attendee_ids.unlink()
        lines = []
        for line in self.group.group_members:
            val = {'name':line.id}
            lines += [val]
        self.update({'attendee_ids':lines})

    @api.one
    def get_attendance_manually(self):
        self.attendee_ids.unlink()
        for line in self.group.group_members:
            self.env['microfinance.table.attendance'].create({'header_id':self.id, 'name':line.id})

class microfinance_table_line(models.Model):
    _name = 'microfinance.table.lines'

    header_id = fields.Many2one('microfinance.table')
    transaction_type = fields.Selection([('registration',"Registration Fee"),('membership',"Membership Fees"),('penalties',"Penalties"),('fines',"Fines"),('insurance',"Insurance"),('savings',"Savings"),('deposits',"Share Contribution"),('loan_fees',"Loan Processing Fees"),('loan',"Loan"),('loan_repayment',"Loan Repayment"),('membership',"Membership Fees")])
    group = fields.Many2one('microfinance.group')
    member = fields.Many2one('microfinance.member')
    amount = fields.Float()
    direction = fields.Selection([('inward',"Money In"),('outward',"Money Out")])

class microfinance_table_attendance(models.Model):
    _name = 'microfinance.table.attendance'

    header_id = fields.Many2one('microfinance.table')
    name = fields.Many2one('microfinance.member')
    present = fields.Boolean(default = False, string = 'Present')
    absent = fields.Boolean(default = False, string = 'Absent with Apology')
    reason = fields.Char()

    @api.onchange('present')
    def toggle_present(self):
        if self.present == True:
            self.absent = False

    @api.onchange('absent')
    def toggle_false(self):
        if self.absent == True:
            self.present = False

class microfinance_charges(models.Model):
    _name = 'microfinance.charges'

    name = fields.Many2one('microfinance.charges.setup')
    description = fields.Char()
    member = fields.Many2one('microfinance.member')
    group = fields.Many2one('microfinance.group')
    charge_type = fields.Selection([('fines','Fines'),('attendance',"Non Attendance")])
    account = fields.Many2one('account.account')
    amount = fields.Float()
    table_session_id = fields.Many2one('microfinance.table')

    @api.onchange('name')
    def get_account(self):
        self.account = self.name.account.id
        self.amount = self.name.amount

class microfinance_charges_setup(models.Model):
    _name = 'microfinance.charges.setup'

    name = fields.Char()
    description = fields.Char()
    charge_type = fields.Selection([('fines',"Fines"),('attendance',"Non Attendance")])
    account = fields.Many2one('account.account')
    amount = fields.Float(string = 'Default Amount')

    @api.one
    def compute_charges(self,member,session):
        amount = 0.0
        member_charges =[]
        #member = self.env['microfinance.member'].search([('id','=',member)])
        loans = self.env['microfinance.loan'].search([('member_no','=',member)])
        for loan in loans:
            if self.charge_type == 'defaulting':
                #test defaulting
                if loan.balance_due > 0:
                    #charge defaulting
                    member_charges.append({charge_type:100})

        if self.charge_type == 'attendance':
            #test attendance
            attendance = self.env['microfinance.table.attendance'].search([('header_id','=',session),('name','=',member)])
            if (len(attendance)<=0) or not (attendance.present or attendance.absent):
                #charge non attendance
                #raise ValidationError('Charged member for non attendance')
                member_charges.append({self.charge_type:50})
        #raise ValidationError(str(member_charges))
        return member_charges



class microfinance_group_ledger(models.Model):
    _name = 'microfinance.group.ledger.entry'

    entryno = fields.Integer()
    table_session_id = fields.Many2one('microfinance.table')
    group_no = fields.Many2one('microfinance.group')
    group_name = fields.Char()
    transaction_type = fields.Selection([('inward',"Banking In"),('outward',"Banking Out")])
    transaction_no = fields.Char()
    amount = fields.Float()
    dr = fields.Float()
    cr = fields.Float()
