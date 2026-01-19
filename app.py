import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Ajouter le répertoire courant au path pour importer optimizer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from optimizer import ExamScheduler
except ImportError:
    st.error("Impossible d'importer optimizer.py. Assurez-vous qu'il est dans le même dossier.")
    ExamScheduler = None

# Configuration de la page
st.set_page_config(
    page_title="Plateforme Examens Universitaires",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration base de données
DB_CONFIG = {
    'dbname': 'examens_db',
    'user': 'postgres',
    'password': '5432',
    'host': 'localhost',
    'port': '5432'
}

# Connexion à la base de données
@st.cache_resource
def get_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f" Erreur de connexion à la base de données: {str(e)}")
        st.info("Vérifiez que PostgreSQL est démarré et que les identifiants sont corrects")
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
        st.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
        st.code(query)
        return pd.DataFrame()

# CSS personnalisé
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .stat-number {
        font-size: 36px;
        font-weight: bold;
    }
    .stat-label {
        font-size: 14px;
        opacity: 0.9;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - Navigation
st.sidebar.title("Navigation")
role = st.sidebar.selectbox(
    "Sélectionner votre rôle",
    ["Doyen/Vice-Doyen", "Administrateur Examens", "Chef de Département", "Étudiant", "Professeur"]
)

st.sidebar.markdown("---")

# Fonction pour afficher les KPIs
def display_kpis():
    """Affiche les indicateurs clés de performance"""
    col1, col2, col3, col4 = st.columns(4)
    
    # KPI 1: Nombre total d'examens
    query1 = "SELECT COUNT(*) as total FROM examens"
    result = execute_query(query1)
    total_examens = result['total'].iloc[0] if not result.empty else 0
    
    col1.metric(" Total Examens", f"{total_examens:,}")
    
    # KPI 2: Taux d'occupation moyen
    query2 = """
    SELECT
        ROUND(
            CAST(
                AVG(nb_inscrits::NUMERIC / l.capacite_examen * 100)
                AS NUMERIC
            ),
            2
        ) AS taux
    FROM examens e
    JOIN lieux_examen l ON e.lieu_id = l.id
"""

    result = execute_query(query2)
    taux_occ = result['taux'].iloc[0] if not result.empty and result['taux'].iloc[0] is not None else 0
    col2.metric("Taux Occupation", f"{taux_occ}%")
    
    # KPI 3: Nombre de conflits
    query3 = """
        SELECT COUNT(*) as conflits
        FROM examens e1
        JOIN examens e2 ON e1.date_examen = e2.date_examen
            AND e1.lieu_id = e2.lieu_id
            AND e1.id < e2.id
            AND e1.heure_debut < e2.heure_debut + (e2.duree_minutes || ' minutes')::interval
            AND e2.heure_debut < e1.heure_debut + (e1.duree_minutes || ' minutes')::interval
    """
    result = execute_query(query3)
    conflits = result['conflits'].iloc[0] if not result.empty else 0
    col3.metric("Conflits Détectés", conflits)
    
    # KPI 4: Professeurs mobilisés
    query4 = "SELECT COUNT(DISTINCT professeur_id) as total FROM affectations_surveillance"
    result = execute_query(query4)
    profs = result['total'].iloc[0] if not result.empty else 0
    col4.metric(" Professeurs", f"{profs:,}")

# ========================================
# VUE DOYEN / VICE-DOYEN
# ========================================
def doyen_view():
    st.title("Tableau de Bord - Direction")
    
    display_kpis()
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Répartition des Examens par Département")
        query = """
            SELECT d.nom as departement, COUNT(e.id) as nb_examens
            FROM examens e
            JOIN modules m ON e.module_id = m.id
            JOIN formations f ON m.formation_id = f.id
            JOIN departements d ON f.dept_id = d.id
            GROUP BY d.nom
            ORDER BY nb_examens DESC
        """
        df = execute_query(query)
        if not df.empty:
            fig = px.bar(df, x='departement', y='nb_examens',
                        color='nb_examens',
                        color_continuous_scale='Viridis')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée disponible. Générez d'abord le planning.")
    
    with col2:
        st.subheader("Occupation des Amphithéâtres")
        query = """
    SELECT
        l.nom,
        COUNT(e.id) AS nb_utilisations,
        ROUND(
            CAST(
                AVG(e.nb_inscrits::NUMERIC / l.capacite_examen * 100)
                AS NUMERIC
            ),
            2
        ) AS taux_moyen
    FROM lieux_examen l
    LEFT JOIN examens e ON l.id = e.lieu_id
    WHERE l.type = 'amphitheatre'
    GROUP BY l.nom, l.capacite_examen
    ORDER BY nb_utilisations DESC
"""

        df = execute_query(query)
        if not df.empty and df['nb_utilisations'].sum() > 0:
            fig = px.bar(df, x='nom', y='taux_moyen',
                        title="Taux d'occupation moyen (%)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée d'occupation. Générez d'abord le planning.")
    
    st.markdown("---")
    
    # Calendrier des examens
    st.subheader("Calendrier Global des Examens")
    query = """
        SELECT date_examen, COUNT(*) as nb_examens
        FROM examens
        GROUP BY date_examen
        ORDER BY date_examen
    """
    df = execute_query(query)
    if not df.empty:
        fig = px.line(df, x='date_examen', y='nb_examens',
                    markers=True,
                    title="Nombre d'examens par jour")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucun examen planifié. Utilisez l'onglet Administrateur pour générer le planning.")
    
    # Statistiques par département
    st.subheader(" Statistiques Détaillées par Département")
    query = """
        SELECT
            d.nom as departement,
            COUNT(DISTINCT e.id) as nb_examens,
            COUNT(DISTINCT a.professeur_id) as nb_profs_mobilises,
            SUM(e.nb_inscrits) as total_etudiants,
            COUNT(DISTINCT e.date_examen) as nb_jours
        FROM departements d
        LEFT JOIN formations f ON d.id = f.dept_id
        LEFT JOIN modules m ON f.id = m.formation_id
        LEFT JOIN examens e ON m.id = e.module_id
        LEFT JOIN affectations_surveillance a ON e.id = a.examen_id
        GROUP BY d.nom
        ORDER BY nb_examens DESC
    """
    df = execute_query(query)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Aucune statistique disponible.")

# ========================================
# VUE ADMINISTRATEUR EXAMENS
# ========================================
def admin_view():
    st.title("Administration des Examens")
    
    tab1, tab2, tab3 = st.tabs(["Génération Automatique", "Détection de Conflits", "Gestion Manuelle"])
    
    with tab1:
        st.subheader("Génération Automatique du Planning")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            annee = st.text_input("Année Académique", "2024-2025")
        with col2:
            session = st.selectbox("Session", ["normale", "rattrapage"])
        with col3:
            start_date = st.date_input("Date de début", datetime.now() + timedelta(days=30))
        
        if st.button("Générer le Planning", type="primary"):
            if ExamScheduler is None:
                st.error("Le module optimizer n'est pas disponible")
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
                    
                    st.success(f"Planning généré en {execution_time:.2f} secondes!")
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Examens planifiés", scheduled)
                    col2.metric("Conflits", len(conflicts))
                    col3.metric("Jours utilisés", stats.get('nb_jours', 0))
                    
                    if conflicts:
                        st.warning(f"{len(conflicts)} modules non planifiés")
                        st.dataframe(pd.DataFrame(conflicts))
                except Exception as e:
                    st.error(f"Erreur lors de la génération: {str(e)}")
    
    with tab2:
        st.subheader(" Détection des Conflits")
        
        # Conflits étudiants (plusieurs examens le même jour)
        st.markdown("#### Étudiants avec plusieurs examens le même jour")
        query = """
            SELECT
                et.matricule,
                et.nom,
                et.prenom,
                e.date_examen,
                COUNT(e.id) as nb_examens_jour
            FROM etudiants et
            JOIN inscriptions i ON et.id = i.etudiant_id
            JOIN examens e ON i.module_id = e.module_id
            GROUP BY et.matricule, et.nom, et.prenom, e.date_examen
            HAVING COUNT(e.id) > 1
            ORDER BY nb_examens_jour DESC
            LIMIT 100
        """
        df = execute_query(query)
        if not df.empty:
            st.error(f"{len(df)} conflits détectés")
            st.dataframe(df, use_container_width=True)
        else:
            st.success("Aucun conflit étudiant détecté")
        
        # Conflits salles
        st.markdown("#### Salles surchargées")
        query = """
            SELECT
                l.nom as salle,
                l.capacite_examen,
                e.nb_inscrits,
                e.date_examen,
                e.heure_debut,
                m.nom as module
            FROM examens e
            JOIN lieux_examen l ON e.lieu_id = l.id
            JOIN modules m ON e.module_id = m.id
            WHERE e.nb_inscrits > l.capacite_examen
            ORDER BY (e.nb_inscrits - l.capacite_examen) DESC
        """
        df = execute_query(query)
        if not df.empty:
            st.error(f" {len(df)} salles surchargées")
            st.dataframe(df, use_container_width=True)
        else:
            st.success("Aucune salle surchargée")
        
        # Professeurs surchargés
        st.markdown("#### Professeurs avec plus de 3 examens/jour")
        query = """
            SELECT
                p.nom,
                p.prenom,
                e.date_examen,
                COUNT(a.id) as nb_surveillances
            FROM professeurs p
            JOIN affectations_surveillance a ON p.id = a.professeur_id
            JOIN examens e ON a.examen_id = e.id
            GROUP BY p.nom, p.prenom, e.date_examen
            HAVING COUNT(a.id) > 3
            ORDER BY nb_surveillances DESC
        """
        df = execute_query(query)
        if not df.empty:
            st.error(f" {len(df)} surcharges détectées")
            st.dataframe(df, use_container_width=True)
        else:
            st.success("Aucune surcharge professeur")
    
    with tab3:
        st.subheader(" Gestion Manuelle")
        
        # Liste des examens
        query = """
            SELECT
                e.id,
                m.code,
                m.nom as module,
                f.nom as formation,
                e.date_examen,
                e.heure_debut,
                l.nom as lieu,
                e.nb_inscrits,
                e.statut
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
            st.info("Aucun examen planifié.")

# ========================================
# VUE CHEF DE DÉPARTEMENT (CORRIGÉE)
# ========================================
def chef_dept_view():
    st.title("Gestion Départementale")
    
    # 1. Sélection du département
    query_depts = "SELECT id, nom FROM departements ORDER BY nom"
    depts = execute_query(query_depts)
    
    if depts.empty:
        st.warning(" Aucun département trouvé. Veuillez d'abord initialiser la base de données.")
        return
    
    dept_selected = st.selectbox("Sélectionner votre département", depts['nom'].tolist())
    dept_id = int(depts[depts['nom'] == dept_selected]['id'].iloc[0])
    
    st.markdown("---")
    
    # 2. Section des Métriques (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    
    # Nombre d'examens planifiés pour le département
    query_examens = """
        SELECT COUNT(DISTINCT e.id) as total
        FROM examens e
        INNER JOIN modules m ON e.module_id = m.id
        INNER JOIN formations f ON m.formation_id = f.id
        WHERE f.dept_id = %s
    """
    res_exams = execute_query(query_examens, params=(dept_id,))
    total_exams = res_exams['total'].iloc[0] if not res_exams.empty else 0
    col1.metric("Examens", total_exams)
    
    # Nombre total d'étudiants inscrits dans les formations du département
    query_etud = """
        SELECT COUNT(DISTINCT et.id) as total
        FROM etudiants et
        INNER JOIN formations f ON et.formation_id = f.id
        WHERE f.dept_id = %s
    """
    res_etud = execute_query(query_etud, params=(dept_id,))
    total_etud = res_etud['total'].iloc[0] if not res_etud.empty else 0
    col2.metric("Étudiants", total_etud)
    
    # Professeurs du département mobilisés (ou profs surveillant des modules du dept)
    query_profs = """
        SELECT COUNT(DISTINCT a.professeur_id) as total
        FROM affectations_surveillance a
        INNER JOIN examens e ON a.examen_id = e.id
        INNER JOIN modules m ON e.module_id = m.id
        INNER JOIN formations f ON m.formation_id = f.id
        WHERE f.dept_id = %s
    """
    res_profs = execute_query(query_profs, params=(dept_id,))
    total_profs = res_profs['total'].iloc[0] if not res_profs.empty else 0
    col3.metric(" Surveillants", total_profs)
    
    # Étendue du calendrier (Nombre de jours d'examens)
    query_jours = """
        SELECT COUNT(DISTINCT e.date_examen) as total
        FROM examens e
        INNER JOIN modules m ON e.module_id = m.id
        INNER JOIN formations f ON m.formation_id = f.id
        WHERE f.dept_id = %s
    """
    res_jours = execute_query(query_jours, params=(dept_id,))
    total_jours = res_jours['total'].iloc[0] if not res_jours.empty else 0
    col4.metric(" Jours", total_jours)
    
    st.markdown("---")
    
    # 3. Liste détaillée des examens par formation
    st.subheader(f" Planning des Examens : {dept_selected}")
    
    query_details = """
        SELECT
            f.nom as "Formation",
            m.nom as "Module",
            e.date_examen as "Date",
            e.heure_debut as "Heure",
            e.duree_minutes as "Durée (min)",
            l.nom as "Lieu",
            e.nb_inscrits as "Inscrits"
        FROM examens e
        INNER JOIN modules m ON e.module_id = m.id
        INNER JOIN formations f ON m.formation_id = f.id
        INNER JOIN lieux_examen l ON e.lieu_id = l.id
        WHERE f.dept_id = %s
        ORDER BY e.date_examen ASC, e.heure_debut ASC
    """
    
    df_details = execute_query(query_details, params=(dept_id,))
    
    if not df_details.empty:
        # Mise en forme de la date pour l'affichage
        df_details['Date'] = pd.to_datetime(df_details['Date']).dt.strftime('%d/%m/%Y')
        
        st.dataframe(df_details, use_container_width=True, hide_index=True)
        
        # Bouton de téléchargement
        csv = df_details.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=" Exporter le planning (CSV)",
            data=csv,
            file_name=f"planning_{dept_selected.replace(' ', '_')}.csv",
            mime="text/csv"
        )
    else:
        st.info(f"ℹ️ Aucun examen n'est encore planifié pour le département {dept_selected}.")

# ========================================
# VUE ÉTUDIANT
# ========================================
def etudiant_view():
    st.title(" Mon Planning d'Examens")
    
    matricule = st.text_input("Entrez votre matricule", "ETU000001")
    
    if st.button(" Rechercher"):
        query = """
            SELECT
                et.nom,
                et.prenom,
                f.nom as formation,
                f.niveau
            FROM etudiants et
            JOIN formations f ON et.formation_id = f.id
            WHERE et.matricule = %s
        """
        etudiant = execute_query(query, params=(matricule,))
        
        if not etudiant.empty:
            st.success(f"Bienvenue {etudiant['prenom'].iloc[0]} {etudiant['nom'].iloc[0]} - {etudiant['formation'].iloc[0]}")
            
            # Planning personnel
            query = """
                SELECT
                    m.nom as module,
                    m.code,
                    e.date_examen,
                    e.heure_debut,
                    e.duree_minutes,
                    l.nom as lieu,
                    l.batiment
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
                st.subheader(" Vos Examens")
                
                for _, row in planning.iterrows():
                    with st.expander(f" {row['date_examen']} - {row['module']}"):
                        col1, col2, col3 = st.columns(3)
                        col1.write(f"**Heure:** {row['heure_debut']}")
                        col2.write(f"**Durée:** {row['duree_minutes']} min")
                        col3.write(f"**Lieu:** {row['lieu']} ({row['batiment']})")
            else:
                st.info("Aucun examen planifié pour le moment")
        else:
            st.error("Matricule introuvable")

# ========================================
# VUE PROFESSEUR
# ========================================
def professeur_view():
    st.title(" Mes Surveillances")
    
    matricule = st.text_input("Entrez votre matricule", "PROF0001")
    
    if st.button(" Rechercher"):
        query = """
            SELECT
                p.nom,
                p.prenom,
                d.nom as departement,
                p.grade
            FROM professeurs p
            JOIN departements d ON p.dept_id = d.id
            WHERE p.matricule = %s
        """
        prof = execute_query(query, params=(matricule,))
        
        if not prof.empty:
            st.success(f"Bienvenue {prof['prenom'].iloc[0]} {prof['nom'].iloc[0]} - {prof['departement'].iloc[0]}")
            
            # Surveillances
            query = """
                SELECT
                    e.date_examen,
                    e.heure_debut,
                    e.duree_minutes,
                    m.nom as module,
                    f.nom as formation,
                    l.nom as lieu,
                    a.role,
                    e.nb_inscrits
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
                st.subheader(f"{len(surveillances)} Surveillances Prévues")
                st.dataframe(surveillances, use_container_width=True)
                
                # Statistiques
                col1, col2 = st.columns(2)
                col1.metric("Total surveillances", len(surveillances))
                col2.metric("Jours concernés", surveillances['date_examen'].nunique())
            else:
                st.info("Aucune surveillance assignée")
        else:
            st.error("Matricule introuvable")

# ========================================
# ROUTAGE PRINCIPAL
# ========================================
def main():
    if role == "Doyen/Vice-Doyen":
        doyen_view()
    elif role == "Administrateur Examens":
        admin_view()
    elif role == "Chef de Département":
        chef_dept_view()
    elif role == "Étudiant":
        etudiant_view()
    elif role == "Professeur":
        professeur_view()

if __name__ == "__main__":
    main()