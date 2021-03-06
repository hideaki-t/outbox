#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import base64
from codecs import lookup
from email.header import decode_header
from email.mime.base import MIMEBase
from email.mime.text import MIMEText

try:
    from unittest import mock
except ImportError:
    import mock

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from outbox import Outbox, Attachment, Email


def test_encoding():
    for body in [u'すすめ商品を見るに', u'Российская Федерация']:
        message = Email(['nathan@getoffmalawn.com'], 'subject', body)
        text = message.as_mime().as_string()
        assert base64.b64encode(body.encode('UTF-8')).decode('utf8') in text, u"The encoded form of '%s' is incorrect!" % body


def test_attachment_raw_data():
    attachment = Attachment('my filename', fileobj=StringIO('this is some data'))

    assert attachment.name == 'my filename'
    assert attachment.raw == b'this is some data'


def test_attachment_file():
    attachment = Attachment('my filename', fileobj=open(__file__, 'rb'))

    assert attachment.name == 'my filename'
    assert attachment.raw == open(__file__, 'rb').read()
    assert attachment.read() == open(__file__, 'rb').read()

    attachment = Attachment('my filename', fileobj=StringIO('foo data'))

    assert attachment.name == 'my filename'
    assert attachment.raw == b'foo data'
    assert attachment.read() == b'foo data'


def test_rfc2231():
    filename = u'ファイル名'
    a = [Attachment(filename, fileobj=StringIO('this is some data'))]

    e = Email(['test@example.com'], 'subject', 'body')
    assert e.as_mime(a).get_payload()[1].get_filename() == filename

    e = Email(['test@example.com'], 'subject', 'body', rfc2231=True)
    assert e.as_mime(a).get_payload()[1].get_filename() == filename

    e = Email(['test@example.com'], 'subject', 'body', rfc2231=False)
    h, enc = decode_header(e.as_mime(a).get_payload()[1].get_filename())[0]
    assert h.decode(enc) == filename


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
              body='body', fields={'Reply-To': 'nobody@nowhere.com'})

    assert e.body == 'body'
    assert e.subject == 'subject'
    assert e.recipients == ['nathan@getoffmalawn.com']
    assert e.fields == {'Reply-To': 'nobody@nowhere.com'}


def test_content_type():
    alt = 'multipart/alternative'
    mixed = 'multipart/mixed'
    text = 'text/plain'
    html = 'text/html'
    octstr = 'application/octet-stream'
    attachments = [Attachment('filename', fileobj=StringIO('content'))]

    def t(m, root_ct, root_cs, expected_parts):
        def cmpcs(actual, expected):
            if expected is None:
                assert actual is None
            else:
                assert lookup(actual.input_charset) == lookup(expected)

        assert m.get_content_type() == root_ct
        cmpcs(m.get_charset(), root_cs)
        p = m.get_payload()
        for p, e in zip(m.get_payload(), expected_parts):
            typ, ct, cs = e
            assert isinstance(p, typ)
            assert p.get_content_type() == ct
            cmpcs(p.get_charset(), cs)

    e = Email(recipients=['test@example.com'], subject='subject', body='body')
    t(e.as_mime(), text, 'utf8', [])
    t(e.as_mime(attachments), mixed, None,
      [(MIMEText, text, 'utf8'), (MIMEBase, octstr, None)])

    e = Email(recipients=['test@example.com'], subject='subject', html_body='body')
    t(e.as_mime(), html, 'utf8', [])
    t(e.as_mime(attachments), mixed, None,
      [(MIMEText, html, 'utf8'), (MIMEBase, octstr, None)])

    e = Email(recipients=['test@example.com'], subject='subject', body='body', html_body='body')
    t(e.as_mime(), alt, None,
      [(MIMEText, text, 'utf8'), (MIMEText, html, 'utf8')])
    t(e.as_mime(attachments), mixed, None,
      [(MIMEBase, alt, None), (MIMEBase, octstr, None)])
    t(e.as_mime(attachments).get_payload()[0], alt, None,
      [(MIMEText, text, 'utf8'), (MIMEText, html, 'utf8')])


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
    assert o.connection_details == ('server', 1234, 'TLS', False)


def test_outbox_login():
    o = Outbox('username', 'password', 'server', 1234)

    with mock.patch('smtplib.SMTP') as SMTP:
        smtp = SMTP.return_value
        o._login()

    print(smtp.mock_calls)
    smtp.set_debuglevel.assert_any_call(False)
    smtp.starttls.assert_any_call()
    smtp.login.assert_any_call('username', 'password')


def test_outbox_login_errors():
    try:
        Outbox('username', 'password', 'server', 1234, mode='asdf')
    except ValueError:
        pass
    else:
        assert False, "Invalid node not blocked"


def test_outbox_send():
    message = Email(['nathan@getoffmalawn.com'], 'subject', 'body')
    o = Outbox('username', 'password', 'server', 1234, debug=True)

    import email.mime.multipart

    with mock.patch.object(email.mime.multipart.MIMEMultipart, 'as_string', lambda self: 'foo'):
        with mock.patch('smtplib.SMTP') as SMTP:
            smtp = SMTP.return_value
            o.send(message, [Attachment('foo', fileobj=StringIO('foo'))])

    smtp.set_debuglevel.assert_any_call(True)
    smtp.starttls.assert_any_call()
    smtp.login.assert_any_call('username', 'password')
    smtp.sendmail.assert_any_call('username', message.recipients, 'foo')
    smtp.quit.assert_any_call()


def test_outbox_context():
    message = Email(['nathan@getoffmalawn.com'], 'subject', 'body')
    outbox = Outbox('username', 'password', 'server', 1234)

    import email.mime.multipart

    with mock.patch.object(email.mime.multipart.MIMEMultipart, 'as_string', lambda self: 'foo'):
        with mock.patch('smtplib.SMTP') as SMTP:
            smtp = SMTP.return_value
            with outbox as o:
                o.send(message, [Attachment('foo', fileobj=StringIO('foo'))])

    smtp.set_debuglevel.assert_any_call(False)
    smtp.starttls.assert_any_call()
    smtp.login.assert_any_call('username', 'password')
    smtp.sendmail.assert_any_call('username', message.recipients, 'foo')
    smtp.quit.assert_any_call()


if __name__ == '__main__':
    test_encoding()
    test_attachment_raw_data()
    test_attachment_file()
    test_rfc2231()
    test_email_errors_recipients()
    test_email_errors_bodies()
    test_email()
    test_content_type()
    test_single_recipient_becomes_list()
    test_outbox_attributes()
    test_outbox_login()
    test_outbox_login_errors()
    test_outbox_send()
    test_outbox_context()
    print("All tests passed")
