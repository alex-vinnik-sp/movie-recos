#!/usr/bin/env python3

import os
from dotenv import load_dotenv
from snowflake.snowpark import Session
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.otel.semconv.trace import SpanAttributes
import json

def create_snowpark_session() -> Session:
    # Configure Snowflake connection with conditional authentication
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")
    
    snowflake_config = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
    }
    
    # Add authentication method based on environment
    if snowflake_password:
        snowflake_config["password"] = snowflake_password
    else:
        snowflake_config["authenticator"] = "externalbrowser"
    
    snowpark_session = Session.builder.configs(snowflake_config).create()
    return snowpark_session


def main():
    
    # Load environment variables from .env file
    load_dotenv(override=True)
    
    # Create Snowpark session
    snowpark_session = create_snowpark_session()
        
    connector = SnowflakeConnector(snowpark_session=snowpark_session)
    print("✓ SnowflakeConnector initialized")
        
    events = connector.get_events(
        app_name='movie_agent',
        app_version='v1'
    )
    
    print(f"\n✓ Retrieved {len(events)} events")
    
    print(f"type: {type(events['record_attributes'][0])}")
    print(events['record_attributes'][0])
    record_id = json.loads(events['record_attributes'][0]).get(SpanAttributes.RECORD_ID)
    print(f"record_id: {record_id}")
    record_id = events['record_attributes'][0].get(SpanAttributes.RECORD_ID)
    print(f"record_id: {record_id}")

if __name__ == "__main__":
    main()

