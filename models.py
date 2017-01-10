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
            interest_calculated = round((interest/installments),2)
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

    name = fields.Char()
    member_name = fields.Char()
    application_date = fields.Date()
    employer_code = fields.Many2one('microfinance.employers')
    id_no = fields.Char()
    pin = fields.Char()
    gender = fields.Selection([('male',"Male"),('female',"Female")])
    occupation = fields.Char()
    mobile = fields.Char()
    email = fields.Char()


    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.member_application_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

class microfinance_group_application(models.Model):
    _name = 'microfinance.group.application'

    name = fields.Char(string = 'No.')
    application_date = fields.Date()
    group_name = fields.Char(string='Name')
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

    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.group_application_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

class microfinance_member(models.Model):
    _name = 'microfinance.member'

    name = fields.Char(string = 'No.')
    member_name = fields.Char()
    registration_date = fields.Date()
    employer_code = fields.Many2one('microfinance.employers')
    staff_no = fields.Char()
    id_no = fields.Char()
    pin = fields.Char()
    gender = fields.Selection([('male',"Male"),('female',"Female")])
    occupation = fields.Char()
    mobile = fields.Char()
    email = fields.Char()
    loan_ids = fields.One2many('microfinance.loan','member_no')
    loans = fields.Float(compute = 'compute_loan_stats')


    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.member_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

    @api.one
    @api.depends('loan_ids')
    def compute_loan_stats(self):
        self.loans = sum(loan.balance for loan in self.loan_ids)

class microfinance_group(models.Model):
    _name = 'microfinance.group'

    name = fields.Char(string = 'No.')
    group_name = fields.Char(string='Name')
    group_members = fields.One2many('microfinance.group.member','group_id')
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

    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.group_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

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


