import streamlit as st
import pandas as pd
import plotly.express as px
import json

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & CUSTOM CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="eVidyaloka Impact Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Professional UI
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }

    /* Summary Box Styling */
    .summary-box {
        background-color: #e0f2f1;
        border-left: 6px solid #00796b;
        padding: 20px;
        border-radius: 5px;
        margin-top: 20px;
        margin-bottom: 20px;
        font-size: 18px;
        color: #004d40;
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: white; padding: 15px; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-left: 5px solid #00796b;
    }

    h1, h2, h3 { color: #2c3e50; font-family: 'Helvetica Neue', sans-serif; }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; white-space: pre-wrap; background-color: white;
        border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e3f2fd; color: #0d47a1; border-bottom: 2px solid #0d47a1;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 2. DATA LOGIC & CALCULATIONS
# -----------------------------------------------------------------------------

def extract_answer_value(val):
    try:
        if pd.isna(val): return None
        clean_val = str(val).strip()
        if clean_val.startswith('"') and clean_val.endswith('"'):
            clean_val = clean_val[1:-1].replace('""', '"')
        data = json.loads(clean_val)
        return int(data.get('value', -1))
    except:
        return None


def calculate_row_score(row, key_df, assessment_type):
    score = 0
    total_questions = 0
    grade = row['Grade']
    relevant_key = key_df[(key_df['Grade'] == f"G{grade}") & (key_df['Assessment'] == assessment_type)]

    for q_num in range(1, 11):
        q_col = f"Q{q_num}"
        if q_col in row:
            student_ans = extract_answer_value(row[q_col])
            correct_row = relevant_key[relevant_key['Question #'] == q_num]
            if not correct_row.empty:
                correct_ans = correct_row.iloc[0]['Correct Value']
                if student_ans == correct_ans:
                    score += 1
                total_questions += 1
    return score, total_questions


@st.cache_data
def process_workbook(uploaded_file):
    try:
        xls = pd.read_excel(uploaded_file, sheet_name=None)
        if not all(x in xls for x in ['WB-Baseline-English', 'WB-Endline-English', 'AnswerKey']):
            st.error("Missing required sheets.")
            return None, None, None, None

        baseline_df = xls['WB-Baseline-English']
        endline_df = xls['WB-Endline-English']
        answer_key = xls['AnswerKey']

        # Calculate Scores
        baseline_df['Score'], baseline_df['Max_Score'] = zip(*baseline_df.apply(
            lambda x: calculate_row_score(x, answer_key, 'Baseline'), axis=1
        ))
        baseline_df['Percentage'] = (baseline_df['Score'] / baseline_df['Max_Score']) * 100

        endline_df['Score'], endline_df['Max_Score'] = zip(*endline_df.apply(
            lambda x: calculate_row_score(x, answer_key, 'Endline'), axis=1
        ))
        endline_df['Percentage'] = (endline_df['Score'] / endline_df['Max_Score']) * 100

        # Merge
        merged_df = pd.merge(
            baseline_df[['Student ID', 'State', 'Center', 'Grade', 'Percentage', 'Score']],
            endline_df[['Student ID', 'Percentage', 'Score']],
            on='Student ID', suffixes=('_BL', '_EL')
        )
        merged_df['Growth'] = merged_df['Percentage_EL'] - merged_df['Percentage_BL']

        return merged_df, baseline_df, endline_df, answer_key
    except Exception as e:
        st.error(f"Error: {e}")
        return None, None, None, None


# -----------------------------------------------------------------------------
# 3. MAIN APP
# -----------------------------------------------------------------------------
st.sidebar.title("📂 Data Setup")
uploaded_file = st.sidebar.file_uploader("Upload Workbook", type=["xlsx"])

if uploaded_file:
    df_merged, df_bl, df_el, answer_key = process_workbook(uploaded_file)

    if df_merged is not None:
        # Sidebar Filters
        st.sidebar.divider()
        st.sidebar.header("🔍 Filters")
        selected_state = st.sidebar.multiselect("State", df_merged['State'].unique(),
                                                default=df_merged['State'].unique())
        selected_grade = st.sidebar.multiselect("Grade", sorted(df_merged['Grade'].unique()),
                                                default=sorted(df_merged['Grade'].unique()))

        # Apply Filters
        filtered_df = df_merged[(df_merged['State'].isin(selected_state)) & (df_merged['Grade'].isin(selected_grade))]
        filtered_bl = df_bl[(df_bl['State'].isin(selected_state)) & (df_bl['Grade'].isin(selected_grade))]
        filtered_el = df_el[(df_el['State'].isin(selected_state)) & (df_el['Grade'].isin(selected_grade))]

        st.title("eVidyaloka Impact Dashboard 🚀")

        # TABS
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Executive Summary",
            "🏫 Centre Performance",
            "🔍 Deep Dive (Students)",
            "❓ Question Analysis"
        ])

        # --- TAB 1: EXECUTIVE SUMMARY ---
        with tab1:
            st.markdown("### High Level Overview")

            # Calculate Metrics
            avg_bl = filtered_df['Percentage_BL'].mean()
            avg_el = filtered_df['Percentage_EL'].mean()
            avg_growth = filtered_df['Growth'].mean()
            count_students = len(filtered_df)

            # Metrics Row
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Students Assessed", f"{count_students:,}")
            kpi2.metric("Baseline Avg", f"{avg_bl:.1f}%")
            kpi3.metric("Endline Avg", f"{avg_el:.1f}%", delta=f"{avg_el - avg_bl:.1f}%")
            kpi4.metric("Avg Growth", f"{avg_growth:.1f}%")

            # --- NEW: TEXT SUMMARY SECTION ---
            summary_html = f"""
            <div class="summary-box">
                <b>📊 Impact Insight:</b><br>
                Across <b>{count_students:,}</b> students, the average proficiency score improved from 
                <b>{avg_bl:.1f}%</b> in the baseline to <b>{avg_el:.1f}%</b> in the endline assessment. 
                This indicates a net positive learning outcome of <b>{avg_growth:.1f}%</b> for the selected cohort.
            </div>
            """
            st.markdown(summary_html, unsafe_allow_html=True)
            # ---------------------------------

            st.divider()

            # Grade Comparison Chart
            grade_stats = filtered_df.groupby('Grade')[['Percentage_BL', 'Percentage_EL']].mean().reset_index()
            grade_melted = grade_stats.melt(id_vars='Grade', var_name='Type', value_name='Score')

            fig = px.bar(grade_melted, x='Grade', y='Score', color='Type', barmode='group',
                         title="Average Performance by Grade (Baseline vs Endline)",
                         color_discrete_map={'Percentage_BL': '#bdc3c7', 'Percentage_EL': '#00796b'})
            fig.update_layout(plot_bgcolor='white')
            st.plotly_chart(fig, use_container_width=True)

        # --- TAB 2: CENTRE PERFORMANCE ---
        with tab2:
            st.markdown("### Centre Wise Performance Analysis")
            st.caption(
                "This matrix helps identify high-performing centers (Top Right) vs. those needing attention (Bottom Left).")

            center_stats = filtered_df.groupby('Center').agg(
                Avg_Growth=('Growth', 'mean'),
                Avg_Endline=('Percentage_EL', 'mean'),
                Count=('Student ID', 'count')
            ).reset_index()

            # Full Width Scatter Plot
            fig_scatter = px.scatter(
                center_stats, x='Avg_Endline', y='Avg_Growth', size='Count', color='Avg_Growth',
                hover_name='Center', title="Growth vs Proficiency Matrix",
                labels={'Avg_Endline': 'Final Proficiency (%)', 'Avg_Growth': 'Growth (%)'},
                color_continuous_scale='Teal',
                height=600
            )
            fig_scatter.add_hline(y=center_stats['Avg_Growth'].mean(), line_dash="dot", annotation_text="Avg Growth",
                                  annotation_position="bottom right")
            fig_scatter.add_vline(x=center_stats['Avg_Endline'].mean(), line_dash="dot", annotation_text="Avg Score",
                                  annotation_position="top right")

            st.plotly_chart(fig_scatter, use_container_width=True)

        # --- TAB 3: DEEP DIVE (STUDENTS) ---
        with tab3:
            st.markdown("### 🕵️ Student Level Deep Dive")
            search_term = st.text_input("Search by Student ID or Center Name:")

            display_df = filtered_df.copy()
            if search_term:
                display_df = display_df[
                    display_df['Student ID'].astype(str).str.contains(search_term) |
                    display_df['Center'].str.contains(search_term, case=False)
                    ]

            st.dataframe(
                display_df[['Student ID', 'Grade', 'Center', 'Percentage_BL', 'Percentage_EL', 'Growth']]
                .style.format("{:.1f}", subset=['Percentage_BL', 'Percentage_EL', 'Growth'])
                .background_gradient(subset=['Growth'], cmap='RdYlGn'),
                use_container_width=True
            )

        # --- TAB 4: QUESTION ANALYSIS ---
        with tab4:
            st.markdown("### 🧪 Question Difficulty Analysis")
            st.info("Analyzing Endline Data to identify learning gaps.")


            def calculate_question_stats(df, key_df, assessment_type):
                stats = []
                for grade in df['Grade'].unique():
                    grade_df = df[df['Grade'] == grade]
                    key_subset = key_df[(key_df['Grade'] == f"G{grade}") & (key_df['Assessment'] == assessment_type)]

                    for q_num in range(1, 11):
                        q_col = f"Q{q_num}"
                        if q_col in grade_df.columns:
                            q_key = key_subset[key_subset['Question #'] == q_num]
                            if not q_key.empty:
                                correct_val = q_key.iloc[0]['Correct Value']
                                extracted = grade_df[q_col].apply(extract_answer_value)
                                is_correct = (extracted == correct_val)
                                accuracy = is_correct.mean() * 100
                                stats.append({'Grade': grade, 'Question': f"Q{q_num}", 'Accuracy': accuracy})
                return pd.DataFrame(stats)


            q_stats = calculate_question_stats(filtered_el, answer_key, 'Endline')

            if not q_stats.empty:
                col1, col2 = st.columns([2, 1])

                with col1:
                    fig_heat = px.density_heatmap(
                        q_stats, x='Question', y='Grade', z='Accuracy',
                        color_continuous_scale='RdYlGn', text_auto='.0f',
                        title="Question Accuracy Heatmap (Red = Hard, Green = Easy)",
                        range_color=[0, 100]
                    )
                    st.plotly_chart(fig_heat, use_container_width=True)

                with col2:
                    avg_by_q = q_stats.groupby('Question')['Accuracy'].mean().sort_values()
                    hardest = avg_by_q.idxmin()
                    easiest = avg_by_q.idxmax()

                    st.warning(f"🚨 **Hardest Question:** {hardest}")
                    st.caption(f"Only {avg_by_q.min():.1f}% of students got this right.")

                    st.success(f"✅ **Easiest Question:** {easiest}")
                    st.caption(f"{avg_by_q.max():.1f}% of students answered correctly.")

                    st.markdown("#### Question Breakdown")
                    st.bar_chart(avg_by_q)

else:
    st.info("Please upload the workbook to view the dashboard.")
    