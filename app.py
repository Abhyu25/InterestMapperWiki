import gradio as gr
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timedelta
from functools import cache
import re

# Function to extract title from Wikipedia URL
def extract_title(url):
    if not url.startswith("https://en.wikipedia.org/wiki/"):
        raise ValueError("URL must be from en.wikipedia.org")
    return url.split("wiki/")[1]

# Cached API call for pageviews
@cache
def get_pageviews(title, start_date, end_date):
    try:
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia.org/all-access/all-agents/{title}/daily/{start_date}/{end_date}"
        headers = {'User-Agent': 'Gradio-Wiki-Analyzer/1.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()['items']
        return [(item['timestamp'][:8], item['views']) for item in data]
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"API error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error fetching pageviews: {str(e)}")

# Validate and format dates
def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y%m%d')
        return date_str
    except ValueError:
        raise ValueError("Date must be in YYYYMMDD format")

# Main processing function
def process_inputs(url1, url2, start_date, end_date):
    # Set default dates if empty
    if not start_date or not end_date:
        end_date_obj = datetime.now()
        start_date_obj = end_date_obj - timedelta(days=30)
        start_date = start_date_obj.strftime('%Y%m%d')
        end_date = end_date_obj.strftime('%Y%m%d')

    # Validate inputs
    start_date = validate_date(start_date)
    end_date = validate_date(end_date)

    # Extract titles
    title1 = extract_title(url1)
    title2 = extract_title(url2)

    # Fetch data
    views1 = get_pageviews(title1, start_date, end_date)
    views2 = get_pageviews(title2, start_date, end_date)

    # Process data into DataFrame
    dates1, counts1 = zip(*views1) if views1 else ([], [])
    dates2, counts2 = zip(*views2) if views2 else ([], [])

    all_dates = sorted(set(dates1) | set(dates2))
    view_dict1 = dict(views1)
    view_dict2 = dict(views2)

    df = pd.DataFrame({
        'Date': all_dates,
        f'{title1} Views': [view_dict1.get(d, 0) for d in all_dates],
        f'{title2} Views': [view_dict2.get(d, 0) for d in all_dates]
    })

    # Create Plotly figure
    fig = px.line(
        df,
        x='Date',
        y=[f'{title1} Views', f'{title2} Views'],
        title='Wikipedia Page Views Comparison',
        labels={'value': 'Views', 'variable': 'Topic'}
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Page Views",
        legend_title="Topics",
        template="plotly_dark",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=0.01,
            xanchor="right",
            x=0.99
        ),
        width=None,
        height=500,
        margin=dict(l=50, r=50, t=50, b=50)
    )

    return df, fig, "Analysis completed successfully!"

# Gradio interface
def create_app():
    with gr.Blocks(title="Wikipedia Page Views Analyzer") as demo:
        gr.Markdown("# Wikipedia Page Views Analyzer")
        gr.Markdown("Compare page views between two Wikipedia articles")

        with gr.Row():
            url1 = gr.Textbox(
                label="Topic 1 URL",
                placeholder="https://en.wikipedia.org/wiki/Python_(programming_language)",
                value="https://en.wikipedia.org/wiki/Python_(programming_language)"
            )
            url2 = gr.Textbox(
                label="Topic 2 URL",
                placeholder="https://en.wikipedia.org/wiki/Java_(programming_language)",
                value="https://en.wikipedia.org/wiki/Java_(programming_language)"
            )

        with gr.Row():
            start_date = gr.Textbox(
                label="Start Date (YYYYMMDD)",
                placeholder="Default: 30 days ago"
            )
            end_date = gr.Textbox(
                label="End Date (YYYYMMDD)",
                placeholder="Default: today"
            )

        submit = gr.Button("Analyze")
        status = gr.Textbox(label="Status", interactive=False)

        with gr.Tabs():
            with gr.Tab("Data"):
                dataframe = gr.DataFrame(
                    headers=["Date", "Topic 1 Views", "Topic 2 Views"]
                )
            with gr.Tab("Trends"):
                plot = gr.Plot()

        # Handle submission with error handling and status updates
        def wrapped_process(url1, url2, start_date, end_date):
            try:
                df, fig, msg = process_inputs(url1, url2, start_date, end_date)
                return df, fig, msg
            except ValueError as e:
                return pd.DataFrame(), None, f"Error: {str(e)}"
            except Exception as e:
                return pd.DataFrame(), None, f"Unexpected error: {str(e)}"

        submit.click(
            fn=wrapped_process,
            inputs=[url1, url2, start_date, end_date],
            outputs=[dataframe, plot, status],
            queue=True
        )

    return demo

# Launch the app
if __name__ == "__main__":
    app = create_app()
    app.launch()
