import streamlit as st
import json
import altair as alt
import pandas as pd

def parse_mzqc(json_data: dict):
    """
    Parse the mzQC JSON structure (according to the official schema).
    Returns a dictionary that is easy to use in our Streamlit app.
    """
    mzqc_root = json_data.get("mzQC", {})
    
    # Basic info
    version = mzqc_root.get("version", "N/A")
    creation_date = mzqc_root.get("creationDate", "N/A")
    description = mzqc_root.get("description", "N/A")
    contact_name = mzqc_root.get("contactName", "N/A")
    contact_address = mzqc_root.get("contactAddress", "N/A")
    
    # Qualities
    run_qualities = mzqc_root.get("runQualities", [])
    set_qualities = mzqc_root.get("setQualities", [])
    
    # Controlled vocabularies
    cv_list = mzqc_root.get("controlledVocabularies", [])

    return {
        "version": version,
        "creation_date": creation_date,
        "description": description,
        "contact_name": contact_name,
        "contact_address": contact_address,
        "run_qualities": run_qualities,
        "set_qualities": set_qualities,
        "controlled_vocabularies": cv_list
    }

def show_basic_info(parsed_data: dict):
    """Display the basic metadata about the mzQC file."""
    st.subheader("Basic mzQC Metadata")
    st.write(f"**Version:** {parsed_data['version']}")
    st.write(f"**Creation Date:** {parsed_data['creation_date']}")
    st.write(f"**Description:** {parsed_data['description']}")
    st.write(f"**Contact Name:** {parsed_data['contact_name']}")
    st.write(f"**Contact Address:** {parsed_data['contact_address']}")
    
    st.write("**Controlled Vocabularies:**")
    for cv in parsed_data["controlled_vocabularies"]:
        name = cv.get("name", "N/A")
        uri = cv.get("uri", "N/A")
        version = cv.get("version", "N/A")
        st.write(f"- **Name:** {name}")
        st.write(f"  - **URI:** {uri}")
        st.write(f"  - **Version:** {version}")

def show_qualities(qualities: list, quality_type: str):
    """
    Display information about either runQualities or setQualities,
    including metadata, input files, analysis software, and QC metrics.
    """
    st.header(f"{quality_type} ({len(qualities)} total)")
    if not qualities:
        st.info(f"No {quality_type} found in this mzQC file.")
        return

    selection = st.selectbox(f"Select {quality_type} to inspect:", range(len(qualities)))
    quality = qualities[selection]
    
    metadata = quality.get("metadata", {})
    
    # Input Files
    input_files = metadata.get("inputFiles", [])
    st.subheader("Input Files")
    for i, f in enumerate(input_files):
        st.write(f"**File {i+1}**")
        st.write(f"- Name: {f.get('name', 'N/A')}")
        st.write(f"- Location: {f.get('location', 'N/A')}")
        ff = f.get("fileFormat", {})
        st.write(f"- File Format: {ff.get('name', 'N/A')} ({ff.get('accession', 'N/A')})")
        if "fileProperties" in f:
            for prop in f["fileProperties"]:
                st.write(f"  - Property: {prop.get('name', 'N/A')} = {prop.get('value', 'N/A')}")
    
    # Analysis Software
    analysis_sw = metadata.get("analysisSoftware", [])
    st.subheader("Analysis Software")
    for i, sw in enumerate(analysis_sw):
        st.write(f"**Software {i+1}**")
        st.write(f"- Name: {sw.get('name', 'N/A')} ({sw.get('accession', 'N/A')})")
        st.write(f"- Version: {sw.get('version', 'N/A')}")
        st.write(f"- URI: {sw.get('uri', 'N/A')}")
        if "description" in sw:
            st.write(f"- Description: {sw['description']}")
    
    label = metadata.get("label", None)
    if label:
        st.write(f"**Label:** {label}")
    
    cv_params = metadata.get("cvParameters", [])
    if cv_params:
        st.subheader("Additional Metadata (cvParameters)")
        for param in cv_params:
            st.write(f"- {param.get('name', 'N/A')}: {param.get('value', 'N/A')}")
    
    quality_metrics = quality.get("qualityMetrics", [])
    st.subheader("Quality Metrics")
    if not quality_metrics:
        st.info("No quality metrics found.")
        return

    for i, metric in enumerate(quality_metrics):
        st.markdown("---")
        st.write(f"**Metric {i+1}:**")
        st.write(f"- **Name:** {metric.get('name', 'N/A')} ({metric.get('accession', 'N/A')})")
        desc = metric.get('description', None)
        if desc:
            st.write(f"- **Description:** {desc}")
        
        metric_value = metric.get("value", None)
        if isinstance(metric_value, (int, float, str)):
            st.write(f"- **Value:** {metric_value}")
        elif isinstance(metric_value, (list, dict)):
            st.write("- **Value (JSON):**")
            st.json(metric_value)
        else:
            st.write("- **Value:** Unknown format")
        
        unit = metric.get("unit", None)
        if unit:
            if isinstance(unit, dict):
                st.write(f"- **Unit:** {unit.get('name', 'N/A')} ({unit.get('accession', 'N/A')})")
            elif isinstance(unit, list):
                st.write("- **Unit(s):**")
                for u in unit:
                    st.write(f"  - {u.get('name', 'N/A')} ({u.get('accession', 'N/A')})")

        chart = create_plot_from_metric(metric)
        if chart:
            st.altair_chart(chart, use_container_width=True)

