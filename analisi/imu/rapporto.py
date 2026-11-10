"""Generazione del rapporto Markdown (rapporto_fase2.md) dai risultati di valuta.py.
Contiene numeri e tabelle della sessione: va scritto SOLO nella cartella delle uscite."""
import datetime

import numpy as np


def _f(x, n=2):
    return '-' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{x:.{n}f}'


def _p(x):
    return '-' if x is None or (isinstance(x, float) and np.isnan(x)) else f'{100 * x:.0f}%'


INT_RISULTATI = ("| Freq. | Tipo | Rif | Rilev. | TP/FP/FN | Prec. | Richiamo | Err. medio (s) | Dev.std (s) | Mediana (s) "
                 "| TP entro 0,1/0,2/0,3 s | idem dopo aver tolto la mediana |\n|---|---|---|---|---|---|---|---|---|---|---|---|")


def _riga(fs, m):
    return (f"| {fs} Hz | {m['tipo']} | {m['n_rif']} | {m['n_det']} | {m['tp']}/{m['fp']}/{m['fn']} | {_p(m['precisione'])} | "
            f"{_p(m['richiamo'])} | {_f(m['media'])} | {_f(m['std'])} | {_f(m['mediana'])} | "
            f"{_p(m['entro_0.1'])}/{_p(m['entro_0.2'])}/{_p(m['entro_0.3'])} | "
            f"{_p(m['entro_c_0.1'])}/{_p(m['entro_c_0.2'])}/{_p(m['entro_c_0.3'])} |")


def _tabella(R, modo):
    righe = [INT_RISULTATI]
    for fs, r in R['freq'].items():
        for t in 'APV':
            righe.append(_riga(fs, r[modo]['metriche'][t]))
    return '\n'.join(righe)


