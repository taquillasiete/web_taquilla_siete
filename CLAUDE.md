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
