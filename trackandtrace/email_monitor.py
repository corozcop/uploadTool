"""
Email Monitoring Module
======================

Handles IMAP email monitoring, searching, and attachment processing.
"""

import email
import imaplib
import os
import re
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import hashlib

from imapclient import IMAPClient
from imapclient.exceptions import IMAPClientError

from .config import EmailConfig
from .logging_config import get_logger

logger = get_logger(__name__)


class EmailAttachment:
    """Represents an email attachment"""
    
    def __init__(self, filename: str, content: bytes, content_type: str):
        self.filename = filename
        self.content = content
        self.content_type = content_type
        self.size = len(content)
        self.checksum = hashlib.md5(content).hexdigest()
    
    def save_to_file(self, directory: str) -> str:
        """Save attachment to file and return the file path"""
        Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename to avoid conflicts
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(self.filename)
        unique_filename = f"{timestamp}_{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        file_path = Path(directory) / unique_filename
        
        with open(file_path, 'wb') as f:
            f.write(self.content)
        
        logger.info(f"Saved attachment to {file_path}", 
                   filename=self.filename, 
                   size=self.size, 
                   checksum=self.checksum)
        
        return str(file_path)


class EmailMessage:
    """Represents an email message with metadata"""
    
    def __init__(self, uid: int, subject: str, sender: str, date: datetime, 
                 attachments: List[EmailAttachment]):
        self.uid = uid
        self.subject = subject
        self.sender = sender
        self.date = date
        self.attachments = attachments
        self.processed = False
    
    def has_excel_attachments(self) -> bool:
        """Check if email has Excel attachments"""
        excel_extensions = ['.xlsx', '.xls']
        return any(
            Path(att.filename).suffix.lower() in excel_extensions 
            for att in self.attachments
        )
    
    def get_excel_attachments(self) -> List[EmailAttachment]:
        """Get only Excel attachments"""
        excel_extensions = ['.xlsx', '.xls']
        return [
            att for att in self.attachments 
            if Path(att.filename).suffix.lower() in excel_extensions
        ]


