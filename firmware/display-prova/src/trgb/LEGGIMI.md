# Driver LilyGO T-RGB

Copiato da LilyGo-T-RGB 1.0.5 (licenza MIT, vedi LICENSE) senza `LV_Helper` (richiede LVGL 8.4).
Adattato a SensorLib 0.3.x: `extension.begin(...)` al posto di `init(...)` e callback GPIO del touch con parametri `uint8_t`.

Per SwimTimer: doppio framebuffer (`double_fb`), `bufferNascosto()` e `mostra()` con attesa del vsync.
