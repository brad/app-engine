"""Environment params and backend implementations."""

import json
import logging
import datetime

from google.appengine.api import mail
from google.appengine.ext import deferred
from mailchimp import mailchimp
import stripe

import handlers
import model


def get_env():
  """Get environmental parameters."""
  j = json.load(open('config.json'))

  stripe_backend = None
  mailing_list_subscriber = None
  if j['appName'] == 'local':
    stripe_backend = FakeStripe()
    mailing_list_subscriber = FakeSubscriber()
  else:
    stripe_backend = ProdStripe(model.Config.get().stripe_private_key)
    mailing_list_subscriber = MailchimpSubscriber()

  return handlers.Environment(
    app_name=j['appName'],
    stripe_public_key=model.Config.get().stripe_public_key,
    stripe_backend=stripe_backend,
    mailing_list_subscriber=mailing_list_subscriber,
    mail_sender=MailSender())


class ProdStripe(handlers.StripeBackend):
  def __init__(self, stripe_private_key):
    self.stripe_private_key = stripe_private_key

  def CreateCustomer(self, email, card_token):
    stripe.api_key = self.stripe_private_key
    customer = stripe.Customer.create(card=card_token, email=email)
    return customer.id

  def Charge(self, customer_id, amount_cents):
    stripe.api_key = self.stripe_private_key
    try:
      charge = stripe.Charge.create(
        amount=amount_cents,
        currency='usd',
        customer=customer_id,
        statement_description='MayOne.US',
      )
    except stripe.CardError, e:
      raise handlers.PaymentError(str(e))
    return charge.id


class FakeStripe(handlers.StripeBackend):
  def CreateCustomer(self, email, card_token):
    logging.error('USING FAKE STRIPE')
    if email == 'failure@failure.biz':
      return 'doomed_customer'
    else:
      return 'fake_1234'

  def Charge(self, customer_id, amount_cents):
    logging.error('USING FAKE STRIPE')
    if customer_id == 'doomed_customer':
      raise handlers.PaymentError(
        'You have no chance to survive make your time')
    logging.error('CHARGED CUSTOMER %s %d cents', customer_id, amount_cents)
    return 'fake_charge_1234'


class MailchimpSubscriber(handlers.MailingListSubscriber):
  def Subscribe(self, email, first_name, last_name, amount_cents, ip_addr, time,
                source, phone=None, zipcode=None, volunteer=None, skills=None, rootstrikers=None,
                nonce=None, pledgePageSlug=None):
    deferred.defer(_subscribe_to_mailchimp,
                   email, first_name, last_name,
                   amount_cents, ip_addr, source, phone, zipcode,
                   volunteer, skills, rootstrikers, nonce, pledgePageSlug)


class FakeSubscriber(handlers.MailingListSubscriber):
  def Subscribe(self, **kwargs):
    logging.info('Subscribing %s', kwargs)


class MailSender(object):
  def __init__(self, defer=True):
    # this can
    self.defer = defer

  def Send(self, to, subject, text_body, html_body, reply_to=None):
    if self.defer:
      deferred.defer(_send_mail, to, subject, text_body, html_body)
    else:
      _send_mail(to, subject, text_body, html_body, reply_to)


def _send_mail(to, subject, text_body, html_body, reply_to=None):
  """Deferred email task"""
  sender = ('MayOne no-reply <noreply@%s.appspotmail.com>' %
            model.Config.get().app_name)
  message = mail.EmailMessage(sender=sender, subject=subject)
  message.to = to
  message.body = text_body
  message.html = html_body
  if reply_to:
    message.reply_to = reply_to
  message.send()


def _subscribe_to_mailchimp(email_to_subscribe, first_name, last_name,
                            amount, request_ip, source, phone=None, zipcode=None,
                            volunteer=None, skills=None, rootstrikers=None,
                            nonce=None, pledgePageSlug=None):
  mailchimp_api_key = model.Config.get().mailchimp_api_key
  mailchimp_list_id = model.Config.get().mailchimp_list_id
  mc = mailchimp.Mailchimp(mailchimp_api_key)

  merge_vars = {
    'FNAME': first_name,
    'LNAME': last_name,
    'optin_ip': request_ip,
    'optin_time': str(datetime.datetime.now())
  }

  if source:
    merge_vars['SOURCE'] = source

  if amount:
    amount_dollars = '{0:.02f}'.format(float(amount) / 100.0)
    merge_vars['LASTPLEDGE'] = amount_dollars

  if volunteer == 'Yes':
    merge_vars['VOLN'] = volunteer

  if nonce is not None:
    merge_vars['UUT'] = nonce

  if skills is not None and len(skills)>0:
    merge_vars['SKILLS'] = skills[0:255]

  if phone is not None:
    merge_vars['PHONE'] = phone

  if zipcode is not None:
    merge_vars['ZIPCODE'] = zipcode
  
  if rootstrikers is not None:
    merge_vars['ROOTS'] = rootstrikers
    
  if pledgePageSlug is not None:
    merge_vars['PPURL'] = pledgePageSlug

  # list ID and email struct
  logging.info('Subscribing: %s', email_to_subscribe)
  mc.lists.subscribe(id=mailchimp_list_id,
                     email=dict(email=email_to_subscribe),
                     merge_vars=merge_vars,
                     double_optin=False,
                     update_existing=True,
                     send_welcome=False)
