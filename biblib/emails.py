"""
Template emails
"""

class Email(object):
    """
    Data structure that contains email content data
    """
    msg_plain = ''
    msg_html = ''
    subject = ''
    salt = ''

class PermissionsChangedEmail(Email):
    msg_plain = '''{payload}'''
    msg_html = '''{payload}'''
    subject = "[ADS] Your library permissions have been updated"