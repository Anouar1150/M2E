import streamlit as st
from datetime import date
from fpdf import FPDF

st.set_page_config(page_title="Cotation M2E", layout="wide")
st.title("\U0001F4CB Cotation Ergonomique M2E - Vie Série")


# Affichage des informations du poste dans la barre latérale
st.sidebar.header("📌 Identification du poste")
departement = st.sidebar.selectbox("Département", ["Logistique", "Tôlerie", "Peinture", "Montage", "Qualité"])
uet = st.sidebar.text_input("UET")
poste = st.sidebar.text_input("Nom du poste")
date_cotation = st.sidebar.date_input("Date de la cotation", value=date.today())
evaluateur = st.sidebar.text_input("Nom de l’évaluateur")

# Afficher les informations sélectionnées en haut de page
st.write("## Informations sur le poste en cours de cotation :")
st.markdown(f"- **Département** : {departement}")
st.markdown(f"- **UET** : {uet}")
st.markdown(f"- **Poste** : {poste}")
st.markdown(f"- **Date de cotation** : {date_cotation.strftime('%d/%m/%Y')}")
st.markdown(f"- **Évaluateur** : {evaluateur}")


# Pondérations avec explications
PONDERATIONS = {
    "M1 - Retournement facilité avec appui (0.5)": 0.5,
    "M2 - Poussée ou traction assistée (0.7)": 0.7,
    "M3 - Retournement sans appui (1.5)": 1.5,
    "M4 - Bras écartés >1m ou tendus >50cm (1.5)": 1.5,
    "M5 - Maintien précis 1 main prolongé (1.5)": 1.5,
    "M6 - Charge instable ou CG déporté (1.5)": 1.5,
    "M7 - Port >6kg hors fenêtre ergonomique (1.5)": 1.5,
    "M8 - Prise bout des doigts ou 1 main >6kg (1.5)": 1.5,
    "M9 - Port >6kg avec marches (1.5)": 1.5,
    "M10 - Port >6kg avec déplacement >5m (1.5)": 1.5,
    "M11 - Effort en abduction (bras écartés) (2.0)": 2.0,
    "M12 - Soulèvement en position assise (2.0)": 2.0
}

POSTURES_NIVEAU_4_5 = [
    # TRONC : FLEXION
    "A4 - Dos penché sans appui ou avec charge / durée (30°-60°)",
    "A5 - Dos penché sans appui ou avec charge / durée (>60°)",
    "B4 - Dos penché avec appui stable, courte durée et effort <2kg (30°-60°)",
    "B5 - Dos penché avec appui stable, courte durée et effort <2kg (>60°)",

    # TRONC : INCLINAISON
    "C4 - Inclinaison latérale du tronc (30°-60°)",
    "C5 - Inclinaison latérale du tronc > 60°",

    # TRONC : ROTATION
    "D4 - Rotation tronc modérée (45°-90°) ou inclinaison avec maintien",
    "D5 - Rotation tronc importante ≥ 90° ou forte inclinaison prolongée",

    # TÊTE
    "E4 - Inclinaison tête >30° ou rotation 45°-90° (durée > 5s)",
    "E5 - Rotation tête ≥ 90° ou forte extension arrière",

    # BRAS / MAINS
    "F4 - Bras levés / tendus avec charge ou durée > 5s",
    "F5 - Bras très hauts ou en élévation prolongée (> 45°)",

    # BRAS (léger)
    "G4 - Bras brièvement levés sans charge (≤ 5s, ≤ 2kg)",

    # POIGNET / MAIN
    "H4 - Poignet très fléchi ou en extension > 60°",

    # GENOUX / ACCROUPISSEMENT / PIÉTINEMENT
    "K4 - Accroupi ≤ 5s, obstacle < 500mm ou piétinement latéral > 30%",
    "K5 - Accroupi > 5s ou piétinement arrière > 30% ou déplacement rapide"
]

FREQ_CLASSES = [(0, 10), (11, 30), (31, 67), (68, 120), (121, 190), (191, 290), (291, 490), (491, 720), (721, float('inf'))]
POIDS_CLASSES = [(1.01, 2), (2.01, 4), (4.01, 6), (6.01, 9), (9.01, 12), (12.01, 15), (15.01, 20), (20.01, 25), (25.01, float('inf'))]
GRILLE_EFFORT = [
    [1,1,2,2,3,4,4,5,5],
    [1,2,2,3,3,3,4,4,5],
    [2,2,3,3,3,4,4,5,5],
    [2,3,3,3,4,4,5,5,5],
    [2,3,3,4,5,5,5,5,5],
    [3,3,4,5,5,5,5,5,5],
    [3,4,5,5,5,5,5,5,5],
    [4,5,5,5,5,5,5,5,5],
    [4,5,5,5,5,5,5,5,5]
]

