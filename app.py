import streamlit as st
from datetime import date
from fpdf import FPDF
from utils import (
    get_cotation_cognitif, 
    get_cotation_posture_finale, 
    get_effort_level_global,
    ajuster_niveau_posture_selon_conditions,
    reset_champs_si_requis,
    POIDS_CLASSES, 
    FREQ_CLASSES, 
    effort_table
)
import unicodedata
import re
import yaml
with open("constants.yaml", "r", encoding="utf-8") as f:
    constants = yaml.safe_load(f)

PONDERATIONS = constants["ponderations"]
POSTURES_NIVEAU_4_5 = constants["postures_niveau_4_5"]


st.set_page_config(page_title="Cotation M2E", layout="wide")
st.title("\U0001F4CB Cotation Ergonomique M2E - Vie Série")

reset_champs_si_requis()

# ⚠️ Initialisation ici avant tout appel à .operations
if "operations" not in st.session_state:
    st.session_state.operations = []


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

# ✅ Ne pas utiliser "form_op" ici
if "form_values" not in st.session_state:
    st.session_state.form_values = {
        "nom_op": "",
        "postures": [],
        "freq_posture": 0,
        "poids": 0.0,
        "freq_effort": 0,
        "pondérations": [],
        "N1": False,
        "N2": False,
        "N3": False,
    }

st.header("Ajouter une opération")
with st.form("ajout_operation"):
    nom_op = st.text_input("Nom de l'opération", key="nom_op")
    postures = st.multiselect("Postures contraignantes :", POSTURES_NIVEAU_4_5, key="postures")
    freq_posture = st.number_input("Fréquence horaire postures", min_value=0, key="freq_posture")
    poids = st.number_input("Poids ou effort estimé (kg)", min_value=0.0, key="poids")
    freq_effort = st.number_input("Fréquence horaire effort", min_value=0, key="freq_effort")
    pondérations = st.multiselect("Pondérations :", list(PONDERATIONS.keys()), key="pondérations")
    N1 = st.checkbox("N1 - Travail en aveugle", key="N1")
    N2 = st.checkbox("N2 - Accessibilité difficile", key="N2")
    N3 = st.checkbox("N3 - Ajustement/indexage délicat", key="N3")

    submitted = st.form_submit_button("Ajouter l'opération")

    if submitted:
        if postures and freq_posture == 0:
            st.error("⚠️ Tu as sélectionné des postures contraignantes mais pas de fréquence horaire.")
        elif poids > 0 and freq_effort == 0:
            st.error("⚠️ Tu as indiqué un poids mais pas de fréquence horaire.")
        else:
            coeff = 1.0
            if len([m for m in pondérations if m in ["M3", "M4", "M5", "M6", "M7", "M8", "M9", "M10"]]) >= 2:
                coeff = 2.0
            elif pondérations:
                coeff = max(PONDERATIONS[m] for m in pondérations)
            effort_pondere = poids * coeff
            niveaux = [int(p[1]) for p in postures if p[1].isdigit()]
            niveau_posture = max(niveaux + [3])
            if niveaux.count(4) >= 2:
                niveau_posture = 5

            st.session_state.operations.append({
                "op": nom_op, "postures": postures, "freq_posture": freq_posture,
                "poids": poids, "freq_effort": freq_effort, "effort_pondere": effort_pondere,
                "pondérations": pondérations,
                "niveau_posture": niveau_posture,
                "N1": N1, "N2": N2, "N3": N3
            })
            st.success("✅ Opération ajoutée !")
            st.session_state.reset_required = True
            st.rerun()




st.header("Opérations enregistrées")

LIBELLES_COGNITIF = {
    "N1": "Travail en aveugle",
    "N2": "Accessibilité difficile",
    "N3": "Ajustement/indexage délicat"
}

# EXTRACTION DES EFFORTS PONDÉRÉS
efforts_pondérés = [op["effort_pondere"] for op in st.session_state.operations if op["effort_pondere"] > 0]
frequences_efforts = [op["freq_effort"] for op in st.session_state.operations if op["effort_pondere"] > 0]

# CALCUL DES CHARGES SIGNIFICATIVES
if efforts_pondérés:
    effort_max = max(efforts_pondérés)
    seuil_significatif = 0.75 * effort_max
    efforts_significatifs = [
        (op["effort_pondere"], op["freq_effort"])
        for op in st.session_state.operations
        if op["effort_pondere"] >= seuil_significatif
    ]
    total_freq_significative = sum(freq for _, freq in efforts_significatifs)
    if total_freq_significative > 0:
        effort_moyen_significatif = sum(e * f for e, f in efforts_significatifs) / total_freq_significative
    else:
        effort_moyen_significatif = 0
