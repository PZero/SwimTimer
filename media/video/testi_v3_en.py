"""English on-screen texts for the video v3 (genera_video_v3.py --lingua en). Italian original -> English.
Texts that are not listed stay unchanged (numbers, names, URLs)."""
EN = {
    # gancio
    'bordo del muro': 'wall edge', 'fotogramma': 'frame', 'TEST IN VASCA': 'POOL TEST', 'Quando tocca': 'When does the hand',
    'davvero': 'really touch', 'il muro?': 'the wall?', '1 fotogramma = 0,02 s': '1 frame = 0.02 s', 'ADESSO?': 'NOW?',
    # la prova
    'LA PROVA · 9 NOVEMBRE': 'THE TEST · 9 NOVEMBER', 'Una camera,': 'One camera,', 'un tag in testa.': 'one tag on the head.',
    'Insta360 X4 sul fondo, vicino al muro': 'Insta360 X4 on the pool floor, next to the wall',
    'di video a 50 fps': 'of video at 50 fps', 'di dati IMU a 214 Hz': 'of IMU data at 214 Hz',
    'memoria piena: fine registrazione': 'memory full: recording stops', '±1000 °/s · 6 assi': '±1000 °/s · 6 axes',
    'Nuotate brevi: partenza, virata, arrivo, pausa.': 'Short swims: start, turn, finish, rest.',
    # sync
    'SINCRONIA': 'SYNC', 'Un colpo sul tag': 'One tap on the tag', '= istante zero.': '= time zero.', '11,4 g': '11.4 g',
    'video 0,82 s  ↔  dati: picco di |a|': 'video 0.82 s  ↔  data: |a| peak',
    't_dati = t_picco + (t_video − 0,82) · k': 't_data = t_peak + (t_video − 0.82) · k',
    # etichette a mano
    'ETICHETTE A MANO': 'HAND LABELS', 'Ogni evento,': 'Every event,', 'fotogramma per fotogramma.': 'frame by frame.',
    'eventi': 'events', 'arrivi A': 'finishes A', 'partenze P': 'starts P', 'virate V': 'turns V', 'bracciate B': 'strokes B',
    'Il riferimento su cui tarare i filtri.': 'The reference used to tune the filters.',
    # filtri
    'FILTRI SUI DATI IMU': 'FILTERS ON THE IMU DATA', 'La testa racconta': 'The head tells', 'cosa succede.': 'what happens.',
    'testa nello spazio (dati reali)': 'head in space (real data)', 'Orientamento della testa': 'Head orientation',
    'filtro di Mahony: giroscopio + gravità': 'Mahony filter: gyroscope + gravity', 'Arrivo': 'Finish',
    'viso al cielo > 0,8 per 0,3 s, dopo almeno 3 s di nuotata': 'face up > 0.8 for 0.3 s, after at least 3 s of swimming',
    'Virata': 'Turn', 'sommità della testa verso il fondo (capriola)': 'top of the head towards the floor (flip turn)',
    'Partenza': 'Start', "prima scivolata 2–12 s dopo l'arrivo": 'first glide 2–12 s after the finish',
    # risultati dei filtri
    'RISULTATI DEI FILTRI': 'FILTER RESULTS', 'Vicini.': 'Close.', 'Non abbastanza.': 'Not close enough.',
    'Arrivi trovati': 'Finishes found', "Errore sull'arrivo": 'Finish timing error', '± 0,88 s': '± 0.88 s',
    'Partenze trovate': 'Starts found', 'Virate trovate': 'Turns found', 'Tempo partenza - arrivo': 'Start-to-finish time',
    '± 1,47 s': '± 1.47 s', 'OBIETTIVO': 'TARGET', '± 0,3 s': '± 0.3 s', 'non raggiunto': 'not reached',
    # colpo di scena
    'COLPO DI SCENA': 'PLOT TWIST', 'Lo stesso arrivo,': 'The same finish,', 'etichettato due volte.': 'labelled twice.',
    'prima: 152,06 s': 'first: 152.06 s', 'verificato: 151,62 s': 'verified: 151.62 s', '−0,44 s': '−0.44 s',
    'Stessi arrivi, due passate: fino a ±0,45 s': 'Same finishes, two passes: up to ±0.45 s',
    'Editor a 30 fps su un video a 50 fps': 'Editor at 30 fps on a 50 fps video',
    'Orologi di camera e tag: deriva dello 0,24%': 'Camera and tag clocks: 0.24% drift',
    'Il problema era': 'The problem was', 'il riferimento.': 'the reference.',
    # opencv
    'OPENCV · 1': 'OPENCV · 1', 'Il video': 'The video', 'si analizza da solo.': 'analyses itself.',
    'differenza dallo sfondo': 'background difference', 'stabilizzata e pulita': 'stabilised and cleaned',
    "Stabilizzazione: l'inquadratura oscilla di qualche pixel (ECC)": 'Stabilisation: the view wobbles by a few pixels (ECC)',
    'Sfondo mediano ogni 10 s: resta solo il corpo': 'Median background every 10 s: only the body remains',
    'Filtro colore pelle contro le bolle della capriola': 'Skin-colour filter against the flip-turn bubbles',
    'Distanza dal muro,': 'Distance from the wall,', '50 volte al secondo.': '50 times per second.',
    'chimografo: tempo × distanza dal muro': 'kymograph: time × distance from the wall',
    'Tocco = la mano raggiunge il bordo del muro.': 'Touch = the hand reaches the wall edge.',
    "Stacco = l'ultimo fotogramma attaccato al muro.": 'Push-off = the last frame still on the wall.',
    'UN ARRIVO, TRE VISTE': 'ONE FINISH, THREE VIEWS', '-0,2 s': '-0.2 s', 'TOCCO': 'TOUCH', '+0,2 s': '+0.2 s',
    'video: distanza dal muro': 'video: distance from the wall', 'IMU: rotazione e viso al cielo': 'IMU: rotation and face up',
    "Ora il riferimento viene dal video, non dall'occhio.": 'Now the reference comes from the video, not from the eye.',
    'RISULTATI OPENCV': 'OPENCV RESULTS', 'Partenze:': 'Starts:', 'al fotogramma.': 'to the frame.', 'Partenze': 'Starts',
    '± 0,14 s': '± 0.14 s', 'Arrivi': 'Finishes', '± 0,4 s': '± 0.4 s', 'Virate': 'Turns', '± 0,45 s': '± 0.45 s',
    'Tipo di evento': 'Event type', '0 errori': '0 errors', 'Dal fondo il muro è una fascia:': 'From the floor the wall is a band:',
    'la prossima volta, camera sul muro.': 'next time, the camera goes on the wall.',
    # decisione
    'LA DECISIONE': 'THE DECISION', 'Metodo,': 'Method,', 'non tentativi.': 'not trial and error.',
    'Dataset con etichette verificate': 'Dataset with verified labels', 'Banco di prova in streaming': 'Streaming test bench',
    'Validazione su sessioni nuove': 'Validation on new sessions', "RETE NEURALE · SOLO PER L'ARRIVO": 'NEURAL NETWORK · FINISH ONLY',
    'Regola-porta': 'Gate rule', 'bracciate finite, vicino al muro': 'strokes over, near the wall', 'Rete 1D': '1D network',
    'int8 sul nRF52840': 'int8 on the nRF52840', 'Tempo del tocco': 'Touch time', "datato all'indietro": 'back-dated',
    'tocco': 'touch', 'notifica': 'notification', '≤ 1,5 s': '≤ 1.5 s', 'Il tempo resta quello del tocco.': 'The time stays the touch time.',
    'Prima la rete batte un metodo classico, poi va sul tag.': 'The network must beat a classic method first, then it goes on the tag.',
    # prossimi passi
    'PROSSIMI PASSI': 'NEXT STEPS', 'Il secondo test, già strutturato.': 'The second test, already structured.',
    'Ripetute da 100 m': '100 m repeats', 'partenza e arrivo davanti alla camera': 'start and finish in front of the camera',
    'Camera attaccata al muro': 'Camera fixed to the wall', 'il muro diventa una linea netta': 'the wall becomes a sharp line',
    'Sync a inizio e fine': 'Sync at start and end', 'la deriva si misura, non si stima': 'the drift is measured, not guessed',
    'Frequenza più bassa': 'Lower sample rate', 'sedute più lunghe nella stessa memoria': 'longer sessions in the same memory',
    'Editor a fotogrammi veri': 'Editor with real frames', 'frecce per spostare ogni etichetta': 'arrow keys move every label',
    # chiusura e miniatura
    'PROGETTO APERTO': 'OPEN PROJECT', 'Dati reali, metodo aperto · prossimo test in arrivo': 'Real data, open method · next test coming',
    'Primo test in vasca': 'First pool test', 'IMU, OpenCV e rete neurale': 'IMU, OpenCV and a neural network', '± 0,02 s?': '± 0.02 s?',
}
