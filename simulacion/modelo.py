"""Simulacion por eventos discretos del caso "Deposito B".

Objetos permanentes: Tecnico T, Tecnico I, Supervisor y Depositos 1, 2 y 3.
Todos los tiempos estan en MINUTOS y se redondean a 2 decimales.
"""

from dataclasses import dataclass

from simulacion.generador import GeneradorCongruencial


@dataclass
class Parametros:
    # Simulacion
    tiempo_x: float = 1440          # minutos a simular (1440 = 1 dia)
    max_iteraciones: int = 100000
    desde_hora_j: float = 0         # mostrar filas a partir de esta hora...
    filas_i: int = 100              # ...y esta cantidad de filas
    # Generador
    semilla: int = 1234
    a: int = 1714                   # constante multiplicativa
    c: int = 1221                   # constante aditiva
    m: int = 3922                   # modulo
    # Tecnico T (temperatura)
    t_min: float = 5                # demora U[t_min, t_max)
    t_max: float = 9
    t_prob_extra: float = 0.30      # probabilidad de regular equipos (solo dep. 1 y 2)
    t_extra: float = 3              # minutos extra
    t_tras_12: float = 10
    t_tras_23: float = 12
    t_tras_31: float = 13
    # Tecnico I (iluminacion)
    i_demora: float = 5
    i_tras_12: float = 13
    i_tras_23: float = 12
    i_tras_31: float = 13
    # Supervisor
    s_demora: float = 18
    s_traslado: float = 10
    s_regreso: float = 180          # vuelve 3 horas despues de revisar el 3er deposito
    s_prob_1: float = 0.33          # probabilidad de empezar la pasada por cada deposito
    s_prob_2: float = 0.33
    s_prob_3: float = 0.34
    # Depositos donde arranca cada uno (deben ser distintos)
    inicio_t: int = 1
    inicio_i: int = 2
    inicio_s: int = 3

    def validar(self):
        """Devuelve una lista de errores (vacia si todo esta bien)."""
        errores = []
        if self.tiempo_x <= 0:
            errores.append("El tiempo X debe ser mayor que 0.")
        if not 1 <= self.max_iteraciones <= 100000:
            errores.append("Las iteraciones deben estar entre 1 y 100.000.")
        if self.filas_i < 1:
            errores.append("La cantidad de filas i debe ser al menos 1.")
        if not 0 <= self.semilla < self.m:
            errores.append("La semilla debe estar entre 0 y m - 1.")
        if self.t_min >= self.t_max:
            errores.append("En U[a;b) del Técnico T, a debe ser menor que b.")
        if not 0 <= self.t_prob_extra <= 1:
            errores.append("La probabilidad del tiempo extra debe estar entre 0 y 1.")
        if round(self.s_prob_1 + self.s_prob_2 + self.s_prob_3, 6) != 1:
            errores.append("Las probabilidades del supervisor deben sumar 1.")
        if len({self.inicio_t, self.inicio_i, self.inicio_s}) != 3:
            errores.append("El Técnico T, el Técnico I y el Supervisor deben arrancar en depósitos distintos.")
        return errores


def siguiente_deposito(dep):
    """Recorrido circular: 1 -> 2 -> 3 -> 1."""
    return dep % 3 + 1