else:
    effort_max = 0
    seuil_significatif = 0
    effort_moyen_significatif = 0
    total_freq_significative = 0


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
        st.write(f"Effort pondéré : {round(op['effort_pondere'], 2)} kg (Fréquence : {op['freq_effort']} f/h)")
        st.write("Pondérations :", ", ".join(op['pondérations']) or "Aucune")
        contraintes_cognitives = [
    LIBELLES_COGNITIF[k] for k in ["N1", "N2", "N3"] if op.get(k)
]
        st.write("Cognitif :", ", ".join(contraintes_cognitives) or "Aucune")
        st.markdown("---")
    with cols[1]:
        if st.button("❌", key=f"delete_{i}"):
            st.session_state.operations.pop(i)
            st.rerun()

st.header("Facteurs globaux du poste")
high_movement = st.checkbox("Déplacement > 20m/min (Posture = 5, P1 direct)")
rear_stepping = st.checkbox("Piétinement arrière > 30% (Posture = 5)")
lateral_stepping = st.checkbox("Piétinement latéral > 30% (Posture = 4)")
abs_regulation = st.checkbox("Absence de régulation / dépendance")
controle_visuel = st.checkbox("Contrôle visuel / éclairage non adapté")
engagement_rg = st.selectbox("Engagement RG (%)", ["< 95%", "95% - 100%", "> 100%"], index=0)


if st.session_state.operations:
    st.header("\U0001F4CA Cotation globale du poste")
    niveau_posture, freq_par_niveau = get_cotation_posture_finale(st.session_state.operations)

    # Appel ici, avec tous les paramètres prêts
    niveau_posture, posture_explication = ajuster_niveau_posture_selon_conditions(
        operations=st.session_state.operations,
        niveau_posture=niveau_posture,
        high_movement=high_movement,
        rear_stepping=rear_stepping,
        lateral_stepping=lateral_stepping
    )


    effort_moyen = total_effort_x_freq / total_freq_effort if total_freq_effort else 0
    niveau_effort_global = get_effort_level_global(effort_moyen, total_freq_effort)
    niveau_effort_significatif = get_effort_level_global(effort_moyen_significatif, total_freq_significative)
    niveau_effort = max(niveau_effort_global, niveau_effort_significatif)
    
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

    st.write("**Cotation POSTURE :**", freq_par_niveau)
    st.write(f"→ Cotation finale posture : **Niveau {niveau_posture}**")

    if posture_explication:
        st.markdown("**Explication(s) liée(s) à la posture :**")
        for exp in posture_explication:
            st.markdown(f"- {exp}")



    st.write("**Cotation EFFORT :**")
    st.write(f"→ Moyenne pondérée de **tous les efforts pondérés** = {effort_moyen:.2f} kg")
    st.write(f"→ Fréquence totale associée = {total_freq_effort}")

    st.write(f"→ Moyenne pondérée des **charges significatives** (≥ 75% de {effort_max:.2f} kg) = {effort_moyen_significatif:.2f} kg")
    st.write(f"→ Fréquence totale significative = {total_freq_significative}")

    st.write(f"→ Cotation effort retenue = **Niveau {niveau_effort}**")



    st.write("**Cotation COGNITIF :**")
    st.write(f"→ Nombre d'opérations avec contrainte cognitive = {cognitif_count}")

    
    st.write(f"→ Engagement RG = {engagement_rg}")
    st.write(f"→ Contraintes cognitives : {nb_contraintes_cognitives} détectées")

    if contraintes_detectees:
        st.write("→ Autres contraintes cognitives détectées :")
    for c in contraintes_detectees:
        st.markdown(f"- {c}")

    st.write(f"→ Cotation cognitive = {niveau_cognitif}")


    niveaux = [niveau_posture, niveau_effort, niveau_cognitif]
    if high_movement:
        cotation = "P1 (Très contraignant)"
    elif niveaux.count(4) >= 2 or any(n == 5 for n in niveaux):
        cotation = "P1 (Très contraignant)"
    elif niveaux.count(4) == 1:
        cotation = "P2 (Contraignant)"
    else:
        cotation = "P3 (Recommandé)"
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
        
def safe_text(text):
    return text.encode('latin-1', 'replace').decode('latin-1')

