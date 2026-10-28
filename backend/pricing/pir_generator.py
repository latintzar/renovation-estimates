"""
Property Intelligence Report (PIR) Generator
=============================================

V2.0 - 6-Dimension Property Analysis Framework

Generates comprehensive property analysis for target and comparable properties.
Uses canonical room_ids from photo clustering as the single source of truth.

V2 ARCHITECTURE (2026-01-16):
- Bracket-based approach (generate_bracket_pir, synthesize_local_market_context,
  generate_strategic_reasoning) has been REMOVED
- V2 uses data-driven comparable analysis via:
  - strategy_selector.py: Analyzes ALL comparables to identify 3 renovation strategies  
  - delta_scope_generator.py: Calculates delta scope from target to each strategy

6-DIMENSION ANALYSIS FRAMEWORK:
1. Shell & Preparation (Masonry/Plaster) - Wall/ceiling substrates and condition
2. Apertures & Enclosure (Joinery/Glazing) - Windows, shutters, internal doors
3. Systems & Services (MEP) - Electrical, plumbing, HVAC evidence
4. Surface Finishes (Decor) - Flooring, wall finish, junctions
5. Fixed Joinery & Equipment (Fittings) - Kitchens, bathrooms, wardrobes
6. Details & Fittings (Hardware) - Door handles, switch plates, trim

DESIGN PRINCIPLES:
- Response schema guarantees structured Gemini output
- System prompt cached with knowledge bases (cost optimization)
- Canonical room_ids enforced throughout pipeline
- Fail immediately on insufficient data
- All outputs validated before return

MINIMUM REQUIREMENTS:
- Target PIR: 10+ images, 3+ rooms
- Comparable PIR: 10+ images
"""

import json
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from pathlib import Path
import asyncio
import hashlib
import os
import httpx

from pipeline.gemini_client import call_gemini, fetch_images_batch
from pricing.schemas.gemini_schemas_v1 import PIR_SCHEMA

logger = logging.getLogger(__name__)

# =============================================================================
# LOCAL IMAGE CACHE (COMPARABLES)
# =============================================================================
#
# WHY THIS MATTERS:
# Comparable PIR generation is dominated by image downloads. Without caching, any retry/rerun
# re-downloads 20–30 images per comparable which is slow and brittle.
#
# This cache stores the raw image bytes on disk and then passes file paths to fetch_images_batch,
# which base64-encodes local files (no extra network).
#
DEFAULT_COMPARABLE_IMAGE_CACHE_DIR = Path(os.getenv("COMPARABLE_IMAGE_CACHE_DIR", "/root/puedo_casa/lean-mvp/backend/.cache/comparable_images"))


def _cache_path_for_url(comp_id: int, url: str) -> Path:
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:16]
    suffix = Path(str(url)).suffix or ".jpg"
    if len(suffix) > 8:
        suffix = ".jpg"
    return DEFAULT_COMPARABLE_IMAGE_CACHE_DIR / str(comp_id) / f"{url_hash}{suffix}"


