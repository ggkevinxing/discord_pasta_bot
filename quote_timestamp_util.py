from datetime import datetime, timedelta
import pytz

def convert_utc_to_timezone(utc_dt: datetime, timezone: str) -> datetime:
    """
    Convert a UTC datetime object to a specific timezone.

    :param utc_dt: A datetime object in UTC.
    :param timezone: A string representing the target timezone (e.g., "America/New_York").
    :return: A datetime object in the specified timezone.
    """
    target_tz = pytz.timezone(timezone)
    return utc_dt.replace(tzinfo=pytz.utc).astimezone(target_tz)


def format_date_for_quotes(d: datetime, timezone: str) -> str:
    """
    Formats the date to be displayed in a quote embed.
    """
    now = datetime.now()

    localized_date = convert_utc_to_timezone(d, timezone)

    # Check if the date is today
    if localized_date.date() == now.date():
        return f"Today at {localized_date.strftime('%I:%M %p')}"
    
    # Check if the date is within the last 7 days
    elif localized_date.date() > (now - timedelta(days=7)).date():
        return f"{localized_date.strftime('%A')} at {localized_date.strftime('%I:%M %p')}"
    
    # Default format for older dates
    else:
        return localized_date.strftime('%m/%d/%Y')