# Copyright (c) 2025, Oliver Blackstock III and contributors
# For license information, please see license.txt

import frappe
import random
import time
from frappe.utils import getdate
from datetime import datetime, timedelta
from frappe.model.document import Document
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt, make_purchase_invoice

def get_random_cost_center():
	centers = frappe.get_all('Cost Center')
	return random.choice(centers).name

def create_po(supplier, transaction_date=datetime.today(), desired_status='Draft'):
	# Create a PO
	po = frappe.new_doc('Purchase Order')
	po.supplier = supplier

	# -- Create items --
	# get Item Supplier list
	supplier_item_names = frappe.get_all('Item Supplier', fields=['parent'], filters={'supplier':supplier})
	# build an item list from the names
	# Do this with get_doc to get objects instead of dicts
	supplier_items = []
	for data in supplier_item_names:
		supplier_items.append(frappe.get_doc('Item', data.parent))
	
	# pick a random number of these items
	num_items = random.randint(1, len(supplier_items))
	
	# shuffle the items
	random.shuffle(supplier_items)
	# Create the PO Items
	po_items = []
	for _ in range(0, num_items):
		# pop off an item
		item = supplier_items.pop()
		po_item = frappe.new_doc('Purchase Order Item')
		po_item.item_name = item.name
		po_item.item_code = item.item_code
		po_item.qty = random.randint(1, 5)
		po_item.uom = item.uoms[0].uom
		po_item.rate = item.valuation_rate
		po_items.append(po_item)
	
	po.items = po_items
	
	# -- Handle Accounting Dimensions --
	po.cost_center = get_random_cost_center()
	dimensions = frappe.get_all('Accounting Dimension', fields=['*'])
	# set a value for each dimension
	for dimension in dimensions:
		# get all of the possible dimension values
		values = frappe.get_all(dimension.document_type)
		setattr(po, dimension.fieldname, random.choice(values).name)
	
	# was a date provided?
	po.transaction_date = transaction_date
	po.schedule_date = (transaction_date + timedelta(days=7))
	po.insert()

	status_list = ["Draft", "Submitted", "Bill", "Pay"]

	if desired_status == "Random":
		desired_status = random.choice(status_list)

	# check the status to see which 
	if desired_status == 'Submitted':
		po.submit()
	if desired_status == 'Bill':
		po.submit()
		purchase_receipt = make_purchase_receipt(po.name)
		purchase_receipt.insert()
		purchase_receipt.submit()
		purchase_invoice = make_purchase_invoice(po.name)
	if desired_status == 'Pay':
		po.submit()
		purchase_receipt = make_purchase_receipt(po.name)
		purchase_receipt.insert()
		purchase_receipt.submit()
		purchase_invoice = make_purchase_invoice(po.name)
		purchase_invoice.submit()

def create_so(customer, transaction_date=datetime.today(), desired_status='Draft', max_so_item_variety=3, max_so_item_qty=10, markup=10):
	# create SO
	so = frappe.new_doc('Sales Order')

	so.customer = customer

	so.transaction_date = transaction_date
	so.delivery_date = (transaction_date + timedelta(days=7))
	
	## -- Create Items --
	products = frappe.get_all('Item', filters={'item_group':'Products'})
	num_items = random.randint(1, max_so_item_variety)

	# -- Handle Accounting Dimensions --
	so.cost_center = get_random_cost_center()
	dimensions = frappe.get_all('Accounting Dimension', fields=['*'])
	# set a value for each dimension
	for dimension in dimensions:
		# get all of the possible dimension values
		values = frappe.get_all(dimension.document_type)
		setattr(so, dimension.fieldname, random.choice(values).name)
	
	# shuffle the products
	random.shuffle(products)
	so_items = []
	for _ in range(0, num_items):
		# pop off a product
		product = products.pop()
		item = frappe.get_doc('Item', product.name)
		so_item = frappe.new_doc('Sales Order Item')
		so_item.item_code = item.item_code
		so_item.item_name = item.name
		so_item.qty = random.randint(1, max_so_item_qty)
		so_item.uom = item.uoms[0].uom
		so_item.rate = item.valuation_rate * (1 + (markup * .01))
		so_items.append(so_item)
	
	so.items = so_items
	so.insert()


class SFSPracticeData(Document):
	def on_submit(self):
		if int(self.po_number_to_generate) > 0:
			for _ in range(0, int(self.po_number_to_generate)):
				# was there a supplier given?
				supplier = ''
				supplier_item_names = []
				if self.supplier is not None:
					supplier = self.supplier
					supplier_item_names = frappe.get_all('Item Supplier', fields=['parent'], filters={'supplier':self.supplier})
					# if the supplier given doesn't have item associations, throw an error
					if len(supplier_item_names) == 0:
						raise Exception("Selected Supplier has no Item associations")
				else:
					# if not, we need to find a supplier with associated items
					# this query ensures we only get a supplier with item associations
					suppliers = frappe.db.sql('select distinct supplier from `tabItem Supplier`')
					# choose one at random
					supplier = random.choice(suppliers)[0]
				
				# was there a transaction date passed?
				transaction_date = datetime.today()
				if self.po_date is not None:
					transaction_date = getdate(self.po_date)
				create_po(supplier, transaction_date, self.desired_purchase_status)
		if (int(self.so_number_to_generate) > 0):
			for _ in range(0, int(self.so_number_to_generate)):
				customer = ''
				# was there a customer given?
				if self.customer is not None:
					customer = self.customer
				else:
					# if not, we need to get a random customer
					customers = frappe.get_all('Customer')
					customer = random.choice(customers).name
				
				transaction_date = datetime.today()
				if self.so_date is not None:
					transaction_date = getdate(self.so_date)
				create_so(
					customer, 
					transaction_date, 
					self.desired_sale_status, 
					max_so_item_qty=self.max_so_item_qty, 
					max_so_item_variety=self.max_so_item_variety, 
					markup=self.so_markup)