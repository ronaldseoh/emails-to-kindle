import email
import email.policy

import tempfile
import os
import json
from subprocess import check_call
import datetime

from imapclient import IMAPClient
from bs4 import BeautifulSoup as Soup

from rs_mailer import EmailSender


# Check the path of the directory where this script is located
# to read keys and config files 
# (Ignore symbolic links)
script_location = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(script_location, "emails-to-kindle_config.json"), 'r') as config_file:
    config = json.load(config_file)

today_date = datetime.datetime.utcnow().date() 
today = str(today_date)
    
temp_directory_path = os.path.join(tempfile.gettempdir(), 'emails-to-kindle', today)

check_call(['mkdir', '-p', temp_directory_path])

os.chdir(temp_directory_path)

with IMAPClient(config['imap_address']) as imap_server_connection:
    imap_server_connection.login(config['email_id'], config['email_pw'])
    imap_server_connection.select_folder('INBOX')

    messages = imap_server_connection.search('UNSEEN')
    
    if len(messages) > 0:
        for _, message_data in imap_server_connection.fetch(messages, 'RFC822').items():
            email_message = email.message_from_bytes(message_data[b'RFC822'], policy=email.policy.default)
            
            payloads = email_message.get_payload()
            
            for payload in payloads:
                if payload.get_content_type() == 'text/html':
                    payload_html = payload.get_content()
                    
                    payload_soup = Soup(payload_html, features='lxml')
                    
                    html_tag = payload_soup.find('html')
                    
                    head_tag = payload_soup.new_tag('head')
                    html_tag.insert(0, head_tag)
                    
                    title_tag = payload_soup.new_tag('title')
                    title_tag.string = email_message.get('From') + ': ' + email_message.get('Subject')
                    
                    print(title_tag.string)
                    
                    head_tag.insert(0, title_tag)
                    
                    filename = today + " ".join([c for c in title_tag.string if c.isalpha() or c.isdigit() or c==' ']).rstrip()
                    
                    with open(filename + '.html', 'w') as output_file:
                        output_file.write(str(payload_soup))
                        
                    break
            
            # Create EmailSender instance
            sender = EmailSender(
                id=config['email_id'],
                password=config['email_pw'],
                smtp_address=config['smtp_address'],
                port_number=config['smtp_port_number'],
                ssl_needed=config['smtp_ssl_needed'],
                recipient_addresses=config['email_recipient_addresses'],
                subject=config['email_subject'],
                msg_body=config['email_subject'],
                attachments_path=filename + '.html'
            )

            # Send the email
            sender.send()
    else:
        print("No new emails.")