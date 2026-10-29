"""Generador congruencial mixto:  X(n+1) = (a * X(n) + c) mod m

Es el UNICO generador de numeros aleatorios del programa. Todas las variables
aleatorias lo comparten (no usamos el random de Python).
"""


class GeneradorCongruencial:
    def __init__(self, semilla, a, c, m, decimales=2):
        self.semilla = semilla
        self.a = a              # constante multiplicativa
        self.c = c              # constante aditiva
        self.m = m              # modulo
        self.decimales = decimales
        self.x = semilla        # ultimo X generado
        self.usados = 0         # cuantos Rnd se pidieron

    def siguiente(self):
        """Calcula el proximo X y devuelve Rnd = X / m TRUNCADO a 2 decimales.

        Truncamos (en vez de redondear) para que el Rnd nunca valga 1.00.
        """
        self.x = (self.a * self.x + self.c) % self.m
        self.usados += 1
        factor = 10 ** self.decimales
        return (self.x * factor // self.m) / factor

    def secuencia(self, cantidad):
        """Lista de (i, X, Rnd) desde la semilla, para mostrar en la pestaña Generador."""
        copia = GeneradorCongruencial(self.semilla, self.a, self.c, self.m, self.decimales)
        filas = []
        for i in range(1, cantidad + 1):
            rnd = copia.siguiente()
            filas.append((i, copia.x, rnd))
        return filas

    def periodo(self):
        """Cuantos valores distintos genera antes de empezar a repetirse."""
        vistos = {}           # X -> posicion en la que aparecio
        x = self.semilla
        posicion = 0
        while x not in vistos:
            vistos[x] = posicion
            x = (self.a * x + self.c) % self.m
            posicion += 1
        return posicion - vistos[x]