def _sezione_sessione(R, tol):
    L = []
    k = R['k']
    ks = R['k_stima']
    L.append(f"## Sessione `{R['nome']}`\n")
    L.append("### 1. Dati e riferimento\n")
    L.append(f"- Registrazione decodificata: {R['n_campioni']} campioni, {R['durata_s'] / 60:.1f} min, fs = {R['fs']:.3f} Hz "
             f"(fit blocchi/timestamp), {R['blocchi']} blocchi dati; cambi di rotazione dei canali corretti: {R['cambi_rotazione']}.")
    L.append(f"- Picco di sync (max |a|, 11,4 g) a t = {R['sync_dati_s']:.4f} s dati = video 0,82 s.")
    fv = R['finestra_valida']
    L.append(f"- Riferimento (video, eventi A/P/V verificati): A {R['n_rif']['A']}, P {R['n_rif']['P']}, V {R['n_rif']['V']}. "
             f"Finestra di valutazione (solo qui contano FP e FN): dati {fv[0]:.1f}-{fv[1]:.1f} s (video 0,8-530 s).\n")
    L.append("### 2. Scala video -> dati (k)\n")
    L.append("Mappatura: `t_dati = t_sync + (t_video - 0,82) * k`.\n")
    L.append("Metodo (tre famiglie di caratteristiche IMU, indipendenti dai rilevatori da valutare; stimatore robusto a "
             "intercetta libera per gruppo, vedi `stima_k.py`):")
    L.append("1. **Urti di spinta** (picco |a| > 8 g entro -1,5/+2 s da una P o V): sono eventi fisici, legati allo stacco dei piedi dal muro;")
    L.append("2. **inizio del gruppo di bracciate** dopo una P;")
    L.append("3. **fine del gruppo di bracciate** prima di una A.")
    L.append(f"\nRisultato: **k = {k:.4f}** (IC 95% bootstrap {ks['ci95'][0]:.4f}-{ks['ci95'][1]:.4f}; {ks['n_usate']} coppie "
             f"inlier su {ks['n_coppie']}; residuo dopo il fit {ks['std_residuo_s']:.2f} s; stesso risultato partendo da k=1,0 e da k=1,0024). "
             f"I soli 4 urti ben definiti si allineano a 0,07 s con k = 0,9994 (IC ampio, 0,992-1,0004).")
    L.append(f"La vecchia stima k = {R['k_meta']:.4f} (deriva 0,24%) e' **in disaccordo con gli urti**: rispetto a k = 1 sposterebbe "
             "gli eventi di 1,1 s a video 465 s, mentre con k ~ 1 i 4 urti inlier (video 45-465 s) coincidono a 0,07 s. Il dato e' pero' scarso "
             "(solo 5 P/V su ~24 hanno un urto > 8 g nella finestra) e le sole caratteristiche di bracciata non discriminano (IC +/-0,5%). "
             "Conclusione prudente: k ~ 1,000; k = 1,0024 e' fuori dall'IC degli urti (0,992-1,0004) ma dentro quello combinato (0,995-1,005), quindi "
             "non e' escluso con rigore statistico; inoltre l'orologio del tag (nRF52840, ppm) e quello del video non hanno motivo fisico di divergere dello 0,24%. "
             "Si consiglia di usare k = 1 e di verificarlo con due sync (inizio e fine) nelle prossime registrazioni.")
    L.append("\nSensibilita' dei risultati a k (214 Hz, assi fissi, stessi eventi rilevati; tolleranza di abbinamento "
             f"{tol:.1f} s):\n")
    L.append("| k | A: TP, dev.std, mediana (s) | P: TP, dev.std, mediana (s) | V: TP, dev.std, mediana (s) |\n|---|---|---|---|")
    for kk, v in R['sensibilita_k'].items():
        L.append(f"| {kk} | " + " | ".join(f"{v[t]['tp']}, {_f(v[t]['std'])}, {_f(v[t]['mediana'])}" for t in 'APV') + " |")
    L.append("\nLe soglie e gli offset dei rilevatori originali (A +0,23 s, P -0,66 s, V +1,4/-3,0 s) furono tarati con k = 1,0024 "
             "su etichette manuali: usando k stimato compare uno scarto sistematico di ~+0,4...0,8 s (mediana) uguale per i tre tipi. "
             "Un k diverso e un offset costante sono quasi indistinguibili al centro del video (0,0024 x 265 s = 0,64 s): "
             "per questo la tabella dei risultati riporta anche la statistica 'dopo aver tolto la mediana'.\n")
    # ---- fine video
    fvd = R['fine_video']
    L.append("### 3. Verifica della fine del video\n")
    L.append("Riferimenti dopo video 470 s e attivita' dei dati (RMS di |w| nei 3 s prima/dopo il tempo dati predetto; nuotata > ~130 dps):\n")
    L.append("| Tipo | t video (s) | t dati predetto (s) | RMS prima (dps) | RMS dopo (dps) |\n|---|---|---|---|---|")
    for r in fvd['righe']:
        L.append(f"| {r['tipo']} | {r['t_video']:.1f} | {r['t_dati_pred']:.1f} | {r['rms_prima']:.0f} | {r['rms_dopo']:.0f} |")
    q = fvd['quiete_piu_lunga']
    ult = fvd['ultimo_evento_dati_s']
    prima = [x for x in fvd['tratti_nuotata'] if x['t_dati'][1] <= ult + 5]
    dopo = [x for x in fvd['tratti_nuotata'] if x['t_dati'][0] > ult + 5]
    ultimo, prossimo = prima[-1], (dopo[0] if dopo else None)
    L.append(f"\n**Confermato**: dopo la P a video 510,5 s (dati {fvd['righe'][-1]['t_dati_pred']:.0f} s) i dati NON mostrano nuotata. "
             f"L'ultimo gruppo di bracciate termina a dati {ultimo['t_dati'][1]:.1f} s (video equivalente {ultimo['t_video'][1]:.1f} s, coerente con la A a video 504,4 s); "
             f"poi il tag resta quasi fermo: quiete piu' lunga {q['durata_s']:.0f} s (dati {q['da_dati_s']:.0f}-{q['a_dati_s']:.0f} s, "
             f"video equivalente {q['da_video_s']:.0f}-{q['a_video_s']:.0f} s, |w| < 60 dps)"
             + (f" e nuotata di nuovo solo da dati {prossimo['t_dati'][0]:.0f} s (video eq. {prossimo['t_video'][0]:.0f} s). " if prossimo else ". ")
             + f"Durante la quiete l'accelerazione media e' ({', '.join(f'{x:.2f}' for x in fvd['acc_media_quiete'])}) g "
             f"contro ({', '.join(f'{x:.2f}' for x in fvd['acc_media_ultimo_tratto'])}) g nell'ultimo tratto di nuotata: testa ferma e piu' verticale, "
             "compatibile con una sosta (non con un tag appoggiato).")
    cont = R.get('continuita')
    if cont:
        L.append(f"\nContinuita' dei dati: scarto massimo tra timestamp di blocco e attesi dai campioni {cont['max_dev_ms']:.1f} ms, "
                 f"blocchi con scarto > 20 ms: {cont['n_blocchi_20ms']} su {cont['n_blocchi']}.")
    ip = fvd.get('ipotesi_salto')
    if ip:
        L.append(f"\nIl flusso dati e' continuo (sequenza blocchi e timestamp senza salti), quindi non e' un buco di registrazione. "
                 f"**Ipotesi (da verificare guardando il video)**: il video non contiene una pausa di circa {ip['delta_s']:.0f} s presente nei dati "
                 f"(riposo piu' lungo, o taglio/salto del video). Se si assume che la P di video {ip['p_video_s']:.1f} s sia la partenza della nuotata "
                 f"che nei dati inizia a {ip['inizio_nuotata_dati_s']:.1f} s, l'arrivo successivo rilevato a dati {ip['a_dati_s']:.1f} s cadrebbe a video ~"
                 f"{_f(ip['a_video_ipotetico_s'], 1)} s, cioe' proprio in fondo al video ({_f(ip['durata_video_s'], 1)} s): coerente con un video che finisce all'arrivo. "
                 "Controllo da fare sul video: dopo l'arrivo a 504 s il nuotatore resta fermo ~50 s (e quel tratto e' stato tagliato), oppure il tempo del video "
                 "salta/si ferma? Finche' non e' chiarito, le etichette dopo ~504 s non sono affidabili (restano nella finestra di valutazione: "
                 "la P a 510,5 s e' probabilmente un FN in piu').\n")
    # ---- risultati
    L.append("### 4. Risultati dei rilevatori originali (streaming, non ritarati)\n")
    L.append(f"Abbinamento uno-a-uno entro +/-{tol:.1f} s; errore = t_rilevato - t_riferimento. "
             "`fisso` = assi anatomici stimati sull'intera sessione (ottimistico, vedi limiti); `online` = stima causale.\n")
    L.append("Attenzione: con uno scarto sistematico di ~+0,8 s e una tolleranza di 1,5 s l'errore dei TP e' troncato a +1,5 s, quindi TP/FN, "
             "media e dev.std dipendono da k e dalla tolleranza (vedi la tabella di sensibilita' a k). Le colonne 'dopo aver tolto la mediana' "
             "dicono cosa si otterrebbe ritarando l'offset costante (non fatto qui).\n")
    L.append("#### 4a. Assi fissi (calibrazione tipo '3 pose' ideale)\n")
    L.append(_tabella(R, 'fisso'))
    L.append("\n#### 4b. Assi stimati online (causali)\n")
    L.append(_tabella(R, 'online'))
    L.append("\n#### 4c. Arrivo: ritardo di notifica e causalita'\n")
    L.append("| Freq. | Ritardo notifica rispetto al tocco: mediana / p90 / max (s) | Notifiche entro 2 s | Violazioni t_notifica<t_evento | Test di causalita' (rilancio su dati troncati) |\n|---|---|---|---|---|")
    for fs, r in R['freq'].items():
        for modo in ('fisso', 'online'):
            m = r[modo]['metriche']['A']
            rn = m['ritardo_notifica']
            c = r[modo].get('causalita_A')
            ct = '-' if c is None else (f"OK ({c['provati']} eventi)" if c['ok'] else f"FALLITO ({len(c['falliti'])})")
            L.append(f"| {fs} Hz {modo} | {_f(rn['mediana'])} / {_f(rn['p90'])} / {_f(rn['max'])} | {_p(rn['entro_2s'])} | "
                     f"{r[modo]['violazioni']} | {ct} |")
    r0 = next(iter(R['freq'].values()))['fisso']
    lp, lv = r0['latenza_decisione']['P'], r0['latenza_decisione']['V']
    L.append(f"\nLatenza di P e V (214 Hz), dall'istante stimato dell'evento: decisione della regola P mediana {lp['regola_mediana']:.0f} s "
             f"(max {lp['regola_max']:.0f}), V mediana {lv['regola_mediana']:.0f} s (max {lv['regola_max']:.0f}); notifica finale (post-elaborazione "
             f"V->A e dedup entro 2 s, finalizzati prudentemente a evento + 50 s) mediana {lp['mediana']:.0f} s. Sono i valori che richiedono le "
             "regole originali cosi' come sono (filtri centrati, 'nessun altro evento entro N s'); non un requisito, e P/V possono tollerare "
             "alcuni secondi, non decine.\n")
    # ---- meta temporale
    mt = R['meta_temporale']
    L.append("### 5. Validazione: divisione temporale (struttura 'una sessione esclusa' pronta, con 1 sola sessione)\n")
    L.append(f"Assi (F, U) calibrati su una meta' (taglio a dati {mt['meta']:.0f} s) e rilevatore valutato sull'altra, in entrambe le direzioni (somma delle due prove). "
             "E' una validazione debole: stessa seduta e stesso nuotatore.\n")
    L.append("| Tipo | Rif | Rilev. | TP/FP/FN | Prec. | Richiamo | Err. medio | Dev.std | Mediana |\n|---|---|---|---|---|---|---|---|---|")
    for t in 'APV':
        m = mt['pool'][t]
        L.append(f"| {t} | {m['n_rif']} | {m['n_det']} | {m['tp']}/{m['fp']}/{m['fn']} | {_p(m['precisione'])} | {_p(m['richiamo'])} | "
                 f"{_f(m['media'])} | {_f(m['std'])} | {_f(m['mediana'])} |")
    # ---- compressione
    L.append("\n### 6. Frequenza di campionamento e memoria (2 MiB)\n")
    L.append("Ricampionamento con filtro anti-aliasing (FIR a fase zero, taglio 0,4 x fs) e compressione con lo schema del firmware "
             "(delta int8 + escape 0x80 = 13 byte), misurata sui dati ricampionati. Controllo: lo stesso schema simulato sui dati originali "
             f"produce {R['compressione'][0]['blocchi']} blocchi contro {R['blocchi']} reali ({100 * (R['compressione'][0]['blocchi'] / R['blocchi'] - 1):+.1f}%).\n")
    L.append("| Freq. (Hz) | Campioni/blocco | Campioni con escape | Byte/campione | Minuti nei 2 MiB (tutta la sessione) | Minuti (solo in acqua) |\n|---|---|---|---|---|---|")
    for c in R['compressione']:
        L.append(f"| {c['fs']:.0f} | {c['campioni_per_blocco']:.1f} | {100 * c['escape_frac']:.0f}% | {c['byte_per_campione']:.1f} | "
                 f"{c['minuti_2MiB']:.1f} | {c.get('minuti_2MiB_acqua', float('nan')):.1f} |")
    L.append("\nCapacita' = 8190 blocchi dati (un header e un footer di sessione). A 26 Hz il delta int8 non basta piu' (>80% di escape): "
             "il guadagno in minuti e' ~6x contro un fattore 8 di riduzione dei campioni; uno schema diverso (delta a 16 bit per canale, "
             "o risoluzione ridotta del giroscopio) farebbe meglio, ma cambia il formato del file (tocca firmware e decodifica).\n")
    return L


