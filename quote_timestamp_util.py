from datetime import datetime, timedelta

def format_date_for_quotes(date: datetime) -> str:
    now = datetime.now()
    
    # Check if the date is today
    if date.date() == now.date():
        return f"Today at {date.strftime('%I:%M %p')}"
    
    # Check if the date is within the last 7 days
    elif date.date() > (now - timedelta(days=7)).date():
        return f"{date.strftime('%A')} at {date.strftime('%I:%M %p')}"
    
    # Default format for older dates
    else:
        return date.strftime('%m/%d/%Y')