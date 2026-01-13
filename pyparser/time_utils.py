#----------------------------------------------------
#                   DATETIME UTILS
# -----------------------------------------------------

from typing import Union
from dateutil import parser
from datetime import datetime
import pandas as pd
import re
import pytz
import logging

JAN_1_2000_UNIX = 946702800
JAN_1_2050_UNIX = 2524608000




def extract_dates(df: pd.DataFrame, 
                  timestamp_regex: list, 
                  multiple_dates: str = 'newest',
                  fuzzy: bool = True,
                  default_tz: str = 'UTC',
                ) -> pd.DataFrame:
    
    # Compile regex patterns once
    compiled_patterns = [re.compile(regex, re.IGNORECASE) for regex in timestamp_regex]

    # Filter rows that match any timestamp regex
    match_any_pattern = lambda x: any(pattern.search(x) for pattern in compiled_patterns)
    df['is_time_field'] = df['attribute'].apply(match_any_pattern)

    parse_valid_date = lambda row: parse_date(row['value'], fuzzy, default_tz) if row['is_time_field'] else pd.NA
    df['parsed_ts'] = df.apply(parse_valid_date, axis=1)

    def get_group_ts(group):
        valid_timestamps = group.dropna()
        if not valid_timestamps.empty:
            if multiple_dates == 'newest':
                return valid_timestamps.max()
            elif multiple_dates == 'oldest':
                return valid_timestamps.min()
        return pd.NA
    
    group_timestamps = df.groupby('entity_id')['parsed_ts'].transform(get_group_ts)
    #df['timestamp'] = group_timestamps
    df['timestamp_UTC'] = group_timestamps.apply(convert_to_utc)


    return df[['path', 'entity_id', 'timestamp_UTC', 'attribute', 'value']]


# - - - - - - - - - - - - - - - - - -

def convert_to_utc(timestamp, tzinfo=None):
        if pd.isna(timestamp):
            return pd.NA
        if timestamp.tzinfo is not None and timestamp.tzinfo != pytz.UTC:
            timestamp = timestamp.astimezone(pytz.UTC)
        return timestamp.replace(tzinfo=tzinfo)

def parse_date(date_str: str, 
               fuzzy=True, 
               user_tz='UTC',
               default_origin_tz='UTC', 
               fail_action='ignore') -> datetime:
    date_str = str(date_str).strip()
    try:
        # Check if the date_str is a Unix timestamp
        if date_str.isdigit(): 
            if int(date_str) in range(JAN_1_2000_UNIX, JAN_1_2050_UNIX):  # Unix timestamps for 1-1-2000 and 1-1-2050
                #logging.debug(f"date_str is a digit: {date_str}")
                return datetime.fromtimestamp(int(date_str), tz=pytz.UTC)
            raise ValueError("Not a valid Unix timestamp")
        else:
            default_datetime = datetime.now().replace(day=1, month=1, year=2000, hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.timezone(default_timezone))
            date = parser.parse(date_str, fuzzy=fuzzy, default=default_datetime)
            #logging.debug(f"date: {date}")
            if date.tzinfo is None:
                date = date.replace(tzinfo=pytz.timezone(default_origin_tz))
        return date.astimezone(pytz.timezone(user_tz))
    except Exception as e:  
        if fail_action == 'raise':
            raise ValueError("Invalid date format")
        elif fail_action == 'ignore':
            logging.debug(f"Ignore -- Failed to parse date: {date_str} -- {e}")
            # logging.debug(f"Error: {e}")
            #traceback.print_exc()
            return None
        else:
            raise ValueError("Invalid fail_action")


# - - - - - - - - - - - - - - - - - -


def is_valid_date(date_str: str, fuzzy=True) -> bool:
    return parse_date(date_str, fuzzy) is not None

# - - - - - - - - - - - - - - - - - -

def get_tzinfo(date: Union[str, datetime], fuzzy=True) -> str:
    if not isinstance(date, datetime):
        date = parse_date(date, fuzzy, fail_action='raise')
    return date.tzinfo


# --------

def unix_ms(dt: datetime) -> int:
    """Convert datetime to unix timestamp in milliseconds."""
    if dt is None:
        return 0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=pytz.UTC)
    return int(dt.timestamp() * 1000)