# Garmin Recovery — Operación, trazabilidad y control de cambios

**Revisión:** 2.4.11 · Europe/Madrid  
**Ámbito:** documentación operativa; no altera automatizaciones, credenciales ni datos deportivos.

## 1. Arquitectura vigente

Workflows permanentes (solo seis):

1. `.github/workflows/sync.yml`: recibe `schedule`, `repository_dispatch` (`garmin-sync`) y `workflow_dispatch`; procesa Intervals.icu.
2. `.github/workflows/garmin-heart-rate.yml`: obtiene Garmin FC, HRV y sueño después de Sync.
3. `.github/workflows/advanced-analytics-rpe.yml`: recuperación, calidad de datos y RPE.
4. `.github/workflows/crossfit-insights.yml`: fuerza, WODs y certificado de datos preparados.
5. `.github/workflows/monitor-monthly.yml`: salud de cadena, diagnóstico y resumen mensual.
6. `.github/workflows/garmin-ci.yml`: pruebas de código y workflows, independiente de la cadena de datos.

Conservar scripts históricos (`monitor_v231.py`, `recovery_v231.py`, `test_quality_v248.py`, etc.) mientras estén importados; el número de versión del nombre no implica que sobren.

## 2. Horarios oficiales

| Concepto | Europe/Madrid |
|---|---|
| Sync principal | 08:30, 16:45, 22:45 |
| Informe ChatGPT | 09:05, 17:10, 23:10 |
| Watchdog GitHub | 11:05, 19:20, 01:20 |
| Informe semanal | Domingo 20:15 |

Usar zona `Europe/Madrid`, incluidos los cambios de horario de verano/invierno. GitHub Actions puede retrasar los cron: evaluar evidencia real (`created_at`, evento, `conclusion`) y no asumir que un horario equivale a ejecución.

## 3. Origen comprobable de cada ejecución

- `schedule`: origen programado de GitHub verificado.
- `repository_dispatch` con tipo `garmin-sync`: compatible con respaldo externo Apps Script; confirmar la procedencia en el registro de Apps Script y el evento.
- `workflow_dispatch`: **origen no determinado**. Puede ser un clic manual, una petición externa o un respaldo que use esa API. No rotularlo automáticamente «manual» ni «Apps Script probado».
- `workflow_run`: etapa hija; debe seguir a un resultado `success` del flujo padre.

Para certificar el respaldo comparar la hora de ejecución en Apps Script y GitHub, el tipo de evento y el identificador si está disponible. No cambiar `Code.gs` sin inspeccionar su versión real. No compartir tokens ni claves por chat.

## 4. Preparación de datos no equivale a entrega

- `report_ready.json.status == ready` certifica **preparación** dentro de un ciclo; no equivale a recepción en ChatGPT.
- `delivery_status = unconfirmed_no_chatgpt_receipt` debe interpretarse como **desconocido**, no como error de entrega ni como éxito.
- Para evitar duplicados, no emitir un segundo informe solo por faltar acuse. Necesaria evidencia independiente de que no se entregó.
- Si se implementa acuse externo, utilizar `cycle_id + report_type` como clave de idempotencia y conservar fecha/resultado del acuse. Una instrucción textual a ChatGPT no constituye un recibo técnico de entrega.
- Los Sync manuales fuera de las ventanas programadas pueden completar la cadena sin generar un nuevo certificado de slot: es normal.

## 5. Política fisiológica

- Medir frescura desde el **timestamp real de cada muestra**, no solo `generated_at`.
- La recuperación `pending` **no autoriza intensidad alta**. No extrapolar HRV/sueño de la noche anterior al día actual.
- Tras turno nocturno, considerar la posibilidad de sueño diurno o fragmentado; la ventana conservadora ampliada no confirma que el usuario haya dormido.
- Separar claramente `quality score`, `readiness híbrido` y `recovery_assessment.state`.
- No comparar cargas de mancuerna, máquina y barra como si fueran métricas mecánicas equivalentes.
- El volumen de WOD usa repeticiones/distancias **realmente realizadas**; no completar rondas a partir de la prescripción.
- HRR insuficiente o inconsistente se describe como observación, no como conclusión sobre aptitud cardiovascular.

## 6. Política de actualizaciones

1. Cambiar un archivo y conservar la posibilidad de revertirlo por commit.
2. Esperar la CI verde antes de modificar otro archivo.
3. Después de los cambios de analítica, ejecutar un único Sync manual y verificar toda la cadena.
4. Contrastar JSON publicados, fechas de muestras, RPE y ausencia de duplicados.
5. Borrar solo workflows temporales ya ejecutados y certificados. No borrar los seis permanentes.
6. Medir al menos 3 ciclos automáticos consecutivos antes de certificar un comportamiento autónomo; medir 30 días para evaluar la fiabilidad sostenida.

## 7. Criterios objetivos de aceptación sugeridos

- CI verde en el commit de cambio; pruebas de medianoche, turnos y parser de WOD incluidas.
- Cinco etapas de la cadena terminadas en `success` después de una sincronización de prueba.
- Cero WOD con repeticiones prescritas contabilizadas como realizadas sin evidencia.
- Recuperación `pending` hasta sueño/HRV actuales confirmados.
- RPE por ID coincidente (sin emparejar por fecha cuando hay múltiples sesiones).
- Cero duplicados de informe **confirmados** por `cycle_id + tipo`.
- Seguimiento mensual de ejecución por horario, completitud de la cadena y cobertura de datos, sin equiparar objetivos futuros con cifras ya logradas.

## 8. Hallazgos que no quedan cerrados solo por instalar código

**H01: origen del respaldo.** Requiere comprobar los registros de Apps Script y su disparador real.

**H02: entrega ChatGPT.** Requiere acuse independiente; un JSON del repositorio no puede certificar que la aplicación haya mostrado una notificación.

**H06: planificación.** En Google Sheets `Planificados` existe la sentadilla prevista del 09/10 como `PREVISTO`. Contrastar con la sesión realizada 10×2 hasta 170 kg y actualizar manualmente el estado a `SUSTITUIDO/REALIZADO DISTINTO`, conservando ambos registros; no sobrescribir lo prescrito con lo ejecutado.

**H07: HRR y series históricas.** Necesitan más mediciones válidas y comparables; mejorar el código no crea datos retrospectivos.
