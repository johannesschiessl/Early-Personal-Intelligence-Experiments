import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict

class DailySummary:
    def __init__(self, assistant):
        self.logger = logging.getLogger('DailySummary')
        self.assistant = assistant

    def _format_events_for_prompt(self, events: List[Dict]) -> str:
        if not events:
            return "No events scheduled."
        
        formatted_events = []
        for event in events:
            start = datetime.fromisoformat(event['start'].get('dateTime', event['start'].get('date')))
            formatted_start = start.strftime("%H:%M")
            formatted_events.append(f"- {formatted_start}: {event['summary']}")
        
        return "\n".join(formatted_events)

    def generate_summary(self, chat_id: int, is_morning: bool = True) -> str:
        try:
            # Get the date range for events
            now = datetime.now(timezone.utc)
            if is_morning:
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = now.replace(hour=23, minute=59, second=59, microsecond=999999)
                time_context = "today"
            else:
                tomorrow = now + timedelta(days=1)
                start_time = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
                time_context = "tomorrow"

            # Get calendar events
            events_response = self.assistant.calendar_handler.list_events(max_results=10)
            if not events_response['success']:
                self.logger.error(f"Failed to fetch calendar events: {events_response['error']}")
                return "I apologize, but I couldn't fetch your calendar events at the moment."

            # Filter events for the relevant time period
            filtered_events = []
            for event in events_response['events']:
                event_datetime_str = event['start'].get('dateTime', event['start'].get('date'))
                event_datetime = datetime.fromisoformat(event_datetime_str)
                
                # If the datetime is naive, assume UTC
                if event_datetime.tzinfo is None:
                    event_datetime = event_datetime.replace(tzinfo=timezone.utc)
                
                if start_time <= event_datetime <= end_time:
                    filtered_events.append(event)

            # Create the prompt for the LLM
            prompt = f"""
            You are providing a daily summary. The time is {'morning' if is_morning else 'evening'}.
            Please start with an appropriate greeting and end with a suitable motivational message or quote.

            Here are the scheduled events for {time_context}:
            {self._format_events_for_prompt(filtered_events)}

            Please provide a friendly summary of what to expect {time_context}, incorporating the scheduled events 
            and adding some encouraging words. Keep it concise but engaging.
            """

            # Get the response from the assistant
            response = self.assistant.chat(prompt)
            
            # Send the message to the user
            return response

        except Exception as e:
            self.logger.error(f"Error generating daily summary: {str(e)}", exc_info=True)
            return "I apologize, but I encountered an error while generating your daily summary." 