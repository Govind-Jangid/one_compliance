import frappe
import json
from frappe.model.document import Document
from frappe.utils import *
from frappe.model.mapper import *
from frappe import _
from datetime import date

class ComplianceAgreement(Document):
	''' Method used for validate Signature '''
	def on_update_after_submit(self):
		self.sign_validation()

	def sign_validation(self):
		if self.workflow_state == 'Approved' and not self.authority_signature:
			frappe.throw('Authority Signature is required for Approval')
		if self.workflow_state == 'Customer Approved' and not self.customer_signature:
			frappe.throw('Customer Signature is required for Approval')

@frappe.whitelist()
def create_project_from_agreement(name):
	''' Method to create projects from Compliance Agreement '''
	doc = frappe.get_doc('Compliance Agreement', name)
	if doc.compliance_category_details:
		for compliance_category in doc.compliance_category_details:
			if compliance_category.compliance_sub_category:
				project_template  = frappe.db.get_value('Compliance Sub Category', compliance_category.compliance_sub_category, 'project_template')
				if project_template:
					project = frappe.new_doc('Project')
					today = getdate(frappe.utils.today())
					my_date = date(2023, 2, 27)
					project.project_name = doc.customer_name + '-' + compliance_category.compliance_sub_category + '-' + str(my_date)
					project.customer = doc.customer
					project.compliance_agreement = doc.name
					project.save()
					frappe.msgprint('Project Created', alert = 1)
					project_template_doc = frappe.get_doc('Project Template', project_template)
					for task in project_template_doc.tasks:
						''' Method to create task against created project from the Project Template '''
						if not frappe.db.exists('Task',{'project':project.name, 'subject':task.subject}):
							tasks_doc = frappe.get_doc('Task',task.task)
							task_doc = frappe.new_doc('Task')
							task_doc.compliance_sub_category = compliance_category.compliance_sub_category
							task_doc.subject = task.subject
							task_doc.project = project.name
							task_doc.type = 'ToDo'
							if tasks_doc.expected_time:
								task_doc.expected_time = tasks_doc.expected_time
							task_doc.save(ignore_permissions=True)
			else :
				frappe.throw(
				title = _('ALERT !!'),
				msg = _('Project Template does not exist')
				)

@frappe.whitelist()
def assign_tasks(source_name, target_doc = None):
	''' Method to assign tasks for custom button Assign Task and route to Compliance Task Assignement doctype '''
	def set_missing_values(source, target):
		for categories in source.compliance_category:
			target.append('category', {
			'compliance_category' : categories.compliance_category
			})
		for task in source.compliance_category_details:
			task_doc = get_task_from_project(task.compliance_sub_category, source.customer_name)
			for tasks in task_doc:
				target.append('task_details', {
				'sub_category' : task.compliance_sub_category,
				'task':tasks.name
				})
	doc = get_mapped_doc(
		'Compliance Agreement',
		source_name,
		{
		'Compliance Agreement': {
		'doctype': 'Compliance Task Assignment',
		},
		}, target_doc, set_missing_values)
	doc.save()
	return doc


@frappe.whitelist()
def get_task_from_project(sub_category, customer_name):
	''' Method to get tasks from project based on Sub Category '''
	task_items = []
	if frappe.db.exists ('Project', { 'customer': customer_name }):
		project_doc = frappe.db.get_list('Project', {'customer': customer_name})
		for projects in project_doc:
			task_list = frappe.db.get_list('Task', filters={'project': projects.name}, fields = ['compliance_sub_category','name'])
			for tasks in task_list:
				if tasks.compliance_sub_category == sub_category:
					task_items.append(tasks)
	return task_items

@frappe.whitelist()
def check_project_status(compliance_agreement):
	if frappe.db.exists('Project', {'compliance_agreement':compliance_agreement, 'status':'Completed'}):
		return True

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
	def set_missing_values(source, target):
		if frappe.db.exists('Project', {'compliance_agreement':source.name}):
			company = frappe.db.get_value('Project', {'compliance_agreement':source.name},'company')
			income_account = frappe.db.get_value('Company',company, 'default_income_account')
		if source.compliance_category_details:
			for sub_category in source.compliance_category_details:
				rate = calculate_rate(source.compliance_category_details, sub_category.compliance_category)
				if source.invoice_based_on == 'Project':
					target.append('items', {
					'item_name' : sub_category.compliance_sub_category,
					'rate' : sub_category.rate,
					'qty' : 1,
					'income_account' : income_account,
					'description' : sub_category.name,
					})
				if source.invoice_based_on == 'Consolidated':
					if not check_exist(target, sub_category.compliance_category):
						target.append('items', {
							'item_name' : sub_category.compliance_category,
							'rate' : rate,
							'qty' : 1,
							'income_account' : income_account,
							'description' : sub_category.name,
						})
	doclist = get_mapped_doc(
		'Compliance Agreement',
		source_name,
		{
			'Compliance Agreement':{
                'doctype':'Sales Invoice'

				},
			},
		target_doc,
		set_missing_values
	)
	doclist.save()

	return doclist

def check_exist(target, compliance_category):
    ''' checking if item allready exist in child table '''
    exist = False
    try:
        if target.items:
            for item in target.items:
                if compliance_category:
                    if item.item_name == compliance_category:
                        exist = True
    except:
        exist = False
    return exist

def calculate_rate(compliance_category_details, compliance_category):
	rate = 0
	for category in compliance_category_details:
		if category.compliance_category == compliance_category:
			rate += category.rate
	return rate
