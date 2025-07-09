import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from scipy.stats import gaussian_kde
df=pd.read_csv(r"C:\Users\Abhi9\Downloads\simple_straight.csv")
df=df.drop(labels=3098880,axis=0)
df['Closed PnL']=df['Closed PnL'].replace('-',np.nan)
df['Closed PnL'] = df['Closed PnL'].astype('Float64')
df['Timestamp IST'] = pd.to_datetime(df['Timestamp IST'])
df = df.sort_values(['Account', 'Timestamp IST'])
df['Cumulative PnL'] = df.groupby('Account')['Closed PnL'].cumsum()
df['Month'] = df['Timestamp IST'].dt.to_period('M')
unique_accounts = df['Account'].unique()
# Function to create standard PnL trend plot (your original logic)
def create_standard_pnl_plot(account):
    trader_data = df[df['Account'] == account]
    monthly_data = trader_data.groupby('Month').agg({
        'Cumulative PnL': 'last',
        'Timestamp IST': 'last'
    }).reset_index()
    
    fig = go.Figure()
    
    # Main PnL line
    fig.add_trace(
        go.Scatter(
            x=monthly_data['Timestamp IST'],
            y=monthly_data['Cumulative PnL'],
            mode='lines+markers',
            line=dict(color='#4E79A7', width=3),
            marker=dict(size=8, color='#4E79A7'),
            hovertemplate="<b>%{x|%b %Y}</b><br>PnL: $%{y:,.2f}<extra></extra>"
        )
    )
    
    # Layout configuration
    fig.update_layout(
        title=f"{account[:8]}",
        title_x=0.5,
        showlegend=False,
        margin=dict(l=50, r=50, b=80, t=80),
        plot_bgcolor='rgba(250,250,250,1)',
        paper_bgcolor='white',
        font=dict(family="Arial", size=12),
        height=500,
        width=900
    )
    
    # Y-axis
    fig.update_yaxes(
        title_text="Cumulative PnL (USD)",
        tickprefix="$",
        gridcolor='rgba(220,220,220,0.5)',
        zerolinecolor='rgba(150,150,150,0.5)'
    )
    
    # X-axis
    fig.update_xaxes(
        title_text="Timeline",
        tickformat="%b %Y",
        gridcolor='rgba(220,220,220,0.5)',
        range=[pd.to_datetime('2024-06-01'), pd.to_datetime('2025-07-01')]
    )
    
    # Final PnL annotation
    final_pnl = monthly_data['Cumulative PnL'].iloc[-1]
    fig.add_annotation(
        xref="paper",
        yref="y",
        x=0.95,
        y=final_pnl,
        text=f"Final PnL: ${final_pnl:,.2f}",
        showarrow=True,
        arrowhead=2,
        ax=-40,
        ay=0,
        bordercolor="#4E79A7",
        borderwidth=1,
        bgcolor="white"
    )
    
    # Zero line reference
    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="gray",
        opacity=0.7
    )
    
    return fig

