import frappe
import json
from frappe.utils import *
from frappe.email.doctype.notification.notification import get_context
from frappe.utils.user import get_users_with_role
from frappe import _
from one_compliance.one_compliance.doctype.compliance_agreement.compliance_agreement import create_project_from_agreement
from datetime import datetime
from frappe.utils import add_months

@frappe.whitelist()
def create_notification_log(subject, type, for_user, email_content, document_type, document_name):
    ''' Method to Create Notification Log '''
    notification_doc = frappe.new_doc('Notification Log')
    notification_doc.subject = subject
    notification_doc.type = type
    notification_doc.for_user = for_user
    notification_doc.email_content = email_content
    notification_doc.document_type = document_type
    notification_doc.document_name = document_name
    notification_doc.save()
    frappe.db.commit()

@frappe.whitelist()
def create_todo(doctype, name, assign_to, owner, description):
    ''' Method used for create ToDo '''
    todo = frappe.new_doc('ToDo')
    todo.status = 'Open'
    todo.owner = owner
    todo.reference_type = doctype
    todo.reference_name = name
    todo.description = description
    todo.allocated_to = assign_to
    todo.date = frappe.utils.today()
    todo.save(ignore_permissions = True)

@frappe.whitelist()
def task_daily_sheduler():
    """ Method to send task before due date and overdue notification to employee and task overdue and no action taken notification to director"""
    tasks = frappe.db.get_all('Task', filters= {'status': ['not in', ['Template', 'Completed', 'Cancelled']]})
    if tasks:
        for task in tasks:
            doc = frappe.get_doc('Task', task.name)
            assigns = frappe.db.get_value('Task', doc.name, '_assign')
            if assigns:
                assigns = json.loads(assigns)
                for assign in assigns:
                    context = get_context(doc)
                    if assign:
                        today = frappe.utils.today()
                        if doc.exp_end_date:
                            days_diff = date_diff(getdate(doc.exp_end_date), getdate(today))
                            if days_diff == 0:
                                send_notification(doc, assign, context, 'task_overdue_notification_for_employee')
                                send_notification_to_roles(doc, 'Director', context, 'task_overdue_notification_for_director')
                            if days_diff == 1:
                                send_notification(doc, assign, context, 'task_before_due_date__notification')
                        if doc.exp_start_date:
                            if doc.status == 'Open' and (getdate(doc.exp_start_date) < getdate(today)):
                                send_notification_to_roles(doc, 'Director', context, 'no_action_taken_notification_for_director')

@frappe.whitelist()
def send_notification(doc, for_user, context, notification_template_fieldname):
    notification_template = frappe.db.get_value('Compliance Sub Category', doc.compliance_sub_category, notification_template_fieldname)
    if notification_template:
        subject_template, content_template = frappe.db.get_value('Notification Template', notification_template, ['subject', 'content'])
        subject = frappe.render_template(subject_template, context)
        content = frappe.render_template(content_template, context)
        create_notification_log(subject, 'Mention', for_user, content, doc.doctype, doc.name)

@frappe.whitelist()
def send_notification_to_roles(doc, role, context, notification_template_fieldname):
    """ Method to send notification to perticular role """
    users = get_users_with_role(role)
    for user in users:
        send_notification(doc, user, context, notification_template_fieldname)

@frappe.whitelist()
def view_credential_details(customer,purpose):
    """ Method to view customer Credential details """
    if frappe.db.exists('Customer Credentials',{'customer':customer}):
        customer_credential = frappe.db.get_value('Customer Credentials',{'customer':customer})
        if frappe.db.exists('Credential Details', {'parent':customer_credential,'purpose':purpose}):
            username, password, url = frappe.db.get_value('Credential Details', {'parent':customer_credential,'purpose':purpose}, ['username', 'password','url'])
            return [username, password, url]
        else:
            frappe.throw(_('Credential not configured for this Purpose'))

