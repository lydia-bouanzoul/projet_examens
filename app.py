import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from optimizer import ExamScheduler
except ImportError:
    st.error("Impossible d'importer optimizer.py")
    ExamScheduler = None

st.set_page_config(
    page_title="ExamPro - Gestion des Examens",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_CONFIG = {
        'dbname': 'examens_db',
        'user': 'postgres',
        'password': '5432',
        'host': 'localhost',
        'port': '5432'
    }
# FONCTIONS DE BASE DE DONNÉES
@st.cache_resource
def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Erreur de connexion: {str(e)}")
        return None

def execute_query(query, params=None):
    """Exécute une requête SQL et retourne un DataFrame"""
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()
    try:
        df = pd.read_sql_query(query, conn, params=params)
        return df
    except Exception as e:
        st.error(f" Erreur SQL: {str(e)}")
        return pd.DataFrame()

def hash_password(password):
    """Hash le mot de passe"""
    return hashlib.sha256(password.encode()).hexdigest()

def init_users_table():
    """Initialise la table users si elle n'existe pas"""
    conn = get_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(30) NOT NULL,
                    reference_id INTEGER,
                    nom VARCHAR(100),
                    prenom VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            users_demo = [
                ('admin', 'admin123', 'admin', None, 'Admin', 'Système'),
                ('doyen', 'doyen123', 'doyen', None, 'Benali', 'Ahmed'),
                ('chef_info', 'chef123', 'chef_dept', 1, 'Mammeri', 'Fatima'),
                ('prof001', 'prof123', 'professeur', None, 'Kadi', 'Youcef'),
                ('etu001', 'etu123', 'etudiant', None, 'Benyahia', 'Amina')
            ]
            
            for username, password, role, ref_id, nom, prenom in users_demo:
                cur.execute("""
                    INSERT INTO users (username, password_hash, role, reference_id, nom, prenom)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (username, hash_password(password), role, ref_id, nom, prenom))
            
            conn.commit()
            cur.close()
        except Exception as e:
            pass

def load_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Variables */
    :root {
        --primary: #6366f1;
        --secondary: #8b5cf6;
        --accent: #ec4899;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
    }
    
    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        animation: slideDown 0.5s ease-out;
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        opacity: 0.95;
    }
    
    /* Cards statistiques */
    .stat-card {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border-left: 4px solid var(--primary);
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 24px rgba(0,0,0,0.15);
    }
    
    .stat-card h3 {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stat-card .stat-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        line-height: 1;
    }
    
    /* Page de connexion */
    .login-container {
        max-width: 450px;
        margin: 5rem auto;
        padding: 3rem;
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.15);
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .login-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin: 0;
    }
    
    .login-header p {
        color: #64748b;
        margin-top: 0.5rem;
        font-size: 0.95rem;
    }
    
    /* Boutons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        width: 100%;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%);
    }
    
    [data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Inputs */
    .stTextInput>div>div>input {
        border-radius: 10px;
        border: 2px solid #e2e8f0;
        padding: 0.75rem;
        transition: all 0.3s;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #6366f1;
        box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
    }
    
    /* Selectbox */
    .stSelectbox>div>div {
        border-radius: 10px;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Dataframe */
    .dataframe {
        border-radius: 10px !important;
        overflow: hidden;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
        background-color: #f1f5f9;
        font-weight: 600;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        border-radius: 10px;
        background-color: #f8fafc;
        font-weight: 600;
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid;
    }
    
    /* Progress bar */
    .stProgress > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    </style>
    """, unsafe_allow_html=True)
# GESTION DE SESSION
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user' not in st.session_state:
    st.session_state.user = None

# AUTHENTIFICATION
def authenticate_user(username, password):
    """Authentifie un utilisateur"""
    query = """
        SELECT id, username, role, reference_id, nom, prenom
        FROM users
        WHERE username = %s AND password_hash = %s
    """
    result = execute_query(query, params=(username, hash_password(password)))
    
    if not result.empty:
        st.session_state.logged_in = True
        st.session_state.user = {
            'id': result['id'].iloc[0],
            'username': result['username'].iloc[0],
            'role': result['role'].iloc[0],
            'reference_id': result['reference_id'].iloc[0] if pd.notna(result['reference_id'].iloc[0]) else None,
            'nom': result['nom'].iloc[0],
            'prenom': result['prenom'].iloc[0]
        }
        return True
    return False

def logout():
    """Déconnexion"""
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

def login_page():
    """Page de connexion moderne"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="login-container fade-in">
            <div class="login-header">
                <h1>🎓ExamPro</h1>
                <p>Plateforme de Gestion des Examens</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("Connexion")
        
        username = st.text_input(" Nom d'utilisateur", placeholder="Votre identifiant")
        password = st.text_input("Mot de passe", type="password", placeholder="Votre mot de passe")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("Se connecter", use_container_width=True):
                if authenticate_user(username, password):
                    st.success(" Connexion réussie!")
                    st.rerun()
                else:
                    st.error(" Identifiants incorrects")
        
        with col_btn2:
            if st.button("Aide", use_container_width=True):
                st.info("Contactez l'administrateur")
        
        # Comptes démo
        with st.expander("Comptes de démonstration"):
            st.markdown("""
            | Rôle | Username | Password |
            |------|----------|----------|
            | Admin | `admin` | `admin123` |
            | Doyen | `doyen` | `doyen123` |
            | Chef Dept | `chef_info` | `chef123` |
            | Professeur | `prof001` | `prof123` |
            | Étudiant | `etu001` | `etu123` |
            """)

def display_header():
    """Affiche le header moderne"""
    user = st.session_state.user
    role_labels = {
        'admin': 'Administrateur',
        'doyen': 'Doyen',
        'chef_dept': 'Chef de Département',
        'professeur': 'Professeur',
        'etudiant': 'Étudiant'
    }
    
    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1>ExamPro</h1>
                <p>Bienvenue, {user['prenom']} {user['nom']} • {role_labels.get(user['role'], 'Utilisateur')}</p>
            </div>
            <div style="text-align: right;">
                <p style="margin: 0; font-size: 1.1rem; font-weight: 600;">{datetime.now().strftime('%d/%m/%Y')}</p>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{datetime.now().strftime('%H:%M')}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_kpis():
    """Affiche les KPIs"""
    col1, col2, col3, col4 = st.columns(4)
    
    queries = [
        ("SELECT COUNT(*) FROM examens", "Total Examens"),
        ("SELECT ROUND(CAST(AVG(nb_inscrits::NUMERIC / l.capacite_examen * 100) AS NUMERIC), 2) FROM examens e JOIN lieux_examen l ON e.lieu_id = l.id", " Taux Occupation"),
        ("SELECT COUNT(*) FROM examens e1 JOIN examens e2 ON e1.date_examen = e2.date_examen AND e1.lieu_id = e2.lieu_id AND e1.id < e2.id", " Conflits"),
        ("SELECT COUNT(DISTINCT professeur_id) FROM affectations_surveillance", " Professeurs")
    ]
    
    for i, (query, label) in enumerate(queries):
        result = execute_query(query)
        if not result.empty:
            value = result.iloc[0, 0] if result.iloc[0, 0] is not None else 0
            if "Taux" in label:
                value_str = f"{value}%"
            else:
                value_str = f"{int(value):,}"
        else:
            value_str = "0"
        
        [col1, col2, col3, col4][i].markdown(f"""
        <div class="stat-card">
            <h3>{label}</h3>
            <p class="stat-value">{value_str}</p>
        </div>
        """, unsafe_allow_html=True)

def admin_view():
    """Vue Administrateur"""
    st.markdown("## Administration des Examens")
    
    tab1, tab2, tab3 = st.tabs([" Génération", " Conflits", "Gestion"])
    
    with tab1:
        st.markdown("### Génération Automatique du Planning")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            annee = st.text_input(" Année", "2024-2025")
        with col2:
            session = st.selectbox("Session", ["normale", "rattrapage"])
        with col3:
            start_date = st.date_input("Date début", datetime.now() + timedelta(days=30))
        
        if st.button(" Générer", type="primary", use_container_width=True):
            if ExamScheduler is None:
                st.error(" Module optimizer indisponible")
                return
            
            with st.spinner("Génération en cours..."):
                try:
                    scheduler = ExamScheduler(DB_CONFIG)
                    start_time = datetime.now()
                    
                    scheduled, conflicts = scheduler.generate_schedule(
                        annee_academique=annee,
                        session=session,
                        start_date=start_date,
                        max_days=45
                    )
                    
                    end_time = datetime.now()
                    execution_time = (end_time - start_time).total_seconds()
                    
                    stats = scheduler.get_statistics()
                    scheduler.close()
                    
                    st.balloons()
                    st.success(f"Planning généré en {execution_time:.2f}s!")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Planifiés", scheduled)
                    col2.metric("Conflits", len(conflicts))
                    col3.metric("Jours", stats.get('nb_jours', 0))
                    
                    if conflicts:
                        st.warning(f"{len(conflicts)} modules non planifiés")
                        st.dataframe(pd.DataFrame(conflicts), use_container_width=True)
                except Exception as e:
                    st.error(f" {str(e)}")
    
    with tab2:
        st.markdown("### Détection des Conflits")
        
        # Conflits étudiants
        st.markdown("#### Étudiants (plusieurs examens/jour)")
        query = """
            SELECT et.matricule, et.nom, et.prenom, e.date_examen, COUNT(e.id) as nb
            FROM etudiants et
            JOIN inscriptions i ON et.id = i.etudiant_id
            JOIN examens e ON i.module_id = e.module_id
            GROUP BY et.matricule, et.nom, et.prenom, e.date_examen
            HAVING COUNT(e.id) > 1
            LIMIT 50
        """
        df = execute_query(query)
        if not df.empty:
            st.error(f" {len(df)} conflits")
            st.dataframe(df, use_container_width=True)
        else:
            st.success("Aucun conflit")
        
        # Salles surchargées
        st.markdown("#### Salles surchargées")
        query = """
            SELECT l.nom, l.capacite_examen, e.nb_inscrits, e.date_examen, m.nom as module
            FROM examens e
            JOIN lieux_examen l ON e.lieu_id = l.id
            JOIN modules m ON e.module_id = m.id
            WHERE e.nb_inscrits > l.capacite_examen
            LIMIT 50
        """
        df = execute_query(query)
        if not df.empty:
            st.error(f"{len(df)} salles")
            st.dataframe(df, use_container_width=True)
        else:
            st.success(" Aucune salle surchargée")
    
    with tab3:
        st.markdown("### Liste des Examens")
        query = """
            SELECT e.id, m.code, m.nom as module, f.nom as formation, e.date_examen,
                e.heure_debut, l.nom as lieu, e.nb_inscrits
            FROM examens e
            JOIN modules m ON e.module_id = m.id
            JOIN formations f ON m.formation_id = f.id
            JOIN lieux_examen l ON e.lieu_id = l.id
            ORDER BY e.date_examen, e.heure_debut
            LIMIT 100
        """
        df = execute_query(query)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Aucun examen")

def doyen_view():
    """Vue Doyen"""
    st.markdown("## Tableau de Bord Stratégique")
    
    display_kpis()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Examens par Département")
        query = """
            SELECT d.nom, COUNT(e.id) as nb
            FROM examens e
            JOIN modules m ON e.module_id = m.id
            JOIN formations f ON m.formation_id = f.id
            JOIN departements d ON f.dept_id = d.id
            GROUP BY d.nom
            ORDER BY nb DESC
        """
        df = execute_query(query)
        if not df.empty:
            fig = px.bar(df, x='nom', y='nb', color='nb', color_continuous_scale='Viridis')
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Nombre")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Générez le planning")
    
    with col2:
        st.markdown("### Occupation Amphithéâtres")
        query = """
            SELECT l.nom, ROUND(CAST(AVG(e.nb_inscrits::NUMERIC / l.capacite_examen * 100) AS NUMERIC), 2) as taux
            FROM lieux_examen l
            LEFT JOIN examens e ON l.id = e.lieu_id
            WHERE l.type = 'amphitheatre'
            GROUP BY l.nom
            HAVING COUNT(e.id) > 0
        """
        df = execute_query(query)
        if not df.empty:
            fig = px.bar(df, x='nom', y='taux', color='taux', color_continuous_scale='RdYlGn')
            fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="Taux (%)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée")

def chef_dept_view():
    """Vue Chef de Département"""
    st.markdown("## Gestion Départementale")
    
    query_depts = "SELECT id, nom FROM departements ORDER BY nom"
    depts = execute_query(query_depts)
    
    if depts.empty:
        st.warning("Aucun département")
        return
    
    dept_selected = st.selectbox("Département", depts['nom'].tolist())
    dept_id = int(depts[depts['nom'] == dept_selected]['id'].iloc[0])
    
    col1, col2, col3, col4 = st.columns(4)
    stats_queries = [
        ("SELECT COUNT(DISTINCT e.id) FROM examens e JOIN modules m ON e.module_id = m.id JOIN formations f ON m.formation_id = f.id WHERE f.dept_id = %s", " Examens"),
        ("SELECT COUNT(DISTINCT et.id) FROM etudiants et JOIN formations f ON et.formation_id = f.id WHERE f.dept_id = %s", " Étudiants"),
        ("SELECT COUNT(DISTINCT a.professeur_id) FROM affectations_surveillance a JOIN examens e ON a.examen_id = e.id JOIN modules m ON e.module_id = m.id JOIN formations f ON m.formation_id = f.id WHERE f.dept_id = %s", " Profs"),
        ("SELECT COUNT(DISTINCT e.date_examen) FROM examens e JOIN modules m ON e.module_id = m.id JOIN formations f ON m.formation_id = f.id WHERE f.dept_id = %s", " Jours")
    ]
    
    for i, (query, label) in enumerate(stats_queries):
        result = execute_query(query, params=(dept_id,))
        value = result.iloc[0, 0] if not result.empty else 0
        [col1, col2, col3, col4][i].metric(label, f"{value:,}")
    
    st.markdown("---")
    st.markdown(f"### Planning - {dept_selected}")
    
    query = """
        SELECT f.nom as "Formation", m.nom as "Module", e.date_examen as "Date",
            e.heure_debut as "Heure", e.duree_minutes as "Durée", 
            l.nom as "Lieu", e.nb_inscrits as "Inscrits"
        FROM examens e
        JOIN modules m ON e.module_id = m.id
        JOIN formations f ON m.formation_id = f.id
        JOIN lieux_examen l ON e.lieu_id = l.id
        WHERE f.dept_id = %s
        ORDER BY e.date_examen, e.heure_debut
    """
    df = execute_query(query, params=(dept_id,))
    
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d/%m/%Y')
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Télécharger", csv, f"planning_{dept_selected}.csv", "text/csv")
    else:
        st.info("Aucun examen")

def etudiant_view():
    """Vue Étudiant"""
    st.markdown("## Mon Planning")
    
    matricule = st.text_input("Matricule", "ETU000001")
    
    if st.button("Rechercher", type="primary"):
        query = """
            SELECT et.nom, et.prenom, f.nom as formation, f.niveau
            FROM etudiants et
            JOIN formations f ON et.formation_id = f.id
            WHERE et.matricule = %s
        """
        etudiant = execute_query(query, params=(matricule,))
        
        if not etudiant.empty:
            st.success(f" {etudiant['prenom'].iloc[0]} {etudiant['nom'].iloc[0]} - {etudiant['formation'].iloc[0]}")
            
            query = """
                SELECT m.nom, m.code, e.date_examen, e.heure_debut, e.duree_minutes, l.nom as lieu, l.batiment
                FROM etudiants et
                JOIN inscriptions i ON et.id = i.etudiant_id
                JOIN modules m ON i.module_id = m.id
                JOIN examens e ON m.id = e.module_id
                JOIN lieux_examen l ON e.lieu_id = l.id
                WHERE et.matricule = %s
                ORDER BY e.date_examen, e.heure_debut
            """
            planning = execute_query(query, params=(matricule,))
            
            if not planning.empty:
                st.markdown("### Vos Examens")
                for _, row in planning.iterrows():
                    with st.expander(f"{row['date_examen']} - {row['nom']}"):
                        col1, col2, col3 = st.columns(3)
                        col1.write(f"**Heure:** {row['heure_debut']}")
                        col2.write(f"**Durée:** {row['duree_minutes']} min")
                        col3.write(f"**Lieu:** {row['lieu']} ({row['batiment']})")
            else:
                st.info("Aucun examen planifié")
        else:
            st.error(" Matricule introuvable")

def professeur_view():
    """Vue Professeur"""
    st.markdown("## Mes Surveillances")
    
    matricule = st.text_input("Matricule", "PROF0001")
    
    if st.button("Rechercher", type="primary"):
        query = """
            SELECT p.nom, p.prenom, d.nom as departement, p.grade
            FROM professeurs p
            JOIN departements d ON p.dept_id = d.id
            WHERE p.matricule = %s
        """
        prof = execute_query(query, params=(matricule,))
        
        if not prof.empty:
            st.success(f" {prof['prenom'].iloc[0]} {prof['nom'].iloc[0]} - {prof['departement'].iloc[0]}")
            
            query = """
                SELECT e.date_examen, e.heure_debut, e.duree_minutes, m.nom as module,
                    f.nom as formation, l.nom as lieu, a.role, e.nb_inscrits
                FROM professeurs p
                JOIN affectations_surveillance a ON p.id = a.professeur_id
                JOIN examens e ON a.examen_id = e.id
                JOIN modules m ON e.module_id = m.id
                JOIN formations f ON m.formation_id = f.id
                JOIN lieux_examen l ON e.lieu_id = l.id
                WHERE p.matricule = %s
                ORDER BY e.date_examen, e.heure_debut
            """
            surveillances = execute_query(query, params=(matricule,))
            
            if not surveillances.empty:
                st.markdown(f"### {len(surveillances)} Surveillances")
                st.dataframe(surveillances, use_container_width=True)
                
                col1, col2 = st.columns(2)
                col1.metric("Total", len(surveillances))
                col2.metric("Jours", surveillances['date_examen'].nunique())
            else:
                st.info("Aucune surveillance")
        else:
            st.error(" Matricule introuvable")


def main():
    """Application principale"""
    load_css()
    init_users_table()
    
    if not st.session_state.logged_in:
        login_page()
    else:
        with st.sidebar:
            st.markdown(f"""
            <div style="text-align: center; padding: 1.5rem; background: rgba(255,255,255,0.1); border-radius: 15px; margin-bottom: 2rem;">
                <div style="width: 80px; height: 80px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; margin: 0 auto 1rem auto; display: flex; align-items: center; justify-content: center; font-size: 2rem;">
                    👤
                </div>
                <h3 style="color: white; margin: 0; font-size: 1.2rem;">{st.session_state.user['prenom']} {st.session_state.user['nom']}</h3>
                <p style="color: rgba(255,255,255,0.7); margin: 0.5rem 0 0 0; font-size: 0.9rem;">@{st.session_state.user['username']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### Navigation")
            
            role = st.session_state.user['role']
            
            if role == 'admin':
                page = st.radio("", ["Dashboard", "Administration"], label_visibility="collapsed")
            elif role == 'doyen':
                page = st.radio("", ["Dashboard"], label_visibility="collapsed")
            elif role == 'chef_dept':
                page = st.radio("", ["Mon Département"], label_visibility="collapsed")
            elif role == 'professeur':
                page = st.radio("", ["Mes Surveillances"], label_visibility="collapsed")
            else:
                page = st.radio("", ["Mon Planning"], label_visibility="collapsed")
            
            st.markdown("---")
            
            st.markdown("### Paramètres")
            if st.button("Déconnexion", use_container_width=True):
                logout()
            
            st.markdown("---")
            st.markdown("""
            <div style="text-align: center; color: rgba(255,255,255,0.5); font-size: 0.8rem;">
                <p>ExamPro v1.0</p>
                <p>© 2025 Université</p>
            </div>
            """, unsafe_allow_html=True)
        display_header()
        
        if role == 'admin':
            if "Administration" in page:
                admin_view()
            else:
                display_kpis()
                doyen_view()
        elif role == 'doyen':
            doyen_view()
        elif role == 'chef_dept':
            chef_dept_view()
        elif role == 'professeur':
            professeur_view()
        else:
            etudiant_view()

if __name__ == "__main__":
    main()
