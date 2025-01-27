import pandas as pd
from supabase import create_client, Client
import os
from datetime import datetime, timedelta
import pytz
import streamlit as st

@st.cache_resource
def setup_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
    return supabase

@st.cache_data(show_spinner=False, ttl=timedelta(minutes=10))
def supabase_blocks(active=True):
    supabase = setup_client()
    response = supabase.table('block_history').select("*").order("created_at", desc=True).execute()
    data = response.data
    df = pd.DataFrame(data).drop(columns='id')

    if len(df) > 0:
        df = df.rename(columns={"start_time": "block_startTime", "end_time": "block_endTime",
                                "predicted_arrival": "predictedArrival", "route_id": "id"})
        df['coach'] = df['coach'].astype(str)
        df = df.sort_values('created_at', ascending=False)
        if active:
            df = df.drop_duplicates(subset=['coach'], keep='first')
        return df.copy()
    else:
        return None

@st.cache_data(show_spinner=False, ttl=timedelta(minutes=5))
def supabase_soc():
    supabase = setup_client()
    yesterday = datetime.today() - pd.Timedelta(days=1)
    response = supabase.table('soc').select("*").gt("created_at", yesterday).execute()
    data = response.data
    df = pd.DataFrame(data)
    # st.write(df)
    df['vehicle'] = df['vehicle'].astype(str)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df.sort_values(by='created_at', ascending=False, inplace=True)

    # Drop duplicate entries for each vehicle, keeping only the first (most recent)
    df.drop_duplicates(subset='vehicle', keep='first', inplace=True)
    df = df[['soc', 'vehicle', 'odometer', 'status', 'last_transmission', 'created_at']]
    # Format the odometer column with thousands separator
    df['odometer'] = df['odometer'].apply(lambda x: "{:,}".format(x))

    return df.copy()

@st.cache_data(show_spinner=False, ttl=timedelta(minutes=60))
def supabase_active_location():
    supabase = setup_client()
    response = supabase.table('location').select("*").order("created_at", desc=True).execute()
    data = response.data
    df = pd.DataFrame(data)
    if len(df) > 0:
        df['coach'] = df['coach'].astype(str)
        df = df.sort_values('created_at', ascending=False)
        df = df.drop_duplicates(subset=['coach'], keep='first')
        df = df.drop(columns=['id'])
        return df.copy()

    else:
        return None

@st.cache_data(show_spinner=False, ttl=timedelta(minutes=60))
def supabase_soc_history(vehicle=None):
    supabase = setup_client()
    if vehicle is None:
        response = supabase.table('soc').select("*").order("created_at", desc=True).execute()
    elif vehicle is not None:
        response = supabase.table('soc').select("*").eq('vehicle', vehicle).order("created_at", desc=True).execute()

    data = response.data
    df = pd.DataFrame(data)
    df['vehicle'] = df['vehicle'].astype(str)
    df['created_at'] = pd.to_datetime(df['created_at'])
    df.sort_values(by='created_at', ascending=False, inplace=True)

    # Convert last_transmission column to California timezone
    california_tz = pytz.timezone('US/Pacific')
    df['created_at'] = pd.to_datetime(df['created_at']).dt.tz_convert(california_tz)
    return df.copy()
