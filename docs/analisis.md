# TP4 – Depósito B: análisis del sistema

Unidad de tiempo: **minutos**. Todos los tiempos se redondean a 2 decimales.

## Enunciado (resumen)

Un predio tiene 3 depósitos. El **Técnico T** (temperatura) y el **Técnico I** (iluminación) recorren los depósitos 1 → 2 → 3 → 1 haciendo controles. Si un depósito está ocupado, esperan a que se libere. Un **Supervisor** revisa los 3 depósitos (18 min cada uno, 10 min de traslado). Si hay un técnico trabajando, lo **interrumpe**, y esa tarea se reinicia cuando el supervisor sale. Después de revisar los 3 depósitos se va y vuelve a las 3 horas.

**Se desea conocer:**
1. Cuántas veces algún servicio tuvo que reiniciar su tarea por coincidir con el supervisor.
2. El total de controles de cada técnico en cada depósito.

## Supuestos del grupo (el enunciado no los especifica)

| Supuesto | Decisión |
|---|---|
| Depósito inicial | Parámetro. Por defecto T = 1, I = 2 y Supervisor = 3. No pueden repetirse en la primera pasada. |
| Pasadas siguientes del supervisor | El depósito inicial se sortea con una distribución discreta equiprobable (0,33 / 0,33 / 0,34). Después sigue el recorrido circular (por ejemplo 2 → 3 → 1). |
| Recorrido | Todos siguen el orden circular 1 → 2 → 3 → 1 desde donde arrancan. |
| Regreso del supervisor | 180 min contados desde que **termina de revisar el 3er depósito**. |
| Reinicio por interrupción | La tarea se reinicia con una **demora nueva**. Para T se sortean de nuevo la U[5;9) **y** el 30% del tiempo extra. |
| Orden al salir el supervisor | Entra primero el técnico **interrumpido** y después el que estaba en la cola. |
| Rnd | Se trunca a 2 decimales (así nunca vale 1,00). |
| Eventos simultáneos | Primero los fines (liberan depósitos), después las llegadas. El supervisor llega antes que los técnicos. |
| Conteo de controles | Un control se cuenta cuando **termina**. Una tarea interrumpida no se cuenta. |

## Objetos

| Objeto | Tipo | Estados | Otros atributos |
|---|---|---|---|
| Técnico T | Permanente | En tarea · Trasladándose · En cola · Interrumpido | depósito (actual o destino), controles por depósito, reinicios |
| Técnico I | Permanente | En tarea · Trasladándose · En cola · Interrumpido | depósito (actual o destino), controles por depósito, reinicios |
| Supervisor | Permanente | Revisando · Trasladándose · Fuera del predio | depósito, depósitos revisados en la pasada (0 a 3) |
| Depósito 1, 2 y 3 | Permanente (servidores) | Libre · Control temperatura · Control iluminación · Supervisión | cola, técnico interrumpido |

No hay objetos temporales: no entran ni salen clientes del sistema.

## Eventos

| Evento | Qué pasa |
|---|---|
| Inicialización | Cada uno empieza en su depósito y se generan las primeras demoras. |
| Fin tarea T / Fin tarea I | Se suma el control. Se libera el depósito y entra el que esperaba. El técnico se traslada al siguiente depósito. |
| Llegada T / Llegada I | Si el depósito está libre, empieza la tarea (con una demora nueva). Si no, pasa a la cola. |
| Llegada Supervisor | Si hay un técnico trabajando, lo interrumpe (reinicios + 1). Empieza la revisión de 18 min. |
| Fin revisión Supervisor | Libera el depósito: primero entra el interrumpido y después la cola. Si ya revisó 3 depósitos, se va por 180 min; si no, se traslada (10 min). |
| Regreso Supervisor | Sortea por qué depósito empieza y llega a ese depósito. |
| Fin de simulación | Ocurre en el instante X, o al llegar a 100.000 iteraciones. |

## Colas

Hay una cola por depósito, con disciplina FIFO. Por delante de la cola está el técnico interrumpido, que tiene prioridad. Como hay 2 técnicos, en cada depósito puede haber como máximo 1 técnico interrumpido y 1 en cola.

## Variables aleatorias y fórmulas

Generador congruencial mixto (único y compartido por todas las variables):

```
X(n+1) = (1714 · X(n) + 1221) mod 3922        X0 = 1234
Rnd    = trunc(X / 3922, 2 decimales)
```

> El período de este generador es **468** (menor que m = 3922) porque no cumple Hull-Dobell: mcd(1221, 3922) = 37 ≠ 1. La app lo muestra en la pestaña "Generador".

| Variable | Distribución | Fórmula usada |
|---|---|---|
| Demora del Técnico T | U[5; 9) | `demora = 5 + (9 − 5) · Rnd` |
| ¿Tiempo extra? (solo Dep 1 y 2) | Bernoulli p = 0,30 | `Rnd < 0,30 → Sí (+3 min)`, si no `No` |
| Depósito inicial del supervisor (desde la 2da pasada) | Discreta equiprobable | `Rnd < 0,33 → 1`; `Rnd < 0,66 → 2`; si no `3` |

Son constantes (no aleatorias): la demora de I (5 min), la del supervisor (18 min), los traslados y el regreso (180 min).

## Fórmulas de lo que se desea conocer

- **Reinicios** = cantidad de eventos "Llegada Supervisor" en los que el depósito tenía un técnico **En tarea**. Se suma 1 en cada uno, separado por técnico.
- **Controles[técnico][depósito]** = cantidad de eventos "Fin tarea" de ese técnico en ese depósito.
