import datetime
import json

import frappe
import mailchimp_transactional
from frappe.model.document import Document
from frappe.utils import get_datetime_str
from mailchimp_transactional.api_client import ApiClientError
from six import string_types

#whitelist this function
@frappe.whitelist(allow_guest=True)
def send_email_with_template(recipients, from_email: str, template: str, variables, subject: str = None,
                             bcc_address: str = None, raise_exc=False) -> dict:
  """
  Send a transactional email to a list of recipients using a template defined in Mailchimp (Mandrill)
  :param recipients: List of emails to send to.
  [{
    "email":"abc@example.com"
  }]
  :param subject: The subject of the email (Optional since the subject can be set to a default)
  :param from_email: The sender of the email
  :param template: The name (slug) of the template as in Mandrill
  :param variables: The dynamic content in the template as a list of dict
   [{
    "name":"variable_name",
    "content":"variable_value"
   }]
  :param bcc_address: BCC Address
  :param raise_exc: Whether to raise exception or not when sending the email
  :return: The response from the Mailchimp Transactional API
  """
  from_email="hungpqtcv@gmail.com"
  template="default_template"
  subject="Test"
  recipients=[{"email":"hung.pham@wellspringsaigon.edu.vn"}]
  variables=[{"name":"variable_name","content":"variable_value"}]
  
  if isinstance(recipients, string_types):
    recipients = json.loads(recipients)
  if isinstance(variables, string_types):
    variables = json.loads(variables)
  if not raise_exc:
    # Fail silently
    try:
      return _send_message(recipients, subject, from_email, template, variables)
    except ApiClientError as error:
      frappe.log_error(frappe.get_traceback(), "Mailchimp: API Error")
    except Exception as e:
      frappe.log_error(frappe.get_traceback(), "Mailchimp: Error")
  else:
    # Raise exceptions
    return _send_message(recipients, subject, from_email, template, variables, bcc_address)

def _send_message(recipients: list, subject: str, from_email: str, template: str, variables: list,
                  bcc_address: str = None) -> dict:
  _validate_recipients(recipients)
  _validate_template(template, variables)

  client = mailchimp_transactional.Client(get_mailchimp_api_key())
  return client.messages.send_template(
      {
          "template_name": template,
          "template_content": [],  # For backward compatibility reason, just an empty array
          "message": {
              "to": recipients,
              "subject": subject,
              "from_email": from_email,
              "merge_language": "handlebars",
              "global_merge_vars": variables,
              "bcc_address": bcc_address
          }
      }
  )


def get_mailchimp_api_key() -> str:
  """
  Returns the API key of Transactional Email of Mailchimp (Mandrill)
  :return:
  """
  api_key = frappe.get_value("Mailchimp Settings", "Mailchimp Settings", "transactional_email_api_key")
  if api_key is None:
    frappe.throw("Mailchimp API Key not specified")
  return api_key


def _validate_template(template: str, variables: list) -> None:
  """
  Checks whether the template is not empty and that the variables are in the correct format with values
  :param template: The slug (name) of the template
  :param variables: The list of variables for dynamic content
  :return:
  """
  if template is None or not len(template):
    frappe.throw("Template name missing")

  if variables and len(variables):
    if not all(map(lambda x: x.get("name", None) is not None and x.get("content", None) is not None, variables)):
      frappe.throw("Template Content invalid. Make sure 'name' and 'content' are specified as strings")


def _validate_recipients(recipients: list) -> None:
  """
  Checks whether the recipients list are valid and that it's in the right format
  :param recipients: The list of emails that will be sent to
  :return:
  """
  if recipients is None or len(recipients) == 0:
    frappe.throw("Recipients must be defined")

  for recipient in recipients:
    email = recipient.get('email', None)
    if email is None:
      frappe.throw("Email must be specified")


def create_vars_from_doc(doc: Document, key=None) -> list:
  """
  Utility function to prepare the template vars from a doc
  :param doc: The document as a dictionary
  :param key: Optionally specify the key name. If not specified, the scrub name of the doctype will be used
              For instance, Sales Order will be called sales_order
  :return:
  """
  if not doc:
    return []
  doc = doc.as_dict(convert_dates_to_str=True, no_nulls=True)
  if len(doc) == 0:
    return []
  doctype = doc.get("doctype").lower()
  template_vars = []
  to_del = []
  for k, v in doc.items():
    # Remove iterables from the variables
    if isinstance(v, (list, tuple, dict)):
      to_del.append(k)
      continue
    # Convert date object to string
    if isinstance(v, datetime.date):
      doc[k] = get_datetime_str(v)
  for k in to_del:
    del doc[k]
  template_vars.append({"name": key if key is not None else frappe.scrub(doctype), "content": doc})
  return template_vars
