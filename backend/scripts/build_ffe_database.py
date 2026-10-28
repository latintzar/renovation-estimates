#!/usr/bin/env python3
"""
=============================================================================
build_ffe_database.py - Build the complete FFE SQLite Database
=============================================================================

PURPOSE: Create ffe.db with ~120 granular FF&E items for the Unified Estimator.

DESIGN PRINCIPLES:
- Granular items (not bundles) - same precision as BCCA
- 4 tiers with low/mid/high values each
- Every item has documented basis_notes with sources
- Complete coverage (non-pareto) - all items a property might need

CATEGORIES:
1. KITCHEN_APPLIANCES (~15 items) - COLD, COOKING, CLEANING
2. LIVING_FURNITURE (~12 items) - SEATING, TABLES, STORAGE
3. DINING_FURNITURE (~7 items)
4. BEDROOM_FURNITURE (~12 items) - SLEEPING, STORAGE, CHILDREN
5. BATHROOM_FFE (~6 items)
6. LIGHTING (~8 items)
7. TEXTILES (~10 items) - WINDOW, FLOOR, SOFT
8. OUTDOOR (~6 items)
9. HOME_OFFICE (~5 items)
10. LAUNDRY (~4 items)
11. STORAGE_GENERAL (~4 items)
12. DECOR (~6 items)

TOTAL: ~95-100 items with full documentation

USAGE:
    python build_ffe_database.py

OUTPUT:
    Lean MVP/backend/pricing/data/ffe.db
    
AUTHOR: Reformia Team
DATE: 2026-01-11
VERSION: 1.0.0
=============================================================================
"""

import sqlite3
import json
import os
from datetime import date
from typing import Optional, List
from dataclasses import dataclass, asdict

# =============================================================================
# OUTPUT PATH
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "..", "pricing", "data", "ffe.db")

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class FFECategory:
    """Top-level category definition."""
    code: str
    name_es: str
    name_en: str
    description_es: str
    icon: str

@dataclass
class FFESubcategory:
    """Subcategory within a category."""
    code: str
    category_code: str
    name_es: str
    name_en: str

@dataclass
class FFEItem:
    """
    A single FF&E item with full tier pricing.
    
    Price Tiers:
    - budget: IKEA, Beko, basic brands
    - mid: Kave Home, Balay/Bosch, Spanish mid-market
    - high: Treku, Siemens, Spanish/German premium
    - luxury: Poliform, Gaggenau, designer grade
    
    Each tier has low/mid/high values. Use 'mid' for estimates.
    """
    code: str
    category_code: str
    subcategory_code: Optional[str]
    
    name_es: str
    name_en: str
    description_es: str
    typical_specs: str
    
    # Tier pricing: (low, mid, high) - use mid for estimates
    # None for high means open-ended (luxury)
    budget_low: float
    budget_mid: float
    budget_high: float
    
    mid_low: float
    mid_mid: float
    mid_high: float
    
    high_low: float
    high_mid: float
    high_high: float
    
    luxury_low: float
    luxury_mid: Optional[float]
    luxury_high: Optional[float]
    
    # Measurement
    unit: str  # 'ud', 'ml', 'pair', 'set', 'pack'
    typical_quantity: str  # "1 per kitchen", "4-6 per dining"
    
    # Metadata
    investment_priority: str  # 'alta', 'media', 'baja'
    lifespan_years: int
    energy_relevant: bool
    
    # Reference brands (lists)
    brands_budget: List[str]
    brands_mid: List[str]
    brands_high: List[str]
    brands_luxury: List[str]
    
    # Documentation (CRITICAL)
    basis_notes: str
    source_retailers: List[str]
    source_year: int
    
    # Style matching (for adaptation framework) - with defaults
    # These help Gemini match comparable photos to DB items
    # Most items are "generic" style - Gemini adapts at selection time
    style_tags: List[str] = None      # ["nórdico", "minimalista", "contemporáneo"]
    material_tags: List[str] = None   # ["madera", "tela", "metal"]
    finish_tags: List[str] = None     # ["natural", "lacado", "tapizado"]
    design_era: str = "contemporáneo" # "clásico", "moderno", "contemporáneo", "atemporal"
    size_category: str = "medium"     # "compact", "medium", "large", "varies"
    
    def __post_init__(self):
        """Set default values for style fields if None."""
        if self.style_tags is None:
            self.style_tags = ["contemporáneo"]
        if self.material_tags is None:
            self.material_tags = ["varies"]
        if self.finish_tags is None:
            self.finish_tags = ["varies"]


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

SCHEMA_SQL = """
-- =============================================================================
-- FFE Database Schema v1.0
-- Granular FF&E pricing for Unified Estimator
-- =============================================================================

-- Categories
CREATE TABLE IF NOT EXISTS ffe_categories (
    code TEXT PRIMARY KEY,
    name_es TEXT NOT NULL,
    name_en TEXT,
    description_es TEXT,
    icon TEXT
);

-- Subcategories
CREATE TABLE IF NOT EXISTS ffe_subcategories (
    code TEXT PRIMARY KEY,
    category_code TEXT NOT NULL,
    name_es TEXT NOT NULL,
    name_en TEXT,
    FOREIGN KEY (category_code) REFERENCES ffe_categories(code)
);

-- Items (granular products)
CREATE TABLE IF NOT EXISTS ffe_items (
    code TEXT PRIMARY KEY,
    category_code TEXT NOT NULL,
    subcategory_code TEXT,
    
    name_es TEXT NOT NULL,
    name_en TEXT,
    description_es TEXT,
    typical_specs TEXT,
    
    -- Tier pricing (low/mid/high per tier)
    budget_low REAL,
    budget_mid REAL,
    budget_high REAL,
    
    mid_low REAL,
    mid_mid REAL,
    mid_high REAL,
    
    high_low REAL,
    high_mid REAL,
    high_high REAL,
    
    luxury_low REAL,
    luxury_mid REAL,
    luxury_high REAL,
    
    -- Measurement
    unit TEXT DEFAULT 'ud',
    typical_quantity TEXT,
    
    -- Metadata
    investment_priority TEXT,
    lifespan_years INTEGER,
    energy_relevant BOOLEAN DEFAULT 0,
    
    -- Brands (JSON arrays)
    brands_budget TEXT,
    brands_mid TEXT,
    brands_high TEXT,
    brands_luxury TEXT,
    
    -- Style matching (for adaptation framework)
    -- These help Gemini match comparable photos to DB items
    style_tags TEXT,         -- JSON: ["nórdico", "minimalista"]
    material_tags TEXT,      -- JSON: ["madera", "tela", "metal"]
    finish_tags TEXT,        -- JSON: ["natural", "lacado", "tapizado"]
    design_era TEXT,         -- "clásico", "moderno", "contemporáneo", "atemporal"
    size_category TEXT,      -- "compact", "medium", "large", "varies"
    
    -- Documentation
    basis_notes TEXT NOT NULL,
    source_retailers TEXT,
    source_year INTEGER,
    last_updated DATE,
    
    FOREIGN KEY (category_code) REFERENCES ffe_categories(code),
    FOREIGN KEY (subcategory_code) REFERENCES ffe_subcategories(code)
);

-- Indices for discovery
CREATE INDEX IF NOT EXISTS idx_ffe_category ON ffe_items(category_code);
CREATE INDEX IF NOT EXISTS idx_ffe_subcategory ON ffe_items(subcategory_code);
CREATE INDEX IF NOT EXISTS idx_ffe_priority ON ffe_items(investment_priority);
CREATE INDEX IF NOT EXISTS idx_ffe_style ON ffe_items(style_tags);
CREATE INDEX IF NOT EXISTS idx_ffe_design_era ON ffe_items(design_era);
CREATE INDEX IF NOT EXISTS idx_ffe_energy ON ffe_items(energy_relevant);
"""


# =============================================================================
# CATEGORIES DEFINITION
# =============================================================================

CATEGORIES = [
    FFECategory(
        code="KITCHEN_APPLIANCES",
        name_es="Electrodomésticos de Cocina",
        name_en="Kitchen Appliances",
        description_es="Frigoríficos, hornos, placas, lavavajillas, lavadoras",
        icon="appliances"
    ),
    FFECategory(
        code="LIVING_FURNITURE",
        name_es="Mobiliario de Salón",
        name_en="Living Room Furniture",
        description_es="Sofás, mesas de centro, muebles TV, estanterías",
        icon="sofa"
    ),
    FFECategory(
        code="DINING_FURNITURE",
        name_es="Mobiliario de Comedor",
        name_en="Dining Furniture",
        description_es="Mesas de comedor, sillas, taburetes",
        icon="dining"
    ),
    FFECategory(
        code="BEDROOM_FURNITURE",
        name_es="Mobiliario de Dormitorio",
        name_en="Bedroom Furniture",
        description_es="Camas, colchones, mesitas, armarios",
        icon="bed"
    ),
    FFECategory(
        code="BATHROOM_FFE",
        name_es="Accesorios de Baño",
        name_en="Bathroom Accessories",
        description_es="Espejos, toalleros, accesorios (no sanitarios)",
        icon="bathroom"
    ),
    FFECategory(
        code="LIGHTING",
        name_es="Iluminación Decorativa",
        name_en="Decorative Lighting",
        description_es="Lámparas colgantes, de pie, de mesa, apliques",
        icon="lamp"
    ),
    FFECategory(
        code="TEXTILES",
        name_es="Textiles y Complementos",
        name_en="Textiles & Soft Furnishings",
        description_es="Cortinas, alfombras, ropa de cama, cojines",
        icon="textiles"
    ),
    FFECategory(
        code="OUTDOOR",
        name_es="Mobiliario Exterior",
        name_en="Outdoor Furniture",
        description_es="Mesas, sillas, tumbonas, sombrillas de terraza",
        icon="outdoor"
    ),
    FFECategory(
        code="HOME_OFFICE",
        name_es="Despacho / Oficina en Casa",
        name_en="Home Office",
        description_es="Escritorios, sillas de oficina, estanterías",
        icon="office"
    ),
    FFECategory(
        code="LAUNDRY",
        name_es="Lavandería",
        name_en="Laundry",
        description_es="Lavadora, secadora, tendedero, muebles lavandería",
        icon="laundry"
    ),
    FFECategory(
        code="STORAGE",
        name_es="Almacenaje General",
        name_en="General Storage",
        description_es="Estanterías, cajoneras, organizadores",
        icon="storage"
    ),
    FFECategory(
        code="DECOR",
        name_es="Decoración",
        name_en="Decor",
        description_es="Arte, plantas, jarrones, objetos decorativos",
        icon="decor"
    ),
]


# =============================================================================
# SUBCATEGORIES DEFINITION
# =============================================================================

SUBCATEGORIES = [
    # Kitchen
    FFESubcategory("COLD", "KITCHEN_APPLIANCES", "Frío", "Cold Storage"),
    FFESubcategory("COOKING", "KITCHEN_APPLIANCES", "Cocción", "Cooking"),
    FFESubcategory("CLEANING", "KITCHEN_APPLIANCES", "Limpieza/Lavado", "Cleaning"),
    FFESubcategory("SMALL_APPLIANCES", "KITCHEN_APPLIANCES", "Pequeño Electrodoméstico", "Small Appliances"),
    
    # Living
    FFESubcategory("SEATING", "LIVING_FURNITURE", "Asientos", "Seating"),
    FFESubcategory("TABLES", "LIVING_FURNITURE", "Mesas", "Tables"),
    FFESubcategory("STORAGE_LIVING", "LIVING_FURNITURE", "Almacenaje Salón", "Living Storage"),
    
    # Bedroom
    FFESubcategory("SLEEPING", "BEDROOM_FURNITURE", "Descanso", "Sleeping"),
    FFESubcategory("BEDROOM_STORAGE", "BEDROOM_FURNITURE", "Almacenaje Dormitorio", "Bedroom Storage"),
    FFESubcategory("CHILDREN", "BEDROOM_FURNITURE", "Infantil", "Children"),
    
    # Textiles
    FFESubcategory("WINDOW", "TEXTILES", "Ventanas", "Window Treatments"),
    FFESubcategory("FLOOR", "TEXTILES", "Suelo", "Floor Coverings"),
    FFESubcategory("SOFT", "TEXTILES", "Ropa de Cama", "Soft Furnishings"),
]


# =============================================================================
# ITEMS: KITCHEN APPLIANCES
# =============================================================================

