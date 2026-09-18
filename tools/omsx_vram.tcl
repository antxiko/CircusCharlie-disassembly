# omsx_vram.tcl - Vuelca la VRAM DE VERDAD de Circus Charlie.
#
# Para que sirve: las imagenes de tools/graficos.py se montan ejecutando en
# Python los pasos del cartucho, y mirar el dibujo no basta para darlas por
# buenas. Esto deja correr el juego de verdad y, en varios instantes, vuelca
# los 16 KB de VRAM, los ocho registros del VDP y las variables que dicen QUE
# se estaba dibujando en ese momento.
#
# No pone NINGUN punto de ruptura: los volcados van por reloj emulado, que es
# lo unico que no ahoga al emulador. Y lleva perro guardian de tiempo REAL,
# para que un guion roto no pueda dejarlo colgado.
#
#   "C:/Program Files/openMSX/openmsx.exe" -machine Philips_VG_8020 \
#       -cart circus.rom -script tools/omsx_vram.tcl
#
# Variables de entorno:
#   PP_SALIDA  carpeta de salida (por defecto work/omsx)

proc opcion {nombre porDefecto} {
    global env
    if {[info exists env($nombre)]} { return $env($nombre) }
    return $porDefecto
}

set ::SALIDA [opcion PP_SALIDA {C:/Users/Antxiko/Documents/DES_ASM/CIRCUS_DISAM/work/omsx}]
file mkdir $::SALIDA
set ::n 0

proc vuelca {etiqueta} {
    set i [format %02d $::n]
    incr ::n
    set datos [debug read_block VRAM 0 16384]
    set f [open $::SALIDA/vram_$i.bin w]
    fconfigure $f -translation binary
    puts -nonewline $f $datos
    close $f
    set r {}
    for {set k 0} {$k < 8} {incr k} {
        lappend r [format %02X [debug read {VDP regs} $k]]
    }
    set f [open $::SALIDA/info_$i.txt w]
    puts $f [format {etiqueta %s} $etiqueta]
    puts $f [format {tiempo %s} [machine_info time]]
    puts $f [format {regs %s} [join $r { }]]
    # Las variables de trabajo de ESTE cartucho, sacadas de su listado:
    #   0xE000 la escena que despacha 0x40C6
    #   0xE002 el modo (bit 5: dos jugadores; bit 6: partida en marcha)
    #   0xE003 el reloj de cuadros
    #   0xE052 EL TIPO DE FASE, que es el que elige cual de las cinco
    #          atracciones se monta (tabla de 0x5FEF)
    #   0xE056 el numero de fase, en BCD
    #   0xE05B la tanda de decorado, que sube de ocho en ocho cada cinco fases
    foreach {nombre dir} {escena 0xE000 modo 0xE002 reloj 0xE003
                          tipo_de_fase 0xE052 numero_de_fase 0xE056
                          tanda 0xE05B} {
        puts $f [format {%s %d} $nombre [debug read memory $dir]]
    }
    close $f
    catch { screenshot -raw $::SALIDA/pant_$i.png }
}

proc pulsa {} {
    keymatrixdown 8 0x01
    after time 0.4 suelta
}
proc suelta {} {
    keymatrixup 8 0x01
}

# --- calendario -------------------------------------------------------------
# NO SE PULSA NADA. La demostracion del cartucho pasa sola por el logotipo de
# la casa, la pantalla de TITULO y luego las atracciones, asi que lo unico que
# hace falta es volcar a menudo y dejarla correr. Pulsar espacio pronto se
# salta el titulo, que es justo lo que no se quiere.
#
# Que hay en cada volcado NO se decide mirando el dibujo: lo dice el
# `tipo_de_fase` que el info_NN.txt lee de (0xE052).
for {set t 3} {$t <= 170} {incr t 3} {
    after time $t [list vuelca demo]
}
after time 174 { exit }

after realtime 500 {
    puts {PERRO GUARDIAN a los 500 s reales}
    exit
}