if st.button("📄 Télécharger la synthèse en PDF"):

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Synthèse Cotation Ergonomique - Méthode M2E", ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, safe_text(f"Département : {departement}"), ln=True)
    pdf.cell(0, 10, safe_text(f"UET : {uet}"), ln=True)
    pdf.cell(0, 10, safe_text(f"Poste : {poste}"), ln=True)
    pdf.cell(0, 10, safe_text(f"Évaluateur : {evaluateur}"), ln=True)
    pdf.ln(5)

    # Couleur selon cotation finale
    cotation = st.session_state.get("cotation", "P3 (Recommandé)")
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
        pdf.multi_cell(0, 8, safe_text(f"Ajustement(s) : {', '.join(posture_explication)}"))

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
    if total_freq_significative > 0:
        pdf.multi_cell(0, 8, f"Effort pondéré des charges significatives : {effort_moyen_significatif:.2f} kg (>= 75% de {effort_max:.2f} kg)")
        pdf.multi_cell(0, 8, f"Fréquence significative totale : {total_freq_significative}")

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
    contraintes_n123 = [LIBELLES_COGNITIF[k] for k in ["N1", "N2", "N3"] if any(op.get(k) for op in st.session_state.operations)]
    if contraintes_n123:
        contraintes_str = ", ".join(set(contraintes_n123))
        pdf.multi_cell(0, 8, f"Contraintes N1/N2/N3 : {len(contraintes_n123)} ({contraintes_str})")
    else:
        pdf.multi_cell(0, 8, "Contraintes N1/N2/N3 : 0")


    # JUSTIFICATION
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Justification Cotation Finale", ln=True)
    pdf.set_font("Arial", "", 11)

    details_niveaux = {
        "Posture": niveau_posture,
        "Effort": niveau_effort,
        "Cognitif": niveau_cognitif
    }

    niveaux_4 = [k for k, v in details_niveaux.items() if v == 4]
    niveaux_5 = [k for k, v in details_niveaux.items() if v == 5]

    if cotation.startswith("P1"):
        if niveaux_5:
            justification = f"Poste classé en P1 car le critère {', '.join(niveaux_5)} est à 5"
        else:
            justification = f"Poste classé en P1 car au moins deux critères sont à 4 : {', '.join(niveaux_4)}"
    elif cotation.startswith("P2"):
        justification = f"Poste classé en P2 car un seul critère est à 4 : {', '.join(niveaux_4)}"
    else:
        justification = "Poste classé en P3 car tous les critères sont à 3 ou moins"

    pdf.multi_cell(0, 8, justification)


    # OPÉRATIONS
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Détail des opérations enregistrées", ln=True)
    pdf.set_font("Arial", "", 11)

    for idx, op in enumerate(st.session_state.operations, 1):
        pdf.cell(0, 8, safe_text(f"{idx}. {op['op']}"), ln=True)
        if op['postures']:
            pdf.cell(0, 8, safe_text(f"   - Postures : {', '.join(op['postures'])}"), ln=True)
            pdf.cell(0, 8, f"   - Fréquence postures : {op['freq_posture']} f/h", ln=True)
        if op['poids'] > 0:
            pdf.cell(0, 8, f"   - Poids : {op['poids']} kg", ln=True)
            pdf.cell(0, 8, f"   - Effort pondéré : {round(op['effort_pondere'], 2)} kg", ln=True)
        if op['pondérations']:
            pdf.cell(0, 8, safe_text(f"   - Pondérations : {', '.join(op['pondérations'])}"), ln=True)
        contraintes = [LIBELLES_COGNITIF[k] for k in ["N1", "N2", "N3"] if op.get(k)]
        if contraintes:
            pdf.cell(0, 8, f"   - Contraintes cognitives : {', '.join(contraintes)}", ln=True)
        pdf.ln(1)

    

    # Construction initiale du nom de fichier
    nom_fichier = f"M2E_{departement}_{uet}_{poste}_{date_cotation.strftime('%Y-%m-%d')}.pdf".replace(" ", "_")

    # Normalisation Unicode (remplacement des caractères accentués)
    nom_fichier = unicodedata.normalize("NFKD", nom_fichier).encode("ASCII", "ignore").decode("ASCII")

    # Nettoyage des caractères interdits dans un nom de fichier
    nom_fichier = re.sub(r'[\/\\:*?"<>|\x00-\x1F]', '_', nom_fichier)
    nom_fichier = re.sub(r'_+', '_', nom_fichier).strip('_ ')

    pdf.output(nom_fichier)

    with open(nom_fichier, "rb") as f:
        st.download_button("📥 Télécharger le PDF", f, file_name=nom_fichier)

