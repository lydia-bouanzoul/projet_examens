import psycopg2
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker('fr_FR')

# Configuration de la connexion
DB_CONFIG = {
    'dbname': 'examens_db',
    'user': 'postgres',
    'password': '5432',
    'host': 'localhost',
    'port': '5432'
}

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

def generate_departements(conn):
    """Génère 7 départements"""
    departements = [
        ('Informatique', 'INFO', 'Bâtiment A'),
        ('Mathématiques', 'MATH', 'Bâtiment B'),
        ('Physique', 'PHYS', 'Bâtiment C'),
        ('Chimie', 'CHIM', 'Bâtiment D'),
        ('Biologie', 'BIO', 'Bâtiment E'),
        ('Géologie', 'GEO', 'Bâtiment F'),
        ('Économie', 'ECO', 'Bâtiment G')
    ]
    
    cur = conn.cursor()
    for nom, code, batiment in departements:
        cur.execute("""
            INSERT INTO departements (nom, code, batiment)
            VALUES (%s, %s, %s)
        """, (nom, code, batiment))
    conn.commit()
    cur.close()
    print("✓ 7 départements créés")

def generate_lieux_examen(conn):
    """Génère des salles et amphithéâtres"""
    cur = conn.cursor()
    
    # Amphithéâtres (capacités variables)
    amphis = [
        ('Amphi A', 300, 250, 'amphitheatre', 'Bâtiment Central', ['projecteur', 'sonorisation']),
        ('Amphi B', 250, 200, 'amphitheatre', 'Bâtiment Central', ['projecteur', 'sonorisation']),
        ('Amphi C', 200, 160, 'amphitheatre', 'Bâtiment Central', ['projecteur']),
        ('Amphi D', 180, 144, 'amphitheatre', 'Bâtiment Nord', ['projecteur']),
        ('Amphi E', 150, 120, 'amphitheatre', 'Bâtiment Nord', ['projecteur']),
        ('Amphi F', 120, 96, 'amphitheatre', 'Bâtiment Sud', ['projecteur']),
        ('Amphi G', 100, 80, 'amphitheatre', 'Bâtiment Sud', ['projecteur']),
    ]
    
    for nom, cap, cap_exam, type_lieu, bat, equip in amphis:
        cur.execute("""
            INSERT INTO lieux_examen (nom, capacite, capacite_examen, type, batiment, equipements)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (nom, cap, cap_exam, type_lieu, bat, equip))
    
    # Salles (20 étudiants max en période d'examen)
    batiments = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    for bat in batiments:
        for i in range(1, 16):  # 15 salles par bâtiment = 105 salles
            nom = f'Salle {bat}{i:02d}'
            capacite = random.choice([25, 30, 35, 40])
            cur.execute("""
                INSERT INTO lieux_examen (nom, capacite, capacite_examen, type, batiment, equipements)
                VALUES (%s, %s, 20, 'salle', %s, %s)
            """, (nom, capacite, f'Bâtiment {bat}', ['tableau']))
    
    conn.commit()
    cur.close()
    print("✓ 112 lieux d'examen créés (7 amphis + 105 salles)")

def generate_formations(conn):
    """Génère plus de 200 formations"""
    cur = conn.cursor()
    cur.execute("SELECT id, code FROM departements")
    departements = cur.fetchall()
    
    niveaux = ['L1', 'L2', 'L3', 'M1', 'M2']
    parcours = ['Classique', 'Professionnel', 'Recherche', 'International']
    
    formation_count = 0
    for dept_id, dept_code in departements:
        for niveau in niveaux:
            for parcours_type in parcours:
                if niveau in ['L1', 'L2'] and parcours_type == 'Recherche':
                    continue  # Pas de parcours recherche en L1/L2
                
                nb_modules = random.choice([6, 7, 8, 9])
                code = f"{dept_code}-{niveau}-{parcours_type[:3].upper()}"
                nom = f"{niveau} {dept_code} - {parcours_type}"
                
                cur.execute("""
                    INSERT INTO formations (nom, code, dept_id, niveau, nb_modules)
                    VALUES (%s, %s, %s, %s, %s)
                """, (nom, code, dept_id, niveau, nb_modules))
                formation_count += 1
    
    conn.commit()
    cur.close()
    print(f"✓ {formation_count} formations créées")

def generate_professeurs(conn):
    """Génère des professeurs (environ 500)"""
    cur = conn.cursor()
    cur.execute("SELECT id FROM departements")
    dept_ids = [row[0] for row in cur.fetchall()]
    
    grades = ['Professeur', 'Maître de Conférences A', 'Maître de Conférences B', 'Maître Assistant A']
    specialites = ['Théorique', 'Appliquée', 'Expérimentale', 'Modélisation', 'Analyse']
    
    for i in range(500):
        dept_id = random.choice(dept_ids)
        matricule = f"PROF{i+1:04d}"
        nom = fake.last_name()
        prenom = fake.first_name()
        email = f"{prenom.lower()}.{nom.lower()}.{matricule.lower()}@univ.dz"
        grade = random.choice(grades)
        specialite = random.choice(specialites)
        
        cur.execute("""
            INSERT INTO professeurs (matricule, nom, prenom, email, dept_id, grade, specialite)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (matricule, nom, prenom, email, dept_id, grade, specialite))
    
    conn.commit()
    cur.close()
    print("✓ 500 professeurs créés")