class microfinance_loan(models.Model):
    _name = 'microfinance.loan'

    name = fields.Char(string = 'No.')
    application_date = fields.Date()
    member_no = fields.Many2one('microfinance.member')
    member_name = fields.Char(string = 'Member Name')
    group_no = fields.Many2one('microfinance.group')
    group_name = fields.Char(string = 'Group Name')
    employer_code = fields.Many2one('microfinance.employers')
    staff_no = fields.Char()
    loan_batch = fields.Many2one('microfinance.loan.batch')
    requested_amount = fields.Float()
    approved_amount = fields.Float()
    balance = fields.Float(compute = 'compute_loan_stats')
    interest_balance = fields.Float(compute = 'compute_loan_stats')
    loan_purpose = fields.Text()
    posted = fields.Boolean()
    loan_type = fields.Many2one('microfinance.loan.products')
    installments = fields.Integer()
    scale = fields.Many2one('microfinance.scales')
    interest = fields.Float(string = 'Expected Income')
    #interest_rate = fields.Float()
    posting = fields.Selection([('individual',"Individual"),('batch',"Batch")], default = 'individual')
    matrix = fields.Many2one('microfinance.product.scale.matrix')
    schedule_ids = fields.One2many('microfinance.loan.repayment.schedule', 'loan_id')

    @api.one
    @api.onchange('name')
    def get_sequence(self):
        setup = self.env['microfinance.setup'].search([('id','=',1)])
        sequence = self.env['ir.sequence'].search([('id','=',setup.loan_nos.id)])
        self.name = sequence.next_by_id(sequence.id, context = None)

    @api.onchange('member_no')
    def populate_member(self):
        if self.member_no:
            self.member_name = self.member_no.member_name
            #self.employer_code = self.member_no.employer_code.id
            self.staff_no = self.member_no.staff_no

    @api.onchange('loan_type','scale')
    def get_loan_product_amount(self):
        if self.loan_type and self.scale:
            matrix = self.env['microfinance.product.scale.matrix'].search([('product.id','=',self.loan_type.id),('scale.id','=',self.scale.id)])
            if len(matrix)>0:
                #self.matrix.id = matrix.id
                self.approved_amount = matrix.total_input
                self.interest = matrix.margin
                self.installments = self.loan_type.installments
            else:
                raise ValidationError('Matrix with Product::' + self.loan_type.name +' and scale::' + self.scale.name +' does not exist. Please create one')

    @api.one
    @api.depends('posted')
    def compute_loan_stats(self):
        if self.posted:
            ledgers = self.env['microfinance.member.ledger.entry'].search([('transaction_no','=',self.name)])
            self.balance = sum(ledger.amount for ledger in ledgers if ledger.transaction_type == 'loan')
            self.interest_balance = sum(ledger.amount for ledger in ledgers if ledger.transaction_type == 'interest')

    @api.one
    def action_post(self, paying_bank):
        if not self.posted:
            #date
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

            #loans = self.env['microfinance.loan'].search([('batch_no','=',self.id)])

            member_ledger = self.env['microfinance.member.ledger.entry']
            #get last entry no
            ledgers = self.env['microfinance.member.ledger.entry'].search([])
            entries = [ledger.entryno for ledger in ledgers]
            try:
                entryno = max(entries)
            except:
                entryno = 0

            #get required accounts for the transaction

            #setup = self.env['microfinance.setup'].search([('id','=',1)])
            loan_acc = setup.loans_account.id
            bank = self.env['res.partner.bank'].search([('bank','=',paying_bank)])
            bank_acc = bank.journal_id.default_credit_account_id.id
            loan_interest_acc = setup.loan_interest_acc.id
            loan_interest_receivable_acc = setup.loan_interest_receivable_acc.id
            #loan_processing_fee_acc = setup.loan_processing_fee_acc.id
            #processing_rate = setup.processing_rate

            #this section allows for any charges applicable to your loan to be made
            #processing_fee = 0.0
            #processing_fee = (processing_rate*0.01)*self.approved_amount
            amount_to_disburse = 0.0
            #amount_to_disburse = self.approved_amount# - processing_fee
            interest = 0.0
            interest = self.interest#approved_amount*self.loan_type.interest_rate*0.01
            #post loan journal
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_name,'account_id':loan_acc,'move_id':move_id,'debit':self.approved_amount})#loan debtor
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_name,'account_id':bank_acc,'move_id':move_id,'credit':self.approved_amount})#bank account
            #journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_name+'::Processing Fees','account_id':loan_processing_fee_acc,'move_id':move_id,'credit':processing_fee})#processing fees
            #post interest receivable
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_name+'::Loan interest','account_id':loan_interest_receivable_acc,'move_id':move_id,'debit':interest})
            journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':self.name +'::'+self.member_name+'::Loan interest','account_id':loan_interest_acc,'move_id':move_id,'credit':interest})
            self.posted = True
            #post member ledger entry

            entryno += 1
            #loan
            member_ledger.create({'member_no':self.member_no.id,'member_name':self.member_name,'date':today,'transaction_no':self.name,'transaction_name':'Loan Application','amount':self.approved_amount,
            'transaction_type':'loan','entryno':entryno})
            #interest
            entryno += 1
            member_ledger.create({'member_no':self.member_no.id,'member_name':self.member_name,'date':today,'transaction_no':self.name,'transaction_name':'Loan Interest Due','amount':interest,
            'transaction_type':'interest','entryno':entryno})

    @api.one
    def generate_schedule(self):
        #delete first then generate schedule
        if self.application_date:
            self.env['microfinance.loan.repayment.schedule'].search([('loan_id','=',self.id)]).unlink()
            repayment_schedule = self.env['microfinance.loan.repayment.schedule']
            loan_product = self.env['microfinance.loan.products'].search([('id','=',self.loan_type.id)])
            loan_schedule = calc_interest(self.approved_amount,self.installments,self.interest,loan_product.repayment_method)
            principal = loan_schedule[0]
            interest = loan_schedule[1]
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