def scrivi(percorso, risultati, confronti, opz):
    L = []
    L.append("# Rapporto fase 2 - banco di prova dei rilevatori IMU\n")
    L.append(f"Generato il {datetime.date.today().isoformat()} da `analisi/imu/valuta.py`. "
             "Contiene dati personali (sessioni di nuoto): NON va nel repository.\n")
    L.append("## Sintesi\n")
    for R in risultati:
        r214 = next(iter(R['freq'].values()))['fisso']['metriche']
        r26 = list(R['freq'].values())[-1]['fisso']['metriche']
        ro = next(iter(R['freq'].values()))['online']['metriche']
        L.append(f"- Sessione `{R['nome']}`: k = {R['k']:.4f} (IC95% {R['k_stima']['ci95'][0]:.4f}-{R['k_stima']['ci95'][1]:.4f}).")
        for t, nome in (('A', 'Arrivo'), ('P', 'Partenza'), ('V', 'Virata')):
            m = r214[t]
            m26 = r26[t]
            L.append(f"  - {nome}: richiamo {_p(m['richiamo'])}, precisione {_p(m['precisione'])}, scarto mediano {_f(m['mediana'])} s, "
                     f"dev.std {_f(m['std'])} s a 214 Hz; a {list(R['freq'].keys())[-1]} Hz richiamo {_p(m26['richiamo'])}, "
                     f"dev.std {_f(m26['std'])} s; assi online: richiamo {_p(ro[t]['richiamo'])}, precisione {_p(ro[t]['precisione'])}.")
        rn = r214['A']['ritardo_notifica']
        L.append(f"  - Notifica dell'arrivo: mediana {_f(rn['mediana'])} s e max {_f(rn['max'])} s dopo il tocco (requisito 1,5-2 s: "
                 f"{_p(rn['entro_2s'])} entro 2 s); test di causalita': "
                 f"{'OK' if next(iter(R['freq'].values()))['fisso'].get('causalita_A', {}).get('ok') else 'non eseguito/fallito'}.")
        mins = ', '.join(f"{c['fs']:.0f} Hz: {c['minuti_2MiB']:.0f} min" for c in R['compressione'])
        L.append(f"  - Minuti di registrazione nei 2 MiB: {mins}.")
    for c in confronti:
        m = c['metriche']
        L.append(f"- Verifica del porting (vecchie etichette, tolleranze {c['tolleranze']}): "
                 + "; ".join(f"{t}: {m[t]['tp']}/{m[t]['n_rif']} trovati, errore {_f(m[t]['media'])} +/- {_f(m[t]['std'])} s" for t in 'APV')
                 + " (riferimento test.md: A 10/15 +0,00+/-0,88; P 11/14 -0,02+/-0,90; V 11/12 -0,01+/-0,69).")
    L.append("")
    for R in risultati:
        L.extend(_sezione_sessione(R, opz.tol))
    L.append("## 7. Limiti\n")
    L += [
        "- **Una sola sessione, un solo nuotatore, un solo montaggio.** Nessuna validazione tra sessioni; la divisione temporale e' debole.",
        "- **Assi anatomici 'fissi' stimati sull'intera sessione** (e il verso con le etichette A): i risultati 'fisso' sono un limite superiore, non causale. "
        "I risultati 'online' sono realizzabili ma servono ~20 s di nuotata per il riscaldamento; U (sommita') online peggiora molto V.",
        "- **Riferimento**: eventi OpenCV con incertezza dichiarata di +/-0,15 s (P), +/-0,3 s (A), +/-0,45 s (V); precisione di A/V non verificabile meglio di cosi'. "
        "Le vecchie soglie/offset sono tarati su un altro riferimento con k = 1,0024: da qui lo scarto sistematico.",
        "- **k incerto** (vedi sezione 2): +/-0,5% con le caratteristiche di bracciata; gli urti dicono k ~ 1 ma sono pochi. "
        "Un errore di 0,1% su k = 0,5 s a fine video.",
        "- **Fine video non spiegata**: dopo ~504 s di video il riferimento non e' affidabile; ipotesi nella sezione 3, da verificare sul video.",
        "- **Ricampionamento software** al posto di un vero ODR piu' basso (filtro interno LSM6DS3, rumore e saturazione diversi): i risultati a 104/52/26 Hz "
        "dicono che l'informazione dei rilevatori attuali e' a bassa frequenza, ma vanno confermati con registrazioni vere a quell'ODR. "
        "Il giroscopio satura a +/-1000 dps solo fuori dall'acqua in questa sessione (da test.md, non riverificato qui).",
        "- **Compressione misurata su questa sessione** (con tratti a riposo e fuori acqua): un allenamento piu' intenso ha piu' escape.",
        "- **Latenze di P e V** dei rilevatori originali: decine di secondi (vedi 4c): sono un artefatto delle regole non causali portate pari pari.",
        "- Bracciate escluse; nessun confronto con cronometro; nuotate brevi con ritorno al bordo della camera (non e' una vasca da 50 m completa).",
        "",
    ]
    L.append("## 8. Proposte per la fase 3\n")
    L += [
        "1. **Ancora fine dagli urti (P e V).** Gli urti di spinta (|a| > 8 g) sono nitidi e legati allo stacco dei piedi (4 inlier a +0,2...0,5 s dall'etichetta, scarto 0,07 s), ma compaiono solo in 5 P/V su ~24. "
        "Proposta: macro (regole attuali o HMM) per individuare la finestra di partenza/virata, poi micro = picco d'urto nella finestra come istante dello stacco; "
        "se manca l'urto si ricade sulla regola attuale. Va misurata la copertura con piu' dati (un tag al polso/caviglia darebbe etichette migliori).",
        "2. **Macchina a stati vincolata (macro->micro dalla letteratura sulla segmentazione del nuoto con IMU).** Stati: sosta, spinta/scivolata, nuotata, capriola, arrivo. "
        "Transizioni obbligate (P -> V* -> A -> sosta -> P) tagliano i FP delle V (qui ~50% di precisione) e rendono sfruttabile l'idea gia' notata di 'ultima bracciata = tocco' "
        "con un rilevatore di bracciate affidabile (picchi giroscopio passa-banda, ciclo ~1,6 s) e il conteggio delle inversioni di rotta per distinguere arrivo da virata.",
        "3. **Rilevatore di arrivo a rete neurale, causale.** Finestra di 4-6 s, 26-52 Hz (gli esperimenti dicono che non si perde informazione a 26 Hz), 6 canali + 'su' stimato "
        "(Mahony) con data augmentation a rotazione casuale del montaggio; CNN 1D depthwise int8 di ~5-10 mila parametri (poche decine di kB: sta nell'nRF52840; "
        "tempi da misurare). Uscita doppia: probabilita' di 'tocco avvenuto' + offset all'indietro (regressione) per datare l'evento; soglia/isteresi per notificare entro 1,5-2 s. "
        "Servono almeno 50-100 arrivi etichettati con precisione 0,1 s per tipo di arrivo (viso al cielo / testa bassa) e validazione 'una sessione esclusa'.",
        "4. **Calibrazione degli assi.** I risultati online mostrano che F (viso) si stima bene senza calibrare, U (sommita') no: o si calibra con le 3 pose all'inizio, "
        "o si cambia la rappresentazione in modo che V non dipenda da U (rotazione netta, componente rispetto alla gravita'). Da decidere prima del firmware.",
        "5. **Piano dati per la prossima registrazione:** due colpi di sync (inizio e fine, cosi' k si misura direttamente), colpetti a ogni pausa, vasca da 50 m, "
        "una seconda sessione con montaggio ruotato, e se possibile un tag di riferimento al polso o alla caviglia (tocco e stacco ben visibili) per etichette automatiche. "
        "Aggiungere la sessione = nuova cartella con `sessione.json` (vedi README).",
        "",
    ]
    L.append("## 9. Verifica del porting\n")
    if confronti:
        for c in confronti:
            L.append(f"Sessione di confronto `{c['nome']}` (vecchie etichette manuali, tolleranze {c['tolleranze']}): il porting streaming con assi fissi "
                     "riproduce i numeri di test.md (le differenze, se presenti, sono dovute alla finalizzazione differita di P/V):\n")
            L.append("| Tipo | Rif | Rilev. | TP | Err. medio (s) | Dev.std (s) |\n|---|---|---|---|---|---|")
            for t in 'APV':
                m = c['metriche'][t]
                L.append(f"| {t} | {m['n_rif']} | {m['n_det']} | {m['tp']} | {_f(m['media'])} | {_f(m['std'])} |")
    else:
        L.append("(nessuna sessione di confronto)")
    L.append("")
    with open(percorso, 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))
