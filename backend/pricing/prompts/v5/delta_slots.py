from __future__ import annotations

import json
from typing import Dict, List


def build_v5_delta_slots_prompt(
    *,
    listing_id: int,
    strategy_name: str,
    room_id: str,
    room_type: str,
    slot_ids: List[str],
    room_slot_narratives: Dict[str, str],
    tier_slot_targets: Dict[str, str],
) -> str:
    """
    V5 delta prompt for ONE room (Spanish): output ONE short work narrative per slot.

    WHY THIS MATTERS:
    Delta is an intermediate artifact that feeds decomposition into priced work items.
    We need tight, factual, one-sentence descriptions of the minimum work to close the gap
    between CURRENT (the target property) and TARGET (the comparable property).
    """
    return f"""
Eres un tecnico de reformas comparando dos estados de una habitacion:
- CURRENT: lo que hay ahora en la vivienda objetivo (segun el PIR).
- TARGET: lo que tiene el comparable seleccionado (segun su PIR).

Tu trabajo es describir, slot por slot, el MINIMO trabajo necesario para que CURRENT
llegue al nivel de TARGET. No mas, no menos.

listing_id: {listing_id}
strategy_name: {strategy_name}
room_id: {room_id}
room_type: {room_type}

QUE BUSCAMOS:
Queremos frases cortas y practicas que un contratista pueda entender.
La idea es cerrar la brecha entre lo que tiene la vivienda y lo que tiene el comparable.
Si el comparable tiene suelo de hormigon pulido y la vivienda tiene terrazo, la frase deberia
describir el cambio de pavimento, no inventar un material ni un estilo que no aparece en TARGET.

Piensa como un aparejador que redacta una medicion: que hay que tocar, que se queda como esta.
Si CURRENT y TARGET describen esencialmente lo mismo (o la diferencia es insignificante), escribe
exactamente "no change".

AVISO IMPORTANTE — RAZONA SOBRE EL TIPO DE HABITACION:
Las narrativas de TARGET pueden proceder de una habitacion DIFERENTE del comparable (por ejemplo,
si el comparable no tiene balcon, las narrativas de TARGET se han tomado de otro tipo de estancia).
Esto es intencionado: te damos el mejor contexto disponible. PERO tu trabajo es razonar si cada
slot tiene sentido para esta habitacion en concreto.

Para cada slot, antes de escribir la frase, preguntate:
"¿Tiene sentido fisico y funcional hacer esto EN UN(A) {room_type}?"

Por ejemplo:
- Instalar aire acondicionado split en un balcon → no tiene sentido → "no change".
- Instalar armario empotrado en un pasillo o recibidor → no es habitual → "no change".
- Fabricar cabecero a medida en un dormitorio individual → es un capricho de diseno, no un
  estandar de mercado → "no change".
- Sustituir pavimento en cualquier estancia → si, tiene sentido → describir el cambio.
- Renovar cableado electrico en cualquier estancia → si, tiene sentido → describir el cambio.

Si el slot describe algo que seria fisicamente absurdo o innecesario para este tipo de habitacion,
escribe "no change". Pero OJO: las elecciones de materiales y acabados del comparable (suelos de
madera, hormigon pulido, baldosa porcelanica, pintura lisa, etc.) SON decisiones legitimas que
debes respetar. No las sustituyas por alternativas genericas. El comparable es tu referencia.

RAZONA SOBRE SI VALE LA PENA — ANTES de escribir cada cambio, preguntate:
"¿Esto arregla un estado genuinamente malo (roto, sucio, anticuado, inseguro)?
¿Mejora la eficiencia energetica (aislamiento, carpinteria, instalaciones)?
¿Es una forma obvia de subir el valor de reventa de la vivienda?"
Si la respuesta a LAS TRES es NO, escribe "no change". Una reforma inteligente no sustituye un
acabado funcional por otro equivalente solo porque el comparable tiene algo distinto — eso es
gastar dinero sin impacto. Recuerda que uno de los objetivos de la reforma es acercar la
calificacion energetica de la vivienda a la del comparable (o mejorarla), asi que valora siempre
los cambios que contribuyan a ello (ventanas, sellado, aislamiento, instalaciones eficientes).

FORMATO DE SALIDA (JSON):
{{"room_id": "{room_id}", "room_type": "{room_type}", "slot_work_narratives": {{"<slot_id>": "<string>"}}}}

COMO ESCRIBIR CADA FRASE:
- Exactamente UNA frase en espanol por slot (maximo ~140 caracteres, ~16 palabras).
- Si no hay cambio, escribe literalmente: "no change" (en ingles, sin comillas extra).
- La frase debe ser concreta y apoyarse solo en lo que dicen CURRENT y TARGET.
  Por ejemplo: si TARGET dice "tarima de madera clara", escribe "Sustituir terrazo por tarima de madera clara."
  Usa el material EXACTO que describe TARGET, no un generico.
- Si el slot describe un CAMBIO DE ACABADO VISIBLE (pavimento, alicatado, pintura, carpinteria visible, griferia/metal),
  incluye siempre un descriptor VISUAL concreto derivado de TARGET (el comparable): tono/color (claro/oscuro o un color si aparece),
  acabado (mate/satinado/pulido), y/o formato/patron (formato grande, damero, etc.) si TARGET lo sugiere.
  WHY THIS MATTERS: el delta alimenta generacion de imagen y, si es vago, la imagen apenas cambia.
- No inventes acabados, materiales ni estilos que no aparezcan en TARGET.
  Si TARGET dice "hormigon pulido", di "hormigon pulido", no "microcemento" ni "resina epoxi".
- Cuando el cambio de un slot implica trabajos auxiliares evidentes (demolicion previa,
  preparacion de soporte, sellado, pruebas), puedes mencionarlos brevemente en la misma frase,
  pero solo si son consecuencia directa del cambio.
- No inventes cambios estructurales (mover tabiques, abrir huecos, convertir ventanas en puertas)
  a menos que CURRENT y TARGET lo digan explicitamente.
- No menciones precios.
- Devuelve SOLO JSON valido.

SLOTS:
{json.dumps(slot_ids, ensure_ascii=False)}

CURRENT (narrativas del PIR de la vivienda):
{json.dumps(room_slot_narratives, ensure_ascii=False)[:8000]}

TARGET (narrativas del PIR del comparable):
{json.dumps(tier_slot_targets, ensure_ascii=False)[:8000]}
""".strip()
