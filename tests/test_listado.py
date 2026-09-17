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
