#!/usr/bin/env python2

import mox

from outbox import Outbox, Attachment, Email

from StringIO import StringIO

class replace(object):
    def __init__(self, orig, new):
        self.orig = orig
        self.parent = orig.im_class
        self.orig_name = orig.im_func.__name__
        self.new = new

    def __enter__(self):
        setattr(self.parent, self.orig_name, self.new)

    def __exit__(self, type, value, traceback):
        setattr(self.parent, self.orig_name, self.orig)

def test_encoding():
    body = u'すすめ商品を見るに'
    body = u'Российская Федерация'
    message = Email(['nathan@getoffmalawn.com'], 'subject', body)

    text = message.as_mime().as_string()

    assert 'w5DCoMOQwr7DkcKBw5HCgcOQwrjDkMK5w5HCgcOQwrrDkMKww5HCjyDDkMKkw5DCtcOQwrTDkMK1\nw5HCgMOQwrDDkcKGw5DCuMORwo8=' in text, u"The encoded form of '%s' is incorrect!" % body

def test_attachment_raw_data():
    attachment = Attachment('my filename', fileobj=StringIO('this is some data'))

    assert attachment.name == 'my filename'
    assert attachment.raw == 'this is some data'

def test_attachment_file():
    attachment = Attachment('my filename', fileobj=open(__file__, 'rb'))

    assert attachment.name == 'my filename'
    assert attachment.raw == open(__file__, 'rb').read()
    assert attachment.read() == open(__file__, 'rb').read()

    attachment = Attachment('my filename', fileobj=StringIO('foo data'))

    assert attachment.name == 'my filename'
    assert attachment.raw == 'foo data'
    assert attachment.read() == 'foo data'

def test_email_errors_recipients():
    test_args = [
        (None, '', ''),
        ([], '', ''),
        (5, '', ''),
        ([5], '', ''),
    ]

    for f in test_args:
        try:
            Email(*f)
        except (ValueError, TypeError):
            pass
        else:
            assert False, "No recipients should be stopped"

def test_email_errors_bodies():
    try:
        Email(recipients=[''], subject='foo', body=None, html_body=None)
    except ValueError:
        pass
    else:
        assert False, "You shouldn't be able to construct an email with no body"

def test_email():
    e = Email(recipients=['nathan@getoffmalawn.com'], subject='subject',
            body='body')

    assert e.body == 'body'
    assert e.subject == 'subject'
    assert e.recipients == ['nathan@getoffmalawn.com']

def test_single_recipient_becomes_list():
    e = Email(recipients='nathan@getoffmalawn.com', subject='subject',
            body='body')

    assert isinstance(e.recipients, list)
    assert e.recipients == ['nathan@getoffmalawn.com']
    assert e.recipients != 'nathan@getoffmalawn.com'

def test_outbox_attributes():
    o = Outbox('username', 'password', 'server', 1234)

    assert o.username == 'username'
    assert o.password == 'password'
    assert o.connection_details == ('server', 1234, 'TLS')

def test_outbox_login():
    m = mox.Mox()

    import smtplib

    smtplib.SMTP = m.CreateMockAnything()
    smtp = m.CreateMockAnything()
    smtplib.SMTP('server',1234).AndReturn(smtp)
    smtp.starttls()
    smtp.login('username', 'password')

    m.ReplayAll()

    o = Outbox('username', 'password', 'server', 1234)
    o._login()

    m.VerifyAll()
    m.UnsetStubs()

def test_outbox_login_errors():
    try:
        Outbox('username', 'password', 'server', 1234, mode='asdf')
    except ValueError:
        pass
    else:
        assert False, "Invalid node not blocked"


def test_outbox_send():
    m = mox.Mox()
    message = Email(['nathan@getoffmalawn.com'], 'subject', 'body')

    import smtplib, email.mime.multipart

    with replace(email.mime.multipart.MIMEMultipart.as_string, lambda self: 'foo'):
        smtplib.SMTP = m.CreateMockAnything()
        smtp = m.CreateMockAnything()

        smtplib.SMTP('server', 1234).AndReturn(smtp)

        smtp.starttls()
        smtp.login('username', 'password')
        smtp.sendmail('username', message.recipients, 'foo')
        smtp.quit()

        m.ReplayAll()

        o = Outbox('username', 'password', 'server', 1234)
        o.send(message, [Attachment('foo', fileobj=StringIO('foo'))])

        m.VerifyAll()
        m.UnsetStubs()

def test_outbox_context():
    m = mox.Mox()
    message = Email(['nathan@getoffmalawn.com'], 'subject', 'body')

    import smtplib, email.mime.multipart

    with replace(email.mime.multipart.MIMEMultipart.as_string, lambda self: 'foo'):
        smtplib.SMTP = m.CreateMockAnything()
        smtp = m.CreateMockAnything()

        smtplib.SMTP('server', 1234).AndReturn(smtp)

        smtp.starttls()
        smtp.login('username', 'password')
        smtp.sendmail('username', message.recipients, 'foo')
        smtp.quit()

        m.ReplayAll()

        with Outbox('username', 'password', 'server', 1234) as o:
            o.send(message, [Attachment('foo', fileobj=StringIO('foo'))])

        m.VerifyAll()
        m.UnsetStubs()
