# Copyright (c) 2025, Oliver Blackstock III and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SFSTestDocument(Document):
	def on_update(self):
		print(self.test_date)
