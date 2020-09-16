import json

import frappe
import mailchimp_transactional
from mailchimp_transactional.api_client import ApiClientError
from six import string_types


def send_email_with_template(recipients, subject: str, from_email: str, template: str, variables,
                             raise_exc=False) -> dict:
  """
  Send a transactional email to a list of recipients using a template defined in Mailchimp (Mandrill)
  :param recipients: List of emails to send to.
  [{
    "email":"abc@example.com"
  }]
  :param subject: The subject of the email
  :param from_email: The sender of the email
  :param template: The name (slug) of the template as in Mandrill
  :param variables: The dynamic content in the template as a list of dict
   [{
    "name":"variable_name",
    "content":"variable_value"
   }]
  :param raise_exc: Whether to raise exception or not when sending the email
  :return: The response from the Mailchimp Transactional API
  """
  if isinstance(recipients, string_types):
    recipients = json.loads(recipients)
  if isinstance(variables, string_types):
    variables = json.loads(variables)
  if not raise_exc:
    # Fail silently
    try:
      return _send_message(recipients, subject, from_email, template, variables)
    except ApiClientError as error:
      frappe.log_error(str(error.__dict__), "Mailchimp: API Error")
    except Exception as e:
      frappe.log_error(str(e.__dict__), "Mailchimp: Error")
  else:
    # Raise exceptions
    return _send_message(recipients, subject, from_email, template, variables)


def _send_message(recipients: list, subject: str, from_email: str, template: str, variables: list) -> dict:
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