COTATION_POSTURE = [
    [1, 1, 1, 1],
    [1, 2, 2, 2],
    [1, 2, 3, 3],
    [2, 3, 4, 5],
    [4, 4, 5, 5]
]
POSTURE_FREQ_CLASSES = [(0, 10), (11, 100), (101, 400), (401, float('inf'))]

def get_cotation_cognitif(nb_contraintes, engagement_rg):
    if engagement_rg == "> 100%":
        return 5
    elif nb_contraintes >= 2:
        return 4
    else:
        return 3

def get_posture_level(max_level, total_freq):
    for i, (f_min, f_max) in enumerate(POSTURE_FREQ_CLASSES):
        if f_min <= total_freq <= f_max:
            return COTATION_POSTURE[max_level - 1][i]
    return 5

def get_effort_level_global(poids_moyen, freq):
    if poids_moyen <= 1:
        return 3
    freq_idx = next((i for i, (f_min, f_max) in enumerate(FREQ_CLASSES) if f_min <= freq <= f_max), len(FREQ_CLASSES)-1)
    poids_idx = next((j for j, (p_min, p_max) in enumerate(POIDS_CLASSES) if p_min <= poids_moyen <= p_max), len(POIDS_CLASSES)-1)
    return GRILLE_EFFORT[freq_idx][poids_idx]

if "operations" not in st.session_state:
    st.session_state.operations = []

