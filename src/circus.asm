; ==========================================================================
; CIRCUS CHARLIE - Konami - MSX1 - cartucho RC-712 de 16 KB en la pagina 1
; ==========================================================================
; Generado por tools/mkasm.py a partir del trazado de flujo real.
; Los comentarios provienen de tools/../src/*.notes y estan anclados a
; direccion, de modo que sobreviven a un retrazado.
; ==========================================================================

	org 0x04000


; ----------------------------------------------------------------------
; DATOS cabecera_del_cartucho: "AB" y la direccion de INIT (0x407B);
;   STATEMENT, DEVICE y TEXT a cero, y los seis bytes reservados tambien
;   0x4000..0x4010  (16 bytes)
DATA_cabecera_del_cartucho:
	defw 04241h,0407bh,00000h,00000h,00000h,00000h,00000h,00000h	; 4000

; ======================================================================
; CODIGO 0x4010..0x40c7  (183 bytes)
; ======================================================================



; ----------------------------------------------------------------------
; ESCRIBIR Y LEER LA VRAM. Las dos rutinas que usa todo el cartucho en vez de la BIOS: preparan el puerto una vez y luego mueven los bytes con el registro C ya cargado en el juego de registros alternativo, que es lo que permite sacar un byte por `out (c),a` sin volver a calcular nada.
; ----------------------------------------------------------------------
escribe_en_vram:
	call prepara_escritura_vram		;4010   ; pone el puntero de escritura de la VRAM en DE y deja 0x98 en C'
	exx			;4013   ; al juego alternativo, donde C vale 0x98 (el puerto de datos del VDP)
	out (c),a		;4014   ; y ahi va el byte
	exx			;4016   ; de vuelta al juego normal
	ei			;4017   ; L_45EC entro con `di`: aqui se vuelven a permitir las interrupciones
	ret			;4018
lee_de_vram:
	call prepara_lectura_vram		;4019   ; lo mismo pero para leer: prepara el puntero y deja 0x98 en C'
	exx			;401c
	in a,(c)		;401d   ; el byte leido vuelve en A
	exx			;401f
	ei			;4020
	ret			;4021

; ----------------------------------------------------------------------
; SUMAR UN INDICE DE OCHO BITS A UN PUNTERO. Dos rutinas gemelas, una para HL y otra para DE, con el acarreo propagado a mano. Las llama medio cartucho para indexar tablas.
; ----------------------------------------------------------------------
suma_a_a_hl:
	add a,l			;4022   ; HL += A, sin tocar mas registros
	ld l,a			;4023
	ret nc			;4024   ; si no hubo acarreo ya esta
	inc h			;4025   ; y si lo hubo, el byte alto
	ret			;4026
suma_a_a_de:
	add a,e			;4027   ; DE += A, la gemela de la de arriba
	ld e,a			;4028
	ret nc			;4029
	inc d			;402a
	ret			;402b

; ----------------------------------------------------------------------
; EL GANCHO DE LA INTERRUPCION, que es donde vive el juego entero. INIT no arranca ningun bucle: engancha esto en H.KEYI (0xFD9B) y se queda en el `jr $` de 0x40A9, de modo que todo lo que pasa, pasa una vez por cuadro desde aqui.
; ----------------------------------------------------------------------
gancho_de_interrupcion:
	di			;402c
	call 0013eh		;402d   ; BIOS RDVDP - Reads VDP status register | lee el registro de estado del VDP para que el VDP baje su bandera
	call L_7A3D		;4030   ; primero el sonido, que no puede esperar
	ld hl,0e005h		;4033   ; el cerrojo de reentrada: cuenta cuantas interrupciones se han solapado
	ld a,(hl)			;4036
	inc (hl)			;4037   ; apunta esta
	or a			;4038   ; si ya habia una dentro, no se entra otra vez
	jr nz,L_404B		;4039
L_403B:
	ld (hl),001h		;403b   ; se toma el cerrojo
	ei			;403d   ; y se abren las interrupciones ESTANDO dentro: el cuadro puede tardar mas de un cuadro
	call lee_los_mandos		;403e   ; lee los mandos y el teclado
	call reparte_la_escena		;4041   ; y aqui se despacha la escena que toque
	di			;4044   ; al salir, se cierra
	ld hl,0e005h		;4045
	dec (hl)			;4048   ; suelta el cerrojo
	jr nz,L_403B		;4049   ; si mientras tanto entro otra interrupcion, se atiende ahora sin volver a la pila
L_404B:
	ei			;404b
	reti		;404c

; ----------------------------------------------------------------------
; EL DESPACHADOR DE ESCENAS. El truco de esta familia de cartuchos: la tabla de destinos va PEGADA detras del `call`, y el `pop hl` recupera su propia direccion de retorno, que es justo donde empieza la tabla. Asi que quien llama no tiene que pasar ningun puntero, solo el numero de escena en A.
; ----------------------------------------------------------------------
despacha_por_tabla:
	add a,a			;404e   ; el numero de escena, por dos: son palabras
	pop hl			;404f   ; la direccion de retorno ES la tabla
	call suma_a_a_hl		;4050   ; HL += A, o sea la entrada que toca
	ld e,(hl)			;4053   ; y de ahi sale el destino
	inc hl			;4054
	ld d,(hl)			;4055
	ex de,hl			;4056
	jp (hl)			;4057   ; se salta sin dejar retorno: la escena hereda la pila de quien llamo

; ----------------------------------------------------------------------
; INTERCAMBIAR DOS BLOQUES DE B BYTES, byte a byte y sin memoria auxiliar. Se usa para permutar tablas de la RAM sin copiarlas dos veces.
; ----------------------------------------------------------------------
intercambia_bloques:
	ld c,(hl)			;4058   ; se guarda el de (HL)
	ld a,(de)			;4059   ; se trae el de (DE)
	ld (hl),a			;405a   ; y cada uno acaba en el sitio del otro
	ld a,c			;405b
	ld (de),a			;405c
	inc hl			;405d
	inc de			;405e
	djnz intercambia_bloques		;405f
	ret			;4061

; ----------------------------------------------------------------------
; EL INTERPRETE DE ROTULOS, con dos puertas que solo se diferencian en la mascara. El guion trae [destino en VRAM, palabra] y luego los indices de patron, con 0xFE para saltar a otro destino y 0xFF para terminar. Con la mascara a 0xFF el rotulo se pinta, y con la mascara a 0x00 se escriben ceros: el MISMO guion sirve para borrarlo, sin una segunda copia de la geometria.
; ----------------------------------------------------------------------
borra_rotulo:
	ld c,000h		;4062   ; mascara 0x00: todo byte sale como cero, o sea BORRA
	jr L_4068		;4064
pinta_rotulo:
	ld c,0ffh		;4066   ; mascara 0xFF: los bytes pasan tal cual
L_4068:
	ld e,(hl)			;4068   ; de la cabecera del guion sale el destino en la VRAM
	inc hl			;4069
	ld d,(hl)			;406a
	inc hl			;406b
L_406C:
	ld a,(hl)			;406c   ; el siguiente byte del guion
	inc hl			;406d
	ld b,a			;406e
	inc b			;406f   ; 0xFF (B pasa a cero) es el fin del rotulo
	ret z			;4070
	inc b			;4071   ; 0xFE (B pasa a cero otra vez) es "sigue en otro sitio de la VRAM"
	jr z,L_4068		;4072
	and c			;4074   ; aqui muerde la mascara: o el byte, o un cero
	call escribe_en_vram		;4075   ; y a la VRAM
	inc de			;4078   ; la siguiente celda de la tabla de nombres
	jr L_406C		;4079

; ----------------------------------------------------------------------
; INIT, la direccion que trae la cabecera del cartucho. Hace cuatro cosas y se echa a dormir: modo 1 de interrupcion, gancho en H.KEYI, pila en 0xE500 y un kilobyte de RAM a cero. A partir del `ei` final, el juego entero corre dentro de la interrupcion.
; ----------------------------------------------------------------------
init:
	di			;407b
	im 1		;407c
	ld a,0c3h		;407e   ; un `jp` en 0xFD9A y la direccion detras: asi se engancha H.KEYI
	ld (0fd9ah),a		;4080
	ld hl,gancho_de_interrupcion		;4083   ; el gancho es el de 0x402C
	ld (0fd9bh),hl		;4086
	ld sp,0e500h		;4089   ; la pila, por encima de las variables
	ld hl,0e000h		;408c   ; y las variables, a cero de 0xE000 a 0xE3FF
	ld de,0e001h		;408f
	ld bc,003ffh		;4092
	ld (hl),000h		;4095
	ldir		;4097
	ld a,001h		;4099   ; el cerrojo, tomado durante el arranque
	ld (0e005h),a		;409b
	call arranca_el_hardware		;409e   ; prepara el VDP y la pantalla
	xor a			;40a1
	ld (0e005h),a		;40a2   ; y ahora si, se suelta
	call 0013eh		;40a5   ; BIOS RDVDP - Reads VDP status register | se lee el estado del VDP antes de abrir, para no entrar con una bandera vieja
	ei			;40a8
espera_para_siempre:
	jr espera_para_siempre		;40a9   ; aqui se queda el hilo principal: todo lo demas pasa en la interrupcion

; ----------------------------------------------------------------------
; EL REPARTO DE ESCENAS, que es lo que corre en cada cuadro. Elige a donde ir con el numero de escena que hay en (0xE000) y, ademas, APILA a mano la direccion por la que seguira cuando la escena haga `ret`: una de dos, segun el bit 6 de (0xE002). La escena 8 es la excepcion, y por eso se salta el `push`.
; ----------------------------------------------------------------------
reparte_la_escena:
	ld hl,0e003h		;40ab   ; el contador de cuadros, que casi todo lo demas usa para ir a compas
	inc (hl)			;40ae
	ld a,(0e002h)		;40af   ; el bit 6 de (0xE002) decide cual de los dos remates se apila
	and 040h		;40b2
	ld hl,044bah		;40b4   ; uno
	jr nz,L_40BC		;40b7
	ld hl,0477dh		;40b9   ; y el otro
L_40BC:
	ld a,(0e000h)		;40bc   ; el numero de escena
	cp 008h		;40bf   ; la escena 8 no lleva remate detras
	jr z,L_40C4		;40c1
	push hl			;40c3   ; aqui se fabrica el retorno: la escena volvera ahi sola
L_40C4:
	call despacha_por_tabla		;40c4   ; y la tabla de diecisiete entradas va pegada justo detras de este call

; ----------------------------------------------------------------------
; DATOS tabla_de_escenas: 17 entradas, pegada detras del call del despachador;
;   la primera apunta a 0x40E9, justo detras de la tabla
;   0x40c7..0x40e9  (34 bytes)
DATA_tabla_de_escenas:
	defw 040e9h,040f4h,04105h,04114h,04117h,0411fh,04129h,04181h	; 40c7
	defw 0430eh,04165h,041a7h,041c4h,041dah,04221h,04235h,042ach	; 40d7
	defw 04260h	; 40e7  -> L_4260

; ======================================================================
; CODIGO 0x40e9..0x414c  (99 bytes)
; ======================================================================



; ----------------------------------------------------------------------
; ESCENA 0: el arranque frio. Monta la pantalla, pinta el titulo y pasa al compas de 0x4114.
; ----------------------------------------------------------------------
L_40E9:
	call limpia_la_pantalla		;40e9   ; limpia la VRAM
	call monta_la_pantalla_del_titulo		;40ec   ; monta el decorado del titulo
	call L_4708		;40ef   ; y vuelca los ocho registros del VDP
	jr L_4114		;40f2

; ----------------------------------------------------------------------
; ESCENA 1: el letrero de "VIDEO CARTRIDGE" parpadeando. Solo hace algo en los cuadros impares, que es de donde sale el ritmo del parpadeo.
; ----------------------------------------------------------------------
L_40F4:
	ld a,(0e003h)		;40f4   ; el contador de cuadros
	rra			;40f7   ; el bit 0 al acarreo: uno de cada dos cuadros no se hace nada
	ret nc			;40f8
	call L_4B6B		;40f9   ; y el resto del parpadeo lo lleva esta
	ret nz			;40fc
	ld hl,04a53h		;40fd   ; el rotulo "(r) VIDEO CARTRIDGE (r)"
	call pinta_rotulo		;4100   ; con la mascara a 0xFF, o sea pintandolo
	jr L_411B		;4103

; ----------------------------------------------------------------------
; ESCENA 2: la cuenta atras que lo apaga. Cuando (0xE004) llega a cero, borra el mismo rotulo con el mismo guion -esta vez por la puerta de la mascara 0x00- y sigue.
; ----------------------------------------------------------------------
L_4105:
	ld hl,0e004h		;4105   ; el plazo
	dec (hl)			;4108
	ret nz			;4109   ; mientras no llegue a cero, no se toca nada
	ld hl,04a53h		;410a   ; el mismo guion de antes
	call borra_rotulo		;410d   ; pero por la puerta que escribe ceros: lo BORRA
	xor a			;4110
	ld (0e00ah),a		;4111   ; y se apaga la bandera de 0xE00A
L_4114:
	jp pasa_a_la_escena_siguiente		;4114

; ----------------------------------------------------------------------
; ESCENA 3: espera a que el jugador se decida. Si 0x44F7 dice que si (acarreo), se sale por donde estaba; si no, se pasa a la escena 0 de la partida.
; ----------------------------------------------------------------------
L_4117:
	call barre_una_franja		;4117   ; mira si hay que seguir esperando
	ret c			;411a
L_411B:
	xor a			;411b
	jp L_41BC		;411c

; ----------------------------------------------------------------------
; ESCENA 4: otro plazo, este para la pantalla de seleccion.
; ----------------------------------------------------------------------
L_411F:
	ld hl,0e004h		;411f   ; la cuenta atras
	dec (hl)			;4122
	jp nz,L_4527		;4123   ; mientras corre, la escena de 0x4527
	jp plazo_de_32_y_siguiente_escena		;4126

; ----------------------------------------------------------------------
; ESCENA 5: empieza partida. Pone en marcha el guion de la atraccion -25 bytes de pasos con su duracion, y el primer plazo, 0x5C cuadros, a mano- y copia los nueve valores iniciales a 0xE050.
; ----------------------------------------------------------------------
L_4129:
	call baja_los_dos_contadores		;4129   ; comprueba antes si queda algo pendiente
	ret p			;412c
	call pinta_el_marcador		;412d   ; prepara el marcador
	ld hl,0414ch		;4130   ; el guion de pasos
	ld (0e04dh),hl		;4133   ; su puntero vive en (0xE04D)
	ld a,05ch		;4136   ; y el primer plazo, 92 cuadros, va puesto a mano
	ld (0e04fh),a		;4138
	ld hl,043b4h		;413b   ; los nueve valores iniciales de la partida
	ld de,0e050h		;413e
	ld bc,00009h		;4141   ; nueve bytes
	ldir		;4144
	ld (0e059h),bc		;4146   ; BC vale cero al salir del ldir, y se aprovecha para dejar (0xE059) a cero
	jr $+104		;414a

; ----------------------------------------------------------------------
; DATOS guion_de_la_atraccion: 25 bytes de pasos con su duracion; arranca en
;   0x4130
;   0x414c..0x4165  (25 bytes)
DATA_guion_de_la_atraccion:
	defb 008h,010h,038h,080h,000h,010h,038h,040h,008h,040h,004h,038h,008h,060h,038h,008h	; 414c  ..8...8@.@.8.`8.
	defb 008h,038h,038h,024h,008h,040h,038h,014h,008h	; 415c  .88$.@8..

; ======================================================================
; CODIGO 0x4165..0x4255  (240 bytes)
; ======================================================================



; ----------------------------------------------------------------------
; ESCENA 6: arranca la vida. Baja el contador de vidas de (0xE050), y si la partida es de dos jugadores -bit 5 de (0xE002)- pinta antes el rotulo "PLAYER 1".
; ----------------------------------------------------------------------
L_4165:
	call limpia_la_pantalla		;4165   ; limpia la pantalla
	ld hl,0e050h		;4168   ; el contador de vidas
	dec (hl)			;416b   ; una menos: esta se va a jugar
	call pinta_el_marcador		;416c   ; repinta el marcador
	ld a,(0e002h)		;416f   ; el bit 5 dice si hay dos jugadores
	and 020h		;4172
	jr z,L_417E		;4174
	ld hl,04a48h		;4176   ; "PLAYER 1"
	call pinta_rotulo_con_marca		;4179
	ld a,04fh		;417c   ; el plazo para el rotulo, 79 cuadros
L_417E:
	inc a			;417e   ; 80 si no hay rotulo que ensenar
	jr L_41BC		;417f

; ----------------------------------------------------------------------
; ESCENA 7: el guion de la atraccion, paso a paso. Cada paso vive en (0xE009) y dura lo que diga el guion; cuando el plazo se agota, del guion sale el paso siguiente Y su nueva duracion, y el puntero queda guardado en (0xE04D).
; ----------------------------------------------------------------------
pasa_el_guion_de_la_atraccion:
	ld hl,0e04fh		;4181   ; el plazo del paso en curso
	dec (hl)			;4184
	ld b,(hl)			;4185   ; B se queda con lo que queda, para mirarlo despues de escribir
	ld hl,(0e04dh)		;4186   ; donde iba el guion
	ld de,0e009h		;4189
	ld a,(hl)			;418c   ; el paso actual a (0xE009), que es lo que mira el resto del cartucho
	ld (de),a			;418d
	ld a,b			;418e
	or a			;418f   ; si el plazo aun no ha llegado a cero, no se avanza
	jr nz,L_419B		;4190
	inc hl			;4192   ; se agoto: el byte siguiente es la duracion del paso que viene
	ld a,(hl)			;4193
	ld (0e04fh),a		;4194
	inc hl			;4197   ; y se deja el puntero listo para la proxima vez
	ld (0e04dh),hl		;4198
L_419B:
	call L_4C51		;419b   ; mueve lo que haya que mover
	ld a,(0e054h)		;419e   ; si (0xE054) no esta a cero, todavia no toca cambiar de escena
	or a			;41a1
	ret nz			;41a2
L_41A3:
	xor a			;41a3
	jp L_424C		;41a4   ; y si lo esta, se empieza por la escena 0 de la partida

; ----------------------------------------------------------------------
; ESCENA 8: apaga "PLAYER 1" y arranca de verdad. Es la escena sin remate apilado, que es por lo que 0x40BF la trata aparte.
; ----------------------------------------------------------------------
L_41A7:
	ld hl,0e004h		;41a7   ; el plazo del rotulo
	dec (hl)			;41aa
	ret nz			;41ab
	ld hl,04a48h		;41ac   ; el mismo guion de "PLAYER 1"
	call borra_rotulo		;41af   ; por la puerta que escribe ceros: lo borra
L_41B2:
	call L_4C39		;41b2
	ld a,001h		;41b5   ; y se levanta la bandera de "partida en marcha"
	ld (0e054h),a		;41b7
plazo_de_32_y_siguiente_escena:
	ld a,020h		;41ba   ; 32 cuadros de plazo
L_41BC:
	ld (0e004h),a		;41bc
pasa_a_la_escena_siguiente:
	ld hl,0e000h		;41bf   ; el numero de escena
	inc (hl)			;41c2   ; la siguiente
	ret			;41c3

; ----------------------------------------------------------------------
; ESCENA 9: el compas de la partida. Si (0xE00D) no esta a cero -la senal de que se acabo- salta a la escena 15; si no, espera a que se levante (0xE054).
; ----------------------------------------------------------------------
L_41C4:
	call L_4C51		;41c4
	ld a,(0e00dh)		;41c7   ; la senal de fin de partida
	or a			;41ca
	jr z,L_41D3		;41cb
	ld a,00fh		;41cd   ; escena 15, la del final
	ld (0e000h),a		;41cf
	ret			;41d2
L_41D3:
	ld a,(0e054h)		;41d3   ; y si no, se espera
	or a			;41d6
	ret nz			;41d7
	jr plazo_de_32_y_siguiente_escena		;41d8

; ----------------------------------------------------------------------
; ESCENA 10: prepara la bonificacion y el numero de fase. El 0x5000 de (0xE057) NO es una direccion: es el valor 5000 en BCD, que es la bonificacion con la que se entra en la fase y que 0x5290 va restando de 16 en 16.
; ----------------------------------------------------------------------
prepara_la_bonificacion:
	ld hl,05000h		;41da   ; cinco mil, en BCD
	ld (0e057h),hl		;41dd   ; la bonificacion vive en (0xE057)
	ld hl,0e055h		;41e0   ; y el numero de fase, en (0xE056)
	ld (hl),0ffh		;41e3
	inc hl			;41e5
	ld a,(hl)			;41e6
	cp 009h		;41e7   ; de la fase 9 en adelante no se toca
	jr nc,L_41EE		;41e9
	or a			;41eb
	jr nz,L_41F0		;41ec   ; y si estaba a cero, se empieza por la 1
L_41EE:
	ld (hl),001h		;41ee
L_41F0:
	ld a,(0e050h)		;41f0   ; quedan vidas?
	or a			;41f3
	jr nz,L_4217		;41f4
	call limpia_la_pantalla		;41f6   ; no quedan: limpia y saca el cartel
	ld hl,0e004h		;41f9   ; el plazo del cartel
	dec (hl)			;41fc
	ret nz			;41fd
	ld hl,04255h		;41fe   ; "CONTINUE"
	call pinta_rotulo		;4201
	call pinta_el_marcador		;4204   ; y el marcador
	ld a,010h		;4207   ; escena 16, la de la cuenta atras para continuar
	ld (0e000h),a		;4209
	ld a,0ffh		;420c   ; plazo largo: 255 cuadros
	ld (0e004h),a		;420e
	ld a,021h		;4211
	ld (0e00ch),a		;4213
	ret			;4216
L_4217:
	ld a,(0e080h)		;4217   ; si hay otro jugador esperando, se le cede el turno
	or a			;421a
	jr nz,pasa_a_la_escena_siguiente		;421b
L_421D:
	ld a,009h		;421d
	jr L_424C		;421f

; ----------------------------------------------------------------------
; EL CAMBIO DE JUGADOR, y es una sola instruccion la que lo hace todo: los treinta y dos bytes de estado del jugador que juega viven en 0xE050 y los del otro en 0xE080, y se PERMUTAN con la rutina de intercambiar bloques. No hay dos copias de la logica ni indices: el jugador en turno esta siempre en 0xE050.
; ----------------------------------------------------------------------
cambia_de_jugador:
	ld hl,0e050h		;4221   ; el estado del que juega
	ld de,0e080h		;4224   ; y el del que espera
	ld b,020h		;4227   ; treinta y dos bytes cada uno
	call intercambia_bloques		;4229   ; y se cambian de sitio
	ld hl,0e002h		;422c
	ld a,(hl)			;422f
	xor 080h		;4230   ; el bit 7 de (0xE002) dice de quien es el turno; se le da la vuelta
	ld (hl),a			;4232
L_4233:
	jr L_421D		;4233

; ----------------------------------------------------------------------
; ESCENA 11: el relevo. Cuando se agota el plazo, si el otro jugador no tiene partida (0xE080 a cero) se apaga el bit 6 y sigue el mismo; si la tiene, se pasa a la escena 13.
; ----------------------------------------------------------------------
L_4235:
	ld hl,0e004h		;4235   ; el plazo del cartel de relevo
	dec (hl)			;4238
	ret nz			;4239
	ld a,(0e080h)		;423a   ; el estado del otro jugador
	or a			;423d
	jr nz,escena_13_con_plazo_de_32		;423e
	ld hl,0e002h		;4240
	ld a,(hl)			;4243
	and 0bfh		;4244   ; apaga el bit 6 de (0xE002)
	ld (hl),a			;4246
	jp L_41A3		;4247
escena_13_con_plazo_de_32:
	ld a,00dh		;424a   ; escena 13
L_424C:
	ld (0e000h),a		;424c
	ld a,020h		;424f   ; y 32 cuadros de plazo
	ld (0e004h),a		;4251
	ret			;4254

; ----------------------------------------------------------------------
; DATOS guion_continue: 11 bytes; pinta "CONTINUE" en 0x396C. Lo usa 0x41FE
;   0x4255..0x4260  (11 bytes)
DATA_guion_continue:
	defb 06ch,039h,023h,02fh,02eh,034h,029h,02eh,035h,025h,0ffh	; 4255  l9#/.4).5%.

; ======================================================================
; CODIGO 0x4260..0x4378  (280 bytes)
; ======================================================================



; ----------------------------------------------------------------------
; ESCENA 12: la espera con cuenta atras propia, la de (0xE00C). Mientras corre no se hace nada; al acabar, si el paso del guion es cero saca "GAME OVER" y si no, reparte otra vez.
; ----------------------------------------------------------------------
L_4260:
	ld hl,0e00ch		;4260   ; su propia cuenta atras
	ld a,(hl)			;4263
	or a			;4264
	jr z,L_4269		;4265
	dec (hl)			;4267   ; una menos y a esperar
	ret			;4268
L_4269:
	ld a,(0e009h)		;4269   ; el paso del guion de la atraccion
	or a			;426c
	jr nz,arranca_al_otro_jugador		;426d
	ld hl,0e004h		;426f
	dec (hl)			;4272
	ret nz			;4273
	ld hl,04a3bh		;4274   ; "GAME  OVER", que ademas sigue en el guion de "PLAYER 1"
	call pinta_rotulo_con_marca		;4277
	ld a,00dh		;427a   ; escena 13
	ld (0e000h),a		;427c
	xor a			;427f
	jp L_41BC		;4280

; ----------------------------------------------------------------------
; ESCENA 13: pone en pie al jugador que entra. Le copia sus seis valores iniciales, le da tres vidas y le pone el tanteo a cero -en 0xE049 o en 0xE046 segun de quien sea el turno, que lo dice el bit 7 de (0xE002) pasado al acarreo con `add a,a`.
; ----------------------------------------------------------------------
arranca_al_otro_jugador:
	ld hl,043b7h		;4283   ; los seis valores iniciales
	ld de,0e053h		;4286
	ld bc,00006h		;4289   ; seis bytes
	ldir		;428c
	ld a,003h		;428e   ; tres vidas
	ld (0e050h),a		;4290
	ld a,(0e002h)		;4293   ; el turno
	add a,a			;4296   ; el bit 7 al acarreo
	ld hl,0e049h		;4297   ; el tanteo de un jugador
	jr nc,L_429E		;429a
	ld l,046h		;429c   ; o el del otro, cambiando solo el byte bajo
L_429E:
	xor a			;429e   ; tres bytes de tanteo BCD a cero
	ld (hl),a			;429f
	inc hl			;42a0
	ld (hl),a			;42a1
	inc hl			;42a2
	ld (hl),a			;42a3
	ld a,00ch		;42a4   ; escena 12
	ld (0e000h),a		;42a6
	jp L_4217		;42a9

; ----------------------------------------------------------------------
; ESCENA 14: la bonificacion, que se va gastando. Resta de dieciseis en dieciseis con `daa`, o sea en BCD, y hace sonar el aviso una vez de cada cuatro cuadros. Cuando llega a cero, pasa a cobrar.
; ----------------------------------------------------------------------
consume_la_bonificacion:
	ld bc,(0e057h)		;42ac   ; la bonificacion que queda
	ld a,b			;42b0
	or c			;42b1   ; cero?
	jr z,termina_la_fase		;42b2
	ld de,00010h		;42b4   ; dieciseis menos
	call suma_puntos		;42b7
	call L_5290		;42ba   ; y se repinta
	ld a,(0e003h)		;42bd   ; el contador de cuadros
	and 003h		;42c0   ; uno de cada cuatro
	ret nz			;42c2
	ld a,006h		;42c3   ; el sonido 6, el tictac
	jp L_7BA2		;42c5

; ----------------------------------------------------------------------
; EL FIN DE FASE: suma una vida, sube el numero de fase en BCD y, cada cinco fases, avanza la tanda de decorado (0xE05B de ocho en ocho). Es el unico sitio donde se regala una vida.
; ----------------------------------------------------------------------
termina_la_fase:
	ld a,(0e028h)		;42c8   ; espera a que no quede nada moviendose
	or a			;42cb
	ret nz			;42cc
	ld hl,0e050h		;42cd   ; las vidas
	inc (hl)			;42d0   ; una mas
	inc hl			;42d1
	ld a,(hl)			;42d2
	add a,001h		;42d3   ; la fase siguiente, en BCD
	daa			;42d5
	ld (hl),a			;42d6
	inc hl			;42d7
	inc (hl)			;42d8   ; y el contador de fases dentro de la tanda
	ld a,(hl)			;42d9
	cp 005h		;42da   ; cada cinco
	jr nz,L_42ED		;42dc
	xor a			;42de
	ld (hl),a			;42df   ; se reinicia
	ld hl,0e05bh		;42e0
	ld a,(hl)			;42e3
	add a,008h		;42e4   ; y el decorado salta ocho
	cp 018h		;42e6   ; la tanda de decorado da la vuelta en 0x18
	jr nz,L_42EC		;42e8
	ld a,010h		;42ea   ; y vuelve a 0x10, o sea que las dos primeras no se repiten
L_42EC:
	ld (hl),a			;42ec
L_42ED:
	ld a,(0e05bh)		;42ed   ; el decorado que toca
	ld (0e05ah),a		;42f0
	ld a,006h		;42f3   ; la fase 6
	ld (0e056h),a		;42f5
	ld hl,08000h		;42f8   ; y la bonificacion de las fases largas: 8000, tambien en BCD
	ld (0e057h),hl		;42fb
	xor a			;42fe
	ld (0e00dh),a		;42ff   ; se baja la senal de fin de partida
	ld (0e059h),a		;4302
	jp L_4233		;4305
remata_la_fase:
	call reparte_los_puntos_pendientes		;4308   ; reparte los puntos que queden
	jp plazo_de_32_y_siguiente_escena		;430b

; ----------------------------------------------------------------------
; ESCENA 15: el fin de partida. Suena el 0x94, se pinta el cartel y se deja un plazo de 80 cuadros; mientras corre, el bit 3 del propio plazo hace parpadear lo que haya en pantalla.
; ----------------------------------------------------------------------
L_430E:
	ld a,(0e001h)		;430e   ; solo la primera vez
	or a			;4311
	jr nz,L_432C		;4312
	ld a,094h		;4314   ; el sonido del fin de partida
	call L_7BA2		;4316
	ld a,050h		;4319   ; 80 cuadros de plazo
	ld (0e004h),a		;431b
L_431E:
	call limpia_la_pantalla		;431e   ; limpia
	call L_4347		;4321   ; y monta el decorado del cartel
	call barre_la_pantalla_entera		;4324
	ld hl,0e001h		;4327
	inc (hl)			;432a   ; se marca que ya se ha hecho
	ret			;432b
L_432C:
	ld hl,0e004h		;432c   ; el plazo
	dec (hl)			;432f
	jr z,remata_la_fase		;4330
	bit 3,(hl)		;4332   ; el bit 3 del plazo: parpadeo de ocho en ocho cuadros
	jp nz,barre_la_pantalla_entera		;4334
	call donde_va_el_cursor		;4337
	ld bc,0001bh		;433a   ; 27 celdas que borrar
	xor a			;433d
	jp rellena_vram		;433e

; ----------------------------------------------------------------------
; EL MONTAJE DE LA PANTALLA DEL TITULO. Cuatro cargas encadenadas y, al final, un bucle que repite DIECISIETE veces el mismo bloquecito de dieciseis bytes por la VRAM: es como se pinta la cenefa sin guardarla diecisiete veces.
; ----------------------------------------------------------------------
monta_la_pantalla_del_titulo:
	call L_4B49		;4341
	call carga_la_pantalla_de_fondo		;4344
L_4347:
	ld hl,047f1h		;4347   ; los patrones del titulo
	ld de,07600h		;434a   ; a 0x3600 de la VRAM
	call L_45CD		;434d
	ld de,05600h		;4350   ; y la tabla de color
	ld bc,00180h		;4353
	ld a,070h		;4356   ; relleno de 0x70, o sea un color plano
	call rellena_vram		;4358
	ld hl,04a69h		;435b   ; los colores del rotulo
	call descomprime		;435e
	ld de,04600h		;4361   ; desde 0x0600
	ld b,011h		;4364   ; diecisiete veces
L_4366:
	push bc			;4366
	push de			;4367
	ld hl,04378h		;4368   ; el mismo bloquecito
	call L_45CD		;436b
	pop hl			;436e
	ld bc,00010h		;436f   ; y cada vuelta dieciseis celdas mas alla
	add hl,bc			;4372
	ex de,hl			;4373
	pop bc			;4374
	djnz L_4366		;4375
	ret			;4377

; ----------------------------------------------------------------------
; DATOS bloque_4378: 9 bytes -> 16 en VRAM. Lo carga 0x4368
;   0x4378..0x4381  (9 bytes)
DATA_bloque_4378:
	defb 00ah,0e0h,003h,090h,083h,080h,080h,060h,000h	; 4378  .......`.

; ======================================================================
; CODIGO 0x4381..0x43b4  (51 bytes)
; ======================================================================



; ----------------------------------------------------------------------
; EL CIERRE DE LA PARTIDA: borra el tanteo del jugador que toque -0xE049 o 0xE046 segun el bit 5- propagando un cero con `ldir` desde la propia celda, vuelve a poner los nueve valores iniciales y, si hay dos jugadores, copia el estado entero al hueco del segundo.
; ----------------------------------------------------------------------
reparte_los_puntos_pendientes:
	ld hl,0e049h		;4381   ; el tanteo de un jugador
	ld bc,000e7h		;4384   ; 231 bytes por delante
	ld a,(0e002h)		;4387
	and 020h		;438a   ; el bit 5: si hay dos jugadores
	push af			;438c
	jr z,L_4394		;438d
	ld l,046h		;438f   ; entonces el otro tanteo
	inc bc			;4391   ; y tres bytes mas
	inc bc			;4392
	inc bc			;4393
L_4394:
	ld d,h			;4394
	ld e,l			;4395
	inc e			;4396
	ld (hl),000h		;4397   ; se pone un cero
	ldir		;4399   ; y el ldir lo arrastra por todo el bloque
	ld hl,043b4h		;439b   ; los nueve valores iniciales otra vez
	ld de,0e050h		;439e
	ld bc,00009h		;43a1
	ldir		;43a4
	pop af			;43a6
	ret z			;43a7   ; con un solo jugador, aqui se acaba
	ld hl,0e050h		;43a8   ; y con dos, el estado se duplica en 0xE080
	ld de,0e080h		;43ab
	ld bc,00020h		;43ae   ; los treinta y dos bytes
	ldir		;43b1
	ret			;43b3

; ----------------------------------------------------------------------
; DATOS valores_iniciales: 9 bytes a 0xE050; 0x4283 copia los seis de 0x43B7
;   en adelante
;   0x43b4..0x43bd  (9 bytes)
DATA_valores_iniciales:
	defb 003h,001h,001h,001h,002h,0ffh,006h,000h,080h	; 43b4  .........

; ======================================================================
; CODIGO 0x43bd..0x4722  (869 bytes)
; ======================================================================


baja_los_dos_contadores:
	ld hl,0e003h		;43bd   ; el contador de cuadros
	dec (hl)			;43c0
	inc hl			;43c1
	dec (hl)			;43c2   ; y el de al lado
	ret m			;43c3   ; si se paso de cero, se sale con el signo puesto
	ld a,(hl)			;43c4
	srl a		;43c5   ; el bit de abajo al acarreo
	jr c,L_43CB		;43c7
	xor 01fh		;43c9   ; y en media vuelta el indice va al reves: de ahi sale el vaiven
L_43CB:
	ld e,a			;43cb
	ld d,038h		;43cc   ; la fila 0x38 de la VRAM
	ld b,018h		;43ce   ; veinticuatro filas
L_43D0:
	xor a			;43d0
	call escribe_en_vram		;43d1   ; un cero en cada una
	ld a,020h		;43d4   ; y la de abajo, 32 celdas mas alla
	call suma_a_a_de		;43d6
	djnz L_43D0		;43d9
L_43DB:
	ld de,03b00h		;43db   ; los atributos de sprites
	ld a,0d0h		;43de   ; 0xD0 en el byte de fila: es el valor que los saca de la pantalla
	ld bc,00080h		;43e0   ; los 128 bytes de la tabla
	call rellena_vram		;43e3
	xor a			;43e6
	ret			;43e7

; ----------------------------------------------------------------------
; SUMAR PUNTOS, en BCD y a seis digitos. DE trae lo que se suma; el tanteo que se toca es el de 0xE049 o el de 0xE046 segun de quien sea el turno -bit 7 de (0xE002)-, y con el bit 6 puesto no se suma nada, que es como se congela el marcador durante los cortes.
; ----------------------------------------------------------------------
suma_puntos:
	ld a,(0e002h)		;43e8   ; el turno y las banderas
	add a,a			;43eb   ; el bit 7 al acarreo, el 6 al signo
	ret p			;43ec   ; con el bit 6 puesto no se suman puntos
	ld hl,0e049h		;43ed   ; el tanteo de un jugador
	jr nc,L_43F4		;43f0
	ld l,046h		;43f2   ; o el del otro
L_43F4:
	ld a,(hl)			;43f4
	add a,e			;43f5   ; los dos digitos de abajo
	daa			;43f6   ; en BCD
	ld (hl),a			;43f7
	ld e,a			;43f8
	inc l			;43f9
	ld a,(hl)			;43fa
	adc a,d			;43fb   ; los del medio, con el acarreo
	daa			;43fc
	ld (hl),a			;43fd
	ld d,a			;43fe
	inc hl			;43ff
	jr nc,mira_si_es_record		;4400   ; si no llego arriba, ya esta
	ld a,(hl)			;4402
	add a,001h		;4403   ; y el tercer par
	daa			;4405
	ld (hl),a			;4406
	jr nc,mira_la_vida_extra		;4407
	ld bc,09999h		;4409   ; si desborda los seis digitos, el record se clava en 999999
	ld (0e043h),bc		;440c
	ld (0e044h),bc		;4410
	jr L_4477		;4414

; ----------------------------------------------------------------------
; LA VIDA EXTRA. El umbral vive en (0xE053) y se compara con el tercer par de digitos del tanteo, o sea con las centenas de millar. Cada vez que se cruza, el umbral sube DOS -no uno- y, cuando desbordaria, se clava en 0xFF: a partir de ahi ya no hay mas vidas de regalo.
; ----------------------------------------------------------------------
mira_la_vida_extra:
	ld a,(0e053h)		;4416   ; el umbral
	cp (hl)			;4419   ; contra los digitos altos del tanteo
	jr nc,mira_si_es_record		;441a
	push de			;441c
	push hl			;441d
	add a,002h		;441e   ; el siguiente umbral, dos mas
	daa			;4420
	jr nc,L_4425		;4421
	ld a,0ffh		;4423   ; si se paso, 0xFF: no habra mas
L_4425:
	ld (0e053h),a		;4425
	ld hl,0e050h		;4428   ; las vidas
	inc (hl)			;442b   ; una mas
	call pinta_las_vidas		;442c   ; repinta el contador
	ld a,005h		;442f   ; y suena el aviso
	call L_7BA2		;4431
	pop hl			;4434
	pop de			;4435

; ----------------------------------------------------------------------
; EL RECORD. Compara primero el par alto y, solo si empata, los cuatro digitos de abajo con `sbc hl,de`. Si el tanteo gana, el record pasa a ser este.
; ----------------------------------------------------------------------
mira_si_es_record:
	ld a,(0e045h)		;4436   ; el par alto del record
	ld b,(hl)			;4439
	sub b			;443a   ; contra el del tanteo
	jr c,L_4446		;443b
	jr nz,L_4480		;443d   ; si el record es mayor, no hay nada que hacer
	ld hl,(0e043h)		;443f   ; empatan arriba: se miran los cuatro de abajo
	sbc hl,de		;4442
	jr nc,L_4480		;4444
L_4446:
	ld (0e043h),de		;4446   ; el tanteo nuevo manda
	ld a,b			;444a
	ld (0e045h),a		;444b
	jr L_4477		;444e

; ----------------------------------------------------------------------
; EL MARCADOR ENTERO. Pinta los rotulos fijos -"HI", "STAGE", "BONUS" y "1P", mas "2P" si hay dos jugadores-, y detras los numeros. Cuando hay dos jugadores le da la vuelta al bit 7 antes de pintar el segundo tanteo, para que la misma rutina sirva para los dos.
; ----------------------------------------------------------------------
pinta_el_marcador:
	ld hl,0499fh		;4450   ; los cuatro rotulos del marcador
	call pinta_rotulo		;4453
	ld a,(0e002h)		;4456
	bit 5,a		;4459   ; el bit 5: hay dos jugadores?
	jr z,L_446B		;445b
	ld hl,049bdh		;445d   ; entonces tambien el "2P"
	call pinta_rotulo		;4460
	ld a,(0e002h)		;4463
	xor 080h		;4466   ; se finge el otro turno
	call pinta_el_tanteo		;4468   ; y se pinta su tanteo con la misma rutina
L_446B:
	call pinta_las_vidas		;446b   ; el contador de vidas
	call pinta_la_bonificacion		;446e
	ld hl,0e058h		;4471   ; y la bonificacion
	call L_52A0		;4474
L_4477:
	ld hl,0e045h		;4477   ; el record
	ld de,0380fh		;447a   ; en la fila de arriba, columna 15
	call L_4491		;447d
L_4480:
	ld a,(0e002h)		;4480

; ----------------------------------------------------------------------
; PINTAR UN TANTEO. Elige la fila y la variable segun el turno -bit 7 de (0xE002)- y cae en el impresor de BCD. Tres bytes, seis digitos.
; ----------------------------------------------------------------------
pinta_el_tanteo:
	ld de,03805h		;4483   ; la celda de la VRAM del primer tanteo
	ld hl,0e04bh		;4486   ; y su variable
	add a,a			;4489   ; el bit 7 al acarreo
	jr nc,L_4491		;448a
	ld e,025h		;448c   ; la columna del segundo tanteo
	ld hl,0e048h		;448e
L_4491:
	ld b,003h		;4491   ; tres bytes de BCD
	jr imprime_bcd		;4493
pinta_la_bonificacion:
	ld de,0381ch		;4495   ; la celda de la bonificacion
	ld hl,0e051h		;4498
	ld b,001h		;449b   ; un solo byte, dos digitos

; ----------------------------------------------------------------------
; EL IMPRESOR DE BCD, que es de donde salen todos los numeros de la pantalla. Parte cada byte en sus dos digitos y les suma 0x10, que es donde empieza el "0" en la fuente de este cartucho; el digito alto va primero y el puntero de la variable retrocede mientras el de la VRAM avanza, porque el BCD esta guardado del reves.
; ----------------------------------------------------------------------
imprime_bcd:
	ld a,(hl)			;449d   ; el byte que toca
	push af			;449e
	and 00fh		;449f   ; el digito de abajo
	or 010h		;44a1   ; +0x10: el "0" de la fuente
	ld c,a			;44a3
	pop af			;44a4
	and 0f0h		;44a5   ; y el de arriba
	rra			;44a7   ; cuatro veces a la derecha
	rra			;44a8
	rra			;44a9
	rra			;44aa
	or 010h		;44ab
	call escribe_en_vram		;44ad   ; primero el alto
	inc de			;44b0
	ld a,c			;44b1
	call escribe_en_vram		;44b2   ; y detras el bajo
	dec hl			;44b5   ; la variable va hacia atras
	inc de			;44b6   ; y la pantalla hacia delante
	djnz imprime_bcd		;44b7
	ret			;44b9

; ----------------------------------------------------------------------
; EL PARPADEO DEL "1P" / "2P". Cada 32 cuadros -los cinco bits de abajo del contador a cero- repinta o borra el rotulo del jugador que esta en turno. Con dos jugadores se descuenta uno para que los dos no parpadeen a la vez.
; ----------------------------------------------------------------------
parpadea_el_turno:
	ld hl,(0e002h)		;44ba   ; de un tiron: (0xE002) y el contador de cuadros
	ld a,01fh		;44bd   ; los cinco bits de abajo
	and h			;44bf
	ret nz			;44c0   ; solo uno de cada 32 cuadros
	ld c,a			;44c1
	bit 5,h		;44c2   ; con dos jugadores
	jr z,L_44C7		;44c4
	dec c			;44c6   ; se desfasa uno
L_44C7:
	bit 7,l		;44c7   ; el bit 7 dice de quien es el turno
	ld hl,049b7h		;44c9   ; el rotulo de uno
	jr z,L_44D1		;44cc
	ld hl,049bdh		;44ce   ; o el del otro
L_44D1:
	jp L_4068		;44d1   ; y se pinta con la mascara que traiga C

; ----------------------------------------------------------------------
; EL CONTADOR DE VIDAS, pintado como cinco marcas de derecha a izquierda: mientras queden vidas se escribe la marca 0x0B y, en cuanto se acaban, un cero. Por eso el hueco se ve siempre, aunque solo queden dos.
; ----------------------------------------------------------------------
pinta_las_vidas:
	ld de,0383dh		;44d4   ; la celda mas a la derecha
	ld a,(0e050h)		;44d7   ; las vidas que quedan
	ld c,a			;44da
	ld b,005h		;44db   ; cinco marcas como maximo
	ld a,00bh		;44dd   ; la marca
L_44DF:
	dec c			;44df   ; una menos
	jp p,L_44E5		;44e0
	ld a,000h		;44e3   ; agotadas: a partir de aqui, celda vacia
L_44E5:
	call escribe_en_vram		;44e5
	dec de			;44e8   ; y hacia la izquierda
	djnz L_44DF		;44e9
	ret			;44eb
barre_la_pantalla_entera:
	ld a,000h		;44ec   ; se empieza por la fila 0
	ld (0e00ah),a		;44ee
L_44F1:
	call barre_una_franja		;44f1   ; y se barre hasta que la rutina diga que ha terminado
	jr c,L_44F1		;44f4
	ret			;44f6

; ----------------------------------------------------------------------
; EL BARRIDO DE LA PANTALLA, tres filas por llamada. (0xE00A) dice por donde va; devuelve acarreo mientras quede trabajo, y al pasar de 17 saca la pantalla de seleccion. Las tres filas se borran a la vez, que es lo que hace que la cortina baje a buen ritmo sin comerse el cuadro.
; ----------------------------------------------------------------------
barre_una_franja:
	ld hl,0e00ah		;44f7   ; por donde iba
	ld a,(hl)			;44fa
	inc (hl)			;44fb   ; y la deja avanzada
	cp 011h		;44fc   ; diecisiete pasadas
	jr nc,L_451C		;44fe
	ld de,03888h		;4500   ; la esquina de arriba
	ld c,a			;4503
	add a,e			;4504   ; mas el paso, que es la columna
	ld e,a			;4505
	ld a,c			;4506
	add a,a			;4507   ; el paso por dos
	add a,0c0h		;4508   ; +0xC0: de ahi sale el patron de la cortina
	ld c,a			;450a
	ld b,003h		;450b   ; tres filas de golpe
	xor a			;450d
L_450E:
	call escribe_en_vram		;450e
	ld a,020h		;4511   ; la de abajo
	call suma_a_a_de		;4513
	ld a,c			;4516
	inc c			;4517
	djnz L_450E		;4518
	scf			;451a   ; acarreo: todavia queda
	ret			;451b
L_451C:
	push af			;451c
	ld hl,049c3h		;451d   ; "PLAY SELECT" con sus cuatro opciones
	call z,pinta_rotulo		;4520
	pop af			;4523
	cp 034h		;4524   ; y se avisa si se llego al paso 52
	ret			;4526
L_4527:
	ld bc,03e3fh		;4527   ; el par de patrones del cursor
	bit 3,(hl)		;452a   ; el bit 3 del plazo: parpadea de ocho en ocho cuadros
	jr nz,L_4531		;452c
L_452E:
	ld bc,00000h		;452e   ; y en la otra mitad, celdas vacias
L_4531:
	call donde_va_el_cursor		;4531   ; donde va el cursor
	ld a,b			;4534
	call escribe_en_vram		;4535   ; los dos patrones, uno detras de otro
	ld a,c			;4538
	inc de			;4539
	call escribe_en_vram		;453a
	ret			;453d

; ----------------------------------------------------------------------
; DONDE CAE EL CURSOR DEL MENU. La opcion elegida vive en (0xE042); sumando 0x14 y girando dos veces a la derecha sale directamente el byte bajo de la celda, con la fila 0x7A de la VRAM fija en D.
; ----------------------------------------------------------------------
donde_va_el_cursor:
	ld a,(0e042h)		;453e   ; la opcion elegida
	add a,014h		;4541   ; el desplazamiento hasta la primera fila del menu
	rrca			;4543   ; dos giros: cada opcion esta a cuatro filas de la anterior
	rrca			;4544
	ld e,a			;4545
	ld d,07ah		;4546   ; la pagina, fija
	ret			;4548
pinta_rotulo_con_marca:
	call pinta_rotulo		;4549   ; el rotulo
	ld a,(0e002h)		;454c   ; el turno
	or a			;454f
	ret p			;4550   ; con el bit 7 a cero no hay marca que anadir
	ld a,012h		;4551   ; y con el a uno, el patron 0x12 delante
	dec de			;4553
	call escribe_en_vram		;4554
	ret			;4557

; ----------------------------------------------------------------------
; LIMPIAR LA PANTALLA: pone la tabla de nombres entera a cero y saca los sprites fuera de cuadro.
; ----------------------------------------------------------------------
limpia_la_pantalla:
	call L_43DB		;4558
	ld de,07800h		;455b   ; la tabla de nombres
	ld bc,00300h		;455e   ; sus 768 celdas
	xor a			;4561   ; a cero

; ----------------------------------------------------------------------
; RELLENAR LA VRAM con el mismo byte, BC veces. Los dos `ex af,af'` seguidos de 0x4565 no son un despiste: valen como espera, y ademas dejan el byte en el juego correcto para el bucle.
; ----------------------------------------------------------------------
rellena_vram:
	call prepara_escritura_vram		;4562   ; prepara el puntero de escritura
L_4565:
	ex af,af'			;4565
L_4566:
	ex af,af'			;4566   ; aqui entra tambien la de repetir del descompresor
	exx			;4567
	out (c),a		;4568   ; el byte, tal cual
	exx			;456a
	ex af,af'			;456b
	dec bc			;456c   ; una menos
	ld a,b			;456d
	or c			;456e
	jr nz,L_4566		;456f   ; hasta que BC llega a cero
	ei			;4571
	ret			;4572

; ----------------------------------------------------------------------
; LA RAMA "REPETIR" DEL DESCOMPRESOR: lee UN byte del bloque y lo escribe C veces cayendo en el relleno de arriba.
; ----------------------------------------------------------------------
repite_byte:
	ld a,(hl)			;4573   ; el byte que se repite
	inc hl			;4574
	jr L_4565		;4575
L_4577:
	di			;4577
	call prepara_escritura_vram		;4578

; ----------------------------------------------------------------------
; LA RAMA "COPIAR" DEL DESCOMPRESOR: B bytes del bloque a la VRAM, tal cual. El baile de `ld a,c / ld c,b / ld b,a` pasa la cuenta de C a B, y el `inc c` de despues es lo que hace que una cuenta de cero valga 256.
; ----------------------------------------------------------------------
copia_literal:
	ld a,c			;457b   ; la cuenta estaba en C y el bucle la quiere en B
	ld c,b			;457c
	ld b,a			;457d
	or a			;457e   ; cuenta cero
	jr z,L_4582		;457f
	inc c			;4581   ; vale 256, no cero
L_4582:
	ld a,(hl)			;4582   ; byte a byte
	exx			;4583
	out (c),a		;4584
	exx			;4586
	inc hl			;4587
	djnz L_4582		;4588
	dec c			;458a   ; la segunda vuelta del contador largo
	jr nz,L_4582		;458b
	ei			;458d
	ret			;458e

; ----------------------------------------------------------------------
; COPIAR DE VRAM A VRAM, byte a byte y pasando por el Z80: el VDP no sabe hacerlo solo, asi que cada byte se lee por un puerto y se escribe por el otro.
; ----------------------------------------------------------------------
copia_vram_a_vram:
	call lee_de_vram		;458f   ; lee de (HL) en la VRAM
	ex de,hl			;4592
	call escribe_en_vram		;4593   ; y escribe en (DE), tambien en la VRAM
	ex de,hl			;4596
	inc hl			;4597
	inc de			;4598
	dec bc			;4599   ; una menos
	ld a,c			;459a
	or b			;459b
	jr nz,copia_vram_a_vram		;459c
	ret			;459e
duplica_los_tercios_de_color:
	ld de,02000h		;459f   ; el primer tercio de la tabla de color
	ld hl,02800h		;45a2   ; al segundo
L_45A5:
	ld bc,00800h		;45a5   ; dos kilobytes
	call copia_vram_a_vram		;45a8
	ld bc,00800h		;45ab   ; los otros dos kilobytes
	jr copia_vram_a_vram		;45ae
duplica_los_tercios_de_patrones:
	call duplica_los_tercios_de_color		;45b0   ; primero el color
	ld de,00000h		;45b3   ; y luego los patrones, del primer tercio a los otros dos
	ld hl,00800h		;45b6
	jr L_45A5		;45b9
carga_la_pantalla_de_fondo:
	call descomprime_los_dos_bloques		;45bb   ; los dos bloques comprimidos del fondo
	jr duplica_los_tercios_de_patrones		;45be   ; y se reparten a los tres tercios
descomprime_los_dos_bloques:
	ld hl,047deh		;45c0   ; el primero trae su destino delante
	call descomprime		;45c3
	jp descomprime		;45c6   ; y el segundo va pegado detras, con el HL que quedo

; ----------------------------------------------------------------------
; EL DESCOMPRESOR, con tres puertas. Por 0x45C9 el bloque trae delante su destino de VRAM; por 0x45CD el destino ya viene en DE; por 0x45D1 ademas esta puesto el puntero de escritura. El lenguaje son bytes de control, y es al reves de lo que parece: con el bit 7 a CERO se repite un byte y con el bit 7 PUESTO se copian n bytes tal cual.
; ----------------------------------------------------------------------
descomprime:
	ld e,(hl)			;45c9   ; el destino de VRAM, que va delante del bloque
	inc hl			;45ca
	ld d,(hl)			;45cb
	inc hl			;45cc
L_45CD:
	di			;45cd   ; aqui entran los que ya lo traen en DE
	call prepara_escritura_vram		;45ce
L_45D1:
	ld a,(hl)			;45d1   ; el byte de control
	and 07fh		;45d2   ; los siete bits de abajo son la cuenta
	ld c,a			;45d4
	ld a,(hl)			;45d5   ; y el byte entero se guarda para mirarle el bit 7
	inc hl			;45d6
	jr nz,L_45DE		;45d7   ; cuenta distinta de cero: hay tramo
	cp c			;45d9   ; cuenta cero, y el byte es 0x00: se acabo el bloque
	jr nz,descomprime		;45da   ; cuenta cero y el byte es 0x80: detras viene otro destino de VRAM
	ei			;45dc
	ret			;45dd
L_45DE:
	ld b,000h		;45de   ; la parte alta de la cuenta, siempre cero
	cp c			;45e0   ; compara el byte con su propia cuenta: solo difieren si el bit 7 esta puesto
	push af			;45e1
	call nz,copia_literal		;45e2   ; bit 7 puesto -> copiar n bytes tal cual
	pop af			;45e5
	call z,repite_byte		;45e6   ; bit 7 a cero -> repetir el siguiente byte n veces
	di			;45e9
	jr L_45D1		;45ea

; ----------------------------------------------------------------------
; PREPARAR EL PUERTO DE LA VRAM. Usa SETWRT de la BIOS y luego se guarda el puerto de datos en C', para que los bucles de arriba solo tengan que hacer `out (c),a`. Y algo importante: SETWRT se queda con los catorce bits de abajo de HL, que es por lo que los bloques llevan destinos como 0x5800 o 0x6000 -son 0x1800 y 0x2000.
; ----------------------------------------------------------------------
prepara_escritura_vram:
	ex af,af'			;45ec
	ex de,hl			;45ed
	call 00053h		;45ee   ; BIOS SETWRT - Enables VDP to write | SETWRT de la BIOS: el puntero de escritura
	di			;45f1
	ex de,hl			;45f2
	exx			;45f3
	ld a,(00006h)		;45f4   ; el puerto de datos del VDP, de la tabla de la BIOS
	ld c,a			;45f7   ; a C', donde lo esperan los bucles
	exx			;45f8
	ex af,af'			;45f9
	ret			;45fa
prepara_lectura_vram:
	ex de,hl			;45fb
	call 00050h		;45fc   ; BIOS SETRD - Enables VDP to read | SETRD de la BIOS: el puntero de lectura
	di			;45ff
	ex de,hl			;4600
	exx			;4601
	ld a,(00007h)		;4602   ; y el puerto de lectura a C'
	ld c,a			;4605
	exx			;4606
	ret			;4607

; ----------------------------------------------------------------------
; REPARTIR UN BLOQUE A LOS TRES TERCIOS de la pantalla, y ademas a la tabla de color, que esta 0x2000 mas alla. Con dos llamadas encadenadas se cubren los seis destinos sin repetir el bloque seis veces.
; ----------------------------------------------------------------------
copia_a_los_tres_tercios:
	push de			;4608
	call L_4612		;4609
	pop de			;460c
	ld hl,00800h		;460d   ; un tercio son 0x800 bytes
	add hl,de			;4610
	ex de,hl			;4611
L_4612:
	ld hl,00800h		;4612   ; el tercio siguiente
	add hl,de			;4615
	call copia_bloque_guardando		;4616
	push bc			;4619
	ld bc,02000h		;461a   ; la tabla de color esta 0x2000 por encima
	add hl,bc			;461d
	ex de,hl			;461e
	add hl,bc			;461f
	ex de,hl			;4620
	pop bc			;4621
copia_bloque_guardando:
	push bc			;4622
	push de			;4623
	push hl			;4624
	call copia_vram_a_vram		;4625   ; copia y deja los registros como estaban
	pop hl			;4628
	pop de			;4629
	pop bc			;462a
	ret			;462b

; ----------------------------------------------------------------------
; LISTAS DE PATRON REPETIDO, y es una maquina de dos lineas que se usa por toda la ROM: cada entrada es `[N][ocho bytes]` y escribe ESE patron N veces seguidas. El truco esta en el `ld bc,0fff8h / add hl,bc`, que devuelve el puntero al principio del mismo patron despues de cada copia. Asi se llena media pantalla de suelo o de cielo con nueve bytes.
; ----------------------------------------------------------------------
vuelca_patrones_repetidos:
	call prepara_escritura_vram		;462c
L_462F:
	ld a,(hl)			;462f   ; cuantas veces se repite el patron que viene
	inc hl			;4630
	or a			;4631
	ret z			;4632   ; un cero cierra la lista
	ld b,a			;4633
L_4634:
	push bc			;4634
	ld bc,00008h		;4635   ; ocho bytes, que es un patron entero
	call copia_literal		;4638   ; y a la VRAM
	ld bc,0fff8h		;463b   ; retroceso de ocho: el mismo patron otra vez
	add hl,bc			;463e
	pop bc			;463f
	djnz L_4634		;4640   ; hasta completar las N copias
	ld c,008h		;4642   ; y ahora si, el patron siguiente
	add hl,bc			;4644
	jr L_462F		;4645

; ----------------------------------------------------------------------
; GIRAR LOS PATRONES DEL BUFER. El bucle de 0x4663 es una transposicion: saca el bit de arriba de cada uno de los ocho bytes y con ellos arma un byte nuevo, ocho veces. Eso vuelca un dibujo de 8x8 sobre su diagonal, que es como se consiguen las poses giradas sin guardarlas aparte.
; ----------------------------------------------------------------------
transpone_patrones:
	push bc			;4647
	rlca			;4648   ; dos giros a la izquierda: el par de bits de arriba manda
	rlca			;4649
	ld b,a			;464a
	ld a,c			;464b
	and 038h		;464c   ; los bits 3 a 5 eligen la fila de destino
	ld de,0e288h		;464e   ; el bufer de salida
	call suma_a_a_de		;4651
	ld a,c			;4654
	and 007h		;4655   ; y los tres de abajo, la columna
	add a,a			;4657   ; por ocho, que es lo que ocupa un patron
	add a,a			;4658
	add a,a			;4659
	ld hl,0e280h		;465a   ; el bufer de entrada
	call suma_a_a_hl		;465d
L_4660:
	push bc			;4660
	ld c,008h		;4661   ; ocho bytes de salida
L_4663:
	ld b,008h		;4663   ; y ocho bits por byte
L_4665:
	rlc (hl)		;4665   ; el bit de arriba del byte de la fila
	rra			;4667   ; se va metiendo en A por la derecha
	djnz L_4665		;4668
	ld (de),a			;466a   ; el byte armado
	inc de			;466b
	inc hl			;466c
	dec c			;466d
	jr nz,L_4663		;466e
	ld a,0f0h		;4670   ; +0xF0 y `dec d`: retrocede dieciseis, o sea la fila de arriba
	call suma_a_a_de		;4672
	dec d			;4675
	pop bc			;4676
	djnz L_4660		;4677
	pop bc			;4679
	ret			;467a

; ----------------------------------------------------------------------
; PREPARAR UNA FIGURA EN EL BUFER. B dice a que altura del bufer se trabaja (por ocho) y C trae dos cosas: en los dos bits de arriba, si hay que girarla, y en el resto, la variante. La copia de ida y vuelta por 0xE378 es un hueco de paso para no pisar lo que se esta leyendo.
; ----------------------------------------------------------------------
prepara_la_figura:
	ld a,b			;467b   ; la altura, por ocho
	add a,a			;467c
	add a,a			;467d
	add a,a			;467e
	ld (0e37fh),a		;467f   ; se guarda para el resto de la rutina
	ld e,a			;4682
	ld d,000h		;4683
	ld iy,0e280h		;4685   ; y ahi cae dentro del bufer
	add iy,de		;4689
	ld a,c			;468b
	and 0c0h		;468c   ; los dos bits de arriba de C
	call nz,transpone_patrones		;468e   ; si alguno esta puesto, la figura va girada
	ld ix,0e280h		;4691   ; el principio del bufer
	ld c,008h		;4695   ; ocho patrones
L_4697:
	push bc			;4697
	push ix		;4698
	ld hl,0e378h		;469a   ; el hueco de paso
	ld de,00008h		;469d   ; de ocho en ocho: se coge una columna entera
L_46A0:
	ld a,(ix+000h)		;46a0
	ld (hl),a			;46a3
	add ix,de		;46a4
	inc hl			;46a6
	djnz L_46A0		;46a7
	pop ix		;46a9
	pop bc			;46ab
	ld a,003h		;46ac
	push iy		;46ae
L_46B0:
	ex af,af'			;46b0
	push bc			;46b1
	call desplaza_el_bufer		;46b2
	pop bc			;46b5
	push bc			;46b6
	push iy		;46b7
	ld hl,0e378h		;46b9
L_46BC:
	ld a,(hl)			;46bc
	ld (iy+000h),a		;46bd
	inc hl			;46c0
	add iy,de		;46c1
	djnz L_46BC		;46c3
	pop iy		;46c5
	ld a,(0e37fh)		;46c7   ; la altura guardada en 0x467F
	ld c,a			;46ca
	add iy,bc		;46cb
	pop bc			;46cd
	ex af,af'			;46ce
	dec a			;46cf   ; tres pasadas
	jr nz,L_46B0		;46d0
	pop iy		;46d2
	inc ix		;46d4
	inc iy		;46d6
	dec c			;46d8
	jr nz,L_4697		;46d9
	ret			;46db

; ----------------------------------------------------------------------
; DESPLAZAR EL BUFER UN PIXEL. Rota a la izquierda los ocho bytes encadenados -el acarreo de uno entra en el siguiente-, y si al final sale acarreo lo suma al byte de delante: asi la figura se mueve por dentro del patron sin perder el pixel que se sale.
; ----------------------------------------------------------------------
desplaza_el_bufer:
	push bc			;46dc
	call L_46E1		;46dd
	pop bc			;46e0
L_46E1:
	ld hl,0e378h		;46e1   ; el hueco de paso
	ld a,b			;46e4
	call suma_a_a_hl		;46e5   ; B bytes por delante
	push hl			;46e8
	xor a			;46e9
L_46EA:
	dec hl			;46ea   ; de atras hacia delante, arrastrando el acarreo
	rl (hl)		;46eb
	djnz L_46EA		;46ed
	pop hl			;46ef
	ret nc			;46f0   ; si no se salio nada por la izquierda, ya esta
	dec hl			;46f1
	inc (hl)			;46f2   ; y si se salio, entra por el byte de delante
	ret			;46f3

; ----------------------------------------------------------------------
; EL ARRANQUE DEL HARDWARE, lo que hace INIT antes de dormirse: apaga el sonido, borra los dieciseis kilobytes de VRAM enteros y vuelca los ocho registros del VDP desde 0x4722, pasando antes por 0xE038 para dejar una copia en RAM que el resto del cartucho pueda consultar.
; ----------------------------------------------------------------------
arranca_el_hardware:
	ld a,0b8h		;46f4
	call L_7A34		;46f6
	ld a,094h		;46f9   ; el sonido de arranque
	call L_7BA2		;46fb
	ld de,00000h		;46fe   ; la VRAM entera
	ld bc,04000h		;4701   ; los dieciseis kilobytes
	xor a			;4704   ; a cero
	call rellena_vram		;4705
L_4708:
	ld hl,04722h		;4708   ; los ocho registros del VDP
	ld de,0e038h		;470b   ; y su copia en RAM, que queda para consultar
	ld bc,00008h		;470e
	ldir		;4711   ; ocho bytes
L_4713:
	ld hl,0e038h		;4713
	ld d,008h		;4716   ; y ocho escrituras
L_4718:
	ld b,(hl)			;4718   ; el valor
	call 00047h		;4719   ; BIOS WRTVDP - Writes data in the VDP-register | WRTVDP: C lleva el numero de registro
	inc hl			;471c
	inc c			;471d   ; el siguiente registro
	dec d			;471e
	jr nz,L_4718		;471f
	ret			;4721

; ----------------------------------------------------------------------
; DATOS registros_del_vdp: los ocho bytes de R0..R7 que L_4708 copia a 0xE038
;   y vuelca con WRTVDP
;   0x4722..0x472a  (8 bytes)
DATA_registros_del_vdp:
	defb 002h,0e2h,00eh,07fh,007h,076h,003h,0e1h	; 4722  .....v..

; ======================================================================
; CODIGO 0x472a..0x47da  (176 bytes)
; ======================================================================


codigo_huerfano_472A:
	ld (0e03fh),a		;472a   ; ninguna instruccion del cartucho llega hasta aqui
	jr $-26		;472d

; ----------------------------------------------------------------------
; LEER EL MANDO. Pide al PSG el puerto de los mandos y le da la vuelta a los bits (`cpl`), porque en el MSX un boton pulsado se lee como cero. El bit 6 del registro 15 elige el puerto, y el bit 7 de (0xE002) -de quien es el turno- es lo que lo decide: cada jugador tiene el suyo.
; ----------------------------------------------------------------------
lee_el_mando:
	ld e,08fh		;472f   ; la seleccion de puerto
	ld hl,0e002h		;4731
	bit 7,(hl)		;4734   ; el turno
	jr z,L_473A		;4736
	set 6,e		;4738   ; el segundo jugador usa el otro puerto
L_473A:
	ld a,00fh		;473a   ; registro 15 del PSG: el que elige el puerto
	call 00093h		;473c   ; BIOS WRTPSG - Writes data to PSG-register
	ld a,00eh		;473f   ; y el 14, que es donde se lee
	call 00096h		;4741   ; BIOS RDPSG - Reads value from PSG-register
	cpl			;4744   ; pulsado es cero, asi que se invierte
	and 03fh		;4745   ; seis bits: cuatro direcciones y dos botones
	ret			;4747

; ----------------------------------------------------------------------
; LA LECTURA DE CADA CUADRO. Guarda lo que hay ahora en (0xE009) y lo de antes en (0xE008), que es lo que permite distinguir "esta pulsado" de "se acaba de pulsar". Si el bit 4 de (0xE002) esta puesto, en vez del mando se lee el TECLADO.
; ----------------------------------------------------------------------
lee_los_mandos:
	call lee_el_mando		;4748   ; el mando
	bit 4,(hl)		;474b   ; el bit 4: se juega con teclado
	call nz,lee_el_teclado		;474d   ; entonces manda lo que diga el teclado
	ld hl,0e009h		;4750   ; la lectura de este cuadro
	ld c,(hl)			;4753   ; la de antes se guarda al lado
	ld (hl),a			;4754
	dec hl			;4755
	ld (hl),c			;4756
	ret			;4757

; ----------------------------------------------------------------------
; LEER EL TECLADO por filas del PPI, armando los mismos seis bits que devuelve el mando: asi todo lo de arriba funciona igual se juegue con palanca o con teclas.
; ----------------------------------------------------------------------
lee_el_teclado:
	ld a,007h		;4758   ; una fila del teclado
	call 00141h		;475a   ; BIOS SNSMAT - Returns the value of the specified line from the keyboard matrix
	cpl			;475d   ; pulsado es cero, se invierte
	rrca			;475e
	and 020h		;475f
	ld e,a			;4761
	ld a,008h		;4762   ; y otra fila
	call 00141h		;4764   ; BIOS SNSMAT - Returns the value of the specified line from the keyboard matrix
	cpl			;4767
	rrca			;4768
	rrca			;4769
	ld b,a			;476a
	and 004h		;476b
	or e			;476d
	ld c,a			;476e
	ld a,b			;476f   ; la otra fila, recolocada a su sitio
	rrca			;4770
	rrca			;4771
	ld b,a			;4772
	and 018h		;4773   ; las dos teclas de esta fila
	or c			;4775
	ld c,a			;4776
	ld a,b			;4777
	rrca			;4778
	and 003h		;4779   ; y las dos que quedan
	or c			;477b
	ret			;477c

; ----------------------------------------------------------------------
; EL MENU DE SELECCION, y es el remate que 0x40AB apila cuando el bit 6 de (0xE002) esta a cero. Junta las TRES entradas -los dos puertos de mando y el teclado- con un `or`, de modo que en el menu vale cualquiera de ellas, y detecta el FLANCO (`xor c / and b`): lo que cuenta es el momento en que se pulsa, no que siga pulsado.
; ----------------------------------------------------------------------
atiende_el_menu:
	ld e,08fh		;477d   ; el primer puerto de mando
	call L_473A		;477f
	ld d,a			;4782
	ld e,0cfh		;4783   ; y el segundo
	call L_473A		;4785
	or d			;4788   ; se juntan
	ld d,a			;4789
	call lee_el_teclado		;478a   ; mas el teclado
	or d			;478d
	ld hl,0e040h		;478e   ; lo de ahora en (0xE040)
	ld c,(hl)			;4791
	ld (hl),a			;4792   ; y lo de antes justo detras
	inc hl			;4793
	ld (hl),c			;4794
	ld b,a			;4795
	xor c			;4796   ; los bits que han cambiado
	and b			;4797   ; y de esos, los que ahora estan pulsados: el flanco
	ret z			;4798   ; nada nuevo, no se hace nada
	ld b,a			;4799
	ld a,000h		;479a   ; se reinicia el plazo de la pantalla
	ld (0e004h),a		;479c
	ld a,005h		;479f   ; solo la escena 5 responde al menu
	ld hl,0e000h		;47a1
	cp (hl)			;47a4
	jr nz,salta_a_la_escena_5		;47a5
	ld a,b			;47a7
	cp 010h		;47a8   ; de 0x10 para arriba son los botones; por debajo, direcciones
	jr c,mueve_el_cursor		;47aa
	ld hl,047dah		;47ac   ; los cuatro modos de juego
	ld a,(0e042h)		;47af   ; indexados por la opcion elegida
	call suma_a_a_hl		;47b2
	ld a,(hl)			;47b5
	ld (0e002h),a		;47b6   ; y el modo elegido queda en (0xE002)
	ld hl,00008h		;47b9   ; a la escena 8, que es la que arranca sin remate apilado
	ld (0e000h),hl		;47bc
	ret			;47bf
salta_a_la_escena_5:
	ld (hl),a			;47c0
	jp L_431E		;47c1   ; y se monta la pantalla de fin

; ----------------------------------------------------------------------
; MOVER EL CURSOR DEL MENU. Arriba resta y abajo suma, y el `and 003h` del final hace que las cuatro opciones den la vuelta: de la ultima se pasa a la primera sin un solo `cp`.
; ----------------------------------------------------------------------
mueve_el_cursor:
	push bc			;47c4
	call L_452E		;47c5   ; borra el cursor de donde estaba
	pop af			;47c8
	ld hl,0e042h		;47c9   ; la opcion elegida
	ld b,(hl)			;47cc
	rra			;47cd   ; el bit 0: arriba
	jr nc,L_47D1		;47ce
	dec b			;47d0   ; una menos
L_47D1:
	rra			;47d1   ; el bit 1: abajo
	jr nc,L_47D5		;47d2
	inc b			;47d4   ; una mas
L_47D5:
	ld a,b			;47d5
	and 003h		;47d6   ; cuatro opciones, y da la vuelta sola
	ld (hl),a			;47d8
	ret			;47d9

; ----------------------------------------------------------------------
; DATOS tabla_47DA: 4 valores: 40 60 50 70
;   0x47da..0x47de  (4 bytes)

; ----------------------------------------------------------------------
; LOS CUATRO MODOS DE JUEGO, que es lo que el menu deja en (0xE002): 0x40, 0x60, 0x50 y 0x70. El bit 6 va puesto siempre -es lo que le dice a 0x40AB que ya no estamos en el menu-, el bit 5 significa DOS JUGADORES y el bit 4, TECLADO en vez de mando. De ahi salen las cuatro lineas del rotulo: 1PLAYER/2PLAYERS por JOYSTICK/KEYBOARD.
; ----------------------------------------------------------------------
DATA_tabla_47DA:
	defb 040h,060h,050h,070h	; 47da

; ----------------------------------------------------------------------
; DATOS bloque_color_pantalla: 376 bytes -> 512 en la tabla de color (0x2000).
;   Lo carga 0x45C0, y 0x4347 entra por 0x47F1 para cargar solo los 384
;   ultimos
;   0x47de..0x4956  (376 bytes)
DATA_bloque_color_pantalla:
	defb 000h,060h,050h,0ffh,002h,033h,006h,0ffh,088h,000h,003h,003h,00ch,01eh,03eh,03fh	; 47de  .`P..3........>?
	defb 07fh,020h,0ffh,08bh,000h,01ch,022h,063h,063h,063h,022h,01ch,000h,018h,038h,004h	; 47ee  . ...."ccc"...8.
	defb 018h,0cah,07eh,000h,03eh,063h,003h,00eh,03ch,070h,07fh,000h,03eh,063h,003h,00eh	; 47fe  ..~.>c..<p..>c..
	defb 003h,063h,03eh,000h,00eh,01eh,036h,066h,066h,07fh,006h,000h,07fh,060h,07eh,063h	; 480e  .c>...6ff....`~c
	defb 003h,063h,03eh,000h,03eh,063h,060h,07eh,063h,063h,03eh,000h,07fh,063h,006h,00ch	; 481e  .c>.>c`~cc>..c..
	defb 018h,018h,018h,000h,03eh,063h,063h,03eh,063h,063h,03eh,000h,03eh,063h,063h,03fh	; 482e  ....>cc>cc>.>cc?
	defb 003h,063h,03eh,03ch,042h,099h,0a1h,0a1h,099h,042h,03ch,000h,007h,003h,09ch,01ch	; 483e  .c><B....B<.....
	defb 038h,070h,0e1h,0cdh,0cdh,0fdh,079h,000h,000h,000h,0eeh,06bh,06bh,06bh,0ebh,000h	; 484e  8p....y....kkk..
	defb 000h,000h,073h,01ah,07ah,05ah,07ah,000h,003h,000h,0f3h,004h,05bh,004h,000h,001h	; 485e  ..s.zZz.....[...
	defb 07eh,004h,000h,0c1h,01ch,036h,063h,063h,07fh,063h,063h,000h,07eh,063h,063h,07eh	; 486e  ~....6cc.cc.~cc~
	defb 063h,063h,07eh,000h,03eh,063h,060h,060h,060h,063h,03eh,000h,07ch,066h,063h,063h	; 487e  cc~.>c```c>.|fcc
	defb 063h,066h,07ch,000h,07fh,060h,060h,07eh,060h,060h,07fh,000h,07fh,060h,060h,07eh	; 488e  cf|..``~``...``~
	defb 060h,060h,060h,000h,03eh,063h,060h,067h,063h,063h,03fh,000h,063h,063h,063h,07fh	; 489e  ```.>c`gcc?.ccc.
	defb 063h,063h,063h,000h,03ch,005h,018h,083h,03ch,000h,01fh,004h,006h,08bh,066h,03ch	; 48ae  ccc.<...<.....f<
	defb 000h,063h,066h,06ch,078h,07ch,06eh,067h,000h,006h,060h,093h,07fh,000h,063h,077h	; 48be  .cflx|ng..`...cw
	defb 07fh,07fh,06bh,063h,063h,000h,063h,073h,07bh,07fh,06fh,067h,063h,000h,03eh,005h	; 48ce  ..kcc.cs{.ogc.>.
	defb 063h,0a3h,03eh,000h,07eh,063h,063h,063h,07eh,060h,060h,000h,03eh,063h,063h,063h	; 48de  c.>.~ccc~``.>ccc
	defb 06fh,066h,03dh,000h,07eh,063h,063h,062h,07ch,066h,063h,000h,03eh,063h,060h,03eh	; 48ee  of=.~ccb|fc.>c`>
	defb 003h,063h,03eh,000h,07eh,006h,018h,001h,000h,006h,063h,082h,03eh,000h,004h,063h	; 48fe  .c>.~.....c.>..c
	defb 0a3h,036h,01ch,008h,000h,063h,063h,06bh,06bh,07fh,077h,022h,000h,063h,076h,03ch	; 490e  .6...cckk.w".cv<
	defb 01ch,01eh,037h,063h,000h,066h,066h,07eh,03ch,018h,018h,018h,000h,07fh,007h,00eh	; 491e  ..7c.ff~<.......
	defb 01ch,038h,070h,07fh,008h,000h,0a0h,000h,000h,002h,000h,08ah,0aah,0aah,0dah,000h	; 492e  .8p.............
	defb 000h,008h,048h,0eeh,04ah,04ah,06ah,000h,00fh,01fh,0ffh,0ffh,0ffh,0ffh,00fh,000h	; 493e  ..H.JJj.........
	defb 000h,0feh,0e0h,0e0h,0c0h,0c0h,080h,000h	; 494e  ........

; ----------------------------------------------------------------------
; DATOS bloque_patrones_4956: 73 bytes -> 512 en la tabla de patrones (0x0000)
;   0x4956..0x499f  (73 bytes)
DATA_bloque_patrones_4956:
	defb 000h,040h,008h,000h,0a8h,000h,088h,000h,000h,000h,000h,000h,000h,000h,000h,088h	; 4956  .@..............
	defb 000h,000h,000h,000h,000h,000h,000h,000h,000h,088h,000h,000h,000h,000h,000h,000h	; 4966  ................
	defb 000h,000h,000h,088h,000h,000h,000h,000h,000h,000h,000h,000h,088h,008h,055h,008h	; 4976  ..............U.
	defb 088h,008h,0ddh,002h,000h,006h,033h,082h,0e5h,05eh,006h,000h,003h,0f0h,005h,090h	; 4986  ......3..^......
	defb 038h,0f0h,078h,0f0h,078h,0f0h,078h,0f0h,000h	; 4996  8.x.x.x..

; ----------------------------------------------------------------------
; DATOS guion_marcador: 30 bytes, 4 tramos: "HI", "STAGE", "BONUS" y "1P". Lo
;   pinta 0x4450
;   0x499f..0x49bd  (30 bytes)
DATA_guion_marcador:
	defb 00ch,038h,028h,029h,020h,0feh,016h,038h,033h,034h,021h,027h,025h,020h,0feh,02ch	; 499f  .8() ..834!'% .,
	defb 038h,022h,02fh,02eh,035h,033h,020h,0feh,002h,038h,011h,030h,020h,0ffh	; 49af  8"/.53 ..8.0 .

; ----------------------------------------------------------------------
; DATOS guion_2p: 6 bytes: "2P" en 0x3822. Lo pinta 0x445D
;   0x49bd..0x49c3  (6 bytes)
DATA_guion_2p:
	defb 022h,038h,012h,030h,020h,0ffh	; 49bd

; ----------------------------------------------------------------------
; DATOS guion_play_select: 120 bytes, 6 tramos: "PLAY SELECT", las cuatro
;   filas del menu y el "(c) 1984". Lo pinta 0x451D
;   0x49c3..0x4a3b  (120 bytes)
DATA_guion_play_select:
	defb 0abh,039h,030h,02ch,021h,039h,000h,033h,025h,02ch,025h,023h,034h,0feh,007h,03ah	; 49c3  .90,!9.3%,%#4..:
	defb 0c1h,0e0h,0dch,0d1h,0e9h,0d5h,0e2h,000h,000h,0ech,0edh,000h,0dah,0dfh,0e9h,0e3h	; 49d3  ................
	defb 0e4h,0d9h,0d3h,0dbh,0feh,047h,03ah,0c2h,0e0h,0dch,0d1h,0e9h,0d5h,0e2h,0e3h,000h	; 49e3  .....G:.........
	defb 0ech,0edh,000h,0dah,0dfh,0e9h,0e3h,0e4h,0d9h,0d3h,0dbh,0feh,087h,03ah,0c1h,0e0h	; 49f3  .............:..
	defb 0dch,0d1h,0e9h,0d5h,0e2h,000h,000h,0ech,0edh,000h,0dbh,0d5h,0e9h,0d2h,0dfh,0d1h	; 4a03  ................
	defb 0e2h,0d4h,0feh,0c7h,03ah,0c2h,0e0h,0dch,0d1h,0e9h,0d5h,0e2h,0e3h,000h,0ech,0edh	; 4a13  ....:...........
	defb 000h,0dbh,0d5h,0e9h,0d2h,0dfh,0d1h,0e2h,0d4h,0feh,00bh,039h,01ah,01bh,01ch,01dh	; 4a23  ...........9....
	defb 01eh,01fh,000h,011h,019h,018h,014h,0ffh	; 4a33  ........

; ----------------------------------------------------------------------
; DATOS guion_game_over: "GAME  OVER" en 0x396B, y acaba en 0xFE: sigue en el
;   guion de PLAYER 1. Lo pinta 0x4274
;   0x4a3b..0x4a48  (13 bytes)
DATA_guion_game_over:
	defb 06bh,039h,027h,021h,02dh,025h,000h,000h,02fh,036h,025h,032h,0feh	; 4a3b  k9'!-%../6%2.

; ----------------------------------------------------------------------
; DATOS guion_player_1: 11 bytes: "PLAYER 1" en 0x392C. Lo pinta 0x41AC
;   0x4a48..0x4a53  (11 bytes)
DATA_guion_player_1:
	defb 02ch,039h,030h,02ch,021h,039h,025h,032h,000h,011h,0ffh	; 4a48  ,90,!9%2...

; ----------------------------------------------------------------------
; DATOS guion_video_cartridge: 22 bytes: "(r) VIDEO CARTRIDGE (r)" en 0x3966.
;   Lo pintan 0x40FD y 0x410A
;   0x4a53..0x4a69  (22 bytes)
DATA_guion_video_cartridge:
	defb 066h,039h,020h,000h,036h,029h,024h,025h,02fh,000h,023h,021h,032h,034h,032h,029h	; 4a53  f9 .6)$%/.#!242)
	defb 024h,027h,025h,000h,020h,0ffh	; 4a63

; ----------------------------------------------------------------------
; DATOS bloque_color_4A69: 224 bytes -> 272 en color (0x2600). Lo carga 0x435B
;   0x4a69..0x4b49  (224 bytes)
DATA_bloque_color_4A69:
	defb 000h,066h,086h,001h,007h,00fh,01fh,01fh,03fh,004h,03eh,08bh,03fh,01fh,01fh,00fh	; 4a69  .f......?.>.?...
	defb 007h,001h,0f8h,0fdh,0fdh,0fch,084h,006h,001h,081h,085h,003h,0fdh,086h,0f9h,0c0h	; 4a79  ................
	defb 0e0h,0e0h,0c0h,000h,00bh,0efh,005h,000h,08ah,071h,0f3h,0f3h,0f7h,087h,007h,007h	; 4a89  .........q......
	defb 003h,003h,001h,005h,000h,081h,078h,003h,0fdh,088h,0c1h,081h,081h,0c1h,0fdh,0fdh	; 4a99  ......x.........
	defb 0fch,078h,005h,000h,006h,0e3h,081h,0f7h,003h,0ffh,081h,07bh,004h,000h,082h,007h	; 4aa9  .x.........{....
	defb 0cfh,003h,0dfh,083h,0cfh,0c7h,0d0h,003h,0dfh,081h,0cfh,004h,000h,086h,0c0h,0e0h	; 4ab9  ................
	defb 0e0h,020h,080h,0c0h,004h,0f0h,088h,0e0h,0c0h,001h,007h,00fh,01fh,01fh,03fh,004h	; 4ac9  . ............?.
	defb 03eh,087h,03fh,01fh,01fh,00fh,007h,001h,0f9h,003h,0fdh,081h,085h,006h,001h,081h	; 4ad9  >.?.............
	defb 085h,003h,0fdh,081h,0f9h,004h,0e0h,081h,0efh,003h,0ffh,081h,0f7h,007h,0e3h,004h	; 4ae9  ................
	defb 000h,08ch,007h,08fh,0cfh,0c8h,0c0h,0c7h,0cfh,0deh,0deh,0dfh,0dfh,0cfh,004h,000h	; 4af9  ................
	defb 08ch,0e0h,0f1h,0f9h,079h,079h,0f9h,0f9h,079h,079h,0f9h,0f9h,07dh,005h,000h,081h	; 4b09  ....yy..yy..}...
	defb 0eeh,003h,0feh,081h,0f0h,006h,0e0h,085h,0f3h,0f7h,0f7h,0f3h,0f0h,00bh,0f7h,090h	; 4b19  ................
	defb 000h,080h,080h,000h,003h,08fh,09eh,09ch,0bfh,0bfh,0bch,0beh,09fh,09fh,08fh,083h	; 4b29  ................
	defb 004h,000h,08ch,0e0h,0f0h,070h,038h,0f8h,0f8h,000h,008h,0f8h,0f8h,0f0h,0c0h,000h	; 4b39  .....p8.........

; ======================================================================
; CODIGO 0x4b49..0x4ba6  (93 bytes)
; ======================================================================


L_4B49:
	ld a,011h		;4b49
	ld (0e00ah),a		;4b4b
	ld hl,00000h		;4b4e
	ld (0e00eh),hl		;4b51
	ld hl,04ba6h		;4b54
	ld de,06208h		;4b57
	call L_45CD		;4b5a
	ld de,00208h		;4b5d
	ld bc,000d0h		;4b60
	ld a,0f0h		;4b63
	call rellena_vram		;4b65
	jp duplica_los_tercios_de_patrones		;4b68
L_4B6B:
	ld hl,(0e00eh)		;4b6b
	ld de,00020h		;4b6e
	add hl,de			;4b71
	ld (0e00eh),hl		;4b72
	ex de,hl			;4b75
	or a			;4b76
	ld hl,03aaah		;4b77
	sbc hl,de		;4b7a
	ex de,hl			;4b7c
	ld a,041h		;4b7d
	ld b,003h		;4b7f
	call L_4B97		;4b81
	ld bc,00b0ch		;4b84
	call L_4B97		;4b87
	ld b,c			;4b8a
	call L_4B97		;4b8b
	xor a			;4b8e
	call rellena_vram		;4b8f
	ld hl,0e00ah		;4b92
	dec (hl)			;4b95
	ret			;4b96
L_4B97:
	push de			;4b97
L_4B98:
	call escribe_en_vram		;4b98
	inc de			;4b9b
	inc a			;4b9c
	djnz L_4B98		;4b9d
	pop de			;4b9f
	ld hl,00020h		;4ba0
	add hl,de			;4ba3
	ex de,hl			;4ba4
	ret			;4ba5

; ----------------------------------------------------------------------
; DATOS bloque_4BA6: 147 bytes -> 208 en VRAM. Lo carga 0x4B54
;   0x4ba6..0x4c39  (147 bytes)
DATA_bloque_4BA6:
	defb 00eh,000h,082h,007h,00fh,006h,000h,082h,0f8h,0f0h,004h,03eh,004h,03fh,090h,01fh	; 4ba6  ...........>.?..
	defb 03fh,07fh,0ffh,0feh,0fch,0f8h,0f0h,0e0h,0c0h,080h,000h,000h,000h,03eh,03eh,005h	; 4bb6  ?............>>.
	defb 000h,083h,01fh,07fh,0fbh,005h,000h,083h,00fh,0cfh,0efh,005h,000h,083h,078h,0fch	; 4bc6  ..............x.
	defb 0bch,005h,000h,083h,03fh,07fh,0f3h,005h,000h,083h,087h,0c7h,0c7h,005h,000h,083h	; 4bd6  ....?...........
	defb 0bch,0feh,0dfh,005h,000h,08dh,078h,0fch,0bch,060h,0f0h,0f0h,060h,000h,0f0h,0f0h	; 4be6  ......x..`..`...
	defb 0f0h,03fh,03fh,006h,03eh,090h,0f8h,0fch,0feh,07fh,03fh,01fh,00fh,007h,03eh,03eh	; 4bf6  .??.>.....?...>>
	defb 03eh,07eh,0fch,0fch,0f8h,0e0h,005h,0f1h,083h,0fbh,07fh,01fh,006h,0efh,082h,0cfh	; 4c06  >~..............
	defb 00fh,008h,01eh,088h,0e1h,003h,03fh,0f1h,0e1h,0f3h,07fh,01eh,008h,0e7h,008h,08fh	; 4c16  ......?.........
	defb 008h,01eh,082h,0f1h,0f2h,004h,0f5h,08ah,0f2h,0f1h,0e0h,010h,0c8h,068h,0c8h,028h	; 4c26  .............h.(
	defb 010h,0e0h,000h	; 4c36

; ======================================================================
; CODIGO 0x4c39..0x4c93  (90 bytes)
; ======================================================================


L_4C39:
	call L_5FD6		;4c39
	call L_604C		;4c3c
	ret			;4c3f
L_4C40:
	cp 007h		;4c40
	jr nc,$+103		;4c42
	ld a,(0e052h)		;4c44
	cp 003h		;4c47
	jr z,$+108		;4c49
	jr $+94		;4c4b
L_4C4D:
	ld a,038h		;4c4d
	jr L_4C61		;4c4f
L_4C51:
	ld a,(0e056h)		;4c51
	cp 008h		;4c54
	jr nc,L_4C4D		;4c56
	ld a,(0e14ch)		;4c58
	cp 014h		;4c5b
	jr nc,L_4C6D		;4c5d
	ld a,034h		;4c5f
L_4C61:
	push af			;4c61
	ld hl,0e009h		;4c62
	and (hl)			;4c65
	ld (hl),a			;4c66
	pop af			;4c67
	ld hl,0e138h		;4c68
	and (hl)			;4c6b
	ld (hl),a			;4c6c
L_4C6D:
	ld a,(0e134h)		;4c6d
	cp 006h		;4c70
	push af			;4c72
	jr nc,L_4C7B		;4c73
	ld a,(0e052h)		;4c75
	or a			;4c78
	jr z,L_4C7E		;4c79
L_4C7B:
	call L_4CE4		;4c7b
L_4C7E:
	pop af			;4c7e
	jr nc,L_4C40		;4c7f
	ld a,(0e052h)		;4c81
	push af			;4c84
	and 003h		;4c85
	jr z,L_4C8C		;4c87
	call L_56B3		;4c89
L_4C8C:
	call L_528A		;4c8c
	pop af			;4c8f
	call despacha_por_tabla		;4c90

; ----------------------------------------------------------------------
; DATOS tabla_4C93: 5 entradas, desde el call de 0x4C90; cierra en 0x4C9D, que
;   es su entrada mas baja
;   0x4c93..0x4c9d  (10 bytes)
DATA_tabla_4C93:
	defw 04cc2h,04c9dh,04cbah,04cb5h,04cd6h	; 4c93

; ======================================================================
; CODIGO 0x4c9d..0x4cea  (77 bytes)
; ======================================================================


L_4C9D:
	call L_536F		;4c9d
	call L_5416		;4ca0
L_4CA3:
	call L_5643		;4ca3
	call L_567D		;4ca6
L_4CA9:
	ld hl,0e0b0h		;4ca9
	ld de,03b00h		;4cac
	ld bc,00080h		;4caf
	jp L_4577		;4cb2
L_4CB5:
	call L_57CB		;4cb5
	jr L_4CA3		;4cb8
L_4CBA:
	call L_57CB		;4cba
	call L_5918		;4cbd
	jr L_4CA3		;4cc0
L_4CC2:
	call L_5CE3		;4cc2
	call L_4CE4		;4cc5
	call L_5D76		;4cc8
	call L_5EBC		;4ccb
	call L_5F0F		;4cce
	call L_5EDB		;4cd1
	jr L_4CA9		;4cd4
L_4CD6:
	call L_5B00		;4cd6
	call L_5AAF		;4cd9
	call L_5C1E		;4cdc
	call L_5B7C		;4cdf
	jr L_4CA9		;4ce2
L_4CE4:
	ld a,(0e134h)		;4ce4
	call despacha_por_tabla		;4ce7

; ----------------------------------------------------------------------
; DATOS tabla_4CEA: 10 entradas, desde el call de 0x4CE7; dos de ellas son
;   0x0000 -huecos del reparto- y por eso el encaje crudo se paraba en cinco.
;   Con diez cierra en 0x4CFE, su entrada mas baja no nula, y ademas explica
;   0x502D y 0x5000, que ninguna otra instruccion alcanza
;   0x4cea..0x4cfe  (20 bytes)
DATA_tabla_4CEA:
	defw 04ea7h,04cfeh,04f10h,04d27h,0506dh,00000h,0502dh,00000h	; 4cea
	defw 0500fh,05000h	; 4cfa  -> L_500F L_5000

; ======================================================================
; CODIGO 0x4cfe..0x5116  (1048 bytes)
; ======================================================================


L_4CFE:
	call L_5200		;4cfe
	jr nc,L_4D08		;4d01
	ld hl,0e139h		;4d03
	set 3,(hl)		;4d06
L_4D08:
	ld hl,0e18ch		;4d08
	ld a,(hl)			;4d0b
	cp 07eh		;4d0c
	jr nz,L_4D11		;4d0e
	inc (hl)			;4d10
L_4D11:
	ld hl,0e140h		;4d11
	inc (hl)			;4d14
	ld a,(hl)			;4d15
	cp 008h		;4d16
	jr nz,L_4D27		;4d18
	ld a,(0e009h)		;4d1a
	and 030h		;4d1d
	jr z,L_4D27		;4d1f
	ld hl,051c9h		;4d21
	ld (0e200h),hl		;4d24
L_4D27:
	call L_5171		;4d27
	ld hl,0e104h		;4d2a
	ld b,003h		;4d2d
L_4D2F:
	ld a,(0e130h)		;4d2f
	add a,010h		;4d32
	sub (hl)			;4d34
	inc hl			;4d35
	cp 010h		;4d36
	jr nc,L_4D52		;4d38
	ld a,044h		;4d3a
	sub (hl)			;4d3c
	cp 011h		;4d3d
	jr nc,L_4D52		;4d3f
	dec hl			;4d41
	ld a,0c3h		;4d42
	ld (hl),a			;4d44
	ld de,00300h		;4d45
	call suma_puntos		;4d48
	ld a,004h		;4d4b
	call L_7BA2		;4d4d
	jr L_4D59		;4d50
L_4D52:
	ld a,007h		;4d52
	call suma_a_a_hl		;4d54
	djnz L_4D2F		;4d57
L_4D59:
	ld de,0e156h		;4d59
	call L_533D		;4d5c
	ld a,003h		;4d5f
	call c,L_5304		;4d61
	ld a,(0e202h)		;4d64
	or a			;4d67
	jp z,L_4E74		;4d68
	ld a,(0e052h)		;4d6b
	or a			;4d6e
	call z,L_4E93		;4d6f
	jp c,L_5035		;4d72
	ld a,(0e052h)		;4d75
	cp 002h		;4d78
	jr nz,L_4D9E		;4d7a
	ld hl,0e130h		;4d7c
	ld a,03fh		;4d7f
	cp (hl)			;4d81
	jp nc,L_4E74		;4d82
	ld (hl),a			;4d85
	ld e,000h		;4d86
	ld a,(0e218h)		;4d88
	add a,a			;4d8b
	jr nc,L_4D8F		;4d8c
	inc a			;4d8e
L_4D8F:
	cp 004h		;4d8f
	ld d,a			;4d91
	jr c,L_4DFC		;4d92
	ld d,010h		;4d94
	cp 006h		;4d96
	jr c,L_4D9C		;4d98
	ld d,020h		;4d9a
L_4D9C:
	jr L_4DF5		;4d9c
L_4D9E:
	cp 003h		;4d9e
	jr nz,L_4DFE		;4da0
	ld b,007h		;4da2
	ld hl,0e170h		;4da4
L_4DA7:
	ld a,04ch		;4da7
	sub (hl)			;4da9
	inc hl			;4daa
	cp 020h		;4dab
	jr nc,L_4DB9		;4dad
	ld a,(0e130h)		;4daf
	add a,026h		;4db2
	sub (hl)			;4db4
	cp 005h		;4db5
	jr c,L_4DBE		;4db7
L_4DB9:
	inc hl			;4db9
	djnz L_4DA7		;4dba
	jr L_4E13		;4dbc
L_4DBE:
	ld a,007h		;4dbe
	sub b			;4dc0
	add a,a			;4dc1
	push af			;4dc2
	ld hl,0e180h		;4dc3
	call suma_a_a_hl		;4dc6
	ld (hl),000h		;4dc9
	pop af			;4dcb
	ld hl,0e170h		;4dcc
	call suma_a_a_hl		;4dcf
	ld (hl),0ffh		;4dd2
	ld a,07eh		;4dd4
	ld (0e130h),a		;4dd6
	ld (0e18ch),a		;4dd9
	ld (0e17ch),a		;4ddc
	ld b,018h		;4ddf
	ld hl,0e0fch		;4de1
L_4DE4:
	ld (hl),0c3h		;4de4
	inc hl			;4de6
	djnz L_4DE4		;4de7
	ld a,(0e218h)		;4de9
	cp 001h		;4dec
	ld de,00200h		;4dee
	jr c,L_4E67		;4df1
	ld d,005h		;4df3
L_4DF5:
	push de			;4df5
	ld a,004h		;4df6
	call L_7BA2		;4df8
	pop de			;4dfb
L_4DFC:
	jr L_4E67		;4dfc
L_4DFE:
	cp 004h		;4dfe
	jr nz,L_4E26		;4e00
	ld a,(0e056h)		;4e02
	cp 008h		;4e05
	jr nc,L_4E13		;4e07
	or a			;4e09
	jr nz,L_4E57		;4e0a
	ld a,(0e14ch)		;4e0c
	cp 040h		;4e0f
	jr nc,L_4E57		;4e11
L_4E13:
	ld hl,0e130h		;4e13
	ld a,098h		;4e16
	cp (hl)			;4e18
	jr nc,L_4E74		;4e19
	ld (hl),a			;4e1b
	inc hl			;4e1c
	inc hl			;4e1d
	ld (hl),005h		;4e1e
	call L_5087		;4e20
	jp L_4FF6		;4e23
L_4E26:
	or a			;4e26
	jr nz,L_4E57		;4e27
L_4E29:
	ld a,(0e130h)		;4e29
	sub 083h		;4e2c
	cp 005h		;4e2e
	jr nc,L_4E13		;4e30
	ld hl,0e1d4h		;4e32
	ld a,03eh		;4e35
	sub (hl)			;4e37
	cp 024h		;4e38
	jr nc,L_4E13		;4e3a
	ld a,085h		;4e3c
	ld (0e130h),a		;4e3e
	ld a,004h		;4e41
	ld (0e134h),a		;4e43
	ld a,001h		;4e46
	call L_7BA2		;4e48
	ld a,(0e009h)		;4e4b
	ld (0e138h),a		;4e4e
	ld hl,051bah		;4e51
	jp L_5161		;4e54
L_4E57:
	ld hl,0e130h		;4e57
	ld a,085h		;4e5a
	cp (hl)			;4e5c
	jr nc,L_4E74		;4e5d
	ld (hl),a			;4e5f
	ld e,000h		;4e60
	ld a,(0e218h)		;4e62
	add a,a			;4e65
	ld d,a			;4e66
L_4E67:
	call suma_puntos		;4e67
	xor a			;4e6a
	ld (0e134h),a		;4e6b
	ld (0e140h),a		;4e6e
	ld (0e218h),a		;4e71
L_4E74:
	call L_5272		;4e74
	jp nc,L_4FA5		;4e77
	ld a,002h		;4e7a
	ld (0e134h),a		;4e7c
	ld hl,0e1e0h		;4e7f
	res 7,(hl)		;4e82
	set 6,(hl)		;4e84
	ld hl,0e1c0h		;4e86
	ld a,(hl)			;4e89
	xor 010h		;4e8a
	ld (hl),a			;4e8c
	ld de,00500h		;4e8d
	jp suma_puntos		;4e90
L_4E93:
	ld hl,0e14dh		;4e93
	ld a,(0e130h)		;4e96
	add a,020h		;4e99
	sub (hl)			;4e9b
	cp 005h		;4e9c
	ret nc			;4e9e
	dec hl			;4e9f
	ld a,03ch		;4ea0
	sub (hl)			;4ea2
	inc hl			;4ea3
	cp 030h		;4ea4
	ret			;4ea6
L_4EA7:
	ld a,(0e009h)		;4ea7
	and 00ch		;4eaa
	ld hl,(0e137h)		;4eac
	jr nz,L_4EBC		;4eaf
	ld a,(0e052h)		;4eb1
	cp 004h		;4eb4
	jr z,L_4EBC		;4eb6
	ld a,001h		;4eb8
	jr L_4EC8		;4eba
L_4EBC:
	ld bc,000c0h		;4ebc
	add hl,bc			;4ebf
	ld (0e137h),hl		;4ec0
	ld a,h			;4ec3
	and 00ch		;4ec4
	rrca			;4ec6
	rrca			;4ec7
L_4EC8:
	ld (0e132h),a		;4ec8
	ld a,(0e052h)		;4ecb
	cp 003h		;4ece
	jr nz,L_4EE5		;4ed0
	call L_5200		;4ed2
	jr nc,L_4EE5		;4ed5
	ld hl,0e139h		;4ed7
	set 3,(hl)		;4eda
	ld hl,0e18ch		;4edc
	inc (hl)			;4edf
	ld a,006h		;4ee0
	ld (0e134h),a		;4ee2
L_4EE5:
	call L_5213		;4ee5
	jr z,L_4E74		;4ee8
	xor a			;4eea
	ld (0e272h),a		;4eeb
	ld hl,051e9h		;4eee
	call L_5161		;4ef1
	ld a,001h		;4ef4
	ld (0e134h),a		;4ef6
	ld a,(0e009h)		;4ef9
	ld (0e138h),a		;4efc
	ld (0e139h),a		;4eff
	ld a,(0e052h)		;4f02
	cp 001h		;4f05
	ld a,002h		;4f07
	jr z,L_4F0D		;4f09
L_4F0B:
	ld a,003h		;4f0b
L_4F0D:
	jp L_7BA2		;4f0d
L_4F10:
	call L_5213		;4f10
	jr z,L_4F67		;4f13
	ld hl,0e1e0h		;4f15
	set 7,(hl)		;4f18
	ld hl,0e1c0h		;4f1a
	ld a,(hl)			;4f1d
	push af			;4f1e
	xor 010h		;4f1f
	ld (hl),a			;4f21
	pop af			;4f22
	and 01fh		;4f23
	cp 011h		;4f25
	jr nc,L_4F2D		;4f27
	cp 005h		;4f29
	jr nc,L_4F3C		;4f2b
L_4F2D:
	bit 4,a		;4f2d
	ld a,0fch		;4f2f
	jr z,L_4F35		;4f31
	ld a,004h		;4f33
L_4F35:
	ld b,001h		;4f35
	ld hl,051e6h		;4f37
	jr L_4F59		;4f3a
L_4F3C:
	ld b,000h		;4f3c
	cp 007h		;4f3e
	jr nc,L_4F49		;4f40
	ld a,0f0h		;4f42
	ld hl,051deh		;4f44
	jr L_4F59		;4f47
L_4F49:
	cp 009h		;4f49
	jr nc,L_4F54		;4f4b
	ld a,0f8h		;4f4d
	ld hl,051d1h		;4f4f
	jr L_4F59		;4f52
L_4F54:
	ld a,0fch		;4f54
	ld hl,051dbh		;4f56
L_4F59:
	ld (0e138h),a		;4f59
	ld a,b			;4f5c
	call L_5166		;4f5d
	ld a,003h		;4f60
	ld (0e134h),a		;4f62
	jr L_4F0B		;4f65
L_4F67:
	ld a,(0e1f2h)		;4f67
	or a			;4f6a
	ret z			;4f6b
	ld hl,0521dh		;4f6c
	ld a,(0e1e0h)		;4f6f
	bit 1,a		;4f72
	jr z,L_4F79		;4f74
	ld hl,05227h		;4f76
L_4F79:
	ld a,(0e1c0h)		;4f79
	push af			;4f7c
	and 00fh		;4f7d
	call suma_a_a_hl		;4f7f
	ld a,(hl)			;4f82
	ld (0e130h),a		;4f83
	pop af			;4f86
	and 01fh		;4f87
	cp 010h		;4f89
	jr c,L_4F92		;4f8b
	cpl			;4f8d
	sub 005h		;4f8e
	and 01fh		;4f90
L_4F92:
	cp 007h		;4f92
	jr c,L_4F9A		;4f94
	ld a,003h		;4f96
	jr L_4FA2		;4f98
L_4F9A:
	cp 004h		;4f9a
	ld a,000h		;4f9c
	jr c,L_4FA2		;4f9e
	ld a,001h		;4fa0
L_4FA2:
	ld (0e132h),a		;4fa2
L_4FA5:
	ld a,(0e134h)		;4fa5
	cp 006h		;4fa8
	jr z,L_4FEA		;4faa
	ld a,(0e052h)		;4fac
	or a			;4faf
	jr z,L_4FEA		;4fb0
	ld hl,0e14ch		;4fb2
	ld de,(0e130h)		;4fb5
	ld b,010h		;4fb9
	cp 002h		;4fbb
	jr nz,L_4FC1		;4fbd
	ld b,000h		;4fbf
L_4FC1:
	ld a,d			;4fc1
	sub (hl)			;4fc2
	add a,b			;4fc3
	cp 038h		;4fc4
	jr nc,L_4FD5		;4fc6
	inc hl			;4fc8
	ld a,e			;4fc9
	sub (hl)			;4fca
	add a,030h		;4fcb
	cp 004h		;4fcd
	jr c,L_5035		;4fcf
	cp 038h		;4fd1
	jr c,L_5018		;4fd3
L_4FD5:
	call L_5238		;4fd5
	jr c,L_4FED		;4fd8
	call L_524B		;4fda
	jr c,L_4FED		;4fdd
	call L_52D9		;4fdf
	call L_5A08		;4fe2
	jr c,L_5018		;4fe5
	call L_5326		;4fe7
L_4FEA:
	jp L_5087		;4fea
L_4FED:
	ld de,05231h		;4fed
	call L_61AB		;4ff0
	call L_5087		;4ff3
L_4FF6:
	ld a,009h		;4ff6
	ld (0e134h),a		;4ff8
L_4FFB:
	ld a,048h		;4ffb
	jp L_7BA2		;4ffd
L_5000:
	ld a,(0e012h)		;5000
	or a			;5003
	ret nz			;5004
	ld a,008h		;5005
	ld (0e134h),a		;5007
	ld a,08fh		;500a
	jp L_7BA2		;500c
L_500F:
	ld a,(0e028h)		;500f
	or a			;5012
	ret nz			;5013
	ld (0e054h),a		;5014
	ret			;5017
L_5018:
	ld a,(0e052h)		;5018
	cp 001h		;501b
	jr z,L_4FF6		;501d
	cp 004h		;501f
	ld a,006h		;5021
	ld (0e134h),a		;5023
	jr nz,L_4FFB		;5026
	ld a,007h		;5028
	jp L_7BA2		;502a
L_502D:
	ld hl,0e130h		;502d
	inc (hl)			;5030
	inc (hl)			;5031
	jp L_4E13		;5032
L_5035:
	ld a,(0e052h)		;5035
	or a			;5038
	ld c,001h		;5039
	ld b,000h		;503b
	jr nz,L_5042		;503d
	ld c,004h		;503f
	ld b,c			;5041
L_5042:
	cp 001h		;5042
	ld a,(hl)			;5044
	jr nz,L_5049		;5045
	sub 010h		;5047
L_5049:
	sub 01eh		;5049
	add a,b			;504b
	ld (0e130h),a		;504c
	dec hl			;504f
	ld a,(hl)			;5050
	add a,014h		;5051
	ld (0e131h),a		;5053
	ld a,c			;5056
	ld (0e132h),a		;5057
	call L_5087		;505a
	ld de,02000h		;505d
	call suma_puntos		;5060
	ld a,001h		;5063
	ld (0e00dh),a		;5065
	ld a,011h		;5068
	jp L_7BA2		;506a
L_506D:
	call L_5171		;506d
	ld a,(0e202h)		;5070
	or a			;5073
	jp z,L_4E74		;5074
	call L_4E93		;5077
	jr c,L_5035		;507a
	ld a,(0e130h)		;507c
	cp 079h		;507f
	jp c,L_4E74		;5081
	jp L_4E29		;5084
L_5087:
	ld hl,0e130h		;5087
	ld b,(hl)			;508a
	inc hl			;508b
	ld c,(hl)			;508c
	inc hl			;508d
	ld a,(hl)			;508e
	push af			;508f
	bit 0,a		;5090
	jr z,L_5095		;5092
	inc b			;5094
L_5095:
	ld a,(0e052h)		;5095
	cp 001h		;5098
	jr z,L_50A4		;509a
	pop af			;509c
	add a,a			;509d
	add a,a			;509e
	ld de,0513dh		;509f
	jr L_50AD		;50a2
L_50A4:
	pop af			;50a4
	ld d,a			;50a5
	add a,a			;50a6
	add a,a			;50a7
	add a,a			;50a8
	sub d			;50a9
	ld de,05116h		;50aa
L_50AD:
	call suma_a_a_de		;50ad
	ld hl,0e0c4h		;50b0
	call L_5109		;50b3
	ld a,010h		;50b6
	add a,b			;50b8
	ld b,a			;50b9
	call L_5109		;50ba
	ld a,(0e052h)		;50bd
	cp 004h		;50c0
	jr z,L_50D8		;50c2
	cp 001h		;50c4
	ret nz			;50c6
	ld a,b			;50c7
	add a,010h		;50c8
	ld b,a			;50ca
	ld a,c			;50cb
	sub 008h		;50cc
	ld c,a			;50ce
	call L_510C		;50cf
	ld a,c			;50d2
	add a,010h		;50d3
	ld c,a			;50d5
	jr L_5109		;50d6
L_50D8:
	ld a,(0e003h)		;50d8
	rra			;50db
	rra			;50dc
	and 003h		;50dd
	ld d,a			;50df
	add a,a			;50e0
	add a,d			;50e1
	ld de,05155h		;50e2
	call suma_a_a_de		;50e5
	ld a,(0e134h)		;50e8
	cp 006h		;50eb
	jr c,L_50F5		;50ed
	ld a,(0e0d5h)		;50ef
	add a,008h		;50f2
	ld c,a			;50f4
L_50F5:
	ld b,0a6h		;50f5
	ld a,c			;50f7
	sub 005h		;50f8
	ld c,a			;50fa
	call L_510C		;50fb
	ld a,c			;50fe
	add a,010h		;50ff
	ld c,a			;5101
	call L_510C		;5102
	ld b,096h		;5105
	jr L_510C		;5107
L_5109:
	call L_510C		;5109
L_510C:
	ld (hl),b			;510c
	inc hl			;510d
	ld (hl),c			;510e
	inc hl			;510f
	ld a,(de)			;5110
	inc de			;5111
	ld (hl),a			;5112
	inc hl			;5113
	inc hl			;5114
	ret			;5115

; ----------------------------------------------------------------------
; DATOS tabla_5116: 39 bytes; la indexa 0x50AA
;   0x5116..0x513d  (39 bytes)
DATA_tabla_5116:
	defb 044h,048h,04ch,050h,094h,098h,09ch,054h,058h,05ch,060h,07ch,080h,084h,044h,048h	; 5116  DHLP...TX\`|..DH
	defb 04ch,050h,094h,098h,09ch,054h,058h,05ch,060h,088h,08ch,090h,044h,048h,04ch,050h	; 5126  LP...TX\`...DHLP
	defb 094h,098h,09ch,034h,038h,03ch,040h	; 5136

; ----------------------------------------------------------------------
; DATOS tabla_513D: 24 bytes; la indexa 0x509F
;   0x513d..0x5155  (24 bytes)
DATA_tabla_513D:
	defb 044h,048h,04ch,050h,054h,058h,05ch,060h,044h,048h,04ch,050h,064h,068h,06ch,070h	; 513d  DHLPTX\`DHLPdhlp
	defb 074h,078h,07ch,080h,034h,038h,03ch,040h	; 514d  tx|.48<@

; ----------------------------------------------------------------------
; DATOS tabla_5155: 12 bytes; la indexa 0x50E2
;   0x5155..0x5161  (12 bytes)
DATA_tabla_5155:
	defb 094h,098h,090h,09ch,0a0h,090h,09ch,0a0h,090h,0a4h,0a8h,090h	; 5155  ............

; ======================================================================
; CODIGO 0x5161..0x51b9  (88 bytes)
; ======================================================================


L_5161:
	xor a			;5161
	jr L_5166		;5162
L_5164:
	ld a,001h		;5164
L_5166:
	ld (0e200h),hl		;5166
	ld (0e202h),a		;5169
	xor a			;516c
	ld (0e205h),a		;516d
	ret			;5170
L_5171:
	ld a,(0e202h)		;5171
	ld b,a			;5174
	ld hl,0e205h		;5175
	bit 0,b		;5178
	jr nz,L_517F		;517a
	inc (hl)			;517c
	jr L_5180		;517d
L_517F:
	dec (hl)			;517f
L_5180:
	ld a,(hl)			;5180
	cp 008h		;5181
	ld a,001h		;5183
	jr c,L_5189		;5185
	ld a,004h		;5187
L_5189:
	ld (0e132h),a		;5189
	ld hl,0e130h		;518c
	ld de,(0e200h)		;518f
	bit 0,b		;5193
	ld a,(de)			;5195
	jr nz,L_519A		;5196
	neg		;5198
L_519A:
	add a,(hl)			;519a
	ld (hl),a			;519b
	ex de,hl			;519c
	bit 0,b		;519d
	jr nz,L_51A4		;519f
	inc hl			;51a1
	jr L_51A5		;51a2
L_51A4:
	dec hl			;51a4
L_51A5:
	ld a,(hl)			;51a5
	inc a			;51a6
	jr nz,L_51B3		;51a7
	dec hl			;51a9
	dec hl			;51aa
	inc a			;51ab
	ld (0e202h),a		;51ac
L_51AF:
	ld (0e200h),hl		;51af
	ret			;51b2
L_51B3:
	inc a			;51b3
	jr nz,L_51AF		;51b4
	inc hl			;51b6
	jr L_51AF		;51b7

; ----------------------------------------------------------------------
; DATOS rampa_de_caida_1: FE, 5 4 5 4 4 3 ... 0 0, y FF
;   0x51b9..0x51e8  (47 bytes)
DATA_rampa_de_caida_1:
	defb 0feh,005h,004h,005h,004h,004h,003h,004h,003h,003h,003h,002h,003h,002h,003h,002h	; 51b9  ................
	defb 003h,002h,003h,002h,003h,002h,003h,002h,002h,002h,001h,002h,002h,001h,002h,001h	; 51c9  ................
	defb 001h,002h,001h,001h,001h,001h,000h,001h,001h,000h,001h,000h,000h,000h,0ffh	; 51d9  ...............

; ----------------------------------------------------------------------
; DATOS rampa_de_caida_2: FE, 3 3 3 2 ... 0 0, y FF
;   0x51e8..0x5200  (24 bytes)
DATA_rampa_de_caida_2:
	defb 0feh,003h,003h,003h,002h,003h,002h,003h,002h,003h,003h,003h,002h,002h,001h,002h	; 51e8  ................
	defb 000h,001h,001h,001h,000h,000h,000h,0ffh	; 51f8  ........

; ======================================================================
; CODIGO 0x5200..0x521d  (29 bytes)
; ======================================================================


L_5200:
	ld b,006h		;5200
	ld hl,0e170h		;5202
L_5205:
	ld a,04fh		;5205
	sub (hl)			;5207
	jr c,L_520D		;5208
	cp 005h		;520a
	ret c			;520c
L_520D:
	inc hl			;520d
	inc hl			;520e
	djnz L_5205		;520f
	or a			;5211
	ret			;5212
L_5213:
	ld hl,0e008h		;5213
	ld a,(hl)			;5216
	cpl			;5217
	and 030h		;5218
	inc hl			;521a
	and (hl)			;521b
	ret			;521c

; ----------------------------------------------------------------------
; DATOS curva_de_salto_1: diez alturas, simetrica
;   0x521d..0x5227  (10 bytes)
DATA_curva_de_salto_1:
	defb 01fh,025h,030h,041h,04eh,052h,04eh,041h,030h,025h	; 521d  .%0ANRNA0%

; ----------------------------------------------------------------------
; DATOS curva_de_salto_2: diez alturas, la otra variante
;   0x5227..0x5231  (10 bytes)
DATA_curva_de_salto_2:
	defb 01ah,01fh,027h,034h,03eh,042h,03eh,034h,027h,01fh	; 5227  ..'4>B>4'.

; ----------------------------------------------------------------------
; DATOS tabla_5231: 7 valores; la usa 0x4FED
;   0x5231..0x5238  (7 bytes)
DATA_tabla_5231:
	defb 008h,006h,008h,006h,008h,008h,006h	; 5231

; ======================================================================
; CODIGO 0x5238..0x54c5  (653 bytes)
; ======================================================================


L_5238:
	ld hl,0e157h		;5238
	ld a,(0e130h)		;523b
	add a,030h		;523e
	sub (hl)			;5240
	cp 010h		;5241
	ret nc			;5243
	dec hl			;5244
	ld a,04dh		;5245
	sub (hl)			;5247
	cp 026h		;5248
	ret			;524a
L_524B:
	ld b,003h		;524b
	ld hl,0e150h		;524d
	ld de,0e160h		;5250
L_5253:
	ld a,038h		;5253
	sub (hl)			;5255
	inc hl			;5256
	cp 016h		;5257
	jr nc,L_526C		;5259
	ld a,(de)			;525b
	bit 7,a		;525c
	ld a,(0e130h)		;525e
	ld c,018h		;5261
	jr z,L_5267		;5263
	ld c,010h		;5265
L_5267:
	sub c			;5267
	sub (hl)			;5268
	cp 026h		;5269
	ret c			;526b
L_526C:
	inc hl			;526c
	inc de			;526d
	inc de			;526e
	djnz L_5253		;526f
	ret			;5271
L_5272:
	ld a,(0e202h)		;5272
	or a			;5275
	ret z			;5276
	ld hl,0e1d6h		;5277
	ld a,(0e130h)		;527a
	add a,014h		;527d
	sub (hl)			;527f
	cp 020h		;5280
	ret nc			;5282
	inc hl			;5283
	ld a,04fh		;5284
	sub (hl)			;5286
	cp 030h		;5287
	ret			;5289
L_528A:
	ld a,(0e003h)		;528a
	and 007h		;528d
	ret nz			;528f
L_5290:
	ld hl,0e057h		;5290
	ld a,(hl)			;5293
	sub 010h		;5294
	daa			;5296
	ld (hl),a			;5297
	inc hl			;5298
	jr nc,L_52A0		;5299
	ld a,(hl)			;529b
	sub 001h		;529c
	daa			;529e
	ld (hl),a			;529f
L_52A0:
	ld de,03832h		;52a0
	ld b,002h		;52a3
	call imprime_bcd		;52a5
	ld a,(0e000h)		;52a8
	cp 00bh		;52ab
	ret nz			;52ad
	inc hl			;52ae
	inc hl			;52af
	ld a,(hl)			;52b0
	cp 010h		;52b1
	dec hl			;52b3
	jr z,L_52BB		;52b4
	or (hl)			;52b6
	ret nz			;52b7
	jp L_4FF6		;52b8
L_52BB:
	ld a,(hl)			;52bb
	or a			;52bc
	ret nz			;52bd
	ld a,(0e052h)		;52be
	or a			;52c1
	ld c,a			;52c2
	ld b,003h		;52c3
	ld a,08dh		;52c5
	jr z,L_52D3		;52c7
	ld b,005h		;52c9
	ld a,08bh		;52cb
	bit 1,c		;52cd
	jr nz,L_52D3		;52cf
	ld a,089h		;52d1
L_52D3:
	ex af,af'			;52d3
	ld a,b			;52d4
	ex af,af'			;52d5
	jp L_7BA2		;52d6
L_52D9:
	ld b,003h		;52d9
	ld hl,0e150h		;52db
	ld de,0e160h		;52de
L_52E1:
	ld a,02ch		;52e1
	sub (hl)			;52e3
	inc hl			;52e4
	cp 002h		;52e5
	jr nc,L_52FB		;52e7
	ld a,(de)			;52e9
	bit 7,a		;52ea
	ld a,(0e130h)		;52ec
	ld c,03fh		;52ef
	jr z,L_52F5		;52f1
	ld c,02fh		;52f3
L_52F5:
	add a,004h		;52f5
	sub (hl)			;52f7
	cp c			;52f8
	jr c,L_5301		;52f9
L_52FB:
	inc hl			;52fb
	inc de			;52fc
	inc de			;52fd
	djnz L_52E1		;52fe
	ret			;5300
L_5301:
	ld a,003h		;5301
	sub b			;5303
L_5304:
	ld hl,0e210h		;5304
	call suma_a_a_hl		;5307
	ld a,(hl)			;530a
	or a			;530b
	ret z			;530c
	xor a			;530d
	ld (hl),a			;530e
L_530F:
	ld hl,0e218h		;530f
	inc (hl)			;5312
	ret			;5313
L_5314:
	ld a,006h		;5314
	sub b			;5316
	jr L_5304		;5317
L_5319:
	ld hl,0e217h		;5319
	ld a,(hl)			;531c
	or a			;531d
	ret z			;531e
	xor a			;531f
	ld (hl),a			;5320
	inc hl			;5321
	set 7,(hl)		;5322
	jr L_530F		;5324
L_5326:
	ld b,006h		;5326
	ld de,0e170h		;5328
L_532B:
	call L_533D		;532b
	jr c,L_5314		;532e
	inc de			;5330
	inc de			;5331
	djnz L_532B		;5332
	ld de,0e1b0h		;5334
	call L_533D		;5337
	jr c,L_5319		;533a
	ret			;533c
L_533D:
	ld a,(0e052h)		;533d
	cp 003h		;5340
	ld a,(de)			;5342
	ld c,038h		;5343
	jr nz,L_5349		;5345
	ld c,020h		;5347
L_5349:
	sub c			;5349
	cp 002h		;534a
	ret			;534c
L_534D:
	ld a,(0e134h)		;534d
	or a			;5350
	ld a,(0e009h)		;5351
	jr z,L_5359		;5354
	ld a,(0e138h)		;5356
L_5359:
	and 00ch		;5359
	ret z			;535b
	cp 005h		;535c
	ccf			;535e
	sbc a,a			;535f
	ret nz			;5360
	inc a			;5361
	ret			;5362
L_5363:
	ld a,0c3h		;5363
	ld (0e0f8h),a		;5365
	ld bc,00402h		;5368
	ex de,hl			;536b
	jp L_6A6D		;536c
L_536F:
	ld hl,(0e055h)		;536f
	ld de,0ffb0h		;5372
	add hl,de			;5375
	ld a,h			;5376
	cp 005h		;5377
	ret nc			;5379
	inc l			;537a
	ld h,0a8h		;537b
	ld a,l			;537d
	or a			;537e
	jr nz,L_5388		;537f
	call L_534D		;5381
	dec a			;5384
	ld (0e143h),a		;5385
L_5388:
	ld a,(0e143h)		;5388
	or a			;538b
	jr z,L_5363		;538c
	bit 7,l		;538e
	jr z,L_5397		;5390
	ld a,002h		;5392
	ld (0e213h),a		;5394
L_5397:
	ld a,l			;5397
	add a,002h		;5398
	cp 004h		;539a
	jr c,L_5363		;539c
	ld a,(0e003h)		;539e
	and 004h		;53a1
	add a,0a0h		;53a3
	ld b,a			;53a5
	ld de,09808h		;53a6
	ld a,l			;53a9
	add a,002h		;53aa
	push hl			;53ac
	ld hl,0e0f8h		;53ad
	call L_563A		;53b0
	pop de			;53b3
	ld (0e156h),de		;53b4
	ld hl,071b1h		;53b8
	ld bc,00204h		;53bb
L_53BE:
	ld a,e			;53be
	and 006h		;53bf
	call suma_a_a_hl		;53c1
	ld a,(hl)			;53c4
	inc hl			;53c5
	ld h,(hl)			;53c6
	ld l,a			;53c7
L_53C8:
	call L_53F3		;53c8
	di			;53cb
	set 6,d		;53cc
L_53CE:
	push hl			;53ce
	push bc			;53cf
	push de			;53d0
	call prepara_escritura_vram		;53d1
L_53D4:
	ld a,(hl)			;53d4
	exx			;53d5
	out (c),a		;53d6
	exx			;53d8
	inc hl			;53d9
	inc de			;53da
	ld a,e			;53db
	and 01fh		;53dc
	jr z,L_53E3		;53de
	dec c			;53e0
	jr nz,L_53D4		;53e1
L_53E3:
	pop de			;53e3
	ld a,020h		;53e4
	call suma_a_a_de		;53e6
	pop bc			;53e9
	pop hl			;53ea
	ld a,c			;53eb
	call suma_a_a_hl		;53ec
	djnz L_53CE		;53ef
	ei			;53f1
	ret			;53f2
L_53F3:
	ld a,d			;53f3
	rra			;53f4
	rra			;53f5
	rra			;53f6
	rra			;53f7
	rr e		;53f8
	rra			;53fa
	rr e		;53fb
	rra			;53fd
	rr e		;53fe
	and 003h		;5400
	add a,038h		;5402
	ld d,a			;5404
	ret			;5405
L_5406:
	ld a,(0e134h)		;5406
	ld de,0e009h		;5409
	or a			;540c
	jr z,L_5412		;540d
	ld de,0e138h		;540f
L_5412:
	ld a,(de)			;5412
	and 00ch		;5413
	ret			;5415
L_5416:
	ld ix,0e160h		;5416
	ld de,0e100h		;541a
	ld hl,0e150h		;541d
	ld b,003h		;5420
L_5422:
	push bc			;5422
	ld a,(ix+000h)		;5423
	or a			;5426
	push hl			;5427
	push af			;5428
	call nz,L_5505		;5429
	pop af			;542c
	call z,L_5440		;542d
	pop hl			;5430
	inc hl			;5431
	inc hl			;5432
	inc ix		;5433
	inc ix		;5435
	pop bc			;5437
	djnz L_5422		;5438
	ret			;543a
L_543B:
	call L_5601		;543b
	jr L_5443		;543e
L_5440:
	call L_55FE		;5440
L_5443:
	ld (ix-010h),0ffh		;5443
	push de			;5447
	call L_5472		;5448
	jr nc,L_5470		;544b
	ld a,b			;544d
	push ix		;544e
	pop bc			;5450
	ld hl,00002h		;5451
	add hl,bc			;5454
	dec a			;5455
	jr nz,L_545C		;5456
	ld a,l			;5458
	and 0f0h		;5459
	ld l,a			;545b
L_545C:
	ld a,(hl)			;545c
	or a			;545d
	jr z,L_5470		;545e
	inc hl			;5460
	ld d,(hl)			;5461
	ld a,0efh		;5462
	call suma_a_a_hl		;5464
	dec h			;5467
	ld a,c			;5468
	rra			;5469
	and 007h		;546a
	ld e,a			;546c
	call L_547A		;546d
L_5470:
	pop de			;5470
	ret			;5471
L_5472:
	ld de,0fec0h		;5472
	ld hl,(0e055h)		;5475
	add hl,de			;5478
	ret			;5479
L_547A:
	ld a,(bc)			;547a
	or a			;547b
	ret nz			;547c
	ld a,d			;547d
	sub (hl)			;547e
	ret c			;547f
	cp 003h		;5480
	ret nc			;5482
L_5483:
	push bc			;5483
	ld hl,0e059h		;5484
	inc (hl)			;5487
	ld a,(hl)			;5488
	inc hl			;5489
	inc (hl)			;548a
	and 00fh		;548b
	ld a,(hl)			;548d
	jr nz,L_549A		;548e
	ld b,00ch		;5490
	cp 020h		;5492
	jr nz,L_5498		;5494
	ld b,010h		;5496
L_5498:
	sub b			;5498
	ld (hl),a			;5499
L_549A:
	pop bc			;549a
	add a,a			;549b
	push af			;549c
	ld a,(0e052h)		;549d
	ld hl,054c5h		;54a0
	cp 001h		;54a3
	jr z,L_54B1		;54a5
	ld hl,05a6fh		;54a7
	bit 1,a		;54aa
	jr nz,L_54B1		;54ac
	ld hl,05f8fh		;54ae
L_54B1:
	pop af			;54b1
	call suma_a_a_hl		;54b2
	ld a,(hl)			;54b5
	ld (bc),a			;54b6
	inc hl			;54b7
	inc bc			;54b8
	ld a,(hl)			;54b9
	ld (bc),a			;54ba
	ld hl,0e210h		;54bb
	ld a,e			;54be
	call suma_a_a_hl		;54bf
	ld (hl),002h		;54c2
	ret			;54c4

; ----------------------------------------------------------------------
; DATOS pares_54C5: 32 pares; los lee 0x54A0
;   0x54c5..0x5505  (64 bytes)
DATA_pares_54C5:
	defb 00fh,080h	; 54c5
	defb 00fh,060h	; 54c7
	defb 08fh,060h	; 54c9
	defb 00fh,060h	; 54cb
	defb 00fh,090h	; 54cd
	defb 00fh,060h	; 54cf
	defb 00fh,070h	; 54d1
	defb 08fh,060h	; 54d3
	defb 00fh,0a0h	; 54d5
	defb 00fh,060h	; 54d7
	defb 00fh,060h	; 54d9
	defb 00fh,080h	; 54db
	defb 08fh,060h	; 54dd
	defb 00fh,050h	; 54df
	defb 00fh,060h	; 54e1
	defb 00fh,060h	; 54e3
	defb 00fh,080h	; 54e5
	defb 08fh,060h	; 54e7
	defb 00fh,080h	; 54e9
	defb 00fh,060h	; 54eb
	defb 00fh,060h	; 54ed
	defb 00fh,0a0h	; 54ef
	defb 08fh,060h	; 54f1
	defb 00fh,060h	; 54f3
	defb 00fh,080h	; 54f5
	defb 08fh,060h	; 54f7
	defb 00fh,090h	; 54f9
	defb 00fh,080h	; 54fb
	defb 08fh,060h	; 54fd
	defb 00fh,080h	; 54ff
	defb 00fh,050h	; 5501
	defb 00fh,090h	; 5503

; ======================================================================
; CODIGO 0x5505..0x59f9  (1268 bytes)
; ======================================================================


L_5505:
	call L_534D		;5505
	ld b,a			;5508
	ld a,(0e003h)		;5509
	ld c,a			;550c
	rra			;550d
	sbc a,a			;550e
	add a,b			;550f
	jp z,L_55E9		;5510
	add a,(hl)			;5513
	ld (hl),a			;5514
	cp 002h		;5515
	jr c,L_558D		;5517
	push hl			;5519
	push de			;551a
	call L_55B0		;551b
	pop de			;551e
	pop hl			;551f
	push hl			;5520
	call L_55E9		;5521
	pop hl			;5524
	push de			;5525
	bit 7,(ix+000h)		;5526
	ld de,06feah		;552a
	ld bc,0060ah		;552d
	jr z,L_5537		;5530
	ld de,07026h		;5532
	ld c,008h		;5535
L_5537:
	push de			;5537
	ld e,(hl)			;5538
	inc hl			;5539
	ld d,(hl)			;553a
	ld hl,06fe6h		;553b
	ld a,e			;553e
	and 006h		;553f
	rra			;5541
	call suma_a_a_hl		;5542
	ld a,(hl)			;5545
	pop hl			;5546
	push af			;5547
	call L_53F3		;5548
	pop af			;554b
	call L_5551		;554c
	pop de			;554f
	ret			;5550
L_5551:
	set 6,d		;5551
	push de			;5553
	push bc			;5554
	exx			;5555
	pop bc			;5556
	pop de			;5557
	ld b,c			;5558
	ld hl,00020h		;5559
	exx			;555c
	ld d,a			;555d
	ld a,e			;555e
	ld e,000h		;555f
	or 0e0h		;5561
	neg		;5563
	cp b			;5565
	jr nc,L_556D		;5566
	push bc			;5568
	ld b,a			;5569
	pop af			;556a
	sub b			;556b
	ld e,a			;556c
L_556D:
	exx			;556d
L_556E:
	di			;556e
	call prepara_escritura_vram		;556f
	exx			;5572
	push bc			;5573
L_5574:
	ld a,(hl)			;5574
	inc hl			;5575
	add a,d			;5576
	jr nc,L_557C		;5577
	add a,d			;5579
	and 007h		;557a
L_557C:
	out (c),a		;557c
	djnz L_5574		;557e
	ld a,e			;5580
	call suma_a_a_hl		;5581
	pop bc			;5584
	exx			;5585
	ex de,hl			;5586
	add hl,de			;5587
	ex de,hl			;5588
	djnz L_556E		;5589
	ei			;558b
	ret			;558c
L_558D:
	ld hl,0e160h		;558d
	ld a,(hl)			;5590
	inc hl			;5591
	inc hl			;5592
	add a,(hl)			;5593
	inc hl			;5594
	inc hl			;5595
	add a,(hl)			;5596
	and 00fh		;5597
	cp 00fh		;5599
	jr z,L_55A1		;559b
	ld (ix+000h),000h		;559d
L_55A1:
	call L_55FE		;55a1
	push de			;55a4
	ld de,04800h		;55a5
	ld bc,0060ah		;55a8
	call L_6A6D		;55ab
	pop de			;55ae
	ret			;55af
L_55B0:
	ld a,(hl)			;55b0
	cp 03eh		;55b1
	ret nc			;55b3
	cp 03ch		;55b4
	ld hl,0e0b0h		;55b6
	jr nc,L_55E0		;55b9
	cp 004h		;55bb
	jr c,L_55E0		;55bd
	add a,016h		;55bf
	ld d,a			;55c1
	ld a,047h		;55c2
	ld b,002h		;55c4
	call L_55D5		;55c6
	ld b,003h		;55c9
	bit 7,(ix+000h)		;55cb
	jr z,L_55D5		;55cf
	ld (hl),0c3h		;55d1
	jr L_55D8		;55d3
L_55D5:
	ld (hl),a			;55d5
	add a,010h		;55d6
L_55D8:
	inc hl			;55d8
	ld (hl),d			;55d9
	inc hl			;55da
	inc hl			;55db
	inc hl			;55dc
	djnz L_55D5		;55dd
	ret			;55df
L_55E0:
	ex de,hl			;55e0
	ld b,005h		;55e1
L_55E3:
	call L_5601		;55e3
	djnz L_55E3		;55e6
	ret			;55e8
L_55E9:
	ld a,(hl)			;55e9
	push af			;55ea
	call L_5625		;55eb
	bit 7,(ix+000h)		;55ee
	pop bc			;55f2
	jr z,L_5601		;55f3
	ld a,(de)			;55f5
	cpl			;55f6
	or b			;55f7
	jp p,L_5601		;55f8
	ld a,b			;55fb
	jr L_561D		;55fc
L_55FE:
	call L_5601		;55fe
L_5601:
	ld a,0c3h		;5601
	ld (de),a			;5603
	inc de			;5604
	inc de			;5605
	inc de			;5606
	inc de			;5607
	ret			;5608
L_5609:
	ld a,(0e052h)		;5609
	cp 003h		;560c
	ret nz			;560e
	ld a,(hl)			;560f
	and 004h		;5610
	add a,094h		;5612
	ld b,a			;5614
	ld a,(hl)			;5615
	ld c,006h		;5616
	ld hl,0a303h		;5618
	jr L_562B		;561b
L_561D:
	ld bc,0780eh		;561d
	ld hl,0540eh		;5620
	jr L_562B		;5623
L_5625:
	ld bc,0a816h		;5625
	ld hl,0400eh		;5628
L_562B:
	ex de,hl			;562b
	add a,c			;562c
	inc c			;562d
	inc c			;562e
	inc c			;562f
	cp c			;5630
	jr nc,L_5635		;5631
	ld d,0c3h		;5633
L_5635:
	call L_563A		;5635
	ex de,hl			;5638
	ret			;5639
L_563A:
	ld (hl),d			;563a
	inc hl			;563b
	ld (hl),a			;563c
	inc hl			;563d
	ld (hl),b			;563e
	inc hl			;563f
	ld (hl),e			;5640
	inc hl			;5641
	ret			;5642
L_5643:
	ld hl,(0e055h)		;5643
	ld a,h			;5646
	or a			;5647
	jr nz,L_5677		;5648
	ld a,l			;564a
	add a,002h		;564b
	cp 004h		;564d
	jr c,L_566D		;564f
	ld a,l			;5651
	ld (0e14ch),a		;5652
L_5655:
	call L_57A8		;5655
	ld hl,0740fh		;5658
	ld bc,00308h		;565b
	jr z,L_5666		;565e
	ld hl,0735ah		;5660
	ld bc,00307h		;5663
L_5666:
	ld de,(0e14ch)		;5666
	jp L_53BE		;566a
L_566D:
	ld bc,00803h		;566d
	ld de,(0e14ch)		;5670
	call L_6A6D		;5674
L_5677:
	ld a,0ffh		;5677
	ld (0e14ch),a		;5679
	ret			;567c
L_567D:
	call L_534D		;567d
	ld c,a			;5680
	ld b,000h		;5681
	jp p,L_5687		;5683
	dec b			;5686
L_5687:
	ld hl,(0e055h)		;5687
	add hl,bc			;568a
	ld (0e055h),hl		;568b
	ld a,h			;568e
	add a,a			;568f
	add a,a			;5690
	add a,014h		;5691
	cp 034h		;5693
	ld b,a			;5695
	jr nz,L_569A		;5696
	ld b,0f8h		;5698
L_569A:
	ld a,l			;569a
	ld de,0b60bh		;569b
	ld hl,0e0f0h		;569e
	call L_563A		;56a1
	add a,010h		;56a4
	jr nc,L_56AA		;56a6
	ld d,0c3h		;56a8
L_56AA:
	bit 7,b		;56aa
	jr nz,L_56B0		;56ac
	ld b,010h		;56ae
L_56B0:
	jp L_563A		;56b0
L_56B3:
	call L_5406		;56b3
	ret z			;56b6
	bit 3,a		;56b7
	ld hl,0e14ah		;56b9
	ld a,(0e1d4h)		;56bc
	ld b,a			;56bf
	ld a,(0e1cah)		;56c0
	jr z,L_56CA		;56c3
	dec (hl)			;56c5
	dec a			;56c6
	dec b			;56c7
	jr L_56CD		;56c8
L_56CA:
	inc (hl)			;56ca
	inc a			;56cb
	inc b			;56cc
L_56CD:
	ld (0e1cah),a		;56cd
	ld a,b			;56d0
	ld (0e1d4h),a		;56d1
L_56D4:
	ld a,(hl)			;56d4
	and 006h		;56d5
	ld hl,06acbh		;56d7
	call suma_a_a_hl		;56da
	ld e,(hl)			;56dd
	inc hl			;56de
	ld d,(hl)			;56df
	ex de,hl			;56e0
	ld de,(0e14ah)		;56e1
	call L_53F3		;56e5
	call L_5711		;56e8
	ld a,(0e14ah)		;56eb
	sub 02eh		;56ee
	res 0,a		;56f0
	ld (0e0e1h),a		;56f2
	ld (0e0e9h),a		;56f5
	add a,01eh		;56f8
	ld (0e0e5h),a		;56fa
	ld (0e0edh),a		;56fd
	add a,009h		;5700
	ld (0e121h),a		;5702
	ld (0e129h),a		;5705
	sub 02eh		;5708
	ld (0e125h),a		;570a
	ld (0e12dh),a		;570d
	ret			;5710
L_5711:
	di			;5711
	set 6,d		;5712
	ld a,015h		;5714
	ld b,020h		;5716
	call L_578B		;5718
	inc hl			;571b
	inc hl			;571c
	ld c,006h		;571d
	ld a,020h		;571f
L_5721:
	push hl			;5721
	ex af,af'			;5722
	ld a,006h		;5723
	call suma_a_a_hl		;5725
	ex af,af'			;5728
	ld b,005h		;5729
	call L_578B		;572b
	pop hl			;572e
	ld b,006h		;572f
L_5731:
	ld a,(hl)			;5731
	inc hl			;5732
	exx			;5733
	out (c),a		;5734
	exx			;5736
	inc de			;5737
	ld a,e			;5738
	and 01fh		;5739
	call z,L_57B0		;573b
	djnz L_5731		;573e
	ld b,006h		;5740
	call L_578E		;5742
	inc hl			;5745
	inc hl			;5746
	ld a,02fh		;5747
	dec c			;5749
	jr nz,L_5721		;574a
	ld a,0eah		;574c
	dec h			;574e
	call suma_a_a_hl		;574f
	ld a,0c0h		;5752
	dec d			;5754
	ld b,00fh		;5755
	call L_578B		;5757
	ld a,008h		;575a
	call suma_a_a_hl		;575c
	ld a,031h		;575f
	ld b,00fh		;5761
	call L_578B		;5763
	dec hl			;5766
	ld a,(hl)			;5767
	sub 0b8h		;5768
	and 00ch		;576a
	add a,a			;576c
	add a,080h		;576d
	ld l,a			;576f
	ld h,0e2h		;5770
	ld de,02288h		;5772
	ld c,008h		;5775
	call L_57A8		;5777
	jr nz,L_5788		;577a
	push hl			;577c
	ld d,02ah		;577d
	call L_4577		;577f
	pop hl			;5782
	ld de,03288h		;5783
	ld c,008h		;5786
L_5788:
	jp L_4577		;5788
L_578B:
	call L_57B3		;578b
L_578E:
	ld a,(hl)			;578e
	or a			;578f
	jr nz,L_5799		;5790
	inc hl			;5792
	ld a,(hl)			;5793
	call suma_a_a_hl		;5794
	dec h			;5797
	ld a,(hl)			;5798
L_5799:
	inc hl			;5799
	exx			;579a
	out (c),a		;579b
	exx			;579d
	inc de			;579e
	ld a,e			;579f
	and 01fh		;57a0
	call z,L_57B0		;57a2
	djnz L_578E		;57a5
	ret			;57a7
L_57A8:
	ld a,(0e052h)		;57a8
	or a			;57ab
	ret z			;57ac
	cp 002h		;57ad
	ret			;57af
L_57B0:
	ld a,0e0h		;57b0
	dec d			;57b2
L_57B3:
	push hl			;57b3
	ld l,a			;57b4
	and 01fh		;57b5
	ld h,a			;57b7
	xor l			;57b8
	add a,e			;57b9
	jr nc,L_57BD		;57ba
	inc d			;57bc
L_57BD:
	and 0e0h		;57bd
	ld l,a			;57bf
	ld a,e			;57c0
	add a,h			;57c1
	and 01fh		;57c2
	or l			;57c4
	ld e,a			;57c5
	pop hl			;57c6
	call prepara_escritura_vram		;57c7
	ret			;57ca
L_57CB:
	ld ix,0e180h		;57cb
	ld de,0e0fch		;57cf
	ld hl,0e170h		;57d2
	ld b,006h		;57d5
L_57D7:
	push bc			;57d7
	push hl			;57d8
	ld a,(ix+000h)		;57d9
	or a			;57dc
	push af			;57dd
	call nz,L_5855		;57de
	pop af			;57e1
	call z,L_543B		;57e2
	pop hl			;57e5
	pop bc			;57e6
	inc hl			;57e7
	inc hl			;57e8
	inc ix		;57e9
	inc ix		;57eb
	djnz L_57D7		;57ed
	ld a,(0e052h)		;57ef
	cp 003h		;57f2
	ret nz			;57f4
	ld a,(ix+000h)		;57f5
	or a			;57f8
	ret z			;57f9
	ld de,0e0f8h		;57fa
	cp 07eh		;57fd
	jr z,L_5808		;57ff
	ld a,(0e139h)		;5801
	and 00ch		;5804
	jr nz,L_5837		;5806
L_5808:
	ld a,038h		;5808
	ld de,0a038h		;580a
	cp (hl)			;580d
	push de			;580e
	call nz,L_583E		;580f
	pop de			;5812
	ld bc,00303h		;5813
	ld hl,0724ah		;5816
	call L_53C8		;5819
	ld hl,0e0f8h		;581c
	ld (hl),0a3h		;581f
	inc hl			;5821
	ld (hl),03ch		;5822
	inc hl			;5824
	call L_5406		;5825
	jr z,L_5830		;5828
	ld a,(0e003h)		;582a
	rra			;582d
	and 007h		;582e
L_5830:
	add a,094h		;5830
	ld (hl),a			;5832
	inc hl			;5833
	ld (hl),003h		;5834
	ret			;5836
L_5837:
	ld a,(hl)			;5837
	sub 003h		;5838
	jr nc,L_5870		;583a
	jr L_589F		;583c
L_583E:
	ld (0e17ch),de		;583e
	ld e,000h		;5842
	ld bc,00e03h		;5844
	call L_6A6D		;5847
	call L_58B8		;584a
	ret nz			;584d
	call L_5472		;584e
	ret nc			;5851
	jp L_6128		;5852
L_5855:
	ld a,(0e052h)		;5855
	cp 002h		;5858
	jr z,L_58C6		;585a
	call L_534D		;585c
	ld b,a			;585f
	ld a,(0e003h)		;5860
	ld c,a			;5863
	rra			;5864
	sbc a,a			;5865
	add a,b			;5866
	add a,(hl)			;5867
	cp 002h		;5868
	jr c,L_589E		;586a
	inc hl			;586c
	ld (hl),0a0h		;586d
	dec hl			;586f
L_5870:
	ld (hl),a			;5870
	ld a,(0e130h)		;5871
	cp 085h		;5874
	jr nc,L_588C		;5876
	push hl			;5878
	call L_5609		;5879
	pop hl			;587c
	push de			;587d
	ld e,(hl)			;587e
	inc hl			;587f
	ld d,(hl)			;5880
	ld hl,07242h		;5881
	ld bc,00305h		;5884
	call L_53BE		;5887
	pop de			;588a
	ret			;588b
L_588C:
	call L_5601		;588c
	push de			;588f
	ld e,(hl)			;5890
	inc hl			;5891
	ld d,(hl)			;5892
	ld hl,072d2h		;5893
	ld bc,00305h		;5896
L_5899:
	call L_53C8		;5899
	pop de			;589c
	ret			;589d
L_589E:
	ld (hl),a			;589e
L_589F:
	push de			;589f
	ld bc,00503h		;58a0
L_58A3:
	ld e,(hl)			;58a3
	inc hl			;58a4
	ld d,(hl)			;58a5
	call L_6A6D		;58a6
	pop de			;58a9
	call L_58B8		;58aa
	cp 00fh		;58ad
	jr z,L_58B5		;58af
	ld (ix+000h),000h		;58b1
L_58B5:
	jp L_5601		;58b5
L_58B8:
	ld hl,0e180h		;58b8
	ld b,005h		;58bb
	ld a,(hl)			;58bd
L_58BE:
	inc hl			;58be
	inc hl			;58bf
	add a,(hl)			;58c0
	djnz L_58BE		;58c1
	and 00fh		;58c3
	ret			;58c5
L_58C6:
	push de			;58c6
	push ix		;58c7
	pop bc			;58c9
	ld a,(0e1b0h)		;58ca
	cp 0feh		;58cd
	jr z,L_58DA		;58cf
	ld d,a			;58d1
	ld a,(hl)			;58d2
	sub d			;58d3
	add a,020h		;58d4
	cp 040h		;58d6
	jr c,L_58E3		;58d8
L_58DA:
	call L_5406		;58da
	jr z,L_590D		;58dd
	bit 3,a		;58df
	jr nz,L_58EA		;58e1
L_58E3:
	ld a,(0e003h)		;58e3
	and 003h		;58e6
	jr nz,L_58EB		;58e8
L_58EA:
	dec (hl)			;58ea
L_58EB:
	ld e,(hl)			;58eb
	inc hl			;58ec
	ld d,050h		;58ed
	ld (hl),d			;58ef
	dec hl			;58f0
	ld a,(hl)			;58f1
	cp 002h		;58f2
	jr c,L_5906		;58f4
	and 00eh		;58f6
	add a,a			;58f8
	add a,a			;58f9
	ld hl,05a2fh		;58fa
	call suma_a_a_hl		;58fd
	ld bc,00204h		;5900
	jp L_5899		;5903
L_5906:
	ld (hl),001h		;5906
	ld bc,00302h		;5908
	jr L_58A3		;590b
L_590D:
	ld a,(0e003h)		;590d
	and 001h		;5910
	jr nz,L_58EB		;5912
	jr L_58EA		;5914
L_5916:
	dec (hl)			;5916
	ret			;5917
L_5918:
	ld hl,0e1bah		;5918
	ld a,(hl)			;591b
	or a			;591c
	jr nz,L_5916		;591d
	ld de,0e1b0h		;591f
	ld a,(de)			;5922
	cp 002h		;5923
	jr c,L_592B		;5925
	cp 0ffh		;5927
	jr c,L_5947		;5929
L_592B:
	ld (hl),080h		;592b
	xor a			;592d
	ld (0e1b4h),a		;592e
	ld (0e1b5h),a		;5931
	ld hl,059fah		;5934
	ld (0e1b6h),hl		;5937
	ld a,0feh		;593a
	ld (de),a			;593c
	inc de			;593d
	ld a,050h		;593e
	ld (de),a			;5940
	ld (0e217h),a		;5941
	jp L_59CE		;5944
L_5947:
	ex de,hl			;5947
	ld a,(0e1b4h)		;5948
	or a			;594b
	jr nz,L_59A4		;594c
	call L_5406		;594e
	jr z,L_5958		;5951
	bit 3,a		;5953
	jr z,L_599A		;5955
	dec (hl)			;5957
L_5958:
	dec (hl)			;5958
L_5959:
	ld a,(hl)			;5959
	inc hl			;595a
	inc hl			;595b
	bit 2,a		;595c
	jr z,L_5968		;595e
	bit 1,a		;5960
	jr nz,L_596C		;5962
	ld (hl),004h		;5964
	jr L_596E		;5966
L_5968:
	ld (hl),000h		;5968
	jr L_596E		;596a
L_596C:
	ld (hl),008h		;596c
L_596E:
	call L_59CE		;596e
	ld hl,0e1b0h		;5971
	ld de,0e170h		;5974
	ld b,006h		;5977
L_5979:
	inc de			;5979
	ld a,(de)			;597a
	dec de			;597b
	cp 002h		;597c
	jr c,L_598B		;597e
	ld a,(de)			;5980
	or a			;5981
	jr z,L_598B		;5982
	add a,018h		;5984
	sub (hl)			;5986
	cp 002h		;5987
	jr c,L_5990		;5989
L_598B:
	inc de			;598b
	inc de			;598c
	djnz L_5979		;598d
	ret			;598f
L_5990:
	inc hl			;5990
	inc hl			;5991
	ld (hl),00ch		;5992
	ld a,001h		;5994
	ld (0e1b4h),a		;5996
	ret			;5999
L_599A:
	ld a,(0e003h)		;599a
	and 001h		;599d
	jr nz,L_5959		;599f
	dec (hl)			;59a1
	jr L_5959		;59a2
L_59A4:
	ld a,(0e1b5h)		;59a4
	ld b,a			;59a7
	inc hl			;59a8
	ld de,(0e1b6h)		;59a9
	bit 0,b		;59ad
	ld a,(de)			;59af
	jr nz,L_59B4		;59b0
	neg		;59b2
L_59B4:
	add a,(hl)			;59b4
	ld (hl),a			;59b5
	dec hl			;59b6
	dec (hl)			;59b7
	dec (hl)			;59b8
	ex de,hl			;59b9
	bit 0,b		;59ba
	jr nz,L_59C1		;59bc
	inc hl			;59be
	jr L_59C2		;59bf
L_59C1:
	dec hl			;59c1
L_59C2:
	ld a,(hl)			;59c2
	inc a			;59c3
	jr nz,L_59EC		;59c4
	dec hl			;59c6
	inc a			;59c7
	ld (0e1b5h),a		;59c8
L_59CB:
	ld (0e1b6h),hl		;59cb
L_59CE:
	ld hl,0e1b0h		;59ce
	ld b,(hl)			;59d1
	inc hl			;59d2
	ld c,(hl)			;59d3
	ld a,0feh		;59d4
	cp b			;59d6
	jr nz,L_59DB		;59d7
	ld c,0c3h		;59d9
L_59DB:
	inc hl			;59db
	ld a,(hl)			;59dc
	inc hl			;59dd
	ld e,(hl)			;59de
	ld hl,0e0f8h		;59df
	add a,084h		;59e2
	ld (hl),c			;59e4
	inc hl			;59e5
	ld (hl),b			;59e6
	inc hl			;59e7
	ld (hl),a			;59e8
	inc hl			;59e9
	ld (hl),e			;59ea
	ret			;59eb
L_59EC:
	inc a			;59ec
	jr nz,L_59CB		;59ed
	xor a			;59ef
	ld (0e1b4h),a		;59f0
	ld (0e1b5h),a		;59f3
	inc hl			;59f6
	jr L_59CB		;59f7

; ----------------------------------------------------------------------
; DATOS rampa_59FA: FE, luego 4 4 4 3 3 2 2 2 2 1 1 0 0, y FF de cierre
;   0x59f9..0x5a08  (15 bytes)
DATA_rampa_59FA:
	defb 0feh,004h,004h,004h,003h,003h,002h,002h,002h,002h,001h,001h,000h,000h,0ffh	; 59f9  ...............

; ======================================================================
; CODIGO 0x5a08..0x5a2f  (39 bytes)
; ======================================================================


L_5A08:
	ld b,006h		;5a08
	ld de,0e170h		;5a0a
	ld hl,(0e130h)		;5a0d
L_5A10:
	ld a,(0e134h)		;5a10
	and a			;5a13
	call z,L_5A1E		;5a14
	ret c			;5a17
	inc de			;5a18
	djnz L_5A10		;5a19
	ld de,0e1b0h		;5a1b
L_5A1E:
	ld a,(de)			;5a1e
	inc de			;5a1f
	sub h			;5a20
	add a,00eh		;5a21
	cp 01ch		;5a23
	ret nc			;5a25
	ld a,(de)			;5a26
	sub l			;5a27
	add a,010h		;5a28
	cp 028h		;5a2a
	ret nc			;5a2c
	scf			;5a2d
	ret			;5a2e

; ----------------------------------------------------------------------
; DATOS piezas_de_tres_tiles: 16 grupos de cuatro: tres indices de patron y un
;   cero
;   0x5a2f..0x5a6f  (64 bytes)
DATA_piezas_de_tres_tiles:
	defb 0b0h,0b1h,0b2h,000h	; 5a2f
	defb 0b3h,0b4h,0b5h,000h	; 5a33
	defb 0aah,0abh,0ach,000h	; 5a37
	defb 0adh,0aeh,0afh,000h	; 5a3b
	defb 0bah,0bbh,0bch,000h	; 5a3f
	defb 0bdh,0beh,0bfh,000h	; 5a43
	defb 000h,0b6h,0b7h,000h	; 5a47
	defb 000h,0b8h,0b9h,000h	; 5a4b
	defb 0b0h,0b1h,0b2h,000h	; 5a4f
	defb 0b3h,0b4h,0b5h,000h	; 5a53
	defb 0aah,0abh,0ach,000h	; 5a57
	defb 0adh,0aeh,0afh,000h	; 5a5b
	defb 0a4h,0a5h,0a6h,000h	; 5a5f
	defb 0a7h,0a8h,0a9h,000h	; 5a63
	defb 000h,0a0h,0a1h,000h	; 5a67
	defb 000h,0a2h,0a3h,000h	; 5a6b

; ----------------------------------------------------------------------
; DATOS pares_5A6F: otros 32 pares del mismo formato; los lee 0x54A7
;   0x5a6f..0x5aaf  (64 bytes)
DATA_pares_5A6F:
	defb 00fh,080h	; 5a6f
	defb 00fh,0b8h	; 5a71
	defb 08fh,0a0h	; 5a73
	defb 00fh,0a0h	; 5a75
	defb 00fh,080h	; 5a77
	defb 00fh,080h	; 5a79
	defb 00fh,0c0h	; 5a7b
	defb 08fh,0a0h	; 5a7d
	defb 08fh,0a0h	; 5a7f
	defb 00fh,0c0h	; 5a81
	defb 00fh,0a0h	; 5a83
	defb 00fh,0a0h	; 5a85
	defb 08fh,0a0h	; 5a87
	defb 00fh,0c0h	; 5a89
	defb 08fh,0a0h	; 5a8b
	defb 00fh,0a0h	; 5a8d
	defb 00fh,0a0h	; 5a8f
	defb 08fh,0c0h	; 5a91
	defb 00fh,0c0h	; 5a93
	defb 00fh,0c0h	; 5a95
	defb 00fh,0a0h	; 5a97
	defb 00fh,0c0h	; 5a99
	defb 00fh,0a0h	; 5a9b
	defb 00fh,0b0h	; 5a9d
	defb 08fh,060h	; 5a9f
	defb 00fh,0c0h	; 5aa1
	defb 00fh,0b0h	; 5aa3
	defb 08fh,080h	; 5aa5
	defb 00fh,0d0h	; 5aa7
	defb 00fh,0c0h	; 5aa9
	defb 00fh,090h	; 5aab
	defb 00fh,0c0h	; 5aad

; ======================================================================
; CODIGO 0x5aaf..0x5c14  (357 bytes)
; ======================================================================


L_5AAF:
	ld a,(0e056h)		;5aaf
	or a			;5ab2
	ret z			;5ab3
	ld hl,0e26eh		;5ab4
	ld a,(hl)			;5ab7
	sub c			;5ab8
	ld (hl),a			;5ab9
	ret nc			;5aba
	ld hl,0e25ch		;5abb
	ld b,004h		;5abe
L_5AC0:
	ld a,(hl)			;5ac0
	or a			;5ac1
	jr z,L_5ACB		;5ac2
	inc hl			;5ac4
	inc hl			;5ac5
	inc hl			;5ac6
	inc hl			;5ac7
	djnz L_5AC0		;5ac8
	ret			;5aca
L_5ACB:
	ld de,(0e26ch)		;5acb
	ld a,(de)			;5acf
	and 018h		;5ad0
	rra			;5ad2
	rra			;5ad3
	rra			;5ad4
	inc a			;5ad5
	ld b,a			;5ad6
	ld a,03ah		;5ad7
L_5AD9:
	add a,01eh		;5ad9
	djnz L_5AD9		;5adb
	ld (hl),a			;5add
	ld a,(de)			;5ade
	inc hl			;5adf
	ld (hl),a			;5ae0
	inc hl			;5ae1
	ld (hl),0d8h		;5ae2
	inc hl			;5ae4
	inc de			;5ae5
	ld a,(de)			;5ae6
	ld (hl),a			;5ae7
	inc de			;5ae8
	ld a,(de)			;5ae9
	ld (0e26eh),a		;5aea
	inc de			;5aed
	ld (0e26ch),de		;5aee
	ld hl,(0e26ch)		;5af2
	ld a,(hl)			;5af5
	inc a			;5af6
	jr nz,L_5AFC		;5af7
	ld hl,(0e25ah)		;5af9
L_5AFC:
	ld (0e26ch),hl		;5afc
	ret			;5aff
L_5B00:
	call L_5406		;5b00
	jr z,L_5B16		;5b03
	bit 2,a		;5b05
	ld a,(0e270h)		;5b07
	jr z,L_5B73		;5b0a
	dec a			;5b0c
	cp 020h		;5b0d
	jr nc,L_5B13		;5b0f
	ld a,020h		;5b11
L_5B13:
	ld (0e270h),a		;5b13
L_5B16:
	ld hl,0e270h		;5b16
	ld a,(hl)			;5b19
	inc hl			;5b1a
	add a,(hl)			;5b1b
	ld e,a			;5b1c
	ld d,000h		;5b1d
	and 03fh		;5b1f
	ld (hl),a			;5b21
	ex de,hl			;5b22
	add hl,hl			;5b23
	add hl,hl			;5b24
	ld c,h			;5b25
	ld hl,0e14ah		;5b26
	ld a,(hl)			;5b29
	sub c			;5b2a
	ld (hl),a			;5b2b
	push bc			;5b2c
	call L_56D4		;5b2d
	pop bc			;5b30
	ld a,(0e056h)		;5b31
	or a			;5b34
	jr nz,L_5B42		;5b35
	ld hl,0e14ch		;5b37
	ld a,(hl)			;5b3a
	sub c			;5b3b
	ld (hl),a			;5b3c
	push bc			;5b3d
	call L_5655		;5b3e
	pop bc			;5b41
L_5B42:
	push bc			;5b42
	ld b,000h		;5b43
	ld a,c			;5b45
	or a			;5b46
	jr z,L_5B4E		;5b47
	neg		;5b49
	ld c,a			;5b4b
	ld b,0ffh		;5b4c
L_5B4E:
	call L_5687		;5b4e
	pop bc			;5b51
	ld hl,0e25ch		;5b52
	ld b,004h		;5b55
L_5B57:
	push bc			;5b57
	push hl			;5b58
	ld a,(hl)			;5b59
	or a			;5b5a
	jr z,L_5B6A		;5b5b
	inc hl			;5b5d
	inc hl			;5b5e
	ld a,(hl)			;5b5f
	sub c			;5b60
	ld (hl),a			;5b61
	ld a,003h		;5b62
	cp (hl)			;5b64
	pop hl			;5b65
	push hl			;5b66
	call nc,L_5BF3		;5b67
L_5B6A:
	pop hl			;5b6a
	pop bc			;5b6b
	inc hl			;5b6c
	inc hl			;5b6d
	inc hl			;5b6e
	inc hl			;5b6f
	djnz L_5B57		;5b70
	ret			;5b72
L_5B73:
	inc a			;5b73
	cp 080h		;5b74
	jr c,L_5B7A		;5b76
	ld a,080h		;5b78
L_5B7A:
	jr L_5B13		;5b7a
L_5B7C:
	ld hl,0e25ch		;5b7c
	ld b,004h		;5b7f
L_5B81:
	push hl			;5b81
	push bc			;5b82
	ld a,(hl)			;5b83
	or a			;5b84
	jr z,L_5BB5		;5b85
	ex af,af'			;5b87
	inc hl			;5b88
	ld d,(hl)			;5b89
	inc hl			;5b8a
	ld e,(hl)			;5b8b
	ld c,e			;5b8c
	inc hl			;5b8d
	ld b,(hl)			;5b8e
	call L_53F3		;5b8f
	push de			;5b92
	push bc			;5b93
	ld a,c			;5b94
	and 006h		;5b95
	ld c,a			;5b97
	add a,a			;5b98
	add a,a			;5b99
	add a,c			;5b9a
	rra			;5b9b
	ld hl,07527h		;5b9c
	call suma_a_a_hl		;5b9f
	push hl			;5ba2
	call L_5BBE		;5ba3
	ld a,c			;5ba6
	add a,00fh		;5ba7
	ex af,af'			;5ba9
	pop hl			;5baa
	pop bc			;5bab
	pop de			;5bac
	ld a,020h		;5bad
	call suma_a_a_de		;5baf
	call L_5BBE		;5bb2
L_5BB5:
	pop bc			;5bb5
	pop hl			;5bb6
	inc hl			;5bb7
	inc hl			;5bb8
	inc hl			;5bb9
	inc hl			;5bba
	djnz L_5B81		;5bbb
	ret			;5bbd
L_5BBE:
	ex af,af'			;5bbe
	ld c,a			;5bbf
L_5BC0:
	push bc			;5bc0
	ld b,002h		;5bc1
	call L_5BDB		;5bc3
	pop bc			;5bc6
	dec b			;5bc7
	jr z,L_5BE5		;5bc8
	dec b			;5bca
L_5BCB:
	ld a,(hl)			;5bcb
	add a,c			;5bcc
	call escribe_en_vram		;5bcd
	inc de			;5bd0
	djnz L_5BCB		;5bd1
	inc hl			;5bd3
	ld a,(hl)			;5bd4
	dec a			;5bd5
	jr z,L_5BD9		;5bd6
	dec de			;5bd8
L_5BD9:
	ld b,002h		;5bd9
L_5BDB:
	ld a,(hl)			;5bdb
	add a,c			;5bdc
	call escribe_en_vram		;5bdd
	inc hl			;5be0
	inc de			;5be1
	djnz L_5BDB		;5be2
	ret			;5be4
L_5BE5:
	inc hl			;5be5
	inc hl			;5be6
	ld a,(hl)			;5be7
	or a			;5be8
	jr z,L_5BEC		;5be9
	dec de			;5beb
L_5BEC:
	ld a,(hl)			;5bec
	add a,c			;5bed
	call escribe_en_vram		;5bee
	inc hl			;5bf1
	ret			;5bf2
L_5BF3:
	ld c,(hl)			;5bf3
	ld (hl),000h		;5bf4
	inc hl			;5bf6
	ld d,(hl)			;5bf7
	inc hl			;5bf8
	ld e,(hl)			;5bf9
	inc hl			;5bfa
	ld b,(hl)			;5bfb
	call L_53F3		;5bfc
	ld hl,05c14h		;5bff
	push de			;5c02
	push bc			;5c03
	call L_5BC0		;5c04
	pop bc			;5c07
	pop de			;5c08
	ld a,020h		;5c09
	call suma_a_a_de		;5c0b
	ld a,c			;5c0e
	add a,00fh		;5c0f
	ex af,af'			;5c11
	jr L_5BBE		;5c12

; ----------------------------------------------------------------------
; DATOS diez_ceros: los recorre 0x5BFF
;   0x5c14..0x5c1e  (10 bytes)
DATA_diez_ceros:
	defb 000h,000h,000h,000h,000h,000h,000h,000h,000h,000h	; 5c14  ..........

; ======================================================================
; CODIGO 0x5c1e..0x5c8e  (112 bytes)
; ======================================================================


L_5C1E:
	ld a,(0e134h)		;5c1e
	cp 005h		;5c21
	ret nc			;5c23
	ld hl,0e25ch		;5c24
	ld b,004h		;5c27
L_5C29:
	push hl			;5c29
	push bc			;5c2a
	ld a,(hl)			;5c2b
	or a			;5c2c
	jr z,L_5C85		;5c2d
	ld de,(0e130h)		;5c2f
	inc hl			;5c33
	inc hl			;5c34
	ld a,d			;5c35
	sub (hl)			;5c36
	add a,010h		;5c37
	ld c,a			;5c39
	inc hl			;5c3a
	ld a,(hl)			;5c3b
	add a,a			;5c3c
	add a,a			;5c3d
	add a,a			;5c3e
	add a,008h		;5c3f
	cp c			;5c41
	jr c,L_5C85		;5c42
	dec hl			;5c44
	dec hl			;5c45
	ld a,e			;5c46
	sub (hl)			;5c47
	add a,01ch		;5c48
	cp 024h		;5c4a
	jr nc,L_5C85		;5c4c
	cp 004h		;5c4e
	jr c,L_5C59		;5c50
	pop bc			;5c52
	pop hl			;5c53
	scf			;5c54
	call L_5018		;5c55
	ret			;5c58
L_5C59:
	ld a,c			;5c59
	cp 006h		;5c5a
	jr c,L_5C85		;5c5c
	pop bc			;5c5e
	pop hl			;5c5f
	ld hl,051e9h		;5c60
	call L_5161		;5c63
	ld a,001h		;5c66
	ld (0e134h),a		;5c68
	ld a,(0e272h)		;5c6b
	inc a			;5c6e
	cp 004h		;5c6f
	jr c,L_5C75		;5c71
	ld a,004h		;5c73
L_5C75:
	ld (0e272h),a		;5c75
	ld e,000h		;5c78
	add a,a			;5c7a
	ld d,a			;5c7b
	call suma_puntos		;5c7c
	ld a,001h		;5c7f
	call L_7BA2		;5c81
	ret			;5c84
L_5C85:
	pop bc			;5c85
	pop hl			;5c86
	inc hl			;5c87
	inc hl			;5c88
	inc hl			;5c89
	inc hl			;5c8a
	djnz L_5C29		;5c8b
	ret			;5c8d

; ----------------------------------------------------------------------
; DATOS trios_5C8E: 28 grupos de tres, y 0xFF de cierre
;   0x5c8e..0x5ce3  (85 bytes)
DATA_trios_5C8E:
	defb 088h,003h,020h	; 5c8e
	defb 088h,004h,080h	; 5c91
	defb 070h,003h,040h	; 5c94
	defb 088h,004h,080h	; 5c97
	defb 088h,004h,040h	; 5c9a
	defb 078h,004h,080h	; 5c9d
	defb 088h,003h,030h	; 5ca0
	defb 078h,004h,080h	; 5ca3
	defb 088h,003h,040h	; 5ca6
	defb 080h,004h,070h	; 5ca9
	defb 080h,001h,070h	; 5cac
	defb 078h,003h,030h	; 5caf
	defb 088h,004h,070h	; 5cb2
	defb 078h,001h,030h	; 5cb5
	defb 088h,003h,020h	; 5cb8
	defb 078h,004h,070h	; 5cbb
	defb 088h,001h,030h	; 5cbe
	defb 080h,003h,070h	; 5cc1
	defb 088h,004h,030h	; 5cc4
	defb 080h,001h,070h	; 5cc7
	defb 088h,003h,020h	; 5cca
	defb 078h,001h,030h	; 5ccd
	defb 080h,003h,070h	; 5cd0
	defb 088h,004h,030h	; 5cd3
	defb 078h,001h,050h	; 5cd6
	defb 080h,003h,030h	; 5cd9
	defb 088h,004h,070h	; 5cdc
	defb 078h,003h,050h	; 5cdf
	defb 0ffh	; 5ce2

; ======================================================================
; CODIGO 0x5ce3..0x5f58  (629 bytes)
; ======================================================================


L_5CE3:
	ld hl,0e1f2h		;5ce3
	ld (hl),000h		;5ce6
	ld a,(0e1e0h)		;5ce8
	and 00fh		;5ceb
	inc a			;5ced
	ld b,a			;5cee
	ld a,(0e134h)		;5cef
	cp 002h		;5cf2
	jr nz,L_5D0B		;5cf4
	ld a,(0e009h)		;5cf6
	rra			;5cf9
	rra			;5cfa
	and 003h		;5cfb
	jr z,L_5D0B		;5cfd
	ld hl,0e1c1h		;5cff
	and 001h		;5d02
	xor (hl)			;5d04
	jr nz,L_5D0A		;5d05
	inc b			;5d07
	jr L_5D0B		;5d08
L_5D0A:
	dec b			;5d0a
L_5D0B:
	ld a,b			;5d0b
	ld hl,05f61h		;5d0c
	call suma_a_a_hl		;5d0f
	ld b,(hl)			;5d12
	ld hl,0e1eeh		;5d13
	inc (hl)			;5d16
	ld a,(hl)			;5d17
	cp b			;5d18
	ret c			;5d19
	xor a			;5d1a
	ld (hl),a			;5d1b
	dec a			;5d1c
	ld (0e1f2h),a		;5d1d
	ld hl,0e1c0h		;5d20
	ld a,(hl)			;5d23
	ld b,a			;5d24
	add a,001h		;5d25
	daa			;5d27
	ld (hl),a			;5d28
	bit 4,a		;5d29
	ld a,001h		;5d2b
	jr nz,L_5D30		;5d2d
	xor a			;5d2f
L_5D30:
	ld (0e1c1h),a		;5d30
	ld a,(0e1cah)		;5d33
	ld c,a			;5d36
	ld de,05f7bh		;5d37
	ld hl,0521dh		;5d3a
	ld a,(0e1e0h)		;5d3d
	bit 6,a		;5d40
	jr z,L_5D4E		;5d42
	ld a,(0e1cbh)		;5d44
	ld c,a			;5d47
	ld a,(0e1e2h)		;5d48
	or a			;5d4b
	jr z,L_5D72		;5d4c
L_5D4E:
	bit 1,a		;5d4e
	jr z,L_5D58		;5d50
	ld de,05f85h		;5d52
	ld hl,05227h		;5d55
L_5D58:
	ld a,b			;5d58
	push af			;5d59
	and 00fh		;5d5a
	push af			;5d5c
	call suma_a_a_hl		;5d5d
	pop af			;5d60
	call suma_a_a_de		;5d61
	ld b,(hl)			;5d64
	ld a,(de)			;5d65
	ld hl,0e1d6h		;5d66
	ld (hl),b			;5d69
	pop de			;5d6a
	bit 4,d		;5d6b
	jr z,L_5D71		;5d6d
	neg		;5d6f
L_5D71:
	add a,c			;5d71
L_5D72:
	ld (0e1d7h),a		;5d72
	ret			;5d75
L_5D76:
	ld a,(0e134h)		;5d76
	cp 004h		;5d79
	ld a,(0e1f2h)		;5d7b
	jr z,L_5DEA		;5d7e
	or a			;5d80
	ret z			;5d81
	ld a,(0e134h)		;5d82
	cp 003h		;5d85
	jr z,L_5DD7		;5d87
	ld hl,05f67h		;5d89
	ld de,05f7bh		;5d8c
	ld a,(0e1e0h)		;5d8f
	bit 1,a		;5d92
	jr z,L_5D9C		;5d94
	ld hl,05f71h		;5d96
	ld de,05f85h		;5d99
L_5D9C:
	ld a,(0e1c0h)		;5d9c
	ld b,a			;5d9f
	and 00fh		;5da0
	push af			;5da2
	call suma_a_a_hl		;5da3
	pop af			;5da6
	call suma_a_a_de		;5da7
	ld a,(hl)			;5daa
	bit 4,b		;5dab
	jr nz,L_5DB1		;5dad
	neg		;5daf
L_5DB1:
	push af			;5db1
	ld a,(de)			;5db2
	bit 4,b		;5db3
	jr z,L_5DB9		;5db5
	neg		;5db7
L_5DB9:
	add a,03dh		;5db9
	ld (0e1cah),a		;5dbb
	pop af			;5dbe
L_5DBF:
	push af			;5dbf
	ld hl,0e14ah		;5dc0
	add a,(hl)			;5dc3
	ld (hl),a			;5dc4
	call L_56D4		;5dc5
	pop af			;5dc8
	ld c,a			;5dc9
	bit 7,a		;5dca
	ld b,000h		;5dcc
	jr z,L_5DD2		;5dce
	ld b,0ffh		;5dd0
L_5DD2:
	call L_5687		;5dd2
	jr L_5DF7		;5dd5
L_5DD7:
	ld a,(0e138h)		;5dd7
	push af			;5dda
	push af			;5ddb
	ld hl,0e1d4h		;5ddc
	add a,(hl)			;5ddf
	ld (hl),a			;5de0
	pop af			;5de1
	ld hl,0e1cah		;5de2
	add a,(hl)			;5de5
	ld (hl),a			;5de6
	pop af			;5de7
	jr L_5DBF		;5de8
L_5DEA:
	push af			;5dea
	call L_56B3		;5deb
	call L_5643		;5dee
	call L_567D		;5df1
	pop af			;5df4
	or a			;5df5
	ret z			;5df6
L_5DF7:
	ld de,03880h		;5df7
	ld bc,00100h		;5dfa
	xor a			;5dfd
	call rellena_vram		;5dfe
	ld a,(0e056h)		;5e01
	or a			;5e04
	jr nz,L_5E10		;5e05
	ld a,(0e055h)		;5e07
	ld (0e14ch),a		;5e0a
	call L_5655		;5e0d
L_5E10:
	ld hl,0e1c0h		;5e10
	ld a,(0e1e0h)		;5e13
	ld bc,076ech		;5e16
	bit 1,a		;5e19
	jr z,L_5E20		;5e1b
	ld bc,07806h		;5e1d
L_5E20:
	ld de,03889h		;5e20
	bit 7,a		;5e23
	jr z,L_5E41		;5e25
	ld a,(0e1cah)		;5e27
	cp 008h		;5e2a
	jr c,L_5E44		;5e2c
	ld e,a			;5e2e
	ld d,020h		;5e2f
	call L_53F3		;5e31
	ld a,(0e1e0h)		;5e34
	ld bc,07876h		;5e37
	bit 1,a		;5e3a
	jr z,L_5E41		;5e3c
	ld bc,0797eh		;5e3e
L_5E41:
	call L_5E74		;5e41
L_5E44:
	ld a,(0e1e2h)		;5e44
	or a			;5e47
	ret z			;5e48
	ld a,(0e1e1h)		;5e49
	ld b,a			;5e4c
	ld a,(0e1cah)		;5e4d
	add a,b			;5e50
	ret c			;5e51
	ld (0e1cbh),a		;5e52
	cp 008h		;5e55
	ret c			;5e57
	ld hl,0e14ch		;5e58
	ld e,(hl)			;5e5b
	cp e			;5e5c
	ret nc			;5e5d
	ld e,a			;5e5e
	ld d,020h		;5e5f
	call L_53F3		;5e61
	ld a,(0e1e2h)		;5e64
	ld bc,07876h		;5e67
	bit 1,a		;5e6a
	jr z,L_5E71		;5e6c
	ld bc,0797eh		;5e6e
L_5E71:
	ld hl,0e1c9h		;5e71
L_5E74:
	push bc			;5e74
	ld a,(hl)			;5e75
	and 01fh		;5e76
	cp 010h		;5e78
	jr c,L_5E81		;5e7a
	cpl			;5e7c
	sub 005h		;5e7d
	and 01fh		;5e7f
L_5E81:
	ld c,a			;5e81
	pop hl			;5e82
	rlca			;5e83
	call suma_a_a_hl		;5e84
	push de			;5e87
	ld e,(hl)			;5e88
	inc hl			;5e89
	ld d,(hl)			;5e8a
	ex de,hl			;5e8b
	pop de			;5e8c
L_5E8D:
	push de			;5e8d
L_5E8E:
	ld a,(hl)			;5e8e
	inc hl			;5e8f
	ld b,a			;5e90
	inc b			;5e91
	jr z,L_5EBA		;5e92
	inc b			;5e94
	jr nz,L_5E9F		;5e95
L_5E97:
	ld a,020h		;5e97
	pop de			;5e99
	call suma_a_a_de		;5e9a
	jr L_5E8D		;5e9d
L_5E9F:
	call escribe_en_vram		;5e9f
	ld a,c			;5ea2
	cp 006h		;5ea3
	jr c,L_5EAA		;5ea5
	dec de			;5ea7
	jr L_5EAB		;5ea8
L_5EAA:
	inc de			;5eaa
L_5EAB:
	ld a,e			;5eab
	and 01fh		;5eac
	jr nz,L_5E8E		;5eae
L_5EB0:
	ld a,(hl)			;5eb0
	inc hl			;5eb1
	inc a			;5eb2
	jr z,L_5EBA		;5eb3
	inc a			;5eb5
	jr z,L_5E97		;5eb6
	jr L_5EB0		;5eb8
L_5EBA:
	pop de			;5eba
	ret			;5ebb
L_5EBC:
	ld a,(0e1e2h)		;5ebc
	and 00fh		;5ebf
	inc a			;5ec1
	ld hl,05f61h		;5ec2
	call suma_a_a_hl		;5ec5
	ld b,(hl)			;5ec8
	ld hl,0e1c8h		;5ec9
	inc (hl)			;5ecc
	ld a,(hl)			;5ecd
	cp b			;5ece
	ret c			;5ecf
	xor a			;5ed0
	ld (hl),a			;5ed1
	inc hl			;5ed2
	ld a,(hl)			;5ed3
	add a,001h		;5ed4
	daa			;5ed6
	ld (hl),a			;5ed7
	jp L_5DF7		;5ed8
L_5EDB:
	ld a,(0e134h)		;5edb
	cp 002h		;5ede
	ret z			;5ee0
	ld hl,(0e055h)		;5ee1
	ld bc,0ff60h		;5ee4
	add hl,bc			;5ee7
	jr nc,L_5F0A		;5ee8
	ld hl,0e1cah		;5eea
	ld a,(hl)			;5eed
	add a,008h		;5eee
	cp 010h		;5ef0
	ret nc			;5ef2
	ld a,(0e1e1h)		;5ef3
	add a,(hl)			;5ef6
	ld (hl),a			;5ef7
	ld hl,(0e1e2h)		;5ef8
	ld (0e1e0h),hl		;5efb
	ld a,(0e1c9h)		;5efe
	ld (0e1c0h),a		;5f01
	ld bc,0e1e2h		;5f04
	jp L_5483		;5f07
L_5F0A:
	xor a			;5f0a
	ld (0e1e2h),a		;5f0b
	ret			;5f0e
L_5F0F:
	ld a,(0e134h)		;5f0f
	ld b,a			;5f12
	cp 002h		;5f13
	jr nz,L_5F4D		;5f15
	ld a,(0e1f2h)		;5f17
	or a			;5f1a
	ret z			;5f1b
	ld a,b			;5f1c
	cp 003h		;5f1d
	jr z,L_5F4D		;5f1f
	ld hl,05f58h		;5f21
	call descomprime		;5f24
	ld a,(0e1e1h)		;5f27
	rra			;5f2a
	ld b,a			;5f2b
	ld a,(0e1cah)		;5f2c
	add a,b			;5f2f
	sub 018h		;5f30
	ret c			;5f32
	ld (0e1d4h),a		;5f33
L_5F36:
	push af			;5f36
	and 006h		;5f37
	ld hl,0735ah		;5f39
	ld bc,00307h		;5f3c
	call suma_a_a_hl		;5f3f
	ld e,(hl)			;5f42
	inc hl			;5f43
	ld d,(hl)			;5f44
	ex de,hl			;5f45
	pop af			;5f46
	ld e,a			;5f47
	ld d,0a0h		;5f48
	jp L_53C8		;5f4a
L_5F4D:
	ld hl,05f58h		;5f4d
	call descomprime		;5f50
	ld a,(0e1d4h)		;5f53
	jr L_5F36		;5f56

; ----------------------------------------------------------------------
; DATOS bloque_5F58: 9 bytes -> 96 en la tabla de nombres (0x3A80). Lo cargan
;   0x5F21 y 0x5F4D
;   0x5f58..0x5f61  (9 bytes)
DATA_bloque_5F58:
	defb 080h,03ah,020h,000h,020h,003h,020h,000h,000h	; 5f58  .: . . ..

; ----------------------------------------------------------------------
; DATOS rampa_5F61: 6 valores: 14 12 10 8 6 4
;   0x5f61..0x5f67  (6 bytes)
DATA_rampa_5F61:
	defb 00eh,00ch,00ah,008h,006h,004h	; 5f61

; ----------------------------------------------------------------------
; DATOS curva_5F67: FE y nueve alturas simetricas
;   0x5f67..0x5f71  (10 bytes)
DATA_curva_5F67:
	defb 0feh,002h,005h,00ch,015h,017h,017h,015h,00ch,005h	; 5f67  ..........

; ----------------------------------------------------------------------
; DATOS curva_5F71: FF y nueve alturas simetricas
;   0x5f71..0x5f7b  (10 bytes)
DATA_curva_5F71:
	defb 0ffh,001h,004h,009h,010h,011h,011h,010h,009h,004h	; 5f71  ..........

; ----------------------------------------------------------------------
; DATOS velocidades_5F7B: diez valores con signo, de +63 a -61 pasando por 0
;   0x5f7b..0x5f85  (10 bytes)
DATA_velocidades_5F7B:
	defb 03fh,03dh,038h,02ch,017h,000h,0e9h,0d4h,0c8h,0c3h	; 5f7b  ?=8,......

; ----------------------------------------------------------------------
; DATOS velocidades_5F85: los mismos diez, mas suaves: de +47 a -46
;   0x5f85..0x5f8f  (10 bytes)
DATA_velocidades_5F85:
	defb 02fh,02eh,02ah,021h,011h,000h,0efh,0dfh,0d6h,0d2h	; 5f85  /.*!......

; ----------------------------------------------------------------------
; DATOS pares_5F8F: 32 pares (bandera, altura), el mismo formato que 0x54C5
;   0x5f8f..0x5fcf  (64 bytes)
DATA_pares_5F8F:
	defb 081h,0a0h	; 5f8f
	defb 082h,090h	; 5f91
	defb 081h,0a0h	; 5f93
	defb 083h,080h	; 5f95
	defb 080h,0c0h	; 5f97
	defb 081h,0a0h	; 5f99
	defb 083h,0b0h	; 5f9b
	defb 082h,098h	; 5f9d
	defb 080h,0c0h	; 5f9f
	defb 081h,0a0h	; 5fa1
	defb 081h,080h	; 5fa3
	defb 083h,0a0h	; 5fa5
	defb 080h,0c8h	; 5fa7
	defb 081h,0a0h	; 5fa9
	defb 082h,090h	; 5fab
	defb 081h,0a0h	; 5fad
	defb 081h,0a0h	; 5faf
	defb 082h,090h	; 5fb1
	defb 081h,0a0h	; 5fb3
	defb 083h,080h	; 5fb5
	defb 080h,0c0h	; 5fb7
	defb 081h,0a0h	; 5fb9
	defb 083h,0b0h	; 5fbb
	defb 082h,098h	; 5fbd
	defb 080h,0c0h	; 5fbf
	defb 081h,0a0h	; 5fc1
	defb 081h,080h	; 5fc3
	defb 083h,0a0h	; 5fc5
	defb 080h,0c8h	; 5fc7
	defb 081h,0a0h	; 5fc9
	defb 082h,090h	; 5fcb
	defb 081h,0a0h	; 5fcd

; ----------------------------------------------------------------------
; DATOS bloque_5FCF: 7 bytes -> 32 en VRAM (0x1FE0). Lo carga 0x5FDC
;   0x5fcf..0x5fd6  (7 bytes)
DATA_bloque_5FCF:
	defb 0e0h,05fh,010h,0ffh,010h,000h,000h	; 5fcf

; ======================================================================
; CODIGO 0x5fd6..0x5fef  (25 bytes)
; ======================================================================


L_5FD6:
	ld hl,061bah		;5fd6
	call descomprime		;5fd9
	ld hl,05fcfh		;5fdc
	call descomprime		;5fdf
	call L_6968		;5fe2
	ld hl,0699dh		;5fe5
	push hl			;5fe8
	ld a,(0e052h)		;5fe9
	call despacha_por_tabla		;5fec

; ----------------------------------------------------------------------
; DATOS tabla_5FEF: 5 entradas, desde el call de 0x5FEC; cierra en 0x5FF9
;   0x5fef..0x5ff9  (10 bytes)
DATA_tabla_5FEF:
	defw 06034h,05ff9h,05fffh,06016h,0601fh	; 5fef

; ======================================================================
; CODIGO 0x5ff9..0x60b6  (189 bytes)
; ======================================================================


L_5FF9:
	call L_6D97		;5ff9
	jp L_7149		;5ffc
L_5FFF:
	call L_6019		;5fff
	ld de,02d00h		;6002
	ld hl,07056h		;6005
	call L_45CD		;6008
	ld de,00d00h		;600b
	ld bc,00100h		;600e
	ld a,060h		;6011
	jp rellena_vram		;6013
L_6016:
	call L_71D9		;6016
L_6019:
	ld hl,06547h		;6019
	jp descomprime		;601c
L_601F:
	call L_7477		;601f
	ld de,05b20h		;6022
	ld hl,06323h		;6025
	call L_45CD		;6028
	call L_603D		;602b
	ld hl,068bdh		;602e
	jp descomprime		;6031
L_6034:
	call L_753B		;6034
	ld hl,067a1h		;6037
	call descomprime		;603a
L_603D:
	ld de,05ba0h		;603d
	ld hl,0667dh		;6040
	jp L_45CD		;6043
L_6046:
	xor a			;6046
L_6047:
	ld (hl),a			;6047
	inc hl			;6048
	djnz L_6047		;6049
	ret			;604b
L_604C:
	ld hl,(0e14ah)		;604c
	exx			;604f
	ld hl,0e130h		;6050
	ld b,050h		;6053
	call L_6046		;6055
	call L_6046		;6058
	exx			;605b
	ld (0e14ah),hl		;605c
	ld a,0c3h		;605f
	ld hl,0e0b0h		;6061
	ld b,080h		;6064
	call L_6047		;6066
	ld de,0e0e0h		;6069
	ld hl,06d63h		;606c
	ld bc,00010h		;606f
	ldir		;6072
	ld de,0e120h		;6074
	ld c,010h		;6077
	ldir		;6079
	call L_57A8		;607b
	jr nz,L_6095		;607e
	ex de,hl			;6080
	ld hl,0e0e0h		;6081
	ld b,014h		;6084
L_6086:
	ld a,(hl)			;6086
	cp 0c3h		;6087
	jr z,L_608E		;6089
	add a,058h		;608b
	ld (hl),a			;608d
L_608E:
	inc hl			;608e
	inc hl			;608f
	inc hl			;6090
	inc hl			;6091
	djnz L_6086		;6092
	ex de,hl			;6094
L_6095:
	ld de,0e0b0h		;6095
	ld c,014h		;6098
	ldir		;609a
	ld de,0619dh		;609c
	call L_61AB		;609f
	ld a,002h		;60a2
	ld (0e210h),a		;60a4
	ld hl,0e14ch		;60a7
	dec (hl)			;60aa
	inc hl			;60ab
	ld (hl),0a0h		;60ac
	ld a,(0e052h)		;60ae
	and 00fh		;60b1
	call despacha_por_tabla		;60b3

; ----------------------------------------------------------------------
; DATOS tabla_60B6: 5 entradas, desde el call de 0x60B3; cierra en 0x60C0
;   0x60b6..0x60c0  (10 bytes)
DATA_tabla_60B6:
	defw 06161h,060c0h,060f2h,06139h,06142h	; 60b6

; ======================================================================
; CODIGO 0x60c0..0x6196  (214 bytes)
; ======================================================================


L_60C0:
	ld de,06196h		;60c0
	call L_61AB		;60c3
	ld hl,0e150h		;60c6
	ld b,004h		;60c9
L_60CB:
	dec (hl)			;60cb
	inc hl			;60cc
	ld (hl),048h		;60cd
	inc hl			;60cf
	djnz L_60CB		;60d0
	ld hl,0800fh		;60d2
	ld (0e160h),hl		;60d5
L_60D8:
	ld hl,0e130h		;60d8
	ld (hl),085h		;60db
	inc hl			;60dd
	ld (hl),03ch		;60de
	inc hl			;60e0
	ld (hl),000h		;60e1
	ld a,(0e002h)		;60e3
	bit 6,a		;60e6
	ret z			;60e8
	ld a,089h		;60e9
	ex af,af'			;60eb
	ld a,006h		;60ec
	ex af,af'			;60ee
	jp L_7BA2		;60ef
L_60F2:
	ld hl,0e1b0h		;60f2
	ld (hl),0d0h		;60f5
	inc hl			;60f7
	ld (hl),050h		;60f8
	inc hl			;60fa
	ld (hl),050h		;60fb
	inc hl			;60fd
	ld (hl),00dh		;60fe
	ld hl,059fah		;6100
	ld (0e1b6h),hl		;6103
	ld a,040h		;6106
	ld (0e1bah),a		;6108
	ld (0e217h),a		;610b
	ld a,048h		;610e
	ld (0e14dh),a		;6110
	ld a,03fh		;6113
L_6115:
	ld hl,0e130h		;6115
	ld (hl),a			;6118
	inc hl			;6119
	ld (hl),03ch		;611a
	inc hl			;611c
	ld (hl),000h		;611d
	ld a,08bh		;611f
	ex af,af'			;6121
	ld a,006h		;6122
	ex af,af'			;6124
	call L_7BA2		;6125
L_6128:
	ld hl,0e170h		;6128
	dec (hl)			;612b
	inc hl			;612c
	inc hl			;612d
	dec (hl)			;612e
	inc hl			;612f
	inc hl			;6130
	dec (hl)			;6131
	ld hl,0a00fh		;6132
	ld (0e180h),hl		;6135
	ret			;6138
L_6139:
	ld a,07eh		;6139
	ld (0e18ch),a		;613b
	ld a,07eh		;613e
	jr L_6115		;6140
L_6142:
	ld de,061a4h		;6142
	call L_61AB		;6145
	ld hl,05c8eh		;6148
	ld (0e26ch),hl		;614b
	ld (0e25ah),hl		;614e
	ld hl,0e26eh		;6151
	ld (hl),001h		;6154
	inc hl			;6156
	inc hl			;6157
	ld (hl),050h		;6158
	inc hl			;615a
	inc hl			;615b
	ld (hl),000h		;615c
	jp L_60D8		;615e
L_6161:
	ld hl,0e130h		;6161
	ld (hl),02eh		;6164
	inc hl			;6166
	ld (hl),03ch		;6167
	inc hl			;6169
	ld (hl),000h		;616a
	inc hl			;616c
	inc hl			;616d
	ld (hl),002h		;616e
	ld a,048h		;6170
	ld (0e14dh),a		;6172
	ld a,001h		;6175
	ld (0e1c0h),a		;6177
	ld a,080h		;617a
	ld (0e1cah),a		;617c
	ld hl,0e1e0h		;617f
	ld (hl),041h		;6182
	inc hl			;6184
	ld (hl),090h		;6185
	inc hl			;6187
	ld (hl),083h		;6188
	inc hl			;618a
	ld (hl),0a0h		;618b
	ld a,08dh		;618d
	ex af,af'			;618f
	ld a,004h		;6190
	ex af,af'			;6192
	jp L_7BA2		;6193

; ----------------------------------------------------------------------
; DATOS tres_grupos_de_siete: 0x6196, 0x619D y 0x61A4, siete bytes cada uno
;   0x6196..0x61ab  (21 bytes)
DATA_tres_grupos_de_siete:
	defb 008h,00fh,008h,00fh,00bh,00bh,006h	; 6196
	defb 008h,00fh,008h,00fh,000h,000h,000h	; 619d
	defb 008h,00fh,008h,00fh,00fh,00fh,00fh	; 61a4

; ======================================================================
; CODIGO 0x61ab..0x61ba  (15 bytes)
; ======================================================================


L_61AB:
	ld hl,0e0c7h		;61ab
	ld b,007h		;61ae
L_61B0:
	ld a,(de)			;61b0
	ld (hl),a			;61b1
	inc de			;61b2
	inc hl			;61b3
	inc hl			;61b4
	inc hl			;61b5
	inc hl			;61b6
	djnz L_61B0		;61b7
	ret			;61b9

; ----------------------------------------------------------------------
; DATOS bloque_sprites_61BA: 909 bytes -> 1376 en patrones de sprites
;   (0x1800). Lo carga 0x5FD6, y 0x6025 entra por 0x6323 para cargar solo los
;   704 ultimos
;   0x61ba..0x6547  (909 bytes)
DATA_bloque_sprites_61BA:
	defb 000h,058h,086h,0ffh,0fch,0f0h,0c0h,0e0h,0e0h,003h,0f0h,004h,0f8h,003h,0fch,011h	; 61ba  .X..............
	defb 000h,085h,003h,00fh,03fh,01fh,01fh,003h,00fh,004h,007h,003h,003h,084h,00fh,0ffh	; 61ca  ....?...........
	defb 0dfh,0bfh,005h,07fh,08dh,0bfh,0dbh,0e7h,0ffh,0ffh,0ffh,0f3h,03fh,00fh,003h,000h	; 61da  ............?...
	defb 001h,001h,003h,003h,004h,007h,003h,00fh,011h,0c0h,085h,0f0h,0fch,0ffh,0feh,0feh	; 61ea  ................
	defb 003h,0fch,004h,0f8h,003h,0f0h,010h,000h,089h,0ffh,0e3h,0ddh,09ch,09ch,09ch,0ddh	; 61fa  ................
	defb 0e3h,0ffh,007h,000h,003h,0ffh,081h,083h,004h,0a9h,081h,0ffh,017h,000h,009h,0ffh	; 620a  ................
	defb 017h,000h,083h,0ffh,0f3h,0e3h,004h,0f3h,082h,0e1h,0ffh,017h,000h,089h,0ffh,0c1h	; 621a  ................
	defb 09ch,0fch,0f1h,0c3h,08fh,080h,0ffh,017h,000h,089h,0ffh,0c1h,09ch,0fch,0f1h,0fch	; 622a  ................
	defb 09ch,0c1h,0ffh,017h,000h,089h,0ffh,0f1h,0e1h,0c9h,099h,099h,080h,0f9h,0ffh,017h	; 623a  ................
	defb 000h,089h,0ffh,080h,09fh,081h,09ch,0fch,09ch,0c1h,0ffh,017h,000h,089h,0ffh,0c1h	; 624a  ................
	defb 09ch,09fh,081h,09ch,09ch,0c1h,0ffh,017h,000h,089h,0ffh,080h,09ch,0f9h,0f3h,0e7h	; 625a  ................
	defb 0e7h,0e7h,0ffh,015h,000h,082h,001h,003h,00ch,000h,084h,060h,0e0h,0f0h,0f0h,01ah	; 626a  ...........`....
	defb 000h,082h,018h,018h,004h,000h,083h,067h,02fh,05ch,003h,000h,08eh,001h,001h,000h	; 627a  .......g/\......
	defb 03ch,03fh,0cfh,0c0h,0cfh,0f8h,07fh,0f8h,0fbh,03eh,007h,005h,000h,087h,03ch,0fch	; 628a  <?.......>....<.
	defb 0f3h,003h,0f3h,00fh,0feh,09fh,000h,000h,003h,01fh,01bh,03bh,03ah,09eh,09fh,0c3h	; 629a  ...........;:...
	defb 000h,000h,00fh,000h,007h,000h,000h,000h,0c0h,0f8h,0b8h,0bch,0bch,0f8h,0f9h,0c3h	; 62aa  ................
	defb 000h,000h,0f0h,000h,0f0h,009h,000h,088h,00fh,01fh,03fh,03fh,03fh,03eh,03eh,01ch	; 62ba  ..........???>>.
	defb 008h,000h,088h,080h,0ech,0f8h,0c4h,000h,000h,006h,086h,008h,000h,088h,0e0h,0e0h	; 62ca  ................
	defb 0c0h,000h,000h,001h,001h,003h,00bh,000h,0b2h,030h,0e8h,0e8h,0e8h,078h,001h,000h	; 62da  .........0...x..
	defb 000h,007h,01dh,03dh,03eh,076h,000h,007h,000h,003h,000h,006h,006h,007h,0c0h,080h	; 62ea  ...=>v..........
	defb 000h,0e0h,0c0h,0e0h,0f0h,0f0h,000h,0f0h,000h,0c0h,000h,000h,0c0h,0e0h,01ah,00fh	; 62fa  ................
	defb 003h,000h,002h,002h,001h,001h,037h,000h,003h,000h,007h,003h,000h,083h,038h,068h	; 630a  ......7.......8h
	defb 0f0h,005h,000h,083h,0f0h,000h,0e0h,005h,000h,008h,000h,082h,007h,00fh,005h,01fh	; 631a  ................
	defb 081h,00eh,008h,000h,088h,0c0h,0f6h,0fch,0e2h,080h,000h,003h,043h,008h,000h,083h	; 632a  ............C...
	defb 030h,070h,060h,004h,000h,081h,001h,00bh,000h,0c0h,018h,074h,0f4h,0f4h,0bch,000h	; 633a  0p`........t....
	defb 000h,007h,00dh,01eh,03eh,037h,033h,000h,007h,000h,00fh,000h,006h,006h,007h,0e0h	; 634a  ....>73.........
	defb 040h,080h,0f0h,0e0h,0e0h,070h,070h,000h,0f0h,000h,0c0h,000h,000h,0c0h,0e0h,00dh	; 635a  @....pp.........
	defb 007h,000h,002h,001h,001h,000h,000h,033h,000h,00fh,000h,007h,000h,000h,000h,01ch	; 636a  .......3........
	defb 0b4h,078h,000h,000h,000h,080h,080h,0f0h,000h,0e0h,006h,000h,08fh,090h,0a0h,0e8h	; 637a  .x..............
	defb 0fah,0f6h,05ch,03dh,017h,00bh,003h,006h,004h,005h,003h,001h,008h,000h,089h,080h	; 638a  ..\=............
	defb 0c0h,0c0h,090h,0d0h,0c0h,0e4h,0f8h,003h,00fh,000h,090h,0f8h,0f3h,0e2h,064h,03ch	; 639a  ..............d<
	defb 0fch,0f8h,0e8h,05eh,0bdh,03ch,019h,03eh,0beh,09eh,05eh,010h,000h,090h,07ch,03ch	; 63aa  ...^.<.>..^...|<
	defb 05ch,05ah,066h,07eh,03ch,09ch,07ch,03ch,05ch,05ah,066h,07eh,03ch,09ch,009h,000h	; 63ba  \Zf~<.|<\Zf~<...
	defb 003h,001h,004h,000h,0a8h,05eh,0bdh,03ch,019h,03eh,0beh,09eh,05eh,07dh,03eh,07eh	; 63ca  .....^.<.>..^}>~
	defb 078h,0f7h,0f6h,0ech,068h,000h,004h,005h,00ah,007h,00fh,017h,01fh,00fh,05dh,05ah	; 63da  x...h.........]Z
	defb 0f4h,0f0h,0d0h,0c0h,040h,0fch,0f8h,0d0h,0e0h,0e0h,070h,080h,080h,00ah,000h,0afh	; 63ea  ....@.....p.....
	defb 006h,007h,001h,000h,001h,007h,00fh,00eh,01dh,01eh,00fh,00ch,007h,001h,000h,000h	; 63fa  ................
	defb 0ach,0fch,0f0h,0e0h,0f0h,0fch,05eh,006h,05fh,00fh,056h,00eh,05ch,0f0h,000h,00dh	; 640a  ......^._.V.\...
	defb 013h,023h,027h,027h,007h,0c7h,0cfh,00fh,01fh,01eh,00eh,00eh,00fh,007h,07fh,008h	; 641a  .#''............
	defb 0ffh,097h,087h,038h,070h,070h,078h,038h,000h,000h,0c0h,000h,080h,014h,038h,0bch	; 642a  ...8ppx8......8.
	defb 0bch,03ah,0bch,0feh,03dh,03bh,03dh,01dh,00eh,004h,000h,097h,030h,0e4h,0f4h,03ch	; 643a  .:..=;=.....0..<
	defb 03eh,01eh,000h,080h,080h,0c0h,0e0h,060h,0eeh,03fh,0ffh,07fh,0ebh,0c7h,043h,043h	; 644a  >......`.?....CC
	defb 0c5h,043h,001h,005h,000h,08bh,074h,0f8h,0fch,0feh,0ceh,000h,000h,0c3h,0c1h,0e0h	; 645a  .C....t.........
	defb 0b8h,005h,000h,08ah,01eh,033h,043h,047h,007h,0c7h,0c3h,007h,003h,001h,006h,000h	; 646a  .....3CG........
	defb 008h,0ffh,098h,0fdh,0feh,07fh,03fh,007h,037h,02bh,001h,000h,080h,0c0h,0a0h,0c0h	; 647a  ......?.7+......
	defb 080h,010h,038h,07ch,07ah,0fch,078h,040h,098h,0e0h,0e0h,004h,000h,086h,038h,0e4h	; 648a  ..8|z.x@......8.
	defb 0f4h,0fch,07eh,01eh,006h,000h,08bh,0beh,07fh,03fh,05fh,03fh,07fh,0efh,0c7h,083h	; 649a  ..~......?_?....
	defb 085h,003h,005h,000h,08bh,0b0h,0fah,0fch,0feh,0c6h,000h,000h,003h,081h,0e0h,0b8h	; 64aa  ................
	defb 005h,000h,090h,077h,0ddh,0c1h,003h,007h,00fh,00fh,00fh,03fh,03fh,03eh,078h,0f4h	; 64ba  ...w.......??>x.
	defb 0ech,0c0h,000h,009h,0ffh,081h,0e3h,006h,000h,08ch,0c0h,0f0h,0c0h,080h,000h,0c8h	; 64ca  ................
	defb 09eh,01eh,0cfh,0ffh,0efh,013h,008h,000h,095h,030h,0e4h,0f4h,07ch,09eh,0ceh,0e0h	; 64da  .........0..|...
	defb 0f0h,07ch,0beh,04eh,000h,03dh,00fh,03fh,07fh,0ffh,037h,061h,0e1h,030h,007h,000h	; 64ea  .|.N.=.?..7a.0..
	defb 08bh,0e0h,0f8h,0fch,0feh,0ceh,000h,000h,083h,061h,030h,018h,00bh,000h,08ah,001h	; 64fa  .........a0.....
	defb 000h,005h,005h,006h,04fh,06fh,0ffh,077h,03fh,005h,000h,08bh,0c0h,080h,0d0h,0d8h	; 650a  ....Oo.w?.......
	defb 0d8h,0fah,0fbh,0f6h,0e6h,0feh,0feh,005h,000h,08bh,002h,00ah,006h,00eh,00ah,01fh	; 651a  ................
	defb 0bbh,05dh,0dfh,07fh,01fh,005h,000h,090h,040h,0c0h,060h,0e0h,0f0h,0eah,0e4h,0f4h	; 652a  .]......@.`.....
	defb 0dch,0fch,0feh,0f0h,070h,070h,070h,0e0h,004h,060h,017h,000h,000h	; 653a  ....ppp..`...

; ----------------------------------------------------------------------
; DATOS bloque_6547: 602 bytes -> 704 en VRAM (0x1A20). Lo carga 0x6019, y
;   0x6040 entra por 0x667D para los 320 ultimos
;   0x6547..0x67a1  (602 bytes)
DATA_bloque_6547:
	defb 020h,05ah,008h,000h,088h,00fh,01fh,03fh,03fh,03fh,03eh,03eh,01ch,008h,000h,088h	; 6547   Z.....???>>....
	defb 080h,0ech,0f8h,0c4h,000h,000h,006h,086h,008h,000h,088h,0e0h,0e0h,0c0h,000h,000h	; 6557  ................
	defb 001h,001h,003h,00bh,000h,0c2h,030h,0e8h,0e8h,0e8h,078h,001h,000h,000h,00fh,03dh	; 6567  ......0...x....=
	defb 03dh,01eh,006h,000h,003h,000h,00dh,00ch,019h,011h,009h,0c0h,080h,000h,0c0h,0c0h	; 6577  =...............
	defb 0ech,0f4h,0f0h,000h,0f0h,000h,0e0h,000h,080h,0b0h,0f8h,01ah,00fh,003h,000h,0c2h	; 6587  ................
	defb 042h,001h,001h,003h,000h,001h,000h,001h,000h,000h,000h,038h,068h,0f0h,000h,000h	; 6597  B..........8h...
	defb 003h,002h,000h,0f0h,000h,0e0h,000h,0c0h,00bh,000h,088h,00fh,01fh,03fh,03fh,03fh	; 65a7  .............???
	defb 03eh,03eh,01ch,008h,000h,088h,080h,0ech,0f8h,0c4h,000h,000h,006h,086h,008h,000h	; 65b7  >>..............
	defb 088h,060h,0e0h,0c0h,000h,000h,001h,001h,003h,00bh,000h,0c2h,030h,0e8h,0e8h,0e8h	; 65c7  .`..........0...
	defb 078h,001h,000h,000h,00fh,03dh,07fh,02eh,006h,000h,007h,000h,003h,000h,003h,003h	; 65d7  x....=..........
	defb 003h,0c0h,080h,000h,0e0h,0f8h,0e8h,0f0h,0f0h,000h,0f0h,000h,0c0h,03ah,01ch,064h	; 65e7  .............:.d
	defb 0f4h,01ah,00fh,003h,000h,002h,080h,0c1h,001h,003h,000h,007h,000h,003h,000h,000h	; 65f7  ................
	defb 000h,038h,068h,0f0h,000h,004h,006h,000h,000h,0f0h,000h,0e0h,000h,080h,00bh,000h	; 6607  .8h.............
	defb 088h,00fh,01fh,03fh,03fh,03fh,03eh,03eh,01ch,008h,000h,088h,080h,0e4h,0f8h,0c4h	; 6617  ...???>>........
	defb 000h,000h,006h,086h,008h,000h,088h,0c0h,0e0h,0c0h,000h,000h,001h,001h,003h,00bh	; 6627  ................
	defb 000h,0c2h,030h,0e8h,0e8h,0e8h,078h,001h,000h,000h,01fh,03dh,03dh,01eh,006h,000h	; 6637  ..0...x....==...
	defb 007h,000h,007h,000h,00ch,00ch,00fh,0c0h,080h,000h,0c0h,0ech,0f4h,0f0h,0f0h,000h	; 6647  ................
	defb 0f0h,000h,0d0h,000h,060h,06ch,07eh,01ah,00fh,003h,000h,0c2h,042h,001h,001h,003h	; 6657  ....`l~.....B...
	defb 000h,007h,000h,00eh,000h,000h,000h,038h,068h,0f0h,000h,003h,002h,000h,000h,0f0h	; 6667  .......8h.......
	defb 000h,0e0h,000h,070h,003h,000h,008h,000h,088h,007h,00fh,01fh,03fh,03fh,03eh,03eh	; 6677  ...p........??>>
	defb 01ch,008h,000h,088h,080h,0e4h,0f8h,0c4h,000h,000h,006h,086h,008h,000h,088h,060h	; 6687  ...............`
	defb 0f0h,060h,000h,000h,001h,001h,003h,00bh,000h,0b0h,030h,0e8h,0e8h,0e8h,078h,001h	; 6697  .`........0...x.
	defb 000h,000h,00fh,03dh,07dh,01eh,00eh,000h,0cfh,060h,0ffh,0deh,080h,000h,000h,0c0h	; 66a7  ...=}....`......
	defb 080h,000h,0c0h,0e8h,0e8h,0f0h,0f0h,000h,0e1h,001h,07fh,00ch,000h,000h,000h,01ah	; 66b7  ................
	defb 00fh,003h,080h,0c2h,002h,001h,001h,00fh,000h,007h,005h,000h,08bh,038h,060h,0f0h	; 66c7  .............8`.
	defb 000h,006h,004h,000h,000h,0f0h,000h,0f0h,005h,000h,0c0h,01eh,07fh,03fh,01fh,05eh	; 66d7  .............?.^
	defb 07fh,0feh,0dfh,03fh,077h,00fh,00fh,01eh,01ch,031h,020h,040h,080h,0c0h,0c0h,060h	; 66e7  ...?w....1 @...`
	defb 060h,0e2h,0f1h,0fdh,0feh,0ffh,0ffh,0ffh,01eh,007h,08eh,000h,01eh,07fh,03fh,01fh	; 66f7  `.............?.
	defb 05eh,07fh,0feh,0dfh,03fh,077h,007h,007h,003h,00bh,00dh,000h,040h,080h,0c0h,0c0h	; 6707  ^...?w......@...
	defb 060h,060h,0e6h,0f1h,0f9h,0fdh,0feh,0ffh,0dfh,087h,06eh,0c0h,01eh,07fh,03fh,01fh	; 6717  ``........n...?.
	defb 05eh,07fh,0feh,0dfh,03fh,077h,00fh,00bh,01dh,019h,010h,008h,040h,080h,0c0h,0c0h	; 6727  ^...?w......@...
	defb 060h,066h,0e1h,0f1h,0fdh,0feh,0ffh,0ffh,0ffh,0dfh,04eh,0ddh,02eh,07fh,03fh,01fh	; 6737  `f........N...?.
	defb 05eh,07fh,0feh,0dfh,01fh,037h,007h,003h,04fh,05fh,07fh,027h,060h,0ach,0ceh,0c6h	; 6747  ^....7..O_.'`...
	defb 06eh,06eh,0fch,0fch,0f8h,0f0h,0f0h,0e0h,0e4h,0e4h,0d8h,080h,003h,000h,09ah,020h	; 6757  nn............. 
	defb 070h,078h,0fch,0f8h,000h,000h,002h,007h,00fh,01fh,00fh,003h,0c0h,0f0h,0f8h,0f0h	; 6767  px..............
	defb 0e0h,040h,000h,000h,01fh,03fh,01eh,00eh,004h,003h,000h,08dh,003h,00fh,01fh,00fh	; 6777  .@...?..........
	defb 007h,002h,000h,000h,0f8h,0fch,078h,070h,020h,006h,000h,08dh,004h,00eh,01eh,03fh	; 6787  ......xp ......?
	defb 01fh,000h,000h,040h,0e0h,0f0h,0f8h,0f0h,0c0h,000h	; 6797  ...@......

; ----------------------------------------------------------------------
; DATOS bloque_67A1: 284 bytes -> 384 en VRAM (0x1A20). Lo carga 0x6037
;   0x67a1..0x68bd  (284 bytes)
DATA_bloque_67A1:
	defb 020h,05ah,008h,000h,088h,00fh,01fh,03fh,03fh,03fh,03eh,01eh,01ch,008h,000h,088h	; 67a1   Z.....???>.....
	defb 080h,0ech,0f8h,0c4h,000h,000h,000h,03ch,008h,000h,088h,060h,0e0h,0c0h,000h,000h	; 67b1  .......<...`....
	defb 001h,001h,003h,00bh,000h,091h,030h,0e8h,0e8h,0ebh,0c3h,00bh,00fh,01fh,01fh,03fh	; 67c1  ......0........?
	defb 03fh,000h,03fh,000h,01fh,000h,001h,004h,000h,090h,0feh,0f8h,0e0h,0c0h,040h,080h	; 67d1  ?.?...........@.
	defb 000h,000h,000h,088h,018h,0f0h,060h,020h,000h,000h,006h,000h,085h,03fh,000h,01fh	; 67e1  ......` .....?..
	defb 000h,007h,009h,000h,081h,080h,005h,000h,081h,0c0h,009h,000h,08ch,003h,00fh,01fh	; 67f1  ................
	defb 03fh,03fh,03fh,03eh,03ch,01ch,00ah,000h,007h,004h,000h,08ch,0d0h,0f4h,0fah,0c4h	; 6801  ???><...........
	defb 000h,000h,000h,00ch,00fh,01eh,07ch,0fch,005h,000h,08ah,060h,0e0h,0c0h,000h,000h	; 6811  ......|....`....
	defb 001h,003h,003h,003h,007h,008h,000h,0a5h,030h,0e8h,0e8h,0ebh,0f3h,0f0h,0e0h,080h	; 6821  ........0.......
	defb 000h,003h,003h,001h,001h,000h,003h,000h,001h,000h,001h,007h,007h,006h,00ch,008h	; 6831  ................
	defb 000h,0f8h,0f8h,0e8h,0e8h,000h,0f8h,000h,0f0h,000h,0e0h,0c0h,0c0h,008h,000h,085h	; 6841  ................
	defb 003h,000h,003h,000h,001h,009h,000h,087h,010h,010h,0f8h,000h,0f0h,000h,0e0h,00fh	; 6851  ................
	defb 000h,082h,007h,00fh,004h,01fh,082h,01eh,00fh,008h,000h,088h,0c0h,0f6h,0fch,0e2h	; 6861  ................
	defb 080h,000h,000h,004h,008h,000h,088h,070h,070h,020h,000h,000h,000h,001h,000h,00bh	; 6871  .......pp ......
	defb 000h,087h,018h,074h,0f4h,0f7h,0fbh,000h,000h,003h,001h,005h,000h,093h,002h,002h	; 6881  ...t............
	defb 007h,00eh,008h,000h,01fh,07eh,0fch,0fch,0f6h,0fah,07bh,000h,03fh,000h,0fch,000h	; 6891  .....~....{.?...
	defb 0c0h,003h,000h,082h,006h,003h,009h,000h,081h,001h,004h,000h,08ch,0e0h,080h,000h	; 68a1  ................
	defb 000h,008h,004h,004h,07fh,000h,07eh,000h,0f0h,004h,000h,000h	; 68b1  ......~.....

; ----------------------------------------------------------------------
; DATOS bloque_68BD: 171 bytes -> 224 en VRAM (0x1C80). Lo carga 0x602E
;   0x68bd..0x6968  (171 bytes)
DATA_bloque_68BD:
	defb 080h,05ch,008h,000h,088h,001h,003h,005h,00bh,017h,02fh,05fh,0bfh,008h,000h,098h	; 68bd  .\......../_....
	defb 050h,0f0h,0f8h,0fch,0c4h,0e6h,0ffh,0ffh,039h,067h,06fh,0cfh,0dfh,0dfh,05fh,00fh	; 68cd  P.......9go..._.
	defb 00fh,01fh,03fh,038h,063h,066h,044h,044h,008h,0ffh,088h,0fdh,0c0h,000h,000h,000h	; 68dd  ..?8cfDD........
	defb 001h,001h,000h,007h,0ffh,08bh,0feh,0feh,07ch,07eh,0eeh,0c6h,08ch,098h,080h,0ech	; 68ed  ........|~......
	defb 0c2h,003h,080h,00bh,000h,090h,03bh,077h,0efh,0cfh,0dfh,05fh,05fh,00fh,00fh,007h	; 68fd  ......;w...__...
	defb 00fh,007h,00eh,007h,001h,000h,008h,0ffh,088h,0f7h,0c0h,080h,0c0h,060h,000h,080h	; 690d  .............`..
	defb 0c0h,009h,0ffh,08bh,0f9h,039h,03fh,0b6h,0e0h,000h,000h,0edh,0c2h,080h,080h,003h	; 691d  .....9?.........
	defb 000h,004h,080h,005h,000h,090h,039h,077h,0efh,0cfh,09fh,09fh,09fh,01fh,03fh,03fh	; 692d  ......9w......??
	defb 03dh,073h,061h,0c0h,080h,080h,008h,0ffh,088h,0f8h,0c0h,000h,000h,080h,080h,0e0h	; 693d  =sa.............
	defb 070h,008h,0ffh,083h,07fh,00fh,001h,005h,000h,090h,0edh,0c2h,080h,080h,000h,0e0h	; 694d  p...............
	defb 0f0h,0f0h,0b0h,0f0h,0e0h,070h,0b8h,00ch,000h,000h,000h	; 695d  .....p.....

; ======================================================================
; CODIGO 0x6968..0x6aa7  (319 bytes)
; ======================================================================


L_6968:
	ld hl,06be3h		;6968
	call L_6A42		;696b
	ld hl,06d1ah		;696e
	ld de,04200h		;6971
	di			;6974
	call prepara_escritura_vram		;6975
	call vuelca_patrones_repetidos		;6978
	call L_45D1		;697b
	call L_462F		;697e
	ld de,00000h		;6981
	ld bc,00288h		;6984
	call copia_a_los_tres_tercios		;6987
	call L_72E1		;698a
	call L_57A8		;698d
	ret nz			;6990
	ld de,00288h		;6991
	ld bc,003f8h		;6994
	call copia_a_los_tres_tercios		;6997
	jp L_73B6		;699a
L_699D:
	call L_57A8		;699d
	push af			;69a0
	call z,L_69C8		;69a1
	pop af			;69a4
	ld hl,01000h		;69a5
	ld de,01800h		;69a8
	ld bc,02013h		;69ab
	jr nz,L_69B6		;69ae
	ld h,068h		;69b0
	ld d,070h		;69b2
	ld c,00ah		;69b4
L_69B6:
	ld (0e14ah),hl		;69b6
	call L_6A6D		;69b9
	ld hl,06d0ah		;69bc
	call L_6A42		;69bf
	ld hl,0e14ah		;69c2
	jp L_56D4		;69c5
L_69C8:
	ld hl,06ac1h		;69c8
	cp 002h		;69cb
	jr z,L_69D2		;69cd
	ld hl,06ac6h		;69cf
L_69D2:
	jp descomprime		;69d2
L_69D5:
	ld b,(hl)			;69d5
	inc hl			;69d6
	ld c,(hl)			;69d7
	inc hl			;69d8
	push hl			;69d9
	call prepara_la_figura		;69da
	pop hl			;69dd
	ret			;69de
L_69DF:
	ld d,(hl)			;69df
	inc hl			;69e0
L_69E1:
	ld a,(hl)			;69e1
	inc hl			;69e2
	or a			;69e3
	ret z			;69e4
	ld e,a			;69e5
	push de			;69e6
	ex de,hl			;69e7
	add hl,hl			;69e8
	add hl,hl			;69e9
	add hl,hl			;69ea
	ex de,hl			;69eb
	set 6,d		;69ec
	di			;69ee
	call prepara_escritura_vram		;69ef
	ld de,0e280h		;69f2
	call L_6A1A		;69f5
	pop de			;69f8
	jr L_69E1		;69f9
L_69FB:
	ld a,(hl)			;69fb
	inc hl			;69fc
	or a			;69fd
	ret z			;69fe
	ld e,a			;69ff
	ld d,005h		;6a00
	ex de,hl			;6a02
	add hl,hl			;6a03
	add hl,hl			;6a04
	add hl,hl			;6a05
	ex de,hl			;6a06
	set 6,d		;6a07
	di			;6a09
	call prepara_escritura_vram		;6a0a
	ld de,0e280h		;6a0d
	ld a,(hl)			;6a10
	inc hl			;6a11
	call suma_a_a_de		;6a12
	call L_6A1A		;6a15
	jr L_69FB		;6a18
L_6A1A:
	ld c,(hl)			;6a1a
	inc hl			;6a1b
	ld b,008h		;6a1c
	ex de,hl			;6a1e
L_6A1F:
	rl c		;6a1f
	push bc			;6a21
	ld bc,00008h		;6a22
	call c,copia_literal		;6a25
	add hl,bc			;6a28
	pop bc			;6a29
	djnz L_6A1F		;6a2a
	ex de,hl			;6a2c
	ld a,(hl)			;6a2d
	or a			;6a2e
	jr nz,L_6A1A		;6a2f
	inc hl			;6a31
	ret			;6a32
L_6A33:
	call L_6A51		;6a33
	call L_69D5		;6a36
	call L_69FB		;6a39
	ld a,(hl)			;6a3c
	or a			;6a3d
	jr nz,L_6A33		;6a3e
	inc hl			;6a40
	ret			;6a41
L_6A42:
	call L_6A51		;6a42
	call L_69D5		;6a45
	call L_69DF		;6a48
	ld a,(hl)			;6a4b
	or a			;6a4c
	jr nz,L_6A42		;6a4d
	inc hl			;6a4f
	ret			;6a50
L_6A51:
	ld de,0e280h		;6a51
L_6A54:
	ld a,(hl)			;6a54
	inc hl			;6a55
	or a			;6a56
	ret z			;6a57
	jp m,L_6A64		;6a58
	ld b,a			;6a5b
	ld a,(hl)			;6a5c
	inc hl			;6a5d
L_6A5E:
	ld (de),a			;6a5e
	inc de			;6a5f
	djnz L_6A5E		;6a60
	jr L_6A54		;6a62
L_6A64:
	and 07fh		;6a64
	ld c,a			;6a66
	ld b,000h		;6a67
	ldir		;6a69
	jr L_6A54		;6a6b
L_6A6D:
	ld h,d			;6a6d
	call L_53F3		;6a6e
	call L_57A8		;6a71
	ld a,h			;6a74
	ld hl,06aa9h		;6a75
	jr nz,L_6A7D		;6a78
	ld hl,06a9eh		;6a7a
L_6A7D:
	rra			;6a7d
	rra			;6a7e
	rra			;6a7f
	and 01fh		;6a80
	call suma_a_a_hl		;6a82
	ld a,e			;6a85
	or 0e0h		;6a86
	neg		;6a88
	cp b			;6a8a
	jr nc,L_6A8E		;6a8b
	ld b,a			;6a8d
L_6A8E:
	set 6,d		;6a8e
	di			;6a90
L_6A91:
	push bc			;6a91
	call prepara_escritura_vram		;6a92
L_6A95:
	ld a,(hl)			;6a95
	exx			;6a96
	out (c),a		;6a97
	exx			;6a99
	djnz L_6A95		;6a9a
	inc hl			;6a9c
	ld a,020h		;6a9d
	call suma_a_a_de		;6a9f
	pop bc			;6aa2
	dec c			;6aa3
	jr nz,L_6A91		;6aa4
	ret			;6aa6

; ----------------------------------------------------------------------
; DATOS cola_6AA7: dos ceros, cola de la tabla de 0x6A9E
;   0x6aa7..0x6aa9  (2 bytes)
DATA_cola_6AA7:
	defb 000h,000h	; 6aa7

; ----------------------------------------------------------------------
; DATOS tabla_6AA9: 24 valores; la elige 0x6A75
;   0x6aa9..0x6ac1  (24 bytes)
DATA_tabla_6AA9:
	defb 000h,000h,000h,051h,051h,051h,000h,000h	; 6aa9  ...QQQ..
	defb 040h,004h,000h,001h,005h,000h,000h,002h	; 6ab1  @.......
	defb 000h,000h,001h,000h,000h,003h,000h,000h	; 6ab9  ........

; ----------------------------------------------------------------------
; DATOS bloque_6AC1 (tramo): 10 bytes -> 138 en VRAM. Lo carga 0x69C8, y
;   0x69CF entra por 0x6AC6 para los 32 ultimos
;   0x6ac1..0x6ac6  (5 bytes)  de 0x6ac1..0x6acb (10 bytes)
DATA_bloque_6AC1:
	defb 080h,079h,020h,00ah,000h	; 6ac1

; ----------------------------------------------------------------------
; DATOS bloque_6AC6: 5 bytes -> 32 en la tabla de nombres (0x3860). Lo carga
;   0x69CF
;   0x6ac6..0x6acb  (5 bytes)
DATA_bloque_6AC6:
	defb 060h,078h,020h,009h,000h	; 6ac6

; ----------------------------------------------------------------------
; DATOS escena_del_nivel: 591 bytes, 14 trozos; la monta 0x56D7, y 0x6968
;   entra por 0x6BE3 para los 13 ultimos
;   0x6acb..0x6d1a  (591 bytes)
DATA_escena_del_nivel:
	defb 09fh,06bh,05bh,06bh,017h,06bh,0d3h,06ah,06ah,06ah,06ah,06ah,06bh,06ah,06ah,06ah	; 6acb  .k[k.k.jjjjjkjjj
	defb 000h,0f7h,051h,055h,056h,057h,058h,059h,051h,000h,0feh,051h,075h,075h,077h,078h	; 6adb  ..QUVWXYQ..Quuwx
	defb 079h,051h,000h,0feh,051h,007h,081h,000h,082h,007h,051h,000h,0feh,093h,0b5h,09fh	; 6aeb  yQ..Q.....Q.....
	defb 0a0h,000h,0b8h,091h,092h,093h,000h,0fch,0bbh,0b6h,0aah,0abh,000h,0b7h,0b9h,0bah	; 6afb  ................
	defb 0bbh,000h,0fch,040h,041h,048h,049h,040h,042h,040h,000h,0feh,06eh,06eh,06eh,06ch	; 6b0b  ...@AHI@B@..nnnl
	defb 06dh,06eh,06eh,06eh,000h,0f7h,05ah,05bh,05ch,057h,05dh,05eh,051h,000h,0feh,07ah	; 6b1b  mnnn..Z[\W]^Q..z
	defb 078h,079h,07bh,07ch,07dh,051h,000h,0feh,083h,084h,085h,000h,086h,087h,051h,000h	; 6b2b  xy{|}Q........Q.
	defb 0feh,09ah,0a1h,0a2h,0a3h,000h,099h,094h,092h,095h,000h,0fch,0c6h,0ach,0adh,0aeh	; 6b3b  ................
	defb 000h,0c5h,0bch,0bdh,0beh,000h,0fch,043h,050h,04ah,04bh,040h,044h,040h,000h,0feh	; 6b4b  .......CPJK@D@..
	defb 071h,071h,071h,06fh,070h,071h,071h,071h,000h,0f7h,05fh,060h,061h,062h,063h,064h	; 6b5b  qqqopqqq.._`abcd
	defb 051h,000h,0feh,07bh,07ch,07dh,07dh,07eh,075h,051h,000h,0feh,088h,089h,000h,000h	; 6b6b  Q..{|}}~uQ......
	defb 08ah,08bh,051h,000h,0feh,09ch,0a4h,0a5h,0a6h,000h,09bh,092h,092h,096h,000h,0fch	; 6b7b  ..Q.............
	defb 0c8h,0afh,0b0h,0b1h,000h,0c7h,0bfh,0c0h,0c1h,000h,0fch,045h,04ch,04dh,040h,043h	; 6b8b  ...........ELM@C
	defb 046h,040h,000h,0feh,074h,074h,074h,072h,073h,074h,074h,074h,000h,0f7h,065h,066h	; 6b9b  F@..tttrsttt..ef
	defb 057h,067h,068h,069h,051h,000h,0feh,07dh,07eh,07fh,075h,076h,080h,051h,000h,0feh	; 6bab  WghiQ..}~.uv.Q..
	defb 08ch,08dh,000h,08eh,08fh,090h,051h,000h,0feh,09eh,0a7h,0a8h,0a9h,000h,09dh,092h	; 6bbb  ......Q.........
	defb 097h,098h,000h,0fch,0cah,0b2h,0b3h,0b4h,000h,0c9h,0c2h,0c3h,0c4h,000h,0fch,042h	; 6bcb  ...............B
	defb 04eh,04fh,040h,045h,047h,040h,000h,0feh,004h,000h,08ch,099h,0ffh,042h,0ffh,000h	; 6bdb  NO@EG@.......B..
	defb 018h,03ch,07eh,0ffh,0ffh,042h,0ffh,000h,003h,048h,004h,06ah,0dfh,0f0h,000h,000h	; 6beb  .<~..B...H.j....
	defb 00bh,000h,087h,003h,00fh,03fh,07fh,0ffh,003h,01fh,00eh,0ffh,000h,006h,0a1h,004h	; 6bfb  .....?..........
	defb 055h,07fh,0bfh,0f7h,000h,000h,008h,000h,008h,0f1h,008h,0e3h,008h,0c3h,000h,006h	; 6c0b  U...............
	defb 0a1h,004h,075h,07eh,070h,089h,000h,000h,008h,000h,008h,0ffh,088h,0f0h,0f0h,0f0h	; 6c1b  ..u~p...........
	defb 0e0h,0e0h,0c0h,0c0h,080h,008h,000h,000h,006h,0a1h,004h,081h,02bh,0bch,0f7h,000h	; 6c2b  ............+...
	defb 000h,088h,000h,080h,080h,0c0h,0c0h,0e0h,0e0h,0f0h,008h,000h,000h,003h,048h,004h	; 6c3b  ..............H.
	defb 091h,0f4h,0b0h,000h,000h,008h,0ffh,088h,000h,080h,080h,0c0h,0c0h,0e0h,0e0h,0f0h	; 6c4b  ................
	defb 000h,004h,090h,004h,099h,00ah,0aah,000h,000h,090h,0f8h,0fch,0ffh,0ffh,0ffh,0ffh	; 6c5b  ................
	defb 0f8h,0e0h,000h,000h,000h,0c3h,0e7h,000h,000h,000h,000h,003h,048h,004h,0b9h,0ffh	; 6c6b  ............H...
	defb 0f0h,000h,000h,008h,0ffh,088h,0f8h,0fch,0ffh,0ffh,0ffh,0ffh,0f8h,0e0h,000h,004h	; 6c7b  ................
	defb 090h,004h,0c5h,00ah,0aah,000h,000h,008h,0ffh,090h,00fh,0ffh,0dfh,0bfh,07fh,07fh	; 6c8b  ................
	defb 07fh,07fh,0c0h,0e0h,0f0h,0f8h,0a8h,0fch,0fch,0feh,008h,000h,000h,004h,000h,004h	; 6c9b  ................
	defb 09fh,06eh,0eeh,000h,000h,008h,0ffh,090h,07fh,0bfh,0dbh,0e7h,0ffh,0ffh,0ffh,0f3h	; 6cab  .n..............
	defb 0aeh,0c6h,086h,086h,086h,087h,0c3h,0c0h,008h,000h,000h,004h,000h,004h,0aah,06eh	; 6cbb  ...............n
	defb 0eeh,000h,000h,002h,000h,006h,0ffh,002h,0fch,006h,0ffh,082h,0f3h,0f9h,006h,0ffh	; 6ccb  ................
	defb 002h,0e0h,006h,0ffh,002h,000h,006h,0ffh,000h,006h,061h,004h,040h,0c6h,018h,041h	; 6cdb  ..........a.@..A
	defb 000h,048h,030h,0c6h,018h,000h,050h,001h,000h,000h,086h,0ffh,0fch,0f0h,0c0h,0e0h	; 6ceb  .H0...P.........
	defb 0e0h,003h,0f0h,004h,0f8h,003h,0fch,000h,004h,090h,004h,0b5h,0f0h,000h,000h,004h	; 6cfb  ................
	defb 0f8h,084h,0ffh,0ffh,015h,01fh,000h,001h,000h,004h,051h,0f0h,000h,000h,000h	; 6d0b  ..........Q....

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_6D1A: 5 patrones: 8, 8, 1, 4 y 21 veces
;   0x6d1a..0x6d48  (46 bytes)
DATA_patrones_repetidos_6D1A:
	defb 008h,080h,080h,077h,077h,055h,000h,000h,088h	; 6d1a  ...wwU...
	defb 008h,0e0h,0e0h,077h,077h,055h,000h,000h,088h	; 6d23  ...wwU...
	defb 001h,08eh,08eh,077h,077h,055h,000h,000h,088h	; 6d2c  ...wwU...
	defb 004h,0b3h,083h,0f3h,0f3h,055h,088h,0f3h,0f3h	; 6d35  .....U...
	defb 015h,0f0h,0f0h,0f0h,0f0h,0f0h,0f0h,0f0h,0e0h	; 6d3e  .........
	defb 000h	; 6d47

; ----------------------------------------------------------------------
; DATOS bloque_6D48: 17 bytes -> 632 en VRAM
;   0x6d48..0x6d59  (17 bytes)
DATA_bloque_6D48:
	defb 058h,020h,060h,0f3h,040h,080h,040h,080h,070h,0fdh,058h,0e0h,058h,0e0h,020h,08eh	; 6d48  X `.@.@.p.X.X. .
	defb 000h	; 6d58

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_6D59: 1 patron
;   0x6d59..0x6d63  (10 bytes)
DATA_patrones_repetidos_6D59:
	defb 012h,0fdh,0fdh,0fdh,0fdh,0f0h,0f0h,0f0h,0f0h	; 6d59  .........
	defb 000h	; 6d62

; ----------------------------------------------------------------------
; DATOS sprites_6D63: 13 grupos de (Y, X, patron, color); 0x606C copia los
;   cuatro primeros con ldir
;   0x6d63..0x6d97  (52 bytes)
DATA_sprites_6D63:
	defb 02fh,0d2h,000h,008h	; 6d63
	defb 02fh,0f0h,008h,008h	; 6d67
	defb 02fh,0d2h,004h,00eh	; 6d6b
	defb 02fh,0f0h,00ch,001h	; 6d6f
	defb 024h,0cah,0fch,005h	; 6d73
	defb 024h,0f8h,0fch,005h	; 6d77
	defb 017h,0cah,0fch,005h	; 6d7b
	defb 017h,0f8h,0fch,005h	; 6d7f
	defb 0c3h,0e8h,064h,008h	; 6d83
	defb 0c3h,0e8h,068h,008h	; 6d87
	defb 0c3h,0e8h,06ch,008h	; 6d8b
	defb 0c3h,0e8h,070h,008h	; 6d8f
	defb 0c3h,0e8h,074h,008h	; 6d93

; ======================================================================
; CODIGO 0x6d97..0x6dc1  (42 bytes)
; ======================================================================


L_6D97:
	ld hl,06dc1h		;6d97
	call L_6A33		;6d9a
	ld de,04b00h		;6d9d
	call prepara_escritura_vram		;6da0
	call L_6DB5		;6da3
	ld hl,06fc1h		;6da6
	call L_6DB5		;6da9
	ld de,00b00h		;6dac
	ld bc,00280h		;6daf
	jp L_4612		;6db2
L_6DB5:
	ld b,004h		;6db5
L_6DB7:
	push bc			;6db7
	push hl			;6db8
	call L_462F		;6db9
	pop hl			;6dbc
	pop bc			;6dbd
	djnz L_6DB7		;6dbe
	ret			;6dc0

; ----------------------------------------------------------------------
; DATOS escena_6DC1: 484 bytes por la puerta 0x6A33 (la de la pagina fija y el
;   ajuste por fila); la monta 0x6D97
;   0x6dc1..0x6fa5  (484 bytes)
DATA_escena_6DC1:
	defb 008h,000h,088h,006h,00dh,057h,03fh,05fh,0ffh,03ah,0bch,010h,000h,000h,004h,049h	; 6dc1  .....W?_.:.....I
	defb 0b0h,000h,070h,000h,0d8h,040h,0e0h,000h,000h,008h,000h,088h,001h,00bh,02dh,017h	; 6dd1  ..p..@........-.
	defb 05fh,06fh,0feh,0feh,000h,003h,049h,0c4h,000h,01ch,000h,0ech,030h,01ch,000h,000h	; 6de1  _o....I.....0...
	defb 008h,000h,090h,001h,003h,003h,00bh,00bh,05bh,02fh,03fh,0f8h,0d0h,0e0h,060h,060h	; 6df1  ........[/?...``
	defb 0a0h,0c0h,0c0h,018h,000h,000h,006h,099h,0b8h,000h,07ch,000h,0e0h,060h,0f8h,000h	; 6e01  ..........|..`..
	defb 000h,008h,000h,090h,001h,013h,013h,01dh,00bh,007h,027h,01fh,0ech,0f0h,0d0h,0e0h	; 6e11  ..........'.....
	defb 0a0h,0a0h,0c0h,080h,000h,005h,099h,0cch,028h,0f8h,000h,0f4h,078h,0f8h,000h,000h	; 6e21  ........(...x...
	defb 008h,000h,090h,09fh,0cfh,0e7h,077h,03eh,03fh,09fh,0dfh,0c0h,080h,080h,000h,080h	; 6e31  ......w>?.......
	defb 080h,080h,000h,018h,000h,000h,006h,099h,0b3h,000h,07ch,000h,0dbh,060h,0f8h,000h	; 6e41  ..........|..`..
	defb 000h,008h,000h,089h,03fh,0dfh,05fh,02eh,0bdh,0ffh,07fh,037h,0c0h,007h,000h,000h	; 6e51  ....?._....7....
	defb 005h,099h,0c7h,028h,0f8h,000h,0efh,078h,0f8h,000h,000h,008h,000h,088h,0deh,0fdh	; 6e61  ...(...x........
	defb 07dh,03bh,0beh,0bfh,0dfh,07eh,008h,000h,000h,003h,000h,072h,000h,060h,000h,09ah	; 6e71  };...~.....r.`..
	defb 030h,0c0h,000h,0bdh,000h,060h,000h,0e5h,030h,0c0h,000h,000h,008h,000h,088h,07fh	; 6e81  0....`..0.......
	defb 0bfh,0beh,0ddh,07fh,0beh,0beh,05fh,000h,002h,000h,086h,010h,0c0h,000h,0aeh,030h	; 6e91  ......_........0
	defb 0c0h,000h,0d1h,010h,0c0h,000h,0f9h,030h,0c0h,000h,000h,008h,000h,088h,0fdh,03fh	; 6ea1  .......0.......?
	defb 05eh,05eh,06fh,07fh,03eh,0bch,008h,000h,000h,003h,000h,060h,000h,060h,000h,088h	; 6eb1  ^^o.>......`.`..
	defb 030h,0c0h,000h,000h,008h,000h,088h,07eh,0fch,07dh,0fbh,076h,07eh,0bch,0deh,000h	; 6ec1  0......~.}.v~...
	defb 002h,000h,074h,010h,0c0h,000h,09ch,030h,0c0h,000h,000h,008h,000h,089h,0bfh,0feh	; 6ed1  ..t....0........
	defb 07eh,05fh,0efh,06fh,037h,017h,000h,005h,080h,01ah,000h,000h,006h,099h,062h,000h	; 6ee1  ~_.o7.........b.
	defb 07ch,000h,08ah,060h,0f8h,000h,000h,008h,000h,089h,0feh,07ch,07eh,03eh,0ffh,0ffh	; 6ef1  |..`.......|~>..
	defb 07fh,03eh,000h,003h,080h,004h,000h,000h,005h,099h,076h,028h,0f8h,000h,09eh,078h	; 6f01  .>........v(...x
	defb 0f8h,000h,000h,008h,000h,090h,03fh,01fh,00bh,027h,017h,00fh,003h,001h,040h,060h	; 6f11  ......?..'....@`
	defb 0e0h,0d8h,0f0h,0f8h,0e8h,0f8h,018h,000h,000h,006h,099h,067h,000h,07ch,000h,08fh	; 6f21  ...........g.|..
	defb 060h,0f8h,000h,0bfh,000h,07ch,000h,0e7h,060h,0f8h,000h,000h,008h,000h,090h,07fh	; 6f31  `....|..`.......
	defb 03fh,00fh,047h,027h,00eh,001h,003h,080h,0a0h,0b0h,070h,0e0h,0f0h,0e8h,0f8h,000h	; 6f41  ?.G'......p.....
	defb 005h,099h,07bh,028h,0f8h,000h,0a3h,078h,0f8h,000h,0d3h,028h,0f8h,000h,0fbh,078h	; 6f51  ..{(...x...(...x
	defb 0f8h,000h,000h,008h,000h,088h,0f0h,0fah,05eh,02fh,02fh,00bh,01bh,002h,010h,000h	; 6f61  ........^//.....
	defb 000h,004h,049h,06fh,000h,070h,000h,097h,040h,0e0h,000h,06ch,000h,070h,000h,094h	; 6f71  ..Io.p..@..l.p..
	defb 040h,0e0h,000h,000h,008h,000h,088h,0feh,0beh,07bh,07fh,04fh,01fh,007h,003h,000h	; 6f81  @........{.O....
	defb 003h,049h,083h,000h,01ch,000h,0abh,030h,01ch,000h,080h,000h,01ch,000h,0a8h,030h	; 6f91  .I.....0.......0
	defb 01ch,000h,000h,000h	; 6fa1

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_6FA5: 3 patrones: 15, 3 y 2 veces; sigue a la
;   escena de 0x6DC1
;   0x6fa5..0x6fc1  (28 bytes)
DATA_patrones_repetidos_6FA5:
	defb 00fh,080h,080h,080h,080h,080h,080h,080h,080h	; 6fa5  .........
	defb 003h,080h,088h,080h,080h,080h,080h,080h,080h	; 6fae  .........
	defb 002h,080h,080h,080h,080h,080h,080h,080h,088h	; 6fb7  .........
	defb 000h	; 6fc0

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_6FC1: 4 patrones: 3, 5, 5 y 7 veces. 0x6DA6 lo pasa
;   por L_6DB5, que llama CUATRO veces con el mismo HL
;   0x6fc1..0x6fe6  (37 bytes)
DATA_patrones_repetidos_6FC1:
	defb 003h,080h,080h,080h,080h,080h,080h,088h,080h	; 6fc1  .........
	defb 005h,080h,088h,080h,080h,080h,080h,080h,080h	; 6fca  .........
	defb 005h,080h,080h,080h,080h,080h,080h,080h,080h	; 6fd3  .........
	defb 007h,080h,080h,088h,080h,080h,080h,080h,080h	; 6fdc  .........
	defb 000h	; 6fe5

; ----------------------------------------------------------------------
; DATOS tabla_6FE6: 4 valores; los indexa 0x553B con `and 006h / rra`
;   0x6fe6..0x6fea  (4 bytes)
DATA_tabla_6FE6:
	defb 020h,05ch,048h,034h	; 6fe6

; ----------------------------------------------------------------------
; DATOS lista_6FEA: 60 bytes; la recorre 0x552A con bc=0x060A
;   0x6fea..0x7026  (60 bytes)
DATA_lista_6FEA:
	defb 0e4h,0e4h,090h,091h,092h,0e4h,0e0h,098h,099h,09ah,09bh,09ch,0e1h,093h,094h,095h	; 6fea  ................
	defb 096h,097h,0e5h,052h,053h,0e5h,052h,053h,0e0h,040h,041h,0e0h,040h,041h,0e0h,040h	; 6ffa  ...RS.RS.@A.@A.@
	defb 041h,0e0h,040h,041h,0e2h,09dh,09eh,0e2h,09dh,09eh,0e0h,042h,043h,044h,045h,046h	; 700a  A.@A.......BCDEF
	defb 0e0h,047h,048h,049h,04ah,04bh,0e1h,0e1h,04fh,050h,051h,0e1h	; 701a  .GHIJK..OPQ.

; ----------------------------------------------------------------------
; DATOS lista_7026: 48 bytes del mismo formato; la recorre 0x5532 con c=8
;   0x7026..0x7056  (48 bytes)
DATA_lista_7026:
	defb 0e4h,0e4h,090h,091h,092h,0e4h,0e0h,098h,099h,09ah,09bh,09ch,0e1h,093h,094h,095h	; 7026  ................
	defb 096h,097h,0e5h,052h,053h,0e5h,052h,053h,0e0h,040h,041h,0e0h,040h,041h,0e0h,042h	; 7036  ...RS.RS.@A.@A.B
	defb 043h,044h,045h,046h,0e2h,09fh,0a0h,0a1h,0a2h,0a3h,0e0h,0e0h,04ch,04dh,04eh,0e0h	; 7046  CDEF........LMN.

; ----------------------------------------------------------------------
; DATOS bloque_7056: 243 bytes -> 256 en VRAM. Lo carga 0x6005 con DE=0x2D00
;   0x7056..0x7149  (243 bytes)
DATA_bloque_7056:
	defb 0b0h,01eh,07fh,03fh,01fh,05eh,07fh,0feh,0dfh,040h,080h,0c0h,0c0h,060h,060h,0e2h	; 7056  ...?.^...@...``.
	defb 0f1h,03fh,077h,00fh,00fh,01eh,01ch,031h,020h,0fdh,0feh,0ffh,0ffh,0ffh,01eh,007h	; 7066  .?w....1 .......
	defb 08eh,000h,001h,000h,000h,001h,001h,003h,003h,079h,0feh,0ffh,07fh,079h,0fdh,0fbh	; 7076  .........y...y..
	defb 07fh,004h,000h,086h,080h,098h,084h,0c4h,000h,001h,006h,000h,0a0h,0ffh,0dfh,03fh	; 7086  ...............?
	defb 02fh,077h,067h,041h,023h,0f4h,0f8h,0fch,0fch,0fch,07ch,038h,074h,001h,007h,003h	; 7096  /wgA#.....|8t...
	defb 001h,005h,007h,00fh,00dh,0e4h,0f8h,0fch,0fch,0e6h,0f6h,0eeh,0ffh,005h,000h,095h	; 70a6  ................
	defb 060h,010h,010h,003h,007h,000h,000h,001h,001h,001h,000h,0ffh,07fh,0ffh,0bfh,0dfh	; 70b6  `...............
	defb 09dh,004h,08dh,0d0h,0e0h,004h,0f0h,092h,0e0h,0d0h,007h,01fh,00fh,007h,017h,01fh	; 70c6  ................
	defb 03fh,037h,090h,0e0h,0f0h,0f0h,098h,0d8h,0b8h,0fch,006h,000h,08ah,080h,040h,00fh	; 70d6  ?7............@.
	defb 01dh,003h,003h,007h,007h,00ch,008h,004h,0ffh,0bch,0bfh,007h,041h,023h,040h,080h	; 70e6  ............A#@.
	defb 0c0h,0c0h,0c0h,080h,0c0h,080h,000h,01eh,07fh,03fh,01fh,05eh,07fh,0feh,000h,040h	; 70f6  .........?.^...@
	defb 080h,0c0h,0c0h,060h,060h,0e6h,0dfh,03fh,077h,007h,007h,00bh,00dh,01bh,0f1h,0f9h	; 7106  ...``..?w.......
	defb 0fdh,0feh,0ffh,0ffh,0dfh,087h,000h,000h,001h,000h,000h,001h,001h,003h,000h,079h	; 7116  ...............y
	defb 0feh,0ffh,07fh,079h,0fdh,0fbh,005h,000h,086h,080h,080h,098h,003h,000h,001h,005h	; 7126  ...y............
	defb 000h,090h,07fh,0ffh,0dfh,01fh,01fh,02fh,036h,06dh,0c4h,0e4h,0f4h,0f8h,0fch,07ch	; 7136  ......./6m.....|
	defb 01ch,0b8h,000h	; 7146

; ======================================================================
; CODIGO 0x7149..0x7155  (12 bytes)
; ======================================================================


L_7149:
	ld hl,07155h		;7149
	call L_6A42		;714c
	ld de,01200h		;714f
	jp vuelca_patrones_repetidos		;7152

; ----------------------------------------------------------------------
; DATOS escena_7155: 73 bytes, 2 trozos; la monta 0x7149
;   0x7155..0x719e  (73 bytes)
DATA_escena_7155:
	defb 008h,000h,098h,017h,01fh,007h,00fh,00fh,03fh,06fh,0ceh,0feh,0ffh,0feh,0ffh,0ffh	; 7155  ........?o......
	defb 0ffh,0ffh,0ffh,080h,000h,000h,000h,000h,0c0h,060h,030h,000h,004h,000h,006h,040h	; 7165  .........`0....@
	defb 0ffh,0eeh,000h,000h,008h,000h,098h,09ch,0bch,0bch,07eh,03fh,01fh,00fh,003h,0ffh	; 7175  ..........~?....
	defb 0ffh,0ffh,0ffh,0ffh,0bfh,0ffh,0fch,090h,0d0h,0d0h,0e0h,0c0h,080h,000h,000h,000h	; 7185  ................
	defb 004h,000h,006h,04eh,0ffh,0eeh,000h,000h,000h	; 7195  ...N.....

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_719E: 2 patrones, 14 veces cada uno; sigue a la
;   escena de 0x7155
;   0x719e..0x71b1  (19 bytes)
DATA_patrones_repetidos_719E:
	defb 00eh,080h,080h,080h,040h,048h,0d0h,0d0h,0d0h	; 719e  ....@H...
	defb 00eh,0d0h,0d0h,0d0h,0d0h,0d0h,0d0h,0d0h,0d0h	; 71a7  .........
	defb 000h	; 71b0

; ----------------------------------------------------------------------
; DATOS rectangulos_tabla_71B1: 4 punteros; la usa 0x53B8 con bc=0x0204
;   0x71b1..0x71b9  (8 bytes)
DATA_rectangulos_tabla_71B1:
	defw 071d1h,071c9h,071c1h,071b9h	; 71b1  -> 0x71d1 0x71c9 0x71c1 DATA_rectangulos_71B9

; ----------------------------------------------------------------------
; DATOS rectangulos_71B9: cuatro rectangulos de 2x4 tiles, 8 bytes cada uno
;   0x71b9..0x71d9  (32 bytes)
DATA_rectangulos_71B9:
	defb 040h,041h,042h,043h	; 71b9
	defb 04eh,04fh,050h,051h	; 71bd
	defb 044h,045h,046h,047h	; 71c1
	defb 052h,053h,054h,055h	; 71c5
	defb 048h,049h,04ah,040h	; 71c9
	defb 056h,057h,058h,04eh	; 71cd
	defb 04bh,04ch,04dh,040h	; 71d1
	defb 059h,05ah,05bh,04eh	; 71d5

; ======================================================================
; CODIGO 0x71d9..0x71eb  (18 bytes)
; ======================================================================


L_71D9:
	ld hl,071ebh		;71d9
	call L_6A42		;71dc
	ld de,01400h		;71df
	call vuelca_patrones_repetidos		;71e2
	ld hl,0728fh		;71e5
	jp descomprime		;71e8

; ----------------------------------------------------------------------
; DATOS escena_71EB: 68 bytes, 3 trozos; la monta 0x71D9
;   0x71eb..0x722f  (68 bytes)
DATA_escena_71EB:
	defb 00ch,000h,087h,001h,003h,003h,007h,007h,01fh,07fh,005h,0ffh,000h,005h,099h,006h	; 71eb  ................
	defb 080h,0fbh,0ddh,0e0h,000h,000h,008h,000h,084h,007h,003h,003h,001h,004h,000h,005h	; 71fb  ................
	defb 0ffh,083h,07fh,01fh,007h,000h,005h,099h,006h,090h,07bh,0ddh,0e0h,000h,000h,008h	; 720b  ..........{.....
	defb 000h,001h,007h,006h,00fh,001h,007h,008h,0ffh,000h,005h,099h,006h,09fh,0eah,055h	; 721b  ...............U
	defb 020h,000h,000h,000h	; 722b

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_722F: 2 patrones, 31 y 10 veces
;   0x722f..0x7242  (19 bytes)
DATA_patrones_repetidos_722F:
	defb 01fh,0d0h,0d0h,0d0h,0d0h,0d0h,0d0h,0d0h,0d0h	; 722f  .........
	defb 00ah,0d0h,0d0h,0d0h,0d0h,0d8h,0d0h,0d0h,0d0h	; 7238  .........
	defb 000h	; 7241

; ----------------------------------------------------------------------
; DATOS rectangulos_tabla_7242: 4 punteros; la usa 0x5887 con bc=0x0305
;   0x7242..0x724a  (8 bytes)
DATA_rectangulos_tabla_7242:
	defw 07262h,07253h,07280h,07271h	; 7242  -> 0x7262 DATA_rectangulos_7253 0x7280 0x7271

; ----------------------------------------------------------------------
; DATOS rectangulo_724A: 3x3 tiles; lo pinta 0x5819 llamando a L_53C8
;   directamente
;   0x724a..0x7253  (9 bytes)
DATA_rectangulo_724A:
	defb 089h,08ah,08bh	; 724a
	defb 0a5h,0a1h,0a6h	; 724d
	defb 098h,099h,09ah	; 7250

; ----------------------------------------------------------------------
; DATOS rectangulos_7253: cuatro rectangulos de 3x5 tiles, 15 bytes cada uno
;   0x7253..0x728f  (60 bytes)
DATA_rectangulos_7253:
	defb 081h,082h,083h,084h,080h	; 7253
	defb 0a0h,0a1h,0a1h,0a2h,09fh	; 7258
	defb 090h,091h,092h,093h,080h	; 725d
	defb 085h,086h,087h,088h,080h	; 7262
	defb 0a3h,0a1h,0a1h,0a4h,09fh	; 7267
	defb 094h,095h,096h,097h,080h	; 726c
	defb 080h,089h,08ah,08bh,080h	; 7271
	defb 09fh,0a5h,0a1h,0a6h,09fh	; 7276
	defb 080h,098h,099h,09ah,080h	; 727b
	defb 08ch,08dh,08eh,08fh,080h	; 7280
	defb 0a7h,0a1h,0a1h,0a8h,09fh	; 7285
	defb 09bh,09ch,09dh,09eh,080h	; 728a

; ----------------------------------------------------------------------
; DATOS bloque_728F: 67 bytes -> 96 en VRAM, 2 tramos (0x3580 y 0x1580). Lo
;   carga 0x71E5
;   0x728f..0x72d2  (67 bytes)
DATA_bloque_728F:
	defb 080h,075h,083h,007h,01fh,07fh,004h,0ffh,0a2h,0dfh,0e0h,0f8h,0feh,0ffh,03fh,00fh	; 728f  .u............?.
	defb 007h,00fh,08fh,087h,003h,007h,0ffh,0ffh,0fdh,0f8h,01fh,0bfh,0ffh,0ffh,0e0h,0c0h	; 729f  ................
	defb 0e1h,0f1h,0f0h,0e0h,0f0h,0fch,0ffh,07fh,01fh,007h,0fbh,004h,0ffh,083h,0feh,0f8h	; 72af  ................
	defb 0e0h,080h,080h,055h,004h,0d0h,004h,0d3h,004h,0d0h,018h,0d3h,004h,0d0h,004h,0d3h	; 72bf  ...U............
	defb 004h,0d0h,000h	; 72cf

; ----------------------------------------------------------------------
; DATOS rectangulo_72D2: 3x5 tiles; lo pinta 0x5899
;   0x72d2..0x72e1  (15 bytes)
DATA_rectangulo_72D2:
	defb 081h,0b0h,0b1h,084h,080h	; 72d2
	defb 0a0h,0b2h,0b3h,0a2h,09fh	; 72d7
	defb 090h,0b4h,0b5h,093h,080h	; 72dc

; ======================================================================
; CODIGO 0x72e1..0x72ed  (12 bytes)
; ======================================================================


L_72E1:
	ld hl,072edh		;72e1
	call L_6A42		;72e4
	ld de,01680h		;72e7
	jp vuelca_patrones_repetidos		;72ea

; ----------------------------------------------------------------------
; DATOS escena_72ED: 72 bytes, 3 trozos; la monta 0x72E1
;   0x72ed..0x7335  (72 bytes)
DATA_escena_72ED:
	defb 008h,000h,090h,000h,00fh,07fh,0ffh,07fh,00fh,080h,0f0h,0ffh,0ffh,0ffh,0ffh,0ffh	; 72ed  ................
	defb 0ffh,0ffh,000h,000h,004h,051h,006h,0d0h,0ddh,09bh,000h,0dbh,022h,064h,000h,000h	; 72fd  .....Q......"d..
	defb 008h,000h,008h,0ffh,001h,000h,007h,0ffh,000h,004h,051h,006h,0e0h,0efh,0ffh,000h	; 730d  ..........Q.....
	defb 000h,008h,000h,088h,0ffh,0ffh,0ffh,0ffh,0ffh,07fh,00fh,000h,008h,0ffh,000h,004h	; 731d  ................
	defb 051h,006h,0efh,05fh,0ffh,000h,000h,000h	; 732d  Q.._....

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_7335: 4 patrones: 11, 5, 15 y 14 veces
;   0x7335..0x735a  (37 bytes)
DATA_patrones_repetidos_7335:
	defb 00bh,0a0h,0a0h,0a0h,0a0h,0a0h,0a0h,040h,040h	; 7335  .......@@
	defb 005h,0a0h,0a0h,0a0h,0a0h,0a0h,0a0h,0a0h,0a0h	; 733e  .........
	defb 00fh,040h,040h,040h,040h,048h,040h,040h,040h	; 7347  .@@@@H@@@
	defb 00eh,040h,040h,040h,040h,040h,040h,040h,040h	; 7350  .@@@@@@@@
	defb 000h	; 7359

; ----------------------------------------------------------------------
; DATOS rectangulos_tabla_735A: 4 punteros; la usan 0x5660 y 0x5F39 con
;   bc=0x0307
;   0x735a..0x7362  (8 bytes)
DATA_rectangulos_tabla_735A:
	defw 073a1h,0738ch,07377h,07362h	; 735a  -> 0x73a1 0x738c 0x7377 DATA_rectangulos_7362

; ----------------------------------------------------------------------
; DATOS rectangulos_7362: cuatro rectangulos de 3x7 tiles, 21 bytes cada uno
;   0x7362..0x73b6  (84 bytes)
DATA_rectangulos_7362:
	defb 0d0h,0d1h,0dbh,0dbh,0dbh,0d2h,0d0h	; 7362
	defb 0e0h,0e1h,0e2h,0e2h,0e2h,0e1h,0e0h	; 7369
	defb 0d0h,0efh,0e1h,0e1h,0e1h,0f0h,0d0h	; 7370
	defb 0d3h,0d4h,0dbh,0dbh,0dch,0d5h,0d0h	; 7377
	defb 0e3h,0e4h,0e2h,0e2h,0e5h,0e6h,0e0h	; 737e
	defb 0f1h,0f2h,0e1h,0e1h,0f3h,0f4h,0d0h	; 7385
	defb 0d6h,0ddh,0dbh,0dbh,0deh,0d7h,0d0h	; 738c
	defb 0e7h,0e8h,0e2h,0e2h,0e9h,0eah,0e0h	; 7393
	defb 0f5h,0f6h,0e1h,0e1h,0f7h,0f8h,0d0h	; 739a
	defb 0d8h,0dfh,0dbh,0dbh,0d9h,0dah,0d0h	; 73a1
	defb 0ebh,0ech,0e2h,0e2h,0edh,0eeh,0e0h	; 73a8
	defb 0f9h,0fah,0e1h,0e1h,0fbh,0fch,0d0h	; 73af

; ======================================================================
; CODIGO 0x73b6..0x73c2  (12 bytes)
; ======================================================================


L_73B6:
	ld hl,073c2h		;73b6
	call L_6A42		;73b9
	ld de,00e80h		;73bc
	jp vuelca_patrones_repetidos		;73bf

; ----------------------------------------------------------------------
; DATOS escena_73C2: 49 bytes, 3 trozos; la monta 0x73B6
;   0x73c2..0x73f3  (49 bytes)
DATA_escena_73C2:
	defb 00ch,000h,004h,0ffh,000h,002h,000h,005h,0d0h,0ffh,000h,000h,008h,000h,088h,063h	; 73c2  ...............c
	defb 055h,049h,055h,063h,07fh,063h,055h,000h,002h,000h,005h,0d8h,07fh,000h,000h,008h	; 73d2  UIUc.cU.........
	defb 000h,084h,049h,055h,063h,07fh,002h,0ffh,000h,002h,000h,005h,0dfh,07fh,000h,000h	; 73e2  ..IUc...........
	defb 000h	; 73f2

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_73F3: 3 patrones: 8, 7 y 7 veces
;   0x73f3..0x740f  (28 bytes)
DATA_patrones_repetidos_73F3:
	defb 008h,000h,000h,000h,000h,080h,080h,0a0h,0a0h	; 73f3  .........
	defb 007h,040h,040h,040h,040h,040h,040h,040h,040h	; 73fc  .@@@@@@@@
	defb 007h,040h,040h,040h,040h,088h,088h,0aah,0aah	; 7405  .@@@@....
	defb 000h	; 740e

; ----------------------------------------------------------------------
; DATOS rectangulos_tabla_740F: 4 punteros; la usa 0x5658 con bc=0x0308
;   0x740f..0x7417  (8 bytes)
DATA_rectangulos_tabla_740F:
	defw 0745fh,07447h,0742fh,07417h	; 740f  -> 0x745f 0x7447 0x742f DATA_rectangulos_7417

; ----------------------------------------------------------------------
; DATOS rectangulos_7417: cuatro rectangulos de 3x8 tiles, 24 bytes cada uno
;   0x7417..0x7477  (96 bytes)
DATA_rectangulos_7417:
	defb 0d0h,0d0h,0d1h,0d1h,0d1h,0d1h,0d1h,0d0h	; 7417  ........
	defb 0d0h,0d0h,0d0h,0d0h,0dbh,0dch,0d0h,0d0h	; 741f  ........
	defb 0d0h,0d1h,0d1h,0d1h,0e2h,0e3h,0d1h,0d0h	; 7427  ........
	defb 0d0h,0d2h,0d1h,0d1h,0d1h,0d1h,0d3h,0d0h	; 742f  ........
	defb 0d0h,0d0h,0d0h,0d0h,0ddh,0deh,0d0h,0d0h	; 7437  ........
	defb 0d2h,0d1h,0d1h,0d1h,0e4h,0e5h,0d3h,0d0h	; 743f  ........
	defb 0d0h,0d4h,0d1h,0d1h,0d1h,0d1h,0d5h,0d0h	; 7447  ........
	defb 0d0h,0d0h,0d0h,0d0h,0d8h,0d0h,0d0h,0d0h	; 744f  ........
	defb 0d4h,0d1h,0d1h,0d1h,0dfh,0d1h,0d5h,0d0h	; 7457  ........
	defb 0d0h,0d6h,0d1h,0d1h,0d1h,0d1h,0d7h,0d0h	; 745f  ........
	defb 0d0h,0d0h,0d0h,0d9h,0dah,0d0h,0d0h,0d0h	; 7467  ........
	defb 0d6h,0d1h,0d1h,0e0h,0e1h,0d1h,0d7h,0d0h	; 746f  ........

; ======================================================================
; CODIGO 0x7477..0x7498  (33 bytes)
; ======================================================================


L_7477:
	ld hl,07498h		;7477
	call L_6A42		;747a
	ld de,00ac0h		;747d
	call vuelca_patrones_repetidos		;7480
	ld de,02ac0h		;7483
	ld hl,02bb0h		;7486
	ld bc,002d0h		;7489
	call copia_vram_a_vram		;748c
	ld bc,003c0h		;748f
	ld de,00ac0h		;7492
	jp L_4612		;7495

; ----------------------------------------------------------------------
; DATOS escena_7498: 70 bytes, 2 trozos; la monta 0x7477
;   0x7498..0x74de  (70 bytes)
DATA_escena_7498:
	defb 008h,000h,08ch,000h,077h,077h,077h,000h,03eh,000h,03eh,000h,077h,077h,077h,005h	; 7498  ....www.>.>.www.
	defb 000h,003h,077h,084h,000h,03eh,000h,03eh,000h,004h,000h,005h,058h,0efh,0ffh,000h	; 74a8  ..w..>.>....X...
	defb 000h,008h,000h,098h,000h,03eh,000h,03eh,000h,077h,077h,077h,000h,000h,000h,000h	; 74b8  .....>.>.www....
	defb 000h,077h,077h,077h,000h,03eh,000h,03eh,000h,077h,077h,077h,000h,004h,000h,005h	; 74c8  .www.>.>.www....
	defb 067h,0efh,0ffh,000h,000h,000h	; 74d8

; ----------------------------------------------------------------------
; DATOS patrones_repetidos_74DE: 8 patrones, 15 veces cada uno; sigue a la
;   escena de 0x7498
;   0x74de..0x7527  (73 bytes)
DATA_patrones_repetidos_74DE:
	defb 00fh,000h,0a0h,0a0h,0a0h,000h,070h,000h,070h	; 74de  ......p.p
	defb 00fh,000h,070h,000h,070h,000h,0a0h,0a0h,0a0h	; 74e7  ..p.p....
	defb 00fh,000h,0a0h,0a0h,0a0h,000h,070h,000h,070h	; 74f0  ......p.p
	defb 00fh,000h,078h,000h,070h,000h,0a0h,0a0h,0a0h	; 74f9  ..x.p....
	defb 00fh,000h,0a0h,0a0h,0a0h,000h,070h,000h,070h	; 7502  ......p.p
	defb 00fh,000h,070h,008h,070h,000h,0a0h,0a0h,0a0h	; 750b  ..p.p....
	defb 00fh,000h,0a0h,0a8h,0a0h,000h,070h,000h,070h	; 7514  ......p.p
	defb 00fh,000h,070h,000h,070h,000h,0a0h,0a0h,0a0h	; 751d  ..p.p....
	defb 000h	; 7526

; ----------------------------------------------------------------------
; DATOS indices_7527: 20 valores pequenos
;   0x7527..0x753b  (20 bytes)
DATA_indices_7527:
	defb 00bh,00ch,005h,00dh,00eh,007h,008h,002h,009h,00ah	; 7527  ..........
	defb 003h,004h,005h,005h,006h,000h,001h,002h,001h,000h	; 7531  ..........

; ======================================================================
; CODIGO 0x753b..0x7596  (91 bytes)
; ======================================================================


L_753B:
	ld hl,07596h		;753b
	call descomprime		;753e
	call L_45D1		;7541
	ld hl,07598h		;7544
	ld de,06680h		;7547
	call L_7567		;754a
	ld de,065c0h		;754d
	call L_7567		;7550
	ld a,0f0h		;7553
	ld bc,00480h		;7555
	ld de,00380h		;7558
	call rellena_vram		;755b
	ld bc,00180h		;755e
	ld de,00500h		;7561
	jp L_4612		;7564
L_7567:
	di			;7567
	call prepara_escritura_vram		;7568
L_756B:
	ld a,(hl)			;756b
	inc hl			;756c
	or a			;756d
	ret z			;756e
	ld b,a			;756f
	jp m,L_7580		;7570
	call L_758B		;7573
L_7576:
	out (098h),a		;7576
	push hl			;7578
	pop hl			;7579
	push hl			;757a
	pop hl			;757b
	djnz L_7576		;757c
	jr L_756B		;757e
L_7580:
	res 7,b		;7580
L_7582:
	call L_758B		;7582
	out (098h),a		;7585
	djnz L_7582		;7587
	jr L_756B		;7589
L_758B:
	ld e,008h		;758b
	ld d,(hl)			;758d
	inc hl			;758e
L_758F:
	rl d		;758f
	rra			;7591
	dec e			;7592
	jr nz,L_758F		;7593
	ret			;7595

; ----------------------------------------------------------------------
; DATOS bloque_7596: 194 bytes -> 344 en VRAM (0x23A8). Lo carga 0x753B
;   0x7596..0x7658  (194 bytes)
DATA_bloque_7596:
	defb 0a8h,063h,083h,000h,000h,00fh,005h,000h,001h,0c0h,00dh,000h,082h,001h,00eh,004h	; 7596  .c..............
	defb 000h,083h,007h,038h,0c0h,006h,000h,088h,001h,002h,004h,008h,010h,020h,040h,080h	; 75a6  ...8......... @.
	defb 009h,000h,088h,001h,002h,004h,008h,010h,020h,040h,080h,009h,000h,090h,001h,004h	; 75b6  ........ @......
	defb 008h,010h,020h,040h,080h,080h,000h,002h,004h,008h,010h,020h,040h,080h,047h,000h	; 75c6  .. @....... @.G.
	defb 082h,007h,078h,004h,000h,08fh,007h,078h,080h,000h,000h,000h,003h,03ch,0c0h,000h	; 75d6  ..x....x.....<..
	defb 000h,000h,003h,03ch,0c0h,005h,000h,001h,0e0h,00ch,000h,089h,001h,00eh,000h,000h	; 75e6  ...<............
	defb 000h,000h,001h,01eh,0e0h,004h,000h,082h,00fh,0f0h,004h,000h,082h,00fh,0f0h,006h	; 75f6  ................
	defb 000h,081h,080h,00dh,000h,08dh,007h,038h,000h,000h,000h,007h,018h,0e0h,000h,000h	; 7606  .......8........
	defb 003h,01ch,0e0h,00bh,000h,093h,003h,01ch,000h,000h,000h,001h,00eh,070h,080h,000h	; 7616  .............p..
	defb 001h,00eh,070h,080h,000h,000h,000h,000h,0c0h,00ah,000h,082h,001h,00eh,004h,000h	; 7626  ..p.............
	defb 083h,007h,038h,0c0h,00bh,000h,08ch,003h,000h,000h,001h,006h,018h,020h,0c0h,000h	; 7636  ..8.......... ..
	defb 030h,040h,080h,008h,000h,089h,001h,006h,008h,030h,0c0h,00ch,030h,040h,080h,004h	; 7646  0@.......0..0@..
	defb 000h,000h	; 7656

; ----------------------------------------------------------------------
; DATOS bloque_7658: 148 bytes -> 192 en VRAM; es la segunda mitad de lo que
;   descomprime 0x753B
;   0x7658..0x76ec  (148 bytes)
DATA_bloque_7658:
	defb 004h,000h,089h,001h,002h,00ch,030h,003h,004h,018h,060h,080h,009h,000h,08ch,003h	; 7658  ......0...`.....
	defb 00ch,000h,001h,006h,018h,020h,0c0h,000h,000h,040h,080h,006h,000h,0b3h,001h,002h	; 7668  ..... ...@......
	defb 004h,008h,010h,020h,040h,080h,000h,001h,002h,004h,008h,010h,020h,040h,000h,001h	; 7678  ... @....... @..
	defb 002h,004h,008h,010h,010h,020h,000h,000h,001h,002h,004h,008h,010h,020h,000h,000h	; 7688  ..... ....... ..
	defb 001h,002h,002h,004h,008h,010h,000h,000h,000h,001h,002h,004h,008h,000h,020h,040h	; 7698  .............. @
	defb 080h,005h,000h,002h,020h,003h,040h,003h,080h,003h,001h,002h,002h,003h,004h,003h	; 76a8  .... .@.........
	defb 008h,002h,010h,003h,020h,005h,000h,003h,001h,003h,040h,002h,080h,003h,000h,003h	; 76b8  .... .....@.....
	defb 002h,002h,004h,003h,008h,003h,010h,003h,020h,002h,040h,003h,000h,002h,001h,003h	; 76c8  ........ .@.....
	defb 002h,003h,080h,005h,000h,003h,004h,001h,008h,004h,000h,008h,008h,083h,002h,004h	; 76d8  ................
	defb 008h,005h,000h,000h	; 76e8

; ----------------------------------------------------------------------
; DATOS poses_tabla_1: 11 punteros; la usa 0x5E16 con `ld bc,076ech`
;   0x76ec..0x7702  (22 bytes)
DATA_poses_tabla_1:
	defw 07702h,07712h,07727h,07740h,07760h,0777ch,0778ch,077a8h	; 76ec
	defw 077c8h,077e1h,077f6h	; 76fc

; ----------------------------------------------------------------------
; DATOS poses_guiones_1: los guiones a los que apunta; varios punteros entran
;   a media pose, que es como se reaprovechan
;   0x7702..0x7806  (260 bytes)
DATA_poses_guiones_1:
	defb 000h,000h,000h,000h,088h,089h,08ah,08bh,08ch,0feh,08dh,08eh,08fh,090h,091h,0ffh	; 7702  ................
	defb 000h,000h,000h,000h,000h,092h,093h,094h,091h,0feh,000h,000h,095h,096h,097h,098h	; 7712  ................
	defb 0feh,099h,09ah,08ch,0ffh,000h,000h,000h,000h,000h,09bh,09ch,09dh,0feh,000h,000h	; 7722  ................
	defb 000h,000h,09eh,09fh,0feh,000h,000h,0a0h,0a1h,0feh,0a2h,0a3h,0a4h,0ffh,000h,000h	; 7732  ................
	defb 000h,000h,000h,0a5h,0feh,000h,000h,000h,000h,0a6h,091h,0feh,000h,000h,000h,0a7h	; 7742  ................
	defb 091h,0feh,000h,000h,0a8h,0a4h,0feh,000h,0a9h,0a4h,0feh,0aah,0abh,0ffh,000h,000h	; 7752  ................
	defb 000h,0ach,0feh,000h,000h,0adh,0feh,000h,000h,0aeh,0feh,000h,0afh,0b0h,0feh,000h	; 7762  ................
	defb 0b1h,0feh,000h,0b2h,0feh,0b3h,0b4h,0feh,0b5h,0ffh,0b6h,0feh,0b6h,0feh,0b6h,0feh	; 7772  ................
	defb 0b6h,0feh,0b6h,0feh,0b6h,0feh,0b6h,0feh,0b6h,0ffh,000h,000h,000h,0c4h,0feh,000h	; 7782  ................
	defb 000h,0c5h,0feh,000h,000h,0c6h,0feh,000h,0c7h,0c8h,0feh,000h,0c9h,0feh,000h,0cah	; 7792  ................
	defb 0feh,0cbh,0cch,0feh,0cdh,0ffh,000h,000h,000h,000h,000h,0bdh,0feh,000h,000h,000h	; 77a2  ................
	defb 000h,0beh,0ech,0feh,000h,000h,000h,0bfh,0ech,0feh,000h,000h,0c0h,0bch,0feh,000h	; 77b2  ................
	defb 0c1h,0bch,0feh,0c2h,0c3h,0ffh,000h,000h,000h,000h,000h,0f6h,0f7h,0f8h,0feh,000h	; 77c2  ................
	defb 000h,000h,000h,0f9h,0fah,0feh,000h,000h,0b8h,0b9h,0feh,0bah,0bbh,0bch,0ffh,000h	; 77d2  ................
	defb 000h,000h,000h,000h,0edh,0eeh,0efh,0ech,0feh,000h,000h,0f0h,0f1h,0f2h,0f3h,0feh	; 77e2  ................
	defb 0f4h,0f5h,0e7h,0ffh,000h,000h,000h,000h,0e3h,0e4h,0e5h,0e6h,0e7h,0feh,0e8h,0e9h	; 77f2  ................
	defb 0eah,0ebh,0ech,0ffh	; 7802

; ----------------------------------------------------------------------
; DATOS poses_tabla_2: 11 punteros; la usa 0x5E1D, y 0x561D entra por 0x780E
;   0x7806..0x781c  (22 bytes)
DATA_poses_tabla_2:
	defw 0781ch,07828h,07730h,07835h,07769h,07780h,07795h,07849h	; 7806
	defw 077d1h,0785dh,0786ah	; 7816

; ----------------------------------------------------------------------
; DATOS poses_guiones_2
;   0x781c..0x7876  (90 bytes)
DATA_poses_guiones_2:
	defb 000h,000h,088h,089h,08ah,08bh,08ch,0feh,075h,090h,091h,0ffh,000h,000h,000h,095h	; 781c  ........u.......
	defb 096h,097h,076h,0feh,077h,078h,09ah,08ch,0ffh,000h,000h,000h,079h,07ah,0feh,000h	; 782c  ..v.wx......yz..
	defb 000h,07bh,07ch,0feh,000h,07dh,07eh,0feh,07dh,07fh,0feh,0b7h,0ffh,000h,000h,000h	; 783c  .{|..}~.}.......
	defb 0d4h,0d5h,0feh,000h,000h,0d6h,0d7h,0feh,000h,0d8h,0d9h,0feh,0d8h,0dah,0feh,0cfh	; 784c  ................
	defb 0ffh,000h,000h,000h,0f0h,0f1h,0f2h,0d1h,0feh,0d2h,0d3h,0f5h,0e7h,0ffh,000h,000h	; 785c  ................
	defb 0e3h,0e4h,0e5h,0e6h,0e7h,0feh,0d0h,0ebh,0ech,0ffh	; 786c  ..........

; ----------------------------------------------------------------------
; DATOS poses_tabla_3: 11 punteros; la usan 0x5E37 y 0x5E67
;   0x7876..0x788c  (22 bytes)
DATA_poses_tabla_3:
	defw 0788ch,0789ch,078b3h,078cch,078e7h,0777ch,07905h,07923h	; 7876
	defw 0793eh,07957h,0796eh	; 7886

; ----------------------------------------------------------------------
; DATOS poses_guiones_3
;   0x788c..0x797e  (242 bytes)
DATA_poses_guiones_3:
	defb 0e7h,0e6h,0e5h,0e4h,0e3h,0feh,000h,000h,000h,000h,0ech,0ebh,0eah,0e9h,0e8h,0ffh	; 788c  ................
	defb 0e7h,0efh,0eeh,0edh,0feh,000h,000h,000h,0f3h,0f2h,0f1h,0f0h,0feh,000h,000h,000h	; 789c  ................
	defb 000h,000h,000h,0e7h,0f5h,0f4h,0ffh,0f8h,0f7h,0f6h,0feh,000h,000h,0fah,0f9h,0feh	; 78ac  ................
	defb 000h,000h,000h,000h,0b9h,0b8h,0feh,000h,000h,000h,000h,000h,0bch,0bbh,0bah,0ffh	; 78bc  ................
	defb 0bdh,0feh,0ech,0beh,0feh,000h,0ech,0bfh,0feh,000h,000h,0bch,0c0h,0feh,000h,000h	; 78cc  ................
	defb 000h,0bch,0c1h,0feh,000h,000h,000h,000h,0c3h,0c2h,0ffh,0c4h,0feh,000h,0c5h,0feh	; 78dc  ................
	defb 000h,0c6h,0feh,000h,0c8h,0c7h,0feh,000h,000h,0c9h,0feh,000h,000h,0cah,0feh,000h	; 78ec  ................
	defb 000h,0cch,0cbh,0feh,000h,000h,000h,0cdh,0ffh,0ach,0feh,000h,0adh,0feh,000h,0aeh	; 78fc  ................
	defb 0feh,000h,0b0h,0afh,0feh,000h,000h,0b1h,0feh,000h,000h,0b2h,0feh,000h,000h,0b4h	; 790c  ................
	defb 0b3h,0feh,000h,000h,000h,0b5h,0ffh,0a5h,0feh,091h,0a6h,0feh,000h,091h,0a7h,0feh	; 791c  ................
	defb 000h,000h,0a4h,0a8h,0feh,000h,000h,000h,0a4h,0a9h,0feh,000h,000h,000h,000h,0abh	; 792c  ................
	defb 0aah,0ffh,09dh,09ch,09bh,0feh,000h,000h,09fh,09eh,0feh,000h,000h,000h,000h,0a1h	; 793c  ................
	defb 0a0h,0feh,000h,000h,000h,000h,000h,0a4h,0a3h,0a2h,0ffh,08ch,094h,093h,092h,0feh	; 794c  ................
	defb 000h,000h,000h,098h,097h,096h,095h,0feh,000h,000h,000h,000h,000h,000h,08ch,09ah	; 795c  ................
	defb 099h,0ffh,08ch,08bh,08ah,089h,088h,0feh,000h,000h,000h,000h,091h,090h,08fh,08eh	; 796c  ................
	defb 08dh,0ffh	; 797c

; ----------------------------------------------------------------------
; DATOS poses_tabla_4: 11 punteros; la usan 0x5E3E y 0x5E6E
;   0x797e..0x7994  (22 bytes)
DATA_poses_tabla_4:
	defw 07994h,079a2h,078b7h,079afh,078ech,07780h,0790ah,079c7h	; 797e
	defw 07942h,079dfh,079ech	; 798e

; ----------------------------------------------------------------------
; DATOS poses_guiones_4
;   0x7994..0x79fa  (102 bytes)
DATA_poses_guiones_4:
	defb 0e7h,0e6h,0e5h,0e4h,0e3h,0feh,000h,000h,000h,000h,0ech,0ebh,0d0h,0ffh,0d1h,0f2h	; 7994  ................
	defb 0f1h,0f0h,0feh,000h,000h,000h,0e7h,0f5h,0d3h,0d2h,0ffh,0d5h,0d4h,0feh,000h,0d7h	; 79a4  ................
	defb 0d6h,0feh,000h,000h,0d9h,0d8h,0feh,000h,000h,000h,0dah,0d8h,0feh,000h,000h,000h	; 79b4  ................
	defb 000h,0cfh,0ffh,07ah,079h,0feh,000h,07ch,07bh,0feh,000h,000h,07eh,07dh,0feh,000h	; 79c4  ...zy..|{...~}..
	defb 000h,000h,07fh,07dh,0feh,000h,000h,000h,000h,0b7h,0ffh,076h,097h,096h,095h,0feh	; 79d4  ...}.......v....
	defb 000h,000h,000h,08ch,09ah,078h,077h,0ffh,08ch,08bh,08ah,089h,088h,0feh,000h,000h	; 79e4  .....xw.........
	defb 000h,000h,091h,090h,075h,0ffh	; 79f4

; ======================================================================
; CODIGO 0x79fa..0x7b96  (412 bytes)
; ======================================================================


L_79FA:
	inc hl			;79fa
	ld a,(ix+009h)		;79fb
	inc a			;79fe
	cp (hl)			;79ff
	jp z,L_7AE9		;7a00
	jp m,L_7A07		;7a03
	dec a			;7a06
L_7A07:
	ex af,af'			;7a07
	ld a,(ix+002h)		;7a08
	push bc			;7a0b
	ld d,001h		;7a0c
	call L_7BB8		;7a0e
	pop bc			;7a11
	ex af,af'			;7a12
	ld (ix+009h),a		;7a13
	ret			;7a16
L_7A17:
	ld a,(0e031h)		;7a17
	ld e,a			;7a1a
	ld a,c			;7a1b
	cp 001h		;7a1c
	jr z,L_7A21		;7a1e
	dec a			;7a20
L_7A21:
	rlca			;7a21
	rlca			;7a22
	rlca			;7a23
	dec d			;7a24
	jr z,L_7A2B		;7a25
	cpl			;7a27
	and e			;7a28
	jr L_7A2C		;7a29
L_7A2B:
	or e			;7a2b
L_7A2C:
	set 2,a		;7a2c
	bit 5,a		;7a2e
	jr z,L_7A34		;7a30
	res 2,a		;7a32
L_7A34:
	ld e,a			;7a34
	ld (0e031h),a		;7a35
	ld a,007h		;7a38
	jp 00093h		;7a3a   ; BIOS WRTPSG - Writes data to PSG-register
L_7A3D:
	ld a,(0e031h)		;7a3d
	call L_7A34		;7a40
	ld c,001h		;7a43
	ld ix,0e010h		;7a45
	exx			;7a49
	ld b,003h		;7a4a
	ld de,0000bh		;7a4c
L_7A4F:
	exx			;7a4f
	ld a,(ix+002h)		;7a50
	or a			;7a53
	call nz,L_7A5F		;7a54
	inc c			;7a57
	inc c			;7a58
	exx			;7a59
	add ix,de		;7a5a
	djnz L_7A4F		;7a5c
	ret			;7a5e
L_7A5F:
	bit 6,a		;7a5f
	ld d,001h		;7a61
	call z,L_7A17		;7a63
	ld a,(ix+002h)		;7a66
	or a			;7a69
	jp m,L_7AF9		;7a6a
	dec (ix+000h)		;7a6d
	ret nz			;7a70
L_7A71:
	ld l,(ix+003h)		;7a71
	ld h,(ix+004h)		;7a74
	ld a,(hl)			;7a77
	cp 0feh		;7a78
	jp z,L_79FA		;7a7a
	jr nc,L_7AE9		;7a7d
	bit 7,(ix+002h)		;7a7f
	jp nz,L_7B23		;7a83
	and 0f0h		;7a86
	cp 020h		;7a88
	jr nz,L_7A93		;7a8a
	ld a,(hl)			;7a8c
	and 00fh		;7a8d
	ld (ix+001h),a		;7a8f
	inc hl			;7a92
L_7A93:
	ld a,(hl)			;7a93
	and 0f0h		;7a94
	cp 010h		;7a96
	jr nz,L_7AAC		;7a98
	ld a,006h		;7a9a
	ld a,(hl)			;7a9c
	and 01fh		;7a9d
	ld e,a			;7a9f
	ld a,006h		;7aa0
	call 00093h		;7aa2   ; BIOS WRTPSG - Writes data to PSG-register
	ld d,000h		;7aa5
	call L_7A17		;7aa7
	inc hl			;7aaa
	ld a,(hl)			;7aab
L_7AAC:
	ld b,(ix+002h)		;7aac
	bit 6,b		;7aaf
	jr z,L_7AC4		;7ab1
	ld a,c			;7ab3
	cp 005h		;7ab4
	ld a,(hl)			;7ab6
	jr nz,L_7AC4		;7ab7
	inc hl			;7ab9
	ld (ix+003h),l		;7aba
	ld (ix+004h),h		;7abd
	call L_7ADB		;7ac0
	ret			;7ac3
L_7AC4:
	and 0f0h		;7ac4
	ld b,a			;7ac6
	xor (hl)			;7ac7
	ld d,a			;7ac8
	inc hl			;7ac9
	ld e,(hl)			;7aca
	inc hl			;7acb
	ld (ix+003h),l		;7acc
	ld (ix+004h),h		;7acf
	ex de,hl			;7ad2
	call L_7B8A		;7ad3
	ld a,b			;7ad6
	rrca			;7ad7
	rrca			;7ad8
	rrca			;7ad9
	rrca			;7ada
L_7ADB:
	ld h,a			;7adb
	ld a,(ix+001h)		;7adc
	ld (ix+000h),a		;7adf
	add a,003h		;7ae2
	ld (ix+008h),a		;7ae4
	jr L_7B1B		;7ae7
L_7AE9:
	xor a			;7ae9
	ld (ix+009h),a		;7aea
	ld d,001h		;7aed
	call L_7A17		;7aef
	xor a			;7af2
	ld (ix+002h),a		;7af3
	ld h,a			;7af6
	jr L_7B1B		;7af7
L_7AF9:
	dec (ix+000h)		;7af9
	jp z,L_7A71		;7afc
	dec (ix+008h)		;7aff
	ld a,(ix+008h)		;7b02
	cp (ix+000h)		;7b05
	jr nz,L_7B0F		;7b08
	cp 003h		;7b0a
	jr c,L_7B12		;7b0c
	ret			;7b0e
L_7B0F:
	dec (ix+008h)		;7b0f
L_7B12:
	ld a,(ix+007h)		;7b12
	dec a			;7b15
	ret m			;7b16
	ld (ix+007h),a		;7b17
	ld h,a			;7b1a
L_7B1B:
	ld a,c			;7b1b
	rrca			;7b1c
	add a,088h		;7b1d
	ld e,h			;7b1f
	jp 00093h		;7b20   ; BIOS WRTPSG - Writes data to PSG-register
L_7B23:
	and 0f0h		;7b23
	cp 0d0h		;7b25
	ld a,(hl)			;7b27
	jr nz,L_7B31		;7b28
	and 00fh		;7b2a
	ld (ix+00ah),a		;7b2c
	inc hl			;7b2f
	ld a,(hl)			;7b30
L_7B31:
	cp 0f0h		;7b31
	jr c,L_7B3C		;7b33
	and 00fh		;7b35
	ld (ix+006h),a		;7b37
	inc hl			;7b3a
	ld a,(hl)			;7b3b
L_7B3C:
	cp 0e0h		;7b3c
	jr c,L_7B47		;7b3e
	and 00fh		;7b40
	ld (ix+005h),a		;7b42
	inc hl			;7b45
	ld a,(hl)			;7b46
L_7B47:
	and 00fh		;7b47
	ld b,a			;7b49
	ld a,(ix+00ah)		;7b4a
	jr z,L_7B54		;7b4d
L_7B4F:
	add a,(ix+00ah)		;7b4f
	djnz L_7B4F		;7b52
L_7B54:
	ld (ix+001h),a		;7b54
	ld a,(hl)			;7b57
	inc hl			;7b58
	ld (ix+003h),l		;7b59
	ld (ix+004h),h		;7b5c
	and 0f0h		;7b5f
	rrca			;7b61
	rrca			;7b62
	rrca			;7b63
	rrca			;7b64
	ld b,a			;7b65
	sub 00ch		;7b66
	ld (ix+007h),a		;7b68
	jr z,L_7B73		;7b6b
	ld a,(ix+006h)		;7b6d
	ld (ix+007h),a		;7b70
L_7B73:
	call L_7ADB		;7b73
	ld a,b			;7b76
	ld hl,07b96h		;7b77
	call suma_a_a_hl		;7b7a
	ld l,(hl)			;7b7d
	ld h,000h		;7b7e
	ld a,(ix+005h)		;7b80
	or a			;7b83
	jr z,L_7B8A		;7b84
	ld b,a			;7b86
L_7B87:
	add hl,hl			;7b87
	djnz L_7B87		;7b88
L_7B8A:
	ld a,c			;7b8a
	ld e,h			;7b8b
	call 00093h		;7b8c   ; BIOS WRTPSG - Writes data to PSG-register
	ld a,c			;7b8f
	dec a			;7b90
	ld e,l			;7b91
	call 00093h		;7b92   ; BIOS WRTPSG - Writes data to PSG-register
	ret			;7b95

; ----------------------------------------------------------------------
; DATOS escala_cromatica: los doce periodos del PSG; 0x7B77 los baja de octava
;   con `add hl,hl`
;   0x7b96..0x7ba2  (12 bytes)
DATA_escala_cromatica:
	defb 06ah,064h,05fh,059h,054h,050h,04bh,047h,043h,03fh,03ch,038h	; 7b96  jd_YTPKGC?<8

; ======================================================================
; CODIGO 0x7ba2..0x7c19  (119 bytes)
; ======================================================================


L_7BA2:
	di			;7ba2
	ld d,000h		;7ba3
	cp 011h		;7ba5
	jr nz,L_7BB3		;7ba7
	call L_7BB8		;7ba9
	ld a,052h		;7bac
	call L_7BB8		;7bae
	ld a,053h		;7bb1
L_7BB3:
	call L_7BB8		;7bb3
	ei			;7bb6
	ret			;7bb7
L_7BB8:
	ld c,a			;7bb8
	ld b,002h		;7bb9
	ld hl,0e012h		;7bbb
	cp 089h		;7bbe
	jr c,L_7BC9		;7bc0
	cp 091h		;7bc2
	jr c,L_7BDB		;7bc4
	inc b			;7bc6
	jr L_7BDE		;7bc7
L_7BC9:
	and 03fh		;7bc9
	dec b			;7bcb
	cp 006h		;7bcc
	jr z,L_7BDB		;7bce
	cp 012h		;7bd0
	jr c,L_7BDE		;7bd2
	jr z,L_7BDB		;7bd4
	ld hl,0e028h		;7bd6
	jr L_7BDE		;7bd9
L_7BDB:
	ld hl,0e01dh		;7bdb
L_7BDE:
	dec d			;7bde
	push af			;7bdf
	jr z,L_7BEE		;7be0
	ld e,(hl)			;7be2
	ld a,e			;7be3
	and 03fh		;7be4
	ld (hl),a			;7be6
	ld a,c			;7be7
	and 03fh		;7be8
	cp (hl)			;7bea
	ld (hl),e			;7beb
	jr c,$+45		;7bec
L_7BEE:
	and 03fh		;7bee
	add a,a			;7bf0
	ld de,07c19h		;7bf1
	call suma_a_a_de		;7bf4
	dec hl			;7bf7
	dec hl			;7bf8
L_7BF9:
	ld (hl),001h		;7bf9
	inc hl			;7bfb
	ld (hl),001h		;7bfc
	inc hl			;7bfe
	ld (hl),c			;7bff
	inc hl			;7c00
	ld a,(de)			;7c01
	ld (hl),a			;7c02
	inc hl			;7c03
	inc de			;7c04
	ld a,(de)			;7c05
	ld (hl),a			;7c06
	ld a,005h		;7c07
	add a,l			;7c09
	ld l,a			;7c0a
	ld (hl),000h		;7c0b
	inc hl			;7c0d
	pop af			;7c0e
	jr z,L_7C14		;7c0f
	ex af,af'			;7c11
	ld (hl),a			;7c12
	ex af,af'			;7c13
L_7C14:
	push af			;7c14
	inc hl			;7c15
	inc de			;7c16
	djnz L_7BF9		;7c17

; ----------------------------------------------------------------------
; DATOS tabla_de_sonidos: 23 punteros indexados por el numero de sonido; la
;   primera apunta a RAM (0xC9F1) y tres repiten 0x7D91
;   0x7c19..0x7c47  (46 bytes)
DATA_tabla_de_sonidos:
	defw 0c9f1h,07cb5h,07c83h,07c71h,07cd3h,07ca4h,07cafh,07c47h	; 7c19
	defw 07c94h,07d12h,07d92h,07dfbh,07e82h,07f03h,07f5bh,07fd1h	; 7c29
	defw 07fe7h,07cdfh,07d01h,07d0dh,07d91h,07d91h,07d91h	; 7c39

; ----------------------------------------------------------------------
; DATOS partituras: los 22 sonidos a los que apunta la tabla, de 0x7C47 a
;   0x7FE7
;   0x7c47..0x7ff4  (941 bytes)
DATA_partituras:
	defb 021h,0c0h,040h,0c0h,043h,0c0h,045h,0c0h,055h,0c0h,055h,0c0h,05ah,0c0h,060h,0c0h	; 7c47  !.@.C.E.U.U.Z.`.
	defb 065h,0c0h,06ah,0c0h,070h,0c0h,078h,0c0h,080h,0c0h,088h,0c0h,090h,0c0h,098h,0c0h	; 7c57  e.j.p.x.........
	defb 0a0h,0c0h,0aah,0c0h,0b5h,0c0h,0c0h,0c0h,0d0h,0ffh,021h,0d0h,0d0h,0d0h,0c0h,0d0h	; 7c67  ..........!.....
	defb 0b0h,0d0h,098h,0d0h,088h,0d0h,078h,0c0h,06ch,0b0h,058h,0ffh,023h,0d0h,07fh,0b0h	; 7c77  ......x.l.X.#...
	defb 071h,0d0h,07fh,0b0h,064h,0b0h,056h,021h,0b0h,050h,0a0h,04bh,0ffh,023h,018h,0f2h	; 7c87  q...d.V!.P.K.#..
	defb 050h,000h,000h,022h,01fh,0f1h,0f0h,02fh,000h,000h,000h,000h,0ffh,024h,0b0h,08eh	; 7c97  P..".../.....$..
	defb 0c0h,06ah,0c0h,054h,0c0h,047h,0feh,002h,021h,0d0h,059h,0c0h,06ah,0ffh,021h,0e1h	; 7ca7  .j.T.G..!.Y.j.!.
	defb 070h,0d1h,050h,0e1h,050h,0d1h,078h,0c1h,070h,0c1h,058h,0a1h,070h,091h,070h,0a1h	; 7cb7  p.P.P.x.p.X.p.p.
	defb 060h,091h,048h,0b1h,038h,0a1h,04bh,091h,02bh,081h,028h,0ffh,023h,0e0h,088h,0d0h	; 7cc7  `.H.8.K.+.(.#...
	defb 078h,0e0h,06bh,0d0h,05bh,0d0h,04bh,0ffh,024h,000h,000h,026h,090h,021h,090h,020h	; 7cd7  x.k.[.K.$..&.!. 
	defb 090h,021h,090h,020h,02fh,000h,000h,000h,000h,026h,090h,021h,090h,020h,090h,021h	; 7ce7  .!. /....&.!. .!
	defb 090h,020h,02fh,000h,000h,000h,000h,000h,000h,0ffh,023h,014h,0a1h,070h,000h,000h	; 7cf7  . /.......#..p..
	defb 0a1h,098h,000h,000h,0feh,00ah,02fh,014h,00bh,0feh,008h,0fch,0e2h,0b0h,0e1h,010h	; 7d07  ....../.........
	defb 021h,021h,020h,010h,020h,040h,061h,061h,060h,050h,060h,070h,091h,091h,090h,080h	; 7d17  !! . @aa`P`p....
	defb 090h,0e0h,020h,0e1h,095h,061h,071h,070h,060h,041h,071h,061h,060h,040h,021h,061h	; 7d27  .. ..aqp`Aqa`@!a
	defb 041h,0e2h,0b1h,0e1h,011h,021h,043h,0c1h,0e2h,0b0h,0e1h,010h,021h,021h,020h,010h	; 7d37  A....!C.....!! .
	defb 020h,040h,061h,061h,060h,050h,060h,070h,091h,091h,090h,080h,090h,0e0h,020h,0e1h	; 7d47   @aa`P`p...... .
	defb 095h,021h,0b1h,091h,071h,061h,041h,021h,011h,021h,041h,060h,070h,061h,041h,021h	; 7d57  .!..qaA!.!A`paA!
	defb 0e2h,090h,0b0h,0e1h,010h,020h,040h,060h,071h,071h,071h,071h,070h,060h,073h,081h	; 7d67  ..... @`qqqqp`s.
	defb 091h,091h,090h,070h,060h,070h,095h,091h,0b1h,0b1h,0e0h,022h,0e1h,0b0h,091h,091h	; 7d77  ...p`p....."....
	defb 090h,070h,061h,071h,071h,011h,041h,021h,021h,021h,0ffh,0fch,0e2h,0c1h,021h,091h	; 7d87  .paqq.A!!!....!.
	defb 021h,091h,021h,091h,021h,091h,021h,091h,021h,091h,021h,091h,021h,091h,011h,091h	; 7d97  !.!.!.!.!.!.!...
	defb 021h,091h,021h,091h,021h,091h,0e3h,0b1h,0e2h,081h,041h,081h,0e3h,091h,0e2h,071h	; 7da7  !.!.!.....A....q
	defb 061h,041h,021h,091h,021h,091h,021h,091h,021h,091h,021h,091h,021h,091h,021h,091h	; 7db7  aA!.!.!.!.!.!.!.
	defb 021h,021h,071h,061h,041h,021h,011h,0e3h,0b1h,091h,061h,073h,091h,0e2h,071h,061h	; 7dc7  !!qaA!....as..qa
	defb 0c5h,011h,091h,021h,091h,011h,091h,021h,091h,021h,091h,021h,091h,021h,091h,021h	; 7dd7  ...!...!.!.!.!.!
	defb 091h,0e3h,071h,0e2h,0b1h,021h,0b1h,021h,091h,0c1h,091h,011h,091h,0c1h,091h,091h	; 7de7  ..q..!.!........
	defb 091h,091h,0feh,0ffh,0fch,0e0h,011h,021h,041h,021h,072h,020h,0e1h,0b1h,071h,0b1h	; 7df7  .......!A!r ..q.
	defb 091h,081h,091h,0e0h,045h,041h,061h,051h,041h,031h,021h,010h,020h,041h,001h,0e1h	; 7e07  ....EAaQA1!. A..
	defb 0b1h,0a1h,0b1h,0e0h,041h,027h,011h,021h,041h,021h,072h,020h,0e1h,0b1h,071h,0b1h	; 7e17  ....A'.!A!r ..q.
	defb 091h,081h,091h,0e0h,045h,041h,061h,051h,041h,031h,021h,001h,0e1h,0b1h,091h,07bh	; 7e27  ....EAaQA1!....{
	defb 070h,050h,030h,020h,043h,072h,070h,0e0h,071h,001h,0e1h,071h,041h,091h,071h,051h	; 7e37  pP0 Crp.q..qA.qQ
	defb 040h,058h,023h,052h,050h,0e0h,021h,0e1h,0b1h,091h,051h,041h,051h,061h,090h,074h	; 7e47  @X#RP.!...QAQa.t
	defb 070h,050h,040h,020h,043h,072h,070h,0e0h,071h,051h,041h,011h,041h,021h,011h,020h	; 7e57  pP@ Crp.qQA.A!. 
	defb 0e1h,096h,0b1h,0e0h,021h,001h,0e1h,0b1h,0e0h,001h,041h,021h,001h,0e1h,0b0h,0e0h	; 7e67  ....!.....A!....
	defb 008h,0e1h,0b0h,090h,080h,091h,0a0h,0b0h,0e0h,000h,0ffh,0fch,0e2h,0a1h,0b1h,0e1h	; 7e77  ................
	defb 001h,0e2h,0b1h,0b2h,0b0h,071h,021h,071h,071h,071h,071h,075h,071h,061h,061h,061h	; 7e87  .....q!qqqquqaaa
	defb 061h,061h,050h,060h,071h,041h,071h,061h,071h,0e1h,001h,0e2h,0b7h,0a1h,0b1h,0e1h	; 7e97  aaP`qAqaq.......
	defb 001h,0e2h,0b1h,0b2h,0b0h,071h,021h,0e2h,071h,071h,071h,071h,075h,071h,061h,061h	; 7ea7  .....q!.qqqquqaa
	defb 061h,061h,061h,091h,071h,061h,0bbh,070h,050h,040h,020h,003h,042h,040h,0e1h,001h	; 7eb7  aaa.qa.pP@ .B@..
	defb 0e2h,071h,041h,001h,051h,041h,021h,010h,028h,0e3h,0b3h,0e2h,022h,020h,0b1h,071h	; 7ec7  .qA.QA!.(..." .q
	defb 051h,021h,001h,021h,031h,060h,044h,070h,050h,040h,020h,003h,042h,040h,0e1h,041h	; 7ed7  Q!.!1`DpP@ .B@.A
	defb 021h,011h,0e2h,071h,051h,051h,051h,050h,066h,061h,041h,041h,041h,041h,051h,051h	; 7ee7  !..qQQQPfaAAAAQQ
	defb 051h,050h,048h,070h,060h,050h,061h,070h,080h,090h,0feh,0ffh,0fch,0e1h,0b3h,0a3h	; 7ef7  QPHp`Pap........
	defb 0a7h,083h,0c3h,073h,083h,0a7h,083h,0c3h,003h,013h,037h,013h,0c3h,003h,013h,087h	; 7f07  ...s......7.....
	defb 063h,0c3h,0b3h,0a3h,0a7h,083h,0c3h,073h,083h,0a7h,083h,0c3h,053h,083h,087h,063h	; 7f17  c......s....S..c
	defb 0e0h,057h,033h,037h,013h,0e1h,063h,0c3h,063h,047h,063h,047h,063h,0e0h,03fh,013h	; 7f27  .W37..c.cGcGc.?.
	defb 0e1h,063h,037h,063h,037h,063h,0e0h,01fh,0e1h,0b3h,063h,047h,063h,047h,063h,0e0h	; 7f37  .c7c7c....cGcGc.
	defb 03fh,013h,0e1h,063h,0b3h,0e0h,013h,033h,061h,061h,063h,043h,031h,031h,033h,013h	; 7f47  ?..c...3aacC113.
	defb 0e1h,0b3h,0feh,0ffh,0c7h,0fch,0e2h,083h,0b3h,0b3h,013h,0b3h,0b3h,083h,0b3h,0b3h	; 7f57  ................
	defb 013h,043h,043h,063h,0a3h,0a3h,013h,063h,063h,063h,0a3h,0a3h,013h,0a3h,0a3h,083h	; 7f67  .CCc...ccc......
	defb 0b3h,0b3h,013h,0b3h,0b3h,083h,0b3h,0b3h,023h,083h,083h,033h,063h,063h,0e3h,0b3h	; 7f77  ........#..3cc..
	defb 0e2h,033h,033h,013h,053h,053h,063h,0c7h,013h,063h,063h,0e3h,063h,0e2h,063h,063h	; 7f87  .33.SSc..cc.c.cc
	defb 013h,063h,063h,0e3h,063h,0e2h,063h,063h,0e3h,0b3h,0e2h,033h,033h,0e3h,063h,0e2h	; 7f97  .cc.c.cc...33.c.
	defb 033h,033h,0e3h,0b3h,0e2h,033h,033h,0e3h,063h,0e2h,033h,033h,013h,063h,063h,0e3h	; 7fa7  33...33.c.33.cc.
	defb 063h,0e2h,063h,063h,013h,063h,063h,0e3h,063h,0e2h,063h,063h,0b3h,0a3h,093h,087h	; 7fb7  c.cc.cc.c.cc....
	defb 073h,063h,0e3h,063h,0e2h,063h,0e3h,0b3h,0feh,0ffh,0d4h,0fdh,0e0h,001h,021h,001h	; 7fc7  sc.c.c........!.
	defb 0d6h,0e1h,072h,040h,002h,050h,042h,000h,0e2h,091h,0c1h,0b1h,0c1h,0e1h,003h,0ffh	; 7fd7  ..r@.PB.........
	defb 0d6h,0fbh,0e1h,003h,0e2h,0b3h,093h,073h,051h,0c1h,071h,0c1h,073h	; 7fe7  .......sQ.q.s

; ----------------------------------------------------------------------
; DATOS relleno_final: 12 bytes de 0xFF hasta el final del cartucho
;   0x7ff4..0x8000  (12 bytes)
DATA_relleno_final:
	defb 0ffh,0ffh,0ffh,0ffh,0ffh,0ffh,0ffh,0ffh,0ffh,0ffh,0ffh,0ffh	; 7ff4  ............
