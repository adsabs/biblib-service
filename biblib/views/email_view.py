"""
Email view
"""
from base_view import BaseView
from flask import request, current_app
from flask.ext.mail import Message
from flask_discoverer import advertise
from ..emails import Email, PermissionsChangedEmail
from ..utils import get_post_data, err
from http_errors import WRONG_TYPE_ERROR, MISSING_USERNAME_ERROR


class EmailView(BaseView):
    """Endpoint to email users"""

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    # TODO decide on rate limits
    rate_limit = [50, 60 * 60 * 24]

    @staticmethod
    def send_email(email_addr='', email_template=Email, payload=None):
        """
        Encrypts a payload using itsDangerous.TimeSerializer, adding it along with a base
        URL to an email template. Sends an email with this data using the current app's
        'mail' extension.

        :param email_addr:
        :type email_addr: basestring
        :param email_template: emails.Email
        :param payload

        :return: msg,token
        :rtype flask.ext.mail.Message, basestring
        """
        if payload is None:
            payload = []
        if isinstance(payload, (list, tuple)):
            payload = ' '.join(map(unicode, payload))
        msg = Message(subject=email_template.subject,
                      recipients=[email_addr],
                      body=email_template.msg_plain.format(payload=payload),
                      html=email_template.msg_html.format(payload=payload.replace('\n','<br>'),email_address=email_addr))
        # TODO make this async?
        current_app.extensions['mail'].send(msg)

        current_app.logger.info('Email sent to {0} with payload: {1}'.format(msg.recipients, msg.body))
        return msg

    def post(self):
        """
        HTTP POST request to send a notification email after editing a user's permissions

        :return: the return for if the email was successfully sent

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post data:
        ----------
        List of dicts
        KEYWORD, VALUE
        email:   <e-mail@address>, specifies which user's permissions were
                                   modified
        library:     library ID,   specifies which library for which permissions were changed (URL safe base64 string)
        permission:  read, write,  specifies which permission was changed
                     admin, owner
        value:   boolean,          whether the user has this permission

        Note:
        Payload is a list of dicts, with each dictionary containing the info for one
        permission change. If the same email address is specified in multiple dictionaries,
        only one email will be sent to that address, with all updated permissions listed.
        """
        # Get the user requesting this from the header
        try:
            user_editing = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        try:
            email_data = get_post_data(
                request,
                types=dict(
                    email=unicode,
                    library=basestring,
                    permission=unicode,
                    value=bool
                )
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)

        unique_emails = list(set(d['email'] for d in email_data))
        for u in unique_emails:
            email_info = filter(lambda person: person['email'] == u, email_data)
            info = []
            for i in email_info:
                # URL safe base64 string to UUID
                library_uuid = self.helper_slug_to_uuid(i['library'])
                name = self.helper_library_name(library_uuid)
                tmp = u'Library: {0} \n    Permission: {1} \n    Have permission? {2} \n'.format(name, i['permission'], i['value'])
                info.append(tmp)
            payload = '\n    '.join(info)

            current_app.logger.info('Sending email to {0} with payload: {1}'.format(u, payload))
            try:
                msg = self.send_email(email_addr=u, email_template=PermissionsChangedEmail, payload=payload)
            except:
                current_app.logger.warning('Sending email to {0} failed'.format(u))

        return {}, 200

