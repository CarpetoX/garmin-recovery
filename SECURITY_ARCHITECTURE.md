# Arquitectura privada propuesta

## Hallazgo prioritario
El repositorio `CarpetoX/garmin-recovery` figura público y versiona JSON con métricas personales. El dashboard autenticado **no** protege esos archivos de origen. Auditar el histórico, los artefactos y GitHub Pages antes de publicar. Cambiar visibilidad y retirar datos de los archivos actuales no borra automáticamente el histórico de Git ni las copias existentes.

## Separación de responsabilidades
1. Pipeline existente (sin cambios): Garmin/Intervals/RPE, validaciones, report_ready.json y report_cycles.json.
2. Exportador futuro (server-side): comprobar cycle_id, estado, hashes, timestamps y completitud; exportar solo métricas autorizadas, con mínimo de datos.
3. Almacenamiento privado: base de datos con acceso restringido por usuario; cifrado en tránsito y en reposo, copias controladas.
4. API autenticada: verificar token de sesión y permisos en cada petición; rate limiting; sin secretos en el cliente.
5. Frontend: HTML/JS estático, recibe JSON filtrado mediante la API; estados pendiente/no disponible; jamás deducir READY de una fecha de archivo.

## Opciones de despliegue
- Frontend en Vercel/Cloudflare Pages y backend privado con autenticación gestionada; verificar permisos y políticas antes de uso real.
- Supabase Auth + Postgres con RLS estricta, sin acceso público a tablas personales; revisar políticas con pruebas negativas (usuarios no autorizados).
- No usar GitHub Pages como mecanismo de autenticación; es alojamiento estático.

## Pruebas obligatorias
- Usuario sin sesión: 401 y sin datos personales.
- Usuario distinto: 403 o 404 y sin datos ajenos.
- Ciclo no READY, inconsistente o caducado: no presentar como certificado.
- Ausencia de sueño/RPE: representar dato ausente, nunca cero inventado.
- RPE por bloque separado de métricas cardiovasculares.
- Pruebas móviles, accesibilidad, CSP y ausencia de tokens en bundle/logs.
- Confirmar que no se alteran workflows de producción.
