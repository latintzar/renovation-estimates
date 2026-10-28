"""
BCCA Price Lookup Tool (V0.4.8)
===============================

Simple price lookup for BCCA items by code.

Design Philosophy (V0.4.8):
- The BCCA INDEX (~12,565 items with 100-char AI descriptions) is included
  directly in Gemini's context
- Gemini reads the INDEX, finds matching codes semantically
- This tool simply retrieves the full price/description for a code
- NO embedding search needed - Gemini does semantic matching in-context

Why This Works:
- ~1.1MB index fits easily in Gemini's context window
- Gemini's reasoning selects appropriate codes
- Tool just does O(1) database lookup

Usage in Gemini:
    You read BCCA INDEX and find:
        09ACE00130|Alicatado azulejo 30x30 gres porcel. C1 UNE
    
    You call:
        get_bcca_price("09ACE00130")
    
    You receive:
        {
            "code": "09ACE00130",
            "price": 32.00,
            "unit": "m2",
            "full_desc": "Alicatado con azulejo cerámico 30x30 cm...",
            "found": true
        }
"""

import sqlite3
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BCCAItem:
    """A single BCCA price book item."""
    code: str
    price: float
    unit: str
    short_desc: str
    full_desc: str


class BCCAPriceLookup:
    """
    Simple price lookup by BCCA code.
    
    The heavy lifting (semantic matching) is done by Gemini reading the INDEX.
    This tool just retrieves the price and full description for a code.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize with database path.
        
        Args:
            db_path: Path to construction.db (default: pricing/construction.db)
        """
        if db_path is None:
            db_path = Path(__file__).parent / "construction.db"
        
        self.db_path = db_path
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"BCCA database not found: {self.db_path}")
    
    def get_price(self, code: str) -> Optional[BCCAItem]:
        """
        Get price and details for a BCCA code.
        
        Args:
            code: BCCA item code (e.g., "09ACE00130")
        
        Returns:
            BCCAItem or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, price, unit, short_desc, full_desc
            FROM price_book
            WHERE id = ?
        """, (code,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return BCCAItem(
                code=row[0],
                price=float(row[1]) if row[1] else 0.0,
                unit=row[2] or "ud",
                short_desc=row[3] or "",
                full_desc=row[4] or row[3] or ""
            )
        
        return None
    
    def search_by_keyword(self, keyword: str, limit: int = 10) -> list[BCCAItem]:
        """
        Search for BCCA items by keyword (fallback if Gemini needs help).
        
        Note: Prefer using the INDEX in Gemini context for semantic matching.
        This is a backup for debugging or edge cases.
        
        Args:
            keyword: Search term
            limit: Max results
        
        Returns:
            List of matching BCCAItems
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, price, unit, short_desc, full_desc
            FROM price_book
            WHERE short_desc LIKE ? OR full_desc LIKE ? OR desc_100 LIKE ?
            LIMIT ?
        """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            BCCAItem(
                code=row[0],
                price=float(row[1]) if row[1] else 0.0,
                unit=row[2] or "ud",
                short_desc=row[3] or "",
                full_desc=row[4] or row[3] or ""
            )
            for row in rows
        ]


# =============================================================================
# TOOL FUNCTION (for Gemini tool calling)
# =============================================================================

# Global instance for tool calling
_tool_instance: Optional[BCCAPriceLookup] = None


def _get_tool() -> BCCAPriceLookup:
    """Get or create the tool instance."""
    global _tool_instance
    if _tool_instance is None:
        _tool_instance = BCCAPriceLookup()
    return _tool_instance


def get_bcca_price(code: str) -> Dict[str, Any]:
    """
    Get BCCA price by code.
    
    This is the function Gemini calls as a tool.
    
    WORKFLOW:
    1. Gemini reads BCCA INDEX in context
    2. Gemini identifies relevant code based on scope item
    3. Gemini calls: get_bcca_price("09ACE00130")
    4. This function returns price + full description
    
    Args:
        code: BCCA item code (from INDEX)
    
    Returns:
        {
            "code": "09ACE00130",
            "price": 32.00,
            "unit": "m2",
            "full_desc": "Full description from database...",
            "found": true
        }
        
    Or if not found:
        {
            "code": "INVALID123",
            "found": false,
            "error": "Code INVALID123 not found in BCCA database"
        }
    """
    tool = _get_tool()
    result = tool.get_price(code)
    
    if result:
        logger.info(f"BCCA Price Lookup: {code} = €{result.price}/{result.unit}")
        return {
            "code": result.code,
            "price": result.price,
            "unit": result.unit,
            "short_desc": result.short_desc,
            "full_desc": result.full_desc,
            "found": True
        }
    else:
        logger.warning(f"BCCA Price Lookup: {code} NOT FOUND")
        return {
            "code": code,
            "found": False,
            "error": f"Code {code} not found in BCCA database"
        }


