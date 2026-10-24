# Driver LilyGO T-RGB

Copiato da LilyGo-T-RGB 1.0.5 (licenza MIT, vedi LICENSE) senza `LV_Helper` (richiede LVGL 8.4).
Adattato a SensorLib 0.3.x: `extension.begin(...)` al posto di `init(...)` e callback GPIO del touch con parametri `uint8_t`.

Per SwimTimer: `framebuffer()` per disegnare direttamente solo le parti che cambiano.
Bounce buffer da 10 righe (`bounce_buffer_size_px`) contro lo scorrimento dell immagine.
