"""LAS ATRACCIONES EN PISTA, dibujadas desde las tablas del cartucho.

tools/graficos.py monta el decorado de cada atraccion (0x5FD6) y lo coteja a
cero contra openMSX en 0x4C3C. Lo que falta en esas cinco imagenes -Charlie,
su animal y los obstaculos- no lo pone el montaje sino el cuadro de partida,
cuadro a cuadro. Este modulo es ese cuadro, rutina a rutina, en Python: parte
del estado que dejan `limpia_el_estado_de_la_fase` (0x604C) y el arranque de
cada tipo (tabla 0x60B6), y en cada cuadro mueve lo que el juego mueve y pinta
en el bufer de sprites (0xE0B0) y en la tabla de nombres lo que el juego pinta.

Es un cuadro SIN TOCAR EL MANDO: (0xE009) a cero todo el rato. Charlie se queda
en la salida y lo que se mueve es lo que se mueve solo -los aros, los monos,
las bolas, el trapecio, el caballo, que corre aunque no se pulse nada-.

No se ejecuta el cartucho: tools/z80run.py (tools/corre_circus.py) queda como
COTEJO, y tools/coteja_pista.py compara esta RAM y esta VRAM con las suyas
cuadro a cuadro.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import graficos as G            # noqa: E402

ORG = 0x4000

# El reloj de cuadros (0xE003) al montar la atraccion. No sale de la ROM: lo
# pone el tiempo que se pase en el menu. Es el MEDIDO en 0x4C3C por
# tools/omsx_arranque.tcl (work/arranque/tipo_N_c000.ram, igual en los cinco),
# y con el se coteja en tools/coteja_pista.py.
RELOJ = 0xF4


class Pista:
    """La RAM de 0xE000 a 0xE3FF y la VRAM de una atraccion en marcha."""

    def __init__(self, rom, tipo, reloj=RELOJ):
        self.rom = rom
        self.tipo = tipo
        self.ram = bytearray(0x400)
        v = G.vram_de_la_atraccion(rom, tipo)
        G.pinta_el_marcador(v, rom)
        import escenas as E
        self.bufer = bytes(E.BUFER)     # 0xE280, tal como lo deja el montaje
        self.v = v
        self.vram = v.b
        r = self.ram
        # Lo que deja el camino de la partida hasta 0x4C3C
        self.pon(0xE002, 0x40)          # bit 6: partida en marcha (0x40B2)
        self.pon(0xE003, reloj)
        self.pon(0xE050, 0x02)          # vidas (0x416B)
        self.pon(0xE051, 0x01)          # fase 01 en BCD
        self.pon(0xE052, tipo)
        self.pon16(0xE055, 0x06FF)      # la posicion en la pista (0x41E3/0x42F3)
        self.pon16(0xE057, 0x8000)      # la bonificacion, 8000 en BCD (0x42F8)
        # 0x69B6: la referencia del decorado, 0x1000 o 0x6800 segun el dibujo
        self.pon16(0xE14A, 0x6800 if self.que_dibujo_toca() else 0x1000)
        del r
        self.limpia_el_estado_de_la_fase()

    # -- la RAM ---------------------------------------------------------
    def __getitem__(self, a):
        return self.ram[a - 0xE000]

    def pon(self, a, v):
        self.ram[a - 0xE000] = v & 0xFF

    def lee16(self, a):
        return self[a] | (self[a + 1] << 8)

    def pon16(self, a, v):
        self.pon(a, v)
        self.pon(a + 1, v >> 8)

    def rom8(self, a):
        return self.rom[a - ORG]

    # -- 0x57A8 -----------------------------------------------------------
    def que_dibujo_toca(self):
        """Z puesto (True) en los tipos 0 y 2: los del otro dibujo."""
        return self.tipo in (0, 2)

    # -- 0x604C -----------------------------------------------------------
    def limpia_el_estado_de_la_fase(self):
        ref = self.lee16(0xE14A)
        for a in range(0xE130, 0xE1D0):              # 0x6050: 2 x 80 bytes
            self.pon(a, 0)
        self.pon16(0xE14A, ref)
        for a in range(0xE0B0, 0xE130):              # 0x605F: 128 x 0xC3
            self.pon(a, 0xC3)
        for i in range(16):                          # 0x6069, y 0x6074 sigue
            self.pon(0xE0E0 + i, self.rom8(0x6D63 + i))    # donde lo dejo
            self.pon(0xE120 + i, self.rom8(0x6D73 + i))    # el primer ldir
        if self.que_dibujo_toca():                   # 0x6081: +0x58 a la FILA
            for s in range(20):
                a = 0xE0E0 + 4 * s
                if self[a] != 0xC3:
                    self.pon(a, self[a] + 0x58)
        for i in range(20):                          # 0x6095: desde 0x6D83
            self.pon(0xE0B0 + i, self.rom8(0x6D83 + i))
        self.reparte_la_lista_de_siete(0x619D)       # 0x609C
        self.pon(0xE210, 0x02)                       # 0x60A2
        self.pon(0xE14C, self[0xE14C] - 1)           # 0x60A7
        self.pon(0xE14D, 0xA0)
        [self.arranque_0, self.arranque_1, self.arranque_2,
         self.arranque_3, self.arranque_4][self.tipo]()

    def reparte_la_lista_de_siete(self, de):
        """0x61AB: siete colores, uno por sprite desde 0xE0C7."""
        for i in range(7):
            self.pon(0xE0C7 + 4 * i, self.rom8(de + i))

    # -- los cinco arranques de 0x60B6 ------------------------------------
    def arranque_1(self):
        """0x60C0, el leon: cuatro aros a la fila 0x48 y el jugador en 0x85."""
        self.reparte_la_lista_de_siete(0x6196)
        for i in range(4):
            a = 0xE150 + 2 * i
            self.pon(a, self[a] - 1)
            self.pon(a + 1, 0x48)
        self.pon16(0xE160, 0x800F)
        self.jugador_en(0x85)

    def jugador_en(self, fila):
        """0x60D8 / 0x6115: el jugador, sus tres bytes."""
        self.pon(0xE130, fila)
        self.pon(0xE131, 0x3C)
        self.pon(0xE132, 0x00)

    def arranque_0(self):
        """0x6161, el trapecio: el jugador en (0x2E, 0x3C) en el estado 2 -ya
        colgado-, y el ritmo de las dos figuras puesto a mano."""
        self.pon(0xE130, 0x2E)
        self.pon(0xE131, 0x3C)
        self.pon(0xE132, 0x00)
        self.pon(0xE134, 0x02)
        self.pon(0xE14D, 0x48)
        self.pon(0xE1C0, 0x01)
        self.pon(0xE1CA, 0x80)
        for i, b in enumerate((0x41, 0x90, 0x83, 0xA0)):
            self.pon(0xE1E0 + i, b)

    def arranque_2(self):
        """0x60F2, la cuerda floja: el suelto -el mono que salta- en (0xD0,
        0x50) con su plazo, la rampa de 0x59FA, y el jugador en 0x3F."""
        for i, b in enumerate((0xD0, 0x50, 0x50, 0x0D)):
            self.pon(0xE1B0 + i, b)
        self.pon16(0xE1B6, 0x59FA)
        self.pon(0xE1BA, 0x40)
        self.pon(0xE217, 0x40)
        self.pon(0xE14D, 0x48)
        self.pon_al_jugador_en_su_sitio(0x3F)

    def pon_al_jugador_en_su_sitio(self, fila):
        """0x6115, y detras 0x6128: los tres primeros recogibles un paso a
        la izquierda y el primero en marcha (0x0F, 0xA0)."""
        self.jugador_en(fila)
        for a in (0xE170, 0xE172, 0xE174):
            self.pon(a, self[a] - 1)
        self.pon16(0xE180, 0xA00F)

    def arranque_3(self):
        """0x6139, las bolas: el jugador en 0x7E, y el septimo -la bola en la
        que va subido- con el mismo 0x7E en (0xE18C)."""
        self.pon(0xE18C, 0x7E)
        self.pon_al_jugador_en_su_sitio(0x7E)

    def arranque_4(self):
        """0x6142, el caballo: el guion de la cola (0x5C8E) en sus dos
        punteros, la primera pieza a un cuadro, la velocidad 0x50."""
        self.reparte_la_lista_de_siete(0x61A4)
        self.pon16(0xE26C, 0x5C8E)
        self.pon16(0xE25A, 0x5C8E)
        self.pon(0xE26E, 0x01)
        self.pon(0xE270, 0x50)
        self.pon(0xE272, 0x00)
        self.jugador_en(0x85)

    # -- EL CUADRO ---------------------------------------------------------
    def cuadro(self):
        """Un cuadro de la escena 9 hasta el vuelco de sprites de 0x4CA9."""
        self.pon(0xE003, self[0xE003] + 1)           # 0x40AB
        # 0x4C51 limita_los_mandos: sin mando no hay nada que recortar
        self.remata_el_cuadro_del_jugador()
        self.despacha_por_tipo_de_fase()

    def tras_el_vuelco(self):
        """Lo que 0x40B4 apila detras de la escena: el parpadeo del 1P."""
        self.parpadea_el_turno()

    def remata_el_cuadro_del_jugador(self):
        """0x4C6D: con estado < 6, solo se despacha fuera de la fase 0."""
        if self[0xE134] >= 6 or self.tipo != 0:
            self.despacha_el_estado_del_jugador()

    def despacha_el_estado_del_jugador(self):
        e = self[0xE134]
        if e == 0:
            self.estado_0_corriendo()
        elif e == 2:                     # 0x4F10: sin boton, a 0x4F67
            self.estado_2_la_voltereta()
        else:
            raise NotImplementedError("estado %d" % e)

    def estado_0_corriendo(self):
        """0x4EA7 sin direccion pulsada: el dibujo 1, salvo en la fase 4."""
        if self.tipo == 4:                           # 0x4EBC: corre siempre
            hl = (self.lee16(0xE137) + 0xC0) & 0xFFFF
            self.pon16(0xE137, hl)
            self.pon(0xE132, ((hl >> 8) & 0x0C) >> 2)
        else:
            self.pon(0xE132, 0x01)
        if self.tipo == 3 and self.mira_si_pisa_el_borde():
            raise NotImplementedError("la caida de la fase 3 (estado 6)")
        # 0x4EE5: sin boton no hay salto; 0x4E74 sin gesto -> mira_los_choques,
        # que sin choque acaba en dibuja_al_jugador (0x4FEA)
        self.dibuja_al_jugador()

    def estado_2_la_voltereta(self):
        """0x4F67: colgado del trapecio. Solo en los cuadros en que el trapecio
        cumple un paso: la altura sale de la curva (0x521D o 0x5227) y la pose
        del paso, reflejado pasada la mitad. Y entonces se dibuja."""
        if not self[0xE1F2]:
            return
        curva = 0x5227 if self[0xE1E0] & 2 else 0x521D
        paso = self[0xE1C0]
        self.pon(0xE130, self.rom8(curva + (paso & 0x0F)))
        a = paso & 0x1F
        if a >= 0x10:
            a = ((~a & 0xFF) - 5) & 0x1F
        self.pon(0xE132, 3 if a >= 7 else (1 if a >= 4 else 0))
        self.dibuja_al_jugador()                     # 0x4FA5, fase 0 -> 0x4FEA

    def dibuja_al_jugador(self):
        """0x5087."""
        b, c, pose = self[0xE130], self[0xE131], self[0xE132]
        if pose & 1:
            b = (b + 1) & 0xFF
        if self.tipo == 1:
            de = 0x5116 + pose * 7          # 0x50A4: por SIETE, no por ocho
        else:
            de = 0x513D + pose * 4
        hl = 0xE0C4
        hl, de = self.mete_sprite_con_patron(hl, b, c, de, 2)
        b = (b + 0x10) & 0xFF
        hl, de = self.mete_sprite_con_patron(hl, b, c, de, 2)
        if self.tipo == 4:
            self.dibuja_al_jugador_de_la_fase_4(hl, c)
            return
        if self.tipo != 1:
            return
        b = (b + 0x10) & 0xFF
        c = (c - 8) & 0xFF
        hl, de = self.mete_sprite_con_patron(hl, b, c, de, 1)
        c = (c + 0x10) & 0xFF
        self.mete_sprite_con_patron(hl, b, c, de, 2)

    def dibuja_al_jugador_de_la_fase_4(self, hl, c):
        """0x50D8: el caballo, tres sprites; su galope sale del reloj -uno de
        cada cuatro cuadros, cuatro poses de tres patrones en 0x5155-."""
        de = 0x5155 + ((self[0xE003] >> 2) & 3) * 3
        if self[0xE134] >= 6:
            raise NotImplementedError("el caballo sin jinete")
        c = (c - 5) & 0xFF
        hl, de = self.mete_sprite_con_patron(hl, 0xA6, c, de, 1)
        c = (c + 0x10) & 0xFF
        hl, de = self.mete_sprite_con_patron(hl, 0xA6, c, de, 1)
        self.mete_sprite_con_patron(hl, 0x96, c, de, 1)

    def mete_sprite_con_patron(self, hl, b, c, de, n):
        """0x510C (y 0x5109, que mete dos): fila, columna y patron de (DE)."""
        for _ in range(n):
            self.pon(hl, b)
            self.pon(hl + 1, c)
            self.pon(hl + 2, self.rom8(de))
            de += 1
            hl += 4
        return hl, de

    def despacha_por_tipo_de_fase(self):
        """0x4C81."""
        if self.tipo & 3:
            self.cuenta_el_paso()
        self.baja_la_bonificacion_cada_ocho()
        if self.tipo == 0:                           # 0x4CC2, y a 0x4CA9
            self.avanza_la_animacion_grande()
            self.despacha_el_estado_del_jugador()
            self.mueve_la_figura_grande()
            self.avanza_la_segunda_figura()
            self.repinta_lo_que_sujeta()
            if self[0xE134] != 2:                    # 0x5EDB
                raise NotImplementedError("el relevo de la segunda figura")
            return
        if self.tipo == 1:                           # 0x4C9D
            self.mueve_el_decorado()
            self.mueve_los_tres_moviles()
        elif self.tipo == 2:                         # 0x4CBA
            self.mueve_los_seis_recogibles()
            self.mueve_el_suelto()
        elif self.tipo == 3:                         # 0x4CB5
            self.mueve_los_seis_recogibles()
        elif self.tipo == 4:                         # 0x4CD6, y a 0x4CA9
            c = self.mueve_lo_que_se_empuja()
            self.saca_la_siguiente_de_la_cola(c)
            self.mira_la_cola_contra_el_jugador()
            self.pinta_la_cola()
            return
        else:
            raise NotImplementedError
        self.pinta_el_borde_del_decorado()           # 0x4CA3
        self.desplaza_el_decorado()

    def cuenta_el_paso(self):
        """0x56B3: sin direccion pulsada, nada."""

    def baja_la_bonificacion_cada_ocho(self):
        """0x528A: uno de cada ocho cuadros, 10 menos en BCD, y se pinta."""
        if self[0xE003] & 7:
            return
        lo = self[0xE057]
        a, cy = bcd_resta(lo, 0x10)
        self.pon(0xE057, a)
        if cy:
            a, _ = bcd_resta(self[0xE058], 0x01)
            self.pon(0xE058, a)
        G.imprime_bcd(self.v, 0x3832, (self[0xE058], self[0xE057]))

    def que_direccion_se_pulsa(self):
        """0x534D: -1, 0 o 1. Sin mando, 0."""
        return 0

    def mueve_el_decorado(self):
        """0x536F: con la posicion por encima de 0x0550 no hay nada que hacer."""
        hl = (self.lee16(0xE055) + 0xFFB0) & 0xFFFF
        if (hl >> 8) >= 5:
            return
        raise NotImplementedError

    def mueve_los_tres_moviles(self):
        """0x5416."""
        ix, de, hl = 0xE160, 0xE100, 0xE150
        for b in (3, 2, 1):
            if self[ix]:
                de = self.mueve_el_movil_activo(ix, de, hl)
            else:
                de = self.arranca_movil_parado(ix, de, hl, b)
            hl += 2
            ix += 2

    def mueve_el_movil_activo(self, ix, de, hl):
        """0x5505. Devuelve el hueco de sprite siguiente."""
        b = self.que_direccion_se_pulsa()
        c = self[0xE003]
        a = (0xFF if c & 1 else 0) + b
        a &= 0xFF
        if a == 0:
            return self.quita_el_movil(ix, de, hl)
        a = (a + self[hl]) & 0xFF
        self.pon(hl, a)
        if a < 2:
            raise NotImplementedError("suma_los_tres_moviles")
        self.mete_el_movil_en_los_sprites(ix, hl)
        de = self.quita_el_movil(ix, de, hl)
        if self[ix] & 0x80:
            tabla, bc = 0x7026, 0x0608
        else:
            tabla, bc = 0x6FEA, 0x060A
        self.pinta_el_movil(hl, tabla, bc)
        return de

    def pinta_el_movil(self, hl, tabla, bc):
        """0x5537: el aro, de tiles, con uno de cuatro ajustes (0x6FE6)."""
        e, d = self[hl], self[hl + 1]
        ajuste = self.rom8(0x6FE6 + ((e & 6) >> 1))
        celda = G.celda_de_la_posicion(d, e)
        self.vuelca_recortando_por_el_borde(celda, bc, ajuste, tabla)

    def vuelca_recortando_por_el_borde(self, celda, bc, ajuste, hl):
        """0x5551: C filas de B celdas, cortadas en el borde derecho; cada
        indice lleva sumado el ajuste, y si desborda se le da la vuelta."""
        ancho, filas = bc >> 8, bc & 0xFF
        cabe = (-((celda & 0xFF) | 0xE0)) & 0xFF
        salta = 0
        if cabe < ancho:
            salta = ancho - cabe
            ancho = cabe
        for _ in range(filas):
            for i in range(ancho):
                a = self.rom8(hl) + ajuste
                hl += 1
                if a > 0xFF:
                    a = (a + ajuste) & 7
                self.vram[(celda + i) & 0x3FFF] = a & 0xFF
            hl += salta
            celda += 0x20

    def mete_el_movil_en_los_sprites(self, ix, hl):
        """0x55B0."""
        a = self[hl]
        if a >= 0x3E:
            return
        if a >= 0x3C or a < 4:                       # 0x55E0: los cinco, fuera
            for i in range(5):
                self.libera_un_hueco(0xE0B0 + 4 * i)
            return
        # 0x55BF: cinco sprites en columna -filas 0x47, 0x57...- en la
        # columna del aro + 0x16; con el bit 7 el tercero va fuera (0xC3)
        d = (a + 0x16) & 0xFF
        fila, hl = 0x47, 0xE0B0
        for i in range(5):
            if i == 2 and self[ix] & 0x80:
                self.pon(hl, 0xC3)
            else:
                self.pon(hl, fila)
                fila = (fila + 0x10) & 0xFF
            self.pon(hl + 1, d)
            hl += 4

    def quita_el_movil(self, ix, de, hl):
        """0x55E9."""
        a = self[hl]
        de = self.patrones_del_movil_quieto(a, de)
        if not (self[ix] & 0x80):
            return self.libera_un_hueco(de)
        raise NotImplementedError("quita_el_movil, bit 7")

    def patrones_del_movil_quieto(self, a, hueco):
        """0x5625: fila 0x40, patron 0xA8, color 0x0E; fuera si no ha
        entrado aun lo bastante."""
        return self.movil_a_sprite(a, hueco, 0xA8, 0x16, 0x40, 0x0E)

    def movil_a_sprite(self, a, hueco, b, c, d, e):
        """0x562B."""
        a = (a + c) & 0xFF
        if a < ((c + 3) & 0xFF):
            d = 0xC3
        return self.mete_un_sprite(hueco, d, a, b, e)

    def mete_un_sprite(self, hl, d, a, b, e):
        """0x563A: fila, columna, patron y color."""
        self.pon(hl, d)
        self.pon(hl + 1, a)
        self.pon(hl + 2, b)
        self.pon(hl + 3, e)
        return hl + 4

    def libera_un_hueco(self, de):
        """0x5601."""
        self.pon(de, 0xC3)
        return de + 4

    def arranca_movil_parado(self, ix, de, hl, b, huecos=2):
        """0x5440 (dos huecos) y 0x543B (uno): suelta sus huecos de sprite y
        mira si le toca entrar."""
        for _ in range(huecos):
            de = self.libera_un_hueco(de)
        self.pon(ix - 0x10, 0xFF)                    # 0x5443: a la derecha
        if self.lee16(0xE055) < 0x0140:              # 0x5472: sin acarreo, fuera
            return de
        # 0x5451: mira el estado del SIGUIENTE movil (el tercero, el primero)
        hl = ix + 2 if b != 1 else (ix + 2) & 0xFFF0
        if self[hl] == 0:                            # 0x545C: no esta en pista
            return de
        distancia = self[hl + 1]                     # su segundo byte de la tabla
        pos = hl - 0x10                              # 0x5462: su posicion
        indice = ((ix & 0xFF) >> 1) & 7              # 0x5468: 0, 1 o 2
        self.pone_un_movil_en_su_sitio(ix, distancia, pos, indice)
        return de

    def pone_un_movil_en_su_sitio(self, bc, d, hl, e):
        """0x547A: entra cuando el de delante se ha alejado lo que dice la
        tabla, con tres pixeles de margen."""
        if self[bc]:
            return
        a = d - self[hl]
        if a < 0 or a >= 3:
            return
        self.pon(0xE059, self[0xE059] + 1)           # 0x5484
        self.pon(0xE05A, self[0xE05A] + 1)
        a = self[0xE05A]
        if (self[0xE059] & 0x0F) == 0:
            a = (a - (0x10 if a == 0x20 else 0x0C)) & 0xFF
            self.pon(0xE05A, a)
        self.elige_la_tabla_del_movil(a, bc, e)

    def elige_la_tabla_del_movil(self, a, bc, e):
        """0x549B: el par numero A de la tabla del tipo, al estado del movil."""
        if self.tipo == 1:
            tabla = 0x54C5
        elif self.tipo & 2:
            tabla = 0x5A6F
        else:
            tabla = 0x5F8F
        p = tabla + ((2 * a) & 0xFF)
        self.pon(bc, self.rom8(p))
        self.pon(bc + 1, self.rom8(p + 1))
        self.pon(0xE210 + e, 0x02)

    def pinta_el_borde_del_decorado(self):
        """0x5643: fuera de la primera pantalla solo se marca 0xFF."""
        if self[0xE056]:
            self.pon(0xE14C, 0xFF)
            return
        raise NotImplementedError

    def desplaza_el_decorado(self):
        """0x567D: sin mando la posicion no cambia."""
        self.corre_el_decorado_bc(0)

    def corre_el_decorado_bc(self, bc):
        """0x5687: la posicion en la pista mas BC, y los dos sprites del
        marcador de metros: fila 0xB6, patron (alto*4 + 0x14), color 0x0B."""
        hl = (self.lee16(0xE055) + bc) & 0xFFFF
        self.pon16(0xE055, hl)
        b = ((hl >> 8) * 4 + 0x14) & 0xFF
        if b == 0x34:
            b = 0xF8
        a = hl & 0xFF
        self.mete_un_sprite(0xE0F0, 0xB6, a, b, 0x0B)
        a2 = a + 0x10
        d = 0xB6
        if a2 > 0xFF:
            d = 0xC3
        if not (b & 0x80):
            b = 0x10
        self.mete_un_sprite(0xE0F4, d, a2 & 0xFF, b, 0x0B)

    def parpadea_el_turno(self):
        """0x44BA: cada 32 cuadros, el 1P se borra o se pinta."""
        h = self[0xE003]
        if h & 0x1F:
            return
        mascara = 0xFF if h & 0x20 else 0x00
        rotulo = 0x49BD if self[0xE002] & 0x80 else 0x49B7
        G.pinta_rotulo(self.v, self.rom, rotulo, mascara)

    # -- los seis recogibles y el suelto (tipos 2 y 3) -----------------------
    def mueve_los_seis_recogibles(self):
        """0x57CB: estado en 0xE180, posicion en 0xE170, hueco desde 0xE0FC."""
        ix, de, hl = 0xE180, 0xE0FC, 0xE170
        for b in (6, 5, 4, 3, 2, 1):
            if self[ix]:
                de = self.mueve_un_recogible(ix, de, hl)
            else:
                de = self.arranca_movil_parado(ix, de, hl, b, huecos=1)
            hl += 2
            ix += 2
        if self.tipo == 3:
            self.el_septimo_de_la_fase_3(ix, hl)

    def mira_si_pisa_el_borde(self):
        """0x5200: acarreo si alguna de las seis bolas llega a menos de cinco
        pixeles de 0x4F, que es donde choca con la de Charlie."""
        for i in range(6):
            a = 0x4F - self[0xE170 + 2 * i]
            if 0 <= a < 5:
                return True
        return False

    def el_septimo_de_la_fase_3(self, ix, hl):
        """0x57EF: la bola de Charlie, 3x3 tiles en (0xA0, 0x38) y el sprite
        0xE0F8 encima -fila 0xA3, columna 0x3C, patron 0x94, color 3-."""
        a = self[ix]
        if not a:
            return
        if a != 0x7E and self[0xE139] & 0x0C:
            raise NotImplementedError("el septimo, cayendo (0x5837)")
        if self[hl] != 0x38:                         # 0x580D
            self.coloca_el_septimo()
        self.pinta_rectangulo(0xA038, 0x724A, 0x0303)
        # 0x5825: sin mando el patron no rueda
        self.mete_un_sprite(0xE0F8, 0xA3, 0x3C, 0x94, 0x03)

    def coloca_el_septimo(self):
        """0x583E."""
        self.pon16(0xE17C, 0xA038)
        G.pinta_bloque_en_su_sitio(self.v, self.rom, 0xA000, 0x0E03,
                                   self.que_dibujo_toca())
        if self.suma_los_estados():
            return
        if self.lee16(0xE055) < 0x0140:
            return
        raise NotImplementedError("baja_los_tres_recogibles desde el septimo")

    def mueve_un_recogible(self, ix, de, hl):
        """0x5855."""
        if self.tipo == 2:
            return self.mueve_el_recogible_de_la_fase_2(ix, de, hl)
        a = (0xFF if self[0xE003] & 1 else 0) + self.que_direccion_se_pulsa()
        a = (a + self[hl]) & 0xFF
        if a < 2:                                    # 0x589E apaga_el_recogible
            self.pon(hl, a)
            G.pinta_bloque_en_su_sitio(self.v, self.rom,
                                       (self[hl + 1] << 8) | self[hl], 0x0503,
                                       self.que_dibujo_toca())
            if self.suma_los_estados() != 0x0F:
                self.pon(ix, 0)
            return self.libera_un_hueco(de)
        self.pon(hl + 1, 0xA0)
        return self.pinta_un_recogible(ix, de, hl, a)

    def pinta_un_recogible(self, ix, de, hl, a):
        """0x5870: la bola, 3x5 tiles de una de las cuatro de 0x7242, y su
        sprite de encima, que rueda con el bit 2 de la posicion."""
        self.pon(hl, a)
        if self[0xE130] >= 0x85:
            raise NotImplementedError("el recogible quieto (0x588C)")
        de = self.elige_los_patrones_del_movil(hl, de)
        self.elige_rectangulo_y_pinta((self[hl + 1] << 8) | self[hl], 0x7242,
                                      0x0305)
        return de

    def elige_los_patrones_del_movil(self, hl, de):
        """0x5609, la de la fase 3: patron 0x94 o 0x98, fila 0xA3, color 3."""
        a = self[hl]
        return self.movil_a_sprite(a, de, (a & 4) + 0x94, 0x06, 0xA3, 0x03)

    def mueve_el_recogible_de_la_fase_2(self, ix, de, hl):
        """0x58C6: los monos de la cuerda. Uno de cada cuatro cuadros un paso
        a la izquierda si el suelto anda cerca (ventana de 0x40), y si no uno
        de cada dos."""
        cerca = False
        if self[0xE1B0] != 0xFE:
            cerca = ((self[hl] - self[0xE1B0] + 0x20) & 0xFF) < 0x40
        if cerca:
            baja = (self[0xE003] & 3) == 0           # 0x58E3
        else:
            baja = (self[0xE003] & 1) == 0           # 0x590D, sin mando
        if baja:
            self.pon(hl, self[hl] - 1)               # 0x58EA
        self.pon(hl + 1, 0x50)                       # 0x58EB: la fila fija
        a = self[hl]
        if a < 2:                                    # 0x5906 lo_deja_quieto
            self.pon(hl, 0x01)
            G.pinta_bloque_en_su_sitio(self.v, self.rom, (0x50 << 8) | 0x01,
                                       0x0302, self.que_dibujo_toca())
            if self.suma_los_estados() != 0x0F:
                self.pon(ix, 0)
            return self.libera_un_hueco(de)
        tabla = 0x5A2F + ((a & 0x0E) << 2)           # 0x58F6: 8 piezas de 2x4
        self.pinta_rectangulo((0x50 << 8) | a, tabla, 0x0204)
        return de                                    # 0x589C: el pop de DE

    def suma_los_estados(self):
        """0x58B8: los seis estados sumados, nibble bajo."""
        return sum(self[0xE180 + 2 * i] for i in range(6)) & 0x0F

    def pinta_rectangulo(self, de, hl, bc):
        """0x53C8: B filas de C celdas; cada fila se corta en la columna 31."""
        celda = G.celda_de_la_posicion(de >> 8, de & 0xFF)
        filas, ancho = bc >> 8, bc & 0xFF
        for _ in range(filas):
            for i in range(ancho):
                self.vram[(celda + i) & 0x3FFF] = self.rom8(hl + i)
                if ((celda + i + 1) & 0x1F) == 0:
                    break
            celda += 0x20
            hl += ancho

    def elige_rectangulo_y_pinta(self, de, hl, bc):
        """0x53BE: uno de cuatro dibujos segun los bits 1-2 de la columna."""
        p = hl + (de & 6)
        self.pinta_rectangulo(de, self.rom8(p) | (self.rom8(p + 1) << 8), bc)

    def mueve_el_suelto(self):
        """0x5918: el mono que salta."""
        if self[0xE1BA]:
            self.pon(0xE1BA, self[0xE1BA] - 1)
            return
        x = self[0xE1B0]
        if x < 2 or x == 0xFF:                       # 0x592B: se reinicia
            self.pon(0xE1BA, 0x80)
            self.pon(0xE1B4, 0)
            self.pon(0xE1B5, 0)
            self.pon16(0xE1B6, 0x59FA)
            self.pon(0xE1B0, 0xFE)
            self.pon(0xE1B1, 0x50)
            self.pon(0xE217, 0x50)
            self.mete_el_suelto_en_los_sprites()
            return
        if self[0xE1B4]:
            self.recorre_la_rampa_del_suelto()
            return
        self.pon(0xE1B0, x - 1)                      # 0x5958, sin mando
        a = self[0xE1B0]                             # 0x5959: el dibujo
        if not (a & 4):
            pose = 0x00
        elif a & 2:
            pose = 0x08
        else:
            pose = 0x04
        self.pon(0xE1B2, pose)
        self.mete_el_suelto_en_los_sprites()
        self.mira_los_seis_contra_el_suelto()

    def mira_los_seis_contra_el_suelto(self):
        """0x5971: si un mono de la cuerda le cae a dos pixeles, el suelto se
        bloquea y salta por encima (su rampa)."""
        for i in range(6):
            de = 0xE170 + 2 * i
            if self[de + 1] < 2 or self[de] == 0:
                continue
            if ((self[de] + 0x18 - self[0xE1B0]) & 0xFF) < 2:
                self.pon(0xE1B2, 0x0C)
                self.pon(0xE1B4, 0x01)
                return

    def recorre_la_rampa_del_suelto(self):
        """0x59A4: el salto, con la rampa de 0x59FA de ida y de vuelta."""
        sentido = self[0xE1B5]
        de = self.lee16(0xE1B6)
        a = self.rom8(de)
        if not (sentido & 1):
            a = -a
        self.pon(0xE1B1, self[0xE1B1] + a)
        self.pon(0xE1B0, self[0xE1B0] - 2)
        hl = de + 1 if not (sentido & 1) else de - 1
        a = self.rom8(hl)
        if a == 0xFF:                                # 0x59C6: el tope
            hl -= 1
            self.pon(0xE1B5, 0x01)
        elif a == 0xFE:                              # 0x59EC: el otro
            self.pon(0xE1B4, 0)
            self.pon(0xE1B5, 0)
            hl += 1
        self.pon16(0xE1B6, hl)
        self.mete_el_suelto_en_los_sprites()

    def mete_el_suelto_en_los_sprites(self):
        """0x59CE: en 0xE0F8, patron 0x84 + su dibujo; con 0xFE, fuera."""
        b, c = self[0xE1B0], self[0xE1B1]
        if b == 0xFE:
            c = 0xC3
        self.mete_un_sprite(0xE0F8, c, b, (self[0xE1B2] + 0x84) & 0xFF,
                            self[0xE1B3])

    # -- el trapecio (tipo 0) --------------------------------------------------
    def avanza_la_animacion_grande(self):
        """0x5CE3: el trapecio cumple un paso cada tantos cuadros como diga
        0x5F61 -14, 12, 10, 8, 6 o 4- con el nibble de (0xE1E0) mas uno; al
        cumplirlo, el paso sube en BCD y se coloca la figura."""
        self.pon(0xE1F2, 0)
        b = self.rom8(0x5F61 + (self[0xE1E0] & 0x0F) + 1)   # sin mando
        self.pon(0xE1EE, self[0xE1EE] + 1)
        if self[0xE1EE] < b:
            return
        self.pon(0xE1EE, 0)
        self.pon(0xE1F2, 0xFF)
        viejo = self[0xE1C0]
        nuevo = bcd_suma(viejo, 1)
        self.pon(0xE1C0, nuevo)
        self.pon(0xE1C1, 1 if nuevo & 0x10 else 0)
        self.coloca_la_figura_grande(viejo)

    def coloca_la_figura_grande(self, paso):
        """0x5D33: la altura (0x521D/0x5227) a 0xE1D6 y la columna -la de la
        figura mas la velocidad con signo de 0x5F7B/0x5F85- a 0xE1D7."""
        c = self[0xE1CA]
        a = self[0xE1E0]
        if a & 0x40:
            c = self[0xE1CB]
            a = self[0xE1E2]
            if not a:
                self.pon(0xE1D7, 0)
                return
        alturas, velocidades = (0x5227, 0x5F85) if a & 2 else (0x521D, 0x5F7B)
        i = paso & 0x0F
        self.pon(0xE1D6, self.rom8(alturas + i))
        v = self.rom8(velocidades + i)
        if paso & 0x10:
            v = -v
        self.pon(0xE1D7, v + c)

    def mueve_la_figura_grande(self):
        """0x5D76: en el paso cumplido la figura grande -el decorado del
        trapecio- se corre lo que diga su curva (0x5F67/0x5F71), la columna
        de la figura (0xE1CA) sale de las velocidades mas 0x3D, y se repinta
        todo."""
        if self[0xE134] == 4:
            raise NotImplementedError("estado 4")
        if not self[0xE1F2]:
            return
        if self[0xE134] == 3:
            raise NotImplementedError("estado 3")
        curva, velocidades = (0x5F71, 0x5F85) if self[0xE1E0] & 2 \
            else (0x5F67, 0x5F7B)
        b = self[0xE1C0]
        i = b & 0x0F
        a = self.rom8(curva + i)
        if not (b & 0x10):
            a = -a & 0xFF
        v = self.rom8(velocidades + i)
        if b & 0x10:
            v = -v
        self.pon(0xE1CA, v + 0x3D)
        self.pon(0xE14A, self[0xE14A] + a)           # 0x5DBF
        self.pinta_la_figura_grande()
        self.corre_el_decorado_bc(a | 0xFF00 if a & 0x80 else a)
        self.borra_la_franja_de_abajo()

    def borra_la_franja_de_abajo(self):
        """0x5DF7: 256 celdas a cero desde 0x3880, y las dos figuras."""
        for a in range(0x3880, 0x3980):
            self.vram[a] = 0
        if not self[0xE056]:
            raise NotImplementedError("la columna que entra, en el titulo")
        self.pinta_las_dos_figuras()

    def pinta_las_dos_figuras(self):
        """0x5E10: la pose de la primera en 0x3889 (o, con el bit 7, en la
        columna de 0xE1CA); y la segunda, si esta activa, con su paso propio."""
        a = self[0xE1E0]
        bc = 0x7806 if a & 2 else 0x76EC
        de = 0x3889
        pinta = True
        if a & 0x80:
            x = self[0xE1CA]
            if x < 8:
                pinta = False
            else:
                de = G.celda_de_la_posicion(0x20, x)
                bc = 0x797E if a & 2 else 0x7876
        if pinta:
            self.pinta_una_pose(0xE1C0, bc, de)
        if not self[0xE1E2]:
            return
        x = self[0xE1E1] + self[0xE1CA]
        if x > 0xFF:
            return
        self.pon(0xE1CB, x)
        if x < 8 or x >= self[0xE14C]:
            return
        de = G.celda_de_la_posicion(0x20, x)
        bc = 0x797E if self[0xE1E2] & 2 else 0x7876
        self.pinta_una_pose(0xE1C9, bc, de)

    def pinta_una_pose(self, hl, bc, de):
        """0x5E74: el guion de la pose -indices; 0xFE fila nueva, 0xFF fin-.
        Pasada la mitad del paso la pose se refleja y a partir de la sexta se
        escribe de derecha a izquierda. Al tocar la columna 0 se salta el
        resto de la fila."""
        a = self[hl] & 0x1F
        if a >= 0x10:
            a = ((~a & 0xFF) - 5) & 0x1F
        c = a
        p = bc + 2 * a
        g = self.rom8(p) | (self.rom8(p + 1) << 8)
        fila = de
        de = fila
        while True:
            b = self.rom8(g)
            g += 1
            if b == 0xFF:
                return
            if b == 0xFE:
                fila += 0x20                         # 0x5E97
                de = fila
                continue
            self.vram[de & 0x3FFF] = b
            de = de - 1 if c >= 6 else de + 1
            if (de & 0x1F) == 0:                     # 0x5EB0: el resto fuera
                while True:
                    b = self.rom8(g)
                    g += 1
                    if b == 0xFF:
                        return
                    if b == 0xFE:
                        fila += 0x20
                        de = fila
                        break

    def avanza_la_segunda_figura(self):
        """0x5EBC: el mismo ritmo, con su contador (0xE1C8) y su paso (0xE1C9)."""
        b = self.rom8(0x5F61 + (self[0xE1E2] & 0x0F) + 1)
        self.pon(0xE1C8, self[0xE1C8] + 1)
        if self[0xE1C8] < b:
            return
        self.pon(0xE1C8, 0)
        self.pon(0xE1C9, bcd_suma(self[0xE1C9], 1))
        self.borra_la_franja_de_abajo()

    def repinta_lo_que_sujeta(self):
        """0x5F0F: en el paso cumplido, la franja de 0x5F58 y la plataforma
        -3x7 de una de cuatro en 0x735A- en la fila 0xA0."""
        if self[0xE134] != 2:
            raise NotImplementedError("repinta_desde_arriba")
        if not self[0xE1F2]:
            return
        G.descomprime(self.v, self.rom, 0x5F58)
        a = self[0xE1CA] + (self[0xE1E1] >> 1) - 0x18
        if a < 0:
            return
        self.pon(0xE1D4, a)
        p = 0x735A + (a & 6)
        dibujo = self.rom8(p) | (self.rom8(p + 1) << 8)
        self.pinta_rectangulo(0xA000 | a, dibujo, 0x0307)

    # -- el caballo (tipo 4) ---------------------------------------------------
    def mueve_lo_que_se_empuja(self):
        """0x5B00 sin mando -> 0x5B16: la velocidad (0xE270) mas el resto
        (0xE271); los dos bits que desbordan son los pixeles del cuadro.
        Devuelve ese avance, que es la C que hereda la cola."""
        a = (self[0xE270] + self[0xE271]) & 0xFF
        self.pon(0xE271, a & 0x3F)
        c = a >> 6
        self.pon(0xE14A, self[0xE14A] - c)
        self.pinta_la_figura_grande()
        if not self[0xE056]:
            raise NotImplementedError("la segunda capa (0x5B37)")
        self.corre_el_decorado_bc((-c) & 0xFFFF if c else 0)
        self.corre_la_cola_con_la_velocidad(c)
        return c

    def pinta_la_figura_grande(self):
        """0x56D4: una de cuatro figuras (0x6ACB) segun los bits 1-2 de la
        referencia, volcada en su celda, y la columna de ocho sprites que la
        acompanan -los de 0xE0E1 y 0xE121- recolocada."""
        ref = self[0xE14A]
        p = 0x6ACB + (ref & 6)
        dibujo = self.rom8(p) | (self.rom8(p + 1) << 8)
        celda = G.celda_de_la_posicion(self[0xE14B], ref)
        G.vuelca_la_figura(self.v, self.rom, dibujo, celda, self.bufer,
                           self.que_dibujo_toca())
        a = (ref - 0x2E) & 0xFE
        for x in (0xE0E1, 0xE0E9):
            self.pon(x, a)
        a = (a + 0x1E) & 0xFF
        for x in (0xE0E5, 0xE0ED):
            self.pon(x, a)
        a = (a + 0x09) & 0xFF
        for x in (0xE121, 0xE129):
            self.pon(x, a)
        a = (a - 0x2E) & 0xFF
        for x in (0xE125, 0xE12D):
            self.pon(x, a)

    def corre_la_cola_con_la_velocidad(self, c):
        """0x5B52: cada pieza viva C pixeles a la izquierda; a tres, se apaga."""
        for i in range(4):
            hl = 0xE25C + 4 * i
            if not self[hl]:
                continue
            self.pon(hl + 2, self[hl + 2] - c)
            if self[hl + 2] <= 3:
                self.apaga_un_hueco_de_la_cola(hl)

    def saca_la_siguiente_de_la_cola(self, c):
        """0x5AAF: descuenta el plazo y, al pasar de cero, saca la siguiente
        pieza del guion (0x5C8E) al primer hueco libre, en la columna 0xD8."""
        if not self[0xE056]:
            return
        a = self[0xE26E] - c
        self.pon(0xE26E, a)
        if a >= 0:
            return
        for i in range(4):
            hl = 0xE25C + 4 * i
            if not self[hl]:
                break
        else:
            return
        de = self.lee16(0xE26C)
        g = self.rom8(de)
        self.pon(hl, 0x3A + 0x1E * (((g & 0x18) >> 3) + 1))
        self.pon(hl + 1, g)
        self.pon(hl + 2, 0xD8)
        self.pon(hl + 3, self.rom8(de + 1))
        self.pon(0xE26E, self.rom8(de + 2))
        de += 3
        if self.rom8(de) == 0xFF:                    # 0x5AF6: fin del guion
            de = self.lee16(0xE25A)
        self.pon16(0xE26C, de)

    def mira_la_cola_contra_el_jugador(self):
        """0x5C1E: si una pieza le cae encima, choque o salto por encima."""
        if self[0xE134] >= 5:
            return
        for i in range(4):
            hl = 0xE25C + 4 * i
            if not self[hl]:
                continue
            c = (self[0xE131] - self[hl + 2] + 0x10) & 0xFF
            if ((self[hl + 3] * 8 + 8) & 0xFF) < c:
                continue
            a = (self[0xE130] - self[hl + 1] + 0x1C) & 0xFF
            if a >= 0x24:
                continue
            if a >= 4 or c >= 6:
                raise NotImplementedError("la cola alcanza al jugador")

    def pinta_la_cola(self):
        """0x5B7C: cada pieza, dos filas de dos o tres celdas desde la tabla
        de 0x7527; el byte de estado es el desplazamiento de patrones, y la
        fila de abajo lleva quince mas."""
        for i in range(4):
            hl = 0xE25C + 4 * i
            estado = self[hl]
            if not estado:
                continue
            d, e, b = self[hl + 1], self[hl + 2], self[hl + 3]
            celda = G.celda_de_la_posicion(d, e)
            c = e & 6
            p = 0x7527 + ((c * 5) >> 1)
            self.pinta_dos_o_tres_celdas(p, celda, b, estado)
            self.pinta_dos_o_tres_celdas(p, celda + 0x20, b,
                                         (estado + 0x0F) & 0xFF)

    def pinta_dos_o_tres_celdas(self, hl, de, b, c, tabla=None):
        """0x5BBE / 0x5BC0."""
        leer = self.rom8 if tabla is None else tabla

        def fila(n):
            nonlocal hl, de
            for _ in range(n):
                self.vram[de & 0x3FFF] = (leer(hl) + c) & 0xFF
                hl += 1
                de += 1

        fila(2)
        b -= 1
        if b == 0:                                   # 0x5BE5 pinta_una_celda
            hl += 2
            if leer(hl):
                de -= 1
            self.vram[de & 0x3FFF] = (leer(hl) + c) & 0xFF
            return
        b -= 1
        for _ in range(b or 256):                    # 0x5BCB: djnz, 0 = 256
            self.vram[de & 0x3FFF] = (leer(hl) + c) & 0xFF
            de += 1
        hl += 1
        if leer(hl) != 1:
            de -= 1
        fila(2)

    def apaga_un_hueco_de_la_cola(self, hl):
        """0x5BF3: el hueco libre, y por donde paso se pinta con los diez
        ceros de 0x5C14 -o sea, el estado a secas-."""
        c = self[hl]
        self.pon(hl, 0)
        d, e, b = self[hl + 1], self[hl + 2], self[hl + 3]
        celda = G.celda_de_la_posicion(d, e)
        self.pinta_dos_o_tres_celdas(0x5C14, celda, b, c)
        self.pinta_dos_o_tres_celdas(0x5C14, celda + 0x20, b, (c + 0x0F) & 0xFF)

    # -- el resultado --------------------------------------------------------
    def sprites(self):
        return bytes(self.ram[0xB0:0x130])

    def vram_vista(self):
        """La VRAM tal como la ve el vuelco de 0x4CA9: con la SAT puesta."""
        out = bytearray(self.vram)
        out[0x3B00:0x3B80] = self.sprites()
        return out


def bcd_resta(a, b):
    """`sub b / daa`: la resta en BCD, con el acarreo."""
    r = a - b
    cy = r < 0
    r &= 0xFF
    lo_borrow = (a & 0x0F) < (b & 0x0F)
    if lo_borrow:
        r = (r - 6) & 0xFF
    if cy:
        r = (r - 0x60) & 0xFF
    return r, cy


def bcd_suma(a, b):
    """`add a,b / daa`, sin acarreo de salida."""
    r = a + b
    if (a & 0x0F) + (b & 0x0F) > 9:
        r += 6
    if r > 0x99:
        r += 0x60
    return r & 0xFF


def en_pista(rom, tipo, cuadros, reloj=RELOJ):
    """La VRAM de la atraccion `cuadros` vuelcos despues del montaje: la del
    vuelco numero `cuadros`, con la SAT que carga ese vuelco."""
    p = Pista(rom, tipo, reloj)
    for k in range(cuadros):
        if k:
            p.tras_el_vuelco()
        p.cuadro()
    return p
