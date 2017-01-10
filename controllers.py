# -*- coding: utf-8 -*-
from openerp import http

# class Microfinance(http.Controller):
#     @http.route('/microfinance/microfinance/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/microfinance/microfinance/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('microfinance.listing', {
#             'root': '/microfinance/microfinance',
#             'objects': http.request.env['microfinance.microfinance'].search([]),
#         })

#     @http.route('/microfinance/microfinance/objects/<model("microfinance.microfinance"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('microfinance.object', {
#             'object': obj
#         })