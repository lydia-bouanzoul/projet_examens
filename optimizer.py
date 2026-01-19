import psycopg2
from datetime import datetime, timedelta, time
from collections import defaultdict
import random

class ExamScheduler:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)
        self.cur = self.conn.cursor()
        self.conflicts = []
        
    def clear_existing_schedule(self, annee_academique, session):
        """Supprime les examens existants pour cette session"""
        self.cur.execute("""
            DELETE FROM affectations_surveillance
            WHERE examen_id IN (
                SELECT id FROM examens
                WHERE annee_academique = %s AND session = %s
            )
        """, (annee_academique, session))
        
        self.cur.execute("""
            DELETE FROM examens
            WHERE annee_academique = %s AND session = %s
        """, (annee_academique, session))
        
        self.conn.commit()
        print(f"✓ Planning existant supprimé pour {session} {annee_academique}")
    
    def get_modules_to_schedule(self, annee_academique):
        """Récupère tous les modules à planifier avec nb d'inscrits"""
        self.cur.execute("""
            SELECT
                m.id,
                m.code,
                m.nom,
                m.duree_examen,
                m.formation_id,
                f.dept_id,
                COUNT(i.etudiant_id) as nb_inscrits
            FROM modules m
            JOIN formations f ON m.formation_id = f.id
            JOIN inscriptions i ON m.id = i.module_id
            WHERE i.annee_academique = %s
            GROUP BY m.id, m.code, m.nom, m.duree_examen, m.formation_id, f.dept_id
            ORDER BY nb_inscrits DESC
        """, (annee_academique,))
        
        return self.cur.fetchall()
    
    def get_available_rooms(self):
        """Récupère toutes les salles disponibles"""
        self.cur.execute("""
            SELECT id, nom, capacite_examen, type
            FROM lieux_examen
            WHERE disponible = TRUE
            ORDER BY capacite_examen DESC
        """)
        
        return self.cur.fetchall()
    
    def get_professors_by_department(self, dept_id):
        """Récupère les professeurs d'un département"""
        self.cur.execute("""
            SELECT id, nom, prenom
            FROM professeurs
            WHERE dept_id = %s
        """, (dept_id,))
        
        return self.cur.fetchall()
    
    def get_all_professors(self):
        """Récupère tous les professeurs"""
        self.cur.execute("""
            SELECT id, dept_id
            FROM professeurs
        """)
        
        return self.cur.fetchall()
    
    def check_student_conflict(self, module_id, date_examen, heure_debut):
        """Vérifie si des étudiants ont déjà un examen ce jour"""
        self.cur.execute("""
            SELECT COUNT(DISTINCT i.etudiant_id)
            FROM inscriptions i
            JOIN examens e ON e.module_id IN (
                SELECT module_id
                FROM inscriptions
                WHERE etudiant_id = i.etudiant_id
            )
            WHERE i.module_id = %s
            AND e.date_examen = %s
        """, (module_id, date_examen))
        
        result = self.cur.fetchone()
        return result[0] if result else 0
    
    def check_room_conflict(self, room_id, date_examen, heure_debut, duree):
        """Vérifie si la salle est disponible"""
        heure_fin = (datetime.combine(datetime.today(), heure_debut) +
                    timedelta(minutes=duree)).time()
        
        self.cur.execute("""
            SELECT COUNT(*)
            FROM examens
            WHERE lieu_id = %s
            AND date_examen = %s
            AND (
                (heure_debut <= %s AND
                (heure_debut + (duree_minutes || ' minutes')::interval)::time > %s)
                OR
                (heure_debut < %s AND
                (heure_debut + (duree_minutes || ' minutes')::interval)::time >= %s)
            )
        """, (room_id, date_examen, heure_debut, heure_debut, heure_fin, heure_fin))
        
        result = self.cur.fetchone()
        return result[0] > 0
    
    def count_professor_exams_on_date(self, prof_id, date_examen):
        """Compte le nombre d'examens d'un prof sur une date"""
        self.cur.execute("""
            SELECT COUNT(*)
            FROM affectations_surveillance a
            JOIN examens e ON a.examen_id = e.id
            WHERE a.professeur_id = %s
            AND e.date_examen = %s
        """, (prof_id, date_examen))
        
        result = self.cur.fetchone()
        return result[0] if result else 0
    
    def assign_room(self, nb_inscrits, date_examen, heure_debut, duree):
        """Trouve et assigne une salle appropriée"""
        rooms = self.get_available_rooms()
        
        # Trier par capacité croissante pour optimiser l'utilisation
        suitable_rooms = [r for r in rooms if r[2] >= nb_inscrits]
        suitable_rooms.sort(key=lambda x: x[2])
        
        for room_id, nom, capacite, type_lieu in suitable_rooms:
            if not self.check_room_conflict(room_id, date_examen, heure_debut, duree):
                return room_id
        
        return None
    
    def assign_supervisors(self, examen_id, dept_id, date_examen, nb_required=2):
        """Assigne des surveillants à un examen"""
        # D'abord, essayer les profs du même département
        dept_profs = self.get_professors_by_department(dept_id)
        assigned = []
        
        for prof_id, nom, prenom in dept_profs:
            if len(assigned) >= nb_required:
                break
            
            # Vérifier contrainte max 3 examens par jour
            count = self.count_professor_exams_on_date(prof_id, date_examen)
            if count < 3:
                self.cur.execute("""
                    INSERT INTO affectations_surveillance (examen_id, professeur_id, role)
                    VALUES (%s, %s, %s)
                """, (examen_id, prof_id, 'responsable' if len(assigned) == 0 else 'surveillant'))
                assigned.append(prof_id)
        
        # Si pas assez de profs du département, prendre d'autres
        if len(assigned) < nb_required:
            all_profs = self.get_all_professors()
            random.shuffle(all_profs)
            
            for prof_id, _ in all_profs:
                if prof_id in assigned:
                    continue
                if len(assigned) >= nb_required:
                    break
                
                count = self.count_professor_exams_on_date(prof_id, date_examen)
                if count < 3:
                    self.cur.execute("""
                        INSERT INTO affectations_surveillance (examen_id, professeur_id, role)
                        VALUES (%s, %s, %s)
                    """, (examen_id, prof_id, 'surveillant'))
                    assigned.append(prof_id)
        
        return len(assigned)
    
    def generate_schedule(self, annee_academique="2024-2025", session="normale",
                        start_date=None, max_days=30):
        """Génère le planning complet des examens"""
        print("\n=== GÉNÉRATION DU PLANNING ===\n")
        
        if start_date is None:
            start_date = datetime.now().date() + timedelta(days=30)
        
        # Nettoyer le planning existant
        self.clear_existing_schedule(annee_academique, session)
        
        # Récupérer les modules à planifier
        modules = self.get_modules_to_schedule(annee_academique)
        print(f"{len(modules)} modules à planifier")
        
        # Créneaux horaires disponibles
        time_slots = [
            time(8, 0),
            time(10, 30),
            time(14, 0)
        ]
        
        scheduled = 0
        current_date = start_date
        max_date = start_date + timedelta(days=max_days)
        
        for module_id, code, nom, duree, formation_id, dept_id, nb_inscrits in modules:
            exam_scheduled = False
            attempts = 0
            
            while not exam_scheduled and current_date < max_date and attempts < 100:
                # Essayer chaque créneau horaire
                for heure in time_slots:
                    # Vérifier les conflits étudiants
                    student_conflicts = self.check_student_conflict(module_id, current_date, heure)
                    
                    if student_conflicts > 0:
                        continue
                    
                    # Trouver une salle
                    room_id = self.assign_room(nb_inscrits, current_date, heure, duree)
                    
                    if room_id:
                        # Créer l'examen
                        self.cur.execute("""
                            INSERT INTO examens (module_id, lieu_id, date_examen, heure_debut,
                                            duree_minutes, session, annee_academique, nb_inscrits)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            RETURNING id
                        """, (module_id, room_id, current_date, heure, duree, session,
                            annee_academique, nb_inscrits))
                        
                        examen_id = self.cur.fetchone()[0]
                        
                        # Assigner des surveillants
                        nb_supervisors = self.assign_supervisors(examen_id, dept_id, current_date)
                        
                        if nb_supervisors > 0:
                            self.conn.commit()
                            scheduled += 1
                            exam_scheduled = True
                            
                            if scheduled % 50 == 0:
                                print(f"  ✓ {scheduled}/{len(modules)} examens planifiés")
                            break
                
                if not exam_scheduled:
                    current_date += timedelta(days=1)
                    attempts += 1
            
            if not exam_scheduled:
                self.conflicts.append({
                    'module': nom,
                    'code': code,
                    'nb_inscrits': nb_inscrits,
                    'raison': 'Impossible de trouver un créneau'
                })
        
        self.conn.commit()
        
        print(f"\n {scheduled}/{len(modules)} examens planifiés avec succès")
        if self.conflicts:
            print(f" {len(self.conflicts)} modules non planifiés")
        
        return scheduled, self.conflicts
    
    def get_statistics(self):
        """Calcule des statistiques sur le planning"""
        stats = {}
        
        # Nombre total d'examens
        self.cur.execute("SELECT COUNT(*) FROM examens")
        stats['total_examens'] = self.cur.fetchone()[0]
        
        # Taux d'occupation des salles
        self.cur.execute("""
    SELECT
        ROUND(
            CAST(
                AVG(e.nb_inscrits::NUMERIC / l.capacite_examen * 100)
                AS NUMERIC
            ),
            2
        ) AS taux_occupation
    FROM examens e
    JOIN lieux_examen l ON e.lieu_id = l.id
""")

        result = self.cur.fetchone()
        stats['taux_occupation'] = round(float(result[0]) if result[0] else 0, 2)
        
        # Charge moyenne des professeurs
        self.cur.execute("""
            SELECT AVG(nb_surveillances) as moy_surveillances
            FROM (
                SELECT professeur_id, COUNT(*) as nb_surveillances
                FROM affectations_surveillance
                GROUP BY professeur_id
            ) sub
        """)
        result = self.cur.fetchone()
        stats['moy_surveillances'] = round(float(result[0]) if result[0] else 0, 2)
        
        # Nombre de jours utilisés
        self.cur.execute("""
            SELECT COUNT(DISTINCT date_examen) FROM examens
        """)
        stats['nb_jours'] = self.cur.fetchone()[0]
        
        return stats
    
    def close(self):
        self.cur.close()
        self.conn.close()


# Exemple d'utilisation
if __name__ == "__main__":
    DB_CONFIG = {
        'dbname': 'examens_db',
        'user': 'postgres',
        'password': '5432',
        'host': 'localhost',
        'port': '5432'
    }
    
    scheduler = ExamScheduler(DB_CONFIG)
    
    # Générer le planning
    start = datetime.now()
    scheduled, conflicts = scheduler.generate_schedule(
        annee_academique="2024-2025",
        session="normale",
        start_date=datetime(2025, 6, 1).date(),
        max_days=45
    )
    end = datetime.now()
    
    # Afficher les statistiques
    print("\n=== STATISTIQUES ===")
    stats = scheduler.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print(f"\n  Temps d'exécution: {(end - start).total_seconds():.2f} secondes")
    
    scheduler.close()