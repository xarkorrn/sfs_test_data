# Copyright (c) 2025, Oliver Blackstock III and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

def create_copy(doctype, obj):
	# create a new PO Template
	new_doc = frappe.new_doc(doctype)
	# # copy all of the data
	new_doc.__dict__ = obj.__dict__
	# # change all the relevant details
	new_doc.doctype = doctype

	# for field in obj.meta.fields:
	# 	if hasattr(new_doc, field.fieldname):
	# 		new_doc.set(field.fieldname, obj.get(field.fieldname))
	# # new_doc.name = ''
	new_doc.insert()
	return new_doc.items

class SFSTemplateConverter(Document):
	def on_update(self):
		templates = []
		# check if POs should be processed
		if self.po == 1:
			# get all template tags associated with POs
			po_tags = frappe.get_all(
				'Tag Link', fields=['document_name'], 
				filters={'tag':'template', 'document_type':'Purchase Order'})
			# create a list of PO names
			po_names = list(map(lambda tag: tag['document_name'], po_tags))
			# get all the POs
			po_templates = []
			for name in po_names:
				po_templates.append(frappe.get_doc('Purchase Order', name))
			# create PO Templates
			for template in po_templates:
				templates.append(create_copy('SFS PO Template', template))
		
		if self.so == 1:
			# get all template tags associated with SOs
			so_tags = frappe.get_all(
				'Tag Link', fields=['document_name'], 
				filters={'tag':'template', 'document_type':'Sales Order'})
			# create a list of SO names
			so_names = list(map(lambda tag: tag['document_name'], so_tags))
			# get all the SOs
			so_templates = []
			for name in so_names:
				so_templates.append(frappe.get_doc('Sales Order', name))
			# create SO Templates
			templates = []
			for template in so_templates:
				templates.append(create_copy('SFS SO Template', template))
		# when all is done, commit
		frappe.db.commit()
		print(templates)
		