class EmailMonitor:
    """Email monitoring and processing class"""
    
    def __init__(self, config: EmailConfig):
        self.config = config
        self.client: Optional[IMAPClient] = None
        self.processed_emails: set = set()
        self._load_processed_emails()
    
    def _load_processed_emails(self):
        """Load previously processed email UIDs"""
        # This could be extended to load from a persistent store
        # For now, we'll rely on email read status
        pass
    
    def connect(self) -> bool:
        """Connect to IMAP server"""
        try:
            self.client = IMAPClient(self.config.host, port=self.config.port, 
                                   use_uid=True, ssl=self.config.use_ssl)
            self.client.login(self.config.username, self.config.password)
            
            # Select the inbox
            self.client.select_folder(self.config.folder)
            
            logger.info(f"Connected to IMAP server {self.config.host}:{self.config.port}")
            return True
            
        except IMAPClientError as e:
            logger.error(f"IMAP connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during IMAP connection: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IMAP server"""
        if self.client:
            try:
                self.client.close_folder()
                self.client.logout()
                logger.info("Disconnected from IMAP server")
            except Exception as e:
                logger.warning(f"Error during IMAP disconnection: {e}")
            finally:
                self.client = None
    
    def search_matching_emails(self) -> List[EmailMessage]:
        """Search for unread emails matching the subject filter"""
        if not self.client:
            logger.error("IMAP client not connected")
            return []
        
        try:
            # Search for unread emails with matching subject
            search_criteria = [
                'UNSEEN',  # Unread emails
                'SUBJECT', self.config.subject_filter
            ]
            
            message_uids = self.client.search(search_criteria)
            
            if not message_uids:
                logger.info("No matching unread emails found")
                return []
            
            logger.info(f"Found {len(message_uids)} matching emails")
            
            # Fetch email messages
            emails = []
            for uid in message_uids:
                email_message = self._fetch_email_message(uid)
                if email_message:
                    emails.append(email_message)
            
            return emails
            
        except IMAPClientError as e:
            logger.error(f"Error searching emails: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching emails: {e}")
            return []
    
    def _fetch_email_message(self, uid: int) -> Optional[EmailMessage]:
        """Fetch and parse an email message"""
        try:
            # Fetch email data
            response = self.client.fetch([uid], ['ENVELOPE', 'RFC822'])
            
            if uid not in response:
                logger.warning(f"Email UID {uid} not found in response")
                return None
            
            envelope = response[uid][b'ENVELOPE']
            raw_message = response[uid][b'RFC822']
            
            # Parse email
            email_message = email.message_from_bytes(raw_message)
            
            # Extract metadata
            subject = envelope.subject.decode() if envelope.subject else ""
            sender = envelope.from_[0].mailbox.decode() + "@" + envelope.from_[0].host.decode()
            date = envelope.date
            
            # Extract attachments
            attachments = self._extract_attachments(email_message)
            
            return EmailMessage(uid, subject, sender, date, attachments)
            
        except Exception as e:
            logger.error(f"Error fetching email UID {uid}: {e}")
            return None
    
    def _extract_attachments(self, email_message) -> List[EmailAttachment]:
        """Extract attachments from email message"""
        attachments = []
        
        try:
            for part in email_message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        content = part.get_payload(decode=True)
                        content_type = part.get_content_type()
                        
                        attachment = EmailAttachment(filename, content, content_type)
                        attachments.append(attachment)
                        
                        logger.info(f"Found attachment: {filename} ({attachment.size} bytes)")
        
        except Exception as e:
            logger.error(f"Error extracting attachments: {e}")
        
        return attachments
    
    def mark_email_as_read(self, uid: int) -> bool:
        """Mark email as read"""
        if not self.client:
            logger.error("IMAP client not connected")
            return False
        
        try:
            self.client.add_flags([uid], ['\\Seen'])
            logger.info(f"Marked email UID {uid} as read")
            return True
            
        except IMAPClientError as e:
            logger.error(f"Error marking email UID {uid} as read: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error marking email as read: {e}")
            return False
    
    def save_attachments(self, email_message: EmailMessage, 
                        directory: str) -> List[str]:
        """Save email attachments to directory"""
        saved_files = []
        
        for attachment in email_message.get_excel_attachments():
            try:
                file_path = attachment.save_to_file(directory)
                saved_files.append(file_path)
                
                logger.info(f"Saved attachment from email UID {email_message.uid}",
                           filename=attachment.filename,
                           path=file_path,
                           size=attachment.size)
                
            except Exception as e:
                logger.error(f"Error saving attachment {attachment.filename}: {e}")
        
        return saved_files
    
    def process_emails(self, pending_directory: str) -> List[Dict[str, Any]]:
        """Process all matching emails and return job information"""
        if not self.connect():
            logger.error("Failed to connect to email server")
            return []
        
        try:
            matching_emails = self.search_matching_emails()
            
            if not matching_emails:
                logger.info("No matching emails to process")
                return []
            
            # Filter emails with Excel attachments
            emails_with_excel = [
                email for email in matching_emails 
                if email.has_excel_attachments()
            ]
            
            if not emails_with_excel:
                logger.info("No emails with Excel attachments found")
                return []
            
            logger.info(f"Processing {len(emails_with_excel)} emails with Excel attachments")
            
            # Process each email
            jobs = []
            for email_message in emails_with_excel:
                try:
                    # Save attachments
                    saved_files = self.save_attachments(email_message, pending_directory)
                    
                    if saved_files:
                        # Create job information
                        job = {
                            'id': f"email_{email_message.uid}_{uuid.uuid4().hex[:8]}",
                            'email_uid': email_message.uid,
                            'subject': email_message.subject,
                            'sender': email_message.sender,
                            'date': email_message.date,
                            'files': saved_files,
                            'status': 'pending'
                        }
                        jobs.append(job)
                        
                        logger.info(f"Created job for email UID {email_message.uid}",
                                   job_id=job['id'],
                                   files_count=len(saved_files))
                    
                except Exception as e:
                    logger.error(f"Error processing email UID {email_message.uid}: {e}")
            
            return jobs
            
        finally:
            self.disconnect()
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect() 