def create_plot_from_metric(metric: dict):
    """
    Create visualizations based on QC metric data.
    """
    metric_name = metric.get("name", "Unknown Metric")
    metric_value = metric.get("value", None)

    if isinstance(metric_value, (int, float)):
        df = pd.DataFrame({"Metric": [metric_name], "Value": [metric_value]})
        chart = alt.Chart(df).mark_bar().encode(
            x=alt.X("Value:Q", title="Value"),
            y=alt.Y("Metric:N", title="Metric")
        ).properties(title=f"{metric_name}: {metric_value}")
        return chart

    if isinstance(metric_value, list) and all(isinstance(x, (int, float)) for x in metric_value):
        df = pd.DataFrame({"Index": range(len(metric_value)), "Value": metric_value})
        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X("Index:Q", title="Index"),
            y=alt.Y("Value:Q", title="Value"),
            tooltip=["Index", "Value"]
        ).properties(title=f"Series: {metric_name}")
        return chart

    if isinstance(metric_value, dict):
        keys = list(metric_value.keys())
        if len(keys) == 2 and isinstance(metric_value[keys[0]], list) and isinstance(metric_value[keys[1]], list):
            list1 = metric_value[keys[0]]
            list2 = metric_value[keys[1]]
            if len(list1) == len(list2):
                if all(isinstance(x, str) for x in list1) and all(isinstance(x, (int, float)) for x in list2):
                    df = pd.DataFrame({"Category": list1, "Value": list2})
                    chart = alt.Chart(df).mark_bar().encode(
                        x=alt.X("Value:Q", title="Value"),
                        y=alt.Y("Category:N", title="Category", sort="-x"),
                        tooltip=["Category", "Value"]
                    ).properties(title=f"{metric_name}: Category vs. Value")
                    return chart
                elif all(isinstance(x, (int, float)) for x in list1) and all(isinstance(x, str) for x in list2):
                    df = pd.DataFrame({"Category": list2, "Value": list1})
                    chart = alt.Chart(df).mark_bar().encode(
                        x=alt.X("Value:Q", title="Value"),
                        y=alt.Y("Category:N", title="Category", sort="-x"),
                        tooltip=["Category", "Value"]
                    ).properties(title=f"{metric_name}: Category vs. Value")
                    return chart

        df = pd.DataFrame(list(metric_value.items()), columns=["Category", "Value"])
        if df["Value"].apply(lambda x: isinstance(x, (int, float))).all():
            chart = alt.Chart(df).mark_bar().encode(
                x="Category:N",
                y="Value:Q",
                tooltip=["Category", "Value"]
            ).properties(title=f"Categorized Values: {metric_name}")
            return chart

    return None

def main():
    st.title("mzQC Viewer")
    st.write(
        """
        This app allows you to upload an **mzQC** JSON file, parse it, and explore 
        its contents through textual summaries and simple visualizations. 
        \n
        **Instructions**:
        - Upload an mzQC file using the uploader below.
        - The app will automatically convert a **.mzqc** file to JSON if needed.
        - Explore the metadata, input files, analysis software, and QC metrics.
        """
    )
    
    uploaded_file = st.file_uploader("Upload your mzQC file (.json or .mzqc)", type=["json", "mzqc"])
    if uploaded_file is not None:
        try:
            # Check file extension to decide how to load
            file_name = uploaded_file.name.lower()
            if file_name.endswith('.mzqc'):
                # Assume .mzqc is a JSON file with a different extension
                file_content = uploaded_file.getvalue().decode("utf-8")
                data = json.loads(file_content)
            else:
                data = json.load(uploaded_file)
            
            parsed_data = parse_mzqc(data)
            show_basic_info(parsed_data)
            show_qualities(parsed_data["run_qualities"], "runQualities")
            show_qualities(parsed_data["set_qualities"], "setQualities")
        except Exception as e:
            st.error(f"Error parsing file: {e}")

if __name__ == "__main__":
    main()
