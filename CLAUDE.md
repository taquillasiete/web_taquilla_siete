# Taquilla Siete — web

Sitio estático (HTML/CSS/JS plano, sin build), desplegado en GitHub Pages con dominio propio (`CNAME` → taquillasiete.com).

## Al crear o modificar una página HTML

Cada página del sitio debe llevar siempre, en su `<head>`:

1. El script de **GoatCounter** (analítica): `<script data-goatcounter="https://taquillasiete.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>`
2. `<link rel="canonical">` con su URL real en `https://taquillasiete.com/...`
3. Etiquetas **Open Graph** (`og:title`, `og:description`, `og:image`, `og:url`) y **Twitter Card**
4. Un bloque **JSON-LD** `"@type": "Organization"` (datos estructurados, importante para que Google e IAs como ChatGPT/Perplexity citen el sitio correctamente)
5. Mención de **"Madrid"** en el contenido visible de la página (SEO local — ver conversación sobre posicionamiento)

Para crear una página nueva, parte de [_template.html](_template.html) — ya incluye todo lo anterior con placeholders — y copia el header/footer de otra página existente para mantener consistencia visual.

Cuando añadas una página nueva, añade también su URL en [sitemap.xml](sitemap.xml).

## Una página por Mirada y por evento

- **Miradas**: cada reseña vive en `miradas/<titulo>.html` (JSON-LD `Review` con su `url`). [la-mirada.html](la-mirada.html) es solo el índice: kicker, título enlazado, director · año, frase-resumen y "Leer la mirada →". Al añadir una mirada nueva: crea su página copiando otra de `miradas/`, añádela al índice, a las píldoras "otras miradas" del pie de las demás, a la lista de slugs del script de redirección de `la-mirada.html` (enlaces antiguos `#slug`) y al sitemap.
- **Eventos**: cada Live/Rewind vive en `eventos/live-<tema>.html` o `eventos/rewind-<pelicula>.html`, con su JSON-LD `Event`/`ScreeningEvent` (el JSON-LD de evento va **solo** ahí, no en `live.html`/`rewind.html`). En los índices [live.html](live.html) y [rewind.html](rewind.html) el título y el cartel de cada evento enlazan a su página. Cuando un evento pasa: en su página cambia "Próximo evento" por "Evento anterior" y quita el botón de entradas y el `offers` del JSON-LD; en el índice pásalo al bloque de anteriores.
- Las páginas en subcarpetas usan rutas `../` (CSS, JS, imágenes, menú). `check-seo.py` revisa también las subcarpetas y que el canonical coincida con la ruta del fichero.

## Verificación antes de hacer commit/push

Ejecuta siempre, tras crear o modificar cualquier página:

```
python check-seo.py
```

Este script ([check-seo.py](check-seo.py)) revisa automáticamente que ninguna página se quede "descolgada": comprueba GoatCounter, canonical, Open Graph, Twitter Card, JSON-LD Organization, mención de Madrid, alt en imágenes, que el `sitemap.xml` esté sincronizado con los ficheros HTML reales (sin huecos ni huérfanos), y que ninguna imagen en `assets/` pese más de 300KB. Sale con código de error si falta algo — soluciónalo antes de comitear.

Si el script marca una imagen pesada, conviértela a WebP con Pillow (`pip install Pillow`):
```python
from PIL import Image
img = Image.open("ruta/original.jpg")
img.save("ruta/original.webp", "WEBP", quality=82, method=6)
```
Actualiza luego todas las referencias (`<img src>`, `og:image`, JSON-LD) al nuevo `.webp` y borra el fichero original.

## Al publicar (commit + push)

1. **Antes del commit**: `python actualiza-sitemap.py` — pone en cada URL del `sitemap.xml` su `<lastmod>` (fecha del último cambio en git, o hoy si tiene cambios sin comitear). Luego `python check-seo.py`.
2. **Después del push**, cuando GitHub Pages haya desplegado (1-2 min; comprueba con `curl` que una página cambiada ya sirve la versión nueva): `python indexnow.py` — avisa a Bing vía IndexNow de las páginas HTML cambiadas en el último commit (`--todas` para todo el sitemap, o pasa rutas concretas). Google no usa IndexNow: para algo urgente, el usuario pide la indexación a mano en Search Console.
3. El fichero `<32 hex>.txt` de la raíz es la clave de IndexNow: no lo borres ni lo renombres.
