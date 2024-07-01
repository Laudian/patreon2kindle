# patreon2kindle
This is for people that have subscribed to webnovels via Patreon but want to read the latest chapters on their Kindle. This scans your emails for new chapters, converts them to epub and sends them to your Kindle via email.

# Installation
1. Install Calibre, as I use their ebook_convert tool: https://calibre-ebook.com
2. Install Python. Tested on 3.12: https://www.python.org
3. Install the dependencies via PIP: ```pip install bs4 pytz```
I might go into more detail at a later time, but for now find some tutorial on the internet if you don't know how to use PIP.
4. Clone or download the repo
5. Fill out the settings in patreon2kindle.conf
6. Don't forget to allowlist your email with Amazon.

While 'scan_only' is 'True', the program will scan your emails for new chapters but only add them to the database. Otherwise, you might get hundreds of chapters send to your Kindle on the first run.

# Limitations
For now, emails are only sent via STARTTLS on port 587. If anyone actually ends up using this, I can add configurations options for this.

The program can only parse Patreon's current email layout. I plan on adding past (and future) layouts later.

If you want to send some chapters right away, you need to delete them from the database after the initial scan. You need some software to edit SQLITE files for this.

No support for Multipart emails for now. That means emails with attachments don't work. Probably lots of other email related problems.