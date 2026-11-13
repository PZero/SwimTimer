# Protocollo USB ricevitore <-> host (versione 1)

Seriale USB CDC (115200 8N1 nominale, la velocita' reale e' quella dell'USB). Interi little-endian.

## Frame (in entrambi i versi)
| off | campo | note |
|---|---|---|
| 0 | `0xA5 0x5A` | sincronismo |
| 2 | tipo u8 | vedi sotto |
| 3 | id tag u32 | id del chip (FICR DEVICEID[0], come l'annuncio); 0 se non riferito a una tag |
| 7 | numero u32 | `seq` del blocco (BLOCCO, OK, ERR), contatore o argomento negli altri |
| 11 | lunghezza payload u16 | max 4200 |
| 13 | payload | |
| 13+len | CRC32 u32 | IEEE 802.3 (come `zlib.crc32`) dei byte da `tipo` a fine payload |

Un frame con CRC errato o lunghezza > 4200 si scarta e si cerca il prossimo `A5 5A` dal byte successivo.

## Dispositivo -> host
- **0x01 BLOCCO** (id tag, numero = seq): payload = blocco fisico u16, CRC32 del blocco u32, millis del primo campione u32, poi 4096 byte del blocco (cosi' come nella flash della tag, formato `.swr` 3). Il ricevitore ha gia' verificato il CRC32 del blocco. **La tag non riceve la conferma finche' l'host non risponde OK.**
- **0x02 STAT** (id tag, numero = ms dall'avvio), ogni secondo per ogni tag conosciuta, 33 byte: slot u8, collegamento u8 (0 non vista da > 3 s, 1 vista, 2 connessione in corso, 3 sicurezza/scoperta servizi, 4 attiva), RSSI i8, stato annuncio u8 (0 sonno, 1 pronta, 2 registra, 4 piena, 5 errore, 6 sincronizza), batteria mV/20 u8, % memoria non confermata u8, bit di errore u8, blocchi in attesa sulla tag u16 (dall'ultimo annuncio), byte/s u32, blocchi ricevuti u32 (validi, inoltrati all'host), blocchi confermati u32 (CONFERMATO ricevuto dalla tag), blocchi scartati per CRC u16, ms avvistamento->PRONTO u32 (0 = non ancora; senza la pausa fra tentativi), ultimo seq annunciato u32, ms dall'ultimo annuncio u16 (saturato).
- **0x03 EVENTO** (id tag, numero = argomento): payload = testo ASCII (max 200 byte dalla 0.1.7, senza terminatore; 120 fino alla 0.1.6, 80 fino alla 0.1.4). Un EVENTO per ogni fatto, mai silenzioso. Dalla 0.1.5:
  - `connect() dopo N ms dall'avvistamento; attese ms host/inAttesa0/sonno/pausa/altra a/b/c/d/e`: perche' la tag, gia' vista, non e' stata collegata prima (host senza PRESENZA, annuncio con 0 blocchi, tag in sonno, pausa fra tentativi, altra tag in connessione).
  - `connect(): timeout 5000 ms senza collegamento; ultimo annuncio X ms fa, RSSI r, cancel c` e `connect() rifiutata (num = codice SoftDevice)`.
  - `disconnessa: motivo HCI 0x.. in fase <fase>, N ms dal collegamento` (numero = motivo HCI).
  - `PRONTO inviato; tempi cum. ms connect()/conn/cifr/mtu/disc/pronto a/b/c/d/e/f` (millisecondi cumulativi dall'avvistamento utile; numero = ms totali).
  - `link effettivo: PHY 2M DLE 251 MTU 247 intervallo 7.50 ms` (stato letto dal SoftDevice dopo PRONTO; `NON completo` se PHY/DLE non raggiunti in 2 s; `cambiato` quando l'intervallo cambia: 7,5 ms con una tag sola, 11,25-15 ms se ce n'e' un'altra impegnata).
  - ogni 10 blocchi: `10 blocchi, medie ms periodo/radio/usb/host/tag a/b/c/d/e; loop max N ms` (periodo = distanza fra blocchi completi, radio = primo->ultimo frammento, usb = invio del BLOCCO all'host, host = fine invio -> OK, tag = OK -> CONFERMATO, loop max = massimo intervallo fra due giri del loop).
  - dalla 0.1.6 (tag 0.6.2+, PRONTO versione 2): `DIAGNOSI tag: reset causa C RESETREAS 0x.. guasto G pc 0x.. lr 0x.. cfsr 0x..; stack libero B loop/cb/ble a/b/c; diario N righe` (numero = causa) e, subito dopo, un EVENTO `diario tag: <riga>` per ogni riga del diario (numero = progressivo): l'host li scrive nel log come ogni EVENTO.
  - dalla 0.1.7 (tag 0.6.4+): `DIAGNOSI2 tag: int=7.50 mtu=247 dle=251 phy=2 vbus=0 vbus_su=N vbus_giu=N vbus_ms=<millis tag dell'ultimo evento VBUS> hci3E=N disc=N ultdisc=0x.. stkble=B tagms=<millis tag>` (numero = disconnessioni 0x3E). Righe `chiave=valore` separate da spazio: l'host le legge. Il formato dei frame USB non cambia.
  Le scritture su CONTROLLO falliscono con numero = codice SoftDevice (65535 = nessuna risposta in 1,5 s).
- **0x04 HELLO** (id 0): payload = testo versione, ad esempio `ricevitore-0.1.7`; all'avvio e ogni 10 s.

## Host -> dispositivo
- **0x20 OK** (id tag, numero = seq): payload = CRC32 del blocco u32. Significa "blocco seq salvato **e riletto**": solo allora il ricevitore manda CONFERMA alla tag.
- **0x21 ERR** (id tag, numero = seq): payload = motivo u8 (1 disco pieno, 2 errore di scrittura/rilettura, 3 dati non validi: CRC16 di pagina). Il ricevitore manda STOP alla tag e chiude il collegamento; la tag tiene il blocco.
- **0x22 PRESENZA** (id 0, numero 0, payload vuoto): ogni secondo. **Senza PRESENZA da 3 s il ricevitore non si collega a nessuna tag** (default sicuro: i dati restano sulla tag).

Se un OK non arriva entro 20 s dal BLOCCO, il ricevitore chiude il collegamento (nessuna conferma: la tag reinvia al collegamento successivo).