# Function to create signed log scale plot (using your plotting style)
def create_signed_log_plot(account):
    trader_data = df[df['Account'] == account]
    monthly_data = trader_data.groupby('Month').agg({
        'Cumulative PnL': 'last',
        'Timestamp IST': 'last'
    }).reset_index()
    
    # Apply signed log transform
    monthly_data['Signed Log PnL'] = np.sign(monthly_data['Cumulative PnL']) * np.log10(1 + abs(monthly_data['Cumulative PnL']))
    
    fig = go.Figure()
    
    # Main PnL line
    fig.add_trace(
        go.Scatter(
            x=monthly_data['Timestamp IST'],
            y=monthly_data['Signed Log PnL'],
            mode='lines+markers',
            line=dict(color='#E15759', width=3),
            marker=dict(size=8, color='#E15759'),
            hovertemplate="<b>%{x|%b %Y}</b><br>Log Value: %{y:.2f}<br>Actual PnL: $%{customdata:,.2f}<extra></extra>",
            customdata=monthly_data['Cumulative PnL']
        )
    )
    
    # Layout configuration (matches your style)
    fig.update_layout(
        title=f"{account}",
        title_x=0.5,
        showlegend=False,
        margin=dict(l=50, r=50, b=80, t=80),
        plot_bgcolor='rgba(250,250,250,1)',
        paper_bgcolor='white',
        font=dict(family="Arial", size=12),
        height=500,
        width=900
    )
    
    # Y-axis
    fig.update_yaxes(
        title_text="Signed Log PnL",
        gridcolor='rgba(220,220,220,0.5)',
        zerolinecolor='rgba(150,150,150,0.5)'
    )
    
    # X-axis
    fig.update_xaxes(
        title_text="Timeline",
        tickformat="%b %Y",
        gridcolor='rgba(220,220,220,0.5)',
        range=[pd.to_datetime('2024-06-01'), pd.to_datetime('2025-07-01')]
    )
    
    # Final PnL annotation (showing actual PnL)
    final_pnl = monthly_data['Cumulative PnL'].iloc[-1]
    fig.add_annotation(
        xref="paper",
        yref="y",
        x=0.95,
        y=monthly_data['Signed Log PnL'].iloc[-1],
        text=f"Final PnL: ${final_pnl:,.2f}",
        showarrow=True,
        arrowhead=2,
        ax=-40,
        ay=0,
        bordercolor="#E15759",
        borderwidth=1,
        bgcolor="white"
    )
    
    # Zero line reference
    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="gray",
        opacity=0.7
    )
    
    return fig

# Function to create KDE plot for closed PnL distribution
def create_kde_plot(account):
    trader_data = df[df['Account'] == account]
    pnl_values = trader_data['Closed PnL'].dropna()
    
    if len(pnl_values) < 2:
        print(f"Not enough data for KDE plot for account {account[:8]}...")
        return None
    
    # Calculate KDE
    kde = gaussian_kde(pnl_values)
    x_vals = np.linspace(pnl_values.min(), pnl_values.max(), 500)
    y_vals = kde(x_vals)
    
    fig = go.Figure()
    
    # KDE line
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='lines',
            line=dict(color='#59A14F', width=2),
            fill='tozeroy',
            fillcolor='rgba(89, 161, 79, 0.2)',
            name='Density'
        )
    )
    
    # Mean line
    mean_pnl = pnl_values.mean()
    fig.add_vline(
        x=mean_pnl,
        line=dict(color='#E15759', width=2, dash='dash'),
        annotation_text=f"Mean: ${mean_pnl:,.2f}",
        annotation_position="top right"
    )
    
    # Layout (matches your style)
    fig.update_layout(
        title=f"{account}",
        title_x=0.5,
        xaxis_title="Closed PnL (USD)",
        yaxis_title="Density",
        plot_bgcolor='rgba(250,250,250,1)',
        paper_bgcolor='white',
        font=dict(family="Arial", size=12),
        height=500,
        width=900,
        showlegend=False
    )
    
    # Add summary statistics
    stats_text = (f"<b>Statistics:</b><br>"
                 f"Trades: {len(pnl_values):,}<br>"
                 f"Mean: ${mean_pnl:,.2f}<br>"
                 f"Std Dev: ${pnl_values.std():,.2f}<br>"
                 f"Min: ${pnl_values.min():,.2f}<br>"
                 f"Max: ${pnl_values.max():,.2f}")
    
    fig.add_annotation(
        xref="paper",
        yref="paper",
        x=0.95,
        y=0.95,
        text=stats_text,
        showarrow=False,
        align="right",
        bordercolor="black",
        borderwidth=1,
        bgcolor="white"
    )
    
    return fig

for trader in unique_accounts:
    # Create standard PnL plot
    std_fig = create_standard_pnl_plot(trader)
    std_fig.show()
    
    # Create signed log plot
    log_fig = create_signed_log_plot(trader)
    log_fig.show()
    
    # Create KDE plot
    kde_fig = create_kde_plot(trader)
    if kde_fig is not None:
        kde_fig.show()