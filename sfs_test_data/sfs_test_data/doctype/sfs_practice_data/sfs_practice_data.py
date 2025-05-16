# Copyright (c) 2025, Oliver Blackstock III and contributors
# For license information, please see license.txt

import frappe
import random
import time
from datetime import datetime, timedelta
from frappe.model.document import Document
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt, make_purchase_invoice

def create_new_po(template_name, desired_status, item_chance=50):
	# get the original PO
	po = frappe.get_doc('Purchase Order', template_name)
	# create new PO
	new_po = frappe.new_doc('Purchase Order')
	# copy all the values
	new_po.__dict__ = po.__dict__
	# change all the relevant details
	new_po.name = ''
	# new_po.status = "Draft" # default to draft
	# new_po.transaction_date = datetime.today()
	new_po.schedule_date = (datetime.now() + timedelta(days=5))

	# -- Process Items --
	# shuffle the items on the PO
	random.shuffle(po.items)

	# pop off the first item to ensure that there is at least 1 item
	first_item = po.items.pop()

	new_items = [first_item]
	# process the other items with a chance for each to appear on the new PO
	for item in po.items:
		if random.randint(1, 100) < item_chance:
			new_items.append(item)
	

	# randomize quantities
	for item in new_items:
		item.qty = random.randint(1, 20)
		# set the required date on each item, or the system will reset the PO
		# required date to the minimum amongst the items
		item.schedule_date = new_po.schedule_date
	
	new_po.items = new_items
	# insert the new po
	new_po.insert()

	status_list = ["Draft", "Submitted", "Bill", "Pay"]
	if desired_status == "Random":
		desired_status = random.choice(status_list)

	# check the status to see which 
	if desired_status == 'Submitted':
		new_po.submit()
	if desired_status == 'Bill':
		new_po.submit()
		purchase_receipt = make_purchase_receipt(new_po.name)
		purchase_receipt.insert()
		purchase_receipt.submit()
		purchase_invoice = make_purchase_invoice(new_po.name)
	if desired_status == 'Pay':
		new_po.submit()
		purchase_receipt = make_purchase_receipt(new_po.name)
		purchase_receipt.insert()
		purchase_receipt.submit()
		purchase_invoice = make_purchase_invoice(new_po.name)
		purchase_invoice.submit()

	frappe.db.commit()


class SFSPracticeData(Document):
	def on_submit(self):
		# get all POs that carry the tag
		tags = frappe.db.get_list('Tag Link', fields=['*'], filters={'tag':self.tag_name})
		# grab a random choice
		for i in range(0, int(self.number_to_generate)):
			po = random.choice(tags)
			create_new_po(po.document_name, self.desired_purchase_status, int(self.chance_per_item))