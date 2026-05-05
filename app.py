import streamlit as st
import os, json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import (
    init_db, save_job, load_jobs,
    save_candidate, load_candidates, load_ranked_candidates,
    save_score, update_status,
    parse_resume,
    calculate_skill_match, calculate_ats_score,
    calculate_similarity, calculate_section_scores, compute_final_score,
    SKILL_LIST,
)

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RecruitIQ · AI Hiring Platform",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_db()
os.makedirs("uploads", exist_ok=True)

# ─────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --bg:       #07080d;
    --surface:  #0f1118;
    --card:     #141720;
    --border:   #1e2235;
    --accent:   #6c63ff;
    --accent2:  #00d4aa;
    --accent3:  #ff6b6b;
    --text:     #e8eaf0;
    --muted:    #6b7280;
    --gold:     #f5c842;
}

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Remove default padding */
.block-container { padding: 2rem 2.5rem 4rem !important; max-width: 1400px; }

/* Headings */
h1,h2,h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.02em; }

/* Cards */
.riq-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

/* Metric tiles */
.metric-tile {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    text-align: center;
}
.metric-tile .val {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1;
}
.metric-tile .lbl {
    font-size: 0.82rem;
    color: var(--muted);
    margin-top: 6px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

/* Score badge */
.score-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 999px;
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
}
.score-high  { background: #00d4aa22; color: #00d4aa; border: 1px solid #00d4aa44; }
.score-mid   { background: #f5c84222; color: #f5c842; border: 1px solid #f5c84244; }
.score-low   { background: #ff6b6b22; color: #ff6b6b; border: 1px solid #ff6b6b44; }

/* Status pills */
.pill-Shortlisted { background:#00d4aa22; color:#00d4aa; border:1px solid #00d4aa44; padding:3px 12px; border-radius:999px; font-size:0.8rem; }
.pill-Rejected    { background:#ff6b6b22; color:#ff6b6b; border:1px solid #ff6b6b44; padding:3px 12px; border-radius:999px; font-size:0.8rem; }
.pill-On-Hold     { background:#f5c84222; color:#f5c842; border:1px solid #f5c84244; padding:3px 12px; border-radius:999px; font-size:0.8rem; }
.pill-Pending     { background:#6c63ff22; color:#6c63ff; border:1px solid #6c63ff44; padding:3px 12px; border-radius:999px; font-size:0.8rem; }

/* Section tag */
.tag {
    display: inline-block;
    background: #6c63ff15;
    color: #8b85ff;
    border: 1px solid #6c63ff30;
    padding: 2px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    margin: 2px;
}

/* Divider */
.riq-divider { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }

/* Streamlit overrides */
div[data-testid="stMetric"] { display: none; }
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.4rem !important;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stSelectbox div, .stTextInput input, .stTextArea textarea {
    background: var(--card) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
}
.stExpander { background: var(--card) !important; border: 1px solid var(--border) !important; border-radius: 12px !important; }
[data-testid="stFileUploader"] { background: var(--card) !important; border: 1px dashed var(--border) !important; border-radius: 12px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='padding:0.5rem 0 1.5rem'>
      <div style='font-family:Syne,sans-serif;font-size:1.5rem;font-weight:800;color:#e8eaf0'>
        🎯 RecruitIQ
      </div>
      <div style='font-size:0.78rem;color:#6b7280;margin-top:4px;letter-spacing:0.05em'>
        AI-POWERED HIRING PLATFORM
      </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio("", [
        "📊 Dashboard",
        "💼 Create Job",
        "📂 Upload Resumes",
        "🏆 Candidate Ranking",
        "📈 Analytics",
    ], label_visibility="collapsed")

    st.markdown("<hr style='border-color:#1e2235;margin:1.5rem 0'>", unsafe_allow_html=True)
    jobs      = load_jobs()
    cands     = load_candidates()
    st.markdown(f"""
    <div style='font-size:0.82rem;color:#6b7280'>
      <div style='margin-bottom:6px'>📋 <b style='color:#e8eaf0'>{len(jobs)}</b> Jobs</div>
      <div>👤 <b style='color:#e8eaf0'>{len(cands)}</b> Candidates</div>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────
def score_label(s):
    if s >= 70:   return "score-high"
    if s >= 45:   return "score-mid"
    return "score-low"

def badge(s):
    return f'<span class="score-badge {score_label(s)}">{s}</span>'

def metric_tile(val, label, color="var(--accent)"):
    return f"""
    <div class='metric-tile'>
      <div class='val' style='color:{color}'>{val}</div>
      <div class='lbl'>{label}</div>
    </div>"""

plotly_layout = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e8eaf0",
    font_family="DM Sans",
    margin=dict(l=20, r=20, t=40, b=20),
)

# ─────────────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    st.markdown("<h1 style='margin-bottom:0.2rem'>Recruiter Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6b7280;margin-bottom:2rem'>Overview of your hiring pipeline</p>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(metric_tile(len(jobs), "Active Jobs", "#6c63ff"), unsafe_allow_html=True)
    with c2: st.markdown(metric_tile(len(cands), "Candidates", "#00d4aa"), unsafe_allow_html=True)

    # Count statuses across all scores
    con = __import__("sqlite3").connect("recruiter.db")
    cur = con.cursor()
    cur.execute("SELECT status, COUNT(*) FROM scores GROUP BY status")
    status_data = dict(cur.fetchall())
    cur.execute("SELECT COUNT(*) FROM scores WHERE final_score >= 70")
    top_count = cur.fetchone()[0]
    con.close()

    with c3: st.markdown(metric_tile(top_count, "High Matches (≥70)", "#f5c842"), unsafe_allow_html=True)
    with c4: st.markdown(metric_tile(status_data.get("Shortlisted",0), "Shortlisted", "#00d4aa"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown("<div class='riq-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔥 Recent Jobs")
        if jobs:
            for j in jobs[:5]:
                skills_str = ", ".join(j["skills"][:5])
                st.markdown(f"""
                <div style='padding:0.8rem 0;border-bottom:1px solid #1e2235'>
                  <div style='font-family:Syne,sans-serif;font-weight:700'>{j['title']}</div>
                  <div style='font-size:0.8rem;color:#6b7280;margin-top:3px'>📍 {j['location']} &nbsp;·&nbsp; 🕒 {j['experience']}</div>
                  <div style='margin-top:6px'>{''.join(f"<span class='tag'>{s}</span>" for s in j['skills'][:6])}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("No jobs yet. Create your first job posting!")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown("<div class='riq-card'>", unsafe_allow_html=True)
        st.markdown("#### 📌 Pipeline Status")
        if status_data:
            fig = go.Figure(go.Pie(
                labels=list(status_data.keys()),
                values=list(status_data.values()),
                hole=0.65,
                marker_colors=["#6c63ff","#00d4aa","#ff6b6b","#f5c842"],
            ))
            fig.update_layout(**plotly_layout, height=260, showlegend=True,
                              legend=dict(orientation="h", y=-0.1))
            fig.update_traces(textinfo="none")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown("<div style='color:#6b7280;padding:2rem 0;text-align:center'>No scores yet</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# PAGE: CREATE JOB
# ─────────────────────────────────────────────────────────────────────
elif page == "💼 Create Job":
    st.markdown("<h1>Create Job Posting</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6b7280;margin-bottom:2rem'>Define the role and required qualifications</p>", unsafe_allow_html=True)

    with st.form("job_form"):
        c1, c2 = st.columns(2)
        with c1:
            title    = st.text_input("Job Title *", placeholder="e.g. Senior Data Scientist")
            location = st.text_input("Location", placeholder="e.g. Bangalore / Remote")
        with c2:
            exp      = st.selectbox("Experience Required", ["0–1 Years","1–3 Years","3–5 Years","5+ Years"])
            dept     = st.text_input("Department", placeholder="e.g. Engineering")

        skills_input = st.text_area("Required Skills (comma-separated) *",
                                     placeholder="python, machine learning, sql, tensorflow …",
                                     height=80)
        jd = st.text_area("Full Job Description *",
                           placeholder="Describe responsibilities, qualifications, nice-to-haves …",
                           height=220)

        submitted = st.form_submit_button("💾 Save Job Posting", use_container_width=True)

    if submitted:
        if not title.strip():
            st.error("Job title is required.")
        elif not jd.strip():
            st.error("Job description is required.")
        else:
            save_job({
                "title": title.strip(),
                "location": location.strip(),
                "skills": [s.strip().lower() for s in skills_input.split(",") if s.strip()],
                "experience": exp,
                "description": jd.strip(),
                "department": dept.strip(),
            })
            st.success(f"✅ Job **{title}** saved successfully!")

# ─────────────────────────────────────────────────────────────────────
# PAGE: UPLOAD RESUMES
# ─────────────────────────────────────────────────────────────────────
elif page == "📂 Upload Resumes":
    st.markdown("<h1>Upload Resumes</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6b7280;margin-bottom:2rem'>Upload PDF or DOCX files — they will be parsed and stored automatically</p>", unsafe_allow_html=True)

    files = st.file_uploader("Drop resume files here",
                              type=["pdf","docx"],
                              accept_multiple_files=True,
                              label_visibility="collapsed")

    if files:
        progress = st.progress(0, text="Parsing resumes …")
        for i, file in enumerate(files):
            path = os.path.join("uploads", file.name)
            with open(path, "wb") as f:
                f.write(file.getbuffer())
            data = parse_resume(path)
            if data:
                save_candidate(data)
            progress.progress((i + 1) / len(files),
                               text=f"Parsed {i+1}/{len(files)}: {file.name}")
        progress.empty()
        st.success(f"✅ {len(files)} resume(s) uploaded and parsed!")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 👤 Candidate Database")
    cands = load_candidates()
    if cands:
        df = pd.DataFrame(cands)[["name","email","phone","education","experience_years"]]
        df.columns = ["Name","Email","Phone","Education","Exp (yrs)"]
        df.index = range(1, len(df)+1)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No candidates yet. Upload some resumes above.")

# ─────────────────────────────────────────────────────────────────────
# PAGE: CANDIDATE RANKING
# ─────────────────────────────────────────────────────────────────────
elif page == "🏆 Candidate Ranking":
    st.markdown("<h1>Candidate Ranking</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6b7280;margin-bottom:2rem'>AI-powered scoring against a specific job</p>", unsafe_allow_html=True)

    jobs = load_jobs()
    if not jobs:
        st.warning("No jobs found. Create a job first.")
        st.stop()

    job_titles = [j["title"] for j in jobs]
    sel_title  = st.selectbox("Select Job", job_titles)
    job        = next(j for j in jobs if j["title"] == sel_title)

    col_run, col_dl = st.columns([1, 4])
    with col_run:
        run = st.button("⚡ Score All Candidates", use_container_width=True)

    if run:
        cands = load_candidates()
        if not cands:
            st.warning("No candidates uploaded yet.")
        else:
            bar = st.progress(0, text="Scoring …")
            for i, c in enumerate(cands):
                path = os.path.join("uploads", c["filename"])
                text = open(path, "rb").read() if os.path.exists(path) else ""
                # Re-parse to get sections & raw text
                parsed = parse_resume(path) if os.path.exists(path) else {}
                raw    = parsed.get("raw_text","")
                secs   = parsed.get("sections",{})

                skill_score, missing = calculate_skill_match(c["skills"], job["skills"])
                ats   = calculate_ats_score(skill_score, c["email"], c["phone"],
                                             c["education"], c["experience_years"])
                sim   = calculate_similarity(job["description"], raw)
                final = compute_final_score(ats, sim)

                save_score(c["id"], job["id"], {
                    "ats": ats, "similarity": sim,
                    "skill": skill_score, "final": final,
                    "missing": missing
                })
                bar.progress((i+1)/len(cands), text=f"Scored {i+1}/{len(cands)}")
            bar.empty()
            st.success("✅ Scoring complete!")

    # ── Display ranked results ──
    ranked = load_ranked_candidates(job["id"])
    if not ranked:
        st.info("Run scoring above to see ranked candidates.")
    else:
        st.markdown("<hr class='riq-divider'>", unsafe_allow_html=True)
        st.markdown(f"#### 🏅 {len(ranked)} Candidates Ranked · Job: **{job['title']}**")

        # Summary mini-metrics
        scores = [r["Final Score"] for r in ranked]
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1: st.markdown(metric_tile(f"{max(scores)}", "Top Score", "#00d4aa"), unsafe_allow_html=True)
        with mc2: st.markdown(metric_tile(f"{int(sum(scores)/len(scores))}", "Avg Score", "#6c63ff"), unsafe_allow_html=True)
        with mc3: st.markdown(metric_tile(sum(1 for s in scores if s>=70), "Strong (≥70)", "#f5c842"), unsafe_allow_html=True)
        with mc4: st.markdown(metric_tile(len([r for r in ranked if r["Status"]=="Shortlisted"]), "Shortlisted", "#00d4aa"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        for rank, r in enumerate(ranked, 1):
            status_class = r["Status"].replace(" ","-")
            with st.expander(
                f"#{rank}  {r['name']}  ·  Final: {r['Final Score']}  ·  {r['Status']}",
                expanded=(rank == 1)
            ):
                left, right = st.columns([3, 2])
                with left:
                    st.markdown(f"""
                    <div>
                      <div style='font-family:Syne,sans-serif;font-size:1.3rem;font-weight:700'>{r['name']}</div>
                      <div style='color:#6b7280;font-size:0.85rem;margin:4px 0 12px'>
                        📧 {r['email']} &nbsp;·&nbsp; 📱 {r['phone']}
                      </div>
                      <div style='margin-bottom:8px'>
                        🎓 <span style='color:#e8eaf0'>{r['education'] or 'N/A'}</span>
                      </div>
                      <div style='margin-bottom:12px'>
                        🕒 <span style='color:#e8eaf0'>{r['experience_years']} yrs experience</span>
                      </div>
                      <div>{''.join(f"<span class='tag'>{s}</span>" for s in r['skills'][:10])}</div>
                    </div>""", unsafe_allow_html=True)

                with right:
                    # Radar / bar chart for scores
                    fig = go.Figure(go.Bar(
                        x=["ATS","Similarity","Skill Match","Final"],
                        y=[r["ATS"], r["Similarity"], r["Skill Match"], r["Final Score"]],
                        marker_color=["#6c63ff","#00d4aa","#f5c842","#ff6b6b"],
                        text=[r["ATS"], r["Similarity"], r["Skill Match"], r["Final Score"]],
                        textposition="outside",
                    ))
                    fig.update_layout(**plotly_layout, height=200,
                                      yaxis=dict(range=[0,110], showgrid=False, showticklabels=False),
                                      xaxis=dict(showgrid=False))
                    st.plotly_chart(fig, use_container_width=True)

                if r["Missing Skills"]:
                    st.markdown(f"**⚠️ Missing Skills:** `{'`, `'.join(r['Missing Skills'])}`")

                # Status actions
                st.markdown("<div style='margin-top:0.8rem'>", unsafe_allow_html=True)
                sa, sb, sc, _ = st.columns([1,1,1,3])
                if sa.button("✅ Shortlist", key=f"sl_{r['id']}"):
                    update_status(r["id"], job["id"], "Shortlisted")
                    st.rerun()
                if sb.button("❌ Reject", key=f"rj_{r['id']}"):
                    update_status(r["id"], job["id"], "Rejected")
                    st.rerun()
                if sc.button("⏸ Hold", key=f"hd_{r['id']}"):
                    update_status(r["id"], job["id"], "On-Hold")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # Download
        st.markdown("<br>", unsafe_allow_html=True)
        df_export = pd.DataFrame([{
            "Rank": i+1, "Name": r["name"], "Email": r["email"], "Phone": r["phone"],
            "Education": r["education"], "Exp (yrs)": r["experience_years"],
            "ATS": r["ATS"], "Similarity": r["Similarity"],
            "Skill Match": r["Skill Match"], "Final Score": r["Final Score"],
            "Missing Skills": ", ".join(r["Missing Skills"]),
            "Status": r["Status"]
        } for i, r in enumerate(ranked)])

        st.download_button(
            "📥 Export CSV",
            df_export.to_csv(index=False),
            f"ranked_{sel_title.replace(' ','_')}.csv",
            "text/csv",
            use_container_width=False
        )

# ─────────────────────────────────────────────────────────────────────
# PAGE: ANALYTICS
# ─────────────────────────────────────────────────────────────────────
elif page == "📈 Analytics":
    st.markdown("<h1>Analytics</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#6b7280;margin-bottom:2rem'>Insights across your entire hiring pipeline</p>", unsafe_allow_html=True)

    import sqlite3 as _sql
    con = _sql.connect("recruiter.db")
    scores_df = pd.read_sql("""
        SELECT s.*, c.name, c.skills AS cskills, c.experience_years, j.title AS job_title
        FROM scores s
        JOIN candidates c ON c.id=s.candidate_id
        JOIN jobs j ON j.id=s.job_id
    """, con)
    con.close()

    if scores_df.empty:
        st.info("No scoring data yet. Run candidate ranking first.")
        st.stop()

    # Row 1: Score distribution + Status breakdown
    r1c1, r1c2 = st.columns(2)
    with r1c1:
        st.markdown("<div class='riq-card'>", unsafe_allow_html=True)
        st.markdown("#### Score Distribution")
        fig = px.histogram(scores_df, x="final_score", nbins=20,
                           color_discrete_sequence=["#6c63ff"])
        fig.update_layout(**plotly_layout, height=280,
                          xaxis_title="Final Score", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with r1c2:
        st.markdown("<div class='riq-card'>", unsafe_allow_html=True)
        st.markdown("#### Pipeline Status")
        status_counts = scores_df["status"].value_counts().reset_index()
        status_counts.columns = ["Status","Count"]
        fig2 = px.pie(status_counts, names="Status", values="Count", hole=0.6,
                      color_discrete_sequence=["#6c63ff","#00d4aa","#ff6b6b","#f5c842"])
        fig2.update_layout(**plotly_layout, height=280, showlegend=True)
        fig2.update_traces(textinfo="none")
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Row 2: ATS vs Similarity scatter + avg score per job
    r2c1, r2c2 = st.columns(2)
    with r2c1:
        st.markdown("<div class='riq-card'>", unsafe_allow_html=True)
        st.markdown("#### ATS vs Semantic Similarity")
        fig3 = px.scatter(scores_df, x="ats_score", y="similarity_score",
                          color="status", size="final_score",
                          hover_data=["name","job_title"],
                          color_discrete_sequence=["#6c63ff","#00d4aa","#ff6b6b","#f5c842"])
        fig3.update_layout(**plotly_layout, height=300,
                           xaxis_title="ATS Score", yaxis_title="Similarity Score")
        st.plotly_chart(fig3, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with r2c2:
        st.markdown("<div class='riq-card'>", unsafe_allow_html=True)
        st.markdown("#### Avg Score by Job")
        avg_by_job = scores_df.groupby("job_title")["final_score"].mean().reset_index()
        avg_by_job.columns = ["Job","Avg Score"]
        avg_by_job = avg_by_job.sort_values("Avg Score", ascending=True)
        fig4 = px.bar(avg_by_job, x="Avg Score", y="Job", orientation="h",
                      color="Avg Score",
                      color_continuous_scale=["#ff6b6b","#f5c842","#00d4aa"])
        fig4.update_layout(**plotly_layout, height=300,
                           coloraxis_showscale=False, yaxis_title="")
        st.plotly_chart(fig4, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Row 3: Top candidates table
    st.markdown("<div class='riq-card'>", unsafe_allow_html=True)
    st.markdown("#### 🏅 Top 10 Candidates (All Jobs)")
    top10 = scores_df.nlargest(10,"final_score")[
        ["name","job_title","ats_score","similarity_score","skill_score","final_score","status"]
    ].reset_index(drop=True)
    top10.index = range(1, len(top10)+1)
    top10.columns = ["Name","Job","ATS","Similarity","Skill","Final","Status"]
    st.dataframe(top10, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)