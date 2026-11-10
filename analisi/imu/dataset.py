"""Caricatore unico di una sessione (dati IMU + riferimento) con mappatura video -> dati.

FORMATO DEL DATASET (una cartella per sessione; le sessioni future si aggiungono
copiando una nuova cartella, senza toccare il codice):

    <cartella_sessione>/
        sessione.json      metadati (vedi sotto)
        <file>.swr         registrazione del tag (percorso relativo in "swr")
        eventi.json        riferimento: {"eventi":[{"t_video_s":..,"tipo":"A|P|V|X","nota":..}]}
                           (accettato anche un .csv con colonne t_video_s,tipo)

    sessione.json
        nome                  etichetta libera della sessione
        swr                   file .swr (relativo alla cartella o assoluto)
        indice_sessione       sessione dentro il .swr (null = la piu' lunga)
        riferimento           file degli eventi (default eventi.json)
        montaggio             testo libero (posizione/orientamento del tag)
        sync.video_s          istante del colpo di sync nel video
        sync.dati_s           istante del picco nei dati (null = lo cerca nella finestra)
        sync.ricerca_dati_s   [a, b] finestra di ricerca del picco (s dati)
        k                     scala video->dati: t_dati = sync_dati + (t_video - sync_video) * k
        k_metodo              come e' stato stimato k
        durata_video_s        i riferimenti oltre questo istante non esistono
        etichettato_fino_s    video etichettato fino a qui (dopo: nessun negativo valido)
        acqua_dati_s          [a, b] intervallo "in acqua" (calibrazione assi anatomici)
        tipi                  tipi di evento etichettati (es. ["A","P","V"])

I tempi "dati" sono secondi dal primo campione della sessione decodificata.
"""
import hashlib
import json
import os
import csv
from dataclasses import dataclass, field

import numpy as np

from formato_swr import carica_swr


@dataclass
class Sessione:
    nome: str
    t: np.ndarray                 # s, passo costante
    acc: np.ndarray               # (N,3) g
    gyro: np.ndarray              # (N,3) dps
    fs: float
    eventi: list                  # [(t_dati_s, tipo)] ordinati, solo A/P/V
    meta: dict
    finestra_valida: tuple        # (t_ini, t_fin) in s dati, dove il riferimento e' completo
    sync_dati_s: float = 0.0
    k: float = 1.0
    extra: dict = field(default_factory=dict)


def _leggi_eventi(percorso):
    if percorso.lower().endswith('.csv'):
        with open(percorso, encoding='utf-8-sig') as f:
            return [dict(t_video_s=float(r['t_video_s']), tipo=r['tipo']) for r in csv.DictReader(f)]
    with open(percorso, encoding='utf-8-sig') as f:
        return json.load(f)['eventi']


def trova_picco_sync(t, acc, a, b):
    """Istante (s dati) del massimo del modulo dell'accelerazione nella finestra [a,b]."""
    n = np.linalg.norm(acc, axis=1)
    m = np.nonzero((t >= a) & (t <= b))[0]
    i = m[np.argmax(n[m])]
    return float(t[i]), float(n[i])


def _cache_path(swr, indice, cartella_cache):
    st = os.stat(swr)
    h = hashlib.sha1(f'{os.path.abspath(swr)}|{st.st_size}|{st.st_mtime_ns}|{indice}'.encode()).hexdigest()[:16]
    return os.path.join(cartella_cache, f'swr_{h}.npz')


def carica_dati(swr, indice=None, cartella_cache=None):
    if cartella_cache:
        os.makedirs(cartella_cache, exist_ok=True)
        cp = _cache_path(swr, indice, cartella_cache)
        if os.path.exists(cp):
            z = np.load(cp)
            return dict(fs=float(z['fs']), acc_g=z['acc_g'], gyro_dps=z['gyro_dps'],
                        t=np.arange(len(z['acc_g'])) / float(z['fs']), raw=z['raw'],
                        cambi_rotazione=int(z['cambi']), blocchi=z['blocchi'])
    r = carica_swr(swr, indice)
    if cartella_cache:
        np.savez(cp, fs=r['fs'], acc_g=r['acc_g'], gyro_dps=r['gyro_dps'], raw=r['raw'],
                 cambi=r['cambi_rotazione'], blocchi=r['blocchi'])
    return r


def video_a_dati(t_video, sync_video, sync_dati, k):
    return sync_dati + (np.asarray(t_video, float) - sync_video) * k


def carica_sessione(cartella, cartella_cache=None, k=None):
    """Carica una sessione. k (se dato) sovrascrive quello dei metadati."""
    with open(os.path.join(cartella, 'sessione.json'), encoding='utf-8-sig') as f:
        meta = json.load(f)
    swr = meta['swr']
    swr = swr if os.path.isabs(swr) else os.path.normpath(os.path.join(cartella, swr))
    r = carica_dati(swr, meta.get('indice_sessione'), cartella_cache)
    t, acc, gyro, fs = r['t'], r['acc_g'], r['gyro_dps'], r['fs']
    sy = meta['sync']
    sync_dati = sy.get('dati_s')
    if sync_dati is None:
        a, b = sy['ricerca_dati_s']
        sync_dati, _ = trova_picco_sync(t, acc, a, b)
    k_eff = float(k if k is not None else meta.get('k', 1.0))
    rif = meta.get('riferimento', 'eventi.json')
    ev = _leggi_eventi(os.path.join(cartella, rif))
    tipi = set(meta.get('tipi', ['A', 'P', 'V']))
    eventi = sorted((float(video_a_dati(e['t_video_s'], sy['video_s'], sync_dati, k_eff)), e['tipo'])
                    for e in ev if e['tipo'] in tipi)
    fine_v = meta.get('etichettato_fino_s', meta.get('durata_video_s', 1e9))
    # il riferimento e' completo da sync (inizio video) fino a fine_v
    f_ini = float(video_a_dati(sy['video_s'], sy['video_s'], sync_dati, k_eff))
    f_fin = float(video_a_dati(fine_v, sy['video_s'], sync_dati, k_eff))
    return Sessione(nome=meta.get('nome', os.path.basename(cartella.rstrip('/\\'))), t=t, acc=acc, gyro=gyro,
                    fs=fs, eventi=eventi, meta=meta, finestra_valida=(f_ini, min(f_fin, float(t[-1]))),
                    sync_dati_s=sync_dati, k=k_eff,
                    extra=dict(cambi_rotazione=r['cambi_rotazione'], blocchi=r['blocchi']))


def elenca_sessioni(radice):
    """Cartelle con sessione.json: radice stessa oppure sue sottocartelle dirette."""
    if os.path.exists(os.path.join(radice, 'sessione.json')):
        return [radice]
    out = []
    for n in sorted(os.listdir(radice)):
        p = os.path.join(radice, n)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, 'sessione.json')):
            out.append(p)
    return out

