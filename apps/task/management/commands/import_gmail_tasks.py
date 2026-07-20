#python manage.py import_gmail_tasks

import imaplib
import email
import re
import quopri
from email.header import decode_header
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.task.models import Task

EMAIL = "tasks.afs@gmail.com"
PASSWORD = "xaoe mlml asjj bjmc"  # Replace with your App Password or use environment variable

from django.utils.text import Truncator

def summarize_task_text(full_text):
    # Simple rule-based summary: first sentence or 12 words
    first_sentence = full_text.split(".")[0].strip()
    if len(first_sentence.split()) >= 3:
        return Truncator(first_sentence).chars(80)
    return Truncator(full_text).words(12)

class Command(BaseCommand):
    help = "Fetch meeting notes from Gmail and create tasks"

    def handle(self, *args, **kwargs):
        self.stdout.write("Connecting to Gmail...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, 'SUBJECT "Daily Scrum Meeting"')      #'(FROM "gemini-notes@google.com")')
#        print('Status', status, ' messages ', messages)
        email_ids = messages[0].split()[-5:]  # Last 5 notes
#        print("Email IDs: ", email_ids)
        for eid in email_ids:
            _, msg_data = mail.fetch(eid, "(RFC822)")
#            print("Message Data: ", msg_data)
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    content = ""

                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                raw = part.get_payload(decode=True)
                                decoded = quopri.decodestring(raw).decode(errors="ignore")
                                content = decoded
                    else:
                        content = msg.get_payload(decode=True).decode(errors="ignore")
#                    print("Content: ", content)
                    tasks = self.extract_tasks_from_text(content)
                    for full_text in tasks:
                        title = summarize_task_text(full_text)
                        print("\n--- Task ---")
                        print("Title:", title)
                        print("Description:", full_text.strip())
                        print("---\n")
                        task_obj, created = Task.objects.get_or_create(
                            title=title[:255],
                            defaults={
                                "description": full_text.strip(),
                                "priority": "Medium",
                                "due_date": None,
                                "created_at": timezone.now()
                            }
                        )
                        if created:
                            self.stdout.write(f"Created task: {task_obj.title}")
                        else:
                            self.stdout.write(f"Skipped existing task: {task_obj.title}")

        mail.logout()
        self.stdout.write("Done importing tasks.")

    def extract_tasks_from_text(self, text):
        # 1. Find the "Suggested next steps" section
        section_match = re.search(r"Suggested next steps\s*(.*?)(?:\n[A-Z][a-zA-Z ]+?:|\Z)", text, re.DOTALL | re.IGNORECASE)
        if not section_match:
            return []

        task_block = section_match.group(1).strip()

        # 2. Reconstruct full tasks by combining wrapped lines
        lines = task_block.splitlines()
        tasks = []
        buffer = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if re.match(r"^[A-Z][a-z]+\s[A-Z][a-z]+ will\b", line):  # e.g., "Ken Gordon will"
                if buffer:
                    tasks.append(buffer.strip())
                buffer = line
            else:
                buffer += " " + line

        if buffer:
            tasks.append(buffer.strip())

        print("Parsed Tasks:", tasks)
        return tasks

