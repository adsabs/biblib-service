"""
Template emails
"""

open_tag = '''<p style="font-family: sans-serif; font-size: 14px; font-weight: normal; margin: 0; Margin-bottom: 15px;">'''

html_template = """
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html>
        <head>
            <meta name="viewport" content="width=device-width">
            <meta http-equiv="Content-Type" content="text/html charset=UTF-8" />
        </head>
        <body>
            <table border="0" cellpadding="0" cellspacing="0" height="100%" width="100%" id="bodyTable" style="background-color: #E0E0E0;">
                <tr>
                    <td align="center" valign="top">
                        <table border="0" cellpadding="10" cellspacing="0" width="600" id="emailContainer">
                            <tr>
                                <td align="center" valign="top">
                                    <table border="0" cellpadding="20" cellspacing="0" width="100%" id="emailHeader">

                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" valign="top">
                                    <table border="0" cellpadding="20" cellspacing="0" width="100%" id="emailBody" style="background-color: #ffffff;">
                                        <tr>
                                            <td align="center" valign="top" background="https://ui.adsabs.harvard.edu/styles/img/background.jpg" style="width:100%; background-color: #150E35" >
                                                <img src="https://ui.adsabs.harvard.edu/styles/img/ads_logo.png" alt="Astrophysics Data System" style="width: 70%; color: #ffffff; font-size: 34px; font-family: sans-serif;"/> 
                                            </td>
                                        </tr>
                                        <tr>
                                            <td align="left" valign="top">
                                                {msg}
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                            <tr>
                                <td align="center" valign="top">
                                    <table border="0" cellpadding="20" cellspacing="0" width="100%" id="emailFooter" style="color: #999999; font-size: 12px; text-align: center; font-family: sans-serif;">
                                        <tr>
                                            <td align="center" valign="top">
                                                <p> This message was sent to {email_address}. </p>
                                                <p> &copy; SAO/NASA <a href="https://ui.adsabs.harvard.edu">Astrophysics Data System</a> <br> 60 Garden Street <br> Cambridge, MA</p>
                                            </td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
    </html>
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
    msg_plain = '''
    Hi,
    Another user has recently updated your library permissions for the following libraries: 
    
    {payload}
    
    If this is a mistake, please contact the library owner. 
    
    - the ADS team
    '''
    msg = '''
    {open_tag}Hi, </p>
    
    {open_tag}Another user has recently updated your library permissions for the following libraries:</p>
    
    {open_tag}{payload}</p>
    
    {open_tag}If this is a mistake, please contact the library owner.</p>
    
    {open_tag}-the ADS team</p>
    '''.format(open_tag=open_tag,payload='''{payload}''')
    msg_html = html_template.format(msg=msg, email_address='''{email_address}''')
    subject = "[ADS] Your library permissions have been updated"