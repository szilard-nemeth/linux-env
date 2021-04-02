import logging
import os

from pythoncommons.email import EmailConfig, EmailAccount, EmailService
from pythoncommons.file_utils import FileUtils

from yarndevfunc.utils import FileUtils2

LOG = logging.getLogger(__name__)


class Config:
    def __init__(self, args, attachment_file: str):
        FileUtils.ensure_file_exists_and_readable(attachment_file)
        self.attachment_file = attachment_file
        self.email_account = EmailAccount(args.account_user, args.account_password)
        self.email_conf = EmailConfig(args.smtp_server, args.smtp_port, self.email_account)
        self.sender = args.sender
        self.recipients = args.recipients
        self.subject = args.subject


class SendLatestCommandDataInEmail:
    def __init__(self, args, attachment_file: str):
        self.config = Config(args, attachment_file)

    def run(self):
        LOG.info(
            "Starting sending latest command data in email. Details: \n"
            f"SMTP server: {self.config.email_conf.smtp_server}\n"
            f"SMTP port: {self.config.email_conf.smtp_port}\n"
            f"Account user: {self.config.email_account.user}\n"
            f"Recipients: {self.config.recipients}\n"
            f"Sender: {self.config.sender}\n"
            f"Subject: {self.config.subject}\n"
            f"Attachment file: {self.config.attachment_file}\n"
        )

        zip_extract_dest = FileUtils.join_path(os.sep, "tmp", "extracted_zip")
        FileUtils2.extract_zip_file(self.config.attachment_file, zip_extract_dest)

        # TODO use constant FILE_SUMMARY
        summary_file = FileUtils.join_path(os.sep, zip_extract_dest, "summary.txt")
        FileUtils.ensure_file_exists(summary_file)

        body = FileUtils.read_file(summary_file)
        email_service = EmailService(self.config.email_conf)
        email_service.send_mail(
            self.config.sender, self.config.subject, body, self.config.recipients, self.config.attachment_file
        )
        LOG.info("Finished sending email to recipients")
