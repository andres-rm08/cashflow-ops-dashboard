import pandas as pd
import streamlit as st

st.set_page_config(page_title="Cashflow-Aware Ops Prioritization", layout="wide")

today = pd.Timestamp.today().normalize()

@st.cache_data
def load_data():
    transactions = pd.read_csv("data/transactions.csv")
    ops = pd.read_csv("data/ops_items.csv")
    risk = pd.read_csv("data/risk_data_quality.csv")
    clients = pd.read_csv("data/client_tier.csv")

    df = (ops.merge(transactions, on="ops_item_id", how="left").merge(risk, on="ops_item_id", how="left")
        .merge(clients, on="client_id", how="left"))
    return df

df = load_data()

if "status_y" in df.columns:
    df["invoice_status"] = df["status_y"]
elif "status" in df.columns:
    df["invoice_status"] = df["status"]
else:
    df["invoice_status"] = df.get("status_x", "open")
df["is_overdue"] = (df["invoice_status"] == "overdue").astype(int) * 100
df['amount'] = df['amount'].fillna(0)
df['due_date'] = pd.to_datetime(df['due_date'], errors='coerce')
df['days_past_due'] = (today - df['due_date']).dt.days
df['days_past_due'] = df['days_past_due'].fillna(0)
df['days_past_due'] = df['days_past_due'].clip(lower=0) 
df['sla_due'] = pd.to_datetime(df['sla_due'], errors='coerce')
df["days_to_sla"] = (df["sla_due"] - today).dt.days
df["days_to_sla"] = df["days_to_sla"].fillna(999)
df["sla_risk"] = (df["days_to_sla"] <= 0).astype(int) * 100
df["blocks_invoicing"] = df["blocks_invoicing"].fillna(0).astype(int)
df["missing_fields"] = df["missing_fields"].fillna(0)
df["age_days"] = df["age_days"].fillna(0)

def get_aging_bucket(days):
    if days == 0:
        return "Current"
    elif days <= 30:
        return "0-30 days"
    elif days <= 60:
        return "31-60 days"
    elif days <= 90:
        return "61-90 days"
    else:
        return "90+ days"

df['aging_bucket'] = df['days_past_due'].apply(get_aging_bucket)
df['has_exception'] = ((df['blocks_invoicing'] == 1) | (df['missing_fields'] > 0)).astype(int)
exception_rate = df['has_exception'].mean() * 100

weights = {'A': 3, 'B': 2, 'C': 1}
df['tier_raw_score'] = df['tier'].map(weights).fillna(1)

def scale(a):
    a_min = a.min()
    a_max = a.max()
    if a_max == a_min:
        return pd.Series(50, index=a.index)
    return (a - a_min) / (a_max - a_min) * 100

df['scaled_amount'] = scale(df['amount'])
df['scaled_age_days'] = scale(df['age_days'])

df['transaction_comp'] = df['is_overdue'] + df['scaled_amount']
df['ops_comp'] = df['sla_risk'] + df['scaled_age_days']
df['data_comp'] = df['blocks_invoicing'] * 5 + df['missing_fields']
df['client_comp'] = df['tier_raw_score']

df['scaled_transaction_comp'] = scale(df['transaction_comp'])
df['scaled_ops_comp'] = scale(df['ops_comp'])
df['scaled_data_comp'] = scale(df['data_comp'])
df['scaled_client_comp'] = scale(df['client_comp'])

st.title("Cashflow-Aware Operations Prioritization Dashboard")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total AR in queue", f"${df['amount'].sum():,.0f}")
with col2:
    overdue_amount = df.loc[df["is_overdue"] == 100, "amount"].sum()
    st.metric("Past-due AR", f"${overdue_amount:,.0f}")
with col3:
    blocked_amount = df.loc[df["blocks_invoicing"] == 1, "amount"].sum()
    st.metric("AR on billing hold", f"${blocked_amount:,.0f}")
with col4:
    pct_overdue = (df["is_overdue"] == 100).mean() * 100
    st.metric("% items overdue", f"{pct_overdue:,.1f}%")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Total AR in queue", f"${df['amount'].sum():,.0f}")
with col2:
    overdue_amount = df.loc[df["is_overdue"] == 100, "amount"].sum()
    st.metric("Past-due AR", f"${overdue_amount:,.0f}")
with col3:
    blocked_amount = df.loc[df["blocks_invoicing"] == 1, "amount"].sum()
    st.metric("AR on billing hold", f"${blocked_amount:,.0f}")
with col4:
    pct_overdue = (df["is_overdue"] == 100).mean() * 100
    st.metric("% items overdue", f"{pct_overdue:,.1f}%")
with col5:
    st.metric("Exception rate", f"{exception_rate:.1f}%")

st.subheader("AR Aging Analysis")
aging_summary = df.groupby('aging_bucket').agg({
    'amount': 'sum',
    'invoice_id': 'count'
}).rename(columns={'invoice_id': 'count'})

bucket_order = ['Current', '0-30 days', '31-60 days', '61-90 days', '90+ days']
aging_summary = aging_summary.reindex([b for b in bucket_order if b in aging_summary.index], fill_value=0)
st.dataframe(aging_summary.style.format({'amount': '${:,.0f}', 'count': '{:,.0f}'}))

st.subheader("Policy weights")
c1, c2, c3 = st.columns(3)
with c1:
    transaction_w = st.slider("Cash / transaction weight", 0.0, 1.0, 0.4, 0.05)
with c2:
    ops_w = st.slider("Ops / SLA weight", 0.0, 1.0, 0.3, 0.05)
with c3:
    data_w = st.slider("Data-quality weight", 0.0, 1.0, 0.2, 0.05)

used = transaction_w + ops_w + data_w
client_w = max(0.0, 1.0 - used)

df['priority_score'] = (df['scaled_transaction_comp'] * transaction_w
                        + df['scaled_ops_comp'] * ops_w 
                        + df['scaled_data_comp'] * data_w
                        + df['scaled_client_comp'] * client_w)

df = df.sort_values("priority_score", ascending=False)

top_20 = df.head(20)
top_20_ar = top_20['amount'].sum()
total_ar = df['amount'].sum()
top_20_pct_ar = (top_20_ar / total_ar * 100) if total_ar > 0 else 0
top_20_count = len(top_20)
total_count = len(df)
top_20_pct_count = (top_20_count / total_count * 100) if total_count > 0 else 0

st.subheader("Top items to process")
st.dataframe(df[["ops_item_id","client_id","invoice_id","amount","invoice_status","blocks_invoicing",
                "priority_score",]].head(20))

csv = df[["ops_item_id","client_id","invoice_id","amount","status","blocks_invoicing",
          "priority_score",]].head(20).to_csv(index=False)

st.download_button(label="Download top 20 items as CSV", data=csv,
    file_name="top_items_to_process.csv",
    mime="text/csv")

