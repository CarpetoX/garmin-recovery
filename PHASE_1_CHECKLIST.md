# V5.0 · Fase 1: seguridad sin tocar producción

**Estado:** prototipo local; no hay autenticación, servidor, despliegue ni exportación de datos personales.

## Hechos verificados
- `CarpetoX/garmin-recovery` es público (comprobación de repositorio del 14-10-2026).
- `.gitignore` excluye secretos habituales pero **no** excluye `*.json`.
- Los JSON publicados pueden contener información sensible de salud y entrenamiento.
- Existe rama `feature/dashboard-v5-private`; `main` permanece sin cambios.

## Decisiones de diseño
1. No publicar GitHub Pages con JSON personales, ni poner claves/tokens en HTML.
2. Mantener el pipeline de seis workflows sin cambios.
3. Migrar la información personal a almacenamiento privado antes de habilitar el dashboard remoto.
4. Autenticación OIDC gestionada y autorización por usuario en backend; comprobar `401` sin sesión y denegación entre usuarios.
5. Un exportador del lado del servidor validará integridad del ciclo, hashes, run IDs, frescura, cobertura y estado de publicación. El `security/export_gate.py` actual es **solo una comprobación preliminar** de estructura: no habilita la publicación.
6. No desplegar hasta resolver la exposición del repositorio actual y su histórico. Hacer copia verificable antes de cualquier migración.

## Pasos siguientes
- Auditar qué rutas JSON son públicas y dónde aparecen secretos/identificadores; **no** imprimir sus valores en logs.
- Elegir alojamiento privado y proveedor de identidad (por ejemplo Supabase Auth con políticas RLS probadas).
- Implementar API de solo lectura, esquema de snapshot mínimo y pruebas de acceso negativas.
- Conectar frontend a `/api/dashboard` solo tras autenticación real.

## Pruebas locales
Desde la raíz de este paquete:

```sh
python -m unittest discover -s tests -v
python -m security.export_gate --certificate /ruta/a/report_ready.json
```

El segundo comando solo devuelve un estado de prevalidación; **nunca** certifica por sí mismo un ciclo.
