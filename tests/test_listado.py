"""Lo que se afirma del cartucho, comprobado contra sus bytes.

No se comprueba contra el listado generado -que podria estar mal por la misma
razon que lo estuviera la afirmacion- sino contra la ROM, ejecutando las
maquinas del propio cartucho: el interprete de guiones (tools/guiones.py), el
descompresor (tools/rle.py) y la maquina de escenas (tools/escenas.py).

El invariante que mas vale es el ENCAJE: si el formato estuviera mal leido, un
bloque no acabaria clavado donde empieza el siguiente.
"""

import os
import re
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

ROM = os.path.join(RAIZ, "circus.rom")
ASM = os.path.join(RAIZ, "src", "circus.asm")
ORG = 0x4000

# Las filas de datos del listado, con su direccion en el comentario. Es lo que
# permite que estas comprobaciones corran en un clon pelado: el cartucho NO
# viaja con el repositorio, pero el listado SI, y ahi dentro esta cada byte de
# cada bloque de datos con su direccion al lado.
FILA = re.compile(r"^\s+def(b|w)\s+([0-9a-fA-F,h ]+)\s*;\s*([0-9a-f]{4})")


def imagen_desde_el_listado():
    """Rehace los 16 KB a partir de las filas defb/defw de src/circus.asm.

    Los tramos de CODIGO quedan a cero: aqui no se comprueba ni una sola cosa
    del codigo, solo de los datos -guiones, bloques comprimidos, tablas,
    cabecera y registros del VDP-, que son justamente los que salen como
    defb/defw. Si algun dia hiciera falta comprobar codigo, este atajo no
    valdria y habria que exigir la ROM.
    """
    img = bytearray(16384)
    with open(ASM, encoding="utf-8") as f:
        for ln in f:
            m = FILA.match(ln)
            if not m:
                continue
            ancho, cuerpo, dirr = m.group(1), m.group(2), int(m.group(3), 16)
            p = dirr - ORG
            for tok in cuerpo.split(","):
                tok = tok.strip().rstrip("h")
                if not tok:
                    continue
                v = int(tok, 16)
                if ancho == "b":
                    img[p] = v
                    p += 1
                else:
                    img[p] = v & 0xFF
                    img[p + 1] = v >> 8
                    p += 2
    return bytes(img)


def hay_datos():
    return os.path.exists(ROM) or os.path.exists(ASM)


def lee():
    """El cartucho si esta, y si no la imagen rehecha desde el listado."""
    if os.path.exists(ROM):
        with open(ROM, "rb") as f:
            return f.read()
    return imagen_desde_el_listado()


class Cabecera(unittest.TestCase):
    def test_es_un_cartucho_msx(self):
        rom = lee()
        self.assertEqual(rom[:2], b"AB")
        self.assertEqual(len(rom), 16384)

    def test_init_es_407b(self):
        rom = lee()
        self.assertEqual(rom[2] | (rom[3] << 8), 0x407B)

    def test_las_otras_tres_entradas_estan_a_cero(self):
        """STATEMENT, DEVICE y TEXT. El cartucho solo usa INIT."""
        rom = lee()
        self.assertEqual(rom[4:10], b"\x00" * 6)


class RegistrosDelVdp(unittest.TestCase):
    """Los ocho bytes de 0x4722 que L_4708 vuelca en R0..R7."""

    def setUp(self):
        self.r = lee()[0x4722 - ORG:0x472A - ORG]

    def test_son_los_ocho_medidos(self):
        self.assertEqual(self.r, bytes([0x02, 0xE2, 0x0E, 0x7F, 0x07, 0x76, 0x03, 0xE1]))

    def test_es_screen_2(self):
        """R0 bit 1 (M3) puesto y R1 bits 3-4 (M1,M2) a cero."""
        self.assertTrue(self.r[0] & 0x02)
        self.assertFalse(self.r[1] & 0x18)

    def test_sprites_de_16x16_sin_ampliar(self):
        self.assertTrue(self.r[1] & 0x02)       # SI: 16x16
        self.assertFalse(self.r[1] & 0x01)      # MAG: sin ampliar

    def test_la_tabla_de_nombres_esta_en_3800(self):
        self.assertEqual(self.r[2] * 0x400, 0x3800)

    def test_los_patrones_de_sprites_estan_en_1800(self):
        self.assertEqual(self.r[6] * 0x800, 0x1800)

    def test_los_atributos_de_sprites_estan_en_3b00(self):
        self.assertEqual(self.r[5] * 0x80, 0x3B00)


