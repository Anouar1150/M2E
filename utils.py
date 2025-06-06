POSTURE_FREQ_CLASSES = [(0, 10), (11, 100), (101, 400), (401, float('inf'))]

COTATION_POSTURE = [
    [1, 1, 1, 1],
    [1, 2, 2, 2],
    [1, 2, 3, 3],
    [2, 3, 4, 5],
    [4, 4, 5, 5]
]

FREQ_CLASSES = [
    (0, 10),          # ≤ 10
    (10, 30),         # >10 à 30
    (30, 67),         # >30 à 67
    (67, 120),        # >67 à 120
    (120, 190),       # >120 à 190
    (190, 290),       # >190 à 290
    (290, 490),       # >290 à 490
    (490, 720),       # >490 à 720
    (720, float('inf'))  # >721
]
POIDS_CLASSES = [
    (0.0, 1.0),        # ≤ 1
    (1.0, 2.0),        # >1 à 2
    (2.0, 4.0),        # >2 à 4
    (4.0, 6.0),        # >4 à 6
    (6.0, 9.0),        # >6 à 9
    (9.0, 12.0),       # >9 à 12
    (12.0, 15.0),      # >12 à 15
    (15.0, 20.0),      # >15 à 20
    (20.0, 25.0),      # >20 à 25
    (25.0, float('inf'))  # >25
]
effort_table = [
    [1, 1, 1, 2, 2, 3, 3, 4, 4, 5],
    [1, 1, 2, 2, 3, 3, 3, 4, 4, 5],
    [1, 2, 2, 3, 3, 3, 4, 4, 5, 5],
    [1, 2, 3, 3, 3, 4, 4, 5, 5, 5],
    [2, 2, 3, 3, 4, 5, 5, 5, 5, 5],
    [2, 3, 3, 4, 5, 5, 5, 5, 5, 5],
    [3, 3, 4, 5, 5, 5, 5, 5, 5, 5],
    [3, 4, 5, 5, 5, 5, 5, 5, 5, 5],
    [3, 4, 5, 5, 5, 5, 5, 5, 5, 5],
]

def get_cotation_cognitif(nb_contraintes, engagement_rg):
    if engagement_rg == "> 100%":
        return 5
    elif nb_contraintes >= 2:
        return 4
    else:
        return 3

def get_cotation_posture_finale(operations):
    freq_by_level = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    for op in operations:
        freq = op.get("freq_posture", 0)
        niveau = op.get("niveau_posture", 3)  # par défaut 3 si manquant
        freq_by_level[niveau] += freq

    cotation_candidates = []
    for niveau, freq in freq_by_level.items():
        for i, (fmin, fmax) in enumerate(POSTURE_FREQ_CLASSES):
            if fmin < freq <= fmax:
                cotation = COTATION_POSTURE[niveau - 1][i]
                cotation_candidates.append(cotation)
                break

    if cotation_candidates:
        return max(cotation_candidates), freq_by_level
    else:
        return 3, freq_by_level  # valeur par défaut
    
def ajuster_niveau_posture_selon_conditions(operations, niveau_posture, high_movement=False, rear_stepping=False, lateral_stepping=False):
    """Ajuste le niveau de posture global en fonction :
    - des opérations niveau 5 à faible fréquence
    - de l’effort pondéré
    - des facteurs globaux s’ils sont plus contraignants
    """
    posture_explication = []

    freq_niv5 = sum(
        op.get("freq_posture", 0)
        for op in operations
        if op.get("niveau_posture") == 5
    )

    posture5_le6kg = False
    posture5_gt6kg = False

    if freq_niv5 <= 10:
        for op in operations:
            if op.get("niveau_posture") == 5 and op.get("freq_posture", 0) <= 10:
                effort = op.get("effort_pondere", 999)
                if effort <= 6:
                    posture5_le6kg = True
                else:
                    posture5_gt6kg = True

        if posture5_gt6kg:
            niveau_posture = 4
            posture_explication.append("Ajustement posture : posture 5 ≤10 f/h avec effort >6 kg → posture 4")
        elif posture5_le6kg:
            niveau_posture = 3
            posture_explication.append("Ajustement posture : posture 5 ≤10 f/h avec effort ≤6 kg → posture 3")

    # Facteurs globaux : écrasent si plus contraignants
    if high_movement:
        niveau_posture = max(niveau_posture, 5)
        posture_explication.append("Majoration posture : déplacement > 20m/min")
    if rear_stepping:
        niveau_posture = max(niveau_posture, 5)
        posture_explication.append("Majoration posture : piétinement arrière > 30%")
    if lateral_stepping:
        niveau_posture = max(niveau_posture, 4)
        posture_explication.append("Majoration posture : piétinement latéral > 30%")

    return niveau_posture, posture_explication



def get_effort_level_global(poids_moyen, freq):
    if poids_moyen <= 1.0:
        poids_idx = 0
    else:
        poids_idx = next(
            (j for j, (p_min, p_max) in enumerate(POIDS_CLASSES) if p_min < poids_moyen <= p_max),
            len(POIDS_CLASSES) - 1
        )

    if freq <= 10:
        freq_idx = 0
    else:
        freq_idx = next(
            (i for i, (f_min, f_max) in enumerate(FREQ_CLASSES) if f_min < freq <= f_max),
            len(FREQ_CLASSES) - 1
        )

    return effort_table[freq_idx][poids_idx]