def generate_modules(conn):
    """Génère des modules pour chaque formation"""
    cur = conn.cursor()
    cur.execute("SELECT id, nb_modules FROM formations")
    formations = cur.fetchall()
    
    cur.execute("SELECT id FROM professeurs")
    prof_ids = [row[0] for row in cur.fetchall()]
    
    module_names = [
        'Analyse', 'Algèbre', 'Probabilités', 'Statistiques', 'Physique',
        'Chimie', 'Informatique', 'Programmation', 'Base de données', 'Réseaux',
        'Systèmes', 'Architecture', 'Électronique', 'Optique', 'Mécanique',
        'Thermodynamique', 'Géométrie', 'Topologie', 'Économétrie', 'Microéconomie'
    ]
    
    module_count = 0
    for formation_id, nb_modules in formations:
        for i in range(nb_modules):
            code = f"MOD-{formation_id}-{i+1:02d}"
            nom = f"{random.choice(module_names)} {i+1}"
            credits = random.choice([4, 5, 6])
            semestre = random.choice([1, 2])
            duree = random.choice([90, 120, 150, 180])
            responsable = random.choice(prof_ids)
            
            cur.execute("""
                INSERT INTO modules (code, nom, credits, formation_id, semestre, duree_examen, responsable_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (code, nom, credits, formation_id, semestre, duree, responsable))
            module_count += 1
    
    conn.commit()
    cur.close()
    print(f"✓ {module_count} modules créés")

def generate_etudiants(conn):
    """Génère 13000 étudiants"""
    cur = conn.cursor()
    cur.execute("SELECT id FROM formations")
    formation_ids = [row[0] for row in cur.fetchall()]
    
    promotions = [2020, 2021, 2022, 2023, 2024, 2025]
    
    for i in range(13000):
        matricule = f"ETU{i+1:06d}"
        nom = fake.last_name()
        prenom = fake.first_name()
        email = f"{prenom.lower()}.{nom.lower()}{i}@etu.univ.dz"
        formation_id = random.choice(formation_ids)
        promotion = random.choice(promotions)
        
        cur.execute("""
            INSERT INTO etudiants (matricule, nom, prenom, email, formation_id, promotion)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (matricule, nom, prenom, email, formation_id, promotion))
        
        if (i + 1) % 1000 == 0:
            conn.commit()
            print(f"  {i+1}/13000 étudiants créés...")
    
    conn.commit()
    cur.close()
    print("✓ 13000 étudiants créés")

def generate_inscriptions(conn):
    """Génère environ 130000 inscriptions"""
    cur = conn.cursor()
    
    # Récupérer tous les étudiants avec leur formation
    cur.execute("SELECT id, formation_id FROM etudiants")
    etudiants = cur.fetchall()
    
    annee = "2024-2025"
    inscription_count = 0
    
    for etudiant_id, formation_id in etudiants:
        # Récupérer les modules de cette formation
        cur.execute("SELECT id FROM modules WHERE formation_id = %s", (formation_id,))
        modules = cur.fetchall()
        
        # Inscrire l'étudiant à tous les modules de sa formation
        for (module_id,) in modules:
            cur.execute("""
                INSERT INTO inscriptions (etudiant_id, module_id, annee_academique)
                VALUES (%s, %s, %s)
            """, (etudiant_id, module_id, annee))
            inscription_count += 1
        
        if (inscription_count) % 10000 == 0:
            conn.commit()
            print(f"  {inscription_count} inscriptions créées...")
    
    conn.commit()
    cur.close()
    print(f"✓ {inscription_count} inscriptions créées")

def main():
    print("=== GÉNÉRATION DES DONNÉES ===\n")
    
    try:
        conn = connect_db()
        print("✓ Connexion à la base de données établie\n")
        
        generate_departements(conn)
        generate_lieux_examen(conn)
        generate_formations(conn)
        generate_professeurs(conn)
        generate_modules(conn)
        generate_etudiants(conn)
        generate_inscriptions(conn)
        
        conn.close()
        print("\n=== GÉNÉRATION TERMINÉE AVEC SUCCÈS ===")
        
    except Exception as e:
        print(f"\n❌ Erreur: {e}")

if __name__ == "__main__":
    main()