import streamlit as st
from datetime import timedelta
import pytz
import pandas as pd
from calls.supa_select import supabase_blocks
import streamlit_ext as ste


def get_block_data():

    # Get the active blocks from supabase
    blocks = supabase_blocks(active=False)
    blocks['created_at'] = pd.to_datetime(blocks['created_at'])
    blocks['date'] = blocks['created_at'].dt.strftime('%Y-%m-%d')
    blocks = blocks.sort_values('created_at', ascending=False)
    blocks = blocks.drop_duplicates(subset=['date', 'coach'], keep='first')
    blocks = blocks.drop(columns=['created_at'])

    return blocks.copy()


def show_and_format_block_history(blocks, df, key):

    results = []

    for idx, row in blocks.iterrows():
        relevant_df = df[df['vehicle'] == row['coach']]
        utc = pytz.timezone('UTC')
        california_tz = pytz.timezone('US/Pacific')
        relevant_df['last_transmission'] = pd.to_datetime(relevant_df['last_transmission']).dt.tz_localize(utc).dt.tz_convert(california_tz).dt.tz_localize(None)

        block_start_time = pd.to_datetime(row['date'] + ' ' + row['block_startTime'])
        block_end_time = pd.to_datetime(row['date'] + ' ' + row['block_endTime'])

        relevant_starts = relevant_df[
            (relevant_df['last_transmission'] <= block_start_time) &
            (relevant_df['last_transmission'] >= block_start_time - timedelta(hours=7))
            ]
        relevant_starts = relevant_starts.sort_values('last_transmission', ascending=False)

        if relevant_starts.empty:
            # Omit writing SOC and odometer changes
            start_soc = None
            start_odometer = None
            start_time_change = None
            start_trans = None
        else:
            start_soc = relevant_starts.iloc[0]['soc']
            start_odometer = relevant_starts.iloc[0]['odometer']

            # calculate time change between last_transmission and block_start_time in hours
            start_time_change = block_start_time - relevant_starts.iloc[0]['last_transmission']
            start_time_change = start_time_change.total_seconds() / 3600
            start_time_change = int(start_time_change)
            start_trans = relevant_starts.iloc[0]['last_transmission']

        relevant_ends = relevant_df[
            (relevant_df['last_transmission'] >= block_end_time - timedelta(hours=1)) &
            (relevant_df['last_transmission'] <= block_end_time + timedelta(hours=5))
            ]
        relevant_ends = relevant_ends.sort_values('last_transmission', ascending=True)

        if relevant_ends.empty:
            # Omit writing SOC and odometer changes
            end_soc = None
            end_odometer = None
            end_time_change = None
            end_trans = None
        else:
            soc_idx = relevant_ends.iloc[0:2]['soc'].argmin()
            end_soc = relevant_ends.iloc[soc_idx]['soc']

            end_odometer = relevant_ends.iloc[0:2]['odometer'].max()
            end_trans = relevant_ends.iloc[soc_idx]['last_transmission']

            # calculate time change between block_end_time and first_transmission in hours
            end_time_change = relevant_ends.iloc[soc_idx]['last_transmission'] - block_end_time
            end_time_change = end_time_change.total_seconds() / 3600
            end_time_change = int(end_time_change)

        soc_change = None if start_soc is None or end_soc is None else abs(end_soc - start_soc)
        miles_travelled = None if start_odometer is None or end_odometer is None else end_odometer - start_odometer

        # Calculate kWh used
        if start_soc is not None and end_soc is not None and miles_travelled is not None:
            soc_change = abs(end_soc - start_soc)
            kwh_used = soc_change / 100 * 440  # Assuming the bus has a 440 kWh capacity
            kwh_per_mile = None
            if miles_travelled < 40:
                miles_travelled = None

            if miles_travelled is not None:
                kwh_per_mile = kwh_used / miles_travelled

                if kwh_per_mile < 1 or kwh_per_mile > 4:
                    kwh_per_mile = None
                    kwh_used = None
                    soc_change = None
                    end_soc = None
  
        if  miles_travelled is None:
            kwh_per_mile = None
            kwh_used = None
            soc_change = None
            end_soc = None

        result = {
            'Vehicle': row['coach'],
            'Date': row['date'],
            'Start SOC (%)': start_soc,
            'End SOC (%)': end_soc,
            'SOC Change (%)': soc_change,
            'Start Odometer': start_odometer,
            'End Odometer': end_odometer,
            'Start Trans': start_trans,
            'End Trans': end_trans,
            "Miles Travelled": miles_travelled,
            "kWh Used": kwh_used,
            "kWh per Mile": kwh_per_mile,
            'Start Time Change (hrs)': start_time_change,
            'End Time Change (hrs)': end_time_change,
        }
        results.append(result)

    result_df = pd.DataFrame(results)
    # st.dataframe(result_df)

    # merge blocks and result_df
    block_col_config = {
        "coach": st.column_config.TextColumn("Coach"),
        "id": st.column_config.TextColumn("Route"),
        "block_id": st.column_config.TextColumn("Block"),
        "block_startTime": st.column_config.TimeColumn("Start Time", format="hh:mmA"),
        "block_endTime": st.column_config.TimeColumn("End Time", format="hh:mmA"),
        "predictedArrival": st.column_config.TimeColumn("Predicted Arrival Time",
                                                        format="hh:mmA"),
        "date": st.column_config.DateColumn("Date", format="MM/DD/YY")
    }
    block_col_order = ["date", "coach", "id", "block_id",
                    "block_startTime",
                    "block_endTime", "predictedArrival",
                    "Start SOC (%)", "End SOC (%)", "SOC Change (%)",
                    "Miles Travelled", "kWh per Mile",
                    ]
    # st.write(blocks)
    # st.write(result_df)
    if len(result_df) > 0 and len(blocks) > 0:
        blocks = blocks.merge(result_df, left_on=['coach', 'date'], right_on=['Vehicle', 'Date'], how='left')
        blocks = blocks.drop(columns=['Vehicle'])
        blocks = blocks.sort_values(by=['date', 'block_startTime'], ascending=False)
        show_details = st.checkbox("Toggle More Details", key=key)
        exclude_na = st.checkbox("Exclude Rows with Unmatched Start or End SOC", key = key + "nan" )
        if show_details:
            block_col_order = ["date", "coach", "id", "block_id",
                            "block_startTime",
                            "Start Trans", "Start Time Change (hrs)",
                                "block_endTime", "predictedArrival",
                            "End Trans", "End Time Change (hrs)",
                            "Start SOC (%)", "End SOC (%)", "SOC Change (%)",
                            "Start Odometer", "End Odometer", "Miles Travelled", "kWh Used", "kWh per Mile",
                            ]
        if exclude_na: 
            blocks = blocks.dropna(how='any')

        st.dataframe(blocks, hide_index=True,
                    column_order=block_col_order,
                    column_config=block_col_config,
                    use_container_width=True,
                    )
        
        if key == "all":
            ste.download_button("Download Data as CSV", blocks, "block_history.csv")