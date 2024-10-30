from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import pickle
import logging
from datetime import datetime, timedelta

class CalendarHandler:
    def __init__(self):
        self.logger = logging.getLogger('CalendarHandler')
        self.SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
                      'https://www.googleapis.com/auth/calendar.events']
        self.creds = None
        self._authenticate()

    def _authenticate(self):
        """Handle Google Calendar authentication"""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', self.SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)

        self.service = build('calendar', 'v3', credentials=self.creds)

    def add_event(self, summary, start_time, end_time=None, description=None):
        """Add an event to Google Calendar"""
        try:
            if not end_time:
                end_time = (datetime.fromisoformat(start_time) + timedelta(hours=1)).isoformat()

            event = {
                'summary': summary,
                'description': description,
                'start': {'dateTime': start_time, 'timeZone': 'UTC'},
                'end': {'dateTime': end_time, 'timeZone': 'UTC'}
            }

            event = self.service.events().insert(calendarId='primary', body=event).execute()
            return {
                'success': True,
                'event_id': event['id'],
                'link': event['htmlLink']
            }
        except Exception as e:
            self.logger.error(f"Error adding calendar event: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def list_events(self, max_results=10):
        """List upcoming events from Google Calendar"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return {'success': True, 'events': events}
        except Exception as e:
            self.logger.error(f"Error listing calendar events: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)} 