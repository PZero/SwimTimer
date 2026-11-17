"""Aggiornamento del firmware della tag XIAO via Bluetooth dal PC (stesso protocollo OTA della pagina tools/index.html).

Uso:  python tools/ota_ble.py xiao-0.6.5.bin 0.6.5 [--nome SwimTag] [--indirizzo AA:BB:..] [--forza]
Richiede: pip install bleak
Protocollo (firmware/xiao-stream/LEGGIMI.md): "OTA,<byte>,<crc32 hex>,<versione>[,forza]" su 0004,
scritture su 0006 = uint32 offset LE + dati, "OTAEND"; risposte su 0005 (K/X/G + testo).
"""
import argparse, asyncio, re, sys, zlib

BASE = '-5b1d-4c8e-9f3a-1d2c3b4a5e60'
SERVIZIO, COMANDI, RISPOSTE, OTA = ('7a1e000%s' % n + BASE for n in '1456')


async def main(a):
    from bleak import BleakClient, BleakScanner
    bin_ = open(a.bin, 'rb').read()
    if b'SWIMTAG_BOARD=xiao-nrf52840;' not in bin_:
        sys.exit('il file non contiene la firma della XIAO')
    if a.indirizzo:
        dev = await BleakScanner.find_device_by_address(a.indirizzo, timeout=15)
    else:
        dev = await BleakScanner.find_device_by_filter(
            lambda d, ad: SERVIZIO in [u.lower() for u in ad.service_uuids] or (a.nome and (ad.local_name or d.name or '').startswith(a.nome)),
            timeout=20)
    if not dev:
        sys.exit('tag non trovata (svegliala con 4 tap o collega l\'USB)')
    print('tag:', dev.name, dev.address)
    coda = asyncio.Queue()
    stato = {'offset': None}

    def risposta(_, d: bytearray):
        t = d[1:].decode(errors='replace')
        tipo = chr(d[0]) if d else '?'
        if tipo == 'G':
            print('  log:', t)
            return
        m = re.match(r'ota offset,(\d+)', t)
        if m:
            stato['offset'] = int(m.group(1))
            return
        if re.match(r'ota,\d+', t):
            return
        coda.put_nowait((tipo, t))

    async def attendi(prefisso, s):
        while True:
            tipo, t = await asyncio.wait_for(coda.get(), s)
            if tipo == 'X' and t.startswith('ota'):
                raise RuntimeError(t)
            if tipo == 'K' and t.startswith(prefisso):
                return t

    # Windows: niente servizi in cache (dopo un cambio di firmware la cache puo' mostrare solo GAP/GATT)
    async with BleakClient(dev, timeout=20, winrt={'use_cached_services': False}) as c:
        await c.start_notify(RISPOSTE, risposta)
        await asyncio.sleep(1.0)          # lascia arrivare il log rimandato alla connessione
        while not coda.empty():
            coda.get_nowait()
        crc = '%08x' % (zlib.crc32(bin_) & 0xFFFFFFFF)
        cmd = f'OTA,{len(bin_)},{crc},{a.versione}' + (',forza' if a.forza else '')
        await c.write_gatt_char(COMANDI, cmd.encode(), response=True)
        try:
            pronto = await attendi('ota pronto', 10)
            blocco = max(16, int(pronto.split(',')[1]) if ',' in pronto else 180)
            off, ultimo = 0, -1
            while off < len(bin_):
                n = min(blocco, len(bin_) - off)
                await c.write_gatt_char(OTA, off.to_bytes(4, 'little') + bin_[off:off + n], response=True)
                if stato['offset'] is not None:
                    off, stato['offset'] = stato['offset'], None
                else:
                    off += n
                pct = off * 100 // len(bin_)
                if pct // 10 != ultimo:
                    ultimo = pct // 10
                    print(f'  {pct}% ({off // 1024} KB)')
            await c.write_gatt_char(COMANDI, b'OTAEND', response=True)
            print(await attendi('ota ok', 20), '- la tag si riavvia')
        except Exception as e:
            try:
                await c.write_gatt_char(COMANDI, b'OTAABORT', response=True)
            except Exception:
                pass
            sys.exit(f'OTA non riuscito: {e}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('bin')
    ap.add_argument('versione', help='es. 0.6.5')
    ap.add_argument('--nome', default='')
    ap.add_argument('--indirizzo', default='')
    ap.add_argument('--forza', action='store_true')
    asyncio.run(main(ap.parse_args()))