class TablasDelDespachador(unittest.TestCase):
    """Las cinco tablas pegadas detras de un `call L_404E`.

    El encaje que las fija: ninguna entrada puede caer DENTRO de la tabla, y la
    mas baja marca donde acaba, porque el codigo al que apunta viene detras.
    """

    TABLAS = {0x40C7: 17, 0x4C93: 5, 0x4CEA: 5, 0x5FEF: 5, 0x60B6: 5}

    def entradas(self, ini, n):
        rom = lee()
        p = ini - ORG
        return [rom[p + 2 * i] | (rom[p + 2 * i + 1] << 8) for i in range(n)]

    def test_toda_entrada_cae_dentro_del_cartucho(self):
        for ini, n in self.TABLAS.items():
            for e in self.entradas(ini, n):
                self.assertTrue(ORG <= e < ORG + 16384,
                                f"tabla 0x{ini:04X}: 0x{e:04X} se sale")

    def test_ninguna_entrada_cae_dentro_de_su_tabla(self):
        for ini, n in self.TABLAS.items():
            fin = ini + 2 * n
            for e in self.entradas(ini, n):
                self.assertFalse(ini <= e < fin,
                                 f"tabla 0x{ini:04X}: 0x{e:04X} cae dentro")

    def test_la_de_escenas_cierra_donde_apunta_su_primera_entrada(self):
        """0x40C7 + 17*2 = 0x40E9, y la primera palabra es 0x40E9."""
        self.assertEqual(self.entradas(0x40C7, 17)[0], 0x40C7 + 17 * 2)


class Guiones(unittest.TestCase):
    """El interprete de rotulos de 0x4066, ejecutado."""

    def texto(self, tramos):
        return ["".join(chr(b + 0x20) for b in cuerpo) for _, cuerpo in tramos]

    def test_los_rotulos_que_se_leen(self):
        from guiones import ejecuta
        rom = lee()
        esperado = {
            0x4255: ["CONTINUE"],
            0x49BD: ["2P@"],
            0x4A48: ["PLAYER 1"],
            0x4A53: ["@ VIDEO CARTRIDGE @"],
        }
        for ini, textos in esperado.items():
            fin, tramos = ejecuta(rom, ORG, ini)
            self.assertIsNotNone(fin, f"el guion de 0x{ini:04X} no cierra")
            self.assertEqual(self.texto(tramos), textos)

    def test_el_marcador_trae_sus_cuatro_rotulos(self):
        from guiones import ejecuta
        fin, tramos = ejecuta(lee(), ORG, 0x499F)
        self.assertEqual(fin, 0x49BD)
        self.assertEqual(self.texto(tramos), ["HI@", "STAGE@", "BONUS@", "1P@"])

    def test_el_menu_dice_play_select(self):
        from guiones import ejecuta
        fin, tramos = ejecuta(lee(), ORG, 0x49C3)
        self.assertEqual(fin, 0x4A3B)
        self.assertEqual(self.texto(tramos)[0], "PLAY SELECT")


class BloquesComprimidos(unittest.TestCase):
    """El descompresor de 0x45C9, ejecutado.

    Que los bloques encadenen sin dejar un byte suelto es LA prueba de que el
    formato esta bien leido: con el lenguaje mal entendido, el descompresor se
    pararia en cualquier sitio menos en el borde del siguiente.
    """

    CADENA = [0x61BA, 0x6547, 0x67A1, 0x68BD, 0x6968]

    def test_la_cadena_de_graficos_encaja_sin_huecos(self):
        from rle import descomprime
        rom = lee()
        for ini, siguiente in zip(self.CADENA, self.CADENA[1:]):
            fin, _ = descomprime(rom, ORG, ini, True)
            self.assertEqual(fin, siguiente,
                             f"0x{ini:04X} acaba en 0x{fin:04X}, no en 0x{siguiente:04X}")

    def test_los_destinos_de_vram_caen_donde_dicen_los_registros(self):
        """0x5800 es 0x1800: SETWRT se queda con los catorce bits de abajo, y
        0x1800 es justo donde R6 pone los patrones de sprites."""
        from rle import descomprime
        _, tramos = descomprime(lee(), ORG, 0x61BA, True)
        self.assertEqual(tramos[0][0] & 0x3FFF, 0x1800)

    def test_el_bloque_de_color_de_la_pantalla_llena_512_bytes(self):
        from rle import descomprime
        fin, tramos = descomprime(lee(), ORG, 0x47DE, True)
        self.assertEqual(fin, 0x4956)
        self.assertEqual(sum(len(c) for _, c in tramos), 512)


