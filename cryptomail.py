import os
import sys
import yaml
import gnupg
import socks
import getpass
import smtplib
import datetime
import argparse
from email.mime.text import MIMEText

class Email(object):

    def __init__(self, recipient, subject, body):
        self.gpg = gnupg.GPG(homedir='~/.gnupg')
        self.smtp = None
        self.recipient = recipient
        self.subject = subject
        self.body = body

    def connect(self):
        if CFG['tor']:
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, '0.0.0.0', 9000, True)
            socks.wrapmodule(smtplib)

        self.smtp = smtplib.SMTP(CFG['host'], CFG['port'])
        self.smtp.starttls()
        self.smtp.login(CFG['user'], CFG['pwd'])

    def find_keyid(self):
        keys = self.gpg.list_keys()
        for key in keys:
            for uid in key['uids']:
                if self.recipient in uid:
                    return key['keyid']

        return None

    def send(self):
        keyid = self.find_keyid()
        if not keyid:
            print("ERROR: not found a key for {0}".format(self.recipient))
            return

        encrypted_data = self.gpg.encrypt(self.body, keyid)
        encrypted_body = str(encrypted_data)

        msg = MIMEText(encrypted_body)
        msg['Subject'] = self.subject
        msg['From'] =  CFG['from']
        msg['To'] = self.recipient
        msg['Date'] = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')

        self.connect()
        self.smtp.sendmail(CFG['from'], [self.recipient], msg.as_string())

class Scheduler(object):

    def run(self, email_path):
        if not os.path.exists(email_path):
            print("ERROR: email file does not exist")
            return

        with open(email_path, 'r') as handle:
            data = handle.read()

        headers_raw, body = data.split("\n\n", 1)
        headers = yaml.load(headers_raw)

        for recipient in CFG['recipients']:
            print("Sending to " + recipient)
            eml = Email(recipient, headers['Subject'], body)
            eml.send()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('mail', metavar='MAIL', help="file containing the mail subject and body")
    parser.add_argument('-c', '--config', action='store', default='config.yaml', help="config you want to use (default: config.yaml)")
    args = parser.parse_args()

    if args.config:
        arg_cfg = args.config
    else:
        arg_cfg = 'config.yaml'

    if not os.path.exists(arg_cfg):
        print("ERROR: config file does not exist")
        sys.exit(-1)

    with open(arg_cfg, 'r') as handle:
        CFG = yaml.load(handle.read())

    CFG['pwd'] = getpass.getpass("Insert the password for {}: " .format(CFG['user']))

    s = Scheduler()
    s.run(args.mail)