def search_bcca(keyword: str, limit: int = 10) -> Dict[str, Any]:
    """
    Search BCCA by keyword (backup tool).
    
    Use this only when you need to discover codes.
    Prefer reading the INDEX directly in context.
    
    Args:
        keyword: Search term (Spanish)
        limit: Max results (default 10)
    
    Returns:
        {
            "keyword": "alicatado",
            "results": [
                {"code": "...", "price": ..., "desc": "..."},
                ...
            ],
            "count": 5
        }
    """
    tool = _get_tool()
    results = tool.search_by_keyword(keyword, limit)
    
    logger.info(f"BCCA Search: '{keyword}' → {len(results)} results")
    
    return {
        "keyword": keyword,
        "results": [
            {
                "code": r.code,
                "price": r.price,
                "unit": r.unit,
                "desc": r.short_desc
            }
            for r in results
        ],
        "count": len(results)
    }


# =============================================================================
# FFE LOOKUP (for furniture/appliances)
# =============================================================================

class FFEPriceLookup:
    """
    FFE (Furniture, Fixtures & Equipment) price lookup.
    
    Similar to BCCA but with tier-based pricing:
    - budget_low / budget_mid / budget_high
    - mid_low / mid_mid / mid_high
    - high_low / high_mid / high_high
    - luxury_low / luxury_mid / luxury_high
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize with database path."""
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "ffe.db"
        
        self.db_path = db_path
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"FFE database not found: {self.db_path}")
    
    def get_item(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get FFE item with all tier pricing.
        
        Args:
            code: FFE item code (e.g., "FFE_SOFA_3P")
        
        Returns:
            Full item data with all tiers, or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                code, name_es, description_es, unit,
                budget_low, budget_mid, budget_high,
                mid_low, mid_mid, mid_high,
                high_low, high_mid, high_high,
                luxury_low, luxury_mid, luxury_high,
                category_code
            FROM ffe_items
            WHERE code = ?
        """, (code,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "code": row[0],
                "name_es": row[1],
                "description_es": row[2],
                "unit": row[3] or "ud",
                "pricing": {
                    "budget": {"low": row[4], "mid": row[5], "high": row[6]},
                    "mid": {"low": row[7], "mid": row[8], "high": row[9]},
                    "high": {"low": row[10], "mid": row[11], "high": row[12]},
                    "luxury": {"low": row[13], "mid": row[14], "high": row[15]},
                },
                "category": row[16],
                "found": True
            }
        
        return None


# Global FFE instance
_ffe_instance: Optional[FFEPriceLookup] = None


def _get_ffe_tool() -> FFEPriceLookup:
    """Get or create FFE tool instance."""
    global _ffe_instance
    if _ffe_instance is None:
        _ffe_instance = FFEPriceLookup()
    return _ffe_instance


def get_ffe_price(code: str, tier: str = "mid") -> Dict[str, Any]:
    """
    Get FFE price by code and tier.
    
    Args:
        code: FFE item code (e.g., "FFE_SOFA_3P")
        tier: Price tier ("budget", "mid", "high", "luxury")
    
    Returns:
        {
            "code": "FFE_SOFA_3P",
            "name": "Sofá 3 plazas",
            "tier": "mid",
            "price_low": 1200,
            "price_mid": 1850,
            "price_high": 2500,
            "unit": "ud",
            "found": true
        }
    """
    tool = _get_ffe_tool()
    result = tool.get_item(code)
    
    if result:
        tier_prices = result["pricing"].get(tier, result["pricing"]["mid"])
        
        logger.info(f"FFE Price Lookup: {code} ({tier}) = €{tier_prices['mid']}/{result['unit']}")
        
        return {
            "code": result["code"],
            "name": result["name_es"],
            "description": result["description_es"],
            "tier": tier,
            "price_low": tier_prices["low"],
            "price_mid": tier_prices["mid"],
            "price_high": tier_prices["high"],
            "unit": result["unit"],
            "category": result["category"],
            "found": True
        }
    else:
        logger.warning(f"FFE Price Lookup: {code} NOT FOUND")
        return {
            "code": code,
            "found": False,
            "error": f"Code {code} not found in FFE database"
        }