class LasDosPantallasDeMenu(unittest.TestCase):
    """Las dos pantallas que graficos.py monta desde la ROM, y que NO son la
    misma: la de LA CASA (logotipo de KONAMI y "- VIDEO CARTRIDGE -") y la de
    TITULO (el menu con "PLAY SELECT").

    Contra un volcado del emulador las dos dan CERO bytes de diferencia en las
    cuatro tablas; eso se comprueba con tools/coteja_vram.py, que necesita el
    volcado. Lo de aqui es lo que se puede atar sin emulador: donde acaba cada
    cosa, que es lo que costo averiguar.
    """

    def monta(self, cual):
        import graficos
        graficos.ORG = ORG
        return getattr(graficos, cual)(lee())

    def celda(self, v, fila, col):
        return v.b[0x3800 + fila * 32 + col]

    def test_el_logotipo_acaba_en_la_fila_4_columna_10(self):
        """Diecisiete pasadas y el reflejo respecto de 0x3AAA dejan las tres
        franjas en 0x388A. Las celdas son patrones CORRELATIVOS del 0x41 al
        0x5A, en filas de 3, 11 y 12."""
        v = self.monta("vram_de_la_presentacion")
        self.assertEqual([self.celda(v, 4, 10 + i) for i in range(3)],
                         [0x41, 0x42, 0x43])
        self.assertEqual([self.celda(v, 5, 10 + i) for i in range(11)],
                         list(range(0x44, 0x4F)))
        self.assertEqual([self.celda(v, 6, 10 + i) for i in range(12)],
                         list(range(0x4F, 0x5B)))
        self.assertEqual(self.celda(v, 7, 10), 0x00,
                         "la fila de abajo se borra: es el rastro de la pasada"
                         " anterior")

    def test_el_rotulo_de_la_casa_lleva_una_RAYA_a_cada_lado(self):
        """No es un (r) ni una arroba: el tile 0x20 de esta fuente es una raya
        horizontal, y se ve dibujandolo. El rotulo es "- VIDEO CARTRIDGE -"."""
        v = self.monta("vram_de_la_presentacion")
        self.assertEqual(self.celda(v, 11, 6), 0x20)
        self.assertEqual(self.celda(v, 11, 24), 0x20)
        import graficos
        patron, _ = graficos.celda(v, 0x20, 1)
        self.assertEqual(list(patron), [0, 0, 0, 0, 0x7E, 0, 0, 0])

    def test_las_cuatro_opciones_van_de_dos_en_dos_filas(self):
        """El comentario del listado decia CUATRO filas y son DOS: el guion de
        0x49C3 las pinta en la 16, la 18, la 20 y la 22."""
        v = self.monta("vram_de_la_seleccion")
        for fila in (16, 18, 20, 22):
            self.assertNotEqual(self.celda(v, fila, 7), 0,
                                "falta el renglon de la fila %d" % fila)

    def test_el_cursor_sale_de_una_ROTACION_y_no_de_una_division(self):
        """`add a,014h / rrca / rrca`: con la opcion 0 rotar y dividir dan lo
        mismo (0x05), pero con la 1 la rotacion da 0x45 y la division 0x05. Si
        se implementa con un desplazamiento, las cuatro opciones salen en la
        misma fila."""
        import graficos
        self.assertEqual([graficos.donde_va_el_cursor(k) for k in range(4)],
                         [0x3A05, 0x3A45, 0x3A85, 0x3AC5])
        v = self.monta("vram_de_la_seleccion")
        self.assertEqual(self.celda(v, 16, 5), 0x3E)
        self.assertEqual(self.celda(v, 16, 6), 0x3F)

    def test_en_las_pantallas_de_menu_no_hay_un_solo_sprite(self):
        """Por eso se dibujan sin sprites, y por eso la hoja de patrones de
        sprite NO puede salir de aqui: los 2048 bytes de 0x1800 estan a cero.
        Dibujarla desde esta VRAM daba una lamina entera negra."""
        v = self.monta("vram_de_la_presentacion")
        self.assertEqual(set(v.b[0x1800:0x2000]), {0},
                         "en la pantalla de titulo no hay patrones de sprite")

    def test_los_sprites_salen_de_su_propio_par_de_bloques(self):
        """0x5FD6 descomprime 0x61BA y 0x5FCF, y ahi si hay dibujos."""
        v = self.monta("vram_con_los_sprites")
        self.assertNotEqual(set(v.b[0x1800:0x2000]), {0})


