import streamlit as st
import requests
import pandas as pd
import io
# from folium import Map, Marker
# from streamlit_folium import st_folium


# API endpoint
API_URL = "https://services3.arcgis.com/n6uYoouQZW75n5WI/arcgis/rest/services/Wisconsin_Statewide_Parcels/FeatureServer/0/query"

# Available fields from the schema (simplified list for this example)
AVAILABLE_FIELDS = ['OBJECTID', 'PARCELID', 'TAXPARCELID', 'PARCELDATE', 'TAXROLLYEAR', 'OWNERNME1'
                    , 'OWNERNME2', 'PSTLADRESS', 'SITEADRESS', 'ADDNUMPREFIX', 'ADDNUM', 'ADDNUMSUFFIX'
                    , 'PREFIX', 'STREETNAME', 'STREETTYPE', 'SUFFIX', 'LANDMARKNAME', 'UNITTYPE', 'UNITID'
                    , 'PLACENAME', 'ZIPCODE', 'ZIP4', 'STATE', 'SCHOOLDIST', 'SCHOOLDISTNO', 'CNTASSDVALUE'
                    , 'LNDVALUE', 'IMPVALUE', 'MFLVALUE', 'ESTFMKVALUE', 'NETPRPTA', 'GRSPRPTA', 'PROPCLASS'
                    , 'AUXCLASS', 'ASSDACRES', 'DEEDACRES', 'GISACRES', 'CONAME', 'LOADDATE', 'LONGITUDE', 'LATITUDE']

def query_parcels(where_clause, out_fields):
    params = {
        "where": where_clause,
        "outFields": ",".join(out_fields),
        "f": "json"
    }
    response = requests.get(API_URL, params=params, verify=False)
    if response.status_code == 200:
        data = response.json()
        if "features" in data:
            # Extract attributes from features
            return [feature["attributes"] for feature in data["features"]]
        else:
            st.error("No features found in the response.")
            return []
    else:
        st.error(f"API request failed with status code: {response.status_code}")
        return []

def generate_google_maps_link(lat, lon):
    if pd.notna(lat) and pd.notna(lon):
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
    return ""

def create_map(df):
    # Filter out rows with missing lat/lon
    df_map = df.dropna(subset=["LATITUDE", "LONGITUDE"])
    if df_map.empty:
        st.warning("No valid latitude/longitude data to display on the map.")
        return None
    
    # Center the map on the mean coordinates
    center_lat = df_map["LATITUDE"].mean()
    center_lon = df_map["LONGITUDE"].mean()
    
    # Create Folium map
    m = Map(location=[center_lat, center_lon], zoom_start=10)
    
    # Add markers
    for _, row in df_map.iterrows():
        popup_text = f"""
        <b>Owner:</b> {row["OWNERNME1"]}<br>
        <b>Parcel ID:</b> {row["PARCELID"]}<br>
        <b>Address:</b> {row["SITEADRESS"]}<br>
        <b>GIS Acres:</b> {row["GISACRES"]}
        """
        Marker(
            location=[row["LATITUDE"], row["LONGITUDE"]],
            popup=popup_text,
            tooltip=row["OWNERNME1"]
        ).add_to(m)
    
    return m

def main():
    st.title("Wisconsin Parcels Search")

    # Query Parameters
    st.subheader("Query Parameters")
    
    # Field-based search
    search_field = st.selectbox("Field to Search", ["OWNERNME1", "OWNERNME2", "PARCELID", "SITEADRESS", "CONAME", "PARCELID"])
    search_value = st.text_input(f"Enter value for {search_field}", "")
    query_type = st.radio("Query Type", ["Partial Match", "Exact Match"])
    
    # Acreage filter
    st.subheader("Optional Acreage Filter")
    min_acres = st.number_input("Minimum GIS Acres (leave as 0 for no filter)", min_value=0.0, step=0.1, value=0.0)

    # Construct WHERE clause
    where_conditions = []
    if search_value:
        if query_type == "Exact Match":
            where_conditions.append(f"{search_field} = '{search_value}'")
        else:
            where_conditions.append(f"{search_field} LIKE '%{search_value}%'")
    if min_acres > 0:
        where_conditions.append(f"GISACRES > {min_acres}")
    
    # Combine conditions or use default
    if where_conditions:
        where_clause = " AND ".join(where_conditions)
    else:
        where_clause = "1=1"  # Default to return all (limited by API max record count)

    # Display the exact query
    st.write(f"**Query WHERE Clause:** `{where_clause}`")

    # Fields to Return
    st.subheader("Fields to Return")
    selected_fields = st.multiselect("Select Fields", AVAILABLE_FIELDS, default=['PARCELID', 'OWNERNME1', 'OWNERNME2', 'PSTLADRESS', 'SITEADRESS', 'ZIPCODE', 'SCHOOLDIST', 'CNTASSDVALUE', 'LNDVALUE', 'IMPVALUE', 'MFLVALUE', 'ESTFMKVALUE', 'NETPRPTA', 'GRSPRPTA', 'PROPCLASS', 'AUXCLASS', 'ASSDACRES', 'DEEDACRES', 'GISACRES', 'CONAME', 'LOADDATE', 'LONGITUDE', 'LATITUDE'])#["OWNERNME1", "PARCELID", "SITEADRESS", "GISACRES"])

    # Button to Execute Query
    if st.button("Search"):
        if not selected_fields:
            st.warning("Please select at least one field to return.")
        else:
            with st.spinner("Querying the API..."):
                # Ensure LATITUDE and LONGITUDE are included for Google Maps links
                query_fields = selected_fields
                if "LATITUDE" not in selected_fields or "LONGITUDE" not in selected_fields:
                    query_fields = list(set(selected_fields + ["LATITUDE", "LONGITUDE"]))
                
                results = query_parcels(where_clause, query_fields)
                if results:
                    # Convert to DataFrame
                    df = pd.DataFrame(results)
                    
                    # Generate Google Maps links
                    df["Google Maps Link"] = df.apply(lambda row: generate_google_maps_link(row["LATITUDE"], row["LONGITUDE"]), axis=1)
                    
                    # # Create a clickable hyperlink column for Streamlit
                    # df["Google Maps"] = df["Google Maps Link"].apply(lambda x: f'<a href="{x}" target="_blank">View on Map</a>' if x else "")
                    
                    # # Filter to only selected fields plus the link column (exclude raw link in display)
                    # display_fields = selected_fields + ["Google Maps"]
                    # df_display = df[display_fields]
                    
                    st.write("### Results")
                    # Render the table with clickable links
                    st.dataframe(df)

                    # # Display Map
                    # st.write("### Results Map")
                    # folium_map = create_map(df)
                    # if folium_map:
                    #     st_folium(folium_map, width=700, height=500)

                    # Prepare Excel file (use the raw URL, not the HTML)
                    df_excel = df[selected_fields + ["Google Maps Link"]]
                    
                    # Download as Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df_excel.to_excel(writer, index=False)
                    excel_data = output.getvalue()
                    st.download_button(
                        label="Download as Excel",
                        data=excel_data,
                        file_name="parcel_results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.write("No results found.")

if __name__ == "__main__":
    main()
