"use client";

/**
 * MapModal - Clean Full-Screen Map View
 * =====================================
 * 
 * Simple Mapbox modal with:
 * - 3D buildings
 * - Layer switcher (top-left)
 * - Standard Mapbox controls (top-right)
 * - X button clearly visible
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { X, Layers, Map as MapIcon, Satellite, Sun } from "lucide-react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

// Recipient-owned public Mapbox token.
const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || "";

interface MapModalProps {
  isOpen: boolean;
  onClose: () => void;
  lat: number;
  lng: number;
  address?: string;
  title?: string;
}

type MapStyle = "streets" | "satellite" | "light";

const MAP_STYLES: Record<MapStyle, { url: string; icon: typeof MapIcon; label: string }> = {
  streets: { url: "mapbox://styles/mapbox/streets-v12", icon: MapIcon, label: "Map" },
  satellite: { url: "mapbox://styles/mapbox/satellite-streets-v12", icon: Satellite, label: "Satellite" },
  light: { url: "mapbox://styles/mapbox/light-v11", icon: Sun, label: "Light" },
};

export function MapModal({
  isOpen,
  onClose,
  lat,
  lng,
}: MapModalProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const marker = useRef<mapboxgl.Marker | null>(null);
  const [mapStyle, setMapStyle] = useState<MapStyle>("streets");
  const [isLoaded, setIsLoaded] = useState(false);
  const [showLayerMenu, setShowLayerMenu] = useState(false);

  // Initialize map
  useEffect(() => {
    if (!isOpen || !mapContainer.current || map.current || !MAPBOX_TOKEN) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: MAP_STYLES[mapStyle].url,
      center: [lng, lat],
      zoom: 16,
      pitch: 50,
      bearing: 0,
      antialias: true,
    });

    const mapInstance = map.current;

    // Add navigation controls (zoom + compass + pitch)
    mapInstance.addControl(
      new mapboxgl.NavigationControl({
        visualizePitch: true,
      }),
      "top-right"
    );

    // Add scale
    mapInstance.addControl(
      new mapboxgl.ScaleControl({ maxWidth: 100 }),
      "bottom-right"
    );

    mapInstance.on("load", () => {
      setIsLoaded(true);
      add3DBuildings(mapInstance);

      // Fly to location
      mapInstance.flyTo({
        center: [lng, lat],
        zoom: 17,
        pitch: 50,
        duration: 1500,
        essential: true,
      });
    });

    // Add property marker
    const el = document.createElement("div");
    el.innerHTML = `
      <div style="
        width: 32px;
        height: 32px;
        background: #da654d;
        border-radius: 50% 50% 50% 0;
        transform: rotate(-45deg);
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
      ">
        <div style="transform: rotate(45deg); color: white; font-size: 14px;">🏠</div>
      </div>
    `;

    marker.current = new mapboxgl.Marker({ element: el, anchor: "bottom" })
      .setLngLat([lng, lat])
      .addTo(mapInstance);

    return () => {
      marker.current?.remove();
      marker.current = null;
      map.current?.remove();
      map.current = null;
      setIsLoaded(false);
    };
  }, [isOpen, lat, lng]); // eslint-disable-line react-hooks/exhaustive-deps

  // Add 3D buildings
  const add3DBuildings = (mapInstance: mapboxgl.Map) => {
    const layers = mapInstance.getStyle().layers;
    const labelLayerId = layers?.find(
      (layer) => layer.type === "symbol" && layer.layout?.["text-field"]
    )?.id;

    if (!mapInstance.getLayer("3d-buildings")) {
      mapInstance.addLayer(
        {
          id: "3d-buildings",
          source: "composite",
          "source-layer": "building",
          filter: ["==", "extrude", "true"],
          type: "fill-extrusion",
          minzoom: 14,
          paint: {
            "fill-extrusion-color": "#d4d0cc",
            "fill-extrusion-height": ["get", "height"],
            "fill-extrusion-base": ["get", "min_height"],
            "fill-extrusion-opacity": 0.7,
          },
        },
        labelLayerId
      );
    }
  };

  // Handle style change
  const handleStyleChange = useCallback((style: MapStyle) => {
    setMapStyle(style);
    setShowLayerMenu(false);
    if (map.current) {
      map.current.setStyle(MAP_STYLES[style].url);
      map.current.once("style.load", () => {
        if (map.current) add3DBuildings(map.current);
      });
    }
  }, []);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black">
      {/* Map Container */}
      <div ref={mapContainer} className="w-full h-full" />

      {!MAPBOX_TOKEN && (
        <div className="absolute inset-0 flex items-center justify-center bg-neutral-100 p-8 text-center text-sm text-neutral-600">
          Set NEXT_PUBLIC_MAPBOX_TOKEN to show the map.
        </div>
      )}

      {/* Loading Overlay */}
      {MAPBOX_TOKEN && !isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-stone-900/80">
          <div className="w-8 h-8 border-3 border-white/20 border-t-white rounded-full animate-spin" />
        </div>
      )}

      {/* Close Button - Top Left, clearly visible */}
      <button
        onClick={onClose}
        className="absolute top-4 left-4 z-10 p-2.5 rounded-full bg-white shadow-lg text-stone-600 hover:text-stone-900 hover:bg-stone-50 transition-colors"
        aria-label="Close map"
      >
        <X className="w-5 h-5" />
      </button>

      {/* Layer Switcher - Below close button */}
      <div className="absolute top-16 left-4 z-10">
        <button
          onClick={() => setShowLayerMenu(!showLayerMenu)}
          className="p-2.5 rounded-lg bg-white shadow-lg text-stone-600 hover:text-stone-900 hover:bg-stone-50 transition-colors"
          aria-label="Change map style"
        >
          <Layers className="w-5 h-5" />
        </button>

        {/* Layer Menu Dropdown */}
        {showLayerMenu && (
          <div className="absolute top-12 left-0 bg-white rounded-lg shadow-xl overflow-hidden min-w-[140px]">
            {(Object.keys(MAP_STYLES) as MapStyle[]).map((style) => {
              const { icon: Icon, label } = MAP_STYLES[style];
              return (
                <button
                  key={style}
                  onClick={() => handleStyleChange(style)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
                    mapStyle === style
                      ? "bg-stone-100 text-stone-900 font-medium"
                      : "text-stone-600 hover:bg-stone-50"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Click outside to close layer menu */}
      {showLayerMenu && (
        <div 
          className="absolute inset-0 z-[5]" 
          onClick={() => setShowLayerMenu(false)} 
        />
      )}
    </div>
  );
}