@frappe.whitelist()
def view_customer_documents(customer,compliance_sub_category):
    """ Method to view customer documents """
    if frappe.db.exists('Customer Document',{'customer':customer}):
        customer_document =frappe.db.get_value('Customer Document',{'customer':customer})
        if frappe.db.exists('Customer Document Record',{'parent':customer_document,'compliance_sub_category':compliance_sub_category}):
            document_attachment = frappe.db.get_value('Customer Document Record',{'parent':customer_document,'compliance_sub_category':compliance_sub_category}, ['document_attachment'])
            return [document_attachment]
        else:
            frappe.throw(_('Document not attached for this sub category'))


@frappe.whitelist()
def edit_customer_credentials(customer):
    """ Method to edit or add customer Credential """
    if frappe.db.exists('Customer Credentials',{'customer':customer}):
        customer_credential = frappe.db.get_value('Customer Credentials',{'customer':customer})
        return customer_credential
                        days_diff = date_diff(getdate(doc.expected_time), today)
                        if days_diff == 1:
                            sub_doc = frappe.db.get_value('Compliance Sub Category', doc.compliance_sub_category, 'task_before_due_date__notification')
                            if sub_doc:
                                subject_template, content_template = frappe.db.get_value('Notification Template', sub_doc, ['subject', 'content'])
                                subject = frappe.render_template(subject_template, context)
                                content = frappe.render_template(content_template, context)
                                create_notification_log(subject, 'Mention', assign, content, doc.doctype, doc.name)
                        if days_diff == 0:
                            sub_doc = frappe.db.get_value('Compliance Sub Category', doc.compliance_sub_category, 'task_overdue_notification')
                            if sub_doc:
                                subject_template, content_template = frappe.db.get_value('Notification Template', sub_doc, ['subject', 'content'])
                                subject = frappe.render_template(subject_template, context)
                                content = frappe.render_template(content_template, context)
                                create_notification_log(subject, 'Mention', assign, content, doc.doctype, doc.name)

@frappe.whitelist()
def create_and_assign_task_automatically():
    sub_category_list = frappe.db.get_all('Compliance Sub Category')
    for sub_category in sub_category_list:
        sub_category_doc = frappe.get_doc('Compliance Sub Category', sub_category.name)
        if sub_category_doc.allow_repeat == 1:
            task_list = frappe.get_last_doc('Task', {'compliance_sub_category' : sub_category_doc.name})
            print(task_list)
            project_doc = frappe.get_doc('Project', task_list.project)
            print(project_doc)
            agreement_doc = frappe.get_doc('Compliance Agreement', project_doc.compliance_agreement)
            current_date = getdate(today())
            print(current_date)
            due_date = task_list.exp_start_date
            if sub_category_doc.repeat_on == 'Monthly':
                next_date = add_months(due_date, 1)
                print(next_date)
                if next_date == current_date:
                    print("inside")
                    create_project_from_agreement(agreement_doc.name)
                    assign_task_automatically(project_doc)
            if sub_category_doc.repeat_on == 'Quarterly':
                next_date = add_months(due_date, 3)
                if next_date == current_date:
                    create_project_from_agreement(agreement_doc)
                    assign_task_automatically(project_doc)
            if sub_category_doc.repeat_on == 'Half yearly':
                next_date = add_months(due_date, 6)
                if next_date == current_date:
                    create_project_from_agreement(agreement_doc)
                    assign_task_automatically(project_doc)
            if sub_category_doc.repeat_on == 'yearly':
                next_date = add_months(due_date, 12)
                if next_date == current_date:
                    create_project_from_agreement(agreement_doc)
                    assign_task_automatically(project_doc)

@frappe.whitelist()
def assign_task_automatically(project_doc):
    all_task = frappe.db.get_all('Task', {'project' : project_doc.name})
    print(all_task)
    for tasks in all_task:
        task_items = frappe.get_doc('Task', tasks.name)
        assign_to = task_items._assign
        assign_to = json.loads(assign_to)
        for assign in assign_to:
            print(assign)
            create_todo('Task', task_items.get('task'), assign, assign, 'Tasks Assigned Successfully')
