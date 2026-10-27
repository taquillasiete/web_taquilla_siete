# Taquilla Siete — web

Sitio estático (HTML/CSS/JS plano, sin build), desplegado en GitHub Pages con dominio propio (`CNAME` → taquillasiete.com).

## Al crear o modificar una página HTML

Cada página del sitio debe llevar siempre, en su `<head>`:

1. El script de **GoatCounter** (analítica): `<script data-goatcounter="https://taquillasiete.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>`
2. `<link rel="canonical">` con su URL real en `https://taquillasiete.com/...`, **sin `.html`** (`/sesiones`, `/eventos/live-tema`; la portada es `/`). Igual en `og:url`, JSON-LD, `sitemap.xml` y enlaces internos (`href="sesiones"`, `href="./#contacto"`, `href="../"`). GitHub Pages sirve las dos formas; la canónica es la limpia
3. Etiquetas **Open Graph** (`og:title`, `og:description`, `og:image`, `og:url`) y **Twitter Card**
4. Un bloque **JSON-LD** `"@type": "Organization"` (datos estructurados, importante para que Google e IAs como ChatGPT/Perplexity citen el sitio correctamente)
5. Mención de **"Madrid"** en el contenido visible de la página (SEO local — ver conversación sobre posicionamiento)

Además, en todas las páginas:

- `<script>document.documentElement.classList.add("js")</script>` justo tras el viewport: sin él, los bloques `.reveal` no se ocultan/animan (y sin JS el contenido se ve igual, que es lo que queremos).
- Fuentes **alojadas en la propia web** (`@font-face` al principio de `css/style.css`, ficheros en `assets/fonts/`): no enlaces Google Fonts.
- Favicon: `favicon.ico` + `apple-touch-icon.png` de la raíz. Imagen para redes genérica: `assets/logos/og-taquilla-siete.jpg` (1200×630); el `logo` del JSON-LD sigue siendo el JPG cuadrado.
- Cada `<img>` con `width` y `height` (tamaño real del fichero) para que la página no "salte" al cargar. Fotos en WebP, como mucho 1200 px de lado.
- Nada de `style="…"` sueltos: usa clases (`.mt-s`, `.mt-l`, `.mt-xl`, `.mb-l` para separaciones). Excepción: `--ratio` en `.media-foto`.
- Si cambias `css/style.css` o `js/main.js`, sube el `?v=N` en **todas** las páginas.
- [404.html](404.html) la sirve GitHub Pages en cualquier ruta inexistente: por eso usa rutas absolutas (`/css/...`, `/sesiones`). Es oculta (noindex).

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

0. **Antes de nada**: `git pull --rebase` — el Action de la agenda hace commits solos en `main`.
1. **Antes del commit**: `python actualiza-sitemap.py` — pone en cada URL del `sitemap.xml` su `<lastmod>` (fecha del último cambio en git, o hoy si tiene cambios sin comitear). Luego `python check-seo.py`.
2. **Después del push**, cuando GitHub Pages haya desplegado (1-2 min; comprueba con `curl` que una página cambiada ya sirve la versión nueva): `python indexnow.py` — avisa a Bing vía IndexNow de las páginas HTML cambiadas en el último commit (`--todas` para todo el sitemap, o pasa rutas concretas). Google no usa IndexNow: para algo urgente, el usuario pide la indexación a mano en Search Console.
3. El fichero `<32 hex>.txt` de la raíz es la clave de IndexNow: no lo borres ni lo renombres.

## Páginas ocultas (solo con enlace)

- Llevan `<meta name="robots" content="noindex">`, **no** van en `sitemap.xml` (check-seo.py lo comprueba), no se enlazan desde la web e `indexnow.py` las ignora. Resto de requisitos (GoatCounter, OG, JSON-LD, Madrid) igual que cualquier página.
- [agenda.html](agenda.html): página del QR para bares (`https://taquillasiete.com/agenda`, URL fija). Muestra la próxima Sesión, Live y Rewind (una de cada) y un calendario con hoy y esos días. Lee `agenda.json`, que genera [actualiza-agenda.py](actualiza-agenda.py):
  - **Sesiones**: del Google Calendar público del club, pero **solo** los eventos con un año entre paréntesis en el título ("Película (1999)"). El usuario no quiere que salga nada más del calendario.
  - **Live y Rewind**: del JSON-LD de `eventos/*.html` (no del calendario).
  - Un GitHub Action ([.github/workflows/agenda.yml](.github/workflows/agenda.yml)) lo regenera cada 6 h y hace commit si cambia. Al crear o tocar una página de `eventos/`, ejecuta también `python actualiza-agenda.py` antes de comitear.
  - La página oculta cada evento 3 h después de su inicio aunque el JSON no se haya regenerado.