st.header("Ajouter une opération")
with st.form("form_op"):
    nom_op = st.text_input("Nom de l'opération")
    postures = st.multiselect("Postures contraignantes :", POSTURES_NIVEAU_4_5)
    freq_posture = st.number_input("Fréquence horaire postures", min_value=0)
    poids = st.number_input("Poids ou effort estimé (kg)", min_value=0.0)
    freq_effort = st.number_input("Fréquence horaire effort", min_value=0)
    pondérations = st.multiselect("Pondérations :", list(PONDERATIONS.keys()))
    N1 = st.checkbox("N1 - Travail en aveugle")
    N2 = st.checkbox("N2 - Accessibilité difficile")
    N3 = st.checkbox("N3 - Ajustement/indexage délicat")
    submitted = st.form_submit_button("Ajouter l'opération")
    if submitted:
        # Vérifications conditionnelles
        if postures and freq_posture == 0:
            st.error("⚠️ Tu as sélectionné des postures contraignantes mais pas de fréquence horaire. Merci de la renseigner.")
        elif poids > 0 and freq_effort == 0:
            st.error("⚠️ Tu as indiqué un poids ou effort mais pas de fréquence horaire. Merci de la renseigner.")
        else:
            coeff = 1.0
            if len([m for m in pondérations if m in ["M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]]) >= 2:
                coeff = 2.0
            elif pondérations:
                coeff = max(PONDERATIONS[m] for m in pondérations)
            effort_pondere = poids * coeff
            niveau_posture = max([int(p[1]) for p in postures if p[1].isdigit()] + [3])
            st.session_state.operations.append({
                "op": nom_op, "postures": postures, "freq_posture": freq_posture,
                "poids": poids, "freq_effort": freq_effort, "effort_pondere": effort_pondere,
                "pondérations": pondérations,
                "niveau_posture": niveau_posture,
                "N1": N1, "N2": N2, "N3": N3
            })
            st.success("✅ Opération ajoutée !")


st.header("Opérations enregistrées")

LIBELLES_COGNITIF = {
    "N1": "Travail en aveugle",
    "N2": "Accessibilité difficile",
    "N3": "Ajustement/indexage délicat"
}

total_freq_posture = 0
max_posture_level = 0
total_effort_x_freq = 0
total_freq_effort = 0
cognitif_count = 0

for i, op in enumerate(st.session_state.operations):
    # MISE À JOUR DES VARIABLES DE CALCUL
    total_freq_posture += op['freq_posture']
    max_posture_level = max(max_posture_level, op['niveau_posture'])
    total_effort_x_freq += op['effort_pondere'] * op['freq_effort']
    total_freq_effort += op['freq_effort']
    if op["N1"] or op["N2"] or op["N3"]:
        cognitif_count += 1

    # AFFICHAGE
    cols = st.columns([6, 1])
    with cols[0]:
        st.write(f"**{i+1}. {op['op']}**")
        st.write("Postures :", ", ".join(op['postures']) or "Aucune")
        st.write("Fréquence posture :", op['freq_posture'])
        st.write("Effort pondéré :", round(op['effort_pondere'], 2), "kg")
        st.write("Pondérations :", ", ".join(op['pondérations']) or "Aucune")
        contraintes_cognitives = [
    LIBELLES_COGNITIF[k] for k in ["N1", "N2", "N3"] if op.get(k)
]
        st.write("Cognitif :", ", ".join(contraintes_cognitives) or "Aucune")
        st.markdown("---")
    with cols[1]:
        if st.button("❌", key=f"delete_{i}"):
            st.session_state.operations.pop(i)
            st.experimental_rerun()


        

st.header("Facteurs globaux du poste")
high_movement = st.checkbox("Déplacement > 20m/min (Posture = 5, P1 direct)")
rear_stepping = st.checkbox("Piétinement arrière > 30% (Posture = 5)")
lateral_stepping = st.checkbox("Piétinement latéral > 30% (Posture = 4)")
abs_regulation = st.checkbox("Absence de régulation / dépendance")
controle_visuel = st.checkbox("Contrôle visuel / éclairage non adapté")
engagement_rg = st.selectbox("Engagement RG (%)", ["< 95%", "95% - 100%", "> 100%"], index=0)


if st.session_state.operations:
    st.header("\U0001F4CA Cotation globale du poste")
    niveau_posture = get_posture_level(max_posture_level, total_freq_posture)
    posture_explication = []
    if high_movement or rear_stepping:
        niveau_posture = 5
        posture_explication.append("Forcé par facteur global déplacement/piétinement arrière")
    elif niveau_posture < 4 and lateral_stepping:
        niveau_posture = 4
        posture_explication.append("Forcé par facteur global piétinement latéral")

    effort_moyen = total_effort_x_freq / total_freq_effort if total_freq_effort else 0
    niveau_effort = get_effort_level_global(effort_moyen, total_freq_effort)
    
    nb_contraintes_cognitives = cognitif_count  # N1, N2, N3 déjà comptés

    contraintes_detectees = []

    if abs_regulation:
        nb_contraintes_cognitives += 1
        contraintes_detectees.append("Absence de régulation / dépendance")
    if controle_visuel:
        nb_contraintes_cognitives += 1
        contraintes_detectees.append("Contrôle visuel / éclairage non adapté")
    if engagement_rg == "95% - 100%":
            nb_contraintes_cognitives += 1


    
    niveau_cognitif = get_cotation_cognitif(nb_contraintes_cognitives, engagement_rg)

    st.write("**Détail des calculs posture :**")
    st.write(f"→ Niveau maximal observé dans les opérations = {max_posture_level}")
    st.write(f"→ Fréquence totale des postures = {total_freq_posture}")
    st.write(f"→ Cotation initiale calculée selon grille = {get_posture_level(max_posture_level, total_freq_posture)}")
    if posture_explication:
        st.write(f"→ Ajustée à {niveau_posture} à cause de : {', '.join(posture_explication)}")
    else:
        st.write(f"→ Cotation finale posture = {niveau_posture}")


    st.write("**Détail des calculs effort :**")
    st.write(f"→ Somme (poids pondéré × fréquence) = {total_effort_x_freq:.2f}")
    st.write(f"→ Somme des fréquences = {total_freq_effort}")
    st.write(f"→ Poids moyen pondéré = {effort_moyen:.2f} kg → Niveau {niveau_effort}")

    st.write("**Détail des calculs cognitif :**")
    st.write(f"→ Nombre d'opérations avec contrainte cognitive = {cognitif_count}")

    
    st.write("**Détail des calculs cognitifs :**")
    st.write(f"→ Engagement RG = {engagement_rg}")
    st.write(f"→ Contraintes cognitives : {nb_contraintes_cognitives} détectées")

    if contraintes_detectees:
        st.write("→ Autres contraintes cognitives détectées :")
    for c in contraintes_detectees:
        st.markdown(f"- {c}")

    st.write(f"→ Cotation cognitive = {niveau_cognitif}")


    niveaux = [niveau_posture, niveau_effort, niveau_cognitif]
    if high_movement:
        cotation = "P1 (Rouge)"
    elif niveaux.count(4) >= 2 or any(n == 5 for n in niveaux):
        cotation = "P1 (Rouge)"
    elif niveaux.count(4) == 1:
        cotation = "P2 (Jaune)"
    else:
        cotation = "P3 (Vert)"
    st.success(f"➡️ Cotation finale : **{cotation}**")
    st.session_state['cotation'] = cotation
else:
     st.info("Ajoute au moins une opération pour calculer la cotation globale.")
    
    


class PDF(FPDF):
    def niveau_color(self, niveau):
        if niveau == 5:
            return (255, 102, 102)  # Rouge
        elif niveau == 4:
            return (255, 255, 153)  # Jaune
        else:
            return (255, 255, 255)  # Blanc (pas de fond)
if st.button("📄 Télécharger la synthèse en PDF"):

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Synthèse Cotation Ergonomique - Méthode M2E", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Département : {departement}", ln=True)
    pdf.cell(0, 10, f"UET : {uet}", ln=True)
    pdf.cell(0, 10, f"Poste : {poste}", ln=True)
    pdf.cell(0, 10, f"Date de cotation : {date_cotation.strftime('%d/%m/%Y')}", ln=True)
    pdf.cell(0, 10, f"Évaluateur : {evaluateur}", ln=True)
    pdf.ln(5)

    # Couleur selon cotation finale
    cotation = st.session_state.get("cotation", "P3 (Vert)")
    if cotation.startswith("P1"):
        pdf.set_fill_color(255, 102, 102)
    elif cotation.startswith("P2"):
        pdf.set_fill_color(255, 255, 153)
    else:
        pdf.set_fill_color(153, 255, 153)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Cotation finale : {cotation}", ln=True, fill=True)
    pdf.set_fill_color(255, 255, 255)

    # POSTURE
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Posture", ln=True)
    pdf.set_font("Arial", "", 11)
    r, g, b = pdf.niveau_color(niveau_posture)
    pdf.set_fill_color(r, g, b)
    pdf.cell(0, 8, f"Niveau posture = {niveau_posture}", ln=True, fill=(niveau_posture >= 4))
    pdf.set_fill_color(255, 255, 255)
    pdf.multi_cell(0, 8, f"Niveau max observé : {max_posture_level}")
    pdf.multi_cell(0, 8, f"Fréquence cumulée : {total_freq_posture}")
    if posture_explication:
        pdf.multi_cell(0, 8, f"Ajustement(s) : {', '.join(posture_explication)}")

    # EFFORT
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Effort", ln=True)
    pdf.set_font("Arial", "", 11)
    r, g, b = pdf.niveau_color(niveau_effort)
    pdf.set_fill_color(r, g, b)
    pdf.cell(0, 8, f"Niveau effort = {niveau_effort}", ln=True, fill=(niveau_effort >= 4))
    pdf.set_fill_color(255, 255, 255)
    pdf.multi_cell(0, 8, f"Poids moyen pondéré : {effort_moyen:.2f} kg")
    pdf.multi_cell(0, 8, f"Fréquence cumulée : {total_freq_effort}")

    # COGNITIF
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Cognitif", ln=True)
    pdf.set_font("Arial", "", 11)
    r, g, b = pdf.niveau_color(niveau_cognitif)
    pdf.set_fill_color(r, g, b)
    pdf.cell(0, 8, f"Niveau cognitif = {niveau_cognitif}", ln=True, fill=(niveau_cognitif >= 4))
    pdf.set_fill_color(255, 255, 255)
    pdf.multi_cell(0, 8, f"Engagement RG : {engagement_rg}")
    if contraintes_detectees:
        pdf.multi_cell(0, 8, "Contraintes globales : " + ", ".join(contraintes_detectees))
    pdf.multi_cell(0, 8, f"Contraintes N1/N2/N3 : {cognitif_count}")

    # JUSTIFICATION
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Justification Cotation Finale", ln=True)
    pdf.set_font("Arial", "", 11)
    if cotation.startswith("P1"):
        justification = "Poste classé en P1 car au moins 2 critères sont à 4 ou 1 critère à 5"
    elif cotation.startswith("P2"):
        justification = "Poste classé en P2 car un seul critère est à 4"
    else:
        justification = "Poste classé en P3 car tous les critères sont à 3 ou moins"
    pdf.multi_cell(0, 8, justification)

    # OPÉRATIONS
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Détail des opérations enregistrées", ln=True)
    pdf.set_font("Arial", "", 11)

    for idx, op in enumerate(st.session_state.operations, 1):
        pdf.cell(0, 8, f"{idx}. {op['op']}", ln=True)
        if op['postures']:
            pdf.cell(0, 8, f"   - Postures : {', '.join(op['postures'])}", ln=True)
            pdf.cell(0, 8, f"   - Fréquence postures : {op['freq_posture']} f/h", ln=True)
        if op['poids'] > 0:
            pdf.cell(0, 8, f"   - Poids : {op['poids']} kg", ln=True)
            pdf.cell(0, 8, f"   - Effort pondéré : {round(op['effort_pondere'], 2)} kg", ln=True)
        if op['pondérations']:
            pdf.cell(0, 8, f"   - Pondérations : {', '.join(op['pondérations'])}", ln=True)
        contraintes = [LIBELLES_COGNITIF[k] for k in ["N1", "N2", "N3"] if op.get(k)]
        if contraintes:
            pdf.cell(0, 8, f"   - Contraintes cognitives : {', '.join(contraintes)}", ln=True)
        pdf.ln(1)

    #Formatage de la date en AAAA-MM-JJ
    nom_fichier = f"M2E_{departement}_{uet}_{poste}_{date_cotation.strftime('%Y-%m-%d')}.pdf".replace(" ", "_")

    pdf.output(nom_fichier)
    with open(nom_fichier, "rb") as f:
        st.download_button("📥 Télécharger le PDF", f, file_name=nom_fichier)


