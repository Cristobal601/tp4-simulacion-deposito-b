"""Pruebas: python -m unittest discover tests"""

import unittest

from simulacion.generador import GeneradorCongruencial
from simulacion.modelo import Parametros, Simulacion


class TestGenerador(unittest.TestCase):
    def test_primeros_valores(self):
        # X1 = (1714 * 1234 + 1221) mod 3922 = 2339  ->  2339 / 3922 = 0.5963... -> 0.59
        gen = GeneradorCongruencial(1234, 1714, 1221, 3922)
        self.assertEqual(gen.siguiente(), 0.59)
        self.assertEqual(gen.x, 2339)
        self.assertEqual([gen.siguiente() for _ in range(3)], [0.50, 0.92, 0.13])

    def test_nunca_da_uno(self):
        gen = GeneradorCongruencial(1234, 1714, 1221, 3922)
        self.assertTrue(all(0 <= gen.siguiente() < 1 for _ in range(5000)))

    def test_periodo(self):
        self.assertEqual(GeneradorCongruencial(1234, 1714, 1221, 3922).periodo(), 468)


class TestSimulacion(unittest.TestCase):
    def simular(self, **cambios):
        sim = Simulacion(Parametros(**cambios))
        sim.ejecutar()
        return sim

    def test_primeras_filas(self):
        filas = self.simular(filas_i=6).filas_mostradas
        # Inicio: T en Dep 1 con Rnd 0.59 -> 5 + 4 * 0.59 = 7.36, Rnd 0.50 -> sin extra
        self.assertEqual(filas[0]["t_demora"], 7.36)
        self.assertEqual(filas[0]["t_hay_extra"], "No")
        self.assertEqual([f["evento"] for f in filas[1:]], [
            "Fin tarea I (Dep 2)", "Fin tarea T (Dep 1)", "Llegada I (Dep 3)",
            "Llegada T (Dep 2)", "Fin revisión Sup (Dep 3)"])
        # El Tecnico I llega al Dep 3 mientras revisa el supervisor -> cola
        self.assertEqual(filas[3]["i_estado"], "En cola")
        # T en Dep 2: Rnd 0.92 -> 8.68, Rnd 0.13 < 0.30 -> +3 = 11.68 -> fin 29.04
        self.assertEqual(filas[4]["t_fin_tarea"], 29.04)
        # Sale el supervisor: entra I desde la cola
        self.assertEqual(filas[5]["i_estado"], "En tarea")
        self.assertEqual(filas[5]["i_fin_tarea"], 23)

    def test_ultima_fila_en_instante_x(self):
        sim = self.simular(tiempo_x=500)
        self.assertEqual(sim.ultima_fila["reloj"], 500)

    def test_maximo_iteraciones(self):
        sim = self.simular(tiempo_x=10 ** 9, max_iteraciones=1000)
        self.assertEqual(sim.ultima_fila["fila"], 1000)

    def test_nunca_dos_adentro_y_reinicios(self):
        sim = Simulacion(Parametros(tiempo_x=20000))
        sim.inicializar()
        while sim.fila < 5000:
            hora, _, tipo, quien = sim.proximo_evento()
            sim.fila += 1
            sim.reloj = hora
            {"fin_tarea": lambda: sim.fin_tarea(sim.tecnicos[quien]),
             "llegada_tecnico": lambda: sim.llegada_tecnico(sim.tecnicos[quien]),
             "fin_revision": sim.fin_revision,
             "llegada_supervisor": sim.llegada_supervisor,
             "regreso_supervisor": sim.regreso_supervisor}[tipo]()
            # Cada tecnico esta trabajando en un solo deposito como mucho
            for tec in sim.tecnicos.values():
                ocupados = [d for d in sim.depositos.values() if d.ocupante == tec.nombre]
                self.assertEqual(len(ocupados), 1 if tec.estado == "En tarea" else 0)
        self.assertGreater(sim.reinicios_total, 0)
        self.assertEqual(sim.reinicios_total,
                         sim.tecnicos["T"].reinicios + sim.tecnicos["I"].reinicios)

    def test_arranques_repetidos_invalidos(self):
        self.assertTrue(Parametros(inicio_t=1, inicio_i=1).validar())

    def test_valores_por_defecto_validos(self):
        self.assertEqual(Parametros().validar(), [])

    def test_demoras_y_traslados_en_cero_invalidos(self):
        atributos = ("t_min", "t_tras_12", "t_tras_23", "t_tras_31",
                     "i_demora", "i_tras_12", "i_tras_23", "i_tras_31",
                     "s_demora", "s_traslado", "s_regreso")
        for atributo in atributos:
            with self.subTest(atributo=atributo):
                self.assertEqual(len(Parametros(**{atributo: 0}).validar()), 1)

    def test_informa_todos_los_ceros_juntos(self):
        self.assertEqual(len(Parametros(i_demora=0, s_traslado=0, t_tras_12=0).validar()), 3)

    def test_tiempo_extra_en_cero_depende_de_su_probabilidad(self):
        self.assertEqual(len(Parametros(t_extra=0, t_prob_extra=0.3).validar()), 1)
        self.assertEqual(Parametros(t_extra=0, t_prob_extra=0).validar(), [])

    def test_ceros_permitidos(self):
        self.assertEqual(Parametros(desde_hora_j=0, s_prob_1=0, s_prob_2=0.5, s_prob_3=0.5).validar(), [])


if __name__ == "__main__":
    unittest.main()
