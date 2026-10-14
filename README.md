# Garmin Recovery Dashboard V5.0 — prototipo aislado

Esta versión es un prototipo de interfaz con datos **sintéticos**. No se conecta a Garmin, GitHub, ni almacena información personal. No implementa autenticación real.

## Uso
Abre `index.html` en un navegador moderno. Los gráficos y los filtros funcionan sin conexión. Para producción, desplegar tras configurar autenticación en servidor, autorización por usuario, almacenamiento privado y API que entregue únicamente snapshots certificados. No alojar JSON personales en un sitio público ni exponer tokens en JavaScript.

## Archivos
- `index.html`: interfaz y gráficos SVG interactivos.
- `SECURITY_ARCHITECTURE.md`: arquitectura propuesta y controles de publicación.

## Aislamiento
No cambia workflows ni archivos del repositorio existente. Colocar bajo `dashboard-v5/` en la rama `feature/dashboard-v5-private`, **sin fusionar** hasta revisar la exposición actual de datos.