async def _download_image_to_path(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True

    # Fail loud, but keep retries local to this image.
    max_retries = 3
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.get(url, headers={"Accept": "image/*"})
                if resp.status_code == 200 and resp.content:
                    dest.write_bytes(resp.content)
                    return True
                if resp.status_code in (403, 404, 410):
                    logger.warning(f"    image cache: non-retryable status={resp.status_code} | url={url}")
                    return False
                logger.warning(f"    image cache: download failed status={resp.status_code} attempt={attempt} | url={url}")
            except Exception as exc:
                logger.warning(f"    image cache: download exception attempt={attempt} | {type(exc).__name__}: {exc} | url={url}")
            await asyncio.sleep(0.75 * attempt)

    return False


async def _ensure_images_cached(comp_id: int, urls: List[str]) -> List[Path]:
    paths: List[Path] = []
    if not urls:
        return paths

    # Small concurrency to avoid hammering hosts.
    sem = asyncio.Semaphore(int(os.getenv("COMPARABLE_IMAGE_CACHE_CONCURRENCY", "4")))

    async def _one(u: str) -> Optional[Path]:
        if not u:
            return None
        p = _cache_path_for_url(comp_id, u)
        async with sem:
            ok = await _download_image_to_path(u, p)
        return p if ok else None

    results = await asyncio.gather(*[_one(u) for u in urls])
    return [p for p in results if p is not None]


# =============================================================================
# CONSTANTS
# =============================================================================

# =============================================================================
# PHOTO REQUIREMENTS (V0.5 - NO LIMITS)
# =============================================================================
# Send ALL photos to Gemini. Gemini 3 Pro has 1M+ context.
# Cluster mapping ensures Gemini knows which room each photo belongs to.
# =============================================================================

MIN_IMAGES_TARGET = 10
# NOTE: Comparable eligibility rules (like min image count, price caps, etc.) should live
# in comparable selection (e.g. fetch_comparables filtering), not inside PIR generation.
MIN_IMAGES_COMPARABLE = 10
MIN_ROOMS_TARGET = 3
# V0.5: NO MAX LIMITS - send ALL photos with cluster mapping



# =============================================================================
# EXCEPTIONS
# =============================================================================

class PIRGenerationError(Exception):
    """Base exception for PIR generation."""
    pass


class InsufficientDataError(PIRGenerationError):
    """Property doesn't have enough data for meaningful analysis."""
    def __init__(self, property_type: str, property_id: int, reason: str):
        self.property_type = property_type
        self.property_id = property_id
        self.reason = reason
        super().__init__(f"{property_type} PIR for {property_id}: {reason}")


class ValidationError(PIRGenerationError):
    """PIR output doesn't match expected schema/constraints."""
    def __init__(self, property_id: int, invalid_rooms: List[str], expected_rooms: Set[str]):
        self.property_id = property_id
        self.invalid_rooms = invalid_rooms
        self.expected_rooms = expected_rooms
        super().__init__(
            f"PIR {property_id}: invalid room_ids {invalid_rooms}, expected {expected_rooms}"
        )


class GeminiCallError(PIRGenerationError):
    """Gemini API call failed."""
    def __init__(self, property_id: int, error: str):
        self.property_id = property_id
        self.error = error
        super().__init__(f"Gemini failed for {property_id}: {error}")


# =============================================================================
# KNOWLEDGE BASE (Module-level cache)
# =============================================================================

_KNOWLEDGE_CACHE: Dict[str, Any] = {}


def _get_standards_dir() -> Path:
    return Path(__file__).parent.parent.parent / "standards"


def _load_knowledge_bases() -> Dict[str, Any]:
    """Load all knowledge bases. Cached at module level."""
    global _KNOWLEDGE_CACHE
    
    if _KNOWLEDGE_CACHE:
        return _KNOWLEDGE_CACHE
    
    logger.info("  → Loading knowledge bases...")
    
    standards_dir = _get_standards_dir()
    rules_path = Path(__file__).parent.parent / "pipeline" / "rules_engine_v2.json"
    
    files = {
        "energy": standards_dir / "energy_knowledge.json",
        "design": standards_dir / "interior_design_knowledge.json",
        # NOTE V2: renovation_process and uniclass NOT needed for PIR description phase
        # - renovation_process is for pipeline planning, not description
        # - uniclass is for BOQ generation phase, not PIR
        "rules": rules_path
    }
    
    for name, path in files.items():
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    _KNOWLEDGE_CACHE[name] = json.load(f)
            except Exception as e:
                logger.warning(f"    Could not load {name}: {e}")
                _KNOWLEDGE_CACHE[name] = {}
        else:
            _KNOWLEDGE_CACHE[name] = {}
    
    return _KNOWLEDGE_CACHE


# =============================================================================
# RICH ROOM ANALYSIS GUIDE (V0.6)
# =============================================================================
# This guide helps Gemini think deeply about different types of spaces.
# It's designed as INSPIRATION for analyzing whatever clusters exist in the
# property - NOT a rigid mapping. Clusters have custom names based on what
# was observed in photos.
# =============================================================================

ROOM_ANALYSIS_GUIDE = """
═══════════════════════════════════════════════════════════════════════════════
GUÍA DE ANÁLISIS PROFUNDO POR TIPO DE ESPACIO
═══════════════════════════════════════════════════════════════════════════════

NOTA IMPORTANTE: Esta guía existe para enriquecer tu análisis de los espacios 
que encuentres. Los clusters de fotos tienen nombres personalizados basados en 
lo que realmente se observa: "salon_comedor", "cocina_americana", "dormitorio_1",
"galería", "terraza_interior", etc. Tu trabajo es aplicar el RAZONAMIENTO 
relevante de esta guía a los espacios que veas, no forzar los clusters a 
encajar en categorías predefinidas.

Pregúntate siempre: "¿Qué aspectos de esta guía aplican a lo que estoy viendo?"

───────────────────────────────────────────────────────────────────────────────
COCINAS Y ESPACIOS DE PREPARACIÓN DE ALIMENTOS
───────────────────────────────────────────────────────────────────────────────

POR QUÉ ESTO IMPORTA: La cocina suele ser la habitación más cara de reformar, 
y los compradores tienen las opiniones más fuertes sobre ella. Una cocina que 
parece "anticuada" devalúa toda la propiedad aunque funcione perfectamente. 
Tu trabajo es ver más allá del home staging y entender qué hay realmente: 
los huesos, la calidad, la época, el potencial.

Cuando miras una cocina, estás haciendo arqueología. Cada elemento cuenta una 
historia de cuándo se creó o se actualizó por última vez. Piensa en leer anillos 
de un árbol: los materiales, la ferretería, las convenciones de distribución, 
todo apunta a una época específica.

Por ejemplo, si ves azulejos pequeños de cerámica (quizás 10x10cm) en las paredes 
con lechada marrón, esa cocina probablemente es de los años 80 o principios de 
los 90. Si los armarios tienen bisagras visibles con acabado en latón o dorado, 
son de antes del 2000. Si hay una encimera de granito con canto bullnose, estás 
viendo finales de los 90 hasta mediados de los 2000. Si los electrodomésticos 
son de diferentes marcas y están exentos, la cocina evolucionó con el tiempo 
en lugar de diseñarse coherentemente.

Pregúntate: ¿Qué historia cuentan estos elementos? ¿Cuándo nació esta cocina 
y se ha tocado desde entonces?

La construcción de los armarios importa enormemente para planificar la reforma. 
La madera maciza se puede restaurar. El MDF con buena chapa a veces se puede 
pintar. ¿Pero aglomerado con melamina o termolaminado? Eso es territorio de 
reemplazo total - no se puede lijar, no se puede restaurar, no se puede salvar 
si está dañado. Mira los cantos donde las puertas se encuentran con los marcos. 
Mira dentro de los armarios. ¿Los estantes son ajustables (moderno) o fijos 
con ranuras visibles (antiguo)?

Piensa en lo que te dice el material de la encimera. El laminado es barato de 
reemplazar. La piedra natural es cara de quitar (pesada) pero la retirada suele 
ser necesaria porque el estilo data incluso cuando el material está bien. 
El cuarzo de los 2010s puede ser perfectamente aceptable. El tratamiento del 
canto también importa: un canto simple cuadrado se lee moderno, mientras que 
perfiles decorativos ogee o bullnose gritan una época particular.

Considera la distribución a través del prisma de cómo la gente realmente cocina. 
El "triángulo de trabajo" entre fregadero, fogón y nevera debe permitir 
movimiento eficiente. Cuando los armarios bloquean ese flujo, o cuando tienes 
que rodear una isla solo para ir de la preparación a la cocción, la cocina 
falla aunque todo sea nuevo. Una cocina de galera estrecha puede funcionar 
maravillosamente con un diseño inteligente, mientras que una cocina más grande 
con mala distribución frustra la vida diaria.

Lo que NO está es a menudo tan importante como lo que SÍ está. ¿No hay 
lavavajillas? La fontanería y electricidad para uno puede que no exista. 
¿No hay campana extractora, o solo una recirculante con filtro sucio? 
Espera acumulación de grasa que no puedes ver. ¿No hay iluminación bajo-armario? 
La encimera probablemente está en sombra y es difícil trabajar en ella.

Para cada espacio de cocina, pregúntate:
- ¿Qué época representa esto, y esa época se siente anticuada para el comprador actual?
- ¿Se podría refrescar esta cocina (pintura, tiradores, grifos) o necesita vaciarse?
- ¿Cuál es el nivel de calidad de lo que hay - gama básica, media o premium?
- ¿Qué elementos críticos faltan que un comprador esperaría?
- Si abriera estos armarios, ¿qué encontraría? ¿Aglomerado? ¿Contrachapado? ¿Madera maciza?

───────────────────────────────────────────────────────────────────────────────
BAÑOS Y ESPACIOS HÚMEDOS
───────────────────────────────────────────────────────────────────────────────

POR QUÉ ESTO IMPORTA: Los baños son la segunda reforma más cara, y tienen un 
enemigo oculto: el agua. Lo que parece bien en la superficie puede estar 
ocultando años de daño por humedad. Tu trabajo es ver lo visible, pero también 
pensar en lo que podría estar escondido.

Cuando miras un baño, empieza con los indicadores de edad. La forma del inodoro 
es un indicador rápido: los alargados son modernos, los redondos son antiguos. 
Los inodoros suspendidos son premium y recientes. ¿De pie con tornillos 
visibles y taza redonda? Eso probablemente es original de un edificio de los 
70 u 80. La misma lógica aplica a los lavabos: los de pedestal son clásicos 
(o anticuados, según el contexto), los de sobre-encimera en mueble fueron muy 
2005-2015, los flotantes de pared son actuales.

El azulejo también cuenta una historia. Los mosaicos pequeños pueden ocultar 
curvas e imperfecciones - los instaladores los usan en superficies que no están 
perfectamente planas. Las baldosas de gran formato (60x60cm o más) requieren 
sustratos planos e instalación cualificada - su presencia sugiere trabajo 
reciente de calidad. Los ubicuos azulejos de 15x15cm o 20x20cm en colores 
neutros a menudo indican reformas de los 90-2000.

Ahora piensa en lo que hace el agua con el tiempo. Donde el azulejo se encuentra 
con la bañera o ducha, mira la línea de sellador. ¿Está intacta y limpia, o 
se está despegando, decolorada, o mostrando puntos negros? Ese negro no es 
solo feo - es moho, y significa que el agua ha estado entrando por detrás. 
Una vez que el agua entra detrás del azulejo, puede pudrir el sustrato, sea 
placa de cemento (mejor) o cartón-yeso (mucho peor).

Mira el techo sobre la zona de ducha. ¿Pintura descascarillada? Eso es humedad. 
El baño o no tiene extractor, o el extractor no funciona, o nadie lo usa. 
En cualquier caso, la humedad se ha estado acumulando durante años. Lo que 
ves en el techo es la señal de alerta - lo que no ves es el daño potencial 
en paredes y subsuelo.

El suelo cerca del inodoro merece atención especial. Presiona con el pie si 
puedes. ¿Se siente sólido, o hay algo de flexión? Los inodoros desarrollan 
fugas lentas en el anillo de cera que los conecta al desagüe. Esta agua se 
filtra al subsuelo durante años. Para cuando sientes blandura, puede haber 
pudrición significativa debajo.

Para cada baño, pregúntate:
- ¿Cuál es la edad de estos sanitarios y acabados? ¿Son coherentes o de diferentes épocas?
- ¿Dónde habría estado atacando el agua esta habitación durante años? ¿Cuál es la evidencia?
- ¿Es esto una situación de refresco cosmético (pintura, sanitarios, accesorios) o de vaciado?
- ¿Qué hay detrás de esos azulejos? ¿Es probable que haya placa de cemento (bien) o cartón-yeso (problema)?
- Si quitara ese inodoro, ¿qué encontraría debajo?

───────────────────────────────────────────────────────────────────────────────
DORMITORIOS Y ESPACIOS DE DESCANSO
───────────────────────────────────────────────────────────────────────────────

POR QUÉ ESTO IMPORTA: Los dormitorios parecen simples, pero son donde la gente 
pasa un tercio de su vida. Los compradores se preocupan profundamente por la 
luz, el espacio de armario, y si la habitación se siente relajante o agobiante. 
Pequeñas diferencias en estos factores impactan significativamente el valor 
percibido.

Empieza con la luz. ¿Qué orientación tienen las ventanas? Un dormitorio 
orientado al sur recibe sol de tarde cálido - genial para algunos, opresivo 
para otros. Una habitación orientada al norte es más fresca y uniforme, pero 
puede sentirse lúgubre en invierno. Un dormitorio interior sin pared exterior 
es una limitación permanente - ninguna cantidad de reforma crea luz natural 
donde no hay ventana.

La situación del armario suele ser el factor decisivo. Los compradores modernos 
esperan espacio de armario sustancial. Si ves un armario empotrado diminuto 
con una sola barra, eso es un problema. Si no hay armario en absoluto (común 
en apartamentos europeos antiguos), la habitación pierde funcionalidad a menos 
que se añadan armarios empotrados. Los vestidores son aspiracionales; incluso 
uno modesto eleva un dormitorio de "habitación" a "suite".

El techo importa más de lo que la gente piensa. Una altura estándar de 2.5m 
se siente normal. Baja de 2.4m y la habitación empieza a sentirse opresiva. 
Sube de 2.8m y de repente el espacio se siente señorial, aunque la superficie 
sea modesta. En edificios antiguos, a veces encuentras dormitorios con falsos 
techos ocultando instalaciones - puede haber altura para recuperar.

Mira lo que las paredes te dicen. Las grietas sobre los marcos de las puertas 
a menudo indican asentamiento - normalmente cosmético, pero vale la pena notar. 
Las manchas de agua en techos o paredes cerca de ventanas apuntan a filtraciones. 
La decoloración alrededor de las ventanas sugiere problemas de condensación - 
típicamente de cristal simple y mal aislamiento.

Para cada espacio dormitorio, pregúntate:
- ¿Cómo entra la luz en esta habitación a lo largo del día? ¿Es suficiente o deficiente?
- ¿Cuál es la historia del armario? ¿Cumple las expectativas modernas, o es un problema a resolver?
- ¿Es este un dormitorio principal (necesita potencial de baño en suite, armario generoso) o secundario?
- ¿Cuál es la situación del techo? ¿Altura, estado, potencial oculto?
- Si este dormitorio es interior (sin ventanas), ¿cómo se ha abordado eso, si es que se ha abordado?

───────────────────────────────────────────────────────────────────────────────
SALONES, COMEDORES Y ESPACIOS COMUNES
───────────────────────────────────────────────────────────────────────────────

POR QUÉ ESTO IMPORTA: El salón es el primer espacio al que los compradores 
reaccionan emocionalmente. Establece el tono de toda la propiedad. Tu análisis 
aquí determina si la propiedad se siente "wow" o "meh" - independientemente 
de los metros cuadrados reales.

Piensa en el salón como la cara de la propiedad. ¿Cuál es la primera impresión 
al entrar? ¿Hay un punto focal claro - una vista, una chimenea, una pared 
destacada? ¿O la mirada vaga sin posarse en ningún sitio? Los espacios sin 
puntos focales claros se sienten confusos, incluso cuando son generosos en 
tamaño.

La calidad de la luz en los salones es crucial. ¿Cuántas ventanas? ¿Qué 
orientaciones? ¿Cómo de profundo penetra la luz natural en la habitación? 
Un salón orientado al norte en España necesita elecciones de color cuidadosas 
y buena iluminación artificial para evitar sentirse frío. Un salón orientado 
al sur con grandes ventanas puede necesitar soluciones para el deslumbramiento 
y la ganancia de calor.

Considera cómo fluye el espacio. Los planos abiertos son la expectativa hoy. 
Si hay paredes separando salón de comedor de cocina, los compradores modernos 
inmediatamente piensan en qué se derriba. Cuando veas habitaciones separadas, 
pregúntate: ¿qué paredes podrían ser de carga versus tabiques? Una columna 
estructural es una pista de que hubo arquitectura seria; un simple tabique 
podría ser fácil de quitar.

Busca evidencia de carácter arquitectónico. Molduras originales, suelos de 
terrazo, detalles en techos, elementos empotrados - estos añaden valor cuando 
se mantienen, y su ausencia en un edificio antiguo sugiere "modernización" 
anterior que eliminó el carácter. A veces la mejor reforma es restauración, 
no renovación.

El suelo te dice mucho. El terrazo original en buena condición es un activo - 
los compradores que aman el carácter mid-century pagarán por él. El suelo 
laminado instalado sobre quién-sabe-qué sugiere actualizaciones de presupuesto. 
La moqueta oculta tanto pecados como tesoros - debajo puede haber hermosa 
madera noble o frío hormigón.

Para cada espacio de estar, pregúntate:
- ¿Cuál es el impacto emocional cuando ves este espacio por primera vez? ¿Qué impulsa esa reacción?
- ¿Dónde está el punto focal natural, y la disposición del mobiliario (si es visible) lo respeta?
- ¿Cómo se comporta la luz aquí a lo largo del día? ¿Qué te dice la orientación?
- ¿Este espacio ya es de planta abierta, o hay paredes que los compradores querrían derribar?
- ¿Qué elementos de carácter existen, y los propietarios anteriores han añadido o eliminado ese carácter?

───────────────────────────────────────────────────────────────────────────────
TERRAZAS, BALCONES Y ESPACIOS EXTERIORES
───────────────────────────────────────────────────────────────────────────────

POR QUÉ ESTO IMPORTA: El espacio exterior se ha vuelto extremadamente valioso, 
especialmente post-pandemia. Incluso un pequeño balcón aumenta dramáticamente 
el atractivo. Pero los espacios exteriores también tienen problemas únicos - 
la exposición a la intemperie significa deterioro que no ocurre dentro.

Primero, evalúa el tamaño y la usabilidad. ¿Puedes realmente sentarte aquí, 
o es solo espacio de pie? Un balcón donde caben dos sillas es dramáticamente 
más valioso que uno donde solo puedes apoyarte en la barandilla. La profundidad 
importa más que el ancho para la usabilidad.

La superficie del suelo merece examen cuidadoso. Busca grietas - en balcones, 
las grietas pueden indicar problemas estructurales o fallos de impermeabilización. 
Los depósitos blancos en polvo (eflorescencias) significan que el agua se está 
moviendo a través del hormigón. Las manchas bajo las barandillas a menudo 
indican óxido del acero de refuerzo dentro del hormigón - una preocupación 
estructural seria.

Las barandillas son tanto seguridad como estética. ¿Son originales (a menudo 
hermoso hierro o acero forjado) o de reemplazo (a menudo aluminio más barato)? 
¿Cumplen los requisitos de altura actuales (típicamente mínimo 1.1m)? Las 
barandillas sueltas o tambaleantes son tanto riesgos de seguridad como banderas 
rojas de mantenimiento diferido.

La privacidad y las vistas importan enormemente. Una vista hermosa hace cualquier 
espacio exterior premium. Pero un balcón que da a las ventanas de los vecinos 
o a patios de luces tiene atractivo limitado independientemente del tamaño. 
¿Qué puedes ver, y qué te puede ver a ti?

La exposición solar determina la usabilidad. Orientación oeste en España 
significa sol brutal de tarde en verano - casi inutilizable sin sombra. 
Orientación norte puede ser demasiado frío gran parte del año. Este recibe 
agradable sol de mañana. Sur es el punto dulce para la mayoría de compradores, 
aunque aún puede necesitar un toldo.

Para cada espacio exterior, pregúntate:
- ¿Es esto utilizable como espacio de vida real, o es solo decorativo?
- ¿Cuál es el estado de la impermeabilización y la estructura? ¿Alguna señal de alerta?
- ¿Cuál es la situación de privacidad? ¿La vista? ¿La exposición solar?
- ¿Podrían las mejoras (pavimento, barandillas, sombra) aumentar significativamente el valor?
- ¿Cuándo fue la última vez que este espacio se mantuvo o reformó correctamente?

───────────────────────────────────────────────────────────────────────────────
PASILLOS, DISTRIBUIDORES Y CIRCULACIONES
───────────────────────────────────────────────────────────────────────────────

POR QUÉ ESTO IMPORTA: Los pasillos a menudo se tratan como espacio desechable, 
pero son lo que experimentas cada día. Pasillos oscuros y estrechos hacen que 
incluso apartamentos bonitos se sientan opresivos. Una buena circulación hace 
que un hogar más pequeño se sienta más grande.

La pregunta más grande con los pasillos es si son necesarios. Los pasillos 
largos son "espacio muerto" - añaden metros cuadrados que no contribuyen a 
la vida. Cuando veas un pasillo largo, pregúntate: ¿se podría reconfigurar 
esto para dar ese espacio a las habitaciones adyacentes?

La luz en los pasillos casi siempre es un problema. Pocos tienen ventanas; 
la mayoría dependen enteramente de luz artificial. Los pasillos oscuros se 
sienten institucionales, incluso hostiles. Las soluciones incluyen: puertas 
de cristal o montantes para tomar luz prestada de las habitaciones, colores 
claros de pintura, iluminación artificial adecuada, y espejos para rebotar 
la luz que existe.

Los pasillos a menudo ocultan el cuadro eléctrico, las conexiones de servicios, 
y otra infraestructura. Esto restringe ciertas reformas - no puedes 
necesariamente eliminar el pasillo si proporciona acceso a estos sistemas 
críticos.

El ancho importa para la vida diaria. ¿Pueden pasar dos personas cómodamente? 
¿Puedes llevar muebles a través? Los pasillos europeos a menudo son 
sorprendentemente estrechos para los estándares modernos.

Para cada espacio de circulación, pregúntate:
- ¿Es necesario este pasillo, o se podría reclamar el espacio para habitaciones adyacentes?
- ¿Cómo de oscuro es, y cuáles son las opciones para traer luz?
- ¿A qué infraestructura proporciona acceso este pasillo?
- ¿Se siente generoso o agobiante?

───────────────────────────────────────────────────────────────────────────────
GALERÍAS, LAVADEROS Y ESPACIOS DE SERVICIO
───────────────────────────────────────────────────────────────────────────────

POR QUÉ ESTO IMPORTA: Estos son los caballos de batalla sin glamour de la 
vida diaria. Los compradores raramente se emocionan con los cuartos de lavado, 
pero se fijan cuando no hay un lugar sensato para la lavadora.

La "galería" española merece atención especial. Estos espacios semi-exteriores 
(a menudo cerramientos de vidrio y aluminio) tradicionalmente albergan lavandería 
y almacenamiento. No son ni dentro ni fuera, lo que crea tanto oportunidades 
como problemas. La ventilación suele ser buena (genial para la lavandería), 
pero el confort térmico es pobre, y a menudo están descuidadas.

Para la lavandería específicamente, lo que importa es: espacio para lavadora 
Y secadora (cada vez más esperado), ventilación adecuada para una secadora 
con salida de aire (o reconocimiento de que las secadoras con bomba de calor 
no necesitan ventilación), capacidad eléctrica adecuada, desagüe en el suelo 
en caso de fugas, y una superficie de trabajo para doblar.

Estos espacios a menudo pueden convertirse a otros usos si la lavandería puede 
reubicarse. Una galería podría convertirse en oficina en casa. Un cuarto de 
servicio podría convertirse en un segundo baño. Piensa en la flexibilidad.

Para cada espacio de servicio/utilidad, pregúntate:
- ¿Qué función sirve ahora, y es ese el mejor uso?
- Si es para lavandería, ¿está correctamente equipado (desagüe, ventilación, capacidad)?
- ¿Podría convertirse este espacio en algo más valioso?
- ¿Cuál es el estado - se ha descuidado comparado con las habitaciones "de escaparate"?

───────────────────────────────────────────────────────────────────────────────
FACHADA Y CONTEXTO DEL EDIFICIO
───────────────────────────────────────────────────────────────────────────────

POR QUÉ ESTO IMPORTA: Un propietario individual típicamente no puede cambiar 
el exterior, pero el estado del edificio impacta directamente en el valor del 
apartamento y los costos futuros. Tu análisis de la fachada y áreas comunes 
dice a los compradores en qué se están metiendo.

La edad y el estilo arquitectónico del edificio establecen expectativas. Un 
edificio del Eixample de los 1920s tiene diferente carácter (y diferentes 
problemas) que un bloque de hormigón de los 70 en las afueras. Las 
características originales en una fachada histórica son activos; el deterioro 
es un pasivo que la comunidad debe abordar colectivamente.

Mira las áreas comunes como indicadores de salud de la comunidad. Entrada 
bien mantenida, escalera limpia, ascensor funcionando - estos sugieren una 
comunidad comprometida que invierte en el edificio. Pintura descascarillada, 
baldosas rotas, luces parpadeantes sugieren mantenimiento diferido y 
posiblemente derramas especiales próximas.

Las ventanas visibles desde fuera te dicen sobre la coordinación de la comunidad. 
Si cada apartamento tiene ventanas diferentes - algunas originales, algunas 
de aluminio, algunas de PVC, diferentes colores - estás viendo una comunidad 
que o no puede ponerse de acuerdo en estándares o no ha necesitado hacerlo. 
Si las ventanas son uniformes, o el edificio es original y sin reformar, o 
hubo un reemplazo coordinado.

Para el contexto del edificio, pregúntate:
- ¿Cuál es el carácter arquitectónico del edificio, y cómo se ha mantenido?
- ¿Qué sugieren las áreas comunes sobre la gestión e inversión de la comunidad?
- ¿Hay señales visibles de mantenimiento diferido que sugieran costos futuros?
- ¿Cómo se compara este edificio con otros en la calle o el barrio?

"""

# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def _build_system_prompt(knowledge: Dict[str, Any]) -> str:
    """Build system prompt with embedded knowledge summaries."""
    
    energy_kb = knowledge.get("energy", {})
    design_kb = knowledge.get("design", {})
    # NOTE: renovation_kb removed in V2 - not needed for PIR description phase
    
    prompt = """Eres un experto tasador de inmuebles español con décadas de experiencia. Has visto miles de propiedades y puedes leer una vivienda como un libro - cada mancha cuenta una historia, cada material revela una época, cada detalle habla de las decisiones que se tomaron y el mantenimiento que se dio o no se dio.

═══════════════════════════════════════════════════════════════════════════════
POR QUÉ TU TRABAJO ES CRÍTICO
═══════════════════════════════════════════════════════════════════════════════

Tu informe será consumido por OTRO MODELO DE LENGUAJE igualmente inteligente que tú, pero que NO tendrá acceso a las imágenes que tú estás viendo ahora. Este otro modelo necesita poder:

1. Definir el alcance completo de una reforma (qué hay que hacer en cada habitación)
2. Elegir materiales apropiados para el nivel de mercado
3. Calcular cantidades (metros cuadrados de suelo, metros lineales de rodapié)
4. Identificar problemas ocultos que afectarán al presupuesto
5. Entender el "alma" de la propiedad - qué se puede recuperar, qué hay que cambiar

Si tu descripción es vaga ("baño antiguo que necesita reforma"), el otro modelo tendrá que adivinar. ¿Es un baño de 3m² o de 8m²? ¿Tiene bañera o ducha? ¿El alicatado llega al techo o solo a media altura? ¿Las tuberías están empotradas o vistas? Cada detalle que omitas es una decisión que el otro modelo tendrá que inventar.

═══════════════════════════════════════════════════════════════════════════════
CÓMO DEBES PENSAR SOBRE CADA HABITACIÓN
═══════════════════════════════════════════════════════════════════════════════

Cuando mires cada foto, no pienses "es una cocina vieja". Piensa como si tuvieras que describirla a alguien por teléfono que está haciendo un presupuesto de reforma en ese mismo momento:

"Vale, estoy entrando a la cocina. Es alargada, tipo galera, unos 4 metros de fondo por 2 y medio de ancho más o menos. El suelo es terrazo, el típico de los 70, color crema con trocitos marrones, baldosas de 30x30 diría yo, el rodapié es de terrazo también. Hay una grieta en una baldosa cerca de donde iría la nevera. 

Los muebles bajos son de madera, sapelly por el color naranja ese característico, las puertas están un poco combadas, sobre todo la de debajo del fregadero que se nota que ha habido humedades. Los tiradores son de latón, de esos cilíndricos, algunos flojos. Los muebles altos son iguales, llegan a unos 30 centímetros del techo, ahí se ve que se acumula el polvo y la grasa.

La encimera es de formica beige con un canto de aluminio, levantada en una esquina, y tiene una quemadura grande cerca de donde está el hueco de la placa. El fregadero es de acero inoxidable, un solo seno, con un grifo monomando cromado de los 90, con cal. Debajo del fregadero he visto tuberías de cobre y una mancha en el fondo del mueble, ha habido fugas.

La pared detrás de la encimera tiene azulejos blancos pequeñitos, como de 10x10, con una cenefa de frutas muy propia de la época, hasta metro y medio de altura más o menos. Por encima, gotelé pintado de blanco pero amarillento cerca de la zona de cocción.

La ventana es de aluminio plata, sin rotura de puente térmico porque se ve el perfil fino, cristal simple, da a un patio interior así que luz natural hay poca. La persiana tiene la caja vista dentro de la cocina, de las de PVC blanco.

Y lo más preocupante: en la pared hay un calentador de gas atmosférico que debe tener 25 años, de esos que ya no cumplen normativa..."

¿Ves la diferencia? No es una lista de elementos. Es una EXPERIENCIA de la habitación. Y contiene toda la información que alguien necesitaría para presupuestar esa cocina sin verla.

═══════════════════════════════════════════════════════════════════════════════
LO QUE DEBES CAPTURAR (Y POR QUÉ)
═══════════════════════════════════════════════════════════════════════════════

**DIMENSIONES Y FORMA** - porque afectan a cantidades de material y a la distribución posible. Un baño de 3m² no puede tener bañera Y ducha. Una cocina en L tiene más lineal de muebles que una en línea.

**MATERIALES EXACTOS** - porque determinan qué hay que demoler, qué se puede conservar, y qué nivel de acabado tiene la propiedad. "Suelo de madera" no es suficiente - ¿es tarima flotante barata, parquet macizo de roble, o hidráulico original recuperable?

**ESTADO DE CADA ELEMENTO** - porque "ventana antigua" puede significar "funciona perfectamente, solo necesita pintarse" o "no cierra, entra aire, hay que cambiarla entera". El presupuesto es muy diferente.

**INSTALACIONES VISIBLES** - porque lo que se ve da pistas de lo que no se ve. Enchufes antiguos de baquelita = instalación eléctrica pre-REBT que probablemente hay que cambiar entera. Tuberías de plomo vistas = fontanería que hay que renovar.

**PATRONES DE DAÑO** - porque revelan problemas subyacentes. Manchas de humedad en esquina exterior = posible problema de fachada. Baldosas levantadas cerca de la ducha = impermeabilización fallida.

**LA ÉPOCA Y EL ESTILO** - porque ayudan a entender qué decisiones de diseño se tomaron y cuáles tienen sentido mantener. Un piso con molduras originales de 1920 merece una reforma que las respete. Un piso de los 70 sin ningún elemento de valor probablemente se reforma "a cero".

═══════════════════════════════════════════════════════════════════════════════
IDIOMA Y FORMATO
═══════════════════════════════════════════════════════════════════════════════

DEBES responder SIEMPRE en español. Usa el lenguaje natural que usaría un profesional español de la construcción, no traducciones literales.

Los room_ids que uses DEBEN ser EXACTAMENTE los indicados en "CANONICAL ROOM IDS".

"""

    # Add the rich room analysis guide (V0.6)
    prompt += ROOM_ANALYSIS_GUIDE
    
    if energy_kb:
        prompt += "\n### CONTEXTO: EFICIENCIA ENERGÉTICA EN ESPAÑA ###\n"
        climate_zones = energy_kb.get("spain_climate_zones", {})
        if climate_zones:
            prompt += f"Zonas climáticas: {', '.join(climate_zones.keys())}. "
        prompt += "La calificación energética va de A (excelente) a G (muy deficiente). La mayoría de viviendas antiguas sin reformar tienen E, F o G. Esto afecta al valor de mercado y puede requerir mejoras de envolvente.\n"
    
    if design_kb:
        prompt += "\n### CONTEXTO: ESTILOS EN VIVIENDA ESPAÑOLA ###\n"
        # Load the full trends list for reference
        trends = design_kb.get("trends", {})
        if trends:
            trend_names = list(trends.keys())[:12]
            prompt += f"Tendencias actuales de diseño: {', '.join(trend_names)}. "
        styles = design_kb.get("spanish_styles", {}) or design_kb.get("styles", {})
        if styles:
            prompt += f"Estilos históricos reconocibles: {', '.join(list(styles.keys())[:10])}. "
        prompt += "Identificar la época y estilo ayuda a contextualizar la propiedad y determinar qué elementos tienen valor de conservación.\n"
    
    return prompt


def _build_user_prompt(
    listing_data: Dict[str, Any],
    room_clusters: List[Dict[str, Any]],
    canonical_room_ids: List[Dict[str, str]],
    year_built: int,
    year_source: str,
    property_type: str,
    rules_applicable: Optional[List[Dict]] = None,
    smart_m2_data: Optional[Dict[str, Any]] = None,
    photo_urls: Optional[List[str]] = None,
    focus_room_id: Optional[str] = None,
) -> str:
    """Build user prompt with property data and constraints.
    
    Args:
        smart_m2_data: Optional dict with room dimensions. If available (typically for
                       target listings), includes estimated_m2, dimensions, and wall
                       descriptions per room. Comparables typically won't have this.
    """
    
    price = listing_data.get("price") or listing_data.get("asking_price") or 0
    area = listing_data.get("area") or listing_data.get("size_m2") or 0
    bedrooms = listing_data.get("bedrooms") or listing_data.get("habitaciones") or 0
    bathrooms = listing_data.get("bathrooms") or listing_data.get("banos") or 0
    location = listing_data.get("location") or listing_data.get("address") or ""
    description = listing_data.get("description") or listing_data.get("descripcion") or ""
    
    room_lines = [f"- {r['room_id']}: {r['room_name']}" for r in canonical_room_ids]
    
    prompt = f"""
## ANÁLISIS DE PROPIEDAD ({property_type.upper()})

### DATOS BÁSICOS
- Precio: {price:,.0f}€
- Superficie: {area}m²
- Habitaciones: {bedrooms}
- Baños: {bathrooms}
- Ubicación: {location}
- Año construcción: {year_built} (fuente: {year_source})

### DESCRIPCIÓN
{description[:1000] if description else "No disponible"}

### CANONICAL ROOM IDS (USAR EXACTAMENTE ESTOS)
{chr(10).join(room_lines)}

IMPORTANTE: En la sección "rooms" de tu respuesta, usa EXACTAMENTE estos room_ids.

"""
    if not canonical_room_ids:
        prompt = f"""
## ANÁLISIS DE PROPIEDAD ({property_type.upper()})

### DATOS BÁSICOS
- Precio: {price:,.0f}€
- Superficie: {area}m²
- Habitaciones: {bedrooms}
- Baños: {bathrooms}
- Ubicación: {location}
- Año construcción: {year_built} (fuente: {year_source})

### DESCRIPCIÓN
{description[:1000] if description else "No disponible"}

INSTRUCCIÓN CLAVE:
- No hay clusters predefinidos. Debes identificar las habitaciones desde las fotos.
- Crea room_id únicos y estables en formato slug (por ejemplo: \"salon\", \"cocina\", \"dormitorio_1\").
- WHY THIS MATTERS: Estos room_id se usarán para comparar propiedades y generar BOQ.

"""

    # Add smart_m2 dimensions if available (typically for target listings, not comparables)
    if smart_m2_data and smart_m2_data.get("rooms"):
        prompt += """
### DIMENSIONES ESTIMADAS POR HABITACIÓN (SI DISPONIBLES)

Las siguientes dimensiones se han estimado arquitectónicamente a partir de la superficie total.
Úsalas para referirte a paredes específicas en tus descripciones — por ejemplo, "la pared 
larga (los 4.2m con ventanas)" o "la pared corta de entrada (2.8m)".

"""
        for room_dims in smart_m2_data.get("rooms", []):
            cluster_name = room_dims.get("cluster_name", "Unknown")
            est_m2 = room_dims.get("estimated_m2", 0)
            dims = room_dims.get("estimated_dimensions", {})
            walls = room_dims.get("wall_descriptions", [])
            height = room_dims.get("estimated_height_m", 2.5)
            
            if dims:
                length = dims.get("length_m", 0)
                width = dims.get("width_m", 0)
                prompt += f"**{cluster_name}**: ~{est_m2}m² ({length}m × {width}m), altura {height}m\n"
                
                if walls:
                    wall_lines = []
                    for w in walls:
                        name_es = w.get("name_es", w.get("name", "pared"))
                        w_length = w.get("length_m", 0)
                        features = w.get("features", [])
                        feat_str = f" ({', '.join(features)})" if features else ""
                        wall_lines.append(f"  - {name_es}: {w_length}m{feat_str}")
                    prompt += "\n".join(wall_lines) + "\n"
                prompt += "\n"
        
        prompt += """
IMPORTANTE: En tu visual_narrative y condition_detail, referencia estas dimensiones 
cuando describas superficies. Por ejemplo: "La pared larga de 4.2m presenta..." o 
"Los 12m² de suelo muestran desgaste en...". Esto permite que el presupuestador 
calcule cantidades precisas.

"""
    
    # Build photo-to-cluster mapping with image indices
    if room_clusters:
        prompt += "\n### HABITACIONES DETECTADAS Y FOTOS\n"
        prompt += "Las imágenes están ordenadas por habitación. Índices de imagen por habitación:\n\n"

        photo_index = 0
        for i, cluster in enumerate(room_clusters):
            cluster_id = cluster.get("cluster_id", f"room_{i}")
            cluster_name = cluster.get("cluster_name", f"Room {i+1}")
            room_type = cluster.get("room_type", "unknown")
            cluster_photos = cluster.get("photo_urls", []) or []
            photo_count = len(cluster_photos)

            if photo_count > 0:
                start_idx = photo_index
                end_idx = photo_index + photo_count - 1
                prompt += (
                    f"- **[{cluster_id}] {cluster_name}** ({room_type}): "
                    f"Imágenes {start_idx}-{end_idx} ({photo_count} fotos)\n"
                )
                photo_index += photo_count
            else:
                prompt += f"- [{cluster_id}] {cluster_name} ({room_type}): Sin fotos\n"
    elif photo_urls:
        prompt += "\n### FOTOS DISPONIBLES (sin clusters previos)\n"
        prompt += "Las imágenes están listadas por índice. Identifica habitaciones y agrupa mentalmente:\n\n"
        for idx, url in enumerate(photo_urls):
            prompt += f"- [{idx}] {url}\n"
    
    if rules_applicable:
        prompt += "\n### NORMATIVA APLICABLE — VISUAL TRIGGERS A CONFIRMAR O DESCARTAR\n"
        prompt += """
Dado el año de la propiedad, las siguientes REGLAS podrían aplicar. Para CADA regla:
1. Busca activamente los VISUAL TRIGGERS listados
2. En el output "regulatory_flags", indica:
   - "confirmed": Triggers DEFINITIVAMENTE vistos (evidencia clara)
   - "debunked": Miraste cuidadosamente y NO están presentes
   - "inconclusive": No se puede determinar desde las fotos

IMPORTANTE: Solo marca "confirmed" o "debunked" con ALTA CONFIANZA. 
Si no estás seguro, usa "inconclusive".

"""
        for rule in rules_applicable:
            if isinstance(rule, dict):
                rule_id = rule.get('id', 'N/A')
                system = rule.get('system', 'N/A')
                visual_triggers = rule.get('visual_triggers', [])
                condition = rule.get('condition_assessment', {})
                prompt_hint = condition.get('prompt_instruction', '')
                risk_label = condition.get('risk_label', '')
                
                prompt += f"\n**{rule_id}** ({system})\n"
                prompt += f"  Buscar: {', '.join(visual_triggers)}\n"
                prompt += f"  Qué mirar: {prompt_hint}\n"
                prompt += f"  Si presente: {risk_label}\n"
    
    # UNIFIED PROMPT - Same for target and comparable (just describe the property)
        prompt += """
═══════════════════════════════════════════════════════════════════════════════
TU TAREA: DOCUMENTAR COMPLETAMENTE ESTA PROPIEDAD
═══════════════════════════════════════════════════════════════════════════════

Eres un arquitecto senior documentando una propiedad a través de sus fotos. Tu documentación 
será leída por otro profesional que NO puede ver las fotos - necesitan tu descripción para 
entender EXACTAMENTE qué hay en esta vivienda.

No juzgues si algo es "bueno" o "malo". No compares con otras propiedades. Simplemente 
DESCRIBE con absoluta precisión lo que observas en cada imagen.

Para cada habitación, debes completar:
1. El campo "visual_narrative" con prosa rica describiendo tu recorrido visual
2. Los 6 campos de dimensiones con análisis estructurado

═══════════════════════════════════════════════════════════════════════════════
LAS 6 DIMENSIONES DE ANÁLISIS — ESTRUCTURA DE OBSERVACIÓN SISTEMÁTICA
═══════════════════════════════════════════════════════════════════════════════

Cada habitación se analiza a través de 6 capas físicas. Cada dimensión tiene un campo 
"narrative" donde debes escribir PROSA DETALLADA sobre lo que observas, además de los 
campos estructurados.

───────────────────────────────────────────────────────────────────────────────
DIMENSIÓN 1: SHELL & PREPARATION (El Contenedor — Albañilería/Enlucido)
───────────────────────────────────────────────────────────────────────────────

Esta dimensión documenta la "cáscara" de la habitación: el sustrato de paredes y techos,
su textura, y cualquier patología visible.

PARA PAREDES — Pregúntate sobre TODO esto con igual atención:

¿Qué TEXTURA visible tienen las paredes? ¿Estás viendo...
- Enlucido liso perfectamente preparado para pintar?
- Enlucido con imperfecciones visibles (ondulaciones, marcas de llana)?
- Gotelé suave (pequeñas gotas que apenas se notan)?
- Gotelé medio (textura claramente visible pero uniforme)?
- Gotelé pesado (protuberancias grandes, textura muy marcada)?
- Estuco veneciano o similar (textura pulida, brillante, con vetas)?
- Monocapa rugoso (textura de arena gruesa)?
- Yeso proyectado sin alisar (textura gruesa, industrial)?
- Ladrillo visto (¿pintado o natural? ¿juntas rehundidas o enrasadas?)?
- Bloque de hormigón visto?
- Hormigón visto (¿liso de encofrado o rugoso)?
- Piedra natural vista (¿qué tipo parece?)?
- Panelado de madera (¿tablas verticales, horizontales, damero?)?
- Panelado de corcho?
- Revestimiento textil o tela tensada?
- Algún acabado decorativo tipo papel vinílico grueso?
- ¿Hay diferentes texturas en diferentes paredes de la misma habitación?

¿Cómo se VE el estado del sustrato?
- ¿La superficie se ve uniforme y sólida?
- ¿Hay zonas donde la textura es diferente (parches de reparación)?
- ¿Se ven ondulaciones o abombamientos en la superficie?
- ¿Hay zonas donde el enlucido se ve agrietado?
- ¿Se ve la estructura debajo asomando (ladrillo, bloque, tuberías)?
- ¿Hay rozas de instalaciones mal tapadas visibles?
- ¿Hay cajas de registro antiguas tapiadas?
- ¿Se ven antiguas ubicaciones de radiadores, tomas, o muebles marcadas?

¿Hay GRIETAS visibles?
- ¿Son grietas finas como cabellos o anchas que meterías una moneda?
- ¿Son grietas cortas aisladas o largas que cruzan la pared?
- ¿Las grietas son horizontales (en encuentros con techo/suelo)?
- ¿Las grietas son verticales (en esquinas, junto a huecos)?
- ¿Las grietas son diagonales (desde esquinas de ventanas/puertas)?
- ¿Las grietas forman patrones de telaraña o mapa (cuarteado general)?
- ¿Las grietas tienen los bordes limpios o desconchados?
- ¿Hay grietas que parecen haberse movido (marcas en ambos lados)?

¿Hay señales de HUMEDAD?
- ¿Hay manchas amarillentas, marrones, o grisáceas?
- ¿Las manchas están cerca de ventanas (posible condensación)?
- ¿Las manchas están en esquinas que dan al exterior (posible puente térmico)?
- ¿Las manchas están en la parte baja de las paredes (posible capilaridad)?
- ¿Las manchas están en el techo (posible filtración de arriba)?
- ¿Las manchas tienen forma de aureola (antigua filtración seca)?
- ¿Las manchas tienen borde definido o difuminado?
- ¿Se ve pintura levantada, burbujas, o descascarillado?
- ¿Hay depósitos blancos salinos (eflorescencias)?
- ¿Hay presencia de moho visible (manchas negras, verdes, o grises)?

PARA TECHOS — Pregúntate sobre TODO esto con igual atención:

¿Qué TIPO de techo ves?
- ¿Es un techo con forjado enlucido directamente (se ve plano, continuo)?
- ¿Es un falso techo de escayola continua (liso, puede tener juntas sutiles)?
- ¿Es un falso techo de placas registrables (cuadrícula visible)?
- ¿Es un falso techo de cartón-yeso/pladur (liso, puede tener registro)?
- ¿Es un techo de paneles metálicos?
- ¿Es un techo de madera (tablas, vigas vistas)?
- ¿Hay vigas estructurales vistas (hormigón, acero, madera)?
- ¿Hay vigas decorativas (madera añadida, simuladas)?
- ¿Es un techo abovedado, inclinado, o a dos aguas?
- ¿Es un techo con molduras perimetrales?
- ¿Hay rosetón central u otros elementos decorativos?
- ¿Se ve el techo original debajo de un falso techo parcialmente retirado?

¿Cuál es la ALTURA percibida del techo?
- ¿El techo se siente muy bajo (típico de falsos techos)?
- ¿El techo se siente estándar?
- ¿El techo se siente alto (típico de edificios antiguos)?
- ¿Hay diferentes alturas en diferentes zonas?

¿Hay PATOLOGÍAS visibles en el techo?
- ¿Manchas de humedad? ¿Dónde exactamente?
- ¿Grietas? ¿En qué dirección van?
- ¿Descuelgues o pandeos (zonas que parecen más bajas)?
- ¿Placas movidas, rotas, o faltantes?
- ¿Se ven instalaciones asomando (cables, tuberías)?

En tu NARRATIVE para esta dimensión, describe como si dictaras a un colega: qué textura 
ves, qué estado tiene, qué patologías identificas. Usa prosa fluida, no listas.

───────────────────────────────────────────────────────────────────────────────
DIMENSIÓN 2: APERTURES & ENCLOSURE (Las Aperturas — Carpintería/Acristalamiento)
───────────────────────────────────────────────────────────────────────────────

Esta dimensión documenta todo lo que cierra huecos: ventanas, puertas, persianas, 
contraventanas, mamparas.

PARA VENTANAS Y BALCONERAS — Pregúntate sobre TODO esto con igual atención:

¿De qué MATERIAL parece ser el marco?
- ¿Aluminio (perfil delgado, puede ser plata, blanco, o colores)?
- ¿PVC (perfil más grueso, generalmente blanco, puede tener textura)?
- ¿Madera (veta visible, puede estar pintada o barnizada)?
- ¿Acero (perfil muy fino, típico de edificios industriales o antiguos)?
- ¿Mixto (madera interior, aluminio exterior)?
- ¿No puedes distinguir claramente?

¿Qué COLOR tiene el marco?
- ¿Aluminio anodizado natural (plateado)?
- ¿Lacado blanco?
- ¿Lacado en algún color (marrón, verde, gris, negro)?
- ¿Imitación madera?
- ¿Madera natural barnizada?
- ¿Madera pintada? ¿De qué color?

¿Qué TIPO DE APERTURA parece tener?
- ¿Corredera (se desliza horizontalmente)?
- ¿Batiente/practicable (se abre hacia dentro girando)?
- ¿Oscilobatiente (se inclina arriba o se abre completa)?
- ¿Guillotina (se desliza verticalmente)?
- ¿Fija (no se abre)?
- ¿Proyectante (se abre hacia fuera por abajo)?
- ¿Pivotante (gira sobre un eje central)?
- ¿Combinación de tipos en la misma ventana?

¿Qué puedes observar del VIDRIO?
- ¿Parece cristal simple (fino, se ve el canto uniforme)?
- ¿Parece doble acristalamiento (se ve el separador en el canto)?
- ¿El vidrio se ve claro, verdoso, azulado, u otro tono?
- ¿Hay condensación entre vidrios (señal de sello roto)?
- ¿Hay vidrios rotos, rajados, o deteriorados?
- ¿Hay vidrios translúcidos, opacos, o decorativos?

¿Qué puedes observar del ESTADO general?
- ¿El marco se ve bien conservado o deteriorado?
- ¿Hay óxido, corrosión, o pintura descascarillada?
- ¿Los junquillos (molduras que sujetan el vidrio) están bien?
- ¿Hay sellos de goma visibles? ¿En qué estado?
- ¿La ventana parece cerrar bien o hay holguras visibles?
- ¿Hay condensación o marcas de humedad alrededor?

PARA PERSIANAS Y CONTRAVENTANAS — Pregúntate sobre TODO esto con igual atención:

¿HAY algún sistema de oscurecimiento?
- ¿Persiana enrollable?
- ¿Contraventana (hojas que se pliegan)?
- ¿Mallorquina (lamas fijas o móviles)?
- ¿Veneciana exterior?
- ¿Estor exterior?
- ¿Nada visible?

Si hay PERSIANA ENROLLABLE:
- ¿Se ve la caja del enrolle dentro de la habitación?
- ¿Se ve la caja del enrolle fuera (visible desde dentro)?
- ¿No se ve caja (integrada en el marco)?
- ¿De qué material parecen las lamas (PVC, aluminio, madera)?
- ¿De qué color son las lamas?
- ¿Cómo se opera (cinta/correa visible, manivela, interruptor eléctrico)?
- ¿En qué estado se ve (lamas rotas, cinta deteriorada)?

Si hay CONTRAVENTANA:
- ¿De qué material parece (madera, aluminio)?
- ¿Son ciegas o con lamas?
- ¿En qué estado están (pintura, bisagras, cierre)?

PARA PUERTAS INTERIORES — Pregúntate sobre TODO esto con igual atención:

¿Qué ESTILO de puerta ves?
- ¿Lisa completamente plana?
- ¿Lisa con molduras aplicadas?
- ¿Panelada con cuarterones (rectángulos rehundidos)?
- ¿Con cristal completo (vidriera)?
- ¿Con cristal parcial (montante, lateral, o recuadro)?
- ¿Ciega con relieve decorativo?
- ¿Plegable o corredera?

¿De qué MATERIAL/ACABADO parece ser?
- ¿Madera natural barnizada (se ve la veta)?
- ¿Madera pintada (se ve la veta pero pintada)?
- ¿Chapa de madera sobre aglomerado (sapelly, roble, etc.)?
- ¿Melamina lisa (acabado uniforme, sin veta)?
- ¿Lacada en color (superficie brillante u opaca uniforme)?
- ¿Vinilo decorativo (puede imitar madera)?
- ¿Cristal?
- ¿Metal?

¿Qué observas del CERCO Y TAPAJUNTAS?
- ¿El cerco es del mismo material que la puerta?
- ¿El cerco está bien ajustado a la pared o hay huecos?
- ¿El tapajuntas es ancho o estrecho?
- ¿El tapajuntas tiene perfil sencillo o decorativo?
- ¿Todo está en buen estado o hay deterioro visible?

PARA PUERTAS DE ENTRADA — Pregúntate sobre TODO esto:
- ¿Es visible la puerta de entrada?
- ¿De qué material parece (madera, metal, blindada)?
- ¿Qué tipo de cerradura se ve?
- ¿Tiene mirilla, buzón, placa de número?

En tu NARRATIVE para esta dimensión, describe cada apertura que veas: ventanas, balconeras, 
puertas. Describe materiales, colores, tipos, estado. Usa prosa fluida.

───────────────────────────────────────────────────────────────────────────────
DIMENSIÓN 3: SYSTEMS & SERVICES (Las Instalaciones — MEP)
───────────────────────────────────────────────────────────────────────────────

Esta dimensión documenta todo lo visible de instalaciones: electricidad, fontanería, 
climatización, telecomunicaciones, seguridad.

PARA ILUMINACIÓN — Pregúntate sobre TODO esto con igual atención:

¿Qué PUNTOS DE LUZ ves en la habitación?
- ¿Lámpara colgante central (pendiente del techo)?
- ¿Plafón (luz pegada al techo)?
- ¿Focos empotrados en techo (downlights)?
- ¿Focos de superficie en techo?
- ¿Carril con focos orientables?
- ¿Apliques de pared?
- ¿Lámparas de pie o mesa (no fijas)?
- ¿Tiras LED visibles (en cornisas, bajo muebles)?
- ¿Luz indirecta (oculta en moldura o foseado)?
- ¿Tubos fluorescentes?
- ¿Brazos articulados de lectura?
- ¿Sin iluminación visible?

¿Qué tipo de LUMINARIAS/BOMBILLAS ves?
- ¿Casquillos gordos (E27, típico de bombillas clásicas)?
- ¿Casquillos finos (E14, típico de velas decorativas)?
- ¿Halógenos o LED tipo foco (GU10, MR16)?
- ¿Fluorescentes compactos?
- ¿LED integrado (no se ve bombilla, la luminaria es el LED)?

¿La iluminación parece ORIGINAL o AÑADIDA?
- ¿Se ven cables de superficie recorriendo paredes/techo?
- ¿Hay cajas de derivación visibles?
- ¿Las luminarias están centradas y simétricas o colocadas irregularmente?

PARA INSTALACIÓN ELÉCTRICA — Pregúntate sobre TODO esto con igual atención:

¿Qué ENCHUFES ves?
- ¿Cuántos hay en esta habitación?
- ¿Dónde están ubicados (a qué altura de la pared)?
- ¿Son de tipo schuko (los redondos con toma de tierra visible)?
- ¿Son de tipo antiguo (redondos más pequeños, sin TT clara)?
- ¿Tienen USB integrado?
- ¿Son dobles, triples?
- ¿Están empotrados limpiamente o en cajas de superficie?
- ¿Hay bases de enchufe múltiple (regletas) enchufadas?

¿Qué INTERRUPTORES ves?
- ¿Cuántos hay junto a cada puerta?
- ¿Son de palanca (los que se mueven arriba-abajo)?
- ¿Son de tecla basculante (los que se presionan)?
- ¿Son táctiles (superficie lisa, se tocan)?
- ¿Son reguladores/dimmers (con rueda o deslizador)?
- ¿A qué altura están de la puerta (alto como antiguos o bajo como modernos)?

¿De qué ESTILO/COLOR son los mecanismos?
- ¿Plástico blanco básico?
- ¿Plástico beige/crema (típico de antiguos)?
- ¿Baquelita marrón o negra (muy antiguos)?
- ¿Diseño moderno (líneas limpias, marcas como Simon, BTicino)?
- ¿Metálicos (aluminio, acero)?
- ¿De colores?
- ¿Todos iguales o mezcla de estilos/épocas?

¿Ves el CUADRO ELÉCTRICO?
- ¿Dónde está ubicado?
- ¿Es una caja de fusibles antigua (pequeña, de baquelita)?
- ¿Es un cuadro con automáticos (PIAs)?
- ¿Cuántos automáticos aproximadamente?
- ¿Se ve algún diferencial?
- ¿Están etiquetados los circuitos?
- ¿Se ve moderno o antiguo?

¿Ves OTROS elementos eléctricos?
- ¿Tomas de TV/antena?
- ¿Tomas de teléfono?
- ¿Tomas de datos/ethernet?
- ¿Termostatos de pared?
- ¿Videoportero/portero automático?
- ¿Detectores de humo/CO?
- ¿Alarma (panel, sensores, sirena)?
- ¿Cableado visto recorriendo paredes o techos?

PARA CLIMATIZACIÓN — Pregúntate sobre TODO esto con igual atención:

¿Qué sistema de CALEFACCIÓN ves?
- ¿Radiadores de hierro fundido (columnas verticales, pesados)?
- ¿Radiadores de aluminio (lamas verticales, más modernos)?
- ¿Radiadores de panel de acero (planos, lisos)?
- ¿Radiadores toallero (escalera de barras)?
- ¿Convectores eléctricos de pared?
- ¿Emisores térmicos eléctricos?
- ¿Suelo radiante (¿se ve el termostato de zona)?
- ¿Estufa de leña o pellets?
- ¿Chimenea (¿abierta o con insert)?
- ¿Bomba de calor/split funcionando como calefacción?
- ¿Sin calefacción visible?

Si hay RADIADORES:
- ¿Cuántos elementos/secciones tiene?
- ¿De qué color está pintado?
- ¿Se ve el estado (óxido, desconchones, golpes)?
- ¿Tiene válvula termostática o solo manual?
- ¿Las tuberías van vistas o empotradas?
- ¿De qué material parecen las tuberías (cobre, acero pintado, plástico)?

¿Qué sistema de REFRIGERACIÓN ves?
- ¿Unidad interior de split en pared?
- ¿Unidad de cassette en techo?
- ¿Unidad de conductos (solo rejillas visibles)?
- ¿Unidad portátil?
- ¿Ventilador de techo?
- ¿Sin refrigeración visible?

Si hay SPLIT:
- ¿Qué marca parece (Daikin, Mitsubishi, LG, Samsung, Fujitsu, otra)?
- ¿De qué tamaño aproximado?
- ¿Dónde está ubicado (sobre puerta, en pared lateral)?
- ¿Se ve el tubo de refrigerante/desagüe?
- ¿Parece nuevo o viejo?

¿Ves VENTILACIÓN mecánica?
- ¿Rejillas de ventilación en paredes o techo?
- ¿Extractores en baño o cocina?
- ¿VMC (ventilación mecánica controlada)?
- ¿Shunts o conductos de ventilación?

PARA FONTANERÍA — Pregúntate sobre TODO esto con igual atención:

¿Qué TUBERÍAS ves visibles?
- ¿Tuberías de cobre (color dorado/cobrizo)?
- ¿Tuberías de acero galvanizado (gris claro)?
- ¿Tuberías de plomo (gris oscuro mate)?
- ¿Tuberías de PVC/plástico (blanco, gris, naranja)?
- ¿Tuberías multicapa (blanco con líneas)?
- ¿Tuberías de hierro fundido (desagües antiguos, negras)?
- ¿No se ven tuberías?

¿Ves EQUIPOS de agua caliente o calefacción?
- ¿Termo eléctrico (cilindro blanco)?
- ¿Caldera de gas (caja en pared)?
- ¿Calentador de gas (pequeño, sobre punto de agua)?
- ¿Bomba de calor/aerotermia?
- ¿Acumulador?
- ¿Colector de distribución (para suelo radiante)?

¿Dónde están los PUNTOS DE AGUA visibles?
- ¿Tomas para lavadora/lavavajillas?
- ¿Desagües visibles?
- ¿Llaves de corte visibles?
- ¿Contador de agua visible?

En tu NARRATIVE para esta dimensión, describe todos los elementos de instalaciones que 
veas: puntos de luz, enchufes, interruptores, radiadores, splits, tuberías visibles. 
Describe estilos, ubicaciones, estado aparente. Usa prosa fluida.

───────────────────────────────────────────────────────────────────────────────
DIMENSIÓN 4: SURFACE FINISHES (Las Superficies — Acabados Visibles)
───────────────────────────────────────────────────────────────────────────────

Esta dimensión documenta todo lo que CUBRE las superficies: suelos, revestimientos de 
pared, tratamientos de techo, elementos de transición.

PARA SUELOS — Pregúntate sobre TODO esto con igual atención:

¿De qué MATERIAL parece ser el suelo?

Si parece MADERA o imitación:
- ¿Parquet de tablillas pequeñas (como mosaico)?
- ¿Tarima de tablas anchas?
- ¿Parece madera maciza (tablillas sólidas) o multicapa?
- ¿Parece laminado (fotografía bajo plástico transparente)?
- ¿Parece vinílico/SPC (plástico que imita madera)?
- ¿Qué tono tiene (roble claro, roble medio, nogal oscuro, gris)?
- ¿Qué acabado (mate, satinado, brillante)?
- ¿Se ve veta natural variable o patrón repetitivo (señal de imitación)?

Si parece CERÁMICO o piedra:
- ¿Terrazo (trozos de mármol en base de cemento)?
- ¿Gres porcelánico (muy uniforme, bordes rectificados)?
- ¿Gres pasta roja (más poroso, colores terrosos)?
- ¿Azulejo de pasta blanca (típico antiguo)?
- ¿Baldosa hidráulica (patrones geométricos artesanales)?
- ¿Mármol natural (vetas orgánicas)?
- ¿Granito (moteado uniforme)?
- ¿Pizarra (superficie irregular, gris oscuro)?
- ¿Barro cocido (terracota)?
- ¿Piedra natural irregular?

Si parece OTRO material:
- ¿Moqueta/alfombra de pared a pared?
- ¿Linóleo o vinílico continuo?
- ¿Microcemento o similar (continuo, sin juntas)?
- ¿Resina epoxi?
- ¿Cemento pulido visto?

¿Qué FORMATO tienen las piezas?
- ¿Baldosas pequeñas (como las antiguas)?
- ¿Baldosas medianas (formato estándar)?
- ¿Baldosas grandes (formatos modernos)?
- ¿Planchas enormes (gran formato)?
- ¿Tablillas estrechas (parquet tradicional)?
- ¿Tablas anchas?
- ¿Lamas muy largas?

¿Qué PATRÓN de colocación ves?
- ¿Recto a junta corrida (alineado)?
- ¿Recto a matajunta (desplazado)?
- ¿Espiga clásica (45 grados)?
- ¿Espiga húngara (chevron)?
- ¿Diagonal?
- ¿Damero?
- ¿Irregular/rústico?

¿Cuál es el ESTADO del suelo?
- ¿Se ve nuevo, usado, o muy gastado?
- ¿Hay zonas de más desgaste (pasos frecuentes)?
- ¿Hay piezas rotas, fisuradas, o desportilladas?
- ¿Hay piezas que suenan huecas o se mueven?
- ¿Las juntas están bien o deterioradas?
- ¿Hay manchas, decoloraciones, o quemaduras?
- ¿El suelo está nivelado o hay desniveles visibles?

PARA REVESTIMIENTOS DE PARED — Pregúntate sobre TODO esto con igual atención:

¿Las paredes están PINTADAS?
- ¿De qué color?
- ¿Acabado mate (no refleja)?
- ¿Acabado satinado (ligero brillo)?
- ¿Acabado brillante (muy reflectante)?
- ¿Se ve la pintura uniforme o con defectos?
- ¿Se ve la textura del sustrato debajo (gotelé, etc.)?

¿Las paredes tienen PAPEL PINTADO o similar?
- ¿Es liso/texturizado sin dibujo?
- ¿Tiene patrón (¿geométrico, floral, otro?)?
- ¿De qué color o colores?
- ¿Se ve bien adherido o despegándose?

¿Las paredes están ALICATADAS (zonas húmedas)?
- ¿Hasta qué altura llega el alicatado (solo salpicadero, media altura, completo)?
- ¿De qué formato son los azulejos?
- ¿De qué color o colores?
- ¿Son lisos, con relieve, con dibujo?
- ¿Tienen brillo o son mate?
- ¿Están bien colocados o hay defectos visibles?
- ¿Las juntas están bien o ennegrecidas/deterioradas?

¿Las paredes tienen OTRO REVESTIMIENTO?
- ¿Madera (lambrin, friso)?
- ¿Corcho?
- ¿Piedra decorativa?
- ¿Ladrillo visto decorativo?
- ¿Paneles acústicos?
- ¿Espejos?
- ¿Vidrio lacado?

PARA TECHOS (acabado superficial) — Pregúntate:
- ¿Está pintado? ¿De qué color?
- ¿Es del mismo tono que las paredes o diferente?
- ¿Tiene algún tratamiento decorativo?
- ¿Está limpio o amarillento/manchado?

PARA ELEMENTOS DE TRANSICIÓN — Pregúntate sobre TODO esto con igual atención:

¿Hay RODAPIÉ/ZÓCALO?
- ¿De qué material parece (madera, MDF pintado, cerámico, aluminio, PVC)?
- ¿De qué altura aproximada (bajo, estándar, alto)?
- ¿Tiene perfil simple o con moldura?
- ¿De qué color?
- ¿Está en buen estado o deteriorado?

¿Hay CORNISA/MOLDURA de techo?
- ¿Hay moldura perimetral?
- ¿De qué estilo (simple, clásica elaborada, moderna)?
- ¿De qué material parece (escayola, poliestireno, madera)?
- ¿Está en buen estado?

¿Hay OTROS elementos de transición?
- ¿Cenefas decorativas en paredes?
- ¿Perfiles de aluminio o acero en encuentros?
- ¿Juntas de dilatación visibles?
- ¿Remates en esquinas?

En tu NARRATIVE para esta dimensión, describe cada superficie visible: qué material 
parece el suelo, qué acabado tienen las paredes, qué elementos de transición hay. 
Describe colores, formatos, patrones, estado. Usa prosa fluida.

───────────────────────────────────────────────────────────────────────────────
DIMENSIÓN 5: FIXED JOINERY & EQUIPMENT (Lo Fijo — Mobiliario Empotrado)
───────────────────────────────────────────────────────────────────────────────

Esta dimensión documenta todo el mobiliario FIJO: cocinas, baños, armarios empotrados, 
vestidores, estanterías fijas.

Si la habitación NO TIENE mobiliario fijo, indica "None" y en el narrative escribe 
"Esta habitación no tiene mobiliario fijo empotrado."

PARA COCINAS — Pregúntate sobre TODO esto con igual atención:

¿Qué MUEBLES BAJOS ves?
- ¿Cuántos módulos/cuerpos aproximadamente?
- ¿Qué distribución (lineal, en L, en U, isla)?
- ¿Las puertas son lisas completamente?
- ¿Las puertas tienen moldura (estilo shaker)?
- ¿Las puertas tienen cristal?
- ¿De qué acabado parecen (melamina, laminado, lacado, madera)?
- ¿De qué color?
- ¿Tienen tiradores visibles o son sin tirador?
- ¿Se ven en buen estado o deteriorados?

¿Qué MUEBLES ALTOS ves?
- ¿Hay muebles altos?
- ¿Llegan hasta el techo o dejan hueco?
- ¿Coinciden con los bajos en estilo?
- ¿Hay vitrinas con cristal?
- ¿Hay estantes abiertos?

¿Qué ENCIMERA ves?
- ¿De qué material parece (laminado, madera, granito, cuarzo, mármol, porcelánico)?
- ¿De qué color?
- ¿Cómo es el canto (redondeado, recto, biselado)?
- ¿Se ve en buen estado o deteriorada?

¿Qué FREGADERO ves?
- ¿De qué material (acero inoxidable, resina/composite, porcelana)?
- ¿De qué tipo (sobre encimera, bajo encimera, integrado)?
- ¿Cuántas cubetas tiene?
- ¿Tiene escurridor?

¿Qué ELECTRODOMÉSTICOS ves?
- ¿Hay placa de cocción? ¿De qué tipo (vitrocerámica, inducción, gas)?
- ¿Hay horno? ¿Dónde está ubicado?
- ¿Hay microondas? ¿Integrado o de sobremesa?
- ¿Hay nevera? ¿Integrada o vista?
- ¿Hay lavavajillas? ¿Integrado o visto?
- ¿Hay lavadora/secadora en cocina?
- ¿Qué marcas se ven?
- ¿Parecen nuevos o antiguos?

¿Qué CAMPANA ves?
- ¿Hay campana?
- ¿De qué tipo (decorativa de pared, integrada bajo mueble, de techo, telescópica)?
- ¿Parece que extrae al exterior o recircula?

¿Hay OTROS elementos?
- ¿Despensero/columna de almacenaje?
- ¿Botellero?
- ¿Especieros extraíbles?
- ¿Zona de office/mesa integrada?

PARA BAÑOS — Pregúntate sobre TODO esto con igual atención:

¿Qué INODORO ves?
- ¿Es de pie (base en el suelo) o suspendido (colgado)?
- ¿Tiene cisterna vista (baja, alta) u oculta?
- ¿La taza es redonda o alargada?
- ¿De qué color?
- ¿Se ve nuevo o antiguo?

¿Hay BIDÉ?
- ¿Sí o no?
- ¿De pie o suspendido?
- ¿A juego con el inodoro?

¿Qué LAVABO ves?
- ¿De pedestal (columna al suelo)?
- ¿De semipedestal (columna corta)?
- ¿Sobre mueble (posado encima)?
- ¿Bajo encimera (integrado por debajo)?
- ¿De pared (sin columna ni mueble)?
- ¿Integrado en encimera?
- ¿De qué material parece (porcelana, resina, cristal, piedra)?
- ¿De qué forma (rectangular, ovalado, redondo)?
- ¿De qué color?

¿Hay MUEBLE DE BAÑO?
- ¿Sí o no?
- ¿Es suspendido o con patas?
- ¿De qué acabado (melamina, lacado, madera)?
- ¿De qué color?
- ¿Cuántos cajones/puertas?
- ¿Tiene encimera integrada?

¿Qué zona de DUCHA/BAÑERA ves?
- ¿Hay bañera?
  - ¿De qué material parece (acero esmaltado, acrílico, hierro fundido)?
  - ¿De qué forma (rectangular, esquina, exenta)?
  - ¿Tiene hidromasaje?
- ¿Hay plato de ducha?
  - ¿De qué material parece (porcelana, resina, acrílico)?
  - ¿De qué forma (cuadrado, rectangular, semicircular)?
  - ¿De qué color?
- ¿Hay ducha de obra (sin plato, el suelo continúa)?
- ¿Cuál es el cerramiento?
  - ¿Mampara fija?
  - ¿Mampara corredera?
  - ¿Mampara abatible?
  - ¿Mampara plegable?
  - ¿Cortina?
  - ¿Sin cerramiento?
- Si hay mampara, ¿el vidrio es transparente, translúcido, o serigrafiado?

PARA ARMARIOS EMPOTRADOS/VESTIDORES — Pregúntate sobre TODO esto:

¿Qué tipo de ARMARIO ves?
- ¿Empotrado con puertas correderas?
- ¿Empotrado con puertas batientes/abatibles?
- ¿Empotrado con puertas plegables?
- ¿Vestidor abierto (sin puertas)?
- ¿Frente de armario solamente (no ves interior)?

¿De qué ACABADO son las puertas?
- ¿Espejo?
- ¿Melamina lisa?
- ¿Melamina imitación madera?
- ¿Lacado?
- ¿Cristal translúcido?
- ¿De qué color?

Si se ve el INTERIOR:
- ¿Hay baldas? ¿Fijas o regulables?
- ¿Hay barras de colgar?
- ¿Hay cajoneras?
- ¿Hay zapatero?
- ¿Hay otros organizadores?

¿En qué ESTADO se ve?
- ¿Las puertas funcionan bien o están atascadas/desalineadas?
- ¿Los acabados están bien o deteriorados?
- ¿El interior está limpio u organizado?

PARA OTROS ELEMENTOS FIJOS — ¿Ves...?
- ¿Estanterías empotradas en pared?
- ¿Librerías fijas?
- ¿Escritorio empotrado?
- ¿Banco corrido bajo ventana?
- ¿Chimenea fija (no estufa)?
- ¿Radiador empotrado en mueble?

En tu NARRATIVE para esta dimensión, describe todo el mobiliario fijo que veas: 
cocina completa, baño completo, armarios. Describe materiales, colores, configuración,
estado. Usa prosa fluida.

───────────────────────────────────────────────────────────────────────────────
DIMENSIÓN 6: DETAILS & FITTINGS (Los Detalles — Herrajes y Accesorios)
───────────────────────────────────────────────────────────────────────────────

Esta dimensión documenta los pequeños detalles que definen el nivel de acabado: 
manillas, tiradores, grifería, accesorios, remates.

PARA MANILLAS DE PUERTAS — Pregúntate sobre TODO esto con igual atención:

¿Qué TIPO de manilla ves?
- ¿Manilla (palanca que se baja)?
- ¿Pomo (esfera que se gira)?
- ¿Tirador (barra que se tira)?
- ¿Otro tipo?

¿De qué FORMA es la manilla?
- ¿Recta simple (tipo L)?
- ¿Curvada ergonómica?
- ¿De diseño (formas especiales)?
- ¿Clásica ornamentada?

¿De qué ACABADO/COLOR parece ser?
- ¿Latón brillante (dorado)?
- ¿Latón satinado/mate?
- ¿Latón envejecido?
- ¿Cromo brillante (plateado espejo)?
- ¿Cromo satinado/mate?
- ¿Acero inoxidable?
- ¿Negro mate?
- ¿Níquel cepillado?
- ¿Bronce?
- ¿Blanco?
- ¿Otro color?

¿Tiene ESCUDO o roseta?
- ¿Placa rectangular alrededor (escudo)?
- ¿Círculo pequeño (roseta)?
- ¿Sin ninguno?

¿En qué ESTADO se ve?
- ¿Brillante y bien conservada?
- ¿Con pátina de uso?
- ¿Deteriorada, oxidada, suelta?

PARA TIRADORES DE MUEBLES — Pregúntate sobre TODO esto con igual atención:

¿Qué TIPO de tirador ves?
- ¿Pomo (botón)?
- ¿Tirador de barra?
- ¿Tirador de arco?
- ¿Uñero (ranura para dedos)?
- ¿Gola (perfil en canto)?
- ¿Sin tirador (push-click)?
- ¿Otro tipo?

¿De qué ACABADO/MATERIAL parecen ser?
- ¿Acero inoxidable?
- ¿Aluminio?
- ¿Cromo?
- ¿Latón?
- ¿Negro mate?
- ¿Porcelana/cerámica?
- ¿Plástico?
- ¿Cuero?
- ¿Otro?

¿Son todos IGUALES o hay mezcla?
- ¿Todos los tiradores de la vivienda son del mismo estilo?
- ¿Hay diferentes estilos en diferentes zonas?

PARA GRIFERÍA — Pregúntate sobre TODO esto con igual atención:

¿Qué TIPO de grifo ves?
- ¿Monomando (una sola palanca)?
- ¿Bimando/mezclador (dos mandos)?
- ¿Termostático (con selector de temperatura)?
- ¿De caño alto?
- ¿De caño bajo?
- ¿Extraíble?
- ¿De pared (empotrado)?
- ¿Cascada?
- ¿De sensor automático?

¿De qué ACABADO parece ser?
- ¿Cromo brillante?
- ¿Cromo cepillado/satinado?
- ¿Negro mate?
- ¿Dorado/oro?
- ¿Bronce?
- ¿Blanco?
- ¿Acero inoxidable?
- ¿Bicolor?

¿Qué MARCA parece ser (si visible)?
- ¿Grohe, Hansgrohe, Roca, Tres, Gessi, otra marca visible?
- ¿Marca genérica o no visible?

¿En qué ESTADO se ve?
- ¿Brillante, limpio?
- ¿Con cal acumulada?
- ¿Manchado, deteriorado?
- ¿Goteando?

PARA ACCESORIOS DE BAÑO — Pregúntate sobre TODO esto con igual atención:

¿Qué ESPEJO ves?
- ¿Solo luna pegada a pared?
- ¿Espejo con marco (¿de qué material/color?)?
- ¿Espejo integrado en mueble?
- ¿Espejo con luz perimetral?
- ¿Espejo con antivaho?
- ¿Armario con espejo?

¿Qué ILUMINACIÓN de espejo ves?
- ¿Apliques laterales?
- ¿Luz superior?
- ¿LED perimetral integrado?
- ¿Sin iluminación de espejo?

¿Qué TOALLEROS ves?
- ¿Barra fija?
- ¿Anilla?
- ¿Toallero escalera?
- ¿Radiador toallero?
- ¿Gancho simple?

¿Qué OTROS ACCESORIOS ves?
- ¿Portarrollos (¿empotrado, de pared, de pie?)?
- ¿Jabonera?
- ¿Vaso/portacepillos?
- ¿Escobillero?
- ¿Repisa/balda?
- ¿Dispensador de jabón?
- ¿Secador de manos?

¿Son todos del MISMO CONJUNTO?
- ¿Los accesorios parecen a juego?
- ¿Son de diferentes estilos/épocas?

PARA MECANISMOS ELÉCTRICOS (estética) — Pregúntate:

¿Qué ESTILO de mecanismos ves?
- ¿Blancos básicos estándar?
- ¿Blancos de diseño (líneas más limpias)?
- ¿De aluminio/metálicos?
- ¿Negros?
- ¿De otros colores?
- ¿Smart/táctiles?
- ¿Antiguos de baquelita?

¿Qué MARCA parecen (si reconocible)?
- ¿Simon, Legrand, Schneider, BTicino, Jung, otra?
- ¿Genéricos?

¿Son todos COHERENTES?
- ¿Todos los mecanismos son del mismo estilo?
- ¿Hay mezcla de épocas/estilos?

PARA CALIDAD DE EJECUCIÓN GENERAL — Pregúntate:

¿Cómo se ven los REMATES de silicona?
- ¿Limpios y uniformes?
- ¿Amarillentos?
- ¿Con moho?
- ¿Despegados o rotos?

¿Cómo se ven las JUNTAS de azulejo?
- ¿Limpias y uniformes?
- ¿De qué color?
- ¿Ennegrecidas/con moho?
- ¿Desiguales o rotas?

¿Cómo es la COHERENCIA general?
- ¿Todo parece planificado y coordinado?
- ¿Hay mezcla de estilos sin coherencia?
- ¿Se nota trabajo profesional o bricolaje?

En tu NARRATIVE para esta dimensión, describe la "joyería" de la vivienda: manillas, 
tiradores, grifos, accesorios, la calidad de los remates. Describe acabados, estilos, 
coherencia. Usa prosa fluida.

═══════════════════════════════════════════════════════════════════════════════
TRIGGERS — ELEMENTOS QUE REQUIEREN INTERVENCIÓN
═══════════════════════════════════════════════════════════════════════════════

Además de las 6 dimensiones por habitación, identifica TRIGGERS a nivel de propiedad. 
Un trigger es algo que observas que claramente requiere intervención - no una opinión 
sobre si algo es "feo", sino evidencia objetiva de un problema o carencia.

Para cada trigger, explica tu razonamiento en "detailed_reasoning" referenciando 
las dimensiones y habitaciones donde observaste las evidencias.

═══════════════════════════════════════════════════════════════════════════════
LA PROPIEDAD COMO CONJUNTO
═══════════════════════════════════════════════════════════════════════════════

En "property_narrative", integra tus observaciones de todas las habitaciones para 
contar la historia de la vivienda: qué época representa, qué intervenciones ha tenido, 
qué coherencia tiene el conjunto, qué carácter tiene.

En "renovation_context", resume el estado general observado y qué tipo de 
intervenciones parecen necesarias basándote en las evidencias documentadas.

═══════════════════════════════════════════════════════════════════════════════
FORMATO DE SALIDA
═══════════════════════════════════════════════════════════════════════════════

JSON estructurado con TODOS los campos. Las narrativas deben ser EXTENSAS - varios 
párrafos cada una. No te preocupes por la longitud, preocúpate por la COMPLETITUD.

Recuerda: otro profesional tan capaz como tú va a leer esto SIN ver las fotos. 
Si omites algo, tendrá que inventarlo. Si describes algo vagamente, tendrá que adivinar.
"""

    if focus_room_id:
        prompt += f"""

INSTRUCCIÓN CRÍTICA (FOCO DE ESTA LLAMADA):
- Solo debes analizar y devolver UNA habitación: room_id="{focus_room_id}".
- En "rooms" devuelve exactamente 1 elemento (esa habitación). No inventes otras habitaciones.
- Aun así, rellena building_profile, design_profile, triggers, y property_narrative con lo que puedas inferir de estas fotos.
"""
    
    return prompt


# =============================================================================
# VALIDATION
# =============================================================================

def _validate_pir_room_ids(pir: Dict[str, Any], canonical_ids: Set[str]) -> Dict[str, Any]:
    """Validate PIR room_ids match canonical set from clustering."""
    
    rooms = pir.get("rooms", [])
    found_ids = set()
    invalid = []
    
    for room in rooms:
        room_id = room.get("room_id", "")
        found_ids.add(room_id)
        if room_id not in canonical_ids:
            invalid.append(room_id)
    
    missing = list(canonical_ids - found_ids)
    
    return {
        "valid": len(invalid) == 0,
        "invalid_rooms": invalid,
        "missing_rooms": missing,
        "analyzed_count": len(rooms),
        "expected_count": len(canonical_ids)
    }


# =============================================================================
# TARGET PIR GENERATOR
# =============================================================================

async def generate_target_pir(
    listing_id: int,
    listing_data: Dict[str, Any],
    room_clusters: List[Dict[str, Any]],
    year_built: int,
    year_source: str,
    smart_m2_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate Property Intelligence Report for target property.
    
    The target PIR is the foundation of the renovation estimate.
    It identifies triggers, regulatory issues, and room conditions.
    
    Args:
        smart_m2_data: Optional dict from smart_m2 step containing room dimensions.
                       If available, the PIR will reference specific wall dimensions
                       in visual narratives (e.g., "the long wall (4.2m)").
                       This is critical for Phase 1 (Scope + BoQ) quantity calculations.
    """
    logger.info("═" * 79)
    logger.info(f"PIR GENERATION (Target) - Listing {listing_id}")
    logger.info("═" * 79)
    
    # Validate inputs
    if not room_clusters:
        raise InsufficientDataError("Target", listing_id, "No room clusters")
    
    if len(room_clusters) < MIN_ROOMS_TARGET:
        raise InsufficientDataError(
            "Target", listing_id, 
            f"Need {MIN_ROOMS_TARGET}+ rooms, got {len(room_clusters)}"
        )
    
    # Build canonical room_ids from clusters
    canonical_room_ids = [
        {"room_id": c.get("cluster_id", f"room_{i}"), "room_name": c.get("cluster_name", f"Room {i+1}")}
        for i, c in enumerate(room_clusters)
    ]
    canonical_set = set(r["room_id"] for r in canonical_room_ids)
    logger.info(f"  → Canonical room_ids: {list(canonical_set)}")
    
    # Load knowledge
    knowledge = _load_knowledge_bases()
    
    # Get applicable rules based on property year
    # These are rules that COULD apply given the property's age
    rules_applicable = []
    rules_engine = knowledge.get("rules", {})
    if rules_engine:
        for rule in rules_engine.get('rules', []):
            if isinstance(rule, dict):
                year_trigger = rule.get('year_trigger', 0)
                if year_built < year_trigger:
                    rules_applicable.append(rule)
        logger.info(f"  → {len(rules_applicable)} rules applicable for year {year_built}")

    # Collect photos from clusters with mapping
    all_photos: List[str] = []
    photo_to_cluster: Dict[str, str] = {}  # source -> cluster_name mapping
    for cluster in room_clusters:
        cluster_name = cluster.get("cluster_name", cluster.get("cluster_id", "unknown"))
        for src in cluster.get("photo_urls", []) or []:
            if not src:
                continue
            all_photos.append(str(src))
            photo_to_cluster[str(src)] = str(cluster_name)
    
    logger.info(f"  → Fetching ALL_PHOTOS images: {len(all_photos)} sources (from {len(room_clusters)} clusters)...")
    fetched = await fetch_images_batch(all_photos)
    if not isinstance(fetched, list):
        raise RuntimeError(f"fetch_images_batch returned unexpected type: {type(fetched).__name__}")

    img_by_src: Dict[str, Any] = {}
    ok = 0
    for src, img in zip(all_photos, fetched):
        img_by_src[str(src)] = img
        if img is not None:
            ok += 1
    logger.info(f"  → Fetched: {ok}/{len(all_photos)}")
    
    if ok < MIN_IMAGES_TARGET:
        raise InsufficientDataError("Target", listing_id, f"Need {MIN_IMAGES_TARGET}+ images, got {ok}")

    if smart_m2_data:
        logger.info(f"  → Smart M2 data included: {len(smart_m2_data.get('rooms', []))} rooms with dimensions")

    system_prompt = _build_system_prompt(knowledge)

    # One Gemini call per room, in parallel (bounded).
    room_concurrency = int(os.getenv("TARGET_PIR_ROOM_CONCURRENCY", "3"))
    room_concurrency = max(1, room_concurrency)
    sem = asyncio.Semaphore(room_concurrency)

    async def _one_room(cluster: Dict[str, Any]) -> Dict[str, Any]:
        cluster_id = str(cluster.get("cluster_id") or "").strip()
        cluster_name = str(cluster.get("cluster_name") or cluster_id or "unknown").strip()
        if not cluster_id:
            raise ValueError(f"target_pir: cluster missing cluster_id | cluster_name={cluster_name}")

        sources = [str(s) for s in (cluster.get("photo_urls") or []) if s]
        room_images = [img_by_src.get(s) for s in sources if img_by_src.get(s) is not None]
        if not room_images:
            raise InsufficientDataError("Target", listing_id, f"Room {cluster_id} has 0 fetched images")

        # Keep Smart M2 context tight: only include this room’s ledger.
        room_smart_m2 = None
        if smart_m2_data and isinstance(smart_m2_data.get("rooms"), list):
            matches = []
            for r in smart_m2_data.get("rooms") or []:
                if not isinstance(r, dict):
                    continue
                if str(r.get("room_id") or "").strip() == cluster_id:
                    matches.append(r)
            if matches:
                room_smart_m2 = {"rooms": matches}

        user_prompt = _build_user_prompt(
            listing_data=listing_data,
            room_clusters=[cluster],
            canonical_room_ids=[{"room_id": cluster_id, "room_name": cluster_name}],
            year_built=year_built,
            year_source=year_source,
            property_type="target",
            rules_applicable=rules_applicable,
            smart_m2_data=room_smart_m2,
            photo_urls=None,
            focus_room_id=cluster_id,
        )

        async with sem:
            logger.info(
                f"  → [room:{cluster_id}] Gemini Pro | images={len(room_images)} | name={cluster_name}"
            )
            response = await call_gemini(
                prompt=user_prompt,
                model="pro",
                images=room_images,
                temperature=0.2,
                max_tokens=65000,
                response_schema=PIR_SCHEMA,
                system_instruction=system_prompt,
                use_spanish=True,
            )

        if not response.success:
            raise GeminiCallError(
                listing_id, f"room={cluster_id} | {response.error or 'Unknown error'}"
            )

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise GeminiCallError(listing_id, f"room={cluster_id} | JSON parse failed: {e}")

        return data

    logger.info(
        "  → Calling Gemini Pro per-room (parallel) | rooms=%s | concurrency=%s",
        len(room_clusters),
        room_concurrency,
    )
    room_results = await asyncio.gather(*[_one_room(c) for c in room_clusters])

    # Merge per-room PIRs into a single PIR (rooms are disjoint; other fields are de-duped).
    merged_rooms: List[Dict[str, Any]] = []
    merged_triggers: List[Dict[str, Any]] = []
    merged_flags: List[Dict[str, Any]] = []
    building_profile: Dict[str, Any] = {}
    design_profile: Dict[str, Any] = {}
    property_narrative = ""
    renovation_context = ""

    seen_trigger_keys: Set[str] = set()
    seen_flag_keys: Set[str] = set()

    for idx, part in enumerate(room_results):
        if not isinstance(part, dict):
            raise RuntimeError(f"target_pir merge: room result not dict | idx={idx} type={type(part).__name__}")

        if idx == 0:
            building_profile = part.get("building_profile") or {}
            design_profile = part.get("design_profile") or {}
            property_narrative = str(part.get("property_narrative") or "").strip()
            renovation_context = str(part.get("renovation_context") or "").strip()

        for r in part.get("rooms") or []:
            if isinstance(r, dict):
                merged_rooms.append(r)

        for t in part.get("triggers") or []:
            if not isinstance(t, dict):
                continue
            key = f"{t.get('category','')}|{t.get('trigger','')}"
            if key in seen_trigger_keys:
                continue
            seen_trigger_keys.add(key)
            merged_triggers.append(t)

        for f in part.get("regulatory_flags") or []:
            if not isinstance(f, dict):
                continue
            key = str(f.get("rule_id") or "").strip()
            if not key or key in seen_flag_keys:
                continue
            seen_flag_keys.add(key)
            merged_flags.append(f)

    pir: Dict[str, Any] = {
        "building_profile": building_profile,
        "rooms": merged_rooms,
        "design_profile": design_profile,
        "triggers": merged_triggers,
        "regulatory_flags": merged_flags,
        "property_narrative": property_narrative,
        "renovation_context": renovation_context,
    }
    
    # Validate room_ids
    validation = _validate_pir_room_ids(pir, canonical_set)
    if not validation["valid"]:
        raise ValidationError(listing_id, validation["invalid_rooms"], canonical_set)
    
    if validation["missing_rooms"]:
        logger.warning(f"  ⚠ Rooms not analyzed: {validation['missing_rooms']}")
    
    # Add metadata
    pir["_metadata"] = {
        "listing_id": listing_id,
        "type": "target",
        "generated_at": datetime.now().isoformat(),
        "version": "v0.5.0",
        "photo_count": ok,
        "room_count": validation["analyzed_count"],
        "room_parallel": True,
        "room_concurrency": room_concurrency,
    }
    
    logger.info(f"  ✓ Target PIR complete: {validation['analyzed_count']} rooms")
    return pir


# =============================================================================
# COMPARABLE PIR GENERATOR — REMOVED
# =============================================================================
# V5 replaced per-comparable PIR with v5_generate_selected_comparable_room_pirs
# which runs room-level PIR on the ONE selected comparable only.
# Old generate_comparable_pir + generate_pirs_batch removed (dead code).
# See git history for the original implementation.
#
# =============================================================================
# V2 ARCHITECTURE (2026-01-16)
# =============================================================================
# The previous bracket-based approach (generate_bracket_pir, synthesize_local_market_context,
# generate_strategic_reasoning) has been DELETED.
#
# V2 uses data-driven comparable analysis with:
# - strategy_selector.py: Analyzes ALL comparables to identify 3 renovation strategies
# - delta_scope_generator.py: Calculates delta scope from target to each strategy
#
# PIRs are now generated using the new 6-DIMENSION framework for both target
# and comparables. The dimensions provide structured analysis of:
# 1. Shell & Preparation (Masonry/Plaster)
# 2. Apertures & Enclosure (Joinery/Glazing)
# 3. Systems & Services (MEP)
# 4. Surface Finishes (Decor)
# 5. Fixed Joinery & Equipment (Fittings)
# 6. Details & Fittings (Hardware)
#
# See: V2_IMPLEMENTATION_PLAN.md for full architecture documentation.
# =============================================================================
