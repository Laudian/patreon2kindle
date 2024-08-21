from bs4 import BeautifulSoup
from datetime import datetime
from email import policy
from smtplib import SMTP
from email.message import EmailMessage
import imaplib
import email
import time
import quopri
import os
import sqlite3
import configparser
import pytz
import subprocess

class Patreon2Kindle():
    
    def init_db(self):
        self.db = sqlite3.connect("database.db")
        self.cur = self.db.cursor()

        # Check if DB is already initialized
        if self.cur.execute("SELECT name FROM sqlite_master").fetchone() is None:
            self.cur.execute("CREATE TABLE chapters(mailid, author, title, source, content_html, content_clean, datetime)")

    def init_conf(self):
        self.conf = configparser.ConfigParser()
        self.conf.read('patreon2kindle.conf')

    def get_mails(self, author: str):
        imap = imaplib.IMAP4_SSL(host=self.conf["EMAIL"]["imap_host"])
        imap.login(self.conf["EMAIL"]["username"], self.conf["EMAIL"]["password"])
        imap.select()
        
        typ, msg_ids = imap.search(None, f'(FROM "{author} (via Patreon)")')
        all_ids = [int(x) for x in msg_ids[0].decode().split()]
        old_ids = self.get_old_ids(author)
        if old_ids is None:
            old_ids = []
        new_ids = [x for x in all_ids if x not in old_ids]
        print("Found new IDs: " + str(new_ids))

        mails = []
        for mailid in new_ids:
            # Fetch email Subject + Text and parse
            typ, msg_data = imap.fetch(str(mailid), '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1], policy=email.policy.SMTP)
            
            mails.append((mailid, msg))

        imap.close()
            
        return mails
        
    def get_old_ids(self, author: str):
        old_ids = self.cur.execute(f"SELECT mailid FROM chapters WHERE author='{author}'").fetchall()
        old_ids = [int(x[0]) for x in old_ids]
        return old_ids

    def send_email(self, title: str):
        smtp_host = self.conf["EMAIL"]["smtp_host"]
        username = self.conf["EMAIL"]["username"]
        password = self.conf["EMAIL"]["password"]
        from_addr = self.conf["EMAIL"]["from_address"]
        to_addr = self.conf["EMAIL"]["to_address"]
        filename = title.replace(" ", "_") + ".epub"

        print(f"Sending {title} via email to {to_addr}")

        # Build email
        msg = EmailMessage()
        msg.set_content("New Chapter.")
        msg['Subject'] = title
        msg['From'] = from_addr
        msg['To'] = to_addr
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain="laudian.de")
        #msg.preamble = 'You will not see this in a MIME-aware mail reader.\n'

        with open("convert_output.epub", "rb") as file:
            data = file.read()

        msg.add_attachment(data, maintype="application", subtype="epub+zip",
                           filename=filename)

        # Establish SMTP connection
        
        smtp = SMTP(smtp_host, 587)
        smtp.starttls()
        smtp.ehlo()
        smtp.login(username, password)

        #smtp.send_message(msg, from_addr=from_addr, to_addrs=[to_addr])
        smtp.send_message(msg, from_addr=from_addr, to_addrs=["michael_rabe_GRts9W@kindle.com",
                                                              "michael_rabe@hotmail.de"])

        print(f"{title} sent.\n")
    def run(self):
        self.init_conf()
        self.init_db()

        authors = self.conf["AUTHORS"]
        for author_key in authors:
            author = self.conf["AUTHORS"][author_key]
            print(f"Now looking for chapters from {author}.")
            mails = self.get_mails(author)
            for mailid, mail in mails:
                self.handle_mail(mailid, mail, author)

        if self.conf["GENERAL"]["scan_only"] == "True":
            print("Initial scan completed. You can now change "
                  "'scan_only' to 'False' in the conf file")
        else:
            print("Scan complete.")

        input("Press Enter to close.")

    def handle_mail(self, mailid: int, mail, author: str):
        # Try to parse email/content if possible, add mailid to database anyway if not
        title = mail["subject"].split('"')[1]
        print(f"Found new chapter {title}.")
        try:
            source = mail.get_payload()

            # Fix quoted-printable encoding
            content = quopri.decodestring(source).decode("utf-8")

            # Parse content from source file
            soup = BeautifulSoup(content, "html.parser")
            content_list = soup.find("div")("p")
            content_joined = "".join([str(line)+"\n" for line in content_list])

            # Build HTML file from content    
            content_html = f"<h1 class='chapter'> {title} </h1>\n\n {content_joined}"
                            
            joinedsoup = BeautifulSoup(content_html, "html.parser")
            content_clean = joinedsoup.get_text()
                
            maildate = datetime(*(time.strptime(mail["date"], "%a, %d %b %Y %H:%M:%S +0000")[0:6]), tzinfo=pytz.UTC)
            
            parse_success = True
        except:
            print(f"Chapter {title} could not be parsed and was skipped")
            source, = ""
            content_html = ""
            content_clean = ""
            maildate = ""
            parse_success = False

        # Write new chapter to db
        query = ("INSERT INTO chapters VALUES (?, ?, ?, ?, ?, ?, ?)")
        params = (mailid, author, title, source, content_html, content_clean, str(maildate))
        self.cur.execute(query, params)
        self.db.commit()

        if self.conf["GENERAL"]["scan_only"] == "True" or not parse_success:
            return
        
        # Convert chapter to epub
        # Write chapter to file
        input_file = "convert_input.html"
        with open(input_file, "w", encoding="utf-8") as file:
            file.write(content_html)

        #Convert input_file to epub
        ebook_convert_path = self.conf["GENERAL"]["ebook_convert_path"]
        output_file = "convert_output.epub"
        #structure = "--chapter=\"//*[@class = 'chapter']\" --chapter-mark=pagebreak --level1-toc=\"//*[@class = 'chapter']\" --use-auto-toc"
        metadata = f"--authors='{author}' --author-sort='{author}' --title='{title}'"
        process = subprocess.run([ebook_convert_path, input_file, output_file,
                                  f"--chapter=//*[@class = 'chapter']",
                                  f"--chapter-mark=pagebreak",
                                  f"--level1-toc=//*[@class = 'chapter']",
                                  f"--use-auto-toc",
                                  f"--authors={author}",
                                  f"--author-sort={author}",
                                  f"--title={title}"],
                                  capture_output=False, text=True, check=True)

        # Send email
        self.send_email(title)
        
        
if __name__ == "__main__":
    cmd = Patreon2Kindle()
    cmd.run()
