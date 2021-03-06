import imaplib
import email
import os
import itertools

import config
import database
import decode
import file_names


def login():
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(config.username, config.password)
    mail.list()
    # Out: list of "folders" aka labels in gmail.
    mail.select("inbox")  # connect to inbox.
    return mail

def get_sender_address(msg):
    sender = msg['from'].split()[-1]
    address = email.utils.parseaddr(sender)[-1]
    return address

def get_payment_system(file_name, address):
    if file_name.count(config.kaspi_key) != 0 and address == config.kaspi_address:
        return config.kaspi_key
    if file_name.count(config.rps_key) != 0 and address == config.rps_address:
        return config.rps_key
    if file_name.count(config.processing_key) != 0 and address == config.processing_address:
        return config.processing_key
    if file_name.count(config.qazkom_key) != 0 and address == config.qazkom_address:
        return config.qazkom_key
    return 'unknown payment system'

def save_attachments(msg):
    full_list = list()
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
            continue
        original_file_name = decode.decode_file_name(part.get_filename()).lower()

        sender_address = get_sender_address(msg)
        payment_system = get_payment_system(original_file_name, sender_address)
        new_file_name = file_names.set_file_name(original_file_name, payment_system)

        if bool(new_file_name):
            file_path = os.path.join(config.attachment_dir, new_file_name)
            with open(file_path, 'wb') as f:
                f.write(part.get_payload(decode=True))
                full_list.append(new_file_name)
    return full_list


def parse_gmail():
    mail = login()
    result, data = mail.search(None, "ALL")
    id_list = database.get_unread_messages(data[0].split())
    attachments_list = list()
    for mail_id in id_list:
        result, data = mail.fetch(mail_id, config.mail_format)
        raw = email.message_from_bytes(data[0][1])
        files = save_attachments(raw)
        if len(files) != 0:
            attachments_list.append(files)
    database.add_messages(id_list)
    attachments_list = list(itertools.chain.from_iterable(attachments_list))
    return attachments_list