def formatear_dia_hora(minutos):
    """1500.5 -> 'Día 2 01:00'"""
    dia = int(minutos // 1440) + 1
    resto = minutos % 1440
    return f"Día {dia} {int(resto // 60):02d}:{int(resto % 60):02d}"


# ---------------------------------------------------------------------------
# Objetos del sistema
# ---------------------------------------------------------------------------

class Tecnico:
    def __init__(self, nombre):
        self.nombre = nombre        # "T" o "I"
        self.estado = ""            # En tarea | Trasladándose | En cola | Interrumpido
        self.deposito = 0           # deposito donde esta (o hacia donde viaja)
        self.fin_tarea = None       # proximo evento: fin de su tarea
        self.llegada = None         # proximo evento: llegada al proximo deposito
        self.controles = {1: 0, 2: 0, 3: 0}
        self.reinicios = 0


class Supervisor:
    def __init__(self):
        self.estado = ""            # Revisando | Trasladándose | Fuera del predio
        self.deposito = 0
        self.revisados = 0          # depositos revisados en la pasada actual (0 a 3)
        self.fin_revision = None    # proximo evento
        self.llegada = None         # proximo evento
        self.regreso = None         # proximo evento


class Deposito:
    def __init__(self, numero):
        self.numero = numero
        self.ocupante = None        # None, "T", "I" o "S"
        self.cola = []              # tecnicos esperando para entrar
        self.interrumpido = None    # tecnico interrumpido por el supervisor

    def estado(self):
        textos = {None: "Libre", "T": "Control temperatura",
                  "I": "Control iluminación", "S": "Supervisión"}
        return textos[self.ocupante]


# ---------------------------------------------------------------------------
# Columnas del vector de estado: (grupo, [(clave, titulo), ...])
# La interfaz y la exportacion a Excel usan esta misma lista.
# ---------------------------------------------------------------------------

COLUMNAS = [
    ("General", [("fila", "Fila"), ("reloj", "Reloj (min)"),
                 ("dia_hora", "Día y hora"), ("evento", "Evento")]),
    ("Técnico T - tarea", [("t_rnd_demora", "RND demora"), ("t_demora", "Demora"),
                           ("t_rnd_extra", "RND extra"), ("t_hay_extra", "¿+ extra?"),
                           ("t_tiempo_tarea", "Tiempo tarea"), ("t_fin_tarea", "Fin tarea")]),
    ("Técnico T - traslado", [("t_tiempo_traslado", "Tiempo traslado"), ("t_llegada", "Llegada")]),
    ("Técnico I - tarea", [("i_tiempo_tarea", "Tiempo tarea"), ("i_fin_tarea", "Fin tarea")]),
    ("Técnico I - traslado", [("i_tiempo_traslado", "Tiempo traslado"), ("i_llegada", "Llegada")]),
    ("Supervisor - eventos", [("s_fin_revision", "Fin revisión"), ("s_tiempo_traslado", "Tiempo traslado"),
                              ("s_llegada", "Llegada"), ("s_regreso", "Regreso"),
                              ("s_rnd_deposito", "RND depósito"), ("s_deposito_sorteado", "Depósito sorteado")]),
    ("Técnico T", [("t_estado", "Estado"), ("t_deposito", "Depósito"), ("t_ctrl_1", "Controles D1"),
                   ("t_ctrl_2", "Controles D2"), ("t_ctrl_3", "Controles D3"), ("t_reinicios", "Reinicios")]),
    ("Técnico I", [("i_estado", "Estado"), ("i_deposito", "Depósito"), ("i_ctrl_1", "Controles D1"),
                   ("i_ctrl_2", "Controles D2"), ("i_ctrl_3", "Controles D3"), ("i_reinicios", "Reinicios")]),
    ("Supervisor", [("s_estado", "Estado"), ("s_deposito", "Depósito"), ("s_revisados", "Revisados en la pasada")]),
    ("Depósito 1", [("d1_estado", "Estado"), ("d1_cola", "Cola"), ("d1_interrumpido", "Interrumpido")]),
    ("Depósito 2", [("d2_estado", "Estado"), ("d2_cola", "Cola"), ("d2_interrumpido", "Interrumpido")]),
    ("Depósito 3", [("d3_estado", "Estado"), ("d3_cola", "Cola"), ("d3_interrumpido", "Interrumpido")]),
    ("Estadísticas", [("reinicios_total", "Reinicios totales")]),
]

# Lista "plana" de claves, en el mismo orden que las columnas
CLAVES = [clave for grupo, columnas in COLUMNAS for clave, titulo in columnas]


# ---------------------------------------------------------------------------
# Simulacion
# ---------------------------------------------------------------------------

class Simulacion:
    def __init__(self, p: Parametros):
        self.p = p
        self.gen = GeneradorCongruencial(p.semilla, p.a, p.c, p.m)
        self.reloj = 0.0
        self.fila = 0
        self.tecnicos = {"T": Tecnico("T"), "I": Tecnico("I")}
        self.sup = Supervisor()
        self.depositos = {1: Deposito(1), 2: Deposito(2), 3: Deposito(3)}
        self.reinicios_total = 0
        self.aux = {}               # valores calculados SOLO en la fila actual (rnd, tiempos)
        self.filas_mostradas = []   # filas desde la hora j (como mucho i filas)
        self.ultima_fila = None     # fila del instante X (o de la ultima iteracion)

    # ---- Bucle principal ---------------------------------------------------

    def ejecutar(self):
        self.inicializar()
        nombre = "Inicialización"
        self.guardar_fila(nombre)

        while self.fila < self.p.max_iteraciones:
            hora, _, tipo, quien = self.proximo_evento()
            if hora > self.p.tiempo_x:
                # El proximo evento cae despues de X: cerramos en el instante X
                self.fila += 1
                self.reloj = self.p.tiempo_x
                self.aux = {}
                self.ultima_fila = self.foto("Fin de simulación")
                return

            self.fila += 1
            self.reloj = hora
            self.aux = {}
            nombre = self.nombre_evento(tipo, quien)

            if tipo == "fin_tarea":
                self.fin_tarea(self.tecnicos[quien])
            elif tipo == "llegada_tecnico":
                self.llegada_tecnico(self.tecnicos[quien])
            elif tipo == "fin_revision":
                self.fin_revision()
            elif tipo == "llegada_supervisor":
                self.llegada_supervisor()
            elif tipo == "regreso_supervisor":
                self.regreso_supervisor()

            self.guardar_fila(nombre)

        # Se llego al maximo de iteraciones antes del tiempo X
        self.ultima_fila = self.foto(nombre)

    def proximo_evento(self):
        """Busca el evento de menor hora.

        Si dos eventos ocurren a la misma hora, se resuelve por prioridad
        (numero mas chico primero): primero se liberan los depositos y el
        supervisor llega antes que los tecnicos.
        """
        T, I, sup = self.tecnicos["T"], self.tecnicos["I"], self.sup
        candidatos = [
            (sup.fin_revision, 0, "fin_revision", "S"),
            (T.fin_tarea, 1, "fin_tarea", "T"),
            (I.fin_tarea, 2, "fin_tarea", "I"),
            (sup.llegada, 3, "llegada_supervisor", "S"),
            (sup.regreso, 4, "regreso_supervisor", "S"),
            (T.llegada, 5, "llegada_tecnico", "T"),
            (I.llegada, 6, "llegada_tecnico", "I"),
        ]
        programados = [ev for ev in candidatos if ev[0] is not None]
        return min(programados)

    def nombre_evento(self, tipo, quien):
        if tipo == "fin_tarea":
            return f"Fin tarea {quien} (Dep {self.tecnicos[quien].deposito})"
        if tipo == "llegada_tecnico":
            return f"Llegada {quien} (Dep {self.tecnicos[quien].deposito})"
        if tipo == "fin_revision":
            return f"Fin revisión Sup (Dep {self.sup.deposito})"
        if tipo == "llegada_supervisor":
            return f"Llegada Sup (Dep {self.sup.deposito})"
        return "Regreso Sup"

    # ---- Eventos -----------------------------------------------------------

    def inicializar(self):
        self.iniciar_tarea(self.tecnicos["T"], self.p.inicio_t)
        self.iniciar_tarea(self.tecnicos["I"], self.p.inicio_i)
        self.sup.deposito = self.p.inicio_s
        self.llegada_supervisor()

    def llegada_tecnico(self, tec):
        tec.llegada = None
        deposito = self.depositos[tec.deposito]
        if deposito.ocupante is None:
            self.iniciar_tarea(tec, tec.deposito)
        else:
            # Hay alguien adentro: espera en la cola del deposito
            deposito.cola.append(tec.nombre)
            tec.estado = "En cola"

    def fin_tarea(self, tec):
        dep = tec.deposito
        tec.controles[dep] += 1
        tec.fin_tarea = None

        # Se libera el deposito y entra el que estaba esperando (si hay)
        self.depositos[dep].ocupante = None
        self.atender_siguiente(self.depositos[dep])

        # El tecnico viaja al siguiente deposito
        tiempo = self.tiempo_traslado(tec.nombre, dep)
        pre = tec.nombre.lower()
        self.aux[f"{pre}_tiempo_traslado"] = tiempo
        tec.estado = "Trasladándose"
        tec.deposito = siguiente_deposito(dep)
        tec.llegada = round(self.reloj + tiempo, 2)

    def llegada_supervisor(self):
        self.sup.llegada = None
        deposito = self.depositos[self.sup.deposito]

        # Si hay un tecnico trabajando, el supervisor lo interrumpe
        if deposito.ocupante in ("T", "I"):
            tec = self.tecnicos[deposito.ocupante]
            tec.estado = "Interrumpido"
            tec.fin_tarea = None        # su tarea se cancela; se reinicia despues
            tec.reinicios += 1
            self.reinicios_total += 1
            deposito.interrumpido = tec.nombre

        deposito.ocupante = "S"
        self.sup.estado = "Revisando"
        self.sup.fin_revision = round(self.reloj + self.p.s_demora, 2)

    def fin_revision(self):
        dep = self.sup.deposito
        self.sup.fin_revision = None
        self.sup.revisados += 1

        self.depositos[dep].ocupante = None
        self.atender_siguiente(self.depositos[dep])

        if self.sup.revisados == 3:
            # Termino la pasada: se va y vuelve en 3 horas
            self.sup.estado = "Fuera del predio"
            self.sup.deposito = 0
            self.sup.regreso = round(self.reloj + self.p.s_regreso, 2)
        else:
            self.aux["s_tiempo_traslado"] = self.p.s_traslado
            self.sup.estado = "Trasladándose"
            self.sup.deposito = siguiente_deposito(dep)
            self.sup.llegada = round(self.reloj + self.p.s_traslado, 2)

    def regreso_supervisor(self):
        """Vuelve al predio: sortea por que deposito empieza la nueva pasada."""
        self.sup.regreso = None
        self.sup.revisados = 0
        rnd = self.gen.siguiente()
        if rnd < self.p.s_prob_1:
            dep = 1
        elif rnd < self.p.s_prob_1 + self.p.s_prob_2:
            dep = 2
        else:
            dep = 3
        self.aux["s_rnd_deposito"] = rnd
        self.aux["s_deposito_sorteado"] = dep
        self.sup.deposito = dep
        self.llegada_supervisor()

    # ---- Auxiliares ----------------------------------------------------------

    def iniciar_tarea(self, tec, dep):
        """El tecnico entra al deposito y se genera su demora (con nuevos Rnd)."""
        self.depositos[dep].ocupante = tec.nombre
        tec.estado = "En tarea"
        tec.deposito = dep

        if tec.nombre == "T":
            rnd = self.gen.siguiente()
            demora = round(self.p.t_min + (self.p.t_max - self.p.t_min) * rnd, 2)
            self.aux["t_rnd_demora"] = rnd
            self.aux["t_demora"] = demora
            extra = 0
            if dep in (1, 2):   # el tiempo extra solo puede pasar en los depositos 1 y 2
                rnd_extra = self.gen.siguiente()
                self.aux["t_rnd_extra"] = rnd_extra
                if rnd_extra < self.p.t_prob_extra:
                    extra = self.p.t_extra
                    self.aux["t_hay_extra"] = "Sí"
                else:
                    self.aux["t_hay_extra"] = "No"
            tiempo = round(demora + extra, 2)
            self.aux["t_tiempo_tarea"] = tiempo
        else:
            tiempo = self.p.i_demora
            self.aux["i_tiempo_tarea"] = tiempo

        tec.fin_tarea = round(self.reloj + tiempo, 2)

    def atender_siguiente(self, deposito):
        """Cuando se libera un deposito: primero el interrumpido, despues la cola."""
        if deposito.interrumpido is not None:
            tec = self.tecnicos[deposito.interrumpido]
            deposito.interrumpido = None
            self.iniciar_tarea(tec, deposito.numero)   # reinicia con demora NUEVA
        elif deposito.cola:
            tec = self.tecnicos[deposito.cola.pop(0)]
            self.iniciar_tarea(tec, deposito.numero)

    def tiempo_traslado(self, nombre, desde):
        p = self.p
        if nombre == "T":
            return {1: p.t_tras_12, 2: p.t_tras_23, 3: p.t_tras_31}[desde]
        return {1: p.i_tras_12, 2: p.i_tras_23, 3: p.i_tras_31}[desde]

    # ---- Vector de estado ------------------------------------------------------

    def guardar_fila(self, evento):
        """Guarda la fila solo si esta dentro de la ventana [hora j, i filas]."""
        if self.reloj >= self.p.desde_hora_j and len(self.filas_mostradas) < self.p.filas_i:
            self.filas_mostradas.append(self.foto(evento))

    def foto(self, evento):
        """Diccionario con TODOS los valores de la fila actual del vector de estado."""
        f = {"fila": self.fila, "reloj": self.reloj,
             "dia_hora": formatear_dia_hora(self.reloj), "evento": evento}
        f.update(self.aux)

        for tec in self.tecnicos.values():
            pre = tec.nombre.lower()
            f[f"{pre}_fin_tarea"] = tec.fin_tarea
            f[f"{pre}_llegada"] = tec.llegada
            f[f"{pre}_estado"] = tec.estado
            f[f"{pre}_deposito"] = tec.deposito
            for dep in (1, 2, 3):
                f[f"{pre}_ctrl_{dep}"] = tec.controles[dep]
            f[f"{pre}_reinicios"] = tec.reinicios

        f["s_fin_revision"] = self.sup.fin_revision
        f["s_llegada"] = self.sup.llegada
        f["s_regreso"] = self.sup.regreso
        f["s_estado"] = self.sup.estado
        f["s_deposito"] = self.sup.deposito or "-"
        f["s_revisados"] = self.sup.revisados

        for num, dep in self.depositos.items():
            f[f"d{num}_estado"] = dep.estado()
            f[f"d{num}_cola"] = ", ".join(dep.cola)
            f[f"d{num}_interrumpido"] = dep.interrumpido or ""

        f["reinicios_total"] = self.reinicios_total
        return f

    def resultados(self):
        T, I = self.tecnicos["T"], self.tecnicos["I"]
        return {
            "tiempo_simulado": self.reloj,
            "iteraciones": self.fila,
            "rnd_usados": self.gen.usados,
            "reinicios_total": self.reinicios_total,
            "reinicios_t": T.reinicios,
            "reinicios_i": I.reinicios,
            "controles_t": dict(T.controles),
            "controles_i": dict(I.controles),
        }
