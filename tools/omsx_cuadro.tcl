# omsx_cuadro.tcl - A QUE CUADRO PERTENECE LA FOTO.
#
# EL PROBLEMA. tools/omsx_atracciones.tcl vuelca la VRAM y pide la foto una
# detras de otra, y eso no da un par comparable: el `screenshot` de openMSX
# devuelve un cuadro del renderizador, que no tiene por que ser el del instante
# en que se leyo la VRAM. Entre uno y otro el juego ha movido los sprites y ha
# subido el marcador, asi que cotejar el dibujo hecho desde esa VRAM contra esa
# foto acusa al renderizador de fallos que son del reloj: en el acto del
# monociclo la foto ensena 50 puntos donde la VRAM dice 49.
#
# LO QUE NO LO ARREGLA: congelar con `set ::pause on` antes de volcar. Probado,
# y da EXACTAMENTE las mismas diferencias: con la maquina parada el renderizador
# no vuelve a pintar, asi que la foto sigue siendo la de antes de la pausa.
#
# LO QUE SI: no buscar el cuadro bueno, MEDIRLO. Se dispara la foto una sola
# vez y se vuelca la VRAM en una rafaga de cuadros alrededor, antes y despues.
# Si alguno de esos estados reproduce la foto punto por punto, quedan probadas
# las dos cosas de golpe: que el desfase es del emulador y que el renderizador
# de tools/vram.py es exacto. Lo comprueba tools/coteja_pixels.py.
#
#   "C:/Program Files/openMSX/openmsx.exe" -machine Philips_VG_8020 \
#       -cart circus.rom -script tools/omsx_cuadro.tcl
#
# Variables de entorno:
#   PP_SALIDA  carpeta de salida (por defecto work/serie)

proc opcion {nombre porDefecto} {
    global env
    if {[info exists env($nombre)]} { return $env($nombre) }
    return $porDefecto
}

set ::SALIDA [opcion PP_SALIDA {C:/Users/Antxiko/Documents/DES_ASM/CIRCUS_DISAM/work/serie}]
file mkdir $::SALIDA

# El cuadro del MSX no dura 1/50 s, dura 1/50,15: en trece cuadros la
# diferencia ya se nota, y aqui se cuentan cuadros.
set ::CUADRO 0.019940
set ::VENTANA 6

# El instante de la foto dentro de cada atraccion. Se puede mover para
# comprobar que un punto suelto que no casa es una escritura a mitad de
# barrido -el VDP lee la tabla de nombres linea a linea, y pilla la celda
# mientras el juego la esta reescribiendo- y no un fallo del renderizador: con
# la foto en otro instante, esos puntos cambian de sitio o desaparecen.
set ::INSTANTE [opcion PP_INSTANTE 27.5]

# Lanzado con `-script`, openMSX arranca con el renderizador sin inicializar y
# las capturas salen negras sin que nadie proteste.
catch { set renderer SDLGL-PP }

# Y HAY QUE APAGARLE LOS EFECTOS DE TELEVISOR, o la foto no es un cuadro: es
# DOS. Con `blur` a 50 -lo de fabrica- openMSX simula el fosforo mezclando el
# cuadro anterior, y un punto que se enciende en uno y se apaga en el siguiente
# sale a media intensidad: el magenta (201,104,178) del monociclo aparece como
# (101,56,89), que no es ningun color del MSX. Son nueve puntos en una pantalla
# -el borde de la figura, que se mueve un punto por cuadro- y bastan para que
# el cotejo no de cero. Lo mismo el `glow` y el `deflicker`.
catch { set blur 0 }
catch { set glow 0 }
catch { set deflicker off }
catch { set scale_algorithm simple }

proc vuelca_vram {acto k} {
    global SALIDA
    set datos [debug read_block VRAM 0 16384]
    set signo [expr {$k < 0 ? "m" : "p"}]
    set nom [format {%s/vram_%s_%s%02d.bin} $SALIDA $acto $signo [expr {abs($k)}]]
    set f [open $nom w]
    fconfigure $f -translation binary
    puts -nonewline $f $datos
    close $f
}

proc foto {acto} {
    global SALIDA
    set r {}
    for {set k 0} {$k < 8} {incr k} {
        lappend r [format %02X [debug read {VDP regs} $k]]
    }
    set f [open $SALIDA/info_$acto.txt w]
    puts $f [format {etiqueta %s} $acto]
    puts $f [format {tiempo %s} [machine_info time]]
    puts $f [format {regs %s} [join $r { }]]
    foreach {nombre dir} {escena 0xE000 modo 0xE002 reloj 0xE003
                          tipo_de_fase 0xE052 numero_de_fase 0xE056
                          tanda 0xE05B} {
        puts $f [format {%s %d} $nombre [debug read memory $dir]]
    }
    close $f
    catch { screenshot -raw $SALIDA/pant_$acto.png }
}

proc pulsa {} {
    keymatrixdown 8 0x01
    after time 0.4 suelta
}
proc suelta {} {
    keymatrixup 8 0x01
}

# LA ESCENA 9, NO LA 10: la 10 monta la fase pero la 9 es la que LIMPIA, y
# encadena sola a la 10. Entrando por la 10 queda en pantalla lo que no repinte
# el decorado nuevo. (Ver tools/omsx_atracciones.tcl.)
proc monta_tipo {tipo} {
    debug write memory 0xE052 $tipo
    debug write memory 0xE004 1
    debug write memory 0xE000 9
}

# --- calendario -------------------------------------------------------------
# Un ciclo por atraccion, con REINICIO entre una y otra: sin el, las celdas que
# el decorado nuevo no toca se quedan con las de la anterior.
set ::tipos {0 1 2 3 4}
set ::i 0

proc siguiente {} {
    global CUADRO VENTANA
    if {$::i >= [llength $::tipos]} { exit }
    set tipo [lindex $::tipos $::i]
    incr ::i
    set acto acto_$tipo
    reset
    after time 16.0 { pulsa }
    after time 18.0 { pulsa }
    after time 20.0 { pulsa }
    after time 24.0 [list monta_tipo $tipo]
    # La rafaga: la foto en el centro, y la VRAM de cada cuadro alrededor.
    for {set k [expr {-$VENTANA}]} {$k <= $VENTANA} {incr k} {
        set t [expr {$::INSTANTE + $k * $CUADRO}]
        after time $t [list vuelca_vram $acto $k]
    }
    after time $::INSTANTE [list foto $acto]
    after time 29.0 { siguiente }
}

after time 1.0 { siguiente }

after realtime 900 {
    puts {PERRO GUARDIAN a los 900 s reales}
    exit
}