class ElMotorDeEscenas(unittest.TestCase):
    """La maquina de 0x6A42 EJECUTADA, no solo medida.

    tools/escenas.py medía donde acaba cada escena; ahora ademas la pinta, que
    es lo que hace falta para dibujar un nivel desde la ROM. La lectura que
    faltaba estaba en 0x6A1E: un `ex de,hl` pone HL en el BUFER y DE en el
    guion, asi que los ocho bytes que se escriben salen del bufer
    descomprimido y no del guion; la mascara solo dice CUALES de los ocho
    patrones se vuelcan, y el bufer avanza ocho se escriban o no.

    Medido contra los volcados del emulador: lo que esta escena escribe
    coincide al 100 % con la atraccion del monociclo y al 96 % con otras tres
    -la diferencia es lo que cada atraccion pinta encima-.
    """

    def test_la_escena_del_nivel_acaba_donde_empieza_la_siguiente(self):
        import escenas
        v = bytearray(0x4000)
        self.assertEqual(escenas.monta(lee(), ORG, 0x6BE3, v, 0x42), 0x6D1A)

    def test_pintar_no_cambia_donde_acaba(self):
        """El recorrido que mide y el que pinta tienen que dar lo mismo: si no,
        uno de los dos esta leyendo el guion de otra manera."""
        import escenas
        for ini, var in ((0x6BE3, 0x42), (0x6DC1, 0x33), (0x7155, 0x42),
                         (0x71EB, 0x42), (0x72ED, 0x42), (0x73C2, 0x42),
                         (0x7498, 0x42)):
            v = bytearray(0x4000)
            self.assertEqual(escenas.monta(lee(), ORG, ini, v, var),
                             escenas.escena(lee(), ORG, ini, var)[0],
                             "la escena 0x%04X no acaba igual" % ini)

    def test_la_escena_escribe_en_la_tabla_de_patrones(self):
        """Y no en cualquier sitio: el destino sale de (D,E)*8 con el bit 14
        puesto, que es la marca de escritura del VDP."""
        import escenas
        v = bytearray(0x4000)
        escenas.monta(lee(), ORG, 0x6BE3, v, 0x42)
        tocados = [a for a in range(0x4000) if v[a]]
        self.assertTrue(tocados, "la escena no ha escrito nada")
        self.assertTrue(all(0x2000 <= a < 0x3800 for a in tocados),
                        "hay escrituras fuera de la tabla de patrones")


