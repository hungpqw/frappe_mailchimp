import json

import frappe
import mailchimp_transactional
from mailchimp_transactional.api_client import ApiClientError
from six import string_types


def send_message_with_template(recipients, subject: str, from_email: str, template: str, variables, raise_exc=False):
  if isinstance(recipients, string_types):
    recipients = json.loads(recipients)
  if isinstance(variables, string_types):
    variables = json.loads(variables)
  if not raise_exc:
    try:
      return _send_message(recipients, subject, from_email, template, variables)
    except ApiClientError as error:
      frappe.log_error(str(error.__dict__), "Mailchimp: API Error")
    except Exception as e:
      frappe.log_error(str(e.__dict__), "Mailchimp: Error")
  else:
    return _send_message(recipients, subject, from_email, template, variables)


def _send_message(recipients: list, subject: str, from_email: str, template: str, variables: list):
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
              "global_merge_vars": variables
          }
      }
  )


def get_mailchimp_api_key() -> str:
  api_key = frappe.get_value("Mailchimp Settings", "Mailchimp Settings", "api_key")
  if api_key is None:
    frappe.throw("Mailchimp API Key not specified")
  return api_key


def _validate_template(template: str, template_content: list) -> None:
  if template is None or not len(template):
    frappe.throw("Template name missing")

  if template_content and len(template_content):
    if not all(map(lambda x: x.get("name", None) is not None and x.get("content", None) is not None, template_content)):
      frappe.throw("Template Content invalid. Make sure 'name' and 'content' are specified as strings")


def _validate_recipients(recipients: list) -> None:
  if recipients is None or len(recipients) == 0:
    frappe.throw("Recipients must be defined")

  for recipient in recipients:
    email = recipient.get('email', None)
    if email is None:
      frappe.throw("Email must be specified")
