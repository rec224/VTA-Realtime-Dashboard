# from streamlit_supabase_auth import login_form, logout_button

import json
import os

import pandas as pd
import streamlit as st
import yaml
from dotenv import load_dotenv
from supabase import create_client, Client


def show_soc():
    # get config settings from YAML
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Convert the data to a JSON string
    config_json = json.dumps(config)

    # Mileage Data
    mileages = {'7774': 105.9, '7773': 167.3, '7772': 145.9, '7771': 107.0, '7072': 112.1}

    # Load environment variables
    load_dotenv()

    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)

    response = supabase.table('soc').select("*").execute()

    # Extract the data from the APIResponse object
    data = response.data

    # Convert the data to a DataFrame
    df = pd.DataFrame(data)

    # make vehicle column text
    df['vehicle'] = df['vehicle'].astype('object')

    # Convert the 'created_at' column to datetime type
    df['created_at'] = pd.to_datetime(df['created_at'])

    # Sort the DataFrame by 'created_at' column in descending order
    df.sort_values(by='created_at', ascending=False, inplace=True)

    # Drop duplicate entries for each vehicle, keeping only the first (most recent)
    df.drop_duplicates(subset='vehicle', keep='first', inplace=True)

    df = df[['soc', 'vehicle', 'odometer', 'status', 'last_transmission']]

    # dataframe string formatting
    column_config = {
        "soc": st.column_config.ProgressColumn(
            "State of Charge",
            help="Battery Percentage of Bus",
            format="%d%%",
            width='medium',
            min_value=0,
            max_value=100,
        ),
        "vehicle": st.column_config.TextColumn(
            "Coach",
            help="Bus Identification Number",
            # format="%d",
        ),
        "odometer": st.column_config.NumberColumn(
            "Odometer (mi)",
            help="Bus Odometer Reading in miles",
            # format="%d",
        ),
        "last_transmission": st.column_config.DatetimeColumn(
            "Last Transmission Time",
            help="Time of Last Transmission",
            format="HH:mm MM/DD/YYYY",
        )
    }

    col_order = ['vehicle', 'soc',  'odometer', 'last_transmission']

    # Separate the DataFrame into active and inactive buses
    active_buses = df[df['status'] == True]
    inactive_buses = df[df['status'] == False]

    active_buses = active_buses.drop(columns=['status'])
    inactive_buses = inactive_buses.drop(columns=['status'])

    # Format the odometer column with thousands separator
    df['odometer'] = df['odometer'].apply(lambda x: "{:,}".format(x))

    # Format the last_transmission column
    df['last_transmission'] = pd.to_datetime(df['last_transmission'])
    # df['last_transmission'] = df['last_transmission'].dt.strftime("%H:%M %m/%d/%y")

    # Display the active buses DataFrame
    st.subheader("Active Buses")
    active_buses.sort_values('vehicle', inplace=True)
    st.dataframe(active_buses, hide_index=True, column_config=column_config, column_order=col_order)


    # Display the inactive buses DataFrame
    st.subheader("Inactive Buses")
    inactive_buses.sort_values('vehicle', inplace=True)
    st.dataframe(inactive_buses, hide_index=True, column_config=column_config, column_order=col_order)

    # df = pd.DataFrame(response['data'])
    # st.write(df)
    #
    # df = pd.read_pickle('df.pkl')
    # prob_data = pd.DataFrame(columns=['coach', 'block', 'Safe Prob.', 'safe_prob', 'Overall Prob.', 'prob'])
    # coaches = df.vehicle.value_counts()
    # ebec_input = pd.DataFrame(columns=['Date', 'Vehicle', 'start_per'])
    #
    # for coach in coaches.index:
    #     # grab most recent data
    #     coach_df = df[df.vehicle == coach]
    #     row = coach_df[coach_df.Date == coach_df.Date.max()].iloc[0, :]
    #     ebec_input = ebec_input.append({'Date': row['Date'], 'Vehicle': row['vehicle'], 'start_per': row['soc']},
    #                                    ignore_index=True)
    #
    # ebec_input['month'] = ebec_input['Date'].dt.month
    # output = ebec_input
    # output.start_per = (np.around(output.start_per.astype(float), 0)).astype(int)
    # output.Date = pd.to_datetime(output.Date)
    # output.Date = output.Date.dt.strftime("%m/%d %I:%M %p PST")
    # output = output.rename(columns={'start_per': "SOC (%)", "Date": "Last Online"})
    # output.to_csv("output.csv")
    #
    # # TODO: Add number of blocks covered w/ tolerance
    # # both safely and overall
    # # st.markdown("## State of Charge (SOC)")
    # st.markdown("### Active (last 3 hrs)")
    #
    # cols = st.columns(2)
    # with cols[0]:
    #     bar = alt.Chart(output).mark_bar(color='green').encode(
    #         x='SOC (%):Q',
    #         y=alt.Y('Vehicle:N', sort='ascending'),
    #     ).properties(height=alt.Step(40))
    #     st.altair_chart(bar, use_container_width=True)
    # output.index = output.Vehicle
    # with cols[1]:
    #     output['SOC (%)'] = output['SOC (%)'].astype(str) + '%'
    #     st.dataframe(output[['SOC (%)', "Last Online"]].sort_index(ascending=True), use_container_width=True)
    #
    # st.markdown("### Inactive (more than 3 hrs)")