KITCHEN_APPLIANCES = [
    # =========================================================================
    # COLD STORAGE
    # =========================================================================
    FFEItem(
        code="FFE_APP_FRIDGE_COMBI",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COLD",
        name_es="Frigorífico combi",
        name_en="Combi fridge-freezer",
        description_es="Frigorífico-congelador combinado. Budget: plástico interior, clase A. Mid: inox antihuellas, No Frost total, A+. High: BioFresh, WiFi. Luxury: panelable, columna completa.",
        typical_specs="180-200cm altura, 300-400L total, 70-100L congelador",
        budget_low=350, budget_mid=450, budget_high=550,
        mid_low=600, mid_mid=800, mid_high=1000,
        high_low=1200, high_mid=1600, high_high=2000,
        luxury_low=2500, luxury_mid=3500, luxury_high=None,
        unit="ud", typical_quantity="1 per kitchen",
        investment_priority="alta", lifespan_years=12, energy_relevant=True,
        brands_budget=["Beko", "Indesit", "Teka", "Hisense"],
        brands_mid=["Balay", "Bosch", "Samsung", "LG"],
        brands_high=["Siemens iQ500/700", "Neff", "Miele", "Liebherr"],
        brands_luxury=["Gaggenau", "Sub-Zero", "Miele MasterCool"],
        basis_notes="MediaMarkt/El Corte Inglés price survey Dec 2024. Budget anchor: Beko RCNA366K40XBN (€449). Mid anchor: Bosch KGN39VIEA (€799). High anchor: Siemens KG39NAICT (€1,499). Luxury: Gaggenau panelable starts €3,000. Energy class A or better only. Prices include IVA.",
        source_retailers=["MediaMarkt", "El Corte Inglés", "Worten"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_FRIDGE_AMERICAN",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COLD",
        name_es="Frigorífico americano side-by-side",
        name_en="American side-by-side fridge",
        description_es="Frigorífico grande tipo americano con dispensador. Budget: sin dispensador. Mid: dispensador agua. High: dispensador hielo, InstaView. Luxury: built-in integrado.",
        typical_specs="180cm altura, 90cm ancho, 500-600L total",
        budget_low=700, budget_mid=900, budget_high=1100,
        mid_low=1200, mid_mid=1600, mid_high=2000,
        high_low=2200, high_mid=2800, high_high=3500,
        luxury_low=5000, luxury_mid=7000, luxury_high=None,
        unit="ud", typical_quantity="1 per large kitchen",
        investment_priority="media", lifespan_years=12, energy_relevant=True,
        brands_budget=["Hisense", "Beko", "Haier"],
        brands_mid=["Samsung", "LG", "Bosch"],
        brands_high=["LG InstaView", "Samsung Bespoke", "Siemens"],
        brands_luxury=["Sub-Zero", "Liebherr Monolith", "Gaggenau"],
        basis_notes="MediaMarkt survey Dec 2024. Hisense RS670 (€899). Samsung RS68A (€1,599). LG InstaView (€2,799). Sub-Zero starts €5,000+. Less common in Spanish apartments - mostly for chalets/large kitchens.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_FRIDGE_INTEGRABLE",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COLD",
        name_es="Frigorífico integrable",
        name_en="Built-in integrated fridge",
        description_es="Frigorífico para integrar en columna de cocina. Budget: básico. Mid: No Frost, buen aislamiento. High: zona 0°C, iluminación LED. Luxury: columna completa premium.",
        typical_specs="177cm altura para integrar en columna 180cm",
        budget_low=400, budget_mid=550, budget_high=700,
        mid_low=800, mid_mid=1000, mid_high=1200,
        high_low=1400, high_mid=1800, high_high=2200,
        luxury_low=2800, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="1 per integrated kitchen",
        investment_priority="alta", lifespan_years=12, energy_relevant=True,
        brands_budget=["Beko", "Teka", "Candy"],
        brands_mid=["Balay", "Bosch", "Electrolux"],
        brands_high=["Siemens", "Neff", "Miele"],
        brands_luxury=["Gaggenau", "Miele MasterCool"],
        basis_notes="Price premium ~20-30% over freestanding for integration. Balay 3FIB3720 (€999). Siemens KI81RADE0 (€1,699). Common in modern Spanish kitchens with integrated design.",
        source_retailers=["MediaMarkt", "El Corte Inglés", "Teka stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_FREEZER_VERTICAL",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COLD",
        name_es="Congelador vertical",
        name_en="Upright freezer",
        description_es="Congelador vertical independiente. Budget: manual. Mid: No Frost. High: cajones organizados, alarma puerta. Luxury: integrable premium.",
        typical_specs="155-185cm altura, 200-280L capacidad",
        budget_low=250, budget_mid=350, budget_high=450,
        mid_low=500, mid_mid=650, mid_high=800,
        high_low=900, high_mid=1200, high_high=1500,
        luxury_low=1800, luxury_mid=2500, luxury_high=None,
        unit="ud", typical_quantity="0-1 per property (optional)",
        investment_priority="baja", lifespan_years=15, energy_relevant=True,
        brands_budget=["Beko", "Indesit", "Candy"],
        brands_mid=["Balay", "Bosch", "AEG"],
        brands_high=["Liebherr", "Siemens", "Miele"],
        brands_luxury=["Liebherr Premium", "Miele FN"],
        basis_notes="Optional item - only ~30% of Spanish households have separate freezer. Beko RFNE312 (€349). Bosch GSN58AWEV (€699). Liebherr GNP (€1,200+).",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_WINE_COOLER",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COLD",
        name_es="Vinoteca",
        name_en="Wine cooler/cellar",
        description_es="Vinoteca para conservación de vinos. Budget: 12-20 botellas básica. Mid: 30-50 botellas, dos zonas. High: 50-100 botellas, antivibraciones. Luxury: integrada, 100+ botellas.",
        typical_specs="30-100 botellas, una o dos zonas temperatura",
        budget_low=150, budget_mid=250, budget_high=350,
        mid_low=450, mid_mid=700, mid_high=950,
        high_low=1100, high_mid=1600, high_high=2200,
        luxury_low=2800, luxury_mid=4500, luxury_high=None,
        unit="ud", typical_quantity="0-1 per property (luxury optional)",
        investment_priority="baja", lifespan_years=15, energy_relevant=True,
        brands_budget=["Cecotec", "Orbegozo", "Klarstein"],
        brands_mid=["Liebherr entry", "Haier", "Bosch"],
        brands_high=["Liebherr Vinidor", "EuroCave", "Climadiff"],
        brands_luxury=["EuroCave Premiere", "Sub-Zero Wine", "Gaggenau RW"],
        basis_notes="Luxury item, not standard. Amazon/MediaMarkt survey. Cecotec GrandSommelier (€249). Liebherr WKes (€899). EuroCave (€2,000+). Common in high-end renovations only.",
        source_retailers=["Amazon", "MediaMarkt", "EuroCave dealers"],
        source_year=2024
    ),
    
    # =========================================================================
    # COOKING
    # =========================================================================
    FFEItem(
        code="FFE_APP_OVEN_BUILTIN",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COOKING",
        name_es="Horno empotrado pirolítico",
        name_en="Built-in pyrolytic oven",
        description_es="Horno empotrado 60cm con limpieza pirolítica. Budget: limpieza manual/vapor. Mid: pirolítico básico. High: pirolítico + vapor, sonda carne. Luxury: combinado vapor + microondas.",
        typical_specs="60cm ancho, 70-75L capacidad, pirolítico",
        budget_low=250, budget_mid=350, budget_high=450,
        mid_low=500, mid_mid=700, mid_high=900,
        high_low=1000, high_mid=1400, high_high=1800,
        luxury_low=2000, luxury_mid=3000, luxury_high=None,
        unit="ud", typical_quantity="1 per kitchen",
        investment_priority="alta", lifespan_years=15, energy_relevant=True,
        brands_budget=["Teka", "Beko", "Candy"],
        brands_mid=["Balay", "Bosch Serie 6", "AEG"],
        brands_high=["Siemens iQ700", "Neff Slide&Hide", "Miele H7"],
        brands_luxury=["Gaggenau", "Wolf", "Miele Generation 7000"],
        basis_notes="Budget: Teka HSB 635 (€349). Mid: Bosch HBG579BS0 (€699). High: Siemens HB678GBS6 (€1,299). Luxury: Gaggenau BO480 (€2,500+). Pirolítico strongly recommended for high/luxury.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_OVEN_COMPACT",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COOKING",
        name_es="Horno compacto con microondas",
        name_en="Compact oven with microwave",
        description_es="Horno compacto 45cm que combina horno y microondas. Budget: básico. Mid: grill + convección. High: vapor añadido. Luxury: multifunción total.",
        typical_specs="45cm altura, 40-45L capacidad, microondas integrado",
        budget_low=350, budget_mid=500, budget_high=650,
        mid_low=750, mid_mid=1000, mid_high=1250,
        high_low=1400, high_mid=1800, high_high=2200,
        luxury_low=2500, luxury_mid=3500, luxury_high=None,
        unit="ud", typical_quantity="0-1 per kitchen (alternative to separate)",
        investment_priority="media", lifespan_years=12, energy_relevant=True,
        brands_budget=["Teka", "Beko", "Candy"],
        brands_mid=["Bosch", "Balay", "AEG"],
        brands_high=["Siemens", "Neff", "Miele"],
        brands_luxury=["Gaggenau", "Miele Generation 7000"],
        basis_notes="Popular for compact kitchens. Saves space by combining two appliances. Bosch CMG636BS1 (€999). Siemens CM678G4S6 (€1,799). Optional - many prefer separate units.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_HOB_INDUCTION",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COOKING",
        name_es="Placa de inducción 60cm",
        name_en="60cm induction hob",
        description_es="Placa vitrocerámica de inducción 4 zonas. Budget: zonas fijas, sin boost. Mid: zona flexible, boost, touch slider. High: flex induction full. Luxury: con extractor integrado.",
        typical_specs="60cm ancho, 4 zonas, 7.2-7.4kW total",
        budget_low=250, budget_mid=350, budget_high=450,
        mid_low=500, mid_mid=700, mid_high=900,
        high_low=1000, high_mid=1400, high_high=1800,
        luxury_low=2500, luxury_mid=3500, luxury_high=None,
        unit="ud", typical_quantity="1 per kitchen",
        investment_priority="alta", lifespan_years=15, energy_relevant=True,
        brands_budget=["Teka", "Beko", "Candy"],
        brands_mid=["Balay", "Bosch", "AEG"],
        brands_high=["Siemens flexInduction", "Neff T56", "Miele KM"],
        brands_luxury=["Bora", "Gaggenau CX", "Miele KMDA"],
        basis_notes="Comparison: Teka IZ6420 (€299), Bosch PXX675DC1E (€699), Siemens EX675LYC1E (€1,299), Bora Pure con extractor (€3,200). Induction only, not standard vitro.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_HOB_GAS",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COOKING",
        name_es="Placa de gas 60cm",
        name_en="60cm gas hob",
        description_es="Placa de gas 4-5 fuegos. Budget: básica esmaltada. Mid: inox, wok central. High: cristal templado, parrillas fundición. Luxury: diseño profesional.",
        typical_specs="60cm ancho, 4-5 fuegos, gas natural/butano",
        budget_low=150, budget_mid=220, budget_high=290,
        mid_low=350, mid_mid=500, mid_high=650,
        high_low=750, high_mid=1000, high_high=1300,
        luxury_low=1500, luxury_mid=2200, luxury_high=None,
        unit="ud", typical_quantity="1 per kitchen (alternative to induction)",
        investment_priority="alta", lifespan_years=20, energy_relevant=False,
        brands_budget=["Teka", "Beko", "Meireles"],
        brands_mid=["Balay", "Bosch", "Smeg"],
        brands_high=["Siemens", "Neff", "Smeg Victoria"],
        brands_luxury=["Gaggenau VG", "Lacanche", "Bertazzoni"],
        basis_notes="Still preferred by some for cooking control. Teka EX60 (€220). Bosch PGH6B5B90 (€499). Smeg SRV576GH (€999). Professional ranges €2,000+.",
        source_retailers=["MediaMarkt", "El Corte Inglés", "Teka stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_HOOD_INTEGRATED",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COOKING",
        name_es="Campana integrada/telescópica",
        name_en="Integrated/telescopic hood",
        description_es="Campana integrada en mueble. Budget: básica 2 velocidades. Mid: motor eficiente, LED. High: silenciosa, sensor. Luxury: integración perfecta.",
        typical_specs="60cm ancho, 300-700 m³/h extracción",
        budget_low=80, budget_mid=130, budget_high=180,
        mid_low=220, mid_mid=350, mid_high=480,
        high_low=550, high_mid=800, high_high=1050,
        luxury_low=1200, luxury_mid=1800, luxury_high=None,
        unit="ud", typical_quantity="1 per kitchen",
        investment_priority="media", lifespan_years=12, energy_relevant=True,
        brands_budget=["Teka", "Cata", "Mepamsa"],
        brands_mid=["Balay", "Bosch", "Elica"],
        brands_high=["Siemens", "Neff", "Falmec"],
        brands_luxury=["Gaggenau", "Miele", "Bora downdraft"],
        basis_notes="Hidden design, most common in integrated kitchens. Teka CNL6415 (€129). Bosch DFS067A50 (€349). Neff D46ED52N0 (€799). Premium versions very quiet (<50dB).",
        source_retailers=["MediaMarkt", "Leroy Merlin"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_HOOD_DECORATIVE",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COOKING",
        name_es="Campana decorativa de pared",
        name_en="Decorative wall-mounted hood",
        description_es="Campana visible tipo chimenea. Budget: inox básica. Mid: inox+cristal, potente. High: diseño, muy silenciosa. Luxury: diseño de autor.",
        typical_specs="60-90cm ancho, 500-900 m³/h extracción",
        budget_low=100, budget_mid=180, budget_high=260,
        mid_low=320, mid_mid=500, mid_high=680,
        high_low=800, high_mid=1200, high_high=1600,
        luxury_low=2000, luxury_mid=3000, luxury_high=None,
        unit="ud", typical_quantity="1 per kitchen (alternative to integrated)",
        investment_priority="media", lifespan_years=12, energy_relevant=True,
        brands_budget=["Teka", "Cata", "Mepamsa"],
        brands_mid=["Balay", "Bosch", "Elica"],
        brands_high=["Siemens", "Falmec", "Elica NicolaTesla"],
        brands_luxury=["Falmec Circle", "Elica Majestic", "Best"],
        basis_notes="Statement piece in open kitchens. Teka DVT985 (€179). Bosch DWB96BC50 (€499). Falmec Lumina (€1,200). Design campanas are focal points.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_MICROWAVE_BUILTIN",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="COOKING",
        name_es="Microondas integrado",
        name_en="Built-in microwave",
        description_es="Microondas empotrable 60cm. Budget: solo microondas. Mid: grill añadido. High: inverter, sensor. Luxury: cajón calentador.",
        typical_specs="60cm ancho para integrar, 20-25L",
        budget_low=150, budget_mid=220, budget_high=290,
        mid_low=350, mid_mid=500, mid_high=650,
        high_low=750, high_mid=1000, high_high=1250,
        luxury_low=1400, luxury_mid=2000, luxury_high=None,
        unit="ud", typical_quantity="1 per kitchen",
        investment_priority="baja", lifespan_years=10, energy_relevant=True,
        brands_budget=["Teka", "Beko", "Candy"],
        brands_mid=["Balay", "Bosch", "AEG"],
        brands_high=["Siemens", "Neff", "Miele M6"],
        brands_luxury=["Gaggenau BMP", "Miele M7"],
        basis_notes="Teka ML822BIS (€229). Bosch BFL524MS0 (€499). Siemens BF634LGS1 (€899). Alternative: countertop microwave €80-200 (not integrated).",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    
    # =========================================================================
    # CLEANING
    # =========================================================================
    FFEItem(
        code="FFE_APP_DISHWASHER_60",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="CLEANING",
        name_es="Lavavajillas 60cm",
        name_en="60cm dishwasher",
        description_es="Lavavajillas estándar 60cm, 13-14 cubiertos. Budget: clase E, ruidoso. Mid: clase C, silencioso. High: clase A, muy silencioso, tercera bandeja. Luxury: panelable premium.",
        typical_specs="60cm ancho, 13-14 cubiertos, clase C o mejor",
        budget_low=300, budget_mid=400, budget_high=500,
        mid_low=550, mid_mid=700, mid_high=850,
        high_low=900, high_mid=1200, high_high=1500,
        luxury_low=1600, luxury_mid=2000, luxury_high=None,
        unit="ud", typical_quantity="1 per kitchen",
        investment_priority="alta", lifespan_years=12, energy_relevant=True,
        brands_budget=["Beko", "Indesit", "Teka"],
        brands_mid=["Balay", "Bosch Serie 4/6", "Samsung"],
        brands_high=["Siemens iQ500", "Neff", "Miele G5"],
        brands_luxury=["Miele G7", "Gaggenau DF"],
        basis_notes="Budget: Beko DVN06430W (€399). Mid: Bosch SMS4HMW02E (€699). High: Siemens SN65ZX00CE (€1,199). Luxury: Miele G7 (€1,800+). Noise level critical: budget 49dB+, luxury <42dB.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_DISHWASHER_45",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="CLEANING",
        name_es="Lavavajillas 45cm compacto",
        name_en="45cm compact dishwasher",
        description_es="Lavavajillas compacto 45cm, 9-10 cubiertos. Para cocinas pequeñas o 1-2 personas.",
        typical_specs="45cm ancho, 9-10 cubiertos",
        budget_low=300, budget_mid=380, budget_high=460,
        mid_low=500, mid_mid=650, mid_high=800,
        high_low=900, high_mid=1100, high_high=1300,
        luxury_low=1400, luxury_mid=1800, luxury_high=None,
        unit="ud", typical_quantity="1 per small kitchen",
        investment_priority="alta", lifespan_years=12, energy_relevant=True,
        brands_budget=["Beko", "Teka", "Candy"],
        brands_mid=["Balay", "Bosch", "AEG"],
        brands_high=["Siemens", "Neff", "Miele"],
        brands_luxury=["Miele G7 45cm"],
        basis_notes="~10% premium over 60cm for compact size. Bosch SPS4HMI61E 45cm (€699). Common in studio apartments and small kitchens.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_WASHER",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="CLEANING",
        name_es="Lavadora 8-9kg",
        name_en="Washing machine 8-9kg",
        description_es="Lavadora carga frontal 8-9kg. Budget: básica, ruidosa. Mid: silenciosa, vapor, app. High: dosificación automática, muy silenciosa. Luxury: premium.",
        typical_specs="8-9kg capacidad, 1400rpm centrifugado",
        budget_low=300, budget_mid=400, budget_high=500,
        mid_low=550, mid_mid=700, mid_high=850,
        high_low=900, high_mid=1200, high_high=1500,
        luxury_low=1600, luxury_mid=2200, luxury_high=None,
        unit="ud", typical_quantity="1 per property",
        investment_priority="alta", lifespan_years=12, energy_relevant=True,
        brands_budget=["Beko", "Indesit", "Teka"],
        brands_mid=["Balay", "Bosch Serie 6", "Samsung"],
        brands_high=["Siemens iQ700", "AEG 8000", "Miele W1"],
        brands_luxury=["Miele W1 Excellence", "AEG 9000"],
        basis_notes="Budget: Beko WTA9715XW (€399). Mid: Bosch WGG254ZXES (€699). High: Siemens WM16XMH0ES (€1,199). Luxury: Miele W1 (€1,800+). AutoDose feature increasingly standard at mid+ tiers.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_DRYER",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="CLEANING",
        name_es="Secadora bomba de calor 8-9kg",
        name_en="Heat pump dryer 8-9kg",
        description_es="Secadora con bomba de calor (eficiente). Budget: condensación básica. Mid: bomba calor estándar. High: bomba calor premium, sensores. Luxury: bomba calor silenciosa.",
        typical_specs="8-9kg capacidad, bomba de calor A++",
        budget_low=350, budget_mid=450, budget_high=550,
        mid_low=600, mid_mid=750, mid_high=900,
        high_low=1000, high_mid=1300, high_high=1600,
        luxury_low=1700, luxury_mid=2200, luxury_high=None,
        unit="ud", typical_quantity="0-1 per property (optional)",
        investment_priority="media", lifespan_years=12, energy_relevant=True,
        brands_budget=["Beko", "Indesit", "Candy"],
        brands_mid=["Balay", "Bosch", "Samsung"],
        brands_high=["Siemens", "AEG", "Miele T1"],
        brands_luxury=["Miele T1 Excellence"],
        basis_notes="Only ~30% of Spanish households have dryer. Beko DH8534GX0 (€449). Bosch WTH85V08ES (€749). Miele T1 (€1,700+). Heat pump mandatory for energy efficiency.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_APP_WASHER_DRYER",
        category_code="KITCHEN_APPLIANCES",
        subcategory_code="CLEANING",
        name_es="Lavasecadora",
        name_en="Washer-dryer combo",
        description_es="Lavadora-secadora combinada. Budget: básica. Mid: buen rendimiento. High: eficiente. Luxury: premium. Nota: menos eficiente que separadas.",
        typical_specs="8kg lavado, 5-6kg secado típico",
        budget_low=400, budget_mid=550, budget_high=700,
        mid_low=800, mid_mid=1000, mid_high=1200,
        high_low=1300, high_mid=1600, high_high=1900,
        luxury_low=2000, luxury_mid=2500, luxury_high=None,
        unit="ud", typical_quantity="1 per small property (space-saving)",
        investment_priority="media", lifespan_years=10, energy_relevant=True,
        brands_budget=["Beko", "Indesit", "Candy"],
        brands_mid=["Balay", "Bosch", "Samsung"],
        brands_high=["Siemens", "AEG", "LG"],
        brands_luxury=["Miele WT1"],
        basis_notes="Space-saving but compromised drying capacity (usually 5-6kg vs 8kg wash). Beko HTV8736XS (€549). Bosch WDU8H541ES (€999). Popular in small apartments.",
        source_retailers=["MediaMarkt", "El Corte Inglés"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: LIVING FURNITURE
# =============================================================================

LIVING_FURNITURE = [
    FFEItem(
        code="FFE_LIV_SOFA_2P",
        category_code="LIVING_FURNITURE",
        subcategory_code="SEATING",
        name_es="Sofá 2 plazas",
        name_en="2-seater sofa",
        description_es="Sofá 2 plazas (~150-170cm). Budget: tela sintética, espuma blanda. Mid: algodón/lino, espuma HR. High: bouclé/terciopelo. Luxury: diseñador.",
        typical_specs="150-170cm ancho, 85-95cm profundidad",
        budget_low=300, budget_mid=450, budget_high=600,
        mid_low=900, mid_mid=1300, mid_high=1700,
        high_low=2200, high_mid=3200, high_high=4500,
        luxury_low=5500, luxury_mid=8000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per living room",
        investment_priority="alta", lifespan_years=12, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Merkamueble"],
        brands_mid=["Kave Home", "Kenay Home", "La Redoute"],
        brands_high=["Sancal", "Expormim", "Grassoler"],
        brands_luxury=["Poliform", "Minotti", "B&B Italia"],
        basis_notes="~75-80% of 3P prices. IKEA KIVIK 2P (€449). Kave Home (€1,100-1,500). Many Spanish flats prefer 2P for space.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_SOFA_3P",
        category_code="LIVING_FURNITURE",
        subcategory_code="SEATING",
        name_es="Sofá 3 plazas",
        name_en="3-seater sofa",
        description_es="Sofá 3 plazas (~200-220cm). Budget: tela sintética, espuma blanda. Mid: algodón/lino mezclado, espuma HR. High: bouclé/terciopelo, plumas+espuma. Luxury: cuero premium o diseñador.",
        typical_specs="200-220cm ancho, 85-95cm profundidad, 75-85cm alto",
        budget_low=400, budget_mid=600, budget_high=800,
        mid_low=1200, mid_mid=1700, mid_high=2200,
        high_low=2800, high_mid=4000, high_high=5500,
        luxury_low=7000, luxury_mid=10000, luxury_high=None,
        unit="ud", typical_quantity="1 per living room",
        investment_priority="alta", lifespan_years=12, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Merkamueble"],
        brands_mid=["Kave Home", "Kenay Home", "La Redoute"],
        brands_high=["Sancal", "Expormim", "Grassoler", "Fama"],
        brands_luxury=["Poliform", "Minotti", "B&B Italia", "Flexform"],
        basis_notes="IKEA KIVIK 3P (€599). Kave Home Blok (€1,599). Sancal Roll (€3,800). Poliform Bristol (€9,000+). Delivery extra (€50-200). Sales (Jan/Jul) discount 20-40%.",
        source_retailers=["IKEA", "Kave Home", "Sancal showroom"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_SOFA_CHAISE",
        category_code="LIVING_FURNITURE",
        subcategory_code="SEATING",
        name_es="Sofá con chaise longue",
        name_en="Sofa with chaise longue",
        description_es="Sofá con extensión chaise longue. Budget: básico. Mid: configuraciones múltiples. High: modular premium. Luxury: diseño modular.",
        typical_specs="260-320cm total, chaise izq o dcha",
        budget_low=600, budget_mid=850, budget_high=1100,
        mid_low=1500, mid_mid=2200, mid_high=2900,
        high_low=3500, high_mid=5000, high_high=7000,
        luxury_low=9000, luxury_mid=14000, luxury_high=None,
        unit="ud", typical_quantity="1 per living room (alternative)",
        investment_priority="alta", lifespan_years=12, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Merkamueble"],
        brands_mid=["Kave Home", "Kenay Home", "Fama"],
        brands_high=["Sancal", "Grassoler", "Fama Arianne"],
        brands_luxury=["Poliform", "Minotti", "B&B Italia"],
        basis_notes="Very popular in Spain - provides extra lounging. IKEA SÖDERHAMN chaise (€849). Kave Home Blok chaise (€2,199). Typical 30-40% premium over 3P.",
        source_retailers=["IKEA", "Kave Home", "Fama stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_ARMCHAIR",
        category_code="LIVING_FURNITURE",
        subcategory_code="SEATING",
        name_es="Butaca / Sillón",
        name_en="Armchair",
        description_es="Butaca individual para salón. Budget: tela básica. Mid: diseño nórdico. High: tapizado premium. Luxury: icono diseño.",
        typical_specs="70-85cm ancho, 75-85cm profundidad",
        budget_low=150, budget_mid=250, budget_high=350,
        mid_low=450, mid_mid=700, mid_high=950,
        high_low=1200, high_mid=1800, high_high=2500,
        luxury_low=3000, luxury_mid=5000, luxury_high=None,
        unit="ud", typical_quantity="0-2 per living room",
        investment_priority="media", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Sklum", "Maisons du Monde"],
        brands_mid=["Kave Home", "Kenay", "Made.com"],
        brands_high=["Sancal", "Expormim", "Mobles 114"],
        brands_luxury=["Vitra", "Cassina", "Fritz Hansen", "Carl Hansen"],
        basis_notes="IKEA STRANDMON (€249). Kave Home (€500-900). Sancal (€1,500+). Classic designs (Eames, Wegner) in luxury tier.",
        source_retailers=["IKEA", "Kave Home", "Design stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_COFFEE_TABLE",
        category_code="LIVING_FURNITURE",
        subcategory_code="TABLES",
        name_es="Mesa de centro",
        name_en="Coffee table",
        description_es="Mesa baja para salón. Budget: MDF/aglomerado. Mid: madera maciza o mármol sintético. High: mármol natural, nogal. Luxury: diseño firmado.",
        typical_specs="80-120cm, altura 35-45cm",
        budget_low=80, budget_mid=140, budget_high=200,
        mid_low=300, mid_mid=500, mid_high=700,
        high_low=900, high_mid=1500, high_high=2200,
        luxury_low=2500, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="1 per living room",
        investment_priority="media", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Maisons du Monde", "Sklum"],
        brands_mid=["Kave Home", "Kenay", "Made.com"],
        brands_high=["Treku", "Punt", "Expormim"],
        brands_luxury=["Poliform", "B&B Italia", "Cassina"],
        basis_notes="Wide material variance. IKEA LACK (€15) to designer marble (€5K+). Typical mid: Kave Home (€350-600). High: Treku Arina (€1,200).",
        source_retailers=["IKEA", "Kave Home", "Treku showroom"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_SIDE_TABLE",
        category_code="LIVING_FURNITURE",
        subcategory_code="TABLES",
        name_es="Mesa auxiliar",
        name_en="Side table",
        description_es="Mesa pequeña auxiliar junto a sofá. Budget: básica. Mid: madera/metal. High: diseño. Luxury: firmada.",
        typical_specs="40-50cm diámetro o lado, altura 45-55cm",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=120, mid_mid=200, mid_high=280,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1500, luxury_high=None,
        unit="ud", typical_quantity="1-2 per living room",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Sklum", "Zara Home"],
        brands_mid=["Kave Home", "Kenay", "HAY"],
        brands_high=["Punt", "Treku", "Muuto"],
        brands_luxury=["Vitra", "Cassina", "Zanotta"],
        basis_notes="Often sold in sets or multiples. IKEA GLADOM (€19). Kave Home Rhet (€169). HAY DLM (€299).",
        source_retailers=["IKEA", "Kave Home", "HAY store"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_CONSOLE",
        category_code="LIVING_FURNITURE",
        subcategory_code="TABLES",
        name_es="Consola entrada",
        name_en="Console table",
        description_es="Mueble estrecho para entrada o pasillo. Budget: melamina. Mid: madera. High: diseño. Luxury: firmado.",
        typical_specs="100-140cm ancho, 30-40cm profundidad, 75-85cm alto",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=300, mid_mid=500, mid_high=700,
        high_low=850, high_mid=1300, high_high=1800,
        luxury_low=2200, luxury_mid=3500, luxury_high=None,
        unit="ud", typical_quantity="0-1 per property",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Maisons du Monde", "Sklum"],
        brands_mid=["Kave Home", "Kenay", "La Redoute"],
        brands_high=["Treku", "Punt", "Ethnicraft"],
        brands_luxury=["Poliform", "Molteni", "Porada"],
        basis_notes="Not always needed - depends on layout. IKEA HEMNES (€179). Kave Home (€400-700). Treku (€1,200+).",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_TV_UNIT",
        category_code="LIVING_FURNITURE",
        subcategory_code="STORAGE_LIVING",
        name_es="Mueble TV",
        name_en="TV unit/console",
        description_es="Mueble bajo para televisión. Budget: melamina básica. Mid: melamina premium o roble. High: nogal, diseño modular. Luxury: sistemas de pared.",
        typical_specs="150-200cm ancho, 40-50cm alto",
        budget_low=100, budget_mid=200, budget_high=300,
        mid_low=400, mid_mid=650, mid_high=900,
        high_low=1000, high_mid=1600, high_high=2200,
        luxury_low=2500, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="1 per living room",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Merkamueble"],
        brands_mid=["Kave Home", "Kenay", "Sklum"],
        brands_high=["Treku", "Punt", "Novamobili"],
        brands_luxury=["Poliform", "B&B Italia", "Lema"],
        basis_notes="IKEA BESTÅ (€200-400 configured). Kave Home (€450-800). Treku modular (€1,500+). Often integrated into wall systems at luxury.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_BOOKSHELF",
        category_code="LIVING_FURNITURE",
        subcategory_code="STORAGE_LIVING",
        name_es="Estantería / Librería",
        name_en="Bookshelf / Bookcase",
        description_es="Estantería para libros y decoración. Budget: básica modular. Mid: madera/metal. High: diseño. Luxury: a medida.",
        typical_specs="80-200cm ancho, 180-220cm alto",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=350, mid_mid=600, mid_high=850,
        high_low=1000, high_mid=1800, high_high=2600,
        luxury_low=3000, luxury_mid=5000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per living room",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Sklum", "Conforama"],
        brands_mid=["Kave Home", "Kenay", "String"],
        brands_high=["Treku", "Punt", "USM Haller"],
        brands_luxury=["Poliform", "Molteni", "USM premium"],
        basis_notes="IKEA BILLY/KALLAX (€79-200). String System (€500-1,500 configured). USM Haller (€2,000+). Modular systems more flexible.",
        source_retailers=["IKEA", "String dealers", "USM dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIV_SIDEBOARD",
        category_code="LIVING_FURNITURE",
        subcategory_code="STORAGE_LIVING",
        name_es="Aparador",
        name_en="Sideboard",
        description_es="Aparador para almacenaje en salón/comedor. Budget: melamina. Mid: madera/lacado. High: diseño. Luxury: firmado.",
        typical_specs="140-200cm ancho, 40-50cm profundidad, 75-85cm alto",
        budget_low=150, budget_mid=280, budget_high=410,
        mid_low=550, mid_mid=900, mid_high=1250,
        high_low=1500, high_mid=2400, high_high=3300,
        luxury_low=4000, luxury_mid=6500, luxury_high=None,
        unit="ud", typical_quantity="0-1 per living/dining",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Maisons du Monde", "Conforama"],
        brands_mid=["Kave Home", "Kenay", "Ethnicraft"],
        brands_high=["Treku", "Punt", "Novamobili"],
        brands_luxury=["Poliform", "Molteni", "Giorgetti"],
        basis_notes="IKEA BESTÅ configured (€350). Kave Home (€700-1,100). Treku Aura (€2,200+). Often most prominent piece in dining area.",
        source_retailers=["IKEA", "Kave Home", "Treku showroom"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: DINING FURNITURE
# =============================================================================

DINING_FURNITURE = [
    FFEItem(
        code="FFE_DIN_TABLE_4P",
        category_code="DINING_FURNITURE",
        subcategory_code=None,
        name_es="Mesa comedor 4 personas",
        name_en="4-person dining table",
        description_es="Mesa comedor pequeña (~120cm). Budget: melamina/MDF. Mid: madera maciza o chapa. High: nogal, diseño. Luxury: firmado.",
        typical_specs="120cm largo, 80cm ancho, 75cm alto",
        budget_low=100, budget_mid=180, budget_high=260,
        mid_low=350, mid_mid=550, mid_high=750,
        high_low=900, high_mid=1400, high_high=1900,
        luxury_low=2500, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="1 per small dining area",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Muebles Lufe"],
        brands_mid=["Kave Home", "Kenay", "Made.com"],
        brands_high=["Treku", "Punt", "Expormim"],
        brands_luxury=["Poliform", "B&B Italia", "Cassina"],
        basis_notes="For apartments/small dining. IKEA EKEDALEN (€249 extendable). Kave Home Argo (€499). Treku (€1,200+).",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DIN_TABLE_6P",
        category_code="DINING_FURNITURE",
        subcategory_code=None,
        name_es="Mesa comedor 6 personas",
        name_en="6-person dining table",
        description_es="Mesa comedor mediana (~160cm). Budget: melamina/MDF. Mid: roble macizo o chapa. High: nogal macizo, mármol. Luxury: diseño firmado.",
        typical_specs="160cm largo, 90cm ancho, 75cm alto",
        budget_low=150, budget_mid=250, budget_high=350,
        mid_low=500, mid_mid=800, mid_high=1100,
        high_low=1300, high_mid=2000, high_high=2800,
        luxury_low=3500, luxury_mid=5500, luxury_high=None,
        unit="ud", typical_quantity="1 per dining area",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Muebles Lufe"],
        brands_mid=["Kave Home", "Kenay", "Made.com"],
        brands_high=["Treku", "Punt", "Expormim"],
        brands_luxury=["Poliform", "B&B Italia", "Cassina"],
        basis_notes="Most common size. IKEA MÖRBYLÅNGA (€449). Kave Home Argo (€799). Treku Arina (€1,800). Material and legs drive price.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DIN_TABLE_8P",
        category_code="DINING_FURNITURE",
        subcategory_code=None,
        name_es="Mesa comedor 8+ personas",
        name_en="8+ person dining table",
        description_es="Mesa comedor grande (~200-240cm). Budget: melamina extensible. Mid: madera maciza. High: nogal/mármol. Luxury: firmada.",
        typical_specs="200-240cm largo, 90-100cm ancho",
        budget_low=250, budget_mid=400, budget_high=550,
        mid_low=750, mid_mid=1200, mid_high=1650,
        high_low=2000, high_mid=3200, high_high=4500,
        luxury_low=5500, luxury_mid=9000, luxury_high=None,
        unit="ud", typical_quantity="1 per large dining area",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Muebles Lufe"],
        brands_mid=["Kave Home", "Kenay", "Ethnicraft"],
        brands_high=["Treku", "Punt", "Expormim"],
        brands_luxury=["Poliform", "Molteni", "Maxalto"],
        basis_notes="For larger properties/entertaining. IKEA MÖRBYLÅNGA 220cm (€599). Ethnicraft Oak Slice (€1,800). Statement piece in open-plan living.",
        source_retailers=["IKEA", "Ethnicraft dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DIN_CHAIR",
        category_code="DINING_FURNITURE",
        subcategory_code=None,
        name_es="Silla comedor (unidad)",
        name_en="Dining chair (each)",
        description_es="Silla de comedor individual. Budget: plástico/melamina. Mid: madera+tela, nórdico. High: roble tapizada. Luxury: diseño firmado.",
        typical_specs="Altura asiento 45-47cm",
        budget_low=30, budget_mid=50, budget_high=75,
        mid_low=100, mid_mid=150, mid_high=200,
        high_low=250, high_mid=400, high_high=550,
        luxury_low=600, luxury_mid=900, luxury_high=None,
        unit="ud", typical_quantity="4-8 per dining area",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Sklum", "Maisons du Monde"],
        brands_mid=["Kave Home", "Kenay", "Made.com"],
        brands_high=["Andreu World", "Viccarbe", "Punt"],
        brands_luxury=["Vitra", "Fritz Hansen", "Cassina", "Carl Hansen"],
        basis_notes="IKEA NORDMYRA (€45). Kave Home Yvette (€139). Andreu World Nuez (€380). Vitra Eames DSW original (€550). Replicas cheaper but quality varies.",
        source_retailers=["IKEA", "Kave Home", "Vitra store"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DIN_BENCH",
        category_code="DINING_FURNITURE",
        subcategory_code=None,
        name_es="Banco comedor",
        name_en="Dining bench",
        description_es="Banco para comedor (2-3 personas). Budget: básico. Mid: tapizado. High: diseño. Luxury: firmado.",
        typical_specs="120-180cm largo, 40cm ancho, altura asiento 45cm",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=300, mid_mid=500, mid_high=700,
        high_low=850, high_mid=1300, high_high=1800,
        luxury_low=2200, luxury_mid=3500, luxury_high=None,
        unit="ud", typical_quantity="0-1 per dining area",
        investment_priority="baja", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Sklum", "Maisons du Monde"],
        brands_mid=["Kave Home", "Kenay", "Made.com"],
        brands_high=["Treku", "Punt", "Ethnicraft"],
        brands_luxury=["Carl Hansen", "E15", "Zeitraum"],
        basis_notes="Trendy alternative to chairs on one side. IKEA SKOGSTA (€149). Kave Home (€350-600). Saves space, informal feel.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DIN_BAR_STOOL",
        category_code="DINING_FURNITURE",
        subcategory_code=None,
        name_es="Taburete alto (isla cocina)",
        name_en="Bar stool (kitchen island)",
        description_es="Taburete para barra de cocina o isla. Budget: básico metal/plástico. Mid: madera/tapizado. High: diseño. Luxury: firmado.",
        typical_specs="Altura asiento 65-75cm para encimera estándar",
        budget_low=40, budget_mid=70, budget_high=100,
        mid_low=130, mid_mid=200, mid_high=270,
        high_low=320, high_mid=500, high_high=680,
        luxury_low=800, luxury_mid=1200, luxury_high=None,
        unit="ud", typical_quantity="2-4 per kitchen island",
        investment_priority="media", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Sklum", "Amazon"],
        brands_mid=["Kave Home", "Kenay", "Normann Copenhagen"],
        brands_high=["Viccarbe", "Andreu World", "Hay"],
        brands_luxury=["Vitra", "Fritz Hansen", "Magis"],
        basis_notes="Essential for kitchens with island/peninsula. IKEA GLENN (€45). Kave Home (€150-250). Hay About a Stool (€350). Height matters: 65cm for 90cm counter, 75cm for bar.",
        source_retailers=["IKEA", "Kave Home", "HAY store"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DIN_HIGHCHAIR",
        category_code="DINING_FURNITURE",
        subcategory_code=None,
        name_es="Trona bebé",
        name_en="Baby high chair",
        description_es="Trona para bebé/niño pequeño. Budget: básica plástico. Mid: madera evolutiva. High: diseño evolutivo. Luxury: firmado evolutivo.",
        typical_specs="Convertible, crece con el niño idealmente",
        budget_low=30, budget_mid=50, budget_high=70,
        mid_low=100, mid_mid=180, mid_high=260,
        high_low=300, high_mid=450, high_high=600,
        luxury_low=700, luxury_mid=1000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per property (family)",
        investment_priority="baja", lifespan_years=5, energy_relevant=False,
        brands_budget=["IKEA", "Chicco básica", "Amazon"],
        brands_mid=["Stokke Clikk", "Cybex", "BabyBjörn"],
        brands_high=["Stokke Tripp Trapp", "Nomi", "Leander"],
        brands_luxury=["Stokke Steps", "Bugaboo Giraffe"],
        basis_notes="Only needed for families with young children. IKEA ANTILOP (€20). Stokke Tripp Trapp (€299) is gold standard - lasts years, grows with child.",
        source_retailers=["IKEA", "El Corte Inglés", "Stokke dealers"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: BEDROOM FURNITURE
# =============================================================================

BEDROOM_FURNITURE = [
    FFEItem(
        code="FFE_BED_FRAME_SINGLE",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="SLEEPING",
        name_es="Cama individual 90cm (estructura)",
        name_en="Single bed frame 90cm",
        description_es="Estructura de cama individual para colchón 90cm. Budget: melamina. Mid: madera/lacado. High: tapizado. Luxury: diseño.",
        typical_specs="Para colchón 90x190/200cm",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=300, mid_mid=500, mid_high=700,
        high_low=850, high_mid=1300, high_high=1750,
        luxury_low=2000, luxury_mid=3200, luxury_high=None,
        unit="ud", typical_quantity="1 per single bedroom",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Muebles Lufe", "Conforama"],
        brands_mid=["Kenay", "Kave Home", "La Redoute"],
        brands_high=["Treku", "Novamobili", "Joquer"],
        brands_luxury=["Poliform", "Flou", "Schramm"],
        basis_notes="IKEA MALM 90cm (€129). Kave Home (€400-600). Often for children's rooms or guest rooms.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BED_FRAME_DOUBLE",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="SLEEPING",
        name_es="Cama matrimonio 150cm (estructura+cabecero)",
        name_en="Double bed frame 150cm",
        description_es="Estructura de cama y cabecero para colchón 150cm. Budget: melamina. Mid: lacado o roble. High: nogal, tapizado. Luxury: diseño de autor.",
        typical_specs="Para colchón 150x190/200cm",
        budget_low=200, budget_mid=350, budget_high=500,
        mid_low=600, mid_mid=1000, mid_high=1400,
        high_low=1600, high_mid=2500, high_high=3500,
        luxury_low=4000, luxury_mid=6000, luxury_high=None,
        unit="ud", typical_quantity="1 per master bedroom",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Muebles Lufe", "Conforama"],
        brands_mid=["Kenay", "Kave Home", "Tediber"],
        brands_high=["Treku", "Novamobili", "Joquer"],
        brands_luxury=["Poliform", "B&B Italia", "Schramm"],
        basis_notes="IKEA MALM 150cm (€249). Tediber con canapé (€990). Treku (€2,500+). Cabecero tapizado increasingly popular at mid+ tiers.",
        source_retailers=["IKEA", "Tediber", "Treku showroom"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BED_FRAME_KING",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="SLEEPING",
        name_es="Cama king 180cm (estructura+cabecero)",
        name_en="King bed frame 180cm",
        description_es="Estructura de cama y cabecero para colchón 180cm. Budget: melamina. Mid: lacado o roble. High: nogal, tapizado. Luxury: diseño de autor.",
        typical_specs="Para colchón 180x200cm",
        budget_low=250, budget_mid=420, budget_high=590,
        mid_low=750, mid_mid=1200, mid_high=1650,
        high_low=1900, high_mid=3000, high_high=4200,
        luxury_low=5000, luxury_mid=7500, luxury_high=None,
        unit="ud", typical_quantity="1 per master bedroom (large)",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Muebles Lufe", "Conforama"],
        brands_mid=["Kenay", "Kave Home", "Tediber"],
        brands_high=["Treku", "Novamobili", "Joquer"],
        brands_luxury=["Poliform", "B&B Italia", "Flexform"],
        basis_notes="~20% premium over 150cm. IKEA MALM 180cm (€299). Premium for larger rooms. Common in chalets, less common in apartments.",
        source_retailers=["IKEA", "Tediber"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_MATTRESS_SINGLE",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="SLEEPING",
        name_es="Colchón 90cm",
        name_en="Single mattress 90cm",
        description_es="Colchón individual 90cm. Budget: espuma básica. Mid: muelles ensacados. High: visco premium. Luxury: artesanal.",
        typical_specs="90x190 o 90x200cm",
        budget_low=100, budget_mid=180, budget_high=260,
        mid_low=350, mid_mid=500, mid_high=650,
        high_low=750, high_mid=1100, high_high=1500,
        luxury_low=2000, luxury_mid=3500, luxury_high=None,
        unit="ud", typical_quantity="1 per single bed",
        investment_priority="alta", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Carrefour", "Pikolin básico"],
        brands_mid=["Tediber", "Emma", "Flex", "Pikolin"],
        brands_high=["Tempur", "Flex Nube", "Hästens entry"],
        brands_luxury=["Hästens", "Vispring", "Duxiana"],
        basis_notes="~60% of double prices. IKEA HAUGESUND (€179). Tediber (€490). Children's rooms often get mid-range.",
        source_retailers=["IKEA", "Tediber", "Flex stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_MATTRESS_DOUBLE",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="SLEEPING",
        name_es="Colchón 150cm",
        name_en="Double mattress 150cm",
        description_es="Colchón matrimonio 150cm. Budget: espuma básica. Mid: muelles ensacados, espuma HR. High: látex o visco premium. Luxury: artesanal, naturales.",
        typical_specs="150x190 o 150x200cm",
        budget_low=200, budget_mid=350, budget_high=500,
        mid_low=600, mid_mid=900, mid_high=1200,
        high_low=1400, high_mid=2200, high_high=3000,
        luxury_low=4000, luxury_mid=7000, luxury_high=None,
        unit="ud", typical_quantity="1 per double bed",
        investment_priority="alta", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Carrefour", "Pikolin básico"],
        brands_mid=["Tediber", "Emma", "Flex", "Pikolin"],
        brands_high=["Tempur", "Flex Nube", "Hästens entry"],
        brands_luxury=["Hästens", "Vispring", "Hastens Vividus"],
        basis_notes="Critical comfort item. D2C brands disrupted: Tediber €790, Emma €799. Hästens Excel €6,000, Vividus €100K+. 10-year warranty standard at mid+.",
        source_retailers=["Tediber", "El Corte Inglés", "Flex store"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_MATTRESS_KING",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="SLEEPING",
        name_es="Colchón 180cm",
        name_en="King mattress 180cm",
        description_es="Colchón king 180cm. Budget: espuma básica. Mid: muelles ensacados. High: visco premium. Luxury: artesanal.",
        typical_specs="180x200cm",
        budget_low=280, budget_mid=450, budget_high=620,
        mid_low=750, mid_mid=1100, mid_high=1450,
        high_low=1700, high_mid=2700, high_high=3700,
        luxury_low=5000, luxury_mid=9000, luxury_high=None,
        unit="ud", typical_quantity="1 per king bed",
        investment_priority="alta", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Carrefour", "Pikolin básico"],
        brands_mid=["Tediber", "Emma", "Flex", "Pikolin"],
        brands_high=["Tempur", "Flex Nube", "Hästens"],
        brands_luxury=["Hästens", "Vispring", "Duxiana"],
        basis_notes="~20-25% premium over 150cm. Tediber King €990. Often two 90cm mattresses (€1,580) for individual firmness.",
        source_retailers=["Tediber", "Flex stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BED_NIGHTSTAND",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="BEDROOM_STORAGE",
        name_es="Mesita de noche (unidad)",
        name_en="Nightstand (each)",
        description_es="Mesita de noche individual. Budget: melamina. Mid: lacado o roble. High: nogal, diseño. Luxury: diseño firmado.",
        typical_specs="45-55cm ancho, 35-45cm alto",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=120, mid_mid=200, mid_high=280,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1400, luxury_high=None,
        unit="ud", typical_quantity="2 per master bedroom, 1 per single",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Sklum"],
        brands_mid=["Kave Home", "Kenay", "Made.com"],
        brands_high=["Treku", "Punt", "Novamobili"],
        brands_luxury=["Poliform", "B&B Italia", "Minotti"],
        basis_notes="IKEA MALM (€45). Kave Home (€150-250). Treku (€500+). Usually bought as pair. Often matched to bed frame at mid+ tiers.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BED_WARDROBE_ML",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="BEDROOM_STORAGE",
        name_es="Armario empotrado (por metro lineal)",
        name_en="Built-in wardrobe (per linear meter)",
        description_es="Armario empotrado interior+puertas por metro lineal. Budget: melamina básica. Mid: melamina premium, soft-close. High: lacado, interiores organizados. Luxury: vestidor con iluminación.",
        typical_specs="Precio por metro lineal, altura estándar 240cm",
        budget_low=400, budget_mid=600, budget_high=800,
        mid_low=1000, mid_mid=1400, mid_high=1800,
        high_low=2200, high_mid=3000, high_high=3800,
        luxury_low=4500, luxury_mid=6500, luxury_high=None,
        unit="ml", typical_quantity="2-4ml per bedroom",
        investment_priority="alta", lifespan_years=25, energy_relevant=False,
        brands_budget=["IKEA PAX", "Leroy Merlin", "Bricomart"],
        brands_mid=["Schmidt", "Mobalpa", "Leicht"],
        brands_high=["Santos", "Dica", "Poliform"],
        brands_luxury=["Poliform Ubik", "Molteni Gliss", "B&B Italia"],
        basis_notes="IKEA PAX configured (€500-800/ml). Schmidt (€1,200-1,800/ml). Poliform (€3,000+/ml). Includes interior fittings. Carpintero local €800-1,200/ml.",
        source_retailers=["IKEA", "Schmidt stores", "Poliform dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BED_CHEST",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="BEDROOM_STORAGE",
        name_es="Cómoda",
        name_en="Chest of drawers",
        description_es="Cómoda con cajones para dormitorio. Budget: melamina. Mid: madera/lacado. High: diseño. Luxury: firmado.",
        typical_specs="80-120cm ancho, 45cm profundidad, 80-100cm alto",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=350, mid_mid=550, mid_high=750,
        high_low=950, high_mid=1500, high_high=2050,
        luxury_low=2500, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per bedroom",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Sklum"],
        brands_mid=["Kave Home", "Kenay", "La Redoute"],
        brands_high=["Treku", "Punt", "Novamobili"],
        brands_luxury=["Poliform", "Molteni", "Giorgetti"],
        basis_notes="IKEA MALM 6 cajones (€179). Kave Home (€450-700). Often not needed if wardrobe has good interior storage.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BED_BUNK",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="CHILDREN",
        name_es="Litera",
        name_en="Bunk bed",
        description_es="Litera para dos niños. Budget: metal básico. Mid: madera maciza. High: diseño con almacenaje. Luxury: configuración a medida.",
        typical_specs="Para 2 colchones 90x190/200cm",
        budget_low=150, budget_mid=280, budget_high=410,
        mid_low=550, mid_mid=850, mid_high=1150,
        high_low=1400, high_mid=2100, high_high=2800,
        luxury_low=3500, luxury_mid=5500, luxury_high=None,
        unit="ud", typical_quantity="0-1 per children's room",
        investment_priority="media", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Amazon"],
        brands_mid=["Flexa", "Asoral", "Muebles Lufe"],
        brands_high=["Rafa Kids", "Oeuf", "Nidi"],
        brands_luxury=["Custom carpentry", "Minimal design"],
        basis_notes="IKEA MYDAL (€199). Flexa Classic (€899). Popular space saver for families. Safety standards important.",
        source_retailers=["IKEA", "Flexa dealers", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BED_TRUNDLE",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="CHILDREN",
        name_es="Cama nido",
        name_en="Trundle bed",
        description_es="Cama con segunda cama extraíble debajo. Budget: básica. Mid: con almacenaje. High: diseño. Luxury: configuración premium.",
        typical_specs="Para 2 colchones 90x190cm",
        budget_low=200, budget_mid=350, budget_high=500,
        mid_low=650, mid_mid=950, mid_high=1250,
        high_low=1500, high_mid=2200, high_high=2900,
        luxury_low=3500, luxury_mid=5000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per room (guest/children)",
        investment_priority="media", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Merkamueble"],
        brands_mid=["Asoral", "Muebles Lufe", "La Redoute"],
        brands_high=["Flexa", "Nidi", "Rafa Kids"],
        brands_luxury=["Custom carpentry"],
        basis_notes="Very popular in Spain for guest rooms and children. IKEA SLÅKT (€299). Asoral (€850). Practical for occasional guests.",
        source_retailers=["IKEA", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BED_CANAPE",
        category_code="BEDROOM_FURNITURE",
        subcategory_code="SLEEPING",
        name_es="Canapé abatible 150cm",
        name_en="Storage bed base 150cm",
        description_es="Base de cama con almacenaje interior (tapa abatible). Budget: tela básica. Mid: polipiel/tela premium. High: tapizado premium. Luxury: diseño integrado.",
        typical_specs="Para colchón 150x190/200cm, hueco ~30cm alto",
        budget_low=250, budget_mid=400, budget_high=550,
        mid_low=700, mid_mid=950, mid_high=1200,
        high_low=1400, high_mid=1900, high_high=2400,
        luxury_low=2800, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="1 per bedroom (alternative to base)",
        investment_priority="media", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Merkamueble"],
        brands_mid=["Flex", "Pikolin", "Tediber"],
        brands_high=["Relax", "Jensen", "Tempur"],
        brands_luxury=["Custom upholstery"],
        basis_notes="Very popular in Spanish apartments for storage. IKEA MALM storage (€399). Tediber canapé (€590). Essential where closet space limited.",
        source_retailers=["IKEA", "Tediber", "Flex stores"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: BATHROOM FFE (Not sanitaryware - that's BCCA)
# =============================================================================

BATHROOM_FFE = [
    FFEItem(
        code="FFE_BATH_MIRROR_STANDARD",
        category_code="BATHROOM_FFE",
        subcategory_code=None,
        name_es="Espejo baño estándar",
        name_en="Standard bathroom mirror",
        description_es="Espejo de baño sin iluminación. Budget: básico marco. Mid: sin marco pulido. High: diseño. Luxury: firmado.",
        typical_specs="60-80cm ancho, 70-100cm alto",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=120, mid_mid=200, mid_high=280,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1500, luxury_high=None,
        unit="ud", typical_quantity="1 per bathroom",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Bricomart"],
        brands_mid=["Roca", "Duravit basic", "Cosmic"],
        brands_high=["Inbani", "Cosmic premium", "Antonio Lupi"],
        brands_luxury=["Agape", "Boffi", "Antonio Lupi"],
        basis_notes="IKEA GODMORGON (€59). Leroy Merlin (€80-150). Roca (€200-350). Designer mirrors €500+.",
        source_retailers=["IKEA", "Leroy Merlin", "Roca stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BATH_MIRROR_LED",
        category_code="BATHROOM_FFE",
        subcategory_code=None,
        name_es="Espejo baño con LED",
        name_en="LED bathroom mirror",
        description_es="Espejo con iluminación LED integrada. Budget: LED básico. Mid: LED perimetral, antivaho. High: táctil, sensor. Luxury: diseño inteligente.",
        typical_specs="60-100cm ancho, LED integrado, antivaho opcional",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=300, mid_mid=500, mid_high=700,
        high_low=850, high_mid=1300, high_high=1750,
        luxury_low=2000, luxury_mid=3200, luxury_high=None,
        unit="ud", typical_quantity="1 per bathroom",
        investment_priority="media", lifespan_years=15, energy_relevant=True,
        brands_budget=["Leroy Merlin", "Amazon", "BAUHAUS"],
        brands_mid=["Roca", "Duravit", "Cosmic"],
        brands_high=["Inbani", "Antonio Lupi", "Keuco"],
        brands_luxury=["Boffi", "Agape", "Antonio Lupi premium"],
        basis_notes="Very popular upgrade. Leroy Merlin LED (€150-300). Roca Prisma LED (€450). Inbani (€900+). Antivaho standard at mid+.",
        source_retailers=["Leroy Merlin", "Roca stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BATH_TOWEL_HEATED",
        category_code="BATHROOM_FFE",
        subcategory_code=None,
        name_es="Toallero radiador",
        name_en="Heated towel rail",
        description_es="Radiador toallero eléctrico o de agua. Budget: eléctrico básico. Mid: eléctrico cromado. High: diseño. Luxury: firmado.",
        typical_specs="50-60cm ancho, 80-120cm alto, eléctrico o agua",
        budget_low=60, budget_mid=120, budget_high=180,
        mid_low=250, mid_mid=400, mid_high=550,
        high_low=700, high_mid=1100, high_high=1500,
        luxury_low=1800, luxury_mid=2800, luxury_high=None,
        unit="ud", typical_quantity="1 per bathroom",
        investment_priority="media", lifespan_years=15, energy_relevant=True,
        brands_budget=["Leroy Merlin", "Bricomart", "Amazon"],
        brands_mid=["Roca", "Zehnder basic", "Deltacalor"],
        brands_high=["Zehnder", "Vasco", "Tubes"],
        brands_luxury=["Tubes Scaletta", "Antrax", "Vola"],
        basis_notes="Leroy Merlin básico (€120). Zehnder Metropolitan (€450). Tubes Scaletta (€1,200+). Eléctrico más fácil de instalar.",
        source_retailers=["Leroy Merlin", "Porcelanosa"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BATH_TOWEL_RACK",
        category_code="BATHROOM_FFE",
        subcategory_code=None,
        name_es="Toallero simple",
        name_en="Towel rack/bar",
        description_es="Barra o anilla para toallas sin calefacción. Budget: cromado básico. Mid: inox cepillado. High: diseño. Luxury: firmado.",
        typical_specs="Barra 50-60cm o anilla",
        budget_low=15, budget_mid=30, budget_high=45,
        mid_low=60, mid_mid=100, mid_high=140,
        high_low=180, high_mid=280, high_high=380,
        luxury_low=450, luxury_mid=700, luxury_high=None,
        unit="ud", typical_quantity="1-2 per bathroom",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Bricomart"],
        brands_mid=["Roca", "Tres Grifería", "Grohe"],
        brands_high=["Dornbracht", "Keuco", "Fantini"],
        brands_luxury=["Vola", "Agape", "Boffi"],
        basis_notes="IKEA (€15-30). Roca Victoria (€60). Dornbracht (€250+). Often included in accessory sets.",
        source_retailers=["IKEA", "Leroy Merlin"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BATH_ACCESSORIES_SET",
        category_code="BATHROOM_FFE",
        subcategory_code=None,
        name_es="Set accesorios baño (5 piezas)",
        name_en="Bathroom accessories set (5 pieces)",
        description_es="Conjunto: portarrollos, escobillero, jabonera, vaso, gancho. Budget: plástico/cromado. Mid: inox cepillado. High: diseño coordinado. Luxury: firmado.",
        typical_specs="5 piezas coordinadas",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=150, mid_mid=280, mid_high=410,
        high_low=500, high_mid=800, high_high=1100,
        luxury_low=1400, luxury_mid=2200, luxury_high=None,
        unit="set", typical_quantity="1 set per bathroom",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Primark Home"],
        brands_mid=["Roca", "Tres Grifería", "Cosmic"],
        brands_high=["Keuco", "Emco", "Inda"],
        brands_luxury=["Vola", "Agape", "Boffi"],
        basis_notes="IKEA BALUNGEN set (€50). Roca Victoria set (€250). Keuco (€600+). Coordinated finish important.",
        source_retailers=["IKEA", "Leroy Merlin", "Porcelanosa"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_BATH_STORAGE",
        category_code="BATHROOM_FFE",
        subcategory_code=None,
        name_es="Mueble auxiliar baño",
        name_en="Bathroom storage unit",
        description_es="Columna o estantería auxiliar para baño. Budget: MDF lacado. Mid: madera resistente. High: diseño. Luxury: integrado premium.",
        typical_specs="30-40cm ancho, columna o bajo",
        budget_low=50, budget_mid=100, budget_high=150,
        mid_low=220, mid_mid=380, mid_high=540,
        high_low=700, high_mid=1100, high_high=1500,
        luxury_low=1800, luxury_mid=2800, luxury_high=None,
        unit="ud", typical_quantity="0-1 per bathroom",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Bricomart"],
        brands_mid=["Roca", "Duravit", "Salgar"],
        brands_high=["Inbani", "Burgbad", "Laufen"],
        brands_luxury=["Boffi", "Antonio Lupi", "Agape"],
        basis_notes="IKEA LILLÅNGEN (€99). Roca Victoria (€350). Often not needed if under-sink storage sufficient.",
        source_retailers=["IKEA", "Porcelanosa"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: LIGHTING
# =============================================================================

LIGHTING = [
    FFEItem(
        code="FFE_LIGHT_PENDANT_S",
        category_code="LIGHTING",
        subcategory_code=None,
        name_es="Lámpara colgante pequeña (<40cm)",
        name_en="Small pendant light (<40cm)",
        description_es="Lámpara colgante pequeña para pasillos, cocina. Budget: básica. Mid: diseño español. High: premium. Luxury: firmada.",
        typical_specs="<40cm diámetro",
        budget_low=25, budget_mid=50, budget_high=75,
        mid_low=100, mid_mid=180, mid_high=260,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1400, luxury_high=None,
        unit="ud", typical_quantity="2-4 per property",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Amazon"],
        brands_mid=["Faro Barcelona", "Schuller", "Mantra"],
        brands_high=["Marset", "Vibia", "Santa & Cole"],
        brands_luxury=["Foscarini", "Flos", "Louis Poulsen"],
        basis_notes="IKEA HEKTAR (€29). Faro (€80-200). Marset Tam Tam (€400). Good for multiples over kitchen island.",
        source_retailers=["IKEA", "La Casa de la Lámpara"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIGHT_PENDANT_M",
        category_code="LIGHTING",
        subcategory_code=None,
        name_es="Lámpara colgante mediana (40-60cm)",
        name_en="Medium pendant light (40-60cm)",
        description_es="Lámpara colgante mediana para comedor/salón. Budget: básica industrial. Mid: diseño español (Faro). High: Marset, Vibia. Luxury: diseño firmado.",
        typical_specs="40-60cm diámetro",
        budget_low=40, budget_mid=80, budget_high=120,
        mid_low=180, mid_mid=350, mid_high=500,
        high_low=600, high_mid=1000, high_high=1500,
        luxury_low=1800, luxury_mid=2800, luxury_high=None,
        unit="ud", typical_quantity="1-2 per property",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Amazon"],
        brands_mid=["Faro Barcelona", "Schuller", "Mantra"],
        brands_high=["Marset", "Vibia", "Santa & Cole", "LZF"],
        brands_luxury=["Foscarini", "Flos", "Moooi", "Louis Poulsen"],
        basis_notes="Spanish lighting brands excellent value: Faro (€150-400), Marset (€500-1,500). Vibia Skan (€800). Louis Poulsen PH (€1,200+).",
        source_retailers=["IKEA", "La Casa de la Lámpara", "Marset store"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIGHT_PENDANT_L",
        category_code="LIGHTING",
        subcategory_code=None,
        name_es="Lámpara colgante grande (>60cm)",
        name_en="Large pendant light (>60cm)",
        description_es="Lámpara colgante grande, statement piece. Budget: industrial grande. Mid: diseño español. High: premium. Luxury: icónica.",
        typical_specs=">60cm diámetro, statement piece",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=350, mid_mid=600, mid_high=850,
        high_low=1100, high_mid=1800, high_high=2500,
        luxury_low=3000, luxury_mid=5000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per property",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Amazon industrial"],
        brands_mid=["Faro Barcelona", "LZF", "Arturo Álvarez"],
        brands_high=["Marset Discoco", "Vibia", "Santa & Cole"],
        brands_luxury=["Flos Skygarden", "Moooi", "Foscarini Caboche"],
        basis_notes="Statement dining room piece. LZF Nut (€850). Flos Skygarden (€2,500). Dramatic impact in double-height spaces.",
        source_retailers=["La Casa de la Lámpara", "Design stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIGHT_FLOOR",
        category_code="LIGHTING",
        subcategory_code=None,
        name_es="Lámpara de pie",
        name_en="Floor lamp",
        description_es="Lámpara de pie para salón/rincón lectura. Budget: básica. Mid: diseño nórdico. High: icónica. Luxury: edición limitada.",
        typical_specs="150-180cm altura",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=150, mid_mid=280, mid_high=410,
        high_low=550, high_mid=900, high_high=1250,
        luxury_low=1500, luxury_mid=2500, luxury_high=None,
        unit="ud", typical_quantity="1-2 per property",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Maisons du Monde", "Amazon"],
        brands_mid=["Faro Barcelona", "Schuller", "Normann Copenhagen"],
        brands_high=["Santa & Cole Tripode", "Marset", "Vibia"],
        brands_luxury=["Flos Arco", "Foscarini Twiggy", "Artemide"],
        basis_notes="IKEA RANARP (€35). Santa & Cole Tripode G5 (€750). Flos Arco (€2,200) is iconic. Good ambient light for living rooms.",
        source_retailers=["IKEA", "La Casa de la Lámpara"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIGHT_TABLE",
        category_code="LIGHTING",
        subcategory_code=None,
        name_es="Lámpara de mesa",
        name_en="Table lamp",
        description_es="Lámpara de sobremesa para mesitas/consolas. Budget: básica. Mid: diseño. High: premium. Luxury: icónica.",
        typical_specs="30-50cm altura",
        budget_low=20, budget_mid=40, budget_high=60,
        mid_low=100, mid_mid=180, mid_high=260,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1500, luxury_high=None,
        unit="ud", typical_quantity="2-4 per property",
        investment_priority="baja", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Zara Home", "Maisons du Monde"],
        brands_mid=["Faro Barcelona", "Kartell", "HAY"],
        brands_high=["Marset", "Vibia", "Santa & Cole"],
        brands_luxury=["Flos", "Artemide", "Ingo Maurer"],
        basis_notes="IKEA LAMPAN (€5). Kartell Bourgie (€300). Flos Taccia (€900). Good for bedside and living room accents.",
        source_retailers=["IKEA", "La Casa de la Lámpara"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIGHT_WALL",
        category_code="LIGHTING",
        subcategory_code=None,
        name_es="Aplique de pared",
        name_en="Wall sconce",
        description_es="Aplique de pared para pasillos/cabeceros. Budget: básico. Mid: LED integrado. High: diseño. Luxury: firmado.",
        typical_specs="Aplique interior decorativo",
        budget_low=20, budget_mid=40, budget_high=60,
        mid_low=80, mid_mid=150, mid_high=220,
        high_low=300, high_mid=500, high_high=700,
        luxury_low=850, luxury_mid=1300, luxury_high=None,
        unit="ud", typical_quantity="2-6 per property",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Amazon"],
        brands_mid=["Faro Barcelona", "Schuller", "Mantra"],
        brands_high=["Marset", "Vibia", "Santa & Cole"],
        brands_luxury=["Flos", "Artemide", "Foscarini"],
        basis_notes="IKEA (€20-40). Faro aplique (€80-200). Marset Bicoca (€200). Popular for bedside reading and hallways.",
        source_retailers=["IKEA", "La Casa de la Lámpara"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIGHT_CHANDELIER",
        category_code="LIGHTING",
        subcategory_code=None,
        name_es="Lámpara araña / lustre",
        name_en="Chandelier",
        description_es="Lámpara de araña tradicional o moderna. Budget: acrílico/metal. Mid: cristal básico. High: cristal premium. Luxury: cristal artesanal.",
        typical_specs="60-100cm diámetro, múltiples brazos",
        budget_low=150, budget_mid=300, budget_high=450,
        mid_low=600, mid_mid=1000, mid_high=1400,
        high_low=1800, high_mid=3000, high_high=4200,
        luxury_low=5000, luxury_mid=10000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per property",
        investment_priority="baja", lifespan_years=30, energy_relevant=False,
        brands_budget=["Amazon", "Leroy Merlin", "Maisons du Monde"],
        brands_mid=["Schuller", "Italamp", "Eglo"],
        brands_high=["Barovier & Toso", "Italamp premium"],
        brands_luxury=["Venini", "Baccarat", "Swarovski"],
        basis_notes="For traditional or dramatic spaces. Amazon (€200-500). Italamp (€1,000-2,000). Venini Murano (€5,000+). Not common in modern renovations.",
        source_retailers=["Amazon", "La Casa de la Lámpara", "Design stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LIGHT_RECESSED_PACK",
        category_code="LIGHTING",
        subcategory_code=None,
        name_es="Pack downlights empotrados (6 uds)",
        name_en="Recessed downlights pack (6 pcs)",
        description_es="Pack de focos empotrados LED. Budget: básicos fijos. Mid: orientables, CRI90. High: Dim to Warm. Luxury: diseño arquitectónico.",
        typical_specs="Pack 6 unidades, LED, empotrar en techo",
        budget_low=40, budget_mid=80, budget_high=120,
        mid_low=180, mid_mid=300, mid_high=420,
        high_low=550, high_mid=900, high_high=1250,
        luxury_low=1500, luxury_mid=2400, luxury_high=None,
        unit="pack", typical_quantity="2-4 packs per property",
        investment_priority="alta", lifespan_years=15, energy_relevant=True,
        brands_budget=["IKEA", "Leroy Merlin", "Philips básico"],
        brands_mid=["Philips HUE", "FLOS Easy", "Arkoslight"],
        brands_high=["iGuzzini", "Deltalight", "Arkoslight pro"],
        brands_luxury=["Flos Architectural", "Erco", "Kreon"],
        basis_notes="Note: Installation is BCCA. This is just fixtures. IKEA LAKENE pack (€80). Arkoslight (€300/6). Good general lighting foundation.",
        source_retailers=["IKEA", "Leroy Merlin", "Arkoslight dealers"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: TEXTILES
# =============================================================================

TEXTILES = [
    FFEItem(
        code="FFE_TEXT_CURTAIN",
        category_code="TEXTILES",
        subcategory_code="WINDOW",
        name_es="Cortina confeccionada (por ventana)",
        name_en="Ready-made curtain (per window)",
        description_es="Cortina confeccionada lista para colgar. Budget: poliéster. Mid: lino sintético o algodón. High: lino natural. Luxury: a medida.",
        typical_specs="Por ventana estándar (140cm ancho)",
        budget_low=50, budget_mid=100, budget_high=150,
        mid_low=200, mid_mid=350, mid_high=500,
        high_low=600, high_mid=1000, high_high=1400,
        luxury_low=1500, luxury_mid=2500, luxury_high=None,
        unit="ud", typical_quantity="3-6 per property",
        investment_priority="media", lifespan_years=8, energy_relevant=False,
        brands_budget=["IKEA", "Zara Home", "Primark Home"],
        brands_mid=["El Corte Inglés", "Textura", "Leroy Merlin"],
        brands_high=["Gancedo", "Gastón y Daniela", "Ka International"],
        brands_luxury=["Confección a medida", "Diseñador"],
        basis_notes="IKEA AINA (€60 pair). El Corte Inglés (€150-400). Gancedo fabrics by meter (€80-200/m) + confección. Custom = €1,500+/window.",
        source_retailers=["IKEA", "El Corte Inglés", "Gancedo"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_TEXT_BLIND_ROLLER",
        category_code="TEXTILES",
        subcategory_code="WINDOW",
        name_es="Estor enrollable (por ventana)",
        name_en="Roller blind (per window)",
        description_es="Estor enrollable screen o blackout. Budget: básico. Mid: screen 5%, motorizable. High: motorizado, diseño. Luxury: automático integrado.",
        typical_specs="Por ventana, medida estándar o a medida",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=120, mid_mid=200, mid_high=280,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1400, luxury_high=None,
        unit="ud", typical_quantity="4-8 per property",
        investment_priority="media", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Bricomart"],
        brands_mid=["Kaaten", "Bandalux", "Saxun"],
        brands_high=["Bandalux premium", "Luxaflex", "Hunter Douglas"],
        brands_luxury=["Hunter Douglas motorizado", "Lutron"],
        basis_notes="IKEA FRIDANS (€35). Kaaten a medida (€150-250). Bandalux motorizado (€400+). Screen popular for control light without blocking.",
        source_retailers=["IKEA", "Leroy Merlin", "Kaaten"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_TEXT_BLIND_VENETIAN",
        category_code="TEXTILES",
        subcategory_code="WINDOW",
        name_es="Persiana veneciana (por ventana)",
        name_en="Venetian blind (per window)",
        description_es="Persiana veneciana aluminio o madera. Budget: aluminio básica. Mid: aluminio premium. High: madera. Luxury: madera premium/motorizada.",
        typical_specs="Por ventana, lamas aluminio o madera",
        budget_low=40, budget_mid=80, budget_high=120,
        mid_low=150, mid_mid=250, mid_high=350,
        high_low=450, high_mid=700, high_high=950,
        luxury_low=1100, luxury_mid=1700, luxury_high=None,
        unit="ud", typical_quantity="0-4 per property",
        investment_priority="baja", lifespan_years=12, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Bricomart"],
        brands_mid=["Kaaten", "Luxaflex basic", "Bandalux"],
        brands_high=["Luxaflex Wood", "Hunter Douglas", "Bandalux"],
        brands_luxury=["Hunter Douglas premium", "Lutron"],
        basis_notes="Less common than rollers in Spain. IKEA LINDMON (€80). Luxaflex wood (€400+). Good for offices and specific aesthetic.",
        source_retailers=["IKEA", "Leroy Merlin", "Luxaflex dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_TEXT_RUG_S",
        category_code="TEXTILES",
        subcategory_code="FLOOR",
        name_es="Alfombra pequeña (<2m²)",
        name_en="Small rug (<2m²)",
        description_es="Alfombra pequeña para entrada/baño. Budget: sintética. Mid: algodón/yute. High: lana. Luxury: artesanal.",
        typical_specs="<2m², entrada o pie de cama",
        budget_low=20, budget_mid=50, budget_high=80,
        mid_low=120, mid_mid=200, mid_high=280,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1500, luxury_high=None,
        unit="ud", typical_quantity="1-3 per property",
        investment_priority="baja", lifespan_years=8, energy_relevant=False,
        brands_budget=["IKEA", "Primark Home", "Amazon"],
        brands_mid=["Zara Home", "La Redoute", "Sklum"],
        brands_high=["Nanimarquina small", "GAN", "Now Carpets"],
        brands_luxury=["Nanimarquina", "The Rug Company"],
        basis_notes="IKEA (€20-60). Zara Home (€80-150). Small format, often decorative accent.",
        source_retailers=["IKEA", "Zara Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_TEXT_RUG_M",
        category_code="TEXTILES",
        subcategory_code="FLOOR",
        name_es="Alfombra mediana (2-4m²)",
        name_en="Medium rug (2-4m²)",
        description_es="Alfombra mediana para dormitorio. Budget: sintética. Mid: lana/algodón. High: lana premium. Luxury: artesanal.",
        typical_specs="2-4m², típico 160x230cm",
        budget_low=60, budget_mid=120, budget_high=180,
        mid_low=280, mid_mid=450, mid_high=620,
        high_low=800, high_mid=1300, high_high=1800,
        luxury_low=2200, luxury_mid=3500, luxury_high=None,
        unit="ud", typical_quantity="1-2 per property",
        investment_priority="media", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Sklum", "Amazon"],
        brands_mid=["Kave Home", "La Redoute", "Benuta"],
        brands_high=["Nanimarquina", "GAN", "Now Carpets"],
        brands_luxury=["Nanimarquina", "The Rug Company", "CC-Tapis"],
        basis_notes="IKEA STOENSE (€129). Kave Home (€300-500). Nanimarquina (€1,500+). Good for bedrooms.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_TEXT_RUG_L",
        category_code="TEXTILES",
        subcategory_code="FLOOR",
        name_es="Alfombra grande (>4m², ~200x300)",
        name_en="Large area rug (>4m²)",
        description_es="Alfombra decorativa grande para salón. Budget: sintética. Mid: lana/algodón. High: lana premium/sisal. Luxury: vintage o diseño.",
        typical_specs="200x300cm aproximadamente, >4m²",
        budget_low=100, budget_mid=250, budget_high=400,
        mid_low=500, mid_mid=900, mid_high=1300,
        high_low=1500, high_mid=2800, high_high=4000,
        luxury_low=4500, luxury_mid=7000, luxury_high=None,
        unit="ud", typical_quantity="1 per living room",
        investment_priority="media", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Sklum", "Amazon"],
        brands_mid=["Kave Home", "La Redoute", "Benuta"],
        brands_high=["Nanimarquina", "GAN", "Now Carpets"],
        brands_luxury=["Diurne", "The Rug Company", "Vintage Persian"],
        basis_notes="GAN and Nanimarquina are Spanish high-end brands. Nanimarquina Bicicleta (€2,500). Vintage Persian varies wildly.",
        source_retailers=["IKEA", "Kave Home", "Nanimarquina store"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_TEXT_BEDDING",
        category_code="TEXTILES",
        subcategory_code="SOFT",
        name_es="Juego ropa cama completo (150cm)",
        name_en="Complete bedding set (150cm)",
        description_es="Funda nórdica + sábanas + fundas almohada. Budget: polialgodón. Mid: algodón 200TC. High: algodón 400TC, percal. Luxury: lino/seda.",
        typical_specs="Juego completo para cama 150cm",
        budget_low=40, budget_mid=70, budget_high=100,
        mid_low=150, mid_mid=250, mid_high=350,
        high_low=450, high_mid=700, high_high=950,
        luxury_low=1100, luxury_mid=1800, luxury_high=None,
        unit="set", typical_quantity="2 sets per bed (rotation)",
        investment_priority="alta", lifespan_years=5, energy_relevant=False,
        brands_budget=["IKEA", "Primark", "Carrefour"],
        brands_mid=["Zara Home", "H&M Home", "El Corte Inglés"],
        brands_high=["Casa de Cotó", "Yves Delorme", "Descamps"],
        brands_luxury=["Frette", "Pratesi", "D. Porthault"],
        basis_notes="IKEA DVALA (€50). Zara Home (€150-300). Frette (€800+). Thread count matters: budget 120TC, luxury 600TC+.",
        source_retailers=["IKEA", "Zara Home", "El Corte Inglés"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_TEXT_CUSHIONS",
        category_code="TEXTILES",
        subcategory_code="SOFT",
        name_es="Set cojines decorativos (4 uds)",
        name_en="Decorative cushion set (4 pcs)",
        description_es="Set de cojines decorativos para sofá. Budget: poliéster. Mid: algodón/lino. High: diseño. Luxury: firmado.",
        typical_specs="4 cojines 45x45cm aproximadamente",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=120, mid_mid=200, mid_high=280,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1400, luxury_high=None,
        unit="set", typical_quantity="1-2 sets per living room",
        investment_priority="baja", lifespan_years=5, energy_relevant=False,
        brands_budget=["IKEA", "Primark", "H&M Home"],
        brands_mid=["Zara Home", "Maisons du Monde", "Sklum"],
        brands_high=["HAY", "Ferm Living", "Muuto"],
        brands_luxury=["Hermès", "Loro Piana", "Dedar"],
        basis_notes="IKEA (€5-15/each). Zara Home (€25-50/each). Design cushions €100+/each. Quick way to refresh sofas.",
        source_retailers=["IKEA", "Zara Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_TEXT_TOWELS",
        category_code="TEXTILES",
        subcategory_code="SOFT",
        name_es="Juego toallas baño (6 piezas)",
        name_en="Bath towel set (6 pieces)",
        description_es="Set 2 toallas baño + 2 lavabo + 2 tocador. Budget: algodón básico. Mid: 500gsm. High: 700gsm egipcio. Luxury: orgánico/diseño.",
        typical_specs="6 piezas coordinadas",
        budget_low=25, budget_mid=50, budget_high=75,
        mid_low=100, mid_mid=180, mid_high=260,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1400, luxury_high=None,
        unit="set", typical_quantity="2 sets per bathroom",
        investment_priority="media", lifespan_years=5, energy_relevant=False,
        brands_budget=["IKEA", "Primark", "Carrefour"],
        brands_mid=["Zara Home", "El Corte Inglés", "H&M Home"],
        brands_high=["Sheridan", "Christy", "Descamps"],
        brands_luxury=["Frette", "Abyss & Habidecor", "Pratesi"],
        basis_notes="IKEA VÅGSJÖN (€40/set). Zara Home (€100-200/set). GSM (grams/m²) indicates quality: 400=basic, 700=luxury.",
        source_retailers=["IKEA", "Zara Home", "El Corte Inglés"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: OUTDOOR
# =============================================================================

OUTDOOR = [
    FFEItem(
        code="FFE_OUT_DINING_SET_4",
        category_code="OUTDOOR",
        subcategory_code=None,
        name_es="Conjunto comedor exterior 4 personas",
        name_en="4-person outdoor dining set",
        description_es="Mesa + 4 sillas para terraza. Budget: resina/acero. Mid: aluminio. High: teca/aluminio premium. Luxury: diseño.",
        typical_specs="Mesa 90-120cm + 4 sillas",
        budget_low=150, budget_mid=300, budget_high=450,
        mid_low=650, mid_mid=1000, mid_high=1350,
        high_low=1700, high_mid=2600, high_high=3500,
        luxury_low=4500, luxury_mid=7000, luxury_high=None,
        unit="set", typical_quantity="1 per terrace",
        investment_priority="media", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Carrefour"],
        brands_mid=["Kave Home", "Sklum", "Made.com"],
        brands_high=["Kettal", "Tribu", "Gloster"],
        brands_luxury=["Kettal premium", "Paola Lenti", "Roda"],
        basis_notes="IKEA SJÄLLAND (€299). Kave Home (€800-1,200). Kettal (€2,500+). Weather resistance critical.",
        source_retailers=["IKEA", "Kave Home", "Kettal dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OUT_LOUNGE_SET",
        category_code="OUTDOOR",
        subcategory_code=None,
        name_es="Conjunto sofás exterior",
        name_en="Outdoor lounge set",
        description_es="Sofá + sillones exterior para terraza grande. Budget: resina trenzada. Mid: aluminio + cojines. High: diseño premium. Luxury: firmado.",
        typical_specs="Sofá 2-3 plazas + 2 sillones",
        budget_low=400, budget_mid=700, budget_high=1000,
        mid_low=1400, mid_mid=2200, mid_high=3000,
        high_low=4000, high_mid=6500, high_high=9000,
        luxury_low=12000, luxury_mid=20000, luxury_high=None,
        unit="set", typical_quantity="0-1 per large terrace",
        investment_priority="media", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Maisons du Monde"],
        brands_mid=["Kave Home", "Sklum", "Made.com"],
        brands_high=["Kettal", "Gandia Blasco", "Tribu"],
        brands_luxury=["Paola Lenti", "Roda", "B&B Italia Outdoor"],
        basis_notes="IKEA SOLLERÖN (€700). Kave Home (€1,500-2,500). Gandia Blasco (€5,000+). Only for larger terraces.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OUT_LOUNGER",
        category_code="OUTDOOR",
        subcategory_code=None,
        name_es="Tumbona",
        name_en="Sun lounger",
        description_es="Tumbona para terraza/piscina. Budget: resina. Mid: aluminio textilene. High: teca/diseño. Luxury: firmada.",
        typical_specs="Reclinable, para exterior",
        budget_low=50, budget_mid=100, budget_high=150,
        mid_low=250, mid_mid=450, mid_high=650,
        high_low=900, high_mid=1500, high_high=2100,
        luxury_low=2800, luxury_mid=4500, luxury_high=None,
        unit="ud", typical_quantity="0-2 per terrace/pool",
        investment_priority="baja", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Carrefour"],
        brands_mid=["Kave Home", "Sklum", "Made.com"],
        brands_high=["Kettal", "Tribu", "Gandia Blasco"],
        brands_luxury=["Paola Lenti", "Roda", "Dedon"],
        basis_notes="IKEA FALSTER (€99). Kave Home (€350-600). Kettal (€1,500+). Essential for pool areas.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OUT_PARASOL",
        category_code="OUTDOOR",
        subcategory_code=None,
        name_es="Sombrilla/parasol",
        name_en="Parasol/umbrella",
        description_es="Sombrilla grande para terraza. Budget: básica. Mid: 3m+, inclinable. High: brazo lateral. Luxury: motorizada.",
        typical_specs="Diámetro 2.5-4m",
        budget_low=50, budget_mid=100, budget_high=150,
        mid_low=250, mid_mid=450, mid_high=650,
        high_low=900, high_mid=1500, high_high=2100,
        luxury_low=2800, luxury_mid=4500, luxury_high=None,
        unit="ud", typical_quantity="1 per dining/lounge area",
        investment_priority="media", lifespan_years=8, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Carrefour"],
        brands_mid=["Jardiland", "Hesperide", "Fermob"],
        brands_high=["Glatz", "Umbrosa", "Tuuci"],
        brands_luxury=["Tuuci premium", "Dedon"],
        basis_notes="IKEA LINDÖJA (€99). Glatz Alu-Smart (€500). Cantilever/side-post models €1,000+. Essential for summer use.",
        source_retailers=["IKEA", "Leroy Merlin", "Jardiland"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OUT_PLANTER_L",
        category_code="OUTDOOR",
        subcategory_code=None,
        name_es="Macetero grande",
        name_en="Large planter",
        description_es="Macetero grande para terraza. Budget: plástico. Mid: fibra/resina. High: cerámica/acero corten. Luxury: diseño.",
        typical_specs=">50cm diámetro o lado",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=150, mid_mid=280, mid_high=410,
        high_low=550, high_mid=900, high_high=1250,
        luxury_low=1500, luxury_mid=2500, luxury_high=None,
        unit="ud", typical_quantity="2-6 per terrace",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Lidl"],
        brands_mid=["Elho", "Lechuza", "Vondom basic"],
        brands_high=["Vondom", "Atelier Vierkant", "Domani"],
        brands_luxury=["Atelier Vierkant", "Domani", "Custom ceramic"],
        basis_notes="IKEA MUSKOT (€25). Lechuza Cubico (€200). Vondom (€400+). Drainage important for plants.",
        source_retailers=["IKEA", "Leroy Merlin", "Vondom dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OUT_BBQ",
        category_code="OUTDOOR",
        subcategory_code=None,
        name_es="Barbacoa",
        name_en="BBQ/Grill",
        description_es="Barbacoa para terraza. Budget: carbón básica. Mid: gas portátil. High: gas premium. Luxury: built-in.",
        typical_specs="Carbón o gas, portátil o fija",
        budget_low=50, budget_mid=120, budget_high=190,
        mid_low=350, mid_mid=600, mid_high=850,
        high_low=1200, high_mid=2000, high_high=2800,
        luxury_low=4000, luxury_mid=7000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per terrace",
        investment_priority="baja", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Carrefour"],
        brands_mid=["Weber Spirit", "Campingaz", "Char-Broil"],
        brands_high=["Weber Genesis", "Napoleon", "Broil King"],
        brands_luxury=["Weber Summit", "Big Green Egg", "Kalamazoo"],
        basis_notes="Weber Compact (€180). Weber Genesis (€1,200). Big Green Egg (€2,500+). Gas more convenient, charcoal more flavor.",
        source_retailers=["Leroy Merlin", "Weber stores", "El Corte Inglés"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: HOME OFFICE
# =============================================================================

HOME_OFFICE = [
    FFEItem(
        code="FFE_OFFICE_DESK",
        category_code="HOME_OFFICE",
        subcategory_code=None,
        name_es="Escritorio",
        name_en="Desk",
        description_es="Escritorio para home office. Budget: melamina básica. Mid: ajustable altura manual. High: ajustable eléctrico. Luxury: diseño premium.",
        typical_specs="120-160cm ancho, 60-80cm profundidad",
        budget_low=60, budget_mid=120, budget_high=180,
        mid_low=300, mid_mid=500, mid_high=700,
        high_low=900, high_mid=1400, high_high=1900,
        luxury_low=2500, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="1 per home office",
        investment_priority="alta", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Amazon Basics", "Conforama"],
        brands_mid=["FlexiSpot", "Autonomous", "Fully Jarvis"],
        brands_high=["Steelcase Ology", "Herman Miller", "USM"],
        brands_luxury=["USM Haller", "Vitra", "Knoll"],
        basis_notes="IKEA BEKANT (€229 manual, €549 electric). FlexiSpot E7 (€550). Steelcase (€1,500+). Standing desks increasingly popular.",
        source_retailers=["IKEA", "FlexiSpot", "Steelcase dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OFFICE_CHAIR",
        category_code="HOME_OFFICE",
        subcategory_code=None,
        name_es="Silla oficina ergonómica",
        name_en="Ergonomic office chair",
        description_es="Silla ergonómica para trabajo. Budget: básica con ruedas. Mid: ajustable, soporte lumbar. High: mesh premium. Luxury: icónica.",
        typical_specs="Ajustable altura, soporte lumbar",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=350, mid_mid=550, mid_high=750,
        high_low=950, high_mid=1400, high_high=1850,
        luxury_low=2200, luxury_mid=3500, luxury_high=None,
        unit="ud", typical_quantity="1 per desk",
        investment_priority="alta", lifespan_years=12, energy_relevant=False,
        brands_budget=["IKEA", "Amazon Basics", "Songmics"],
        brands_mid=["Secretlab", "Autonomous", "Branch"],
        brands_high=["Herman Miller Aeron", "Steelcase Leap", "HAG"],
        brands_luxury=["Herman Miller Embody", "Vitra ID", "Humanscale Freedom"],
        basis_notes="IKEA MARKUS (€199). Secretlab Titan (€500). Herman Miller Aeron (€1,400). Worth investment for daily use.",
        source_retailers=["IKEA", "Secretlab", "Herman Miller dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OFFICE_SHELF",
        category_code="HOME_OFFICE",
        subcategory_code=None,
        name_es="Estantería despacho",
        name_en="Office bookshelf",
        description_es="Estantería para despacho/documentos. Budget: básica. Mid: modular. High: diseño. Luxury: sistema premium.",
        typical_specs="80-200cm ancho, varios niveles",
        budget_low=50, budget_mid=100, budget_high=150,
        mid_low=250, mid_mid=450, mid_high=650,
        high_low=900, high_mid=1500, high_high=2100,
        luxury_low=2800, luxury_mid=4500, luxury_high=None,
        unit="ud", typical_quantity="1 per office",
        investment_priority="media", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Amazon", "Conforama"],
        brands_mid=["String System", "Vitsoe 606", "Muuto"],
        brands_high=["USM Haller", "String premium", "Hay"],
        brands_luxury=["USM Haller configured", "Vitsoe 606", "Cassina"],
        basis_notes="IKEA BILLY (€79). String System (€400-1,000). USM Haller (€1,500+). Modular systems grow with needs.",
        source_retailers=["IKEA", "String dealers", "USM dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OFFICE_STORAGE",
        category_code="HOME_OFFICE",
        subcategory_code=None,
        name_es="Cajonera/archivador",
        name_en="File cabinet/drawer unit",
        description_es="Cajonera bajo mesa o archivador. Budget: melamina. Mid: metal con ruedas. High: diseño. Luxury: premium.",
        typical_specs="3-4 cajones, bajo mesa o independiente",
        budget_low=40, budget_mid=80, budget_high=120,
        mid_low=180, mid_mid=300, mid_high=420,
        high_low=550, high_mid=900, high_high=1250,
        luxury_low=1500, luxury_mid=2400, luxury_high=None,
        unit="ud", typical_quantity="1 per desk",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Amazon", "Staples"],
        brands_mid=["Bisley", "Herman Miller tu", "Vitra"],
        brands_high=["USM Haller", "Herman Miller", "Vitra premium"],
        brands_luxury=["USM Haller", "Knoll", "Cassina"],
        basis_notes="IKEA ALEX (€99). Bisley (€250). USM (€800+). Mobile pedestals popular for flexibility.",
        source_retailers=["IKEA", "Bisley dealers", "USM dealers"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_OFFICE_MONITOR_ARM",
        category_code="HOME_OFFICE",
        subcategory_code=None,
        name_es="Brazo monitor",
        name_en="Monitor arm",
        description_es="Brazo articulado para monitor. Budget: básico fijo. Mid: ajustable. High: gas spring premium. Luxury: para múltiples monitores.",
        typical_specs="Para monitores 17-32 pulgadas",
        budget_low=25, budget_mid=50, budget_high=75,
        mid_low=100, mid_mid=180, mid_high=260,
        high_low=350, high_mid=550, high_high=750,
        luxury_low=900, luxury_mid=1400, luxury_high=None,
        unit="ud", typical_quantity="1-2 per desk",
        investment_priority="media", lifespan_years=10, energy_relevant=False,
        brands_budget=["Amazon Basics", "IKEA", "Aliexpress"],
        brands_mid=["Ergotron LX", "Humanscale M2", "CBS Ollin"],
        brands_high=["Ergotron HX", "Humanscale M8", "CBS Flo"],
        brands_luxury=["Herman Miller Flo", "Humanscale premium"],
        basis_notes="Amazon Basics (€40). Ergotron LX (€180). Essential for ergonomics and desk space.",
        source_retailers=["Amazon", "IKEA", "Ergotron dealers"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: DECOR
# =============================================================================

DECOR = [
    FFEItem(
        code="FFE_DECOR_WALL_ART",
        category_code="DECOR",
        subcategory_code=None,
        name_es="Cuadro/arte pared (grande)",
        name_en="Wall art (large)",
        description_es="Arte de pared grande para salón. Budget: print enmarcado. Mid: arte limitado. High: artista conocido. Luxury: original firmado.",
        typical_specs=">80cm lado mayor",
        budget_low=30, budget_mid=80, budget_high=130,
        mid_low=200, mid_mid=400, mid_high=600,
        high_low=900, high_mid=1800, high_high=2700,
        luxury_low=4000, luxury_mid=10000, luxury_high=None,
        unit="ud", typical_quantity="1-3 per property",
        investment_priority="baja", lifespan_years=50, energy_relevant=False,
        brands_budget=["IKEA", "Desenio", "Society6"],
        brands_mid=["Etsy artists", "Local galleries", "Juniqe"],
        brands_high=["Emerging artists", "Gallery pieces"],
        brands_luxury=["Established artists", "Auction houses"],
        basis_notes="IKEA frames+prints (€50-100). Desenio (€100-300). Original art varies enormously. Very personal choice.",
        source_retailers=["IKEA", "Desenio", "Galleries"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DECOR_MIRROR_DECO",
        category_code="DECOR",
        subcategory_code=None,
        name_es="Espejo decorativo",
        name_en="Decorative mirror",
        description_es="Espejo decorativo para pared (no baño). Budget: básico. Mid: marco diseño. High: artesanal. Luxury: firmado.",
        typical_specs="Varios tamaños, decorativo",
        budget_low=30, budget_mid=70, budget_high=110,
        mid_low=180, mid_mid=350, mid_high=520,
        high_low=700, high_mid=1200, high_high=1700,
        luxury_low=2200, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="1-2 per property",
        investment_priority="baja", lifespan_years=30, energy_relevant=False,
        brands_budget=["IKEA", "Maisons du Monde", "Zara Home"],
        brands_mid=["Kave Home", "HAY", "Muuto"],
        brands_high=["Gubi", "Menu", "Moebe"],
        brands_luxury=["Fiam", "Glas Italia", "Custom"],
        basis_notes="IKEA STOCKHOLM (€79). HAY Strap (€200). Decorative mirrors amplify light and space.",
        source_retailers=["IKEA", "Kave Home", "Design stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DECOR_VASE",
        category_code="DECOR",
        subcategory_code=None,
        name_es="Jarrón decorativo",
        name_en="Decorative vase",
        description_es="Jarrón para decoración/flores. Budget: cerámica básica. Mid: diseño. High: artesanal. Luxury: firmado/artístico.",
        typical_specs="Varios tamaños",
        budget_low=10, budget_mid=25, budget_high=40,
        mid_low=60, mid_mid=120, mid_high=180,
        high_low=250, high_mid=450, high_high=650,
        luxury_low=800, luxury_mid=1500, luxury_high=None,
        unit="ud", typical_quantity="3-6 per property",
        investment_priority="baja", lifespan_years=30, energy_relevant=False,
        brands_budget=["IKEA", "Zara Home", "H&M Home"],
        brands_mid=["HAY", "Muuto", "Ferm Living"],
        brands_high=["Menu", "Kähler", "Bitossi"],
        brands_luxury=["Venini", "Lalique", "Pottery artist"],
        basis_notes="IKEA (€5-20). HAY (€50-150). Designer ceramics €200+. Multiple vases create impact.",
        source_retailers=["IKEA", "Zara Home", "Design stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DECOR_PLANT_LARGE",
        category_code="DECOR",
        subcategory_code=None,
        name_es="Planta grande de interior",
        name_en="Large indoor plant",
        description_es="Planta grande para interior (sin macetero). Budget: ficus/dracena básica. Mid: Monstera/Fiddle. High: palmera/olivo. Luxury: ejemplar grande.",
        typical_specs=">100cm altura",
        budget_low=30, budget_mid=60, budget_high=90,
        mid_low=120, mid_mid=200, mid_high=280,
        high_low=400, high_mid=700, high_high=1000,
        luxury_low=1500, luxury_mid=3000, luxury_high=None,
        unit="ud", typical_quantity="2-4 per property",
        investment_priority="baja", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Mercado flores"],
        brands_mid=["Be Green", "Leaf Supply", "Garden centers"],
        brands_high=["Viveros especializados", "Be Green premium"],
        brands_luxury=["Ejemplares únicos", "Bonsái artístico"],
        basis_notes="IKEA FEJKA artificial (€30). Monstera real (€80-150). Large Fiddle Leaf Fig (€200+). Plants soften spaces.",
        source_retailers=["IKEA", "Garden centers", "Be Green"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DECOR_CLOCK",
        category_code="DECOR",
        subcategory_code=None,
        name_es="Reloj de pared",
        name_en="Wall clock",
        description_es="Reloj de pared decorativo. Budget: básico. Mid: diseño nórdico. High: icónico. Luxury: coleccionable.",
        typical_specs="25-50cm diámetro típico",
        budget_low=15, budget_mid=35, budget_high=55,
        mid_low=80, mid_mid=150, mid_high=220,
        high_low=300, high_mid=500, high_high=700,
        luxury_low=900, luxury_mid=1500, luxury_high=None,
        unit="ud", typical_quantity="1-2 per property",
        investment_priority="baja", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Amazon", "Maisons du Monde"],
        brands_mid=["HAY", "Muuto", "Normann Copenhagen"],
        brands_high=["Vitra", "Alessi", "Georg Jensen"],
        brands_luxury=["Vitra Ball Clock", "Howard Miller", "Vintage"],
        basis_notes="IKEA STOMMA (€10). HAY Wall Clock (€100). Vitra Ball Clock (€450). Functional decor.",
        source_retailers=["IKEA", "Design stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_DECOR_CANDLE_SET",
        category_code="DECOR",
        subcategory_code=None,
        name_es="Set velas/candeleros",
        name_en="Candle/candleholder set",
        description_es="Set velas y candeleros decorativos. Budget: básico. Mid: diseño. High: premium. Luxury: artesanal.",
        typical_specs="Set varios tamaños",
        budget_low=15, budget_mid=35, budget_high=55,
        mid_low=80, mid_mid=150, mid_high=220,
        high_low=300, high_mid=500, high_high=700,
        luxury_low=900, luxury_mid=1500, luxury_high=None,
        unit="set", typical_quantity="1-2 sets per property",
        investment_priority="baja", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Zara Home", "H&M Home"],
        brands_mid=["HAY", "Ferm Living", "Muuto"],
        brands_high=["Menu", "Georg Jensen", "Skultuna"],
        brands_luxury=["Georg Jensen premium", "Christofle"],
        basis_notes="IKEA JUBLA set (€10). Ferm Living (€80-150). Creates ambiance and warmth.",
        source_retailers=["IKEA", "Zara Home", "Design stores"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: LAUNDRY
# =============================================================================

LAUNDRY = [
    FFEItem(
        code="FFE_LAUND_RACK",
        category_code="LAUNDRY",
        subcategory_code=None,
        name_es="Tendedero interior/exterior",
        name_en="Drying rack",
        description_es="Tendedero para secar ropa. Budget: básico plegable. Mid: extensible. High: eléctrico/pared. Luxury: integrado.",
        typical_specs="Plegable o extensible de pared",
        budget_low=15, budget_mid=30, budget_high=45,
        mid_low=60, mid_mid=100, mid_high=140,
        high_low=180, high_mid=300, high_high=420,
        luxury_low=500, luxury_mid=800, luxury_high=None,
        unit="ud", typical_quantity="1 per laundry area",
        investment_priority="baja", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Carrefour"],
        brands_mid=["Vileda", "Artweger", "Leifheit"],
        brands_high=["Foxydry", "Ceiling-mounted", "Artweger premium"],
        brands_luxury=["Built-in", "Architectural solutions"],
        basis_notes="IKEA MULIG (€15). Vileda extensible (€80). Ceiling-mounted (€250+). Common in Spanish apartments without dryers.",
        source_retailers=["IKEA", "Leroy Merlin", "Amazon"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LAUND_CABINET",
        category_code="LAUNDRY",
        subcategory_code=None,
        name_es="Mueble columna lavandería",
        name_en="Laundry cabinet/tower",
        description_es="Columna de almacenaje para lavandería. Budget: melamina. Mid: melamina premium. High: a medida. Luxury: integrado diseño.",
        typical_specs="60-70cm ancho, 180-200cm alto",
        budget_low=80, budget_mid=150, budget_high=220,
        mid_low=300, mid_mid=500, mid_high=700,
        high_low=900, high_mid=1400, high_high=1900,
        luxury_low=2500, luxury_mid=4000, luxury_high=None,
        unit="ud", typical_quantity="0-1 per laundry area",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Bricomart"],
        brands_mid=["Salgar", "Roca laundry", "Custom"],
        brands_high=["Schmidt", "Custom carpentry"],
        brands_luxury=["Integrated with kitchen design"],
        basis_notes="IKEA ENHET (€150). Salgar (€400). Custom (€1,000+). Useful for organizing detergents, plancha, etc.",
        source_retailers=["IKEA", "Leroy Merlin"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LAUND_IRON_BOARD",
        category_code="LAUNDRY",
        subcategory_code=None,
        name_es="Tabla de planchar",
        name_en="Ironing board",
        description_es="Tabla de planchar. Budget: básica plegable. Mid: con rejilla. High: centro planchado. Luxury: integrada en mueble.",
        typical_specs="Plegable estándar o integrada",
        budget_low=20, budget_mid=40, budget_high=60,
        mid_low=80, mid_mid=140, mid_high=200,
        high_low=280, high_mid=450, high_high=620,
        luxury_low=800, luxury_mid=1200, luxury_high=None,
        unit="ud", typical_quantity="1 per property",
        investment_priority="baja", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Carrefour", "Lidl"],
        brands_mid=["Vileda", "Brabantia", "Leifheit"],
        brands_high=["Brabantia premium", "Centro planchado"],
        brands_luxury=["Built-in solutions", "Wall-mounted premium"],
        basis_notes="IKEA JÄLL (€15). Brabantia (€80-150). Centro planchado Laurastar (€500+). Wall-mounted saves space.",
        source_retailers=["IKEA", "El Corte Inglés", "Amazon"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_LAUND_BASKET",
        category_code="LAUNDRY",
        subcategory_code=None,
        name_es="Cesto ropa sucia",
        name_en="Laundry basket/hamper",
        description_es="Cesto para ropa sucia. Budget: plástico. Mid: mimbre/tela. High: diseño. Luxury: integrado en mueble.",
        typical_specs="40-60L capacidad",
        budget_low=10, budget_mid=25, budget_high=40,
        mid_low=50, mid_mid=90, mid_high=130,
        high_low=180, high_mid=300, high_high=420,
        luxury_low=500, luxury_mid=800, luxury_high=None,
        unit="ud", typical_quantity="1-2 per property",
        investment_priority="baja", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Carrefour", "Lidl"],
        brands_mid=["Zara Home", "Brabantia", "Kave Home"],
        brands_high=["Menu", "HAY", "Frost"],
        brands_luxury=["Custom integrated", "Designer pieces"],
        basis_notes="IKEA KLUNKA (€10). Brabantia (€50-100). Menu bin (€200). Often hidden in bathroom/bedroom.",
        source_retailers=["IKEA", "Zara Home", "Amazon"],
        source_year=2024
    ),
]

# =============================================================================
# ITEMS: GENERAL STORAGE
# =============================================================================

STORAGE = [
    FFEItem(
        code="FFE_STOR_ENTRANCE",
        category_code="STORAGE",
        subcategory_code=None,
        name_es="Mueble zapatero entrada",
        name_en="Shoe cabinet (entrance)",
        description_es="Zapatero para entrada. Budget: básico. Mid: con espejo. High: diseño. Luxury: a medida.",
        typical_specs="80-120cm ancho, capacidad 12-24 pares",
        budget_low=40, budget_mid=80, budget_high=120,
        mid_low=180, mid_mid=300, mid_high=420,
        high_low=550, high_mid=900, high_high=1250,
        luxury_low=1500, luxury_mid=2500, luxury_high=None,
        unit="ud", typical_quantity="1 per entrance",
        investment_priority="media", lifespan_years=15, energy_relevant=False,
        brands_budget=["IKEA", "Conforama", "Merkamueble"],
        brands_mid=["Kave Home", "Kenay", "Made.com"],
        brands_high=["Treku", "Punt", "Novamobili"],
        brands_luxury=["Custom carpentry", "Poliform"],
        basis_notes="IKEA BISSA (€50). Kave Home (€250-400). Essential in Spanish homes where shoes off is common.",
        source_retailers=["IKEA", "Kave Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_STOR_HALL_COAT",
        category_code="STORAGE",
        subcategory_code=None,
        name_es="Perchero/colgador entrada",
        name_en="Coat rack/hooks",
        description_es="Perchero de pie o ganchos de pared. Budget: básico. Mid: diseño nórdico. High: premium. Luxury: firmado.",
        typical_specs="Ganchos pared o perchero de pie",
        budget_low=15, budget_mid=35, budget_high=55,
        mid_low=80, mid_mid=150, mid_high=220,
        high_low=300, high_mid=500, high_high=700,
        luxury_low=900, luxury_mid=1500, luxury_high=None,
        unit="ud", typical_quantity="1 per entrance",
        investment_priority="baja", lifespan_years=20, energy_relevant=False,
        brands_budget=["IKEA", "Leroy Merlin", "Amazon"],
        brands_mid=["HAY", "Muuto", "Normann Copenhagen"],
        brands_high=["Vitra Hang It All", "String", "Mogg"],
        brands_luxury=["Vitra Eames", "Cassina", "Kartell"],
        basis_notes="IKEA TJUSIG (€20). HAY (€80-150). Vitra Hang It All (€300). Functional but can be design statement.",
        source_retailers=["IKEA", "Design stores"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_STOR_BASKET_SET",
        category_code="STORAGE",
        subcategory_code=None,
        name_es="Set cestas almacenaje (3 uds)",
        name_en="Storage basket set (3 pcs)",
        description_es="Set de cestas para organización. Budget: plástico/tela. Mid: mimbre/algodón. High: diseño. Luxury: artesanal.",
        typical_specs="3 tamaños diferentes",
        budget_low=15, budget_mid=35, budget_high=55,
        mid_low=70, mid_mid=120, mid_high=170,
        high_low=220, high_mid=380, high_high=540,
        luxury_low=700, luxury_mid=1100, luxury_high=None,
        unit="set", typical_quantity="2-4 sets per property",
        investment_priority="baja", lifespan_years=10, energy_relevant=False,
        brands_budget=["IKEA", "Primark", "Flying Tiger"],
        brands_mid=["Zara Home", "H&M Home", "Muji"],
        brands_high=["HAY", "Ferm Living", "Menu"],
        brands_luxury=["African baskets", "Artisan weavers"],
        basis_notes="IKEA FLADIS (€12/set). Zara Home (€60-100/set). Useful for open shelving and organization.",
        source_retailers=["IKEA", "Zara Home"],
        source_year=2024
    ),
    FFEItem(
        code="FFE_STOR_TRASTERO",
        category_code="STORAGE",
        subcategory_code=None,
        name_es="Estantería metálica trastero",
        name_en="Metal storage shelving (utility)",
        description_es="Estantería metálica para trastero/garaje. Budget: básica cromada. Mid: industrial. High: modular premium. Luxury: custom.",
        typical_specs="90-180cm ancho, 180-200cm alto, varios niveles",
        budget_low=40, budget_mid=80, budget_high=120,
        mid_low=180, mid_mid=300, mid_high=420,
        high_low=550, high_mid=900, high_high=1250,
        luxury_low=1500, luxury_mid=2500, luxury_high=None,
        unit="ud", typical_quantity="1-2 per storage room",
        investment_priority="baja", lifespan_years=20, energy_relevant=False,
        brands_budget=["Bricomart", "Leroy Merlin", "IKEA"],
        brands_mid=["Elfa", "Container Store style", "Industrial"],
        brands_high=["USM Haller", "String System"],
        brands_luxury=["Custom steel", "Architectural solutions"],
        basis_notes="Bricomart cromada (€60). IKEA OMAR (€80). For utility storage, not living spaces.",
        source_retailers=["Bricomart", "Leroy Merlin", "IKEA"],
        source_year=2024
    ),
]


# =============================================================================
# COMBINE ALL ITEMS
# =============================================================================

ALL_ITEMS = (
    KITCHEN_APPLIANCES +
    LIVING_FURNITURE +
    DINING_FURNITURE +
    BEDROOM_FURNITURE +
    BATHROOM_FFE +
    LIGHTING +
    TEXTILES +
    OUTDOOR +
    HOME_OFFICE +
    DECOR +
    LAUNDRY +
    STORAGE
)


# =============================================================================
# DATABASE BUILDER
# =============================================================================

def create_database():
    """Create the FFE database with all categories, subcategories, and items."""
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # Remove existing database
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing database: {DB_PATH}")
    
    # Connect and create schema
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("Creating schema...")
    cursor.executescript(SCHEMA_SQL)
    conn.commit()
    
    # Insert categories
    print(f"Inserting {len(CATEGORIES)} categories...")
    for cat in CATEGORIES:
        cursor.execute(
            """INSERT INTO ffe_categories (code, name_es, name_en, description_es, icon)
               VALUES (?, ?, ?, ?, ?)""",
            (cat.code, cat.name_es, cat.name_en, cat.description_es, cat.icon)
        )
    conn.commit()
    
    # Insert subcategories
    print(f"Inserting {len(SUBCATEGORIES)} subcategories...")
    for subcat in SUBCATEGORIES:
        cursor.execute(
            """INSERT INTO ffe_subcategories (code, category_code, name_es, name_en)
               VALUES (?, ?, ?, ?)""",
            (subcat.code, subcat.category_code, subcat.name_es, subcat.name_en)
        )
    conn.commit()
    
    # Insert items
    print(f"Inserting {len(ALL_ITEMS)} items...")
    today = date.today().isoformat()
    
    for item in ALL_ITEMS:
        cursor.execute(
            """INSERT INTO ffe_items (
                code, category_code, subcategory_code,
                name_es, name_en, description_es, typical_specs,
                budget_low, budget_mid, budget_high,
                mid_low, mid_mid, mid_high,
                high_low, high_mid, high_high,
                luxury_low, luxury_mid, luxury_high,
                unit, typical_quantity,
                investment_priority, lifespan_years, energy_relevant,
                brands_budget, brands_mid, brands_high, brands_luxury,
                style_tags, material_tags, finish_tags, design_era, size_category,
                basis_notes, source_retailers, source_year, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.code, item.category_code, item.subcategory_code,
                item.name_es, item.name_en, item.description_es, item.typical_specs,
                item.budget_low, item.budget_mid, item.budget_high,
                item.mid_low, item.mid_mid, item.mid_high,
                item.high_low, item.high_mid, item.high_high,
                item.luxury_low, item.luxury_mid, item.luxury_high,
                item.unit, item.typical_quantity,
                item.investment_priority, item.lifespan_years, 1 if item.energy_relevant else 0,
                json.dumps(item.brands_budget),
                json.dumps(item.brands_mid),
                json.dumps(item.brands_high),
                json.dumps(item.brands_luxury),
                json.dumps(item.style_tags),
                json.dumps(item.material_tags),
                json.dumps(item.finish_tags),
                item.design_era,
                item.size_category,
                item.basis_notes,
                json.dumps(item.source_retailers),
                item.source_year,
                today
            )
        )
    
    conn.commit()
    
    # Verify counts
    cursor.execute("SELECT COUNT(*) FROM ffe_categories")
    cat_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ffe_subcategories")
    subcat_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ffe_items")
    item_count = cursor.fetchone()[0]
    
    # Category breakdown
    print("\n" + "="*70)
    print("FFE DATABASE CREATED SUCCESSFULLY")
    print("="*70)
    print(f"\nDatabase: {DB_PATH}")
    print(f"\nCategories: {cat_count}")
    print(f"Subcategories: {subcat_count}")
    print(f"Items: {item_count}")
    
    print("\n--- Items by Category ---")
    cursor.execute("""
        SELECT c.name_es, COUNT(i.code) 
        FROM ffe_categories c 
        LEFT JOIN ffe_items i ON c.code = i.category_code 
        GROUP BY c.code 
        ORDER BY COUNT(i.code) DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} items")
    
    print("\n--- Items by Investment Priority ---")
    cursor.execute("""
        SELECT investment_priority, COUNT(*) 
        FROM ffe_items 
        GROUP BY investment_priority
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} items")
    
    print("\n--- Energy-Relevant Items ---")
    cursor.execute("SELECT COUNT(*) FROM ffe_items WHERE energy_relevant = 1")
    energy_count = cursor.fetchone()[0]
    print(f"  {energy_count} items affect energy rating")
    
    # Sample queries
    print("\n--- Sample Items (Kitchen Appliances) ---")
    cursor.execute("""
        SELECT code, name_es, budget_mid, mid_mid, high_mid, luxury_mid 
        FROM ffe_items 
        WHERE category_code = 'KITCHEN_APPLIANCES'
        LIMIT 5
    """)
    for row in cursor.fetchall():
        luxury = f"€{row[5]:,}" if row[5] else "€??+"
        print(f"  {row[0]}: {row[1]}")
        print(f"    Budget: €{row[2]:,.0f} | Mid: €{row[3]:,.0f} | High: €{row[4]:,.0f} | Luxury: {luxury}")
    
    conn.close()
    
    print("\n" + "="*70)
    print("DATABASE BUILD COMPLETE")
    print("="*70)
    print(f"\nTo use: Import from pricing/ffe_discovery.py")
    print("Example: discover_ffe(category='KITCHEN_APPLIANCES')")
    
    return DB_PATH


def verify_database():
    """Verify the database is correctly built and queryable."""
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check all items have required fields
    cursor.execute("""
        SELECT code FROM ffe_items 
        WHERE basis_notes IS NULL OR basis_notes = ''
    """)
    missing_basis = cursor.fetchall()
    if missing_basis:
        print(f"WARNING: {len(missing_basis)} items missing basis_notes:")
        for row in missing_basis:
            print(f"  - {row[0]}")
    
    # Check price ranges make sense
    cursor.execute("""
        SELECT code, name_es, budget_mid, luxury_mid
        FROM ffe_items 
        WHERE budget_mid > luxury_mid AND luxury_mid IS NOT NULL
    """)
    bad_prices = cursor.fetchall()
    if bad_prices:
        print(f"ERROR: {len(bad_prices)} items have budget > luxury:")
        for row in bad_prices:
            print(f"  - {row[0]}: {row[1]} (budget={row[2]}, luxury={row[3]})")
        return False
    
    conn.close()
    print("✅ Database verification passed")
    return True


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("FFE DATABASE BUILDER v1.0")
    print("Building granular FF&E pricing database for Unified Estimator")
    print("="*70 + "\n")
    
    # Build
    db_path = create_database()
    
    # Verify
    print("\nVerifying database...")
    if verify_database():
        print(f"\n✅ Success! Database created at: {db_path}")
        print(f"   Size: {os.path.getsize(db_path) / 1024:.1f} KB")
    else:
        print("\n❌ Database verification failed. Please check errors above.")