class ElVdpPintaCuatroSpritesPorLinea(unittest.TestCase):
    """El tope de sprites del TMS9918, que es lo unico que separaba a
    tools/vram.py de la pantalla de verdad.

    El VDP recorre la lista de la 0 a la 31 y, en cuanto encuentra el QUINTO
    sprite que cruza la linea que esta pintando, lo anota en el registro de
    estado y no pinta ni ese ni los que vengan detras. Pintarlos todos es
    dibujar una pantalla que la maquina no puede dar: en Circus Charlie son
    SEIS los que cruzan las lineas 48 a 52 del acto del trapecio, y el
    hardware se come dos.

    Estos no necesitan el cartucho ni el emulador: se fabrica una VRAM a mano.
    El cotejo contra el emulador de verdad es tools/coteja_pixels.py.
    """

    REGS = [0x02, 0xE2, 0x0E, 0x7F, 0x07, 0x76, 0x03, 0xE1]

    def vram_con(self, sprites, grande=True):
        """Una VRAM vacia con los sprites pedidos, cada uno de un color."""
        v = bytearray(16384)
        regs = list(self.REGS)
        regs[1] = 0xE2 if grande else 0xE0
        attr = regs[5] * 0x80
        base = regs[6] * 0x800
        for i in range(32 * 4):             # 0xD0 corta la lista: lista vacia
            v[attr + i] = 0xD0
        for n, (y, x, col) in enumerate(sprites):
            v[attr + n * 4] = y
            v[attr + n * 4 + 1] = x
            v[attr + n * 4 + 2] = 0
            v[attr + n * 4 + 3] = col
        if len(sprites) < 32:
            v[attr + len(sprites) * 4] = 0xD0
        for i in range(32):                 # el patron 0, todo relleno
            v[base + i] = 0xFF
        return bytes(v), regs

    def pinta(self, sprites, grande=True):
        import vram
        v, regs = self.vram_con(sprites, grande)
        fondo = regs[7] & 0x0F
        tela = [[fondo] * 256 for _ in range(192)]
        vram.pinta_sprites(v, regs, tela, fondo)
        return tela

    def test_del_quinto_en_adelante_no_se_pinta(self):
        """Seis sprites en la misma linea: se ven los cuatro primeros."""
        colores = [2, 3, 4, 5, 6, 7]
        tela = self.pinta([(50, 16 * i, c) for i, c in enumerate(colores)])
        vistos = [tela[55][16 * i] for i in range(6)]
        self.assertEqual(vistos, [2, 3, 4, 5, 1, 1],
                         "el quinto y el sexto no los pinta el VDP")

    def test_el_tope_es_por_linea_y_no_por_pantalla(self):
        """Seis sprites repartidos de dos en dos: ninguna linea pasa de cuatro,
        asi que se ven los seis."""
        puestos = [(20, 0, 2), (20, 16, 3), (60, 32, 4),
                   (60, 48, 5), (100, 64, 6), (100, 80, 7)]
        tela = self.pinta(puestos)
        vistos = [tela[y + 5][x] for y, x, _ in puestos]
        self.assertEqual(vistos, [2, 3, 4, 5, 6, 7])

    def test_un_sprite_transparente_gasta_su_plaza(self):
        """El tope lo marca la RANURA OCUPADA, no el punto pintado: el VDP no
        mira el color ni el dibujo, solo si el sprite cruza la linea. Con dos
        transparentes delante, el quinto sigue sin verse."""
        tela = self.pinta([(50, 0, 0), (50, 16, 0), (50, 32, 4),
                           (50, 48, 5), (50, 64, 6)])
        self.assertEqual(tela[55][32], 4)
        self.assertEqual(tela[55][48], 5)
        self.assertEqual(tela[55][64], 1, "es el quinto de la linea")

    def test_el_de_menor_numero_queda_encima(self):
        """Asi es como se hacen las figuras de varios colores en el MSX1:
        solapando sprites de un color cada uno."""
        tela = self.pinta([(50, 0, 6), (50, 0, 11)])
        self.assertEqual(tela[55][4], 6)

    def test_la_lista_se_corta_en_d0(self):
        """Un sprite con y=0xD0 termina la lista, y los de detras no existen:
        por eso los que 'sobran' en la linea no son los mismos si la lista
        acaba antes."""
        import vram
        v, regs = self.vram_con([(50, 16 * i, 2 + i) for i in range(6)])
        v = bytearray(v)
        attr = regs[5] * 0x80
        v[attr + 2 * 4] = 0xD0             # corta en el tercero
        fondo = regs[7] & 0x0F
        tela = [[fondo] * 256 for _ in range(192)]
        vram.pinta_sprites(bytes(v), regs, tela, fondo)
        vistos = [tela[55][16 * i] for i in range(6)]
        self.assertEqual(vistos, [2, 3, 1, 1, 1, 1])


class Escenas(unittest.TestCase):
    """La maquina de 0x6A42: descomprimir a RAM y volcar por mascaras."""

    def test_la_escena_de_6be3_cierra_donde_empieza_la_siguiente(self):
        from escenas import escena
        fin, trozos = escena(lee(), ORG, 0x6BE3, 0x42)
        self.assertEqual(fin, 0x6D1A)
        self.assertEqual(len(trozos), 13)

    def test_la_escena_de_6dc1_va_por_la_otra_puerta(self):
        """0x6D97 la monta con `call L_6A33`, no con 0x6A42: la diferencia es
        que 0x69FB lee un byte de ajuste por fila. Por la puerta equivocada el
        recorrido se pasa de largo, que es justo lo que hace util el test."""
        from escenas import escena
        self.assertEqual(escena(lee(), ORG, 0x6DC1, 0x33)[0], 0x6FA5)
        self.assertNotEqual(escena(lee(), ORG, 0x6DC1, 0x42)[0], 0x6FA5)


if __name__ == "__main__":
    unittest.main()
