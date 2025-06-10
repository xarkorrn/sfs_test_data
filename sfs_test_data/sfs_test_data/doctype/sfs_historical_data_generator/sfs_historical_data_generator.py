# Copyright (c) 2025, Oliver Blackstock III and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from datetime import datetime, timedelta
import random
from frappe.model.document import Document
from erpnext.selling.doctype.quotation.quotation import make_sales_order
from erpnext.selling.doctype.sales_order.sales_order import make_purchase_order, make_sales_invoice, make_delivery_note
from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request, make_payment_entry
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice, make_purchase_receipt

def get_random_cost_center():
	centers = frappe.get_all('Cost Center')
	return random.choice(centers).name

def create_historical_data(project, customer, max_item_variety, max_item_qty, markup, start_date, cost_center):
	# Create Quote
		quote = frappe.new_doc("Quotation")
		quote.party_name = customer.name

		# Get products
		products = frappe.get_all('Item', filters={'item_group':'Products'})
		num_items = random.randint(1, max_item_variety)

		# shuffle the products
		random.shuffle(products)
		quote_items = []
		for _ in range(0, num_items):
			# pop off a product
			product = products.pop()
			item = frappe.get_doc('Item', product.name)
			quote_item = frappe.new_doc('Quotation Item')
			quote_item.item_code = item.item_code
			quote_item.item_name = item.name
			quote_item.qty = random.randint(1, max_item_qty)
			quote_item.uom = item.uoms[0].uom
			quote_item.rate = item.valuation_rate * (1 + (float(markup) * .01))
			quote_items.append(quote_item)
		quote.items = quote_items
		if (project):
			quote.project = project.name
		quote.insert()

		quote.submit()

		# Create sales order from quote
		sales_order = make_sales_order(quote.name)
		if (project):
			sales_order.project = project.name
		sales_order.transaction_date = getdate(start_date)
		sales_order.delivery_date = sales_order.transaction_date + timedelta(days=7)
		
		# Handle Accounting Dimensions
		sales_order.cost_center = cost_center
		dimensions = frappe.get_all('Accounting Dimension', fields=['*'])
		# set a value for each dimension
		for dimension in dimensions:
			# get all of the possible dimension values
			values = frappe.get_all(dimension.document_type)
			if (len(values) > 0):
				setattr(sales_order, dimension.fieldname, random.choice(values).name)
		sales_order.insert()
		sales_order.submit()
		sales_invoice = make_sales_invoice(sales_order.name)
		sales_invoice.set_posting_time = 1
		sales_invoice.posting_date = start_date
		sales_invoice.insert()
		sales_invoice.save()
		sales_invoice.submit()

		# Process the payment from the Customer (assume pre-payment so that
		# the necessary funds are there to buy materials)
		si_pr = make_payment_request(dt='Sales Invoice', dn=sales_invoice.name, return_doc=True)
		si_pr.submit()
		si_payment = si_pr.create_payment_entry(submit=False)
		si_payment.posting_date = start_date
		si_payment.submit()

		# Purchase the required items for the Sales Order
		# find the supplier to provide items, there should only be one for
		# testing as it represents us purchasing items at cost
		si = frappe.get_last_doc('Item Supplier', filters={'parent':sales_order.items[0].item_name})
		
		purchase_order = make_purchase_order(sales_order.name, selected_items=sales_order.items)
		# update the prices using valuation rates
		for i in range(0, len(purchase_order.items)):
			doc = frappe.get_doc('Item', purchase_order.items[i].item_name)
			purchase_order.items[i].rate = doc.valuation_rate

		purchase_order.supplier = si.supplier
		purchase_order.transaction_date = start_date
		purchase_order.schedule_date = sales_order.delivery_date
		if (project):
			purchase_order.project = project.name
		# -- Handle Accounting Dimensions --
		# purchase_order.cost_center = get_random_cost_center()
		purchase_order.insert()
		purchase_order.submit()
		purchase_invoice = make_purchase_invoice(purchase_order.name)
		purchase_invoice.set_posting_time = 1
		purchase_invoice.posting_date = start_date
		
		purchase_invoice.insert()
		purchase_invoice.save()
		purchase_invoice.submit()

		# Process payment to the supplier
		pi_pr = make_payment_request(dt='Purchase Invoice', dn=purchase_invoice.name, return_doc = True)
		pi_pr.submit()
		pi_payment = pi_pr.create_payment_entry(submit=False)
		pi_payment.posting_date = start_date
		pi_payment.submit()

		# Receive items
		po_receipt = make_purchase_receipt(purchase_order.name)
		po_receipt.insert()
		po_receipt.submit()
		# Now, delivery items to customer
		delivery_note = make_delivery_note(sales_order.name)
		delivery_note.insert()
		delivery_note.submit()

class SFSHistoricalDataGenerator(Document):
	def on_submit(self):
		# Create a Project
		# If there is a project name, let's create the project
		project = None
		if (self.project_name):
			project = frappe.new_doc("Project")
			project.project_name = self.project_name
			project.insert()

		for i in range(0, self.number_to_generate):
			customer = None
			# was there a provided customer?
			if (self.customer):
				customer = frappe.get_doc('Customer', self.customer)
			else:
				customers = frappe.get_all('Customer')
				choice = random.choice(customers).name
				customer = frappe.get_doc('Customer', choice)
			rand_date = getdate(self.start_date)
			create_historical_data(project, customer,self.max_item_variety, self.max_item_qty, self.markup, rand_date, self.cost_center)

		

		