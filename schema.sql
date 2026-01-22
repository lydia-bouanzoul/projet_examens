-- ============================================
-- SCHÉMA BASE DE DONNÉES - PLATEFORME EXAMENS
-- ============================================

-- Suppression des tables existantes
DROP TABLE IF EXISTS examens CASCADE;
DROP TABLE IF EXISTS inscriptions CASCADE;
DROP TABLE IF EXISTS modules CASCADE;
DROP TABLE IF EXISTS affectations_surveillance CASCADE;
DROP TABLE IF EXISTS professeurs CASCADE;
DROP TABLE IF EXISTS etudiants CASCADE;
DROP TABLE IF EXISTS lieux_examen CASCADE;
DROP TABLE IF EXISTS formations CASCADE;
DROP TABLE IF EXISTS departements CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- ============================================
-- TABLE: Départements
-- ============================================
CREATE TABLE departements (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL UNIQUE,
    code VARCHAR(10) NOT NULL UNIQUE,
    batiment VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE: Formations
-- ============================================
CREATE TABLE formations (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(200) NOT NULL,
    code VARCHAR(20) NOT NULL UNIQUE,
    dept_id INTEGER NOT NULL REFERENCES departements(id),
    niveau VARCHAR(20) NOT NULL, -- L1, L2, L3, M1, M2
    nb_modules INTEGER DEFAULT 6,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE: Lieux d'examen
-- ============================================
CREATE TABLE lieux_examen (
    id SERIAL PRIMARY KEY,
    nom VARCHAR(100) NOT NULL UNIQUE,
    capacite INTEGER NOT NULL CHECK (capacite > 0),
    capacite_examen INTEGER NOT NULL CHECK (capacite_examen <= capacite),
    type VARCHAR(20) NOT NULL, -- 'amphitheatre', 'salle'
    batiment VARCHAR(50),
    equipements TEXT[], -- projecteur, tableau, ordinateurs, etc.
    disponible BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLE: Étudiants
-- ============================================
CREATE TABLE etudiants (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(20) NOT NULL UNIQUE,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    formation_id INTEGER NOT NULL REFERENCES formations(id),
    promotion INTEGER NOT NULL, -- 2024, 2025, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les recherches
CREATE INDEX idx_etudiants_formation ON etudiants(formation_id);
CREATE INDEX idx_etudiants_promo ON etudiants(promotion);

-- ============================================
-- TABLE: Professeurs
-- ============================================
CREATE TABLE professeurs (
    id SERIAL PRIMARY KEY,
    matricule VARCHAR(20) NOT NULL UNIQUE,
    nom VARCHAR(100) NOT NULL,
    prenom VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE,
    dept_id INTEGER NOT NULL REFERENCES departements(id),
    specialite VARCHAR(200),
    grade VARCHAR(50), -- Professeur, Maître de conférences, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les recherches
CREATE INDEX idx_professeurs_dept ON professeurs(dept_id);

-- ============================================
-- TABLE: Modules
-- ============================================
CREATE TABLE modules (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    nom VARCHAR(200) NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0),
    formation_id INTEGER NOT NULL REFERENCES formations(id),
    semestre INTEGER CHECK (semestre IN (1, 2)),
    duree_examen INTEGER DEFAULT 120, -- en minutes
    pre_requis_id INTEGER REFERENCES modules(id),
    responsable_id INTEGER REFERENCES professeurs(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour optimiser les recherches
CREATE INDEX idx_modules_formation ON modules(formation_id);

-- ============================================
-- TABLE: Inscriptions
-- ============================================
CREATE TABLE inscriptions (
    id SERIAL PRIMARY KEY,
    etudiant_id INTEGER NOT NULL REFERENCES etudiants(id) ON DELETE CASCADE,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    annee_academique VARCHAR(9) NOT NULL, -- 2024-2025
    note NUMERIC(5,2) CHECK (note >= 0 AND note <= 20),
    statut VARCHAR(20) DEFAULT 'inscrit', -- inscrit, valide, ajourne
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(etudiant_id, module_id, annee_academique)
);

-- Index pour optimiser les requêtes
CREATE INDEX idx_inscriptions_etudiant ON inscriptions(etudiant_id);
CREATE INDEX idx_inscriptions_module ON inscriptions(module_id);
CREATE INDEX idx_inscriptions_annee ON inscriptions(annee_academique);

-- ============================================
-- TABLE: Examens
-- ============================================
CREATE TABLE examens (
    id SERIAL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules(id),
    lieu_id INTEGER NOT NULL REFERENCES lieux_examen(id),
    date_examen DATE NOT NULL,
    heure_debut TIME NOT NULL,
    duree_minutes INTEGER NOT NULL CHECK (duree_minutes > 0),
    session VARCHAR(20) NOT NULL, -- 'normale', 'rattrapage'
    annee_academique VARCHAR(9) NOT NULL,
    statut VARCHAR(20) DEFAULT 'planifie', -- planifie, en_cours, termine, annule
    nb_inscrits INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(module_id, session, annee_academique)
);

-- Index pour optimiser les requêtes
CREATE INDEX idx_examens_date ON examens(date_examen);
CREATE INDEX idx_examens_lieu ON examens(lieu_id);
CREATE INDEX idx_examens_module ON examens(module_id);

-- ============================================
-- TABLE: Affectations de surveillance
-- ============================================
CREATE TABLE affectations_surveillance (
    id SERIAL PRIMARY KEY,
    examen_id INTEGER NOT NULL REFERENCES examens(id) ON DELETE CASCADE,
    professeur_id INTEGER NOT NULL REFERENCES professeurs(id),
    role VARCHAR(20) DEFAULT 'surveillant', -- 'responsable', 'surveillant'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(examen_id, professeur_id)
);

-- Index pour optimiser les requêtes
CREATE INDEX idx_surveillance_examen ON affectations_surveillance(examen_id);
CREATE INDEX idx_surveillance_prof ON affectations_surveillance(professeur_id);

-- ============================================
-- TABLE: Utilisateurs (pour l'authentification)
-- ============================================
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL, -- 'doyen', 'admin', 'chef_dept', 'etudiant', 'professeur'
    reference_id INTEGER, -- ID dans la table correspondante
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- VUES UTILES
-- ============================================

-- Vue: Examens avec détails complets
CREATE OR REPLACE VIEW v_examens_details AS
SELECT
    e.id,
    e.date_examen,
    e.heure_debut,
    e.duree_minutes,
    e.session,
    e.statut,
    m.code as module_code,
    m.nom as module_nom,
    f.nom as formation_nom,
    f.niveau,
    d.nom as departement_nom,
    l.nom as lieu_nom,
    l.type as lieu_type,
    l.capacite_examen,
    e.nb_inscrits,
    (l.capacite_examen - e.nb_inscrits) as places_disponibles
FROM examens e
JOIN modules m ON e.module_id = m.id
JOIN formations f ON m.formation_id = f.id
JOIN departements d ON f.dept_id = d.id
JOIN lieux_examen l ON e.lieu_id = l.id;

-- Vue: Charge de surveillance par professeur
CREATE OR REPLACE VIEW v_charge_surveillance AS
SELECT 
    p.id,
    p.nom,
    p.prenom,
    d.nom as departement,
    COUNT(a.id) as nb_surveillances,
    COUNT(DISTINCT e.date_examen) as nb_jours
FROM professeurs p
LEFT JOIN affectations_surveillance a ON p.id = a.professeur_id
LEFT JOIN examens e ON a.examen_id = e.id
JOIN departements d ON p.dept_id = d.id
GROUP BY p.id, p.nom, p.prenom, d.nom;

-- Vue: Planning étudiant
CREATE OR REPLACE VIEW v_planning_etudiant AS
SELECT
    et.id as etudiant_id,
    et.matricule,
    et.nom,
    et.prenom,
    e.date_examen,
    e.heure_debut,
    e.duree_minutes,
    m.nom as module_nom,
    l.nom as lieu_nom,
    l.batiment
FROM etudiants et
JOIN inscriptions i ON et.id = i.etudiant_id
JOIN modules m ON i.module_id = m.id
JOIN examens e ON m.id = e.module_id
JOIN lieux_examen l ON e.lieu_id = l.id
ORDER BY et.id, e.date_examen, e.heure_debut;