class microfinance_loan_product(models.Model):
    _name = 'microfinance.loan.products'

    name = fields.Char()
    description = fields.Char()
    interest_rate = fields.Float()
    installments = fields.Integer()
    loan_product_input_ids = fields.One2many('microfinance.loan.product.inputs', 'loan_product')
    repayment_method = fields.Selection([('straight',"Straight")], default = 'straight')

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
    miscellaneous_journal = fields.Many2one('account.journal')
    loans_journal = fields.Many2one('account.journal')
    loans_account = fields.Many2one('account.account')
    loan_interest_acc = fields.Many2one('account.account')
    loan_interest_receivable_acc = fields.Many2one('account.account')
    loan_processing_fee_acc = fields.Many2one('account.account')
    processing_rate = fields.Float()

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
    member_no = fields.Many2one('microfinance.member')
    member_name = fields.Char()
    group_no = fields.Many2one('microfinance.group')
    group_name = fields.Char()
    transaction_type = fields.Selection([('loan',"loan"),('interest',"Interest")])
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
    total = fields.Float()#compute = 'sum_total'
    principal_paid = fields.Boolean()#compute = 'check'
    interest_paid = fields.Boolean()#compute = 'check'


class receipt_header(models.Model):
    _name = 'microfinance.receipt.header'

    name = fields.Char()
    date = fields.Date(default=fields.date.today())
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

    @api.one
    @api.onchange('bank_code')
    def get_bank(self):
        #get bank name
        bank = self.env['account.journal'].search([('id','=',self.bank_code.id)])
        self.bank_name = bank.name

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
                        member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':factor*line.amount,'transaction_type':entry_type,'entryno':entryno})

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

                    #else:
                    #   principal = 'runBal'
                    #   runBal = 0
                    #record unallocated
                    #if runBal > 0:
                    #   unallocated = runBal

                    if interest > 0:
                        entryno += 1
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':setup.loan_interest_account.id,'move_id':move_id,'credit':abs(interest)})
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(interest)})
                        member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':interest,'transaction_type':'interest','entryno':entryno})

                    if principal > 0:
                        entryno += 1
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':credit_acc,'move_id':move_id,'credit':abs(principal)})
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(principal)})
                        member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':factor*principal,'transaction_type':entry_type,'entryno':entryno})
                    '''
                    if unallocated > 0:
                        entryno += 1
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':setup.unallocated_funds.id,'move_id':move_id,'credit':abs(unallocated)})
                        journal_lines.create({'journal_id':journal.id,'period_id':period_id,'date':today,'name':line.transaction_type + '::' + line.member_no.name,'account_id':bank_acc,'move_id':move_id,'debit':abs(unallocated)})
                        member_ledger.create({'member_no':line.member_no.id,'member_name':member_name,'date':today,'transaction_no':transaction_no,'transaction_name':transaction_name + '::' + self.name,'amount':factor*principal,'transaction_type':'unallocated'})
                    '''
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
    transaction_type = fields.Selection([('registration',"Registration Fee"),('deposits',"Share Contribution"),('shares',"Shares Capital"),('repayment',"Loan Repayment"),('unallocated',"Unallocated Funds")])
    member_no = fields.Many2one('microfinance.member')
    loan_no = fields.Many2one('microfinance.loan', domain = [('posted','=',True)])
    description = fields.Char()
    amount = fields.Float()

class payment_header(models.Model):
    _name = 'microfinance.payment.header'

    name = fields.Char()
    date = fields.Date(default=fields.date.today())
    bank_code = fields.Many2one('account.journal',domain = [('type','=','bank')])
    bank_name = fields.Char()
    amount = fields.Float(compute = 'compute_total')#compute = 'compute_total'
    amount_words = fields.Char(compute = 'compute_total')
    payment_to = fields.Char()
    on_behalf_of = fields.Char()
    payment_narration = fields.Text()
    cashier = fields.Many2one('res.users', default=lambda self: self.env.user, readonly = True)
    pay_mode = fields.Selection([('cash',"Cash"),('cheque',"Cheque")])
    cheque_no = fields.Char()
    status = fields.Selection([('open',"Open"),('pending',"Pending Approval"),('approved',"Approved"),('rejected',"Rejected")], default = 'open')
    posted = fields.Boolean()


    line_ids = fields.One2many('microfinance.payment.line','no')

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
    member_no = fields.Many2one('microfinance.member')
    description = fields.Char()
    amount = fields.Float()
